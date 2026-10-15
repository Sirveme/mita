"""Suscripciones Web Push (VAPID) por navegador/dispositivo (zMita-33)."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func

from app.core.database import Base


class PushSuscripcion(Base):
    __tablename__ = "push_suscripciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=True, index=True)   # UsuarioMita.id si hay sesión
    rol = Column(String(20), nullable=True)                   # cliente / tecnico / admin
    solicitud_id = Column(Integer, nullable=True, index=True)
    endpoint = Column(Text, unique=True, nullable=False)      # URL del push service (única)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    plataforma = Column(String(20), nullable=True)            # ios / android / windows / mac / otro
    user_agent = Column(String(400), nullable=True)
    activo = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    ultimo_envio_ok = Column(DateTime, nullable=True)
