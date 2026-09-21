"""Problema específico de servicio (niveles 2-3 del flujo estilo VISA)."""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey

from app.core.database import Base


class ProblemaServicio(Base):
    __tablename__ = "problemas_servicio"

    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas_servicio.id"), index=True)
    tipo = Column(String(20), nullable=False, index=True)   # urgencia | reparacion | instalacion
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    imagen_url = Column(String(300))
    icono = Column(String(50))
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
