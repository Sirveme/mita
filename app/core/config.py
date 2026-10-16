from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database - OBLIGATORIO para PostgreSQL
    DATABASE_URL: str  # Sin valor por defecto, debe venir de Railway
    
    # Security & JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hora
    REFRESH_TOKEN_EXPIRE_DAYS: int = 90    # 90 días - SESIÓN PERMANENTE
    
    # APIs Externas
    RENIEC_API_URL: str = "https://api.apis.net.pe/v2/reniec/dni"
    RENIEC_API_TOKEN: str = "token-desarrollo"

    # API DNI/RUC (misma config que Facturalo.pro / QueVendi.pro) — decolecta.com
    APIS_NET_PE_TOKEN: str = ""
    APIS_NET_BASE: str = "https://api.decolecta.com"
    APIS_NET_REFERER: str = "https://mita.pe"
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    
    # Pasarelas de Pago - Culqi (Tarjetas)
    CULQI_PUBLIC_KEY: Optional[str] = None
    CULQI_SECRET_KEY: Optional[str] = None

    # Pasarelas de Pago - Tunki (Yape)
    TUNKI_API_KEY: Optional[str] = None
    TUNKI_SECRET_KEY: Optional[str] = None
    TUNKI_WEBHOOK_SECRET: Optional[str] = None
    TUNKI_MERCHANT_ID: Optional[str] = None
    
    # Google Maps
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    GOOGLE_MAPS_SERVER_KEY: Optional[str] = None   # key sin restricción de referrer, solo backend

    # SMS / OTP (zMita-39). Sin proveedor configurado el OTP no bloquea: celular 'no_verificado'.
    SMS_PROVEEDOR: Optional[str] = None            # twilio | nexmo | labsmobile | ... (vacío = sin proveedor)
    SMS_API_KEY: Optional[str] = None
    SMS_API_SECRET: Optional[str] = None
    SMS_REMITENTE: Optional[str] = "MITA"

    # Facturalo.pro — emisión real de comprobantes (zMita-41). Contrato: docs/api-v1-emision.md
    FACTURALO_BASE_URL: str = "https://facturalo.pro"
    FACTURALO_API_KEY: Optional[str] = None        # X-API-Key (fpl_...). Nunca en el frontend.
    FACTURALO_API_SECRET: Optional[str] = None     # X-API-Secret.
    # pruebas -> emite en serie de pruebas (B999/F999); produccion -> serie automática del emisor (B940/F940...).
    FACTURALO_MODO: str = "pruebas"
    # Los montos de MITA ya incluyen IGV: precio_unitario (sin IGV) = monto / 1.18. Si fueran netos, pon false.
    FACTURALO_IGV_INCLUIDO: bool = True

    # OpenAI (chat IA de solicitudes)
    OPENAI_API_KEY: Optional[str] = None

    # Token para incluir traceback en respuestas de error del chat (header X-Debug-Token)
    DEBUG_TOKEN: Optional[str] = None

    # Proveedores de voz (TTS) opcionales
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None

    # Web Push (VAPID) — avisos sin costo (zMita-33)
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_SUBJECT: str = "mailto:avisos@mita.pe"

    # PagoOK — validación de pagos Yape/Plin por consulta (pull) — zMita-34 v2
    PAGOOK_BASE_URL: str = "https://pagook.pro/api/v1"
    PAGOOK_API_KEY: Optional[str] = None   # credencial cuenta_api de MITA; nunca en el frontend

    # Environment
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    # Shim de autenticación de demostración (zMita-40, Parte A2). NUNCA en producción.
    DEMO_AUTH: bool = False
    # Cobro con tarjeta (pasarela heredada Culqi/Tunki). Off por defecto hasta que opere para MITA.
    PASARELA_ACTIVA: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # URLs
    FRONTEND_URL: str = "https://tu-subdominio.up.railway.app"
    BACKEND_URL: str = "https://tu-subdominio.up.railway.app/api"
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://tu-subdominio.up.railway.app"
    ]
    
    # Comisiones
    COMISION_CAMBIO_ACEITE: float = 50.0
    COMISION_ELECTRICIDAD: float = 80.0
    COMISION_GASFITERIA: float = 70.0
    COMISION_ELECTRODOMESTICOS: float = 90.0
    
    # Timeouts
    TIMEOUT_BUSQUEDA_TECNICO: int = 120
    
    # WebSocket
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30  # segundos
    
    # Uploads
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_DIR: str = "uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"   # no romper si el .env trae variables aún no declaradas (SMTP, OpenAI, etc.)

settings = Settings()