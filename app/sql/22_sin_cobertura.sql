-- 22_sin_cobertura.sql (zMita-16)
-- Registra intentos de solicitud en distritos sin cobertura, para análisis de expansión.

CREATE TABLE IF NOT EXISTS solicitudes_sin_cobertura (
    id                  SERIAL PRIMARY KEY,
    distrito_solicitado VARCHAR(100) NOT NULL,
    direccion_ingresada TEXT,
    lat                 DECIMAL(10, 8),
    lng                 DECIMAL(11, 8),
    cliente_id          INTEGER REFERENCES personal(id),
    area_servicio_id    INTEGER,
    problema_id         INTEGER,
    descripcion         TEXT,
    creado_en           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sin_cobertura_distrito ON solicitudes_sin_cobertura (distrito_solicitado);
CREATE INDEX IF NOT EXISTS idx_sin_cobertura_fecha    ON solicitudes_sin_cobertura (creado_en);
