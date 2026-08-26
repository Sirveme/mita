"""
Consulta de identidad DNI (RENIEC) y RUC (SUNAT) para la postulación.

Replica la configuración de los proyectos hermanos Facturalo.pro y QueVendi.pro
(cliente Bearer contra apis.net.pe / decolecta.com). El token, base y referer se
leen EN CADA LLAMADA desde el entorno vivo (os.environ) — no como constantes de
módulo — porque main.py hace load_dotenv() DESPUÉS de importar los routers, así
que un snapshot al import quedaría vacío. Mismo patrón que Facturalo._token().

Degrada con elegancia: ante cualquier fallo (sin token, 401, red, JSON inválido)
devuelve None y el formulario continúa pidiendo/validando el RUC manualmente.

Env (ver .env):
  APIS_NET_PE_TOKEN   token Bearer (decolecta 'sk_...' o apis.net.pe 'apis-token-...')
  APIS_NET_BASE       base URL (default https://api.decolecta.com)
  APIS_NET_REFERER    header Referer (default https://mita.pe)
  RENIEC_API_TOKEN    fallback del token (compat con config previa de MITA)
"""

import os
import logging

import httpx

logger = logging.getLogger("mita.sunat")

_TIMEOUT = 10.0
_DEFAULT_BASE = "https://api.decolecta.com"


def _token() -> str:
    return (os.environ.get("APIS_NET_PE_TOKEN") or os.environ.get("RENIEC_API_TOKEN") or "").strip()


def _base() -> str:
    return (os.environ.get("APIS_NET_BASE") or _DEFAULT_BASE).strip().rstrip("/")


def _referer() -> str:
    return (os.environ.get("APIS_NET_REFERER") or "https://mita.pe").strip()


def _paths(base: str) -> tuple[str, str]:
    """Devuelve (dni_path, ruc_path) según el proveedor (v1 decolecta / v2 apis.net.pe)."""
    if "apis.net" in base:
        return "/v2/reniec/dni", "/v2/sunat/ruc"
    # decolecta u otros -> v1
    return "/v1/reniec/dni", "/v1/sunat/ruc"


def _get(path: str, numero: str) -> dict | None:
    token = _token()
    if not token:
        logger.info("APIS_NET_PE_TOKEN no configurado: se omite consulta %s", path)
        return None
    base = _base()
    url = f"{base}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Referer": _referer(),
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(url, params={"numero": numero}, headers=headers)
        if r.status_code != 200:
            logger.info("%s numero=%s -> HTTP %s: %s", path, numero, r.status_code, r.text[:160])
            return None
        return r.json()
    except Exception as e:  # red, timeout, JSON inválido
        logger.warning("%s numero=%s error: %s", path, numero, e)
        return None


def _split_nombre(nombre: str) -> dict:
    """Divide 'APE_PAT APE_MAT NOMBRES...' (formato SUNAT/RENIEC persona natural)."""
    partes = (nombre or "").split()
    if len(partes) >= 3:
        return {"apellido_paterno": partes[0], "apellido_materno": partes[1], "nombres": " ".join(partes[2:])}
    if len(partes) == 2:
        return {"apellido_paterno": partes[0], "apellido_materno": "", "nombres": partes[1]}
    return {"apellido_paterno": "", "apellido_materno": "", "nombres": nombre or ""}


def consultar_dni(dni: str) -> dict | None:
    """Devuelve {nombres, apellido_paterno, apellido_materno} o None si no se encuentra.

    Soporta ambos esquemas de respuesta:
      - decolecta (snake_case): first_name, first_last_name, second_last_name, full_name
      - apis.net.pe v2 (camelCase): nombres, apellidoPaterno, apellidoMaterno"""
    dni = (dni or "").strip()
    if len(dni) != 8 or not dni.isdigit():
        return None
    dni_path, _ = _paths(_base())
    data = _get(dni_path, dni)
    if not data:
        return None

    nombres = data.get("nombres") or data.get("first_name") or ""
    ap_pat = data.get("apellidoPaterno") or data.get("first_last_name") or ""
    ap_mat = data.get("apellidoMaterno") or data.get("second_last_name") or ""

    # Si el proveedor solo trae el nombre completo, lo dividimos
    if not (nombres or ap_pat):
        full = data.get("full_name") or data.get("nombreCompleto") or data.get("nombre") or ""
        if not full:
            return None
        return _split_nombre(full)

    return {"nombres": nombres.strip(), "apellido_paterno": ap_pat.strip(), "apellido_materno": ap_mat.strip()}


def consultar_ruc(ruc: str) -> dict | None:
    """Consulta un RUC. Devuelve razon_social + nombres/apellidos parseados, o None.

    Para persona natural (RUC 10#########), razon_social suele ser 'APE_PAT APE_MAT NOMBRES'."""
    ruc = (ruc or "").strip()
    if len(ruc) != 11 or not ruc.isdigit():
        return None
    _, ruc_path = _paths(_base())
    data = _get(ruc_path, ruc)
    if not data:
        return None

    razon = data.get("razon_social") or data.get("razonSocial") or data.get("nombre") or ""
    if not razon:
        return None
    out = {
        "razon_social": razon.strip(),
        "estado": (data.get("estado") or "").strip(),
        "condicion": (data.get("condicion") or "").strip(),
        "direccion": (data.get("direccion") or "").strip(),
    }
    out.update(_split_nombre(razon))
    return out


def ruc_contiene_dni(ruc: str, dni: str) -> bool:
    """Validación anti-fraude: el RUC de persona natural (10XXXXXXXXX) contiene el DNI."""
    ruc = (ruc or "").strip()
    dni = (dni or "").strip()
    if len(ruc) != 11 or not ruc.isdigit():
        return False
    if len(dni) != 8 or not dni.isdigit():
        return False
    return dni in ruc
