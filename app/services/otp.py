"""
Verificación de celular por código (OTP) — zMita-39, Parte A.

- Código de 6 dígitos, vence en 5 min (config otp_vigencia_seg).
- Máximo 3 envíos por número por hora (otp_max_envios_hora) y 5 intentos por código (otp_max_intentos).
- Sin proveedor de SMS: no bloquea; devuelve estado 'no_verificado' y la torre lo ve marcado.
"""
import logging
import random
from datetime import datetime, timedelta

from app.models.cierre import CodigoVerificacion
from app.services import sms
from app.services.config_service import ConfigService

logger = logging.getLogger("mita.otp")


def _cfg(db, clave, defecto):
    try:
        return int(ConfigService.get(db, clave, defecto) or defecto)
    except Exception:
        return defecto


def _normaliza(celular: str) -> str:
    return "".join(ch for ch in (celular or "") if ch.isdigit())[-9:]


def enviar_codigo(db, celular: str) -> dict:
    """Genera y envía un código. Devuelve {ok, estado, sin_proveedor?, espera_seg?, mensaje}."""
    cel = _normaliza(celular)
    if len(cel) != 9 or not cel.startswith("9"):
        return {"ok": False, "estado": "pendiente", "mensaje": "Celular peruano inválido (9 dígitos, empieza con 9)."}

    # Sin proveedor: no bloquear el flujo
    if not sms.hay_proveedor():
        logger.info("[otp] sin proveedor: %s queda no_verificado", cel)
        return {"ok": True, "estado": "no_verificado", "sin_proveedor": True,
                "mensaje": "No pudimos enviar el SMS (sin proveedor). Puedes continuar; quedará sin verificar."}

    # Límite de envíos por hora
    max_envios = _cfg(db, "otp_max_envios_hora", 3)
    hace_una_hora = datetime.utcnow() - timedelta(hours=1)
    envios = (db.query(CodigoVerificacion)
              .filter(CodigoVerificacion.celular == cel, CodigoVerificacion.created_at >= hace_una_hora)
              .count())
    if envios >= max_envios:
        return {"ok": False, "estado": "pendiente",
                "mensaje": f"Demasiados intentos. Espera una hora e inténtalo de nuevo."}

    vigencia = _cfg(db, "otp_vigencia_seg", 300)
    codigo = f"{random.randint(0, 999999):06d}"
    cv = CodigoVerificacion(celular=cel, codigo=codigo,
                            expira_en=datetime.utcnow() + timedelta(seconds=vigencia),
                            enviado_por=(sms.settings.SMS_PROVEEDOR or "sms"))
    db.add(cv); db.commit()
    sms.enviar_sms(cel, f"Tu código MITA es {codigo}. Vence en {vigencia // 60} min.")
    return {"ok": True, "estado": "pendiente", "mensaje": "Te enviamos un código por SMS."}


def verificar_codigo(db, celular: str, codigo: str) -> dict:
    """Verifica el último código vigente. Devuelve {ok, estado, mensaje}."""
    cel = _normaliza(celular)
    cv = (db.query(CodigoVerificacion)
          .filter(CodigoVerificacion.celular == cel, CodigoVerificacion.usado.is_(False))
          .order_by(CodigoVerificacion.id.desc()).first())
    if not cv:
        return {"ok": False, "estado": "pendiente", "mensaje": "Pide un código primero."}
    if datetime.utcnow() > cv.expira_en:
        return {"ok": False, "estado": "pendiente", "mensaje": "El código venció. Pide uno nuevo."}
    max_intentos = _cfg(db, "otp_max_intentos", 5)
    if (cv.intentos or 0) >= max_intentos:
        return {"ok": False, "estado": "pendiente", "mensaje": "Demasiados intentos. Pide un código nuevo."}
    if (codigo or "").strip() != cv.codigo:
        cv.intentos = (cv.intentos or 0) + 1
        db.commit()
        restan = max_intentos - cv.intentos
        return {"ok": False, "estado": "pendiente",
                "mensaje": f"Código incorrecto. Te quedan {max(restan, 0)} intentos."}
    cv.usado = True
    db.commit()
    return {"ok": True, "estado": "verificado", "mensaje": "Celular verificado."}
