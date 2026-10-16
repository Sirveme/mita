"""
Web Push (VAPID) — envío de avisos sin costo (zMita-33).

enviar_push(suscripciones, titulo, cuerpo, url, tag) -> dict con conteos.
  - 404/410 del push service => la suscripción se marca activo=false.
  - Nunca lanza: los avisos son best-effort y jamás deben romper el flujo.

Las funciones avisar_* (Parte D) resuelven los destinatarios y delegan en enviar_push.
Se llaman donde el evento ya ocurre; si el evento aún no existe, quedan listas.
"""
import re
import json
import uuid
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger("mita.push")


def push_configurado() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def _claims():
    return {"sub": settings.VAPID_SUBJECT or "mailto:avisos@mita.pe"}


def _topic_valido(t):
    """RFC 8030: Topic <= 32 chars, solo [A-Za-z0-9-_]. Un push nuevo reemplaza al viejo
    no entregado con el mismo Topic."""
    if not t:
        return None
    t = re.sub(r"[^A-Za-z0-9_-]", "-", str(t))
    return t[:32] or None


def enviar_push(db, suscripciones, titulo, cuerpo, url="/", tag="mita", data_extra=None,
                urgente=False, topic=None, ttl=3600) -> dict:
    """Envía a una lista de PushSuscripcion. Registra cada envío en push_envios y el
    último código/motivo en la suscripción. Baja (activo=false) SOLO con 404/410.
    Devuelve {ok, fallidas, desactivadas, total, aviso_ids}."""
    res = {"ok": 0, "fallidas": 0, "desactivadas": 0, "total": 0, "aviso_ids": []}
    if not push_configurado():
        logger.warning("[push] VAPID no configurado; no se envía nada")
        return res
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        logger.error("[push] pywebpush no instalado")
        return res
    from app.models.push_suscripcion import PushEnvio

    subs = list(suscripciones or [])
    res["total"] = len(subs)
    headers = {"Urgency": "high" if urgente else "normal"}
    tp = _topic_valido(topic)
    if tp:
        headers["Topic"] = tp

    for s in subs:
        aviso_id = uuid.uuid4().hex[:16]
        enviado_en = datetime.utcnow()
        payload = json.dumps({
            "title": titulo, "body": cuerpo, "url": url, "tag": tag,
            "aviso_id": aviso_id, "enviado_en": enviado_en.isoformat(),
            **({"data": data_extra} if data_extra else {}),
        }, ensure_ascii=False)
        codigo = None
        motivo = ""
        try:
            resp = webpush(
                subscription_info={"endpoint": s.endpoint,
                                   "keys": {"p256dh": s.p256dh, "auth": s.auth}},
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=dict(_claims()),
                ttl=ttl,
                headers=headers,
            )
            codigo = getattr(resp, "status_code", 201)
            motivo = "enviado"
            s.ultimo_envio_ok = enviado_en
            res["ok"] += 1
        except WebPushException as e:
            codigo = getattr(getattr(e, "response", None), "status_code", None)
            if codigo in (404, 410):
                s.activo = False
                motivo = f"baja ({codigo}): suscripción expirada"
                res["desactivadas"] += 1
                logger.info("[push] suscripción %s dada de baja (%s)", s.id, codigo)
            else:
                # 403 (VAPID), 413, 429, 5xx, timeout... se registran pero NO dan de baja
                motivo = f"error {codigo or 's/código'} (sigue activa)"
                res["fallidas"] += 1
                logger.warning("[push] fallo envío a %s: %s (no se da de baja)", s.id, codigo or e)
        except Exception as e:
            motivo = f"excepción: {str(e)[:60]}"
            res["fallidas"] += 1
            logger.warning("[push] error inesperado enviando a %s: %s", getattr(s, "id", "?"), e)

        s.ultimo_codigo = codigo
        s.ultimo_motivo = motivo[:120]
        s.ultimo_envio_at = enviado_en
        try:
            db.add(PushEnvio(aviso_id=aviso_id, suscripcion_id=getattr(s, "id", None),
                             tag=tag, enviado_en=enviado_en, codigo_http=codigo))
            res["aviso_ids"].append(aviso_id)
        except Exception:
            logger.exception("[push] no se pudo registrar push_envios")

    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("[push] no se pudo commitear el envío")
    logger.info("[push] envío '%s': %s", tag, {k: res[k] for k in ("ok", "fallidas", "desactivadas", "total")})
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


def _usuarios_de_personal(db, personal_ids):
    """Mapea Personal.id -> UsuarioMita.id (técnicos) para dirigir el push (Parte F)."""
    if not personal_ids:
        return []
    try:
        from app.models.auth_mita import UsuarioMita
        filas = (db.query(UsuarioMita.id)
                 .filter(UsuarioMita.personal_id.in_(list(personal_ids)),
                         UsuarioMita.tipo == "tecnico").all())
        return [f[0] for f in filas]
    except Exception:
        logger.exception("[push] no se pudo mapear personal->usuario")
        return []


def _avisar_cliente(db, solicitud, cuerpo, url, tag, evento, urgente=False, topic=None,
                    data_extra=None, titulo="MITA"):
    """Avisa al cliente por el canal elegido: WhatsApp (si lo eligió) o push."""
    canal = (getattr(solicitud, "canal_avisos", None) or "").lower()
    if canal == "whatsapp":
        from app.services.whatsapp import enviar_whatsapp
        return enviar_whatsapp(solicitud, evento, cuerpo)
    subs = _del_cliente(db, solicitud_id=getattr(solicitud, "id", None),
                        usuario_id=getattr(solicitud, "cliente_id", None) or getattr(solicitud, "usuario_id", None))
    return enviar_push(db, subs, titulo, cuerpo, url=url, tag=tag, data_extra=data_extra,
                       urgente=urgente, topic=topic)


# ----------------------------------------------------------------------------
# Parte D — una función por evento. Todas best-effort (nunca lanzan).
# ----------------------------------------------------------------------------
def avisar_solicitud_registrada(db, solicitud):
    """Cliente: recibimos tu solicitud."""
    try:
        return _avisar_cliente(db, solicitud, "Recibimos tu solicitud. Te avisamos apenas un técnico la acepte.",
                               url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}",
                               evento="solicitud_registrada", topic=f"registrada-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_solicitud_registrada")


def avisar_nuevo_servicio(db, solicitud, tecnico_usuario_ids=None, tecnico_personal_ids=None,
                          especialidad="", distrito=""):
    """Técnicos de esa especialidad y disponibles hoy (Parte F). Sin dirección exacta."""
    try:
        usuario_ids = list(tecnico_usuario_ids) if tecnico_usuario_ids is not None else None
        if usuario_ids is None and tecnico_personal_ids is not None:
            usuario_ids = _usuarios_de_personal(db, tecnico_personal_ids)
        subs = _tecnicos(db, usuario_ids=usuario_ids)
        esp = especialidad or "servicio"
        dist = distrito or "tu zona"
        return enviar_push(db, subs, "Nuevo servicio disponible",
                           f"Nuevo servicio de {esp} en {dist}. Toca para ver detalles.",
                           url="/tecnico/panel", tag=f"nuevo-{getattr(solicitud,'id','')}",
                           data_extra={"tipo": "nuevo_servicio"}, urgente=True,
                           topic=f"nuevo-{getattr(solicitud,'id','')}")
    except Exception:
        logger.exception("[push] avisar_nuevo_servicio")


def avisar_servicio_aceptado(db, solicitud, tecnico_nombre="Tu técnico", minutos=None):
    """Cliente: {técnico} está en camino. (urgente)"""
    try:
        eta = f" Llega en ~{minutos} min." if minutos else ""
        return _avisar_cliente(db, solicitud, f"{tecnico_nombre} aceptó tu servicio.{eta}",
                               url=f"/cliente/servicio/{solicitud.id}/seguimiento", tag=f"sol-{solicitud.id}",
                               evento="servicio_aceptado", urgente=True, topic=f"aceptado-{solicitud.id}",
                               data_extra={"tipo": "tecnico_asignado"})
    except Exception:
        logger.exception("[push] avisar_servicio_aceptado")


def avisar_en_camino(db, solicitud, tecnico_nombre="Tu técnico", minutos=None):
    """Cliente: tu técnico está en camino, llega en ~N min. (urgente)"""
    try:
        eta = f", llega en ~{minutos} min" if minutos else ""
        return _avisar_cliente(db, solicitud, f"{tecnico_nombre} está en camino{eta}.",
                               url=f"/cliente/servicio/{solicitud.id}/seguimiento", tag=f"sol-{solicitud.id}",
                               evento="en_camino", urgente=True, topic=f"en-camino-{solicitud.id}",
                               data_extra={"tipo": "en_camino"})
    except Exception:
        logger.exception("[push] avisar_en_camino")


def avisar_tecnico_llego(db, solicitud):
    """Cliente: tu técnico llegó. (urgente)"""
    try:
        return _avisar_cliente(db, solicitud, "Tu técnico llegó.",
                               url=f"/cliente/servicio/{solicitud.id}/seguimiento", tag=f"sol-{solicitud.id}",
                               evento="tecnico_llego", urgente=True, topic=f"llego-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_tecnico_llego")


def avisar_presupuesto(db, solicitud):
    """Cliente: tienes un presupuesto por revisar. (urgente)"""
    try:
        return _avisar_cliente(db, solicitud, "Tienes un presupuesto por revisar.",
                               url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}",
                               evento="presupuesto", urgente=True, topic=f"presupuesto-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_presupuesto")


def avisar_mensaje(db, solicitud, destino_rol, autor_nombre="Alguien"):
    """Nuevo mensaje del chat de 3 (Topic por solicitud, agrupa)."""
    try:
        cuerpo = f"Nuevo mensaje de {autor_nombre}"
        sid = getattr(solicitud, "id", "")
        if destino_rol == "cliente":
            return _avisar_cliente(db, solicitud, cuerpo, url=f"/cliente/servicio/{sid}/chats",
                                   tag=f"sol-{sid}", evento="mensaje", topic=f"chat-{sid}")
        subs = _tecnicos(db, usuario_ids=_usuarios_de_personal(db, [getattr(solicitud, "tecnico_id", None)]))
        return enviar_push(db, subs, "MITA", cuerpo, url=f"/tecnico/servicio/{sid}",
                           tag=f"sol-{sid}", topic=f"chat-{sid}")
    except Exception:
        logger.exception("[push] avisar_mensaje")


def avisar_liquidacion(db, liq):
    """Técnico: tu liquidación está lista para que emitas tu Recibo por Honorarios."""
    try:
        subs = _tecnicos(db, usuario_ids=_usuarios_de_personal(db, [getattr(liq, "tecnico_id", None)]))
        return enviar_push(db, subs, "Tu liquidación",
                           f"Tu liquidación está lista: S/ {float(getattr(liq,'a_transferir',0) or 0):.2f}. "
                           f"Emite tu Recibo por Honorarios.",
                           url="/tecnico/mi-liquidacion", tag=f"liq-{getattr(liq,'id','')}",
                           topic=f"liq-{getattr(liq,'id','')}")
    except Exception:
        logger.exception("[push] avisar_liquidacion")


def avisar_liquidacion_pagada(db, liq):
    """Técnico: tu parte fue pagada."""
    try:
        subs = _tecnicos(db, usuario_ids=_usuarios_de_personal(db, [getattr(liq, "tecnico_id", None)]))
        return enviar_push(db, subs, "Tu liquidación",
                           f"Te pagamos S/ {float(getattr(liq,'a_transferir',0) or 0):.2f} "
                           f"({getattr(liq,'pago_medio','') or ''}).",
                           url="/tecnico/mi-liquidacion", tag=f"liq-{getattr(liq,'id','')}",
                           topic=f"liq-{getattr(liq,'id','')}")
    except Exception:
        logger.exception("[push] avisar_liquidacion_pagada")


def avisar_seguimos_buscando(db, solicitud):
    """Cliente: seguimos buscando un técnico."""
    try:
        return _avisar_cliente(db, solicitud,
                               "Seguimos buscando un técnico disponible, te avisamos apenas uno acepte.",
                               url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}",
                               evento="seguimos_buscando", topic=f"buscando-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_seguimos_buscando")


def avisar_pago_recibido(db, solicitud):
    """Cliente: pago recibido, buscando técnico."""
    try:
        return _avisar_cliente(db, solicitud, "¡Pago recibido! Estamos buscando un técnico para ti.",
                               url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}",
                               evento="pago_recibido", topic=f"pago-{solicitud.id}")
    except Exception:
        logger.exception("[push] avisar_pago_recibido")


def avisar_comprobante(db, solicitud):
    """Cliente: tu comprobante está listo."""
    try:
        return _avisar_cliente(db, solicitud, "Tu comprobante está listo.",
                               url=f"/cliente/servicio/{solicitud.id}/chats", tag=f"sol-{solicitud.id}",
                               evento="comprobante", topic=f"comprobante-{solicitud.id}")
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
