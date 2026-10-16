"""
API de Web Push (zMita-33/35): clave pública, suscribir/desuscribir, canal de avisos,
confirmación de entrega (/recibido) y panel admin con métricas.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.push_suscripcion import PushSuscripcion, PushEnvio
from app.services import push as push_srv

logger = logging.getLogger("mita.push")
router = APIRouter(prefix="/api/v1/push", tags=["Push"])


def _asegurar_tablas():
    """Crea push_suscripciones y push_envios si faltan (idempotente). Auto-cura prod."""
    try:
        from app.core.database import engine
        PushSuscripcion.__table__.create(bind=engine, checkfirst=True)
        PushEnvio.__table__.create(bind=engine, checkfirst=True)
        return True
    except Exception:
        logger.exception("[push] no se pudieron asegurar las tablas de push")
        return False


def _error_bd(e, db) -> JSONResponse:
    try:
        db.rollback()
    except Exception:
        pass
    detalle = str(getattr(e, "orig", e))
    bajo = detalle.lower()
    if ("push_suscripciones" in bajo or "push_envios" in bajo) and \
            any(k in bajo for k in ("exist", "no existe", "relation", "undefined", "does not", "column")):
        msg = ("La tabla de avisos aún no está actualizada en el servidor. Vuelve a desplegar MITA "
               "(se crea sola al arrancar) o corre las migraciones 29 y 30.")
    else:
        msg = "No se pudo guardar tu suscripción a los avisos."
    logger.exception("[push] error de BD")
    return JSONResponse(status_code=503, content={"ok": False, "error": msg, "detalle": detalle[:300]})


def _plataforma(ua: str) -> str:
    u = (ua or "").lower()
    if "iphone" in u or "ipad" in u or ("safari" in u and "mac" in u and "mobile" in u):
        return "ios"
    if "android" in u:
        return "android"
    if "windows" in u:
        return "windows"
    if "mac" in u:
        return "mac"
    return "otro"


async def _sesion(request: Request, db: Session):
    """(usuario_id, rol) desde la cookie de sesión, o (None, None)."""
    try:
        from app.routes.login_mita import get_current_user
        user = await get_current_user(request, db)
    except Exception:
        user = None
    if not user:
        return None, None
    tipo = (getattr(user, "tipo", "") or getattr(user, "rol", "") or "").lower()
    if tipo in ("admin", "gerente", "secretaria"):
        rol = "admin"
    elif tipo in ("tecnico", "proveedor"):
        rol = "tecnico"
    else:
        rol = "cliente"
    return getattr(user, "id", None), rol


@router.get("/clave-publica")
async def clave_publica():
    return {"clave": settings.VAPID_PUBLIC_KEY, "configurado": push_srv.push_configurado()}


@router.get("/canal-config")
async def canal_config(db: Session = Depends(get_db)):
    """Datos para armar el enlace de WhatsApp en el cliente."""
    from app.services.whatsapp import numero_mita
    return {"whatsapp_numero": numero_mita(db)}


@router.post("/suscribir")
async def suscribir(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """Guarda/actualiza la suscripción. Un mismo dispositivo NO acumula filas: si llega
    dispositivo_id, se reutiliza/reemplaza su fila. Nunca devuelve un 500 mudo."""
    try:
        sub = data.get("subscription") or data
        endpoint = sub.get("endpoint")
        keys = sub.get("keys") or {}
        p256dh, auth = keys.get("p256dh"), keys.get("auth")
        if not endpoint or not p256dh or not auth:
            return JSONResponse(status_code=422,
                                content={"ok": False, "error": "La suscripción llegó incompleta. Reintenta."})
        ua = request.headers.get("user-agent", "")[:400]
        plataforma = (data.get("plataforma") or _plataforma(ua)).lower()
        usuario_id, rol = await _sesion(request, db)
        rol = data.get("rol") or rol or "cliente"
        solicitud_id = data.get("solicitud_id")
        dispositivo_id = (data.get("dispositivo_id") or "")[:64] or None

        _asegurar_tablas()
        # Reutilizar la fila: por endpoint exacto; si no, por dispositivo (mismo equipo, nuevo endpoint)
        row = db.query(PushSuscripcion).filter(PushSuscripcion.endpoint == endpoint).first()
        if not row and dispositivo_id:
            row = (db.query(PushSuscripcion)
                   .filter(PushSuscripcion.dispositivo_id == dispositivo_id)
                   .order_by(PushSuscripcion.id.desc()).first())
        if not row:
            row = PushSuscripcion(endpoint=endpoint)
            db.add(row)

        # Completar TODOS los campos obligatorios antes de cualquier otra consulta
        row.endpoint = endpoint
        row.p256dh = p256dh
        row.auth = auth
        row.plataforma = plataforma
        row.user_agent = ua
        row.activo = True
        if dispositivo_id:
            row.dispositivo_id = dispositivo_id
        if usuario_id:
            row.usuario_id = usuario_id
        if rol:
            row.rol = rol
        if solicitud_id:
            try:
                row.solicitud_id = int(solicitud_id)
            except (TypeError, ValueError):
                pass
        db.flush()   # persistir la fila actual (ya completa) antes del dedup

        # Dedup: un mismo dispositivo no acumula filas -> desactivar las demás
        if dispositivo_id and row.id:
            (db.query(PushSuscripcion)
             .filter(PushSuscripcion.dispositivo_id == dispositivo_id,
                     PushSuscripcion.id != row.id)
             .update({PushSuscripcion.activo: False}, synchronize_session=False))

        # Si el cliente activó push para una solicitud, marcar el canal
        if rol == "cliente" and row.solicitud_id:
            _marcar_canal(db, row.solicitud_id, "push")
        db.commit()
        return {"ok": True, "id": row.id, "plataforma": plataforma, "rol": row.rol}
    except SQLAlchemyError as e:
        return _error_bd(e, db)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception("[push] error inesperado al suscribir")
        return JSONResponse(status_code=500,
                            content={"ok": False, "error": "Error inesperado al activar los avisos.",
                                     "detalle": str(e)[:300]})


def _marcar_canal(db, solicitud_id, canal):
    try:
        from app.models.solicitud_mita import Solicitud
        s = db.query(Solicitud).get(int(solicitud_id))
        if s:
            s.canal_avisos = canal
    except Exception:
        logger.exception("[push] no se pudo marcar canal_avisos")


@router.post("/canal")
async def set_canal(data: dict = Body(...), db: Session = Depends(get_db)):
    """Guarda el canal elegido para una solicitud (push / whatsapp / ninguno)."""
    solicitud_id = data.get("solicitud_id")
    canal = (data.get("canal") or "ninguno").lower()
    if canal not in ("push", "whatsapp", "ninguno"):
        raise HTTPException(status_code=422, detail="Canal inválido")
    if not solicitud_id:
        raise HTTPException(status_code=422, detail="Falta solicitud_id")
    _marcar_canal(db, solicitud_id, canal)
    db.commit()
    return {"ok": True, "canal": canal}


@router.post("/desuscribir")
async def desuscribir(data: dict = Body(...), db: Session = Depends(get_db)):
    endpoint = data.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=422, detail="Falta endpoint")
    row = db.query(PushSuscripcion).filter(PushSuscripcion.endpoint == endpoint).first()
    if row:
        row.activo = False
        db.commit()
    return {"ok": True}


@router.post("/prueba")
async def prueba(data: dict = Body(default={}), db: Session = Depends(get_db)):
    """Envía 'tus avisos están activos ✓'. Devuelve aviso_id para medir la demora."""
    endpoint = (data or {}).get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=422, detail="Falta endpoint")
    row = db.query(PushSuscripcion).filter(PushSuscripcion.endpoint == endpoint,
                                           PushSuscripcion.activo == True).first()
    if not row:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    res = push_srv.enviar_push(db, [row], "MITA", "MITA: tus avisos están activos ✓",
                               url="/prueba-avisos", tag="prueba", urgente=True, topic=f"prueba-{row.id}")
    aviso_id = (res.get("aviso_ids") or [None])[0]
    return {"ok": res["ok"] > 0, "aviso_id": aviso_id, "resultado": res}


@router.post("/recibido")
async def recibido(data: dict = Body(...), db: Session = Depends(get_db)):
    """El service worker confirma la entrega (no bloquea la notificación)."""
    aviso_id = (data or {}).get("aviso_id")
    if not aviso_id:
        return {"ok": False}
    cuando = datetime.utcnow()
    rec = (data.get("recibido_en") or "")
    if rec:
        try:
            cuando = datetime.fromisoformat(rec.replace("Z", "").split("+")[0])
        except Exception:
            cuando = datetime.utcnow()
    try:
        (db.query(PushEnvio)
         .filter(PushEnvio.aviso_id == aviso_id, PushEnvio.recibido_en.is_(None))
         .update({PushEnvio.recibido_en: cuando}, synchronize_session=False))
        db.commit()
    except Exception:
        db.rollback()
        return {"ok": False}
    return {"ok": True}


@router.get("/envio/{aviso_id}")
async def estado_envio(aviso_id: str, db: Session = Depends(get_db)):
    """Estado de un aviso concreto (para mostrar la demora en /prueba-avisos)."""
    e = db.query(PushEnvio).filter(PushEnvio.aviso_id == aviso_id).order_by(PushEnvio.id.desc()).first()
    if not e:
        return {"encontrado": False}
    demora = None
    if e.recibido_en and e.enviado_en:
        demora = round((e.recibido_en - e.enviado_en).total_seconds(), 1)
    return {"encontrado": True, "recibido": bool(e.recibido_en),
            "demora_seg": demora, "codigo_http": e.codigo_http}


# -------- Admin --------
def _nombre_usuario(db, usuario_id):
    if not usuario_id:
        return None
    try:
        from app.models.auth_mita import UsuarioMita
        u = db.query(UsuarioMita).get(usuario_id)
        return (u.nombres or u.dni) if u else None
    except Exception:
        return None


@router.get("/admin/suscripciones")
async def listar_suscripciones(request: Request, db: Session = Depends(get_db)):
    uid, rol = await _sesion(request, db)
    if rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administración")
    rows = db.query(PushSuscripcion).order_by(PushSuscripcion.id.desc()).limit(200).all()
    return [{"id": r.id, "rol": r.rol, "plataforma": r.plataforma, "usuario_id": r.usuario_id,
             "usuario_nombre": _nombre_usuario(db, r.usuario_id),
             "solicitud_id": r.solicitud_id, "activo": bool(r.activo),
             "ultimo_codigo": r.ultimo_codigo, "ultimo_motivo": r.ultimo_motivo,
             "ultimo_envio_at": r.ultimo_envio_at.isoformat() if r.ultimo_envio_at else None,
             "ultimo_envio_ok": r.ultimo_envio_ok.isoformat() if r.ultimo_envio_ok else None,
             "created_at": r.created_at.isoformat() if r.created_at else None,
             "endpoint": (r.endpoint[:48] + "…") if r.endpoint else ""} for r in rows]


@router.get("/admin/metricas")
async def metricas(request: Request, db: Session = Depends(get_db)):
    uid, rol = await _sesion(request, db)
    if rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administración")
    desde = datetime.utcnow() - timedelta(hours=24)
    envios = db.query(PushEnvio).filter(PushEnvio.enviado_en >= desde).all()
    total = len(envios)
    recibidos = [e for e in envios if e.recibido_en]
    demoras = [(e.recibido_en - e.enviado_en).total_seconds() for e in recibidos if e.enviado_en]
    entrega_pct = round(100.0 * len(recibidos) / total, 1) if total else None
    demora_media = round(sum(demoras) / len(demoras), 1) if demoras else None
    # últimos envíos para la tabla
    recientes = (db.query(PushEnvio).order_by(PushEnvio.id.desc()).limit(50).all())
    def _estado(e):
        if e.recibido_en:
            return "recibido"
        if e.codigo_http and e.codigo_http < 300:
            return "enviado"
        return "sin confirmar"
    lista = [{"id": e.id, "aviso_id": e.aviso_id, "tag": e.tag, "suscripcion_id": e.suscripcion_id,
              "codigo_http": e.codigo_http, "estado": _estado(e),
              "enviado_en": e.enviado_en.isoformat() if e.enviado_en else None,
              "demora_seg": round((e.recibido_en - e.enviado_en).total_seconds(), 1)
                            if (e.recibido_en and e.enviado_en) else None} for e in recientes]
    return {"ventana_horas": 24, "total": total, "recibidos": len(recibidos),
            "entrega_pct": entrega_pct, "demora_media_seg": demora_media, "envios": lista}


@router.get("/admin/whatsapp-pendientes")
async def whatsapp_pendientes(request: Request, db: Session = Depends(get_db)):
    """Solicitudes cuyo cliente eligió WhatsApp: texto listo para copiar (mientras no hay API)."""
    uid, rol = await _sesion(request, db)
    if rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.models.solicitud_mita import Solicitud
    from app.services.whatsapp import texto_evento, numero_mita
    rows = (db.query(Solicitud).filter(Solicitud.canal_avisos == "whatsapp")
            .order_by(Solicitud.id.desc()).limit(50).all())
    eventos = ["servicio_aceptado", "tecnico_llego", "presupuesto", "comprobante"]
    return {"numero": numero_mita(db),
            "solicitudes": [{"id": s.id, "telefono": getattr(s, "cliente_telefono", None),
                             "estado": s.estado,
                             "textos": {ev: texto_evento(ev, s) for ev in eventos}} for s in rows]}


@router.post("/admin/prueba/{sub_id}")
async def admin_prueba(sub_id: int, request: Request, db: Session = Depends(get_db)):
    uid, rol = await _sesion(request, db)
    if rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administración")
    row = db.query(PushSuscripcion).filter(PushSuscripcion.id == sub_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="No existe")
    res = push_srv.enviar_push(db, [row], "MITA", "MITA: prueba desde la torre de control ✓",
                               url="/admin/push", tag="prueba-admin", urgente=True, topic=f"prueba-{row.id}")
    return {"ok": res["ok"] > 0, "aviso_id": (res.get("aviso_ids") or [None])[0], "resultado": res}
