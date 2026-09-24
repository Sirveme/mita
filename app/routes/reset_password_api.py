"""
Reset de contraseñas del panel MITA.

La clave reseteada queda IGUAL al DNI del usuario y se marca `requiere_cambio_clave`
para forzar el cambio en el próximo ingreso. Autenticación por UsuarioMita
(bcrypt), la misma que usa el login.

Acceso: admin/gerente (MITA) o soporte (SOTE).
- El admin/gerente NO puede resetear su propia cuenta (evita lockout).
- Soporte puede resetear cualquier cuenta (incluso admin).
- Cada reset se registra en la bitácora (integraciones_log → /soporte/logs).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth_mita import UsuarioMita
from app.models.personal import Personal
from app.models.integracion import IntegracionLog
from app.routes.login_mita import hash_password, get_current_user
from app.routes.soporte import _identidad

logger = logging.getLogger("mita.reset_password")

router = APIRouter(tags=["Reset password"])


async def require_admin_or_soporte(request: Request, db: Session = Depends(get_db)) -> dict:
    """Exige sesión de admin/gerente o de soporte.

    Devuelve un dict con el actor y su rol para la auditoría y la regla de
    'no resetear la propia cuenta'.
    """
    # Soporte primero (maestro por cookie, o usuario con es_soporte=True)
    ident = await _identidad(request, db)          # 'soporte-maestro' | 'usuario:<dni>' | None
    user = await get_current_user(request, db)
    if ident:
        return {"actor": ident, "rol": "soporte", "es_admin": False, "user": user}
    if user and (user.tipo or "").lower() in ("admin", "gerente"):
        return {"actor": f"{user.tipo}:{user.dni}", "rol": user.tipo, "es_admin": True, "user": user}
    raise HTTPException(status_code=403,
                        detail="Solo admin/gerente o soporte pueden resetear contraseñas.",
                        headers={"Location": "/login"})


def _nombre_usuario(db: Session, u: UsuarioMita) -> str:
    nombre = (u.nombres or "").strip()
    if u.personal_id:
        p = db.query(Personal).get(u.personal_id)
        if p:
            nombre = f"{p.nombres} {p.apellido_paterno or ''}".strip()
    return nombre or f"DNI {u.dni}"


@router.post("/api/v1/personal/{dni}/reset-password")
async def reset_password(dni: str, request: Request, db: Session = Depends(get_db),
                         actor: dict = Depends(require_admin_or_soporte)):
    dni = (dni or "").strip()
    usuario = db.query(UsuarioMita).filter(UsuarioMita.dni == dni).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # El admin/gerente no puede resetear su propia cuenta (soporte sí puede)
    if actor["es_admin"] and actor.get("user") and actor["user"].dni == dni:
        raise HTTPException(status_code=403,
                            detail="No puedes resetear tu propia cuenta. Pide a soporte que lo haga.")

    nombre = _nombre_usuario(db, usuario)
    usuario.password_hash = hash_password(dni)      # clave = DNI
    usuario.requiere_cambio_clave = True            # fuerza cambio en el 1er ingreso
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None

    # Auditoría (visible en /soporte/logs)
    db.add(IntegracionLog(
        tipo="seguridad", proveedor="password-reset", accion="reset-password",
        usuario=actor["actor"],
        detalle=f"Reseteó la clave de {nombre} (DNI {dni}) a su DNI. Cambio obligatorio en el próximo ingreso.",
    ))
    db.commit()
    logger.info("RESET_PASSWORD dni=%s por=%s (%s)", dni, actor["actor"], actor["rol"])

    return {
        "success": True,
        "mensaje": "Contraseña reseteada. Nueva contraseña: el DNI del usuario.",
        "dni": dni,
        "nombre": nombre,
    }
