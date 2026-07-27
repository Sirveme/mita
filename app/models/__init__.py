"""
Modelos MITA - Servicios Técnicos a Domicilio

Importa todos los módulos de modelos para que queden registrados en el
metadata de SQLAlchemy (Base.metadata) al importar `app.models`.
"""

# Base
from app.core.database import Base

# Modelos existentes (registran sus tablas en Base.metadata)
from app.models import models          # noqa: F401
from app.models import solicitud       # noqa: F401

# Nuevos modelos MITA
from app.models.personal import (
    Personal, TecnicoPersonal, Secretaria, HorarioTecnico,
    DocumentoPersonal, Distrito, TiempoEntreDistritos,
    TipoPersonal, EstadoPersonal, EstadoTecnico, TipoDocumento,
)

from app.models.chat import (
    Conversacion, Mensaje, NotificacionPush, DispositivoUsuario,
    TipoParticipante, EstadoConversacion, EstadoMensaje, TipoMensaje,
)

from app.models.liquidacion import (
    Liquidacion, DetalleLiquidacion, ConfiguracionLiquidacion,
    EstadoLiquidacion, FrecuenciaPago,
)

from app.models.configuracion import (
    ConfiguracionGeneral, TarifaServicio, HorarioAtencion,
    Feriado, MensajeBot,
)

from app.models.auth_mita import UsuarioMita, SesionMita
from app.models.ubigeo import Ubigeo
from app.models.solicitud_mita import Solicitud
from app.models.billetera import BilleteraPersonal
