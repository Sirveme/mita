from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ========== CLIENTE ==========
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página principal - redirecciona al home del cliente"""
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

# ========== TÉCNICO ==========
@router.get("/tecnico/registro", response_class=HTMLResponse)
async def registro_tecnico(request: Request):
    return templates.TemplateResponse("tecnico/registro_tecnico.html", {"request": request})

@router.get("/tecnico/login", response_class=HTMLResponse)
async def login_tecnico(request: Request):
    return templates.TemplateResponse("tecnico/login_tecnico.html", {"request": request})

@router.get("/tecnico/panel", response_class=HTMLResponse)
async def panel_tecnico(request: Request):
    return templates.TemplateResponse("tecnico/panel_tecnico.html", {"request": request})

# ========== ADMIN ==========
@router.get("/admin/login", response_class=HTMLResponse)
async def login_admin(request: Request):
    return templates.TemplateResponse("admin/login_admin.html", {"request": request})

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_admin(request: Request):
    return templates.TemplateResponse("admin/dashboard_admin.html", {"request": request})

# ========== PROVEEDOR ==========
@router.get("/proveedor/login", response_class=HTMLResponse)
async def login_proveedor(request: Request):
    return templates.TemplateResponse("proveedor/login_proveedor.html", {"request": request})

@router.get("/proveedor/panel", response_class=HTMLResponse)
async def panel_proveedor(request: Request):
    return templates.TemplateResponse("proveedor/panel_proveedor.html", {"request": request})


# ========== SERVICIOS CLIENTE - RUTAS ESPECÍFICAS ==========
@router.get("/cliente/servicio/aceite", response_class=HTMLResponse)
async def solicitud_aceite(request: Request):
    """Formulario específico para cambio de aceite"""
    return templates.TemplateResponse("cliente/solicitud_aceite.html", {"request": request})

@router.get("/cliente/servicio/electricidad", response_class=HTMLResponse)
async def solicitud_electricidad(request: Request):
    """Formulario específico para servicios eléctricos"""
    return templates.TemplateResponse("cliente/solicitud_electricidad.html", {"request": request})

@router.get("/cliente/servicio/gasfiteria", response_class=HTMLResponse)
async def solicitud_gasfiteria(request: Request):
    """Formulario específico para gasfitería"""
    return templates.TemplateResponse("cliente/solicitud_gasfiteria.html", {"request": request})

@router.get("/cliente/servicio/electrodomesticos", response_class=HTMLResponse)
async def solicitud_electrodomesticos(request: Request):
    """Formulario específico para electrodomésticos"""
    return templates.TemplateResponse("cliente/solicitud_electrodomesticos.html", {"request": request})

@router.get("/cliente/seguimiento", response_class=HTMLResponse)
async def seguimiento_servicio(request: Request):
    return templates.TemplateResponse("cliente/seguimiento.html", {"request": request})


# ========== VERSIONES ALTERNATIVAS ==========
@router.get("/cliente/home-v2", response_class=HTMLResponse)
async def home_cliente_v2(request: Request):
    return templates.TemplateResponse("cliente/home_cliente_v2.html", {"request": request})

@router.get("/cliente/home-v3", response_class=HTMLResponse)
async def home_cliente_v3(request: Request):
    return templates.TemplateResponse("cliente/home_cliente_v3.html", {"request": request})

# ========== SUSTENTO DE LOS 3 DISEÑOS PROPUESTOS ==========
@router.get("/presentacion", response_class=HTMLResponse)
async def presentacion_cliente(request: Request):
    return templates.TemplateResponse("presentacion/presentacion_cliente.html", {"request": request})