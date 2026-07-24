"""
Modelos para solicitudes sin registro
Ruta: app/models/solicitud.py
SIN RELACIONES (para evitar import circular)
"""

from sqlalchemy import Column, Integer, String, Text, DECIMAL, TIMESTAMP, Boolean, ARRAY, ForeignKey, CheckConstraint, Date
from sqlalchemy.sql import func
from app.core.database import Base


class SolicitudServicio(Base):
    __tablename__ = "solicitudes_servicio"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identificación anónima
    device_id = Column(String(100), index=True)
    push_token = Column(Text)
    
    # Datos cliente
    nombre_contacto = Column(String(255), nullable=False)
    telefono_contacto = Column(String(20), nullable=False, index=True)
    direccion_servicio = Column(Text, nullable=False)
    referencias_direccion = Column(Text)
    latitud = Column(DECIMAL(10, 8))
    longitud = Column(DECIMAL(11, 8))
    
    # Vehículo
    marca_vehiculo = Column(String(100))
    modelo_vehiculo = Column(String(100))
    anio_vehiculo = Column(Integer)
    placa_vehiculo = Column(String(20))
    
    # Servicio
    tipo_servicio = Column(String(100), nullable=False)
    descripcion_adicional = Column(Text)

    # --- MITA: catálogo de servicios técnicos ---
    categoria_servicio_id = Column(Integer, ForeignKey('categorias_servicio.id'))
    tipo_servicio_id = Column(Integer, ForeignKey('tipos_servicio.id'))
    descripcion_problema = Column(Text)
    urgencia = Column(String(20), default='normal')   # normal, urgente, programado
    fotos_problema = Column(ARRAY(Text))              # Array de URLs
    
    # Estado
    estado = Column(String(50), default='pendiente', index=True)
    tecnico_asignado_id = Column(Integer, ForeignKey('tecnicos.id'))
    
    # Vinculación posterior
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    
    # Precio
    precio_estimado = Column(DECIMAL(10, 2))
    precio_final = Column(DECIMAL(10, 2))

    # --- MITA: desglose de precio y comisión (visita S/50 = MITA S/15 + técnico S/35) ---
    precio_visita = Column(DECIMAL(10, 2), default=50.00)
    precio_trabajo_adicional = Column(DECIMAL(10, 2), default=0)
    precio_materiales = Column(DECIMAL(10, 2), default=0)
    precio_total = Column(DECIMAL(10, 2), default=50.00)
    comision_mita = Column(DECIMAL(10, 2), default=15.00)
    pago_tecnico = Column(DECIMAL(10, 2), default=35.00)
    
    # Pago
    metodo_pago = Column(String(50))
    estado_pago = Column(String(50), default='pendiente')
    referencia_pago = Column(String(255))
    
    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    fecha_asignacion = Column(TIMESTAMP)
    fecha_inicio = Column(TIMESTAMP)
    fecha_finalizacion = Column(TIMESTAMP)

    # Fecha y hora solicitada
    fecha_servicio = Column(Date, nullable=True)
    hora_servicio = Column(String(10), nullable=True)
    
    # Calificación
    calificacion = Column(Integer)
    comentario_calificacion = Column(Text)
    
    __table_args__ = (
        CheckConstraint('calificacion >= 1 AND calificacion <= 5', name='check_calificacion_range'),
    )


class MensajeChatSolicitud(Base):
    __tablename__ = "mensajes_chat_solicitud"
    
    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey('solicitudes_servicio.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Remitente
    remitente_tipo = Column(String(20), nullable=False)
    remitente_id = Column(Integer)
    remitente_nombre = Column(String(255))
    
    # Mensaje
    tipo_mensaje = Column(String(50), default='texto')
    contenido = Column(Text, nullable=False)
    archivos_urls = Column(ARRAY(Text))
    
    # Estado
    leido = Column(Boolean, default=False)
    fecha_lectura = Column(TIMESTAMP)
    
    # Timestamp
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    
    __table_args__ = (
        CheckConstraint("remitente_tipo IN ('cliente', 'tecnico', 'sistema')", name='check_remitente_tipo'),
        CheckConstraint("tipo_mensaje IN ('texto', 'imagen', 'audio', 'video', 'ubicacion')", name='check_tipo_mensaje'),
    )