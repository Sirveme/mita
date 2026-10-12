"""
API de integración con Google Maps (zMita-15).

- GET    /api/v1/maps/config                              -> API key para el frontend
- POST   /api/v1/maps/solicitudes/{id}/direccion          -> guarda la dirección validada
- POST   /api/v1/maps/solicitudes/{id}/ubicacion-tecnico  -> el técnico envía su GPS
- GET    /api/v1/maps/solicitudes/{id}/ubicacion-tecnico  -> el cliente consulta la ubicación
- DELETE /api/v1/maps/solicitudes/{id}/ubicacion-tecnico  -> limpia el tracking al terminar

Comparte la tabla `ubicacion_tecnico` y el modelo con ubicacion_api.py.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.solicitud_mita import Solicitud
from app.models.ubicacion_tecnico import UbicacionTecnico
from app.models.solicitud_sin_cobertura import SolicitudSinCobertura
from app.routes.comprobantes_api import require_tecnico
from app.routes.admin_postulantes import require_admin_gerente

logger = logging.getLogger("mita.maps")
router = APIRouter(prefix="/api/v1/maps", tags=["Maps"])


class UbicacionInput(BaseModel):
    lat: float
    lng: float
    precision: Optional[float] = None
    velocidad: Optional[float] = None
    rumbo: Optional[float] = None


class DireccionInput(BaseModel):
    direccion_completa: str
    lat: float
    lng: float
    distrito: Optional[str] = None
    referencia: Optional[str] = None


class SinCoberturaInput(BaseModel):
    distrito_solicitado: str
    direccion_ingresada: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    area_servicio_id: Optional[int] = None
    problema_id: Optional[int] = None
    descripcion: Optional[str] = None


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


@router.get("/config")
async def obtener_config_maps():
    """API key para el frontend (la clave está restringida por dominio en GCP)."""
    if not settings.GOOGLE_MAPS_API_KEY:
        raise HTTPException(503, "Google Maps no configurado")
    return {"api_key": settings.GOOGLE_MAPS_API_KEY, "pais": "pe", "region": "Lima"}


@router.post("/solicitudes/{solicitud_id}/direccion")
async def guardar_direccion(solicitud_id: int, datos: DireccionInput, db: Session = Depends(get_db)):
    """Guarda la dirección validada por Google en la solicitud."""
    s = db.query(Solicitud).get(solicitud_id)
    if not s:
        raise HTTPException(404, "Solicitud no encontrada")
    s.direccion_completa = datos.direccion_completa
    s.cliente_direccion = s.cliente_direccion or datos.direccion_completa
    if datos.distrito:
        s.cliente_distrito = datos.distrito
    if datos.referencia is not None:
        s.cliente_referencia = datos.referencia
    s.cliente_lat = datos.lat
    s.cliente_lng = datos.lng
    s.direccion_validada = True
    db.commit()
    return {"ok": True, "mensaje": "Dirección guardada"}


@router.post("/solicitudes/{solicitud_id}/ubicacion-tecnico")
async def actualizar_ubicacion_tecnico(solicitud_id: int, datos: UbicacionInput,
                                       db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    """El técnico envía su ubicación GPS. Solo el técnico asignado a la solicitud."""
    s = db.query(Solicitud).get(solicitud_id)
    if not s:
        raise HTTPException(404, "Solicitud no encontrada")
    if s.tecnico_id != pid:
        raise HTTPException(403, "No autorizado")
    u = db.query(UbicacionTecnico).filter(UbicacionTecnico.solicitud_id == solicitud_id).first()
    if not u:
        u = UbicacionTecnico(solicitud_id=solicitud_id, tecnico_id=pid)
        db.add(u)
    u.tecnico_id = pid
    u.lat = datos.lat
    u.lng = datos.lng
    u.precision = datos.precision
    u.velocidad = datos.velocidad
    u.rumbo = datos.rumbo
    u.actualizado_en = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/solicitudes/{solicitud_id}/ubicacion-tecnico")
async def obtener_ubicacion_tecnico(solicitud_id: int, db: Session = Depends(get_db)):
    """El cliente consulta la ubicación actual del técnico."""
    u = db.query(UbicacionTecnico).filter(UbicacionTecnico.solicitud_id == solicitud_id).first()
    if not u:
        return {"disponible": False}
    antig = int((datetime.utcnow() - u.actualizado_en).total_seconds()) if u.actualizado_en else None
    return {
        "disponible": True,
        "lat": _f(u.lat), "lng": _f(u.lng),
        "precision": _f(u.precision), "velocidad": _f(u.velocidad), "rumbo": _f(u.rumbo),
        "actualizado_en": u.actualizado_en.isoformat() if u.actualizado_en else None,
        "segundos_antiguedad": antig,
    }


@router.post("/sin-cobertura")
async def registrar_sin_cobertura(datos: SinCoberturaInput, db: Session = Depends(get_db)):
    """Registra un intento de solicitud en un distrito sin cobertura (análisis de expansión)."""
    reg = SolicitudSinCobertura(
        distrito_solicitado=datos.distrito_solicitado.strip(),
        direccion_ingresada=datos.direccion_ingresada,
        lat=datos.lat, lng=datos.lng,
        area_servicio_id=datos.area_servicio_id,
        problema_id=datos.problema_id,
        descripcion=datos.descripcion,
    )
    db.add(reg); db.commit()
    logger.info("Sin cobertura registrado: %s", datos.distrito_solicitado)
    return {"ok": True, "mensaje": "Registrado para futura expansión"}


@router.get("/sin-cobertura/estadisticas")
async def estadisticas_sin_cobertura(db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    """Distritos más solicitados sin cobertura (panel admin)."""
    from sqlalchemy import func as sqlfunc
    rows = (db.query(
                SolicitudSinCobertura.distrito_solicitado.label("distrito"),
                sqlfunc.count(SolicitudSinCobertura.id).label("solicitudes"),
                sqlfunc.min(SolicitudSinCobertura.creado_en).label("primera"),
                sqlfunc.max(SolicitudSinCobertura.creado_en).label("ultima"),
            )
            .group_by(SolicitudSinCobertura.distrito_solicitado)
            .order_by(sqlfunc.count(SolicitudSinCobertura.id).desc())
            .limit(20).all())
    return [
        {"distrito": r.distrito, "solicitudes": r.solicitudes,
         "primera": r.primera.isoformat() if r.primera else None,
         "ultima": r.ultima.isoformat() if r.ultima else None}
        for r in rows
    ]


@router.delete("/solicitudes/{solicitud_id}/ubicacion-tecnico")
async def eliminar_ubicacion_tecnico(solicitud_id: int, db: Session = Depends(get_db),
                                     pid: int = Depends(require_tecnico)):
    """Elimina el tracking cuando el servicio termina (solo el técnico asignado)."""
    s = db.query(Solicitud).get(solicitud_id)
    if s and s.tecnico_id != pid:
        raise HTTPException(403, "No autorizado")
    db.query(UbicacionTecnico).filter(UbicacionTecnico.solicitud_id == solicitud_id).delete()
    db.commit()
    return {"ok": True}
