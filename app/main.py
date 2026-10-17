from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

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

# zMita-13: calificaciones + asignación automática
from app.routes.calificaciones_api import router as calificaciones_api_router
from app.routes.asignacion_api import router as asignacion_api_router

# zMita-14: API del cliente (pendientes de calificar)
from app.routes.cliente_api import router as cliente_api_router
from app.routes.postulacion import router as postulacion_router
from app.routes.admin_postulantes import router as admin_postulantes_router
from app.routes.soporte import router as soporte_router
from app.routes.waitlist import router as waitlist_router
from app.routes.comprobantes_api import router as comprobantes_router
from app.routes.pagos_api import router as pagos_api_router
from app.routes.areas_api import router as areas_api_router
from app.routes.chat_api import router as chat_api_router
from app.routes.tecnico_api import router as tecnico_api_router
from app.routes.reset_password_api import router as reset_password_api_router
from app.routes.ubicacion_api import router as ubicacion_api_router
from app.routes.maps_api import router as maps_api_router
from app.routes.chat_ia_api import router as chat_ia_router
from app.routes.push_api import router as push_router
from app.routes.pagook_api import router as pagook_router
from app.routes.ofertas_api import router as ofertas_router
from app.routes.servicio_api import router as servicio_router

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

    # Seguridad (zMita-40, A2): en producción el shim de demo debe estar apagado.
    from app.core.security import es_produccion
    if es_produccion() and settings.DEMO_AUTH:
        raise RuntimeError(
            "DEMO_AUTH está activo en producción. El shim de autenticación de demostración "
            "no puede usarse en producción: apágalo (DEMO_AUTH=false) para arrancar."
        )

    # Asegurar la tabla de suscripciones push (idempotente). En Railway los SQL de
    # app/sql/ NO se corren solos al desplegar (hay que ejecutar setup_railway a mano),
    # así que garantizamos aquí que push_suscripciones exista para los avisos.
    try:
        import os as _os
        from app.core.database import engine
        from app.models.push_suscripcion import PushSuscripcion, PushEnvio
        PushSuscripcion.__table__.create(bind=engine, checkfirst=True)
        PushEnvio.__table__.create(bind=engine, checkfirst=True)
        # Columnas nuevas (dispositivo_id, ultimo_*, solicitudes.canal_avisos): el ORM ya las
        # usa, pero ALTER no lo hace create_all. Aplicar la migración 30 (idempotente) al arrancar.
        from app.models.pago_solicitud import PagoSolicitud
        from app.models.oferta_servicio import OfertaServicio
        from app.models.servicio_vivo import UbicacionServicio, MensajeServicio, Presupuesto
        from app.models.cierre import CodigoVerificacion, CompradorPreferido, ComprobanteEmitido, CobroEfectivo
        from app.models.liquidacion_mita import LiquidacionMita, LiquidacionItem, ConfiguracionHistorial
        PagoSolicitud.__table__.create(bind=engine, checkfirst=True)
        OfertaServicio.__table__.create(bind=engine, checkfirst=True)
        for _m in (UbicacionServicio, MensajeServicio, Presupuesto,
                   CodigoVerificacion, CompradorPreferido, ComprobanteEmitido, CobroEfectivo,
                   LiquidacionMita, LiquidacionItem, ConfiguracionHistorial):
            _m.__table__.create(bind=engine, checkfirst=True)
        for nombre in ("30_push_envios_canal.sql", "31_pagos_solicitud.sql", "32_pagos_voucher.sql",
                       "33_ofertas_servicio.sql", "34_servicio_vivo.sql", "35_cierre_identificacion.sql",
                       "36_pago_concepto.sql", "37_comprobante_sunat.sql", "38_liquidacion.sql", "39_umbral_boleta.sql", "40_pago_qr_titular.sql"):
            sqlf = _os.path.join(_os.path.dirname(__file__), "sql", nombre)
            if _os.path.exists(sqlf):
                with open(sqlf, encoding="utf-8") as f, engine.begin() as conn:
                    conn.exec_driver_sql(f.read())
        print("✅ Avisos/pagos: tablas y columnas verificadas (push + canal_avisos + pagos_solicitud)")
    except Exception as e:
        print(f"⚠️  No se pudieron verificar las tablas/columnas de avisos/pagos: {e}")

    # Cron de reasignación por timeout de respuesta de técnico
    try:
        from app.tasks.timeout_tecnico import iniciar_scheduler
        iniciar_scheduler()
    except Exception as e:
        print(f"⚠️  No se pudo iniciar el cron de timeouts: {e}")

    # Tarea de fondo de tiempos de ofertas (zMita-38, con advisory lock para multi-worker)
    try:
        from app.tasks.tiempos import iniciar as iniciar_tiempos
        iniciar_tiempos()
    except Exception as e:
        print(f"⚠️  No se pudo iniciar la tarea de tiempos: {e}")

    # Tarea de fondo de comprobantes: reconsulta el CDR de SUNAT (zMita-41)
    try:
        from app.tasks.comprobantes import iniciar as iniciar_comprobantes
        iniciar_comprobantes()
    except Exception as e:
        print(f"⚠️  No se pudo iniciar la tarea de comprobantes: {e}")

    yield  # La app se ejecuta aquí

    # SHUTDOWN - Se ejecuta al cerrar la app
    print("=" * 60)
    print("👋 MITA API cerrando...")
    print("🔒 Limpiando recursos...")
    print("=" * 60)
    try:
        from app.tasks.timeout_tecnico import detener_scheduler
        await detener_scheduler()
    except Exception:
        pass
    
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


# ============================================
# PWA: inyectar <link manifest> + pwa.js en TODAS las páginas HTML (zMita-33)
# Evita editar decenas de plantillas. No toca JSON ni estáticos.
# ============================================
_APPLE_TAGS = (
    '<link rel="apple-touch-icon" href="/static/img/mita/icon-180.png">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-title" content="MITA">'
)
_PWA_SCRIPT = '<script defer src="/static/js/pwa.js?v=33"></script>'


class PWAHeadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        ctype = response.headers.get("content-type", "")
        if request.method != "GET" or "text/html" not in ctype:
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            text = body.decode("utf-8")
        except Exception:
            return StarletteResponse(content=body, status_code=response.status_code,
                                     headers=dict(response.headers), media_type=ctype)
        if "</head>" in text and "/static/js/pwa.js" not in text:
            extra = ""
            if 'rel="manifest"' not in text:
                extra += '<link rel="manifest" href="/manifest.webmanifest">'
            if 'name="theme-color"' not in text:
                extra += '<meta name="theme-color" content="#12101a">'
            extra += _APPLE_TAGS + _PWA_SCRIPT
            text = text.replace("</head>", extra + "</head>", 1)
        data = text.encode("utf-8")
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return StarletteResponse(content=data, status_code=response.status_code,
                                 headers=headers, media_type=ctype)


app.add_middleware(PWAHeadMiddleware)

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
app.include_router(calificaciones_api_router)
app.include_router(asignacion_api_router)
app.include_router(cliente_api_router)
app.include_router(postulacion_router)
app.include_router(admin_postulantes_router)
app.include_router(soporte_router)
app.include_router(waitlist_router)
app.include_router(comprobantes_router)
app.include_router(pagos_api_router)
app.include_router(areas_api_router)
app.include_router(chat_api_router)
app.include_router(tecnico_api_router)
app.include_router(reset_password_api_router)
app.include_router(ubicacion_api_router)
app.include_router(maps_api_router)
app.include_router(chat_ia_router)
app.include_router(push_router)
app.include_router(pagook_router)
app.include_router(ofertas_router)
app.include_router(servicio_router)
from app.routes.cierre_api import router as cierre_router
app.include_router(cierre_router)
from app.routes.liquidacion_api import router as liquidacion_router
app.include_router(liquidacion_router)
from app.routes.estado_api import router as estado_router
app.include_router(estado_router)
from app.routes.pago_qr_admin import router as pago_qr_admin_router
app.include_router(pago_qr_admin_router)

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

# Flujo heredado de "mecánico" (elección de técnico, vehículos): retirado del recorrido del
# cliente (zMita-42, Parte C). Las rutas redirigen al flujo actual; el código NO se borra.
from fastapi.responses import RedirectResponse as _Redir

@app.get("/cliente/solicitud-aceite")
@app.get("/cliente/calendario-horarios")
@app.get("/cliente/metodos-pago")
@app.get("/cliente/buscando-mecanico")
@app.get("/cliente/mecanico-asignado")
@app.get("/cliente/seguimiento")
async def _cliente_flujo_heredado(request: Request):
    """Pantallas del modelo antiguo (incluye elección de técnico). Se redirige al flujo actual."""
    return _Redir(url="/cliente/home", status_code=302)



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




@app.get("/manifest.webmanifest")
async def manifest_webmanifest():
    """Manifest PWA de MITA (servido desde la raíz)."""
    return FileResponse("app/static/mita.webmanifest", media_type="application/manifest+json")

@app.get("/manifest.json")
async def manifest():
    """Compatibilidad: redirige al nuevo manifest."""
    return FileResponse("app/static/mita.webmanifest", media_type="application/manifest+json")

@app.get("/sw.js")
async def service_worker():
    """Service worker único, scope raíz."""
    return FileResponse("app/sw.js", media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

@app.get("/prueba-avisos", response_class=HTMLResponse)
async def prueba_avisos_page(request: Request):
    """Página pública para probar instalación y avisos (sin datos personales)."""
    return templates.TemplateResponse("prueba_avisos.html", {"request": request})

@app.get("/pagar/{solicitud_id}", response_class=HTMLResponse)
async def pagar_qr_page(request: Request, solicitud_id: int, concepto: str = "visita"):
    """Pantalla de pago con QR Yape/Plin (zMita-34 v2 / zMita-36; concepto visita|reparacion, zMita-40)."""
    from app.core.database import get_db
    nombre = ""
    concepto = "reparacion" if (concepto or "").lower() == "reparacion" else "visita"
    db = next(get_db())
    try:
        from app.models.solicitud_mita import Solicitud
        s = db.query(Solicitud).get(solicitud_id)
        nombre = (getattr(s, "cliente_nombre", None) or "") if s else ""
    finally:
        db.close()
    return templates.TemplateResponse("pago_qr.html",
                                      {"request": request, "solicitud_id": solicitud_id,
                                       "cliente_nombre": nombre, "concepto": concepto})

@app.get("/tecnico/servicios/{solicitud_id}", response_class=HTMLResponse)
async def tecnico_oferta_page(request: Request, solicitud_id: int):
    """Pantalla de la oferta de servicio para el técnico (etapa 4)."""
    return templates.TemplateResponse("tecnico/oferta.html", {"request": request, "solicitud_id": solicitud_id})

@app.get("/admin/en-curso", response_class=HTMLResponse)
async def admin_en_curso_page(request: Request):
    """Torre: técnicos en camino con ETA, última ubicación y alertas."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/en_curso.html", {"request": request})


@app.get("/tecnico/mi-liquidacion", response_class=HTMLResponse)
async def tecnico_mi_liquidacion_page(request: Request):
    """Técnico: 'Tu liquidación' (periodo actual, historial, detalle y subida del RxH)."""
    return templates.TemplateResponse("tecnico/mi_liquidacion.html", {"request": request})


@app.get("/admin/liquidaciones-mita", response_class=HTMLResponse)
async def admin_liquidaciones_mita_page(request: Request):
    """Torre: liquidaciones por periodo, con RxH, pago y export XLSX (zMita-41)."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/liquidaciones_mita.html", {"request": request})


@app.get("/admin/pago-qr", response_class=HTMLResponse)
async def admin_pago_qr_page(request: Request):
    """Config del cobro QR (número, titular e imagen del QR) — zMita-44.1."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/pago_qr_config.html", {"request": request})


@app.get("/admin/estado", response_class=HTMLResponse)
async def admin_estado_page(request: Request):
    """Torre: estado del sistema (integraciones) — zMita-42 Parte A3."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/estado.html", {"request": request})


@app.get("/admin/cierres", response_class=HTMLResponse)
async def admin_cierres_page(request: Request):
    """Torre: cierres (por cobrar, efectivo por validar, comprobantes, conformidad, totales del día)."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/cierres.html", {"request": request})

@app.get("/admin/buscando", response_class=HTMLResponse)
async def admin_buscando_page(request: Request):
    """Torre de control: solicitudes buscando técnico (etapa 4)."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/buscando.html", {"request": request})

@app.get("/admin/pagos-qr", response_class=HTMLResponse)
async def admin_pagos_qr_page(request: Request):
    """Torre de control: pagos QR (PagoOK) pendientes/media/conflictos (zMita-34 v2)."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/pagos_qr.html", {"request": request})

@app.get("/admin/push", response_class=HTMLResponse)
async def admin_push_page(request: Request):
    """Panel admin: suscripciones push + enviar prueba por fila."""
    from app.core.database import get_db
    from app.routes.main import _guard_admin
    db = next(get_db())
    try:
        redir = await _guard_admin(request, db)
        if redir:
            return redir
    finally:
        db.close()
    return templates.TemplateResponse("admin/push.html", {"request": request})

@app.get("/offline.html", response_class=HTMLResponse)
async def offline_page(request: Request):
    """Página offline"""
    return templates.TemplateResponse("offline.html", {"request": request})