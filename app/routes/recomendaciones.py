"""
Router para Recomendaciones de Aceite
Ruta: app/routes/recomendaciones.py
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional

from app.core.database import get_db
from app.models.models import (
    MarcaVehiculo,
    ModeloVehiculo,
    RecomendacionAceite,
    Insumo,
    CategoriaInsumo
)

router = APIRouter(prefix="/recomendaciones", tags=["Recomendaciones"])

@router.get("/recomendaciones-vehiculo")
async def obtener_recomendaciones_vehiculo(
    marca: str,
    modelo: str,
    anio: int,
    kilometraje: int,
    db: Session = Depends(get_db)
):
    """
    Obtener paquete completo de recomendaciones para cambio de aceite
    """
    
    # 1. Buscar marca vehículo
    marca_obj = db.query(MarcaVehiculo).filter(
        func.lower(MarcaVehiculo.nombre) == func.lower(marca)
    ).first()
    
    if not marca_obj:
        return {"success": False, "error": f"Marca '{marca}' no encontrada"}
    
    # 2. Buscar modelo
    modelo_obj = db.query(ModeloVehiculo).filter(
        ModeloVehiculo.marca_id == marca_obj.id,
        func.lower(ModeloVehiculo.nombre) == func.lower(modelo)
    ).first()
    
    if not modelo_obj:
        return {"success": False, "error": f"Modelo '{modelo}' no encontrado"}
    
    # 3. Buscar recomendación específica
    recomendacion = db.query(RecomendacionAceite).filter(
        RecomendacionAceite.marca_vehiculo_id == marca_obj.id,
        RecomendacionAceite.modelo_vehiculo_id == modelo_obj.id,
        RecomendacionAceite.anio_inicio <= anio,
        RecomendacionAceite.anio_fin >= anio,
        or_(
            RecomendacionAceite.kilometraje_min == None,
            RecomendacionAceite.kilometraje_min <= kilometraje
        ),
        or_(
            RecomendacionAceite.kilometraje_max == None,
            RecomendacionAceite.kilometraje_max >= kilometraje
        ),
        RecomendacionAceite.activo == True
    ).first()
    
    if not recomendacion:
        return {"success": False, "error": "No hay recomendaciones para este vehículo"}
    
    # 4. Buscar productos de aceite según tipo y viscosidad
    aceites = db.query(Insumo).filter(
        Insumo.categoria_id == db.query(CategoriaInsumo.id).filter(
            CategoriaInsumo.nombre == 'Aceites'
        ).scalar(),
        or_(
            Insumo.nombre.ilike(f'%{recomendacion.viscosidad}%'),
            Insumo.descripcion.ilike(f'%{recomendacion.viscosidad}%')
        ),
        Insumo.activo == True
    ).all()
    
    # Clasificar aceites por tipo_recomendacion
    aceites_por_tipo = {
        'oem': [],
        'premium': [],
        'estandar': [],
        'economico': []
    }
    
    for aceite in aceites:
        tipo = aceite.tipo_recomendacion or 'estandar'
        aceites_por_tipo[tipo].append({
            'id': aceite.id,
            'nombre': aceite.nombre,
            'descripcion': aceite.descripcion,
            'precio': float(aceite.precio_publico or 0),
            'imagen_url': aceite.imagen_url,
            'marca': aceite.marca.nombre if aceite.marca else None
        })
    
    # 5. Buscar filtros recomendados
    filtro_aceite = None
    if recomendacion.filtro_aceite_referencia:
        filtro_aceite = db.query(Insumo).filter(
            Insumo.nombre.ilike(f'%{recomendacion.filtro_aceite_referencia}%'),
            Insumo.activo == True
        ).first()
    
    filtro_aire = None
    if recomendacion.filtro_aire_referencia:
        filtro_aire = db.query(Insumo).filter(
            Insumo.nombre.ilike(f'%{recomendacion.filtro_aire_referencia}%'),
            Insumo.activo == True
        ).first()
    
    filtro_combustible = None
    if recomendacion.filtro_combustible_referencia:
        filtro_combustible = db.query(Insumo).filter(
            Insumo.nombre.ilike(f'%{recomendacion.filtro_combustible_referencia}%'),
            Insumo.activo == True
        ).first()
    
    # 6. Construir respuesta
    return {
        "success": True,
        "vehiculo": {
            "marca": marca_obj.nombre,
            "modelo": modelo_obj.nombre,
            "anio": anio,
            "kilometraje": kilometraje
        },
        "especificaciones": {
            "tipo_aceite": recomendacion.tipo_aceite,
            "viscosidad": recomendacion.viscosidad,
            "capacidad_litros": float(recomendacion.capacidad_litros),
            "especificacion": recomendacion.especificacion,
            "notas": recomendacion.notas
        },
        "aceites": aceites_por_tipo,
        "filtros": {
            "aceite": {
                'id': filtro_aceite.id,
                'nombre': filtro_aceite.nombre,
                'precio': float(filtro_aceite.precio_publico or 0),
                'imagen_url': filtro_aceite.imagen_url
            } if filtro_aceite else None,
            "aire": {
                'id': filtro_aire.id,
                'nombre': filtro_aire.nombre,
                'precio': float(filtro_aire.precio_publico or 0),
                'imagen_url': filtro_aire.imagen_url
            } if filtro_aire else None,
            "combustible": {
                'id': filtro_combustible.id,
                'nombre': filtro_combustible.nombre,
                'precio': float(filtro_combustible.precio_publico or 0),
                'imagen_url': filtro_combustible.imagen_url
            } if filtro_combustible else None
        }
    }


@router.get("/marcas")
async def listar_marcas_vehiculos(
    db: Session = Depends(get_db)
):
    """Listar todas las marcas de vehículos activas"""
    
    marcas = db.query(MarcaVehiculo).filter(
        MarcaVehiculo.activo == True
    ).order_by(MarcaVehiculo.orden_display, MarcaVehiculo.nombre).all()
    
    return {
        "success": True,
        "marcas": [
            {
                "id": m.id,
                "nombre": m.nombre,
                "logo_url": m.logo_url
            }
            for m in marcas
        ]
    }


@router.get("/modelos/{marca_id}")
async def listar_modelos_por_marca(
    marca_id: int,
    db: Session = Depends(get_db)
):
    """Listar modelos de una marca específica"""
    
    modelos = db.query(ModeloVehiculo).filter(
        ModeloVehiculo.marca_id == marca_id,
        ModeloVehiculo.activo == True
    ).order_by(ModeloVehiculo.nombre).all()
    
    return {
        "success": True,
        "marca_id": marca_id,
        "modelos": [
            {
                "id": m.id,
                "nombre": m.nombre,
                "anio_inicio": m.anio_inicio,
                "anio_fin": m.anio_fin,
                "tipo_vehiculo": m.tipo_vehiculo
            }
            for m in modelos
        ]
    }


@router.get("/buscar-por-ids")
async def buscar_recomendaciones_por_ids(
    marca_id: int = Query(..., description="ID de la marca"),
    modelo_id: int = Query(..., description="ID del modelo"),
    anio: int = Query(..., description="Año del vehículo"),
    kilometraje: int = Query(..., description="Kilometraje actual"),
    db: Session = Depends(get_db)
):
    """
    Buscar recomendaciones usando IDs de marca y modelo (más preciso)
    """
    
    # Buscar recomendación específica
    recomendacion = db.query(RecomendacionAceite).filter(
        RecomendacionAceite.marca_vehiculo_id == marca_id,
        RecomendacionAceite.modelo_vehiculo_id == modelo_id,
        RecomendacionAceite.anio_inicio <= anio,
        RecomendacionAceite.anio_fin >= anio,
        or_(
            RecomendacionAceite.kilometraje_min == None,
            RecomendacionAceite.kilometraje_min <= kilometraje
        ),
        or_(
            RecomendacionAceite.kilometraje_max == None,
            RecomendacionAceite.kilometraje_max >= kilometraje
        ),
        RecomendacionAceite.activo == True
    ).first()
    
    if not recomendacion:
        return {
            "success": False,
            "error": "No hay recomendaciones para este vehículo"
        }
    
    # Buscar marca y modelo para info
    marca = db.query(MarcaVehiculo).get(marca_id)
    modelo = db.query(ModeloVehiculo).get(modelo_id)
    
    # Buscar aceites según especificaciones
    categoria_aceites = db.query(CategoriaInsumo).filter(
        CategoriaInsumo.nombre == 'Aceites'
    ).first()
    
    aceites = db.query(Insumo).filter(
        Insumo.categoria_id == categoria_aceites.id,
        or_(
            Insumo.nombre.ilike(f'%{recomendacion.viscosidad}%'),
            Insumo.descripcion.ilike(f'%{recomendacion.viscosidad}%')
        ),
        Insumo.activo == True
    ).all()
    
    # Clasificar aceites por tipo_recomendacion
    aceites_por_tipo = {
        'oem': [],
        'premium': [],
        'estandar': [],
        'economico': []
    }
    
    for aceite in aceites:
        tipo = aceite.tipo_recomendacion or 'estandar'
        aceites_por_tipo[tipo].append({
            'id': aceite.id,
            'nombre': aceite.nombre,
            'descripcion': aceite.descripcion,
            'precio': float(aceite.precio_publico or 0),
            'imagen_url': aceite.imagen_url,
            'marca': aceite.marca.nombre if aceite.marca else None,
            'stock': float(aceite.stock_actual)
        })
    
    # Buscar filtros
    categoria_filtros = db.query(CategoriaInsumo).filter(
        CategoriaInsumo.nombre == 'Filtros'
    ).first()
    
    filtro_aceite = None
    if recomendacion.filtro_aceite_referencia:
        filtro_aceite = db.query(Insumo).filter(
            Insumo.categoria_id == categoria_filtros.id,
            Insumo.nombre.ilike(f'%{recomendacion.filtro_aceite_referencia}%'),
            Insumo.activo == True
        ).first()
    
    filtro_aire = None
    if recomendacion.filtro_aire_referencia:
        filtro_aire = db.query(Insumo).filter(
            Insumo.categoria_id == categoria_filtros.id,
            Insumo.nombre.ilike(f'%{recomendacion.filtro_aire_referencia}%'),
            Insumo.activo == True
        ).first()
    
    filtro_combustible = None
    if recomendacion.filtro_combustible_referencia:
        filtro_combustible = db.query(Insumo).filter(
            Insumo.categoria_id == categoria_filtros.id,
            Insumo.nombre.ilike(f'%{recomendacion.filtro_combustible_referencia}%'),
            Insumo.activo == True
        ).first()
    
    return {
        "success": True,
        "vehiculo": {
            "marca": marca.nombre,
            "modelo": modelo.nombre,
            "anio": anio,
            "kilometraje": kilometraje
        },
        "especificaciones": {
            "tipo_aceite": recomendacion.tipo_aceite,
            "viscosidad": recomendacion.viscosidad,
            "capacidad_litros": float(recomendacion.capacidad_litros),
            "especificacion": recomendacion.especificacion,
            "notas": recomendacion.notas
        },
        "aceites": aceites_por_tipo,
        "filtros": {
            "aceite": {
                'id': filtro_aceite.id,
                'nombre': filtro_aceite.nombre,
                'precio': float(filtro_aceite.precio_publico or 0),
                'imagen_url': filtro_aceite.imagen_url,
                'stock': float(filtro_aceite.stock_actual)
            } if filtro_aceite else None,
            "aire": {
                'id': filtro_aire.id,
                'nombre': filtro_aire.nombre,
                'precio': float(filtro_aire.precio_publico or 0),
                'imagen_url': filtro_aire.imagen_url,
                'stock': float(filtro_aire.stock_actual)
            } if filtro_aire else None,
            "combustible": {
                'id': filtro_combustible.id,
                'nombre': filtro_combustible.nombre,
                'precio': float(filtro_combustible.precio_publico or 0),
                'imagen_url': filtro_combustible.imagen_url,
                'stock': float(filtro_combustible.stock_actual)
            } if filtro_combustible else None
        }
    }