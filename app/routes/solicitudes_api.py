"""
API para crear solicitudes del flujo MITA v2.
POST /api/v1/solicitudes  (bare) — NO colisiona con solicitudes.py (usa /crear, /{id}...).
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.solicitud_mita import Solicitud
from app.models.personal import Personal, EstadoPersonal
from app.models.models import CategoriaServicio

router = APIRouter(prefix="/api/v1/solicitudes", tags=["Solicitudes MITA"])


class SolicitudCreate(BaseModel):
    problema: str
    categoria_id: int
    tecnico_id: Optional[int] = None          # None = asignación automática (zMita-13)
    direccion: str
    distrito: Optional[str] = None
    referencia: Optional[str] = None
    telefono: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    # zMita-13: catálogo + pago adelantado
    tipo_servicio_id: Optional[int] = None
    precio_servicio: Optional[float] = None
    es_precio_fijo: Optional[bool] = False
    metodo_pago: Optional[str] = None
    referencia_pago: Optional[str] = None
    pago_adelantado: Optional[bool] = False


@router.post("")
def crear_solicitud(data: SolicitudCreate, db: Session = Depends(get_db)):
    """Crea una solicitud. Si viene tecnico_id, se asigna directo; si no, queda
    PENDIENTE para la asignación automática (POST /api/v1/asignacion/iniciar/{id})."""
    asignada = False
    if data.tecnico_id is not None:
        tecnico = (
            db.query(Personal)
            .filter(Personal.id == data.tecnico_id, Personal.estado == EstadoPersonal.ACTIVO)
            .first()
        )
        if not tecnico:
            raise HTTPException(status_code=404, detail="Técnico no disponible")
        asignada = True

    solicitud = Solicitud(
        descripcion_problema=data.problema,
        categoria_id=data.categoria_id,
        tecnico_id=data.tecnico_id,
        cliente_direccion=data.direccion,
        cliente_distrito=data.distrito,
        cliente_referencia=data.referencia,
        cliente_telefono=data.telefono,
        cliente_lat=data.lat,
        cliente_lng=data.lng,
        estado="ASIGNADA" if asignada else "PENDIENTE",
        fecha_solicitud=datetime.utcnow(),
        costo_visita=50.0,
        # zMita-13
        tipo_servicio_id=data.tipo_servicio_id,
        precio_servicio=data.precio_servicio,
        es_precio_fijo=bool(data.es_precio_fijo),
        metodo_pago=data.metodo_pago,
        referencia_pago=data.referencia_pago,
        pago_adelantado=bool(data.pago_adelantado),
        pago_confirmado_at=datetime.utcnow() if data.pago_adelantado else None,
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return {
        "success": True,
        "id": solicitud.id,
        "estado": solicitud.estado,
        "mensaje": "Solicitud creada." + (" Técnico asignado." if asignada else " Buscando técnico..."),
    }


# ============================================
# Lista / asignación / respuesta / estado (panel secretaria + técnico)
# ============================================

@router.get("/estado/{solicitud_id}")
def estado_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    """Estado de una solicitud del flujo v2 (usado por el chat para el modal de calificación)."""
    s = db.query(Solicitud).get(solicitud_id)
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    tecnico_nombre = None
    if s.tecnico_id:
        tec = db.query(Personal).get(s.tecnico_id)
        if tec:
            tecnico_nombre = f"{tec.nombres} {tec.apellido_paterno or ''}".strip()
    return {
        "id": s.id,
        "estado": s.estado,
        "calificado": bool(s.calificado),
        "tecnico_id": s.tecnico_id,
        "tecnico_nombre": tecnico_nombre,
        "tecnico_foto": None,
    }


@router.get("")
def listar_solicitudes(estado: Optional[str] = None, db: Session = Depends(get_db)):
    """Lista solicitudes (opcionalmente por estado). Usado por el panel de secretaria."""
    q = db.query(Solicitud).order_by(Solicitud.fecha_solicitud.desc())
    if estado:
        q = q.filter(Solicitud.estado == estado)
    solicitudes = q.limit(50).all()

    cats = {c.id: c.nombre for c in db.query(CategoriaServicio).all()}
    return [
        {
            "id": s.id,
            "descripcion_problema": s.descripcion_problema,
            "categoria": cats.get(s.categoria_id, "General"),
            "categoria_id": s.categoria_id,
            "cliente_nombre": s.cliente_nombre,
            "cliente_telefono": s.cliente_telefono,
            "cliente_direccion": s.cliente_direccion,
            "cliente_distrito": s.cliente_distrito,
            "cliente_referencia": s.cliente_referencia,
            "estado": s.estado,
            "tecnico_id": s.tecnico_id,
            "fecha_solicitud": s.fecha_solicitud.isoformat() if s.fecha_solicitud else None,
        }
        for s in solicitudes
    ]


class AsignarTecnico(BaseModel):
    tecnico_id: int


@router.post("/{solicitud_id}/asignar")
def asignar_tecnico(solicitud_id: int, data: AsignarTecnico, db: Session = Depends(get_db)):
    """La secretaria asigna un técnico a la solicitud (queda ASIGNADA, 90s para aceptar)."""
    solicitud = db.query(Solicitud).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    tecnico = (
        db.query(Personal)
        .filter(Personal.id == data.tecnico_id, Personal.estado == EstadoPersonal.ACTIVO)
        .first()
    )
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no disponible")

    solicitud.tecnico_id = data.tecnico_id
    solicitud.estado = "ASIGNADA"
    db.commit()
    # TODO (zMita-11): notificar al técnico vía WebSocket
    return {"success": True, "mensaje": "Técnico asignado. Tiene 90 segundos para responder."}


class RespuestaTecnico(BaseModel):
    aceptada: bool
    razon: Optional[str] = None


@router.post("/{solicitud_id}/respuesta")
def respuesta_tecnico(solicitud_id: int, data: RespuestaTecnico, db: Session = Depends(get_db)):
    """El técnico acepta (→ EN_CAMINO) o rechaza (→ PENDIENTE, se libera para reasignar)."""
    solicitud = db.query(Solicitud).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if data.aceptada:
        solicitud.estado = "EN_CAMINO"
        solicitud.fecha_aceptacion = datetime.utcnow()
        mensaje = "Solicitud aceptada. El técnico está en camino."
    else:
        solicitud.tecnico_id = None
        solicitud.estado = "PENDIENTE"
        mensaje = "Solicitud rechazada. Se buscará otro técnico."
    db.commit()
    return {"success": True, "mensaje": mensaje}


class CambioEstado(BaseModel):
    estado: str


@router.put("/{solicitud_id}/estado")
def cambiar_estado(solicitud_id: int, data: CambioEstado, db: Session = Depends(get_db)):
    """Actualiza el estado del servicio (EN_CAMINO → LLEGADA → EN_SERVICIO → COMPLETADO)."""
    solicitud = db.query(Solicitud).get(solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    solicitud.estado = data.estado
    ahora = datetime.utcnow()
    if data.estado == "LLEGADA":
        solicitud.fecha_llegada = ahora
    elif data.estado == "EN_SERVICIO":
        solicitud.fecha_inicio_servicio = ahora
    elif data.estado == "COMPLETADO":
        solicitud.fecha_fin_servicio = ahora
    db.commit()
    return {"success": True, "estado": data.estado}
