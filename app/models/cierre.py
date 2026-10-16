"""
Modelos de identificación del cliente (etapa 2) y cierre/comprobante (etapa 7). zMita-39.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from datetime import datetime

from app.core.database import Base


class CodigoVerificacion(Base):
    """OTP de celular: código de 6 dígitos, 5 min de vigencia, con límites de envío/intentos."""
    __tablename__ = "codigos_verificacion"

    id = Column(Integer, primary_key=True, index=True)
    celular = Column(String(15), index=True, nullable=False)
    codigo = Column(String(6), nullable=False)
    expira_en = Column(DateTime, nullable=False)
    intentos = Column(Integer, default=0)       # verificaciones fallidas
    usado = Column(Boolean, default=False)       # verificado con éxito
    enviado_por = Column(String(30))             # proveedor SMS o "sin_proveedor"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class CompradorPreferido(Base):
    """Datos de facturación recordados por celular (se pregunta una vez)."""
    __tablename__ = "compradores_preferidos"

    id = Column(Integer, primary_key=True, index=True)
    celular = Column(String(15), unique=True, index=True, nullable=False)
    tipo_comprobante = Column(String(12))        # boleta / factura
    doc_tipo = Column(String(12))                # DNI / RUC / CE / PASAPORTE
    doc_numero = Column(String(20))
    razon_social = Column(String(200))           # nombres o razón social
    direccion_fiscal = Column(String(255))       # para factura
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComprobanteEmitido(Base):
    """Comprobante por solicitud y concepto (idempotencia: no emitir dos veces lo mismo).
    Estado SUNAT honesto (zMita-41): enviando -> aceptado | rechazado (con CDR real)."""
    __tablename__ = "comprobantes_emitidos"
    __table_args__ = (UniqueConstraint("solicitud_id", "concepto", name="uq_comprobante_sol_concepto"),)

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, index=True, nullable=False)
    concepto = Column(String(20), nullable=False)   # visita / reparacion
    tipo = Column(String(12))                        # boleta / factura
    serie = Column(String(12))
    numero = Column(String(20))
    numero_formato = Column(String(30))              # B999-00000001
    pdf_url = Column(String(300))
    monto = Column(Float)
    total = Column(Float)                            # total con IGV (lo que reporta SUNAT)
    # enviando / aceptado / rechazado / pendiente / anulado / simulado
    estado = Column(String(20), default="pendiente", index=True)
    simulado = Column(Boolean, default=False)        # true solo fuera de producción sin credencial

    # Facturalo / SUNAT
    facturalo_id = Column(String(64), index=True)
    referencia_externa = Column(String(100), index=True)
    codigo_sunat = Column(String(10))
    mensaje_sunat = Column(Text)
    hash_cpe = Column(String(100))
    emitido_en = Column(DateTime)                    # cuándo se encoló (para la cadencia de polling)
    ultima_consulta_en = Column(DateTime)

    # Datos del comprador (para re-emitir la NC de anulación)
    cliente_doc_tipo = Column(String(12))
    cliente_doc_numero = Column(String(20))
    cliente_nombre = Column(String(200))

    # Anulación por Nota de Crédito (motivo 01)
    nc_facturalo_id = Column(String(64))
    nc_numero_formato = Column(String(30))
    nc_estado = Column(String(20))
    anulado_en = Column(DateTime)
    anulado_por = Column(String(60))
    anulado_motivo = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CobroEfectivo(Base):
    """Cobro en efectivo con doble confirmación (técnico declara, cliente confirma)."""
    __tablename__ = "cobros_efectivo"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, index=True, nullable=False)
    monto_total = Column(Float)                  # lo que se debe cobrar
    monto_tecnico = Column(Float)                # lo que el técnico dice que recibió
    monto_cliente = Column(Float)                # lo que el cliente confirma
    # declarado / confirmado / discrepancia / validado_torre
    estado = Column(String(20), default="declarado", index=True)
    declarado_en = Column(DateTime, default=datetime.utcnow)
    validado_por = Column(String(60))            # id/usuario de la torre
    motivo = Column(Text)                        # por qué la torre decidió
    en_poder_tecnico = Column(Boolean, default=True)   # dato para la liquidación (etapa 8)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
