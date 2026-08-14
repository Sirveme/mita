"""
API del cliente (MITA). zMita-14.
Servicios completados pendientes de calificar.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.solicitud_mita import Solicitud
from app.models.personal import Personal
from app.models.models import CategoriaServicio

router = APIRouter(prefix="/api/v1/cliente", tags=["Cliente"])


@router.get("/servicios-pendientes-calificar")
def servicios_pendientes_calificar(cliente_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Servicios completados que el cliente aún no calificó (máx. 5)."""
    if not cliente_id:
        return []  # TODO: obtener cliente_id de la sesión (auth)

    filas = (
        db.query(Solicitud, Personal, CategoriaServicio)
        .outerjoin(Personal, Personal.id == Solicitud.tecnico_id)
        .outerjoin(CategoriaServicio, CategoriaServicio.id == Solicitud.categoria_id)
        .filter(
            and_(
                Solicitud.cliente_id == cliente_id,
                or_(Solicitud.estado == "COMPLETADA", Solicitud.estado == "COMPLETADO"),
                Solicitud.calificado == False,
            )
        )
        .order_by(Solicitud.fecha_fin_servicio.desc().nullslast())
        .limit(5)
        .all()
    )

    out = []
    for s, tec, cat in filas:
        completado = s.fecha_fin_servicio or s.fecha_solicitud
        out.append({
            "id": s.id,
            "categoria_nombre": cat.nombre if cat else "Servicio",
            "categoria_icono": (cat.icono if cat else "fas fa-tools"),
            "categoria_color": (cat.color if cat else "#3b82f6"),
            "tecnico_nombre": (f"{tec.nombres} {tec.apellido_paterno or ''}".strip() if tec else "Técnico"),
            "tecnico_foto": (tec.foto_url if tec else None),
            "completado_at": completado.isoformat() if completado else None,
        })
    return out
