from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()

@router.get("/")
async def listar_servicios(db: Session = Depends(get_db)):
    """Listar todos los servicios"""
    # TODO: Implementar lógica
    return {"servicios": []}

@router.get("/{servicio_id}")
async def obtener_servicio(servicio_id: int, db: Session = Depends(get_db)):
    """Obtener servicio por ID"""
    # TODO: Implementar lógica
    return {"servicio_id": servicio_id}

@router.post("/solicitar")
async def solicitar_servicio(db: Session = Depends(get_db)):
    """Cliente solicita un nuevo servicio"""
    # TODO: Implementar lógica
    return {"message": "Servicio solicitado", "servicio_id": 1}

@router.post("/{servicio_id}/aceptar")
async def aceptar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    """Técnico acepta un servicio"""
    # TODO: Implementar lógica
    return {"message": "Servicio aceptado"}

@router.post("/{servicio_id}/completar")
async def completar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    """Marcar servicio como completado"""
    # TODO: Implementar lógica
    return {"message": "Servicio completado"}

@router.post("/{servicio_id}/calificar")
async def calificar_servicio(servicio_id: int, db: Session = Depends(get_db)):
    """Cliente califica el servicio"""
    # TODO: Implementar lógica
    return {"message": "Servicio calificado"}