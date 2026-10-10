-- SICOM-MUNI: datos de prueba (FICTICIOS). Generado por scripts/make_seeds.py
-- Contraseña de TODOS los usuarios de prueba: Sicom#2026Demo   (cámbiela de inmediato)
-- Es idempotente: puede ejecutarse varias veces.
BEGIN;

-- Usuarios (Argon2id)
INSERT INTO usuarios (id, username, password_hash, nombre_completo, cargo, rol, email, activo, intentos_fallidos) VALUES ('cd677a7e-1ca1-54d7-b769-04e7fcdf54c5', 'solicitante', '$argon2id$v=19$m=65536,t=3,p=4$1fRYg3LnIHMzfRu/U+hCbg$llRdl557q+n9QaoxG2qJBsUsKYUFHD058fBhgYyq+Og', 'María Lidia Quispe Mamani', 'Jefa de Unidad de Obras', 'ROL_SOLICITANTE', 'solicitante@gam.local', true, 0) ON CONFLICT (username) DO NOTHING;
INSERT INTO usuarios (id, username, password_hash, nombre_completo, cargo, rol, email, activo, intentos_fallidos) VALUES ('84dd45bb-363e-5ae0-b159-748f5a8307d0', 'presupuesto', '$argon2id$v=19$m=65536,t=3,p=4$1fRYg3LnIHMzfRu/U+hCbg$llRdl557q+n9QaoxG2qJBsUsKYUFHD058fBhgYyq+Og', 'Juan Carlos Mendoza Rojas', 'Responsable de Presupuesto', 'ROL_PRESUPUESTO', 'presupuesto@gam.local', true, 0) ON CONFLICT (username) DO NOTHING;
INSERT INTO usuarios (id, username, password_hash, nombre_completo, cargo, rol, email, activo, intentos_fallidos) VALUES ('ccf5c3f2-1f02-5932-a6c4-2a60fda42d1e', 'contrataciones', '$argon2id$v=19$m=65536,t=3,p=4$1fRYg3LnIHMzfRu/U+hCbg$llRdl557q+n9QaoxG2qJBsUsKYUFHD058fBhgYyq+Og', 'Rosario Elena Vargas Choque', 'Encargada de Compras Menores', 'ROL_CONTRATACIONES', 'compras@gam.local', true, 0) ON CONFLICT (username) DO NOTHING;
INSERT INTO usuarios (id, username, password_hash, nombre_completo, cargo, rol, email, activo, intentos_fallidos) VALUES ('d0c6d9c2-a64c-5364-b7f6-c78ff7721ae9', 'rpa', '$argon2id$v=19$m=65536,t=3,p=4$1fRYg3LnIHMzfRu/U+hCbg$llRdl557q+n9QaoxG2qJBsUsKYUFHD058fBhgYyq+Og', 'Ing. Fernando Luis Condori Apaza', 'Responsable del Proceso de Contratación', 'ROL_RPA', 'rpa@gam.local', true, 0) ON CONFLICT (username) DO NOTHING;
INSERT INTO usuarios (id, username, password_hash, nombre_completo, cargo, rol, email, activo, intentos_fallidos) VALUES ('f7ba2322-e95a-5fc9-a7bf-935d4be7a08d', 'recepcion', '$argon2id$v=19$m=65536,t=3,p=4$1fRYg3LnIHMzfRu/U+hCbg$llRdl557q+n9QaoxG2qJBsUsKYUFHD058fBhgYyq+Og', 'Pedro Pablo Mamani Flores', 'Responsable de Recepción y Almacenes', 'ROL_RECEPCION', 'almacen@gam.local', true, 0) ON CONFLICT (username) DO NOTHING;
INSERT INTO usuarios (id, username, password_hash, nombre_completo, cargo, rol, email, activo, intentos_fallidos) VALUES ('bc9e4029-f0c5-5052-bc06-a67fdd07f0e5', 'admin', '$argon2id$v=19$m=65536,t=3,p=4$1fRYg3LnIHMzfRu/U+hCbg$llRdl557q+n9QaoxG2qJBsUsKYUFHD058fBhgYyq+Og', 'Administrador del Sistema', 'Administrador', 'ROL_ADMIN', 'admin@gam.local', true, 0) ON CONFLICT (username) DO NOTHING;

-- Parámetros institucionales
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('nombre_gam', 'GOBIERNO AUTÓNOMO MUNICIPAL DE EJEMPLO', 'Nombre del GAM para el membrete de los documentos') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('ciudad', '', 'Ciudad que figura en los documentos') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('da', '01', 'Código de Dirección Administrativa (DA)') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('ue', '001', 'Código de Unidad Ejecutora (UE)') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('gestion', '2026', 'Gestión fiscal vigente') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('logo_url', '', 'URL o ruta del logotipo oficial') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('tope_contratacion_menor', '50000', 'Bs. Límite de Contratación Menor (verificar con la norma vigente)') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('tope_compra_directa', '20000', 'Bs. Hasta este monto: compra directa sin consulta de precios SICOES') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('plazo_orden_max_dias', '15', 'Días calendario: hasta este plazo se emite Orden; sobre él, Contrato') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('min_cotizaciones_consulta', '3', 'Cotizaciones mínimas con consulta de precios (supuesto; verificar)') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('min_cotizaciones_directa', '1', 'Cotizaciones mínimas en compra directa') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('chb_min_justificacion', '80', 'Longitud mínima de la justificación de excepción CHB') ON CONFLICT (clave) DO NOTHING;
INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ('url_publica', '', 'URL pública base para los QR de verificación (si vacío, usa PUBLIC_BASE_URL)') ON CONFLICT (clave) DO NOTHING;

-- Presupuesto inicial (partidas ilustrativas del clasificador 1xxxx a 4xxxx)
INSERT INTO partidas_presupuestarias (id, codigo_partida, descripcion, saldo_disponible, monto_aprobado, gestion, programa, proyecto, actividad, fuente, organismo) VALUES ('ee30b8b9-ca68-58e6-a828-8b070f69bed1', '39500', 'Útiles de escritorio y oficina', 30000.00, 30000.00, 2026, '01', '0000', '001', '20', '230') ON CONFLICT ON CONSTRAINT uq_partida_estructura DO NOTHING;
INSERT INTO partidas_presupuestarias (id, codigo_partida, descripcion, saldo_disponible, monto_aprobado, gestion, programa, proyecto, actividad, fuente, organismo) VALUES ('d6bc6d45-fb06-5a20-a62b-cd2bc3370762', '34200', 'Productos minerales y no metálicos (materiales de construcción)', 80000.00, 80000.00, 2026, '01', '0000', '001', '20', '230') ON CONFLICT ON CONSTRAINT uq_partida_estructura DO NOTHING;
INSERT INTO partidas_presupuestarias (id, codigo_partida, descripcion, saldo_disponible, monto_aprobado, gestion, programa, proyecto, actividad, fuente, organismo) VALUES ('bdd185de-2fa6-5ea6-9109-0b27b6b37624', '25800', 'Mantenimiento y reparación de inmuebles y equipos', 45000.00, 45000.00, 2026, '01', '0000', '001', '20', '230') ON CONFLICT ON CONSTRAINT uq_partida_estructura DO NOTHING;
INSERT INTO partidas_presupuestarias (id, codigo_partida, descripcion, saldo_disponible, monto_aprobado, gestion, programa, proyecto, actividad, fuente, organismo) VALUES ('018e4dbf-0a75-56f5-a847-5f7f96f87b60', '43100', 'Equipo de oficina y muebles', 60000.00, 60000.00, 2026, '01', '0000', '001', '20', '230') ON CONFLICT ON CONSTRAINT uq_partida_estructura DO NOTHING;

-- Catálogo Compro Hecho en Bolivia (EJEMPLO)
INSERT INTO catalogo_chb (id, codigo_unspsc, descripcion_bien, unidad_medida, precio_referencial_nacional, activo) VALUES ('93ad91e2-e52d-5e85-88f4-4e125e043c6f', '30111505', 'Cemento portland IP-30 (bolsa de 50 kg)', 'Bolsa', 58.00, true) ON CONFLICT (codigo_unspsc) DO NOTHING;
INSERT INTO catalogo_chb (id, codigo_unspsc, descripcion_bien, unidad_medida, precio_referencial_nacional, activo) VALUES ('33b842d2-e509-5776-be06-90b3370bb573', '30131501', 'Ladrillo cerámico de 6 huecos', 'Unidad', 1.20, true) ON CONFLICT (codigo_unspsc) DO NOTHING;
INSERT INTO catalogo_chb (id, codigo_unspsc, descripcion_bien, unidad_medida, precio_referencial_nacional, activo) VALUES ('8c08e945-d2e6-5d05-b9eb-7b36ddb28052', '14111507', 'Papel bond tamaño carta 75 g', 'Resma', 32.00, true) ON CONFLICT (codigo_unspsc) DO NOTHING;
INSERT INTO catalogo_chb (id, codigo_unspsc, descripcion_bien, unidad_medida, precio_referencial_nacional, activo) VALUES ('2493b78c-d04c-592c-80ec-6cd752b9f04c', '43211500', 'Computadora de escritorio', 'Unidad', 5200.00, true) ON CONFLICT (codigo_unspsc) DO NOTHING;
INSERT INTO catalogo_chb (id, codigo_unspsc, descripcion_bien, unidad_medida, precio_referencial_nacional, activo) VALUES ('f957410e-284d-55ab-9fb9-c622321bc184', '56101500', 'Escritorio metálico de oficina', 'Unidad', 850.00, true) ON CONFLICT (codigo_unspsc) DO NOTHING;

COMMIT;
