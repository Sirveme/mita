"""
Identificación del comprador (zMita-39, Parte A): boleta/factura, consulta RUC/DNI
(reutiliza sunat_service) y memoria del comprador por celular.
"""
import logging

from app.services.documento import validar_documento, tipo_comprobante_por_documento
from app.models.cierre import CompradorPreferido

logger = logging.getLogger("mita.identificacion")


def consultar_documento(tipo: str, numero: str) -> dict:
    """Valida y, si hay servicio de consulta, trae razón social/nombres.

    Devuelve {ok, tipo, tipo_comprobante, razon_social?, direccion?, consulta_disponible, mensaje}."""
    ok, tipo_n, msg = validar_documento(tipo, numero)
    if not ok:
        return {"ok": False, "tipo": tipo_n, "mensaje": msg}

    out = {"ok": True, "tipo": tipo_n, "tipo_comprobante": tipo_comprobante_por_documento(tipo_n),
           "consulta_disponible": True, "mensaje": "OK"}
    try:
        from app.services import sunat_service
        if tipo_n == "RUC":
            d = sunat_service.consultar_ruc(numero)
            if d:
                out["razon_social"] = d.get("razon_social")
                out["direccion"] = d.get("direccion")
            else:
                out["consulta_disponible"] = False
        elif tipo_n == "DNI":
            d = sunat_service.consultar_dni(numero)
            if d:
                out["razon_social"] = f"{d.get('nombres','')} {d.get('apellido_paterno','')} {d.get('apellido_materno','')}".strip()
            else:
                out["consulta_disponible"] = False
        else:
            # CE / PASAPORTE: no hay consulta pública -> nombres a mano
            out["consulta_disponible"] = False
    except Exception:
        logger.info("[identificacion] consulta no disponible para %s", tipo_n)
        out["consulta_disponible"] = False
    return out


def comprador_recordado(db, celular: str):
    """Devuelve el CompradorPreferido guardado para ese celular, o None."""
    cel = "".join(ch for ch in (celular or "") if ch.isdigit())[-9:]
    if len(cel) != 9:
        return None
    return db.query(CompradorPreferido).filter(CompradorPreferido.celular == cel).first()


def guardar_comprador(db, solicitud, data: dict) -> dict:
    """Valida el documento, lo escribe en la solicitud y lo recuerda por celular.

    data: {tipo_comprobante, doc_tipo, doc_numero, razon_social, direccion_fiscal?}."""
    tipo_comp = (data.get("tipo_comprobante") or "").strip().lower()
    doc_tipo = data.get("doc_tipo")
    doc_numero = (data.get("doc_numero") or "").strip()
    nombre = (data.get("razon_social") or "").strip()

    ok, tipo_n, msg = validar_documento(doc_tipo, doc_numero)
    if not ok:
        return {"ok": False, "mensaje": msg}

    # Coherencia: factura exige RUC
    if tipo_comp == "factura" and tipo_n != "RUC":
        return {"ok": False, "mensaje": "La factura requiere un RUC."}
    if tipo_comp not in ("boleta", "factura"):
        tipo_comp = tipo_comprobante_por_documento(tipo_n)
    if not nombre:
        return {"ok": False, "mensaje": "Falta el nombre o la razón social."}

    solicitud.comprador_tipo_comprobante = tipo_comp
    solicitud.comprador_doc_tipo = tipo_n
    solicitud.comprador_doc_numero = doc_numero
    solicitud.comprador_nombre = nombre
    solicitud.comprador_direccion_fiscal = (data.get("direccion_fiscal") or None)

    # Recordar por celular (upsert)
    cel = "".join(ch for ch in (solicitud.cliente_telefono or "") if ch.isdigit())[-9:]
    if len(cel) == 9:
        cp = db.query(CompradorPreferido).filter(CompradorPreferido.celular == cel).first()
        if not cp:
            cp = CompradorPreferido(celular=cel)
            db.add(cp)
        cp.tipo_comprobante = tipo_comp
        cp.doc_tipo = tipo_n
        cp.doc_numero = doc_numero
        cp.razon_social = nombre
        cp.direccion_fiscal = solicitud.comprador_direccion_fiscal
    db.commit()
    return {"ok": True, "tipo_comprobante": tipo_comp, "tipo": tipo_n}
