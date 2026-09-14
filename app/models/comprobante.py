"""
Shim de compatibilidad. Las definiciones canónicas están en:
  - app/models/servicio_completado.py  (ServicioCompletado)
  - app/models/liquidacion_tecnico.py  (LiquidacionTecnico)

Se re-exportan aquí para no romper imports antiguos (`from app.models.comprobante ...`).
NO redefinir las clases aquí: causaría "Table already defined" en SQLAlchemy.
"""

from app.models.servicio_completado import ServicioCompletado
from app.models.liquidacion_tecnico import LiquidacionTecnico

__all__ = ["ServicioCompletado", "LiquidacionTecnico"]
