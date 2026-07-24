"""
Schemas Pydantic para Insumos
Ruta: app/schemas/insumo.py
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ============================================
# SCHEMAS BASE - CATEGORÍAS Y MARCAS
# ============================================

class CategoriaBase(BaseModel):
    id: int
    nombre: str
    
    class Config:
        from_attributes = True


class MarcaBase(BaseModel):
    id: int
    nombre: str
    logo_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProveedorBase(BaseModel):
    id: int
    ruc: str
    razon_social: str
    nombre_comercial: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============================================
# INSUMO - CREATE
# ============================================

class InsumoCreate(BaseModel):
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    codigo_interno: Optional[str] = None
    codigo_barras: Optional[str] = None
    nombre: str = Field(..., min_length=3, max_length=255)
    descripcion: Optional[str] = None
    presentacion: Optional[str] = None
    unidad_medida: str = Field(default="unidad")
    
    # Stock
    stock_actual: Decimal = Field(default=0, ge=0)
    stock_minimo: Decimal = Field(default=0, ge=0)
    stock_maximo: Decimal = Field(default=0, ge=0)
    
    # Precios
    precio_compra: Optional[Decimal] = Field(None, ge=0)
    precio_venta: Optional[Decimal] = Field(None, ge=0)
    precio_publico: Optional[Decimal] = Field(None, ge=0)
    
    # Metadata
    imagen_url: Optional[str] = None
    requiere_refrigeracion: bool = False
    fecha_vencimiento: Optional[date] = None
    proveedor_principal: Optional[str] = None
    activo: bool = True
    tipo_recomendacion: Optional[str] = Field(None, pattern='^(oem|premium|estandar|economico)$')


# ============================================
# INSUMO - UPDATE
# ============================================

class InsumoUpdate(BaseModel):
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    codigo_interno: Optional[str] = None
    codigo_barras: Optional[str] = None
    nombre: Optional[str] = Field(None, min_length=3, max_length=255)
    descripcion: Optional[str] = None
    presentacion: Optional[str] = None
    unidad_medida: Optional[str] = None
    
    # Stock
    stock_actual: Optional[Decimal] = Field(None, ge=0)
    stock_minimo: Optional[Decimal] = Field(None, ge=0)
    stock_maximo: Optional[Decimal] = Field(None, ge=0)
    
    # Precios
    precio_compra: Optional[Decimal] = Field(None, ge=0)
    precio_venta: Optional[Decimal] = Field(None, ge=0)
    precio_publico: Optional[Decimal] = Field(None, ge=0)
    
    # Metadata
    imagen_url: Optional[str] = None
    requiere_refrigeracion: Optional[bool] = None
    fecha_vencimiento: Optional[date] = None
    proveedor_principal: Optional[str] = None
    activo: Optional[bool] = None


# ============================================
# INSUMO - RESPONSE
# ============================================

class InsumoResponse(BaseModel):
    id: int
    categoria_id: Optional[int]
    marca_id: Optional[int]
    codigo_interno: Optional[str]
    codigo_barras: Optional[str]
    nombre: str
    descripcion: Optional[str]
    presentacion: Optional[str]
    unidad_medida: Optional[str]
    
    # Stock
    stock_actual: Decimal
    stock_minimo: Decimal
    stock_maximo: Decimal
    
    # Precios
    precio_compra: Optional[Decimal]
    precio_venta: Optional[Decimal]
    precio_publico: Optional[Decimal]
    
    # Metadata
    imagen_url: Optional[str]
    requiere_refrigeracion: bool
    fecha_vencimiento: Optional[date]
    proveedor_principal: Optional[str]
    activo: bool
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Relaciones (opcional - se cargan si existen)
    categoria: Optional[CategoriaBase] = None
    marca: Optional[MarcaBase] = None
    
    class Config:
        from_attributes = True


# ============================================
# INSUMO - LISTA (simplificado para tablas)
# ============================================

class InsumoListItem(BaseModel):
    id: int
    codigo_interno: Optional[str]
    nombre: str
    categoria_nombre: Optional[str] = None
    marca_nombre: Optional[str] = None
    stock_actual: Decimal
    precio_publico: Optional[Decimal]
    activo: bool
    
    class Config:
        from_attributes = True


class InsumoListResponse(BaseModel):
    total: int
    items: List[InsumoListItem]
    page: int
    page_size: int


# ============================================
# FILTERS
# ============================================

class InsumoFilters(BaseModel):
    search: Optional[str] = None
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    activo: Optional[bool] = None
    stock_bajo: Optional[bool] = None  # stock_actual < stock_minimo
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ============================================
# RECOMENDACIÓN ACEITE
# ============================================

class RecomendacionAceiteResponse(BaseModel):
    id: int
    marca_vehiculo_id: int
    modelo_vehiculo_id: int
    anio_inicio: int
    anio_fin: int
    tipo_aceite: str
    viscosidad: str
    capacidad_litros: Decimal
    marcas_aceite_recomendadas: Optional[dict] = None
    filtro_aceite_referencia: Optional[str]
    filtro_aire_referencia: Optional[str]
    
    class Config:
        from_attributes = True