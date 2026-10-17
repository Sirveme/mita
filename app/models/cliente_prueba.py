"""Clientes de prueba (modo ensayo, zMita-45 D): por DNI o celular, con monto reducido."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from app.core.database import Base


class ClientePrueba(Base):
    __tablename__ = "clientes_prueba"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(15), index=True)
    celular = Column(String(15), index=True)
    nota = Column(String(200))
    activo = Column(Boolean, default=True)
    creado_por = Column(String(60))
    created_at = Column(DateTime, default=datetime.utcnow)
