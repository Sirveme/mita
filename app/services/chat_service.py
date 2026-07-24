"""
Servicio para gestionar el chat vinculado a servicios
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from typing import Optional, List, Dict
import logging

from app.models.chat import (
    ConversacionServicio,
    MensajeChat,
    TipoMensaje,
    EstadoChat,
    ReporteChat
)
from app.models.servicio import Servicio, EstadoServicio
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


class ChatService:
    """
    Servicio para gestionar conversaciones y mensajes de chat
    """
    
    @staticmethod
    def crear_conversacion(
        db: Session,
        servicio_id: int,
        cliente_id: int,
        tecnico_id: int
    ) -> ConversacionServicio:
        """
        Crea una conversación cuando el técnico acepta el servicio
        """
        
        # Verificar que no exista ya una conversación para este servicio
        conversacion_existente = db.query(ConversacionServicio).filter(
            ConversacionServicio.servicio_id == servicio_id
        ).first()
        
        if conversacion_existente:
            logger.warning(f"Ya existe una conversación para el servicio {servicio_id}")
            return conversacion_existente
        
        # Crear conversación
        conversacion = ConversacionServicio(
            servicio_id=servicio_id,
            cliente_id=cliente_id,
            tecnico_id=tecnico_id,
            estado=EstadoChat.ACTIVO
        )
        
        db.add(conversacion)
        db.commit()
        db.refresh(conversacion)
        
        # Crear mensaje automático del sistema
        mensaje_bienvenida = MensajeChat(
            conversacion_id=conversacion.id,
            emisor_id=tecnico_id,  # Técnicamente el sistema, pero usamos tecnico_id
            rol_emisor="sistema",
            tipo=TipoMensaje.SISTEMA,
            contenido=f"Chat iniciado. Ahora pueden comunicarse durante el servicio.",
            enviado=True,
            entregado=True,
            leido=True
        )
        
        db.add(mensaje_bienvenida)
        conversacion.total_mensajes = 1
        conversacion.ultimo_mensaje_en = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Conversación creada para servicio {servicio_id}")
        
        return conversacion
    
    @staticmethod
    async def enviar_mensaje(
        db: Session,
        conversacion_id: int,
        emisor_id: int,
        contenido: str,
        tipo: TipoMensaje = TipoMensaje.TEXTO,
        archivo_url: Optional[str] = None,
        archivo_nombre: Optional[str] = None,
        archivo_tipo: Optional[str] = None,
        archivo_tamano: Optional[int] = None,
        latitud: Optional[str] = None,
        longitud: Optional[str] = None,
        direccion: Optional[str] = None,
        respondiendo_a: Optional[int] = None
    ) -> Optional[MensajeChat]:
        """
        Envía un mensaje en el chat
        """
        
        # Obtener conversación
        conversacion = db.query(ConversacionServicio).filter(
            ConversacionServicio.id == conversacion_id
        ).first()
        
        if not conversacion:
            logger.error(f"Conversación {conversacion_id} no encontrada")
            return None
        
        # Verificar que el chat esté activo
        if conversacion.estado != EstadoChat.ACTIVO:
            logger.warning(f"Conversación {conversacion_id} no está activa")
            return None
        
        # Verificar que el emisor sea participante
        if emisor_id not in [conversacion.cliente_id, conversacion.tecnico_id]:
            logger.error(f"Usuario {emisor_id} no es participante de la conversación {conversacion_id}")
            return None
        
        # Determinar rol del emisor
        rol_emisor = "cliente" if emisor_id == conversacion.cliente_id else "tecnico"
        
        # Crear mensaje
        mensaje = MensajeChat(
            conversacion_id=conversacion_id,
            emisor_id=emisor_id,
            rol_emisor=rol_emisor,
            tipo=tipo,
            contenido=contenido,
            archivo_url=archivo_url,
            archivo_nombre=archivo_nombre,
            archivo_tipo=archivo_tipo,
            archivo_tamano=archivo_tamano,
            latitud=latitud,
            longitud=longitud,
            direccion=direccion,
            respondiendo_a=respondiendo_a,
            enviado=True
        )
        
        db.add(mensaje)
        
        # Actualizar conversación
        conversacion.total_mensajes += 1
        conversacion.ultimo_mensaje_en = datetime.utcnow()
        conversacion.ultimo_mensaje_id = mensaje.id
        
        # Incrementar contador de no leídos del receptor
        if rol_emisor == "cliente":
            conversacion.no_leidos_tecnico += 1
            destinatario_id = conversacion.tecnico_id
        else:
            conversacion.no_leidos_cliente += 1
            destinatario_id = conversacion.cliente_id
        
        db.commit()
        db.refresh(mensaje)
        
        # Enviar via WebSocket al destinatario
        await ChatService._enviar_mensaje_websocket(
            destinatario_id=destinatario_id,
            mensaje=mensaje,
            conversacion=conversacion
        )
        
        logger.info(f"Mensaje enviado en conversación {conversacion_id}")
        
        return mensaje
    
    @staticmethod
    async def _enviar_mensaje_websocket(
        destinatario_id: int,
        mensaje: MensajeChat,
        conversacion: ConversacionServicio
    ):
        """
        Envía el mensaje via WebSocket al destinatario
        """
        try:
            payload = {
                "tipo": "chat",
                "evento": "nuevo_mensaje",
                "conversacion_id": conversacion.id,
                "servicio_id": conversacion.servicio_id,
                "mensaje": {
                    "id": mensaje.id,
                    "emisor_id": mensaje.emisor_id,
                    "rol_emisor": mensaje.rol_emisor,
                    "tipo_mensaje": mensaje.tipo.value,
                    "contenido": mensaje.contenido,
                    "archivo_url": mensaje.archivo_url,
                    "archivo_nombre": mensaje.archivo_nombre,
                    "creado_en": mensaje.creado_en.isoformat(),
                    "respondiendo_a": mensaje.respondiendo_a
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await manager.send_personal_message(destinatario_id, payload)
            
            # Marcar como entregado si el usuario está online
            if manager.is_user_online(destinatario_id):
                mensaje.entregado = True
                mensaje.entregado_en = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error enviando mensaje via WebSocket: {e}")
    
    @staticmethod
    def marcar_mensajes_como_leidos(
        db: Session,
        conversacion_id: int,
        usuario_id: int
    ):
        """
        Marca todos los mensajes no leídos como leídos
        """
        
        conversacion = db.query(ConversacionServicio).filter(
            ConversacionServicio.id == conversacion_id
        ).first()
        
        if not conversacion:
            return
        
        # Determinar si es cliente o técnico
        es_cliente = usuario_id == conversacion.cliente_id
        
        # Actualizar mensajes
        mensajes_no_leidos = db.query(MensajeChat).filter(
            and_(
                MensajeChat.conversacion_id == conversacion_id,
                MensajeChat.emisor_id != usuario_id,
                MensajeChat.leido == False
            )
        ).all()
        
        for mensaje in mensajes_no_leidos:
            mensaje.leido = True
            mensaje.leido_en = datetime.utcnow()
        
        # Resetear contador
        if es_cliente:
            conversacion.no_leidos_cliente = 0
        else:
            conversacion.no_leidos_tecnico = 0
        
        db.commit()
        
        logger.info(f"Mensajes marcados como leídos en conversación {conversacion_id}")
    
    @staticmethod
    def cerrar_conversacion(
        db: Session,
        servicio_id: int,
        razon: str = "servicio_finalizado"
    ):
        """
        Cierra la conversación cuando el servicio termina/cancela
        """
        
        conversacion = db.query(ConversacionServicio).filter(
            ConversacionServicio.servicio_id == servicio_id
        ).first()
        
        if not conversacion:
            return
        
        if conversacion.estado == EstadoChat.CERRADO:
            logger.warning(f"Conversación {conversacion.id} ya está cerrada")
            return
        
        # Cerrar conversación
        conversacion.estado = EstadoChat.CERRADO
        conversacion.cerrada_en = datetime.utcnow()
        
        # Mensaje automático de cierre
        mensaje_cierre = MensajeChat(
            conversacion_id=conversacion.id,
            emisor_id=conversacion.tecnico_id,
            rol_emisor="sistema",
            tipo=TipoMensaje.SISTEMA,
            contenido=f"Chat cerrado. Motivo: {razon}",
            enviado=True,
            entregado=True,
            leido=True
        )
        
        db.add(mensaje_cierre)
        conversacion.total_mensajes += 1
        
        db.commit()
        
        logger.info(f"Conversación {conversacion.id} cerrada por {razon}")
    
    @staticmethod
    def obtener_conversacion_por_servicio(
        db: Session,
        servicio_id: int,
        usuario_id: int
    ) -> Optional[ConversacionServicio]:
        """
        Obtiene la conversación de un servicio
        Valida que el usuario sea participante
        """
        
        conversacion = db.query(ConversacionServicio).filter(
            ConversacionServicio.servicio_id == servicio_id
        ).first()
        
        if not conversacion:
            return None
        
        # Verificar que el usuario sea participante
        if usuario_id not in [conversacion.cliente_id, conversacion.tecnico_id]:
            logger.warning(f"Usuario {usuario_id} intenta acceder a conversación {conversacion.id} sin permiso")
            return None
        
        return conversacion
    
    @staticmethod
    def obtener_mensajes(
        db: Session,
        conversacion_id: int,
        usuario_id: int,
        limite: int = 50,
        offset: int = 0
    ) -> List[MensajeChat]:
        """
        Obtiene los mensajes de una conversación
        """
        
        # Verificar acceso
        conversacion = db.query(ConversacionServicio).filter(
            ConversacionServicio.id == conversacion_id
        ).first()
        
        if not conversacion:
            return []
        
        if usuario_id not in [conversacion.cliente_id, conversacion.tecnico_id]:
            return []
        
        # Obtener mensajes
        mensajes = db.query(MensajeChat).filter(
            and_(
                MensajeChat.conversacion_id == conversacion_id,
                MensajeChat.eliminado == False
            )
        ).order_by(MensajeChat.creado_en.desc()).limit(limite).offset(offset).all()
        
        return list(reversed(mensajes))  # Ordenar de más antiguo a más reciente
    
    @staticmethod
    def reportar_mensaje(
        db: Session,
        conversacion_id: int,
        mensaje_id: int,
        reportado_por: int,
        usuario_reportado_id: int,
        razon: str,
        descripcion: str
    ) -> ReporteChat:
        """
        Crea un reporte de comportamiento inadecuado
        """
        
        reporte = ReporteChat(
            conversacion_id=conversacion_id,
            mensaje_id=mensaje_id,
            reportado_por=reportado_por,
            usuario_reportado_id=usuario_reportado_id,
            razon=razon,
            descripcion=descripcion
        )
        
        db.add(reporte)
        db.commit()
        db.refresh(reporte)
        
        logger.info(f"Reporte creado: {reporte.id} para mensaje {mensaje_id}")
        
        return reporte
    
    @staticmethod
    def puede_chatear(db: Session, servicio_id: int) -> bool:
        """
        Verifica si el chat está disponible para un servicio
        """
        
        servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
        
        if not servicio:
            return False
        
        # El chat solo está disponible en estos estados
        estados_permitidos = [
            EstadoServicio.ACEPTADO,
            EstadoServicio.EN_CAMINO,
            EstadoServicio.INICIADO,
            EstadoServicio.PAUSADO
        ]
        
        return servicio.estado in estados_permitidos