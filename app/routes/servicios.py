"""
Router de Servicios Técnicos MITA
Ruta: app/routes/servicios.py

Expone el catálogo de servicios (categorías / tipos), la creación de solicitudes
genéricas, el reporte del técnico, historial por teléfono y estadísticas.

Montado en main.py con prefix="/api/v1"  →  endpoints en /api/v1/servicios/...
"""

from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    CategoriaServicio,
    TipoServicio,
    ReporteTecnico,
    Insumo,
)
from app.models.solicitud import SolicitudServicio

router = APIRouter(prefix="/servicios", tags=["Servicios"])

# Modelo de negocio MITA: visita S/50 = comisión MITA S/15 + pago técnico S/35
PRECIO_VISITA_DEFAULT = Decimal("50.00")
COMISION_MITA_DEFAULT = Decimal("15.00")
PAGO_TECNICO_DEFAULT = Decimal("35.00")


# ============================================
# SCHEMAS (request bodies)
# ============================================

class SolicitudCreate(BaseModel):
    # Servicio
    categoria_codigo: Optional[str] = None
    tipo_servicio_codigo: Optional[str] = None
    tipo_servicio_nombre: Optional[str] = None
    descripcion: Optional[str] = None
    urgencia: str = "normal"
    fotos_problema: Optional[List[str]] = None
    # Contacto
    nombre: str
    telefono: str
    email: Optional[str] = None
    distrito: Optional[str] = None
    direccion: str
    referencia: Optional[str] = None
    # Ubicación (opcional)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    # Programación (opcional)
    fecha_servicio: Optional[str] = None
    hora_servicio: Optional[str] = None
    # Identificación anónima (opcional)
    device_id: Optional[str] = None


class MaterialItem(BaseModel):
    nombre: str
    cantidad: float = 1
    precio: float = 0


class ReporteCreate(BaseModel):
    solicitud_id: int
    tecnico_id: int
    diagnostico: str
    causa_problema: Optional[str] = None
    solucion_aplicada: Optional[str] = None
    hubo_trabajo_adicional: bool = False
    descripcion_trabajo_adicional: Optional[str] = None
    tiempo_trabajo_min: Optional[int] = None
    monto_mano_obra: float = 0
    monto_materiales: float = 0
    detalle_materiales: Optional[List[MaterialItem]] = None
    metodo_pago_adicional: Optional[str] = None
    cobrado_por_tecnico: bool = True
    tecnico_emitio_comprobante: bool = False
    tipo_comprobante_tecnico: Optional[str] = None
    numero_comprobante_tecnico: Optional[str] = None
    fotos_antes: Optional[List[str]] = None
    fotos_despues: Optional[List[str]] = None
    observaciones: Optional[str] = None
    requiere_seguimiento: bool = False
    motivo_seguimiento: Optional[str] = None


# ============================================
# CATÁLOGO: CATEGORÍAS Y TIPOS
# ============================================

def _categoria_dict(c: CategoriaServicio) -> dict:
    return {
        "id": c.id,
        "codigo": c.codigo,
        "nombre": c.nombre,
        "descripcion": c.descripcion,
        "icono": c.icono or "fas fa-tools",
        "color": c.color or "#FFCD11",
        "imagen_url": c.imagen_url,
        "orden": c.orden or 0,
        "proximamente": bool(c.proximamente),
    }


@router.get("/categorias")
async def listar_categorias(
    incluir_proximamente: bool = True,
    db: Session = Depends(get_db),
):
    """Lista las categorías de servicio activas (para el grid del home)."""
    query = db.query(CategoriaServicio).filter(CategoriaServicio.activo == True)
    if not incluir_proximamente:
        query = query.filter(CategoriaServicio.proximamente == False)
    categorias = query.order_by(CategoriaServicio.orden).all()

    return {
        "success": True,
        "total": len(categorias),
        "categorias": [_categoria_dict(c) for c in categorias],
    }


@router.get("/categorias/{codigo}/tipos")
async def listar_tipos_por_categoria(codigo: str, db: Session = Depends(get_db)):
    """
    Devuelve la categoría y sus tipos de servicio.
    Contrato consumido por cliente/solicitar_servicio.html.
    """
    categoria = (
        db.query(CategoriaServicio)
        .filter(func.upper(CategoriaServicio.codigo) == codigo.upper())
        .first()
    )
    if not categoria:
        raise HTTPException(status_code=404, detail=f"Categoría '{codigo}' no encontrada")

    tipos = (
        db.query(TipoServicio)
        .filter(
            TipoServicio.categoria_id == categoria.id,
            TipoServicio.activo == True,
        )
        .order_by(TipoServicio.nombre)
        .all()
    )

    return {
        "success": True,
        "categoria": _categoria_dict(categoria),
        "tipos": [
            {
                "id": t.id,
                "codigo": t.codigo,
                "nombre": t.nombre,
                "descripcion": t.descripcion,
                "precio_visita": float(t.precio_visita or PRECIO_VISITA_DEFAULT),
                "duracion_estimada_min": t.duracion_estimada_min or 60,
                "requiere_materiales": bool(t.requiere_materiales),
            }
            for t in tipos
        ],
    }


# ============================================
# SOLICITUDES
# ============================================

@router.post("/solicitar")
async def crear_solicitud(payload: SolicitudCreate, db: Session = Depends(get_db)):
    """Crea una solicitud de servicio (flujo anónimo MITA)."""
    categoria = None
    tipo = None
    if payload.categoria_codigo:
        categoria = (
            db.query(CategoriaServicio)
            .filter(func.upper(CategoriaServicio.codigo) == payload.categoria_codigo.upper())
            .first()
        )
    if payload.tipo_servicio_codigo:
        tipo = (
            db.query(TipoServicio)
            .filter(func.upper(TipoServicio.codigo) == payload.tipo_servicio_codigo.upper())
            .first()
        )

    precio_visita = (tipo.precio_visita if tipo and tipo.precio_visita else PRECIO_VISITA_DEFAULT)

    solicitud = SolicitudServicio(
        device_id=payload.device_id,
        nombre_contacto=payload.nombre,
        telefono_contacto=payload.telefono,
        direccion_servicio=payload.direccion,
        referencias_direccion=payload.referencia,
        latitud=payload.latitud,
        longitud=payload.longitud,
        tipo_servicio=(payload.tipo_servicio_nombre or payload.tipo_servicio_codigo or "General"),
        descripcion_adicional=payload.descripcion,
        # Campos MITA
        categoria_servicio_id=categoria.id if categoria else None,
        tipo_servicio_id=tipo.id if tipo else None,
        descripcion_problema=payload.descripcion,
        urgencia=payload.urgencia or "normal",
        fotos_problema=payload.fotos_problema,
        precio_visita=precio_visita,
        precio_total=precio_visita,
        comision_mita=COMISION_MITA_DEFAULT,
        pago_tecnico=PAGO_TECNICO_DEFAULT,
        precio_estimado=precio_visita,
        estado="pendiente",
        estado_pago="pendiente",
        fecha_servicio=payload.fecha_servicio,
        hora_servicio=payload.hora_servicio,
    )

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return {
        "success": True,
        "mensaje": "Solicitud registrada correctamente",
        "solicitud_id": solicitud.id,
        "precio_visita": float(precio_visita),
    }


@router.get("/historial/cliente/{telefono}")
async def historial_cliente(telefono: str, db: Session = Depends(get_db)):
    """Historial de solicitudes de un cliente por número de teléfono."""
    solicitudes = (
        db.query(SolicitudServicio)
        .filter(SolicitudServicio.telefono_contacto == telefono)
        .order_by(SolicitudServicio.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "telefono": telefono,
        "total": len(solicitudes),
        "solicitudes": [
            {
                "id": s.id,
                "tipo_servicio": s.tipo_servicio,
                "estado": s.estado,
                "estado_pago": s.estado_pago,
                "precio_total": float(s.precio_total) if s.precio_total is not None else None,
                "direccion": s.direccion_servicio,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "calificacion": s.calificacion,
            }
            for s in solicitudes
        ],
    }


# ============================================
# REPORTE DEL TÉCNICO
# ============================================

@router.post("/reporte")
async def crear_reporte(payload: ReporteCreate, db: Session = Depends(get_db)):
    """El técnico reporta el trabajo realizado tras una visita."""
    solicitud = db.query(SolicitudServicio).get(payload.solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    monto_total_adicional = Decimal(str(payload.monto_mano_obra or 0)) + Decimal(str(payload.monto_materiales or 0))

    reporte = ReporteTecnico(
        solicitud_id=payload.solicitud_id,
        tecnico_id=payload.tecnico_id,
        diagnostico=payload.diagnostico,
        causa_problema=payload.causa_problema,
        solucion_aplicada=payload.solucion_aplicada,
        hubo_trabajo_adicional=payload.hubo_trabajo_adicional,
        descripcion_trabajo_adicional=payload.descripcion_trabajo_adicional,
        tiempo_trabajo_min=payload.tiempo_trabajo_min,
        monto_mano_obra=payload.monto_mano_obra,
        monto_materiales=payload.monto_materiales,
        detalle_materiales=[m.dict() for m in payload.detalle_materiales] if payload.detalle_materiales else None,
        monto_total_adicional=monto_total_adicional,
        metodo_pago_adicional=payload.metodo_pago_adicional,
        cobrado_por_tecnico=payload.cobrado_por_tecnico,
        tecnico_emitio_comprobante=payload.tecnico_emitio_comprobante,
        tipo_comprobante_tecnico=payload.tipo_comprobante_tecnico,
        numero_comprobante_tecnico=payload.numero_comprobante_tecnico,
        fotos_antes=payload.fotos_antes,
        fotos_despues=payload.fotos_despues,
        observaciones=payload.observaciones,
        requiere_seguimiento=payload.requiere_seguimiento,
        motivo_seguimiento=payload.motivo_seguimiento,
    )
    db.add(reporte)

    # Reflejar el adicional en la solicitud
    if payload.hubo_trabajo_adicional:
        solicitud.precio_trabajo_adicional = payload.monto_mano_obra
        solicitud.precio_materiales = payload.monto_materiales
        base = solicitud.precio_visita or PRECIO_VISITA_DEFAULT
        solicitud.precio_total = Decimal(str(base)) + monto_total_adicional
    solicitud.estado = "completado"

    db.commit()
    db.refresh(reporte)

    return {
        "success": True,
        "mensaje": "Reporte registrado",
        "reporte_id": reporte.id,
        "monto_total_adicional": float(monto_total_adicional),
    }


# ============================================
# ESTADÍSTICAS
# ============================================

@router.get("/estadisticas/resumen")
async def estadisticas_resumen(db: Session = Depends(get_db)):
    """Resumen agregado de solicitudes e ingresos MITA."""
    total = db.query(func.count(SolicitudServicio.id)).scalar() or 0
    completados = (
        db.query(func.count(SolicitudServicio.id))
        .filter(SolicitudServicio.estado == "completado")
        .scalar()
        or 0
    )
    cancelados = (
        db.query(func.count(SolicitudServicio.id))
        .filter(SolicitudServicio.estado == "cancelado")
        .scalar()
        or 0
    )
    ingresos_mita = db.query(func.coalesce(func.sum(SolicitudServicio.comision_mita), 0)).scalar() or 0
    pagos_tecnicos = db.query(func.coalesce(func.sum(SolicitudServicio.pago_tecnico), 0)).scalar() or 0

    # Solicitudes por categoría
    por_categoria = (
        db.query(CategoriaServicio.nombre, func.count(SolicitudServicio.id))
        .outerjoin(SolicitudServicio, SolicitudServicio.categoria_servicio_id == CategoriaServicio.id)
        .group_by(CategoriaServicio.nombre)
        .all()
    )

    return {
        "success": True,
        "total_solicitudes": total,
        "completados": completados,
        "cancelados": cancelados,
        "ingresos_mita": float(ingresos_mita),
        "pagos_tecnicos": float(pagos_tecnicos),
        "por_categoria": [{"categoria": n, "total": c} for n, c in por_categoria],
    }


# ============================================
# LEGACY (aceite/automotriz) - preservado del router anterior
# ============================================

@router.get("/calcular-total")
async def calcular_total_servicio(
    aceite_id: int,
    filtros_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
):
    """Calcula el total de un servicio de cambio de aceite (base S/50 + insumos)."""
    total = float(PRECIO_VISITA_DEFAULT)

    aceite = db.query(Insumo).get(aceite_id)
    if aceite:
        total += float(aceite.precio_publico or 0)

    filtros_total = 0.0
    if filtros_ids:
        filtros = db.query(Insumo).filter(Insumo.id.in_(filtros_ids)).all()
        filtros_total = sum(float(f.precio_publico or 0) for f in filtros)
        total += filtros_total

    return {
        "success": True,
        "servicio_base": float(PRECIO_VISITA_DEFAULT),
        "aceite": float(aceite.precio_publico or 0) if aceite else 0,
        "filtros": filtros_total,
        "materiales_incluidos": True,
        "total": round(total, 2),
    }
