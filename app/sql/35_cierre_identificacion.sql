-- 35_cierre_identificacion.sql (zMita-39) — Etapa 2 (identificación) + etapa 7 (cierre/comprobante). Idempotente.

-- OTP de celular
CREATE TABLE IF NOT EXISTS codigos_verificacion (
    id          SERIAL PRIMARY KEY,
    celular     VARCHAR(15) NOT NULL,
    codigo      VARCHAR(6)  NOT NULL,
    expira_en   TIMESTAMP   NOT NULL,
    intentos    INTEGER     DEFAULT 0,
    usado       BOOLEAN     DEFAULT FALSE,
    enviado_por VARCHAR(30),
    created_at  TIMESTAMP   DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_codver_cel ON codigos_verificacion (celular);
CREATE INDEX IF NOT EXISTS ix_codver_creado ON codigos_verificacion (created_at);

-- Datos de facturación recordados por celular
CREATE TABLE IF NOT EXISTS compradores_preferidos (
    id               SERIAL PRIMARY KEY,
    celular          VARCHAR(15) UNIQUE NOT NULL,
    tipo_comprobante VARCHAR(12),
    doc_tipo         VARCHAR(12),
    doc_numero       VARCHAR(20),
    razon_social     VARCHAR(200),
    direccion_fiscal VARCHAR(255),
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

-- Comprobantes emitidos (idempotencia por solicitud + concepto)
CREATE TABLE IF NOT EXISTS comprobantes_emitidos (
    id           SERIAL PRIMARY KEY,
    solicitud_id INTEGER NOT NULL,
    concepto     VARCHAR(20) NOT NULL,   -- visita / reparacion
    tipo         VARCHAR(12),
    serie        VARCHAR(12),
    numero       VARCHAR(20),
    pdf_url      VARCHAR(300),
    monto        DOUBLE PRECISION,
    estado       VARCHAR(20) DEFAULT 'pendiente',
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_comprobante_sol_concepto UNIQUE (solicitud_id, concepto)
);
CREATE INDEX IF NOT EXISTS ix_compremit_sol ON comprobantes_emitidos (solicitud_id);

-- Cobro en efectivo con doble confirmación
CREATE TABLE IF NOT EXISTS cobros_efectivo (
    id               SERIAL PRIMARY KEY,
    solicitud_id     INTEGER NOT NULL,
    monto_total      DOUBLE PRECISION,
    monto_tecnico    DOUBLE PRECISION,
    monto_cliente    DOUBLE PRECISION,
    estado           VARCHAR(20) DEFAULT 'declarado',
    declarado_en     TIMESTAMP DEFAULT NOW(),
    validado_por     VARCHAR(60),
    motivo           TEXT,
    en_poder_tecnico BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_cobroef_sol ON cobros_efectivo (solicitud_id);
CREATE INDEX IF NOT EXISTS ix_cobroef_estado ON cobros_efectivo (estado);

-- Columnas nuevas en solicitudes (etapa 2 + etapa 7)
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS celular_verificado BOOLEAN DEFAULT FALSE;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS celular_estado VARCHAR(15) DEFAULT 'pendiente';
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS comprador_tipo_comprobante VARCHAR(12);
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS comprador_doc_tipo VARCHAR(12);
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS comprador_doc_numero VARCHAR(20);
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS comprador_nombre VARCHAR(200);
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS comprador_direccion_fiscal VARCHAR(255);
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS terminado_en TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS monto_por_cobrar DOUBLE PRECISION;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS cobro_metodo VARCHAR(12);
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS cobrado_en TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS cerrado_en TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS conformidad_ok BOOLEAN;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS conformidad_estrellas INTEGER;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS conformidad_comentario TEXT;

-- Config de la etapa 2/7
INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES
    ('otp_vigencia_seg', '300', 'Vigencia del código SMS (segundos)'),
    ('otp_max_envios_hora', '3', 'Máximo de códigos SMS por número por hora'),
    ('otp_max_intentos', '5', 'Máximo de intentos de verificación por código'),
    ('efectivo_minutos_torre', '30', 'Minutos sin confirmación del cliente antes de ir a la torre')
) AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
