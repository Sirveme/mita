"""
Integraciones externas configurables desde el panel de soporte (facturador,
pasarela de pago, etc.) + auditoría de cambios. Las credenciales se guardan
cifradas (Fernet, misma SOL_ENCRYPTION_KEY).
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Integracion(Base):
    __tablename__ = "integraciones"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(30), nullable=False)        # facturador | pasarela
    proveedor = Column(String(50), nullable=False)   # facturalo | nubefact | izipay | ...
    activo = Column(Boolean, default=False)
    modo_sandbox = Column(Boolean, default=True)
    url_produccion = Column(String(300))
    url_sandbox = Column(String(300))
    url_webhook = Column(String(300))
    merchant_id = Column(String(100))
    api_key_encrypted = Column(Text)
    api_secret_encrypted = Column(Text)
    config_json = Column(JSONB, default=dict)
    actualizado_por = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class IntegracionLog(Base):
    __tablename__ = "integraciones_log"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(30))
    proveedor = Column(String(50))
    accion = Column(String(50))          # guardar | activar | probar
    usuario = Column(String(100))
    detalle = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
