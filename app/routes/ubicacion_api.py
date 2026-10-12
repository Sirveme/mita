"""
Seguimiento en vivo del técnico (tipo Uber).

- POST /api/v1/solicitudes/{id}/ubicacion-tecnico  (técnico): guarda su posición.
- GET  /api/v1/solicitudes/{id}/ubicacion-tecnico  (cliente): la consulta.

El técnico envía su posición cada pocos segundos mientras está EN_CAMINO. El GET
es de sólo lectura por solicitud (igual que /estado y /chats), para que la app
del cliente la muestre en el mapa.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.solicitud_mita import Solicitud
from app.models.ubicacion_tecnico import UbicacionTecnico
from app.routes.comprobantes_api import require_tecnico

logger = logging.getLogger("mita.ubicacion")
router = APIRouter(tags=["Ubicación técnico"])


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


@router.post("/api/v1/solicitudes/{sid}/ubicacion-tecnico")
def actualizar_ubicacion(sid: int, datos: dict = Body(...), db: Session = Depends(get_db),
                         pid: int = Depends(require_tecnico)):
    s = db.query(Solicitud).get(sid)
    if not s:
        raise HTTPException(404, "Solicitud no encontrada")
    if s.tecnico_id != pid:
        raise HTTPException(403, "No autorizado")

    lat, lng = _f(datos.get("lat")), _f(datos.get("lng"))
    if lat is None or lng is None:
        raise HTTPException(400, "lat y lng son obligatorios")

    u = db.query(UbicacionTecnico).filter(UbicacionTecnico.solicitud_id == sid).first()
    if not u:
        u = UbicacionTecnico(solicitud_id=sid, tecnico_id=pid)
        db.add(u)
    u.tecnico_id = pid
    u.lat = lat
    u.lng = lng
    u.precision = _f(datos.get("precision"))
    u.velocidad = _f(datos.get("velocidad"))
    u.rumbo = _f(datos.get("rumbo"))
    u.actualizado_en = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/api/v1/solicitudes/{sid}/ubicacion-tecnico")
def obtener_ubicacion(sid: int, db: Session = Depends(get_db)):
    s = db.query(Solicitud).get(sid)
    if not s:
        raise HTTPException(404, "Solicitud no encontrada")
    u = db.query(UbicacionTecnico).filter(UbicacionTecnico.solicitud_id == sid).first()
    if not u:
        return {"disponible": False}
    antig = None
    if u.actualizado_en:
        antig = int((datetime.utcnow() - u.actualizado_en).total_seconds())
    return {
        "disponible": True,
        "lat": _f(u.lat),
        "lng": _f(u.lng),
        "precision": _f(u.precision),
        "actualizado_en": u.actualizado_en.isoformat() if u.actualizado_en else None,
        "segundos_antiguedad": antig,
    }
