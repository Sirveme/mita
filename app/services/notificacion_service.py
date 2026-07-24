"""
Servicio para crear y enviar notificaciones
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

from app.models.notificaciones import (
    Notificacion, 
    TipoNotificacion, 
    CanalNotificacion,
    EstadoNotificacion,
    EventoAuditoria
)
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


class NotificacionService:
    """
    Servicio centralizado para gestionar notificaciones
    """
    
    @staticmethod
    async def crear_notificacion(
        db: Session,
        usuario_id: int,
        rol_destinatario: str,
        tipo: TipoNotificacion,
        titulo: str,
        mensaje: str,
        canal: CanalNotificacion = CanalNotificacion.PUSH,
        emisor_id: Optional[int] = None,
        rol_emisor: Optional[str] = None,
        metadata: Optional[Dict] = None,
        es_urgente: bool = False,
        prioridad: int = 1,
        accion_url: Optional[str] = None,
        accion_tipo: Optional[str] = None,
        enviar_inmediatamente: bool = True
    ) -> Notificacion:
        """
        Crea una nueva notificación y opcionalmente la envía
        """
        
        # Crear notificación en BD
        notificacion = Notificacion(
            usuario_id=usuario_id,
            rol_destinatario=rol_destinatario,
            emisor_id=emisor_id,
            rol_emisor=rol_emisor,
            tipo=tipo,
            canal=canal,
            titulo=titulo,
            mensaje=mensaje,
            metadata=metadata,
            es_urgente=es_urgente,
            prioridad=prioridad,
            accion_url=accion_url,
            accion_tipo=accion_tipo,
            estado=EstadoNotificacion.PENDIENTE
        )
        
        db.add(notificacion)
        db.commit()
        db.refresh(notificacion)
        
        logger.info(f"Notificación creada: {notificacion.id} para usuario {usuario_id}")
        
        # Enviar si está solicitado
        if enviar_inmediatamente and canal == CanalNotificacion.PUSH:
            await NotificacionService.enviar_push(notificacion)
        
        return notificacion
    
    @staticmethod
    async def enviar_push(notificacion: Notificacion):
        """
        Envía una notificación push via WebSocket
        """
        try:
            # Preparar payload
            payload = {
                "tipo": "notificacion",
                "notificacion_id": notificacion.id,
                "titulo": notificacion.titulo,
                "mensaje": notificacion.mensaje,
                "tipo_notificacion": notificacion.tipo.value,
                "es_urgente": notificacion.es_urgente,
                "prioridad": notificacion.prioridad,
                "accion_url": notificacion.accion_url,
                "accion_tipo": notificacion.accion_tipo,
                "metadata": notificacion.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Enviar via WebSocket si el usuario está conectado
            await manager.send_personal_message(notificacion.usuario_id, payload)
            
            # Actualizar estado
            notificacion.estado = EstadoNotificacion.ENVIADA
            notificacion.enviada_en = datetime.utcnow()
            
            logger.info(f"Notificación push enviada: {notificacion.id}")
            
        except Exception as e:
            logger.error(f"Error enviando notificación push {notificacion.id}: {e}")
            notificacion.estado = EstadoNotificacion.ERROR
    
    @staticmethod
    def marcar_como_leida(db: Session, notificacion_id: int, usuario_id: int):
        """
        Marca una notificación como leída
        """
        notificacion = db.query(Notificacion).filter(
            Notificacion.id == notificacion_id,
            Notificacion.usuario_id == usuario_id
        ).first()
        
        if notificacion:
            notificacion.estado = EstadoNotificacion.LEIDA
            notificacion.leida_en = datetime.utcnow()
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def obtener_no_leidas(db: Session, usuario_id: int) -> List[Notificacion]:
        """
        Obtiene todas las notificaciones no leídas de un usuario
        """
        return db.query(Notificacion).filter(
            Notificacion.usuario_id == usuario_id,
            Notificacion.estado != EstadoNotificacion.LEIDA
        ).order_by(Notificacion.creada_en.desc()).all()
    
    @staticmethod
    def contar_no_leidas(db: Session, usuario_id: int) -> int:
        """
        Cuenta las notificaciones no leídas
        """
        return db.query(Notificacion).filter(
            Notificacion.usuario_id == usuario_id,
            Notificacion.estado != EstadoNotificacion.LEIDA
        ).count()


class AuditoriaService:
    """
    Servicio para registrar eventos de auditoría
    """
    
    @staticmethod
    def registrar_evento(
        db: Session,
        evento_tipo: str,
        evento_categoria: str,
        descripcion: str,
        usuario_id: Optional[int] = None,
        rol_usuario: Optional[str] = None,
        entidad_tipo: Optional[str] = None,
        entidad_id: Optional[int] = None,
        datos_antes: Optional[Dict] = None,
        datos_despues: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        exitoso: bool = True,
        error_mensaje: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> EventoAuditoria:
        """
        Registra un evento de auditoría
        """
        
        evento = EventoAuditoria(
            evento_tipo=evento_tipo,
            evento_categoria=evento_categoria,
            descripcion=descripcion,
            usuario_id=usuario_id,
            rol_usuario=rol_usuario,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            metadata=metadata,
            exitoso=exitoso,
            error_mensaje=error_mensaje,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(evento)
        db.commit()
        
        logger.info(f"Evento de auditoría registrado: {evento_tipo}")
        
        return evento