"""Base de conocimiento editable para el chat IA (zMita-22): horarios, garantía, etc."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func

from app.core.database import Base


class ChatConocimiento(Base):
    __tablename__ = "chat_conocimiento"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(60), unique=True, nullable=False, index=True)
    titulo = Column(String(150), nullable=False)
    contenido = Column(Text, default="")
    activo = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
