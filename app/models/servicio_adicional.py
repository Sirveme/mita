"""Servicios adicionales que el técnico propone y el cliente aprueba/rechaza."""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, func

from app.core.database import Base


class ServicioAdicional(Base):
    __tablename__ = "servicios_adicionales"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), index=True)
    tecnico_id = Column(Integer, ForeignKey("personal.id"))
    descripcion = Column(Text, nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    estado = Column(String(20), default="PENDIENTE")   # PENDIENTE | APROBADO | RECHAZADO
    solicitado_en = Column(DateTime, server_default=func.now())
    respondido_en = Column(DateTime)
