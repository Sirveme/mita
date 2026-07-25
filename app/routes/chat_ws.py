"""
WebSocket para chat en tiempo real (MITA)
Archivo NUEVO e independiente de routes/websocket.py (notificaciones).
Ruta base: /ws/chat/{conversacion_id}/{user_type}/{user_id}
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from datetime import datetime

from app.core.database import SessionLocal
from app.models.chat import Conversacion, Mensaje, TipoParticipante, TipoMensaje, EstadoMensaje

router = APIRouter()


class ChatConnectionManager:
    """Gestiona conexiones WebSocket agrupadas por conversación."""

    def __init__(self):
        # {conversacion_id: {user_key: websocket}}
        self.conversaciones: Dict[int, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversacion_id: int, user_key: str):
        await websocket.accept()
        self.conversaciones.setdefault(conversacion_id, {})[user_key] = websocket

    def disconnect(self, conversacion_id: int, user_key: str):
        if conversacion_id in self.conversaciones:
            self.conversaciones[conversacion_id].pop(user_key, None)
            if not self.conversaciones[conversacion_id]:
                del self.conversaciones[conversacion_id]

    async def broadcast(self, conversacion_id: int, message: dict, exclude_key: str = None):
        for user_key, ws in list(self.conversaciones.get(conversacion_id, {}).items()):
            if user_key != exclude_key:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ChatConnectionManager()


def _persistir_mensaje(conversacion_id: int, user_type: str, user_id: int, data: dict):
    """Guarda el mensaje en BD (best-effort). Devuelve el id real o None."""
    db = SessionLocal()
    try:
        msg = Mensaje(
            conversacion_id=conversacion_id,
            de_tipo=TipoParticipante(user_type) if user_type in TipoParticipante._value2member_map_ else TipoParticipante.SISTEMA,
            de_id=user_id,
            de_nombre=data.get("de_nombre"),
            tipo=TipoMensaje(data.get("tipo_mensaje", "texto")) if data.get("tipo_mensaje", "texto") in TipoMensaje._value2member_map_ else TipoMensaje.TEXTO,
            contenido=data.get("contenido"),
            estado=EstadoMensaje.ENVIADO,
        )
        db.add(msg)
        # Actualizar preview de la conversación
        conv = db.query(Conversacion).get(conversacion_id)
        if conv is not None:
            conv.ultimo_mensaje_texto = (data.get("contenido") or "")[:200]
            conv.ultimo_mensaje_at = datetime.utcnow()
        db.commit()
        db.refresh(msg)
        return msg.id
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


@router.websocket("/ws/chat/{conversacion_id}/{user_type}/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversacion_id: int,
    user_type: str,   # cliente | secretaria | tecnico
    user_id: int,
):
    """WebSocket para chat en tiempo real."""
    user_key = f"{user_type}_{user_id}"
    await manager.connect(websocket, conversacion_id, user_key)

    try:
        await manager.broadcast(
            conversacion_id,
            {
                "type": "user_joined",
                "user_type": user_type,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            exclude_key=user_key,
        )

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "mensaje":
                real_id = _persistir_mensaje(conversacion_id, user_type, user_id, data)
                await manager.broadcast(
                    conversacion_id,
                    {
                        "type": "nuevo_mensaje",
                        "mensaje": {
                            "id": real_id if real_id is not None else data.get("temp_id"),
                            "temp_id": data.get("temp_id"),
                            "de_tipo": user_type,
                            "de_id": user_id,
                            "de_nombre": data.get("de_nombre"),
                            "contenido": data.get("contenido"),
                            "tipo_mensaje": data.get("tipo_mensaje", "texto"),
                            "timestamp": datetime.utcnow().isoformat(),
                            "estado": "enviado",
                        },
                    },
                )

            elif event_type == "typing":
                await manager.broadcast(
                    conversacion_id,
                    {
                        "type": "typing",
                        "user_type": user_type,
                        "user_id": user_id,
                        "is_typing": data.get("is_typing", True),
                    },
                    exclude_key=user_key,
                )

            elif event_type == "leido":
                mensaje_ids = data.get("mensaje_ids", [])
                await manager.broadcast(
                    conversacion_id,
                    {
                        "type": "mensajes_leidos",
                        "mensaje_ids": mensaje_ids,
                        "leido_por": user_type,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    exclude_key=user_key,
                )

    except WebSocketDisconnect:
        manager.disconnect(conversacion_id, user_key)
        await manager.broadcast(
            conversacion_id,
            {
                "type": "user_left",
                "user_type": user_type,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
