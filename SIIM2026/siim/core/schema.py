"""Esquema SQLite de SIIM 2026 (versión de esquema = len(MIGRATIONS))."""

M1 = """
CREATE TABLE parametros(clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE usuarios(
  id INTEGER PRIMARY KEY, usuario TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL, rol TEXT NOT NULL,
  hash TEXT NOT NULL, activo INTEGER NOT NULL DEFAULT 1, intentos INTEGER NOT NULL DEFAULT 0,
  bloqueado_hasta TEXT, cambiar_clave INTEGER NOT NULL DEFAULT 0, ultimo_acceso TEXT, creado TEXT);
CREATE TABLE bitacora(
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, usuario TEXT, accion TEXT NOT NULL, tabla TEXT,
  registro TEXT, detalle TEXT, prev_hash TEXT, hash TEXT);
CREATE TABLE cotizaciones(fecha TEXT PRIMARY KEY, tipo_dia TEXT NOT NULL DEFAULT 'HABIL', dolar REAL NOT NULL, ufv REAL NOT NULL);
CREATE TABLE tasas_interes(desde TEXT PRIMARY KEY, r REAL NOT NULL);
CREATE TABLE zonas(codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL);
CREATE TABLE barrios(codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL, zona TEXT);
CREATE TABLE contribuyentes(
  pmc INTEGER PRIMARY KEY, persona TEXT NOT NULL DEFAULT 'N', tipo_doc TEXT, nro_doc TEXT, expedido TEXT,
  paterno TEXT, materno TEXT, nombre TEXT, nit TEXT, razon_social TEXT, zona TEXT, barrio TEXT,
  tipo_via TEXT, calle TEXT, numero TEXT, bloque TEXT, piso TEXT, dpto TEXT, telefono TEXT, celular TEXT,
  email TEXT, medidor TEXT, casilla TEXT, observaciones TEXT, benemerito INTEGER DEFAULT 0,
  fecha_nacimiento TEXT, estado TEXT NOT NULL DEFAULT 'INCOMPLETO', fecha_registro TEXT, usuario TEXT);
CREATE INDEX ix_contrib_nombre ON contribuyentes(paterno, materno, nombre);
CREATE INDEX ix_contrib_doc ON contribuyentes(nro_doc);
CREATE INDEX ix_contrib_nit ON contribuyentes(nit);
CREATE TABLE emp_formularios(id INTEGER PRIMARY KEY, tipo TEXT NOT NULL, nro_orden TEXT, fecha TEXT NOT NULL, pmc INTEGER, usuario TEXT, creado TEXT);
CREATE TABLE inmuebles(
  id INTEGER PRIMARY KEY, pmc INTEGER NOT NULL REFERENCES contribuyentes(pmc), tipo TEXT NOT NULL DEFAULT 'CASA',
  zona TEXT, barrio TEXT, tipo_via TEXT, calle TEXT, numero TEXT, cod_catastral TEXT, cod_censal TEXT,
  material_via TEXT, superficie REAL DEFAULT 0, inclinacion TEXT DEFAULT 'PLANO',
  luz INTEGER DEFAULT 0, agua INTEGER DEFAULT 0, telefono INTEGER DEFAULT 0, alcantarillado INTEGER DEFAULT 0,
  calidad TEXT, sup_construida REAL DEFAULT 0, anio_construccion INTEGER, otras_construcciones REAL DEFAULT 0,
  valor_declarado REAL DEFAULT 0, exento TEXT DEFAULT 'NINGUNO', nro_ddrr TEXT,
  estado TEXT NOT NULL DEFAULT 'ACTIVO', fecha_baja TEXT, usuario TEXT);
CREATE INDEX ix_inm_pmc ON inmuebles(pmc);
CREATE TABLE vehiculos(
  id INTEGER PRIMARY KEY, pmc INTEGER NOT NULL REFERENCES contribuyentes(pmc), placa TEXT NOT NULL, pta TEXT,
  tipo TEXT, marca TEXT, modelo TEXT, procedencia TEXT, pais TEXT, anio_fab INTEGER, anio_imp INTEGER, uso TEXT,
  exento TEXT DEFAULT 'NINGUNO', cilindrada INTEGER DEFAULT 0, toneladas REAL DEFAULT 0, doble_traccion INTEGER DEFAULT 0,
  turbo INTEGER DEFAULT 0, puertas INTEGER DEFAULT 4, chasis TEXT, carroceria TEXT, plazas INTEGER DEFAULT 0,
  revalorizacion REAL DEFAULT 0, nro_motor TEXT, nro_chasis TEXT, color TEXT,
  estado TEXT NOT NULL DEFAULT 'ACTIVO', fecha_baja TEXT, usuario TEXT);
CREATE INDEX ix_veh_pmc ON vehiculos(pmc);
CREATE INDEX ix_veh_placa ON vehiculos(placa);
CREATE TABLE act_tipos(codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL);
CREATE TABLE act_categorias(act TEXT NOT NULL, cat TEXT NOT NULL, descripcion TEXT NOT NULL, PRIMARY KEY(act,cat));
CREATE TABLE ciiu(codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL, es_detalle INTEGER DEFAULT 0);
CREATE TABLE actividades(
  id INTEGER PRIMARY KEY, pmc INTEGER NOT NULL REFERENCES contribuyentes(pmc), act TEXT NOT NULL, cat TEXT NOT NULL,
  nombre_comercial TEXT, nit TEXT, matricula_comercio TEXT, ciiu TEXT, fecha_inicio TEXT, fecha_cese TEXT,
  superficie REAL DEFAULT 0, consumo_elect REAL DEFAULT 0, zona TEXT, barrio TEXT, tipo_via TEXT, calle TEXT, numero TEXT,
  telefono TEXT, exento TEXT DEFAULT 'NINGUNO', habitualidad TEXT DEFAULT 'PERMANENTE',
  nro_licencia TEXT, licencia_emision TEXT, licencia_vence TEXT, estado_licencia TEXT DEFAULT 'SIN LICENCIA',
  estado TEXT NOT NULL DEFAULT 'ACTIVO', usuario TEXT);
CREATE INDEX ix_act_pmc ON actividades(pmc);
CREATE TABLE publicidad(
  id INTEGER PRIMARY KEY, pmc INTEGER NOT NULL REFERENCES contribuyentes(pmc), tipo TEXT NOT NULL, descripcion TEXT,
  ubicacion TEXT, ancho REAL DEFAULT 0, alto REAL DEFAULT 0, fecha_instalacion TEXT, exento TEXT DEFAULT 'NINGUNO',
  estado TEXT NOT NULL DEFAULT 'ACTIVO', usuario TEXT);
CREATE TABLE inspecciones(
  id INTEGER PRIMARY KEY, actividad_id INTEGER REFERENCES actividades(id), pmc INTEGER, fecha TEXT NOT NULL,
  inspector TEXT, resultado TEXT NOT NULL, observaciones TEXT, plazo_subsanar TEXT, usuario TEXT);

-- Tablas base por gestión
CREATE TABLE tb_param(gestion INTEGER NOT NULL, clave TEXT NOT NULL, valor REAL NOT NULL, PRIMARY KEY(gestion,clave));
CREATE TABLE tb_material_via(gestion INTEGER, zona TEXT, material TEXT, valor REAL, PRIMARY KEY(gestion,zona,material));
CREATE TABLE tb_calidad_const(gestion INTEGER, tipo TEXT, calidad TEXT, valor_m2 REAL, PRIMARY KEY(gestion,tipo,calidad));
CREATE TABLE tb_deprec_inm(gestion INTEGER, desde INTEGER, hasta INTEGER, factor REAL, PRIMARY KEY(gestion,desde));
CREATE TABLE tb_escala_inm(gestion INTEGER, orden INTEGER, desde REAL, hasta REAL, cuota_fija REAL, porcentaje REAL, excedente REAL, PRIMARY KEY(gestion,orden));
CREATE TABLE tb_veh_valor(gestion INTEGER, codigo INTEGER, procedencia TEXT, valor REAL, PRIMARY KEY(gestion,codigo,procedencia));
CREATE TABLE tb_veh_cilindrada(gestion INTEGER, codigo INTEGER, desde INTEGER, hasta INTEGER, moto INTEGER DEFAULT 0, PRIMARY KEY(gestion,codigo,moto));
CREATE TABLE tb_moto_valor(gestion INTEGER, codigo INTEGER, valor REAL, PRIMARY KEY(gestion,codigo));
CREATE TABLE tb_veh_deprec(gestion INTEGER, antiguedad INTEGER, factor REAL, PRIMARY KEY(gestion,antiguedad));
CREATE TABLE tb_veh_escala(gestion INTEGER, orden INTEGER, desde REAL, hasta REAL, cuota_fija REAL, porcentaje REAL, excedente REAL, PRIMARY KEY(gestion,orden));
CREATE TABLE tb_veh_correccion(gestion INTEGER, tramo INTEGER, hasta_ton REAL, chasis_torpedo REAL, chasis_cabinado REAL, carr_estacas REAL, carr_micros REAL, carr_buses REAL, carr_otros REAL, PRIMARY KEY(gestion,tramo));
CREATE TABLE tb_act_tope(gestion INTEGER, act TEXT, cat TEXT, tope REAL NOT NULL DEFAULT 0, fijo REAL NOT NULL DEFAULT 0, PRIMARY KEY(gestion,act,cat));
CREATE TABLE tb_act_pua(gestion INTEGER, zona TEXT, valor_m2 REAL, PRIMARY KEY(gestion,zona));
CREATE TABLE tb_act_zona_sup(gestion INTEGER, zona TEXT, desde REAL, hasta REAL, porcentaje REAL, PRIMARY KEY(gestion,zona,desde));
CREATE TABLE tb_act_consumo(gestion INTEGER, desde REAL, hasta REAL, factor REAL, PRIMARY KEY(gestion,desde));
CREATE TABLE tb_publicidad(gestion INTEGER, tipo TEXT, valor_m2 REAL, PRIMARY KEY(gestion,tipo));
CREATE TABLE fechas_venc(rubro TEXT, gestion INTEGER, contado TEXT, cuota1 TEXT, cuota2 TEXT, sin_accesorios TEXT, PRIMARY KEY(rubro,gestion));

-- Liquidación / recaudación
CREATE TABLE liquidaciones(
  id INTEGER PRIMARY KEY, nro TEXT UNIQUE, codigo_pago TEXT UNIQUE, rubro TEXT NOT NULL, pmc INTEGER NOT NULL,
  objeto_id INTEGER, objeto_desc TEXT, gestion INTEGER, tipo_liq TEXT DEFAULT 'ORIGINAL', forma_pago TEXT DEFAULT 'CONTADO',
  base_imponible REAL DEFAULT 0, impuesto REAL DEFAULT 0, credito REAL DEFAULT 0, neto REAL DEFAULT 0,
  fecha TEXT, hora TEXT, fecha_venc TEXT, estado TEXT DEFAULT 'PENDIENTE', detalle TEXT, rectifica_a INTEGER, usuario TEXT);
CREATE INDEX ix_liq_pmc ON liquidaciones(pmc, rubro, gestion);
CREATE TABLE liq_cuotas(id INTEGER PRIMARY KEY, liq_id INTEGER NOT NULL REFERENCES liquidaciones(id), nro INTEGER, monto REAL, vence TEXT, estado TEXT DEFAULT 'PENDIENTE');
CREATE TABLE pagos(
  id INTEGER PRIMARY KEY, nro_recibo TEXT UNIQUE, liq_id INTEGER REFERENCES liquidaciones(id), cuota_id INTEGER, rubro TEXT, pmc INTEGER,
  gestion INTEGER, fecha TEXT NOT NULL, hora TEXT, modalidad TEXT DEFAULT 'CAJA', cajero TEXT, entidad TEXT,
  monto_neto REAL, descuento REAL DEFAULT 0, mant_valor REAL DEFAULT 0, interes REAL DEFAULT 0, multa_df REAL DEFAULT 0,
  sancion REAL DEFAULT 0, total REAL NOT NULL, detalle TEXT, estado TEXT DEFAULT 'VIGENTE', anulado_por TEXT, anulado_motivo TEXT, usuario TEXT);
CREATE INDEX ix_pagos_fecha ON pagos(fecha);
CREATE TABLE transferencias(
  id INTEGER PRIMARY KEY, tipo TEXT NOT NULL, vendedor INTEGER NOT NULL, comprador INTEGER NOT NULL, objeto_id INTEGER NOT NULL,
  fecha_minuta TEXT, nro_ddrr TEXT, fecha_ddrr TEXT, monto_usd REAL DEFAULT 0, monto_bs REAL DEFAULT 0, sup_total REAL, sup_construida REAL,
  nro_poliza TEXT, fecha_poliza TEXT, color TEXT, nro_motor TEXT, nro_chasis TEXT, liq_id INTEGER, estado TEXT DEFAULT 'PENDIENTE', usuario TEXT, fecha TEXT);
CREATE TABLE planes_pago(
  id INTEGER PRIMARY KEY, nro TEXT UNIQUE, pmc INTEGER NOT NULL, fecha TEXT NOT NULL, deuda_total REAL, cuota_inicial REAL DEFAULT 0,
  n_cuotas INTEGER, tasa_anual REAL, estado TEXT DEFAULT 'VIGENTE', resolucion TEXT, usuario TEXT);
CREATE TABLE plan_liqs(plan_id INTEGER, liq_id INTEGER, deuda REAL, PRIMARY KEY(plan_id,liq_id));
CREATE TABLE plan_cuotas(id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL, nro INTEGER, vence TEXT, capital REAL, interes REAL, monto REAL, saldo REAL, estado TEXT DEFAULT 'PENDIENTE', pago_id INTEGER);
CREATE TABLE intimaciones(id INTEGER PRIMARY KEY, nro TEXT UNIQUE, pmc INTEGER NOT NULL, fecha TEXT, plazo_dias INTEGER DEFAULT 10, deuda REAL, detalle TEXT, estado TEXT DEFAULT 'EMITIDA', usuario TEXT);

-- Otros ingresos
CREATE TABLE rubros(codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL, tipo TEXT DEFAULT 'N', permite_subniveles INTEGER DEFAULT 0, nivel INTEGER DEFAULT 1);
CREATE TABLE subniveles(
  codigo TEXT PRIMARY KEY, rubro TEXT NOT NULL REFERENCES rubros(codigo), padre TEXT, descripcion TEXT NOT NULL, tipo TEXT DEFAULT 'ENTRADA',
  frecuencia TEXT DEFAULT 'EVENTUAL', monto REAL DEFAULT 0, porcentaje REAL DEFAULT 0, documento TEXT, fecha TEXT, beneficiario TEXT, activo INTEGER DEFAULT 1);
CREATE TABLE fuc(
  id INTEGER PRIMARY KEY, nro TEXT UNIQUE, fecha TEXT NOT NULL, hora TEXT, nombre TEXT NOT NULL, documento TEXT, detalle TEXT, estado TEXT DEFAULT 'BORRADOR',
  total REAL DEFAULT 0, fecha_pago TEXT, cajero TEXT, modalidad TEXT DEFAULT 'CAJA', entidad TEXT, anulado_motivo TEXT, contrato_id INTEGER, usuario TEXT);
CREATE TABLE fuc_det(id INTEGER PRIMARY KEY, fuc_id INTEGER NOT NULL REFERENCES fuc(id) ON DELETE CASCADE, rubro TEXT, subnivel TEXT, descripcion TEXT, costo REAL, cantidad REAL, total REAL);
CREATE TABLE contratos(
  id INTEGER PRIMARY KEY, nro TEXT UNIQUE, fecha TEXT NOT NULL, subnivel TEXT NOT NULL REFERENCES subniveles(codigo), beneficiario TEXT NOT NULL, documento TEXT,
  monto_periodico REAL NOT NULL, frecuencia TEXT NOT NULL DEFAULT 'MENSUAL', inicio TEXT NOT NULL, fin TEXT, estado TEXT DEFAULT 'VIGENTE', usuario TEXT);
CREATE TABLE contador(clave TEXT PRIMARY KEY, valor INTEGER NOT NULL);
"""

MIGRATIONS = [M1]
