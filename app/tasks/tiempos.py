"""
Tarea de fondo (zMita-38, Parte 0.2): cada 60 s procesa los tiempos de las ofertas
(reenvío/alerta/aviso). Usa pg_try_advisory_lock para que con varios workers corra UNA sola vez.
Expone el "último chequeo" para mostrarlo en la torre.
"""
import time
import asyncio
import logging

from sqlalchemy import text

logger = logging.getLogger("mita.tiempos")
LOCK_KEY = 8237461
_ULTIMO = {"ts": 0.0}
_task = None


def ultimo_chequeo_hace_seg():
    return int(time.time() - _ULTIMO["ts"]) if _ULTIMO["ts"] else None


def _una_pasada():
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        got = db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": LOCK_KEY}).scalar()
        if not got:
            return False
        try:
            from app.services import ofertas
            ofertas.procesar_tiempos(db)
            _ULTIMO["ts"] = time.time()
        finally:
            db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_KEY})
            db.commit()
        return True
    except Exception:
        logger.exception("[tiempos] pasada")
        try:
            db.rollback()
        except Exception:
            pass
        return False
    finally:
        db.close()


async def _loop():
    while True:
        try:
            await asyncio.to_thread(_una_pasada)
        except Exception:
            logger.exception("[tiempos] loop")
        await asyncio.sleep(60)


def iniciar():
    global _task
    try:
        _task = asyncio.get_event_loop().create_task(_loop())
        logger.info("[tiempos] tarea de fondo iniciada (cada 60 s)")
    except Exception:
        logger.exception("[tiempos] no se pudo iniciar")


async def detener():
    if _task:
        _task.cancel()
