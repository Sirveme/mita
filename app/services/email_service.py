"""
Envío de correo (SMTP Hostinger) con adjuntos.

Degrada con elegancia: si no hay configuración SMTP, registra el correo en el
log y devuelve False (no rompe el flujo de postulación). Cuando se configuren
las variables de entorno, empieza a enviar de verdad sin cambios de código.

Env:
  SMTP_HOST      (ej: smtp.hostinger.com)
  SMTP_PORT      (465 SSL | 587 STARTTLS; default 465)
  SMTP_USER      (ej: rrhh@mita.pe)
  SMTP_PASSWORD
  SMTP_FROM      (remitente; default = SMTP_USER)
  RRHH_EMAIL     (destino de postulaciones; default rrhh@mita.pe)
"""

import os
import ssl
import smtplib
import logging
from email.message import EmailMessage
from typing import Iterable, Optional

logger = logging.getLogger("mita.email")

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "465") or "465")
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "").strip() or SMTP_USER
RRHH_EMAIL = os.getenv("RRHH_EMAIL", "rrhh@mita.pe").strip()


def email_configurado() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def enviar_email(
    destinatario: str,
    asunto: str,
    cuerpo_html: str,
    adjuntos: Optional[Iterable[dict]] = None,
    cc: Optional[Iterable[str]] = None,
) -> bool:
    """Envía un correo HTML con adjuntos opcionales.

    adjuntos: iterable de {filename, content(bytes), mimetype?}.
    Devuelve True si se envió, False si no hay SMTP configurado o falló."""
    if not email_configurado():
        logger.warning(
            "SMTP no configurado. Correo NO enviado -> to=%s | asunto=%s", destinatario, asunto
        )
        return False

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = destinatario
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = asunto
    msg.set_content("Este correo requiere un cliente compatible con HTML.")
    msg.add_alternative(cuerpo_html, subtype="html")

    for adj in (adjuntos or []):
        content = adj.get("content")
        if content is None:
            continue
        maintype, _, subtype = (adj.get("mimetype") or "application/octet-stream").partition("/")
        msg.add_attachment(
            content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=adj.get("filename", "adjunto"),
        )

    try:
        if SMTP_PORT == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=20) as s:
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        logger.info("Correo enviado -> %s | %s", destinatario, asunto)
        return True
    except Exception as e:
        logger.error("Fallo al enviar correo a %s: %s", destinatario, e)
        return False
