"""
Servicio de configuración MITA (parámetros de asignación/tarifas). zMita-13.
"""

from typing import Any, Dict, Optional
import json

from sqlalchemy.orm import Session

from app.models.configuracion import ConfiguracionMita


class ConfigService:
    """Acceso a los parámetros de `configuracion_mita` con caché en memoria."""

    _cache: Dict[str, Any] = {}

    @classmethod
    def get(cls, db: Session, clave: str, default: Any = None) -> Any:
        if clave in cls._cache:
            return cls._cache[clave]
        config = db.query(ConfiguracionMita).filter(ConfiguracionMita.clave == clave).first()
        if not config:
            return default
        valor = config.get_valor()
        cls._cache[clave] = valor
        return valor

    @classmethod
    def set(cls, db: Session, clave: str, valor: Any) -> bool:
        config = db.query(ConfiguracionMita).filter(ConfiguracionMita.clave == clave).first()
        if not config:
            return False
        if config.tipo == "json":
            config.valor = json.dumps(valor)
        elif config.tipo == "bool":
            config.valor = "true" if valor else "false"
        else:
            config.valor = str(valor)
        db.commit()
        cls._cache[clave] = valor
        return True

    @classmethod
    def get_all(cls, db: Session, categoria: Optional[str] = None) -> Dict[str, Any]:
        query = db.query(ConfiguracionMita)
        if categoria:
            query = query.filter(ConfiguracionMita.categoria == categoria)
        return {c.clave: c.get_valor() for c in query.all()}

    @classmethod
    def clear_cache(cls):
        cls._cache = {}


# Atajos
def get_tiempo_espera(db: Session) -> int:
    return ConfigService.get(db, "tiempo_espera_asignacion", 60)

def get_tiempo_respuesta(db: Session) -> int:
    return ConfigService.get(db, "tiempo_respuesta_tecnico", 90)

def get_radio_inicial(db: Session) -> float:
    return ConfigService.get(db, "radio_busqueda_inicial_km", 5.0)

def get_tarifa_visita(db: Session) -> float:
    return ConfigService.get(db, "tarifa_visita_default", 50.0)

def get_porcentaje_cancelacion(db: Session) -> int:
    return ConfigService.get(db, "porcentaje_cancelacion", 50)

def usar_prioridad_rating(db: Session) -> bool:
    return ConfigService.get(db, "habilitar_prioridad_rating", False)
