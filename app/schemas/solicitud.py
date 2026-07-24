from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ============================================
# SCHEMAS PARA SOLICITUDES DE SERVICIO
# ============================================

class SolicitudServicioCreate(BaseModel):
    """Schema para CREAR solicitud - SOLO campos que existen en BD"""
    
    # Identificación (sin login)
    device_id: str
    push_token: Optional[str] = None
    
    # Contacto
    nombre_contacto: str = Field(..., min_length=2)
    telefono_contacto: str = Field(..., pattern=r'^9\d{8}$')
    
    # Ubicación
    direccion_servicio: str = Field(..., min_length=5)
    referencias_direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    
    # Tipo de servicio
    tipo_servicio: str = "cambio_aceite"
    descripcion_adicional: Optional[str] = None
    
    # Vehículo
    marca_vehiculo: Optional[str] = None
    modelo_vehiculo: Optional[str] = None
    anio_vehiculo: Optional[int] = None
    placa_vehiculo: Optional[str] = None
    
    # Fecha/hora (opcional en creación)
    fecha_servicio: Optional[datetime] = None
    hora_servicio: Optional[str] = None
    
    # Precio
    precio_estimado: Optional[float] = None
    
    # Método de pago
    metodo_pago: Optional[str] = None
    
    class Config:
        from_attributes = True


class SolicitudServicioResponse(BaseModel):
    """Schema para respuesta de solicitud"""
    id: int
    device_id: str
    nombre_contacto: str
    telefono_contacto: str
    direccion_servicio: str
    tipo_servicio: str
    estado: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SolicitudDetalle(BaseModel):
    """Schema detallado de solicitud con técnico"""
    id: int
    device_id: str
    nombre_contacto: str
    telefono_contacto: str
    direccion_servicio: str
    referencias_direccion: Optional[str] = None
    tipo_servicio: str
    descripcion_adicional: Optional[str] = None
    
    # Vehículo
    marca_vehiculo: Optional[str] = None
    modelo_vehiculo: Optional[str] = None
    anio_vehiculo: Optional[int] = None
    placa_vehiculo: Optional[str] = None
    
    # Fecha/hora
    fecha_servicio: Optional[datetime] = None
    hora_servicio: Optional[str] = None
    
    # Estado
    estado: str
    tecnico_asignado_id: Optional[int] = None
    
    # Precio
    precio_estimado: Optional[float] = None
    precio_final: Optional[float] = None
    
    # Pago
    metodo_pago: Optional[str] = None
    estado_pago: Optional[str] = None
    referencia_pago: Optional[str] = None
    
    # Calificación
    calificacion: Optional[int] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MensajeChatCreate(BaseModel):
    """Schema para crear mensaje de chat"""
    solicitud_id: int
    remitente_tipo: str  # 'cliente', 'tecnico', 'admin'
    remitente_id: Optional[int] = None
    remitente_nombre: str
    tipo_mensaje: str = 'texto'
    contenido: str
    archivos_urls: Optional[list[str]] = None


class MensajeChatResponse(BaseModel):
    """Schema para respuesta de mensaje"""
    id: int
    solicitud_id: int
    remitente_tipo: str
    remitente_nombre: str
    contenido: str
    created_at: datetime
    leido: bool
    
    class Config:
        from_attributes = True