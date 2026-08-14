"""
Calificaciones de servicios (1-5 estrellas + aspectos). zMita-13.
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from datetime import datetime

from app.core.database import Base


class Calificacion(Base):
    __tablename__ = "calificaciones"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    tecnico_id = Column(Integer, ForeignKey("personal.id"), nullable=False, index=True)

    estrellas = Column(Integer, nullable=False)
    comentario = Column(Text)

    # Aspectos específicos (opcionales, 1-5)
    puntualidad = Column(Integer)
    calidad_trabajo = Column(Integer)
    precio_justo = Column(Integer)
    amabilidad = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("estrellas BETWEEN 1 AND 5", name="check_estrellas_rango"),
        UniqueConstraint("solicitud_id", name="unique_calificacion_solicitud"),
    )
