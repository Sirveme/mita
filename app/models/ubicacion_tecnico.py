"""Ubicación en vivo del técnico durante un servicio (seguimiento tipo Uber)."""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, func, UniqueConstraint

from app.core.database import Base


class UbicacionTecnico(Base):
    __tablename__ = "ubicacion_tecnico"
    __table_args__ = (UniqueConstraint("solicitud_id", name="uq_ubicacion_solicitud"),)

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), index=True)
    tecnico_id = Column(Integer, ForeignKey("personal.id"))
    lat = Column(Numeric(10, 8), nullable=False)
    lng = Column(Numeric(11, 8), nullable=False)
    precision = Column(Numeric(8, 2))
    velocidad = Column(Numeric(8, 2))
    rumbo = Column(Numeric(6, 2))
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())
