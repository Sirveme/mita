"""
Cierre y comprobante (zMita-39, Parte B / etapa 7).

Flujo de estados de la solicitud:
  REPARACION_ACEPTADA / SOLO_DIAGNOSTICO --terminar()-->
     POR_COBRAR (si hay algo que cobrar)  --cobro digital/efectivo-->  PAGADO
     POR_CONFORMAR (si no hay nada que cobrar: solo diagnóstico ya pagado)
  PAGADO --emitir comprobante--> POR_CONFORMAR --conformidad--> CERRADO

El dinero en efectivo cobrado queda registrado "en poder del técnico" (dato para la etapa 8).
"""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("mita.cierre")

# Estados en los que el chat queda en solo lectura (se suma a los de servicio.py)
CERRADO = "CERRADO"


def _eps(a, b):
    return abs(float(a or 0) - float(b or 0)) < 0.01


def _presupuesto_aceptado(db, solicitud):
    from app.models.servicio_vivo import Presupuesto
    return (db.query(Presupuesto)
            .filter(Presupuesto.solicitud_id == solicitud.id, Presupuesto.estado == "aceptado")
            .order_by(Presupuesto.version.desc()).first())


def _visita_en_efectivo(solicitud) -> bool:
    """La visita se cobra en efectivo si NO fue prepagada (pagado=0) y el método es efectivo."""
    metodo = (solicitud.metodo_pago or "").lower()
    return metodo == "efectivo" and not solicitud.pagado


def _desglose(db, solicitud):
    # Un presupuesto aceptado = reparación por cobrar (independiente del estado actual,
    # que al momento del cobro ya pasó a POR_COBRAR/PAGADO).
    pr = _presupuesto_aceptado(db, solicitud)
    reparacion = float(pr.monto) if (pr and pr.monto) else 0.0
    visita = float(solicitud.costo_visita or 0) if _visita_en_efectivo(solicitud) else 0.0
    return {"reparacion": round(reparacion, 2), "visita_efectivo": round(visita, 2),
            "total": round(reparacion + visita, 2)}


# ---------------------------------------------------------------------------
# B1 — "Terminé"
# ---------------------------------------------------------------------------
def terminar(db, solicitud) -> dict:
    if solicitud.estado not in ("REPARACION_ACEPTADA", "SOLO_DIAGNOSTICO"):
        return {"ok": False, "mensaje": "Aún no puedes terminar este servicio."}
    solicitud.terminado_en = datetime.utcnow()
    des = _desglose(db, solicitud)
    if des["total"] > 0:
        solicitud.estado = "POR_COBRAR"
        solicitud.monto_por_cobrar = des["total"]
        db.commit()
        _publicar_cobro(db, solicitud, des)
        return {"ok": True, "estado": "POR_COBRAR", "desglose": des}
    # Nada por cobrar (solo diagnóstico con visita ya pagada): a conformidad.
    _emitir(db, solicitud)          # comprobante de la visita si no se emitió en etapa 3
    solicitud.estado = "POR_CONFORMAR"
    db.commit()
    return {"ok": True, "estado": "POR_CONFORMAR", "desglose": des}


def _publicar_cobro(db, solicitud, des):
    from app.services import servicio
    try:
        servicio.mensaje_tarjeta(db, solicitud.id, {
            "tipo": "cobro", "total": des["total"], "reparacion": des["reparacion"],
            "visita_efectivo": des["visita_efectivo"], "estado": "por_cobrar"})
    except Exception:
        logger.exception("[cierre] publicar cobro")


# ---------------------------------------------------------------------------
# B2 — Cobro digital (QR/pasarela)
# ---------------------------------------------------------------------------
def referencia_reparacion(solicitud) -> str:
    """Referencia del cobro de la reparación, distinta de la visita (MITA-SOL-{id})."""
    return f"MITA-SOL-{solicitud.id}-R"


def confirmar_pago_digital(db, solicitud) -> dict:
    """Llamado cuando PagoOK/pasarela confirma el cobro de la reparación."""
    if solicitud.estado not in ("POR_COBRAR",):
        return {"ok": False, "mensaje": "No hay un cobro pendiente."}
    return _pagado(db, solicitud, metodo="digital")


# ---------------------------------------------------------------------------
# B3 — Cobro en efectivo (doble confirmación)
# ---------------------------------------------------------------------------
def declarar_efectivo_tecnico(db, solicitud, monto: float) -> dict:
    from app.models.cierre import CobroEfectivo
    if solicitud.estado != "POR_COBRAR":
        return {"ok": False, "mensaje": "No hay un cobro pendiente."}
    total = float(solicitud.monto_por_cobrar or 0)
    ce = (db.query(CobroEfectivo).filter(CobroEfectivo.solicitud_id == solicitud.id)
          .order_by(CobroEfectivo.id.desc()).first())
    if not ce or ce.estado in ("validado_torre", "confirmado"):
        ce = CobroEfectivo(solicitud_id=solicitud.id, monto_total=total)
        db.add(ce)
    ce.monto_tecnico = float(monto)
    ce.estado = "declarado"
    ce.declarado_en = datetime.utcnow()
    db.commit()
    # Tarjeta de confirmación para el cliente
    from app.services import servicio
    try:
        servicio.mensaje_tarjeta(db, solicitud.id, {
            "tipo": "confirmar_efectivo", "monto": round(float(monto), 2),
            "cobro_id": ce.id, "estado": "por_confirmar"})
    except Exception:
        logger.exception("[cierre] tarjeta efectivo")
    return {"ok": True, "cobro_id": ce.id, "monto": float(monto)}


def confirmar_efectivo_cliente(db, solicitud, monto_cliente: float) -> dict:
    """El cliente confirma el monto pagado en efectivo."""
    from app.models.cierre import CobroEfectivo
    ce = (db.query(CobroEfectivo).filter(CobroEfectivo.solicitud_id == solicitud.id)
          .order_by(CobroEfectivo.id.desc()).first())
    if not ce or ce.estado not in ("declarado",):
        return {"ok": False, "mensaje": "No hay un cobro en efectivo por confirmar."}
    ce.monto_cliente = float(monto_cliente)
    coincide = _eps(ce.monto_cliente, ce.monto_total) and _eps(ce.monto_tecnico, ce.monto_total)
    if coincide:
        ce.estado = "confirmado"
        ce.en_poder_tecnico = True
        db.commit()
        _pagado(db, solicitud, metodo="efectivo")
        return {"ok": True, "estado": "PAGADO"}
    ce.estado = "discrepancia"
    db.commit()
    _alerta_torre(f"Validar efectivo solicitud #{solicitud.id}: técnico S/{ce.monto_tecnico} "
                  f"vs cliente S/{ce.monto_cliente} (total S/{ce.monto_total}).")
    return {"ok": True, "estado": "discrepancia", "mensaje": "Enviamos el caso a la central para validarlo."}


def revisar_efectivo_vencido(db) -> int:
    """Cobros en efectivo 'declarado' sin respuesta del cliente > N min -> torre. Devuelve cuántos."""
    from app.models.cierre import CobroEfectivo
    from app.services.config_service import ConfigService
    try:
        minutos = int(ConfigService.get(db, "efectivo_minutos_torre", 30) or 30)
    except Exception:
        minutos = 30
    limite = datetime.utcnow() - timedelta(minutes=minutos)
    pend = (db.query(CobroEfectivo)
            .filter(CobroEfectivo.estado == "declarado", CobroEfectivo.declarado_en < limite).all())
    for ce in pend:
        ce.estado = "discrepancia"
        _alerta_torre(f"Validar efectivo solicitud #{ce.solicitud_id}: el cliente no confirmó en {minutos} min.")
    if pend:
        db.commit()
    return len(pend)


def validar_efectivo_torre(db, solicitud, monto_final: float, validado_por: str, motivo: str) -> dict:
    """La torre decide el monto final del efectivo y lo registra."""
    from app.models.cierre import CobroEfectivo
    ce = (db.query(CobroEfectivo).filter(CobroEfectivo.solicitud_id == solicitud.id)
          .order_by(CobroEfectivo.id.desc()).first())
    if not ce:
        return {"ok": False, "mensaje": "No hay cobro en efectivo."}
    ce.estado = "validado_torre"
    ce.monto_cliente = float(monto_final)
    ce.validado_por = (validado_por or "torre")[:60]
    ce.motivo = motivo
    ce.en_poder_tecnico = True
    db.commit()
    _pagado(db, solicitud, metodo="efectivo")
    return {"ok": True, "estado": "PAGADO"}


# ---------------------------------------------------------------------------
# B4 — Comprobante y conformidad
# ---------------------------------------------------------------------------
def _pagado(db, solicitud, metodo: str):
    solicitud.estado = "PAGADO"
    solicitud.cobro_metodo = metodo
    solicitud.cobrado_en = datetime.utcnow()
    db.commit()
    # Emitir ANTES de marcar `pagado=1`: así la visita en efectivo aún cuenta como línea.
    _emitir(db, solicitud)
    solicitud.pagado = 1
    solicitud.estado = "POR_CONFORMAR"
    db.commit()
    return {"ok": True, "estado": "PAGADO", "metodo": metodo}


def _visita_ya_facturada(db, solicitud) -> bool:
    from app.models.cierre import ComprobanteEmitido
    if db.query(ComprobanteEmitido).filter(
            ComprobanteEmitido.solicitud_id == solicitud.id,
            ComprobanteEmitido.concepto == "visita",
            ComprobanteEmitido.estado.in_(("enviando", "aceptado", "simulado"))).first():
        return True
    try:
        from app.models.pago_solicitud import PagoSolicitud
        if db.query(PagoSolicitud).filter(
                PagoSolicitud.solicitud_id == solicitud.id,
                PagoSolicitud.comprobante_estado == "emitido").first():
            return True
    except Exception:
        pass
    return False


def _especialidad(db, solicitud) -> str:
    try:
        from app.models.models import CategoriaServicio
        c = db.query(CategoriaServicio).get(solicitud.categoria_id) if solicitud.categoria_id else None
        return c.nombre if c else "servicio"
    except Exception:
        return "servicio"


def _codigo_sunat(db, solicitud):
    """Código de producto SUNAT por especialidad (configurable; obligatorio desde 2027)."""
    try:
        from app.services.config_service import ConfigService
        cat = solicitud.categoria_id
        if cat:
            v = ConfigService.get(db, f"sunat_codigo_cat_{cat}", None)
            if v:
                return v
        return ConfigService.get(db, "sunat_codigo_default", None)
    except Exception:
        return None


def _emitir(db, solicitud, reintento=False) -> dict:
    """Emite el comprobante al comprador (idempotente por solicitud+concepto) vía Facturalo real."""
    from app.services import comprobante
    des = _desglose(db, solicitud)
    reparacion, visita = des["reparacion"], des["visita_efectivo"]
    esp = _especialidad(db, solicitud)
    cod = _codigo_sunat(db, solicitud)

    if reparacion > 0:
        concepto = "reparacion"
        trabajo = ""
        pr = _presupuesto_aceptado(db, solicitud)
        if pr and pr.descripcion_trabajo:
            trabajo = f": {pr.descripcion_trabajo}"
        items = [{"descripcion": f"Reparación{trabajo}", "monto": reparacion, "codigo_sunat": cod}]
        if visita > 0:
            items.append({"descripcion": f"Visita técnica de {esp}", "monto": visita, "codigo_sunat": cod})
        monto = reparacion + visita
    else:
        concepto = "visita"
        if _visita_ya_facturada(db, solicitud) and not reintento:
            return {"ok": True, "ya_emitido": True, "concepto": concepto}
        monto = visita if visita > 0 else float(solicitud.costo_visita or 0)
        items = [{"descripcion": f"Visita técnica de {esp}", "monto": monto, "codigo_sunat": cod}]

    doc_tipo = solicitud.comprador_doc_tipo
    doc_num = solicitud.comprador_doc_numero
    tipo_comp = (solicitud.comprador_tipo_comprobante or "boleta")
    nombre = solicitud.comprador_nombre or (solicitud.cliente_nombre or "Cliente")

    def _pendiente(mensaje):
        from app.models.cierre import ComprobanteEmitido
        ce = (db.query(ComprobanteEmitido).filter(ComprobanteEmitido.solicitud_id == solicitud.id,
                                                  ComprobanteEmitido.concepto == concepto).first())
        if not ce:
            ce = ComprobanteEmitido(solicitud_id=solicitud.id, concepto=concepto, monto=monto)
            db.add(ce)
        ce.estado = "pendiente"; db.commit()
        _alerta_torre(f"Comprobante pendiente solicitud #{solicitud.id}: {mensaje}")
        return {"ok": False, "pendiente": True, "mensaje": mensaje}

    if doc_tipo and doc_num:
        cliente = {"doc_tipo": doc_tipo, "doc_numero": doc_num, "razon_social": nombre,
                   "direccion": solicitud.comprador_direccion_fiscal}
    elif tipo_comp == "factura":
        return _pendiente("Falta el RUC para la factura.")
    else:
        # Boleta sin documento: solo válida bajo el umbral. Si el total lo supera, pedir DNI.
        from app.services.identificacion import umbral_boleta
        if monto >= umbral_boleta(db):
            try:
                from app.services import servicio
                servicio.mensaje_sistema(db, solicitud.id,
                    f"Por el monto (S/ {monto:.2f}) necesitamos tu DNI para la boleta. "
                    f"Complétalo para enviarte el comprobante.")
            except Exception:
                pass
            return _pendiente(f"Boleta de S/ {monto:.2f} requiere DNI (supera el umbral).")
        cliente = {"doc_tipo": None, "doc_numero": "", "razon_social": nombre, "direccion": None}
    return comprobante.emitir(db, solicitud.id, concepto, tipo_comp, cliente, items, monto)


def reintentar_comprobante(db, solicitud, concepto: str) -> dict:
    return _emitir(db, solicitud, reintento=True)


def registrar_conformidad(db, solicitud, resuelto: bool, estrellas=None, comentario=None) -> dict:
    solicitud.conformidad_ok = bool(resuelto)
    solicitud.conformidad_estrellas = int(estrellas) if estrellas else None
    solicitud.conformidad_comentario = (comentario or None)
    solicitud.estado = "CERRADO"
    solicitud.cerrado_en = datetime.utcnow()
    db.commit()
    from app.services import servicio
    try:
        servicio.mensaje_sistema(db, solicitud.id, "Servicio cerrado. ¡Gracias!")
    except Exception:
        pass
    if (not resuelto) or (estrellas and int(estrellas) <= 2):
        _alerta_torre(f"Conformidad negativa solicitud #{solicitud.id}: "
                      f"resuelto={resuelto} estrellas={estrellas}.")
    return {"ok": True, "estado": "CERRADO"}


# ---------------------------------------------------------------------------
# B5 — Torre de control ("Cierres")
# ---------------------------------------------------------------------------
def torre_cierres(db) -> dict:
    from app.models.solicitud_mita import Solicitud
    from app.models.cierre import CobroEfectivo, ComprobanteEmitido
    ahora = datetime.utcnow()

    por_cobrar = []
    for s in db.query(Solicitud).filter(Solicitud.estado == "POR_COBRAR").all():
        edad = int((ahora - s.terminado_en).total_seconds() // 60) if s.terminado_en else None
        por_cobrar.append({"solicitud_id": s.id, "total": s.monto_por_cobrar, "antiguedad_min": edad})

    efectivo = [{"solicitud_id": c.solicitud_id, "monto_tecnico": c.monto_tecnico,
                 "monto_cliente": c.monto_cliente, "monto_total": c.monto_total, "estado": c.estado}
                for c in db.query(CobroEfectivo).filter(CobroEfectivo.estado == "discrepancia").all()]

    comp_pend = [{"id": c.id, "solicitud_id": c.solicitud_id, "concepto": c.concepto, "monto": c.monto,
                  "estado": c.estado, "numero_formato": c.numero_formato,
                  "mensaje_sunat": c.mensaje_sunat}
                 for c in db.query(ComprobanteEmitido)
                 .filter(ComprobanteEmitido.estado.in_(("pendiente", "rechazado", "enviando"))).all()]
    from app.services import facturalo_service as _fact

    conf_neg = []
    for s in (db.query(Solicitud)
              .filter(Solicitud.conformidad_ok.is_(False)).all()):
        conf_neg.append({"solicitud_id": s.id, "estrellas": s.conformidad_estrellas,
                         "comentario": s.conformidad_comentario})
    for s in (db.query(Solicitud)
              .filter(Solicitud.conformidad_estrellas.isnot(None),
                      Solicitud.conformidad_estrellas <= 2).all()):
        if not any(x["solicitud_id"] == s.id for x in conf_neg):
            conf_neg.append({"solicitud_id": s.id, "estrellas": s.conformidad_estrellas,
                             "comentario": s.conformidad_comentario})

    # Totales del día
    inicio_dia = datetime(ahora.year, ahora.month, ahora.day)
    digital = efectivo_total = 0.0
    for s in db.query(Solicitud).filter(Solicitud.cobrado_en >= inicio_dia).all():
        monto = float(s.monto_por_cobrar or 0)
        if s.cobro_metodo == "digital":
            digital += monto
        elif s.cobro_metodo == "efectivo":
            efectivo_total += monto
    return {"por_cobrar": por_cobrar, "efectivo_por_validar": efectivo,
            "comprobantes_pendientes": comp_pend, "conformidad_negativa": conf_neg,
            "facturacion_configurada": _fact.configurado(),
            "totales_dia": {"digital": round(digital, 2), "efectivo_en_poder_tecnicos": round(efectivo_total, 2)}}


def _alerta_torre(texto):
    logger.warning("[torre] %s", texto)
