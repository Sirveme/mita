"""
Tarea de fondo (zMita-41): reconsulta los comprobantes 'enviando' para obtener el CDR real
de SUNAT. Cadencia por comprobante: 5 s el primer minuto, luego 2 min hasta 1 h. Con varios
workers corre UNA sola vez (pg_try_advisory_lock).
"""
import time
import asyncio
import logging

from sqlalchemy import text

logger = logging.getLogger("mita.comprobantes")
LOCK_KEY = 8237462
_task = None


def _una_pasada():
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        try:
            got = db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": LOCK_KEY}).scalar()
        except Exception:
            got = True   # sqlite u otros: sin advisory lock, corre igual
        if not got:
            return
        try:
            from app.services import comprobante
            comprobante.consultar_pendientes(db)
        finally:
            try:
                db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_KEY})
                db.commit()
            except Exception:
                pass
    except Exception:
        logger.exception("[comprobantes] pasada")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


async def _loop():
    while True:
        try:
            await asyncio.to_thread(_una_pasada)
        except Exception:
            logger.exception("[comprobantes] loop")
        await asyncio.sleep(15)


def iniciar():
    global _task
    try:
        _task = asyncio.get_event_loop().create_task(_loop())
        logger.info("[comprobantes] tarea de fondo iniciada (cada 15 s)")
    except Exception:
        logger.exception("[comprobantes] no se pudo iniciar")


async def detener():
    if _task:
        _task.cancel()
