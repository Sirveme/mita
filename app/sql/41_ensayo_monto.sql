-- 41_ensayo_monto.sql (zMita-45) — Monto distinto (C) + modo ensayo (D). Idempotente.

ALTER TABLE pagos_solicitud ADD COLUMN IF NOT EXISTS monto_recibido NUMERIC(10,2);
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS ensayo BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS clientes_prueba (
    id         SERIAL PRIMARY KEY,
    dni        VARCHAR(15),
    celular    VARCHAR(15),
    nota       VARCHAR(200),
    activo     BOOLEAN DEFAULT TRUE,
    creado_por VARCHAR(60),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_clipru_dni ON clientes_prueba (dni);
CREATE INDEX IF NOT EXISTS ix_clipru_cel ON clientes_prueba (celular);

INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES ('monto_ensayo', '1.00', 'Monto de visita/reparación para clientes de prueba (S/)'))
  AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
