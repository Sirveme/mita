"""
Pago por pasarela (IziPay/Culqi/...). Cierra el ciclo: pago → webhook → comprobante.
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Numeric, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class PagoPasarela(Base):
    __tablename__ = "pagos_pasarela"   # coexiste con el modelo legacy 'pagos'

    id = Column(Integer, primary_key=True, index=True)
    referencia = Column(String(100), unique=True, nullable=False, index=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes.id"), index=True)
    servicio_id = Column(Integer, ForeignKey("servicios_completados.id"))

    monto = Column(Numeric(10, 2), nullable=False)
    moneda = Column(String(3), default="PEN")

    # PENDIENTE, EN_PROCESO, APROBADO, RECHAZADO, ERROR, REEMBOLSADO
    estado = Column(String(30), default="PENDIENTE", index=True)

    pasarela = Column(String(30))
    token_pago = Column(Text)
    url_pago = Column(Text)

    respuesta_codigo = Column(String(50))
    respuesta_mensaje = Column(Text)
    respuesta_json = Column(JSONB)

    cliente_email = Column(String(255))
    cliente_telefono = Column(String(20))

    comprobante_emitido = Column(Boolean, default=False)
    comprobante_tipo = Column(String(10))
    comprobante_serie = Column(String(10))
    comprobante_numero = Column(Integer)

    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())
    pagado_en = Column(DateTime)

    # Pre-autorización de tarjeta (retención sin captura hasta finalizar el servicio)
    autorizacion_id = Column(String(100))
    monto_autorizado = Column(Numeric(10, 2))
    monto_capturado = Column(Numeric(10, 2))
    autorizacion_expira = Column(DateTime)
