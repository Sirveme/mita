"""
API de asignación automática de técnicos. zMita-13.
Expone el AsignacionService (iniciar ronda, aceptar/rechazar alerta).
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.asignacion_service import AsignacionService

router = APIRouter(prefix="/api/v1/asignacion", tags=["Asignación"])


@router.post("/iniciar/{solicitud_id}")
def iniciar(solicitud_id: int, db: Session = Depends(get_db)):
    """Crea la cola de asignación y ejecuta la primera ronda de alertas."""
    try:
        cola = AsignacionService.iniciar_asignacion(db, solicitud_id)
    except ValueError as e:
        return {"exito": False, "mensaje": str(e)}
    resultado = AsignacionService.ejecutar_ronda(db, cola.id)
    return {"cola_id": cola.id, **resultado}


@router.post("/cola/{cola_id}/ronda")
def siguiente_ronda(cola_id: int, db: Session = Depends(get_db)):
    """Ejecuta otra ronda (amplía radio / alerta a más técnicos)."""
    return AsignacionService.ejecutar_ronda(db, cola_id)


@router.post("/alerta/{alerta_id}/aceptar")
def aceptar(alerta_id: int, db: Session = Depends(get_db)):
    return AsignacionService.tecnico_acepta(db, alerta_id)


class Rechazo(BaseModel):
    motivo: Optional[str] = None


@router.post("/alerta/{alerta_id}/rechazar")
def rechazar(alerta_id: int, data: Rechazo = Rechazo(), db: Session = Depends(get_db)):
    return AsignacionService.tecnico_rechaza(db, alerta_id, data.motivo)
