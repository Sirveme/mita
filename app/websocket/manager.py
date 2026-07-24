"""
WebSocket Connection Manager
Gestiona todas las conexiones WebSocket activas
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestor de conexiones WebSocket
    
    Mantiene un registro de todas las conexiones activas
    organizadas por usuario_id y rol
    """
    
    def __init__(self):
        # Conexiones activas por usuario_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
        
        # Conexiones por rol
        self.connections_by_role: Dict[str, Set[int]] = {
            "cliente": set(),
            "tecnico": set(),
            "admin": set(),
            "proveedor": set()
        }
        
        # Metadata de conexiones
        self.connection_metadata: Dict[str, dict] = {}
        
    async def connect(self, websocket: WebSocket, usuario_id: int, rol: str, metadata: dict = None):
        """
        Acepta una nueva conexión WebSocket
        """
        await websocket.accept()
        
        # Agregar a lista de conexiones del usuario
        if usuario_id not in self.active_connections:
            self.active_connections[usuario_id] = []
        self.active_connections[usuario_id].append(websocket)
        
        # Agregar a conexiones por rol
        self.connections_by_role[rol].add(usuario_id)
        
        # Guardar metadata
        connection_id = f"{usuario_id}_{id(websocket)}"
        self.connection_metadata[connection_id] = {
            "usuario_id": usuario_id,
            "rol": rol,
            "conectado_en": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        logger.info(f"Usuario {usuario_id} ({rol}) conectado. Total conexiones: {self.get_total_connections()}")
        
        # Notificar al usuario sobre conexión exitosa
        await self.send_personal_message(usuario_id, {
            "tipo": "sistema",
            "evento": "conectado",
            "mensaje": "Conexión establecida exitosamente",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket, usuario_id: int, rol: str):
        """
        Desconecta un WebSocket
        """
        if usuario_id in self.active_connections:
            if websocket in self.active_connections[usuario_id]:
                self.active_connections[usuario_id].remove(websocket)
            
            # Si no quedan conexiones para este usuario, eliminar de diccionario
            if not self.active_connections[usuario_id]:
                del self.active_connections[usuario_id]
                self.connections_by_role[rol].discard(usuario_id)
        
        # Limpiar metadata
        connection_id = f"{usuario_id}_{id(websocket)}"
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        logger.info(f"Usuario {usuario_id} ({rol}) desconectado. Total conexiones: {self.get_total_connections()}")
    
    async def send_personal_message(self, usuario_id: int, message: dict):
        """
        Envía un mensaje a un usuario específico (todas sus conexiones)
        """
        if usuario_id in self.active_connections:
            message_json = json.dumps(message)
            disconnected = []
            
            for connection in self.active_connections[usuario_id]:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error enviando mensaje a usuario {usuario_id}: {e}")
                    disconnected.append(connection)
            
            # Limpiar conexiones muertas
            for conn in disconnected:
                self.active_connections[usuario_id].remove(conn)
    
    async def send_to_role(self, rol: str, message: dict):
        """
        Envía un mensaje a todos los usuarios de un rol específico
        """
        if rol in self.connections_by_role:
            tasks = []
            for usuario_id in self.connections_by_role[rol]:
                tasks.append(self.send_personal_message(usuario_id, message))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast(self, message: dict, exclude_user: int = None):
        """
        Envía un mensaje a todos los usuarios conectados
        """
        tasks = []
        for usuario_id in self.active_connections.keys():
            if exclude_user and usuario_id == exclude_user:
                continue
            tasks.append(self.send_personal_message(usuario_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def is_user_online(self, usuario_id: int) -> bool:
        """
        Verifica si un usuario tiene al menos una conexión activa
        """
        return usuario_id in self.active_connections and len(self.active_connections[usuario_id]) > 0
    
    def get_total_connections(self) -> int:
        """
        Retorna el número total de conexiones activas
        """
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_users_online_by_role(self, rol: str) -> int:
        """
        Retorna el número de usuarios online de un rol específico
        """
        return len(self.connections_by_role.get(rol, set()))


# Instancia global del manager
manager = ConnectionManager()