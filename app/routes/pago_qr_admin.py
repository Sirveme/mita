"""
Configuración del cobro QR (Yape/Plin) en el panel admin: número, titular e IMAGEN del QR
(subida de archivo). Guarda en chat_conocimiento (pago_qr_numero / pago_qr_titular / pago_qr_imagen).
"""
import re
import base64
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.routes.servicio_api import _es_admin

logger = logging.getLogger("mita.pago_qr_admin")
router = APIRouter(tags=["Config pago QR"])

IMG_MIME_OK = ("image/png", "image/jpeg", "image/jpg", "image/webp")
IMG_MAX = 2 * 1024 * 1024   # 2 MB


async def _guard(request, db):
    if not await _es_admin(request, db):
        raise HTTPException(status_code=403, detail="Solo administración")


def _get(db, clave):
    from app.models.chat_conocimiento import ChatConocimiento
    r = db.query(ChatConocimiento).filter(ChatConocimiento.clave == clave).first()
    return (r.contenido or "") if r else ""


def _set(db, clave, titulo, contenido):
    from app.models.chat_conocimiento import ChatConocimiento
    r = db.query(ChatConocimiento).filter(ChatConocimiento.clave == clave).first()
    if not r:
        r = ChatConocimiento(clave=clave, titulo=titulo); db.add(r)
    r.contenido = contenido
    r.activo = bool(contenido)


def _norm_numero(raw: str):
    """Devuelve (digitos, error). Acepta espacios y +51; exige celular peruano de 9 dígitos."""
    d = re.sub(r"\D", "", raw or "")
    if d.startswith("51") and len(d) == 11:
        d = d[2:]
    if len(d) == 9 and d.startswith("9"):
        return d, None
    return None, "El número debe ser un celular peruano de 9 dígitos (empieza con 9), sin +51."


def _valida_imagen(data_url: str):
    """Devuelve (data_url_ok|None, error). '' = sin cambio (no se tocó la imagen)."""
    if not data_url:
        return "", None
    if not data_url.startswith("data:image/"):
        return None, "Sube una imagen (PNG, JPG o WEBP)."
    head, _, b64 = data_url.partition(",")
    mime = head.split(";")[0].replace("data:", "").lower()
    if mime not in IMG_MIME_OK:
        return None, "Formato no soportado. Usa PNG, JPG o WEBP."
    try:
        size = len(base64.b64decode(b64 + "=" * (-len(b64) % 4)))
    except Exception:
        return None, "La imagen no es válida."
    if size > IMG_MAX:
        return None, "La imagen supera los 2 MB."
    return data_url, None


@router.get("/api/v1/admin/pago-qr")
async def pago_qr_get(request: Request, db: Session = Depends(get_db)):
    await _guard(request, db)
    img = _get(db, "pago_qr_imagen")
    return {"numero": _get(db, "pago_qr_numero"), "titular": _get(db, "pago_qr_titular"),
            "tiene_imagen": bool(img), "imagen": img}


@router.post("/api/v1/admin/pago-qr")
async def pago_qr_set(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    await _guard(request, db)
    d = data or {}

    numero_raw = d.get("numero")
    if numero_raw is not None and str(numero_raw).strip() != "":
        numero, err = _norm_numero(str(numero_raw))
        if err:
            raise HTTPException(status_code=422, detail=err)
        _set(db, "pago_qr_numero", "Número Yape/Plin de MITA", numero)

    # titular es opcional; "" lo deja vacío/oculto
    if "titular" in d:
        _set(db, "pago_qr_titular", "Titular del Yape/Plin de MITA", (d.get("titular") or "").strip()[:150])

    if "imagen" in d:
        img, err = _valida_imagen(d.get("imagen") or "")
        if err:
            raise HTTPException(status_code=422, detail=err)
        if img != "":   # "" = no se cambió
            _set(db, "pago_qr_imagen", "Imagen del QR de MITA (Yape/Plin)", img)

    db.commit()
    try:
        from app.routes.chat_ia_api import limpiar_cache_conocimiento
        limpiar_cache_conocimiento()
    except Exception:
        pass
    img = _get(db, "pago_qr_imagen")
    return {"ok": True, "numero": _get(db, "pago_qr_numero"),
            "titular": _get(db, "pago_qr_titular"), "tiene_imagen": bool(img)}
