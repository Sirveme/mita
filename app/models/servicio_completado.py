"""
Servicio completado: registro de cada servicio con distribución de comisiones
(MITA / técnico) y datos del comprobante emitido al cliente.
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey, func

from app.core.database import Base


class ServicioCompletado(Base):
    __tablename__ = "servicios_completados"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"))
    tecnico_id = Column(Integer, ForeignKey("personal.id"), index=True)
    cliente_id = Column(Integer)

    monto_visita = Column(Numeric(10, 2), default=50)
    monto_reparacion = Column(Numeric(10, 2), default=0)
    monto_total = Column(Numeric(10, 2))

    comision_mita_visita = Column(Numeric(10, 2), default=15)
    comision_mita_reparacion = Column(Numeric(10, 2), default=0)
    comision_tecnico_visita = Column(Numeric(10, 2), default=35)
    comision_tecnico_reparacion = Column(Numeric(10, 2), default=0)
    total_mita = Column(Numeric(10, 2))
    total_tecnico = Column(Numeric(10, 2))

    comprobante_tipo = Column(String(10))       # boleta | factura
    comprobante_serie = Column(String(10))
    comprobante_numero = Column(Integer)
    comprobante_emitido = Column(Boolean, default=False)
    comprobante_pdf_url = Column(Text)

    liquidacion_id = Column(Integer, index=True)

    fecha_servicio = Column(DateTime)
    fecha_comprobante = Column(DateTime)
    creado_en = Column(DateTime, server_default=func.now())
