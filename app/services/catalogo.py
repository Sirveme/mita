"""
Fuente única de verdad del catálogo para chat y formulario (zMita-23).
- precio_visita_vigente(): precio de la visita vigente HOY (America/Lima), con promo.
- registrar_historial(): registra un cambio en catalogo_historial.
- invalidar_conocimiento() / ultima_actualizacion(): invalidación del bloque CONOCIMIENTO.
"""
import logging
from datetime import datetime, timedelta, date

from sqlalchemy.orm import Session

from app.services.config_service import ConfigService

logger = logging.getLogger("mita.catalogo")

# Marca de la última actualización del catálogo (se muestra en el admin)
_ESTADO = {"actualizado": datetime.utcnow()}


def hoy_lima() -> date:
    """Fecha de hoy en zona America/Lima (UTC-5, sin DST)."""
    return (datetime.utcnow() - timedelta(hours=5)).date()


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _fecha(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def precio_visita_vigente(db: Session) -> dict:
    """Devuelve {precio, es_promo, regular, promo, hasta} usando la MISMA config
    que ve el formulario. La promo aplica solo si hoy (Lima) está en su vigencia."""
    regular = _f(ConfigService.get(db, "tarifa_visita_default", 50) or 50, 50.0)
    promo = _f(ConfigService.get(db, "tarifa_visita_promo", 0) or 0, 0.0)
    desde = _fecha(ConfigService.get(db, "tarifa_visita_promo_desde", ""))
    hasta = _fecha(ConfigService.get(db, "tarifa_visita_promo_hasta", ""))
    hoy = hoy_lima()
    vigente = promo > 0 and (desde is None or hoy >= desde) and (hasta is None or hoy <= hasta)
    if vigente:
        return {"precio": promo, "es_promo": True, "regular": regular, "promo": promo,
                "hasta": hasta.isoformat() if hasta else None}
    return {"precio": regular, "es_promo": False, "regular": regular, "promo": None, "hasta": None}


def registrar_historial(db: Session, entidad: str, entidad_id, campo: str,
                        anterior, nuevo, usuario_id=None):
    try:
        from app.models.catalogo_historial import CatalogoHistorial
        db.add(CatalogoHistorial(
            entidad=entidad, entidad_id=str(entidad_id), campo=campo,
            valor_anterior=None if anterior is None else str(anterior),
            valor_nuevo=None if nuevo is None else str(nuevo),
            usuario_id=usuario_id,
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("No se pudo registrar historial de catálogo")


def invalidar_conocimiento():
    """Invalida el cache del bloque CONOCIMIENTO del chat y marca la hora."""
    _ESTADO["actualizado"] = datetime.utcnow()
    try:
        from app.routes.chat_ia_api import limpiar_cache_conocimiento
        limpiar_cache_conocimiento()
    except Exception:
        pass


def ultima_actualizacion() -> str:
    return _ESTADO["actualizado"].isoformat()
