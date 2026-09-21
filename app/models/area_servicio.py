"""Área de servicio (nivel 1 del flujo de solicitud estilo VISA)."""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey

from app.core.database import Base


class AreaServicio(Base):
    __tablename__ = "areas_servicio"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(30), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    categoria_id = Column(Integer, ForeignKey("categorias_servicio.id"))
    imagen_url = Column(String(300))
    icono = Column(String(50))
    color1 = Column(String(10))
    color2 = Column(String(10))
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
