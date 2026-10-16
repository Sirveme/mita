-- 38_liquidacion.sql (zMita-41) — Liquidación a técnicos (etapa 8) + historial de parámetros. Idempotente.

CREATE TABLE IF NOT EXISTS liquidaciones_mita (
    id                        SERIAL PRIMARY KEY,
    tecnico_id                INTEGER NOT NULL,
    periodo_inicio            DATE,
    periodo_fin               DATE,
    estado                    VARCHAR(20) DEFAULT 'borrador',
    cantidad_servicios        INTEGER DEFAULT 0,
    parte_tecnico             DOUBLE PRECISION DEFAULT 0,
    parte_mita                DOUBLE PRECISION DEFAULT 0,
    efectivo_en_poder_tecnico DOUBLE PRECISION DEFAULT 0,
    saldo_arrastrado          DOUBLE PRECISION DEFAULT 0,
    a_transferir              DOUBLE PRECISION DEFAULT 0,
    saldo_a_favor_mita        DOUBLE PRECISION DEFAULT 0,
    rxh_numero                VARCHAR(50),
    rxh_fecha                 DATE,
    rxh_monto                 DOUBLE PRECISION,
    rxh_pdf_url               TEXT,
    rxh_observacion           TEXT,
    retencion_activa          BOOLEAN DEFAULT FALSE,
    retencion_monto           DOUBLE PRECISION DEFAULT 0,
    neto_rxh                  DOUBLE PRECISION,
    pago_fecha                TIMESTAMP,
    pago_medio                VARCHAR(30),
    pago_operacion            VARCHAR(100),
    enviada_en                TIMESTAMP,
    aprobada_en               TIMESTAMP,
    creado_en                 TIMESTAMP DEFAULT NOW(),
    actualizado_en            TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_liqmita_tec ON liquidaciones_mita (tecnico_id);
CREATE INDEX IF NOT EXISTS ix_liqmita_periodo ON liquidaciones_mita (periodo_inicio);
CREATE INDEX IF NOT EXISTS ix_liqmita_estado ON liquidaciones_mita (estado);

CREATE TABLE IF NOT EXISTS liquidacion_items (
    id                SERIAL PRIMARY KEY,
    liquidacion_id    INTEGER REFERENCES liquidaciones_mita(id),
    solicitud_id      INTEGER,
    fecha_cierre      TIMESTAMP,
    codigo            VARCHAR(20),
    total             DOUBLE PRECISION,
    visita            DOUBLE PRECISION,
    reparacion        DOUBLE PRECISION,
    efectivo_tecnico  DOUBLE PRECISION DEFAULT 0,
    parte_mita        DOUBLE PRECISION,
    parte_tecnico     DOUBLE PRECISION,
    comision_tipo     VARCHAR(12),
    comision_valor    DOUBLE PRECISION,
    visita_parte_mita DOUBLE PRECISION,
    creado_en         TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_liqitem_liq ON liquidacion_items (liquidacion_id);
CREATE INDEX IF NOT EXISTS ix_liqitem_sol ON liquidacion_items (solicitud_id);

CREATE TABLE IF NOT EXISTS configuracion_historial (
    id            SERIAL PRIMARY KEY,
    clave         VARCHAR(80) NOT NULL,
    valor         TEXT,
    tipo          VARCHAR(12) DEFAULT 'string',
    vigente_desde TIMESTAMP DEFAULT NOW(),
    creado_por    VARCHAR(60),
    creado_en     TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_confhist_clave ON configuracion_historial (clave);
CREATE INDEX IF NOT EXISTS ix_confhist_vig ON configuracion_historial (vigente_desde);

-- Parámetros de liquidación (todos editables en el panel, con historial)
INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES
    ('visita_parte_mita', '15', 'Parte de MITA de la visita (S/)'),
    ('comision_reparacion_tipo', 'porcentaje', 'Comisión de reparación: porcentaje | fijo'),
    ('comision_reparacion_valor', '5', 'Comisión de reparación de MITA (porcentaje o S/ fijo)'),
    ('periodo_liquidacion', 'semanal', 'Periodo de liquidación: semanal | quincenal'),
    ('comision_medio_pago_asume', 'mita', 'Quién asume la comisión del medio de pago: mita | tecnico | compartida'),
    ('retencion_4ta_activa', 'false', 'Aplicar retención de 4ta categoría'),
    ('retencion_4ta_tasa', '8', 'Tasa de retención de 4ta por ciento'),
    ('retencion_4ta_umbral', '1500', 'Umbral por RxH para retener 4ta (S/)')
) AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
