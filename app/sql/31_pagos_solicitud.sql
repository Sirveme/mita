-- 31_pagos_solicitud.sql (zMita-34 v2) — Pago por QR Yape/Plin validado con PagoOK. Idempotente.

CREATE TABLE IF NOT EXISTS pagos_solicitud (
    id                   SERIAL PRIMARY KEY,
    solicitud_id         INTEGER NOT NULL,
    estado               VARCHAR(20) DEFAULT 'esperando_pago',
    canal                VARCHAR(20),
    monto_esperado       NUMERIC(10,2),
    titular_declarado    VARCHAR(150),
    codigo_operacion     VARCHAR(50),
    qr_mostrado_en       TIMESTAMP,
    fecha_hora_declarada TIMESTAMP,
    pago_id              INTEGER,
    nivel                VARCHAR(20),
    motivo               VARCHAR(60),
    contraparte          VARCHAR(150),
    fecha_hora_pago      TIMESTAMP,
    posible_reuso        BOOLEAN DEFAULT FALSE,
    confirmado_por       VARCHAR(20),
    referencia_externa   VARCHAR(150),
    respuesta_cruda      TEXT,
    comprador_nombre     VARCHAR(150),
    comprador_doc_tipo   VARCHAR(12),
    comprador_doc_numero VARCHAR(20),
    comprobante_estado   VARCHAR(20),
    comprobante_tipo     VARCHAR(12),
    comprobante_serie    VARCHAR(12),
    comprobante_numero   VARCHAR(20),
    comprobante_pdf      VARCHAR(300),
    intentos             INTEGER DEFAULT 0,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_pagosol_solicitud ON pagos_solicitud (solicitud_id);
CREATE INDEX IF NOT EXISTS ix_pagosol_estado    ON pagos_solicitud (estado);

-- Número/QR de MITA para el cobro (configurable en el panel)
INSERT INTO chat_conocimiento (clave, titulo, contenido, activo) VALUES
('pago_qr_numero', 'Número Yape/Plin de MITA para cobrar (solo dígitos)', '', FALSE),
('pago_qr_imagen', 'URL de la imagen del QR de MITA (Yape/Plin)', '', FALSE)
ON CONFLICT (clave) DO NOTHING;
