"""
Utilidades para manejo de zonas horarias - MITA
Ubicación: app/utils/timezone_utils.py
"""

from datetime import datetime, time, date
from zoneinfo import ZoneInfo
from typing import Optional

# Zona horaria Perú (Lima)
TIMEZONE_PERU = ZoneInfo("America/Lima")
TIMEZONE_UTC = ZoneInfo("UTC")

# ============================================
# CONVERSIÓN: Perú → UTC (para guardar en BD)
# ============================================

def datetime_peru_to_utc(dt: datetime) -> datetime:
    """
    Convierte datetime de Perú a UTC para guardar en BD.
    
    Args:
        dt: datetime naive o con timezone de Perú
    
    Returns:
        datetime en UTC con timezone
    
    Ejemplo:
        >>> dt_peru = datetime(2024, 12, 5, 10, 0)  # 10 AM Perú
        >>> dt_utc = datetime_peru_to_utc(dt_peru)
        >>> print(dt_utc)  # 2024-12-05 15:00:00+00:00 (UTC)
    """
    if dt.tzinfo is None:
        # Si es naive, asume que es hora de Perú
        dt = dt.replace(tzinfo=TIMEZONE_PERU)
    
    # Convertir a UTC
    return dt.astimezone(TIMEZONE_UTC)


def combine_date_time_peru(date_obj: date, time_obj: time) -> datetime:
    """
    Combina fecha y hora asumiendo zona horaria Perú.
    
    Args:
        date_obj: Fecha (YYYY-MM-DD)
        time_obj: Hora (HH:MM:SS)
    
    Returns:
        datetime con timezone Perú
    
    Ejemplo:
        >>> fecha = date(2024, 12, 5)
        >>> hora = time(10, 0)
        >>> dt = combine_date_time_peru(fecha, hora)
        >>> print(dt)  # 2024-12-05 10:00:00-05:00
    """
    dt_naive = datetime.combine(date_obj, time_obj)
    return dt_naive.replace(tzinfo=TIMEZONE_PERU)


# ============================================
# CONVERSIÓN: UTC → Perú (para mostrar)
# ============================================

def datetime_utc_to_peru(dt: datetime) -> datetime:
    """
    Convierte datetime UTC a hora Perú para mostrar.
    
    Args:
        dt: datetime en UTC
    
    Returns:
        datetime en timezone Perú
    
    Ejemplo:
        >>> dt_utc = datetime(2024, 12, 5, 15, 0, tzinfo=TIMEZONE_UTC)
        >>> dt_peru = datetime_utc_to_peru(dt_utc)
        >>> print(dt_peru)  # 2024-12-05 10:00:00-05:00
    """
    if dt.tzinfo is None:
        # Si es naive, asume UTC
        dt = dt.replace(tzinfo=TIMEZONE_UTC)
    
    return dt.astimezone(TIMEZONE_PERU)


def now_peru() -> datetime:
    """
    Retorna fecha/hora actual en timezone Perú.
    
    Returns:
        datetime con timezone Perú
    
    Ejemplo:
        >>> ahora = now_peru()
        >>> print(ahora)  # 2024-12-05 10:30:45-05:00
    """
    return datetime.now(TIMEZONE_PERU)


def now_utc() -> datetime:
    """
    Retorna fecha/hora actual en UTC.
    
    Returns:
        datetime con timezone UTC
    
    Ejemplo:
        >>> ahora = now_utc()
        >>> print(ahora)  # 2024-12-05 15:30:45+00:00
    """
    return datetime.now(TIMEZONE_UTC)


# ============================================
# FORMATO PARA FRONTEND
# ============================================

def format_datetime_peru(dt: datetime, include_seconds: bool = False) -> str:
    """
    Formatea datetime para mostrar en frontend (hora Perú).
    
    Args:
        dt: datetime en cualquier timezone
        include_seconds: Si incluir segundos
    
    Returns:
        String formateado "DD/MM/YYYY HH:MM" o "DD/MM/YYYY HH:MM:SS"
    
    Ejemplo:
        >>> dt = datetime(2024, 12, 5, 15, 30, 45, tzinfo=TIMEZONE_UTC)
        >>> print(format_datetime_peru(dt))
        '05/12/2024 10:30'
    """
    dt_peru = datetime_utc_to_peru(dt)
    
    if include_seconds:
        return dt_peru.strftime("%d/%m/%Y %H:%M:%S")
    return dt_peru.strftime("%d/%m/%Y %H:%M")


def format_date_peru(dt: datetime) -> str:
    """
    Formatea solo la fecha en formato peruano.
    
    Args:
        dt: datetime
    
    Returns:
        String "DD/MM/YYYY"
    
    Ejemplo:
        >>> dt = datetime(2024, 12, 5, 10, 0, tzinfo=TIMEZONE_PERU)
        >>> print(format_date_peru(dt))
        '05/12/2024'
    """
    dt_peru = datetime_utc_to_peru(dt)
    return dt_peru.strftime("%d/%m/%Y")


def format_time_peru(dt: datetime, format_12h: bool = False) -> str:
    """
    Formatea solo la hora en formato peruano.
    
    Args:
        dt: datetime
        format_12h: Si usar formato 12h con AM/PM
    
    Returns:
        String "HH:MM" o "HH:MM AM/PM"
    
    Ejemplo:
        >>> dt = datetime(2024, 12, 5, 15, 30, tzinfo=TIMEZONE_UTC)
        >>> print(format_time_peru(dt))
        '10:30'
        >>> print(format_time_peru(dt, format_12h=True))
        '10:30 AM'
    """
    dt_peru = datetime_utc_to_peru(dt)
    
    if format_12h:
        return dt_peru.strftime("%I:%M %p")
    return dt_peru.strftime("%H:%M")


# ============================================
# VALIDACIÓN
# ============================================

def is_past_datetime(dt: datetime) -> bool:
    """
    Verifica si un datetime es pasado (en hora Perú).
    
    Args:
        dt: datetime a verificar
    
    Returns:
        True si es pasado, False si es futuro
    
    Ejemplo:
        >>> dt_ayer = datetime(2024, 12, 4, 10, 0, tzinfo=TIMEZONE_PERU)
        >>> print(is_past_datetime(dt_ayer))  # True
    """
    ahora = now_peru()
    dt_peru = datetime_utc_to_peru(dt) if dt.tzinfo else dt.replace(tzinfo=TIMEZONE_PERU)
    return dt_peru < ahora


def is_today_peru(dt: datetime) -> bool:
    """
    Verifica si un datetime es hoy (en hora Perú).
    
    Args:
        dt: datetime a verificar
    
    Returns:
        True si es hoy, False si no
    
    Ejemplo:
        >>> dt = now_peru()
        >>> print(is_today_peru(dt))  # True
    """
    hoy = now_peru().date()
    dt_peru = datetime_utc_to_peru(dt) if dt.tzinfo else dt.replace(tzinfo=TIMEZONE_PERU)
    return dt_peru.date() == hoy


# ============================================
# PARSEO DESDE FRONTEND
# ============================================

def parse_datetime_from_frontend(date_str: str, time_str: str) -> datetime:
    """
    Parsea fecha y hora que vienen del frontend (formato Perú).
    
    Args:
        date_str: Fecha "YYYY-MM-DD" o "DD/MM/YYYY"
        time_str: Hora "HH:MM" o "HH:MM:SS"
    
    Returns:
        datetime en UTC listo para guardar en BD
    
    Ejemplo:
        >>> dt = parse_datetime_from_frontend("2024-12-05", "10:00")
        >>> print(dt)  # 2024-12-05 15:00:00+00:00 (UTC)
    """
    # Detectar formato fecha
    if "/" in date_str:
        # Formato DD/MM/YYYY
        fecha = datetime.strptime(date_str, "%d/%m/%Y").date()
    else:
        # Formato YYYY-MM-DD
        fecha = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Parsear hora
    hora = datetime.strptime(time_str, "%H:%M").time()
    
    # Combinar asumiendo timezone Perú
    dt_peru = combine_date_time_peru(fecha, hora)
    
    # Convertir a UTC para BD
    return datetime_peru_to_utc(dt_peru)


# ============================================
# SERIALIZACIÓN PARA API
# ============================================

def serialize_datetime_for_api(dt: Optional[datetime]) -> Optional[str]:
    """
    Serializa datetime para respuesta API (ISO format en hora Perú).
    
    Args:
        dt: datetime a serializar
    
    Returns:
        String ISO format o None
    
    Ejemplo:
        >>> dt = datetime(2024, 12, 5, 15, 0, tzinfo=TIMEZONE_UTC)
        >>> print(serialize_datetime_for_api(dt))
        '2024-12-05T10:00:00-05:00'
    """
    if dt is None:
        return None
    
    dt_peru = datetime_utc_to_peru(dt)
    return dt_peru.isoformat()


# ============================================
# EJEMPLO DE USO EN ENDPOINTS
# ============================================

"""
# En tus endpoints FastAPI:

from app.utils.timezone_utils import (
    parse_datetime_from_frontend,
    serialize_datetime_for_api,
    format_datetime_peru
)

@app.post("/servicios")
async def crear_servicio(
    fecha: str,  # "2024-12-05"
    hora: str,   # "10:00"
    db: Session = Depends(get_db)
):
    # Parsear fecha/hora del frontend (Perú) → UTC para BD
    fecha_hora_utc = parse_datetime_from_frontend(fecha, hora)
    
    servicio = Servicio(
        fecha_programada=fecha_hora_utc.date(),
        hora_programada=fecha_hora_utc.time(),
        created_at=fecha_hora_utc  # Se guarda en UTC
    )
    
    db.add(servicio)
    db.commit()
    
    # Retornar en hora Perú
    return {
        "id": servicio.id,
        "fecha_hora": serialize_datetime_for_api(servicio.created_at),
        "fecha_formateada": format_datetime_peru(servicio.created_at)
    }


@app.get("/servicios/{id}")
async def obtener_servicio(id: int, db: Session = Depends(get_db)):
    servicio = db.query(Servicio).filter(Servicio.id == id).first()
    
    # BD guarda en UTC, convertir a Perú para mostrar
    return {
        "id": servicio.id,
        "fecha_hora_peru": serialize_datetime_for_api(servicio.created_at),
        "fecha_legible": format_datetime_peru(servicio.created_at),
        "hora_legible": format_time_peru(servicio.created_at, format_12h=True)
    }
"""


# ============================================
# TESTS RÁPIDOS
# ============================================

if __name__ == "__main__":
    print("🧪 TESTS TIMEZONE UTILS\n")
    
    # Test 1: Conversión Perú → UTC
    print("1. Usuario programa servicio 10:00 AM Perú:")
    dt_peru = datetime(2024, 12, 5, 10, 0, tzinfo=TIMEZONE_PERU)
    dt_utc = datetime_peru_to_utc(dt_peru)
    print(f"   Hora Perú: {dt_peru}")
    print(f"   Guardado BD (UTC): {dt_utc}\n")
    
    # Test 2: Conversión UTC → Perú
    print("2. Leer de BD y mostrar al usuario:")
    dt_bd = datetime(2024, 12, 5, 15, 0, tzinfo=TIMEZONE_UTC)
    dt_mostrar = datetime_utc_to_peru(dt_bd)
    print(f"   De BD (UTC): {dt_bd}")
    print(f"   Mostrar (Perú): {dt_mostrar}\n")
    
    # Test 3: Formato legible
    print("3. Formatos para frontend:")
    print(f"   Completo: {format_datetime_peru(dt_bd)}")
    print(f"   Solo fecha: {format_date_peru(dt_bd)}")
    print(f"   Solo hora: {format_time_peru(dt_bd)}")
    print(f"   Hora 12h: {format_time_peru(dt_bd, format_12h=True)}\n")
    
    # Test 4: Parsear desde frontend
    print("4. Parsear del frontend:")
    dt_parsed = parse_datetime_from_frontend("2024-12-05", "10:00")
    print(f"   Input: '2024-12-05' + '10:00' (Perú)")
    print(f"   Output BD: {dt_parsed} (UTC)\n")
    
    # Test 5: Serializar para API
    print("5. Serializar para API:")
    dt_api = serialize_datetime_for_api(dt_bd)
    print(f"   ISO Format: {dt_api}\n")
    
    print("✅ Todos los tests OK")