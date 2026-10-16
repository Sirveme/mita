"""
Validación de documento del COMPRADOR antes de emitir comprobante (zMita-34 v2, Parte D).

Reglas:
  - DNI: 8 dígitos.
  - RUC: 11 dígitos; empieza con 10, 15, 17 o 20.
  - CE (carnet de extranjería): 9 a 12 caracteres alfanuméricos.
  - Pasaporte: 6 a 12 caracteres alfanuméricos.
  - El TIPO debe ser coherente con el número (p.ej. "DNI" con 11 dígitos de RUC -> inválido).

validar_documento(tipo, numero) -> (ok, tipo_normalizado, mensaje)
tipo_comprobante_por_documento(tipo_doc) -> "factura" si RUC, si no "boleta".
"""
import re

RUC_PREFIJOS = ("10", "15", "17", "20")


def _norm_tipo(tipo: str) -> str:
    t = (tipo or "").strip().lower()
    if t in ("dni", "d"):
        return "DNI"
    if t in ("ruc", "r"):
        return "RUC"
    if t in ("ce", "carnet_extranjeria", "carnet", "carne_extranjeria", "cext"):
        return "CE"
    if t in ("pasaporte", "pas", "passport", "pass"):
        return "PASAPORTE"
    return (tipo or "").strip().upper()


def _infiere_tipo(numero: str) -> str:
    n = (numero or "").strip()
    if re.fullmatch(r"\d{8}", n):
        return "DNI"
    if re.fullmatch(r"\d{11}", n) and n[:2] in RUC_PREFIJOS:
        return "RUC"
    if re.fullmatch(r"[A-Za-z0-9]{9,12}", n):
        return "CE"
    if re.fullmatch(r"[A-Za-z0-9]{6,12}", n):
        return "PASAPORTE"
    return ""


def validar_documento(tipo: str, numero: str):
    """Devuelve (ok: bool, tipo_normalizado: str, mensaje: str)."""
    numero = (numero or "").strip()
    tipo_n = _norm_tipo(tipo)
    if not numero:
        return False, tipo_n, "Falta el número de documento."

    reglas = {
        "DNI": (lambda n: bool(re.fullmatch(r"\d{8}", n)), "El DNI debe tener 8 dígitos."),
        "RUC": (lambda n: bool(re.fullmatch(r"\d{11}", n)) and n[:2] in RUC_PREFIJOS,
                "El RUC debe tener 11 dígitos y empezar con 10, 15, 17 o 20."),
        "CE": (lambda n: bool(re.fullmatch(r"[A-Za-z0-9]{9,12}", n)),
               "El carnet de extranjería debe tener de 9 a 12 caracteres."),
        "PASAPORTE": (lambda n: bool(re.fullmatch(r"[A-Za-z0-9]{6,12}", n)),
                      "El pasaporte debe tener de 6 a 12 caracteres."),
    }
    if tipo_n not in reglas:
        return False, tipo_n, f"Tipo de documento no soportado: {tipo!r}."

    # Coherencia tipo<->número: si el número encaja claramente con OTRO tipo (DNI vs RUC),
    # rechazar con mensaje claro (el bug: "DNI" con un número de RUC).
    inferido = _infiere_tipo(numero)
    if inferido in ("DNI", "RUC") and tipo_n in ("DNI", "RUC") and inferido != tipo_n:
        return False, tipo_n, (f"El número parece un {inferido}, pero el tipo dice {tipo_n}. "
                               "Corrige el tipo de documento.")

    ok, msg = reglas[tipo_n]
    if not ok(numero):
        return False, tipo_n, msg
    return True, tipo_n, "OK"


def tipo_comprobante_por_documento(tipo_doc: str) -> str:
    """RUC -> factura; cualquier otro -> boleta."""
    return "factura" if _norm_tipo(tipo_doc) == "RUC" else "boleta"
