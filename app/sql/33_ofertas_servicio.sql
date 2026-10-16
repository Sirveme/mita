-- 33_ofertas_servicio.sql (zMita-37) — Oferta de servicio a técnicos. Idempotente.

CREATE TABLE IF NOT EXISTS ofertas_servicio (
    id            SERIAL PRIMARY KEY,
    solicitud_id  INTEGER NOT NULL,
    tecnico_id    INTEGER NOT NULL,
    enviada_en    TIMESTAMP DEFAULT NOW(),
    vista_en      TIMESTAMP,
    respuesta     VARCHAR(20),
    respondida_en TIMESTAMP,
    intento       INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_oferta_solicitud ON ofertas_servicio (solicitud_id);
CREATE INDEX IF NOT EXISTS ix_oferta_tecnico   ON ofertas_servicio (tecnico_id);

-- Columnas de la solicitud para la etapa 4 (si faltan)
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS aceptada_en TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS alerta_sin_aceptar_en TIMESTAMP;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS aviso_cliente_en TIMESTAMP;

-- Parámetros configurables (etapa 4). Valores por defecto; el dueño los ajusta en el panel.
INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES
  ('max_servicios_simultaneos', '1', 'Máximo de servicios en curso por técnico'),
  ('mostrar_direccion_antes_de_aceptar', 'false', 'Mostrar dirección exacta antes de aceptar'),
  ('minutos_alerta_sin_aceptar', '5', 'Minutos para alertar a la torre si nadie acepta'),
  ('minutos_reenvio', '5', 'Minutos para reenviar la oferta (una vez)'),
  ('minutos_aviso_cliente', '15', 'Minutos para avisar al cliente que seguimos buscando')
) AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
