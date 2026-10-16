"""
API del servicio en vivo (zMita-38): en camino/ETA (A), chat de 3 (B), presupuesto (C).
"""
import json
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.comprobantes_api import require_tecnico
from app.services import servicio

logger = logging.getLogger("mita.servicio")
router = APIRouter(tags=["Servicio en vivo"])
CERRADOS = ("FINALIZADO", "CANCELADA", "CERRADO")


def _sol(db, sid):
    from app.models.solicitud_mita import Solicitud
    s = db.query(Solicitud).get(int(sid))
    if not s:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return s


def _es_mi_servicio(s, pid):
    if s.tecnico_id != pid:
        raise HTTPException(status_code=403, detail="Este servicio no es tuyo")


async def _usuario(request, db):
    try:
        from app.routes.login_mita import get_current_user
        return await get_current_user(request, db)
    except Exception:
        return None


# ========================= Parte A — En camino / ETA =========================
@router.post("/api/v1/tecnico/servicios/{sid}/voy-en-camino")
async def voy_en_camino(sid: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = _sol(db, sid); _es_mi_servicio(s, pid)
    return servicio.voy_en_camino(db, s)


@router.post("/api/v1/tecnico/servicios/{sid}/ubicacion")
async def ubicacion(sid: int, data: dict = Body(...), db: Session = Depends(get_db),
                    pid: int = Depends(require_tecnico)):
    s = _sol(db, sid); _es_mi_servicio(s, pid)
    try:
        lat = float(data.get("lat")); lng = float(data.get("lng"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="lat/lng inválidos")
    return servicio.registrar_ubicacion(db, s, pid, lat, lng, data.get("precision_m"))


@router.post("/api/v1/tecnico/servicios/{sid}/llegue")
async def llegue(sid: int, data: dict = Body(default={}), db: Session = Depends(get_db),
                 pid: int = Depends(require_tecnico)):
    s = _sol(db, sid); _es_mi_servicio(s, pid)
    return servicio.llegue(db, s, lat=(data or {}).get("lat"), lng=(data or {}).get("lng"),
                           confirmar=bool((data or {}).get("confirmar")))


@router.post("/api/v1/tecnico/servicios/{sid}/cliente-no-esta")
async def cliente_no_esta(sid: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = _sol(db, sid); _es_mi_servicio(s, pid)
    return servicio.cliente_no_esta(db, s)


@router.get("/api/v1/servicios/{sid}/seguimiento")
async def seguimiento(sid: int, db: Session = Depends(get_db)):
    """Datos para la cabecera del cliente: técnico, ETA y última ubicación."""
    s = _sol(db, sid)
    from app.models.personal import Personal, TecnicoPersonal
    from app.models.servicio_vivo import UbicacionServicio
    p = db.query(Personal).get(s.tecnico_id) if s.tecnico_id else None
    tp = db.query(TecnicoPersonal).filter(TecnicoPersonal.personal_id == s.tecnico_id).first() if s.tecnico_id else None
    ult = (db.query(UbicacionServicio).filter(UbicacionServicio.solicitud_id == s.id)
           .order_by(UbicacionServicio.id.desc()).first())
    from datetime import datetime
    ubi = None
    if ult:
        ubi = {"lat": float(ult.lat), "lng": float(ult.lng),
               "hace_seg": int((datetime.utcnow() - ult.registrada_en).total_seconds())}
    elif tp and tp.ultima_ubicacion_lat:
        ubi = {"lat": float(tp.ultima_ubicacion_lat), "lng": float(tp.ultima_ubicacion_lng),
               "hace_seg": int((datetime.utcnow() - tp.ultima_ubicacion_at).total_seconds()) if tp.ultima_ubicacion_at else None}
    esp = ""
    try:
        from app.models.models import CategoriaServicio
        c = db.query(CategoriaServicio).get(s.categoria_id) if s.categoria_id else None
        esp = c.nombre if c else ""
    except Exception:
        pass
    nombre = (f"{p.nombres} {p.apellido_paterno}".strip() if p else "Tu técnico")
    try:
        from app.services.config_service import ConfigService
        pasarela = str(ConfigService.get(db, "pasarela_activa", "false")).lower() in ("true", "1", "si", "sí")
    except Exception:
        pasarela = False
    return {"estado": s.estado, "tecnico": nombre.split(" ")[0] if nombre else "",
            "tecnico_nombre": nombre, "foto": getattr(p, "foto_url", None) if p else None,
            "especialidad": esp, "eta_min": s.eta_actual_min, "pasarela_activa": pasarela,
            "monto_por_cobrar": s.monto_por_cobrar,
            "cliente": {"lat": s.cliente_lat, "lng": s.cliente_lng}, "tecnico_ubicacion": ubi}


# ========================= Parte B — Chat de 3 =========================
async def _acceso_chat(request, db, s, rol):
    """Devuelve (rol_efectivo, actor_id) o lanza 403. rol: cliente/tecnico/mita."""
    if rol == "tecnico":
        pid = await require_tecnico(request, db)
        if s.tecnico_id != pid:
            raise HTTPException(status_code=403, detail="No participas en este servicio")
        return "tecnico", pid
    if rol == "mita":
        u = await _usuario(request, db)
        if not u or (getattr(u, "tipo", "") or "").lower() not in ("admin", "gerente", "secretaria"):
            raise HTTPException(status_code=403, detail="Solo administración")
        return "mita", getattr(u, "id", None)
    # cliente
    u = await _usuario(request, db)
    actor = getattr(u, "cliente_id", None) or getattr(u, "id", None) if u else None
    if servicio.rol_de(db, s, "cliente", actor) is None:
        raise HTTPException(status_code=403, detail="No participas en este servicio")
    return "cliente", actor


@router.get("/api/v1/servicios/{sid}/chat")
async def chat_listar(sid: int, rol: str = "cliente", desde: int = 0, request: Request = None,
                      db: Session = Depends(get_db)):
    s = _sol(db, sid)
    rol_ef, actor = await _acceso_chat(request, db, s, rol)
    servicio.marcar_viendo(sid, rol_ef)
    msgs = servicio.listar_mensajes(db, sid, desde_id=desde)
    return {"solo_lectura": s.estado in CERRADOS,
            "mensajes": [{"id": m.id, "autor_rol": m.autor_rol, "tipo": m.tipo,
                          "contenido": m.contenido, "oculto_dato": bool(m.oculto_dato),
                          "creado_en": m.creado_en.isoformat() if m.creado_en else None} for m in msgs]}


@router.post("/api/v1/servicios/{sid}/chat")
async def chat_enviar(sid: int, data: dict = Body(...), rol: str = "cliente", request: Request = None,
                      db: Session = Depends(get_db)):
    s = _sol(db, sid)
    if s.estado in CERRADOS:
        raise HTTPException(status_code=409, detail="El servicio está cerrado (chat de solo lectura)")
    from app.services import ratelimit
    ratelimit.exigir(request, "chat", 30, 60, extra=str(sid))   # 30 mensajes/min por IP y solicitud
    rol_ef, actor = await _acceso_chat(request, db, s, rol)
    tipo = (data.get("tipo") or "texto")
    contenido = data.get("contenido") or ""
    if tipo == "texto" and not str(contenido).strip():
        raise HTTPException(status_code=422, detail="Mensaje vacío")
    nombre = {"cliente": "el cliente", "tecnico": "tu técnico", "mita": "MITA"}.get(rol_ef, "Alguien")
    m, oculto = servicio.enviar_mensaje(db, s, rol_ef, actor, tipo, contenido, nombre_autor=nombre)
    return {"ok": True, "id": m.id, "oculto_dato": oculto,
            "aviso": ("Por tu seguridad ocultamos ese dato; usa el chat de MITA." if oculto else None)}


# ========================= Parte C — Presupuesto =========================
@router.post("/api/v1/tecnico/servicios/{sid}/presupuesto")
async def crear_presupuesto(sid: int, data: dict = Body(...), db: Session = Depends(get_db),
                            pid: int = Depends(require_tecnico)):
    s = _sol(db, sid); _es_mi_servicio(s, pid)
    if s.estado not in ("EN_SITIO", "EN_PROCESO"):
        raise HTTPException(status_code=409, detail="Primero marca que llegaste (EN_SITIO)")
    if not (data.get("diagnostico") or "").strip():
        raise HTTPException(status_code=422, detail="El diagnóstico es obligatorio")
    if data.get("requiere_reparacion") and not data.get("monto"):
        raise HTTPException(status_code=422, detail="Falta el monto de la reparación")
    pr = servicio.crear_presupuesto(db, s, data)
    return {"ok": True, "presupuesto_id": pr.id, "version": pr.version, "estado": s.estado}


@router.post("/api/v1/servicios/presupuestos/{pid}/decision")
async def decidir(pid: int, data: dict = Body(...), request: Request = None, db: Session = Depends(get_db)):
    from app.models.servicio_vivo import Presupuesto
    pr = db.query(Presupuesto).get(pid)
    if not pr:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    s = _sol(db, pr.solicitud_id)
    _rol, actor = await _acceso_chat(request, db, s, "cliente")   # solo el cliente decide
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent", "")[:300] if request else None
    r = servicio.decidir_presupuesto(db, pr, bool(data.get("aceptar")),
                                     decidido_por=str(actor or "cliente"), ip=ip, ua=ua)
    if not r["ok"]:
        raise HTTPException(status_code=409, detail="Ese presupuesto ya no está vigente")
    return r


# ========================= Torre =========================
async def _es_admin(request, db):
    u = await _usuario(request, db)
    return bool(u and (getattr(u, "tipo", "") or "").lower() in ("admin", "gerente", "secretaria"))


@router.get("/api/v1/admin/en-curso")
async def admin_en_curso(request: Request, db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    return servicio.alertas_en_curso(db)


@router.get("/api/v1/admin/presupuestos")
async def admin_presupuestos(request: Request, db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.models.servicio_vivo import Presupuesto
    from app.services.config_service import ConfigService
    umbral = float(ConfigService.get(db, "monto_revision_torre", 500) or 500)
    rows = db.query(Presupuesto).order_by(Presupuesto.id.desc()).limit(100).all()
    return {"umbral": umbral, "presupuestos": [
        {"id": p.id, "solicitud_id": p.solicitud_id, "version": p.version, "estado": p.estado,
         "monto": float(p.monto) if p.monto is not None else None,
         "diagnostico": (p.diagnostico or "")[:120], "requiere_reparacion": bool(p.requiere_reparacion),
         "revisar": bool(p.monto and float(p.monto) > umbral), "reemplazado": p.estado == "reemplazado",
         "decidido_en": p.decidido_en.isoformat() if p.decidido_en else None} for p in rows]}
