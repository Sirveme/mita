"""
API de liquidación a técnicos (etapa 8, zMita-41).
Lenguaje: "Tu liquidación", "Tu parte", "Recibo por Honorarios". Nunca sueldo/planilla/haberes.
"""
import logging
from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.comprobantes_api import require_tecnico
from app.routes.servicio_api import _es_admin
from app.services import liquidacion as liq_srv

logger = logging.getLogger("mita.liquidacion_api")
router = APIRouter(tags=["Liquidación"])

PARAMS = ["visita_parte_mita", "comision_reparacion_tipo", "comision_reparacion_valor",
          "periodo_liquidacion", "comision_medio_pago_asume",
          "retencion_4ta_activa", "retencion_4ta_tasa", "retencion_4ta_umbral"]


async def _guard_admin(request, db):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")


def _liq_dict(l):
    return {"id": l.id, "tecnico_id": l.tecnico_id,
            "periodo_inicio": l.periodo_inicio.isoformat() if l.periodo_inicio else None,
            "periodo_fin": l.periodo_fin.isoformat() if l.periodo_fin else None,
            "estado": l.estado, "cantidad": l.cantidad_servicios,
            "parte_tecnico": l.parte_tecnico, "parte_mita": l.parte_mita,
            "efectivo_en_poder_tecnico": l.efectivo_en_poder_tecnico,
            "saldo_arrastrado": l.saldo_arrastrado, "a_transferir": l.a_transferir,
            "saldo_a_favor_mita": l.saldo_a_favor_mita,
            "rxh_numero": l.rxh_numero, "rxh_monto": l.rxh_monto, "rxh_pdf_url": bool(l.rxh_pdf_url),
            "retencion_monto": l.retencion_monto, "neto_rxh": l.neto_rxh,
            "pago_fecha": l.pago_fecha.isoformat() if l.pago_fecha else None,
            "pago_medio": l.pago_medio, "pago_operacion": l.pago_operacion}


def _item_dict(it):
    return {"solicitud_id": it.solicitud_id, "codigo": it.codigo,
            "fecha_cierre": it.fecha_cierre.isoformat() if it.fecha_cierre else None,
            "total": it.total, "visita": it.visita, "reparacion": it.reparacion,
            "efectivo_tecnico": it.efectivo_tecnico, "parte_mita": it.parte_mita,
            "parte_tecnico": it.parte_tecnico, "comision_tipo": it.comision_tipo,
            "comision_valor": it.comision_valor}


def _nombre(db, tecnico_id):
    from app.models.personal import Personal
    p = db.query(Personal).get(tecnico_id) if tecnico_id else None
    return f"{p.nombres} {p.apellido_paterno or ''}".strip() if p else f"Técnico {tecnico_id}"


# ============================ Torre ============================
@router.get("/api/v1/admin/liquidaciones")
async def admin_listar(periodo: str = None, request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    from app.models.liquidacion_mita import LiquidacionMita
    q = db.query(LiquidacionMita)
    if periodo:
        try:
            q = q.filter(LiquidacionMita.periodo_inicio == date.fromisoformat(periodo))
        except Exception:
            pass
    rows = q.order_by(LiquidacionMita.periodo_inicio.desc(), LiquidacionMita.id.desc()).limit(300).all()
    return {"items": [{**_liq_dict(l), "tecnico": _nombre(db, l.tecnico_id)} for l in rows]}


@router.get("/api/v1/admin/liquidaciones/{lid}")
async def admin_detalle(lid: int, request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    from app.models.liquidacion_mita import LiquidacionMita, LiquidacionItem
    l = db.query(LiquidacionMita).get(lid)
    if not l:
        raise HTTPException(404, "No encontrada")
    items = db.query(LiquidacionItem).filter(LiquidacionItem.liquidacion_id == lid).all()
    return {"liquidacion": {**_liq_dict(l), "tecnico": _nombre(db, l.tecnico_id)},
            "items": [_item_dict(i) for i in items]}


@router.post("/api/v1/admin/liquidaciones/generar")
async def admin_generar(data: dict = Body(default={}), request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    lunes = None
    if (data or {}).get("lunes"):
        try:
            lunes = date.fromisoformat(data["lunes"])
        except Exception:
            raise HTTPException(422, "lunes inválido (YYYY-MM-DD)")
    return liq_srv.generar(db, lunes=lunes)


def _liq(db, lid):
    from app.models.liquidacion_mita import LiquidacionMita
    l = db.query(LiquidacionMita).get(lid)
    if not l:
        raise HTTPException(404, "No encontrada")
    return l


@router.post("/api/v1/admin/liquidaciones/{lid}/enviar")
async def admin_enviar(lid: int, request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    r = liq_srv.enviar(db, _liq(db, lid))
    if not r["ok"]:
        raise HTTPException(409, r["mensaje"])
    return r


@router.post("/api/v1/admin/liquidaciones/{lid}/aprobar")
async def admin_aprobar(lid: int, request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    r = liq_srv.aprobar(db, _liq(db, lid))
    if not r["ok"]:
        raise HTTPException(409, r["mensaje"])
    return r


@router.post("/api/v1/admin/liquidaciones/{lid}/pagar")
async def admin_pagar(lid: int, data: dict = Body(...), request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    d = data or {}
    r = liq_srv.pagar(db, _liq(db, lid), d.get("medio"), d.get("operacion"))
    if not r["ok"]:
        raise HTTPException(409, r["mensaje"])
    return r


@router.get("/api/v1/admin/liquidaciones/export/xlsx")
async def admin_export(periodo: str = None, request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    from app.models.liquidacion_mita import LiquidacionMita
    from app.services.xlsx import build_xlsx
    q = db.query(LiquidacionMita)
    if periodo:
        try:
            q = q.filter(LiquidacionMita.periodo_inicio == date.fromisoformat(periodo))
        except Exception:
            pass
    rows = q.order_by(LiquidacionMita.periodo_inicio.desc(), LiquidacionMita.tecnico_id).all()
    headers = ["Periodo", "Técnico", "Servicios", "Parte técnico (bruto)", "Parte MITA",
               "Efectivo en su poder", "Saldo arrastrado", "A transferir", "Saldo a favor MITA",
               "Estado", "RxH N°", "Retención 4ta", "Neto RxH", "Pago medio", "Pago operación"]
    data = [[l.periodo_inicio.isoformat() if l.periodo_inicio else "", _nombre(db, l.tecnico_id),
             l.cantidad_servicios, l.parte_tecnico, l.parte_mita, l.efectivo_en_poder_tecnico,
             l.saldo_arrastrado, l.a_transferir, l.saldo_a_favor_mita, l.estado, l.rxh_numero or "",
             l.retencion_monto or 0, l.neto_rxh or 0, l.pago_medio or "", l.pago_operacion or ""]
            for l in rows]
    xlsx = build_xlsx(headers, data)
    nombre = f"liquidaciones_{periodo or 'todas'}.xlsx"
    return Response(content=xlsx,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/api/v1/admin/liquidacion-params")
async def admin_params(request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    from app.services.config_service import ConfigService
    return {k: ConfigService.get(db, k, None) for k in PARAMS}


@router.post("/api/v1/admin/liquidacion-params")
async def admin_set_params(data: dict = Body(...), request: Request = None, db: Session = Depends(get_db)):
    await _guard_admin(request, db)
    u = None
    try:
        from app.routes.login_mita import get_current_user
        u = await get_current_user(request, db)
    except Exception:
        pass
    tipos = {"visita_parte_mita": "float", "comision_reparacion_valor": "float",
             "retencion_4ta_tasa": "float", "retencion_4ta_umbral": "float",
             "retencion_4ta_activa": "bool"}
    cambiados = []
    for k, v in (data or {}).items():
        if k in PARAMS:
            liq_srv.set_param(db, k, v, tipo=tipos.get(k, "string"), creado_por=str(getattr(u, "id", "admin")))
            cambiados.append(k)
    return {"ok": True, "cambiados": cambiados}


# ============================ Técnico ============================
@router.get("/api/v1/tecnico/mi-liquidacion")
async def mi_liquidacion(db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    from app.models.liquidacion_mita import LiquidacionMita, LiquidacionItem
    rows = (db.query(LiquidacionMita).filter(LiquidacionMita.tecnico_id == pid)
            .order_by(LiquidacionMita.periodo_inicio.desc(), LiquidacionMita.id.desc()).limit(50).all())
    actual = rows[0] if rows else None
    items = []
    if actual:
        items = db.query(LiquidacionItem).filter(LiquidacionItem.liquidacion_id == actual.id).all()
    return {"actual": _liq_dict(actual) if actual else None,
            "items": [_item_dict(i) for i in items],
            "historial": [_liq_dict(l) for l in rows]}


@router.post("/api/v1/tecnico/liquidaciones/{lid}/rxh")
async def subir_rxh(lid: int, data: dict = Body(...), db: Session = Depends(get_db),
                    pid: int = Depends(require_tecnico)):
    from app.models.liquidacion_mita import LiquidacionMita
    l = db.query(LiquidacionMita).get(lid)
    if not l or l.tecnico_id != pid:
        raise HTTPException(404, "No encontrada")
    d = data or {}
    numero = (d.get("rxh_numero") or "").strip()
    pdf = (d.get("rxh_pdf_url") or "").strip()
    if not numero:
        raise HTTPException(422, "Falta el número de RxH.")
    # Validación del PDF: si viene como data URL, exigir application/pdf y <= 5 MB.
    if pdf.startswith("data:"):
        if not pdf.startswith("data:application/pdf"):
            raise HTTPException(422, "El archivo debe ser un PDF.")
        import base64
        try:
            crudo = pdf.split(",", 1)[1]
            tam = len(base64.b64decode(crudo + "=" * (-len(crudo) % 4)))
        except Exception:
            raise HTTPException(422, "PDF inválido.")
        if tam > 5 * 1024 * 1024:
            raise HTTPException(422, "El PDF supera los 5 MB.")
    r = liq_srv.subir_rxh(db, l, numero, pdf, d.get("rxh_monto"))
    if not r["ok"]:
        raise HTTPException(409, r["mensaje"])
    return r
