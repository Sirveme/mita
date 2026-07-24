"""
Router CRUD para Insumos
Ruta: app/routes/insumos.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import (
    Insumo,
    CategoriaInsumo,
    MarcaInsumo,
    Proveedor,
    MarcaVehiculo,
    ModeloVehiculo,
    RecomendacionAceite
)
from app.schemas.insumo import (
    InsumoCreate, InsumoUpdate, InsumoResponse, 
    InsumoListResponse, InsumoListItem, InsumoFilters,
    CategoriaBase, MarcaBase, ProveedorBase
)

router = APIRouter(prefix="/insumos", tags=["Insumos"])


# ============================================
# LISTAR INSUMOS CON FILTROS Y PAGINACIÓN
# ============================================

@router.get("/", response_model=InsumoListResponse)
async def listar_insumos(
    search: Optional[str] = Query(None, description="Buscar por nombre o código"),
    categoria_id: Optional[int] = Query(None, description="Filtrar por categoría"),
    marca_id: Optional[int] = Query(None, description="Filtrar por marca"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado"),
    stock_bajo: Optional[bool] = Query(None, description="Solo productos con stock bajo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Listar todos los insumos con paginación y filtros.
    """
    
    # Query base con relaciones
    query = db.query(Insumo).options(
        joinedload(Insumo.categoria),
        joinedload(Insumo.marca)
    )
    
    # Aplicar filtros
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Insumo.nombre.ilike(search_term),
                Insumo.codigo_interno.ilike(search_term),
                Insumo.codigo_barras.ilike(search_term),
                Insumo.descripcion.ilike(search_term)
            )
        )
    
    if categoria_id:
        query = query.filter(Insumo.categoria_id == categoria_id)
    
    if marca_id:
        query = query.filter(Insumo.marca_id == marca_id)
    
    if activo is not None:
        query = query.filter(Insumo.activo == activo)
    
    if stock_bajo:
        query = query.filter(Insumo.stock_actual < Insumo.stock_minimo)
    
    # Contar total
    total = query.count()
    
    # Paginación
    offset = (page - 1) * page_size
    insumos = query.order_by(Insumo.nombre).offset(offset).limit(page_size).all()
    
    # Formatear respuesta
    items = []
    for insumo in insumos:
        items.append(InsumoListItem(
            id=insumo.id,
            codigo_interno=insumo.codigo_interno,
            nombre=insumo.nombre,
            categoria_nombre=insumo.categoria.nombre if insumo.categoria else None,
            marca_nombre=insumo.marca.nombre if insumo.marca else None,
            stock_actual=insumo.stock_actual,
            precio_publico=insumo.precio_publico,
            activo=insumo.activo
        ))
    
    return InsumoListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


# ============================================
# OBTENER DETALLE DE INSUMO
# ============================================

@router.get("/{insumo_id}", response_model=InsumoResponse)
async def obtener_insumo(
    insumo_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener detalle completo de un insumo.
    """
    insumo = db.query(Insumo).options(
        joinedload(Insumo.categoria),
        joinedload(Insumo.marca)
    ).filter(Insumo.id == insumo_id).first()
    
    if not insumo:
        raise HTTPException(
            status_code=404,
            detail=f"Insumo con ID {insumo_id} no encontrado"
        )
    
    return insumo


# ============================================
# CREAR INSUMO
# ============================================

@router.post("/", response_model=InsumoResponse, status_code=201)
async def crear_insumo(
    insumo: InsumoCreate,
    db: Session = Depends(get_db)
):
    """
    Crear un nuevo insumo.
    """
    
    # Verificar código interno único
    if insumo.codigo_interno:
        existe = db.query(Insumo).filter(
            Insumo.codigo_interno == insumo.codigo_interno
        ).first()
        if existe:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe un insumo con código interno '{insumo.codigo_interno}'"
            )
    
    # Verificar que categoría existe (si se especifica)
    if insumo.categoria_id:
        categoria = db.query(CategoriaInsumo).filter(
            CategoriaInsumo.id == insumo.categoria_id
        ).first()
        if not categoria:
            raise HTTPException(
                status_code=400,
                detail=f"Categoría con ID {insumo.categoria_id} no encontrada"
            )
    
    # Verificar que marca existe (si se especifica)
    if insumo.marca_id:
        marca = db.query(MarcaInsumo).filter(
            MarcaInsumo.id == insumo.marca_id
        ).first()
        if not marca:
            raise HTTPException(
                status_code=400,
                detail=f"Marca con ID {insumo.marca_id} no encontrada"
            )
    
    # Crear insumo
    nuevo_insumo = Insumo(**insumo.model_dump())
    
    db.add(nuevo_insumo)
    db.commit()
    db.refresh(nuevo_insumo)
    
    # Recargar con relaciones
    insumo_completo = db.query(Insumo).options(
        joinedload(Insumo.categoria),
        joinedload(Insumo.marca)
    ).filter(Insumo.id == nuevo_insumo.id).first()
    
    return insumo_completo


# ============================================
# ACTUALIZAR INSUMO
# ============================================

@router.put("/{insumo_id}", response_model=InsumoResponse)
async def actualizar_insumo(
    insumo_id: int,
    insumo_data: InsumoUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar un insumo existente.
    """
    
    # Buscar insumo
    insumo = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    
    if not insumo:
        raise HTTPException(
            status_code=404,
            detail=f"Insumo con ID {insumo_id} no encontrado"
        )
    
    # Verificar código interno único (si se cambia)
    if insumo_data.codigo_interno and insumo_data.codigo_interno != insumo.codigo_interno:
        existe = db.query(Insumo).filter(
            Insumo.codigo_interno == insumo_data.codigo_interno,
            Insumo.id != insumo_id
        ).first()
        if existe:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe otro insumo con código interno '{insumo_data.codigo_interno}'"
            )
    
    # Actualizar campos
    for field, value in insumo_data.model_dump(exclude_unset=True).items():
        setattr(insumo, field, value)
    
    insumo.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(insumo)
    
    # Recargar con relaciones
    insumo_completo = db.query(Insumo).options(
        joinedload(Insumo.categoria),
        joinedload(Insumo.marca)
    ).filter(Insumo.id == insumo_id).first()
    
    return insumo_completo


# ============================================
# ELIMINAR/DESACTIVAR INSUMO
# ============================================

@router.delete("/{insumo_id}")
async def eliminar_insumo(
    insumo_id: int,
    permanente: bool = Query(False, description="Eliminar permanentemente (true) o solo desactivar (false)"),
    db: Session = Depends(get_db)
):
    """
    Eliminar (desactivar) un insumo.
    Por defecto solo lo desactiva (soft delete).
    """
    
    insumo = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    
    if not insumo:
        raise HTTPException(
            status_code=404,
            detail=f"Insumo con ID {insumo_id} no encontrado"
        )
    
    if permanente:
        # Eliminar permanentemente (cuidado con relaciones)
        db.delete(insumo)
        mensaje = "Insumo eliminado permanentemente"
    else:
        # Soft delete (solo desactivar)
        insumo.activo = False
        insumo.updated_at = datetime.utcnow()
        mensaje = "Insumo desactivado"
    
    db.commit()
    
    return {
        "success": True,
        "message": mensaje,
        "insumo_id": insumo_id
    }


# ============================================
# ENDPOINTS AUXILIARES - CATEGORÍAS
# ============================================

@router.get("/categorias/listar", response_model=List[CategoriaBase])
async def listar_categorias(
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Listar todas las categorías de insumos (para dropdowns).
    """
    query = db.query(CategoriaInsumo)
    
    if activo is not None:
        query = query.filter(CategoriaInsumo.activo == activo)
    
    categorias = query.order_by(CategoriaInsumo.orden, CategoriaInsumo.nombre).all()
    
    return categorias


# ============================================
# ENDPOINTS AUXILIARES - MARCAS
# ============================================

@router.get("/marcas/listar", response_model=List[MarcaBase])
async def listar_marcas(
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Listar todas las marcas de insumos (para dropdowns).
    """
    query = db.query(MarcaInsumo)
    
    if activo is not None:
        query = query.filter(MarcaInsumo.activo == activo)
    
    marcas = query.order_by(MarcaInsumo.nombre).all()
    
    return marcas


# ============================================
# ENDPOINTS AUXILIARES - PROVEEDORES
# ============================================

@router.get("/proveedores/listar", response_model=List[ProveedorBase])
async def listar_proveedores(
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Listar todos los proveedores (para dropdowns).
    """
    query = db.query(Proveedor)
    
    if activo is not None:
        query = query.filter(Proveedor.activo == activo)
    
    proveedores = query.order_by(Proveedor.razon_social).all()
    
    return proveedores


# ============================================
# BUSCAR INSUMOS (autocompletado)
# ============================================

@router.get("/buscar/autocompletar")
async def buscar_autocompletar(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    limite: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Buscar insumos para autocompletado (nombre, código).
    """
    search_term = f"%{q}%"
    
    resultados = db.query(Insumo).filter(
        Insumo.activo == True,
        or_(
            Insumo.nombre.ilike(search_term),
            Insumo.codigo_interno.ilike(search_term)
        )
    ).limit(limite).all()
    
    return [
        {
            "id": r.id,
            "codigo": r.codigo_interno,
            "nombre": r.nombre,
            "precio": float(r.precio_publico) if r.precio_publico else 0,
            "stock": float(r.stock_actual)
        }
        for r in resultados
    ]


# ============================================
# RECOMENDACIONES ACEITE
# ============================================

@router.get("/recomendaciones/buscar")
async def buscar_recomendaciones(
    marca: str = Query(..., description="Marca del vehículo"),
    modelo: str = Query(..., description="Modelo del vehículo"),
    anio: int = Query(..., description="Año del vehículo"),
    kilometraje: Optional[int] = Query(None, description="Kilometraje actual"),
    db: Session = Depends(get_db)
):
    """
    Buscar recomendaciones de aceite según marca/modelo/año/km.
    """
    
    # Buscar marca
    marca_obj = db.query(MarcaVehiculo).filter(
        func.lower(MarcaVehiculo.nombre) == func.lower(marca)
    ).first()
    
    if not marca_obj:
        return {
            "success": False,
            "message": f"Marca '{marca}' no encontrada"
        }
    
    # Buscar modelo
    modelo_obj = db.query(ModeloVehiculo).filter(
        ModeloVehiculo.marca_id == marca_obj.id,
        func.lower(ModeloVehiculo.nombre) == func.lower(modelo)
    ).first()
    
    if not modelo_obj:
        return {
            "success": False,
            "message": f"Modelo '{modelo}' no encontrado para marca '{marca}'"
        }
    
    # Buscar recomendaciones
    query = db.query(RecomendacionAceite).filter(
        RecomendacionAceite.marca_vehiculo_id == marca_obj.id,
        RecomendacionAceite.modelo_vehiculo_id == modelo_obj.id,
        RecomendacionAceite.anio_inicio <= anio,
        RecomendacionAceite.anio_fin >= anio,
        RecomendacionAceite.activo == True
    )
    
    # Filtrar por kilometraje si se proporciona
    if kilometraje:
        query = query.filter(
            or_(
                RecomendacionAceite.kilometraje_min == None,
                RecomendacionAceite.kilometraje_min <= kilometraje
            ),
            or_(
                RecomendacionAceite.kilometraje_max == None,
                RecomendacionAceite.kilometraje_max >= kilometraje
            )
        )
    
    recomendaciones = query.all()
    
    if not recomendaciones:
        return {
            "success": False,
            "message": f"No se encontraron recomendaciones para {marca} {modelo} {anio}"
        }
    
    # Formatear respuesta
    return {
        "success": True,
        "vehiculo": {
            "marca": marca_obj.nombre,
            "modelo": modelo_obj.nombre,
            "anio": anio,
            "kilometraje": kilometraje
        },
        "recomendaciones": [
            {
                "id": r.id,
                "tipo_aceite": r.tipo_aceite,
                "viscosidad": r.viscosidad,
                "especificacion": r.especificacion,
                "capacidad_litros": float(r.capacidad_litros),
                "marcas_recomendadas": r.marcas_aceite_recomendadas,
                "filtros": {
                    "aceite": r.filtro_aceite_referencia,
                    "aire": r.filtro_aire_referencia,
                    "combustible": r.filtro_combustible_referencia
                },
                "notas": r.notas,
                "rango_kilometraje": {
                    "min": r.kilometraje_min,
                    "max": r.kilometraje_max
                }
            }
            for r in recomendaciones
        ]
    }