"""
Sistema de autenticación del panel MITA (login por DNI + sesión por cookie).

Archivo NUEVO e independiente de routes/auth.py (JWT API en /api/v1/auth).
Rutas: GET/POST /login, GET /logout.
Dependencias reutilizables: get_current_user, require_auth, require_admin.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import bcrypt

from app.core.database import get_db
from app.core.templates import templates
from app.models.auth_mita import UsuarioMita, SesionMita

router = APIRouter(tags=["Auth MITA"])

# NOTA: se usa el paquete `bcrypt` directamente en vez de passlib.CryptContext
# porque passlib 1.7.4 es incompatible con bcrypt>=4.1 en este entorno
# (ValueError en detect_wrap_bug). bcrypt limita el secreto a 72 bytes.

SESSION_HOURS = 8
MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 15


def _to72(password: str) -> bytes:
    return (password or "").encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to72(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to72(plain), (hashed or "").encode("utf-8"))
    except Exception:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login del panel MITA."""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Procesa el login por DNI + contraseña."""
    form = await request.form()
    dni = (form.get("dni") or "").strip()
    password = form.get("password") or ""

    def _error(msg: str):
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": msg})

    usuario = (
        db.query(UsuarioMita)
        .filter(UsuarioMita.dni == dni, UsuarioMita.activo == True)
        .first()
    )
    if not usuario:
        return _error("DNI no registrado")

    # Bloqueo temporal por intentos
    if usuario.bloqueado_hasta and usuario.bloqueado_hasta > datetime.utcnow():
        return _error("Cuenta bloqueada temporalmente. Intenta más tarde.")

    # Contraseña
    if not verify_password(password, usuario.password_hash):
        usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
        if usuario.intentos_fallidos >= MAX_INTENTOS:
            usuario.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=BLOQUEO_MINUTOS)
            usuario.intentos_fallidos = 0
        db.commit()
        return _error("Contraseña incorrecta")

    # Login OK -> crear sesión
    token = generate_token()
    sesion = SesionMita(
        usuario_id=usuario.id,
        token=token,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=datetime.utcnow() + timedelta(hours=SESSION_HOURS),
        activa=True,
    )
    db.add(sesion)
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_acceso = datetime.utcnow()
    db.commit()

    # Forzar cambio de clave en primer ingreso
    if usuario.requiere_cambio_clave:
        destino = "/cambiar-clave"
    elif usuario.tipo in ("admin", "gerente"):
        destino = "/admin"
    elif usuario.tipo == "secretaria":
        destino = "/secretaria"
    elif usuario.tipo == "tecnico":
        destino = "/tecnico"
    else:
        destino = "/cliente/home"

    response = RedirectResponse(url=destino, status_code=303)
    response.set_cookie(
        key="mita_session",
        value=token,
        httponly=True,
        max_age=SESSION_HOURS * 3600,
        samesite="lax",
    )
    return response


def validar_clave(clave: str) -> list:
    """Requisitos: min 6 chars, 1 mayúscula, solo letras/números y * @ / \\ #"""
    errores = []
    if len(clave) < 6:
        errores.append("La clave debe tener mínimo 6 caracteres")
    if not any(c.isupper() for c in clave):
        errores.append("La clave debe tener al menos una mayúscula")
    validos = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789*@/\\#")
    if not all(c in validos for c in clave):
        errores.append("La clave solo puede contener letras, números y * @ / \\ #")
    return errores


@router.get("/cambiar-clave", response_class=HTMLResponse)
async def cambiar_clave_page(request: Request):
    return templates.TemplateResponse("auth/cambiar_clave.html", {"request": request})


@router.post("/cambiar-clave")
async def cambiar_clave(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    nueva = form.get("nueva_clave") or ""
    confirmar = form.get("confirmar_clave") or ""

    errores = validar_clave(nueva)
    if errores:
        return templates.TemplateResponse("auth/cambiar_clave.html", {"request": request, "error": errores[0]})
    if nueva != confirmar:
        return templates.TemplateResponse("auth/cambiar_clave.html", {"request": request, "error": "Las claves no coinciden"})

    user.password_hash = hash_password(nueva)
    user.requiere_cambio_clave = False
    db.commit()

    if user.tipo in ("admin", "gerente"):
        destino = "/admin"
    elif user.tipo == "secretaria":
        destino = "/secretaria"
    elif user.tipo == "tecnico":
        destino = "/tecnico"
    else:
        destino = "/cliente/home"
    return RedirectResponse(url=destino, status_code=303)


@router.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    """Cierra la sesión actual."""
    token = request.cookies.get("mita_session")
    if token:
        sesion = db.query(SesionMita).filter(SesionMita.token == token).first()
        if sesion:
            sesion.activa = False
            sesion.cerrada_at = datetime.utcnow()
            db.commit()
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("mita_session")
    return response


# ============================================
# Dependencias de autenticación
# ============================================

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Devuelve el UsuarioMita de la sesión válida, o None."""
    token = request.cookies.get("mita_session")
    if not token:
        return None
    sesion = (
        db.query(SesionMita)
        .filter(
            SesionMita.token == token,
            SesionMita.activa == True,
            SesionMita.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not sesion:
        return None
    return db.query(UsuarioMita).get(sesion.usuario_id)


async def require_auth(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


async def require_admin(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if user.tipo not in ("admin", "gerente", "secretaria"):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return user


# ============================================
# Reset de clave (admin) — deja la clave = DNI y fuerza cambio
# ============================================

@router.get("/admin/reset-clave/{dni}", response_class=HTMLResponse)
async def reset_clave_form(request: Request, dni: str):
    return templates.TemplateResponse("admin/reset_clave.html", {"request": request, "dni": dni})


@router.post("/admin/reset-clave/{dni}")
async def reset_clave(request: Request, dni: str, db: Session = Depends(get_db)):
    usuario = db.query(UsuarioMita).filter(UsuarioMita.dni == dni).first()
    if not usuario:
        return RedirectResponse(url="/admin/usuarios?reset=notfound", status_code=303)

    usuario.password_hash = hash_password(dni)   # clave = DNI
    usuario.requiere_cambio_clave = True
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.commit()
    return RedirectResponse(url="/admin/usuarios?reset=ok", status_code=303)
