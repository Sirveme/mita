"""Historial de cambios del catálogo (precios, servicios, distritos, políticas) — zMita-23."""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.core.database import Base


class CatalogoHistorial(Base):
    __tablename__ = "catalogo_historial"

    id = Column(Integer, primary_key=True, index=True)
    entidad = Column(String(50), index=True)        # categorias | tarifas | distritos | config_mita | chat_conocimiento
    entidad_id = Column(String(60))                 # id o clave
    campo = Column(String(80))
    valor_anterior = Column(Text)
    valor_nuevo = Column(Text)
    usuario_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), index=True)
