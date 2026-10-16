"""
Servicio en vivo (zMita-38): en camino + ETA (A), chat de 3 (B), diagnóstico y presupuesto (C).
"""
import json
import time
import math
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("mita.servicio")

ACTIVOS = ("ACEPTADA", "EN_CAMINO", "EN_SITIO", "EN_PROCESO")
_VIENDO = {}   # (solicitud_id, rol) -> ts de la última vez que ese rol miró el chat


def _metros(lat1, lng1, lat2, lng2):
    R = 6371000.0
    dla = math.radians(lat2 - lat1); dlo = math.radians(lng2 - lng1)
    a = (math.sin(dla / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlo / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ----------------------------------------------------------------------------
# Parte A — En camino / ETA
# ----------------------------------------------------------------------------
def voy_en_camino(db, solicitud):
    solicitud.estado = "EN_CAMINO"
    solicitud.en_camino_desde = datetime.utcnow()
    _recalc_eta(db, solicitud, force=True)
    db.commit()
    try:
        from app.services import push as _push
        from app.routes.tecnico_api import _nombre
        from app.models.personal import Personal
        p = db.query(Personal).get(solicitud.tecnico_id) if solicitud.tecnico_id else None
        _push.avisar_en_camino(db, solicitud, tecnico_nombre=_nombre(p) if p else "Tu técnico",
                               minutos=solicitud.eta_actual_min)
    except Exception:
        logger.exception("[servicio] push voy_en_camino")
    return {"ok": True, "estado": "EN_CAMINO", "eta_min": solicitud.eta_actual_min}


def _tecnico_ubicacion(db, tecnico_id):
    from app.models.personal import TecnicoPersonal
    tp = db.query(TecnicoPersonal).filter(TecnicoPersonal.personal_id == tecnico_id).first()
    if tp and tp.ultima_ubicacion_lat and tp.ultima_ubicacion_lng:
        return float(tp.ultima_ubicacion_lat), float(tp.ultima_ubicacion_lng)
    return None


def _recalc_eta(db, solicitud, force=False):
    """Recalcula la ETA SOLO si pasaron >=3 min o el técnico se movió > 300 m (control de costo)."""
    if not (solicitud.cliente_lat and solicitud.cliente_lng):
        return
    pos = _tecnico_ubicacion(db, solicitud.tecnico_id)
    if not pos:
        return
    tlat, tlng = pos
    ahora = datetime.utcnow()
    if not force and solicitud.eta_calc_en:
        pasaron = (ahora - solicitud.eta_calc_en).total_seconds() >= 180
        movio = False
        if solicitud.eta_calc_lat is not None:
            movio = _metros(tlat, tlng, solicitud.eta_calc_lat, solicitud.eta_calc_lng) > 300
        if not (pasaron or movio):
            return
    from app.services.rutas import eta
    e = eta(tlat, tlng, float(solicitud.cliente_lat), float(solicitud.cliente_lng))
    if e:
        solicitud.eta_actual_min = e["minutos"]
        if solicitud.eta_inicial_min is None:
            solicitud.eta_inicial_min = e["minutos"]
        solicitud.eta_calc_en = ahora
        solicitud.eta_calc_lat = tlat
        solicitud.eta_calc_lng = tlng


def registrar_ubicacion(db, solicitud, tecnico_id, lat, lng, precision_m=None):
    """Guarda la ubicación SOLO mientras el servicio esté EN_CAMINO."""
    if solicitud.estado != "EN_CAMINO":
        return {"ok": False, "motivo": "no_en_camino"}
    from app.models.servicio_vivo import UbicacionServicio
    from app.models.personal import TecnicoPersonal
    db.add(UbicacionServicio(solicitud_id=solicitud.id, tecnico_id=tecnico_id,
                             lat=lat, lng=lng, precision_m=precision_m))
    tp = db.query(TecnicoPersonal).filter(TecnicoPersonal.personal_id == tecnico_id).first()
    if tp:
        tp.ultima_ubicacion_lat = lat; tp.ultima_ubicacion_lng = lng; tp.ultima_ubicacion_at = datetime.utcnow()
    _recalc_eta(db, solicitud)
    db.commit()
    return {"ok": True, "eta_min": solicitud.eta_actual_min}


def llegue(db, solicitud, lat=None, lng=None, confirmar=False):
    """EN_SITIO. Si el técnico está a > 200 m del domicilio, pide confirmación."""
    if lat and lng and solicitud.cliente_lat and solicitud.cliente_lng and not confirmar:
        d = _metros(float(lat), float(lng), float(solicitud.cliente_lat), float(solicitud.cliente_lng))
        if d > 200:
            return {"ok": False, "confirmar": True, "metros": int(d),
                    "mensaje": f"Estás a {int(d)} m de la dirección. ¿Confirmas que llegaste?"}
    solicitud.estado = "EN_SITIO"
    solicitud.fecha_llegada = datetime.utcnow()
    db.commit()
    try:
        from app.services import push as _push
        _push.avisar_tecnico_llego(db, solicitud)
    except Exception:
        logger.exception("[servicio] push llegue")
    return {"ok": True, "estado": "EN_SITIO"}


def cliente_no_esta(db, solicitud):
    """El técnico reporta que el cliente no está -> a la torre (no cancela solo)."""
    solicitud.cliente_no_esta_en = datetime.utcnow()
    db.commit()
    logger.warning("[torre] solicitud %s: el cliente no está. Revisar en /admin/en-curso.", solicitud.id)
    return {"ok": True}


def alertas_en_curso(db):
    """Datos para /admin/en-curso: técnicos en camino con ETA, última ubicación y alertas."""
    from app.models.solicitud_mita import Solicitud
    from app.models.servicio_vivo import UbicacionServicio
    ahora = datetime.utcnow()
    out = []
    sols = db.query(Solicitud).filter(Solicitud.estado.in_(["EN_CAMINO", "EN_SITIO"])).all()
    for s in sols:
        ult = (db.query(UbicacionServicio).filter(UbicacionServicio.solicitud_id == s.id)
               .order_by(UbicacionServicio.id.desc()).first())
        ubi_hace = int((ahora - ult.registrada_en).total_seconds()) if ult else None
        alertas = []
        if s.estado == "EN_CAMINO" and (ubi_hace is None or ubi_hace > 600):
            alertas.append("sin_ubicacion_10min")
        if s.eta_actual_min and s.eta_inicial_min and s.eta_actual_min > s.eta_inicial_min + 15:
            alertas.append("eta_mas_15")
        if s.cliente_no_esta_en:
            alertas.append("cliente_no_esta")
        out.append({"solicitud_id": s.id, "estado": s.estado, "tecnico_id": s.tecnico_id,
                    "eta_inicial": s.eta_inicial_min, "eta_actual": s.eta_actual_min,
                    "ubicacion_hace_seg": ubi_hace, "alertas": alertas})
    return out


# ----------------------------------------------------------------------------
# Parte B — Chat de 3
# ----------------------------------------------------------------------------
def rol_de(db, solicitud, request_rol, actor_id):
    """Valida que actor sea participante. Devuelve el rol efectivo o None."""
    if request_rol == "mita":
        return "mita"
    if request_rol == "tecnico":
        return "tecnico" if solicitud.tecnico_id and actor_id == solicitud.tecnico_id else None
    if request_rol == "cliente":
        # cliente anónimo o por id; si la solicitud tiene cliente_id, exigir match
        if solicitud.cliente_id:
            return "cliente" if actor_id == solicitud.cliente_id else None
        return "cliente"
    return None


def marcar_viendo(solicitud_id, rol):
    _VIENDO[(solicitud_id, rol)] = time.time()


def _viendo(solicitud_id, rol, ventana=8):
    return (time.time() - _VIENDO.get((solicitud_id, rol), 0)) <= ventana


def mensaje_sistema(db, solicitud_id, texto):
    from app.models.servicio_vivo import MensajeServicio
    m = MensajeServicio(solicitud_id=solicitud_id, autor_rol="mita", tipo="sistema", contenido=texto)
    db.add(m); db.commit()
    return m


def enviar_mensaje(db, solicitud, autor_rol, autor_id, tipo, contenido, nombre_autor="Alguien"):
    """Crea un mensaje (oculta celulares/correos en texto) y avisa al destinatario si no mira."""
    from app.models.servicio_vivo import MensajeServicio
    oculto = False
    if tipo == "texto":
        from app.services.privacidad import ocultar_datos
        contenido, oculto = ocultar_datos(contenido)
    payload = contenido if isinstance(contenido, str) else json.dumps(contenido, ensure_ascii=False)
    m = MensajeServicio(solicitud_id=solicitud.id, autor_rol=autor_rol, autor_id=autor_id,
                        tipo=tipo, contenido=payload, oculto_dato=oculto)
    db.add(m); db.commit(); db.refresh(m)
    if oculto:
        logger.warning("[torre] solicitud %s: %s intentó compartir un dato de contacto.", solicitud.id, autor_rol)
    # destinatario: el otro rol (cliente<->tecnico). mita no genera push al revés.
    destino = "cliente" if autor_rol in ("tecnico", "mita") else "tecnico"
    if not _viendo(solicitud.id, destino):
        try:
            from app.services import push as _push
            _push.avisar_mensaje(db, solicitud, destino, autor_nombre=nombre_autor)
        except Exception:
            logger.exception("[servicio] push mensaje")
    return m, oculto


def listar_mensajes(db, solicitud_id, desde_id=0):
    from app.models.servicio_vivo import MensajeServicio
    q = db.query(MensajeServicio).filter(MensajeServicio.solicitud_id == solicitud_id)
    if desde_id:
        q = q.filter(MensajeServicio.id > desde_id)
    return q.order_by(MensajeServicio.id).all()


# ----------------------------------------------------------------------------
# Parte C — Diagnóstico y presupuesto
# ----------------------------------------------------------------------------
def crear_presupuesto(db, solicitud, data):
    """Nueva versión del presupuesto; publica tarjeta en el chat y avisa al cliente."""
    from app.models.servicio_vivo import Presupuesto
    # marcar versiones previas como reemplazadas
    previos = db.query(Presupuesto).filter(Presupuesto.solicitud_id == solicitud.id).all()
    ver = 1
    for p in previos:
        ver = max(ver, (p.version or 1) + 1)
        if p.estado in ("propuesto",):
            p.estado = "reemplazado"
    requiere = bool(data.get("requiere_reparacion"))
    pr = Presupuesto(
        solicitud_id=solicitud.id, version=ver, diagnostico=(data.get("diagnostico") or "").strip(),
        requiere_reparacion=requiere, descripcion_trabajo=(data.get("descripcion_trabajo") or None),
        monto=(float(data["monto"]) if requiere and data.get("monto") not in (None, "") else None),
        incluye_materiales=bool(data.get("incluye_materiales")),
        materiales_detalle=(data.get("materiales_detalle") or None),
        tiempo_estimado=(data.get("tiempo_estimado") or None),
        fotos=(json.dumps(data.get("fotos")) if data.get("fotos") else None),
        estado="propuesto")
    db.add(pr); db.commit(); db.refresh(pr)

    tarjeta = {"tipo": "presupuesto", "presupuesto_id": pr.id, "version": ver,
               "diagnostico": pr.diagnostico, "requiere_reparacion": requiere,
               "monto": float(pr.monto) if pr.monto is not None else None,
               "incluye_materiales": pr.incluye_materiales, "materiales_detalle": pr.materiales_detalle,
               "tiempo_estimado": pr.tiempo_estimado}
    mensaje_tarjeta(db, solicitud.id, tarjeta)

    if requiere:
        try:
            from app.services import push as _push
            _push.avisar_presupuesto(db, solicitud)
        except Exception:
            logger.exception("[servicio] push presupuesto")
    else:
        # sin reparación -> directo a SOLO_DIAGNOSTICO
        solicitud.estado = "SOLO_DIAGNOSTICO"
        db.commit()
    return pr


def mensaje_tarjeta(db, solicitud_id, data):
    from app.models.servicio_vivo import MensajeServicio
    m = MensajeServicio(solicitud_id=solicitud_id, autor_rol="tecnico", tipo="tarjeta",
                        contenido=json.dumps(data, ensure_ascii=False))
    db.add(m); db.commit()
    return m


def decidir_presupuesto(db, presupuesto, aceptar, decidido_por=None, ip=None, ua=None):
    from app.models.solicitud_mita import Solicitud
    if presupuesto.estado != "propuesto":
        return {"ok": False, "motivo": "no_vigente", "estado": presupuesto.estado}
    presupuesto.estado = "aceptado" if aceptar else "rechazado"
    presupuesto.decidido_en = datetime.utcnow()
    presupuesto.decidido_por = (decidido_por or "cliente")[:60]
    presupuesto.ip = (ip or "")[:60] or None
    presupuesto.ua = (ua or "")[:300] or None
    s = db.query(Solicitud).get(presupuesto.solicitud_id)
    if s:
        s.estado = "REPARACION_ACEPTADA" if aceptar else "SOLO_DIAGNOSTICO"
    db.commit()
    mensaje_sistema(db, presupuesto.solicitud_id,
                    "El cliente aceptó el presupuesto." if aceptar else "El cliente no aceptó la reparación.")
    return {"ok": True, "estado_presupuesto": presupuesto.estado, "estado_solicitud": s.estado if s else None}
