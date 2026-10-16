"""
Cálculo de la liquidación del técnico (zMita-41, Parte B). Funciones PURAS (sin BD),
para poder probar las reglas con los casos del dueño.

Reparto por servicio:
  - Visita: MITA se queda `visita_parte_mita` (def 15); el técnico, el resto (def 35).
  - Reparación (monto sobre la visita): comisión de MITA por porcentaje o monto fijo;
    el técnico, el resto.

Efectivo: lo que el técnico cobró en efectivo ya está en su poder y se descuenta de su parte.
Si el efectivo supera su parte, el excedente es saldo a favor de MITA (se arrastra).
"""
from decimal import Decimal, ROUND_HALF_UP


def _money(x) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parte_servicio(visita, reparacion_monto, comision_tipo="porcentaje", comision_valor=20,
                   visita_parte_mita=15):
    """Devuelve el reparto de UN servicio.

    visita: monto de la visita (p. ej. 50). reparacion_monto: monto de la reparación
    SOBRE la visita (el monto del presupuesto aceptado; 0 si solo diagnóstico).
    comision_tipo: 'porcentaje' | 'fijo'. comision_valor: % (0-100) o S/ fijo."""
    visita = float(visita or 0)
    reparacion_monto = float(reparacion_monto or 0)
    mita_visita = min(float(visita_parte_mita or 0), visita)
    tecnico_visita = visita - mita_visita

    if reparacion_monto > 0:
        if (comision_tipo or "porcentaje") == "fijo":
            mita_rep = min(float(comision_valor or 0), reparacion_monto)
        else:
            mita_rep = reparacion_monto * float(comision_valor or 0) / 100.0
    else:
        mita_rep = 0.0
    tecnico_rep = reparacion_monto - mita_rep

    return {
        "visita": _money(visita),
        "reparacion": _money(reparacion_monto),
        "total": _money(visita + reparacion_monto),
        "mita_visita": _money(mita_visita),
        "mita_reparacion": _money(mita_rep),
        "tecnico_visita": _money(tecnico_visita),
        "tecnico_reparacion": _money(tecnico_rep),
        "parte_mita": _money(mita_visita + mita_rep),
        "parte_tecnico": _money(tecnico_visita + tecnico_rep),
    }


def consolidar(servicios, saldo_arrastrado=0.0):
    """Suma las partes de varios servicios y aplica el efectivo ya cobrado por el técnico.

    servicios: lista de dicts con al menos `parte_tecnico`, `parte_mita` y `efectivo_tecnico`
    (lo que ese servicio se cobró en efectivo, 0 si fue digital).
    saldo_arrastrado: saldo a favor de MITA de periodos anteriores (positivo = el técnico debe).

    Devuelve el neto a transferir al técnico y el saldo que se arrastra."""
    parte_tecnico = sum(float(s.get("parte_tecnico", 0)) for s in servicios)
    parte_mita = sum(float(s.get("parte_mita", 0)) for s in servicios)
    efectivo_tecnico = sum(float(s.get("efectivo_tecnico", 0)) for s in servicios)

    # Lo que el técnico ya tiene en efectivo se descuenta de su parte; también se descuenta
    # el saldo que arrastraba a favor de MITA.
    neto = parte_tecnico - efectivo_tecnico - float(saldo_arrastrado or 0)
    if neto >= 0:
        a_transferir = neto
        nuevo_saldo = 0.0
    else:
        a_transferir = 0.0
        nuevo_saldo = -neto   # queda a favor de MITA, se arrastra

    return {
        "cantidad": len(servicios),
        "parte_tecnico": _money(parte_tecnico),
        "parte_mita": _money(parte_mita),
        "efectivo_en_poder_tecnico": _money(efectivo_tecnico),
        "saldo_arrastrado": _money(saldo_arrastrado or 0),
        "a_transferir": _money(a_transferir),
        "saldo_a_favor_mita": _money(nuevo_saldo),
    }


def retencion_4ta(monto_bruto, activa=False, tasa=8.0, umbral=1500.0, suspendido=False):
    """Retención de 4ta categoría sobre el RxH. El sistema CALCULA, no asesora:
    siempre acompañar con 'confirmar con el contador de MITA'."""
    monto_bruto = float(monto_bruto or 0)
    if not activa or suspendido or monto_bruto <= float(umbral or 0):
        return {"retiene": False, "monto": 0.0, "neto": _money(monto_bruto),
                "nota": "Confirmar con el contador de MITA."}
    ret = monto_bruto * float(tasa or 0) / 100.0
    return {"retiene": True, "monto": _money(ret), "neto": _money(monto_bruto - ret),
            "tasa": float(tasa or 0), "nota": "Confirmar con el contador de MITA."}
