"""
Endpoints WebSocket para notificaciones en tiempo real
Ubicación: app/routes/websocket.py
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import logging

from app.core.database import get_db
from app.websocket.manager import manager
from app.websocket.handlers import route_message
from app.core.security import decode_token
from app.models.models import Usuario

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_current_user_ws(token: str, db: Session) -> Usuario:
    """
    Valida el token JWT y retorna el usuario actual
    Para uso en WebSocket
    """
    try:
        payload = decode_token(token)
        usuario_id = payload.get("sub")
        
        if not usuario_id:
            raise Exception("Usuario no encontrado en token")
        
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        
        if not usuario:
            raise Exception(f"Usuario {usuario_id} no existe en BD")
        
        return usuario
        
    except Exception as e:
        logger.error(f"Error validando token WS: {e}")
        raise


@router.websocket("/ws/notificaciones")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint WebSocket principal para notificaciones en tiempo real
    
    Uso desde JavaScript:
    ```javascript
    const token = localStorage.getItem('token');
    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/notificaciones?token=${token}`);
    ```
    """
    
    usuario = None
    
    try:
        # Validar usuario
        usuario = await get_current_user_ws(token, db)
        
        if not usuario:
            logger.warning("Usuario no autenticado, cerrando WebSocket")
            await websocket.close(code=1008)  # Policy Violation
            return
        
        # Determinar rol del usuario
        rol = "cliente"  # Por defecto
        if hasattr(usuario, 'tecnico') and usuario.tecnico:
            rol = "tecnico"
        elif hasattr(usuario, 'es_admin') and usuario.es_admin:
            rol = "admin"
        
        # Extraer metadata de la conexión
        metadata = {
            "ip": websocket.client.host if websocket.client else None,
            "user_agent": websocket.headers.get("user-agent"),
        }
        
        # Conectar al manager
        await manager.connect(websocket, usuario.id, rol, metadata)
        
        logger.info(f"✅ Usuario {usuario.id} ({rol}) conectado vía WebSocket")
        
        # Bucle principal - escuchar mensajes del cliente
        while True:
            # Recibir mensaje
            data_str = await websocket.receive_text()
            
            try:
                message = json.loads(data_str)
                message_type = message.get("tipo")
                
                if not message_type:
                    logger.warning(f"Mensaje sin tipo de usuario {usuario.id}")
                    continue
                
                logger.info(f"📩 Mensaje tipo '{message_type}' de usuario {usuario.id}")
                
                # Rutear mensaje al handler apropiado
                await route_message(message_type, message, usuario.id, db)
                    
            except json.JSONDecodeError:
                logger.error(f"Error decodificando JSON de usuario {usuario.id}")
            except Exception as e:
                logger.error(f"Error procesando mensaje de usuario {usuario.id}: {e}")
    
    except WebSocketDisconnect:
        if usuario:
            # Determinar rol nuevamente para desconectar
            rol = "cliente"
            if hasattr(usuario, 'tecnico') and usuario.tecnico:
                rol = "tecnico"
            elif hasattr(usuario, 'es_admin') and usuario.es_admin:
                rol = "admin"
            
            manager.disconnect(websocket, usuario.id, rol)
            logger.info(f"Usuario {usuario.id} desconectado")
    
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        if usuario:
            rol = "cliente"
            if hasattr(usuario, 'tecnico') and usuario.tecnico:
                rol = "tecnico"
            
            manager.disconnect(websocket, usuario.id, rol)