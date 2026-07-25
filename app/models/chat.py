"""
Sistema de Chat MITA - Estilo WhatsApp
- Conversaciones por solicitud
- Mensajes con estados de lectura
- Soporte multimedia
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class TipoParticipante(str, enum.Enum):
    CLIENTE = "cliente"
    SECRETARIA = "secretaria"
    TECNICO = "tecnico"
    BOT = "bot"
    SISTEMA = "sistema"


class EstadoConversacion(str, enum.Enum):
    ACTIVA = "activa"
    EN_ESPERA = "en_espera"
    CERRADA = "cerrada"
    ARCHIVADA = "archivada"


class EstadoMensaje(str, enum.Enum):
    ENVIANDO = "enviando"      # ⏳ Reloj
    ENVIADO = "enviado"        # ✓ Un check
    ENTREGADO = "entregado"    # ✓✓ Dos checks grises
    LEIDO = "leido"            # ✓✓ Dos checks azules
    FALLIDO = "fallido"        # ❌ Error


class TipoMensaje(str, enum.Enum):
    TEXTO = "texto"
    IMAGEN = "imagen"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENTO = "documento"
    UBICACION = "ubicacion"
    SISTEMA = "sistema"  # Mensajes automáticos del sistema


class Conversacion(Base):
    """
    Una conversación por solicitud de servicio.
    Participantes: Cliente + Secretaria + Técnico (cuando se asigna)
    """
    __tablename__ = "conversaciones"

    id = Column(Integer, primary_key=True, index=True)

    # Referencia a la solicitud
    solicitud_id = Column(Integer, ForeignKey("solicitudes_servicio.id"), nullable=False, index=True)

    # Participantes
    cliente_id = Column(Integer, ForeignKey("clientes.id"), index=True)
    cliente_nombre = Column(String(150))  # Para clientes no registrados
    cliente_telefono = Column(String(20), index=True)
    secretaria_id = Column(Integer, ForeignKey("secretarias.id"))
    tecnico_id = Column(Integer, ForeignKey("tecnicos_personal.id"))  # coexistencia: técnico de personal

    # Estado
    estado = Column(Enum(EstadoConversacion), default=EstadoConversacion.ACTIVA)

    # Contadores para badge de no leídos
    no_leidos_cliente = Column(Integer, default=0)
    no_leidos_secretaria = Column(Integer, default=0)
    no_leidos_tecnico = Column(Integer, default=0)

    # Último mensaje (para preview en lista)
    ultimo_mensaje_texto = Column(String(200))
    ultimo_mensaje_at = Column(DateTime)
    ultimo_mensaje_de = Column(Enum(TipoParticipante))

    # Fases de comunicación permitida
    # Fase 1: Cliente ↔ Secretaria (antes de asignar técnico)
    # Fase 2: Secretaria ↔ Técnico (asignación)
    # Fase 3: Cliente ↔ Técnico (servicio en curso)
    # Fase 4: Cliente ↔ Secretaria (post-servicio)
    fase_actual = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cerrada_at = Column(DateTime)

    # Relaciones
    mensajes = relationship("Mensaje", back_populates="conversacion", order_by="Mensaje.created_at")
    # Relación one-way hacia la solicitud (sin back_populates para no editar SolicitudServicio)
    solicitud = relationship("SolicitudServicio")


class Mensaje(Base):
    """Mensaje individual en una conversación"""
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True, index=True)
    conversacion_id = Column(Integer, ForeignKey("conversaciones.id"), nullable=False, index=True)

    # Remitente
    de_tipo = Column(Enum(TipoParticipante), nullable=False)
    de_id = Column(Integer)  # ID del personal/cliente, null si es bot/sistema
    de_nombre = Column(String(150))  # Nombre para mostrar

    # Contenido
    tipo = Column(Enum(TipoMensaje), default=TipoMensaje.TEXTO)
    contenido = Column(Text)  # Texto del mensaje

    # Multimedia
    archivo_url = Column(String(500))
    archivo_nombre = Column(String(200))
    archivo_tamano = Column(Integer)  # bytes
    archivo_tipo = Column(String(100))  # mime type
    thumbnail_url = Column(String(500))  # Para imágenes/videos

    # Ubicación (si tipo = ubicacion)
    ubicacion_lat = Column(String(20))
    ubicacion_lng = Column(String(20))
    ubicacion_nombre = Column(String(200))

    # Estado de envío
    estado = Column(Enum(EstadoMensaje), default=EstadoMensaje.ENVIADO)

    # Timestamps de estados
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    enviado_at = Column(DateTime, default=datetime.utcnow)
    entregado_at = Column(DateTime)
    leido_at = Column(DateTime)

    # Metadatos (NOTA: 'metadata' es un nombre reservado en SQLAlchemy declarative,
    # por eso la columna se llama 'metadatos'; en BD se mapea a la columna 'metadatos')
    metadatos = Column("metadatos", JSON)

    # Respuesta a otro mensaje (quote/reply)
    respuesta_a_id = Column(Integer, ForeignKey("mensajes.id"))

    # Relaciones
    conversacion = relationship("Conversacion", back_populates="mensajes")
    respuesta_a = relationship("Mensaje", remote_side=[id])


class NotificacionPush(Base):
    """Cola de notificaciones push pendientes"""
    __tablename__ = "notificaciones_push"

    id = Column(Integer, primary_key=True, index=True)

    # Destinatario
    tipo_destinatario = Column(Enum(TipoParticipante), nullable=False)
    destinatario_id = Column(Integer)
    dispositivo_token = Column(String(500))  # FCM token

    # Contenido
    titulo = Column(String(200), nullable=False)
    cuerpo = Column(Text)
    imagen_url = Column(String(500))

    # Acción al tocar
    accion = Column(String(100))  # ruta a abrir
    data = Column(JSON)

    # Estado
    enviado = Column(Boolean, default=False)
    enviado_at = Column(DateTime)
    error = Column(Text)
    intentos = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class DispositivoUsuario(Base):
    """Dispositivos registrados para push notifications"""
    __tablename__ = "dispositivos_usuario"

    id = Column(Integer, primary_key=True, index=True)

    tipo_usuario = Column(Enum(TipoParticipante), nullable=False)
    usuario_id = Column(Integer)  # personal_id o cliente_id

    # Info dispositivo
    token_fcm = Column(String(500), unique=True)
    plataforma = Column(String(20))  # android, ios, web
    modelo = Column(String(100))
    version_app = Column(String(20))

    activo = Column(Boolean, default=True)
    ultimo_uso = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
