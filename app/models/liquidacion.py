"""
Sistema de Liquidaciones MITA
- Liquidaciones periódicas a técnicos
- Detalle de servicios
- Comisiones y deducciones
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    Numeric, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class EstadoLiquidacion(str, enum.Enum):
    PENDIENTE = "pendiente"      # En preparación
    GENERADA = "generada"        # Lista para revisar
    APROBADA = "aprobada"        # Aprobada por admin
    PAGADA = "pagada"            # Pago realizado
    RECHAZADA = "rechazada"      # Rechazada, requiere ajuste
    ANULADA = "anulada"


class FrecuenciaPago(str, enum.Enum):
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"


class Liquidacion(Base):
    """Liquidación periódica a un técnico"""
    __tablename__ = "liquidaciones"

    id = Column(Integer, primary_key=True, index=True)

    # Técnico (coexistencia: técnico de personal)
    tecnico_id = Column(Integer, ForeignKey("tecnicos_personal.id"), nullable=False, index=True)

    # Período
    frecuencia = Column(Enum(FrecuenciaPago), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)

    # Totales
    total_servicios = Column(Integer, default=0)
    total_visitas = Column(Numeric(10, 2), default=0)  # S/35 x visita
    total_trabajos_adicionales = Column(Numeric(10, 2), default=0)
    total_materiales = Column(Numeric(10, 2), default=0)

    # Cálculos
    subtotal = Column(Numeric(10, 2), default=0)
    deducciones = Column(Numeric(10, 2), default=0)  # Penalidades, adelantos
    bonificaciones = Column(Numeric(10, 2), default=0)
    total_pagar = Column(Numeric(10, 2), default=0)

    # Detalle de deducciones/bonificaciones
    detalle_deducciones = Column(JSON)  # [{concepto, monto}]
    detalle_bonificaciones = Column(JSON)  # [{concepto, monto}]

    # Estado
    estado = Column(Enum(EstadoLiquidacion), default=EstadoLiquidacion.PENDIENTE)

    # Aprobación
    aprobada_por = Column(Integer, ForeignKey("personal.id"))
    aprobada_at = Column(DateTime)

    # Pago
    metodo_pago = Column(String(50))
    referencia_pago = Column(String(100))  # Nro operación
    pagada_at = Column(DateTime)
    comprobante_url = Column(String(500))

    # Observaciones
    observaciones = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    tecnico = relationship("TecnicoPersonal")
    detalles = relationship("DetalleLiquidacion", back_populates="liquidacion")


class DetalleLiquidacion(Base):
    """Detalle de cada servicio en la liquidación"""
    __tablename__ = "detalle_liquidaciones"

    id = Column(Integer, primary_key=True, index=True)
    liquidacion_id = Column(Integer, ForeignKey("liquidaciones.id"), nullable=False, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes_servicio.id"), nullable=False)

    # Fecha del servicio
    fecha_servicio = Column(DateTime, nullable=False)

    # Montos
    monto_visita = Column(Numeric(10, 2), default=35)  # Parte técnico
    monto_trabajo_adicional = Column(Numeric(10, 2), default=0)
    monto_materiales = Column(Numeric(10, 2), default=0)
    total_servicio = Column(Numeric(10, 2), default=0)

    # Info del servicio
    categoria = Column(String(100))
    tipo_servicio = Column(String(150))
    cliente_nombre = Column(String(150))
    distrito = Column(String(100))

    liquidacion = relationship("Liquidacion", back_populates="detalles")


class ConfiguracionLiquidacion(Base):
    """Configuración general de liquidaciones"""
    __tablename__ = "configuracion_liquidacion"

    id = Column(Integer, primary_key=True, index=True)

    frecuencia_default = Column(Enum(FrecuenciaPago), default=FrecuenciaPago.QUINCENAL)
    dia_corte_semanal = Column(Integer, default=0)  # 0=Lunes
    dia_corte_quincenal = Column(Integer, default=15)  # Día del mes
    dias_para_pago = Column(Integer, default=3)  # Días después del corte

    # Retenciones
    retencion_garantia = Column(Numeric(5, 2), default=0)  # %

    # Mínimos
    monto_minimo_retiro = Column(Numeric(10, 2), default=0)

    activo = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
