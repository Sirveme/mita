-- 34_servicio_vivo.sql (zMita-38) — Etapas 5-6: en camino, chat de 3 y presupuesto. Idempotente.

CREATE TABLE IF NOT EXISTS ubicaciones_servicio (
    id            SERIAL PRIMARY KEY,
    solicitud_id  INTEGER NOT NULL,
    tecnico_id    INTEGER,
    lat           NUMERIC(10,8) NOT NULL,
    lng           NUMERIC(11,8) NOT NULL,
    precision_m   NUMERIC(8,2),
    registrada_en TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ubiserv_sol ON ubicaciones_servicio (solicitud_id);
CREATE INDEX IF NOT EXISTS ix_ubiserv_reg ON ubicaciones_servicio (registrada_en);

CREATE TABLE IF NOT EXISTS mensajes_servicio (
    id              SERIAL PRIMARY KEY,
    solicitud_id    INTEGER NOT NULL,
    autor_rol       VARCHAR(10) NOT NULL,
    autor_id        INTEGER,
    tipo            VARCHAR(12) DEFAULT 'texto',
    contenido       TEXT,
    oculto_dato     BOOLEAN DEFAULT FALSE,
    creado_en       TIMESTAMP DEFAULT NOW(),
    leido_cliente_en TIMESTAMP,
    leido_tecnico_en TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_msgserv_sol ON mensajes_servicio (solicitud_id);

CREATE TABLE IF NOT EXISTS presupuestos (
    id                  SERIAL PRIMARY KEY,
    solicitud_id        INTEGER NOT NULL,
    version             INTEGER DEFAULT 1,
    diagnostico         TEXT NOT NULL,
    requiere_reparacion BOOLEAN DEFAULT FALSE,
    descripcion_trabajo TEXT,
    monto               NUMERIC(10,2),
    incluye_materiales  BOOLEAN DEFAULT FALSE,
    materiales_detalle  TEXT,
    tiempo_estimado     VARCHAR(80),
    fotos               TEXT,
    estado              VARCHAR(14) DEFAULT 'propuesto',
    decidido_en         TIMESTAMP,
    decidido_por        VARCHAR(60),
    ip                  VARCHAR(60),
    ua                  VARCHAR(300),
    created_at          TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_presup_sol ON presupuestos (solicitud_id);

-- Columnas nuevas
ALTER TABLE tecnicos_personal ADD COLUMN IF NOT EXISTS disponible_hoy BOOLEAN DEFAULT FALSE;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS en_camino_desde TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS cliente_no_esta_en TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS eta_inicial_min INTEGER;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS eta_actual_min INTEGER;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS eta_calc_en TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS eta_calc_lat DOUBLE PRECISION;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS eta_calc_lng DOUBLE PRECISION;

-- Config de la etapa 6
INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES ('monto_revision_torre', '500', 'Presupuesto que la torre debe revisar (S/)'))
  AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
