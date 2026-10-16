"""
API de ofertas de servicio a técnicos (etapa 4, zMita-37).
El técnico ve la oferta, acepta (reclamo atómico) o dice "No puedo". La torre reenvía/ofrece/cancela.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.comprobantes_api import require_tecnico
from app.services import ofertas

logger = logging.getLogger("mita.ofertas")
router = APIRouter(tags=["Ofertas"])
ACTIVOS = ("ACEPTADA", "EN_CAMINO", "EN_SITIO", "EN_PROCESO", "FINALIZADO")


def _primer_nombre(nombre):
    return (nombre or "").strip().split(" ")[0] if nombre else ""


def _especialidad(db, s):
    try:
        from app.models.models import CategoriaServicio
        c = db.query(CategoriaServicio).get(s.categoria_id) if s.categoria_id else None
        return c.nombre if c else ""
    except Exception:
        return ""


def _eta_dict(db, s, tecnico_id):
    try:
        from app.models.personal import TecnicoPersonal
        from app.services.rutas import eta
        tp = db.query(TecnicoPersonal).filter(TecnicoPersonal.personal_id == tecnico_id).first()
        if tp and tp.ultima_ubicacion_lat and s.cliente_lat:
            return eta(float(tp.ultima_ubicacion_lat), float(tp.ultima_ubicacion_lng),
                       float(s.cliente_lat), float(s.cliente_lng))
    except Exception:
        pass
    return None


@router.post("/api/v1/tecnico/ubicacion-actual")
async def ubicacion_actual(data: dict = Body(...), db: Session = Depends(get_db),
                           pid: int = Depends(require_tecnico)):
    """Guarda la última ubicación del técnico (no es seguimiento continuo)."""
    try:
        lat = float(data.get("lat")); lng = float(data.get("lng"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="lat/lng inválidos")
    from app.models.personal import TecnicoPersonal
    tp = db.query(TecnicoPersonal).filter(TecnicoPersonal.personal_id == pid).first()
    if not tp:
        tp = TecnicoPersonal(personal_id=pid); db.add(tp)
    tp.ultima_ubicacion_lat = lat
    tp.ultima_ubicacion_lng = lng
    tp.ultima_ubicacion_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/api/v1/tecnico/ofertas/{solicitud_id}")
async def ver_oferta(solicitud_id: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    """Oferta del servicio. ANTES de aceptar NO incluye dirección exacta, nombre ni teléfono."""
    from app.models.solicitud_mita import Solicitud
    s = db.query(Solicitud).get(solicitud_id)
    if not s:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    aceptada_por_mi = (s.tecnico_id == pid and s.estado in ACTIVOS)
    if s.tecnico_id and s.tecnico_id != pid:
        return {"estado": "tomada_por_otro", "mensaje": "Ya fue tomado por otro técnico."}
    ofertas.marcar_vista(db, solicitud_id, pid)
    mostrar_dir = ofertas.cfg_bool(db, "mostrar_direccion_antes_de_aceptar", False)

    cuando = "ahora"
    if getattr(s, "fecha_programada", None):
        try:
            cuando = s.fecha_programada.strftime("%d/%m %H:%M")
        except Exception:
            pass
    metodo = "Ya pagado" if getattr(s, "pagado", 0) else (s.metodo_pago or "Efectivo al técnico")
    out = {
        "solicitud_id": s.id, "estado": s.estado, "aceptada_por_mi": aceptada_por_mi,
        "especialidad": _especialidad(db, s), "distrito": s.cliente_distrito,
        "problema": s.descripcion_problema, "cuando": cuando, "metodo_pago": metodo,
        "monto_visita": float(getattr(s, "costo_visita", None) or 50.0),
        "eta": _eta_dict(db, s, pid),
    }
    if aceptada_por_mi or mostrar_dir:
        lat, lng = s.cliente_lat, s.cliente_lng
        out["direccion"] = s.cliente_direccion or s.direccion_completa
        out["referencia"] = s.cliente_referencia
        out["cliente_nombre"] = _primer_nombre(s.cliente_nombre)
        out["lat"], out["lng"] = lat, lng
        if lat and lng:
            out["maps_url"] = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
            out["waze_url"] = f"https://waze.com/ul?ll={lat},{lng}&navigate=yes"
    return out


@router.post("/api/v1/tecnico/ofertas/{solicitud_id}/aceptar")
async def aceptar_oferta(solicitud_id: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    r = ofertas.aceptar(db, solicitud_id, pid)
    if r["resultado"] == "aceptada":
        return {"ok": True, "estado": "aceptada", "mensaje": "Aceptaste el servicio.", **r}
    if r["resultado"] == "idempotente":
        return {"ok": True, "estado": "aceptada", "mensaje": "Ya tienes este servicio.", **r}
    return {"ok": False, "estado": "tomada_por_otro", "mensaje": "Ya fue tomado por otro técnico.", **r}


@router.post("/api/v1/tecnico/ofertas/{solicitud_id}/no-puedo")
async def no_puedo_oferta(solicitud_id: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    return ofertas.no_puedo(db, solicitud_id, pid)


# -------------------- Difusión por efectivo (Parte 0.3) --------------------
@router.post("/api/v1/pagos/efectivo")
async def pago_efectivo(data: dict = Body(...), db: Session = Depends(get_db)):
    """El cliente paga en efectivo al técnico: se difunde directo (sin pasar por /pagar)."""
    from app.models.solicitud_mita import Solicitud
    sid = data.get("solicitud_id")
    s = db.query(Solicitud).get(int(sid)) if sid else None
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    s.metodo_pago = "efectivo"
    db.commit()
    n = ofertas.difundir(db, s)
    return {"ok": True, "metodo": "efectivo", "tecnicos": n, "estado": s.estado}


# -------------------- Torre de control (Partes D/E) --------------------
async def _es_admin(request: Request, db: Session) -> bool:
    try:
        from app.routes.login_mita import get_current_user
        u = await get_current_user(request, db)
        return (getattr(u, "tipo", "") or "").lower() in ("admin", "gerente", "secretaria")
    except Exception:
        return False


@router.get("/api/v1/admin/buscando")
async def admin_buscando(request: Request, db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.models.solicitud_mita import Solicitud
    from app.models.oferta_servicio import OfertaServicio
    sols = (db.query(Solicitud).filter(Solicitud.estado.in_(["BUSCANDO_TECNICO", "SIN_TECNICO"]))
            .order_by(Solicitud.id.desc()).limit(50).all())
    out = []
    for s in sols:
        ofs = db.query(OfertaServicio).filter(OfertaServicio.solicitud_id == s.id).all()
        seg = (datetime.utcnow() - s.notificado_en).total_seconds() if s.notificado_en else None
        out.append({
            "solicitud_id": s.id, "estado": s.estado, "especialidad": _especialidad(db, s),
            "distrito": s.cliente_distrito, "segundos_buscando": int(seg) if seg else None,
            "enviadas": len(ofs), "vistas": sum(1 for o in ofs if o.vista_en),
            "respuestas": {r: sum(1 for o in ofs if o.respuesta == r)
                           for r in ("aceptada", "no_puedo", "tomada_por_otro", "vencida")},
            "ofertas": [{"tecnico_id": o.tecnico_id, "vista": bool(o.vista_en), "respuesta": o.respuesta,
                         "respondida_en": o.respondida_en.isoformat() if o.respondida_en else None} for o in ofs],
        })
    return out


@router.get("/api/v1/admin/ultimo-chequeo")
async def ultimo_chequeo(request: Request, db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    try:
        from app.tasks.tiempos import ultimo_chequeo_hace_seg
        return {"hace_seg": ultimo_chequeo_hace_seg()}
    except Exception:
        return {"hace_seg": None}


@router.post("/api/v1/admin/buscando/reenviar")
async def admin_reenviar(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.models.solicitud_mita import Solicitud
    s = db.query(Solicitud).get(int(data.get("solicitud_id") or 0))
    if not s:
        raise HTTPException(status_code=404, detail="No existe")
    n = ofertas.difundir(db, s, intento=(s.intento_notificacion or 1) + 1)
    return {"ok": True, "tecnicos": n}


@router.post("/api/v1/admin/buscando/ofrecer")
async def admin_ofrecer(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """Ofrece a un técnico concreto: le llega la oferta normal, que él decide si acepta."""
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.models.solicitud_mita import Solicitud
    from app.models.oferta_servicio import OfertaServicio
    s = db.query(Solicitud).get(int(data.get("solicitud_id") or 0))
    tid = int(data.get("tecnico_id") or 0)
    if not s or not tid:
        raise HTTPException(status_code=422, detail="Faltan datos")
    if s.estado not in ("BUSCANDO_TECNICO", "SIN_TECNICO"):
        raise HTTPException(status_code=409, detail="La solicitud ya no está buscando técnico")
    s.estado = "BUSCANDO_TECNICO"
    if not db.query(OfertaServicio).filter(OfertaServicio.solicitud_id == s.id,
                                           OfertaServicio.tecnico_id == tid,
                                           OfertaServicio.respuesta.is_(None)).first():
        db.add(OfertaServicio(solicitud_id=s.id, tecnico_id=tid))
    db.commit()
    try:
        from app.services import push as _push
        _push.avisar_nuevo_servicio(db, s, tecnico_personal_ids=[tid],
                                    especialidad=_especialidad(db, s), distrito=s.cliente_distrito or "")
    except Exception:
        logger.exception("push ofrecer")
    return {"ok": True, "tecnico_id": tid}


@router.post("/api/v1/admin/buscando/cancelar")
async def admin_cancelar(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    """Cancela la solicitud (solo estado + motivo; la devolución del dinero es manual)."""
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.models.solicitud_mita import Solicitud
    s = db.query(Solicitud).get(int(data.get("solicitud_id") or 0))
    if not s:
        raise HTTPException(status_code=404, detail="No existe")
    s.estado = "CANCELADA"
    s.cancelado = True
    s.cancelado_at = datetime.utcnow()
    s.cancelado_por = "admin"
    s.motivo_cancelacion = (data.get("motivo") or "").strip()[:300]
    db.commit()
    logger.warning("[torre] solicitud %s CANCELADA por admin. motivo=%r. Devolución: manual.",
                   s.id, s.motivo_cancelacion)
    return {"ok": True, "estado": "CANCELADA"}
