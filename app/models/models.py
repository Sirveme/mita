"""
MODELOS SQLALCHEMY - MITA
Base de datos completa con 30+ tablas
Para Railway PostgreSQL
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Time, 
    Numeric, Text, Enum, ForeignKey, ARRAY, CheckConstraint, Index,TIMESTAMP
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# ============================================
# ENUMS
# ============================================

class RolUsuario(str, enum.Enum):
    """Roles de usuario"""
    CLIENTE = "cliente"
    TECNICO = "tecnico"
    ADMIN = "admin"
    PROVEEDOR = "proveedor"

class RolEnum(enum.Enum):
    cliente = "cliente"
    tecnico = "tecnico"
    admin = "admin"
    proveedor = "proveedor"

class GeneroEnum(enum.Enum):
    M = "M"
    F = "F"
    otro = "otro"
    prefiero_no_decir = "prefiero_no_decir"

class EstadoTecnicoEnum(enum.Enum):
    activo = "activo"
    inactivo = "inactivo"
    suspendido = "suspendido"
    vacaciones = "vacaciones"

class TipoVehiculoEnum(enum.Enum):
    sedan = "sedan"
    suv = "suv"
    hatchback = "hatchback"
    pickup = "pickup"
    van = "van"
    coupe = "coupe"
    otro = "otro"

class TipoCombustibleEnum(enum.Enum):
    gasolina = "gasolina"
    diesel = "diesel"
    hibrido = "hibrido"
    electrico = "electrico"
    gnv = "gnv"

class TipoMovimientoEnum(enum.Enum):
    entrada = "entrada"
    salida = "salida"
    ajuste = "ajuste"
    vencimiento = "vencimiento"

class EstadoServicioEnum(enum.Enum):
    programado = "programado"
    preautorizado = "preautorizado"
    buscando_tecnico = "buscando_tecnico"
    asignado = "asignado"
    en_camino = "en_camino"
    en_proceso = "en_proceso"
    completado = "completado"
    cancelado = "cancelado"
    no_show = "no_show"

class EstadoPagoServicioEnum(enum.Enum):
    pendiente = "pendiente"
    preautorizado = "preautorizado"
    pagado = "pagado"
    rechazado = "rechazado"
    reembolsado = "reembolsado"

class MetodoPagoEnum(enum.Enum):
    culqi_tarjeta = "culqi_tarjeta"
    yape = "yape"
    plin = "plin"
    efectivo = "efectivo"
    transferencia = "transferencia"

class EstadoPagoEnum(enum.Enum):
    pendiente = "pendiente"
    preautorizado = "preautorizado"
    confirmado = "confirmado"
    rechazado = "rechazado"
    reembolsado = "reembolsado"
    cancelado = "cancelado"

# ============================================
# 1. USUARIOS Y PERFILES
# ============================================

class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(255), nullable=False)
    telefono_principal = Column(String(20))
    whatsapp = Column(String(20))
    foto_perfil_url = Column(String(500))
    rol = Column(Enum(RolEnum), nullable=False)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    ultimo_acceso = Column(DateTime(timezone=True))
    activo = Column(Boolean, default=True)
    verificado_email = Column(Boolean, default=False)
    verificado_telefono = Column(Boolean, default=False)
    acepto_terminos = Column(Boolean, default=False)
    acepto_marketing = Column(Boolean, default=False)
    idioma_preferido = Column(String(10), default='es')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    cliente = relationship("Cliente", back_populates="usuario", uselist=False)
    tecnico = relationship("Tecnico", back_populates="usuario", uselist=False)
    notificaciones = relationship("Notificacion", back_populates="usuario")
    sesiones = relationship("SesionUsuario", back_populates="usuario")

class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    dni = Column(String(20), unique=True)
    fecha_nacimiento = Column(Date)
    genero = Column(Enum(GeneroEnum))
    codigo_referido = Column(String(50), unique=True)
    referido_por_id = Column(Integer, ForeignKey("clientes.id"))
    total_servicios = Column(Integer, default=0)
    total_gastado = Column(Numeric(10, 2), default=0)
    fecha_ultimo_servicio = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    usuario = relationship("Usuario", back_populates="cliente")
    referidor = relationship("Cliente", remote_side=[id], foreign_keys=[referido_por_id])
    ubicaciones = relationship("UbicacionCliente", back_populates="cliente")
    vehiculos = relationship("VehiculoCliente", back_populates="cliente")
    servicios = relationship("Servicio", back_populates="cliente")
    cupones_usados = relationship("CuponUsado", back_populates="cliente")

class Tecnico(Base):
    __tablename__ = "tecnicos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    dni = Column(String(20), unique=True, nullable=False)
    direccion_completa = Column(String(500))
    distrito = Column(String(100))
    referencia = Column(String(500))
    departamento = Column(String(100), default='Lima')
    provincia = Column(String(100), default='Lima')
    cv_url = Column(String(500))
    certificados_urls = Column(ARRAY(Text))
    verificado_admin = Column(Boolean, default=False)
    fecha_verificacion = Column(Date)
    rating_promedio = Column(Numeric(3, 2), default=0)
    total_servicios = Column(Integer, default=0)
    tasa_aceptacion = Column(Numeric(5, 2), default=0)
    tasa_completacion = Column(Numeric(5, 2), default=0)
    saldo_disponible = Column(Numeric(10, 2), default=0)
    saldo_pendiente = Column(Numeric(10, 2), default=0)
    banco = Column(String(100))
    numero_cuenta = Column(String(50))
    cci = Column(String(20))
    tipo_cuenta = Column(Enum('ahorros', 'corriente', name='tipo_cuenta_enum'))
    titular_cuenta = Column(String(255))
    placa_vehiculo = Column(String(20))
    marca_vehiculo = Column(String(100))
    modelo_vehiculo = Column(String(100))
    anio_vehiculo = Column(Integer)
    estado = Column(Enum(EstadoTecnicoEnum), default=EstadoTecnicoEnum.activo)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    usuario = relationship("Usuario", back_populates="tecnico")
    horarios = relationship("TecnicoHorario", back_populates="tecnico")
    servicios = relationship("Servicio", back_populates="tecnico")
    comisiones = relationship("ComisionTecnico", back_populates="tecnico")
    #solicitudes = relationship("SolicitudServicio", back_populates="tecnico")

class TecnicoHorario(Base):
    __tablename__ = "tecnicos_horarios"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"), nullable=False, index=True)
    dia_semana = Column(Integer, nullable=False)  # 0=Domingo, 6=Sábado
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint('dia_semana >= 0 AND dia_semana <= 6'),
    )
    
    # Relationships
    tecnico = relationship("Tecnico", back_populates="horarios")

# ============================================
# 2. UBICACIONES
# ============================================

class UbicacionCliente(Base):
    __tablename__ = "ubicaciones_cliente"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), index=True)
    nombre_ubicacion = Column(String(100))  # "Casa", "Trabajo", etc
    direccion_completa = Column(String(500), nullable=False)
    distrito = Column(String(100), nullable=False)
    referencia = Column(String(500))
    departamento = Column(String(100), default='Lima')
    provincia = Column(String(100), default='Lima')
    numero_casa = Column(String(20))
    piso = Column(String(20))
    latitud = Column(Numeric(10, 8))
    longitud = Column(Numeric(11, 8))
    es_predeterminada = Column(Boolean, default=False)
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    cliente = relationship("Cliente", back_populates="ubicaciones")
    servicios = relationship("Servicio", back_populates="ubicacion")

# ============================================
# 3. CATÁLOGO VEHÍCULOS
# ============================================

class MarcaVehiculo(Base):
    __tablename__ = "marcas_vehiculos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    logo_url = Column(String(500))
    pais_origen = Column(String(100))
    activo = Column(Boolean, default=True)
    orden_display = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    modelos = relationship("ModeloVehiculo", back_populates="marca")

class ModeloVehiculo(Base):
    __tablename__ = "modelos_vehiculos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    marca_id = Column(Integer, ForeignKey("marcas_vehiculos.id"))
    nombre = Column(String(100), nullable=False)
    anio_inicio = Column(Integer)
    anio_fin = Column(Integer)
    tipo_vehiculo = Column(Enum(TipoVehiculoEnum))
    motor_litros = Column(Numeric(3, 1))
    tipo_combustible = Column(Enum(TipoCombustibleEnum))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_marca_modelo_anio', 'marca_id', 'nombre', 'anio_inicio', unique=True),
    )
    
    # Relationships
    marca = relationship("MarcaVehiculo", back_populates="modelos")
    especificaciones = relationship("EspecificacionVehiculo", back_populates="modelo")

class EspecificacionVehiculo(Base):
    __tablename__ = "especificaciones_vehiculos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    modelo_id = Column(Integer, ForeignKey("modelos_vehiculos.id"))
    anio = Column(Integer, nullable=False)
    tipo_aceite_motor = Column(String(50))
    capacidad_aceite_litros = Column(Numeric(4, 2))
    tipo_filtro_aceite = Column(String(100))
    presion_llantas_psi = Column(Integer)
    tipo_refrigerante = Column(String(100))
    capacidad_refrigerante = Column(Numeric(4, 2))
    tipo_liquido_frenos = Column(String(50))
    especificaciones_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_modelo_anio_unique', 'modelo_id', 'anio', unique=True),
    )
    
    # Relationships
    modelo = relationship("ModeloVehiculo", back_populates="especificaciones")

class VehiculoCliente(Base):
    __tablename__ = "vehiculos_cliente"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), index=True)
    placa = Column(String(20), unique=True, nullable=False, index=True)
    marca_id = Column(Integer, ForeignKey("marcas_vehiculos.id"))
    modelo_id = Column(Integer, ForeignKey("modelos_vehiculos.id"))
    anio = Column(Integer, nullable=False)
    color = Column(String(50))
    kilometraje_actual = Column(Integer)
    fecha_ultima_revision = Column(Date)
    vin = Column(String(50), unique=True)
    apodo = Column(String(100))
    es_principal = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    cliente = relationship("Cliente", back_populates="vehiculos")
    servicios = relationship("Servicio", back_populates="vehiculo")

# ============================================
# 4. INSUMOS
# ============================================

class CategoriaInsumo(Base):
    __tablename__ = "categorias_insumos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    insumos = relationship("Insumo", back_populates="categoria")

class MarcaInsumo(Base):
    __tablename__ = "marcas_insumos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    logo_url = Column(String(500))
    pais_origen = Column(String(100))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    insumos = relationship("Insumo", back_populates="marca")

class Insumo(Base):
    __tablename__ = "insumos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey("categorias_insumos.id"))
    marca_id = Column(Integer, ForeignKey("marcas_insumos.id"))
    codigo_interno = Column(String(50), unique=True)
    codigo_barras = Column(String(50))
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    presentacion = Column(String(100))
    unidad_medida = Column(String(20))
    stock_actual = Column(Numeric(10, 2), default=0)
    stock_minimo = Column(Numeric(10, 2), default=0)
    stock_maximo = Column(Numeric(10, 2), default=0)
    precio_compra = Column(Numeric(10, 2))
    precio_venta = Column(Numeric(10, 2))
    precio_publico = Column(Numeric(10, 2))
    imagen_url = Column(String(500))
    requiere_refrigeracion = Column(Boolean, default=False)
    fecha_vencimiento = Column(Date)
    proveedor_principal = Column(String(255))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    tipo_recomendacion = Column(String(50))
    
    # Relationships
    categoria = relationship("CategoriaInsumo", back_populates="insumos")
    marca = relationship("MarcaInsumo", back_populates="insumos")
    movimientos = relationship("MovimientoInventario", back_populates="insumo")

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    tipo_movimiento = Column(Enum(TipoMovimientoEnum), nullable=False)
    cantidad = Column(Numeric(10, 2), nullable=False)
    cantidad_anterior = Column(Numeric(10, 2))
    cantidad_nueva = Column(Numeric(10, 2))
    motivo = Column(String(255))
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    documento_referencia = Column(String(100))
    notas = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    insumo = relationship("Insumo", back_populates="movimientos")

# ============================================
# 5. SERVICIOS
# ============================================

# NOTA (MITA): Estas dos clases legacy (tablas plurales `categorias_servicios` /
# `tipos_servicios`) pertenecen al flujo original agendado (Servicio ↔ TipoServicioLegacy).
# El sistema MITA usa las nuevas clases CategoriaServicio / TipoServicio (tablas
# singulares `categorias_servicio` / `tipos_servicio`) definidas más abajo.
# Se renombraron a *Legacy para evitar colisión de nombres; los nombres de tabla NO cambian.
class CategoriaServicioLegacy(Base):
    __tablename__ = "categorias_servicios"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    icono = Column(String(50))
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tipos = relationship("TipoServicioLegacy", back_populates="categoria")

class TipoServicioLegacy(Base):
    __tablename__ = "tipos_servicios"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey("categorias_servicios.id"))
    codigo = Column(String(50), unique=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    duracion_estimada_horas = Column(Numeric(4, 2), nullable=False)
    intervalo_minutos = Column(Integer, nullable=False)
    precio_base = Column(Numeric(10, 2), nullable=False)
    incluye_materiales = Column(Boolean, default=False)
    requiere_vehiculo = Column(Boolean, default=True)
    imagen_url = Column(String(500))
    icono = Column(String(50))
    activo = Column(Boolean, default=True)
    orden_display = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    categoria = relationship("CategoriaServicioLegacy", back_populates="tipos")
    servicios = relationship("Servicio", back_populates="tipo_servicio")

class Servicio(Base):
    __tablename__ = "servicios"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), index=True)
    beneficiario_nombre = Column(String(255))
    beneficiario_telefono = Column(String(20))
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"), index=True)
    tipo_servicio_id = Column(Integer, ForeignKey("tipos_servicios.id"))
    vehiculo_id = Column(Integer, ForeignKey("vehiculos_cliente.id"))
    ubicacion_id = Column(Integer, ForeignKey("ubicaciones_cliente.id"))
    fecha_programada = Column(Date, nullable=False, index=True)
    hora_programada = Column(Time, nullable=False)
    fecha_inicio_real = Column(DateTime(timezone=True))
    fecha_fin_real = Column(DateTime(timezone=True))
    estado = Column(Enum(EstadoServicioEnum), default=EstadoServicioEnum.programado, index=True)
    estado_pago = Column(Enum(EstadoPagoServicioEnum))
    monto_servicio = Column(Numeric(10, 2), nullable=False)
    monto_materiales = Column(Numeric(10, 2), default=0)
    monto_adicionales = Column(Numeric(10, 2), default=0)
    monto_descuento = Column(Numeric(10, 2), default=0)
    monto_total = Column(Numeric(10, 2), nullable=False)
    cupon_aplicado_id = Column(Integer, ForeignKey("cupones.id"))
    notas_cliente = Column(Text)
    notas_tecnico = Column(Text)
    notas_admin = Column(Text)
    calificacion_cliente = Column(Integer)
    comentario_cliente = Column(Text)
    fecha_calificacion = Column(DateTime(timezone=True))
    tiempo_busqueda_segundos = Column(Integer)
    motivo_cancelacion = Column(Text)
    cancelado_por = Column(Enum('cliente', 'tecnico', 'admin', 'sistema', name='cancelado_por_enum'))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint('calificacion_cliente >= 1 AND calificacion_cliente <= 5'),
    )
    
    # Relationships
    cliente = relationship("Cliente", back_populates="servicios")
    tecnico = relationship("Tecnico", back_populates="servicios")
    tipo_servicio = relationship("TipoServicioLegacy", back_populates="servicios")
    vehiculo = relationship("VehiculoCliente", back_populates="servicios")
    ubicacion = relationship("UbicacionCliente", back_populates="servicios")
    pago = relationship("Pago", back_populates="servicio", uselist=False)
    insumos_utilizados = relationship("ServicioInsumoUtilizado", back_populates="servicio")
    mensajes = relationship("MensajeChat", back_populates="servicio")
    notificaciones = relationship("Notificacion", back_populates="servicio")

class ServicioInsumoUtilizado(Base):
    __tablename__ = "servicios_insumos_utilizados"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id", ondelete="CASCADE"))
    insumo_id = Column(Integer, ForeignKey("insumos.id"))
    cantidad = Column(Numeric(10, 2), nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    servicio = relationship("Servicio", back_populates="insumos_utilizados")

# ============================================
# 6. COMISIONES Y PRECIOS
# ============================================

class EsquemaComision(Base):
    __tablename__ = "esquemas_comision"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    tipo_comision = Column(Enum('porcentaje', 'fijo', 'escalonado', name='tipo_comision_enum'))
    valor_base = Column(Numeric(10, 2))
    aplica_a = Column(Enum('todos', 'categoria', 'tipo_servicio', 'tecnico', name='aplica_a_enum'))
    categoria_id = Column(Integer, ForeignKey("categorias_servicios.id"))
    tipo_servicio_id = Column(Integer, ForeignKey("tipos_servicios.id"))
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    comisiones = relationship("ComisionTecnico", back_populates="esquema")

class ComisionTecnico(Base):
    __tablename__ = "comisiones_tecnico"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"))
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    esquema_id = Column(Integer, ForeignKey("esquemas_comision.id"))
    monto_servicio = Column(Numeric(10, 2), nullable=False)
    porcentaje = Column(Numeric(5, 2), nullable=False)
    monto_comision = Column(Numeric(10, 2), nullable=False)
    estado = Column(Enum('pendiente', 'pagado', 'retenido', name='estado_comision_enum'))
    fecha_pago = Column(Date)
    comprobante_pago = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tecnico = relationship("Tecnico", back_populates="comisiones")
    esquema = relationship("EsquemaComision", back_populates="comisiones")

class PrecioDinamico(Base):
    __tablename__ = "precios_dinamicos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    tipo_servicio_id = Column(Integer, ForeignKey("tipos_servicios.id"))
    distrito = Column(String(100))
    dia_semana = Column(Integer)
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
    tipo_ajuste = Column(Enum('descuento', 'recargo', name='tipo_ajuste_enum'))
    porcentaje = Column(Numeric(5, 2))
    monto_fijo = Column(Numeric(10, 2))
    motivo = Column(String(255))
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint('dia_semana >= 0 AND dia_semana <= 6'),
    )

# ============================================
# 7. MARKETING
# ============================================

class Cupon(Base):
    __tablename__ = "cupones"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(255))
    descripcion = Column(Text)
    tipo_descuento = Column(Enum('porcentaje', 'monto_fijo', name='tipo_descuento_enum'))
    valor = Column(Numeric(10, 2), nullable=False)
    monto_minimo = Column(Numeric(10, 2))
    monto_maximo_desc = Column(Numeric(10, 2))
    usos_maximos = Column(Integer)
    usos_actuales = Column(Integer, default=0)
    usos_por_cliente = Column(Integer, default=1)
    categorias_aplica = Column(ARRAY(Integer))
    tipos_aplica = Column(ARRAY(Integer))
    fecha_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_fin = Column(DateTime(timezone=True))
    solo_primer_servicio = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    usos = relationship("CuponUsado", back_populates="cupon")

class CuponUsado(Base):
    __tablename__ = "cupones_usados"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    cupon_id = Column(Integer, ForeignKey("cupones.id"))
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    descuento = Column(Numeric(10, 2))
    usado_en = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    cupon = relationship("Cupon", back_populates="usos")
    cliente = relationship("Cliente", back_populates="cupones_usados")

# ============================================
# 8. PAGOS
# ============================================

class Pago(Base):
    __tablename__ = "pagos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    metodo_pago = Column(Enum(MetodoPagoEnum))
    estado = Column(Enum(EstadoPagoEnum), index=True)
    monto = Column(Numeric(10, 2), nullable=False)
    comision_pasarela = Column(Numeric(10, 2))
    monto_neto = Column(Numeric(10, 2))
    transaccion_id = Column(String(255))
    culqi_charge_id = Column(String(255))
    comprobante_url = Column(String(500))
    numero_operacion = Column(String(100))
    ip_address = Column(INET)
    user_agent = Column(Text)
    fecha_pago = Column(DateTime(timezone=True), index=True)
    confirmado_por_id = Column(Integer, ForeignKey("usuarios.id"))
    fecha_confirmacion = Column(DateTime(timezone=True))
    motivo_rechazo = Column(Text)
    pago_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    servicio = relationship("Servicio", back_populates="pago")

# ============================================
# 9. NOTIFICACIONES Y MENSAJES
# ============================================

class Notificacion(Base):
    __tablename__ = "notificaciones"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    titulo = Column(String(255))
    mensaje = Column(Text)
    tipo = Column(Enum('info', 'success', 'warning', 'error', 'servicio', name='tipo_notif_enum'))
    leida = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    usuario = relationship("Usuario", back_populates="notificaciones")
    servicio = relationship("Servicio", back_populates="notificaciones")

class MensajeChat(Base):
    __tablename__ = "mensajes_chat"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    servicio_id = Column(Integer, ForeignKey("servicios.id"))
    remitente_id = Column(Integer, ForeignKey("usuarios.id"))
    contenido = Column(Text)
    tipo = Column(Enum('texto', 'imagen', 'audio', 'ubicacion', 'sistema', name='tipo_mensaje_enum'))
    leido = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    servicio = relationship("Servicio", back_populates="mensajes")

# ============================================
# 10. AUDITORÍA
# ============================================

class LogCambio(Base):
    __tablename__ = "log_cambios"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    tabla = Column(String(100), nullable=False)
    registro_id = Column(Integer, nullable=False)
    accion = Column(Enum('INSERT', 'UPDATE', 'DELETE', name='accion_enum'))
    campos_previos = Column(JSONB)
    campos_nuevos = Column(JSONB)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    ip_address = Column(INET)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SesionUsuario(Base):
    __tablename__ = "sesiones_usuario"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    token = Column(String(500), unique=True)
    ip_address = Column(INET)
    user_agent = Column(Text)
    fecha_inicio = Column(DateTime(timezone=True), server_default=func.now())
    fecha_fin = Column(DateTime(timezone=True))
    activa = Column(Boolean, default=True)
    
    # Relationships
    usuario = relationship("Usuario", back_populates="sesiones")

# ============================================
# 11. ANALÍTICA
# ============================================

class MetricaDiaria(Base):
    __tablename__ = "metricas_diarias"
    __table_args__ = {'extend_existing': True}
    
    fecha = Column(Date, primary_key=True)
    total_servicios = Column(Integer, default=0)
    servicios_completados = Column(Integer, default=0)
    servicios_cancelados = Column(Integer, default=0)
    revenue_total = Column(Numeric(12, 2), default=0)
    revenue_servicios = Column(Numeric(12, 2), default=0)
    revenue_materiales = Column(Numeric(12, 2), default=0)
    nuevos_clientes = Column(Integer, default=0)
    nuevos_tecnicos = Column(Integer, default=0)
    rating_promedio = Column(Numeric(3, 2))
    tiempo_respuesta_avg = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MetricaTecnicoMensual(Base):
    __tablename__ = "metricas_tecnico_mensual"
    __table_args__ = {'extend_existing': True}
    
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"), primary_key=True)
    anio = Column(Integer, primary_key=True)
    mes = Column(Integer, primary_key=True)
    servicios_completados = Column(Integer)
    servicios_cancelados = Column(Integer)
    ingresos_brutos = Column(Numeric(10, 2))
    comisiones_pagadas = Column(Numeric(10, 2))
    rating_promedio = Column(Numeric(3, 2))


# ============================================
# 12. PROVEEDORES
# ============================================

class Proveedor(Base):
    __tablename__ = "proveedores"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    ruc = Column(String(11), unique=True, nullable=False, index=True)
    razon_social = Column(String(255), nullable=False)
    nombre_comercial = Column(String(255))
    contacto_nombre = Column(String(255))
    contacto_cargo = Column(String(100))
    contacto_telefono = Column(String(20))
    contacto_email = Column(String(255))
    direccion = Column(String(500))
    distrito = Column(String(100))
    departamento = Column(String(100))
    condiciones_pago = Column(String(255))  # "30 días", "Contado", etc
    descuento_volumen = Column(Numeric(5, 2))  # Porcentaje
    plazo_entrega_dias = Column(Integer)
    calificacion = Column(Numeric(3, 2))  # Rating 1-5
    notas = Column(Text)
    activo = Column(Boolean, default=True)
    verificado = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    almacenes = relationship("Almacen", back_populates="responsable")
    #stock_items = relationship("StockAlmacen", back_populates="proveedor")


# ============================================
# 13. ALMACENES E INVENTARIO
# ============================================

class Almacen(Base):
    __tablename__ = "almacenes"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(20), unique=True)
    tipo = Column(String(50))  # 'principal', 'movil', 'tecnico'
    direccion = Column(String(500))
    distrito = Column(String(100))
    departamento = Column(String(100))
    referencia = Column(Text)
    latitud = Column(Numeric(10, 8))
    longitud = Column(Numeric(11, 8))
    responsable_id = Column(Integer, ForeignKey("proveedores.id"))
    telefono = Column(String(20))
    capacidad_m3 = Column(Numeric(10, 2))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    responsable = relationship("Proveedor", back_populates="almacenes")
    stock = relationship("StockAlmacen", back_populates="almacen")


class StockAlmacen(Base):
    __tablename__ = "stock_almacen"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    almacen_id = Column(Integer, ForeignKey("almacenes.id"), nullable=False, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    cantidad = Column(Numeric(10, 2), nullable=False, default=0)
    stock_minimo = Column(Numeric(10, 2))
    stock_maximo = Column(Numeric(10, 2))
    ubicacion_fisica = Column(String(100))  # "Estante A-3", "Zona B", etc
    ultima_entrada = Column(DateTime(timezone=True))
    ultima_salida = Column(DateTime(timezone=True))
    ultima_actualizacion = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_almacen_insumo_unique', 'almacen_id', 'insumo_id', unique=True),
    )
    
    # Relationships
    almacen = relationship("Almacen", back_populates="stock")
    insumo = relationship("Insumo", foreign_keys=[insumo_id])
    #proveedor = relationship("Proveedor", back_populates="stock_items")


# ============================================
# 14. RECOMENDACIONES ACEITE
# ============================================

class RecomendacionAceite(Base):
    __tablename__ = "recomendaciones_aceite"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    marca_vehiculo_id = Column(Integer, ForeignKey("marcas_vehiculos.id"), index=True)
    modelo_vehiculo_id = Column(Integer, ForeignKey("modelos_vehiculos.id"), index=True)
    anio_inicio = Column(Integer, nullable=False)
    anio_fin = Column(Integer, nullable=False)
    kilometraje_min = Column(Integer)
    kilometraje_max = Column(Integer)
    tipo_aceite = Column(String(50), nullable=False)  # 'Sintético', 'Semi-sintético', 'Mineral'
    viscosidad = Column(String(20), nullable=False)  # '5W-30', '10W-40', etc
    especificacion = Column(String(100))  # 'API SN', 'ACEA A3/B4'
    capacidad_litros = Column(Numeric(4, 2), nullable=False)
    marcas_aceite_recomendadas = Column(JSONB)  # Array de marcas: ["Mobil", "Castrol", "Shell"]
    filtro_aceite_referencia = Column(String(100))
    filtro_aire_referencia = Column(String(100))
    filtro_combustible_referencia = Column(String(100))
    notas = Column(Text)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("usuarios.id"))
    
    __table_args__ = (
        Index('idx_marca_modelo_anio', 'marca_vehiculo_id', 'modelo_vehiculo_id', 'anio_inicio', 'anio_fin'),
    )
    
    # Relationships
    marca_vehiculo = relationship("MarcaVehiculo", foreign_keys=[marca_vehiculo_id])
    modelo_vehiculo = relationship("ModeloVehiculo", foreign_keys=[modelo_vehiculo_id])


# ============================================
# 15. SOLICITUD INSUMOS (RELACIÓN SOLICITUD ↔ PRODUCTOS)
# ============================================

class SolicitudInsumo(Base):
    __tablename__ = "solicitud_insumos"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    
    # Cantidad y precios
    cantidad = Column(Numeric(10, 2), nullable=False, default=1)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    descuento = Column(Numeric(5, 2), default=0)  # Porcentaje
    subtotal = Column(Numeric(10, 2), nullable=False)
    
    # Clasificación
    es_principal = Column(Boolean, default=False)  # Aceite principal del servicio
    es_recomendado = Column(Boolean, default=False)  # Sugerido por sistema
    es_adicional = Column(Boolean, default=False)  # Agregado por cliente/técnico
    
    # Agrupación para comprobante
    grupo_comprobante = Column(String(50))  # 'materiales_limpieza', 'filtros', etc
    orden = Column(Integer, default=0)
    
    # Estado
    estado = Column(String(20), default='pendiente')  # pendiente, confirmado, entregado
    confirmado_por = Column(String(50))  # 'cliente', 'tecnico', 'admin'
    
    # Metadatos
    notas = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    insumo = relationship("Insumo", foreign_keys=[insumo_id])


# ============================================
# 16. MITA - CATÁLOGO DE SERVICIOS TÉCNICOS
# Tablas singulares (categorias_servicio / tipos_servicio) — sistema nuevo MITA.
# Usadas por el flujo de solicitud genérico (SolicitudServicio anónima).
# ============================================

class CategoriaServicio(Base):
    __tablename__ = "categorias_servicio"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), unique=True)          # ELEC, GASF, ELDOM, ...
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    icono = Column(String(50), default="fas fa-tools")   # Font Awesome
    color = Column(String(20), default="#FFCD11")        # Hex color
    imagen_url = Column(String(255))
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    proximamente = Column(Boolean, default=False)        # Para sección "Próximamente"
    codigo_unspsc = Column(String(10))                   # zMita-13: facturación SUNAT/UNSPSC
    descripcion_unspsc = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tipos = relationship("TipoServicio", back_populates="categoria")


class TipoServicio(Base):
    __tablename__ = "tipos_servicio"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey("categorias_servicio.id"))
    codigo = Column(String(30), unique=True)          # ELEC-TOMA, GASF-FUGA, ...
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    precio_visita = Column(Numeric(10, 2), default=50.00)
    duracion_estimada_min = Column(Integer, default=60)
    requiere_materiales = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    # zMita-13
    codigo_unspsc = Column(String(10))
    precio_fijo = Column(Numeric(10, 2))          # NULL = requiere cotización
    tiempo_estimado_min = Column(Integer)
    descripcion_cliente = Column(Text)            # lo que ve el cliente
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    categoria = relationship("CategoriaServicio", back_populates="tipos")


class ReporteTecnico(Base):
    """Reporte que emite el técnico tras atender una solicitud MITA."""
    __tablename__ = "reportes_tecnico"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    # OJO: la tabla real de solicitudes es `solicitudes_servicio` (no `solicitudes`)
    solicitud_id = Column(Integer, ForeignKey("solicitudes_servicio.id"), nullable=False, index=True)
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"), nullable=False, index=True)

    # Diagnóstico
    diagnostico = Column(Text, nullable=False)
    causa_problema = Column(Text)
    solucion_aplicada = Column(Text)

    # Trabajo adicional
    hubo_trabajo_adicional = Column(Boolean, default=False)
    descripcion_trabajo_adicional = Column(Text)
    tiempo_trabajo_min = Column(Integer)

    # Costos adicionales
    monto_mano_obra = Column(Numeric(10, 2), default=0)
    monto_materiales = Column(Numeric(10, 2), default=0)
    detalle_materiales = Column(JSONB)  # [{nombre, cantidad, precio}]
    monto_total_adicional = Column(Numeric(10, 2), default=0)

    # Forma de pago del adicional
    metodo_pago_adicional = Column(String(50))
    cobrado_por_tecnico = Column(Boolean, default=True)

    # Comprobante del técnico
    tecnico_emitio_comprobante = Column(Boolean, default=False)
    tipo_comprobante_tecnico = Column(String(20))   # RHE, boleta, factura
    numero_comprobante_tecnico = Column(String(50))

    # Fotos del trabajo
    fotos_antes = Column(ARRAY(Text))
    fotos_despues = Column(ARRAY(Text))

    # Observaciones
    observaciones = Column(Text)
    requiere_seguimiento = Column(Boolean, default=False)
    motivo_seguimiento = Column(Text)

    # Timestamps
    fecha_reporte = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())