from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configurar engine según el tipo de base de datos
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite no soporta pool_size ni max_overflow
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG
    )
else:
    # PostgreSQL y otros
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verificar conexiones
        pool_size=10,        # Tamaño del pool
        max_overflow=20,     # Conexiones extra
        echo=settings.DEBUG  # Log de queries solo en debug
    )

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Dependency para obtener DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()