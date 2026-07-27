from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.core.config import settings

# Importar routers existentes
from app.routes.main import router as main_router
from app.routes.tecnicos import router as tecnicos_router
from app.routes.insumos import router as insumos_router

# Importar nuevos routers de autenticación y WebSocket
from app.routes.auth import router as auth_router
from app.routes.websocket import router as websocket_router
from app.routes.chat import router as chat_router
from app.routes.notificaciones import router as notificaciones_router
from app.routes.pagos import router as pagos_router
from app.routes.solicitudes import router as solicitudes_router
from app.routes.recomendaciones import router as recomendaciones_router
from app.routes.servicios import router as servicios_router

# Nuevos routers MITA (chat en tiempo real)
from app.routes.chat_ws import router as chat_ws_router
from app.routes.chat_mita import router as chat_mita_router

# Router de administración (CRUD)
from app.routes.admin_api import router as admin_api_router

# Login del panel (DNI + cookie de sesión) — archivo nuevo, no toca auth.py (JWT)
from app.routes.login_mita import router as login_mita_router

# APIs del flujo MITA v2 (selector de técnicos + crear solicitud)
from app.routes.tecnicos_api import router as tecnicos_api_router
from app.routes.solicitudes_api import router as solicitudes_api_router

# API de billeteras electrónicas del personal
from app.routes.billeteras_api import router as billeteras_api_router

from dotenv import load_dotenv
load_dotenv()

# ============================================
# LIFESPAN - Reemplaza on_event (startup/shutdown)
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager para manejar startup y shutdown
    """
    # STARTUP - Se ejecuta al iniciar la app
    print("=" * 60)
    print("🚀 MITA API iniciando...")
    print(f"📍 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    print(f"🔐 JWT expiration: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    print(f"🔄 Refresh token: {settings.REFRESH_TOKEN_EXPIRE_DAYS} days")
    print(f"🌐 Host: {settings.HOST}:{settings.PORT}")
    print("=" * 60)
    
    # Aquí puedes agregar:
    # - Conexión a base de datos
    # - Inicialización de Redis
    # - Carga de modelos ML
    # - etc.
    
    yield  # La app se ejecuta aquí
    
    # SHUTDOWN - Se ejecuta al cerrar la app
    print("=" * 60)
    print("👋 MITA API cerrando...")
    print("🔒 Limpiando recursos...")
    print("=" * 60)
    
    # Aquí puedes agregar:
    # - Cerrar conexiones a BD
    # - Cerrar conexiones Redis
    # - Guardar logs finales
    # - etc.


# ============================================
# CREAR APP CON LIFESPAN
# ============================================

app = FastAPI(
    title="MITA API",
    description="API para plataforma de servicios a domicilio",
    version="1.0.0",
    lifespan=lifespan  # <-- NUEVO: Usar lifespan en lugar de on_event
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# ============================================
# REGISTRAR ROUTERS
# ============================================

# Vistas HTML principales
app.include_router(main_router)

# API - Autenticación
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])

# API - WebSocket
app.include_router(websocket_router, prefix="/api/v1", tags=["WebSocket"])

# API - Chat
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])

# API - Notificaciones
app.include_router(notificaciones_router, prefix="/api/v1", tags=["Notificaciones"])

# API - Pagos (Culqi)
app.include_router(pagos_router, tags=["Pagos"])

# API - Técnicos (existente)
app.include_router(tecnicos_router)

# API - Solicitudes de Servicio
app.include_router(solicitudes_router, prefix="/api/v1", tags=["Solicitudes"])

app.include_router(insumos_router, prefix="/api/v1/admin", tags=["Insumos"])

app.include_router(recomendaciones_router, prefix="/api/v1", tags=["Recomendaciones"])

app.include_router(servicios_router, prefix="/api/v1", tags=["Servicios"])

# Chat MITA - WebSocket (tiempo real) + REST (historial/persistencia)
app.include_router(chat_ws_router, tags=["Chat WS"])
app.include_router(chat_mita_router, prefix="/api/v1", tags=["Chat"])

# Admin API - CRUD (el router ya define su prefix /api/v1/admin)
app.include_router(admin_api_router)

# Login del panel MITA (DNI + cookie de sesión) — dueño de /login, /logout
app.include_router(login_mita_router)

# Flujo MITA v2 (los routers ya definen su prefix /api/v1/...)
app.include_router(tecnicos_api_router)
app.include_router(solicitudes_api_router)
app.include_router(billeteras_api_router)

# Cuando estén listos:
# from app.routes.clientes import router as clientes_router
# from app.routes.servicios import router as servicios_router
# app.include_router(clientes_router)
# app.include_router(servicios_router)



# NOTA: GET/POST /login y /logout los sirve ahora app.routes.login_mita
# (login por DNI + cookie de sesión). Se retiró el handler inline anterior
# que servía login.html para evitar la ruta duplicada.

# ============================================
# RUTAS HTML - ADMIN
# ============================================

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Página de login para administradores"""
    return templates.TemplateResponse("admin/login.html", {"request": request})

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    """Dashboard principal de administración"""
    return templates.TemplateResponse("admin/dashboard_admin.html", {"request": request})

@app.get("/admin/tecnicos", response_class=HTMLResponse)
async def admin_tecnicos_page(request: Request):
    """Gestión de técnicos"""
    return templates.TemplateResponse("admin/gestion_tecnicos.html", {"request": request})

# ============================================
# RUTAS HTML - TÉCNICO
# ============================================

@app.get("/tecnico/panel", response_class=HTMLResponse)
async def tecnico_panel_page(request: Request):
    """Panel principal del técnico"""
    return templates.TemplateResponse("tecnico/panel_tecnico.html", {"request": request})

@app.get("/tecnico/historial", response_class=HTMLResponse)
async def tecnico_historial_page(request: Request):
    """Historial de servicios del técnico"""
    return templates.TemplateResponse("tecnico/historial_tecnico.html", {"request": request})

@app.get("/tecnico/ganancias", response_class=HTMLResponse)
async def tecnico_ganancias_page(request: Request):
    """Ganancias del técnico"""
    return templates.TemplateResponse("tecnico/ganancias_tecnico.html", {"request": request})

@app.get("/tecnico/perfil", response_class=HTMLResponse)
async def tecnico_perfil_page(request: Request):
    """Perfil del técnico"""
    return templates.TemplateResponse("tecnico/perfil_tecnico.html", {"request": request})


# ============================================
# RUTAS HTML - CLIENTE
# ============================================

@app.get("/cliente/solicitud-aceite", response_class=HTMLResponse)
async def cliente_solicitud_aceite_page(request: Request):
    """Solicitud de servicio de cambio de aceite"""
    return templates.TemplateResponse("cliente/solicitud_aceite.html", {"request": request})

@app.get("/cliente/calendario-horarios", response_class=HTMLResponse)
async def cliente_calendario_horarios_page(request: Request):
    """Selección de fecha y hora del servicio"""
    return templates.TemplateResponse("cliente/calendario_horarios.html", {"request": request})

@app.get("/cliente/metodos-pago", response_class=HTMLResponse)
async def cliente_metodos_pago_page(request: Request):
    """Selección de método de pago"""
    return templates.TemplateResponse("cliente/metodos_pago.html", {"request": request})

@app.get("/cliente/buscando-mecanico", response_class=HTMLResponse)
async def cliente_buscando_mecanico_page(request: Request):
    """Pantalla de búsqueda de mecánico"""
    return templates.TemplateResponse("cliente/buscando_mecanico.html", {"request": request})

@app.get("/cliente/mecanico-asignado", response_class=HTMLResponse)
async def cliente_mecanico_asignado_page(request: Request):
    """Pantalla de mecánico asignado"""
    return templates.TemplateResponse("cliente/mecanico_asignado.html", {"request": request})

@app.get("/cliente/seguimiento", response_class=HTMLResponse)
async def cliente_seguimiento_page(request: Request):
    """Seguimiento del servicio"""
    return templates.TemplateResponse("cliente/seguimiento.html", {"request": request})



# ============================================
# RUTAS HTML - ADMIN
# ============================================

@app.get("/admin/confirmacion-pagos", response_class=HTMLResponse)
async def admin_confirmacion_pagos_page(request: Request):
    return templates.TemplateResponse("admin/confirmacion_pagos.html", {"request": request})


# ============================================
# RUTAS HTML - CHAT
# ============================================

@app.get("/chat/{servicio_id}", response_class=HTMLResponse)
async def chat_servicio_page(request: Request, servicio_id: int):
    """Chat de un servicio específico"""
    return templates.TemplateResponse(
        "chat/chat_servicio.html",
        {
            "request": request,
            "servicio_id": servicio_id
        }
    )

# ============================================
# HEALTH CHECKS
# ============================================

@app.get("/health")
async def health_check():
    """Endpoint de salud del sistema"""
    return {
        "status": "healthy",
        "service": "MITA API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/api")
async def api_info():
    """Información de la API"""
    return {
        "name": "MITA API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
            "views": "/",
            "auth": {
                "login": "/api/v1/auth/login",
                "register": "/api/v1/auth/register",
                "refresh": "/api/v1/auth/refresh",
                "me": "/api/v1/auth/me"
            },
            "websocket": "/api/v1/ws/notificaciones",
            "chat": "/api/v1/chat",
            "notificaciones": "/api/v1/notificaciones",
            "tecnicos": "/api/tecnicos",
            "admin": {
                "login": "/admin/login",
                "dashboard": "/admin/dashboard",
                "tecnicos": "/admin/tecnicos"
            },
            "tecnico": {
                "panel": "/tecnico/panel",
                "historial": "/tecnico/historial",
                "ganancias": "/tecnico/ganancias",
                "perfil": "/tecnico/perfil"
            }
        }
    }

@app.get("/")
async def root():
    """Ruta raíz"""
    return {
        "message": "Bienvenido a MITA API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api_info": "/api"
    }




@app.get("/manifest.json")
async def manifest():
    """Servir manifest.json"""
    return FileResponse("app/static/manifest.json", media_type="application/json")

@app.get("/sw.js")
async def service_worker():
    """Servir service worker"""
    return FileResponse("app/sw.js", media_type="application/javascript")

@app.get("/offline.html", response_class=HTMLResponse)
async def offline_page(request: Request):
    """Página offline"""
    return templates.TemplateResponse("offline.html", {"request": request})