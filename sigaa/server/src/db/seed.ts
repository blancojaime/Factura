/**
 * Carga de datos iniciales: configuración unificada + maestros y datos demo
 * extraídos de los tres libros originales (tools/extract_seed.py → server/seed/*.json).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Knex } from 'knex';
import { createSchema } from './schema.js';
import { DEFAULT_CONFIG } from './defaults.js';
import { asegurarAdmin } from '../core/auth.js';
import { registrarNro } from '../core/services.js';

type Row = Record<string, any>;
const here = path.dirname(fileURLToPath(import.meta.url));
const SEED_DIR = process.env.SIGAA_SEED_DIR || path.resolve(here, '../../seed');

const load = (f: string): Record<string, Row[]> => JSON.parse(fs.readFileSync(path.join(SEED_DIR, f), 'utf8'));

/** Normaliza fechas: ISO con hora, 'M/D/YYYY' o Date → 'YYYY-MM-DD'. */
export function d(v: any): string | null {
  if (v === null || v === undefined || v === '') return null;
  const s = String(v).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s);
  if (m) return `${m[3]}-${m[1].padStart(2, '0')}-${m[2].padStart(2, '0')}`;
  return null;
}
const ts = (v: any): string | null => (v ? String(v).replace('T', ' ').slice(0, 19) : null);
const s = (v: any): string | null => (v === null || v === undefined || v === '' ? null : String(v).trim());
const n = (v: any, def = 0): number => (v === null || v === undefined || v === '' || isNaN(Number(v)) ? def : Number(v));
const pad2 = (v: any): string => String(v).padStart(2, '0');

async function ins(db: Knex, table: string, rows: Row[]) {
  if (!rows.length) return;
  await db.batchInsert(table, rows, 40);
}
/** Inserta ignorando duplicados de clave única (maestros compartidos entre sistemas). */
async function insIgnore(db: Knex, table: string, rows: Row[], key: string) {
  const seen = new Set((await db(table).select(key)).map((r: any) => r[key]));
  const nuevos: Row[] = [];
  for (const r of rows) {
    if (r[key] === null || r[key] === undefined || seen.has(r[key])) continue;
    seen.add(r[key]);
    nuevos.push(r);
  }
  await ins(db, table, nuevos);
}

export async function seedConfig(db: Knex) {
  const ex = new Set((await db('core_config').select('clave')).map((r: any) => r.clave));
  await ins(db, 'core_config', DEFAULT_CONFIG.filter((c) => !ex.has(c.clave)));
}

export async function seedAlmacenes(db: Knex) {
  const a = load('almacenes.json');
  const bodNom = new Map<string, string>(a.T_BODEGAS.map((b) => [String(b.Bodega), pad2(b.CodBod)]));
  const bc = (v: any): string | null => (v === null || v === undefined ? null : bodNom.get(String(v)) ?? (/^\d+$/.test(String(v)) ? pad2(v) : null));

  await ins(db, 'alm_bodegas', a.T_BODEGAS.map((b) => ({ cod: pad2(b.CodBod), nombre: b.Bodega, responsable: s(b.Responsable), ubicacion: s(b.Ubicacion), estado: s(b.Estado) ?? 'ACTIVO' })));
  await ins(db, 'alm_grupos', a.T_GRUPOS.map((g) => ({ grupo: g.Grupo, nombre: g.NombreGrupo })));
  await ins(db, 'alm_subgrupos', a.T_SUBGRUPOS.map((g) => ({ grupo: g.Grupo, subgrupo: g.SubGrupo, nombre: g.Nombre })));
  await ins(db, 'alm_unidades_medida', a.T_UMEDIDA.map((u) => ({ nombre: u.Unidad })));
  await ins(db, 'alm_causales', a.T_CAUSALES.map((c) => ({ causal: c.Causal, grupo: c.Grupo })));
  await ins(db, 'alm_pasos', a.T_PASOS.map((p) => ({ grupo: p.Grupo, orden: p.Orden, paso: p.Paso, doc: s(p.Doc), clase: s(p.Clase), obligatorio: s(p.Obligatorio) ?? 'SI' })));
  await ins(db, 'alm_docreq', a.T_DOCREQ.map((p) => ({ tipo: p.Tipo, orden: p.Orden, documento: p.Documento, obligatorio: s(p.Obligatorio) ?? 'SI' })));
  await ins(db, 'alm_extintores', a.T_EXTINT.map((x) => ({ cod: x.CodExt, cod_bod: bc(x.Bodega), tipo: s(x.Tipo), capacidad: s(x.Capacidad), ult_recarga: d(x.UltRecarga), venc_recarga: d(x.VencRecarga), estado: s(x.Estado) ?? 'ACTIVO' })));
  await ins(db, 'alm_seguros', a.T_SEGUROS.map((x) => ({ poliza: x.Poliza, aseguradora: s(x.Aseguradora), cobertura: s(x.Cobertura), desde: d(x.Desde), hasta: d(x.Hasta), monto_asegurado: n(x.MontoAsegurado), archivo: s(x.Archivo), estado: s(x.Estado) ?? 'VIGENTE' })));
  await ins(db, 'alm_catalogo', a.T_CATALOGO.map((c) => ({
    codigo: c.Codigo, grupo: c.Grupo, subgrupo: c.SubGrupo, correlativo: c.Correlativo, descripcion: c.Descripcion, unidad: c.Unidad, partida: s(c.Partida), cod_bod: pad2(c.CodBod),
    stock_min: n(c.StockMin), stock_max: n(c.StockMax), perecible: s(c.Perecible) ?? 'NO', peligroso: s(c.Peligroso) ?? 'NO', ubicacion: s(c.Ubicacion), precio_ref: n(c.PrecioRef), estado: s(c.Estado) ?? 'ACTIVO', fecha_reg: ts(c.FechaReg),
  })));
  // maestros compartidos
  await insIgnore(db, 'core_unidades', a.T_UNIDADES.map((u) => ({ nombre: u.Unidad, responsable: s(u.Responsable), cargo: s(u.Cargo) })), 'nombre');
  await insIgnore(db, 'core_funcionarios', a.T_FUNC.map((f) => ({ nombre: f.Nombre, ci: s(f.CI), cargo: s(f.Cargo), unidad: s(f.Unidad), celular: s(f.Celular), estado: s(f.Estado) ?? 'ACTIVO' })), 'nombre');
  await insIgnore(db, 'core_proveedores', a.T_PROV.map((p) => ({ nit: String(p.NIT), razon_social: p.RazonSocial, contacto: s(p.Contacto), telefono: s(p.Telefono), estado: s(p.Estado) ?? 'ACTIVO' })), 'razon_social');
  await insIgnore(db, 'core_proyectos', a.T_PROY.map((p) => ({ nombre: p.Proyecto, estado: s(p.Estado) ?? 'ACTIVO' })), 'nombre');
  await insIgnore(db, 'core_partidas', a.T_PARTIDAS.map((p) => ({ partida: String(p.Partida), descripcion: p.Descripcion })), 'partida');

  // transacciones demo
  await ins(db, 'alm_ingresos', a.T_ING.map((i) => ({
    nro: i.NroCGI, fecha: d(i.Fecha), cod_bod: bc(i.Bodega), tipo: i.Tipo, proveedor: s(i.Proveedor), nit: s(i.NIT), nro_oc: s(i.NroOC), plazo_entrega: d(i.PlazoEntrega), factura: s(i.Factura), fecha_factura: d(i.FechaFactura),
    unidad: s(i.Unidad), preventivo: s(i.Preventivo), nro_pse: s(i.NroPSE), proyecto: s(i.Proyecto), fuente: s(i.Fuente), partida: s(i.Partida), comision: s(i.Comision), obs_plazo: s(i.ObsPlazo), total: n(i.Total), estado: i.Estado, fecha_reg: ts(i.FechaReg), usuario: s(i.Usuario),
  })));
  await ins(db, 'alm_ingresos_det', a.T_INGDET.map((x) => ({ nro: x.NroCGI, item: x.Item, cod_item: x.CodItem, descripcion: s(x.Descripcion), unidad: s(x.Unidad), cantidad: n(x.Cantidad), precio_unit: n(x.PrecioUnit), total: n(x.Total), vencimiento: d(x.Vencimiento), lote: s(x.Lote) })));
  await ins(db, 'alm_ingresos_doc', a.T_INGDOC.map((x) => ({ nro: x.NroCGI, orden: x.Orden, documento: x.Documento, estado: s(x.Estado) })));
  await ins(db, 'alm_salidas', a.T_SAL.map((x) => ({
    nro: x.NroVale, fecha_pedido: d(x.FechaPedido), cod_bod: bc(x.Bodega), estado: x.Estado, unidad: s(x.Unidad), solicitante: s(x.Solicitante), cargo: s(x.Cargo), superior: s(x.Superior), proyecto: s(x.Proyecto), nota_interna: s(x.NotaInterna),
    justificacion: s(x.Justificacion), observ: s(x.Observ), excepcion: s(x.Excepcion), fecha_aprob: ts(x.FechaAprob), aprobador: s(x.Aprobador), fecha_entrega: ts(x.FechaEntrega), entregador: s(x.Entregador), total: n(x.Total), fecha_reg: ts(x.FechaReg), usuario: s(x.Usuario),
  })));
  await ins(db, 'alm_salidas_det', a.T_SALDET.map((x) => ({ nro: x.NroVale, item: x.Item, cod_item: x.CodItem, descripcion: s(x.Descripcion), unidad: s(x.Unidad), cant_pedida: n(x.CantPedida), cant_entregada: n(x.CantEntregada), precio_prom: n(x.PrecioProm), total: n(x.Total), obs: s(x.Obs) })));
  const nroLote = new Map<string, string>();
  for (const x of a.T_INGDET) if (x.Lote) nroLote.set(`${x.NroCGI}|${x.CodItem}`, String(x.Lote));
  await ins(db, 'alm_lotes', a.T_LOTES.map((l) => ({
    id_lote: l.IdLote, cod_bod: pad2(l.Bodega), cod_item: l.CodItem, doc_origen: s(l.DocOrigen), fecha_ing: d(l.FechaIng), vencimiento: d(l.Vencimiento), cant_inicial: n(l.CantInicial), saldo: n(l.Saldo), precio_unit: n(l.PrecioUnit), estado: l.Estado, nro_lote: nroLote.get(`${l.DocOrigen}|${l.CodItem}`) ?? null,
  })));
  await ins(db, 'alm_movimientos', a.T_MOV.map((m) => ({
    id_mov: m.IdMov, fecha: d(m.Fecha), cod_bod: pad2(m.Bodega), cod_item: m.CodItem, tipo: m.Tipo, documento: s(m.Documento), id_lote: s(m.IdLote), cant_ent: n(m.CantEnt), cant_sal: n(m.CantSal), precio_unit: n(m.PrecioUnit), imp_ent: n(m.ImpEnt), imp_sal: n(m.ImpSal),
    referencia: s(m.Referencia), anulado: s(m.Anulado), usuario: s(m.Usuario), fecha_reg: ts(m.FechaReg),
  })));
  await ins(db, 'alm_inventarios', a.T_INV.map((x) => ({ nro: x.NroInv, fecha: d(x.Fecha), cod_bod: bc(x.Bodega), tipo: x.Tipo, responsable: s(x.Responsable), designado: s(x.Designado), observador: s(x.Observador), corte_ing: s(x.CorteIng), corte_sal: s(x.CorteSal), estado: x.Estado, faltante_bs: n(x.FaltanteBs), sobrante_bs: n(x.SobranteBs), fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'alm_inventarios_det', a.T_INVDET.map((x) => ({ nro: x.NroInv, item: x.Item, cod_item: x.CodItem, descripcion: s(x.Descripcion), unidad: s(x.Unidad), saldo_sist: n(x.SaldoSist), conteo: x.Conteo === null ? null : n(x.Conteo), diferencia: n(x.Diferencia), precio_unit: n(x.PrecioUnit), estado_bien: s(x.EstadoBien), obs: s(x.Obs) })));
  const gr = new Map<string, string>(a.T_CAUSALES.map((c) => [c.Causal, c.Grupo]));
  await ins(db, 'alm_bajas', a.T_BAJA.map((x) => ({ nro: x.NroBaja, fecha: d(x.Fecha), cod_bod: bc(x.Bodega), causal: x.Causal, grupo: s(x.Grupo) ?? gr.get(x.Causal) ?? null, responsable: s(x.Responsable), justificacion: s(x.Justificacion), nro_ra: s(x.NroRA), fecha_ra: d(x.FechaRA), total: n(x.Total), estado: x.Estado, origen: s(x.Origen), fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'alm_bajas_det', a.T_BAJADET.map((x) => ({ nro: x.NroBaja, item: x.Item, cod_item: x.CodItem, descripcion: s(x.Descripcion), unidad: s(x.Unidad), id_lote: s(x.IdLote), cantidad: n(x.Cantidad), precio_unit: n(x.PrecioUnit), total: n(x.Total) })));
  await ins(db, 'alm_bajas_paso', a.T_BAJAPASO.map((x) => ({ nro: x.NroBaja, orden: x.Orden, paso: x.Paso, doc: s(x.Doc), clase: s(x.Clase), referencia: s(x.Referencia), fecha: d(x.Fecha), estado: s(x.Estado) ?? 'PENDIENTE', respaldo: s(x.Respaldo) })));
  await ins(db, 'alm_transferencias', a.T_TRF.map((x) => ({ nro: x.NroTrf, fecha: d(x.Fecha), bod_origen: bc(x.BodOrigen), bod_destino: bc(x.BodDestino), entrega: s(x.Entrega), recibe: s(x.Recibe), motivo: s(x.Motivo), total: n(x.Total), estado: x.Estado, fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'alm_transferencias_det', a.T_TRFDET.map((x) => ({ nro: x.NroTrf, item: x.Item, cod_item: x.CodItem, descripcion: s(x.Descripcion), unidad: s(x.Unidad), cantidad: n(x.Cantidad), precio_unit: n(x.PrecioUnit), total: n(x.Total) })));
  await ins(db, 'alm_requerimientos', a.T_REQ.map((x) => ({ nro: x.NroReq, fecha: d(x.Fecha), cod_bod: bc(x.Bodega), tipo: s(x.Tipo), total: n(x.Total), estado: s(x.Estado), justificacion: s(x.Justificacion), fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'alm_requerimientos_det', a.T_REQDET.map((x) => ({ nro: x.NroReq, item: x.Item, cod_item: x.CodItem, descripcion: s(x.Descripcion), unidad: s(x.Unidad), stock: n(x.Stock), cant_solic: n(x.CantSolic), precio_ref: n(x.PrecioRef), total: n(x.Total), partida: s(x.Partida) })));
  await ins(db, 'alm_inspecciones', a.T_INSP.map((x) => ({ nro: x.NroInsp, fecha: d(x.Fecha), cod_bod: bc(x.Bodega), inspector: s(x.Inspector), cumple: n(x.Cumple), no_cumple: n(x.NoCumple), observ: s(x.Observ), fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'alm_inspecciones_det', a.T_INSPDET.map((x) => ({ nro: x.NroInsp, item: x.Item, criterio: x.Criterio, resultado: s(x.Resultado), obs: s(x.Obs) })));
  await ins(db, 'core_bitacora', a.T_BITAC.map((x) => ({ fecha: ts(x.Fecha), usuario: s(x.UsuarioApp) ?? s(x.UsuarioWin), modulo: s(x.Modulo), accion: s(x.Accion), documento: s(x.Documento), detalle: s(x.Detalle) })));
  const nros = [...a.T_ING.map((x) => x.NroCGI), ...a.T_SAL.map((x) => x.NroVale), ...a.T_INV.map((x) => x.NroInv), ...a.T_BAJA.map((x) => x.NroBaja), ...a.T_TRF.map((x) => x.NroTrf), ...a.T_REQ.map((x) => x.NroReq), ...a.T_INSP.map((x) => x.NroInsp)];
  for (const x of nros) await registrarNro(db, x);
}

export async function seedCombustible(db: Knex) {
  const c = load('combustible.json');
  await ins(db, 'com_tipos', c.tblTipos.map((t) => ({ tipo: t.Tipo, clase: s(t.Clase), medidor: s(t.Medidor), rendimiento_ref: n(t['Rendimiento Ref']) })));
  await ins(db, 'com_vehiculos', c.tblVehiculos.map((v) => ({
    codigo: v['Código'], placa: String(v.Placa), tipo: s(v.Tipo), clase: s(v.Clase), uso: s(v.Uso), marca: s(v.Marca), modelo: s(v.Modelo), anio: v['Año'] ?? null, color: s(v.Color), combustible: s(v.Combustible), medidor: s(v.Medidor),
    capacidad_tanque: n(v['Capacidad Tanque L']), rendimiento: n(v.Rendimiento), unidad: s(v.Unidad), conductor: s(v['Conductor Asignado']), acta_asignacion: s(v['Acta Asignación']), estado: s(v.Estado) ?? 'Activo', observaciones: s(v.Observaciones),
  })));
  await ins(db, 'com_conductores', c.tblConductores.map((x) => ({ ci: String(x.CI), nombre: x.Nombre, cargo: s(x.Cargo), unidad: s(x.Unidad), celular: s(x.Celular), licencia: s(x.Licencia), categoria: s(x['Categoría']), vence_licencia: d(x['Vence Licencia']), estado: s(x.Estado) ?? 'Activo', observaciones: s(x.Observaciones) })));
  await ins(db, 'com_puestos', c.tblPuestos.map((x) => ({ codigo: x['Código'], nombre: x.Nombre, ubicacion: s(x['Ubicación']), responsable: s(x.Responsable), combustible: s(x.Combustible), capacidad_l: n(x['Capacidad L']), estado: s(x.Estado) ?? 'Activo' })));
  await ins(db, 'com_contratos', c.tblContratos.map((x) => ({
    nro: x['Nro Contrato'], proveedor: x.Proveedor, modalidad: s(x.Modalidad), combustible: s(x.Combustible), fecha_firma: d(x['Fecha Firma']), vigencia_desde: d(x['Vigencia Desde']), vigencia_hasta: d(x['Vigencia Hasta']),
    monto: n(x['Monto Bs']), recibido: n(x['Recibido Bs']), saldo: n(x['Saldo Bs']), estado: s(x.Estado) ?? 'Vigente', observaciones: s(x.Observaciones),
  })));
  await ins(db, 'com_precios', c.tblPrecios.map((x) => ({ combustible: x.Combustible, precio: n(x['Precio Bs L']), vigente_desde: d(x['Vigente Desde']), norma: s(x.Norma) })));
  await insIgnore(db, 'core_unidades', c.tblUnidades.map((u) => ({ nombre: u.Unidad, sigla: s(u['Código']), responsable: s(u.Responsable), cargo: s(u.Cargo) })), 'nombre');
  await insIgnore(db, 'core_aperturas', c.tblAperturas.map((x) => ({ apertura: x.Apertura, descripcion: s(x['Descripción']), presupuesto: n(x['Presupuesto Bs']) })), 'apertura');
  await insIgnore(db, 'core_proveedores', c.tblProveedores.map((x) => ({ nit: String(x.NIT), razon_social: x['Razón Social'], estacion: s(x['Estación de Servicio']), direccion: s(x['Dirección']), telefono: s(x['Teléfono']) })), 'razon_social');
}

export async function seedActivos(db: Knex) {
  const f = load('activos.json');
  await ins(db, 'af_cuentas', f.T_CUENTAS.map((x) => ({ id_cta: x.ID_Cta, cuenta: x.Cuenta, partida: s(x.Partida), cod_vsiaf: x.Cod_VSIAF, cuenta_vsiaf: s(x.Cuenta_VSIAF), vida_util: n(x.Vida_Util) })));
  await ins(db, 'af_auxiliares', f.T_AUX.map((x) => ({ id_cta: x.ID_Cta, id_aux: x.ID_Aux, auxiliar: x.Auxiliar })));
  await ins(db, 'af_campos', f.T_CAMPOS.map((x) => ({ id_cta: x.ID_Cta, nro: x.Nro, campo: x.Campo, descripcion: s(x.Descripcion) })));
  await ins(db, 'af_edificios', f.T_EDIF.map((x) => ({ cod_edif: x.CodEdif, edificio: x.Edificio, sector: s(x.Sector), comunidad: s(x.Comunidad), responsable: s(x.Responsable) })));
  await ins(db, 'af_ambientes', f.T_AMB.map((x) => ({ cod_edif: x.CodEdif, cod_amb: x.CodAmb, ambiente: x.Ambiente, responsable: s(x.Responsable) })));
  await ins(db, 'af_estados', f.T_ESTADOS.map((x) => ({ cod: pad2(x.Cod), estado: x.Estado, factor: n(x.Factor), descripcion: s(x.Descripcion) })));
  await insIgnore(db, 'core_unidades', f.T_UNID.map((u) => ({ nombre: u.Unidad })), 'nombre');
  await insIgnore(db, 'core_funcionarios', f.T_FUNC.map((x) => ({ nombre: x.Nombre, ci: s(x.CI), cargo: s(x.Cargo), unidad: s(x.Unidad), celular: s(x.Celular), estado: s(x.Estado) ?? 'ACTIVO' })), 'nombre');
  await insIgnore(db, 'core_proveedores', f.T_PROV.map((x) => ({ nit: String(x.NIT), razon_social: x.RazonSocial, contacto: s(x.Representante), telefono: s(x.Telefono), direccion: s(x.Direccion) })), 'razon_social');
  await ins(db, 'af_ingresos', f.T_INGRESOS.map((x) => ({ nro: x.NroIngreso, fecha: d(x.Fecha), tipo_doc: s(x.TipoDoc), nro_doc: s(x.NroDoc), preventivo: s(x.Preventivo), proveedor: s(x.Proveedor), nit: s(x.NIT), factura: s(x.Factura), nro_memo: s(x.NroMemo), comision1: s(x.Comision1), comision2: s(x.Comision2), unidad: s(x.Unidad), fuente_fin: s(x.FuenteFin), observaciones: s(x.Observaciones), total: n(x.Total), estado: x.Estado, fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'af_ingresos_det', f.T_INGDET.map((x) => ({ nro: x.NroIngreso, item: x.Item, id_cta: x.ID_Cta, id_aux: x.ID_Aux, descripcion: s(x.Descripcion), unidad: s(x.Unidad), cantidad: n(x.Cantidad), precio_unit: n(x.PrecioUnit), total: n(x.Total), cant_codif: n(x.CantCodif) })));
  await ins(db, 'af_activos', f.T_ACTIVOS.map((x) => {
    const r: Row = {
      codigo: x.Codigo, nro_ingreso: s(x.NroIngreso), item: x.Item ?? null, cod_edif: x.CodEdif, cod_amb: x.CodAmb, id_cta: x.ID_Cta, id_aux: x.ID_Aux, auxiliar: s(x.Auxiliar), correl: x.Correl, descripcion: s(x.Descripcion), marca: s(x.Marca), modelo: s(x.Modelo), serie: s(x.Serie), color: s(x.Color),
      estado: s(x.Estado) ?? 'Nuevo', valor: n(x.Valor), fecha_ingreso: d(x.FechaIngreso), fecha_codif: d(x.FechaCodif), situacion: s(x.Situacion) === 'EN ALMACÉN' ? 'EN ALMACEN' : s(x.Situacion) ?? 'EN ALMACEN', funcionario: s(x.Funcionario), ci_func: s(x.CI_Func), nro_acta: s(x.NroActa), fecha_asig: d(x.FechaAsig),
      edif_actual: x.EdifActual ?? null, amb_actual: x.AmbActual ?? null, etq_impresa: s(x.EtqImpresa) ?? 'NO', observaciones: s(x.Observaciones),
    };
    for (let i = 1; i <= 13; i++) r['c' + pad2(i)] = s(x['C' + pad2(i)]);
    for (let i = 1; i <= 4; i++) r['foto' + i] = s(x['Foto' + i]);
    return r;
  }));
  await ins(db, 'af_solicitudes', f.T_SOLIC.map((x) => ({ nro: x.NroSol, fecha: d(x.Fecha), unidad: s(x.Unidad), funcionario: s(x.Funcionario), cargo: s(x.Cargo), justificacion: s(x.Justificacion), aprobado_daf: s(x.AprobadoDAF) ?? 'NO', estado: x.Estado, nro_acta: s(x.NroActa), fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'af_solicitudes_det', f.T_SOLDET.map((x) => ({ nro: x.NroSol, item: x.Item, id_cta: x.ID_Cta, id_aux: x.ID_Aux, descripcion: s(x.Descripcion), cantidad: n(x.Cantidad), saldo: n(x.Saldo) })));
  await ins(db, 'af_asignaciones', f.T_ASIG.map((x) => ({ nro: x.NroActa, fecha: d(x.Fecha), nro_sol: s(x.NroSol), funcionario: s(x.Funcionario), ci: s(x.CI), cargo: s(x.Cargo), unidad: s(x.Unidad), cod_edif: x.CodEdif ?? null, cod_amb: x.CodAmb ?? null, cantidad: n(x.Cantidad), valor: n(x.Valor), observaciones: s(x.Observaciones), fecha_reg: ts(x.FechaReg) })));
  await ins(db, 'af_asignaciones_det', f.T_ASIGDET.map((x) => ({ nro: x.NroActa, codigo: x.Codigo })));
  await ins(db, 'af_movimientos', f.T_MOV.map((x) => ({ fecha: d(x.Fecha), codigo: x.Codigo, tipo: x.Tipo, documento: s(x.Documento), origen: s(x.Origen), destino: s(x.Destino), detalle: s(x.Detalle), usuario: s(x.Usuario), fecha_reg: ts(x.FechaReg) })));
  for (const x of [...f.T_INGRESOS.map((r) => r.NroIngreso), ...f.T_SOLIC.map((r) => r.NroSol), ...f.T_ASIG.map((r) => r.NroActa)]) await registrarNro(db, x);
}

export async function seedAll(db: Knex, opts: { demo?: boolean } = {}) {
  await createSchema(db);
  await seedConfig(db);
  if (opts.demo !== false) {
    const hay = await db('alm_bodegas').first();
    if (!hay) {
      await seedAlmacenes(db);
      await seedCombustible(db);
      await seedActivos(db);
    }
  }
  await asegurarAdmin(db);
}
