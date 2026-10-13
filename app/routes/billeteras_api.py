"""
API de billeteras electrónicas del personal (Yape, Plin, OTRA).
Prefijo /api/v1/personal (libre; admin usa /api/v1/admin/personal).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.billetera import BilleteraPersonal
from app.models.personal import Personal
from app.routes.login_mita import get_current_user

router = APIRouter(prefix="/api/v1/personal", tags=["Billeteras"])


def _mask(num: Optional[str]) -> str:
    s = (num or "").strip()
    return ("****" + s[-4:]) if len(s) >= 4 else "****"


async def _acceso_billeteras(personal_id: int, request: Request, db: Session = Depends(get_db)):
    """Solo admin/gerente o el propio técnico sobre su personal_id. Datos bancarios."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado", headers={"Location": "/login"})
    if (user.tipo or "").lower() in ("admin", "gerente"):
        return user
    if getattr(user, "personal_id", None) == personal_id:
        return user
    raise HTTPException(status_code=403, detail="No autorizado")


def _hist(db, personal_id, campo, anterior, nuevo, usuario):
    try:
        from app.services.catalogo import registrar_historial
        registrar_historial(db, "billeteras", personal_id, campo, anterior, nuevo,
                            getattr(usuario, "id", None))
    except Exception:
        pass


class BilleteraCreate(BaseModel):
    tipo: str  # YAPE, PLIN, OTRA
    nombre_billetera: Optional[str] = None
    numero_celular: str
    titular: Optional[str] = None
    es_principal: bool = False


class BilleteraUpdate(BaseModel):
    tipo: Optional[str] = None
    nombre_billetera: Optional[str] = None
    numero_celular: Optional[str] = None
    titular: Optional[str] = None
    activo: Optional[bool] = None
    es_principal: Optional[bool] = None


@router.get("/{personal_id}/billeteras")
def listar_billeteras(personal_id: int, db: Session = Depends(get_db), _=Depends(_acceso_billeteras)):
    billeteras = (
        db.query(BilleteraPersonal)
        .filter(BilleteraPersonal.personal_id == personal_id, BilleteraPersonal.activo == True)
        .all()
    )
    return [
        {
            "id": b.id, "tipo": b.tipo, "nombre_billetera": b.nombre_billetera,
            "numero_celular": b.numero_celular, "titular": b.titular, "es_principal": b.es_principal,
        }
        for b in billeteras
    ]


@router.post("/{personal_id}/billeteras")
def crear_billetera(personal_id: int, data: BilleteraCreate, db: Session = Depends(get_db), usuario=Depends(_acceso_billeteras)):
    personal = db.query(Personal).get(personal_id)
    if not personal:
        raise HTTPException(status_code=404, detail="Personal no encontrado")

    if data.es_principal:
        db.query(BilleteraPersonal).filter(
            BilleteraPersonal.personal_id == personal_id
        ).update({"es_principal": False})

    tipo = (data.tipo or "").upper()
    billetera = BilleteraPersonal(
        personal_id=personal_id,
        tipo=tipo,
        nombre_billetera=data.nombre_billetera if tipo == "OTRA" else None,
        numero_celular=data.numero_celular,
        titular=data.titular,
        es_principal=data.es_principal,
    )
    db.add(billetera)
    db.commit()
    db.refresh(billetera)
    _hist(db, personal_id, "alta", None, f"{tipo} {_mask(data.numero_celular)}", usuario)
    return {"success": True, "id": billetera.id}


@router.put("/{personal_id}/billeteras/{billetera_id}")
def actualizar_billetera(personal_id: int, billetera_id: int, data: BilleteraUpdate, db: Session = Depends(get_db), usuario=Depends(_acceso_billeteras)):
    billetera = (
        db.query(BilleteraPersonal)
        .filter(BilleteraPersonal.id == billetera_id, BilleteraPersonal.personal_id == personal_id)
        .first()
    )
    if not billetera:
        raise HTTPException(status_code=404, detail="Billetera no encontrada")

    if data.es_principal:
        db.query(BilleteraPersonal).filter(
            BilleteraPersonal.personal_id == personal_id,
            BilleteraPersonal.id != billetera_id,
        ).update({"es_principal": False})

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(billetera, field, value)
    db.commit()
    _hist(db, personal_id, "edicion", None, f"{billetera.tipo} {_mask(billetera.numero_celular)}", usuario)
    return {"success": True}


@router.delete("/{personal_id}/billeteras/{billetera_id}")
def eliminar_billetera(personal_id: int, billetera_id: int, db: Session = Depends(get_db), usuario=Depends(_acceso_billeteras)):
    billetera = (
        db.query(BilleteraPersonal)
        .filter(BilleteraPersonal.id == billetera_id, BilleteraPersonal.personal_id == personal_id)
        .first()
    )
    if not billetera:
        raise HTTPException(status_code=404, detail="Billetera no encontrada")
    billetera.activo = False
    db.commit()
    _hist(db, personal_id, "baja", f"{billetera.tipo} {_mask(billetera.numero_celular)}", None, usuario)
    return {"success": True}
