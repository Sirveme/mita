-- 21_ubicacion_tecnico.sql
-- Seguimiento en vivo del técnico (tipo Uber) + coordenadas del cliente.

CREATE TABLE IF NOT EXISTS ubicacion_tecnico (
    id             SERIAL PRIMARY KEY,
    solicitud_id   INTEGER REFERENCES solicitudes(id),
    tecnico_id     INTEGER REFERENCES personal(id),
    lat            DECIMAL(10, 8) NOT NULL,
    lng            DECIMAL(11, 8) NOT NULL,
    precision      DECIMAL(8, 2),
    velocidad      DECIMAL(8, 2),
    rumbo          DECIMAL(6, 2),
    actualizado_en TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ubicacion_solicitud ON ubicacion_tecnico (solicitud_id);
CREATE INDEX IF NOT EXISTS idx_ubicacion_solicitud ON ubicacion_tecnico (solicitud_id);

CREATE INDEX IF NOT EXISTS idx_ubicacion_tecnico ON ubicacion_tecnico (tecnico_id);

-- Coordenadas + dirección validada del cliente (Google Maps)
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS cliente_lat DOUBLE PRECISION;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS cliente_lng DOUBLE PRECISION;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS direccion_completa TEXT;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS direccion_validada BOOLEAN DEFAULT FALSE;
