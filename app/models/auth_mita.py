"""
Modelos de autenticación del panel MITA (login por DNI + sesiones por cookie).

Tablas propias (usuarios_mita / sesiones_mita) independientes del `Usuario`
legacy (JWT API) y del `Personal`. Enlazable a `personal.id` vía personal_id.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class UsuarioMita(Base):
    """Usuario del panel (login con DNI + contraseña)."""
    __tablename__ = "usuarios_mita"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(15), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    # admin | gerente | secretaria | tecnico | cliente
    tipo = Column(String(20), nullable=False, default="admin")

    nombres = Column(String(150))
    email = Column(String(150))
    personal_id = Column(Integer)  # enlace opcional a personal.id
    cliente_id = Column(Integer)   # enlace opcional a clientes.id

    activo = Column(Boolean, default=True)
    verificado = Column(Boolean, default=False)
    requiere_cambio_clave = Column(Boolean, default=False)  # fuerza cambio en 1er login

    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta = Column(DateTime)
    ultimo_acceso = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sesiones = relationship("SesionMita", back_populates="usuario")


class SesionMita(Base):
    """Sesión activa por cookie (token opaco)."""
    __tablename__ = "sesiones_mita"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios_mita.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    ip = Column(String(64))
    user_agent = Column(String(500))
    activa = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    cerrada_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("UsuarioMita", back_populates="sesiones")
