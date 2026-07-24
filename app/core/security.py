"""
Utilidades de seguridad: JWT, hashing, etc.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt

from app.core.config import settings
from app.core.database import get_db
#from app.models.usuario_OLD import Usuario, RefreshToken
from app.models.models import Usuario, SesionUsuario

# Security scheme
security = HTTPBearer(auto_error=False)

# Configuración JWT
SECRET_KEY = settings.SECRET_KEY  # Definir en .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hora
REFRESH_TOKEN_EXPIRE_DAYS = 90  # 90 días



def get_password_hash(password: str) -> str:
    """Hashea una contraseña usando bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que una contraseña coincida con su hash"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un Access Token JWT
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(
    db: Session,
    usuario_id: int,
    dispositivo: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> str:
    """
    Crea un Refresh Token y lo guarda en BD
    """
    # Crear payload
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(usuario_id),
        "exp": expire,
        "type": "refresh"
    }
    
    # Generar token
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # Guardar en BD
    token_db = SesionUsuario(
        usuario_id=usuario_id,
        ip_address=ip_address,
        user_agent=user_agent,
        fecha_fin=expire,
        activa=True
    )
    
    db.add(token_db)
    db.commit()
    
    return token


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    🔧 MODO DEMO: Retorna usuario fake temporalmente
    """
    # Crear objeto fake sin usar modelos
    class FakeCliente:
        id = 999
        usuario_id = 999
    
    class FakeUser:
        id = 999
        email = "demo@serviplus.com"
        nombre = "Usuario"
        apellido = "Demo"
        telefono = "999999999"
        activo = True
        cliente = FakeCliente()
    
    return FakeUser()


def refresh_access_token(refresh_token: str, db: Session) -> dict:
    """
    Genera un nuevo Access Token usando un Refresh Token
    """
    # Decodificar refresh token
    try:
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        
        usuario_id = int(payload.get("sub"))
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado"
        )
    
    # Verificar que el refresh token existe en BD y no está revocado
    token_db = db.query(SesionUsuario).filter(
        SesionUsuario.token == refresh_token
    ).first()
    
    if not token_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no válido"
        )
    
    # Verificar expiración
    if token_db.expira_en < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expirado"
        )
    
    # Actualizar último uso (sliding window)
    token_db.usado_en = datetime.utcnow()
    
    # Extender expiración (opcional - sliding window)
    token_db.expira_en = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    db.commit()
    
    # Generar nuevo access token
    access_token = create_access_token(data={"sub": str(usuario_id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def revoke_refresh_token(token: str, db: Session):
    """
    Revoca un refresh token (logout)
    """
    token_db = db.query(SesionUsuario).filter(
        SesionUsuario.token == token
    ).first()
    
    if token_db:
        token_db.activa = False
        db.commit()


def require_role(allowed_roles: list):
    """
    Decorador para requerir roles específicos
    """
    def role_checker(current_user: Usuario = Depends(get_current_user)):
        if current_user.rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere rol: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker


# Shortcuts para roles específicos
def get_current_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Solo admins"""
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso solo para administradores"
        )
    return current_user


def get_current_tecnico(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Solo técnicos"""
    if current_user.rol != "tecnico":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso solo para técnicos"
        )
    return current_user


def get_current_cliente(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Solo clientes"""
    if current_user.rol != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso solo para clientes"
        )
    return current_user