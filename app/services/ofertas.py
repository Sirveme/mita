"""
Oferta y aceptación de servicios por técnicos (etapa 4, zMita-37).

Lenguaje hacia el técnico: "Nuevo servicio disponible", "Aceptar servicio",
"Aceptaste el servicio", "Ya fue tomado por otro técnico". Nunca "asignado/turno/empleado".
"""
import logging
from datetime import datetime

from sqlalchemy import text

logger = logging.getLogger("mita.ofertas")

ACTIVOS = ("ACEPTADA", "EN_CAMINO", "EN_SITIO", "EN_PROCESO")


def _cfg_int(db, clave, default):
    try:
        from app.services.config_service import ConfigService
        return int(ConfigService.get(db, clave, default) or default)
    except Exception:
        return default


def cfg_bool(db, clave, default=False):
    try:
        from app.services.config_service import ConfigService
        v = ConfigService.get(db, clave, default)
        return str(v).strip().lower() in ("1", "true", "si", "sí", "on", "yes") if v is not None else default
    except Exception:
        return default


def tecnicos_elegibles(db, solicitud):
    """Personal.id de técnicos: activos, con la especialidad, "Disponible hoy" (flag propio,
    independiente de estar atendiendo) y sin pasar el máximo de servicios EN CURSO (por
    solicitudes activas, no por estado_servicio) — zMita-38 Parte 0.1."""
    from app.models.personal import Personal, TecnicoPersonal, TipoPersonal, EstadoPersonal
    from app.models.solicitud_mita import Solicitud
    max_sim = _cfg_int(db, "max_servicios_simultaneos", 1)
    q = (db.query(Personal, TecnicoPersonal)
         .join(TecnicoPersonal, TecnicoPersonal.personal_id == Personal.id)
         .filter(Personal.tipo == TipoPersonal.TECNICO,
                 Personal.estado == EstadoPersonal.ACTIVO,
                 TecnicoPersonal.disponible_hoy == True))
    elegibles = []
    for p, tp in q.all():
        esp = tp.especialidades or []
        if solicitud.categoria_id and esp and solicitud.categoria_id not in esp:
            continue
        en_curso = (db.query(Solicitud)
                    .filter(Solicitud.tecnico_id == p.id, Solicitud.estado.in_(ACTIVOS)).count())
        if en_curso >= max_sim:
            continue
        elegibles.append(p.id)
    return elegibles


def difundir(db, solicitud, intento=1) -> int:
    """Pone la solicitud en BUSCANDO_TECNICO, crea una oferta por técnico elegible y avisa."""
    from app.models.oferta_servicio import OfertaServicio
    ids = tecnicos_elegibles(db, solicitud)
    solicitud.notificado_en = datetime.utcnow()
    solicitud.intento_notificacion = intento
    if not ids:
        solicitud.estado = "SIN_TECNICO"
        db.commit()
        logger.info("[ofertas] solicitud %s sin técnicos elegibles", solicitud.id)
        return 0
    solicitud.estado = "BUSCANDO_TECNICO"
    pendientes = {o.tecnico_id for o in db.query(OfertaServicio)
                  .filter(OfertaServicio.solicitud_id == solicitud.id,
                          OfertaServicio.respuesta.is_(None)).all()}
    for tid in ids:
        if tid in pendientes:
            continue
        db.add(OfertaServicio(solicitud_id=solicitud.id, tecnico_id=tid, intento=intento))
    db.commit()
    try:
        from app.services import push as _push
        from app.models.models import CategoriaServicio
        cat = db.query(CategoriaServicio).get(solicitud.categoria_id) if solicitud.categoria_id else None
        _push.avisar_nuevo_servicio(db, solicitud, tecnico_personal_ids=ids,
                                    especialidad=(cat.nombre if cat else ""),
                                    distrito=getattr(solicitud, "cliente_distrito", "") or "")
    except Exception:
        logger.exception("[ofertas] push nuevo_servicio")
    logger.info("[ofertas] solicitud %s difundida a %s técnicos", solicitud.id, len(ids))
    return len(ids)


def marcar_vista(db, solicitud_id, tecnico_id):
    from app.models.oferta_servicio import OfertaServicio
    o = (db.query(OfertaServicio)
         .filter(OfertaServicio.solicitud_id == solicitud_id, OfertaServicio.tecnico_id == tecnico_id)
         .order_by(OfertaServicio.id.desc()).first())
    if o and not o.vista_en:
        o.vista_en = datetime.utcnow(); db.commit()
    return o


def _marcar_oferta(db, solicitud_id, tecnico_id, respuesta):
    from app.models.oferta_servicio import OfertaServicio
    (db.query(OfertaServicio)
     .filter(OfertaServicio.solicitud_id == solicitud_id, OfertaServicio.tecnico_id == tecnico_id,
             OfertaServicio.respuesta.is_(None))
     .update({OfertaServicio.respuesta: respuesta, OfertaServicio.respondida_en: datetime.utcnow()},
             synchronize_session=False))


def aceptar(db, solicitud_id, tecnico_id) -> dict:
    """Reclamo ATÓMICO. Devuelve {ok, resultado, solicitud_id, chat_id}.
    resultado: aceptada | idempotente | tomada_por_otro."""
    from app.models.solicitud_mita import Solicitud
    from app.models.oferta_servicio import OfertaServicio
    res = db.execute(text(
        "UPDATE solicitudes SET tecnico_id = :t, estado = 'ACEPTADA', "
        "fecha_aceptacion = now(), aceptada_en = now() "
        "WHERE id = :id AND estado = 'BUSCANDO_TECNICO' AND tecnico_id IS NULL "
        "RETURNING id"), {"t": tecnico_id, "id": solicitud_id})
    gano = res.first() is not None
    db.commit()

    if gano:
        _marcar_oferta(db, solicitud_id, tecnico_id, "aceptada")
        (db.query(OfertaServicio)
         .filter(OfertaServicio.solicitud_id == solicitud_id,
                 OfertaServicio.tecnico_id != tecnico_id, OfertaServicio.respuesta.is_(None))
         .update({OfertaServicio.respuesta: "tomada_por_otro",
                  OfertaServicio.respondida_en: datetime.utcnow()}, synchronize_session=False))
        from app.models.personal import Personal
        p = db.query(Personal).get(tecnico_id)
        if p:
            p.estado_servicio = "OCUPADO"
        sala = None
        try:
            from app.routes.tecnico_api import _crear_chats, _nombre
            sala = _crear_chats(db, solicitud_id, _nombre(p), tecnico_id)
        except Exception:
            logger.exception("[ofertas] crear chats")
        db.commit()
        s = db.query(Solicitud).get(solicitud_id)
        _avisar_aceptado(db, s, p)
        return {"ok": True, "resultado": "aceptada", "solicitud_id": solicitud_id,
                "chat_id": getattr(sala, "id", None)}

    # No ganó: idempotencia o tomada por otro
    s = db.query(Solicitud).get(solicitud_id)
    if s and s.tecnico_id == tecnico_id:
        sala = _sala_existente(db, solicitud_id)
        return {"ok": True, "resultado": "idempotente", "solicitud_id": solicitud_id,
                "chat_id": getattr(sala, "id", None)}
    _marcar_oferta(db, solicitud_id, tecnico_id, "tomada_por_otro")
    db.commit()
    return {"ok": False, "resultado": "tomada_por_otro"}


def no_puedo(db, solicitud_id, tecnico_id):
    _marcar_oferta(db, solicitud_id, tecnico_id, "no_puedo")
    db.commit()
    return {"ok": True, "resultado": "no_puedo"}


def _sala_existente(db, solicitud_id):
    try:
        from app.models.chat_sala import ChatSala
        return (db.query(ChatSala)
                .filter(ChatSala.solicitud_id == solicitud_id, ChatSala.tipo == "cliente_tecnico").first())
    except Exception:
        return None


def eta_min(db, solicitud, tecnico_id):
    """Minutos estimados técnico->cliente (o None)."""
    try:
        from app.models.personal import TecnicoPersonal
        from app.services.rutas import eta
        tp = db.query(TecnicoPersonal).filter(TecnicoPersonal.personal_id == tecnico_id).first()
        if tp and tp.ultima_ubicacion_lat and tp.ultima_ubicacion_lng and solicitud.cliente_lat and solicitud.cliente_lng:
            e = eta(float(tp.ultima_ubicacion_lat), float(tp.ultima_ubicacion_lng),
                    float(solicitud.cliente_lat), float(solicitud.cliente_lng))
            return (e or {}).get("minutos")
    except Exception:
        logger.exception("[ofertas] eta")
    return None


def procesar_tiempos(db, ahora=None) -> dict:
    """Parte D: por cada solicitud BUSCANDO_TECNICO, según minutos desde la difusión:
    reenvío (una vez), alerta a la torre (una vez) y aviso al cliente (una vez). Idempotente."""
    from app.models.solicitud_mita import Solicitud
    ahora = ahora or datetime.utcnow()
    alerta_min = _cfg_int(db, "minutos_alerta_sin_aceptar", 5)
    reenvio_min = _cfg_int(db, "minutos_reenvio", 5)
    aviso_min = _cfg_int(db, "minutos_aviso_cliente", 15)
    acciones = {"reenvio": [], "alerta": [], "aviso": []}
    sols = (db.query(Solicitud)
            .filter(Solicitud.estado == "BUSCANDO_TECNICO", Solicitud.notificado_en.isnot(None)).all())
    for s in sols:
        mins = (ahora - s.notificado_en).total_seconds() / 60.0
        if mins >= reenvio_min and (s.intento_notificacion or 1) < 2:
            difundir(db, s, intento=2)
            acciones["reenvio"].append(s.id)
        if mins >= alerta_min and not s.alerta_sin_aceptar_en:
            try:
                from app.services import push as _push
                from app.models.models import CategoriaServicio
                cat = db.query(CategoriaServicio).get(s.categoria_id) if s.categoria_id else None
                _push.avisar_sin_aceptar(db, s, especialidad=(cat.nombre if cat else ""),
                                         distrito=s.cliente_distrito or "")
            except Exception:
                logger.exception("[ofertas] alerta torre")
            s.alerta_sin_aceptar_en = ahora
            acciones["alerta"].append(s.id)
        if mins >= aviso_min and not s.aviso_cliente_en:
            try:
                from app.services import push as _push
                _push.avisar_seguimos_buscando(db, s)
            except Exception:
                logger.exception("[ofertas] aviso cliente")
            s.aviso_cliente_en = ahora
            acciones["aviso"].append(s.id)
    db.commit()
    return acciones


def _avisar_aceptado(db, s, p):
    try:
        from app.routes.tecnico_api import _nombre
        from app.services import push as _push
        nombre = _nombre(p) if p else "Tu técnico"
        minutos = eta_min(db, s, p.id) if (s and p) else None
        _push.avisar_servicio_aceptado(db, s, tecnico_nombre=nombre, minutos=minutos)
        # Mensaje de sistema en el chat de 3 (zMita-38 Parte B)
        from app.services.servicio import mensaje_sistema
        mensaje_sistema(db, s.id, f"{nombre} aceptó tu servicio.")
    except Exception:
        logger.exception("[ofertas] avisar aceptado")
