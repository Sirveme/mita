"""
Schemas Pydantic para Chat
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConversacionResponse(BaseModel):
    id: int
    servicio_id: int
    cliente_id: int
    tecnico_id: int
    estado: str
    total_mensajes: int
    no_leidos_cliente: int
    no_leidos_tecnico: int
    creada_en: datetime
    ultimo_mensaje_en: Optional[datetime]
    
    class Config:
        from_attributes = True


class MensajeCreate(BaseModel):
    contenido: str
    respondiendo_a: Optional[int] = None


class MensajeResponse(BaseModel):
    id: int
    conversacion_id: int
    emisor_id: int
    rol_emisor: str
    tipo: str
    contenido: str
    archivo_url: Optional[str]
    archivo_nombre: Optional[str]
    latitud: Optional[str]
    longitud: Optional[str]
    direccion: Optional[str]
    enviado: bool
    entregado: bool
    leido: bool
    creado_en: datetime
    entregado_en: Optional[datetime]
    leido_en: Optional[datetime]
    
    class Config:
        from_attributes = True


class ReporteCreate(BaseModel):
    mensaje_id: Optional[int]
    usuario_reportado_id: int
    razon: str
    descripcion: str