from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from datetime import datetime

router = APIRouter(prefix="/api/tecnicos", tags=["Técnicos"])

# ========================================
# MODELOS DE RESPUESTA (Pydantic)
# ========================================

from pydantic import BaseModel

class TecnicoBase(BaseModel):
    nombre: str
    apellido: str
    especialidad: str
    telefono: str
    email: str

class TecnicoCreate(TecnicoBase):
    password: str

class TecnicoResponse(TecnicoBase):
    id: int
    disponible: bool
    calificacion: float
    servicios_completados: int
    
    class Config:
        from_attributes = True

class DisponibilidadUpdate(BaseModel):
    disponible: bool
    latitud: Optional[float] = None
    longitud: Optional[float] = None

class ServicioTecnicoResponse(BaseModel):
    id: int
    tipo: str
    cliente: str
    direccion: str
    estado: str
    precio: float
    fecha: datetime

# ========================================
# ENDPOINTS API
# ========================================

@router.get("/", response_model=List[TecnicoResponse])
async def listar_tecnicos(
    disponibles: Optional[bool] = None,
    especialidad: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Listar todos los técnicos con filtros opcionales
    
    - **disponibles**: Filtrar por disponibilidad (True/False)
    - **especialidad**: Filtrar por especialidad (aceite, electricidad, etc.)
    """
    # TODO: Implementar consulta a la base de datos
    
    # Datos de ejemplo
    tecnicos_ejemplo = [
        {
            "id": 1,
            "nombre": "Juan",
            "apellido": "Pérez",
            "especialidad": "Electricidad",
            "telefono": "+51999888777",
            "email": "juan@example.com",
            "disponible": True,
            "calificacion": 4.8,
            "servicios_completados": 150
        },
        {
            "id": 2,
            "nombre": "Carlos",
            "apellido": "López",
            "especialidad": "Gasfitería",
            "telefono": "+51999888666",
            "email": "carlos@example.com",
            "disponible": False,
            "calificacion": 4.9,
            "servicios_completados": 200
        }
    ]
    
    return tecnicos_ejemplo

@router.get("/{tecnico_id}", response_model=TecnicoResponse)
async def obtener_tecnico(tecnico_id: int, db: Session = Depends(get_db)):
    """
    Obtener información detallada de un técnico por ID
    """
    # TODO: Buscar en base de datos
    
    if tecnico_id not in [1, 2]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Técnico no encontrado"
        )
    
    return {
        "id": tecnico_id,
        "nombre": "Juan",
        "apellido": "Pérez",
        "especialidad": "Electricidad",
        "telefono": "+51999888777",
        "email": "juan@example.com",
        "disponible": True,
        "calificacion": 4.8,
        "servicios_completados": 150
    }

@router.post("/", response_model=TecnicoResponse, status_code=status.HTTP_201_CREATED)
async def crear_tecnico(tecnico: TecnicoCreate, db: Session = Depends(get_db)):
    """
    Registrar un nuevo técnico en el sistema
    
    - **nombre**: Nombre del técnico
    - **apellido**: Apellido del técnico
    - **especialidad**: Área de especialización
    - **telefono**: Número de contacto
    - **email**: Correo electrónico
    - **password**: Contraseña (será hasheada)
    """
    # TODO: 
    # 1. Verificar que el email no exista
    # 2. Hashear la contraseña
    # 3. Crear registro en DB
    # 4. Enviar email de bienvenida
    
    return {
        "id": 3,
        "nombre": tecnico.nombre,
        "apellido": tecnico.apellido,
        "especialidad": tecnico.especialidad,
        "telefono": tecnico.telefono,
        "email": tecnico.email,
        "disponible": False,
        "calificacion": 0.0,
        "servicios_completados": 0
    }

@router.put("/{tecnico_id}/disponibilidad")
async def actualizar_disponibilidad(
    tecnico_id: int, 
    disponibilidad: DisponibilidadUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar la disponibilidad del técnico (Online/Offline)
    
    - **disponible**: True para online, False para offline
    - **latitud**: Latitud actual (opcional)
    - **longitud**: Longitud actual (opcional)
    """
    # TODO: 
    # 1. Actualizar en base de datos
    # 2. Si pasa a disponible, notificar al sistema de matching
    # 3. Registrar timestamp de cambio de estado
    
    return {
        "message": "Disponibilidad actualizada",
        "tecnico_id": tecnico_id,
        "disponible": disponibilidad.disponible,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/{tecnico_id}/servicios", response_model=List[ServicioTecnicoResponse])
async def servicios_tecnico(
    tecnico_id: int,
    estado: Optional[str] = None,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Obtener todos los servicios de un técnico con filtros opcionales
    
    - **estado**: Filtrar por estado (pendiente, en_proceso, completado, cancelado)
    - **fecha_inicio**: Fecha de inicio del rango
    - **fecha_fin**: Fecha de fin del rango
    """
    # TODO: Implementar consulta con filtros
    
    servicios_ejemplo = [
        {
            "id": 1,
            "tipo": "Cambio de aceite",
            "cliente": "María López",
            "direccion": "Av. Arequipa 1234",
            "estado": "completado",
            "precio": 120.0,
            "fecha": datetime.now()
        }
    ]
    
    return servicios_ejemplo

@router.get("/{tecnico_id}/estadisticas")
async def estadisticas_tecnico(
    tecnico_id: int,
    periodo: str = "hoy",  # hoy, semana, mes, año
    db: Session = Depends(get_db)
):
    """
    Obtener estadísticas del técnico
    
    - **periodo**: hoy, semana, mes, año
    """
    # TODO: Calcular estadísticas reales
    
    return {
        "servicios_completados": 5,
        "ganancia_total": 420.0,
        "horas_trabajadas": 6.5,
        "calificacion_promedio": 4.9,
        "clientes_atendidos": 5,
        "periodo": periodo
    }

@router.post("/{tecnico_id}/aceptar-servicio/{servicio_id}")
async def aceptar_servicio(
    tecnico_id: int,
    servicio_id: int,
    db: Session = Depends(get_db)
):
    """
    Técnico acepta una solicitud de servicio
    """
    # TODO:
    # 1. Verificar que el técnico esté disponible
    # 2. Verificar que el servicio esté disponible
    # 3. Asignar servicio al técnico
    # 4. Notificar al cliente
    # 5. Cambiar estado a "aceptado"
    
    return {
        "message": "Servicio aceptado exitosamente",
        "servicio_id": servicio_id,
        "tecnico_id": tecnico_id,
        "proximo_paso": "Dirigirse al cliente"
    }

@router.post("/{tecnico_id}/rechazar-servicio/{servicio_id}")
async def rechazar_servicio(
    tecnico_id: int,
    servicio_id: int,
    motivo: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Técnico rechaza una solicitud de servicio
    """
    # TODO:
    # 1. Marcar servicio como rechazado por este técnico
    # 2. Buscar otro técnico disponible
    # 3. Registrar motivo del rechazo
    
    return {
        "message": "Servicio rechazado",
        "servicio_id": servicio_id,
        "motivo": motivo
    }

@router.put("/{tecnico_id}/ubicacion")
async def actualizar_ubicacion(
    tecnico_id: int,
    latitud: float,
    longitud: float,
    db: Session = Depends(get_db)
):
    """
    Actualizar la ubicación GPS del técnico en tiempo real
    """
    # TODO: 
    # 1. Actualizar en Redis (cache rápido)
    # 2. Periódicamente guardar en DB
    # 3. Notificar a clientes que esperan al técnico
    
    return {
        "message": "Ubicación actualizada",
        "latitud": latitud,
        "longitud": longitud,
        "timestamp": datetime.now().isoformat()
    }