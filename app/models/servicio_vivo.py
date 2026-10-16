"""Etapas 5 y 6 (zMita-38): ubicación en camino, chat de 3 y presupuesto."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, func

from app.core.database import Base


class UbicacionServicio(Base):
    """Rastro de ubicación del técnico SOLO durante el traslado (se borra a los 30 días)."""
    __tablename__ = "ubicaciones_servicio"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, nullable=False, index=True)
    tecnico_id = Column(Integer, nullable=True)
    lat = Column(Numeric(10, 8), nullable=False)
    lng = Column(Numeric(11, 8), nullable=False)
    precision_m = Column(Numeric(8, 2), nullable=True)
    registrada_en = Column(DateTime, default=func.now(), index=True)


class MensajeServicio(Base):
    """Chat de 3 (cliente, técnico, MITA)."""
    __tablename__ = "mensajes_servicio"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, nullable=False, index=True)
    autor_rol = Column(String(10), nullable=False)       # cliente / tecnico / mita
    autor_id = Column(Integer, nullable=True)
    tipo = Column(String(12), default="texto")           # texto / imagen / tarjeta / sistema
    contenido = Column(Text)                              # texto o JSON (imagen/tarjeta)
    oculto_dato = Column(Boolean, default=False)          # se ocultó un celular/correo
    creado_en = Column(DateTime, default=func.now(), index=True)
    leido_cliente_en = Column(DateTime, nullable=True)
    leido_tecnico_en = Column(DateTime, nullable=True)


class Presupuesto(Base):
    """Diagnóstico + presupuesto del técnico (con versiones)."""
    __tablename__ = "presupuestos"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, nullable=False, index=True)
    version = Column(Integer, default=1)
    diagnostico = Column(Text, nullable=False)
    requiere_reparacion = Column(Boolean, default=False)
    descripcion_trabajo = Column(Text, nullable=True)
    monto = Column(Numeric(10, 2), nullable=True)
    incluye_materiales = Column(Boolean, default=False)
    materiales_detalle = Column(Text, nullable=True)
    tiempo_estimado = Column(String(80), nullable=True)
    fotos = Column(Text, nullable=True)                   # JSON de urls (opcional)
    # propuesto / aceptado / rechazado / reemplazado
    estado = Column(String(14), default="propuesto", index=True)
    decidido_en = Column(DateTime, nullable=True)
    decidido_por = Column(String(60), nullable=True)      # usuario/ip
    ip = Column(String(60), nullable=True)
    ua = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=func.now())
