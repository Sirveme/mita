"""Registro de intentos de solicitud en distritos sin cobertura (zMita-16)."""
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func

from app.core.database import Base


class SolicitudSinCobertura(Base):
    __tablename__ = "solicitudes_sin_cobertura"

    id = Column(Integer, primary_key=True, index=True)
    distrito_solicitado = Column(String(100), nullable=False, index=True)
    direccion_ingresada = Column(Text)
    lat = Column(Numeric(10, 8))
    lng = Column(Numeric(11, 8))
    cliente_id = Column(Integer, ForeignKey("personal.id"))
    area_servicio_id = Column(Integer)
    problema_id = Column(Integer)
    descripcion = Column(Text)
    creado_en = Column(DateTime, server_default=func.now(), index=True)
