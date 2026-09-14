"""
Liquidación semanal por técnico (con RxH y pago).

COEXISTENCIA: usa la tabla 'liquidaciones_tecnico' para no chocar con el modelo
Liquidacion existente (tabla 'liquidaciones').
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, ForeignKey, func

from app.core.database import Base


class LiquidacionTecnico(Base):
    __tablename__ = "liquidaciones_tecnico"

    id = Column(Integer, primary_key=True, index=True)
    tecnico_id = Column(Integer, ForeignKey("personal.id"), index=True)

    semana_inicio = Column(Date)
    semana_fin = Column(Date)

    cantidad_servicios = Column(Integer, default=0)
    total_a_pagar = Column(Numeric(10, 2), default=0)

    # PENDIENTE, EMITIDO_AUTO, SUBIDO_MANUAL, VALIDADO, OBSERVADO
    rxh_estado = Column(String(30), default="PENDIENTE")
    rxh_numero = Column(String(50))
    rxh_fecha = Column(Date)
    rxh_pdf_url = Column(Text)
    rxh_observacion = Column(Text)

    # PENDIENTE, EN_PROCESO, PAGADO
    pago_estado = Column(String(20), default="PENDIENTE")
    pago_fecha = Column(DateTime)
    pago_referencia = Column(String(100))
    pago_metodo = Column(String(30))

    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())
