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
    """Página principal"""
    return templates.TemplateResponse("cliente/home_cliente.html", {"request": request})

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

# Formulario GENÉRICO MITA (carga tipos por categoría vía ?categoria=CODIGO)
@router.get("/cliente/solicitar", response_class=HTMLResponse)
async def solicitar_servicio(request: Request):
    """Formulario genérico de solicitud (4 pasos) para cualquier categoría."""
    return templates.TemplateResponse("cliente/solicitar_servicio.html", {"request": request})

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

@router.get("/tecnico/panel", response_class=HTMLResponse)
async def panel_tecnico(request: Request):
    """Dashboard principal del técnico"""
    return templates.TemplateResponse("tecnico/panel_tecnico.html", {"request": request})

@router.get("/tecnico/solicitudes", response_class=HTMLResponse)
async def solicitudes_tecnico_view(request: Request):
    """Vista de solicitudes disponibles"""
    return templates.TemplateResponse("tecnico/solicitudes.html", {"request": request})

@router.get("/tecnico/historial", response_class=HTMLResponse)
async def historial_tecnico_view(request: Request):
    """Historial de servicios completados"""
    return templates.TemplateResponse("tecnico/historial_tecnico.html", {"request": request})

@router.get("/tecnico/ganancias", response_class=HTMLResponse)
async def ganancias_tecnico_view(request: Request):
    """Vista de ganancias y finanzas"""
    return templates.TemplateResponse("tecnico/ganancias_tecnico.html", {"request": request})

@router.get("/tecnico/perfil", response_class=HTMLResponse)
async def perfil_tecnico_view(request: Request):
    """Perfil del técnico"""
    return templates.TemplateResponse("tecnico/perfil_tecnico.html", {"request": request})

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