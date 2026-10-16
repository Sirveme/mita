"""
WhatsApp de avisos (zMita-35, Parte E) — interfaz lista, sin API aún.

enviar_whatsapp(solicitud, evento) hoy SOLO registra en el log (no envía). Cuando MITA
tenga WhatsApp Cloud API, se completa esta función y todo lo demás ya queda conectado.
El número de MITA es configurable (clave chat_conocimiento 'whatsapp_numero').
"""
import re
import logging

logger = logging.getLogger("mita.whatsapp")

MENSAJES = {
    "solicitud_registrada": "Recibimos tu solicitud. Te avisamos apenas un técnico la acepte.",
    "servicio_aceptado": "Tu técnico está en camino.",
    "tecnico_llego": "Tu técnico llegó.",
    "presupuesto": "Tienes un presupuesto por revisar.",
    "comprobante": "Tu comprobante está listo.",
}


def texto_evento(evento, solicitud=None) -> str:
    base = MENSAJES.get(evento, "Tienes una novedad en tu solicitud MITA.")
    sid = getattr(solicitud, "id", None) if solicitud is not None else None
    return f"MITA (solicitud #{sid}): {base}" if sid else f"MITA: {base}"


def enviar_whatsapp(solicitud, evento, texto=None) -> dict:
    """Envío por WhatsApp. IMPLEMENTACIÓN PENDIENTE (Cloud API): hoy solo loguea."""
    texto = texto or texto_evento(evento, solicitud)
    sid = getattr(solicitud, "id", "?")
    tel = getattr(solicitud, "cliente_telefono", None)
    logger.info("[whatsapp][PENDIENTE-API] solicitud=%s evento=%s tel=%s texto=%r", sid, evento, tel, texto)
    return {"ok": False, "pendiente_api": True, "evento": evento, "texto": texto}


def numero_mita(db) -> str:
    """Número de WhatsApp de MITA (solo dígitos, con código país), configurable en el panel."""
    try:
        from app.models.chat_conocimiento import ChatConocimiento
        row = db.query(ChatConocimiento).filter(ChatConocimiento.clave == "whatsapp_numero").first()
        n = (row.contenido or "").strip() if row else ""
        return re.sub(r"\D", "", n)
    except Exception:
        return ""
