"""Suscripciones Web Push (VAPID) y registro de envíos (zMita-33 / zMita-35)."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func

from app.core.database import Base


class PushSuscripcion(Base):
    __tablename__ = "push_suscripciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=True, index=True)   # UsuarioMita.id si hay sesión
    rol = Column(String(20), nullable=True)                   # cliente / tecnico / admin
    solicitud_id = Column(Integer, nullable=True, index=True)
    dispositivo_id = Column(String(64), nullable=True, index=True)   # id local estable (dedup)
    endpoint = Column(Text, unique=True, nullable=False)      # URL del push service (única)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    plataforma = Column(String(20), nullable=True)            # ios / android / windows / mac / otro
    user_agent = Column(String(400), nullable=True)
    activo = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    ultimo_envio_ok = Column(DateTime, nullable=True)
    # zMita-35: diagnóstico del último envío (para no marcar bajas falsas)
    ultimo_codigo = Column(Integer, nullable=True)            # código HTTP del push service
    ultimo_motivo = Column(String(120), nullable=True)        # texto legible del último resultado
    ultimo_envio_at = Column(DateTime, nullable=True)         # cuándo se intentó el último envío


class PushEnvio(Base):
    """Un registro por (aviso, suscripción) para medir entrega y demora (zMita-35)."""
    __tablename__ = "push_envios"

    id = Column(Integer, primary_key=True, index=True)
    aviso_id = Column(String(40), nullable=False, index=True)
    suscripcion_id = Column(Integer, nullable=True, index=True)
    tag = Column(String(80), nullable=True)
    enviado_en = Column(DateTime, default=func.now(), index=True)
    codigo_http = Column(Integer, nullable=True)
    recibido_en = Column(DateTime, nullable=True)
