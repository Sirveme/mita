"""
API de pago por QR (Yape/Plin) validado con PagoOK (zMita-34 v2).

El frontend consulta a MITA (este router); SOLO el backend consulta a PagoOK.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.pago_solicitud import PagoSolicitud
from app.services import pagook

logger = logging.getLogger("mita.pagook")
router = APIRouter(prefix="/api/v1/pagos-qr", tags=["Pagos QR"])


def _numero_qr(db):
    try:
        from app.models.chat_conocimiento import ChatConocimiento
        filas = {r.clave: (r.contenido or "") for r in db.query(ChatConocimiento).filter(
            ChatConocimiento.clave.in_(["pago_qr_numero", "pago_qr_imagen"])).all()}
        import re
        return re.sub(r"\D", "", filas.get("pago_qr_numero", "")), (filas.get("pago_qr_imagen") or "").strip()
    except Exception:
        return "", ""


async def _es_admin(request: Request, db: Session) -> bool:
    try:
        from app.routes.login_mita import get_current_user
        u = await get_current_user(request, db)
        tipo = (getattr(u, "tipo", "") or "").lower()
        return tipo in ("admin", "gerente", "secretaria")
    except Exception:
        return False


@router.get("/config")
async def config(db: Session = Depends(get_db)):
    """Datos para la pantalla de pago (zMita-42). El QR se muestra si hay número O imagen;
    la validación automática (PagoOK) es independiente: sin credencial, el pago lo confirma la torre."""
    numero, qr = _numero_qr(db)
    titular = ""
    try:
        from app.models.chat_conocimiento import ChatConocimiento
        row = db.query(ChatConocimiento).filter(ChatConocimiento.clave == "pago_qr_titular").first()
        titular = (row.contenido or "").strip() if row else ""
    except Exception:
        pass
    return {"habilitado": bool(numero or qr), "numero": numero, "qr_imagen": qr,
            "auto_validacion": pagook.configurado(), "titular": titular}


def _solicitud(db, solicitud_id):
    from app.models.solicitud_mita import Solicitud
    return db.query(Solicitud).get(int(solicitud_id))


def _concepto(v):
    return "reparacion" if (str(v or "").strip().lower() == "reparacion") else "visita"


def _ps_actual(db, solicitud_id, concepto="visita"):
    return (db.query(PagoSolicitud)
            .filter(PagoSolicitud.solicitud_id == int(solicitud_id),
                    PagoSolicitud.concepto == concepto)
            .order_by(PagoSolicitud.id.desc()).first())


@router.post("/iniciar")
async def iniciar(data: dict = Body(...), db: Session = Depends(get_db)):
    """Muestra el QR: crea el pago en 'esperando_pago'. Sin PagoOK igual se muestra;
    la validación la hace la torre (nunca se marca pagado solo)."""
    numero, qr_img = _numero_qr(db)
    if not (numero or qr_img):
        raise HTTPException(status_code=503, detail="Pago por QR no disponible")
    sid = data.get("solicitud_id")
    if not sid:
        raise HTTPException(status_code=422, detail="Falta solicitud_id")
    sol = _solicitud(db, sid)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    concepto = _concepto(data.get("concepto"))
    canal = (data.get("canal") or "yape").lower()
    if canal not in ("yape", "plin"):
        canal = "yape"
    # Monto por defecto según el concepto: reparación -> monto_por_cobrar; visita -> costo_visita.
    if concepto == "reparacion":
        defecto = float(getattr(sol, "monto_por_cobrar", None) or getattr(sol, "costo_servicio", None) or 0.0)
    else:
        defecto = float(getattr(sol, "costo_visita", None) or 50.0)
    monto = data.get("monto")
    try:
        monto = float(monto) if monto is not None else defecto
    except (TypeError, ValueError):
        monto = defecto
    if concepto == "reparacion" and not (monto > 0):
        raise HTTPException(status_code=409, detail="No hay un monto por cobrar para la reparación")

    ps = _ps_actual(db, sid, concepto)
    if not ps or ps.estado == "pagada":
        if ps and ps.estado == "pagada":
            return {"ok": True, "ya_pagada": True, "monto": float(ps.monto_esperado or monto)}
        ps = PagoSolicitud(solicitud_id=int(sid), concepto=concepto)
        db.add(ps)
    ps.concepto = concepto
    ps.estado = "esperando_pago"
    ps.canal = canal
    ps.monto_esperado = monto
    ps.titular_declarado = (data.get("titular_declarado") or getattr(sol, "cliente_nombre", "") or "").strip()[:150]
    ps.codigo_operacion = (data.get("codigo_operacion") or "").strip()[:50] or None
    ps.comprador_nombre = (data.get("comprador_nombre") or getattr(sol, "cliente_nombre", "") or "").strip()[:150] or None
    ps.comprador_doc_tipo = (data.get("comprador_doc_tipo") or "").strip()[:12] or None
    ps.comprador_doc_numero = (data.get("comprador_doc_numero") or "").strip()[:20] or None
    ps.qr_mostrado_en = datetime.utcnow()
    if concepto == "visita":
        sol.estado = "ESPERANDO_PAGO"   # la reparación conserva POR_COBRAR hasta confirmarse
    db.commit()
    numero, qr = _numero_qr(db)
    return {"ok": True, "pago_solicitud_id": ps.id, "monto": monto, "canal": canal,
            "numero": numero, "qr_imagen": qr, "titular_declarado": ps.titular_declarado}


@router.post("/ya-pague")
async def ya_pague(data: dict = Body(...), db: Session = Depends(get_db)):
    """El cliente tocó 'Ya pagué': registra la hora y dispara la primera verificación."""
    sid = data.get("solicitud_id")
    ps = _ps_actual(db, sid, _concepto(data.get("concepto"))) if sid else None
    if not ps:
        raise HTTPException(status_code=404, detail="No hay un pago iniciado para esta solicitud")
    if ps.estado == "pagada":
        return pagook.verificar_pago(db, ps)
    # Actualizar datos de último momento (titular/código editables)
    if data.get("titular_declarado"):
        ps.titular_declarado = str(data["titular_declarado"]).strip()[:150]
    if data.get("codigo_operacion"):
        ps.codigo_operacion = str(data["codigo_operacion"]).strip()[:50]
    ps.fecha_hora_declarada = datetime.utcnow()
    ps.estado = "verificando"
    db.commit()
    return pagook.verificar_pago(db, ps, forzar=True)


@router.get("/estado/{solicitud_id}")
async def estado(solicitud_id: int, concepto: str = "visita", request: Request = None,
                 db: Session = Depends(get_db)):
    """La pantalla consulta aquí según la cadencia. El backend consulta a PagoOK con sus guardas."""
    from app.services import ratelimit
    ratelimit.exigir(request, "pagar_estado", 40, 60, extra=str(solicitud_id))  # 40/min por IP y solicitud
    ps = _ps_actual(db, solicitud_id, _concepto(concepto))
    if not ps:
        return {"estado": "sin_iniciar", "pagada": False}
    if ps.estado == "pagada":
        return {"estado": "pagada", "pagada": True, "mensaje": "¡Pago recibido!",
                "comprobante_estado": ps.comprobante_estado}
    # La vigilancia arranca al mostrar el QR (no requiere "Ya pagué")
    r = pagook.verificar_pago(db, ps)
    r["cadencia_ms"] = 10000 if pagook.presion_alta() else None
    r["mostrar_hora_voucher"] = bool(ps.qr_mostrado_en and
                                     (datetime.utcnow() - ps.qr_mostrado_en).total_seconds() > 60
                                     and ps.estado != "pagada")
    r["hora_voucher_puesta"] = bool(ps.hora_voucher)
    return r


@router.post("/hora-voucher")
async def hora_voucher(data: dict = Body(...), db: Session = Depends(get_db)):
    """C2: el cliente declara la hora de su comprobante -> consulta con ventana de 3 min."""
    sid = data.get("solicitud_id")
    hora = data.get("hora")   # ISO local, p.ej. "2026-10-16T10:02:00"
    ps = _ps_actual(db, sid, _concepto(data.get("concepto"))) if sid else None
    if not ps:
        raise HTTPException(status_code=404, detail="No hay un pago iniciado")
    if ps.estado == "pagada":
        return pagook.verificar_pago(db, ps)
    try:
        ps.hora_voucher = datetime.fromisoformat(str(hora).replace("Z", "").split("+")[0].split("-05:00")[0])
    except Exception:
        raise HTTPException(status_code=422, detail="Hora inválida")
    db.commit()
    return pagook.verificar_pago(db, ps, forzar=True, voucher=True)


# -------------------- Torre de control (Parte E) --------------------
@router.get("/admin/pendientes")
async def admin_pendientes(request: Request, db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    rows = (db.query(PagoSolicitud)
            .filter(PagoSolicitud.estado.in_(["esperando_pago", "verificando", "media_pendiente",
                                              "sin_coincidencia", "conflicto", "por_verificar"]))
            .order_by(PagoSolicitud.id.desc()).limit(100).all())
    out = []
    for r in rows:
        try:
            cruda = json.loads(r.respuesta_cruda) if r.respuesta_cruda else {}
        except Exception:
            cruda = {}
        out.append({"id": r.id, "solicitud_id": r.solicitud_id, "estado": r.estado, "nivel": r.nivel,
                    "motivo": r.motivo, "canal": r.canal, "monto": float(r.monto_esperado or 0),
                    "titular_declarado": r.titular_declarado, "contraparte": r.contraparte,
                    "posible_reuso": bool(r.posible_reuso), "confirmado_por": r.confirmado_por,
                    "comprobante_estado": r.comprobante_estado,
                    "candidatos": cruda.get("candidatos") or [],
                    "pagos_ya_usados": cruda.get("pagos_ya_usados") or []})
    return out


@router.post("/admin/usar")
async def admin_usar(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """La torre elige un candidato (media) y lo marca usado -> pagada."""
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    ps = db.query(PagoSolicitud).get(int(data.get("pago_solicitud_id") or 0))
    if not ps:
        raise HTTPException(status_code=404, detail="No existe")
    if ps.estado == "pagada":
        return {"ok": True, "ya_pagada": True}
    pago_id = data.get("pago_id")
    if not pago_id:
        raise HTTPException(status_code=422, detail="Falta pago_id")
    ps.pago_id = int(pago_id)
    ref = pagook._referencia(ps)
    ps.referencia_externa = ref
    m = pagook.marcar_usado(ps.pago_id, ref, sistema="Mita.pe")
    if m.get("status") == 200:
        from app.services.pagook import _al_pagar
        res = _al_pagar(db, ps, operador=True)
        return {"ok": True, "resultado": res}
    if m.get("status") == 409:
        ps.estado = "conflicto"; db.commit()
        raise HTTPException(status_code=409, detail="Ese pago ya fue registrado en otra operación")
    raise HTTPException(status_code=502, detail=f"marcar-usado status {m.get('status')}")


@router.post("/admin/confirmar-manual")
async def admin_confirmar_manual(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """La torre confirma a mano un pago 'por_verificar' (sin PagoOK), tras ver el voucher.
    Es la ÚNICA forma de marcar pagado sin PagoOK, y queda registrada (operador + nota)."""
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    ps = db.query(PagoSolicitud).get(int(data.get("pago_solicitud_id") or 0))
    if not ps:
        raise HTTPException(status_code=404, detail="No existe")
    if ps.estado == "pagada":
        return {"ok": True, "ya_pagada": True}
    nota = (data.get("nota") or "").strip()
    u = None
    try:
        from app.routes.login_mita import get_current_user
        u = await get_current_user(request, db)
    except Exception:
        pass
    ps.referencia_externa = pagook._referencia(ps)
    ps.respuesta_cruda = json.dumps({"confirmacion_manual": {"por": getattr(u, "id", "torre"), "nota": nota,
                                     "cuando": datetime.utcnow().isoformat()}}, ensure_ascii=False)[:8000]
    from app.services.pagook import _al_pagar
    res = _al_pagar(db, ps, operador=True)
    return {"ok": True, "resultado": res, "manual": True}
