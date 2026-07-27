from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ========================================
# CLIENTE - VISTAS HTML
# ========================================

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing principal (nueva, centrada en el problema)"""
    return templates.TemplateResponse("landing_v2.html", {"request": request})

@router.get("/cliente/registro", response_class=HTMLResponse)
async def registro_cliente(request: Request):
    return templates.TemplateResponse("cliente/registro_cliente.html", {"request": request})

@router.get("/cliente/login", response_class=HTMLResponse)
async def login_cliente(request: Request):
    return templates.TemplateResponse("cliente/login_cliente.html", {"request": request})

@router.get("/cliente/home", response_class=HTMLResponse)
async def home_cliente(request: Request):
    return templates.TemplateResponse("cliente/home_cliente.html", {"request": request})

@router.get("/cliente/buscando", response_class=HTMLResponse)
async def buscando_tecnico(request: Request):
    return templates.TemplateResponse("cliente/buscando_tecnico.html", {"request": request})

@router.get("/cliente/seguimiento", response_class=HTMLResponse)
async def seguimiento_servicio(request: Request):
    return templates.TemplateResponse("cliente/seguimiento.html", {"request": request})

# Flujo MITA v2: describe problema → categoría → técnico → dirección → chat
@router.get("/cliente/solicitar", response_class=HTMLResponse)
async def solicitar_servicio(request: Request):
    """Solicitud con selector de técnico (recibe ?problema= desde la landing)."""
    return templates.TemplateResponse("cliente/solicitar.html", {"request": request})

# Demo del chat MITA (estilo WhatsApp) — mensajes precargados + WebSocket
@router.get("/cliente/chat-demo", response_class=HTMLResponse)
async def chat_demo(request: Request):
    """Demo del chat MITA"""
    return templates.TemplateResponse("cliente/chat_demo.html", {"request": request})

# Chat estilo WhatsApp Web (2 columnas)
@router.get("/cliente/chat", response_class=HTMLResponse)
async def chat_whatsapp(request: Request):
    """Chat MITA estilo WhatsApp Web"""
    return templates.TemplateResponse("cliente/chat_whatsapp.html", {"request": request})

# ========================================
# ADMIN - PANEL (zMita-4)
# ========================================
@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Dashboard del panel admin (con sidebar)"""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "active": "dashboard"})

# ========================================
# ADMIN - MÓDULOS CRUD (zMita-3)
# ========================================
@router.get("/admin/catalogo", response_class=HTMLResponse)
async def admin_catalogo(request: Request):
    """Catálogo de servicios (categorías / tipos)"""
    return templates.TemplateResponse("admin/catalogo_servicios.html", {"request": request, "active": "catalogo"})

@router.get("/admin/personal", response_class=HTMLResponse)
async def admin_personal(request: Request):
    """Registro de personal"""
    return templates.TemplateResponse("admin/personal.html", {"request": request, "active": "personal"})

@router.get("/admin/personal/ficha", response_class=HTMLResponse)
async def ficha_personal(request: Request, id: int = None):
    """Ficha completa de un miembro del personal"""
    return templates.TemplateResponse("admin/ficha_personal.html", {"request": request, "active": "personal"})

@router.get("/admin/distritos", response_class=HTMLResponse)
async def admin_distritos(request: Request):
    """Distritos y cobertura"""
    return templates.TemplateResponse("admin/distritos.html", {"request": request, "active": "distritos"})

@router.get("/admin/configuraciones", response_class=HTMLResponse)
async def admin_configuraciones(request: Request):
    """Configuraciones del sistema"""
    return templates.TemplateResponse("admin/configuraciones.html", {"request": request, "active": "configuraciones"})

@router.get("/admin/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request):
    """Lista de usuarios del panel + reset de clave"""
    return templates.TemplateResponse("admin/usuarios.html", {"request": request, "active": "usuarios"})

# ---- Módulos aún en desarrollo (placeholder) ----
@router.get("/admin/solicitudes", response_class=HTMLResponse)
async def admin_solicitudes(request: Request):
    return templates.TemplateResponse("shared/en_desarrollo.html", {"request": request, "active": "solicitudes", "titulo": "Solicitudes", "ruta": "/admin/solicitudes"})

@router.get("/admin/ingresos", response_class=HTMLResponse)
async def admin_ingresos(request: Request):
    return templates.TemplateResponse("shared/en_desarrollo.html", {"request": request, "active": "ingresos", "titulo": "Ingresos", "ruta": "/admin/ingresos"})

@router.get("/admin/egresos", response_class=HTMLResponse)
async def admin_egresos(request: Request):
    return templates.TemplateResponse("shared/en_desarrollo.html", {"request": request, "active": "egresos", "titulo": "Egresos", "ruta": "/admin/egresos"})

@router.get("/admin/liquidaciones", response_class=HTMLResponse)
async def admin_liquidaciones(request: Request):
    return templates.TemplateResponse("shared/en_desarrollo.html", {"request": request, "active": "liquidaciones", "titulo": "Liquidaciones", "ruta": "/admin/liquidaciones"})

# ========================================
# SECRETARIA (zMita-10)
# ========================================
@router.get("/secretaria", response_class=HTMLResponse)
async def secretaria_dashboard(request: Request):
    return templates.TemplateResponse("secretaria/solicitudes.html", {"request": request, "active": "solicitudes"})

@router.get("/secretaria/solicitudes", response_class=HTMLResponse)
async def secretaria_solicitudes(request: Request):
    return templates.TemplateResponse("secretaria/solicitudes.html", {"request": request, "active": "solicitudes"})

@router.get("/secretaria/activos", response_class=HTMLResponse)
async def secretaria_activos(request: Request):
    return templates.TemplateResponse("shared/en_desarrollo.html", {"request": request, "titulo": "Servicios Activos", "ruta": "/secretaria/activos"})

@router.get("/secretaria/tecnicos", response_class=HTMLResponse)
async def secretaria_tecnicos(request: Request):
    return templates.TemplateResponse("shared/en_desarrollo.html", {"request": request, "titulo": "Técnicos", "ruta": "/secretaria/tecnicos"})

@router.get("/secretaria/historial", response_class=HTMLResponse)
async def secretaria_historial(request: Request):
    return templates.TemplateResponse("shared/en_desarrollo.html", {"request": request, "titulo": "Historial", "ruta": "/secretaria/historial"})

# Formularios específicos
@router.get("/cliente/servicio/aceite", response_class=HTMLResponse)
async def solicitud_aceite(request: Request):
    return templates.TemplateResponse("cliente/solicitud_aceite.html", {"request": request})

@router.get("/cliente/servicio/electricidad", response_class=HTMLResponse)
async def solicitud_electricidad(request: Request):
    return templates.TemplateResponse("cliente/solicitud_electricidad.html", {"request": request})

@router.get("/cliente/servicio/gasfiteria", response_class=HTMLResponse)
async def solicitud_gasfiteria(request: Request):
    return templates.TemplateResponse("cliente/solicitud_gasfiteria.html", {"request": request})

@router.get("/cliente/servicio/electrodomesticos", response_class=HTMLResponse)
async def solicitud_electrodomesticos(request: Request):
    return templates.TemplateResponse("cliente/solicitud_electrodomesticos.html", {"request": request})

# ========================================
# TÉCNICO - VISTAS HTML
# ========================================

@router.get("/tecnico/registro", response_class=HTMLResponse)
async def registro_tecnico(request: Request):
    return templates.TemplateResponse("tecnico/registro_tecnico.html", {"request": request})

@router.get("/tecnico/login", response_class=HTMLResponse)
async def login_tecnico(request: Request):
    return templates.TemplateResponse("tecnico/login_tecnico.html", {"request": request})

# ---- Panel del técnico MITA (zMita-5, layout con nav inferior) ----
@router.get("/tecnico", response_class=HTMLResponse)
async def tecnico_dashboard(request: Request):
    """Inicio del panel del técnico"""
    return templates.TemplateResponse("tecnico/dashboard.html", {"request": request, "active": "home"})

@router.get("/tecnico/servicios", response_class=HTMLResponse)
async def tecnico_servicios(request: Request):
    return templates.TemplateResponse("tecnico/servicios.html", {"request": request, "active": "servicios"})

@router.get("/tecnico/chat", response_class=HTMLResponse)
async def tecnico_chat(request: Request):
    return templates.TemplateResponse("tecnico/chat.html", {"request": request, "active": "chat"})

@router.get("/tecnico/ganancias", response_class=HTMLResponse)
async def tecnico_ganancias(request: Request):
    return templates.TemplateResponse("tecnico/ganancias.html", {"request": request, "active": "ganancias"})

@router.get("/tecnico/perfil", response_class=HTMLResponse)
async def tecnico_perfil(request: Request):
    return templates.TemplateResponse("tecnico/perfil.html", {"request": request, "active": "perfil"})

# ---- Vistas legacy del técnico (se conservan) ----
@router.get("/tecnico/panel", response_class=HTMLResponse)
async def panel_tecnico(request: Request):
    """Dashboard legacy del técnico"""
    return templates.TemplateResponse("tecnico/panel_tecnico.html", {"request": request})

@router.get("/tecnico/solicitudes", response_class=HTMLResponse)
async def solicitudes_tecnico_view(request: Request):
    """Vista de solicitudes disponibles"""
    return templates.TemplateResponse("tecnico/solicitudes.html", {"request": request})

@router.get("/tecnico/historial", response_class=HTMLResponse)
async def historial_tecnico_view(request: Request):
    """Historial de servicios completados"""
    return templates.TemplateResponse("tecnico/historial_tecnico.html", {"request": request})

# ========================================
# ADMIN - VISTAS HTML
# ========================================

@router.get("/admin/login", response_class=HTMLResponse)
async def login_admin(request: Request):
    return templates.TemplateResponse("admin/login_admin.html", {"request": request})

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_admin(request: Request):
    return templates.TemplateResponse("admin/dashboard_admin.html", {"request": request})


@router.get("/admin/gestion-insumos", response_class=HTMLResponse)
async def gestion_insumos(request: Request):
    return templates.TemplateResponse("admin/gestion_insumos.html", {"request": request})

# ========================================
# PROVEEDOR - VISTAS HTML
# ========================================

@router.get("/proveedor/login", response_class=HTMLResponse)
async def login_proveedor(request: Request):
    return templates.TemplateResponse("proveedor/login_proveedor.html", {"request": request})

@router.get("/proveedor/panel", response_class=HTMLResponse)
async def panel_proveedor(request: Request):
    return templates.TemplateResponse("proveedor/panel_proveedor.html", {"request": request})

# ========================================
# VERSIONES ALTERNATIVAS
# ========================================

@router.get("/cliente/home-v2", response_class=HTMLResponse)
async def home_cliente_v2(request: Request):
    return templates.TemplateResponse("cliente/home_cliente_v2.html", {"request": request})

@router.get("/cliente/home-v3", response_class=HTMLResponse)
async def home_cliente_v3(request: Request):
    return templates.TemplateResponse("cliente/home_cliente_v3.html", {"request": request})

@router.get("/presentacion", response_class=HTMLResponse)
async def presentacion_cliente(request: Request):
    return templates.TemplateResponse("presentacion/presentacion_cliente.html", {"request": request})



# Para el Cliente - Presentación Ingreso/Acceso de Técnicos
@router.get("/presentacion/ingreso-tecnicos", response_class=HTMLResponse)
async def presentacion_ingreso_tecnicos(request: Request):
    """Presentación del sistema de ingreso de técnicos"""
    return templates.TemplateResponse("presentacion/ingreso_tecnicos.html", {"request": request})