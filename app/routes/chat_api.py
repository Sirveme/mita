"""
Flujo post-pago: técnicos disponibles, asignación y chats del servicio.

  GET  /api/v1/tecnicos-disponibles?categoria_id=..
  POST /api/v1/solicitudes/{id}/asignar-tecnico   {tecnico_id?|auto, tecnico_nombre?}
  GET  /api/v1/solicitudes/{id}/chats
  GET  /api/v1/chats/{sala_id}/mensajes
  POST /api/v1/chats/{sala_id}/mensajes           {mensaje, emisor_tipo?}
  GET  /api/v1/chats/{sala_id}/mensajes/nuevos?desde=<iso>
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.personal import Personal, TecnicoPersonal, TipoPersonal, EstadoPersonal
from app.models.solicitud_mita import Solicitud
from app.models.calificacion import Calificacion
from app.models.chat_sala import ChatSala, ChatMensaje

logger = logging.getLogger("mita.chat")
router = APIRouter(tags=["Chat servicio"])

DEMO_TECNICOS = [
    {"id": None, "nombre": "Carlos López",  "rating": 4.8, "total_servicios": 127, "especialidad": "Técnico", "tiempo_estimado": "15 min", "foto_url": None},
    {"id": None, "nombre": "Juan Pérez",    "rating": 4.6, "total_servicios": 89,  "especialidad": "Técnico", "tiempo_estimado": "25 min", "foto_url": None},
    {"id": None, "nombre": "Miguel Sánchez","rating": 4.9, "total_servicios": 203, "especialidad": "Técnico", "tiempo_estimado": "30 min", "foto_url": None},
]


def _tecnicos_para(db: Session, categoria_id: Optional[int]) -> list:
    """Técnicos activos (opcionalmente de la especialidad) con rating y total. Demo si no hay."""
    ocupados = {r[0] for r in db.query(Solicitud.tecnico_id)
                .filter(Solicitud.tecnico_id.isnot(None),
                        Solicitud.estado.in_(["ASIGNADA", "EN_CAMINO", "EN_PROCESO"])).all()}
    q = (db.query(Personal, TecnicoPersonal)
           .join(TecnicoPersonal, TecnicoPersonal.personal_id == Personal.id)
           .filter(Personal.tipo == TipoPersonal.TECNICO, Personal.estado == EstadoPersonal.ACTIVO))
    out = []
    for p, tp in q.all():
        if p.id in ocupados:
            continue
        esp = tp.especialidades or []
        if categoria_id and esp and categoria_id not in esp:
            continue
        rating = db.query(func.avg(Calificacion.estrellas)).filter(Calificacion.tecnico_id == p.id).scalar()
        rating = round(float(rating), 1) if rating else (float(tp.calificacion_promedio) if tp.calificacion_promedio else 5.0)
        out.append({
            "id": p.id, "nombre": f"{p.nombres} {p.apellido_paterno or ''}".strip(),
            "rating": rating, "total_servicios": tp.total_servicios or 0,
            "especialidad": "Técnico", "tiempo_estimado": "~20 min", "foto_url": p.foto_url,
        })
    out.sort(key=lambda t: (t["rating"], t["total_servicios"]), reverse=True)
    return out[:5] if out else list(DEMO_TECNICOS)


@router.get("/api/v1/tecnicos-disponibles")
def tecnicos_disponibles(categoria_id: Optional[int] = None, area_id: Optional[int] = None,
                         db: Session = Depends(get_db)):
    return {"tecnicos": _tecnicos_para(db, categoria_id)}


@router.post("/api/v1/solicitudes/{solicitud_id}/asignar-tecnico")
def asignar_tecnico(solicitud_id: int, data: dict = Body(default={}), db: Session = Depends(get_db)):
    sol = db.query(Solicitud).get(solicitud_id)
    if not sol:
        raise HTTPException(404, "Solicitud no encontrada")

    tecnico_id = data.get("tecnico_id")
    tecnico_nombre = (data.get("tecnico_nombre") or "").strip()
    rating = data.get("rating"); total = data.get("total_servicios")

    if data.get("auto") and not tecnico_id:
        # MITA asigna: el mejor disponible
        mejores = _tecnicos_para(db, sol.categoria_id)
        if mejores:
            t = mejores[0]; tecnico_id = t["id"]; tecnico_nombre = t["nombre"]; rating = t["rating"]; total = t["total_servicios"]

    persona = db.query(Personal).get(tecnico_id) if tecnico_id else None
    if persona:
        tecnico_nombre = f"{persona.nombres} {persona.apellido_paterno or ''}".strip()
        sol.tecnico_id = persona.id
    tecnico_nombre = tecnico_nombre or "Técnico MITA"
    sol.estado = "ASIGNADA"
    sol.fecha_aceptacion = datetime.utcnow()
    db.commit()

    # Crear salas (idempotente por solicitud+tipo)
    def _sala(tipo, titulo):
        s = db.query(ChatSala).filter(ChatSala.solicitud_id == solicitud_id, ChatSala.tipo == tipo).first()
        if not s:
            s = ChatSala(solicitud_id=solicitud_id, tipo=tipo, titulo=titulo)
            db.add(s); db.flush()
        return s

    sala_tec = _sala("cliente_tecnico", tecnico_nombre)
    sala_adm = _sala("cliente_admin", "MITA Soporte")
    db.commit()

    # Mensajes automáticos (solo si la sala está vacía)
    def _auto(sala, tipo, nombre, texto, emisor_id=None):
        if db.query(ChatMensaje).filter(ChatMensaje.sala_id == sala.id).count() == 0:
            db.add(ChatMensaje(sala_id=sala.id, emisor_id=emisor_id, emisor_tipo=tipo,
                               emisor_nombre=nombre, mensaje=texto))

    _auto(sala_tec, "tecnico", tecnico_nombre,
          f"Hola, soy {tecnico_nombre}. Voy en camino a atender tu solicitud.",
          emisor_id=(persona.id if persona else None))
    _auto(sala_adm, "admin", "MITA Soporte",
          "¡Hola! Soy MITA Soporte. ¿En qué podemos ayudarte con tu servicio?")
    db.commit()

    logger.info("Solicitud %s asignada a %s (id=%s). Notificación al técnico: pendiente (stub).",
                solicitud_id, tecnico_nombre, tecnico_id)
    return {
        "success": True,
        "tecnico": {"id": tecnico_id, "nombre": tecnico_nombre, "rating": rating, "total_servicios": total,
                    "foto_url": (persona.foto_url if persona else None)},
        "salas": [{"id": sala_tec.id, "tipo": sala_tec.tipo}, {"id": sala_adm.id, "tipo": sala_adm.tipo}],
        "chat_principal_id": sala_tec.id,
    }


def _sala_dict(db: Session, s: ChatSala) -> dict:
    ultimo = (db.query(ChatMensaje).filter(ChatMensaje.sala_id == s.id)
              .order_by(ChatMensaje.creado_en.desc()).first())
    iconos = {"cliente_tecnico": "fa-user-gear", "cliente_admin": "fa-headset", "admin_tecnico": "fa-people-arrows"}
    return {
        "id": s.id, "tipo": s.tipo, "titulo": s.titulo or s.tipo, "icono": iconos.get(s.tipo, "fa-comments"),
        "ultimo_mensaje": ultimo.mensaje if ultimo else None,
        "ultimo_at": ultimo.creado_en.isoformat() if ultimo and ultimo.creado_en else None,
    }


@router.get("/api/v1/solicitudes/{solicitud_id}/chats")
def chats_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    sol = db.query(Solicitud).get(solicitud_id)
    salas = (db.query(ChatSala).filter(ChatSala.solicitud_id == solicitud_id)
             .order_by(ChatSala.id).all())
    return {
        "solicitud": {"id": solicitud_id, "estado": sol.estado if sol else None,
                      "problema": sol.descripcion_problema if sol else None,
                      "direccion": (f"{sol.cliente_direccion or ''}{', ' + sol.cliente_distrito if sol and sol.cliente_distrito else ''}" if sol else None)},
        "salas": [_sala_dict(db, s) for s in salas],
    }


def _msg_dict(m: ChatMensaje) -> dict:
    return {"id": m.id, "emisor_tipo": m.emisor_tipo, "emisor_nombre": m.emisor_nombre,
            "mensaje": m.mensaje, "leido": bool(m.leido),
            "creado_en": m.creado_en.isoformat() if m.creado_en else None}


@router.get("/api/v1/chats/{sala_id}/mensajes")
def mensajes(sala_id: int, db: Session = Depends(get_db)):
    sala = db.query(ChatSala).get(sala_id)
    if not sala:
        raise HTTPException(404, "Sala no encontrada")
    ms = db.query(ChatMensaje).filter(ChatMensaje.sala_id == sala_id).order_by(ChatMensaje.creado_en).all()
    return {"sala": _sala_dict(db, sala), "mensajes": [_msg_dict(m) for m in ms]}


@router.post("/api/v1/chats/{sala_id}/mensajes")
def enviar_mensaje(sala_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    sala = db.query(ChatSala).get(sala_id)
    if not sala:
        raise HTTPException(404, "Sala no encontrada")
    texto = (data.get("mensaje") or "").strip()
    if not texto:
        raise HTTPException(400, "Mensaje vacío")
    tipo = data.get("emisor_tipo") or "cliente"
    m = ChatMensaje(sala_id=sala_id, emisor_tipo=tipo, emisor_nombre=data.get("emisor_nombre"),
                    emisor_id=data.get("emisor_id"), mensaje=texto)
    db.add(m); db.commit(); db.refresh(m)
    return {"success": True, "mensaje": _msg_dict(m)}


@router.get("/api/v1/chats/{sala_id}/mensajes/nuevos")
def mensajes_nuevos(sala_id: int, desde: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ChatMensaje).filter(ChatMensaje.sala_id == sala_id)
    if desde:
        try:
            q = q.filter(ChatMensaje.creado_en > datetime.fromisoformat(desde))
        except Exception:
            pass
    ms = q.order_by(ChatMensaje.creado_en).all()
    return {"mensajes": [_msg_dict(m) for m in ms]}
