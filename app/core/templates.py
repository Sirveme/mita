"""
Instancia compartida de Jinja2Templates para todo el proyecto MITA.
Uso: from app.core.templates import templates
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

# Disponible en todas las plantillas: {{ GOOGLE_MAPS_API_KEY }} (vacío si no está configurada)
try:
    from app.core.config import settings
    templates.env.globals["GOOGLE_MAPS_API_KEY"] = settings.GOOGLE_MAPS_API_KEY or ""
except Exception:
    templates.env.globals["GOOGLE_MAPS_API_KEY"] = ""


def _static_version() -> str:
    """Hash corto del commit para cache-busting de estáticos; fallback al tiempo de arranque."""
    import subprocess, os, time
    try:
        v = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                    cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    stderr=subprocess.DEVNULL, timeout=3).decode().strip()
        if v:
            return v
    except Exception:
        pass
    return os.getenv("RAILWAY_GIT_COMMIT_SHA", "")[:8] or str(int(time.time()))


STATIC_V = _static_version()
templates.env.globals["STATIC_V"] = STATIC_V
