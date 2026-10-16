"""
Privacidad del chat (zMita-38, Parte B): ocultar celulares peruanos y correos para que el
contacto quede dentro de MITA. Devuelve (texto_limpio, se_oculto_algo).
"""
import re

REEMPLAZO = "[dato oculto: usa el chat de MITA]"

# Celular peruano: 9 dígitos que empiezan con 9, con o sin +51 y con espacios/guiones/puntos.
_RE_TEL = re.compile(r"(?:\+?51[\s.\-]*)?9(?:[\s.\-]*\d){8}")
_RE_MAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.IGNORECASE)


def ocultar_datos(texto: str):
    t = texto or ""
    oculto = False
    if _RE_MAIL.search(t):
        t = _RE_MAIL.sub(REEMPLAZO, t); oculto = True
    if _RE_TEL.search(t):
        t = _RE_TEL.sub(REEMPLAZO, t); oculto = True
    return t, oculto
