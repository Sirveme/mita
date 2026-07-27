"""
Billeteras electrónicas del personal (Yape, Plin, u OTRA / Open Banking).
Usadas para pagar a técnicos/personal.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime

from app.core.database import Base


class BilleteraPersonal(Base):
    __tablename__ = "billeteras_personal"

    id = Column(Integer, primary_key=True, index=True)
    personal_id = Column(Integer, ForeignKey("personal.id", ondelete="CASCADE"), nullable=False, index=True)

    tipo = Column(String(20), nullable=False)          # YAPE, PLIN, OTRA
    nombre_billetera = Column(String(50))              # solo para tipo OTRA
    numero_celular = Column(String(15), nullable=False)
    titular = Column(String(100))

    activo = Column(Boolean, default=True)
    es_principal = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
