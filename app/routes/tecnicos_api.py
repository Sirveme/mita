"""
API de técnicos disponibles para el selector del cliente (MITA v2).
GET /api/v1/tecnicos/disponibles?categoria_id=..&lat=..&lng=..

Adaptado al esquema real: Personal (datos base) + TecnicoPersonal (estado,
especialidades ARRAY de categoria_id, stats, última ubicación).
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.personal import Personal, TecnicoPersonal, TipoPersonal, EstadoPersonal
from app.models.models import CategoriaServicio

router = APIRouter(prefix="/api/v1/tecnicos", tags=["Tecnicos MITA"])


@router.get("/disponibles")
def tecnicos_disponibles(
    categoria_id: int = Query(...),
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    db: Session = Depends(get_db),
):
    """Técnicos activos con la especialidad pedida, ordenados por tiempo de llegada."""
    cat = db.query(CategoriaServicio).get(categoria_id)
    cat_nombre = cat.nombre if cat else "General"

    filas = (
        db.query(Personal, TecnicoPersonal)
        .join(TecnicoPersonal, TecnicoPersonal.personal_id == Personal.id)
        .filter(
            Personal.tipo == TipoPersonal.TECNICO,
            Personal.estado == EstadoPersonal.ACTIVO,
        )
        .all()
    )

    resultado = []
    for p, t in filas:
        # Filtrar por especialidad en Python (especialidades es ARRAY de categoria_id)
        if not t.especialidades or categoria_id not in t.especialidades:
            continue
        tiempo_llegada = 30
        if lat is not None and lng is not None and t.ultima_ubicacion_lat and t.ultima_ubicacion_lng:
            dist = ((float(t.ultima_ubicacion_lat) - lat) ** 2 + (float(t.ultima_ubicacion_lng) - lng) ** 2) ** 0.5
            tiempo_llegada = int(15 + dist * 100)

        # Experiencia estimada desde la fecha de ingreso
        anios = 1
        if p.fecha_ingreso:
            anios = max(1, (datetime.utcnow().date() - p.fecha_ingreso).days // 365)

        resultado.append({
            "id": p.id,
            "nombre": f"{p.nombres} {p.apellido_paterno}".strip(),
            "especialidad": cat_nombre,
            "foto": p.foto_url,
            "rating": float(t.calificacion_promedio or 5.0),
            "servicios": t.total_servicios or 0,
            "experiencia": f"{anios} año{'s' if anios > 1 else ''}",
            "tiempo_llegada": tiempo_llegada,
            "estado": t.estado_actual.value if t.estado_actual else "disponible",
        })

    resultado.sort(key=lambda x: x["tiempo_llegada"])
    return resultado


class UbicacionTecnico(BaseModel):
    lat: float
    lng: float
    tecnico_id: Optional[int] = None      # TecnicoPersonal.id
    solicitud_id: Optional[int] = None


@router.post("/ubicacion")
def actualizar_ubicacion(data: UbicacionTecnico, db: Session = Depends(get_db)):
    """Actualiza la última ubicación del técnico (tracking en tiempo real)."""
    if data.tecnico_id:
        t = db.query(TecnicoPersonal).get(data.tecnico_id)
        if t:
            t.ultima_ubicacion_lat = data.lat
            t.ultima_ubicacion_lng = data.lng
            t.ultima_ubicacion_at = datetime.utcnow()
            db.commit()
    return {"success": True}
