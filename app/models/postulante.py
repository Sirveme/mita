"""
Postulante: técnico que se postula como PROVEEDOR de MITA.
Los documentos NO se guardan en la BD (se envían por email); aquí solo se
declara qué documentos se enviaron. Al aprobar, el id se conserva como
`personal.postulante_id`.
"""

import enum

from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class EstadoPostulante(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    OBSERVADO = "OBSERVADO"


class TipoRelacion(str, enum.Enum):
    EMPLEADO = "EMPLEADO"
    PROVEEDOR = "PROVEEDOR"


class Postulante(Base):
    __tablename__ = "postulantes"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)  # POST-YYYYMM-XXXX
    estado = Column(String(20), nullable=False, default=EstadoPostulante.PENDIENTE.value, index=True)

    # Identidad
    dni = Column(String(8), unique=True, nullable=False, index=True)
    ruc = Column(String(11), index=True)

    # Datos personales
    nombres = Column(String(150), nullable=False)
    apellido_paterno = Column(String(100))
    apellido_materno = Column(String(100))
    fecha_nacimiento = Column(Date)
    sexo = Column(String(1))

    # Contacto
    celular_1 = Column(String(15), nullable=False)
    celular_2 = Column(String(15))
    email = Column(String(150), nullable=False)

    # Ubicación
    departamento = Column(String(100))
    provincia = Column(String(100))
    distrito = Column(String(100))
    direccion = Column(String(300))
    referencia = Column(String(200))

    # Especialidades / experiencia / formación
    especialidades = Column(JSONB, default=list)          # ['ELECTRICIDAD', ...]
    anios_experiencia = Column(Integer, default=0)
    experiencia_laboral = Column(JSONB, default=list)     # [{empresa, cargo, periodo}]
    nivel_educativo = Column(String(100))
    institucion = Column(String(200))
    certificaciones = Column(Text)

    # Pago (obligatorio)
    banco = Column(String(80))
    numero_cuenta = Column(String(30))
    cci = Column(String(25))
    yape = Column(String(15))
    plin = Column(String(15))

    # Credenciales SOL / Facturación (opcional)
    sol_usuario = Column(String(60))
    sol_clave_encriptada = Column(String(255))
    emision_automatica_rxh = Column(Boolean, default=False)

    # Documentos declarados (se envían por email)
    documentos_enviados = Column(JSONB, default=list)     # [{tipo, nombre_archivo, enviado_email}]

    # Revisión
    fecha_postulacion = Column(DateTime, server_default=func.now())
    fecha_revision = Column(DateTime)
    revisado_por = Column(String(100))
    observaciones = Column(Text)

    @property
    def nombre_completo(self) -> str:
        partes = [self.nombres, self.apellido_paterno, self.apellido_materno]
        return " ".join(p for p in partes if p).strip()
