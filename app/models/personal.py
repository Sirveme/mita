"""
Modelos para gestión de personal MITA
- Personal (base), Técnicos, Secretarias
- Documentos, Distritos, Tiempos entre distritos

NOTA DE ARQUITECTURA (coexistencia):
El técnico de este subsistema se mapea a la tabla NUEVA `tecnicos_personal`
(clase TecnicoPersonal) para NO colisionar con el `Tecnico` legacy (tabla
`tecnicos`, ligado a Usuario y al flujo Servicio). Unificar ambos técnicos en
una sola entidad es una migración posterior que requiere la BD activa.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    Numeric, ForeignKey, JSON, Enum, Time, ARRAY
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class TipoPersonal(str, enum.Enum):
    SECRETARIA = "secretaria"
    TECNICO = "tecnico"
    ADMIN = "admin"
    GERENTE = "gerente"


class EstadoPersonal(str, enum.Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    SUSPENDIDO = "suspendido"
    BAJA = "baja"


class EstadoTecnico(str, enum.Enum):
    DISPONIBLE = "disponible"
    EN_SERVICIO = "en_servicio"
    EN_CAMINO = "en_camino"
    NO_DISPONIBLE = "no_disponible"
    DESCANSO = "descanso"


class Personal(Base):
    """Tabla base para todo el personal de MITA"""
    __tablename__ = "personal"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(Enum(TipoPersonal), nullable=False)

    # Datos personales
    dni = Column(String(15), unique=True, nullable=False, index=True)
    nombres = Column(String(100), nullable=False)
    apellido_paterno = Column(String(100), nullable=False)
    apellido_materno = Column(String(100))
    fecha_nacimiento = Column(Date)
    sexo = Column(String(1))  # M/F
    foto_url = Column(String(500))

    # Contacto
    telefono = Column(String(20), nullable=False, index=True)
    celular_2 = Column(String(15))  # segundo número (zMita-11)
    telefono_emergencia = Column(String(20))
    email = Column(String(150), index=True)

    # Domicilio
    direccion = Column(String(300))
    distrito_id = Column(Integer, ForeignKey("distritos.id"))
    referencia = Column(String(200))

    # Laboral
    fecha_ingreso = Column(Date, default=datetime.utcnow)
    fecha_baja = Column(Date)
    estado = Column(Enum(EstadoPersonal), default=EstadoPersonal.ACTIVO)
    motivo_baja = Column(Text)

    # Acceso al sistema
    usuario = Column(String(50), unique=True)
    password_hash = Column(String(255))
    ultimo_acceso = Column(DateTime)

    # Financiero
    banco = Column(String(50))
    numero_cuenta = Column(String(30))
    cci = Column(String(25))
    tipo_cuenta = Column(String(20))  # ahorro, corriente

    # Tributario (recibo por honorarios / 4ta categoría)
    ruc = Column(String(11))
    emite_recibo_honorarios = Column(Boolean, default=False)  # emite RxH (4ta)

    # Reputación (zMita-13) — el trigger de calificaciones actualiza estos campos
    rating_promedio = Column(Numeric(3, 2), default=0)
    total_servicios = Column(Integer, default=0)
    total_calificaciones = Column(Integer, default=0)

    # Relación laboral y vínculo con postulación (zPostulantes)
    tipo_relacion = Column(String(20), default="PROVEEDOR")  # EMPLEADO / PROVEEDOR
    postulante_id = Column(Integer, ForeignKey("postulantes.id"))

    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    distrito = relationship("Distrito", back_populates="personal")
    documentos = relationship(
        "DocumentoPersonal",
        back_populates="personal",
        foreign_keys="DocumentoPersonal.personal_id",
    )


class TecnicoPersonal(Base):
    """Extensión de Personal para técnicos (tabla nueva: tecnicos_personal)."""
    __tablename__ = "tecnicos_personal"

    id = Column(Integer, primary_key=True, index=True)
    personal_id = Column(Integer, ForeignKey("personal.id"), unique=True, nullable=False)

    # Estado actual
    estado_actual = Column(Enum(EstadoTecnico), default=EstadoTecnico.DISPONIBLE)
    ultima_ubicacion_lat = Column(Numeric(10, 8))
    ultima_ubicacion_lng = Column(Numeric(11, 8))
    ultima_ubicacion_at = Column(DateTime)

    # Especialidades (IDs de categorias_servicio)
    especialidades = Column(ARRAY(Integer))

    # Configuración
    radio_cobertura_km = Column(Numeric(5, 2), default=10)
    acepta_urgentes = Column(Boolean, default=True)
    acepta_nocturnos = Column(Boolean, default=False)

    # Estadísticas (desnormalizado para rendimiento)
    total_servicios = Column(Integer, default=0)
    calificacion_promedio = Column(Numeric(3, 2), default=5.00)
    total_calificaciones = Column(Integer, default=0)
    servicios_mes_actual = Column(Integer, default=0)
    rechazos_mes_actual = Column(Integer, default=0)

    # Financiero
    saldo_pendiente = Column(Numeric(10, 2), default=0)
    total_ganado_historico = Column(Numeric(12, 2), default=0)

    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    personal = relationship("Personal")
    horarios = relationship("HorarioTecnico", back_populates="tecnico")
    # NOTA: la relación con SolicitudServicio se omite deliberadamente: el flujo de
    # solicitudes usa el `tecnico_asignado_id` (tabla legacy `tecnicos`). Unificar
    # cuando se decida migrar el técnico legacy a este modelo.


class Secretaria(Base):
    """Extensión de Personal para secretarias"""
    __tablename__ = "secretarias"

    id = Column(Integer, primary_key=True, index=True)
    personal_id = Column(Integer, ForeignKey("personal.id"), unique=True, nullable=False)

    # Turno
    turno = Column(Integer, default=1)  # 1, 2, 3...
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
    dias_trabajo = Column(ARRAY(Integer))  # 0=Lun, 6=Dom

    # Estado
    en_linea = Column(Boolean, default=False)
    ultimo_heartbeat = Column(DateTime)

    # Estadísticas
    servicios_atendidos_hoy = Column(Integer, default=0)
    chats_activos = Column(Integer, default=0)

    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    personal = relationship("Personal")


class HorarioTecnico(Base):
    """Horarios de disponibilidad del técnico"""
    __tablename__ = "horarios_tecnico"

    id = Column(Integer, primary_key=True, index=True)
    tecnico_id = Column(Integer, ForeignKey("tecnicos_personal.id"), nullable=False)

    dia_semana = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    activo = Column(Boolean, default=True)

    tecnico = relationship("TecnicoPersonal", back_populates="horarios")


class TipoDocumento(str, enum.Enum):
    DNI = "dni"
    ANTECEDENTES_PENALES = "antecedentes_penales"
    ANTECEDENTES_POLICIALES = "antecedentes_policiales"
    ANTECEDENTES_JUDICIALES = "antecedentes_judiciales"
    CERTIFICADO_ESTUDIOS = "certificado_estudios"
    CERTIFICADO_TRABAJO = "certificado_trabajo"
    CV = "cv"
    FOTO_CARNET = "foto_carnet"
    RECIBO_SERVICIOS = "recibo_servicios"
    CONTRATO = "contrato"
    OTRO = "otro"


class DocumentoPersonal(Base):
    """Documentos del personal"""
    __tablename__ = "documentos_personal"

    id = Column(Integer, primary_key=True, index=True)
    personal_id = Column(Integer, ForeignKey("personal.id"), nullable=False)

    tipo = Column(Enum(TipoDocumento), nullable=False)
    nombre = Column(String(200))
    archivo_url = Column(String(500), nullable=False)
    fecha_emision = Column(Date)
    fecha_vencimiento = Column(Date)
    verificado = Column(Boolean, default=False)
    verificado_por = Column(Integer, ForeignKey("personal.id"))
    verificado_at = Column(DateTime)
    observaciones = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    personal = relationship("Personal", back_populates="documentos", foreign_keys=[personal_id])


class Distrito(Base):
    """Distritos de Lima para cobertura"""
    __tablename__ = "distritos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    zona = Column(String(50))  # Lima Centro, Lima Norte, etc.
    codigo_ubigeo = Column(String(10))
    activo = Column(Boolean, default=True)

    # Centro geográfico aproximado
    centro_lat = Column(Numeric(10, 8))
    centro_lng = Column(Numeric(11, 8))

    # Referencia opcional al catálogo de ubigeos (zMita-6)
    ubigeo_id = Column(Integer, ForeignKey("ubigeos.id"))

    personal = relationship("Personal", back_populates="distrito")


class TiempoEntreDistritos(Base):
    """Tiempos estimados entre distritos"""
    __tablename__ = "tiempos_entre_distritos"

    id = Column(Integer, primary_key=True, index=True)
    distrito_origen_id = Column(Integer, ForeignKey("distritos.id"), nullable=False)
    distrito_destino_id = Column(Integer, ForeignKey("distritos.id"), nullable=False)

    tiempo_minutos_normal = Column(Integer)  # Tráfico normal
    tiempo_minutos_pico = Column(Integer)  # Hora pico
    distancia_km = Column(Numeric(6, 2))

    updated_at = Column(DateTime, default=datetime.utcnow)
