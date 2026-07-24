"""
Router de notificaciones
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Usuario

router = APIRouter(prefix="/notificaciones")


@router.get("/")
async def obtener_notificaciones(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene notificaciones del usuario
    """
    # TODO: Implementar cuando tengas el modelo de notificaciones
    return {"message": "Notificaciones endpoint - Por implementar"}


@router.get("/no-leidas/contar")
async def contar_no_leidas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Cuenta notificaciones no leídas
    """
    # TODO: Implementar
    return {"count": 0}