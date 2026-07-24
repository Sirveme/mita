"""
Servicio de Pagos - MITA
Integración con Culqi API para procesar pagos con tarjeta
"""

import httpx
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Pago, Servicio, Cliente, Usuario,
    MetodoPagoEnum, EstadoPagoEnum, EstadoPagoServicioEnum
)
from app.schemas.pago import (
    CulqiCargoRequest, CulqiCargoResponse, CulqiErrorResponse,
    CulqiRefundRequest, CulqiRefundResponse,
    PagoExitosoResponse, PagoErrorResponse,
    soles_a_centimos, centimos_a_soles
)

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTES CULQI
# ============================================

CULQI_API_URL = "https://api.culqi.com/v2"
CULQI_SECURE_URL = "https://secure.culqi.com/v2"

# Comisión de Culqi: 3.99% + IGV (aproximadamente 4.7%)
CULQI_COMISION_PORCENTAJE = 0.047


# ============================================
# CLASE PRINCIPAL DEL SERVICIO
# ============================================

class CulqiService:
    """Servicio para interactuar con la API de Culqi"""

    def __init__(self):
        self.public_key = settings.CULQI_PUBLIC_KEY
        self.secret_key = settings.CULQI_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    def _validar_configuracion(self) -> bool:
        """Verifica que las keys de Culqi estén configuradas"""
        if not self.public_key or not self.secret_key:
            logger.error("Culqi: Keys no configuradas")
            return False
        return True

    async def crear_cargo(
        self,
        token_id: str,
        monto_soles: float,
        email: str,
        descripcion: str,
        servicio_id: int,
        metadata: Optional[Dict[str, Any]] = None,
        antifraud: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Crea un cargo en Culqi usando un token de tarjeta.

        Args:
            token_id: Token generado por Culqi.js (tkn_xxx)
            monto_soles: Monto en soles (ej: 150.00)
            email: Email del cliente
            descripcion: Descripción del cargo
            servicio_id: ID del servicio asociado
            metadata: Datos adicionales opcionales
            antifraud: Detalles antifraude opcionales

        Returns:
            Tuple[bool, dict]: (éxito, datos_respuesta o error)
        """
        if not self._validar_configuracion():
            return False, {"error": "Culqi no está configurado correctamente"}

        # Convertir a céntimos
        monto_centimos = soles_a_centimos(monto_soles)

        # Preparar payload
        payload = {
            "amount": monto_centimos,
            "currency_code": "PEN",
            "email": email,
            "source_id": token_id,
            "description": descripcion,
            "metadata": {
                "servicio_id": str(servicio_id),
                "plataforma": "serviplus",
                **(metadata or {})
            }
        }

        # Agregar antifraude si está disponible
        if antifraud:
            payload["antifraud_details"] = antifraud

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{CULQI_API_URL}/charges",
                    json=payload,
                    headers=self.headers
                )

                data = response.json()

                if response.status_code in [200, 201]:
                    logger.info(f"Culqi: Cargo exitoso {data.get('id')} - S/{monto_soles}")
                    return True, data
                else:
                    logger.warning(f"Culqi: Cargo rechazado - {data}")
                    return False, data

        except httpx.TimeoutException:
            logger.error("Culqi: Timeout en la solicitud")
            return False, {
                "error": "timeout",
                "merchant_message": "Timeout conectando con Culqi",
                "user_message": "El servicio de pagos no responde. Intenta de nuevo."
            }
        except Exception as e:
            logger.error(f"Culqi: Error inesperado - {str(e)}")
            return False, {
                "error": "internal",
                "merchant_message": str(e),
                "user_message": "Error procesando el pago. Intenta de nuevo."
            }

    async def obtener_cargo(self, charge_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Obtiene los detalles de un cargo existente"""
        if not self._validar_configuracion():
            return False, {"error": "Culqi no está configurado"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{CULQI_API_URL}/charges/{charge_id}",
                    headers=self.headers
                )

                if response.status_code == 200:
                    return True, response.json()
                else:
                    return False, response.json()

        except Exception as e:
            logger.error(f"Culqi: Error obteniendo cargo - {str(e)}")
            return False, {"error": str(e)}

    async def crear_reembolso(
        self,
        charge_id: str,
        monto_centimos: Optional[int] = None,
        motivo: str = "solicitud_cliente"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Crea un reembolso total o parcial.

        Args:
            charge_id: ID del cargo a reembolsar (chr_xxx)
            monto_centimos: Monto a reembolsar en céntimos (None = total)
            motivo: Razón del reembolso

        Returns:
            Tuple[bool, dict]: (éxito, datos_respuesta o error)
        """
        if not self._validar_configuracion():
            return False, {"error": "Culqi no está configurado"}

        payload = {
            "charge_id": charge_id,
            "reason": motivo
        }

        if monto_centimos:
            payload["amount"] = monto_centimos

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{CULQI_API_URL}/refunds",
                    json=payload,
                    headers=self.headers
                )

                data = response.json()

                if response.status_code in [200, 201]:
                    logger.info(f"Culqi: Reembolso exitoso para {charge_id}")
                    return True, data
                else:
                    logger.warning(f"Culqi: Error en reembolso - {data}")
                    return False, data

        except Exception as e:
            logger.error(f"Culqi: Error en reembolso - {str(e)}")
            return False, {"error": str(e)}

    def calcular_comision(self, monto_soles: float) -> float:
        """Calcula la comisión de Culqi para un monto dado"""
        return round(monto_soles * CULQI_COMISION_PORCENTAJE, 2)

    def calcular_monto_neto(self, monto_soles: float) -> float:
        """Calcula el monto neto después de la comisión de Culqi"""
        comision = self.calcular_comision(monto_soles)
        return round(monto_soles - comision, 2)


# ============================================
# SERVICIO DE PAGOS (BASE DE DATOS)
# ============================================

class PagoService:
    """Servicio para gestionar pagos en la base de datos"""

    def __init__(self, db: Session):
        self.db = db
        self.culqi = CulqiService()

    async def procesar_pago_tarjeta(
        self,
        servicio_id: int,
        token_id: str,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> PagoExitosoResponse | PagoErrorResponse:
        """
        Procesa un pago con tarjeta usando Culqi.

        1. Valida el servicio
        2. Crea el cargo en Culqi
        3. Registra el pago en la base de datos
        4. Actualiza el estado del servicio
        """
        # 1. Obtener servicio
        servicio = self.db.query(Servicio).filter(Servicio.id == servicio_id).first()
        if not servicio:
            return PagoErrorResponse(
                error="SERVICIO_NO_ENCONTRADO",
                user_message="El servicio no existe"
            )

        # Verificar que no tenga pago ya procesado
        pago_existente = self.db.query(Pago).filter(
            Pago.servicio_id == servicio_id,
            Pago.estado == EstadoPagoEnum.confirmado
        ).first()

        if pago_existente:
            return PagoErrorResponse(
                error="PAGO_YA_PROCESADO",
                user_message="Este servicio ya tiene un pago confirmado",
                retry_allowed=False
            )

        monto = float(servicio.monto_total)
        descripcion = f"MITA - Servicio #{servicio.codigo}"

        # 2. Crear cargo en Culqi
        exito, resultado = await self.culqi.crear_cargo(
            token_id=token_id,
            monto_soles=monto,
            email=email,
            descripcion=descripcion,
            servicio_id=servicio_id
        )

        if not exito:
            # Registrar intento fallido
            await self._registrar_pago_fallido(
                servicio_id=servicio_id,
                monto=monto,
                email=email,
                error=resultado,
                ip_address=ip_address,
                user_agent=user_agent
            )

            return PagoErrorResponse(
                error=resultado.get("type", "PAGO_RECHAZADO"),
                error_code=resultado.get("decline_code"),
                user_message=self._traducir_error_culqi(resultado)
            )

        # 3. Registrar pago exitoso
        comision = self.culqi.calcular_comision(monto)
        monto_neto = self.culqi.calcular_monto_neto(monto)

        pago = Pago(
            servicio_id=servicio_id,
            metodo_pago=MetodoPagoEnum.culqi_tarjeta,
            estado=EstadoPagoEnum.confirmado,
            monto=monto,
            comision_pasarela=comision,
            monto_neto=monto_neto,
            culqi_charge_id=resultado.get("id"),
            transaccion_id=resultado.get("id"),
            fecha_pago=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "culqi_response": {
                    "fraud_score": resultado.get("fraud_score"),
                    "outcome": resultado.get("outcome"),
                    "source_id": resultado.get("source_id")
                }
            }
        )

        self.db.add(pago)

        # 4. Actualizar estado del servicio
        servicio.estado_pago = EstadoPagoServicioEnum.pagado

        self.db.commit()
        self.db.refresh(pago)

        logger.info(f"Pago exitoso: servicio={servicio_id}, charge={resultado.get('id')}")

        return PagoExitosoResponse(
            message="Pago procesado exitosamente",
            pago_id=pago.id,
            servicio_id=servicio_id,
            culqi_charge_id=resultado.get("id"),
            monto=monto,
            estado=EstadoPagoEnum.confirmado
        )

    async def _registrar_pago_fallido(
        self,
        servicio_id: int,
        monto: float,
        email: str,
        error: Dict,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Registra un intento de pago fallido para auditoría"""
        pago = Pago(
            servicio_id=servicio_id,
            metodo_pago=MetodoPagoEnum.culqi_tarjeta,
            estado=EstadoPagoEnum.rechazado,
            monto=monto,
            motivo_rechazo=error.get("merchant_message", str(error)),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"culqi_error": error}
        )

        self.db.add(pago)
        self.db.commit()

    def _traducir_error_culqi(self, error: Dict) -> str:
        """Traduce errores de Culqi a mensajes amigables en español"""

        # Mensaje de usuario de Culqi
        user_message = error.get("user_message", "")
        if user_message:
            return user_message

        # Códigos de rechazo comunes
        decline_code = error.get("decline_code", "")
        traducciones = {
            "insufficient_funds": "Fondos insuficientes en la tarjeta",
            "stolen_card": "La tarjeta fue reportada como robada",
            "lost_card": "La tarjeta fue reportada como perdida",
            "expired_card": "La tarjeta ha expirado",
            "incorrect_cvv": "El código de seguridad (CVV) es incorrecto",
            "invalid_card": "Número de tarjeta inválido",
            "card_declined": "La tarjeta fue rechazada por el banco",
            "processing_error": "Error procesando el pago, intenta de nuevo",
            "fraud_detected": "El pago fue rechazado por medidas de seguridad",
            "contact_issuer": "Contacta a tu banco para autorizar la transacción",
            "try_again": "Error temporal, intenta de nuevo",
        }

        if decline_code in traducciones:
            return traducciones[decline_code]

        # Error genérico
        error_type = error.get("type", "")
        if "card" in error_type.lower():
            return "Problema con la tarjeta. Verifica los datos e intenta de nuevo."

        return "No se pudo procesar el pago. Intenta con otra tarjeta o método de pago."

    async def reembolsar_pago(
        self,
        pago_id: int,
        motivo: str,
        monto_parcial: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Procesa un reembolso para un pago existente.

        Args:
            pago_id: ID del pago a reembolsar
            motivo: Razón del reembolso
            monto_parcial: Monto a reembolsar (None = total)

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        pago = self.db.query(Pago).filter(Pago.id == pago_id).first()

        if not pago:
            return False, "Pago no encontrado"

        if pago.estado != EstadoPagoEnum.confirmado:
            return False, "Solo se pueden reembolsar pagos confirmados"

        if not pago.culqi_charge_id:
            return False, "Este pago no tiene un cargo de Culqi asociado"

        # Determinar monto a reembolsar
        monto_centimos = None
        if monto_parcial:
            monto_centimos = soles_a_centimos(monto_parcial)

        # Procesar reembolso en Culqi
        exito, resultado = await self.culqi.crear_reembolso(
            charge_id=pago.culqi_charge_id,
            monto_centimos=monto_centimos,
            motivo=motivo
        )

        if not exito:
            return False, f"Error en reembolso: {resultado.get('merchant_message', 'Error desconocido')}"

        # Actualizar pago
        pago.estado = EstadoPagoEnum.reembolsado
        pago.metadata = {
            **(pago.metadata or {}),
            "refund": {
                "id": resultado.get("id"),
                "amount": resultado.get("amount"),
                "reason": motivo,
                "date": datetime.utcnow().isoformat()
            }
        }

        # Actualizar servicio
        servicio = self.db.query(Servicio).filter(Servicio.id == pago.servicio_id).first()
        if servicio:
            servicio.estado_pago = EstadoPagoServicioEnum.reembolsado

        self.db.commit()

        return True, f"Reembolso procesado: {resultado.get('id')}"

    def obtener_pago_por_servicio(self, servicio_id: int) -> Optional[Pago]:
        """Obtiene el pago asociado a un servicio"""
        return self.db.query(Pago).filter(
            Pago.servicio_id == servicio_id
        ).order_by(Pago.created_at.desc()).first()

    def obtener_historial_pagos(
        self,
        cliente_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> list[Pago]:
        """Obtiene el historial de pagos de un cliente"""
        return self.db.query(Pago).join(Servicio).filter(
            Servicio.cliente_id == cliente_id
        ).order_by(Pago.created_at.desc()).offset(offset).limit(limit).all()


# ============================================
# INSTANCIA GLOBAL DE CULQI SERVICE
# ============================================

culqi_service = CulqiService()