/**
 * Revalúo técnico de activos fijos totalmente depreciados (valor en libros Bs 1).
 * Base: NC 4 (Revalorización Técnica, Colegio de Auditores de Bolivia), NB-SABS (D.S. 0181), Ley 1178 (SAFCO),
 * D.S. 24051 y NIC 16 (modelo de revaluación). Método comparativo (consulta de mercado) con factor de conservación por estado.
 */
import fs from 'node:fs';
import path from 'node:path';
import type { Db, Usuario } from '../../core/context.js';
import { fail, NotFound } from '../../core/errors.js';
import { isDate, nowIso, num, round, today, txt } from '../../core/util.js';
import { bitacora, siguienteNro } from '../../core/services.js';
import { formatoImagen } from '../../core/logo.js';
import { FOTOS_DIR } from '../../docs/activos.js';

export const REVAL_DIR = () => process.env.SIGAA_REVAL_DIR || path.join(path.dirname(FOTOS_DIR()), 'revaluo');
export const SOPORTE_MAX = 5 * 1024 * 1024;
/** Coeficiente de conservación permitido por estado físico (operativo) y valor sugerido (punto medio redondeado). */
export const FACTORES: Record<string, { min: number; max: number; defecto: number }> = {
  bueno: { min: 0.7, max: 0.85, defecto: 0.78 },
  regular: { min: 0.4, max: 0.6, defecto: 0.5 },
  malo: { min: 0.15, max: 0.35, defecto: 0.25 },
};
export const ESTADOS_ELEGIBLES = Object.keys(FACTORES);
export const VALOR_MINIMO = 1;
const audit = (db: Db, u: Usuario, accion: string, doc: string, detalle: string) => bitacora(db, u, 'ACTIVOS FIJOS', accion, doc, detalle);
const claveEstado = (e: unknown) => txt(e).toLowerCase();

/** Cálculo del Valor Técnico Revaluado: VN base (promedio o mediana de cotizaciones) × factor de conservación; nunca menor a Bs 1. */
export function calcularVtr(valores: number[], metodo: string, factor: number | null | undefined, valorAnterior: number) {
  const v = valores.filter((x) => x > 0).sort((a, b) => a - b);
  let vn = 0;
  if (v.length) {
    if (metodo === 'MEDIANA') vn = v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2;
    else vn = v.reduce((a, b) => a + b, 0) / v.length;
  }
  vn = round(vn, 2);
  const f = factor == null || isNaN(Number(factor)) ? null : Number(factor);
  const vtr = f == null || !vn ? 0 : Math.max(VALOR_MINIMO, round(vn * f, 2));
  return { vn_base: vn, vtr, incremento: vtr ? round(vtr - valorAnterior, 2) : 0 };
}

const valorNeto = (a: any) => (a.valor_libros === null || a.valor_libros === undefined ? num(a.valor) : num(a.valor_libros));

// ───────── Bandeja de selección ─────────
export async function elegibles(db: Db, f: { id_cta?: number; id_aux?: number; texto?: string; incluirEnLote?: boolean } = {}) {
  const q = db('af_activos as a')
    .leftJoin('af_cuentas as c', 'c.id_cta', 'a.id_cta')
    .where('a.situacion', '!=', 'BAJA')
    .whereRaw('ABS(COALESCE(a.valor_libros, a.valor) - 1) < 0.0001')
    .whereRaw('LOWER(a.estado) IN (?, ?, ?)', ESTADOS_ELEGIBLES)
    .whereRaw("COALESCE(a.operativo, 'SI') = 'SI'")
    .select('a.codigo', 'a.descripcion', 'a.auxiliar', 'a.id_cta', 'a.id_aux', 'a.estado', 'a.valor', 'a.valor_libros', 'a.funcionario', 'a.situacion', 'a.fecha_ingreso', 'a.foto1', 'a.operativo', 'c.cuenta')
    .orderBy('a.codigo');
  if (f.id_cta) q.where('a.id_cta', f.id_cta);
  if (f.id_aux) q.where('a.id_aux', f.id_aux);
  if (txt(f.texto)) q.where((b) => b.where('a.codigo', 'like', `%${txt(f.texto)}%`).orWhere('a.descripcion', 'like', `%${txt(f.texto)}%`).orWhere('a.funcionario', 'like', `%${txt(f.texto)}%`));
  const filas: any[] = await q;
  const abiertos = await db('af_reval_items as i').join('af_reval_lotes as l', 'l.id', 'i.lote_id').where('l.estado', 'BORRADOR').select('i.codigo', 'l.nro');
  const mapa = new Map(abiertos.map((x: any) => [x.codigo, x.nro]));
  const out = filas.map((a) => ({ ...a, valor_neto: valorNeto(a), en_lote: mapa.get(a.codigo) || '' }));
  return f.incluirEnLote ? out : out.filter((a) => !a.en_lote);
}

export async function marcarOperativo(db: Db, u: Usuario, codigo: string, operativo: string, motivo: string) {
  const a = await db('af_activos').where({ codigo }).first();
  if (!a) throw new NotFound(`No existe el activo ${codigo}.`);
  if (operativo !== 'SI' && operativo !== 'NO') fail('Indique SI o NO.');
  if (operativo === 'NO' && !txt(motivo)) fail('Indique el motivo (desuso, obsoleto inservible o propuesto para baja).');
  await db('af_activos').where({ codigo }).update({ operativo });
  await audit(db, u, 'OPERATIVO', codigo, `Operativo = ${operativo}${txt(motivo) ? ' · ' + txt(motivo) : ''}`);
  return { ok: true };
}

// ───────── Lotes (hojas de trabajo) ─────────
async function lote(db: Db, id: number) {
  const l = await db('af_reval_lotes').where({ id }).first();
  if (!l) throw new NotFound('El lote de revalúo no existe.');
  return l;
}
async function loteAbierto(db: Db, id: number) {
  const l = await lote(db, id);
  if (l.estado !== 'BORRADOR') fail('El lote ya fue aprobado: no se puede modificar.');
  return l;
}

export async function crearLote(db: Db, u: Usuario, d: { descripcion?: string; codigos: string[]; perito?: string; perito_cargo?: string; comision?: string }) {
  const codigos = [...new Set((d.codigos || []).map(txt).filter(Boolean))];
  if (!codigos.length) fail('Seleccione al menos un activo de la bandeja.');
  const el = new Map((await elegibles(db)).map((a: any) => [a.codigo, a]));
  const malos = codigos.filter((c) => !el.has(c));
  if (malos.length) fail(`No son elegibles (o ya están en otro lote abierto): ${malos.slice(0, 8).join(', ')}${malos.length > 8 ? '…' : ''}.`);
  return db.transaction(async (trx) => {
    const nro = await siguienteNro(trx, 'REV', undefined, 'AF.REV');
    const [id] = await trx('af_reval_lotes').insert({ nro, fecha: today(), descripcion: txt(d.descripcion) || 'Revalúo técnico de activos fijos totalmente depreciados', estado: 'BORRADOR', perito: txt(d.perito), perito_cargo: txt(d.perito_cargo), comision: txt(d.comision), usuario: u.usuario, fecha_reg: nowIso() }, ['id']).then((r: any[]) => r.map((x) => (typeof x === 'object' ? x.id : x)));
    for (const c of codigos) {
      const a: any = el.get(c);
      await trx('af_reval_items').insert({ lote_id: id, codigo: c, valor_anterior: valorNeto(a), estado_fisico: a.estado, operativo: 'SI', metodo: 'PROMEDIO', factor: FACTORES[claveEstado(a.estado)].defecto, vida_anios: 0, vida_meses: 0 });
    }
    await audit(trx, u, 'REVALÚO - LOTE CREADO', nro, `${codigos.length} activos`);
    return { id, nro };
  });
}

export async function actualizarLote(db: Db, u: Usuario, id: number, d: { descripcion?: string; perito?: string; perito_cargo?: string; comision?: string }) {
  await loteAbierto(db, id);
  const upd: Record<string, unknown> = {};
  for (const k of ['descripcion', 'perito', 'perito_cargo', 'comision'] as const) if (d[k] !== undefined) upd[k] = txt(d[k]);
  if (Object.keys(upd).length) await db('af_reval_lotes').where({ id }).update(upd);
  return { ok: true };
}

export async function listarLotes(db: Db) {
  const ls: any[] = await db('af_reval_lotes').orderBy('id', 'desc');
  const its: any[] = await db('af_reval_items').select('lote_id', 'vtr', 'incremento');
  return ls.map((l) => {
    const x = its.filter((i) => i.lote_id === l.id);
    return { ...l, activos: x.length, vtr_total: round(x.reduce((s, i) => s + num(i.vtr), 0), 2), incremento_total: round(x.reduce((s, i) => s + num(i.incremento), 0), 2) };
  });
}

export async function obtenerLote(db: Db, id: number) {
  const l = await lote(db, id);
  const items: any[] = await db('af_reval_items as i').join('af_activos as a', 'a.codigo', 'i.codigo').leftJoin('af_cuentas as c', 'c.id_cta', 'a.id_cta').where('i.lote_id', id).orderBy('i.codigo')
    .select('i.*', 'a.descripcion', 'a.auxiliar', 'a.id_cta', 'a.marca', 'a.modelo', 'a.serie', 'a.funcionario', 'a.situacion', 'a.fecha_ingreso', 'a.foto1', 'a.foto2', 'a.foto3', 'a.foto4', 'c.cuenta', 'a.estado as estado_actual');
  const cots: any[] = items.length ? await db('af_reval_cotizaciones').whereIn('item_id', items.map((i) => i.id)).orderBy('id') : [];
  const lista = items.map((i) => {
    const cs = cots.filter((c) => c.item_id === i.id);
    const completo = problemasItem(i, cs).length === 0;
    return { ...i, valor_anterior: num(i.valor_anterior), vn_base: num(i.vn_base), vtr: num(i.vtr), incremento: num(i.incremento), factor: i.factor == null ? null : num(i.factor), cotizaciones: cs.map((c) => ({ ...c, valor: num(c.valor) })), rango: FACTORES[claveEstado(i.estado_fisico)] || null, completo };
  });
  const porCuenta = new Map<string, { cuenta: string; activos: number; incremento: number }>();
  for (const i of lista) {
    const k = i.cuenta || 'Sin cuenta';
    const x = porCuenta.get(k) || { cuenta: k, activos: 0, incremento: 0 };
    x.activos++; x.incremento = round(x.incremento + i.incremento, 2); porCuenta.set(k, x);
  }
  return {
    ...l, items: lista,
    totales: { activos: lista.length, valor_anterior: round(lista.reduce((s, i) => s + i.valor_anterior, 0), 2), vtr: round(lista.reduce((s, i) => s + i.vtr, 0), 2), incremento: round(lista.reduce((s, i) => s + i.incremento, 0), 2), completos: lista.filter((i) => i.completo).length },
    por_cuenta: [...porCuenta.values()], reserva: 'Reserva por Revalúos Técnicos',
  };
}

function problemasItem(i: any, cots: any[]): string[] {
  const p: string[] = [];
  const r = FACTORES[claveEstado(i.estado_fisico)];
  if (!cots.length) p.push('falta al menos 1 cotización');
  const f = i.factor == null ? null : num(i.factor);
  if (!r) p.push(`el estado "${i.estado_fisico}" no es elegible`);
  else if (f == null || f < r.min - 1e-9 || f > r.max + 1e-9) p.push(`el factor debe estar entre ${r.min} y ${r.max}`);
  if (num(i.vida_anios) * 12 + num(i.vida_meses) <= 0) p.push('falta la nueva vida útil residual');
  if (txt(i.justificacion).length < 10) p.push('falta la justificación técnica del perito');
  if (!(num(i.vtr) >= VALOR_MINIMO)) p.push('el valor técnico no está calculado');
  return p;
}

async function recalcular(db: Db, itemId: number) {
  const i = await db('af_reval_items').where({ id: itemId }).first();
  const cs: any[] = await db('af_reval_cotizaciones').where({ item_id: itemId });
  const r = calcularVtr(cs.map((c) => num(c.valor)), i.metodo, i.factor, num(i.valor_anterior));
  await db('af_reval_items').where({ id: itemId }).update(r);
  return r;
}

async function itemAbierto(db: Db, itemId: number) {
  const i = await db('af_reval_items').where({ id: itemId }).first();
  if (!i) throw new NotFound('La hoja de tasación no existe.');
  await loteAbierto(db, i.lote_id);
  return i;
}

export async function guardarItem(db: Db, u: Usuario, itemId: number, d: { metodo?: string; factor?: number; vida_anios?: number; vida_meses?: number; justificacion?: string }) {
  const i = await itemAbierto(db, itemId);
  const upd: Record<string, unknown> = {};
  if (d.metodo !== undefined) { if (!['PROMEDIO', 'MEDIANA'].includes(d.metodo)) fail('El método debe ser PROMEDIO o MEDIANA.'); upd.metodo = d.metodo; }
  if (d.factor !== undefined) {
    const r = FACTORES[claveEstado(i.estado_fisico)];
    const f = Number(d.factor);
    if (isNaN(f) || f < r.min - 1e-9 || f > r.max + 1e-9) fail(`Para estado ${i.estado_fisico} el factor de conservación debe estar entre ${r.min.toFixed(2)} y ${r.max.toFixed(2)}.`);
    upd.factor = f;
  }
  if (d.vida_anios !== undefined) { const a = Number(d.vida_anios); if (!Number.isInteger(a) || a < 0 || a > 60) fail('Los años de vida útil van de 0 a 60 (números enteros).'); upd.vida_anios = a; }
  if (d.vida_meses !== undefined) { const m = Number(d.vida_meses); if (!Number.isInteger(m) || m < 0 || m > 11) fail('Los meses de vida útil van de 0 a 11.'); upd.vida_meses = m; }
  if (d.justificacion !== undefined) upd.justificacion = txt(d.justificacion);
  if (Object.keys(upd).length) await db('af_reval_items').where({ id: itemId }).update(upd);
  await recalcular(db, itemId);
  await audit(db, u, 'REVALÚO - HOJA DE TASACIÓN', i.codigo, 'Hoja de tasación actualizada');
  return { ok: true };
}

export async function quitarItem(db: Db, u: Usuario, itemId: number) {
  const i = await itemAbierto(db, itemId);
  const cs = await db('af_reval_cotizaciones').where({ item_id: itemId });
  await db('af_reval_cotizaciones').where({ item_id: itemId }).delete();
  await db('af_reval_items').where({ id: itemId }).delete();
  for (const c of cs) if (c.soporte) fs.rmSync(path.join(REVAL_DIR(), path.basename(c.soporte)), { force: true });
  await audit(db, u, 'REVALÚO - ACTIVO RETIRADO', i.codigo, '');
  return { ok: true };
}

export async function eliminarLote(db: Db, u: Usuario, id: number) {
  const l = await loteAbierto(db, id);
  for (const i of await db('af_reval_items').where({ lote_id: id })) await quitarItem(db, u, i.id);
  await db('af_reval_lotes').where({ id }).delete();
  await audit(db, u, 'REVALÚO - LOTE ELIMINADO', l.nro, '');
  return { ok: true };
}

// ───────── Cotizaciones ─────────
function validarCot(d: any) {
  if (!txt(d.proveedor)) fail('Indique el proveedor o fuente de la cotización.');
  if (!isDate(d.fecha)) fail('Indique la fecha de la cotización.');
  if (!(num(d.valor) > 0)) fail('Indique el valor a nuevo (VN) mayor a cero.');
  if (!txt(d.nit) && !txt(d.referencia) && !txt(d.nro_proforma)) fail('Cada cotización necesita un respaldo: NIT, número de proforma o enlace (link).');
}
const camposCot = (d: any) => ({ proveedor: txt(d.proveedor), nit: txt(d.nit), fecha: String(d.fecha).slice(0, 10), nro_proforma: txt(d.nro_proforma), referencia: txt(d.referencia), valor: round(num(d.valor), 2) });

export async function agregarCotizacion(db: Db, u: Usuario, itemId: number, d: any) {
  const i = await itemAbierto(db, itemId);
  validarCot(d);
  if ((await db('af_reval_cotizaciones').where({ item_id: itemId }).count({ n: '*' }).first() as any).n >= 3) fail('Máximo 3 cotizaciones por activo.');
  const [r] = await db('af_reval_cotizaciones').insert({ item_id: itemId, ...camposCot(d) }, ['id']);
  await recalcular(db, itemId);
  await audit(db, u, 'REVALÚO - COTIZACIÓN', i.codigo, `${txt(d.proveedor)} Bs ${num(d.valor)}`);
  return { id: typeof r === 'object' ? (r as any).id : r };
}

export async function editarCotizacion(db: Db, u: Usuario, id: number, d: any) {
  const c = await db('af_reval_cotizaciones').where({ id }).first();
  if (!c) throw new NotFound('La cotización no existe.');
  await itemAbierto(db, c.item_id);
  validarCot(d);
  await db('af_reval_cotizaciones').where({ id }).update(camposCot(d));
  await recalcular(db, c.item_id);
  return { ok: true };
}

export async function quitarCotizacion(db: Db, u: Usuario, id: number) {
  const c = await db('af_reval_cotizaciones').where({ id }).first();
  if (!c) throw new NotFound('La cotización no existe.');
  await itemAbierto(db, c.item_id);
  if (c.soporte) fs.rmSync(path.join(REVAL_DIR(), path.basename(c.soporte)), { force: true });
  await db('af_reval_cotizaciones').where({ id }).delete();
  await recalcular(db, c.item_id);
  return { ok: true };
}

export async function guardarSoporte(db: Db, u: Usuario, id: number, buf: unknown) {
  const c = await db('af_reval_cotizaciones').where({ id }).first();
  if (!c) throw new NotFound('La cotización no existe.');
  await itemAbierto(db, c.item_id);
  if (!Buffer.isBuffer(buf) || !buf.length) fail('Seleccione el archivo de la proforma (PDF, JPG o PNG).');
  if (buf.length > SOPORTE_MAX) fail('El archivo supera 5 MB.');
  const ext = buf.toString('latin1', 0, 5) === '%PDF-' ? 'pdf' : formatoImagen(buf);
  if (!ext || ext === 'webp') fail('El soporte debe ser un PDF, JPG o PNG válido.');
  fs.mkdirSync(REVAL_DIR(), { recursive: true });
  if (c.soporte) fs.rmSync(path.join(REVAL_DIR(), path.basename(c.soporte)), { force: true });
  const nombre = `cot-${id}-${Date.now()}.${ext}`;
  fs.writeFileSync(path.join(REVAL_DIR(), nombre), buf);
  await db('af_reval_cotizaciones').where({ id }).update({ soporte: nombre });
  return { soporte: nombre };
}

// ───────── Aprobación ─────────
export async function aprobarLote(db: Db, u: Usuario, id: number, d: { resolucion?: string }) {
  const l = await loteAbierto(db, id);
  const o = await obtenerLote(db, id);
  if (!o.items.length) fail('El lote no tiene activos.');
  if (!txt(l.perito)) fail('Registre el nombre del perito / responsable de la tasación.');
  const errs: string[] = [];
  for (const i of o.items) for (const p of problemasItem(i, i.cotizaciones)) errs.push(`${i.codigo}: ${p}.`);
  if (errs.length) fail('No se puede aprobar:\n- ' + errs.slice(0, 15).join('\n- ') + (errs.length > 15 ? `\n- …y ${errs.length - 15} observaciones más.` : ''));
  const fecha = today();
  await db.transaction(async (trx) => {
    for (const i of o.items) {
      const a = await trx('af_activos').where({ codigo: i.codigo }).first();
      if (!a || a.situacion === 'BAJA') fail(`${i.codigo}: el activo fue dado de baja.`);
      if (Math.abs(valorNeto(a) - num(i.valor_anterior)) > 0.0001) fail(`${i.codigo}: su valor en libros cambió desde que se armó el lote (${valorNeto(a)}). Retírelo del lote.`);
      const meses = num(i.vida_anios) * 12 + num(i.vida_meses);
      await trx('af_activos').where({ codigo: i.codigo }).update({ valor: i.vtr, valor_libros: i.vtr, vida_residual: meses, revaluado: fecha });
      await trx('af_movimientos').insert({ fecha, codigo: i.codigo, tipo: 'REVALÚO', documento: l.nro, origen: `Bs ${i.valor_anterior.toFixed(2)}`, destino: `Bs ${i.vtr.toFixed(2)}`, detalle: `Revalúo técnico (${i.metodo.toLowerCase()} de ${i.cotizaciones.length} cotización/es × factor ${i.factor}); vida útil residual ${i.vida_anios} año(s) ${i.vida_meses} mes(es). Incremento Bs ${i.incremento.toFixed(2)} a Reserva por Revalúos Técnicos`, usuario: u.usuario, fecha_reg: nowIso(), resolucion: txt(d.resolucion) || null });
    }
    await trx('af_reval_lotes').where({ id }).update({ estado: 'APROBADO', fecha_aprob: fecha, resolucion: txt(d.resolucion) });
    await audit(trx, u, 'REVALÚO - APROBADO', l.nro, `${o.items.length} activos; incremento Bs ${o.totales.incremento.toFixed(2)} a Reserva por Revalúos Técnicos`);
  });
  return { ok: true, nro: l.nro, incremento: o.totales.incremento };
}
