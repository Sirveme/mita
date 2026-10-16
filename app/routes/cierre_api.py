"""
API de identificación del comprador (etapa 2) y cierre/comprobante (etapa 7). zMita-39.
"""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.comprobantes_api import require_tecnico
from app.routes.servicio_api import _sol, _es_mi_servicio, _acceso_chat, _es_admin
from app.services import otp, identificacion, cierre

logger = logging.getLogger("mita.cierre_api")
router = APIRouter(tags=["Cierre e identificación"])


# ========================= Parte A — Identificación =========================
@router.post("/api/v1/identificacion/otp/enviar")
async def otp_enviar(data: dict = Body(...), request: Request = None, db: Session = Depends(get_db)):
    from app.services import ratelimit
    cel = (data or {}).get("celular", "")
    ratelimit.exigir(request, "otp_ip", 10, 3600)          # por IP: 10/hora
    ratelimit.exigir(request, "otp_num", 3, 3600, extra=cel)  # por número: 3/hora
    return otp.enviar_codigo(db, cel)


@router.post("/api/v1/identificacion/otp/verificar")
async def otp_verificar(data: dict = Body(...), request: Request = None, db: Session = Depends(get_db)):
    from app.services import ratelimit
    ratelimit.exigir(request, "otp_verif", 20, 3600)   # por IP: 20 verificaciones/hora
    r = otp.verificar_codigo(db, (data or {}).get("celular", ""), (data or {}).get("codigo", ""))
    sid = (data or {}).get("solicitud_id")
    if sid:
        s = _sol(db, sid)
        s.celular_estado = r.get("estado", "pendiente")
        s.celular_verificado = bool(r.get("ok"))
        db.commit()
    return r


@router.get("/api/v1/identificacion/consulta")
async def identificacion_consulta(tipo: str, numero: str):
    return identificacion.consultar_documento(tipo, numero)


@router.get("/api/v1/servicios/{sid}/comprador")
async def comprador_get(sid: int, db: Session = Depends(get_db)):
    s = _sol(db, sid)
    cp = identificacion.comprador_recordado(db, s.cliente_telefono or "")
    recordado = None
    if cp:
        recordado = {"tipo_comprobante": cp.tipo_comprobante, "doc_tipo": cp.doc_tipo,
                     "doc_numero": cp.doc_numero, "razon_social": cp.razon_social,
                     "direccion_fiscal": cp.direccion_fiscal}
    return {"celular_estado": s.celular_estado, "celular_verificado": bool(s.celular_verificado),
            "actual": {"tipo_comprobante": s.comprador_tipo_comprobante, "doc_tipo": s.comprador_doc_tipo,
                       "doc_numero": s.comprador_doc_numero, "razon_social": s.comprador_nombre,
                       "direccion_fiscal": s.comprador_direccion_fiscal},
            "recordado": recordado}


@router.post("/api/v1/servicios/{sid}/comprador")
async def comprador_set(sid: int, data: dict = Body(...), db: Session = Depends(get_db)):
    s = _sol(db, sid)
    r = identificacion.guardar_comprador(db, s, data or {})
    if not r.get("ok"):
        raise HTTPException(status_code=422, detail=r.get("mensaje", "Datos inválidos"))
    return r


# ========================= Parte B — Cierre (técnico) =======================
@router.post("/api/v1/tecnico/servicios/{sid}/terminar")
async def terminar(sid: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = _sol(db, sid); _es_mi_servicio(s, pid)
    r = cierre.terminar(db, s)
    if not r.get("ok"):
        raise HTTPException(status_code=409, detail=r.get("mensaje"))
    return r


@router.post("/api/v1/tecnico/servicios/{sid}/efectivo")
async def efectivo_tecnico(sid: int, data: dict = Body(...), db: Session = Depends(get_db),
                           pid: int = Depends(require_tecnico)):
    s = _sol(db, sid); _es_mi_servicio(s, pid)
    try:
        monto = float((data or {}).get("monto"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Monto inválido")
    r = cierre.declarar_efectivo_tecnico(db, s, monto)
    if not r.get("ok"):
        raise HTTPException(status_code=409, detail=r.get("mensaje"))
    return r


# ========================= Parte B — Cierre (cliente) =======================
@router.post("/api/v1/servicios/{sid}/cobro-digital")
async def cobro_digital(sid: int, request: Request = None, db: Session = Depends(get_db)):
    """Confirmación MANUAL de cobro digital. Peligrosa: marca PAGADO sin pasar por PagoOK.
    Por eso solo existe fuera de producción (404 en prod) y exige rol admin. El cobro real
    de la reparación va por QR (/pagar/{id}?concepto=reparacion) validado con PagoOK."""
    from app.core.security import es_produccion
    if es_produccion():
        raise HTTPException(status_code=404, detail="No encontrado")
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    s = _sol(db, sid)
    r = cierre.confirmar_pago_digital(db, s)
    if not r.get("ok"):
        raise HTTPException(status_code=409, detail=r.get("mensaje"))
    return r


@router.post("/api/v1/servicios/{sid}/efectivo-confirmar")
async def efectivo_confirmar(sid: int, data: dict = Body(...), request: Request = None,
                             db: Session = Depends(get_db)):
    s = _sol(db, sid)
    await _acceso_chat(request, db, s, "cliente")
    try:
        monto = float((data or {}).get("monto"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Monto inválido")
    r = cierre.confirmar_efectivo_cliente(db, s, monto)
    if not r.get("ok"):
        raise HTTPException(status_code=409, detail=r.get("mensaje"))
    return r


@router.post("/api/v1/servicios/{sid}/conformidad")
async def conformidad(sid: int, data: dict = Body(...), request: Request = None, db: Session = Depends(get_db)):
    s = _sol(db, sid)
    await _acceso_chat(request, db, s, "cliente")
    d = data or {}
    r = cierre.registrar_conformidad(db, s, bool(d.get("resuelto")),
                                     estrellas=d.get("estrellas"), comentario=d.get("comentario"))
    return r


# ========================= Torre =========================
@router.get("/api/v1/admin/cierres")
async def admin_cierres(request: Request, db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    return cierre.torre_cierres(db)


@router.post("/api/v1/admin/servicios/{sid}/validar-efectivo")
async def admin_validar_efectivo(sid: int, data: dict = Body(...), request: Request = None,
                                 db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    s = _sol(db, sid)
    d = data or {}
    try:
        monto = float(d.get("monto"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Monto inválido")
    u = None
    try:
        from app.routes.login_mita import get_current_user
        u = await get_current_user(request, db)
    except Exception:
        pass
    return cierre.validar_efectivo_torre(db, s, monto, validado_por=str(getattr(u, "id", "torre")),
                                         motivo=d.get("motivo", ""))


@router.post("/api/v1/admin/servicios/{sid}/reintentar-comprobante")
async def admin_reintentar_comprobante(sid: int, data: dict = Body(default={}), request: Request = None,
                                       db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    s = _sol(db, sid)
    return cierre.reintentar_comprobante(db, s, (data or {}).get("concepto", "reparacion"))


@router.post("/api/v1/admin/comprobantes/{cid}/anular")
async def admin_anular_comprobante(cid: int, data: dict = Body(...), request: Request = None,
                                   db: Session = Depends(get_db)):
    """Anula un comprobante aceptado emitiendo una NC motivo 01. Motivo obligatorio +
    doble confirmación (confirmar=true, que envía la torre tras confirmar dos veces)."""
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.models.cierre import ComprobanteEmitido
    from app.services import comprobante
    d = data or {}
    motivo = (d.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=422, detail="El motivo de la anulación es obligatorio")
    if not d.get("confirmar"):
        raise HTTPException(status_code=428, detail="Falta la doble confirmación")
    ce = db.query(ComprobanteEmitido).get(cid)
    if not ce:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    u = None
    try:
        from app.routes.login_mita import get_current_user
        u = await get_current_user(request, db)
    except Exception:
        pass
    r = comprobante.anular(db, ce, motivo, por=str(getattr(u, "id", "torre")))
    if not r.get("ok"):
        raise HTTPException(status_code=409, detail=r.get("mensaje", "No se pudo anular"))
    return r
