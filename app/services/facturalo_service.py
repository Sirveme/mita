"""
Cliente real de la API v1 de Facturalo.pro (emisión de comprobantes SUNAT).
Contrato: docs/api-v1-emision.md (generado del código de src/api/v1 de Facturalo).

Autenticación: headers X-API-Key + X-API-Secret (FACTURALO_API_KEY / FACTURALO_API_SECRET).
Emisión ASÍNCRONA: POST /comprobantes devuelve estado 'encolado' (NO aceptado); hay que
consultar GET /comprobantes/{id} para el CDR de SUNAT. La capa de estado/polling y la
idempotencia por referencia_externa viven en app/services/comprobante.py.

Este módulo NO decide estados de negocio: solo habla con Facturalo y normaliza la respuesta.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("mita.facturalo")

IGV = 0.18

# tipo_comprobante SUNAT (catálogo 01)
TIPO = {"boleta": "03", "factura": "01", "nota_credito": "07", "nota_debito": "08"}
# tipo_documento del cliente (catálogo 06): 0 sin doc, 1 DNI, 4 CE, 6 RUC, 7 Pasaporte
DOC = {"DNI": "1", "CE": "4", "RUC": "6", "PASAPORTE": "7"}


def configurado() -> bool:
    return bool(settings.FACTURALO_API_KEY and settings.FACTURALO_API_SECRET)


def _base() -> str:
    """URL final = <host>/api/v1. Tolera que FACTURALO_BASE_URL ya traiga /api/v1 (no duplica)."""
    base = (settings.FACTURALO_BASE_URL or "https://facturalo.pro").rstrip("/")
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")]
    return base + "/api/v1"


def _headers() -> dict:
    return {"X-API-Key": settings.FACTURALO_API_KEY or "",
            "X-API-Secret": settings.FACTURALO_API_SECRET or "",
            "Content-Type": "application/json"}


def _llamar_api(metodo: str, ruta: str, json=None, params=None, timeout=25):
    """Llama a Facturalo. Devuelve (status:int, body:dict). status 0 = error de red."""
    import httpx
    url = _base() + ruta
    try:
        r = httpx.request(metodo, url, headers=_headers(), json=json, params=params, timeout=timeout)
    except Exception as e:
        logger.warning("[facturalo] red %s %s: %s", metodo, ruta, e)
        return 0, {"exito": False, "error": str(e), "codigo": "NETWORK"}
    try:
        body = r.json()
    except Exception:
        body = {}
    return r.status_code, body


def _serie_para(tipo_comp: str, ensayo: bool = False) -> Optional[str]:
    """En pruebas (o si es un ENSAYO, zMita-45) forzamos la serie 999 (B999/F999), aunque
    FACTURALO_MODO=produccion. En producción (no ensayo), serie automática del emisor
    (B940/F940...). Las notas van sin serie: la API elige la letra correcta (B->BC.., F->FC..)."""
    pruebas = ensayo or (settings.FACTURALO_MODO or "pruebas").lower() != "produccion"
    if not pruebas:
        return None   # producción: serie automática del emisor (B940/F940...)
    if tipo_comp == "boleta":
        return "B999"
    if tipo_comp == "factura":
        return "F999"
    return None


def _precio_sin_igv(monto: float, igv_incluido: bool) -> float:
    monto = float(monto or 0)
    return round(monto / (1 + IGV), 2) if igv_incluido else round(monto, 2)


def _cliente_payload(cliente: dict) -> dict:
    doc_tipo = (cliente.get("doc_tipo") or "").upper()
    tipo = DOC.get(doc_tipo, "0")
    numero = (cliente.get("doc_numero") or "").strip()
    # Boleta sin documento (tipo_documento "0"): SUNAT exige numero_documento "0"
    # (nunca vacío ni "-"), con el nombre real en razon_social.
    if tipo == "0" or not numero:
        tipo = "0"; numero = "0"
    out = {"tipo_documento": tipo,
           "numero_documento": numero,
           "razon_social": (cliente.get("razon_social") or "Cliente").strip()[:200]}
    if cliente.get("direccion"):
        out["direccion"] = cliente["direccion"][:200]
    if cliente.get("email"):
        out["email"] = cliente["email"]
    return out


def _items_payload(items: list, igv_incluido: bool) -> list:
    """items: [{descripcion, monto(bruto), cantidad?, codigo_sunat?}]. precio_unitario va SIN IGV."""
    out = []
    for it in items:
        linea = {"descripcion": (it.get("descripcion") or "Servicio")[:250],
                 "cantidad": float(it.get("cantidad") or 1),
                 "unidad_medida": it.get("unidad_medida") or "ZZ",
                 "precio_unitario": _precio_sin_igv(it.get("monto"), igv_incluido),
                 "tipo_afectacion_igv": "10"}
        if it.get("codigo_sunat"):
            linea["codigo"] = str(it["codigo_sunat"])
        out.append(linea)
    return out


def _normaliza_emision(status: int, body: dict) -> dict:
    if status == 200 and body.get("exito"):
        c = body.get("comprobante") or {}
        arch = body.get("archivos") or {}
        return {"ok": True, "id": c.get("id"), "serie": c.get("serie"),
                "numero": c.get("numero"), "numero_formato": c.get("numero_formato"),
                "estado": c.get("estado"), "total": c.get("total"),
                "codigo_sunat": c.get("codigo_sunat"), "mensaje_sunat": c.get("mensaje_sunat"),
                "pdf_url": arch.get("pdf_url")}
    return {"ok": False, "status": status, "error": body.get("error") or "Error de emisión",
            "codigo": body.get("codigo") or f"HTTP_{status}"}


def emitir(cliente: dict, items: list, tipo_comp: str, referencia_externa: str,
           igv_incluido: Optional[bool] = None, ensayo: bool = False) -> dict:
    """Emite boleta/factura. Devuelve la respuesta normalizada (estado 'encolado' al inicio).
    `ensayo=True` fuerza la serie de pruebas (B999/F999) aunque FACTURALO_MODO=produccion."""
    if igv_incluido is None:
        igv_incluido = bool(settings.FACTURALO_IGV_INCLUIDO)
    if tipo_comp == "factura" and (cliente.get("doc_tipo") or "").upper() != "RUC":
        return {"ok": False, "codigo": "FACTURA_REQUIERE_RUC", "error": "La factura exige RUC."}
    if tipo_comp == "factura" and len((cliente.get("doc_numero") or "").strip()) != 11:
        return {"ok": False, "codigo": "RUC_INVALIDO", "error": "El RUC debe tener 11 dígitos."}

    body = {"tipo_comprobante": TIPO.get(tipo_comp, "03"),
            "cliente": _cliente_payload(cliente),
            "items": _items_payload(items, igv_incluido),
            "forma_pago": "Contado",
            "enviar_email": bool(cliente.get("email")),
            "referencia_externa": referencia_externa[:100]}
    serie = _serie_para(tipo_comp, ensayo=ensayo)
    if serie:
        body["serie"] = serie
    status, resp = _llamar_api("POST", "/comprobantes", json=body)
    return _normaliza_emision(status, resp)


def emitir_nota_credito(cliente: dict, items: list, ref_tipo_comp: str, ref_serie: str,
                        ref_numero, motivo: str, referencia_externa: str,
                        motivo_nota: str = "01", igv_incluido: Optional[bool] = None) -> dict:
    """Emite una NC (motivo 01 = anulación total) referenciando el comprobante original.
    La serie va automática: la API usa la letra correcta (boleta->BC.., factura->FC..)."""
    if igv_incluido is None:
        igv_incluido = bool(settings.FACTURALO_IGV_INCLUIDO)
    body = {"tipo_comprobante": "07",
            "cliente": _cliente_payload(cliente),
            "items": _items_payload(items, igv_incluido),
            "documento_ref_tipo": TIPO.get(ref_tipo_comp, "03"),
            "documento_ref_serie": ref_serie,
            "documento_ref_numero": int(ref_numero),
            "motivo_nota": motivo_nota,
            "observaciones": (motivo or "Anulación")[:500],
            "referencia_externa": referencia_externa[:100]}
    status, resp = _llamar_api("POST", "/comprobantes", json=body)
    return _normaliza_emision(status, resp)


def consultar(comprobante_id: str) -> dict:
    """GET /comprobantes/{id}: estado + CDR. Normaliza el ciclo de vida de Facturalo."""
    status, body = _llamar_api("GET", f"/comprobantes/{comprobante_id}")
    if status == 200 and body.get("exito"):
        c = body.get("comprobante") or {}
        est = (c.get("estado") or "").lower()
        aceptado = est in ("aceptado", "aceptado_con_observaciones")
        return {"ok": True, "estado_api": est,
                "aceptado": aceptado, "rechazado": est == "rechazado", "anulado": est == "anulado",
                "terminal": aceptado or est in ("rechazado", "anulado"),
                "codigo_sunat": c.get("codigo_sunat"), "mensaje_sunat": c.get("mensaje_sunat"),
                "hash_cpe": c.get("hash_cpe"), "numero_formato": c.get("numero_formato"),
                "total": c.get("total")}
    return {"ok": False, "status": status, "error": body.get("error"), "codigo": body.get("codigo")}


def buscar_referencia(referencia_externa: str) -> dict:
    """GET /comprobantes/buscar/referencia/{ref}: para idempotencia antes de reintentar."""
    status, body = _llamar_api("GET", f"/comprobantes/buscar/referencia/{referencia_externa}")
    if status == 200 and body.get("exito"):
        c = body.get("comprobante") or {}
        return {"ok": True, "existe": True, "id": c.get("id"),
                "numero_formato": c.get("numero_formato"), "estado": c.get("estado")}
    if status == 404:
        return {"ok": True, "existe": False}
    return {"ok": False, "status": status}


def pdf_url(comprobante_id: str, formato: str = "A4") -> str:
    return f"{_base()}/comprobantes/{comprobante_id}/pdf?formato={formato}"


def ping() -> dict:
    """Healthcheck sin auth: GET /api/v1/estado. Para el panel /admin/estado."""
    status, body = _llamar_api("GET", "/estado", timeout=8)
    return {"ok": status == 200 and bool(body.get("exito")),
            "estado": body.get("estado"), "status": status}
