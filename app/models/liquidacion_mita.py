"""
Liquidación a técnicos (etapa 8, zMita-41). Ciclo: borrador -> enviada -> rxh_recibido
-> aprobada -> pagada. Tabla `liquidaciones_mita` (no choca con las liquidaciones previas).
El historial de parámetros (reparto/comisión/periodo/retención) vive en `configuracion_historial`.
"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, Boolean, ForeignKey
from datetime import datetime

from app.core.database import Base


class LiquidacionMita(Base):
    __tablename__ = "liquidaciones_mita"

    id = Column(Integer, primary_key=True, index=True)
    tecnico_id = Column(Integer, index=True, nullable=False)
    periodo_inicio = Column(Date, index=True)
    periodo_fin = Column(Date)
    # borrador / enviada / rxh_recibido / aprobada / pagada
    estado = Column(String(20), default="borrador", index=True)

    cantidad_servicios = Column(Integer, default=0)
    parte_tecnico = Column(Float, default=0)      # bruto del técnico
    parte_mita = Column(Float, default=0)
    efectivo_en_poder_tecnico = Column(Float, default=0)
    saldo_arrastrado = Column(Float, default=0)   # saldo a favor de MITA que traía
    a_transferir = Column(Float, default=0)       # neto a pagar al técnico
    saldo_a_favor_mita = Column(Float, default=0) # se arrastra al próximo periodo

    # Recibo por Honorarios (lo emite el técnico fuera de MITA, a nombre de MITA)
    rxh_numero = Column(String(50))
    rxh_fecha = Column(Date)
    rxh_monto = Column(Float)
    rxh_pdf_url = Column(Text)
    rxh_observacion = Column(Text)

    # Retención de 4ta (el sistema calcula, no asesora)
    retencion_activa = Column(Boolean, default=False)
    retencion_monto = Column(Float, default=0)
    neto_rxh = Column(Float)                       # bruto - retención

    # Pago
    pago_fecha = Column(DateTime)
    pago_medio = Column(String(30))                # transferencia / yape
    pago_operacion = Column(String(100))

    enviada_en = Column(DateTime)
    aprobada_en = Column(DateTime)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LiquidacionItem(Base):
    """Detalle por servicio, con el valor de comisión VIGENTE a la fecha de cierre (no se recalcula)."""
    __tablename__ = "liquidacion_items"

    id = Column(Integer, primary_key=True, index=True)
    liquidacion_id = Column(Integer, ForeignKey("liquidaciones_mita.id"), index=True)
    solicitud_id = Column(Integer, index=True)
    fecha_cierre = Column(DateTime)
    codigo = Column(String(20))                    # #solicitud, sin datos del cliente
    total = Column(Float)
    visita = Column(Float)
    reparacion = Column(Float)
    efectivo_tecnico = Column(Float, default=0)    # lo que se cobró en efectivo (ya en su poder)
    parte_mita = Column(Float)
    parte_tecnico = Column(Float)
    comision_tipo = Column(String(12))             # porcentaje / fijo (vigente a la fecha)
    comision_valor = Column(Float)
    visita_parte_mita = Column(Float)
    creado_en = Column(DateTime, default=datetime.utcnow)


class ConfiguracionHistorial(Base):
    """Historial de parámetros del panel: quién y desde cuándo rige cada valor."""
    __tablename__ = "configuracion_historial"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(80), index=True, nullable=False)
    valor = Column(Text)
    tipo = Column(String(12), default="string")    # string / int / float / bool
    vigente_desde = Column(DateTime, index=True, default=datetime.utcnow)
    creado_por = Column(String(60))
    creado_en = Column(DateTime, default=datetime.utcnow)
