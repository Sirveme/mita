-- 39_umbral_boleta.sql (zMita-44) — Umbral para exigir documento en la boleta. Idempotente.

INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES ('umbral_boleta_identificada', '700',
              'Monto desde el cual la boleta exige documento del comprador (S/)'))
  AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
