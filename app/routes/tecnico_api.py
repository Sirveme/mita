"""
Dashboard técnico + asignación automática + servicios adicionales.

Técnico (require_tecnico):
  POST /api/v1/tecnico/estado-servicio            {estado}
  GET  /api/v1/tecnico/resumen
  POST /api/v1/tecnico/notificaciones/{id}/responder  {respuesta}
  GET  /api/v1/tecnico/servicios/{id}
  POST /api/v1/solicitudes/{id}/estado            {estado}
  POST /api/v1/solicitudes/{id}/diagnostico       {diagnostico}
  POST /api/v1/solicitudes/{id}/adicionales        {descripcion, monto}
  POST /api/v1/solicitudes/{id}/finalizar
Sistema / cliente:
  POST /api/v1/solicitudes/{id}/buscar-tecnico
  GET  /api/v1/solicitudes/{id}/adicionales
  POST /api/v1/adicionales/{id}/responder          {aprobado}
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.personal import Personal, TecnicoPersonal, TipoPersonal, EstadoPersonal
from app.models.solicitud_mita import Solicitud
from app.models.notificacion_tecnico import NotificacionTecnico
from app.models.servicio_adicional import ServicioAdicional
from app.models.chat_sala import ChatSala, ChatMensaje
from app.routes.comprobantes_api import require_tecnico

logger = logging.getLogger("mita.tecnico")
router = APIRouter(tags=["Dashboard técnico"])

ACTIVOS = ["ACEPTADA", "EN_CAMINO", "EN_SITIO", "EN_PROCESO"]


def _f(v):
    try: return float(v)
    except Exception: return 0.0


def _nombre(p): return f"{p.nombres} {p.apellido_paterno or ''}".strip() if p else "Técnico"


# ============================================
# Estado en servicio (toggle)
# ============================================

@router.post("/api/v1/tecnico/estado-servicio")
def set_estado_servicio(data: dict = Body(...), db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    estado = (data.get("estado") or "").upper()
    if estado not in ("EN_SERVICIO", "FUERA_SERVICIO", "OCUPADO"):
        raise HTTPException(400, "estado inválido")
    p = db.query(Personal).get(pid)
    p.estado_servicio = estado
    db.commit()
    return {"success": True, "estado_servicio": estado}


# ============================================
# Resumen del dashboard (una sola llamada)
# ============================================

@router.get("/api/v1/tecnico/resumen")
def resumen(db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    p = db.query(Personal).get(pid)
    # solicitud entrante (notificación sin responder)
    notif = (db.query(NotificacionTecnico)
             .filter(NotificacionTecnico.tecnico_id == pid, NotificacionTecnico.respuesta.is_(None))
             .order_by(NotificacionTecnico.notificado_en.desc()).first())
    entrante = None
    if notif:
        s = db.query(Solicitud).get(notif.solicitud_id)
        if s and s.estado in ("BUSCANDO_TECNICO",):
            entrante = _solicitud_card(s, notif.id)
    # "Ya tomado": notificación de este técnico cancelada hace pocos segundos
    # (otro la aceptó). Sirve para mostrar el aviso en el dashboard.
    ya_tomada_id = None
    reciente = (db.query(NotificacionTecnico)
                .filter(NotificacionTecnico.tecnico_id == pid,
                        NotificacionTecnico.respuesta == "cancelada",
                        NotificacionTecnico.respondido_en.isnot(None),
                        NotificacionTecnico.respondido_en > datetime.utcnow() - timedelta(seconds=20))
                .order_by(NotificacionTecnico.respondido_en.desc()).first())
    if reciente:
        ya_tomada_id = reciente.id
    # servicio activo
    activo = (db.query(Solicitud).filter(Solicitud.tecnico_id == pid, Solicitud.estado.in_(ACTIVOS))
              .order_by(Solicitud.id.desc()).first())
    return {
        "tecnico": {"nombre": _nombre(p), "estado_servicio": p.estado_servicio or "FUERA_SERVICIO",
                    "rating": _f(p.rating_promedio) or 5.0, "total_servicios": p.total_servicios or 0},
        "entrante": entrante,
        "ya_tomada_notif_id": ya_tomada_id,
        "servicio_activo": _solicitud_card(activo, None) if activo else None,
    }


def _solicitud_card(s: Solicitud, notif_id) -> dict:
    return {
        "id": s.id, "notif_id": notif_id, "estado": s.estado,
        "problema": s.descripcion_problema,
        "direccion": f"{s.cliente_direccion or ''}{', ' + s.cliente_distrito if s.cliente_distrito else ''}",
        "distrito": s.cliente_distrito, "telefono": s.cliente_telefono,
        "costo_visita": _f(s.costo_visita) or 50.0,
    }


# ============================================
# Aceptar / rechazar notificación
# ============================================

def _crear_chats(db: Session, solicitud_id: int, tecnico_nombre: str, tecnico_id):
    def sala(tipo, titulo):
        x = db.query(ChatSala).filter(ChatSala.solicitud_id == solicitud_id, ChatSala.tipo == tipo).first()
        if not x:
            x = ChatSala(solicitud_id=solicitud_id, tipo=tipo, titulo=titulo); db.add(x); db.flush()
        return x
    st = sala("cliente_tecnico", tecnico_nombre); sa = sala("cliente_admin", "MITA Soporte")
    db.flush()
    if db.query(ChatMensaje).filter(ChatMensaje.sala_id == st.id).count() == 0:
        db.add(ChatMensaje(sala_id=st.id, emisor_id=tecnico_id, emisor_tipo="tecnico", emisor_nombre=tecnico_nombre,
                           mensaje=f"Hola, soy {tecnico_nombre}. Voy en camino a atender tu solicitud."))
    if db.query(ChatMensaje).filter(ChatMensaje.sala_id == sa.id).count() == 0:
        db.add(ChatMensaje(sala_id=sa.id, emisor_tipo="admin", emisor_nombre="MITA Soporte",
                           mensaje="¡Hola! Soy MITA Soporte. ¿En qué podemos ayudarte?"))
    return st


def _candidatos_ids(db: Session, s: Solicitud) -> list:
    """IDs de técnicos EN_SERVICIO (con la especialidad del área), mejor rating primero."""
    q = (db.query(Personal, TecnicoPersonal)
         .join(TecnicoPersonal, TecnicoPersonal.personal_id == Personal.id)
         .filter(Personal.tipo == TipoPersonal.TECNICO, Personal.estado == EstadoPersonal.ACTIVO,
                 Personal.estado_servicio == "EN_SERVICIO"))
    cand = []
    for p, tp in q.all():
        esp = tp.especialidades or []
        if s.categoria_id and esp and s.categoria_id not in esp:
            continue
        cand.append((p.id, _f(p.rating_promedio) or 5.0))
    cand.sort(key=lambda x: x[1], reverse=True)
    return [i for i, _ in cand]


def _notificar_a_todos(db: Session, s: Solicitud, intento: int) -> int:
    """Crea una notificación PENDIENTE por cada técnico candidato que no la tenga ya.

    No hace commit ni cambia estado/notificado_en (lo hace el llamador). Devuelve
    el número de técnicos candidatos actuales (0 si no hay ninguno disponible).
    """
    ids = _candidatos_ids(db, s)
    pendientes = {n.tecnico_id for n in
                  db.query(NotificacionTecnico)
                    .filter(NotificacionTecnico.solicitud_id == s.id,
                            NotificacionTecnico.respuesta.is_(None)).all()}
    for tid in ids:
        if tid in pendientes:
            continue
        db.add(NotificacionTecnico(solicitud_id=s.id, tecnico_id=tid, intento=intento,
                                   notificado_en=datetime.utcnow()))
    return len(ids)


@router.post("/api/v1/tecnico/notificaciones/{notif_id}/responder")
def responder_notificacion(notif_id: int, data: dict = Body(...), db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    n = db.query(NotificacionTecnico).get(notif_id)
    if not n or n.tecnico_id != pid:
        raise HTTPException(404, "Notificación no encontrada")
    if n.respuesta == "cancelada" or n.respuesta == "timeout":
        # Otro técnico la tomó, o expiró la ronda: avisar sin error.
        return {"success": False, "estado": "ya_tomada",
                "mensaje": "Este servicio ya fue tomado por otro técnico."}
    if n.respuesta:
        raise HTTPException(409, "Ya respondida")
    resp = (data.get("respuesta") or "").lower()
    ahora = datetime.utcnow()
    n.respondido_en = ahora
    if n.notificado_en:
        n.tiempo_respuesta_seg = int((n.respondido_en - n.notificado_en).total_seconds())
    s = db.query(Solicitud).get(n.solicitud_id)

    if resp in ("aceptada", "acepto", "aceptar"):
        # Reclamo atómico: sólo gana quien deje BUSCANDO_TECNICO -> ACEPTADA primero.
        ganó = (db.query(Solicitud)
                .filter(Solicitud.id == s.id, Solicitud.estado == "BUSCANDO_TECNICO")
                .update({Solicitud.tecnico_id: pid, Solicitud.estado: "ACEPTADA",
                         Solicitud.fecha_aceptacion: ahora}, synchronize_session=False))
        db.commit()
        if not ganó:
            # Otro técnico ya la tomó (o ya no está en búsqueda)
            n.respuesta = "cancelada"; db.commit()
            return {"success": False, "estado": "ya_tomada",
                    "mensaje": "Este servicio ya fue tomado por otro técnico."}
        n.respuesta = "aceptada"
        p = db.query(Personal).get(pid)
        p.estado_servicio = "OCUPADO"
        # Cancelar las notificaciones pendientes de los demás técnicos
        (db.query(NotificacionTecnico)
         .filter(NotificacionTecnico.solicitud_id == s.id,
                 NotificacionTecnico.tecnico_id != pid,
                 NotificacionTecnico.respuesta.is_(None))
         .update({NotificacionTecnico.respuesta: "cancelada",
                  NotificacionTecnico.respondido_en: ahora}, synchronize_session=False))
        db.commit()
        s = db.query(Solicitud).get(s.id)
        sala = _crear_chats(db, s.id, _nombre(p), pid)
        db.commit()
        return {"success": True, "estado": "ACEPTADA", "chat_id": sala.id, "solicitud_id": s.id}

    # Rechazo (PASO): sólo marca la propia; los demás siguen con su notificación.
    n.respuesta = "rechazada"; db.commit()
    return {"success": True, "estado": "rechazada"}


# ============================================
# Servicio activo: detalle, estados, diagnóstico, finalizar
# ============================================

def _adic_dict(a): return {"id": a.id, "descripcion": a.descripcion, "monto": _f(a.monto), "estado": a.estado}

def _detalle(db: Session, s: Solicitud) -> dict:
    adic = db.query(ServicioAdicional).filter(ServicioAdicional.solicitud_id == s.id).all()
    base = _f(s.costo_visita) or 50.0
    aprob = sum(_f(a.monto) for a in adic if a.estado == "APROBADO")
    return {
        "id": s.id, "estado": s.estado, "problema": s.descripcion_problema, "diagnostico": s.diagnostico,
        "direccion": f"{s.cliente_direccion or ''}{', ' + s.cliente_distrito if s.cliente_distrito else ''}",
        "telefono": s.cliente_telefono, "base": base,
        "adicionales": [_adic_dict(a) for a in adic],
        "total": round(base + aprob, 2),
        "hay_pendientes": any(a.estado == "PENDIENTE" for a in adic),
    }


@router.get("/api/v1/tecnico/servicios/{sid}")
def detalle_servicio(sid: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = db.query(Solicitud).get(sid)
    if not s:
        raise HTTPException(404, "No encontrada")
    return _detalle(db, s)


@router.post("/api/v1/solicitudes/{sid}/estado")
def cambiar_estado(sid: int, data: dict = Body(...), db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = db.query(Solicitud).get(sid)
    if not s:
        raise HTTPException(404, "No encontrada")
    estado = (data.get("estado") or "").upper()
    if estado not in ("EN_CAMINO", "EN_SITIO", "EN_PROCESO", "FINALIZADO"):
        raise HTTPException(400, "estado inválido")
    s.estado = estado
    if estado == "EN_SITIO": s.fecha_llegada = datetime.utcnow()
    db.commit()
    return {"success": True, "estado": s.estado}


@router.post("/api/v1/solicitudes/{sid}/diagnostico")
def guardar_diagnostico(sid: int, data: dict = Body(...), db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = db.query(Solicitud).get(sid)
    if not s: raise HTTPException(404, "No encontrada")
    s.diagnostico = (data.get("diagnostico") or "").strip()
    db.commit()
    return {"success": True}


@router.post("/api/v1/solicitudes/{sid}/finalizar")
def finalizar(sid: int, db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = db.query(Solicitud).get(sid)
    if not s: raise HTTPException(404, "No encontrada")
    det = _detalle(db, s)
    if det["hay_pendientes"]:
        raise HTTPException(409, "Hay adicionales pendientes de aprobación del cliente.")
    s.estado = "FINALIZADO"; s.fecha_fin_servicio = datetime.utcnow(); s.costo_total = det["total"]
    p = db.query(Personal).get(pid)
    if p:
        p.estado_servicio = "EN_SERVICIO"
        p.total_servicios = (p.total_servicios or 0) + 1
    db.commit()
    # TODO: capturar el pago pre-autorizado por det["total"] (pagos_api.capturar) — stub por ahora
    logger.info("Servicio %s finalizado. Total S/%.2f. Captura de pago: pendiente (stub).", sid, det["total"])
    return {"success": True, "estado": "FINALIZADO", "total": det["total"]}


# ============================================
# Servicios adicionales
# ============================================

@router.post("/api/v1/solicitudes/{sid}/adicionales")
def crear_adicional(sid: int, data: dict = Body(...), db: Session = Depends(get_db), pid: int = Depends(require_tecnico)):
    s = db.query(Solicitud).get(sid)
    if not s: raise HTTPException(404, "No encontrada")
    desc = (data.get("descripcion") or "").strip(); monto = _f(data.get("monto"))
    if not desc or monto <= 0:
        raise HTTPException(400, "Descripción y monto (>0) son obligatorios.")
    a = ServicioAdicional(solicitud_id=sid, tecnico_id=pid, descripcion=desc, monto=monto)
    db.add(a); db.commit(); db.refresh(a)
    # Aviso al cliente por el chat de soporte/técnico
    sala = db.query(ChatSala).filter(ChatSala.solicitud_id == sid, ChatSala.tipo == "cliente_tecnico").first()
    if sala:
        db.add(ChatMensaje(sala_id=sala.id, emisor_id=pid, emisor_tipo="tecnico", emisor_nombre=_nombre(db.query(Personal).get(pid)),
                           mensaje=f"Propongo un servicio adicional: {desc} por S/ {monto:.2f}. Apruébalo desde tu app."))
        db.commit()
    return {"success": True, "adicional": _adic_dict(a)}


@router.get("/api/v1/solicitudes/{sid}/adicionales")
def listar_adicionales(sid: int, db: Session = Depends(get_db)):
    adic = db.query(ServicioAdicional).filter(ServicioAdicional.solicitud_id == sid).order_by(ServicioAdicional.id).all()
    s = db.query(Solicitud).get(sid)
    base = _f(s.costo_visita) if s else 50.0
    return {"base": base or 50.0, "adicionales": [_adic_dict(a) for a in adic],
            "pendientes": [_adic_dict(a) for a in adic if a.estado == "PENDIENTE"],
            "total": round((base or 50.0) + sum(_f(a.monto) for a in adic if a.estado == "APROBADO"), 2)}


@router.post("/api/v1/adicionales/{aid}/responder")
def responder_adicional(aid: int, data: dict = Body(...), db: Session = Depends(get_db)):
    a = db.query(ServicioAdicional).get(aid)
    if not a: raise HTTPException(404, "No encontrado")
    a.estado = "APROBADO" if data.get("aprobado") else "RECHAZADO"
    a.respondido_en = datetime.utcnow()
    db.commit()
    return {"success": True, "estado": a.estado}


# ============================================
# Buscar técnico (asignación automática) — llamado tras el pago
# ============================================

@router.post("/api/v1/solicitudes/{sid}/buscar-tecnico")
def buscar_tecnico(sid: int, db: Session = Depends(get_db)):
    s = db.query(Solicitud).get(sid)
    if not s: raise HTTPException(404, "No encontrada")
    # Se notifica a TODOS los técnicos EN_SERVICIO con la especialidad, a la vez.
    s.intento_notificacion = 1
    s.tecnico_notificado_id = None
    s.cola_tecnicos = None
    s.notificado_en = datetime.utcnow()
    n = _notificar_a_todos(db, s, intento=1)
    if n == 0:
        s.estado = "SIN_TECNICO"; db.commit()
        return {"success": True, "tecnicos": 0, "mensaje": "No hay técnicos EN SERVICIO ahora."}
    s.estado = "BUSCANDO_TECNICO"
    db.commit()
    logger.info("Solicitud %s: notificados %s técnicos (intento 1). Notificación interna (no WhatsApp).", sid, n)
    return {"success": True, "tecnicos": n, "intento": 1}
