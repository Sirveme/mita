"""
API REST del chat MITA (persistencia / carga de historial).
Complementa el WebSocket (chat_ws.py) y el chat.py legacy (stubs con auth).
Montado en main.py con prefix="/api/v1"  →  /api/v1/chat/...

Rutas (flujo anónimo, sin auth):
  POST /chat/conversacion                              -> crea/obtiene conversación por solicitud
  GET  /chat/conversacion/{conversacion_id}/mensajes   -> historial (usado por chat.js)
  POST /chat/conversacion/{conversacion_id}/mensajes   -> enviar mensaje (fallback sin WS)
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat import (
    Conversacion, Mensaje, TipoParticipante, TipoMensaje, EstadoMensaje, EstadoConversacion,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ============================================
# SCHEMAS
# ============================================

class ConversacionCreate(BaseModel):
    solicitud_id: int
    cliente_id: Optional[int] = None
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None


class MensajeCreate(BaseModel):
    de_tipo: str                     # cliente | secretaria | tecnico | bot | sistema
    de_id: Optional[int] = None
    de_nombre: Optional[str] = None
    contenido: Optional[str] = None
    tipo_mensaje: str = "texto"
    archivo_url: Optional[str] = None


def _mensaje_dict(m: Mensaje) -> dict:
    return {
        "id": m.id,
        "de_tipo": m.de_tipo.value if m.de_tipo else None,
        "de_id": m.de_id,
        "de_nombre": m.de_nombre,
        "tipo": m.tipo.value if m.tipo else "texto",
        "tipo_mensaje": m.tipo.value if m.tipo else "texto",
        "contenido": m.contenido,
        "archivo_url": m.archivo_url,
        "ubicacion_lat": m.ubicacion_lat,
        "ubicacion_lng": m.ubicacion_lng,
        "ubicacion_nombre": m.ubicacion_nombre,
        "estado": m.estado.value if m.estado else "enviado",
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "timestamp": m.created_at.isoformat() if m.created_at else None,
    }


# ============================================
# ENDPOINTS
# ============================================

@router.post("/conversacion")
async def crear_o_obtener_conversacion(payload: ConversacionCreate, db: Session = Depends(get_db)):
    """Crea (o devuelve la existente) la conversación de una solicitud."""
    conv = (
        db.query(Conversacion)
        .filter(Conversacion.solicitud_id == payload.solicitud_id)
        .first()
    )
    if conv is None:
        conv = Conversacion(
            solicitud_id=payload.solicitud_id,
            cliente_id=payload.cliente_id,
            cliente_nombre=payload.cliente_nombre,
            cliente_telefono=payload.cliente_telefono,
            estado=EstadoConversacion.ACTIVA,
            fase_actual=1,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    return {
        "success": True,
        "conversacion_id": conv.id,
        "solicitud_id": conv.solicitud_id,
        "estado": conv.estado.value if conv.estado else None,
        "fase_actual": conv.fase_actual,
    }


@router.get("/conversacion/{conversacion_id}/mensajes")
async def obtener_mensajes(
    conversacion_id: int,
    limite: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Historial de mensajes de una conversación (consumido por chat.js)."""
    conv = db.query(Conversacion).get(conversacion_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    mensajes = (
        db.query(Mensaje)
        .filter(Mensaje.conversacion_id == conversacion_id)
        .order_by(Mensaje.created_at.asc())
        .offset(offset)
        .limit(limite)
        .all()
    )
    return {
        "success": True,
        "conversacion_id": conversacion_id,
        "total": len(mensajes),
        "mensajes": [_mensaje_dict(m) for m in mensajes],
    }


@router.post("/conversacion/{conversacion_id}/mensajes")
async def enviar_mensaje(conversacion_id: int, payload: MensajeCreate, db: Session = Depends(get_db)):
    """Persiste un mensaje (fallback REST cuando no hay WebSocket)."""
    conv = db.query(Conversacion).get(conversacion_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    de_tipo = payload.de_tipo if payload.de_tipo in TipoParticipante._value2member_map_ else "sistema"
    tipo_msg = payload.tipo_mensaje if payload.tipo_mensaje in TipoMensaje._value2member_map_ else "texto"

    msg = Mensaje(
        conversacion_id=conversacion_id,
        de_tipo=TipoParticipante(de_tipo),
        de_id=payload.de_id,
        de_nombre=payload.de_nombre,
        tipo=TipoMensaje(tipo_msg),
        contenido=payload.contenido,
        archivo_url=payload.archivo_url,
        estado=EstadoMensaje.ENVIADO,
    )
    db.add(msg)

    conv.ultimo_mensaje_texto = (payload.contenido or "")[:200]
    conv.ultimo_mensaje_at = datetime.utcnow()
    conv.ultimo_mensaje_de = TipoParticipante(de_tipo)

    db.commit()
    db.refresh(msg)

    return {"success": True, "mensaje": _mensaje_dict(msg)}
