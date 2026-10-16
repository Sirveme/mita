"""
Capa de estado del comprobante (zMita-41, Parte A). Centraliza la emisión real vía Facturalo
con estados HONESTOS:
  - nace 'enviando' (la API lo encola);
  - pasa a 'aceptado' SOLO con el CDR real de SUNAT (codigo_sunat 0);
  - 'rechazado' con código y mensaje;
  - reconsulta cada 5 s el primer minuto, luego cada 2 min hasta 1 h; si sigue → alerta torre.
Idempotencia por (solicitud, concepto) y por referencia_externa = "MITA-SOL-{id}-{concepto}".
Sin credencial: fuera de producción simula; en producción NUNCA devuelve simulado como real.
"""
import logging
from datetime import datetime, timedelta

from app.services import facturalo_service as fact

logger = logging.getLogger("mita.comprobante")

VIVOS = ("enviando", "aceptado", "anulado", "simulado")   # no re-emitir si está en uno de estos


def referencia(solicitud_id, concepto) -> str:
    return f"MITA-SOL-{solicitud_id}-{concepto}"


def _alerta_torre(texto):
    logger.warning("[torre] %s", texto)


def _ce(db, solicitud_id, concepto):
    from app.models.cierre import ComprobanteEmitido
    return (db.query(ComprobanteEmitido)
            .filter(ComprobanteEmitido.solicitud_id == solicitud_id,
                    ComprobanteEmitido.concepto == concepto).first())


def emitir(db, solicitud_id, concepto, tipo_comp, cliente, items, monto) -> dict:
    """Emite (o reutiliza) el comprobante de (solicitud, concepto). No publica 'listo':
    eso lo hace el polling cuando SUNAT acepta."""
    from app.models.cierre import ComprobanteEmitido
    from app.core.security import es_produccion

    ce = _ce(db, solicitud_id, concepto)
    if ce and ce.estado in VIVOS:
        return {"ok": True, "ya_emitido": True, "estado": ce.estado, "id": ce.id}
    if not ce:
        ce = ComprobanteEmitido(solicitud_id=solicitud_id, concepto=concepto)
        db.add(ce)
    ce.tipo = tipo_comp
    ce.monto = float(monto or 0)
    ce.cliente_doc_tipo = (cliente.get("doc_tipo") or None)
    ce.cliente_doc_numero = (cliente.get("doc_numero") or None)
    ce.cliente_nombre = (cliente.get("razon_social") or None)
    ref = referencia(solicitud_id, concepto)
    ce.referencia_externa = ref
    db.commit(); db.refresh(ce)

    if not fact.configurado():
        if es_produccion():
            ce.estado = "pendiente"; db.commit()
            _alerta_torre(f"Facturación no configurada: comprobante de la solicitud #{solicitud_id} "
                          f"({concepto}) quedó PENDIENTE. Configura FACTURALO_API_KEY/SECRET.")
            return {"ok": False, "pendiente": True, "mensaje": "Facturación no configurada."}
        # Fuera de producción: simulado para poder construir el flujo (nunca en prod).
        ce.estado = "simulado"; ce.simulado = True
        ce.numero_formato = f"SIM-{ce.id:08d}"; ce.emitido_en = datetime.utcnow()
        db.commit()
        _al_aceptar(db, ce)   # en dev tratamos el simulado como listo
        return {"ok": True, "simulado": True, "estado": "simulado", "id": ce.id}

    # Idempotencia contra Facturalo: ¿ya existe por referencia_externa?
    prev = fact.buscar_referencia(ref)
    if prev.get("ok") and prev.get("existe") and prev.get("id"):
        ce.facturalo_id = prev["id"]; ce.numero_formato = prev.get("numero_formato")
        ce.estado = "enviando"; ce.emitido_en = ce.emitido_en or datetime.utcnow()
        ce.pdf_url = fact.pdf_url(prev["id"])
        db.commit()
        return {"ok": True, "id": ce.id, "estado": "enviando", "reutilizado": True}

    r = fact.emitir(cliente, items, tipo_comp, ref)
    if not r.get("ok"):
        ce.estado = "pendiente"; db.commit()
        _alerta_torre(f"Comprobante solicitud #{solicitud_id} ({concepto}) no se pudo emitir: "
                      f"{r.get('codigo')} {r.get('error')}. Reintentar en la torre.")
        return {"ok": False, "pendiente": True, "codigo": r.get("codigo"), "mensaje": r.get("error")}

    ce.facturalo_id = r.get("id"); ce.serie = r.get("serie")
    ce.numero = str(r.get("numero")) if r.get("numero") is not None else None
    ce.numero_formato = r.get("numero_formato"); ce.total = r.get("total")
    ce.pdf_url = fact.pdf_url(r["id"]) if r.get("id") else r.get("pdf_url")
    ce.estado = "enviando"; ce.emitido_en = datetime.utcnow()
    db.commit()
    return {"ok": True, "id": ce.id, "estado": "enviando"}


def _due(ce, ahora) -> bool:
    """Cadencia: 5 s el primer minuto, luego 2 min, hasta 1 h."""
    if not ce.emitido_en:
        return True
    if ce.ultima_consulta_en is None:
        return True
    edad = (ahora - ce.emitido_en).total_seconds()
    desde = (ahora - ce.ultima_consulta_en).total_seconds()
    if edad < 60:
        return desde >= 5
    if edad < 3600:
        return desde >= 120
    return False   # > 1 h: deja de consultar; se marca pendiente (abajo)


def consultar_pendientes(db) -> int:
    """Polling de los comprobantes 'enviando' (y de las NC 'enviando'). Devuelve cuántos cerró."""
    from app.models.cierre import ComprobanteEmitido
    ahora = datetime.utcnow()
    cerrados = 0
    enviando = db.query(ComprobanteEmitido).filter(ComprobanteEmitido.estado == "enviando").all()
    for ce in enviando:
        if (ahora - (ce.emitido_en or ahora)).total_seconds() >= 3600:
            ce.estado = "pendiente"; db.commit()
            _alerta_torre(f"Comprobante solicitud #{ce.solicitud_id} ({ce.concepto}) sigue sin CDR "
                          f"tras 1 h. Revisar en la torre.")
            continue
        if not _due(ce, ahora) or not ce.facturalo_id:
            continue
        ce.ultima_consulta_en = ahora
        r = fact.consultar(ce.facturalo_id)
        if not r.get("ok"):
            db.commit(); continue
        ce.codigo_sunat = r.get("codigo_sunat"); ce.mensaje_sunat = r.get("mensaje_sunat")
        ce.hash_cpe = r.get("hash_cpe")
        if r.get("numero_formato"):
            ce.numero_formato = r["numero_formato"]
        if r.get("aceptado"):
            ce.estado = "aceptado"; db.commit()
            _al_aceptar(db, ce); cerrados += 1
        elif r.get("rechazado"):
            ce.estado = "rechazado"; db.commit()
            _alerta_torre(f"SUNAT rechazó el comprobante de la solicitud #{ce.solicitud_id} "
                          f"({ce.concepto}): {ce.codigo_sunat} {ce.mensaje_sunat}. Corregir y reemitir.")
            cerrados += 1
        else:
            db.commit()

    # NC en vuelo
    ncs = db.query(ComprobanteEmitido).filter(ComprobanteEmitido.nc_estado == "enviando").all()
    for ce in ncs:
        if not ce.nc_facturalo_id:
            continue
        r = fact.consultar(ce.nc_facturalo_id)
        if r.get("ok") and r.get("terminal"):
            ce.nc_estado = "aceptado" if r.get("aceptado") else ("rechazado" if r.get("rechazado") else ce.nc_estado)
            db.commit()
    return cerrados


def _al_aceptar(db, ce):
    """Publica 'Tu comprobante está listo' (chat + push) solo cuando está aceptado/simulado."""
    from app.services import servicio
    try:
        servicio.mensaje_tarjeta(db, ce.solicitud_id, {
            "tipo": "comprobante", "serie": ce.serie, "numero": ce.numero,
            "numero_formato": ce.numero_formato, "pdf_url": ce.pdf_url, "comprobante_tipo": ce.tipo})
    except Exception:
        logger.exception("[comprobante] tarjeta")
    try:
        from app.models.solicitud_mita import Solicitud
        from app.services import push as _push
        s = db.query(Solicitud).get(ce.solicitud_id)
        if s:
            _push.avisar_comprobante(db, s)
    except Exception:
        logger.exception("[comprobante] push")
    # Espejo para la vista de pagos QR de la visita
    if ce.concepto == "visita":
        try:
            from app.models.pago_solicitud import PagoSolicitud
            ps = (db.query(PagoSolicitud).filter(PagoSolicitud.solicitud_id == ce.solicitud_id,
                                                 PagoSolicitud.concepto == "visita")
                  .order_by(PagoSolicitud.id.desc()).first())
            if ps:
                ps.comprobante_estado = "emitido"; ps.comprobante_pdf = ce.pdf_url
                ps.comprobante_serie = ce.serie; ps.comprobante_numero = ce.numero
                db.commit()
        except Exception:
            logger.exception("[comprobante] espejo pago")


def anular(db, ce, motivo: str, por: str = "torre") -> dict:
    """Anula emitiendo una Nota de Crédito motivo 01 (anulación total) referenciando el original."""
    if ce.estado not in ("aceptado", "simulado"):
        return {"ok": False, "mensaje": "Solo se anula un comprobante aceptado."}
    if ce.anulado_en:
        return {"ok": False, "mensaje": "Ya fue anulado."}
    if ce.simulado or not fact.configurado():
        ce.estado = "anulado"; ce.nc_estado = "simulado"
        ce.anulado_en = datetime.utcnow(); ce.anulado_por = (por or "torre")[:60]; ce.anulado_motivo = motivo
        db.commit()
        return {"ok": True, "simulado": True}
    cliente = {"doc_tipo": ce.cliente_doc_tipo, "doc_numero": ce.cliente_doc_numero,
               "razon_social": ce.cliente_nombre}
    items = [{"descripcion": f"Anulación de {ce.numero_formato}", "monto": ce.monto}]
    # serie del original: letra inicial (B/F). documento_ref_numero = correlativo.
    ref_tipo = ce.tipo or "boleta"
    ref_serie = ce.serie or (ce.numero_formato or "").split("-")[0]
    ref_numero = ce.numero or (ce.numero_formato or "").split("-")[-1]
    r = fact.emitir_nota_credito(cliente, items, ref_tipo, ref_serie, ref_numero, motivo,
                                 referencia_externa=f"NC-{referencia(ce.solicitud_id, ce.concepto)}")
    if not r.get("ok"):
        return {"ok": False, "mensaje": r.get("error") or "No se pudo emitir la NC", "codigo": r.get("codigo")}
    ce.nc_facturalo_id = r.get("id"); ce.nc_numero_formato = r.get("numero_formato")
    ce.nc_estado = "enviando"; ce.estado = "anulado"
    ce.anulado_en = datetime.utcnow(); ce.anulado_por = (por or "torre")[:60]; ce.anulado_motivo = motivo
    db.commit()
    return {"ok": True, "nc_numero_formato": ce.nc_numero_formato}
