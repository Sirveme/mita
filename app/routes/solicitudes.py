# ============================================
# REEMPLAZAR EN: app/routes/solicitudes.py
# ============================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.solicitud import SolicitudServicio, MensajeChatSolicitud
from app.schemas.solicitud import (
    SolicitudServicioCreate,
    SolicitudServicioResponse,
    SolicitudDetalle,
    MensajeChatCreate
)

router = APIRouter(prefix="/solicitudes", tags=["solicitudes"])

# ============================================
# CREAR SOLICITUD (SIN AUTENTICACIÓN - ANÓNIMA)
# ============================================

@router.post("/crear", response_model=SolicitudServicioResponse, status_code=status.HTTP_201_CREATED)
async def crear_solicitud_anonima(
    solicitud: SolicitudServicioCreate,
    db: Session = Depends(get_db)
):
    """
    Crear solicitud de servicio SIN necesidad de login.
    Se identifica por device_id y telefono_contacto.
    """
    try:
        # Crear nueva solicitud
        nueva_solicitud = SolicitudServicio(
            # Identificación anónima
            device_id=solicitud.device_id,
            nombre_contacto=solicitud.nombre_contacto,
            telefono_contacto=solicitud.telefono_contacto,
            
            # Datos del servicio
            tipo_servicio=solicitud.tipo_servicio,
            descripcion_adicional=solicitud.descripcion_adicional,
            direccion_servicio=solicitud.direccion_servicio,
            #distrito=solicitud.distrito,
            referencias_direccion=solicitud.referencias_direccion,
            
            # Datos del vehículo (si aplica)
            marca_vehiculo=solicitud.marca_vehiculo,
            modelo_vehiculo=solicitud.modelo_vehiculo,
            anio_vehiculo=solicitud.anio_vehiculo,
            placa_vehiculo=solicitud.placa_vehiculo,
            #kilometraje=solicitud.kilometraje,
            
            # Fecha/hora preferida (opcional en este momento)
            #fecha_servicio=solicitud.fecha_servicio,
            #hora_servicio=solicitud.hora_servicio,
            
            # Precio y pago
            precio_estimado=solicitud.precio_estimado,
            metodo_pago=solicitud.metodo_pago,
            
            # Push token (opcional)
            push_token=solicitud.push_token,
            
            # Estado inicial
            estado='iniciado',
            
            # Timestamps
            #created_at=datetime.now(timezone.utc),
            #updated_at=datetime.now(timezone.utc)
        )
        
        db.add(nueva_solicitud)
        db.commit()
        db.refresh(nueva_solicitud)
        
        return nueva_solicitud
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear solicitud: {str(e)}"
        )


# ============================================
# OBTENER SOLICITUD POR ID
# ============================================

@router.get("/{solicitud_id}", response_model=SolicitudDetalle)
async def obtener_solicitud(
    solicitud_id: int,
    device_id: Optional[str] = None,
    telefono: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Obtener solicitud por ID.
    Requiere device_id o telefono para verificar propiedad.
    """
    solicitud = db.query(SolicitudServicio).filter(
        SolicitudServicio.id == solicitud_id
    ).first()
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    # Verificar que quien consulta es el dueño
    if device_id and solicitud.device_id != device_id:
        if telefono and solicitud.telefono_contacto != telefono:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para ver esta solicitud"
            )
    
    return solicitud


# ============================================
# ACTUALIZAR FECHA/HORA DEL SERVICIO
# ============================================

@router.put("/{solicitud_id}/fecha-hora")
async def actualizar_fecha_hora(
    solicitud_id: int,
    fecha_servicio: str,
    hora_servicio: str,
    device_id: str,
    db: Session = Depends(get_db)
):
    solicitud = db.query(SolicitudServicio).filter(
        SolicitudServicio.id == solicitud_id,
        SolicitudServicio.device_id == device_id
    ).first()
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    try:
        solicitud.fecha_servicio = datetime.fromisoformat(fecha_servicio)
        solicitud.hora_servicio = hora_servicio
        # solicitud.updated_at = datetime.utcnow()  # ← COMENTAR ESTO
        
        db.commit()
        db.refresh(solicitud)  # ← AGREGAR ESTO
        
        return {
            "success": True, 
            "message": "Fecha y hora actualizadas",
            "fecha_servicio": solicitud.fecha_servicio.isoformat() if solicitud.fecha_servicio else None,
            "hora_servicio": solicitud.hora_servicio
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar: {str(e)}"
        )


# ============================================
# ACTUALIZAR MÉTODO DE PAGO
# ============================================

@router.put("/{solicitud_id}/metodo-pago")
async def actualizar_metodo_pago(
    solicitud_id: int,
    metodo_pago: str,
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Actualizar método de pago seleccionado.
    """
    solicitud = db.query(SolicitudServicio).filter(
        SolicitudServicio.id == solicitud_id,
        SolicitudServicio.device_id == device_id
    ).first()
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    solicitud.metodo_pago = metodo_pago
    solicitud.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"success": True, "message": "Método de pago actualizado"}


# ============================================
# CONFIRMAR PAGO
# ============================================

@router.post("/{solicitud_id}/confirmar-pago")
async def confirmar_pago(
    solicitud_id: int,
    referencia_pago: str,
    db: Session = Depends(get_db)
):
    """
    Confirmar que el pago fue exitoso.
    Cambia estado a 'buscando_tecnico'.
    """
    solicitud = db.query(SolicitudServicio).filter(
        SolicitudServicio.id == solicitud_id
    ).first()
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    solicitud.estado_pago = 'pagado'
    solicitud.referencia_pago = referencia_pago
    solicitud.estado = 'buscando_tecnico'
    solicitud.fecha_pago = datetime.now(timezone.utc)
    solicitud.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # TODO: Aquí llamar a función de asignación de técnicos
    # await asignar_tecnico(solicitud_id, db)
    
    return {
        "success": True,
        "message": "Pago confirmado",
        "solicitud_id": solicitud_id,
        "estado": solicitud.estado
    }


# ============================================
# CALIFICAR SERVICIO
# ============================================

@router.post("/{solicitud_id}/calificar")
async def calificar_servicio(
    solicitud_id: int,
    calificacion: int,
    comentario: Optional[str] = None,
    device_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Calificar el servicio completado.
    """
    if calificacion < 1 or calificacion > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calificación debe estar entre 1 y 5"
        )
    
    solicitud = db.query(SolicitudServicio).filter(
        SolicitudServicio.id == solicitud_id
    ).first()
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    if device_id and solicitud.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )
    
    solicitud.calificacion = calificacion
    solicitud.comentario_calificacion = comentario
    solicitud.fecha_calificacion = datetime.now(timezone.utc)
    solicitud.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # TODO: Actualizar rating del técnico
    # if solicitud.tecnico_asignado_id:
    #     actualizar_rating_tecnico(solicitud.tecnico_asignado_id, calificacion, db)
    
    return {"success": True, "message": "Calificación guardada"}


# ============================================
# CHAT - ENVIAR MENSAJE
# ============================================

@router.post("/chat/enviar", status_code=status.HTTP_201_CREATED)
async def enviar_mensaje_chat(
    mensaje: MensajeChatCreate,
    db: Session = Depends(get_db)
):
    """
    Enviar mensaje en el chat de una solicitud.
    """
    # Verificar que la solicitud existe
    solicitud = db.query(SolicitudServicio).filter(
        SolicitudServicio.id == mensaje.solicitud_id
    ).first()
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    nuevo_mensaje = MensajeChatSolicitud(
        solicitud_id=mensaje.solicitud_id,
        emisor_tipo=mensaje.emisor_tipo,
        emisor_id=mensaje.emisor_id,
        mensaje=mensaje.mensaje,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(nuevo_mensaje)
    db.commit()
    db.refresh(nuevo_mensaje)
    
    return nuevo_mensaje


# ============================================
# CHAT - OBTENER MENSAJES
# ============================================

@router.get("/chat/{solicitud_id}/mensajes")
async def obtener_mensajes_chat(
    solicitud_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener todos los mensajes de una solicitud.
    """
    mensajes = db.query(MensajeChatSolicitud).filter(
        MensajeChatSolicitud.solicitud_id == solicitud_id
    ).order_by(MensajeChatSolicitud.created_at.asc()).all()
    
    return mensajes


# ============================================
# MIS SOLICITUDES (POR DEVICE_ID)
# ============================================

@router.get("/mis-solicitudes/{device_id}")
async def obtener_mis_solicitudes(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtener todas las solicitudes de un dispositivo.
    """
    solicitudes = db.query(SolicitudServicio).filter(
        SolicitudServicio.device_id == device_id
    ).order_by(SolicitudServicio.created_at.desc()).all()
    
    return solicitudes