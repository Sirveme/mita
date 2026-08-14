"""
Solicitud del flujo MITA v2 (landing → solicitar → técnico → chat).
Tabla `solicitudes` (distinta de `solicitudes_servicio` del flujo anónimo previo).
El técnico se referencia contra `personal.id` (sistema de personal MITA).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from datetime import datetime

from app.core.database import Base


class Solicitud(Base):
    __tablename__ = "solicitudes"

    id = Column(Integer, primary_key=True, index=True)

    # Cliente (puede ser anónimo al inicio)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    cliente_nombre = Column(String(100))
    cliente_telefono = Column(String(15))
    cliente_direccion = Column(String(255))
    cliente_distrito = Column(String(50))
    cliente_referencia = Column(String(255))
    cliente_lat = Column(Float)
    cliente_lng = Column(Float)

    # Servicio
    categoria_id = Column(Integer, ForeignKey("categorias_servicio.id"))
    descripcion_problema = Column(Text)

    # Asignación
    tecnico_id = Column(Integer, ForeignKey("personal.id"))
    secretaria_id = Column(Integer, ForeignKey("personal.id"), nullable=True)

    # Estado: PENDIENTE, ACEPTADA, EN_CAMINO, EN_SERVICIO, COMPLETADA, CANCELADA, RECHAZADA
    estado = Column(String(20), default="PENDIENTE", index=True)

    # Tiempos
    fecha_solicitud = Column(DateTime, default=datetime.utcnow, index=True)
    fecha_aceptacion = Column(DateTime, nullable=True)
    fecha_llegada = Column(DateTime, nullable=True)
    fecha_inicio_servicio = Column(DateTime, nullable=True)
    fecha_fin_servicio = Column(DateTime, nullable=True)

    # Costos
    costo_visita = Column(Float, default=50.0)
    costo_servicio = Column(Float, nullable=True)
    costo_total = Column(Float, nullable=True)

    # Pagos
    metodo_pago = Column(String(20))
    pagado = Column(Integer, default=0)

    # Calificación
    calificacion = Column(Integer, nullable=True)
    comentario = Column(Text, nullable=True)

    # Conversación
    conversacion_id = Column(Integer, ForeignKey("conversaciones.id"), nullable=True)

    # --- zMita-13: catálogo, pago adelantado, cancelación, calificación ---
    tipo_servicio_id = Column(Integer, ForeignKey("tipos_servicio.id"))
    precio_servicio = Column(Float)               # precio fijo o cotizado
    es_precio_fijo = Column(Boolean, default=False)
    pago_adelantado = Column(Boolean, default=False)
    pago_confirmado_at = Column(DateTime, nullable=True)
    metodo_pago = Column(String(20))              # yape, plin, tarjeta, efectivo
    referencia_pago = Column(String(100))
    cancelado = Column(Boolean, default=False)
    cancelado_at = Column(DateTime, nullable=True)
    cancelado_por = Column(String(20))            # cliente, tecnico, sistema
    motivo_cancelacion = Column(Text)
    tarifa_cancelacion = Column(Float)
    calificado = Column(Boolean, default=False)
