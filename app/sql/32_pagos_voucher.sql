-- 32_pagos_voucher.sql (zMita-36) — Hora del voucher (desempate C2) y puntaje de nombre. Idempotente.
ALTER TABLE pagos_solicitud ADD COLUMN IF NOT EXISTS hora_voucher TIMESTAMP;
ALTER TABLE pagos_solicitud ADD COLUMN IF NOT EXISTS puntaje      INTEGER;
