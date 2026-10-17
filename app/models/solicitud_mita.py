"""
Solicitud del flujo MITA v2 (landing → solicitar → técnico → chat).
Tabla `solicitudes` (distinta de `solicitudes_servicio` del flujo anónimo previo).
El técnico se referencia contra `personal.id` (sistema de personal MITA).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from datetime import datetime

from app.core.database import Base


class Solicitud(Base):
    __tablename__ = "solicitudes"

    id = Column(Integer, primary_key=True, index=True)

    # Cliente (puede ser anónimo al inicio)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    cliente_nombre = Column(String(100))
    cliente_telefono = Column(String(15))
    cliente_direccion = Column(String(255))
    cliente_distrito = Column(String(50))
    cliente_referencia = Column(String(255))
    cliente_lat = Column(Float)
    cliente_lng = Column(Float)
    direccion_completa = Column(Text)                      # dirección formateada por Google
    direccion_validada = Column(Boolean, default=False)    # TRUE si Google validó la dirección

    # Servicio
    categoria_id = Column(Integer, ForeignKey("categorias_servicio.id"))
    descripcion_problema = Column(Text)

    # Asignación
    tecnico_id = Column(Integer, ForeignKey("personal.id"))
    secretaria_id = Column(Integer, ForeignKey("personal.id"), nullable=True)

    # Asignación automática (dashboard técnico) — se notifica a TODOS a la vez
    cola_tecnicos = Column(Text)                                        # (legacy) CSV de ids
    tecnico_notificado_id = Column(Integer, ForeignKey("personal.id"))  # (legacy)
    notificado_en = Column(DateTime, nullable=True)                     # inicio del intento actual
    intento_notificacion = Column(Integer, default=1)                   # nº de ronda de notificación
    diagnostico = Column(Text)

    # Estado: PENDIENTE, ACEPTADA, EN_CAMINO, EN_SERVICIO, COMPLETADA, CANCELADA, RECHAZADA
    estado = Column(String(20), default="PENDIENTE", index=True)

    # Tiempos
    fecha_solicitud = Column(DateTime, default=datetime.utcnow, index=True)
    fecha_programada = Column(DateTime, nullable=True)   # cita agendada (chat/formulario)
    fecha_aceptacion = Column(DateTime, nullable=True)
    fecha_llegada = Column(DateTime, nullable=True)
    fecha_inicio_servicio = Column(DateTime, nullable=True)
    fecha_fin_servicio = Column(DateTime, nullable=True)

    # Costos
    costo_visita = Column(Float, default=50.0)
    costo_servicio = Column(Float, nullable=True)
    costo_total = Column(Float, nullable=True)

    # Pagos
    metodo_pago = Column(String(20))
    pagado = Column(Integer, default=0)

    # Calificación
    calificacion = Column(Integer, nullable=True)
    comentario = Column(Text, nullable=True)

    # Conversación
    conversacion_id = Column(Integer, ForeignKey("conversaciones.id"), nullable=True)

    # --- zMita-13: catálogo, pago adelantado, cancelación, calificación ---
    tipo_servicio_id = Column(Integer, ForeignKey("tipos_servicio.id"))
    precio_servicio = Column(Float)               # precio fijo o cotizado
    es_precio_fijo = Column(Boolean, default=False)
    pago_adelantado = Column(Boolean, default=False)
    pago_confirmado_at = Column(DateTime, nullable=True)
    metodo_pago = Column(String(20))              # yape, plin, tarjeta, efectivo
    referencia_pago = Column(String(100))
    cancelado = Column(Boolean, default=False)
    cancelado_at = Column(DateTime, nullable=True)
    cancelado_por = Column(String(20))            # cliente, tecnico, sistema
    motivo_cancelacion = Column(Text)
    tarifa_cancelacion = Column(Float)
    calificado = Column(Boolean, default=False)
    # Canal de avisos elegido por el cliente (zMita-35): push / whatsapp / ninguno
    canal_avisos = Column(String(20), default="ninguno")
    # Etapa 4 (zMita-37)
    aceptada_en = Column(DateTime, nullable=True)
    alerta_sin_aceptar_en = Column(DateTime, nullable=True)   # alerta a la torre (una vez)
    aviso_cliente_en = Column(DateTime, nullable=True)        # "seguimos buscando" (una vez)
    # Etapas 5-6 (zMita-38)
    en_camino_desde = Column(DateTime, nullable=True)
    cliente_no_esta_en = Column(DateTime, nullable=True)
    eta_inicial_min = Column(Integer, nullable=True)
    eta_actual_min = Column(Integer, nullable=True)
    eta_calc_en = Column(DateTime, nullable=True)
    eta_calc_lat = Column(Float, nullable=True)
    eta_calc_lng = Column(Float, nullable=True)

    # Etapa 2 — identificación del comprador (zMita-39)
    celular_verificado = Column(Boolean, default=False)
    celular_estado = Column(String(15), default="pendiente")   # verificado / no_verificado / pendiente
    comprador_tipo_comprobante = Column(String(12))            # boleta / factura
    comprador_doc_tipo = Column(String(12))                    # DNI / RUC / CE / PASAPORTE
    comprador_doc_numero = Column(String(20))
    comprador_nombre = Column(String(200))                     # nombres o razón social
    comprador_direccion_fiscal = Column(String(255))

    # Etapa 7 — cierre y cobro (zMita-39)
    terminado_en = Column(DateTime, nullable=True)
    monto_por_cobrar = Column(Float, nullable=True)
    cobro_metodo = Column(String(12), nullable=True)           # digital / efectivo
    cobrado_en = Column(DateTime, nullable=True)
    cerrado_en = Column(DateTime, nullable=True)
    conformidad_ok = Column(Boolean, nullable=True)            # ¿quedó resuelto?
    conformidad_estrellas = Column(Integer, nullable=True)     # 1..5
    conformidad_comentario = Column(Text, nullable=True)

    # Modo ensayo (zMita-45 D): servicio de un cliente de prueba (monto reducido, serie B999,
    # marca ENSAYO en la torre, excluido de la liquidación).
    ensayo = Column(Boolean, default=False)
