"""
Schemas de autenticación
Ruta: app/schemas/auth.py
"""

from pydantic import BaseModel, validator
from typing import Optional
import re


class LoginRequest(BaseModel):
    """Login con teléfono"""
    identifier: str  # Teléfono
    password: str
    
    @validator('identifier')
    def validate_identifier(cls, v):
        if not v.strip():
            raise ValueError('Teléfono requerido')
        return v.strip()


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    usuario: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('Contraseña debe tener al menos 6 caracteres')
        return v


class CrearCuentaDesdeNumero(BaseModel):
    """Crear cuenta a partir de teléfono existente en solicitud"""
    telefono: str
    password: str
    solicitud_id: Optional[int] = None  # Para vincular solicitudes anteriores
    
    @validator('telefono')
    def validate_telefono(cls, v):
        if not re.match(r'^\d{9}$', v):
            raise ValueError('Teléfono debe tener 9 dígitos')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Contraseña debe tener al menos 6 caracteres')
        return v