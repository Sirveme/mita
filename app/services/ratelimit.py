"""
Rate limiting en memoria (zMita-40, Parte A4). Ventana deslizante por clave.

Por proceso (suficiente para frenar abuso desde una IP/número). Para los flujos de dinero,
la protección fuerte vive en pagook (advisory locks, una consulta en vuelo). Aquí frenamos
fuerza bruta en OTP, login, chat y la vigilancia de /pagar.
"""
import time
import threading
from collections import deque
from fastapi import HTTPException

_LOCK = threading.Lock()
_HITS = {}   # clave -> deque[timestamps]


def _ip(request) -> str:
    try:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request and request.client else "?"
    except Exception:
        return "?"


def permitido(clave: str, limite: int, ventana_seg: float) -> bool:
    """True si la acción está bajo el límite (y la registra); False si lo excede."""
    ahora = time.time()
    with _LOCK:
        dq = _HITS.get(clave)
        if dq is None:
            dq = deque(); _HITS[clave] = dq
        while dq and (ahora - dq[0]) > ventana_seg:
            dq.popleft()
        if len(dq) >= limite:
            return False
        dq.append(ahora)
        return True


def exigir(request, bucket: str, limite: int, ventana_seg: float, extra: str = ""):
    """Lanza 429 si se excede el límite para (bucket, IP[, extra])."""
    clave = f"{bucket}:{_ip(request)}" + (f":{extra}" if extra else "")
    if not permitido(clave, limite, ventana_seg):
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.")
