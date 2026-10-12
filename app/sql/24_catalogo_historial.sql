-- 24_catalogo_historial.sql (zMita-23)
-- Historial de cambios del catálogo + parámetros de promoción de la visita.

CREATE TABLE IF NOT EXISTS catalogo_historial (
    id             SERIAL PRIMARY KEY,
    entidad        VARCHAR(50),
    entidad_id     VARCHAR(60),
    campo          VARCHAR(80),
    valor_anterior TEXT,
    valor_nuevo    TEXT,
    usuario_id     INTEGER,
    created_at     TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_catalogo_historial_entidad ON catalogo_historial (entidad);
CREATE INDEX IF NOT EXISTS idx_catalogo_historial_fecha   ON catalogo_historial (created_at);

-- Promoción de la tarifa de visita (vacía = sin promoción)
INSERT INTO configuracion_mita (clave, valor, tipo, descripcion, categoria) VALUES
('tarifa_visita_promo',       '0',  'float',  'Precio promocional de la visita (0 = sin promoción)', 'tarifas'),
('tarifa_visita_promo_desde', '',   'string', 'Inicio de la promoción (YYYY-MM-DD, vacío = sin límite)', 'tarifas'),
('tarifa_visita_promo_hasta', '',   'string', 'Fin de la promoción (YYYY-MM-DD, vacío = sin límite)', 'tarifas')
ON CONFLICT (clave) DO NOTHING;
