-- 26_voz_config.sql (zMita-29)
-- Configuración de la voz del asistente (laboratorio de voces).

INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('voz_proveedor',     'Voz del asistente: proveedor (openai | azure | elevenlabs)', 'openai', TRUE),
('voz_id',            'Voz del asistente: id de la voz (p.ej. coral)',             'coral',  TRUE),
('voz_velocidad',     'Voz del asistente: velocidad (0.9 a 1.2)',                  '1.0',    TRUE),
('voz_instrucciones', 'Voz del asistente: instrucciones de estilo (OpenAI)',
 'Habla en español peruano de Lima, tono cálido y profesional, ritmo natural, cercano, sin sonar a locutor de radio.', TRUE)
ON CONFLICT (clave) DO NOTHING;
