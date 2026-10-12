-- 23_chat_conocimiento.sql (zMita-22)
-- Base de conocimiento editable para el chat IA (lo que no está en la BD).

CREATE TABLE IF NOT EXISTS chat_conocimiento (
    id         SERIAL PRIMARY KEY,
    clave      VARCHAR(60) UNIQUE NOT NULL,
    titulo     VARCHAR(150) NOT NULL,
    contenido  TEXT DEFAULT '',
    activo     BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Semilla con claves vacías e inactivas (el dueño las llena desde /admin/chat-conocimiento)
INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('horario_atencion',     'Horario de atención',                '', FALSE),
('tiempo_llegada',       'Tiempo estimado de llegada',         '', FALSE),
('garantia',             'Garantía del servicio',              '', FALSE),
('medios_pago',          'Medios de pago',                     '', FALSE),
('politica_diagnostico', 'Política de diagnóstico (¿se descuenta de la reparación?)', '', FALSE),
('que_incluye_visita',   'Qué incluye la visita técnica',      '', FALSE)
ON CONFLICT (clave) DO NOTHING;
