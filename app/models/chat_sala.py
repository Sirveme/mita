"""
Salas y mensajes de chat por servicio (post-asignación de técnico).
Coexiste con el chat legacy (Conversacion/Mensaje en app/models/chat.py).
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func

from app.core.database import Base


class ChatSala(Base):
    __tablename__ = "chat_salas"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), index=True)
    tipo = Column(String(20), nullable=False)   # cliente_tecnico | cliente_admin | admin_tecnico
    titulo = Column(String(120))
    creado_en = Column(DateTime, server_default=func.now())
    estado = Column(String(20), default="activo")


class ChatMensaje(Base):
    __tablename__ = "chat_mensajes"

    id = Column(Integer, primary_key=True, index=True)
    sala_id = Column(Integer, ForeignKey("chat_salas.id"), index=True)
    emisor_id = Column(Integer, ForeignKey("personal.id"))   # null = cliente
    emisor_tipo = Column(String(20), nullable=False)         # cliente | tecnico | admin
    emisor_nombre = Column(String(120))
    mensaje = Column(Text, nullable=False)
    leido = Column(Boolean, default=False)
    creado_en = Column(DateTime, server_default=func.now())
