"""
Routes de autenticación
Ruta: app/routes/auth.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    revoke_refresh_token,
    get_current_user,
    verify_password,
    get_password_hash
)
from app.models.models import Usuario, Cliente
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    ChangePasswordRequest,
    CrearCuentaDesdeNumero
)

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login con TELÉFONO"""
    
    usuario = db.query(Usuario).filter(
        Usuario.telefono_principal == credentials.identifier
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Teléfono no registrado"
        )
    
    if not verify_password(credentials.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta"
        )
    
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    usuario.ultimo_acceso = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": str(usuario.id)},
        expires_delta=timedelta(days=7)
    )
    
    refresh_token = None
    try:
        refresh_token = create_refresh_token(
            db=db,
            usuario_id=usuario.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
    except Exception:
        pass
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "telefono": usuario.telefono_principal,
            "nombre_completo": usuario.nombre_completo,
            "rol": str(usuario.rol),
            "email": usuario.email
        }
    }


@router.post("/crear-cuenta", response_model=LoginResponse)
async def crear_cuenta_desde_numero(
    data: CrearCuentaDesdeNumero,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Crear cuenta a partir de teléfono usado en solicitud
    Vincula solicitudes anteriores
    """
    
    # Verificar que no exista
    if db.query(Usuario).filter(Usuario.telefono_principal == data.telefono).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este teléfono ya tiene cuenta"
        )
    
    # Buscar nombre del teléfono en solicitudes
    from app.models.solicitud import SolicitudServicio
    solicitud_previa = db.query(SolicitudServicio).filter(
        SolicitudServicio.telefono_contacto == data.telefono
    ).first()
    
    nombre = solicitud_previa.nombre_contacto if solicitud_previa else "Usuario"
    
    # Crear usuario
    usuario = Usuario(
        telefono_principal=data.telefono,
        password_hash=get_password_hash(data.password),
        nombre_completo=nombre,
        email=f"{data.telefono}@serviplus.temp",
        rol='cliente',
        activo=True,
        acepto_terminos=True,
        primer_login=False
    )
    
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    
    # Crear registro cliente
    cliente = Cliente(usuario_id=usuario.id)
    db.add(cliente)
    
    # Vincular solicitudes anteriores
    if solicitud_previa:
        db.query(SolicitudServicio).filter(
            SolicitudServicio.telefono_contacto == data.telefono,
            SolicitudServicio.usuario_id.is_(None)
        ).update({"usuario_id": usuario.id})
    
    db.commit()
    
    # Token
    access_token = create_access_token(
        data={"sub": str(usuario.id)},
        expires_delta=timedelta(days=7)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "telefono": usuario.telefono_principal,
            "nombre_completo": usuario.nombre_completo,
            "rol": str(usuario.rol)
        }
    }


@router.post("/refresh")
async def refresh_token(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_db)
):
    """Refresca access token"""
    try:
        result = refresh_access_token(refresh_data.refresh_token, db)
        return result
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


@router.post("/logout")
async def logout(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cierra sesión"""
    try:
        revoke_refresh_token(refresh_data.refresh_token, db)
    except Exception:
        pass
    return {"message": "Sesión cerrada"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cambia contraseña"""
    
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Contraseña actualizada"}


@router.get("/me")
async def get_current_user_info(
    current_user: Usuario = Depends(get_current_user)
):
    """Info usuario actual"""
    return {
        "id": current_user.id,
        "telefono": current_user.telefono_principal,
        "whatsapp": current_user.whatsapp,
        "nombre_completo": current_user.nombre_completo,
        "email": current_user.email,
        "rol": str(current_user.rol),
        "activo": current_user.activo,
        "verificado_telefono": current_user.verificado_telefono,
        "foto": current_user.foto_perfil_url
    }