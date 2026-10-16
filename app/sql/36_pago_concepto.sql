-- 36_pago_concepto.sql (zMita-40) — Cobro por concepto (visita/reparación). Idempotente.

ALTER TABLE pagos_solicitud ADD COLUMN IF NOT EXISTS concepto VARCHAR(12) DEFAULT 'visita';
CREATE INDEX IF NOT EXISTS ix_pagosol_concepto ON pagos_solicitud (concepto);

-- Config de la pasarela de tarjeta (Parte C): apagada hasta que opere para MITA.
INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES ('pasarela_activa', 'false', 'Cobro con tarjeta (pasarela) disponible para el cliente'))
  AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
