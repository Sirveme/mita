"""
Router de chat
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Usuario
# Importar cuando crees los modelos de chat
# from app.models.chat import ConversacionServicio, MensajeChat
# from app.services.chat_service import ChatService
# from app.schemas.chat import ConversacionResponse, MensajeResponse, etc.

router = APIRouter(prefix="/chat")


@router.get("/conversaciones/{servicio_id}")
async def obtener_conversacion(
    servicio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene la conversación de un servicio
    """
    # TODO: Implementar cuando tengas el modelo de chat
    return {"message": "Chat endpoint - Por implementar"}


@router.get("/conversaciones/{conversacion_id}/mensajes")
async def obtener_mensajes(
    conversacion_id: int,
    limite: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene mensajes de una conversación
    """
    # TODO: Implementar
    return {"message": "Mensajes endpoint - Por implementar"}