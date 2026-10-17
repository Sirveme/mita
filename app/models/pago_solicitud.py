"""Pago por QR (Yape/Plin) validado con PagoOK, ligado a una solicitud (zMita-34 v2)."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, func

from app.core.database import Base


class PagoSolicitud(Base):
    __tablename__ = "pagos_solicitud"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, nullable=False, index=True)
    # Concepto del cobro (zMita-40): 'visita' (MITA-SOL-{id}) o 'reparacion' (MITA-SOL-{id}-R)
    concepto = Column(String(12), default="visita", index=True)

    # Estado del pago: esperando_pago / verificando / media_pendiente / pagada /
    # sin_coincidencia / error
    estado = Column(String(20), default="esperando_pago", index=True)

    # Lo declarado por el cliente al mostrar el QR / tocar "Ya pagué"
    canal = Column(String(20))                      # yape / plin
    monto_esperado = Column(Numeric(10, 2))         # exacto, p.ej. 50.00
    monto_recibido = Column(Numeric(10, 2))         # si llegó un monto distinto (zMita-45 C)
    titular_declarado = Column(String(150))         # nombre del TITULAR del medio de pago
    codigo_operacion = Column(String(50))
    qr_mostrado_en = Column(DateTime)
    fecha_hora_declarada = Column(DateTime)         # momento del "Ya pagué"

    # Resultado de PagoOK
    pago_id = Column(Integer)                        # pago_id de PagoOK
    nivel = Column(String(20))                       # alta / media / sin_coincidencia
    motivo = Column(String(60))
    contraparte = Column(String(150))                # titular del medio de pago (PagoOK)
    fecha_hora_pago = Column(DateTime)
    posible_reuso = Column(Boolean, default=False)   # pagos_ya_usados no vacío
    confirmado_por = Column(String(20))              # automatico / operador
    hora_voucher = Column(DateTime)                  # hora del comprobante declarada (desempate C2)
    puntaje = Column(Integer)                         # puntaje_nombre de la última evaluación
    referencia_externa = Column(String(150))         # MITA-SOL-{id}
    respuesta_cruda = Column(Text)                   # JSON de la última respuesta de PagoOK

    # Comprador (para el comprobante; distinto del pagador)
    comprador_nombre = Column(String(150))
    comprador_doc_tipo = Column(String(12))          # DNI / RUC / CE / PASAPORTE
    comprador_doc_numero = Column(String(20))
    # Comprobante
    comprobante_estado = Column(String(20))          # emitido / pendiente / no_aplica
    comprobante_tipo = Column(String(12))            # boleta / factura
    comprobante_serie = Column(String(12))
    comprobante_numero = Column(String(20))
    comprobante_pdf = Column(String(300))

    intentos = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
