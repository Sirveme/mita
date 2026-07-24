-- ============================================
-- MITA - Sistema de Reportes del Técnico
-- Ejecutar en Railway PostgreSQL
-- ============================================

-- ============================================
-- TABLA: solicitudes_servicio (actualizada)
-- NOTA (MITA): la tabla real del flujo de solicitud anónima es `solicitudes_servicio`
-- (modelo SolicitudServicio), NO `solicitudes`. Corregido a solicitudes_servicio.
-- ============================================

-- Agregar columnas nuevas a solicitudes_servicio si no existen
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS categoria_servicio_id INT REFERENCES categorias_servicio(id);
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS tipo_servicio_id INT REFERENCES tipos_servicio(id);
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS descripcion_problema TEXT;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS urgencia VARCHAR(20) DEFAULT 'normal'; -- normal, urgente, programado
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS fotos_problema TEXT[]; -- Array de URLs
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS precio_visita DECIMAL(10,2) DEFAULT 50.00;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS precio_trabajo_adicional DECIMAL(10,2) DEFAULT 0;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS precio_materiales DECIMAL(10,2) DEFAULT 0;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS precio_total DECIMAL(10,2) DEFAULT 50.00;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS comision_mita DECIMAL(10,2) DEFAULT 15.00;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS pago_tecnico DECIMAL(10,2) DEFAULT 35.00;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(50); -- izipay, yape, plin, efectivo
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(30) DEFAULT 'pendiente'; -- pendiente, pagado, reembolsado
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS comprobante_cliente_id INT; -- FK a facturalo_comprobantes
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS calificacion_cliente INT; -- 1-5 estrellas
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS comentario_cliente TEXT;
ALTER TABLE solicitudes_servicio ADD COLUMN IF NOT EXISTS fecha_calificacion TIMESTAMP;

-- ============================================
-- TABLA: reportes_tecnico
-- El técnico reporta el trabajo realizado
-- ============================================

CREATE TABLE IF NOT EXISTS reportes_tecnico (
    id SERIAL PRIMARY KEY,
    solicitud_id INT REFERENCES solicitudes_servicio(id) NOT NULL,
    tecnico_id INT REFERENCES tecnicos(id) NOT NULL,
    
    -- Diagnóstico
    diagnostico TEXT NOT NULL,
    causa_problema TEXT,
    solucion_aplicada TEXT,
    
    -- Trabajo adicional (si hubo)
    hubo_trabajo_adicional BOOLEAN DEFAULT FALSE,
    descripcion_trabajo_adicional TEXT,
    tiempo_trabajo_min INT, -- Minutos trabajados
    
    -- Costos adicionales
    monto_mano_obra DECIMAL(10,2) DEFAULT 0,
    monto_materiales DECIMAL(10,2) DEFAULT 0,
    detalle_materiales JSONB, -- [{nombre, cantidad, precio}]
    monto_total_adicional DECIMAL(10,2) DEFAULT 0,
    
    -- Forma de pago del adicional
    metodo_pago_adicional VARCHAR(50), -- efectivo, yape, plin, transferencia
    cobrado_por_tecnico BOOLEAN DEFAULT TRUE, -- TRUE si el técnico cobró directo
    
    -- Comprobante del técnico
    tecnico_emitio_comprobante BOOLEAN DEFAULT FALSE,
    tipo_comprobante_tecnico VARCHAR(20), -- RHE, boleta, factura
    numero_comprobante_tecnico VARCHAR(50),
    
    -- Fotos del trabajo
    fotos_antes TEXT[],
    fotos_despues TEXT[],
    
    -- Observaciones
    observaciones TEXT,
    requiere_seguimiento BOOLEAN DEFAULT FALSE,
    motivo_seguimiento TEXT,
    
    -- Timestamps
    fecha_reporte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_reportes_solicitud ON reportes_tecnico(solicitud_id);
CREATE INDEX IF NOT EXISTS idx_reportes_tecnico ON reportes_tecnico(tecnico_id);
CREATE INDEX IF NOT EXISTS idx_reportes_fecha ON reportes_tecnico(fecha_reporte);

-- ============================================
-- TABLA: historial_cliente
-- Historial técnico consolidado por cliente
-- ============================================

CREATE TABLE IF NOT EXISTS historial_cliente (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes(id) NOT NULL,
    direccion_id INT REFERENCES ubicaciones_cliente(id),
    
    -- Resumen de servicios
    total_servicios INT DEFAULT 0,
    total_gastado DECIMAL(12,2) DEFAULT 0,
    ultima_visita TIMESTAMP,
    
    -- Servicios más frecuentes (JSONB)
    servicios_frecuentes JSONB, -- [{categoria, tipo, cantidad}]
    
    -- Problemas recurrentes
    problemas_recurrentes JSONB, -- [{descripcion, fecha, veces}]
    
    -- Notas del técnico para futura referencia
    notas_tecnicas TEXT,
    
    -- Datos de la propiedad (para contexto)
    tipo_propiedad VARCHAR(50), -- casa, departamento, oficina, local
    antiguedad_propiedad VARCHAR(50), -- nueva, 1-5 años, 5-10 años, más de 10 años
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_historial_cliente ON historial_cliente(cliente_id);

-- ============================================
-- TABLA: estadisticas_servicio
-- Para análisis y alianzas futuras
-- ============================================

CREATE TABLE IF NOT EXISTS estadisticas_servicio (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    categoria_id INT REFERENCES categorias_servicio(id),
    tipo_servicio_id INT REFERENCES tipos_servicio(id),
    distrito VARCHAR(100),
    
    -- Contadores
    total_solicitudes INT DEFAULT 0,
    total_completados INT DEFAULT 0,
    total_cancelados INT DEFAULT 0,
    
    -- Montos
    ingresos_visitas DECIMAL(12,2) DEFAULT 0,
    ingresos_adicionales DECIMAL(12,2) DEFAULT 0,
    ingresos_totales DECIMAL(12,2) DEFAULT 0,
    
    -- Tiempos promedio
    tiempo_respuesta_avg_min INT,
    tiempo_trabajo_avg_min INT,
    
    -- Materiales más usados (para alianzas)
    materiales_usados JSONB, -- [{nombre, cantidad, precio_promedio}]
    
    -- Calificaciones
    calificacion_promedio DECIMAL(3,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice único para evitar duplicados
CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_fecha_cat_tipo_distrito 
ON estadisticas_servicio(fecha, categoria_id, tipo_servicio_id, distrito);

-- ============================================
-- VISTA: resumen_diario_mita
-- Para dashboard administrativo
-- ============================================

CREATE OR REPLACE VIEW resumen_diario_mita AS
SELECT 
    DATE(s.created_at) as fecha,
    c.nombre as categoria,
    COUNT(*) as total_solicitudes,
    COUNT(CASE WHEN s.estado = 'completado' THEN 1 END) as completados,
    COUNT(CASE WHEN s.estado = 'cancelado' THEN 1 END) as cancelados,
    SUM(s.comision_mita) as ingresos_mita,
    SUM(s.pago_tecnico) as pagos_tecnicos,
    AVG(s.calificacion_cliente) as calificacion_promedio
FROM solicitudes_servicio s
LEFT JOIN categorias_servicio c ON s.categoria_servicio_id = c.id
WHERE s.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(s.created_at), c.nombre
ORDER BY fecha DESC, categoria;

-- ============================================
-- FUNCIÓN: actualizar_historial_cliente
-- Se ejecuta después de cada reporte
-- ============================================
--
-- ⚠️ DESACTIVADO (MITA): este trigger asume que `solicitudes_servicio` tiene una
-- columna `cliente_id`, pero el flujo de solicitud MITA es ANÓNIMO y usa `usuario_id`
-- (puede ser NULL). Tal como está, fallaría al insertar en reportes_tecnico.
-- Requiere decisión de producto sobre cómo consolidar el historial cuando no hay
-- cliente registrado (¿por teléfono? ¿por usuario_id cuando exista?). Se deja
-- comentado para no romper el INSERT de reportes. Reactivar tras reconciliar el modelo.
--
-- CREATE OR REPLACE FUNCTION actualizar_historial_cliente()
-- RETURNS TRIGGER AS $$
-- DECLARE
--     v_cliente_id INT;
--     v_categoria_id INT;
--     v_tipo_servicio_id INT;
--     v_total_gastado DECIMAL(12,2);
-- BEGIN
--     -- Obtener datos de la solicitud
--     SELECT usuario_id, categoria_servicio_id, tipo_servicio_id
--     INTO v_cliente_id, v_categoria_id, v_tipo_servicio_id
--     FROM solicitudes_servicio
--     WHERE id = NEW.solicitud_id;
--
--     -- Calcular total gastado por el cliente
--     SELECT COALESCE(SUM(precio_total), 0)
--     INTO v_total_gastado
--     FROM solicitudes_servicio
--     WHERE usuario_id = v_cliente_id AND estado = 'completado';
--
--     -- Insertar o actualizar historial
--     INSERT INTO historial_cliente (cliente_id, total_servicios, total_gastado, ultima_visita)
--     VALUES (v_cliente_id, 1, v_total_gastado, NOW())
--     ON CONFLICT (cliente_id) DO UPDATE SET
--         total_servicios = historial_cliente.total_servicios + 1,
--         total_gastado = v_total_gastado,
--         ultima_visita = NOW(),
--         updated_at = NOW();
--
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;
--
-- DROP TRIGGER IF EXISTS trg_actualizar_historial ON reportes_tecnico;
-- CREATE TRIGGER trg_actualizar_historial
-- AFTER INSERT ON reportes_tecnico
-- FOR EACH ROW
-- EXECUTE FUNCTION actualizar_historial_cliente();

-- ============================================
-- VERIFICACIÓN FINAL
-- ============================================

SELECT 'Tablas creadas:' as info;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('reportes_tecnico', 'historial_cliente', 'estadisticas_servicio')
ORDER BY table_name;