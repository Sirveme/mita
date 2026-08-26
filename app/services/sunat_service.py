"""
Consulta de identidad (RENIEC/SUNAT) para la postulación.

Degrada con elegancia: si no hay token o la API falla, devuelve None y el
formulario continúa pidiendo el RUC manualmente. Nunca lanza excepción hacia
el endpoint.

Env:
  RENIEC_API_URL    (default: https://api.apis.net.pe/v2/reniec/dni)
  RENIEC_API_TOKEN  (bearer token de apis.net.pe)
  SUNAT_API_URL     (opcional, para consulta de RUC; default apis.net.pe v2)
"""

import os
import logging

import httpx

logger = logging.getLogger("mita.sunat")

_RENIEC_URL = os.getenv("RENIEC_API_URL", "https://api.apis.net.pe/v2/reniec/dni")
_RENIEC_TOKEN = os.getenv("RENIEC_API_TOKEN", "").strip()
_SUNAT_URL = os.getenv("SUNAT_API_URL", "https://api.apis.net.pe/v2/sunat/ruc")
_TIMEOUT = 8.0


def _headers() -> dict:
    h = {"Accept": "application/json"}
    if _RENIEC_TOKEN:
        h["Authorization"] = f"Bearer {_RENIEC_TOKEN}"
    return h


def consultar_dni(dni: str) -> dict | None:
    """Devuelve {nombres, apellido_paterno, apellido_materno} o None si no se encuentra.

    None también cuando no hay token configurado o la API falla: el flujo del
    formulario lo interpreta como "pedir RUC manualmente"."""
    dni = (dni or "").strip()
    if len(dni) != 8 or not dni.isdigit():
        return None
    if not _RENIEC_TOKEN:
        logger.info("RENIEC sin token: se omite consulta de DNI %s", dni)
        return None
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(_RENIEC_URL, params={"numero": dni}, headers=_headers())
        if r.status_code != 200:
            logger.info("RENIEC DNI %s -> HTTP %s", dni, r.status_code)
            return None
        data = r.json()
        return {
            "nombres": data.get("nombres") or data.get("name") or "",
            "apellido_paterno": data.get("apellidoPaterno") or data.get("apellido_paterno") or "",
            "apellido_materno": data.get("apellidoMaterno") or data.get("apellido_materno") or "",
        }
    except Exception as e:  # red, timeout, JSON inválido, etc.
        logger.warning("RENIEC DNI %s error: %s", dni, e)
        return None


def consultar_ruc(ruc: str) -> dict | None:
    """Consulta datos del RUC (persona natural con negocio). Opcional/degradable."""
    ruc = (ruc or "").strip()
    if len(ruc) != 11 or not ruc.isdigit():
        return None
    if not _RENIEC_TOKEN:
        return None
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(_SUNAT_URL, params={"numero": ruc}, headers=_headers())
        if r.status_code != 200:
            return None
        data = r.json()
        return {
            "razon_social": data.get("nombre") or data.get("razonSocial") or "",
            "estado": data.get("estado") or "",
            "direccion": data.get("direccion") or "",
        }
    except Exception as e:
        logger.warning("SUNAT RUC %s error: %s", ruc, e)
        return None


def ruc_contiene_dni(ruc: str, dni: str) -> bool:
    """Validación anti-fraude: el RUC de persona natural (10XXXXXXXXX) contiene el DNI."""
    ruc = (ruc or "").strip()
    dni = (dni or "").strip()
    if len(ruc) != 11 or not ruc.isdigit():
        return False
    if len(dni) != 8 or not dni.isdigit():
        return False
    return dni in ruc
