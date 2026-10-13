-- 27_politica_cancelacion.sql (zMita-30)
-- Política de cancelación editable por el dueño (vacía/inactiva hasta que la complete).

INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('politica_cancelacion', 'Política de cancelación (si el cliente cancela, con el técnico en camino)', '', FALSE)
ON CONFLICT (clave) DO NOTHING;
