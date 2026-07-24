"""
Schemas Pydantic para Pagos - MITA
Integración con Culqi (tarjetas) y Tunki (Yape)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class MetodoPagoEnum(str, Enum):
    culqi_tarjeta = "culqi_tarjeta"
    yape = "yape"
    plin = "plin"
    efectivo = "efectivo"
    transferencia = "transferencia"


class EstadoPagoEnum(str, Enum):
    pendiente = "pendiente"
    preautorizado = "preautorizado"
    confirmado = "confirmado"
    rechazado = "rechazado"
    reembolsado = "reembolsado"
    cancelado = "cancelado"


# ============================================
# CULQI - Crear Token (Frontend -> Backend)
# ============================================

class CulqiTokenRequest(BaseModel):
    """Token generado por Culqi.js en el frontend"""
    token_id: str = Field(..., description="Token de tarjeta generado por Culqi.js")
    servicio_id: int = Field(..., description="ID del servicio a pagar")
    email: str = Field(..., description="Email del cliente")

    @field_validator('token_id')
    @classmethod
    def validar_token(cls, v):
        if not v or not v.startswith('tkn_'):
            raise ValueError('Token de Culqi inválido')
        return v


# ============================================
# CULQI - Crear Cargo
# ============================================

class CulqiCargoRequest(BaseModel):
    """Datos para crear un cargo en Culqi"""
    token_id: str = Field(..., description="Token de tarjeta")
    monto: int = Field(..., ge=100, description="Monto en céntimos (100 = S/1.00)")
    moneda: str = Field(default="PEN", description="Código de moneda ISO 4217")
    email: str = Field(..., description="Email del cliente")
    descripcion: str = Field(..., description="Descripción del cargo")
    servicio_id: int = Field(..., description="ID del servicio")

    # Antifraud (opcional pero recomendado)
    antifraud_details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class CulqiAntifraudDetails(BaseModel):
    """Detalles antifraude para Culqi"""
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    address_city: Optional[str] = None
    country_code: str = "PE"


# ============================================
# CULQI - Respuestas
# ============================================

class CulqiCargoResponse(BaseModel):
    """Respuesta de un cargo exitoso de Culqi"""
    id: str = Field(..., description="ID del cargo (chr_xxx)")
    amount: int
    currency_code: str
    email: str
    description: Optional[str] = None
    source_id: str
    outcome: Optional[Dict[str, Any]] = None
    fraud_score: Optional[float] = None
    creation_date: Optional[int] = None


class CulqiErrorResponse(BaseModel):
    """Respuesta de error de Culqi"""
    object: str = "error"
    type: str
    code: Optional[str] = None
    decline_code: Optional[str] = None
    merchant_message: str
    user_message: str


# ============================================
# PAGO - Crear/Actualizar
# ============================================

class PagoCreate(BaseModel):
    """Crear un nuevo registro de pago"""
    servicio_id: int
    metodo_pago: MetodoPagoEnum
    monto: float = Field(..., ge=0.01)
    email: str
    token_id: Optional[str] = None  # Para pagos con tarjeta
    comprobante_url: Optional[str] = None  # Para Yape/Plin


class PagoUpdate(BaseModel):
    """Actualizar estado de pago"""
    estado: EstadoPagoEnum
    culqi_charge_id: Optional[str] = None
    transaccion_id: Optional[str] = None
    numero_operacion: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================
# PAGO - Respuestas API
# ============================================

class PagoResponse(BaseModel):
    """Respuesta de pago para el frontend"""
    id: int
    servicio_id: int
    metodo_pago: MetodoPagoEnum
    estado: EstadoPagoEnum
    monto: float
    comision_pasarela: Optional[float] = None
    monto_neto: Optional[float] = None
    transaccion_id: Optional[str] = None
    culqi_charge_id: Optional[str] = None
    fecha_pago: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PagoExitosoResponse(BaseModel):
    """Respuesta cuando el pago es exitoso"""
    success: bool = True
    message: str
    pago_id: int
    servicio_id: int
    culqi_charge_id: Optional[str] = None
    monto: float
    estado: EstadoPagoEnum


class PagoErrorResponse(BaseModel):
    """Respuesta cuando el pago falla"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    user_message: str
    retry_allowed: bool = True


# ============================================
# WEBHOOK - Culqi Events
# ============================================

class CulqiWebhookEvent(BaseModel):
    """Evento de webhook de Culqi"""
    id: str
    type: str  # "charge.creation", "charge.update", "refund.creation", etc.
    data: Dict[str, Any]
    creation_date: int


class CulqiRefundRequest(BaseModel):
    """Solicitud de reembolso"""
    charge_id: str = Field(..., description="ID del cargo a reembolsar (chr_xxx)")
    monto: Optional[int] = Field(None, description="Monto parcial en céntimos, None para reembolso total")
    motivo: str = Field(..., description="Motivo del reembolso")


class CulqiRefundResponse(BaseModel):
    """Respuesta de reembolso"""
    id: str
    charge_id: str
    amount: int
    reason: str
    creation_date: int


# ============================================
# TUNKI (YAPE) - Crear Orden de Pago
# ============================================

class TunkiEstadoEnum(str, Enum):
    """Estados de una orden de pago en Tunki"""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    expired = "expired"
    cancelled = "cancelled"
    failed = "failed"


class YapePaymentRequest(BaseModel):
    """Solicitud para crear un pago con Yape via Tunki"""
    servicio_id: int = Field(..., description="ID del servicio a pagar")
    monto: float = Field(..., ge=1.0, description="Monto en soles")
    descripcion: Optional[str] = Field(None, description="Descripción del pago")
    telefono_cliente: Optional[str] = Field(None, description="Teléfono del cliente para notificación")


class TunkiOrderCreate(BaseModel):
    """Datos para crear una orden en Tunki API"""
    amount: float = Field(..., ge=1.0, description="Monto en soles")
    currency: str = Field(default="PEN", description="Moneda")
    description: str = Field(..., description="Descripción del pago")
    external_id: str = Field(..., description="ID externo (servicio_id)")
    expiration_minutes: int = Field(default=15, description="Minutos hasta expiración")

    # Datos del cliente (opcionales)
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None

    # Metadata adicional
    metadata: Optional[Dict[str, Any]] = None


class TunkiOrderResponse(BaseModel):
    """Respuesta de Tunki al crear una orden"""
    id: str = Field(..., description="ID de la orden en Tunki")
    status: TunkiEstadoEnum
    amount: float
    currency: str
    description: str
    external_id: str

    # QR y Deep Link para pago
    qr_code: Optional[str] = Field(None, description="Código QR en base64")
    qr_url: Optional[str] = Field(None, description="URL de la imagen QR")
    deep_link: Optional[str] = Field(None, description="Deep link para abrir Yape")
    payment_url: Optional[str] = Field(None, description="URL de pago web")

    # Tiempos
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TunkiPaymentStatus(BaseModel):
    """Estado de un pago en Tunki"""
    order_id: str
    status: TunkiEstadoEnum
    amount: float
    currency: str
    external_id: str

    # Datos del pago completado
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    payer_phone: Optional[str] = None  # Últimos 4 dígitos

    # Error si aplica
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class YapePaymentResponse(BaseModel):
    """Respuesta al crear un pago con Yape"""
    success: bool = True
    order_id: str
    servicio_id: int
    monto: float
    estado: str

    # Para mostrar al usuario
    qr_code: Optional[str] = None  # Base64 del QR
    qr_url: Optional[str] = None   # URL de imagen QR
    deep_link: Optional[str] = None  # Para abrir Yape directamente

    # Tiempos
    expira_en_minutos: int = 15
    mensaje: str = "Escanea el código QR con tu app de Yape"


class YapePaymentError(BaseModel):
    """Error al procesar pago con Yape"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    user_message: str


class YapeStatusResponse(BaseModel):
    """Respuesta al consultar estado de pago Yape"""
    order_id: str
    servicio_id: int
    estado: str
    pagado: bool
    monto: float

    # Si está pagado
    transaction_id: Optional[str] = None
    fecha_pago: Optional[datetime] = None

    # Si expiró o falló
    mensaje: Optional[str] = None


# ============================================
# TUNKI - Webhook
# ============================================

class TunkiWebhookEvent(BaseModel):
    """Evento de webhook de Tunki"""
    event_type: str  # "payment.completed", "payment.expired", "payment.failed"
    order_id: str
    external_id: str
    status: TunkiEstadoEnum
    amount: float
    currency: str

    # Datos adicionales del pago
    transaction_id: Optional[str] = None
    paid_at: Optional[str] = None

    # Firma para verificación
    signature: Optional[str] = None


# ============================================
# UTILIDADES
# ============================================

def soles_a_centimos(soles: float) -> int:
    """Convierte soles a céntimos para Culqi (S/10.50 -> 1050)"""
    return int(round(soles * 100))


def centimos_a_soles(centimos: int) -> float:
    """Convierte céntimos a soles (1050 -> S/10.50)"""
    return centimos / 100
