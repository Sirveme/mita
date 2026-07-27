"""
API de billeteras electrónicas del personal (Yape, Plin, OTRA).
Prefijo /api/v1/personal (libre; admin usa /api/v1/admin/personal).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.billetera import BilleteraPersonal
from app.models.personal import Personal

router = APIRouter(prefix="/api/v1/personal", tags=["Billeteras"])


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
def listar_billeteras(personal_id: int, db: Session = Depends(get_db)):
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
def crear_billetera(personal_id: int, data: BilleteraCreate, db: Session = Depends(get_db)):
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
    return {"success": True, "id": billetera.id}


@router.put("/{personal_id}/billeteras/{billetera_id}")
def actualizar_billetera(personal_id: int, billetera_id: int, data: BilleteraUpdate, db: Session = Depends(get_db)):
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
    return {"success": True}


@router.delete("/{personal_id}/billeteras/{billetera_id}")
def eliminar_billetera(personal_id: int, billetera_id: int, db: Session = Depends(get_db)):
    billetera = (
        db.query(BilleteraPersonal)
        .filter(BilleteraPersonal.id == billetera_id, BilleteraPersonal.personal_id == personal_id)
        .first()
    )
    if not billetera:
        raise HTTPException(status_code=404, detail="Billetera no encontrada")
    billetera.activo = False
    db.commit()
    return {"success": True}
