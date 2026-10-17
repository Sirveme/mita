"""
Estado del sistema (zMita-42, Parte A3): ✓/✗ por integración, sin mostrar secretos.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.routes.servicio_api import _es_admin

logger = logging.getLogger("mita.estado")
router = APIRouter(tags=["Estado del sistema"])


def _qr(db):
    try:
        from app.models.chat_conocimiento import ChatConocimiento
        import re
        filas = {r.clave: (r.contenido or "") for r in db.query(ChatConocimiento).filter(
            ChatConocimiento.clave.in_(["pago_qr_numero", "pago_qr_imagen", "pago_qr_titular", "whatsapp_numero"])).all()}
        return filas
    except Exception:
        return {}


@router.get("/api/v1/admin/estado")
async def estado(request: Request, db: Session = Depends(get_db)):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")
    from app.services import pagook, facturalo_service as fact
    from app.core.security import es_produccion
    from app.tasks.tiempos import ultimo_chequeo_hace_seg

    f = _qr(db)
    qr_num = bool((f.get("pago_qr_numero") or "").strip())
    qr_img = bool((f.get("pago_qr_imagen") or "").strip())

    fact_ping = None
    if fact.configurado():
        try:
            fact_ping = fact.ping()
        except Exception:
            fact_ping = {"ok": False}

    def item(ok, detalle, falta=None, extra=None):
        d = {"ok": bool(ok), "detalle": detalle}
        if not ok and falta:
            d["falta"] = falta
        if extra:
            d.update(extra)
        return d

    return {
        "entorno": item(es_produccion(), f"ENVIRONMENT={settings.ENVIRONMENT or '(vacío → producción)'}",
                        extra={"demo_auth": bool(settings.DEMO_AUTH), "produccion": es_produccion()}),
        "pagook": item(pagook.configurado(), "Validación automática de pagos",
                       falta="PAGOOK_API_KEY. Sin ella el pago QR igual se muestra, pero lo valida la torre."),
        "qr": item(qr_num or qr_img, f"Número: {'sí' if qr_num else 'no'} · Imagen: {'sí' if qr_img else 'no'}",
                   falta="Configura pago_qr_numero o pago_qr_imagen en el panel.",
                   extra={"titular": bool((f.get('pago_qr_titular') or '').strip())}),
        "facturalo": item(fact.configurado(), f"Modo: {settings.FACTURALO_MODO}",
                          falta="FACTURALO_API_KEY/SECRET. Sin esto los comprobantes quedan pendientes.",
                          extra={"modo": settings.FACTURALO_MODO,
                                 "ping": (fact_ping or {}).get("ok") if fact_ping else None}),
        "google_maps": item(bool(settings.GOOGLE_MAPS_API_KEY), "Clave de navegador (mapa de seguimiento)",
                            falta="GOOGLE_MAPS_API_KEY",
                            extra={"servidor": bool(settings.GOOGLE_MAPS_SERVER_KEY)}),
        "vapid": item(bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY), "Avisos push",
                      falta="VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY"),
        "tarea_fondo": item(ultimo_chequeo_hace_seg() is not None,
                            (f"Último chequeo de tiempos: hace {ultimo_chequeo_hace_seg()} s"
                             if ultimo_chequeo_hace_seg() is not None else "Aún no corre"),
                            falta="La tarea de fondo no ha corrido todavía."),
        "whatsapp": item(bool((f.get("whatsapp_numero") or "").strip()),
                         "Número configurado; envío por Cloud API pendiente de implementar",
                         falta="whatsapp_numero en el panel", extra={"api_implementada": False}),
    }
