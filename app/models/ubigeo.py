"""
Ubigeos del Perú (códigos INEI: DDPPDD).
Referenciado opcionalmente por `distritos.ubigeo_id`.
"""

from sqlalchemy import Column, Integer, String, Boolean

from app.core.database import Base


class Ubigeo(Base):
    __tablename__ = "ubigeos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(6), unique=True, nullable=False, index=True)  # DDPPDD
    departamento = Column(String(50), nullable=False, index=True)
    provincia = Column(String(50), nullable=False)
    distrito = Column(String(50), nullable=False, index=True)
    activo = Column(Boolean, default=True)
