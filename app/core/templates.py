"""
Instancia compartida de Jinja2Templates para todo el proyecto MITA.
Uso: from app.core.templates import templates
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
