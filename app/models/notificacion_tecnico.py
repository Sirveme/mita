"""Notificaciones de solicitud a técnicos (aceptar/rechazar/timeout)."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.core.database import Base


class NotificacionTecnico(Base):
    __tablename__ = "notificaciones_tecnico"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), index=True)
    tecnico_id = Column(Integer, ForeignKey("personal.id"), index=True)
    notificado_en = Column(DateTime, server_default=func.now())
    respondido_en = Column(DateTime)
    respuesta = Column(String(20))          # aceptada | rechazada | timeout
    tiempo_respuesta_seg = Column(Integer)
