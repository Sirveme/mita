"""
Schemas Pydantic para Notificaciones
"""

from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class NotificacionResponse(BaseModel):
    id: int
    usuario_id: int
    tipo: str
    canal: str
    titulo: str
    mensaje: str
    metadata: Optional[Dict]
    estado: str
    es_urgente: bool
    prioridad: int
    accion_url: Optional[str]
    accion_tipo: Optional[str]
    creada_en: datetime
    leida_en: Optional[datetime]
    
    class Config:
        from_attributes = True