"""
Liquidación a técnicos (etapa 8, zMita-41). Genera por corte (lunes 00:00 Lima), solo con
servicios CERRADO cuyo comprobante está aceptado. Cada servicio usa el valor de comisión
VIGENTE a su fecha de cierre (historial en configuracion_historial). Las liquidaciones ya
generadas NO se recalculan.
"""
import json
import logging
from datetime import datetime, date, timedelta

from app.services import liquidacion_calc as calc

logger = logging.getLogger("mita.liquidacion")
LIMA_OFFSET = timedelta(hours=5)   # Lima = UTC-5
LISTO = ("aceptado", "simulado")   # 'simulado' solo ocurre fuera de producción


def _lima(dt: datetime) -> datetime:
    return dt - LIMA_OFFSET


def lunes_de(d: date) -> date:
    return d - timedelta(days=d.weekday())


def periodo_de(db, lunes: date):
    """Devuelve (inicio, fin) según el periodo configurado. Corte en lunes."""
    from app.services.config_service import ConfigService
    periodo = (ConfigService.get(db, "periodo_liquidacion", "semanal") or "semanal")
    dias = 13 if periodo == "quincenal" else 6
    return lunes, lunes + timedelta(days=dias)


def periodo_actual(db, ahora=None):
    ahora = ahora or datetime.utcnow()
    hoy_lima = _lima(ahora).date()
    return periodo_de(db, lunes_de(hoy_lima))


# --------------------------------------------------------------------------
# Historial de parámetros
# --------------------------------------------------------------------------
def _cast(valor, tipo):
    try:
        if tipo == "float":
            return float(valor)
        if tipo == "int":
            return int(valor)
        if tipo == "bool":
            return str(valor).lower() in ("true", "1", "si", "sí")
    except Exception:
        return valor
    return valor


def set_param(db, clave, valor, tipo="string", creado_por="admin", vigente_desde=None):
    """Guarda el parámetro actual y agrega una fila al historial (quién y desde cuándo rige)."""
    from app.models.liquidacion_mita import ConfiguracionHistorial
    from app.services.config_service import ConfigService
    ConfigService.set(db, clave, valor)
    db.add(ConfiguracionHistorial(clave=clave, valor=str(valor), tipo=tipo,
                                  vigente_desde=vigente_desde or datetime.utcnow(),
                                  creado_por=str(creado_por)[:60]))
    db.commit()


def valor_vigente(db, clave, fecha, default=None, tipo="float"):
    """Valor que regía en `fecha` según el historial; si no hay, el valor actual del panel."""
    from app.models.liquidacion_mita import ConfiguracionHistorial
    from app.services.config_service import ConfigService
    fila = (db.query(ConfiguracionHistorial)
            .filter(ConfiguracionHistorial.clave == clave,
                    ConfiguracionHistorial.vigente_desde <= fecha)
            .order_by(ConfiguracionHistorial.vigente_desde.desc()).first())
    if fila:
        return _cast(fila.valor, fila.tipo or tipo)
    return ConfigService.get(db, clave, default)


# --------------------------------------------------------------------------
# Generación
# --------------------------------------------------------------------------
def _reparacion_monto(db, solicitud_id):
    from app.models.servicio_vivo import Presupuesto
    pr = (db.query(Presupuesto).filter(Presupuesto.solicitud_id == solicitud_id,
                                       Presupuesto.estado == "aceptado")
          .order_by(Presupuesto.version.desc()).first())
    return float(pr.monto) if (pr and pr.monto) else 0.0


def _efectivo_tecnico(db, solicitud):
    from app.models.cierre import CobroEfectivo
    if (solicitud.cobro_metodo or "") != "efectivo":
        return 0.0
    ce = (db.query(CobroEfectivo).filter(CobroEfectivo.solicitud_id == solicitud.id,
                                         CobroEfectivo.estado.in_(("confirmado", "validado_torre")))
          .order_by(CobroEfectivo.id.desc()).first())
    return float(ce.monto_cliente or ce.monto_total or 0) if ce else 0.0


def _tiene_comprobante_aceptado(db, solicitud_id):
    from app.models.cierre import ComprobanteEmitido
    return db.query(ComprobanteEmitido).filter(
        ComprobanteEmitido.solicitud_id == solicitud_id,
        ComprobanteEmitido.estado.in_(LISTO)).first() is not None


def _ya_liquidado(db, solicitud_id):
    from app.models.liquidacion_mita import LiquidacionItem
    return db.query(LiquidacionItem).filter(LiquidacionItem.solicitud_id == solicitud_id).first() is not None


def _retencion_suspendida(db, tecnico_id) -> bool:
    from app.services.config_service import ConfigService
    return str(ConfigService.get(db, f"retencion_suspendida_{tecnico_id}", "false")).lower() in ("true", "1")


def generar(db, lunes: date = None, creado_por="sistema") -> dict:
    """Genera las liquidaciones (borrador) del periodo. Idempotente por servicio (no duplica)."""
    from app.models.solicitud_mita import Solicitud
    from app.models.liquidacion_mita import LiquidacionMita, LiquidacionItem

    if lunes is None:
        ini, fin = periodo_actual(db)
    else:
        ini, fin = periodo_de(db, lunes_de(lunes))
    # límites en UTC: lunes 00:00 Lima = +5 h
    ini_utc = datetime(ini.year, ini.month, ini.day) + LIMA_OFFSET
    fin_utc = datetime(fin.year, fin.month, fin.day) + timedelta(days=1) + LIMA_OFFSET

    sols = (db.query(Solicitud)
            .filter(Solicitud.estado == "CERRADO", Solicitud.tecnico_id.isnot(None),
                    Solicitud.cerrado_en >= ini_utc, Solicitud.cerrado_en < fin_utc)
            .all())
    por_tecnico = {}
    for s in sols:
        if _ya_liquidado(db, s.id) or not _tiene_comprobante_aceptado(db, s.id):
            continue
        por_tecnico.setdefault(s.tecnico_id, []).append(s)

    creadas = 0
    for tecnico_id, servicios in por_tecnico.items():
        items = []
        for s in servicios:
            f = s.cerrado_en or datetime.utcnow()
            tipo = valor_vigente(db, "comision_reparacion_tipo", f, "porcentaje", tipo="string")
            valor = valor_vigente(db, "comision_reparacion_valor", f, 5, tipo="float")
            vpm = valor_vigente(db, "visita_parte_mita", f, 15, tipo="float")
            visita = float(s.costo_visita or 50)
            reparacion = _reparacion_monto(db, s.id)
            parte = calc.parte_servicio(visita, reparacion, tipo, valor, vpm)
            parte["efectivo_tecnico"] = _efectivo_tecnico(db, s)
            items.append((s, f, visita, reparacion, parte, tipo, valor, vpm))

        # saldo que arrastra el técnico (última liquidación)
        prev = (db.query(LiquidacionMita).filter(LiquidacionMita.tecnico_id == tecnico_id)
                .order_by(LiquidacionMita.periodo_inicio.desc(), LiquidacionMita.id.desc()).first())
        saldo_prev = float(prev.saldo_a_favor_mita or 0) if prev else 0.0

        cons = calc.consolidar([p for (_s, _f, _v, _r, p, _t, _val, _vpm) in items], saldo_prev)
        liq = LiquidacionMita(tecnico_id=tecnico_id, periodo_inicio=ini, periodo_fin=fin, estado="borrador",
                          cantidad_servicios=cons["cantidad"], parte_tecnico=cons["parte_tecnico"],
                          parte_mita=cons["parte_mita"], efectivo_en_poder_tecnico=cons["efectivo_en_poder_tecnico"],
                          saldo_arrastrado=cons["saldo_arrastrado"], a_transferir=cons["a_transferir"],
                          saldo_a_favor_mita=cons["saldo_a_favor_mita"])
        db.add(liq); db.commit(); db.refresh(liq)
        for (s, f, visita, reparacion, parte, tipo, valor, vpm) in items:
            db.add(LiquidacionItem(liquidacion_id=liq.id, solicitud_id=s.id, fecha_cierre=f,
                                   codigo=f"#{s.id:05d}", total=parte["total"], visita=visita,
                                   reparacion=reparacion, efectivo_tecnico=parte["efectivo_tecnico"],
                                   parte_mita=parte["parte_mita"], parte_tecnico=parte["parte_tecnico"],
                                   comision_tipo=tipo, comision_valor=valor, visita_parte_mita=vpm))
        db.commit()
        creadas += 1
    return {"ok": True, "periodo_inicio": ini.isoformat(), "periodo_fin": fin.isoformat(),
            "liquidaciones": creadas, "tecnicos": len(por_tecnico)}


# --------------------------------------------------------------------------
# Ciclo
# --------------------------------------------------------------------------
def enviar(db, liq) -> dict:
    if liq.estado != "borrador":
        return {"ok": False, "mensaje": "Solo se envía una liquidación en borrador."}
    liq.estado = "enviada"; liq.enviada_en = datetime.utcnow(); db.commit()
    try:
        from app.services import push as _push
        _push.avisar_liquidacion(db, liq)
    except Exception:
        logger.exception("[liquidacion] push enviada")
    return {"ok": True, "estado": "enviada"}


def subir_rxh(db, liq, numero, pdf_url, monto=None) -> dict:
    """El técnico sube el PDF del RxH. Valida monto (avisa, no bloquea) y calcula la retención."""
    if liq.estado not in ("enviada", "rxh_recibido"):
        return {"ok": False, "mensaje": "La liquidación no está lista para el RxH."}
    liq.rxh_numero = str(numero)[:50]
    liq.rxh_pdf_url = pdf_url
    liq.rxh_fecha = datetime.utcnow().date()
    liq.rxh_monto = float(monto) if monto not in (None, "") else None
    liq.estado = "rxh_recibido"
    aviso = None
    if liq.rxh_monto is not None and abs(liq.rxh_monto - float(liq.parte_tecnico or 0)) > 0.5:
        aviso = (f"El RxH dice S/ {liq.rxh_monto:.2f} pero tu parte bruta es "
                 f"S/ {float(liq.parte_tecnico or 0):.2f}. Lo revisaremos; no bloquea.")
    # Retención de 4ta sobre el bruto del RxH (el sistema calcula, no asesora)
    activa = str(valor_vigente(db, "retencion_4ta_activa", datetime.utcnow(), "false", "bool"))
    activa = str(activa).lower() in ("true", "1")
    tasa = float(valor_vigente(db, "retencion_4ta_tasa", datetime.utcnow(), 8, "float") or 8)
    umbral = float(valor_vigente(db, "retencion_4ta_umbral", datetime.utcnow(), 1500, "float") or 1500)
    r = calc.retencion_4ta(liq.parte_tecnico, activa=activa, tasa=tasa, umbral=umbral,
                           suspendido=_retencion_suspendida(db, liq.tecnico_id))
    liq.retencion_activa = r["retiene"]; liq.retencion_monto = r["monto"]; liq.neto_rxh = r["neto"]
    db.commit()
    return {"ok": True, "estado": "rxh_recibido", "aviso": aviso, "retencion": r}


def aprobar(db, liq) -> dict:
    if liq.estado not in ("rxh_recibido", "enviada"):
        return {"ok": False, "mensaje": "Primero debe recibirse el RxH."}
    liq.estado = "aprobada"; liq.aprobada_en = datetime.utcnow(); db.commit()
    return {"ok": True, "estado": "aprobada"}


def pagar(db, liq, medio, operacion) -> dict:
    if liq.estado != "aprobada":
        return {"ok": False, "mensaje": "Solo se paga una liquidación aprobada."}
    liq.estado = "pagada"; liq.pago_fecha = datetime.utcnow()
    liq.pago_medio = (medio or "transferencia")[:30]; liq.pago_operacion = (operacion or "")[:100]
    db.commit()
    try:
        from app.services import push as _push
        _push.avisar_liquidacion_pagada(db, liq)
    except Exception:
        logger.exception("[liquidacion] push pagada")
    return {"ok": True, "estado": "pagada"}
