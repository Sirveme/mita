"""
Endpoints de Pagos - MITA
API REST para procesar pagos con Culqi (tarjetas) y Tunki (Yape)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import hmac
import json
import logging

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.models import Usuario, Servicio, Pago, EstadoPagoEnum
from app.services.pagos import PagoService, culqi_service
from app.services.tunki import YapePaymentService, tunki_service
from app.schemas.pago import (
    CulqiTokenRequest,
    PagoExitosoResponse,
    PagoErrorResponse,
    PagoResponse,
    CulqiWebhookEvent,
    CulqiRefundRequest,
    # Yape/Tunki schemas
    YapePaymentRequest,
    YapePaymentResponse,
    YapePaymentError,
    YapeStatusResponse,
    TunkiWebhookEvent
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


# ============================================
# PROCESAR PAGO CON TARJETA
# ============================================

@router.post(
    "/tarjeta",
    response_model=PagoExitosoResponse | PagoErrorResponse,
    summary="Procesar pago con tarjeta",
    description="Procesa un pago usando un token de Culqi generado en el frontend"
)
async def procesar_pago_tarjeta(
    request: Request,
    datos: CulqiTokenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Procesa un pago con tarjeta de crédito/débito.

    El flujo es:
    1. Frontend genera token con Culqi.js
    2. Frontend envía token_id + servicio_id a este endpoint
    3. Backend crea el cargo en Culqi
    4. Backend registra el pago y actualiza el servicio
    """
    # Verificar que el servicio pertenece al usuario
    servicio = db.query(Servicio).filter(Servicio.id == datos.servicio_id).first()

    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado"
        )

    # Verificar propiedad (asumiendo que el usuario tiene un cliente asociado)
    if current_user.cliente and servicio.cliente_id != current_user.cliente.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para pagar este servicio"
        )

    # Obtener información de la request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Procesar pago
    pago_service = PagoService(db)
    resultado = await pago_service.procesar_pago_tarjeta(
        servicio_id=datos.servicio_id,
        token_id=datos.token_id,
        email=datos.email,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if isinstance(resultado, PagoErrorResponse):
        # Log del error para monitoreo
        logger.warning(
            f"Pago rechazado: servicio={datos.servicio_id}, "
            f"error={resultado.error}, code={resultado.error_code}"
        )

    return resultado


# ============================================
# OBTENER ESTADO DE PAGO
# ============================================

@router.get(
    "/servicio/{servicio_id}",
    response_model=PagoResponse | None,
    summary="Obtener pago de un servicio"
)
async def obtener_pago_servicio(
    servicio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene el pago asociado a un servicio"""
    pago_service = PagoService(db)
    pago = pago_service.obtener_pago_por_servicio(servicio_id)

    if not pago:
        return None

    # Verificar permisos
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()
    if current_user.cliente and servicio.cliente_id != current_user.cliente.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este pago"
        )

    return pago


# ============================================
# HISTORIAL DE PAGOS
# ============================================

@router.get(
    "/historial",
    response_model=list[PagoResponse],
    summary="Historial de pagos del cliente"
)
async def obtener_historial_pagos(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene el historial de pagos del cliente autenticado"""
    if not current_user.cliente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo clientes pueden ver historial de pagos"
        )

    pago_service = PagoService(db)
    pagos = pago_service.obtener_historial_pagos(
        cliente_id=current_user.cliente.id,
        limit=min(limit, 100),
        offset=offset
    )

    return pagos


# ============================================
# WEBHOOK DE CULQI
# ============================================

@router.post(
    "/webhook/culqi",
    status_code=status.HTTP_200_OK,
    summary="Webhook de Culqi",
    include_in_schema=False  # Ocultar de docs públicos
)
async def webhook_culqi(
    request: Request,
    db: Session = Depends(get_db),
    x_culqi_signature: Optional[str] = Header(None)
):
    """
    Recibe eventos de webhook de Culqi.

    Eventos soportados:
    - charge.creation: Cargo creado
    - charge.update: Cargo actualizado
    - refund.creation: Reembolso creado
    """
    body = await request.body()

    # Verificar firma del webhook (si está configurada)
    # Nota: Culqi usa HMAC-SHA256 para firmar webhooks
    # Si tienes un webhook secret configurado, descomenta esto:
    #
    # if settings.CULQI_WEBHOOK_SECRET:
    #     expected_signature = hmac.new(
    #         settings.CULQI_WEBHOOK_SECRET.encode(),
    #         body,
    #         hashlib.sha256
    #     ).hexdigest()
    #
    #     if not hmac.compare_digest(expected_signature, x_culqi_signature or ""):
    #         logger.warning("Webhook Culqi: Firma inválida")
    #         raise HTTPException(status_code=401, detail="Firma inválida")

    try:
        import json
        data = json.loads(body)

        event_type = data.get("type", "")
        event_data = data.get("data", {})

        logger.info(f"Webhook Culqi recibido: {event_type}")

        if event_type == "charge.creation":
            await _procesar_cargo_creado(db, event_data)

        elif event_type == "charge.update":
            await _procesar_cargo_actualizado(db, event_data)

        elif event_type == "refund.creation":
            await _procesar_reembolso_creado(db, event_data)

        else:
            logger.info(f"Webhook Culqi: Evento no manejado - {event_type}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook Culqi: Error procesando - {str(e)}")
        # Siempre retornar 200 para evitar reintentos innecesarios
        return {"status": "error", "message": str(e)}


async def _procesar_cargo_creado(db: Session, data: dict):
    """Procesa evento de cargo creado"""
    charge_id = data.get("id")
    servicio_id = data.get("metadata", {}).get("servicio_id")

    if not servicio_id:
        logger.warning(f"Webhook: Cargo sin servicio_id - {charge_id}")
        return

    logger.info(f"Webhook: Cargo creado {charge_id} para servicio {servicio_id}")


async def _procesar_cargo_actualizado(db: Session, data: dict):
    """Procesa evento de cargo actualizado"""
    charge_id = data.get("id")
    outcome = data.get("outcome", {})
    outcome_type = outcome.get("type", "")

    # Buscar pago por charge_id
    pago = db.query(Pago).filter(Pago.culqi_charge_id == charge_id).first()

    if not pago:
        logger.warning(f"Webhook: Pago no encontrado para cargo {charge_id}")
        return

    # Actualizar según outcome
    if outcome_type == "venta_exitosa":
        pago.estado = EstadoPagoEnum.confirmado
    elif outcome_type == "venta_rechazada":
        pago.estado = EstadoPagoEnum.rechazado
        pago.motivo_rechazo = outcome.get("merchant_message", "Rechazado")

    db.commit()
    logger.info(f"Webhook: Cargo {charge_id} actualizado a {pago.estado}")


async def _procesar_reembolso_creado(db: Session, data: dict):
    """Procesa evento de reembolso creado"""
    refund_id = data.get("id")
    charge_id = data.get("charge_id")

    pago = db.query(Pago).filter(Pago.culqi_charge_id == charge_id).first()

    if not pago:
        logger.warning(f"Webhook: Pago no encontrado para reembolso {refund_id}")
        return

    pago.estado = EstadoPagoEnum.reembolsado
    pago.metadata = {
        **(pago.metadata or {}),
        "refund_id": refund_id,
        "refund_amount": data.get("amount")
    }

    db.commit()
    logger.info(f"Webhook: Reembolso {refund_id} procesado para pago {pago.id}")


# ============================================
# REEMBOLSO (ADMIN)
# ============================================

@router.post(
    "/reembolso",
    summary="Procesar reembolso",
    description="Solo administradores pueden procesar reembolsos"
)
async def procesar_reembolso(
    datos: CulqiRefundRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Procesa un reembolso para un cargo existente"""
    # Verificar que es admin
    if current_user.rol.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden procesar reembolsos"
        )

    # Buscar pago
    pago = db.query(Pago).filter(Pago.culqi_charge_id == datos.charge_id).first()

    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )

    # Procesar reembolso
    pago_service = PagoService(db)
    monto_parcial = datos.monto / 100 if datos.monto else None

    exito, mensaje = await pago_service.reembolsar_pago(
        pago_id=pago.id,
        motivo=datos.motivo,
        monto_parcial=monto_parcial
    )

    if not exito:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=mensaje
        )

    return {"success": True, "message": mensaje}


# ============================================
# YAPE - CREAR PAGO CON QR
# ============================================

@router.post(
    "/yape/crear",
    response_model=YapePaymentResponse | YapePaymentError,
    summary="Crear pago con Yape",
    description="Genera un código QR para pagar con Yape"
)
async def crear_pago_yape(
    request: Request,
    datos: YapePaymentRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea una orden de pago con Yape via Tunki.

    El flujo es:
    1. Cliente selecciona Yape como método de pago
    2. Backend crea orden en Tunki y obtiene QR
    3. Frontend muestra QR al cliente
    4. Cliente escanea QR con app Yape y paga
    5. Tunki notifica via webhook cuando se completa
    """
    # Verificar que el servicio pertenece al usuario
    servicio = db.query(Servicio).filter(Servicio.id == datos.servicio_id).first()

    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado"
        )

    if current_user.cliente and servicio.cliente_id != current_user.cliente.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para pagar este servicio"
        )

    # Obtener datos del cliente
    cliente_email = current_user.email
    cliente_nombre = current_user.nombre_completo
    cliente_telefono = datos.telefono_cliente or current_user.telefono_principal

    # Crear pago con Yape
    yape_service = YapePaymentService(db)
    resultado = await yape_service.crear_pago_yape(
        servicio_id=datos.servicio_id,
        cliente_email=cliente_email,
        cliente_telefono=cliente_telefono,
        cliente_nombre=cliente_nombre
    )

    if isinstance(resultado, YapePaymentError):
        logger.warning(
            f"Error creando pago Yape: servicio={datos.servicio_id}, "
            f"error={resultado.error}"
        )

    return resultado


@router.get(
    "/yape/estado/{order_id}",
    response_model=YapeStatusResponse,
    summary="Verificar estado de pago Yape"
)
async def verificar_estado_yape(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Verifica el estado de un pago con Yape.

    El frontend puede usar este endpoint para polling
    y detectar cuando el pago se completa.
    """
    yape_service = YapePaymentService(db)
    estado = await yape_service.verificar_estado_pago(order_id)

    # Verificar permisos
    if estado.servicio_id:
        servicio = db.query(Servicio).filter(Servicio.id == estado.servicio_id).first()
        if servicio and current_user.cliente and servicio.cliente_id != current_user.cliente.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este pago"
            )

    return estado


@router.post(
    "/yape/cancelar/{order_id}",
    summary="Cancelar pago Yape pendiente"
)
async def cancelar_pago_yape(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Cancela un pago con Yape que aún está pendiente"""
    # Verificar que el pago existe y pertenece al usuario
    pago = db.query(Pago).filter(Pago.transaccion_id == order_id).first()

    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )

    servicio = db.query(Servicio).filter(Servicio.id == pago.servicio_id).first()
    if current_user.cliente and servicio.cliente_id != current_user.cliente.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para cancelar este pago"
        )

    if pago.estado != EstadoPagoEnum.pendiente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden cancelar pagos pendientes"
        )

    # Cancelar en Tunki
    exito, mensaje = await tunki_service.cancelar_orden(order_id)

    if exito:
        pago.estado = EstadoPagoEnum.cancelado
        pago.motivo_rechazo = "Cancelado por el usuario"
        db.commit()

    return {"success": exito, "message": mensaje}


# ============================================
# WEBHOOK DE TUNKI (YAPE)
# ============================================

@router.post(
    "/webhook/tunki",
    status_code=status.HTTP_200_OK,
    summary="Webhook de Tunki",
    include_in_schema=False
)
async def webhook_tunki(
    request: Request,
    db: Session = Depends(get_db),
    x_tunki_signature: Optional[str] = Header(None)
):
    """
    Recibe eventos de webhook de Tunki (Yape).

    Eventos soportados:
    - payment.completed: Pago completado
    - payment.expired: Pago expirado
    - payment.failed: Pago fallido
    - payment.cancelled: Pago cancelado
    """
    body = await request.body()

    # Verificar firma del webhook
    if settings.TUNKI_WEBHOOK_SECRET:
        if not tunki_service.verificar_firma_webhook(body, x_tunki_signature or ""):
            logger.warning("Webhook Tunki: Firma inválida")
            raise HTTPException(status_code=401, detail="Firma inválida")

    try:
        data = json.loads(body)
        event_type = data.get("event_type", "")

        logger.info(f"Webhook Tunki recibido: {event_type}")

        # Procesar evento
        yape_service = YapePaymentService(db)
        await yape_service.procesar_webhook(data)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook Tunki: Error procesando - {str(e)}")
        return {"status": "error", "message": str(e)}


# ============================================
# UTILIDADES
# ============================================

@router.get(
    "/culqi/public-key",
    summary="Obtener public key de Culqi",
    description="Retorna la llave pública de Culqi para el frontend"
)
async def obtener_culqi_public_key():
    """
    Retorna la llave pública de Culqi para usar en el frontend.
    Esta key es segura de exponer al cliente.
    """
    if not settings.CULQI_PUBLIC_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Culqi no está configurado"
        )

    return {
        "public_key": settings.CULQI_PUBLIC_KEY,
        "environment": "live" if settings.CULQI_PUBLIC_KEY.startswith("pk_live_") else "test"
    }


@router.get(
    "/metodos-disponibles",
    summary="Obtener métodos de pago disponibles"
)
async def obtener_metodos_disponibles():
    """
    Retorna los métodos de pago disponibles según la configuración.
    """
    metodos = []

    # Tarjeta (Culqi)
    if settings.CULQI_PUBLIC_KEY and settings.CULQI_SECRET_KEY:
        metodos.append({
            "id": "tarjeta",
            "nombre": "Tarjeta de crédito/débito",
            "descripcion": "Visa, Mastercard, Diners Club",
            "disponible": True,
            "tipo": "instantaneo",
            "icono": "credit-card"
        })

    # Yape (Tunki)
    if settings.TUNKI_API_KEY:
        metodos.append({
            "id": "yape",
            "nombre": "Yape",
            "descripcion": "Paga escaneando el código QR",
            "disponible": True,
            "tipo": "qr",
            "icono": "mobile-alt"
        })

    # Plin (pendiente integración)
    metodos.append({
        "id": "plin",
        "nombre": "Plin",
        "descripcion": "Confirmar pago con comprobante",
        "disponible": True,
        "tipo": "manual",
        "icono": "mobile-alt"
    })

    # Efectivo
    metodos.append({
        "id": "efectivo",
        "nombre": "Efectivo",
        "descripcion": "Paga al técnico al finalizar",
        "disponible": True,
        "tipo": "presencial",
        "icono": "money-bill"
    })

    return {
        "metodos": metodos,
        "default": "yape" if settings.TUNKI_API_KEY else "tarjeta"
    }
