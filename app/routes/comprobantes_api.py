"""
Servicios completados, comprobantes y liquidaciones semanales.

Admin (protegido con require_admin_gerente):
  GET  /api/v1/admin/servicios
  GET  /api/v1/admin/servicios/{id}
  GET  /api/v1/admin/liquidaciones
  GET  /api/v1/admin/liquidaciones/{id}
Acciones:
  POST /api/v1/servicios/{solicitud_id}/completar
  POST /api/v1/servicios/{id}/emitir-comprobante
  POST /api/v1/liquidaciones/generar-semanal
  POST /api/v1/liquidaciones/{id}/emitir-rxh      (auto, SOL)
  POST /api/v1/liquidaciones/{id}/subir-rxh       (manual)
  POST /api/v1/liquidaciones/{id}/validar-rxh
  POST /api/v1/liquidaciones/{id}/registrar-pago
Técnico:
  GET  /api/v1/tecnico/liquidaciones
  GET  /api/v1/tecnico/liquidaciones/{id}
"""

import decimal
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.servicio_completado import ServicioCompletado
from app.models.liquidacion_tecnico import LiquidacionTecnico
from app.models.personal import Personal
from app.models.solicitud_mita import Solicitud
from app.services.config_service import ConfigService
from app.services import facturalo_service
from app.routes.admin_postulantes import require_admin_gerente
from app.routes.login_mita import get_current_user

router = APIRouter(tags=["Comprobantes"])


# ============================================
# Helpers
# ============================================

def _f(v):
    return float(v) if isinstance(v, decimal.Decimal) else v


def _lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _nombre_tecnico(db: Session, tecnico_id):
    if not tecnico_id:
        return None
    p = db.query(Personal).get(tecnico_id)
    return f"{p.nombres} {p.apellido_paterno or ''}".strip() if p else None


def _servicio_dict(db: Session, s: ServicioCompletado) -> dict:
    return {
        "id": s.id, "solicitud_id": s.solicitud_id, "tecnico_id": s.tecnico_id,
        "tecnico_nombre": _nombre_tecnico(db, s.tecnico_id), "cliente_id": s.cliente_id,
        "monto_visita": _f(s.monto_visita), "monto_reparacion": _f(s.monto_reparacion), "monto_total": _f(s.monto_total),
        "total_mita": _f(s.total_mita), "total_tecnico": _f(s.total_tecnico),
        "comision_mita_visita": _f(s.comision_mita_visita), "comision_mita_reparacion": _f(s.comision_mita_reparacion),
        "comision_tecnico_visita": _f(s.comision_tecnico_visita), "comision_tecnico_reparacion": _f(s.comision_tecnico_reparacion),
        "comprobante_tipo": s.comprobante_tipo, "comprobante_serie": s.comprobante_serie,
        "comprobante_numero": s.comprobante_numero, "comprobante_emitido": bool(s.comprobante_emitido),
        "comprobante_pdf_url": s.comprobante_pdf_url,
        "fecha_servicio": s.fecha_servicio.isoformat() if s.fecha_servicio else None,
    }


def _liq_dict(db: Session, l: LiquidacionTecnico) -> dict:
    return {
        "id": l.id, "tecnico_id": l.tecnico_id, "tecnico_nombre": _nombre_tecnico(db, l.tecnico_id),
        "semana_inicio": l.semana_inicio.isoformat() if l.semana_inicio else None,
        "semana_fin": l.semana_fin.isoformat() if l.semana_fin else None,
        "cantidad_servicios": l.cantidad_servicios, "total_a_pagar": _f(l.total_a_pagar),
        "rxh_estado": l.rxh_estado, "rxh_numero": l.rxh_numero,
        "rxh_fecha": l.rxh_fecha.isoformat() if l.rxh_fecha else None, "rxh_pdf_url": l.rxh_pdf_url,
        "rxh_observacion": l.rxh_observacion,
        "pago_estado": l.pago_estado, "pago_referencia": l.pago_referencia, "pago_metodo": l.pago_metodo,
        "pago_fecha": l.pago_fecha.isoformat() if l.pago_fecha else None,
    }


def _calcular_comisiones(db: Session, monto_visita: float, monto_reparacion: float) -> dict:
    cm_visita = float(ConfigService.get(db, "comision_mita_visita", 15))
    ct_visita = float(ConfigService.get(db, "comision_tecnico_visita", 35))
    usar_pct = ConfigService.get(db, "usar_porcentaje_reparacion", True)
    if monto_reparacion and usar_pct:
        pct = float(ConfigService.get(db, "comision_mita_reparacion_pct", 20))
        cm_rep = round(monto_reparacion * pct / 100, 2)
    elif monto_reparacion:
        cm_rep = float(ConfigService.get(db, "monto_fijo_reparacion", 0))
    else:
        cm_rep = 0.0
    ct_rep = round(max(monto_reparacion - cm_rep, 0), 2)
    return {
        "comision_mita_visita": cm_visita, "comision_tecnico_visita": ct_visita,
        "comision_mita_reparacion": cm_rep, "comision_tecnico_reparacion": ct_rep,
        "total_mita": round(cm_visita + cm_rep, 2), "total_tecnico": round(ct_visita + ct_rep, 2),
    }


# ============================================
# Completar servicio + comprobante
# ============================================

@router.post("/api/v1/servicios/{solicitud_id}/completar")
def completar_servicio(solicitud_id: int, data: dict = Body(default={}), db: Session = Depends(get_db)):
    sol = db.query(Solicitud).get(solicitud_id)
    tecnico_id = data.get("tecnico_id") or (sol.tecnico_id if sol else None)
    monto_visita = float(data.get("monto_visita") or ConfigService.get(db, "tarifa_visita_default", 50))
    monto_reparacion = float(data.get("monto_reparacion") or 0)
    com = _calcular_comisiones(db, monto_visita, monto_reparacion)

    s = ServicioCompletado(
        solicitud_id=(solicitud_id if sol else None), tecnico_id=tecnico_id, cliente_id=data.get("cliente_id"),
        monto_visita=monto_visita, monto_reparacion=monto_reparacion,
        monto_total=round(monto_visita + monto_reparacion, 2),
        fecha_servicio=datetime.utcnow(), **com,
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    if data.get("emitir_comprobante"):
        _emitir(db, s, data.get("comprobante_tipo", "boleta"), data.get("cliente") or {})
    return {"success": True, "servicio": _servicio_dict(db, s)}


def _emitir(db: Session, s: ServicioCompletado, tipo: str, cliente: dict):
    res = facturalo_service.emitir_comprobante(
        db, tipo=tipo, cliente=cliente,
        items=[{"descripcion": "Servicio técnico MITA", "cantidad": 1, "precio": _f(s.monto_total)}],
        monto=_f(s.monto_total) or 0,
    )
    if res.get("ok"):
        s.comprobante_tipo = tipo
        s.comprobante_serie = res.get("serie")
        s.comprobante_numero = res.get("numero")
        s.comprobante_pdf_url = res.get("pdf_url")
        s.comprobante_emitido = True
        s.fecha_comprobante = datetime.utcnow()
        db.commit()
    return res


@router.post("/api/v1/servicios/{id}/emitir-comprobante")
def emitir_comprobante_endpoint(id: int, data: dict = Body(default={}), db: Session = Depends(get_db),
                                _=Depends(require_admin_gerente)):
    s = db.query(ServicioCompletado).get(id)
    if not s:
        raise HTTPException(404, "Servicio no encontrado")
    if s.comprobante_emitido:
        raise HTTPException(409, "El comprobante ya fue emitido.")
    res = _emitir(db, s, data.get("comprobante_tipo", "boleta"), data.get("cliente") or {})
    return {"success": res.get("ok"), "resultado": res, "servicio": _servicio_dict(db, s)}


# ============================================
# Admin — servicios
# ============================================

@router.get("/api/v1/admin/servicios")
def listar_servicios(tecnico_id: Optional[int] = None, con_comprobante: Optional[str] = None,
                     desde: Optional[str] = None, hasta: Optional[str] = None,
                     db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    q = db.query(ServicioCompletado)
    if tecnico_id:
        q = q.filter(ServicioCompletado.tecnico_id == tecnico_id)
    if con_comprobante in ("true", "false"):
        q = q.filter(ServicioCompletado.comprobante_emitido.is_(con_comprobante == "true"))
    if desde:
        q = q.filter(ServicioCompletado.fecha_servicio >= desde)
    if hasta:
        q = q.filter(ServicioCompletado.fecha_servicio <= hasta + " 23:59:59")
    items = q.order_by(ServicioCompletado.fecha_servicio.desc()).all()
    return {"success": True, "items": [_servicio_dict(db, s) for s in items]}


@router.get("/api/v1/admin/servicios/{id}")
def detalle_servicio(id: int, db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    s = db.query(ServicioCompletado).get(id)
    if not s:
        raise HTTPException(404, "Servicio no encontrado")
    return _servicio_dict(db, s)


# ============================================
# Liquidaciones semanales
# ============================================

@router.post("/api/v1/liquidaciones/generar-semanal")
def generar_semanal(data: dict = Body(default={}), db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    if data.get("semana_inicio"):
        try:
            ini = _lunes(datetime.strptime(data["semana_inicio"], "%Y-%m-%d").date())
        except Exception:
            raise HTTPException(400, "semana_inicio inválida (YYYY-MM-DD)")
    else:
        ini = _lunes(date.today())
    fin = ini + timedelta(days=6)

    # Servicios de la semana aún no liquidados, agrupados por técnico
    filas = (db.query(ServicioCompletado)
               .filter(ServicioCompletado.liquidacion_id.is_(None),
                       ServicioCompletado.tecnico_id.isnot(None),
                       func.date(ServicioCompletado.fecha_servicio) >= ini,
                       func.date(ServicioCompletado.fecha_servicio) <= fin)
               .all())
    por_tecnico = {}
    for s in filas:
        por_tecnico.setdefault(s.tecnico_id, []).append(s)

    creadas = 0
    for tecnico_id, servicios in por_tecnico.items():
        existente = (db.query(LiquidacionTecnico)
                       .filter(LiquidacionTecnico.tecnico_id == tecnico_id,
                               LiquidacionTecnico.semana_inicio == ini).first())
        liq = existente or LiquidacionTecnico(tecnico_id=tecnico_id, semana_inicio=ini, semana_fin=fin)
        total = sum((_f(s.total_tecnico) or 0) for s in servicios)
        liq.cantidad_servicios = (liq.cantidad_servicios or 0) + len(servicios)
        liq.total_a_pagar = float(liq.total_a_pagar or 0) + round(total, 2)
        if not existente:
            db.add(liq)
            creadas += 1
        db.flush()
        for s in servicios:
            s.liquidacion_id = liq.id
    db.commit()
    return {"success": True, "semana_inicio": ini.isoformat(), "semana_fin": fin.isoformat(),
            "liquidaciones_creadas": creadas, "tecnicos": len(por_tecnico)}


def _query_liq(db, tecnico_id, semana, rxh_estado, pago_estado):
    q = db.query(LiquidacionTecnico)
    if tecnico_id:
        q = q.filter(LiquidacionTecnico.tecnico_id == tecnico_id)
    if semana:
        q = q.filter(LiquidacionTecnico.semana_inicio == semana)
    if rxh_estado:
        q = q.filter(LiquidacionTecnico.rxh_estado == rxh_estado)
    if pago_estado:
        q = q.filter(LiquidacionTecnico.pago_estado == pago_estado)
    return q.order_by(LiquidacionTecnico.semana_inicio.desc(), LiquidacionTecnico.id.desc())


@router.get("/api/v1/admin/liquidaciones")
def listar_liquidaciones(tecnico_id: Optional[int] = None, semana: Optional[str] = None,
                         rxh_estado: Optional[str] = None, pago_estado: Optional[str] = None,
                         db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    items = _query_liq(db, tecnico_id, semana, rxh_estado, pago_estado).all()
    return {"success": True, "items": [_liq_dict(db, l) for l in items]}


def _servicios_de_liq(db: Session, l: LiquidacionTecnico):
    return [_servicio_dict(db, s) for s in
            db.query(ServicioCompletado).filter(ServicioCompletado.liquidacion_id == l.id).all()]


@router.get("/api/v1/admin/liquidaciones/{id}")
def detalle_liquidacion(id: int, db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    l = db.query(LiquidacionTecnico).get(id)
    if not l:
        raise HTTPException(404, "Liquidación no encontrada")
    p = db.query(Personal).get(l.tecnico_id) if l.tecnico_id else None
    return {"liquidacion": _liq_dict(db, l), "servicios": _servicios_de_liq(db, l),
            "tecnico": {"nombre": _nombre_tecnico(db, l.tecnico_id), "banco": getattr(p, "banco", None),
                        "numero_cuenta": getattr(p, "numero_cuenta", None), "cci": getattr(p, "cci", None),
                        "emite_rxh": getattr(p, "emite_recibo_honorarios", False)} if p else None}


@router.post("/api/v1/liquidaciones/{id}/emitir-rxh")
def emitir_rxh(id: int, db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    l = db.query(LiquidacionTecnico).get(id)
    if not l:
        raise HTTPException(404, "Liquidación no encontrada")
    # STUB: emisión automática con credenciales SOL del técnico
    l.rxh_estado = "EMITIDO_AUTO"
    l.rxh_fecha = date.today()
    l.rxh_numero = l.rxh_numero or f"E001-{l.id:05d}"
    db.commit()
    return {"success": True, "rxh_estado": l.rxh_estado, "mensaje": "RxH emitido automáticamente (simulado)."}


@router.post("/api/v1/liquidaciones/{id}/subir-rxh")
def subir_rxh(id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    l = db.query(LiquidacionTecnico).get(id)
    if not l:
        raise HTTPException(404, "Liquidación no encontrada")
    numero = (data.get("rxh_numero") or "").strip()
    if not numero:
        raise HTTPException(400, "Falta el número de RxH.")
    l.rxh_numero = numero
    l.rxh_pdf_url = data.get("rxh_pdf_url") or l.rxh_pdf_url
    l.rxh_estado = "SUBIDO_MANUAL"
    l.rxh_fecha = date.today()
    db.commit()
    return {"success": True, "rxh_estado": l.rxh_estado}


@router.post("/api/v1/liquidaciones/{id}/validar-rxh")
def validar_rxh(id: int, data: dict = Body(default={}), db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    l = db.query(LiquidacionTecnico).get(id)
    if not l:
        raise HTTPException(404, "Liquidación no encontrada")
    if data.get("observacion"):
        l.rxh_estado = "OBSERVADO"
        l.rxh_observacion = data["observacion"]
    else:
        l.rxh_estado = "VALIDADO"
    db.commit()
    return {"success": True, "rxh_estado": l.rxh_estado}


@router.post("/api/v1/liquidaciones/{id}/registrar-pago")
def registrar_pago(id: int, data: dict = Body(...), db: Session = Depends(get_db), _=Depends(require_admin_gerente)):
    l = db.query(LiquidacionTecnico).get(id)
    if not l:
        raise HTTPException(404, "Liquidación no encontrada")
    l.pago_estado = "PAGADO"
    l.pago_referencia = (data.get("pago_referencia") or "").strip() or None
    l.pago_metodo = (data.get("pago_metodo") or "transferencia").strip()
    l.pago_fecha = datetime.utcnow()
    db.commit()
    return {"success": True, "pago_estado": l.pago_estado}


# ============================================
# Técnico — mis liquidaciones
# ============================================

async def _tecnico_id(request: Request, db: Session) -> Optional[int]:
    """personal_id del técnico logueado (rol 'tecnico' o personal PROVEEDOR), o None."""
    user = await get_current_user(request, db)
    if not user:
        return None
    if (user.tipo or "").lower() == "tecnico":
        return user.personal_id
    if user.personal_id:
        p = db.query(Personal).get(user.personal_id)
        if p and (getattr(p, "tipo_relacion", "") or "").upper() == "PROVEEDOR":
            return user.personal_id
    return None


async def require_tecnico(request: Request, db: Session = Depends(get_db)) -> int:
    """Exige sesión de técnico; devuelve su personal_id. 401 (con Location) si no."""
    tid = await _tecnico_id(request, db)
    if not tid:
        raise HTTPException(status_code=401, detail="Solo técnicos", headers={"Location": "/login"})
    return tid


def _tipo_servicio(db: Session, s: ServicioCompletado) -> Optional[str]:
    """Nombre de la categoría del servicio (vía la solicitud), si está disponible."""
    from app.models.models import CategoriaServicio
    if not s.solicitud_id:
        return None
    sol = db.query(Solicitud).get(s.solicitud_id)
    cat_id = getattr(sol, "categoria_id", None) if sol else None
    cat = db.query(CategoriaServicio).get(cat_id) if cat_id else None
    return cat.nombre if cat else None


@router.get("/api/v1/tecnico/servicios")
def mis_servicios(db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    items = (db.query(ServicioCompletado)
               .filter(ServicioCompletado.tecnico_id == pid)
               .order_by(ServicioCompletado.fecha_servicio.desc()).all())
    out = []
    for s in items:
        d = _servicio_dict(db, s)
        d["tipo"] = _tipo_servicio(db, s)
        d["mi_comision"] = _f(s.total_tecnico)
        out.append(d)
    return {"success": True, "items": out}


@router.get("/api/v1/tecnico/liquidaciones")
async def mis_liquidaciones(request: Request, tecnico_id: Optional[int] = None, db: Session = Depends(get_db)):
    tid = await _tecnico_id(request, db) or tecnico_id   # sesión técnico, o ?tecnico_id en demo
    q = db.query(LiquidacionTecnico)
    if tid:
        q = q.filter(LiquidacionTecnico.tecnico_id == tid)
    items = q.order_by(LiquidacionTecnico.semana_inicio.desc()).all()
    return {"success": True, "items": [_liq_dict(db, l) for l in items]}


@router.get("/api/v1/tecnico/liquidaciones/{id}")
async def mi_liquidacion(id: int, request: Request, db: Session = Depends(get_db)):
    l = db.query(LiquidacionTecnico).get(id)
    if not l:
        raise HTTPException(404, "Liquidación no encontrada")
    tid = await _tecnico_id(request, db)
    if tid and l.tecnico_id != tid:
        raise HTTPException(403, "No es tu liquidación")
    return {"liquidacion": _liq_dict(db, l), "servicios": _servicios_de_liq(db, l)}
