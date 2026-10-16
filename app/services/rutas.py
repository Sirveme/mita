"""
ETA técnico -> cliente (zMita-37, Parte B). Google Routes API (computeRoutes, DRIVE con
tráfico) usando GOOGLE_MAPS_SERVER_KEY. Sin clave o si falla: línea recta × 1.4 a 20 km/h,
marcado como aprox. Cache por (origen,destino) 2 min.
"""
import os
import time
import math
import logging

from app.core.config import settings

logger = logging.getLogger("mita.rutas")

_CACHE = {}   # clave -> (ts, dict)
_TTL = 120


def _key(olat, olng, dlat, dlng):
    return f"{round(olat,4)},{round(olng,4)}->{round(dlat,4)},{round(dlng,4)}"


def _recta_km(olat, olng, dlat, dlng):
    R = 6371.0
    dla = math.radians(dlat - olat)
    dlo = math.radians(dlng - olng)
    a = (math.sin(dla / 2) ** 2 +
         math.cos(math.radians(olat)) * math.cos(math.radians(dlat)) * math.sin(dlo / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _aprox(olat, olng, dlat, dlng):
    km = _recta_km(olat, olng, dlat, dlng) * 1.4   # factor calle
    minutos = max(1, round(km / 20.0 * 60))        # 20 km/h
    return {"metros": int(km * 1000), "minutos": minutos, "aprox": True}


def eta(olat, olng, dlat, dlng) -> dict:
    """Devuelve {metros, minutos, aprox}. Nunca lanza."""
    try:
        olat, olng, dlat, dlng = float(olat), float(olng), float(dlat), float(dlng)
    except (TypeError, ValueError):
        return None
    k = _key(olat, olng, dlat, dlng)
    hit = _CACHE.get(k)
    if hit and (time.time() - hit[0] < _TTL):
        return hit[1]

    key = settings.GOOGLE_MAPS_SERVER_KEY or os.getenv("GOOGLE_MAPS_SERVER_KEY")
    if not key:
        out = _aprox(olat, olng, dlat, dlng)
        _CACHE[k] = (time.time(), out)
        return out
    try:
        import httpx
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {"Content-Type": "application/json", "X-Goog-Api-Key": key,
                   "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"}
        body = {
            "origin": {"location": {"latLng": {"latitude": olat, "longitude": olng}}},
            "destination": {"location": {"latLng": {"latitude": dlat, "longitude": dlng}}},
            "travelMode": "DRIVE", "routingPreference": "TRAFFIC_AWARE",
        }
        r = httpx.post(url, headers=headers, json=body, timeout=6)
        data = r.json()
        rutas = data.get("routes") or []
        if r.status_code == 200 and rutas:
            dur = rutas[0].get("duration", "0s")
            seg = int(str(dur).rstrip("s") or 0)
            metros = int(rutas[0].get("distanceMeters") or 0)
            out = {"metros": metros, "minutos": max(1, round(seg / 60)), "aprox": False}
        else:
            logger.warning("[rutas] computeRoutes status=%s", r.status_code)
            out = _aprox(olat, olng, dlat, dlng)
    except Exception as e:
        logger.warning("[rutas] error, uso aprox: %s", e)
        out = _aprox(olat, olng, dlat, dlng)
    _CACHE[k] = (time.time(), out)
    return out
