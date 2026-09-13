"""
Pagos por pasarela — cierre del ciclo: pago → webhook → comprobante → servicio.

Público:
  POST /api/v1/pagos/iniciar
  POST /api/v1/pagos/webhook/izipay      (IziPay notifica; SIEMPRE responde 200)
  GET  /api/v1/pagos/{referencia}/estado (polling del frontend)
  GET  /api/v1/pagos/retorno             (página de retorno tras pagar)
Admin (protegido):
  GET  /api/v1/admin/pagos
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Body, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.models.pago import PagoPasarela as Pago
from app.models.comprobante import ServicioCompletado
from app.services import pasarela_service, facturalo_service
from app.routes.admin_postulantes import require_admin_gerente

logger = logging.getLogger("mita.pagos")
router = APIRouter(tags=["Pagos"])

BASE_URL = ""  # relativo: usamos rutas propias para retorno/webhook


def _pago_dict(p: Pago) -> dict:
    return {
        "id": p.id, "referencia": p.referencia, "solicitud_id": p.solicitud_id, "servicio_id": p.servicio_id,
        "monto": float(p.monto) if p.monto is not None else None, "moneda": p.moneda, "estado": p.estado,
        "pasarela": p.pasarela, "url_pago": p.url_pago,
        "respuesta_codigo": p.respuesta_codigo, "respuesta_mensaje": p.respuesta_mensaje,
        "cliente_email": p.cliente_email, "cliente_telefono": p.cliente_telefono,
        "comprobante_emitido": bool(p.comprobante_emitido), "comprobante_tipo": p.comprobante_tipo,
        "comprobante_serie": p.comprobante_serie, "comprobante_numero": p.comprobante_numero,
        "creado_en": p.creado_en.isoformat() if p.creado_en else None,
        "pagado_en": p.pagado_en.isoformat() if p.pagado_en else None,
    }


# ============================================
# Iniciar pago
# ============================================

@router.post("/api/v1/pagos/iniciar")
def iniciar_pago(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    monto = float(data.get("monto") or 0)
    if monto <= 0:
        return JSONResponse({"success": False, "detail": "Monto inválido."}, status_code=400)

    base = str(request.base_url).rstrip("/")
    url_retorno = f"{base}/api/v1/pagos/retorno"
    url_webhook = f"{base}/api/v1/pagos/webhook/izipay"
    cliente = {"email": data.get("cliente_email"), "ruc": data.get("cliente_ruc"),
               "telefono": data.get("cliente_telefono")}

    res = pasarela_service.crear_pago(db, monto=monto, descripcion="Servicio MITA",
                                      cliente=cliente, url_retorno=url_retorno, url_webhook=url_webhook)
    p = Pago(
        referencia=res["referencia"], solicitud_id=data.get("solicitud_id"),
        servicio_id=data.get("servicio_id"), monto=monto, estado="PENDIENTE",
        pasarela=res.get("pasarela"), token_pago=res.get("token_pago"), url_pago=res.get("url_pago"),
        comprobante_tipo=data.get("tipo_comprobante", "boleta"),
        cliente_email=data.get("cliente_email"), cliente_telefono=data.get("cliente_telefono"),
    )
    db.add(p)
    db.commit()
    return {"success": True, "referencia": p.referencia, "url_pago": p.url_pago, "simulado": res.get("simulado", False)}


# ============================================
# Aprobación + emisión de comprobante
# ============================================

def _aprobar_y_facturar(db: Session, p: Pago):
    """Marca el pago APROBADO, emite el comprobante y actualiza el servicio. No lanza."""
    try:
        p.estado = "APROBADO"
        p.pagado_en = datetime.utcnow()
        if not p.comprobante_emitido:
            res = facturalo_service.emitir_comprobante(
                db, tipo=(p.comprobante_tipo or "boleta"),
                cliente={"email": p.cliente_email, "ruc": None},
                items=[{"descripcion": "Servicio técnico MITA", "cantidad": 1, "precio": float(p.monto or 0)}],
                monto=float(p.monto or 0),
            )
            if res.get("ok"):
                p.comprobante_emitido = True
                p.comprobante_tipo = p.comprobante_tipo or "boleta"
                p.comprobante_serie = res.get("serie")
                p.comprobante_numero = res.get("numero")
                # Reflejar en el servicio si está enlazado
                if p.servicio_id:
                    s = db.query(ServicioCompletado).get(p.servicio_id)
                    if s and not s.comprobante_emitido:
                        s.comprobante_emitido = True
                        s.comprobante_tipo = p.comprobante_tipo
                        s.comprobante_serie = p.comprobante_serie
                        s.comprobante_numero = p.comprobante_numero
                        s.fecha_comprobante = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error al aprobar/facturar pago %s: %s", getattr(p, "referencia", "?"), e)


# ============================================
# Webhook (IziPay) — SIEMPRE 200
# ============================================

@router.post("/api/v1/pagos/webhook/izipay")
async def webhook_izipay(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        # TODO: validar firma/autenticidad con api_secret antes de confiar
        info = pasarela_service.procesar_webhook(db, payload, dict(request.headers))
        ref = info.get("referencia")
        p = db.query(Pago).filter(Pago.referencia == ref).first() if ref else None
        if p:
            p.respuesta_json = payload
            p.respuesta_mensaje = info.get("evento")
            estado = info.get("estado")
            if estado == "APROBADO":
                _aprobar_y_facturar(db, p)
            elif estado:
                p.estado = estado
                db.commit()
        else:
            logger.warning("Webhook IziPay: referencia no encontrada -> %s", ref)
    except Exception as e:
        logger.error("Error procesando webhook IziPay: %s", e)  # nunca romper: IziPay espera 200
    return JSONResponse({"received": True}, status_code=200)


# ============================================
# Estado (polling) + retorno
# ============================================

@router.get("/api/v1/pagos/{referencia}/estado")
def estado_pago(referencia: str, db: Session = Depends(get_db)):
    p = db.query(Pago).filter(Pago.referencia == referencia).first()
    if not p:
        return JSONResponse({"success": False, "detail": "No encontrado"}, status_code=404)
    return {"success": True, "referencia": p.referencia, "estado": p.estado,
            "comprobante_emitido": bool(p.comprobante_emitido),
            "comprobante": (f"{p.comprobante_serie}-{p.comprobante_numero}" if p.comprobante_emitido else None)}


@router.get("/api/v1/pagos/retorno", response_class=HTMLResponse)
async def retorno_pago(request: Request, ref: Optional[str] = None, sim: Optional[str] = None,
                       db: Session = Depends(get_db)):
    p = db.query(Pago).filter(Pago.referencia == ref).first() if ref else None
    # En modo simulado (sin pasarela real), no llegará webhook: cerramos el ciclo aquí.
    if p and sim == "1" and p.estado in ("PENDIENTE", "EN_PROCESO"):
        _aprobar_y_facturar(db, p)
        db.refresh(p)
    exito = bool(p and p.estado == "APROBADO")
    return templates.TemplateResponse("pagos/retorno.html", {
        "request": request, "exito": exito, "pago": _pago_dict(p) if p else None, "referencia": ref,
    })


# ============================================
# Admin — lista de pagos
# ============================================

@router.get("/api/v1/admin/pagos")
def listar_pagos(estado: Optional[str] = None, con_comprobante: Optional[str] = None,
                 desde: Optional[str] = None, hasta: Optional[str] = None,
                 db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    q = db.query(Pago)
    if estado:
        q = q.filter(Pago.estado == estado)
    if con_comprobante in ("true", "false"):
        q = q.filter(Pago.comprobante_emitido.is_(con_comprobante == "true"))
    if desde:
        q = q.filter(Pago.creado_en >= desde)
    if hasta:
        q = q.filter(Pago.creado_en <= hasta + " 23:59:59")
    items = q.order_by(Pago.creado_en.desc()).all()
    return {"success": True, "items": [_pago_dict(p) for p in items]}
