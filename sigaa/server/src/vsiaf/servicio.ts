/**
 * Servicio del submódulo «Envío de activos a VSIAF»: orquesta el adaptador de SIGAA, el motor de importación y el registro de lo
 * enviado. Todo lo que escribe en el VSIAF pasa por el motor (respaldo, escritura atómica, verificación y reversión).
 */
import type { Db, Usuario } from '../core/context.js';
import { BusinessError, fail } from '../core/errors.js';
import { bitacora, cfg, setCfg } from '../core/services.js';
import { nowIso } from '../core/util.js';
import { amigable, armarLote, cargarEquivalencias, ETIQUETA_COLUMNA, ExistenteVsiaf, InfoFila, ParamsLote, SalidaAdaptador, TIPOS_EQUIV, TipoEquiv } from './adaptador.js';
import { redondeo2 } from './calc.js';
import { hoy as hoyIso } from './fecha.js';
import { avisos, errores, ImportacionAbortada, Importador, Opciones, Resultado } from './importador.js';
import { BdVsiaf, detectarInstalacion, incorporacionEspecialHabilitada, InstalacionError, norm, vsiafAbierto } from './instalacion.js';
import { cargarUfv } from './ufv.js';

const audit = (db: Db, u: Usuario, accion: string, doc: string, detalle: string) => bitacora(db, u, 'ACTIVOS FIJOS', accion, doc, detalle);

// ───────────── configuración ─────────────
export async function leerConfigVsiaf(db: Db) {
  return { ruta: await cfg(db, 'VSIAF_RUTA', ''), unidad: await cfg(db, 'VSIAF_UNIDAD', ''), usuario: (await cfg(db, 'VSIAF_USUARIO', 'admin')) || 'admin' };
}
export async function guardarConfigVsiaf(db: Db, u: Usuario, d: { ruta?: string; unidad?: string; usuario?: string }) {
  if (d.unidad !== undefined && [...d.unidad.trim()].length > 5) fail('El código de unidad del VSIAF admite como máximo 5 caracteres.');
  if (d.usuario !== undefined && [...d.usuario.trim()].length > 8) fail('El usuario del VSIAF admite como máximo 8 caracteres.');
  if (d.ruta !== undefined) await setCfg(db, 'VSIAF_RUTA', d.ruta.trim(), 'af', 'Carpeta de instalación del VSIAF (la que contiene vsiaf.exe y dbfs)');
  if (d.unidad !== undefined) await setCfg(db, 'VSIAF_UNIDAD', d.unidad.trim(), 'af', 'Unidad administrativa del VSIAF por defecto');
  if (d.usuario !== undefined) await setCfg(db, 'VSIAF_USUARIO', d.usuario.trim(), 'af', 'Usuario que queda en los registros del VSIAF (máx. 8)');
  await audit(db, u, 'CONFIGURACIÓN VSIAF', '', `Ruta ${d.ruta ?? ''} · unidad ${d.unidad ?? ''}`);
  return leerConfigVsiaf(db);
}

// ───────────── destino (la instalación del VSIAF) ─────────────
function abrir(ruta: string): { bd: BdVsiaf; ufv: ReturnType<typeof cargarUfv> } {
  if (!ruta) fail('Indique la carpeta de instalación del VSIAF (por ejemplo C:\\vsiaf).');
  try {
    const bd = new BdVsiaf(ruta);
    return { bd, ufv: cargarUfv(bd.carpeta, bd.dbfs) };
  } catch (e) {
    if (e instanceof InstalacionError) throw new BusinessError(e.message);
    throw e;
  }
}

export async function infoDestino(db: Db, ruta?: string) {
  const conf = await leerConfigVsiaf(db);
  const r = (ruta ?? conf.ruta) || detectarInstalacion() || '';
  if (!r) return { ruta: '', encontrada: false, mensaje: 'No se encontró el VSIAF en este equipo. Indique la carpeta de instalación.' };
  try {
    const { bd, ufv } = abrir(r);
    const hoy = hoyIso();
    const dias = ufv.diasDesdeUltimoCambio(hoy);
    const avisosD: string[] = [];
    if (dias !== null && dias > 75) avisosD.push(`Las UFV parecen desactualizadas: el último cambio de índice es del ${ufv.ultimoCambio}. Ejecute el actualizador de UFV del Ministerio (cada día 10).`);
    if (ufv.origen.toLowerCase().endsWith('.csv')) avisosD.push('No se encontró tipocambio.app: se usarían las UFV incluidas en SIGAA (aproximadas desde 2021). La vista previa de cálculo puede diferir de la del VSIAF.');
    const cerrada = bd.gestionCerrada();
    if (cerrada) avisosD.push('La gestión de esta base está CERRADA: el VSIAF no permite modificarla.');
    const abierto = vsiafAbierto();
    if (abierto) avisosD.push('El VSIAF está abierto: ciérrelo en todas las PC antes de importar.');
    return {
      ruta: bd.carpeta, encontrada: true, entidad: bd.entidad, entidadNombre: bd.entidadNombre, unidades: bd.unidades(), usuario: bd.usuarioPorDefecto,
      ufv: { origen: ufv.origen, primera: ufv.primera, ultima: ufv.ultima, ultimoCambio: ufv.ultimoCambio }, gestionCerrada: cerrada, vsiafAbierto: abierto,
      incorporacionEspecial: incorporacionEspecialHabilitada(), avisos: avisosD,
    };
  } catch (e) {
    return { ruta: r, encontrada: false, mensaje: (e as Error).message };
  }
}

/** Lo que ya existe en el VSIAF: evita proponer oficinas, responsables y auxiliares repetidos. */
function existentesDe(bd: BdVsiaf): ExistenteVsiaf {
  const ent = bd.entidad;
  const of = new Set<string>(), rs = new Set<string>(), ax = new Set<string>();
  const oficinaPorCodigo = new Map<string, string>();
  for (const r of bd.tabla('OFICINA').registros()) {
    const v = r.valores;
    if (String(v.ENTIDAD ?? '').trim() !== ent) continue;
    of.add(`${String(v.UNIDAD).trim()}|${norm(v.NOMOFIC)}`);
    oficinaPorCodigo.set(`${String(v.UNIDAD).trim()}|${v.CODOFIC}`, norm(v.NOMOFIC));
  }
  for (const r of bd.tabla('RESP').registros()) {
    const v = r.valores;
    if (String(v.ENTIDAD ?? '').trim() !== ent) continue;
    rs.add(`${String(v.UNIDAD).trim()}|${oficinaPorCodigo.get(`${String(v.UNIDAD).trim()}|${v.CODOFIC}`) ?? ''}|${norm(v.NOMRESP)}`);
  }
  for (const r of bd.tabla('AUXILIAR').registros()) {
    const v = r.valores;
    if (String(v.ENTIDAD ?? '').trim() === ent) ax.add(`${String(v.UNIDAD).trim()}|${v.CODCONT}|${norm(v.NOMAUX)}`);
  }
  return {
    oficina: (u, n) => of.has(`${u}|${norm(n)}`), responsable: (u, o, n) => rs.has(`${u}|${norm(o)}|${norm(n)}`), auxiliar: (u, g, n) => ax.has(`${u}|${g}|${norm(n)}`),
  };
}

// ───────────── equivalencias ─────────────
const REGLAS_EQUIV: Record<TipoEquiv, (v: string) => string | null> = {
  grupo: (v) => (/^\d+$/.test(v) && +v >= 1 && +v <= 40 ? null : 'El grupo contable del VSIAF es un número del 1 al 40.'),
  estado: (v) => (['Bueno', 'Regular', 'Malo'].includes(v) ? null : 'El estado del VSIAF es Bueno, Regular o Malo.'),
  org_fin: (v) => (/^\d{3}$/.test(v) ? null : 'El organismo financiador es un código de 3 dígitos (000 = no corresponde).'),
  unidad: (v) => ([...v].length <= 5 ? null : 'El código de unidad admite 5 caracteres como máximo.'),
  motivo_baja: (v) => (/^[1-9]$/.test(v) ? null : 'El motivo de baja del VSIAF va del 1 al 9.'),
  oficina: (v) => ([...v].length <= 65 ? null : 'El nombre de la oficina admite 65 caracteres como máximo.'),
  resp_nombre: (v) => ([...v].length <= 35 ? null : 'El nombre del responsable admite 35 caracteres como máximo.'),
  resp_cargo: (v) => ([...v].length <= 35 ? null : 'El cargo admite 35 caracteres como máximo.'),
  auxiliar: (v) => ([...v].length <= 50 ? null : 'El nombre del auxiliar admite 50 caracteres como máximo.'),
};

export async function listarEquivalencias(db: Db) {
  return db('af_vsiaf_equiv').orderBy(['tipo', 'clave']);
}
/** Crea, modifica o (con valor vacío) elimina equivalencias. */
export async function guardarEquivalencias(db: Db, u: Usuario, items: { tipo: string; clave: string; valor: string }[]) {
  if (!Array.isArray(items) || !items.length) fail('No hay equivalencias para guardar.');
  for (const it of items) {
    if (!(TIPOS_EQUIV as readonly string[]).includes(it.tipo)) fail(`Tipo de equivalencia desconocido: ${it.tipo}.`);
    if (!String(it.clave ?? '').trim()) fail('Cada equivalencia necesita el valor de SIGAA (clave).');
    const v = String(it.valor ?? '').trim();
    if (v) { const m = REGLAS_EQUIV[it.tipo as TipoEquiv](v); if (m) fail(`${it.clave}: ${m}`); }
  }
  await db.transaction(async (trx) => {
    for (const it of items) {
      const clave = String(it.clave).trim();
      const v = String(it.valor ?? '').trim();
      const ex = await trx('af_vsiaf_equiv').where({ tipo: it.tipo, clave }).first();
      if (!v) { if (ex) await trx('af_vsiaf_equiv').where({ id: ex.id }).delete(); }
      else if (ex) await trx('af_vsiaf_equiv').where({ id: ex.id }).update({ valor: v });
      else await trx('af_vsiaf_equiv').insert({ tipo: it.tipo, clave, valor: v });
    }
    await audit(trx, u, 'EQUIVALENCIAS VSIAF', '', `${items.length} equivalencia(s)`);
  });
  return listarEquivalencias(db);
}

// ───────────── selección ─────────────
export async function seleccionVsiaf(db: Db, f: { desde?: string; hasta?: string; id_cta?: number; cod_edif?: number; texto?: string; situacion?: string; estado?: 'PENDIENTES' | 'ENVIADOS' | 'TODOS'; limite?: number }) {
  const q = db('af_activos as a')
    .leftJoin('af_cuentas as c', 'c.id_cta', 'a.id_cta')
    .leftJoin('af_vsiaf_envios as e', (j) => j.on('e.codigo', 'a.codigo').andOn('e.tipo', db.raw('?', ['ACTIVO'])))
    .select('a.codigo', 'a.descripcion', 'a.auxiliar', 'a.valor', 'a.fecha_ingreso', 'a.situacion', 'a.funcionario', 'a.id_cta', 'a.cod_edif', 'a.nro_ingreso', 'c.cuenta', 'c.cod_vsiaf', 'e.lote as lote_envio', 'e.fecha as fecha_envio')
    .orderBy('a.codigo')
    .limit(f.limite ?? 2000);
  if (f.desde) q.where('a.fecha_ingreso', '>=', f.desde);
  if (f.hasta) q.where('a.fecha_ingreso', '<=', f.hasta);
  if (f.id_cta) q.where('a.id_cta', f.id_cta);
  if (f.cod_edif) q.where('a.cod_edif', f.cod_edif);
  if (f.situacion) q.where('a.situacion', f.situacion);
  if (f.texto) q.where((b) => b.where('a.codigo', 'like', `%${f.texto}%`).orWhere('a.descripcion', 'like', `%${f.texto}%`));
  if ((f.estado ?? 'PENDIENTES') === 'PENDIENTES') q.whereNull('e.id');
  else if (f.estado === 'ENVIADOS') q.whereNotNull('e.id');
  return q;
}

// ───────────── validar / importar ─────────────
export interface ParamsEnvio extends ParamsLote {
  ruta?: string;
  usuarioVsiaf?: string;
  soloValidas?: boolean;
  /** Fecha de la vista previa de cálculo (hoy por defecto). */
  fechaCalculo?: string;
  respaldar?: boolean;
  confirmar?: boolean;
  /** Solo pruebas. */
  hoy?: string;
  omitirProceso?: boolean;
  permitirIncorporacionEspecial?: boolean | null;
}

export interface IncidenciaVsiaf { tipo: string; codigo: string; columna: string; etiqueta: string; nivel: string; mensaje: string }

export interface ValidacionLote {
  sinErrores: boolean;
  errores: number;
  avisos: number;
  resumen: SalidaAdaptador['resumen'];
  conteos: Record<string, number>;
  incidencias: IncidenciaVsiaf[];
  faltantes: SalidaAdaptador['faltantes'];
  omitidos: SalidaAdaptador['omitidos'];
  calculos: Resultado['calculos'];
  totalesPorGrupo: Record<string, unknown>[];
  /** Aviso fijo del módulo: el VSIAF no verá los datos hasta Re-indexar. */
  pasoFinal: string;
}
const PASO_FINAL = 'Después de importar: abra el VSIAF → Administradores → Re-indexar, verifique con el Reporte 6 y apruebe los activos ELABORADOS.';

function totalesPorGrupo(calculos: Resultado['calculos']): Record<string, unknown>[] {
  const g = new Map<number, Record<string, any>>();
  for (const r of calculos.ACTIVOS ?? []) {
    const x = g.get(Number(r.codcont)) ?? { codcont: r.codcont, grupo: r.grupo, cantidad: 0, costo_historico: 0, actualizacion_gestion: 0, costo_total_actualizado: 0, dep_gestion: 0, actualizacion_dep_acumulada: 0, dep_acumulada: 0, valor_neto: 0 };
    x.cantidad++;
    for (const c of ['costo_historico', 'actualizacion_gestion', 'costo_total_actualizado', 'dep_gestion', 'actualizacion_dep_acumulada', 'dep_acumulada', 'valor_neto']) x[c] += Number(r[c] ?? 0);
    g.set(Number(r.codcont), x);
  }
  return [...g.values()].sort((a, b) => a.codcont - b.codcont).map((x) => Object.fromEntries(Object.entries(x).map(([k, v]) => [k, typeof v === 'number' && k !== 'codcont' && k !== 'cantidad' ? redondeo2(v) : v])));
}

function incidenciasAmigables(res: Resultado, info: Map<string, InfoFila>): IncidenciaVsiaf[] {
  return res.incidencias.map((i) => {
    const ref = String(i.ref);
    const inf = info.get(ref);
    return { tipo: inf?.tipo ?? i.hoja, codigo: inf?.codigo ?? '', columna: i.columna, etiqueta: ETIQUETA_COLUMNA[i.columna] ?? i.columna, nivel: i.nivel, mensaje: amigable(i.mensaje) };
  });
}

async function preparar(db: Db, p: ParamsEnvio) {
  const conf = await leerConfigVsiaf(db);
  const ruta = p.ruta ?? conf.ruta ?? '';
  const { bd, ufv } = abrir(ruta || detectarInstalacion() || '');
  const salida = await armarLote(db, { ...p, unidad: p.unidad || conf.unidad }, existentesDe(bd));
  const opciones: Opciones = {
    unidadPorDefecto: p.unidad || conf.unidad || undefined, usuario: (p.usuarioVsiaf || conf.usuario || bd.usuarioPorDefecto).slice(0, 8), estadoPorDefecto: p.estadoRegistro ?? 'ELABORADO',
    soloValidas: !!p.soloValidas, respaldar: p.respaldar !== false, hoy: p.hoy, fechaCalculo: p.fechaCalculo ?? p.hoy, omitirProceso: p.omitirProceso, permitirIncorporacionEspecial: p.permitirIncorporacionEspecial,
  };
  const motor = new Importador(bd, ufv, opciones);
  const res = motor.plan(salida.libro);
  return { bd, ruta: bd.carpeta, salida, motor, res, opciones };
}

function validacionDe(salida: SalidaAdaptador, res: Resultado): ValidacionLote {
  return {
    sinErrores: errores(res) === 0, errores: errores(res), avisos: avisos(res), resumen: salida.resumen, conteos: res.conteos, incidencias: incidenciasAmigables(res, salida.info),
    faltantes: salida.faltantes, omitidos: salida.omitidos, calculos: res.calculos, totalesPorGrupo: totalesPorGrupo(res.calculos), pasoFinal: PASO_FINAL,
  };
}

/** Valida el envío **sin escribir nada** en el VSIAF. */
export async function validarLote(db: Db, _u: Usuario, p: ParamsEnvio): Promise<ValidacionLote> {
  const { salida, res } = await preparar(db, p);
  return validacionDe(salida, res);
}

/** Importa al VSIAF (con respaldo, verificación y reversión) y registra lo enviado. */
export async function importarLote(db: Db, u: Usuario, p: ParamsEnvio) {
  if (!p.confirmar) fail('Confirme la importación: se escribirá en la base de datos del VSIAF.');
  const { bd, ruta, salida, motor, res, opciones } = await preparar(db, p);
  const validacion = validacionDe(salida, res);
  const planificadas = motor.planificadas();
  if (!planificadas.length) fail('No hay nada que enviar al VSIAF: no hay activos pendientes ni movimientos nuevos.');
  if (errores(res) && !p.soloValidas) throw new BusinessError(`No se puede importar: hay ${errores(res)} error(es). Corríjalos y valide de nuevo (o elija «importar solo las filas válidas»).`);
  try {
    motor.aplicar(`Importación desde SIGAA (${u.usuario})`);
  } catch (e) {
    const msg = e instanceof ImportacionAbortada ? e.message : `${(e as Error).message}. La base del VSIAF quedó como estaba.`;
    await insertarLote(db, { fecha: nowIso(), usuario: u.usuario, destino: ruta, unidad: opciones.unidadPorDefecto ?? null, estado_registro: opciones.estadoPorDefecto, resultado: 'ERROR', mensaje: msg, respaldo: res.rutaRespaldo ?? null, resumen: JSON.stringify({ resumen: salida.resumen, conteos: res.conteos, errores: errores(res), avisos: avisos(res) }) });
    throw new BusinessError(`No se pudo importar: ${msg}`);
  }
  // Se registra lo enviado: cada fila de origen queda marcada para no reenviarla.
  const id = await db.transaction(async (trx) => {
    const idLote = await insertarLote(trx, {
      fecha: nowIso(), usuario: u.usuario, destino: ruta, unidad: opciones.unidadPorDefecto ?? null, estado_registro: opciones.estadoPorDefecto, resultado: 'IMPORTADO', respaldo: res.rutaRespaldo ?? null, mensaje: PASO_FINAL,
      resumen: JSON.stringify({ resumen: salida.resumen, conteos: res.conteos, errores: errores(res), avisos: avisos(res), totalesPorGrupo: validacion.totalesPorGrupo }),
    });
    for (const o of planificadas) {
      const inf = salida.info.get(String(o.ref));
      if (!inf || !['ACTIVO', 'TRANSFERENCIA', 'BAJA'].includes(inf.tipo)) continue;
      await trx('af_vsiaf_envios').insert({ lote: idLote, tipo: inf.tipo, codigo: inf.codigo, unidad: inf.unidad, codigo_vsiaf: inf.codigoVsiaf ?? null, oficina: inf.oficina ?? null, responsable: inf.responsable ?? null, fecha: nowIso(), usuario: u.usuario });
    }
    await audit(trx, u, 'ENVÍO AL VSIAF', `LOTE-${idLote}`, `${res.conteos.ACTIVOS ?? 0} alta(s), ${res.conteos.TRANSFERENCIAS ?? 0} transferencia(s), ${res.conteos.BAJAS ?? 0} baja(s) en ${ruta}`);
    return idLote;
  });
  void bd;
  return { lote: id, respaldo: res.rutaRespaldo, conteos: res.conteos, validacion, pasoFinal: PASO_FINAL };
}

async function insertarLote(db: Db, d: Record<string, unknown>): Promise<number> {
  const r: any = await db('af_vsiaf_lotes').insert(d).returning('id');
  const x = Array.isArray(r) ? r[0] : r;
  return Number(x && typeof x === 'object' ? x.id : x);
}

export async function listarLotes(db: Db) {
  return db('af_vsiaf_lotes').orderBy('id', 'desc').limit(200);
}
export async function enviosDeActivo(db: Db, codigo: string) {
  return db('af_vsiaf_envios').where({ codigo }).orderBy('id');
}
export { cargarEquivalencias };
