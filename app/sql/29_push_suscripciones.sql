-- 29_push_suscripciones.sql (zMita-33)
-- Suscripciones Web Push (VAPID) por navegador/dispositivo. Idempotente.

CREATE TABLE IF NOT EXISTS push_suscripciones (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER,
    rol             VARCHAR(20),
    solicitud_id    INTEGER,
    endpoint        TEXT NOT NULL UNIQUE,
    p256dh          VARCHAR(255) NOT NULL,
    auth            VARCHAR(255) NOT NULL,
    plataforma      VARCHAR(20),
    user_agent      VARCHAR(400),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    ultimo_envio_ok TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_push_usuario   ON push_suscripciones (usuario_id);
CREATE INDEX IF NOT EXISTS ix_push_solicitud ON push_suscripciones (solicitud_id);
CREATE INDEX IF NOT EXISTS ix_push_rol       ON push_suscripciones (rol);
CREATE INDEX IF NOT EXISTS ix_push_activo    ON push_suscripciones (activo);
