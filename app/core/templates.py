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
