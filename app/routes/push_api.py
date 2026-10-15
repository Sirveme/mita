"""
API de Web Push (zMita-33): clave pública, suscribir, desuscribir y envío de prueba.
"""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.push_suscripcion import PushSuscripcion
from app.services import push as push_srv

logger = logging.getLogger("mita.push")
router = APIRouter(prefix="/api/v1/push", tags=["Push"])


def _asegurar_tabla():
    """Crea push_suscripciones si falta (idempotente). Auto-cura producción sin
    tener que correr la migración a mano."""
    try:
        from app.core.database import engine
        PushSuscripcion.__table__.create(bind=engine, checkfirst=True)
        return True
    except Exception:
        logger.exception("[push] no se pudo asegurar la tabla push_suscripciones")
        return False


def _error_bd(e, db) -> JSONResponse:
    try:
        db.rollback()
    except Exception:
        pass
    detalle = str(getattr(e, "orig", e))
    bajo = detalle.lower()
    if "push_suscripciones" in bajo and any(k in bajo for k in ("exist", "no existe", "relation", "undefined", "does not")):
        msg = ("La tabla de avisos aún no está creada en el servidor. Vuelve a desplegar MITA "
               "(se crea sola al arrancar) o corre la migración 29.")
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


@router.post("/suscribir")
async def suscribir(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """Guarda/actualiza la suscripción. NUNCA devuelve un 500 mudo: ante error
    de BD responde un JSON con 'error' legible (y 'detalle' para el log)."""
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

        _asegurar_tabla()   # auto-cura: crea la tabla si falta (idempotente)
        row = db.query(PushSuscripcion).filter(PushSuscripcion.endpoint == endpoint).first()
        if not row:
            row = PushSuscripcion(endpoint=endpoint)
            db.add(row)
        row.p256dh = p256dh
        row.auth = auth
        row.plataforma = plataforma
        row.user_agent = ua
        row.activo = True
        if usuario_id:
            row.usuario_id = usuario_id
        if rol:
            row.rol = rol
        if solicitud_id:
            try:
                row.solicitud_id = int(solicitud_id)
            except (TypeError, ValueError):
                pass
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
    """Envía 'tus avisos están activos ✓' a la suscripción indicada (por endpoint)."""
    endpoint = (data or {}).get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=422, detail="Falta endpoint")
    row = db.query(PushSuscripcion).filter(PushSuscripcion.endpoint == endpoint,
                                           PushSuscripcion.activo == True).first()
    if not row:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")
    res = push_srv.enviar_push(db, [row], "MITA", "MITA: tus avisos están activos ✓",
                               url="/prueba-avisos", tag="prueba")
    return {"ok": res["ok"] > 0, "resultado": res}


# -------- Admin --------
@router.get("/admin/suscripciones")
async def listar_suscripciones(request: Request, db: Session = Depends(get_db)):
    uid, rol = await _sesion(request, db)
    if rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administración")
    rows = db.query(PushSuscripcion).order_by(PushSuscripcion.id.desc()).limit(200).all()
    return [{"id": r.id, "rol": r.rol, "plataforma": r.plataforma, "usuario_id": r.usuario_id,
             "solicitud_id": r.solicitud_id, "activo": bool(r.activo),
             "ultimo_envio_ok": r.ultimo_envio_ok.isoformat() if r.ultimo_envio_ok else None,
             "created_at": r.created_at.isoformat() if r.created_at else None,
             "endpoint": (r.endpoint[:48] + "…") if r.endpoint else ""} for r in rows]


@router.post("/admin/prueba/{sub_id}")
async def admin_prueba(sub_id: int, request: Request, db: Session = Depends(get_db)):
    uid, rol = await _sesion(request, db)
    if rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administración")
    row = db.query(PushSuscripcion).filter(PushSuscripcion.id == sub_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="No existe")
    res = push_srv.enviar_push(db, [row], "MITA", "MITA: prueba desde la torre de control ✓",
                               url="/admin/push", tag="prueba-admin")
    return {"ok": res["ok"] > 0, "resultado": res}
