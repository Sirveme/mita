"""
Lista de espera por distrito: clientes de zonas aún no habilitadas que dejan
su contacto para avisarles cuando MITA llegue a su distrito.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func

from app.core.database import Base


class WaitlistDistrito(Base):
    __tablename__ = "waitlist_distrito"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    telefono = Column(String(20))
    distrito_id = Column(Integer, ForeignKey("distritos.id"), index=True)
    distrito_nombre = Column(String(100))
    categoria_interes = Column(String(50))     # ELEC, GASF, ELDOM, ...
    mensaje = Column(Text)
    notificado = Column(Boolean, default=False, index=True)
    creado_en = Column(DateTime, server_default=func.now())
