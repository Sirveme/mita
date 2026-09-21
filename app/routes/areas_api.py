"""
Áreas y problemas de servicio (flujo de solicitud estilo VISA).
GET /api/v1/areas-servicio -> áreas activas con sus problemas anidados.
Público (lo consume /cliente/solicitar).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.area_servicio import AreaServicio
from app.models.problema_servicio import ProblemaServicio

router = APIRouter(prefix="/api/v1", tags=["Áreas de servicio"])


@router.get("/areas-servicio")
def listar_areas(db: Session = Depends(get_db)):
    areas = (db.query(AreaServicio)
               .filter(AreaServicio.activo.is_(True))
               .order_by(AreaServicio.orden).all())
    problemas = (db.query(ProblemaServicio)
                   .filter(ProblemaServicio.activo.is_(True))
                   .order_by(ProblemaServicio.orden).all())
    por_area = {}
    for p in problemas:
        por_area.setdefault(p.area_id, []).append({
            "id": p.id, "tipo": p.tipo, "nombre": p.nombre,
            "icono": p.icono, "orden": p.orden,
        })
    def _seed(a):
        # extrae la semilla de picsum de imagen_url (…/seed/<seed>/…), o usa el código
        try:
            if a.imagen_url and "/seed/" in a.imagen_url:
                return a.imagen_url.split("/seed/")[1].split("/")[0]
        except Exception:
            pass
        return (a.codigo or "mita").lower()

    return [{
        "id": a.id, "codigo": a.codigo, "nombre": a.nombre, "descripcion": a.descripcion,
        "categoria_id": a.categoria_id, "icono": a.icono, "color1": a.color1, "color2": a.color2,
        "imagen_url": a.imagen_url, "seed": _seed(a),
        "orden": a.orden, "problemas": por_area.get(a.id, []),
    } for a in areas]
