"""Esquemas SQL. Sistema (maestro) y Gestión (una base por empresa y año)."""

VERSION_ESQUEMA = 1

SISTEMA = """
CREATE TABLE config (clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE empresa (
  id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, razon_social TEXT NOT NULL, nombre_comercial TEXT,
  nit TEXT, direccion TEXT, ciudad TEXT, telefono TEXT, email TEXT, actividad TEXT, rep_legal TEXT,
  matricula TEXT, carpeta TEXT NOT NULL, activa INTEGER NOT NULL DEFAULT 1, creada_en TEXT NOT NULL);
CREATE TABLE gestion (
  id INTEGER PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresa(id), anio INTEGER NOT NULL,
  fecha_inicio TEXT NOT NULL, fecha_fin TEXT NOT NULL, archivo TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'A',
  correlativo_mensual INTEGER NOT NULL DEFAULT 1, creada_en TEXT NOT NULL, cerrada_en TEXT,
  UNIQUE(empresa_id, anio));
CREATE TABLE usuario (
  id INTEGER PRIMARY KEY, login TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, hash TEXT NOT NULL, salt TEXT NOT NULL,
  email TEXT, activo INTEGER NOT NULL DEFAULT 1, es_admin INTEGER NOT NULL DEFAULT 0,
  cambiar_clave INTEGER NOT NULL DEFAULT 1, intentos INTEGER NOT NULL DEFAULT 0, ultimo_acceso TEXT);
CREATE TABLE usuario_empresa (
  id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
  empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE, rol TEXT NOT NULL,
  UNIQUE(usuario_id, empresa_id));
CREATE TABLE permiso (
  id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
  empresa_id INTEGER NOT NULL REFERENCES empresa(id) ON DELETE CASCADE, opcion TEXT NOT NULL,
  UNIQUE(usuario_id, empresa_id, opcion));
CREATE TABLE auditoria (
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, usuario_id INTEGER, login TEXT, empresa_id INTEGER, gestion_id INTEGER,
  modulo TEXT, accion TEXT, detalle TEXT, equipo TEXT);
CREATE INDEX ix_auditoria_fecha ON auditoria(fecha);
CREATE TABLE backup_log (
  id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, tipo TEXT, archivo TEXT, empresa_id INTEGER, resultado TEXT, tamano_mb REAL);
CREATE TABLE normativa (
  id INTEGER PRIMARY KEY, clave TEXT NOT NULL, vigente_desde TEXT NOT NULL, valor TEXT NOT NULL,
  descripcion TEXT, fuente TEXT, UNIQUE(clave, vigente_desde));
"""

GESTION = """
CREATE TABLE parametro (clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE secuencia (clave TEXT PRIMARY KEY, valor INTEGER NOT NULL);
CREATE TABLE tipo_comprobante (codigo TEXT PRIMARY KEY, nombre TEXT NOT NULL, prefijo TEXT NOT NULL);
CREATE TABLE cuenta (
  id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, nivel INTEGER NOT NULL,
  padre_id INTEGER REFERENCES cuenta(id), es_movimiento INTEGER NOT NULL DEFAULT 0,
  tipo TEXT NOT NULL, naturaleza TEXT NOT NULL, moneda_extranjera INTEGER NOT NULL DEFAULT 0,
  ajustable INTEGER NOT NULL DEFAULT 0, es_banco INTEGER NOT NULL DEFAULT 0, es_efectivo INTEGER NOT NULL DEFAULT 0,
  regularizadora INTEGER NOT NULL DEFAULT 0, corriente INTEGER NOT NULL DEFAULT 1, flujo TEXT NOT NULL DEFAULT 'NA',
  patr_col TEXT, costo_tipo TEXT, presupuestable INTEGER NOT NULL DEFAULT 0, activa INTEGER NOT NULL DEFAULT 1);
CREATE INDEX ix_cuenta_padre ON cuenta(padre_id);
CREATE TABLE tipo_cambio (
  fecha TEXT PRIMARY KEY, dolar REAL NOT NULL, ufv REAL NOT NULL DEFAULT 0);
CREATE TABLE centro_costo (
  id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, tipo TEXT NOT NULL DEFAULT 'D',
  activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE tercero (
  id INTEGER PRIMARY KEY, clase TEXT NOT NULL, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, nit TEXT,
  direccion TEXT, telefono TEXT, email TEXT, contacto TEXT, limite_credito REAL NOT NULL DEFAULT 0,
  dias_credito INTEGER NOT NULL DEFAULT 0, activo INTEGER NOT NULL DEFAULT 1);
CREATE INDEX ix_tercero_nit ON tercero(nit);
CREATE TABLE comprobante (
  id INTEGER PRIMARY KEY, tipo TEXT NOT NULL REFERENCES tipo_comprobante(codigo), numero INTEGER NOT NULL,
  mes INTEGER NOT NULL, fecha TEXT NOT NULL, glosa TEXT NOT NULL, moneda TEXT NOT NULL DEFAULT 'BS',
  tc REAL NOT NULL DEFAULT 1, estado TEXT NOT NULL DEFAULT 'V', origen TEXT NOT NULL DEFAULT 'MANUAL', ref_id INTEGER,
  debe_bs REAL NOT NULL DEFAULT 0, haber_bs REAL NOT NULL DEFAULT 0, a_nombre TEXT, nro_doc TEXT,
  creado_por INTEGER, creado_en TEXT, modificado_por INTEGER, modificado_en TEXT, anulado_por INTEGER, anulado_en TEXT);
CREATE INDEX ix_comp_fecha ON comprobante(fecha);
CREATE INDEX ix_comp_tipo_num ON comprobante(tipo, mes, numero);
CREATE TABLE comp_det (
  id INTEGER PRIMARY KEY, comprobante_id INTEGER NOT NULL REFERENCES comprobante(id) ON DELETE CASCADE,
  linea INTEGER NOT NULL, cuenta_id INTEGER NOT NULL REFERENCES cuenta(id), glosa TEXT,
  debe_bs REAL NOT NULL DEFAULT 0, haber_bs REAL NOT NULL DEFAULT 0,
  debe_usd REAL NOT NULL DEFAULT 0, haber_usd REAL NOT NULL DEFAULT 0,
  centro_id INTEGER REFERENCES centro_costo(id), tercero_id INTEGER REFERENCES tercero(id), doc_ref TEXT,
  conciliado TEXT);
CREATE INDEX ix_det_comp ON comp_det(comprobante_id);
CREATE INDEX ix_det_cuenta ON comp_det(cuenta_id);
CREATE TABLE factura (
  id INTEGER PRIMARY KEY, libro TEXT NOT NULL, fecha TEXT NOT NULL, nit TEXT, razon_social TEXT, nro_factura TEXT NOT NULL,
  nro_autorizacion TEXT, cod_control TEXT, dui TEXT, tipo_compra INTEGER NOT NULL DEFAULT 1,
  importe_total REAL NOT NULL DEFAULT 0, no_sujeto REAL NOT NULL DEFAULT 0, exento REAL NOT NULL DEFAULT 0,
  tasa_cero REAL NOT NULL DEFAULT 0, subtotal REAL NOT NULL DEFAULT 0, descuentos REAL NOT NULL DEFAULT 0,
  base_iva REAL NOT NULL DEFAULT 0, iva REAL NOT NULL DEFAULT 0, estado TEXT NOT NULL DEFAULT 'V',
  tercero_id INTEGER REFERENCES tercero(id), comprobante_id INTEGER REFERENCES comprobante(id),
  origen TEXT NOT NULL DEFAULT 'MANUAL', origen_id INTEGER, periodo TEXT NOT NULL, modalidad TEXT);
CREATE INDEX ix_factura_libro ON factura(libro, periodo);
CREATE TABLE almacen (id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, direccion TEXT, activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE unidad (id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL);
CREATE TABLE grupo_item (id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL);
CREATE TABLE vendedor (id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, comision REAL NOT NULL DEFAULT 0, activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE item (
  id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, grupo_id INTEGER REFERENCES grupo_item(id),
  unidad_id INTEGER REFERENCES unidad(id), precio_venta REAL NOT NULL DEFAULT 0, costo_prom REAL NOT NULL DEFAULT 0,
  stock REAL NOT NULL DEFAULT 0, stock_min REAL NOT NULL DEFAULT 0, es_servicio INTEGER NOT NULL DEFAULT 0,
  controla_venc INTEGER NOT NULL DEFAULT 0, tipo TEXT NOT NULL DEFAULT 'M', activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE item_stock (
  item_id INTEGER NOT NULL REFERENCES item(id), almacen_id INTEGER NOT NULL REFERENCES almacen(id),
  cantidad REAL NOT NULL DEFAULT 0, PRIMARY KEY(item_id, almacen_id));
CREATE TABLE item_lote (
  id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES item(id), almacen_id INTEGER NOT NULL REFERENCES almacen(id),
  lote TEXT NOT NULL, vencimiento TEXT, cantidad REAL NOT NULL DEFAULT 0);
CREATE TABLE mov_inv (
  id INTEGER PRIMARY KEY, tipo TEXT NOT NULL, numero INTEGER NOT NULL, fecha TEXT NOT NULL, almacen_id INTEGER NOT NULL REFERENCES almacen(id),
  almacen_dest_id INTEGER REFERENCES almacen(id), glosa TEXT, doc_tipo TEXT, doc_id INTEGER,
  comprobante_id INTEGER REFERENCES comprobante(id), estado TEXT NOT NULL DEFAULT 'V');
CREATE TABLE mov_inv_det (
  id INTEGER PRIMARY KEY, mov_id INTEGER NOT NULL REFERENCES mov_inv(id) ON DELETE CASCADE, item_id INTEGER NOT NULL REFERENCES item(id),
  cantidad REAL NOT NULL, costo_unit REAL NOT NULL DEFAULT 0, costo_total REAL NOT NULL DEFAULT 0, lote TEXT, vencimiento TEXT);
CREATE TABLE kardex (
  id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES item(id), almacen_id INTEGER NOT NULL REFERENCES almacen(id),
  fecha TEXT NOT NULL, mov_id INTEGER, tipo TEXT NOT NULL, detalle TEXT,
  ent_cant REAL NOT NULL DEFAULT 0, sal_cant REAL NOT NULL DEFAULT 0, costo_unit REAL NOT NULL DEFAULT 0,
  ent_val REAL NOT NULL DEFAULT 0, sal_val REAL NOT NULL DEFAULT 0, saldo_cant REAL NOT NULL DEFAULT 0,
  saldo_val REAL NOT NULL DEFAULT 0, costo_prom REAL NOT NULL DEFAULT 0);
CREATE INDEX ix_kardex_item ON kardex(item_id, fecha, id);
CREATE TABLE venta (
  id INTEGER PRIMARY KEY, numero INTEGER NOT NULL, fecha TEXT NOT NULL, tercero_id INTEGER NOT NULL REFERENCES tercero(id),
  tipo_pago TEXT NOT NULL DEFAULT 'CON', moneda TEXT NOT NULL DEFAULT 'BS', tc REAL NOT NULL DEFAULT 1,
  almacen_id INTEGER REFERENCES almacen(id), vendedor_id INTEGER REFERENCES vendedor(id), con_factura INTEGER NOT NULL DEFAULT 1,
  nro_factura TEXT, nro_autorizacion TEXT, subtotal REAL NOT NULL DEFAULT 0, descuento REAL NOT NULL DEFAULT 0,
  recargo REAL NOT NULL DEFAULT 0, total REAL NOT NULL DEFAULT 0, a_cuenta REAL NOT NULL DEFAULT 0, saldo REAL NOT NULL DEFAULT 0,
  costo_total REAL NOT NULL DEFAULT 0, vencimiento TEXT, glosa TEXT, estado TEXT NOT NULL DEFAULT 'V',
  comprobante_id INTEGER REFERENCES comprobante(id), factura_id INTEGER REFERENCES factura(id), mov_id INTEGER REFERENCES mov_inv(id));
CREATE TABLE venta_det (
  id INTEGER PRIMARY KEY, venta_id INTEGER NOT NULL REFERENCES venta(id) ON DELETE CASCADE, item_id INTEGER NOT NULL REFERENCES item(id),
  cantidad REAL NOT NULL, precio REAL NOT NULL, descuento REAL NOT NULL DEFAULT 0, total REAL NOT NULL,
  costo_unit REAL NOT NULL DEFAULT 0, costo_total REAL NOT NULL DEFAULT 0);
CREATE TABLE compra (
  id INTEGER PRIMARY KEY, numero INTEGER NOT NULL, fecha TEXT NOT NULL, tercero_id INTEGER NOT NULL REFERENCES tercero(id),
  tipo_pago TEXT NOT NULL DEFAULT 'CON', moneda TEXT NOT NULL DEFAULT 'BS', tc REAL NOT NULL DEFAULT 1,
  almacen_id INTEGER REFERENCES almacen(id), con_factura INTEGER NOT NULL DEFAULT 1, nro_factura TEXT, nro_autorizacion TEXT,
  subtotal REAL NOT NULL DEFAULT 0, descuento REAL NOT NULL DEFAULT 0, recargo REAL NOT NULL DEFAULT 0, total REAL NOT NULL DEFAULT 0,
  a_cuenta REAL NOT NULL DEFAULT 0, saldo REAL NOT NULL DEFAULT 0, vencimiento TEXT, glosa TEXT, estado TEXT NOT NULL DEFAULT 'V',
  comprobante_id INTEGER REFERENCES comprobante(id), factura_id INTEGER REFERENCES factura(id), mov_id INTEGER REFERENCES mov_inv(id));
CREATE TABLE compra_det (
  id INTEGER PRIMARY KEY, compra_id INTEGER NOT NULL REFERENCES compra(id) ON DELETE CASCADE, item_id INTEGER NOT NULL REFERENCES item(id),
  cantidad REAL NOT NULL, precio REAL NOT NULL, descuento REAL NOT NULL DEFAULT 0, total REAL NOT NULL,
  lote TEXT, vencimiento TEXT);
CREATE TABLE cobro_pago (
  id INTEGER PRIMARY KEY, clase TEXT NOT NULL, numero INTEGER NOT NULL, fecha TEXT NOT NULL, tercero_id INTEGER NOT NULL REFERENCES tercero(id),
  monto REAL NOT NULL, forma TEXT NOT NULL DEFAULT 'EFE', cuenta_id INTEGER REFERENCES cuenta(id), nro_doc TEXT, glosa TEXT,
  estado TEXT NOT NULL DEFAULT 'V', comprobante_id INTEGER REFERENCES comprobante(id));
CREATE TABLE cobro_doc (
  id INTEGER PRIMARY KEY, cobro_id INTEGER NOT NULL REFERENCES cobro_pago(id) ON DELETE CASCADE,
  doc_tipo TEXT NOT NULL, doc_id INTEGER NOT NULL, monto REAL NOT NULL);
CREATE TABLE activo_grupo (
  id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE, vida_anios REAL NOT NULL, pct REAL NOT NULL,
  cta_activo TEXT NOT NULL, cta_dep TEXT NOT NULL, cta_gasto TEXT NOT NULL);
CREATE TABLE activo (
  id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, grupo_id INTEGER NOT NULL REFERENCES activo_grupo(id),
  fecha_alta TEXT NOT NULL, valor_original REAL NOT NULL, valor_actual REAL NOT NULL, dep_acum REAL NOT NULL DEFAULT 0,
  vida_meses INTEGER NOT NULL, pct REAL NOT NULL, ufv_alta REAL NOT NULL DEFAULT 0, ufv_ult REAL NOT NULL DEFAULT 0,
  ubicacion TEXT, responsable TEXT, centro_id INTEGER REFERENCES centro_costo(id), serie TEXT, estado TEXT NOT NULL DEFAULT 'A',
  fecha_baja TEXT, comprobante_id INTEGER REFERENCES comprobante(id));
CREATE TABLE activo_dep (
  id INTEGER PRIMARY KEY, activo_id INTEGER NOT NULL REFERENCES activo(id), periodo TEXT NOT NULL, fecha TEXT NOT NULL,
  actualizacion REAL NOT NULL DEFAULT 0, dep_actualizacion REAL NOT NULL DEFAULT 0, depreciacion REAL NOT NULL DEFAULT 0,
  comprobante_id INTEGER REFERENCES comprobante(id), UNIQUE(activo_id, periodo));
CREATE TABLE empleado (
  id INTEGER PRIMARY KEY, codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, ci TEXT NOT NULL, nua TEXT, fecha_ingreso TEXT NOT NULL,
  fecha_retiro TEXT, cargo TEXT, haber_basico REAL NOT NULL, bono_fijo REAL NOT NULL DEFAULT 0,
  afp TEXT NOT NULL DEFAULT 'GESTORA', aporta_afp INTEGER NOT NULL DEFAULT 1, mayor_65 INTEGER NOT NULL DEFAULT 0,
  jubilado INTEGER NOT NULL DEFAULT 0, centro_id INTEGER REFERENCES centro_costo(id), banco TEXT, cuenta_banco TEXT,
  activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE anticipo (
  id INTEGER PRIMARY KEY, empleado_id INTEGER NOT NULL REFERENCES empleado(id), fecha TEXT NOT NULL, monto REAL NOT NULL,
  descuento_mes REAL NOT NULL DEFAULT 0, saldo REAL NOT NULL, glosa TEXT, comprobante_id INTEGER REFERENCES comprobante(id));
CREATE TABLE planilla (
  id INTEGER PRIMARY KEY, anio INTEGER NOT NULL, mes INTEGER NOT NULL, estado TEXT NOT NULL DEFAULT 'B',
  smn REAL NOT NULL, ufv_mes REAL NOT NULL DEFAULT 0, comprobante_id INTEGER REFERENCES comprobante(id), UNIQUE(anio, mes));
CREATE TABLE planilla_det (
  id INTEGER PRIMARY KEY, planilla_id INTEGER NOT NULL REFERENCES planilla(id) ON DELETE CASCADE,
  empleado_id INTEGER NOT NULL REFERENCES empleado(id), dias INTEGER NOT NULL DEFAULT 30, haber_basico REAL NOT NULL DEFAULT 0,
  bono_antig REAL NOT NULL DEFAULT 0, horas_extra REAL NOT NULL DEFAULT 0, monto_extra REAL NOT NULL DEFAULT 0,
  recargo_nocturno REAL NOT NULL DEFAULT 0, dominical REAL NOT NULL DEFAULT 0, otros_bonos REAL NOT NULL DEFAULT 0,
  total_ganado REAL NOT NULL DEFAULT 0, afp_vejez REAL NOT NULL DEFAULT 0, afp_riesgo REAL NOT NULL DEFAULT 0,
  afp_comision REAL NOT NULL DEFAULT 0, afp_solidario REAL NOT NULL DEFAULT 0, ans REAL NOT NULL DEFAULT 0,
  rciva REAL NOT NULL DEFAULT 0, anticipos REAL NOT NULL DEFAULT 0, otros_desc REAL NOT NULL DEFAULT 0,
  total_desc REAL NOT NULL DEFAULT 0, liquido REAL NOT NULL DEFAULT 0,
  pat_cns REAL NOT NULL DEFAULT 0, pat_riesgo REAL NOT NULL DEFAULT 0, pat_vivienda REAL NOT NULL DEFAULT 0,
  pat_solidario REAL NOT NULL DEFAULT 0, pat_infocal REAL NOT NULL DEFAULT 0,
  rc_neto REAL NOT NULL DEFAULT 0, rc_base REAL NOT NULL DEFAULT 0, rc_impuesto REAL NOT NULL DEFAULT 0,
  rc_cred_smn REAL NOT NULL DEFAULT 0, rc_facturas REAL NOT NULL DEFAULT 0, rc_saldo_ant REAL NOT NULL DEFAULT 0,
  rc_mant_valor REAL NOT NULL DEFAULT 0, rc_saldo_sig REAL NOT NULL DEFAULT 0,
  UNIQUE(planilla_id, empleado_id));
CREATE TABLE presupuesto (
  cuenta_id INTEGER NOT NULL REFERENCES cuenta(id), mes INTEGER NOT NULL, monto REAL NOT NULL DEFAULT 0, PRIMARY KEY(cuenta_id, mes));
CREATE TABLE orden_prod (
  id INTEGER PRIMARY KEY, numero INTEGER NOT NULL, fecha TEXT NOT NULL, item_id INTEGER NOT NULL REFERENCES item(id),
  cant_plan REAL NOT NULL, cant_prod REAL NOT NULL DEFAULT 0, almacen_mp_id INTEGER NOT NULL REFERENCES almacen(id),
  almacen_pt_id INTEGER NOT NULL REFERENCES almacen(id), glosa TEXT, estado TEXT NOT NULL DEFAULT 'A',
  costo_mp REAL NOT NULL DEFAULT 0, costo_mod REAL NOT NULL DEFAULT 0, costo_cif REAL NOT NULL DEFAULT 0,
  fecha_cierre TEXT, comprobante_id INTEGER REFERENCES comprobante(id));
CREATE TABLE orden_mp (
  id INTEGER PRIMARY KEY, orden_id INTEGER NOT NULL REFERENCES orden_prod(id) ON DELETE CASCADE, item_id INTEGER NOT NULL REFERENCES item(id),
  fecha TEXT NOT NULL, cantidad REAL NOT NULL, costo_unit REAL NOT NULL, costo_total REAL NOT NULL, mov_id INTEGER REFERENCES mov_inv(id));
CREATE TABLE orden_mod (
  id INTEGER PRIMARY KEY, orden_id INTEGER NOT NULL REFERENCES orden_prod(id) ON DELETE CASCADE, empleado_id INTEGER REFERENCES empleado(id),
  descripcion TEXT, horas REAL NOT NULL, tarifa REAL NOT NULL, monto REAL NOT NULL);
CREATE TABLE orden_cif (
  id INTEGER PRIMARY KEY, orden_id INTEGER NOT NULL REFERENCES orden_prod(id) ON DELETE CASCADE, concepto TEXT NOT NULL, monto REAL NOT NULL);
"""
