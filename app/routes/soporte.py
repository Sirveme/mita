"""
Panel de soporte técnico (Peru Sistemas Pro / Duilio).
Permite configurar integraciones (facturador / pasarela) y catálogos sin tocar código.

Autenticación: clave maestra SOPORTE_PASSWORD (cookie HMAC, stateless) o un
usuario_mita con es_soporte=True. Todas las rutas /soporte/* requieren auth.

IMPORTANTE: aquí NO va la lógica interna de cada facturador/pasarela — solo la
estructura para configurarlos. Las credenciales se cifran (Fernet).
"""

import os
import hmac
import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Body, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.templates import templates
from app.models.integracion import Integracion, IntegracionLog
from app.services.crypto_service import encrypt, decrypt
from app.routes.login_mita import get_current_user

router = APIRouter(tags=["Soporte"])

SOPORTE_COOKIE = "soporte_session"


# ============================================
# Autenticación
# ============================================

def _soporte_token() -> str:
    pw = os.getenv("SOPORTE_PASSWORD", "")
    secret = (settings.SECRET_KEY or "mita")
    return hmac.new(secret.encode(), ("soporte:" + pw).encode(), hashlib.sha256).hexdigest()


async def _identidad(request: Request, db: Session):
    """Devuelve la identidad de soporte ('soporte-maestro' | 'usuario:<dni>') o None."""
    tok = request.cookies.get(SOPORTE_COOKIE)
    if os.getenv("SOPORTE_PASSWORD") and tok and hmac.compare_digest(tok, _soporte_token()):
        return "soporte-maestro"
    user = await get_current_user(request, db)
    if user and getattr(user, "es_soporte", False):
        return f"usuario:{user.dni}"
    return None


async def require_soporte(request: Request, db: Session = Depends(get_db)) -> str:
    ident = await _identidad(request, db)
    if not ident:
        raise HTTPException(status_code=401, detail="No autenticado", headers={"Location": "/soporte/login"})
    return ident


async def _guard_page(request: Request, db: Session):
    if not await _identidad(request, db):
        return RedirectResponse("/soporte/login", status_code=303)
    return None


# ============================================
# Login / páginas
# ============================================

@router.get("/soporte/login", response_class=HTMLResponse)
async def soporte_login_page(request: Request):
    return templates.TemplateResponse("soporte/login.html", {"request": request})


@router.post("/soporte/login")
async def soporte_login(request: Request, password: str = Form("")):
    esperado = os.getenv("SOPORTE_PASSWORD", "")
    if not esperado or not hmac.compare_digest(password, esperado):
        return templates.TemplateResponse("soporte/login.html", {"request": request, "error": "Clave incorrecta"})
    resp = RedirectResponse("/soporte/facturador", status_code=303)
    resp.set_cookie(SOPORTE_COOKIE, _soporte_token(), httponly=True, samesite="lax", max_age=8 * 3600)
    return resp


@router.get("/soporte/logout")
async def soporte_logout():
    resp = RedirectResponse("/soporte/login", status_code=303)
    resp.delete_cookie(SOPORTE_COOKIE)
    return resp


@router.get("/soporte", response_class=HTMLResponse)
async def soporte_home(request: Request, db: Session = Depends(get_db)):
    redir = await _guard_page(request, db)
    return redir or RedirectResponse("/soporte/facturador", status_code=303)


def _pagina(nombre, active):
    async def _p(request: Request, db: Session = Depends(get_db)):
        redir = await _guard_page(request, db)
        if redir:
            return redir
        return templates.TemplateResponse(f"soporte/{nombre}.html", {"request": request, "active": active})
    return _p

router.add_api_route("/soporte/facturador", _pagina("facturador", "facturador"), response_class=HTMLResponse)
router.add_api_route("/soporte/pasarela", _pagina("pasarela", "pasarela"), response_class=HTMLResponse)
router.add_api_route("/soporte/rubros", _pagina("rubros", "rubros"), response_class=HTMLResponse)
router.add_api_route("/soporte/logs", _pagina("logs", "logs"), response_class=HTMLResponse)


# ============================================
# API de integraciones (JSON) — protegida
# ============================================

def _dict_integracion(i: Integracion) -> dict:
    """Serializa SIN exponer secretos (solo si están configurados)."""
    return {
        "id": i.id, "tipo": i.tipo, "proveedor": i.proveedor, "activo": bool(i.activo),
        "modo_sandbox": bool(i.modo_sandbox),
        "url_produccion": i.url_produccion, "url_sandbox": i.url_sandbox, "url_webhook": i.url_webhook,
        "merchant_id": i.merchant_id,
        "api_key_set": bool(i.api_key_encrypted), "api_secret_set": bool(i.api_secret_encrypted),
        "config_json": i.config_json or {},
        "actualizado_por": i.actualizado_por,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }


@router.get("/soporte/api/integracion/{tipo}")
def listar_integracion(tipo: str, db: Session = Depends(get_db), _=Depends(require_soporte)):
    rows = db.query(Integracion).filter(Integracion.tipo == tipo).order_by(Integracion.proveedor).all()
    return {"tipo": tipo, "items": [_dict_integracion(r) for r in rows]}


@router.post("/soporte/api/integracion/{tipo}")
async def guardar_integracion(tipo: str, request: Request, data: dict = Body(...),
                              db: Session = Depends(get_db), ident: str = Depends(require_soporte)):
    proveedor = (data.get("proveedor") or "").strip().lower()
    if not proveedor:
        raise HTTPException(400, "Falta el proveedor.")

    row = (db.query(Integracion)
             .filter(Integracion.tipo == tipo, Integracion.proveedor == proveedor).first())
    if not row:
        row = Integracion(tipo=tipo, proveedor=proveedor)
        db.add(row)

    # Campos simples
    for campo in ("url_produccion", "url_sandbox", "url_webhook", "merchant_id"):
        if campo in data:
            setattr(row, campo, (data.get(campo) or None))
    row.modo_sandbox = bool(data.get("modo_sandbox", row.modo_sandbox))
    if isinstance(data.get("config_json"), dict):
        row.config_json = data["config_json"]

    # Credenciales: solo re-cifrar si vienen con valor (en blanco = conservar)
    if data.get("api_key"):
        row.api_key_encrypted = encrypt(data["api_key"])
    if data.get("api_secret"):
        row.api_secret_encrypted = encrypt(data["api_secret"])

    row.actualizado_por = ident

    # Activación exclusiva por tipo
    if bool(data.get("activo")):
        db.query(Integracion).filter(Integracion.tipo == tipo).update({Integracion.activo: False})
        db.flush()
        row.activo = True

    db.add(IntegracionLog(tipo=tipo, proveedor=proveedor, accion="guardar", usuario=ident,
                          detalle=f"activo={bool(data.get('activo'))} sandbox={row.modo_sandbox}"))
    db.commit()
    db.refresh(row)
    return {"success": True, "integracion": _dict_integracion(row)}


@router.post("/soporte/api/probar-conexion/{tipo}")
def probar_conexion(tipo: str, data: dict = Body(default={}), db: Session = Depends(get_db),
                    ident: str = Depends(require_soporte)):
    """Prueba de estructura (placeholder). La conexión real se implementará con
    la lógica de cada proveedor."""
    proveedor = (data.get("proveedor") or "").strip().lower()
    url = data.get("url_sandbox") if data.get("modo_sandbox") else data.get("url_produccion")
    faltan = [k for k in ("proveedor",) if not (data.get(k) or "").strip()]
    if not url:
        faltan.append("url")
    db.add(IntegracionLog(tipo=tipo, proveedor=proveedor, accion="probar", usuario=ident,
                          detalle=f"url={url}"))
    db.commit()
    if faltan:
        return {"ok": False, "mensaje": "Faltan datos: " + ", ".join(faltan)}
    return {"ok": True, "mensaje": f"Estructura válida ({proveedor}). La prueba real de conexión está pendiente de implementar."}


@router.get("/soporte/api/logs")
def ultimos_logs(db: Session = Depends(get_db), _=Depends(require_soporte)):
    rows = db.query(IntegracionLog).order_by(IntegracionLog.created_at.desc()).limit(100).all()
    return {"items": [
        {"tipo": r.tipo, "proveedor": r.proveedor, "accion": r.accion, "usuario": r.usuario,
         "detalle": r.detalle, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]}
