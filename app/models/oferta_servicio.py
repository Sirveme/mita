"""Oferta de un servicio a un técnico (etapa 4, zMita-37). Una fila por técnico notificado."""
from sqlalchemy import Column, Integer, String, DateTime, func

from app.core.database import Base


class OfertaServicio(Base):
    __tablename__ = "ofertas_servicio"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, nullable=False, index=True)
    tecnico_id = Column(Integer, nullable=False, index=True)   # Personal.id
    enviada_en = Column(DateTime, default=func.now())
    vista_en = Column(DateTime, nullable=True)
    # aceptada / no_puedo / tomada_por_otro / vencida  (None = sin responder)
    respuesta = Column(String(20), nullable=True)
    respondida_en = Column(DateTime, nullable=True)
    intento = Column(Integer, default=1)
