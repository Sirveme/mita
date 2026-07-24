"""
Servicio de Tunki - MITA
Integración con Tunki API para pagos con Yape
"""

import httpx
import hashlib
import hmac
import logging
import base64
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Pago, Servicio,
    MetodoPagoEnum, EstadoPagoEnum, EstadoPagoServicioEnum
)
from app.schemas.pago import (
    TunkiOrderCreate, TunkiOrderResponse, TunkiPaymentStatus,
    YapePaymentResponse, YapePaymentError, YapeStatusResponse,
    TunkiEstadoEnum
)

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTES TUNKI
# ============================================

TUNKI_API_URL = "https://api.tunki.pe/v1"
TUNKI_SANDBOX_URL = "https://sandbox.tunki.pe/v1"

# Comisión de Tunki/Yape: aproximadamente 0.5% - 1%
TUNKI_COMISION_PORCENTAJE = 0.01

# Tiempo de expiración del QR en minutos
QR_EXPIRATION_MINUTES = 15


# ============================================
# CLASE PRINCIPAL DEL SERVICIO
# ============================================

class TunkiService:
    """Servicio para interactuar con la API de Tunki (Yape)"""

    def __init__(self):
        self.api_key = settings.TUNKI_API_KEY
        self.secret_key = settings.TUNKI_SECRET_KEY
        self.merchant_id = settings.TUNKI_MERCHANT_ID
        self.webhook_secret = settings.TUNKI_WEBHOOK_SECRET

        # Usar sandbox si estamos en desarrollo
        self.base_url = TUNKI_SANDBOX_URL if settings.ENVIRONMENT != "production" else TUNKI_API_URL

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Merchant-Id": self.merchant_id or ""
        }

    def _validar_configuracion(self) -> bool:
        """Verifica que las keys de Tunki estén configuradas"""
        if not self.api_key:
            logger.error("Tunki: API Key no configurada")
            return False
        return True

    async def crear_orden_pago(
        self,
        monto: float,
        servicio_id: int,
        descripcion: str,
        cliente_email: Optional[str] = None,
        cliente_telefono: Optional[str] = None,
        cliente_nombre: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Crea una orden de pago con QR para Yape.

        Args:
            monto: Monto en soles
            servicio_id: ID del servicio a pagar
            descripcion: Descripción del pago
            cliente_email: Email del cliente (opcional)
            cliente_telefono: Teléfono del cliente (opcional)
            cliente_nombre: Nombre del cliente (opcional)
            metadata: Datos adicionales (opcional)

        Returns:
            Tuple[bool, dict]: (éxito, datos_respuesta o error)
        """
        if not self._validar_configuracion():
            return False, {"error": "Tunki no está configurado correctamente"}

        # Preparar payload
        payload = {
            "amount": monto,
            "currency": "PEN",
            "description": descripcion,
            "external_id": f"SERV-{servicio_id}",
            "expiration_minutes": QR_EXPIRATION_MINUTES,
            "callback_url": f"{settings.BACKEND_URL}/pagos/webhook/tunki",
            "metadata": {
                "servicio_id": str(servicio_id),
                "plataforma": "serviplus",
                **(metadata or {})
            }
        }

        # Agregar datos del cliente si están disponibles
        if cliente_email:
            payload["customer_email"] = cliente_email
        if cliente_telefono:
            payload["customer_phone"] = cliente_telefono
        if cliente_nombre:
            payload["customer_name"] = cliente_nombre

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/orders",
                    json=payload,
                    headers=self.headers
                )

                data = response.json()

                if response.status_code in [200, 201]:
                    logger.info(f"Tunki: Orden creada {data.get('id')} - S/{monto}")
                    return True, data
                else:
                    logger.warning(f"Tunki: Error creando orden - {data}")
                    return False, data

        except httpx.TimeoutException:
            logger.error("Tunki: Timeout en la solicitud")
            return False, {
                "error": "timeout",
                "message": "El servicio de pagos no responde. Intenta de nuevo."
            }
        except Exception as e:
            logger.error(f"Tunki: Error inesperado - {str(e)}")
            return False, {
                "error": "internal",
                "message": str(e)
            }

    async def consultar_estado_orden(self, order_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Consulta el estado de una orden de pago.

        Args:
            order_id: ID de la orden en Tunki

        Returns:
            Tuple[bool, dict]: (éxito, datos_estado)
        """
        if not self._validar_configuracion():
            return False, {"error": "Tunki no está configurado"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/orders/{order_id}",
                    headers=self.headers
                )

                if response.status_code == 200:
                    return True, response.json()
                else:
                    return False, response.json()

        except Exception as e:
            logger.error(f"Tunki: Error consultando orden - {str(e)}")
            return False, {"error": str(e)}

    async def cancelar_orden(self, order_id: str) -> Tuple[bool, str]:
        """
        Cancela una orden de pago pendiente.

        Args:
            order_id: ID de la orden en Tunki

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        if not self._validar_configuracion():
            return False, "Tunki no está configurado"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/orders/{order_id}/cancel",
                    headers=self.headers
                )

                if response.status_code in [200, 204]:
                    logger.info(f"Tunki: Orden {order_id} cancelada")
                    return True, "Orden cancelada exitosamente"
                else:
                    data = response.json()
                    return False, data.get("message", "Error cancelando orden")

        except Exception as e:
            logger.error(f"Tunki: Error cancelando orden - {str(e)}")
            return False, str(e)

    def verificar_firma_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Verifica la firma de un webhook de Tunki.

        Args:
            payload: Body raw del webhook
            signature: Firma recibida en el header

        Returns:
            bool: True si la firma es válida
        """
        if not self.webhook_secret:
            logger.warning("Tunki: Webhook secret no configurado, omitiendo verificación")
            return True

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def calcular_comision(self, monto: float) -> float:
        """Calcula la comisión de Tunki para un monto dado"""
        return round(monto * TUNKI_COMISION_PORCENTAJE, 2)

    def calcular_monto_neto(self, monto: float) -> float:
        """Calcula el monto neto después de la comisión de Tunki"""
        comision = self.calcular_comision(monto)
        return round(monto - comision, 2)


# ============================================
# SERVICIO DE PAGOS YAPE (BASE DE DATOS)
# ============================================

class YapePaymentService:
    """Servicio para gestionar pagos con Yape en la base de datos"""

    def __init__(self, db: Session):
        self.db = db
        self.tunki = TunkiService()

    async def crear_pago_yape(
        self,
        servicio_id: int,
        cliente_email: Optional[str] = None,
        cliente_telefono: Optional[str] = None,
        cliente_nombre: Optional[str] = None
    ) -> YapePaymentResponse | YapePaymentError:
        """
        Crea una orden de pago con Yape.

        1. Valida el servicio
        2. Crea la orden en Tunki
        3. Registra el pago pendiente en la base de datos
        4. Retorna el QR para que el cliente pague
        """
        # 1. Obtener servicio
        servicio = self.db.query(Servicio).filter(Servicio.id == servicio_id).first()
        if not servicio:
            return YapePaymentError(
                error="SERVICIO_NO_ENCONTRADO",
                user_message="El servicio no existe"
            )

        # Verificar que no tenga pago ya procesado
        pago_existente = self.db.query(Pago).filter(
            Pago.servicio_id == servicio_id,
            Pago.estado == EstadoPagoEnum.confirmado
        ).first()

        if pago_existente:
            return YapePaymentError(
                error="PAGO_YA_PROCESADO",
                user_message="Este servicio ya tiene un pago confirmado"
            )

        monto = float(servicio.monto_total)
        descripcion = f"MITA - Servicio #{servicio.codigo}"

        # 2. Crear orden en Tunki
        exito, resultado = await self.tunki.crear_orden_pago(
            monto=monto,
            servicio_id=servicio_id,
            descripcion=descripcion,
            cliente_email=cliente_email,
            cliente_telefono=cliente_telefono,
            cliente_nombre=cliente_nombre
        )

        if not exito:
            return YapePaymentError(
                error=resultado.get("error", "TUNKI_ERROR"),
                error_code=resultado.get("code"),
                user_message=resultado.get("message", "Error creando el pago con Yape")
            )

        # 3. Registrar pago pendiente
        pago = Pago(
            servicio_id=servicio_id,
            metodo_pago=MetodoPagoEnum.yape,
            estado=EstadoPagoEnum.pendiente,
            monto=monto,
            transaccion_id=resultado.get("id"),  # Order ID de Tunki
            metadata={
                "tunki_order": {
                    "id": resultado.get("id"),
                    "status": resultado.get("status"),
                    "qr_url": resultado.get("qr_url"),
                    "deep_link": resultado.get("deep_link"),
                    "expires_at": resultado.get("expires_at")
                }
            }
        )

        self.db.add(pago)

        # Actualizar estado del servicio
        servicio.estado_pago = EstadoPagoServicioEnum.pendiente

        self.db.commit()
        self.db.refresh(pago)

        logger.info(f"Pago Yape creado: servicio={servicio_id}, order={resultado.get('id')}")

        return YapePaymentResponse(
            order_id=resultado.get("id"),
            servicio_id=servicio_id,
            monto=monto,
            estado="pendiente",
            qr_code=resultado.get("qr_code"),
            qr_url=resultado.get("qr_url"),
            deep_link=resultado.get("deep_link"),
            expira_en_minutos=QR_EXPIRATION_MINUTES,
            mensaje="Escanea el código QR con tu app de Yape para pagar"
        )

    async def verificar_estado_pago(self, order_id: str) -> YapeStatusResponse:
        """
        Verifica el estado de un pago con Yape.

        Útil para polling desde el frontend.
        """
        # Buscar pago por order_id
        pago = self.db.query(Pago).filter(
            Pago.transaccion_id == order_id,
            Pago.metodo_pago == MetodoPagoEnum.yape
        ).first()

        if not pago:
            # Consultar directamente a Tunki
            exito, estado = await self.tunki.consultar_estado_orden(order_id)

            if not exito:
                return YapeStatusResponse(
                    order_id=order_id,
                    servicio_id=0,
                    estado="desconocido",
                    pagado=False,
                    monto=0,
                    mensaje="No se pudo verificar el estado del pago"
                )

            return YapeStatusResponse(
                order_id=order_id,
                servicio_id=int(estado.get("external_id", "0").replace("SERV-", "")),
                estado=estado.get("status", "unknown"),
                pagado=estado.get("status") == "completed",
                monto=estado.get("amount", 0),
                transaction_id=estado.get("transaction_id"),
                fecha_pago=estado.get("paid_at")
            )

        # Si el pago está pendiente, consultar a Tunki
        if pago.estado == EstadoPagoEnum.pendiente:
            exito, estado = await self.tunki.consultar_estado_orden(order_id)

            if exito and estado.get("status") == "completed":
                # Actualizar pago como confirmado
                await self._confirmar_pago(pago, estado)

        return YapeStatusResponse(
            order_id=order_id,
            servicio_id=pago.servicio_id,
            estado=pago.estado.value,
            pagado=pago.estado == EstadoPagoEnum.confirmado,
            monto=float(pago.monto),
            transaction_id=pago.transaccion_id,
            fecha_pago=pago.fecha_pago
        )

    async def _confirmar_pago(self, pago: Pago, tunki_data: Dict):
        """Confirma un pago después de recibir confirmación de Tunki"""
        comision = self.tunki.calcular_comision(float(pago.monto))
        monto_neto = self.tunki.calcular_monto_neto(float(pago.monto))

        pago.estado = EstadoPagoEnum.confirmado
        pago.comision_pasarela = comision
        pago.monto_neto = monto_neto
        pago.fecha_pago = datetime.utcnow()
        pago.metadata = {
            **(pago.metadata or {}),
            "tunki_confirmation": tunki_data
        }

        # Actualizar servicio
        servicio = self.db.query(Servicio).filter(Servicio.id == pago.servicio_id).first()
        if servicio:
            servicio.estado_pago = EstadoPagoServicioEnum.pagado

        self.db.commit()

        logger.info(f"Pago Yape confirmado: pago_id={pago.id}, servicio={pago.servicio_id}")

    async def procesar_webhook(self, event_data: Dict) -> bool:
        """
        Procesa un evento de webhook de Tunki.

        Args:
            event_data: Datos del evento recibido

        Returns:
            bool: True si se procesó correctamente
        """
        order_id = event_data.get("order_id")
        status = event_data.get("status")
        external_id = event_data.get("external_id", "")

        # Extraer servicio_id del external_id
        servicio_id = int(external_id.replace("SERV-", "")) if external_id.startswith("SERV-") else None

        if not order_id:
            logger.warning("Webhook Tunki: No order_id en el evento")
            return False

        # Buscar pago
        pago = self.db.query(Pago).filter(
            Pago.transaccion_id == order_id
        ).first()

        if not pago:
            logger.warning(f"Webhook Tunki: Pago no encontrado para order {order_id}")
            return False

        # Procesar según el estado
        if status == "completed":
            await self._confirmar_pago(pago, event_data)
            logger.info(f"Webhook Tunki: Pago {order_id} completado")

        elif status == "expired":
            pago.estado = EstadoPagoEnum.cancelado
            pago.motivo_rechazo = "Tiempo de pago expirado"
            self.db.commit()
            logger.info(f"Webhook Tunki: Pago {order_id} expirado")

        elif status == "failed":
            pago.estado = EstadoPagoEnum.rechazado
            pago.motivo_rechazo = event_data.get("error_message", "Pago fallido")
            self.db.commit()
            logger.info(f"Webhook Tunki: Pago {order_id} fallido")

        elif status == "cancelled":
            pago.estado = EstadoPagoEnum.cancelado
            pago.motivo_rechazo = "Pago cancelado"
            self.db.commit()
            logger.info(f"Webhook Tunki: Pago {order_id} cancelado")

        return True


# ============================================
# INSTANCIA GLOBAL
# ============================================

tunki_service = TunkiService()
