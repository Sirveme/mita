"""
API de calificaciones (1-5 estrellas). zMita-13.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.calificacion import Calificacion
from app.models.solicitud_mita import Solicitud
from app.models.personal import Personal

router = APIRouter(prefix="/api/v1/calificaciones", tags=["Calificaciones"])


class CalificacionCreate(BaseModel):
    solicitud_id: int
    estrellas: int = Field(..., ge=1, le=5)
    comentario: Optional[str] = None
    puntualidad: Optional[int] = Field(None, ge=1, le=5)
    calidad_trabajo: Optional[int] = Field(None, ge=1, le=5)
    precio_justo: Optional[int] = Field(None, ge=1, le=5)
    amabilidad: Optional[int] = Field(None, ge=1, le=5)


@router.post("")
def calificar_servicio(data: CalificacionCreate, db: Session = Depends(get_db)):
    """El cliente califica un servicio completado."""
    solicitud = db.query(Solicitud).get(data.solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud.estado not in ("COMPLETADA", "COMPLETADO"):
        raise HTTPException(status_code=400, detail="El servicio aún no está completado")
    if solicitud.calificado:
        raise HTTPException(status_code=400, detail="Este servicio ya fue calificado")

    calificacion = Calificacion(
        solicitud_id=data.solicitud_id,
        cliente_id=solicitud.cliente_id,
        tecnico_id=solicitud.tecnico_id,
        estrellas=data.estrellas,
        comentario=data.comentario,
        puntualidad=data.puntualidad,
        calidad_trabajo=data.calidad_trabajo,
        precio_justo=data.precio_justo,
        amabilidad=data.amabilidad,
    )
    db.add(calificacion)
    solicitud.calificado = True
    db.commit()
    return {"success": True, "mensaje": "¡Gracias por tu calificación!"}


@router.get("/tecnico/{tecnico_id}")
def obtener_rating_tecnico(tecnico_id: int, db: Session = Depends(get_db)):
    """Rating y últimas calificaciones de un técnico."""
    tecnico = db.query(Personal).get(tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    calificaciones = (
        db.query(Calificacion)
        .filter(Calificacion.tecnico_id == tecnico_id)
        .order_by(Calificacion.created_at.desc())
        .limit(10)
        .all()
    )
    nombre = f"{tecnico.nombres} {tecnico.apellido_paterno or ''}".strip()
    return {
        "tecnico_id": tecnico_id,
        "nombre": nombre,
        "rating_promedio": float(tecnico.rating_promedio or 0),
        "total_calificaciones": tecnico.total_calificaciones or 0,
        "ultimas_calificaciones": [
            {"estrellas": c.estrellas, "comentario": c.comentario,
             "fecha": c.created_at.isoformat() if c.created_at else None}
            for c in calificaciones
        ],
    }
