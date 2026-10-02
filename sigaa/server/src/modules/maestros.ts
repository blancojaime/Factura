/**
 * Catálogos y bases de datos maestras (equivalentes a las hojas BD_* de los sistemas originales),
 * expuestos mediante un CRUD genérico dirigido por metadatos.
 */
import type { Db, Modulo, Usuario } from '../core/context.js';
import { Errores, fail, NotFound } from '../core/errors.js';
import { bitacora } from '../core/services.js';
import { num, txt } from '../core/util.js';
import { recalcularContratos } from './combustible/base.js';

export type ColType = 'text' | 'number' | 'select' | 'date' | 'longtext';
export interface MCol {
  name: string;
  label: string;
  type: ColType;
  required?: boolean;
  options?: string[];
  /** valores de otra tabla maestra: "tabla.columna" */
  ref?: string;
  readonly?: boolean;
  width?: number;
}
export interface Maestro {
  key: string;
  titulo: string;
  tabla: string;
  pk: string[];
  autoId?: boolean;
  modulo: Modulo;
  cols: MCol[];
  orden?: string[];
  /** si el registro está en uso en estas tablas/columnas no se puede eliminar */
  uso?: { tabla: string; col: string; label: string }[];
  /** columna cuyo valor se pasa a mayúsculas */
  mayus?: string[];
}

const T = (name: string, label: string, o: Partial<MCol> = {}): MCol => ({ name, label, type: 'text', ...o });
const N = (name: string, label: string, o: Partial<MCol> = {}): MCol => ({ name, label, type: 'number', ...o });
const D = (name: string, label: string, o: Partial<MCol> = {}): MCol => ({ name, label, type: 'date', ...o });
const S = (name: string, label: string, options: string[] | undefined, o: Partial<MCol> = {}): MCol => ({ name, label, type: 'select', options, ...o });
const ESTADO = ['ACTIVO', 'INACTIVO'];

export const MAESTROS: Maestro[] = [
  // ───── Compartidos ─────
  { key: 'unidades', titulo: 'Unidades organizacionales', tabla: 'core_unidades', pk: ['id'], autoId: true, modulo: 'core', cols: [T('nombre', 'Unidad', { required: true, width: 3 }), T('sigla', 'Sigla'), T('responsable', 'Responsable', { width: 2 }), T('cargo', 'Cargo', { width: 2 })], orden: ['nombre'] },
  { key: 'funcionarios', titulo: 'Funcionarios / servidores públicos', tabla: 'core_funcionarios', pk: ['id'], autoId: true, modulo: 'core', cols: [T('nombre', 'Nombre', { required: true, width: 3 }), T('ci', 'CI'), T('cargo', 'Cargo', { width: 2 }), T('unidad', 'Unidad', { ref: 'core_unidades.nombre', width: 2 }), T('celular', 'Celular'), S('estado', 'Estado', ESTADO)], orden: ['nombre'], mayus: ['nombre'] },
  { key: 'proveedores', titulo: 'Proveedores / estaciones de servicio', tabla: 'core_proveedores', pk: ['id'], autoId: true, modulo: 'core', cols: [T('nit', 'NIT', { required: true }), T('razon_social', 'Razón social', { required: true, width: 3 }), T('contacto', 'Contacto / representante'), T('telefono', 'Teléfono'), T('direccion', 'Dirección', { width: 2 }), T('estacion', 'Estación de servicio'), S('estado', 'Estado', ESTADO)], orden: ['razon_social'] },
  { key: 'proyectos', titulo: 'Proyectos / destinos', tabla: 'core_proyectos', pk: ['id'], autoId: true, modulo: 'core', cols: [T('nombre', 'Proyecto / destino', { required: true, width: 4 }), S('estado', 'Estado', ESTADO)], orden: ['nombre'] },
  { key: 'aperturas', titulo: 'Aperturas programáticas', tabla: 'core_aperturas', pk: ['id'], autoId: true, modulo: 'core', cols: [T('apertura', 'Apertura', { required: true }), T('descripcion', 'Descripción', { width: 3 }), N('presupuesto', 'Presupuesto Bs')], orden: ['apertura'] },
  { key: 'partidas', titulo: 'Partidas presupuestarias', tabla: 'core_partidas', pk: ['partida'], modulo: 'core', cols: [T('partida', 'Partida', { required: true }), T('descripcion', 'Descripción', { width: 4 })], orden: ['partida'] },
  // ───── Almacenes ─────
  { key: 'bodegas', titulo: 'Bodegas', tabla: 'alm_bodegas', pk: ['cod'], modulo: 'alm', cols: [T('cod', 'Código (2 dígitos)', { required: true }), T('nombre', 'Bodega', { required: true, width: 3 }), T('responsable', 'Responsable', { ref: 'core_funcionarios.nombre', width: 2 }), T('ubicacion', 'Ubicación'), S('estado', 'Estado', ESTADO)], orden: ['cod'], uso: [{ tabla: 'alm_catalogo', col: 'cod_bod', label: 'catálogo de ítems' }, { tabla: 'alm_lotes', col: 'cod_bod', label: 'existencias' }] },
  { key: 'grupos', titulo: 'Grupos de materiales', tabla: 'alm_grupos', pk: ['grupo'], modulo: 'alm', cols: [N('grupo', 'Grupo', { required: true }), T('nombre', 'Nombre', { required: true, width: 4 })], orden: ['grupo'], uso: [{ tabla: 'alm_subgrupos', col: 'grupo', label: 'subgrupos' }] },
  { key: 'subgrupos', titulo: 'Subgrupos de materiales', tabla: 'alm_subgrupos', pk: ['grupo', 'subgrupo'], modulo: 'alm', cols: [N('grupo', 'Grupo', { required: true }), N('subgrupo', 'Subgrupo', { required: true }), T('nombre', 'Nombre', { required: true, width: 4 })], orden: ['grupo', 'subgrupo'], uso: [{ tabla: 'alm_catalogo', col: 'subgrupo', label: 'catálogo' }] },
  { key: 'umedida', titulo: 'Unidades de medida', tabla: 'alm_unidades_medida', pk: ['nombre'], modulo: 'alm', cols: [T('nombre', 'Unidad', { required: true })], orden: ['nombre'], mayus: ['nombre'] },
  { key: 'causales', titulo: 'Causales de baja', tabla: 'alm_causales', pk: ['causal'], modulo: 'alm', cols: [T('causal', 'Causal', { required: true, width: 3 }), S('grupo', 'Grupo de trámite', ['A', 'B', 'C', 'D'], { required: true })], orden: ['grupo', 'causal'] },
  { key: 'pasos', titulo: 'Pasos del trámite de baja', tabla: 'alm_pasos', pk: ['id'], autoId: true, modulo: 'alm', cols: [S('grupo', 'Grupo', ['A', 'B', 'C', 'D'], { required: true }), N('orden', 'Orden', { required: true }), T('paso', 'Paso / documento', { required: true, width: 5 }), T('doc', 'Código de documento'), S('clase', 'Clase', ['', 'RA', 'BAJA', 'PUB']), S('obligatorio', 'Obligatorio', ['SI', 'NO'])], orden: ['grupo', 'orden'] },
  { key: 'docreq', titulo: 'Documentos de respaldo por tipo de ingreso', tabla: 'alm_docreq', pk: ['id'], autoId: true, modulo: 'alm', cols: [T('tipo', 'Tipo de ingreso', { required: true, width: 3 }), N('orden', 'Orden', { required: true }), T('documento', 'Documento', { required: true, width: 4 }), S('obligatorio', 'Obligatorio', ['SI', 'NO'])], orden: ['tipo', 'orden'] },
  { key: 'extintores', titulo: 'Extintores', tabla: 'alm_extintores', pk: ['cod'], modulo: 'alm', cols: [T('cod', 'Código', { required: true }), S('cod_bod', 'Bodega', undefined, { ref: 'alm_bodegas.cod' }), S('tipo', 'Tipo', ['PQS (polvo químico)', 'CO2', 'AGUA', 'ESPUMA']), T('capacidad', 'Capacidad'), D('ult_recarga', 'Última recarga'), D('venc_recarga', 'Vence recarga'), S('estado', 'Estado', ESTADO)], orden: ['cod'] },
  { key: 'seguros', titulo: 'Pólizas de seguro', tabla: 'alm_seguros', pk: ['poliza'], modulo: 'alm', cols: [T('poliza', 'Póliza', { required: true }), T('aseguradora', 'Aseguradora', { width: 2 }), T('cobertura', 'Cobertura', { width: 3 }), D('desde', 'Desde'), D('hasta', 'Hasta'), N('monto_asegurado', 'Monto asegurado Bs'), S('estado', 'Estado', ['VIGENTE', 'VENCIDA', 'ANULADA'])], orden: ['poliza'] },
  // ───── Combustible ─────
  { key: 'tipos-vehiculo', titulo: 'Tipos de vehículo / equipo (rendimiento de referencia)', tabla: 'com_tipos', pk: ['tipo'], modulo: 'com', cols: [T('tipo', 'Tipo', { required: true }), S('clase', 'Clase', ['Liviano', 'Semipesado', 'Pesado', 'Equipo menor']), S('medidor', 'Medidor', ['Km', 'Horas']), N('rendimiento_ref', 'Rendimiento ref. (L/km o L/h)')], orden: ['clase', 'tipo'] },
  { key: 'vehiculos', titulo: 'Parque automotor y maquinaria', tabla: 'com_vehiculos', pk: ['codigo'], modulo: 'com', cols: [T('codigo', 'Código', { required: true }), T('placa', 'Placa / código', { required: true }), T('tipo', 'Tipo', { ref: 'com_tipos.tipo', required: true }), S('clase', 'Clase', ['Liviano', 'Semipesado', 'Pesado', 'Equipo menor']), S('uso', 'Uso', ['Ejecutivo', 'Operativo'], { required: true }), T('marca', 'Marca'), T('modelo', 'Modelo'), N('anio', 'Año'), T('color', 'Color'), S('combustible', 'Combustible', ['Gasolina', 'Diésel', 'GNV'], { required: true }), S('medidor', 'Medidor', ['Km', 'Horas']), N('capacidad_tanque', 'Tanque (L)'), N('rendimiento', 'Rendimiento (L/km o L/h)'), T('unidad', 'Unidad', { width: 2 }), T('conductor', 'Conductor asignado', { ref: 'com_conductores.nombre', width: 2 }), T('acta_asignacion', 'Acta de asignación'), T('activo_codigo', 'Código de activo fijo'), S('estado', 'Estado', ['Activo', 'Inactivo', 'Baja']), T('observaciones', 'Observaciones', { width: 2 })], orden: ['codigo'] },
  { key: 'conductores', titulo: 'Conductores y operadores', tabla: 'com_conductores', pk: ['ci'], modulo: 'com', cols: [T('ci', 'CI', { required: true }), T('nombre', 'Nombre completo', { required: true, width: 3 }), T('cargo', 'Cargo', { width: 2 }), T('unidad', 'Unidad', { width: 2 }), T('celular', 'Celular'), T('licencia', 'Licencia'), S('categoria', 'Categoría', ['M', 'P', 'A', 'B', 'C', 'T']), D('vence_licencia', 'Vence licencia'), S('estado', 'Estado', ['Activo', 'Inactivo', 'Baja']), T('observaciones', 'Observaciones')], orden: ['nombre'], mayus: ['nombre'] },
  { key: 'puestos', titulo: 'Puestos de almacenamiento en turriles', tabla: 'com_puestos', pk: ['codigo'], modulo: 'com', cols: [T('codigo', 'Código', { required: true }), T('nombre', 'Nombre', { required: true, width: 2 }), T('ubicacion', 'Ubicación', { width: 2 }), T('responsable', 'Responsable', { width: 2 }), S('combustible', 'Combustible', ['Gasolina', 'Diésel', 'GNV'], { required: true }), N('capacidad_l', 'Capacidad (L)'), S('estado', 'Estado', ['Activo', 'Inactivo'])], orden: ['codigo'] },
  { key: 'contratos', titulo: 'Contratos de provisión de combustible', tabla: 'com_contratos', pk: ['nro'], modulo: 'com', cols: [T('nro', 'Nº contrato', { required: true, width: 2 }), T('proveedor', 'Proveedor', { ref: 'core_proveedores.razon_social', required: true, width: 3 }), S('modalidad', 'Modalidad', ['Prepago', 'Postpago'], { required: true }), S('combustible', 'Combustible', ['Gasolina', 'Diésel', 'GNV'], { required: true }), D('fecha_firma', 'Firma'), D('vigencia_desde', 'Vigencia desde'), D('vigencia_hasta', 'Vigencia hasta'), N('monto', 'Monto Bs', { required: true }), N('recibido', 'Recibido Bs', { readonly: true }), N('saldo', 'Saldo Bs', { readonly: true }), S('estado', 'Estado', ['Vigente', 'Concluido', 'Resuelto']), T('observaciones', 'Observaciones')], orden: ['nro'] },
  { key: 'precios', titulo: 'Precios de combustible (por vigencia)', tabla: 'com_precios', pk: ['id'], autoId: true, modulo: 'com', cols: [S('combustible', 'Combustible', ['Gasolina', 'Diésel', 'GNV'], { required: true }), N('precio', 'Precio Bs/L', { required: true }), D('vigente_desde', 'Vigente desde', { required: true }), T('norma', 'Norma')], orden: ['combustible', 'vigente_desde'] },
  // ───── Activos fijos ─────
  { key: 'cuentas', titulo: 'Cuentas contables y partidas', tabla: 'af_cuentas', pk: ['id_cta'], modulo: 'af', cols: [N('id_cta', 'Cta.', { required: true }), T('cuenta', 'Cuenta', { required: true, width: 4 }), T('partida', 'Partida'), N('cod_vsiaf', 'Cód. VSIAF'), T('cuenta_vsiaf', 'Cuenta VSIAF', { width: 2 }), N('vida_util', 'Vida útil (años)')], orden: ['id_cta'], uso: [{ tabla: 'af_activos', col: 'id_cta', label: 'activos' }] },
  { key: 'auxiliares', titulo: 'Auxiliares contables (tipos de activo)', tabla: 'af_auxiliares', pk: ['id_cta', 'id_aux'], modulo: 'af', cols: [N('id_cta', 'Cta.', { required: true }), N('id_aux', 'Aux.', { required: true }), T('auxiliar', 'Auxiliar', { required: true, width: 4 })], orden: ['id_cta', 'id_aux'], uso: [{ tabla: 'af_activos', col: 'id_aux', label: 'activos' }], mayus: ['auxiliar'] },
  { key: 'campos', titulo: 'Campos técnicos por cuenta (ficha)', tabla: 'af_campos', pk: ['id_cta', 'nro'], modulo: 'af', cols: [N('id_cta', 'Cta.', { required: true }), N('nro', 'Nº (1-13)', { required: true }), T('campo', 'Campo', { required: true, width: 3 }), T('descripcion', 'Descripción', { width: 4 })], orden: ['id_cta', 'nro'] },
  { key: 'edificios', titulo: 'Edificios / establecimientos', tabla: 'af_edificios', pk: ['cod_edif'], modulo: 'af', cols: [N('cod_edif', 'Código (1-999)', { required: true }), T('edificio', 'Edificio', { required: true, width: 3 }), S('sector', 'Sector', ['EDUCACIÓN', 'SALUD', 'EJECUTIVO', 'DEPORTES', 'PRODUCTIVO', 'OTROS']), T('comunidad', 'Comunidad'), T('responsable', 'Responsable', { ref: 'core_funcionarios.nombre', width: 2 })], orden: ['cod_edif'], uso: [{ tabla: 'af_activos', col: 'cod_edif', label: 'activos' }] },
  { key: 'ambientes', titulo: 'Ambientes por edificio', tabla: 'af_ambientes', pk: ['cod_edif', 'cod_amb'], modulo: 'af', cols: [N('cod_edif', 'Edificio', { required: true }), N('cod_amb', 'Ambiente (0-99)', { required: true }), T('ambiente', 'Ambiente', { required: true, width: 3 }), T('responsable', 'Responsable', { width: 2 })], orden: ['cod_edif', 'cod_amb'] },
  { key: 'estados', titulo: 'Estados de conservación', tabla: 'af_estados', pk: ['cod'], modulo: 'af', cols: [T('cod', 'Cód.', { required: true }), T('estado', 'Estado', { required: true }), N('factor', 'Factor'), T('descripcion', 'Descripción', { width: 5 })], orden: ['cod'] },
];

export const maestroPorKey = (key: string): Maestro => {
  const m = MAESTROS.find((x) => x.key === key);
  if (!m) throw new NotFound(`El catálogo "${key}" no existe.`);
  return m;
};

function limpiar(m: Maestro, d: Record<string, unknown>, esAlta: boolean) {
  const out: Record<string, unknown> = {};
  const e = new Errores();
  for (const c of m.cols) {
    if (c.readonly) continue;
    if (!(c.name in d)) {
      if (esAlta && c.required) e.add(true, `${c.label} es obligatorio.`);
      continue;
    }
    let v: unknown = d[c.name];
    if (c.type === 'number') {
      if (v === '' || v === null || v === undefined) v = null;
      else if (isNaN(Number(v))) {
        e.add(true, `${c.label} debe ser numérico.`);
        continue;
      } else v = Number(v);
    } else {
      v = v === null || v === undefined ? null : String(v).trim();
      if (v === '') v = null;
      if (v && c.type === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(String(v))) e.add(true, `${c.label}: fecha no válida (AAAA-MM-DD).`);
      if (v && m.mayus?.includes(c.name)) v = String(v).toUpperCase();
      if (v && c.type === 'select' && c.options && !c.options.includes(String(v))) e.add(true, `${c.label}: valor no permitido.`);
    }
    if (c.required && (v === null || v === undefined)) e.add(true, `${c.label} es obligatorio.`);
    out[c.name] = v;
  }
  e.throwIfAny('Datos inválidos:');
  return out;
}

export async function listarMaestro(db: Db, key: string, q?: string) {
  const m = maestroPorKey(key);
  const qb = db(m.tabla).select('*');
  for (const o of m.orden ?? m.pk) qb.orderBy(o);
  if (q) {
    const like = `%${q.toUpperCase()}%`;
    const textCols = m.cols.filter((c) => c.type === 'text' || c.type === 'select').map((c) => c.name);
    qb.where((w) => textCols.forEach((c) => w.orWhereRaw(`upper(cast(${c} as text)) like ?`, [like])));
  }
  return qb.limit(2000);
}

/** Referencias permitidas: solo las declaradas en los metadatos de los catálogos (nunca tablas de seguridad). */
const REFS_PERMITIDAS = new Set(MAESTROS.flatMap((m) => m.cols.filter((c) => c.ref).map((c) => c.ref as string)));

export async function opcionesRef(db: Db, ref: string): Promise<string[]> {
  if (!REFS_PERMITIDAS.has(ref)) throw new NotFound('Lista de valores no disponible.');
  const [t, c] = ref.split('.');
  const rows = await db(t).distinct(c).whereNotNull(c).orderBy(c).limit(5000);
  return rows.map((r: any) => String(r[c]));
}

export async function crearMaestro(db: Db, u: Usuario, key: string, d: Record<string, unknown>) {
  const m = maestroPorKey(key);
  const v = limpiar(m, d, true);
  if (!m.autoId) {
    const w: Record<string, unknown> = {};
    for (const k of m.pk) w[k] = v[k];
    if (await db(m.tabla).where(w).first()) fail('Ya existe un registro con esa clave.');
  }
  await db(m.tabla).insert(v);
  await bitacora(db, u, m.modulo === 'core' ? 'CATÁLOGOS' : m.modulo === 'alm' ? 'ALMACENES' : m.modulo === 'com' ? 'COMBUSTIBLE' : 'ACTIVOS FIJOS', `ALTA ${m.titulo}`.slice(0, 80), m.pk.map((k) => v[k] ?? '').join('/'), JSON.stringify(v).slice(0, 500));
  if (m.tabla === 'com_contratos') await recalcularContratos(db);
  return { ok: true };
}

export async function actualizarMaestro(db: Db, u: Usuario, key: string, id: Record<string, unknown>, d: Record<string, unknown>) {
  const m = maestroPorKey(key);
  const w: Record<string, unknown> = {};
  for (const k of m.pk) w[k] = id[k];
  const ex = await db(m.tabla).where(w).first();
  if (!ex) throw new NotFound('El registro no existe.');
  const v = limpiar(m, { ...ex, ...d }, false);
  for (const k of m.pk) if (!m.autoId && String(v[k]) !== String(ex[k])) fail('No se puede cambiar la clave del registro; elimínelo y créelo nuevamente.');
  for (const k of m.pk) delete v[k];
  await db(m.tabla).where(w).update(v);
  await bitacora(db, u, 'CATÁLOGOS', `MODIFICACIÓN ${m.titulo}`.slice(0, 80), m.pk.map((k) => w[k]).join('/'), JSON.stringify(d).slice(0, 500));
  if (m.tabla === 'com_contratos') await recalcularContratos(db);
}

export async function eliminarMaestro(db: Db, u: Usuario, key: string, id: Record<string, unknown>) {
  const m = maestroPorKey(key);
  const w: Record<string, unknown> = {};
  for (const k of m.pk) w[k] = id[k];
  const ex = await db(m.tabla).where(w).first();
  if (!ex) throw new NotFound('El registro no existe.');
  for (const uso of m.uso ?? []) {
    const col = m.pk.includes(uso.col) ? uso.col : uso.col;
    const val = ex[col] ?? ex[m.pk[0]];
    if (await db(uso.tabla).where(uso.col, val).first()) fail(`No se puede eliminar: está en uso en ${uso.label}. Márquelo como INACTIVO.`);
  }
  await db(m.tabla).where(w).delete();
  await bitacora(db, u, 'CATÁLOGOS', `BAJA ${m.titulo}`.slice(0, 80), m.pk.map((k) => w[k]).join('/'), '');
}
void num;
void txt;
