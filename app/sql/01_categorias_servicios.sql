-- ============================================
-- MITA - Categorías de Servicios Técnicos
-- Ejecutar en Railway PostgreSQL
-- ============================================

-- Primero, actualizar la tabla categorias_servicio si existe
-- o crearla si no existe

-- Verificar si existe la tabla
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'categorias_servicio') THEN
        CREATE TABLE categorias_servicio (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            descripcion TEXT,
            icono VARCHAR(50) DEFAULT 'fas fa-tools',
            color VARCHAR(20) DEFAULT '#FFCD11',
            imagen_url VARCHAR(255),
            orden INT DEFAULT 0,
            activo BOOLEAN DEFAULT TRUE,
            proximamente BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    END IF;
END $$;

-- Agregar columnas si no existen
ALTER TABLE categorias_servicio ADD COLUMN IF NOT EXISTS codigo VARCHAR(20);
ALTER TABLE categorias_servicio ADD COLUMN IF NOT EXISTS icono VARCHAR(50) DEFAULT 'fas fa-tools';
ALTER TABLE categorias_servicio ADD COLUMN IF NOT EXISTS color VARCHAR(20) DEFAULT '#FFCD11';
ALTER TABLE categorias_servicio ADD COLUMN IF NOT EXISTS imagen_url VARCHAR(255);
ALTER TABLE categorias_servicio ADD COLUMN IF NOT EXISTS orden INT DEFAULT 0;
ALTER TABLE categorias_servicio ADD COLUMN IF NOT EXISTS proximamente BOOLEAN DEFAULT FALSE;

-- Limpiar datos anteriores si es necesario
-- DELETE FROM categorias_servicio;

-- Insertar categorías de servicios
INSERT INTO categorias_servicio (codigo, nombre, descripcion, icono, color, orden, activo, proximamente)
VALUES
    ('ELEC', 'Electricidad', 'Instalaciones, reparaciones eléctricas y revisión de tableros', 'fas fa-bolt', '#F59E0B', 1, TRUE, FALSE),
    ('GASF', 'Gasfitería', 'Reparación de fugas, instalación de grifería y destape de desagües', 'fas fa-faucet', '#3B82F6', 2, TRUE, FALSE),
    ('ELDOM', 'Electrodomésticos', 'Reparación de refrigeradoras, lavadoras, microondas y más', 'fas fa-tv', '#8B5CF6', 3, TRUE, FALSE),
    ('MUEB', 'Muebles e Instalaciones', 'Armado de muebles, instalación de cuadros, repisas y reparaciones', 'fas fa-couch', '#10B981', 4, TRUE, FALSE),
    ('ALBA', 'Albañilería', 'Trabajos menores, resane de paredes, mayólicas y pisos', 'fas fa-hard-hat', '#EF4444', 5, TRUE, FALSE),
    ('BOMB', 'Bombas de Agua', 'Reparación e instalación de bombas de agua y tanques', 'fas fa-water', '#06B6D4', 6, TRUE, FALSE),
    ('AUTO', 'Automotriz', 'Cambio de aceite, revisión de frenos, afinamiento a domicilio', 'fas fa-car', '#FFCD11', 99, TRUE, TRUE)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    icono = EXCLUDED.icono,
    color = EXCLUDED.color,
    orden = EXCLUDED.orden,
    activo = EXCLUDED.activo,
    proximamente = EXCLUDED.proximamente,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- TIPOS DE SERVICIO (subcategorías)
-- ============================================

-- Verificar si existe la tabla tipos_servicio
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tipos_servicio') THEN
        CREATE TABLE tipos_servicio (
            id SERIAL PRIMARY KEY,
            categoria_id INT REFERENCES categorias_servicio(id),
            codigo VARCHAR(30) UNIQUE NOT NULL,
            nombre VARCHAR(150) NOT NULL,
            descripcion TEXT,
            precio_visita DECIMAL(10,2) DEFAULT 50.00,
            duracion_estimada_min INT DEFAULT 60,
            requiere_materiales BOOLEAN DEFAULT FALSE,
            activo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    END IF;
END $$;

-- Agregar columnas si no existen
ALTER TABLE tipos_servicio ADD COLUMN IF NOT EXISTS codigo VARCHAR(30);
ALTER TABLE tipos_servicio ADD COLUMN IF NOT EXISTS precio_visita DECIMAL(10,2) DEFAULT 50.00;
ALTER TABLE tipos_servicio ADD COLUMN IF NOT EXISTS duracion_estimada_min INT DEFAULT 60;
ALTER TABLE tipos_servicio ADD COLUMN IF NOT EXISTS requiere_materiales BOOLEAN DEFAULT FALSE;

-- Insertar tipos de servicio por categoría

-- ELECTRICIDAD
INSERT INTO tipos_servicio (categoria_id, codigo, nombre, descripcion, precio_visita, duracion_estimada_min)
VALUES
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELEC'), 'ELEC-TOMA', 'Instalación de tomacorrientes', 'Instalación de tomacorrientes simples o dobles', 50.00, 45),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELEC'), 'ELEC-CORTO', 'Reparación de cortocircuitos', 'Diagnóstico y reparación de cortocircuitos', 50.00, 60),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELEC'), 'ELEC-LUM', 'Instalación de luminarias', 'Instalación de lámparas, arañas y focos', 50.00, 45),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELEC'), 'ELEC-TAB', 'Revisión de tablero eléctrico', 'Revisión y mantenimiento de tablero eléctrico', 50.00, 60),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELEC'), 'ELEC-INT', 'Instalación de interruptores', 'Cambio o instalación de interruptores', 50.00, 30),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELEC'), 'ELEC-OTRO', 'Otro problema eléctrico', 'Diagnóstico de problema eléctrico general', 50.00, 60)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion;

-- GASFITERÍA
INSERT INTO tipos_servicio (categoria_id, codigo, nombre, descripcion, precio_visita, duracion_estimada_min)
VALUES
    ((SELECT id FROM categorias_servicio WHERE codigo = 'GASF'), 'GASF-FUGA', 'Reparación de fugas', 'Detección y reparación de fugas de agua', 50.00, 60),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'GASF'), 'GASF-GRIF', 'Instalación de grifería', 'Instalación o cambio de grifos y llaves', 50.00, 45),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'GASF'), 'GASF-DEST', 'Destape de desagües', 'Destape de desagües y tuberías obstruidas', 50.00, 60),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'GASF'), 'GASF-INOD', 'Reparación de inodoros', 'Reparación o cambio de accesorios de inodoro', 50.00, 45),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'GASF'), 'GASF-TERM', 'Instalación de terma', 'Instalación de termas eléctricas o a gas', 50.00, 90),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'GASF'), 'GASF-OTRO', 'Otro problema de gasfitería', 'Diagnóstico de problema de gasfitería', 50.00, 60)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion;

-- ELECTRODOMÉSTICOS
INSERT INTO tipos_servicio (categoria_id, codigo, nombre, descripcion, precio_visita, duracion_estimada_min, requiere_materiales)
VALUES
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELDOM'), 'ELDOM-REF', 'Reparación de refrigeradora', 'Diagnóstico y reparación de refrigeradoras', 50.00, 90, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELDOM'), 'ELDOM-LAV', 'Reparación de lavadora', 'Diagnóstico y reparación de lavadoras', 50.00, 90, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELDOM'), 'ELDOM-MICRO', 'Reparación de microondas', 'Diagnóstico y reparación de microondas', 50.00, 60, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELDOM'), 'ELDOM-AC', 'Reparación de aire acondicionado', 'Diagnóstico y reparación de aire acondicionado', 50.00, 90, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELDOM'), 'ELDOM-COCI', 'Reparación de cocina', 'Diagnóstico y reparación de cocinas', 50.00, 60, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ELDOM'), 'ELDOM-OTRO', 'Otro electrodoméstico', 'Diagnóstico de electrodoméstico general', 50.00, 60, TRUE)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion;

-- MUEBLES E INSTALACIONES
INSERT INTO tipos_servicio (categoria_id, codigo, nombre, descripcion, precio_visita, duracion_estimada_min)
VALUES
    ((SELECT id FROM categorias_servicio WHERE codigo = 'MUEB'), 'MUEB-ARM', 'Armado de muebles', 'Armado de muebles de melanina o madera', 50.00, 120),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'MUEB'), 'MUEB-CUAD', 'Instalación de cuadros', 'Instalación de cuadros, espejos y decoración', 50.00, 45),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'MUEB'), 'MUEB-REP', 'Instalación de repisas', 'Instalación de repisas y estantes', 50.00, 60),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'MUEB'), 'MUEB-CORT', 'Instalación de cortinas', 'Instalación de barras y cortinas', 50.00, 60),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'MUEB'), 'MUEB-REPAR', 'Reparación de muebles', 'Reparación de muebles dañados', 50.00, 90),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'MUEB'), 'MUEB-OTRO', 'Otra instalación', 'Instalación general de elementos', 50.00, 60)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion;

-- ALBAÑILERÍA
INSERT INTO tipos_servicio (categoria_id, codigo, nombre, descripcion, precio_visita, duracion_estimada_min, requiere_materiales)
VALUES
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ALBA'), 'ALBA-RES', 'Resane de paredes', 'Resane y empastado de paredes', 50.00, 120, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ALBA'), 'ALBA-MAY', 'Instalación de mayólicas', 'Instalación de mayólicas y cerámicos', 50.00, 180, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ALBA'), 'ALBA-PISO', 'Reparación de pisos', 'Reparación de pisos dañados', 50.00, 120, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ALBA'), 'ALBA-PINT', 'Pintura de ambientes', 'Pintura de paredes y techos', 50.00, 240, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'ALBA'), 'ALBA-OTRO', 'Otro trabajo de albañilería', 'Trabajo menor de albañilería', 50.00, 120, TRUE)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion;

-- BOMBAS DE AGUA
INSERT INTO tipos_servicio (categoria_id, codigo, nombre, descripcion, precio_visita, duracion_estimada_min, requiere_materiales)
VALUES
    ((SELECT id FROM categorias_servicio WHERE codigo = 'BOMB'), 'BOMB-REP', 'Reparación de bomba', 'Diagnóstico y reparación de bomba de agua', 50.00, 90, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'BOMB'), 'BOMB-INST', 'Instalación de bomba', 'Instalación de bomba de agua nueva', 50.00, 120, TRUE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'BOMB'), 'BOMB-MANT', 'Mantenimiento de bomba', 'Mantenimiento preventivo de bomba', 50.00, 60, FALSE),
    ((SELECT id FROM categorias_servicio WHERE codigo = 'BOMB'), 'BOMB-TANQ', 'Instalación de tanque', 'Instalación de tanque elevado', 50.00, 180, TRUE)
ON CONFLICT (codigo) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion;

-- Verificar inserciones
SELECT 
    c.nombre AS categoria,
    COUNT(t.id) AS tipos_servicio
FROM categorias_servicio c
LEFT JOIN tipos_servicio t ON c.id = t.categoria_id
GROUP BY c.nombre, c.orden
ORDER BY c.orden;

-- Ver todos los tipos
SELECT 
    c.icono,
    c.nombre AS categoria,
    t.nombre AS tipo_servicio,
    t.precio_visita,
    t.duracion_estimada_min || ' min' AS duracion
FROM tipos_servicio t
JOIN categorias_servicio c ON t.categoria_id = c.id
ORDER BY c.orden, t.nombre;