-- 30_push_envios_canal.sql (zMita-35) — Idempotente.
-- Diagnóstico de envíos, dedup por dispositivo, registro de entregas y canal de avisos.

-- Columnas nuevas en push_suscripciones
ALTER TABLE push_suscripciones ADD COLUMN IF NOT EXISTS dispositivo_id  VARCHAR(64);
ALTER TABLE push_suscripciones ADD COLUMN IF NOT EXISTS ultimo_codigo   INTEGER;
ALTER TABLE push_suscripciones ADD COLUMN IF NOT EXISTS ultimo_motivo   VARCHAR(120);
ALTER TABLE push_suscripciones ADD COLUMN IF NOT EXISTS ultimo_envio_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_push_dispositivo ON push_suscripciones (dispositivo_id);

-- Registro de envíos (entrega y demora)
CREATE TABLE IF NOT EXISTS push_envios (
    id             SERIAL PRIMARY KEY,
    aviso_id       VARCHAR(40) NOT NULL,
    suscripcion_id INTEGER,
    tag            VARCHAR(80),
    enviado_en     TIMESTAMP DEFAULT NOW(),
    codigo_http    INTEGER,
    recibido_en    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_envios_aviso    ON push_envios (aviso_id);
CREATE INDEX IF NOT EXISTS ix_envios_sus      ON push_envios (suscripcion_id);
CREATE INDEX IF NOT EXISTS ix_envios_enviado  ON push_envios (enviado_en);

-- Canal de avisos elegido por el cliente (push / whatsapp / ninguno)
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS canal_avisos VARCHAR(20);

-- Número de WhatsApp de MITA (configurable en el panel). Solo dígitos con código país, p.ej. 51987654321.
INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('whatsapp_numero', 'Número de WhatsApp de MITA (solo dígitos, con código país)', '', FALSE)
ON CONFLICT (clave) DO NOTHING;
