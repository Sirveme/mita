"""
Integración con el facturador electrónico (Facturalo.pro / Nubefact / ...).

Lee el proveedor ACTIVO de la tabla `integraciones` (tipo='facturador'),
descifra su api_key y emite/consulta/anula comprobantes.

ESTADO: STUB. La llamada real al proveedor está marcada con TODO; por ahora
devuelve una serie/número/PDF simulados para poder construir el flujo visual.
Cuando se implemente, solo hay que completar `_llamar_api`.

--- API de Facturalo.pro (referencia) ---
  POST {base}/api/v1/comprobantes/emitir
  Headers: Authorization: Bearer {api_key}
  Body: { tipo, serie, cliente: {ruc|dni, razon_social}, items: [...], total }
  Resp: { serie, numero, pdf_url, hash, estado_sunat }
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.integracion import Integracion
from app.services.crypto_service import decrypt

logger = logging.getLogger("mita.facturalo")

# Series por defecto por tipo de comprobante (fallback si la integración no las trae)
_SERIES = {"boleta": "B001", "factura": "F001"}


def _integracion_activa(db: Session) -> Optional[Integracion]:
    return (db.query(Integracion)
              .filter(Integracion.tipo == "facturador", Integracion.activo.is_(True))
              .first())


def _base_y_key(db: Session):
    integ = _integracion_activa(db)
    if not integ:
        return None, None, None
    base = integ.url_sandbox if integ.modo_sandbox else integ.url_produccion
    api_key = decrypt(integ.api_key_encrypted)
    return integ, base, api_key


def emitir_comprobante(db: Session, tipo: str, cliente: dict, items: list, monto: float) -> dict:
    """Emite un comprobante. Devuelve {ok, serie, numero, pdf_url, mensaje, simulado}.

    tipo: 'boleta' | 'factura'; cliente: {ruc?|dni?, razon_social}; items: [{descripcion, cantidad, precio}]."""
    integ, base, api_key = _base_y_key(db)
    serie = _SERIES.get(tipo, "B001")

    if not integ or not base or not api_key:
        # Sin proveedor configurado -> simulación (permite construir el flujo)
        numero = int(datetime.utcnow().timestamp()) % 100000
        logger.info("Facturador no configurado: comprobante SIMULADO %s-%s", serie, numero)
        return {"ok": True, "simulado": True, "serie": serie, "numero": numero,
                "pdf_url": None, "mensaje": "Comprobante simulado (facturador no configurado)."}

    # TODO: llamada real al proveedor
    #   payload = {"tipo": tipo, "serie": serie, "cliente": cliente, "items": items, "total": monto}
    #   resp = httpx.post(f"{base}/api/v1/comprobantes/emitir",
    #                     headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=20)
    #   data = resp.json(); return {ok, serie, numero, pdf_url ...}
    numero = int(datetime.utcnow().timestamp()) % 100000
    logger.info("STUB emitir_comprobante %s %s-%s via %s", tipo, serie, numero, integ.proveedor)
    return {"ok": True, "simulado": True, "serie": serie, "numero": numero,
            "pdf_url": f"{base}/pdf/{serie}-{numero}",
            "mensaje": f"Emisión pendiente de implementar en {integ.proveedor} (estructura lista)."}


def consultar_comprobante(db: Session, serie: str, numero: int) -> dict:
    """Consulta el estado de un comprobante (STUB)."""
    integ, base, api_key = _base_y_key(db)
    if not integ:
        return {"ok": False, "mensaje": "Facturador no configurado."}
    # TODO: GET {base}/api/v1/comprobantes/{serie}-{numero}
    return {"ok": True, "simulado": True, "serie": serie, "numero": numero,
            "estado": "ACEPTADO (simulado)", "proveedor": integ.proveedor}


def anular_comprobante(db: Session, serie: str, numero: int, motivo: str) -> dict:
    """Anula un comprobante (STUB)."""
    integ, base, api_key = _base_y_key(db)
    if not integ:
        return {"ok": False, "mensaje": "Facturador no configurado."}
    # TODO: POST {base}/api/v1/comprobantes/anular {serie, numero, motivo}
    logger.info("STUB anular %s-%s motivo=%s", serie, numero, motivo)
    return {"ok": True, "simulado": True, "mensaje": f"Anulación registrada (simulada) — {motivo}"}
