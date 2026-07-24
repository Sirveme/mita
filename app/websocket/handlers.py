"""
Handlers de mensajes WebSocket
Ubicación: app/websocket/handlers.py
"""

from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.websocket.manager import manager
from app.models.models import Servicio, Usuario, MensajeChat
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Manejador de mensajes WebSocket
    Procesa diferentes tipos de mensajes del cliente
    """
    
    @staticmethod
    async def handle_ping(data: Dict[str, Any], usuario_id: int, db: Session):
        """
        Responder a ping con pong (heartbeat)
        """
        await manager.send_personal_message(usuario_id, {
            "tipo": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    @staticmethod
    async def handle_chat_message(data: Dict[str, Any], usuario_id: int, db: Session):
        """
        Procesar mensaje de chat
        
        Esperado en data:
        - destinatario_id: int
        - mensaje: str
        - servicio_id: int (opcional)
        """
        destinatario_id = data.get("destinatario_id")
        mensaje_texto = data.get("mensaje")
        servicio_id = data.get("servicio_id")
        
        if not destinatario_id or not mensaje_texto:
            logger.warning(f"Mensaje de chat incompleto de usuario {usuario_id}")
            return
        
        # Obtener datos del emisor
        emisor = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not emisor:
            logger.error(f"Usuario {usuario_id} no encontrado")
            return
        
        # Guardar mensaje en BD
        nuevo_mensaje = MensajeChat(
            servicio_id=servicio_id,
            emisor_id=usuario_id,
            receptor_id=destinatario_id,
            mensaje=mensaje_texto,
            leido=False
        )
        db.add(nuevo_mensaje)
        db.commit()
        db.refresh(nuevo_mensaje)
        
        # Enviar al destinatario
        await manager.send_personal_message(destinatario_id, {
            "tipo": "chat_message",
            "mensaje_id": nuevo_mensaje.id,
            "emisor_id": usuario_id,
            "emisor_nombre": emisor.nombre_completo,
            "mensaje": mensaje_texto,
            "servicio_id": servicio_id,
            "timestamp": nuevo_mensaje.created_at.isoformat(),
            "leido": False
        })
        
        logger.info(f"Mensaje de chat enviado: {usuario_id} → {destinatario_id}")
    
    @staticmethod
    async def handle_typing_indicator(data: Dict[str, Any], usuario_id: int, db: Session):
        """
        Indicador de "está escribiendo..."
        """
        destinatario_id = data.get("destinatario_id")
        escribiendo = data.get("escribiendo", True)
        
        if not destinatario_id:
            return
        
        await manager.send_personal_message(destinatario_id, {
            "tipo": "typing",
            "usuario_id": usuario_id,
            "escribiendo": escribiendo
        })
    
    @staticmethod
    async def handle_location_update(data: Dict[str, Any], usuario_id: int, db: Session):
        """
        Actualización de ubicación del técnico
        
        Esperado en data:
        - servicio_id: int
        - latitude: float
        - longitude: float
        """
        servicio_id = data.get("servicio_id")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        
        if not all([servicio_id, latitude, longitude]):
            logger.warning(f"Datos de ubicación incompletos de usuario {usuario_id}")
            return
        
        # Obtener servicio
        servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
        if not servicio:
            logger.error(f"Servicio {servicio_id} no encontrado")
            return
        
        # Verificar que el usuario es el técnico asignado
        if servicio.tecnico_id != usuario_id:
            logger.warning(f"Usuario {usuario_id} no es técnico del servicio {servicio_id}")
            return
        
        # TODO: Guardar ubicación en BD (tabla historial_ubicaciones)
        
        # Notificar al cliente
        if servicio.cliente_id:
            await manager.send_personal_message(servicio.cliente_id, {
                "tipo": "ubicacion_tecnico",
                "servicio_id": servicio_id,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        logger.info(f"Ubicación actualizada: servicio {servicio_id}")
    
    @staticmethod
    async def handle_accept_service(data: Dict[str, Any], usuario_id: int, db: Session):
        """
        Técnico acepta un servicio
        
        Esperado en data:
        - servicio_id: int
        """
        servicio_id = data.get("servicio_id")
        
        if not servicio_id:
            logger.warning(f"servicio_id faltante en aceptar_servicio de usuario {usuario_id}")
            return
        
        # Obtener servicio
        servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
        if not servicio:
            logger.error(f"Servicio {servicio_id} no encontrado")
            await manager.send_personal_message(usuario_id, {
                "tipo": "error",
                "mensaje": "Servicio no encontrado"
            })
            return
        
        # Verificar que está disponible
        if servicio.estado != "pendiente":
            await manager.send_personal_message(usuario_id, {
                "tipo": "error",
                "mensaje": "Servicio ya fue tomado por otro técnico"
            })
            return
        
        # Asignar técnico
        servicio.tecnico_id = usuario_id
        servicio.estado = "asignado"
        servicio.fecha_asignacion = datetime.utcnow()
        db.commit()
        
        # Obtener datos del técnico
        tecnico = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        
        # Notificar al técnico (confirmación)
        await manager.send_personal_message(usuario_id, {
            "tipo": "servicio_aceptado",
            "servicio_id": servicio_id,
            "mensaje": "Servicio asignado exitosamente"
        })
        
        # Notificar al cliente
        if servicio.cliente_id:
            await manager.send_personal_message(servicio.cliente_id, {
                "tipo": "tecnico_asignado",
                "servicio_id": servicio_id,
                "tecnico": {
                    "id": tecnico.id,
                    "nombre": tecnico.nombre_completo,
                    "telefono": tecnico.telefono,
                    "foto": getattr(tecnico, 'foto_perfil_url', None),
                    "calificacion": getattr(tecnico.tecnico, 'calificacion_promedio', 5.0) if hasattr(tecnico, 'tecnico') else 5.0
                },
                "tiempo_estimado": 30  # TODO: Calcular basado en distancia
            })
        
        # Notificar a otros técnicos que el servicio ya fue tomado
        # TODO: Obtener otros técnicos que recibieron notificación
        
        logger.info(f"Servicio {servicio_id} aceptado por técnico {usuario_id}")
    
    @staticmethod
    async def handle_reject_service(data: Dict[str, Any], usuario_id: int, db: Session):
        """
        Técnico rechaza un servicio
        """
        servicio_id = data.get("servicio_id")
        motivo = data.get("motivo")
        
        if not servicio_id:
            return
        
        # TODO: Registrar rechazo en BD
        # TODO: Notificar a siguiente técnico en la lista
        
        logger.info(f"Servicio {servicio_id} rechazado por técnico {usuario_id}: {motivo}")
    
    @staticmethod
    async def handle_service_status_update(data: Dict[str, Any], usuario_id: int, db: Session):
        """
        Actualización de estado del servicio
        
        Esperado en data:
        - servicio_id: int
        - nuevo_estado: str (en_camino, llegado, en_proceso, completado)
        - notas: str (opcional)
        """
        servicio_id = data.get("servicio_id")
        nuevo_estado = data.get("nuevo_estado")
        notas = data.get("notas")
        
        if not servicio_id or not nuevo_estado:
            return
        
        # Obtener servicio
        servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
        if not servicio:
            return
        
        # Verificar que el usuario es el técnico
        if servicio.tecnico_id != usuario_id:
            logger.warning(f"Usuario {usuario_id} intentó actualizar servicio {servicio_id} que no le pertenece")
            return
        
        # Actualizar estado
        estado_anterior = servicio.estado
        servicio.estado = nuevo_estado
        
        # TODO: Registrar en historial de estados
        
        db.commit()
        
        # Mensajes amigables según estado
        mensajes_estado = {
            "en_camino": "El técnico está en camino",
            "llegado": "El técnico ha llegado a tu ubicación",
            "en_proceso": "El servicio está en progreso",
            "completado": "El servicio ha sido completado"
        }
        
        # Notificar al cliente
        if servicio.cliente_id:
            await manager.send_personal_message(servicio.cliente_id, {
                "tipo": "estado_servicio_actualizado",
                "servicio_id": servicio_id,
                "estado_anterior": estado_anterior,
                "estado_nuevo": nuevo_estado,
                "mensaje": mensajes_estado.get(nuevo_estado, "Estado actualizado"),
                "notas": notas,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        logger.info(f"Servicio {servicio_id} actualizado: {estado_anterior} → {nuevo_estado}")


# ============================================
# ROUTER DE MENSAJES
# ============================================

MESSAGE_HANDLERS = {
    "ping": WebSocketHandler.handle_ping,
    "chat": WebSocketHandler.handle_chat_message,
    "typing": WebSocketHandler.handle_typing_indicator,
    "ubicacion": WebSocketHandler.handle_location_update,
    "aceptar_servicio": WebSocketHandler.handle_accept_service,
    "rechazar_servicio": WebSocketHandler.handle_reject_service,
    "estado_servicio": WebSocketHandler.handle_service_status_update,
}


async def route_message(message_type: str, data: Dict[str, Any], usuario_id: int, db: Session):
    """
    Rutea un mensaje al handler apropiado
    """
    handler = MESSAGE_HANDLERS.get(message_type)
    
    if handler:
        await handler(data, usuario_id, db)
    else:
        logger.warning(f"Tipo de mensaje desconocido: {message_type}")