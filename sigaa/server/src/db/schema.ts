import type { Knex } from 'knex';

/**
 * Esquema unificado de SIGAA. Prefijos:
 *  core_ = maestros compartidos, seguridad y auditoría
 *  alm_  = Almacenes (bienes de consumo)
 *  com_  = Combustible (vales, turriles, viajes)
 *  af_   = Activos Fijos
 * Fechas: texto ISO (YYYY-MM-DD) / fecha-hora ISO. Compatible con SQLite y PostgreSQL.
 */
type Builder = (t: Knex.CreateTableBuilder) => void;

const money = (t: Knex.CreateTableBuilder, name: string) => t.decimal(name, 18, 4).defaultTo(0);
const qty = (t: Knex.CreateTableBuilder, name: string) => t.decimal(name, 18, 6).defaultTo(0);

export const TABLES: Record<string, Builder> = {
  // ───────────────────────── CORE ─────────────────────────
  core_config: (t) => {
    t.string('clave', 60).primary();
    t.text('valor');
    t.text('descripcion');
    t.string('modulo', 20).defaultTo('core');
  },
  core_usuarios: (t) => {
    t.string('usuario', 40).primary();
    t.string('nombre', 120).notNullable();
    t.string('roles', 120).notNullable().defaultTo('CONSULTA');
    t.string('estado', 12).notNullable().defaultTo('ACTIVO');
    t.boolean('debe_cambiar').defaultTo(true);
    t.string('clave_hash', 200).notNullable();
    t.string('ultimo_acceso', 30);
  },
  core_bitacora: (t) => {
    t.increments('id');
    t.string('fecha', 30).notNullable();
    t.string('usuario', 40);
    t.string('modulo', 20);
    t.string('accion', 80);
    t.string('documento', 60);
    t.text('detalle');
    t.index(['modulo', 'fecha']);
    t.index(['documento']);
  },
  core_secuencias: (t) => {
    t.string('prefijo', 12).notNullable();
    t.integer('gestion').notNullable();
    t.integer('ultimo').notNullable().defaultTo(0);
    t.primary(['prefijo', 'gestion']);
  },
  core_unidades: (t) => {
    t.increments('id');
    t.string('nombre', 160).notNullable().unique();
    t.string('responsable', 120);
    t.string('cargo', 120);
    t.string('sigla', 20);
  },
  core_funcionarios: (t) => {
    t.increments('id');
    t.string('nombre', 140).notNullable().unique();
    t.string('ci', 30);
    t.string('cargo', 140);
    t.string('unidad', 160);
    t.string('celular', 30);
    t.string('estado', 12).notNullable().defaultTo('ACTIVO');
  },
  core_proveedores: (t) => {
    t.increments('id');
    t.string('nit', 30).notNullable().index();
    t.string('razon_social', 200).notNullable().unique();
    t.string('contacto', 120);
    t.string('telefono', 40);
    t.string('direccion', 200);
    t.string('estacion', 120); // estación de servicio (combustible)
    t.string('estado', 12).notNullable().defaultTo('ACTIVO');
  },
  core_proyectos: (t) => {
    t.increments('id');
    t.string('nombre', 200).notNullable().unique();
    t.string('estado', 12).notNullable().defaultTo('ACTIVO');
  },
  core_aperturas: (t) => {
    t.increments('id');
    t.string('apertura', 30).notNullable().unique();
    t.string('descripcion', 200);
    money(t, 'presupuesto');
  },
  core_partidas: (t) => {
    t.string('partida', 10).primary();
    t.string('descripcion', 200);
  },

  // ───────────────────────── ALMACENES ─────────────────────────
  alm_bodegas: (t) => {
    t.string('cod', 4).primary();
    t.string('nombre', 160).notNullable().unique();
    t.string('responsable', 120);
    t.string('ubicacion', 160);
    t.string('estado', 12).notNullable().defaultTo('ACTIVO');
  },
  alm_grupos: (t) => {
    t.integer('grupo').primary();
    t.string('nombre', 160).notNullable();
  },
  alm_subgrupos: (t) => {
    t.integer('grupo').notNullable();
    t.integer('subgrupo').notNullable();
    t.string('nombre', 160).notNullable();
    t.primary(['grupo', 'subgrupo']);
  },
  alm_unidades_medida: (t) => {
    t.string('nombre', 40).primary();
  },
  alm_causales: (t) => {
    t.string('causal', 60).primary();
    t.string('grupo', 2).notNullable(); // A = hurto/robo/siniestro, B = merma/venc./deterioro
  },
  alm_pasos: (t) => {
    t.increments('id');
    t.string('grupo', 2).notNullable();
    t.integer('orden').notNullable();
    t.string('paso', 300).notNullable();
    t.string('doc', 20); // código de documento del sistema (ACTAVER, INFSOL, ...)
    t.string('clase', 10); // RA | BAJA | PUBLICACION
    t.string('obligatorio', 2).defaultTo('SI');
    t.unique(['grupo', 'orden']);
  },
  alm_docreq: (t) => {
    t.increments('id');
    t.string('tipo', 80).notNullable();
    t.integer('orden').notNullable();
    t.string('documento', 200).notNullable();
    t.string('obligatorio', 2).defaultTo('SI');
  },
  alm_extintores: (t) => {
    t.string('cod', 20).primary();
    t.string('cod_bod', 4);
    t.string('tipo', 40);
    t.string('capacidad', 20);
    t.string('ult_recarga', 10);
    t.string('venc_recarga', 10);
    t.string('estado', 12).defaultTo('ACTIVO');
  },
  alm_seguros: (t) => {
    t.string('poliza', 40).primary();
    t.string('aseguradora', 120);
    t.string('cobertura', 200);
    t.string('desde', 10);
    t.string('hasta', 10);
    money(t, 'monto_asegurado');
    t.string('archivo', 300);
    t.string('estado', 12).defaultTo('VIGENTE');
  },
  alm_catalogo: (t) => {
    t.string('codigo', 20).primary(); // G-S-0000001
    t.integer('grupo').notNullable();
    t.integer('subgrupo').notNullable();
    t.integer('correlativo').notNullable();
    t.string('descripcion', 240).notNullable();
    t.string('unidad', 40).notNullable();
    t.string('partida', 10);
    t.string('cod_bod', 4).notNullable();
    qty(t, 'stock_min');
    qty(t, 'stock_max');
    t.string('perecible', 2).defaultTo('NO');
    t.string('peligroso', 2).defaultTo('NO');
    t.string('ubicacion', 80);
    money(t, 'precio_ref');
    t.string('estado', 12).defaultTo('ACTIVO');
    t.string('fecha_reg', 30);
    t.unique(['grupo', 'subgrupo', 'correlativo']);
    t.index(['cod_bod']);
  },
  alm_ingresos: (t) => {
    t.string('nro', 20).primary(); // CGI-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('cod_bod', 4).notNullable();
    t.string('tipo', 60).notNullable();
    t.string('proveedor', 200);
    t.string('nit', 30);
    t.string('nro_oc', 40);
    t.string('plazo_entrega', 10);
    t.string('factura', 40);
    t.string('fecha_factura', 10);
    t.string('unidad', 160);
    t.string('preventivo', 30);
    t.string('nro_pse', 30);
    t.string('proyecto', 200);
    t.string('fuente', 120);
    t.string('partida', 10);
    t.string('comision', 300);
    t.text('obs_plazo');
    t.string('motivo_anulacion', 300);
    money(t, 'total');
    t.string('estado', 14).notNullable().defaultTo('REGISTRADO'); // REGISTRADO | INGRESADO | ANULADO
    t.string('fecha_reg', 30);
    t.string('usuario', 60);
  },
  alm_ingresos_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('descripcion', 240);
    t.string('unidad', 40);
    t.string('marca', 120);
    qty(t, 'cantidad');
    money(t, 'precio_unit');
    money(t, 'total');
    t.string('vencimiento', 10);
    t.string('lote', 60);
    t.index(['nro']);
  },
  alm_ingresos_doc: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('orden').notNullable();
    t.string('documento', 240).notNullable(); // termina en "  (*)" si es obligatorio
    t.string('estado', 2); // SI | NO
    t.index(['nro']);
  },
  alm_salidas: (t) => {
    t.string('nro', 20).primary(); // VS-0001/2026
    t.string('fecha_pedido', 10).notNullable();
    t.string('cod_bod', 4).notNullable();
    t.string('estado', 14).notNullable().defaultTo('PEDIDO'); // PEDIDO|APROBADO|ENTREGADO|RECHAZADO|ANULADO
    t.string('unidad', 160);
    t.string('solicitante', 140);
    t.string('cargo', 140);
    t.string('superior', 140);
    t.string('proyecto', 200);
    t.string('nota_interna', 60);
    t.text('justificacion');
    t.text('observ');
    t.string('excepcion', 300);
    t.string('fecha_aprob', 30);
    t.string('aprobador', 140);
    t.string('fecha_entrega', 30);
    t.string('entregador', 140);
    t.string('motivo', 300); // rechazo / anulación
    money(t, 'total');
    t.string('fecha_reg', 30);
    t.string('usuario', 60);
    t.index(['solicitante']);
  },
  alm_salidas_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('descripcion', 240);
    t.string('unidad', 40);
    qty(t, 'cant_pedida');
    qty(t, 'cant_entregada');
    money(t, 'precio_prom');
    money(t, 'total');
    t.string('obs', 300);
    t.index(['nro']);
  },
  alm_lotes: (t) => {
    t.string('id_lote', 12).primary();
    t.string('cod_bod', 4).notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('doc_origen', 30);
    t.string('fecha_ing', 10);
    t.string('vencimiento', 10);
    qty(t, 'cant_inicial');
    qty(t, 'saldo');
    money(t, 'precio_unit');
    t.string('estado', 10).notNullable().defaultTo('ACTIVO'); // ACTIVO|AGOTADO|BAJA|ANULADO
    t.string('nro_lote', 60);
    t.index(['cod_bod', 'cod_item']);
  },
  alm_movimientos: (t) => {
    t.string('id_mov', 12).primary();
    t.string('fecha', 10).notNullable();
    t.string('cod_bod', 4).notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('tipo', 20).notNullable(); // INGRESO|SALIDA|BAJA|TRANSF-ENT|TRANSF-SAL|SALDO INICIAL
    t.string('documento', 30);
    t.string('id_lote', 12);
    qty(t, 'cant_ent');
    qty(t, 'cant_sal');
    money(t, 'precio_unit');
    money(t, 'imp_ent');
    money(t, 'imp_sal');
    t.string('referencia', 300);
    t.string('anulado', 2);
    t.string('usuario', 60);
    t.string('fecha_reg', 30);
    t.index(['cod_bod', 'cod_item', 'fecha']);
    t.index(['documento']);
  },
  alm_inventarios: (t) => {
    t.string('nro', 20).primary(); // INV-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('cod_bod', 4).notNullable();
    t.string('tipo', 40).notNullable();
    t.string('responsable', 140);
    t.string('designado', 300);
    t.string('observador', 200);
    t.string('corte_ing', 200);
    t.string('corte_sal', 200);
    t.string('filtro_subgrupo', 10);
    t.string('estado', 12).notNullable().defaultTo('EN CONTEO'); // EN CONTEO | CERRADO
    money(t, 'faltante_bs');
    money(t, 'sobrante_bs');
    t.string('fecha_reg', 30);
  },
  alm_inventarios_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('descripcion', 240);
    t.string('unidad', 40);
    qty(t, 'saldo_sist');
    t.decimal('conteo', 18, 6); // null = no contado
    qty(t, 'diferencia');
    money(t, 'precio_unit');
    t.string('estado_bien', 20);
    t.string('obs', 300);
    t.index(['nro']);
  },
  alm_bajas: (t) => {
    t.string('nro', 20).primary(); // BAJ-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('cod_bod', 4).notNullable();
    t.string('causal', 60).notNullable();
    t.string('grupo', 2);
    t.string('responsable', 140);
    t.text('justificacion');
    t.string('nro_ra', 40);
    t.string('fecha_ra', 10);
    money(t, 'total');
    t.string('estado', 16).notNullable().defaultTo('EN TRÁMITE'); // EN TRÁMITE|BAJA EJECUTADA|CONCLUIDO|ANULADO
    t.string('origen', 40);
    t.string('fecha_reg', 30);
  },
  alm_bajas_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('descripcion', 240);
    t.string('unidad', 40);
    t.string('id_lote', 12);
    qty(t, 'cantidad');
    money(t, 'precio_unit');
    money(t, 'total');
    t.index(['nro']);
  },
  alm_bajas_paso: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('orden').notNullable();
    t.string('paso', 300).notNullable();
    t.string('doc', 20);
    t.string('clase', 10);
    t.string('referencia', 80);
    t.string('fecha', 10);
    t.string('estado', 12).defaultTo('PENDIENTE'); // PENDIENTE|HECHO|NO APLICA
    t.string('respaldo', 300);
    t.index(['nro']);
  },
  alm_transferencias: (t) => {
    t.string('nro', 20).primary(); // TRF-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('bod_origen', 4).notNullable();
    t.string('bod_destino', 4).notNullable();
    t.string('entrega', 140);
    t.string('recibe', 140);
    t.text('motivo');
    money(t, 'total');
    t.string('estado', 12).notNullable().defaultTo('REGISTRADA'); // REGISTRADA|EJECUTADA
    t.string('fecha_reg', 30);
  },
  alm_transferencias_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('descripcion', 240);
    t.string('unidad', 40);
    qty(t, 'cantidad');
    money(t, 'precio_unit');
    money(t, 'total');
    t.index(['nro']);
  },
  alm_requerimientos: (t) => {
    t.string('nro', 20).primary(); // REQ-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('cod_bod', 4); // null = TODAS
    t.string('tipo', 60);
    money(t, 'total');
    t.string('estado', 12).defaultTo('REGISTRADO');
    t.text('justificacion');
    t.string('fecha_reg', 30);
  },
  alm_requerimientos_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.string('cod_item', 20).notNullable();
    t.string('descripcion', 240);
    t.string('unidad', 40);
    qty(t, 'stock');
    qty(t, 'cant_solic');
    money(t, 'precio_ref');
    money(t, 'total');
    t.string('partida', 10);
    t.index(['nro']);
  },
  alm_inspecciones: (t) => {
    t.string('nro', 20).primary(); // INS-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('cod_bod', 4).notNullable();
    t.string('inspector', 140);
    t.integer('cumple').defaultTo(0);
    t.integer('no_cumple').defaultTo(0);
    t.text('observ');
    t.string('fecha_reg', 30);
  },
  alm_inspecciones_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.string('criterio', 300);
    t.string('resultado', 12);
    t.string('obs', 400);
    t.index(['nro']);
  },

  // ───────────────────────── COMBUSTIBLE ─────────────────────────
  com_tipos: (t) => {
    t.string('tipo', 40).primary();
    t.string('clase', 20);
    t.string('medidor', 8); // Km | Horas
    t.decimal('rendimiento_ref', 12, 4).defaultTo(0); // L/km o L/hora
  },
  com_vehiculos: (t) => {
    t.string('codigo', 20).primary();
    t.string('placa', 20).notNullable().unique();
    t.string('tipo', 40);
    t.string('clase', 20);
    t.string('uso', 12); // Ejecutivo | Operativo
    t.string('marca', 60);
    t.string('modelo', 60);
    t.integer('anio');
    t.string('color', 30);
    t.string('combustible', 12);
    t.string('medidor', 8);
    t.decimal('capacidad_tanque', 10, 2).defaultTo(0);
    t.decimal('rendimiento', 12, 4).defaultTo(0);
    t.string('unidad', 160);
    t.string('conductor', 140);
    t.string('acta_asignacion', 40);
    t.string('estado', 12).defaultTo('Activo');
    t.string('activo_codigo', 20); // vínculo con Activos Fijos
    t.text('observaciones');
  },
  com_conductores: (t) => {
    t.string('ci', 30).primary();
    t.string('nombre', 140).notNullable().unique();
    t.string('cargo', 80);
    t.string('unidad', 160);
    t.string('celular', 30);
    t.string('licencia', 30);
    t.string('categoria', 4);
    t.string('vence_licencia', 10);
    t.string('estado', 12).defaultTo('Activo');
    t.text('observaciones');
  },
  com_puestos: (t) => {
    t.string('codigo', 20).primary();
    t.string('nombre', 120).notNullable();
    t.string('ubicacion', 160);
    t.string('responsable', 120);
    t.string('combustible', 12);
    t.decimal('capacidad_l', 12, 2).defaultTo(0);
    t.string('estado', 12).defaultTo('Activo');
  },
  com_contratos: (t) => {
    t.string('nro', 40).primary();
    t.string('proveedor', 200).notNullable();
    t.string('modalidad', 10); // Prepago | Postpago
    t.string('combustible', 12);
    t.string('fecha_firma', 10);
    t.string('vigencia_desde', 10);
    t.string('vigencia_hasta', 10);
    money(t, 'monto');
    money(t, 'recibido');
    money(t, 'saldo');
    t.string('estado', 12).defaultTo('Vigente');
    t.text('observaciones');
  },
  com_precios: (t) => {
    t.increments('id');
    t.string('combustible', 12).notNullable();
    t.decimal('precio', 12, 4).notNullable();
    t.string('vigente_desde', 10).notNullable();
    t.string('norma', 60);
  },
  com_cronograma: (t) => {
    t.increments('id');
    t.string('mes', 10).notNullable(); // YYYY-MM-01
    t.string('placa', 20).notNullable();
    t.string('obra', 200);
    t.string('apertura', 30);
    t.integer('dias');
    t.decimal('km_horas', 12, 2).defaultTo(0);
    t.decimal('litros_estimados', 12, 2).defaultTo(0);
    t.string('responsable', 140);
    t.text('observaciones');
  },
  com_lotes: (t) => {
    t.string('id_lote', 12).primary();
    t.string('nro_ingreso', 20).notNullable();
    t.string('fecha', 10).notNullable();
    t.string('nro_contrato', 40);
    t.string('proveedor', 200);
    t.string('modalidad', 10);
    t.string('combustible', 12);
    t.integer('corte'); // 30 | 50 | 100
    t.bigInteger('desde');
    t.bigInteger('hasta');
    t.integer('cantidad');
    money(t, 'monto');
    t.string('factura', 40);
    t.string('fecha_factura', 10);
    t.string('nota_ref', 60);
    t.string('comprobante', 60);
    t.text('observaciones');
    t.string('usuario', 60);
    t.string('registrado', 30);
  },
  com_vales: (t) => {
    t.increments('id');
    t.bigInteger('nro_vale').notNullable();
    t.string('id_lote', 12);
    t.string('proveedor', 200).notNullable();
    t.string('combustible', 12).notNullable();
    t.integer('corte').notNullable();
    // Disponible|Entregado|Utilizado|Devuelto→Disponible|Anulado|Vencido|Extraviado
    t.string('estado', 14).notNullable().defaultTo('Disponible');
    t.string('nro_emision', 20);
    t.string('destino', 10);
    t.string('placa', 20);
    t.string('conductor', 140);
    t.string('fecha_entrega', 10);
    t.string('fecha_estado', 10);
    t.text('observaciones');
    t.string('conciliacion', 20);
    t.unique(['proveedor', 'combustible', 'corte', 'nro_vale']);
    t.index(['estado', 'combustible', 'corte']);
    t.index(['nro_emision']);
  },
  com_emisiones: (t) => {
    t.string('nro', 20).primary(); // VC-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('destino', 10).notNullable(); // VEHICULO | TURRIL
    t.string('placa', 20).notNullable(); // placa o código de puesto
    t.string('descripcion_destino', 240);
    t.string('uso', 12);
    t.string('conductor', 140);
    t.string('licencia', 30);
    t.string('unidad', 160);
    t.string('solicitante', 140);
    t.string('cargo_solicitante', 140);
    t.string('combustible', 12);
    t.string('apertura', 30);
    t.string('desc_apertura', 200);
    t.text('trabajo');
    t.string('desde', 10);
    t.string('hasta', 10);
    t.decimal('lectura_actual', 14, 2);
    t.decimal('programado', 14, 2);
    t.integer('cant_vales');
    t.text('detalle_vales');
    money(t, 'monto');
    t.decimal('precio_l', 12, 4);
    t.decimal('litros', 14, 2);
    t.decimal('litros_max', 14, 2);
    t.text('justificacion');
    t.text('observaciones');
    t.string('nro_descargo', 20);
    t.string('estado', 12).defaultTo('Emitido'); // Emitido | Descargado | Anulado
    t.string('usuario', 60);
    t.string('registrado', 30);
    t.index(['placa', 'estado']);
  },
  com_descargos: (t) => {
    t.string('nro', 20).primary(); // DS-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('nro_emision', 20).notNullable();
    t.string('placa', 20);
    t.string('conductor', 140);
    t.string('medidor', 8);
    t.decimal('lectura_inicial', 14, 2);
    t.decimal('lectura_final', 14, 2);
    t.decimal('recorrido', 14, 2);
    t.decimal('litros', 14, 2);
    t.integer('vales_usados');
    money(t, 'monto_usado');
    t.integer('vales_devueltos');
    t.decimal('rendimiento_real', 12, 4);
    t.decimal('rendimiento_ref', 12, 4);
    t.decimal('desviacion', 12, 4);
    t.string('estado', 12); // Conforme | Observado
    t.text('alertas');
    t.text('observaciones');
    t.string('usuario', 60);
    t.string('registrado', 30);
  },
  com_descargo_lineas: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.string('fecha', 10);
    t.string('ruta', 200);
    t.decimal('lectura_salida', 14, 2);
    t.decimal('lectura_llegada', 14, 2);
    t.bigInteger('nro_vale');
    t.decimal('litros', 14, 2);
    t.string('factura', 40);
    t.string('estacion', 120);
    t.index(['nro']);
  },
  com_kardex: (t) => {
    t.increments('id');
    t.string('fecha', 10).notNullable();
    t.string('tipo', 20).notNullable(); // INGRESO|SALIDA|DEVOLUCIÓN|BAJA|DESPACHO
    t.string('documento', 30);
    t.string('almacen', 60); // 'VALES' o código de puesto
    t.string('item', 60).notNullable(); // "VALE GASOLINA Bs 30" | "DIÉSEL (LITROS)"
    t.decimal('entrada', 18, 4).defaultTo(0);
    t.decimal('salida', 18, 4).defaultTo(0);
    t.decimal('costo_unit', 18, 4).defaultTo(0);
    money(t, 'importe_entrada');
    money(t, 'importe_salida');
    t.string('placa', 20);
    t.decimal('lectura', 14, 2);
    t.text('detalle');
    t.string('usuario', 60);
    t.string('registrado', 30);
    t.index(['almacen', 'item']);
  },
  com_conciliaciones: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.string('fecha', 10);
    t.string('proveedor', 200);
    t.string('contrato', 40);
    t.string('desde', 10);
    t.string('hasta', 10);
    t.bigInteger('nro_vale');
    t.integer('corte');
    money(t, 'monto_cobrado');
    t.string('fecha_carga', 10);
    t.string('placa_cobro', 20);
    t.string('placa_sistema', 20);
    t.string('estado_sistema', 14);
    t.string('nro_emision', 20);
    t.string('resultado', 20);
    t.text('detalle');
    t.boolean('pagable').defaultTo(false);
    t.string('factura', 40);
    t.text('observaciones');
    t.string('usuario', 60);
    t.index(['nro']);
  },
  com_viajes: (t) => {
    t.string('nro', 20).primary(); // VJ-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('placa', 20).notNullable();
    t.string('conductor', 140);
    t.string('origen', 120);
    t.string('destino', 120);
    t.string('salida', 10);
    t.string('retorno', 10);
    t.decimal('km_estimado', 14, 2);
    t.decimal('litros_estimados', 14, 2);
    t.string('apertura', 30);
    t.string('desc_apertura', 200);
    money(t, 'fondo');
    t.text('motivo');
    t.string('nota', 60);
    t.string('comprobante', 60);
    t.text('funcionarios');
    t.string('estado', 14).defaultTo('En curso'); // En curso | Descargado
    t.string('fecha_descargo', 10);
    t.decimal('km_recorrido', 14, 2);
    t.decimal('litros_comprados', 14, 2);
    money(t, 'gastado');
    money(t, 'saldo');
    t.decimal('rendimiento_real', 12, 4);
    t.string('resultado', 12);
    t.text('alertas');
    t.text('actividades');
    t.text('conclusiones');
    t.string('usuario', 60);
    t.string('registrado', 30);
  },
  com_viajes_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.string('tipo', 10).notNullable(); // TRAMO | COMPRA
    t.string('placa', 20);
    t.string('fecha', 10);
    t.string('origen', 120);
    t.string('destino', 120);
    t.string('hora_salida', 8);
    t.string('hora_llegada', 8);
    t.decimal('km_inicial', 14, 2);
    t.decimal('km_final', 14, 2);
    t.decimal('recorrido', 14, 2);
    t.string('estacion', 120);
    t.string('factura', 40);
    t.decimal('litros', 14, 2);
    money(t, 'total');
    t.index(['nro']);
  },

  // ───────────────────────── ACTIVOS FIJOS ─────────────────────────
  af_cuentas: (t) => {
    t.integer('id_cta').primary();
    t.string('cuenta', 120).notNullable();
    t.string('partida', 10);
    t.integer('cod_vsiaf');
    t.string('cuenta_vsiaf', 120);
    t.integer('vida_util').defaultTo(0);
  },
  af_auxiliares: (t) => {
    t.integer('id_cta').notNullable();
    t.integer('id_aux').notNullable();
    t.string('auxiliar', 160).notNullable();
    t.primary(['id_cta', 'id_aux']);
  },
  af_campos: (t) => {
    t.integer('id_cta').notNullable();
    t.integer('nro').notNullable();
    t.string('campo', 120).notNullable();
    t.string('descripcion', 240);
    t.primary(['id_cta', 'nro']);
  },
  af_edificios: (t) => {
    t.integer('cod_edif').primary();
    t.string('edificio', 160).notNullable();
    t.string('sector', 40);
    t.string('comunidad', 100);
    t.string('responsable', 140);
  },
  af_ambientes: (t) => {
    t.integer('cod_edif').notNullable();
    t.integer('cod_amb').notNullable();
    t.string('ambiente', 140).notNullable();
    t.string('responsable', 140);
    t.primary(['cod_edif', 'cod_amb']);
  },
  af_estados: (t) => {
    t.string('cod', 2).primary();
    t.string('estado', 20).notNullable().unique();
    t.decimal('factor', 6, 3);
    t.text('descripcion');
  },
  af_ingresos: (t) => {
    t.string('nro', 20).primary(); // ING-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('tipo_doc', 30);
    t.string('nro_doc', 40);
    t.string('preventivo', 30);
    t.string('proveedor', 200);
    t.string('nit', 30);
    t.string('factura', 40);
    t.string('nro_memo', 40);
    t.string('comision1', 140);
    t.string('comision2', 140);
    t.string('unidad', 160);
    t.string('fuente_fin', 120);
    t.text('observaciones');
    money(t, 'total');
    t.string('estado', 16).defaultTo('REGISTRADO'); // REGISTRADO|PARCIAL|CODIFICADO
    t.string('fecha_reg', 30);
  },
  af_ingresos_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.integer('id_cta').notNullable();
    t.integer('id_aux').notNullable();
    t.string('descripcion', 240);
    t.string('unidad', 20);
    t.integer('cantidad').notNullable();
    money(t, 'precio_unit');
    money(t, 'total');
    t.integer('cant_codif').defaultTo(0);
    t.index(['nro']);
  },
  af_activos: (t) => {
    t.string('codigo', 20).primary(); // EEE-AA-CCXXX-NN
    t.string('nro_ingreso', 20);
    t.integer('item');
    t.integer('cod_edif').notNullable();
    t.integer('cod_amb').notNullable();
    t.integer('id_cta').notNullable();
    t.integer('id_aux').notNullable();
    t.string('auxiliar', 160);
    t.integer('correl').notNullable();
    t.string('descripcion', 240);
    t.string('marca', 80);
    t.string('modelo', 80);
    t.string('serie', 80);
    t.string('color', 40);
    t.string('estado', 20).defaultTo('Nuevo');
    money(t, 'valor');
    t.string('fecha_ingreso', 10);
    t.string('fecha_codif', 10);
    t.string('situacion', 14).notNullable().defaultTo('EN ALMACEN'); // EN ALMACEN|ASIGNADO|BAJA
    t.string('funcionario', 140);
    t.string('ci_func', 30);
    t.string('nro_acta', 20);
    t.string('fecha_asig', 10);
    t.integer('edif_actual');
    t.integer('amb_actual');
    for (let i = 1; i <= 13; i++) t.string('c' + String(i).padStart(2, '0'), 200);
    for (let i = 1; i <= 4; i++) t.string('foto' + i, 300);
    t.string('etq_impresa', 2).defaultTo('NO');
    t.text('observaciones');
    t.index(['situacion']);
    t.index(['funcionario']);
    t.index(['nro_ingreso']);
  },
  af_solicitudes: (t) => {
    t.string('nro', 20).primary(); // SOL-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('unidad', 160);
    t.string('funcionario', 140);
    t.string('cargo', 140);
    t.text('justificacion');
    t.string('aprobado_daf', 2).defaultTo('NO');
    t.string('estado', 18).defaultTo('PENDIENTE'); // PENDIENTE|ATENDIDA|ATENDIDA PARCIAL|SIN EXISTENCIA
    t.string('nro_acta', 200);
    t.string('fecha_reg', 30);
  },
  af_solicitudes_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.integer('item').notNullable();
    t.integer('id_cta').notNullable();
    t.integer('id_aux').notNullable();
    t.string('descripcion', 240);
    t.integer('cantidad').notNullable();
    t.integer('saldo').defaultTo(0);
    t.index(['nro']);
  },
  af_asignaciones: (t) => {
    t.string('nro', 20).primary(); // ASG-0001/2026
    t.string('fecha', 10).notNullable();
    t.string('nro_sol', 20);
    t.string('funcionario', 140);
    t.string('ci', 30);
    t.string('cargo', 140);
    t.string('unidad', 160);
    t.integer('cod_edif');
    t.integer('cod_amb');
    t.integer('cantidad');
    money(t, 'valor');
    t.text('observaciones');
    t.string('fecha_reg', 30);
  },
  af_asignaciones_det: (t) => {
    t.increments('id');
    t.string('nro', 20).notNullable();
    t.string('codigo', 20).notNullable();
    t.index(['nro']);
  },
  af_movimientos: (t) => {
    t.increments('id');
    t.string('fecha', 10).notNullable();
    t.string('codigo', 20).notNullable();
    t.string('tipo', 30).notNullable();
    t.string('documento', 30);
    t.string('origen', 200);
    t.string('destino', 200);
    t.text('detalle');
    t.string('usuario', 60);
    t.string('fecha_reg', 30);
    t.index(['codigo']);
  },
};

export const TABLE_ORDER = Object.keys(TABLES);

export async function createSchema(knex: Knex): Promise<void> {
  for (const name of TABLE_ORDER) {
    if (!(await knex.schema.hasTable(name))) {
      await knex.schema.createTable(name, TABLES[name]);
    }
  }
}
