"""
Normalización de texto para voz (zMita-31, Parte D).

`texto_para_voz(t)` convierte el texto que ve el usuario en algo que el TTS lee
bien y SIEMPRE en español:
  - "S/ 50.00" -> "cincuenta soles"; "S/ 120.50" -> "ciento veinte soles con cincuenta céntimos"
  - "7:00 pm" -> "siete de la noche"; "10:00 am" -> "diez de la mañana"; "12:00 pm" -> "doce del mediodía"
  - "mar 13 oct" -> "martes 13 de octubre"
  - "Av." -> "avenida"; "Jr." -> "jirón"; "N°" -> "número"
  - quita emojis/símbolos (🕐 ✓ ✏️ ★ …)
  - reemplaza tokens en inglés que queden (am/pm/OK)

`hora_coloquial(iso)` y `dia_coloquial(iso, ahora)` construyen frases de agenda
("hoy a las 7:00 de la noche") para la oferta ASAP (Parte C).
"""
import re
import unicodedata
from datetime import datetime, timedelta

# ---- números a palabras (0..999 999, suficiente para soles y minutos) ----
_UNID = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
         "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
         "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
         "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve"]
_DEC = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
_CEN = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
        "seiscientos", "setecientos", "ochocientos", "novecientos"]


def _num(n: int) -> str:
    n = int(n)
    if n < 30:
        return _UNID[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DEC[d] + (" y " + _UNID[u] if u else "")
    if n == 100:
        return "cien"
    if n < 1000:
        c, r = divmod(n, 100)
        return _CEN[c] + ((" " + _num(r)) if r else "")
    if n < 1_000_000:
        miles, r = divmod(n, 1000)
        pre = "mil" if miles == 1 else (_num(miles) + " mil")
        return pre + ((" " + _num(r)) if r else "")
    return str(n)


def _soles(entero: int, centimos: int) -> str:
    entero = int(entero)
    txt = "un sol" if entero == 1 else f"{_num(entero)} soles"
    if centimos:
        c = int(centimos)
        txt += " con " + (_num(c) + (" céntimo" if c == 1 else " céntimos"))
    return txt


def _franja(hora24: int) -> str:
    if hora24 == 12:
        return "del mediodía"
    if hora24 == 0:
        return "de la medianoche"
    if hora24 < 12:
        return "de la mañana"
    if hora24 < 19:
        return "de la tarde"
    return "de la noche"


DIAS = {"lun": "lunes", "mar": "martes", "mie": "miércoles", "mié": "miércoles",
        "jue": "jueves", "vie": "viernes", "sab": "sábado", "sáb": "sábado", "dom": "domingo"}
MESES = {"ene": "enero", "feb": "febrero", "mar": "marzo", "abr": "abril", "may": "mayo",
         "jun": "junio", "jul": "julio", "ago": "agosto", "sep": "septiembre", "set": "septiembre",
         "oct": "octubre", "nov": "noviembre", "dic": "diciembre"}
MESES_LARGO = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").lower()


def _rep_moneda(m: re.Match) -> str:
    entero = m.group(1).replace(",", "").replace(".", "")
    cent = m.group(2) or ""
    if cent and len(cent) == 1:
        cent += "0"
    return _soles(int(entero), int(cent) if cent else 0)


def _rep_hora(m: re.Match) -> str:
    h = int(m.group(1))
    mi = int(m.group(2))
    sufijo = (m.group(3) or "").lower().replace(".", "").replace(" ", "")
    # Determinar hora de 24h según am/pm o la franja textual ya presente
    franja_txt = None
    if sufijo in ("am",):
        h24 = 0 if h == 12 else h
    elif sufijo in ("pm",):
        h24 = 12 if h == 12 else h + 12
    elif "mediodia" in _sin_tildes(sufijo):
        h24, franja_txt = 12, "del mediodía"
    elif "manana" in _sin_tildes(sufijo):
        h24, franja_txt = h, "de la mañana"
    elif "tarde" in _sin_tildes(sufijo):
        h24, franja_txt = (h if h >= 12 else h + 12), "de la tarde"
    elif "noche" in _sin_tildes(sufijo):
        h24, franja_txt = (h if h >= 12 else h + 12), "de la noche"
    else:
        return m.group(0)  # sin sufijo claro: no tocar
    franja = franja_txt or _franja(h24)
    palabra_h = _num(h if 1 <= h <= 29 else h24 % 12 or 12)
    if mi == 0:
        return f"{palabra_h} {franja}"
    if mi == 30:
        return f"{palabra_h} y media {franja}"
    if mi == 15:
        return f"{palabra_h} y cuarto {franja}"
    return f"{palabra_h} y {_num(mi)} {franja}"


def _rep_fecha(m: re.Match) -> str:
    dia = DIAS.get(_sin_tildes(m.group(1)), m.group(1))
    num = m.group(2)
    mes = MESES.get(_sin_tildes(m.group(3)), m.group(3))
    return f"{dia} {num} de {mes}"


# Símbolos/emoji a eliminar explícitamente
_SIMBOLOS = "🕐✓✏️★☆•·→←↑↓…✅❌⚠️📍🔊🎤⬛"

_RE_MONEDA = re.compile(r"S/\.?\s*(\d{1,3}(?:[.,]\d{3})*|\d+)(?:[.,](\d{1,2}))?")
_RE_HORA = re.compile(r"\b(\d{1,2}):(\d{2})\s*(a\.?\s*m\.?|p\.?\s*m\.?|de\s+la\s+(?:mañana|manana|tarde|noche)|del\s+mediod[ií]a)?", re.IGNORECASE)
_RE_FECHA = re.compile(r"\b(lun|mar|mié|mie|jue|vie|sáb|sab|dom)\.?\s+(\d{1,2})\s+(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)\.?", re.IGNORECASE)
_ABREV = [
    (re.compile(r"(?i)\bav(?:da)?\.?(?=\s)"), "avenida"),
    (re.compile(r"(?i)\bjr\.?(?=\s)"), "jirón"),
    (re.compile(r"(?i)\bpsje\.?(?=\s)"), "pasaje"),
    (re.compile(r"(?i)\bnro\.?"), "número"),
    (re.compile(r"N\s*[°º]"), "número"),
    (re.compile(r"(?i)\bdpto\.?"), "departamento"),
]
_RE_AMPM = re.compile(r"\b([ap])\.?\s*m\.?\b", re.IGNORECASE)
_RE_OK = re.compile(r"\bok\b", re.IGNORECASE)


def texto_para_voz(texto: str) -> str:
    t = texto or ""
    # 1) moneda y tiempo (antes de tocar símbolos)
    t = _RE_MONEDA.sub(_rep_moneda, t)
    t = _RE_FECHA.sub(_rep_fecha, t)
    t = _RE_HORA.sub(_rep_hora, t)
    # 2) abreviaturas de direcciones
    for rx, val in _ABREV:
        t = rx.sub(val, t)
    # 3) quitar emojis/símbolos
    t = "".join(ch for ch in t if ch not in _SIMBOLOS and not unicodedata.category(ch).startswith("So")
                and not unicodedata.category(ch).startswith("Sk"))
    t = t.replace("…", " ")
    # 4) tokens en inglés que hayan quedado
    t = _RE_AMPM.sub(lambda m: "de la mañana" if m.group(1).lower() == "a" else "de la tarde", t)
    t = _RE_OK.sub("listo", t)
    # 5) limpieza de espacios
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def hora_coloquial(iso: str) -> str:
    """'2026-10-13T19:00' -> '7:00 de la noche' (para mostrar en el mensaje ASAP)."""
    try:
        dt = datetime.fromisoformat(iso)
    except Exception:
        return iso
    h12 = dt.hour % 12 or 12
    return f"{h12}:{dt.minute:02d} {_franja(dt.hour)}"


def dia_coloquial(iso: str, ahora: datetime) -> str:
    """'hoy', 'mañana' o 'el martes 13 de octubre'."""
    try:
        d = datetime.fromisoformat(iso).date()
    except Exception:
        return ""
    hoy = ahora.date()
    if d == hoy:
        return "hoy"
    if d == hoy + timedelta(days=1):
        return "mañana"
    dia_sem = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][d.weekday()]
    return f"el {dia_sem} {d.day} de {MESES_LARGO[d.month]}"
