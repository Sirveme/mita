"""
Cron de reintento de notificación a los técnicos.

Cada `INTERVALO_SEG` revisa las solicitudes en estado BUSCANDO_TECNICO cuyo
intento actual superó `notificaciones_intervalo_seg` (config, 180s por defecto)
sin que nadie aceptara:
  - Si aún quedan reintentos (< `notificaciones_max_reintentos`), REENVÍA la
    notificación a todos los técnicos EN_SERVICIO (sube `intento_notificacion`).
  - Si ya se agotaron los reintentos, la solicitud pasa a 'SIN_TECNICO'
    (el cliente lo ve en su pantalla de búsqueda).

Implementado con asyncio (sin dependencias externas) e integrado en el lifespan
de FastAPI. El trabajo de BD corre en un hilo para no bloquear el event loop.
Cada acción queda registrada en integraciones_log (visible en /soporte/logs).
"""
import asyncio
import logging
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.solicitud_mita import Solicitud
from app.models.notificacion_tecnico import NotificacionTecnico
from app.models.integracion import IntegracionLog
from app.services.config_service import ConfigService, get_max_reintentos, get_intervalo_notif
from app.routes.tecnico_api import _notificar_a_todos

logger = logging.getLogger("mita.timeout_tecnico")

INTERVALO_SEG = 30
_task = None


def _log(db, detalle: str, accion: str = "reenvio"):
    try:
        db.add(IntegracionLog(tipo="flujo", proveedor="asignacion",
                              accion=accion, usuario="sistema", detalle=detalle))
        db.commit()
    except Exception:
        db.rollback()


def _procesar_una(db, s: Solicitud, max_reintentos: int):
    if (s.intento_notificacion or 1) >= max_reintentos:
        # Agotados los reintentos: cerrar como SIN_TECNICO y cancelar pendientes.
        s.estado = "SIN_TECNICO"
        (db.query(NotificacionTecnico)
         .filter(NotificacionTecnico.solicitud_id == s.id,
                 NotificacionTecnico.respuesta.is_(None))
         .update({NotificacionTecnico.respuesta: "timeout",
                  NotificacionTecnico.respondido_en: datetime.utcnow()}, synchronize_session=False))
        db.commit()
        _log(db, f"Solicitud #{s.id}: {max_reintentos} intentos sin respuesta, SIN_TECNICO.",
             accion="sin-tecnico")
        logger.info("Solicitud %s: sin técnicos tras %s intentos", s.id, max_reintentos)
        # Aviso push a la torre de control (admin): servicio sin aceptar (zMita-33)
        try:
            from app.services import push as _push
            from app.models.models import CategoriaServicio
            cat = db.query(CategoriaServicio).get(s.categoria_id) if s.categoria_id else None
            _push.avisar_sin_aceptar(db, s, especialidad=(cat.nombre if cat else ""),
                                     distrito=getattr(s, "cliente_distrito", "") or getattr(s, "distrito", "") or "")
        except Exception:
            logger.exception("push sin_aceptar")
        return

    # Reenviar a todos los técnicos EN_SERVICIO (nueva ronda)
    s.intento_notificacion = (s.intento_notificacion or 1) + 1
    s.notificado_en = datetime.utcnow()
    n = _notificar_a_todos(db, s, intento=s.intento_notificacion)
    db.commit()
    _log(db, f"Solicitud #{s.id}: reenvío #{s.intento_notificacion} a {n} técnico(s).")
    logger.info("Solicitud %s: reenvío #%s a %s técnicos", s.id, s.intento_notificacion, n)


def procesar_timeouts_sync() -> int:
    """Una pasada síncrona. Devuelve el nº de solicitudes procesadas."""
    db = SessionLocal()
    try:
        ConfigService.clear_cache()          # respetar cambios del panel admin
        max_reintentos = get_max_reintentos(db)
        intervalo = get_intervalo_notif(db)
        limite = datetime.utcnow() - timedelta(seconds=intervalo)
        sols = (db.query(Solicitud)
                .filter(Solicitud.estado == "BUSCANDO_TECNICO",
                        Solicitud.notificado_en.isnot(None),
                        Solicitud.notificado_en < limite)
                .all())
        for s in sols:
            try:
                _procesar_una(db, s, max_reintentos)
            except Exception:
                db.rollback()
                logger.exception("Error procesando timeout de solicitud %s", s.id)
        return len(sols)
    finally:
        db.close()


async def _loop():
    logger.info("Cron de timeout de técnicos iniciado (cada %ss)", INTERVALO_SEG)
    while True:
        try:
            await asyncio.to_thread(procesar_timeouts_sync)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error en el loop de timeouts")
        try:
            await asyncio.sleep(INTERVALO_SEG)
        except asyncio.CancelledError:
            break


def iniciar_scheduler():
    """Arranca el loop en background (idempotente)."""
    global _task
    if _task and not _task.done():
        return _task
    _task = asyncio.create_task(_loop())
    print("[SCHEDULER] Cron de timeout de técnicos iniciado (cada 30s)")
    return _task


async def detener_scheduler():
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
