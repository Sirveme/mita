-- 37_comprobante_sunat.sql (zMita-41) — Estado SUNAT real del comprobante + anulación por NC. Idempotente.

ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS numero_formato     VARCHAR(30);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS total              DOUBLE PRECISION;
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS simulado           BOOLEAN DEFAULT FALSE;
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS facturalo_id       VARCHAR(64);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS referencia_externa VARCHAR(100);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS codigo_sunat       VARCHAR(10);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS mensaje_sunat      TEXT;
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS hash_cpe           VARCHAR(100);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS emitido_en         TIMESTAMP;
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS ultima_consulta_en TIMESTAMP;
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS cliente_doc_tipo   VARCHAR(12);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS cliente_doc_numero VARCHAR(20);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS cliente_nombre     VARCHAR(200);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS nc_facturalo_id    VARCHAR(64);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS nc_numero_formato  VARCHAR(30);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS nc_estado          VARCHAR(20);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS anulado_en         TIMESTAMP;
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS anulado_por        VARCHAR(60);
ALTER TABLE comprobantes_emitidos ADD COLUMN IF NOT EXISTS anulado_motivo     TEXT;

CREATE INDEX IF NOT EXISTS ix_compr_estado ON comprobantes_emitidos (estado);
CREATE INDEX IF NOT EXISTS ix_compr_ref ON comprobantes_emitidos (referencia_externa);

-- Código de producto SUNAT por defecto (obligatorio desde 2027; por especialidad: sunat_codigo_cat_<id>)
INSERT INTO configuracion_mita (clave, valor, descripcion)
SELECT v.clave, v.valor, v.descripcion
FROM (VALUES ('sunat_codigo_default', '', 'Código de producto SUNAT por defecto (obligatorio 2027)'))
  AS v(clave, valor, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM configuracion_mita c WHERE c.clave = v.clave);
