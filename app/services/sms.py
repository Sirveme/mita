"""
Interfaz de envío de SMS (zMita-39). Proveedor configurable por variables de entorno
(SMS_PROVEEDOR, SMS_API_KEY, ...). Si no hay proveedor configurado, `enviar_sms` devuelve
{"ok": False, "sin_proveedor": True} y el flujo de OTP NO bloquea (celular 'no_verificado').
"""
import logging

from app.core.config import settings

logger = logging.getLogger("mita.sms")


def hay_proveedor() -> bool:
    return bool((settings.SMS_PROVEEDOR or "").strip())


def enviar_sms(numero: str, texto: str) -> dict:
    """Envía un SMS. Devuelve {ok, sin_proveedor?, proveedor?, mensaje?}.

    Mientras no haya integración real, con proveedor configurado se simula el envío
    (para poder construir el flujo). Sin proveedor, se avisa `sin_proveedor`."""
    prov = (settings.SMS_PROVEEDOR or "").strip()
    if not prov:
        logger.info("[sms] sin proveedor configurado; no se envía a %s", numero)
        return {"ok": False, "sin_proveedor": True, "mensaje": "SMS no configurado"}

    # TODO: integración real por proveedor (twilio/nexmo/labsmobile...). Estructura lista:
    #   if prov == "twilio": client.messages.create(to=numero, from_=settings.SMS_REMITENTE, body=texto)
    logger.info("[sms] (%s) -> %s: %s", prov, numero, texto)
    return {"ok": True, "proveedor": prov, "simulado": True}
