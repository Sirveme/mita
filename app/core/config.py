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
    
    # Environment
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
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