"""
Cifrado simétrico (Fernet) para datos sensibles como la clave SOL.

La llave se lee de la variable de entorno SOL_ENCRYPTION_KEY (una Fernet key
válida = 32 bytes url-safe base64). Se lee EN CADA LLAMADA (os.getenv) porque
main.py hace load_dotenv() después de importar los routers.

Política segura: si NO hay llave configurada, NO se almacena la clave en claro
(devuelve None y registra una advertencia). Con llave, cifra/descifra normal.
"""

import os
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("mita.crypto")


def _fernet() -> Fernet | None:
    key = (os.getenv("SOL_ENCRYPTION_KEY") or "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except Exception as e:
        logger.error("SOL_ENCRYPTION_KEY inválida: %s", e)
        return None


def encrypt_sol(plain: str | None) -> str | None:
    """Cifra la clave SOL. Devuelve el token cifrado, o None si no hay valor/llave."""
    if not plain:
        return None
    f = _fernet()
    if f is None:
        logger.warning("SOL_ENCRYPTION_KEY no configurada: la clave SOL NO se almacena (evita texto plano).")
        return None
    try:
        return f.encrypt(plain.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error("Error cifrando clave SOL: %s", e)
        return None


def decrypt_sol(token: str | None) -> str | None:
    """Descifra la clave SOL (usar solo cuando se necesite). None si falla."""
    if not token:
        return None
    f = _fernet()
    if f is None:
        return None
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return None
