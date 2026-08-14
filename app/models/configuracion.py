"""
Configuraciones del sistema MITA
- Tarifas
- Horarios
- Políticas
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Time,
    Numeric, JSON, Enum
)
from datetime import datetime
import enum

from app.core.database import Base


class ConfiguracionGeneral(Base):
    """Configuración general del sistema"""
    __tablename__ = "configuracion_general"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, nullable=False, index=True)
    valor = Column(Text)
    tipo = Column(String(20))  # string, number, boolean, json
    descripcion = Column(String(300))
    categoria = Column(String(50))  # tarifas, horarios, pagos, etc.
    editable = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TarifaServicio(Base):
    """Tarifas por tipo de servicio"""
    __tablename__ = "tarifas_servicio"

    id = Column(Integer, primary_key=True, index=True)

    # Puede ser por categoría o tipo específico
    categoria_id = Column(Integer)  # FK a categorias_servicio
    tipo_servicio_id = Column(Integer)  # FK a tipos_servicio (más específico)

    # Tarifa base
    precio_visita = Column(Numeric(10, 2), default=50)
    comision_mita = Column(Numeric(10, 2), default=15)
    pago_tecnico = Column(Numeric(10, 2), default=35)

    # O porcentajes
    porcentaje_mita = Column(Numeric(5, 2))  # Alternativa a monto fijo
    porcentaje_tecnico = Column(Numeric(5, 2))

    # Recargos
    recargo_urgente = Column(Numeric(10, 2), default=0)
    recargo_nocturno = Column(Numeric(10, 2), default=0)
    recargo_festivo = Column(Numeric(10, 2), default=0)

    # Descuentos
    descuento_maximo = Column(Numeric(5, 2), default=0)  # % máximo de descuento

    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HorarioAtencion(Base):
    """Horarios de atención del servicio"""
    __tablename__ = "horarios_atencion"

    id = Column(Integer, primary_key=True, index=True)

    dia_semana = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    es_feriado = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)

    descripcion = Column(String(100))  # "Lunes a Viernes", "Feriados"


class Feriado(Base):
    """Días feriados"""
    __tablename__ = "feriados"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, nullable=False, unique=True)
    nombre = Column(String(100), nullable=False)
    se_atiende = Column(Boolean, default=False)
    horario_especial = Column(Boolean, default=False)
    hora_inicio = Column(Time)
    hora_fin = Column(Time)


class ConfiguracionMita(Base):
    """Parámetros configurables del modelo de asignación automática (zMita-13)."""
    __tablename__ = "configuracion_mita"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(50), unique=True, nullable=False, index=True)
    valor = Column(Text, nullable=False)
    tipo = Column(String(20), default="string")   # string, int, float, bool, json
    descripcion = Column(Text)
    categoria = Column(String(50), default="general")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_valor(self):
        """Devuelve el valor convertido al tipo indicado."""
        if self.tipo == "int":
            return int(self.valor)
        if self.tipo == "float":
            return float(self.valor)
        if self.tipo == "bool":
            return str(self.valor).lower() in ("true", "1", "yes", "si")
        if self.tipo == "json":
            import json
            return json.loads(self.valor)
        return self.valor


class MensajeBot(Base):
    """Mensajes predefinidos del bot"""
    __tablename__ = "mensajes_bot"

    id = Column(Integer, primary_key=True, index=True)

    codigo = Column(String(50), unique=True, nullable=False)  # SALUDO, FUERA_HORARIO, etc.
    titulo = Column(String(100))
    mensaje = Column(Text, nullable=False)

    # Variables disponibles: {nombre}, {servicio}, {tecnico}, {hora}, etc.
    variables = Column(JSON)  # Lista de variables que acepta

    activo = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
