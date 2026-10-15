"""
Web Push (VAPID) — envío de avisos sin costo (zMita-33).

enviar_push(suscripciones, titulo, cuerpo, url, tag) -> dict con conteos.
  - 404/410 del push service => la suscripción se marca activo=false.
  - Nunca lanza: los avisos son best-effort y jamás deben romper el flujo.

Las funciones avisar_* (Parte D) resuelven los destinatarios y delegan en enviar_push.
Se llaman donde el evento ya ocurre; si el evento aún no existe, quedan listas.
"""
import json
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger("mita.push")


def push_configurado() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def _claims():
    return {"sub": settings.VAPID_SUBJECT or "mailto:avisos@mita.pe"}


def enviar_push(db, suscripciones, titulo, cuerpo, url="/", tag="mita", data_extra=None) -> dict:
    """Envía a una lista de PushSuscripcion. Devuelve {ok, fallidas, desactivadas, total}."""
    res = {"ok": 0, "fallidas": 0, "desactivadas": 0, "total": 0}
    if not push_configurado():
        logger.warning("[push] VAPID no configurado; no se envía nada")
        return res
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        logger.error("[push] pywebpush no instalado")
        return res

    payload = json.dumps({
        "title": titulo, "body": cuerpo, "url": url, "tag": tag,
        **({"data": data_extra} if data_extra else {}),
    }, ensure_ascii=False)

    subs = list(suscripciones or [])
    res["total"] = len(subs)
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s.endpoint,
                                   "keys": {"p256dh": s.p256dh, "auth": s.auth}},
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=dict(_claims()),
                ttl=3600,
            )
            s.ultimo_envio_ok = datetime.utcnow()
            res["ok"] += 1
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                s.activo = False
                res["desactivadas"] += 1
                logger.info("[push] suscripción %s dada de baja (%s)", s.id, status)
            else:
                res["fallidas"] += 1
                logger.warning("[push] fallo envío a %s: %s", s.id, status or e)
        except Exception as e:
            res["fallidas"] += 1
            logger.warning("[push] error inesperado enviando a %s: %s", getattr(s, "id", "?"), e)
    try:
        db.commit()
    except Exception:
        db.rollback()
    logger.info("[push] envío '%s': %s", tag, res)
    return res


# ----------------------------------------------------------------------------
# Selección de destinatarios
# ----------------------------------------------------------------------------
def _activas(db, **filtros):
    from app.models.push_suscripcion import PushSuscripcion
    q = db.query(PushSuscripcion).filter(PushSuscripcion.activo == True)
    for k, v in filtros.items():
        q = q.filter(getattr(PushSuscripcion, k) == v)
    return q.all()


def _del_cliente(db, solicitud_id=None, usuario_id=None):
    """Suscripciones del cliente: por usuario_id si lo hay, o por solicitud_id."""
    subs = []
    if usuario_id:
        subs = _activas(db, usuario_id=usuario_id, rol="cliente")
    if not subs and solicitud_id:
        subs = _activas(db, solicitud_id=solicitud_id)
    return subs


def _tecnicos(db, usuario_ids=None):
    subs = _activas(db, rol="tecnico")
    if usuario_ids is not None:
        ids = set(usuario_ids)
        subs = [s for s in subs if s.usuario_id in ids]
    return subs


def _admins(db):
    return _activas(db, rol="admin")


# ----------------------------------------------------------------------------
# Parte D — una función por evento. Todas best-effort (nunca lanzan).
# ----------------------------------------------------------------------------
def avisar_solicitud_registrada(db, solicitud):
    """Cliente: recibimos tu solicitud."""
    try:
        subs = _del_cliente(db, solicitud_id=getattr(solicitud, "id", None),
                            usuario_id=getattr(solicitud, "cliente_id", None) or getattr(solicitud, "usuario_id", None))
        return enviar_push(db, subs, "MITA", "Recibimos tu solicitud. Te avisamos apenas un técnico la acepte.",
                           url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_solicitud_registrada")


def avisar_nuevo_servicio(db, solicitud, tecnico_usuario_ids=None, especialidad="", distrito=""):
    """Técnicos disponibles de esa especialidad: nuevo servicio (sin dirección exacta)."""
    try:
        subs = _tecnicos(db, usuario_ids=tecnico_usuario_ids)
        esp = especialidad or "servicio"
        dist = distrito or "tu zona"
        return enviar_push(db, subs, "Nuevo servicio disponible",
                           f"Nuevo servicio de {esp} en {dist}. Toca para ver detalles.",
                           url="/tecnico/panel", tag=f"nuevo-{getattr(solicitud,'id','')}",
                           data_extra={"tipo": "nuevo_servicio"})
    except Exception:
        logger.exception("[push] avisar_nuevo_servicio")


def avisar_servicio_aceptado(db, solicitud, tecnico_nombre="Tu técnico", minutos=None):
    """Cliente: {técnico} está en camino."""
    try:
        subs = _del_cliente(db, solicitud_id=getattr(solicitud, "id", None),
                            usuario_id=getattr(solicitud, "cliente_id", None) or getattr(solicitud, "usuario_id", None))
        eta = f" Llega en ~{minutos} min." if minutos else ""
        return enviar_push(db, subs, "MITA", f"{tecnico_nombre} está en camino.{eta}",
                           url=f"/cliente/servicio/{solicitud.id}/seguimiento", tag=f"sol-{solicitud.id}",
                           data_extra={"tipo": "tecnico_asignado"})
    except Exception:
        logger.exception("[push] avisar_servicio_aceptado")


def avisar_tecnico_llego(db, solicitud):
    """Cliente: tu técnico llegó."""
    try:
        subs = _del_cliente(db, solicitud_id=getattr(solicitud, "id", None),
                            usuario_id=getattr(solicitud, "cliente_id", None) or getattr(solicitud, "usuario_id", None))
        return enviar_push(db, subs, "MITA", "Tu técnico llegó.",
                           url=f"/cliente/servicio/{solicitud.id}/seguimiento", tag=f"sol-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_tecnico_llego")


def avisar_presupuesto(db, solicitud):
    """Cliente: tienes un presupuesto por revisar."""
    try:
        subs = _del_cliente(db, solicitud_id=getattr(solicitud, "id", None),
                            usuario_id=getattr(solicitud, "cliente_id", None) or getattr(solicitud, "usuario_id", None))
        return enviar_push(db, subs, "MITA", "Tienes un presupuesto por revisar.",
                           url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_presupuesto")


def avisar_comprobante(db, solicitud):
    """Cliente: tu comprobante está listo."""
    try:
        subs = _del_cliente(db, solicitud_id=getattr(solicitud, "id", None),
                            usuario_id=getattr(solicitud, "cliente_id", None) or getattr(solicitud, "usuario_id", None))
        return enviar_push(db, subs, "MITA", "Tu comprobante está listo.",
                           url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_comprobante")


def avisar_sin_aceptar(db, solicitud, especialidad="", distrito=""):
    """Admin (torre de control): servicio sin aceptar."""
    try:
        subs = _admins(db)
        esp = especialidad or "servicio"
        dist = distrito or "—"
        return enviar_push(db, subs, "Torre de control",
                           f"Servicio sin aceptar: {esp}, {dist}.",
                           url="/admin/push", tag=f"sin-aceptar-{getattr(solicitud,'id','')}")
    except Exception:
        logger.exception("[push] avisar_sin_aceptar")
