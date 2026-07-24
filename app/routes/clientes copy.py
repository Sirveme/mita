from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from typing import List

router = APIRouter()

@router.get("/")
async def listar_clientes(db: Session = Depends(get_db)):
    """Listar todos los clientes"""
    # TODO: Implementar lógica
    return {"clientes": []}

@router.get("/{cliente_id}")
async def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtener cliente por ID"""
    # TODO: Implementar lógica
    return {"cliente_id": cliente_id}

@router.post("/")
async def crear_cliente(db: Session = Depends(get_db)):
    """Crear nuevo cliente"""
    # TODO: Implementar lógica
    return {"message": "Cliente creado"}

@router.put("/{cliente_id}")
async def actualizar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Actualizar cliente"""
    # TODO: Implementar lógica
    return {"message": "Cliente actualizado"}

@router.delete("/{cliente_id}")
async def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Eliminar cliente"""
    # TODO: Implementar lógica
    return {"message": "Cliente eliminado"}