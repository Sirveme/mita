-- 40_pago_qr_titular.sql (zMita-44.1) — Titular del Yape/Plin (opcional) para la pantalla de pago. Idempotente.

INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('pago_qr_titular', 'Titular del Yape/Plin de MITA (opcional, se muestra al cliente)', '', FALSE)
ON CONFLICT (clave) DO NOTHING;
