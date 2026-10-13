-- 28_contacto_emergencias.sql (zMita-31)
-- Contacto para emergencias (lo muestra el chat cuando hoy ya no hay cupos y el caso es urgente).
-- Vacío/inactivo hasta que el dueño lo complete.

INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('contacto_emergencias', 'Contacto de emergencias (si hoy no hay cupos y el caso es urgente)', '', FALSE)
ON CONFLICT (clave) DO NOTHING;
