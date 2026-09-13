"""
Integración con la pasarela de pagos (IziPay / Culqi / Mercado Pago).

Lee el proveedor ACTIVO de `integraciones` (tipo='pasarela'), descifra sus
credenciales y crea/consulta pagos + procesa webhooks.

ESTADO: STUB. Las llamadas reales están marcadas con TODO; por ahora se simula
un pago para poder construir y probar el flujo completo (pago → webhook →
comprobante). Al integrar IziPay, solo hay que completar los TODO.

--- Referencia IziPay (a confirmar con su documentación) ---
  POST {base}/payments  (Authorization: Bearer {api_key}, merchant_id)
  Body: { amount, currency, order_id, customer, return_url, notify_url }
  Resp: { payment_url, token, transaction_id }
  Webhook: firma HMAC en header; body con { event, transaction_id, status, amount }
"""

import logging
import secrets
from typing import Optional

from sqlalchemy.orm import Session

from app.models.integracion import Integracion
from app.services.crypto_service import decrypt

logger = logging.getLogger("mita.pasarela")


def _activa(db: Session) -> Optional[Integracion]:
    return (db.query(Integracion)
              .filter(Integracion.tipo == "pasarela", Integracion.activo.is_(True))
              .first())


def _cfg(db: Session):
    integ = _activa(db)
    if not integ:
        return None, None, None, None
    base = integ.url_sandbox if integ.modo_sandbox else integ.url_produccion
    return integ, base, decrypt(integ.api_key_encrypted), decrypt(integ.api_secret_encrypted)


def crear_pago(db: Session, monto: float, descripcion: str, cliente: dict,
               url_retorno: str, url_webhook: str) -> dict:
    """Crea una orden de pago. Devuelve {ok, url_pago, token_pago, referencia, pasarela, simulado}."""
    integ, base, api_key, api_secret = _cfg(db)
    referencia = f"MITA-{secrets.token_hex(6)}"
    proveedor = integ.proveedor if integ else "simulado"

    if not integ or not base or not api_key:
        # Sin pasarela configurada -> simulación (la url apunta al retorno propio)
        url = f"{url_retorno}?ref={referencia}&sim=1"
        logger.info("Pasarela no configurada: pago SIMULADO %s", referencia)
        return {"ok": True, "simulado": True, "referencia": referencia, "pasarela": proveedor,
                "url_pago": url, "token_pago": referencia,
                "mensaje": "Pago simulado (pasarela no configurada)."}

    # TODO: llamada real a la pasarela
    #   payload = {"amount": monto, "currency": "PEN", "order_id": referencia,
    #              "customer": cliente, "return_url": url_retorno, "notify_url": url_webhook}
    #   resp = httpx.post(f"{base}/payments", headers={"Authorization": f"Bearer {api_key}"},
    #                     json=payload, timeout=20)  -> data.payment_url / token / transaction_id
    url = f"{url_retorno}?ref={referencia}&sim=1"
    logger.info("STUB crear_pago %s via %s monto=%s", referencia, proveedor, monto)
    return {"ok": True, "simulado": True, "referencia": referencia, "pasarela": proveedor,
            "url_pago": url, "token_pago": referencia,
            "mensaje": f"Emisión de pago pendiente de implementar en {proveedor} (estructura lista)."}


def consultar_pago(db: Session, referencia: str) -> dict:
    """Consulta el estado de un pago en la pasarela (STUB)."""
    integ, base, api_key, _ = _cfg(db)
    if not integ:
        return {"ok": False, "mensaje": "Pasarela no configurada."}
    # TODO: GET {base}/payments/{referencia}
    return {"ok": True, "simulado": True, "referencia": referencia,
            "estado": "APROBADO (simulado)", "pasarela": integ.proveedor}


def procesar_webhook(db: Session, payload: dict, headers: Optional[dict] = None) -> dict:
    """Interpreta el webhook de la pasarela. Devuelve {evento, referencia, estado, monto}.

    TODO: validar la firma/autenticidad con api_secret antes de confiar en el payload."""
    referencia = payload.get("order_id") or payload.get("referencia") or payload.get("transaction_id")
    status = (payload.get("status") or payload.get("estado") or "").upper()
    mapa = {"PAID": "APROBADO", "APPROVED": "APROBADO", "AUTHORIZED": "APROBADO",
            "REJECTED": "RECHAZADO", "DECLINED": "RECHAZADO", "FAILED": "ERROR",
            "REFUNDED": "REEMBOLSADO"}
    estado = mapa.get(status, status or "EN_PROCESO")
    return {"evento": payload.get("event") or payload.get("evento"),
            "referencia": referencia, "estado": estado, "monto": payload.get("amount") or payload.get("monto")}
