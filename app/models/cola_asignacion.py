"""
Cola de asignación automática de técnicos + historial de alertas. zMita-13.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime

from app.core.database import Base


class ColaAsignacion(Base):
    __tablename__ = "cola_asignacion"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id", ondelete="CASCADE"), nullable=False, index=True)

    # PENDIENTE, EN_PROCESO, ASIGNADA, EXPIRADA, CANCELADA
    estado = Column(String(20), default="PENDIENTE", index=True)
    ronda = Column(Integer, default=1)

    tecnicos_alertados = Column(ARRAY(Integer), default=list)
    tecnicos_rechazaron = Column(ARRAY(Integer), default=list)
    tecnicos_timeout = Column(ARRAY(Integer), default=list)

    radio_km = Column(Numeric(5, 2))
    usar_rating = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    ronda_iniciada_at = Column(DateTime)
    expira_at = Column(DateTime)
    asignada_at = Column(DateTime)

    tecnico_asignado_id = Column(Integer, ForeignKey("personal.id"))


class AlertaTecnico(Base):
    __tablename__ = "alertas_tecnico"

    id = Column(Integer, primary_key=True, index=True)
    cola_id = Column(Integer, ForeignKey("cola_asignacion.id", ondelete="CASCADE"), nullable=False)
    tecnico_id = Column(Integer, ForeignKey("personal.id"), nullable=False, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), nullable=False, index=True)

    # ENVIADA, VISTA, ACEPTADA, RECHAZADA, TIMEOUT, NO_SELECCIONADO
    estado = Column(String(20), default="ENVIADA", index=True)

    enviada_at = Column(DateTime, default=datetime.utcnow)
    vista_at = Column(DateTime)
    respondida_at = Column(DateTime)
    expira_at = Column(DateTime)

    distancia_km = Column(Numeric(5, 2))
    rating_tecnico = Column(Numeric(3, 2))
    posicion_en_ronda = Column(Integer)
