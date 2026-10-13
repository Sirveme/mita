-- 25_agenda.sql (zMita-25)
-- Fecha/hora agendada de la visita + semilla de la voz del asistente.

ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS fecha_programada TIMESTAMP;

INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('voz_asistente', 'Voz del asistente (Premium TTS): femenina | masculina', 'femenina', TRUE)
ON CONFLICT (clave) DO NOTHING;
