/**
 * Motor de existencias valoradas por lotes.
 * - Salidas por PEPS con prioridad al vencimiento más próximo (FEFO), nunca de lotes vencidos.
 * - Kardex valorado: cada movimiento referencia su lote y su precio de compra.
 * Todas las funciones reciben una transacción (Db) para ser atómicas.
 */
import type { Db } from '../../core/context.js';
import { EPS, num, round, nowIso, isDate, txt } from '../../core/util.js';
import { fail } from '../../core/errors.js';
import { bitacoraUsuario } from './helpers.js';

export interface LoteRow {
  id_lote: string;
  cod_bod: string;
  cod_item: string;
  doc_origen: string;
  fecha_ing: string;
  vencimiento: string | null;
  cant_inicial: number;
  saldo: number;
  precio_unit: number;
  estado: string;
}

async function nuevoId(db: Db, tabla: string, col: string, letra: string): Promise<string> {
  const r = await db(tabla).max({ m: col }).first();
  const n = r?.m ? Number(String(r.m).slice(1)) : 0;
  return letra + String(n + 1).padStart(6, '0');
}

async function movAdd(
  db: Db,
  usuario: string,
  p: { fecha: string; bod: string; cod: string; tipo: string; doc: string; idLote: string; ce: number; cs: number; pu: number; refer: string },
) {
  await db('alm_movimientos').insert({
    id_mov: await nuevoId(db, 'alm_movimientos', 'id_mov', 'M'),
    fecha: p.fecha,
    cod_bod: p.bod,
    cod_item: p.cod,
    tipo: p.tipo,
    documento: p.doc,
    id_lote: p.idLote,
    cant_ent: p.ce || 0,
    cant_sal: p.cs || 0,
    precio_unit: p.pu,
    imp_ent: p.ce ? round(p.ce * p.pu, 4) : 0,
    imp_sal: p.cs ? round(p.cs * p.pu, 4) : 0,
    referencia: p.refer.slice(0, 300),
    anulado: null,
    usuario: usuario,
    fecha_reg: nowIso(),
  });
}

export const loteVencido = (venc: string | null | undefined, fecha: string): boolean => !!venc && isDate(venc) && venc.slice(0, 10) < fecha;

export async function stockDe(db: Db, bod: string | '', cod: string): Promise<number> {
  const q = db('alm_lotes').where({ cod_item: cod }).whereIn('estado', ['ACTIVO']);
  if (bod) q.andWhere({ cod_bod: bod });
  const r = await q.sum({ s: 'saldo' }).first();
  return num(r?.s);
}

export async function stockDisponibleEntrega(db: Db, bod: string, cod: string, fecha: string): Promise<number> {
  const rows = await db('alm_lotes').where({ cod_bod: bod, cod_item: cod, estado: 'ACTIVO' }).where('saldo', '>', EPS).select('saldo', 'vencimiento');
  return rows.filter((r: any) => !loteVencido(r.vencimiento, fecha)).reduce((t: number, r: any) => t + num(r.saldo), 0);
}

export async function precioPromedio(db: Db, bod: string | '', cod: string): Promise<number> {
  const q = db('alm_lotes').where({ cod_item: cod, estado: 'ACTIVO' });
  if (bod) q.andWhere({ cod_bod: bod });
  const rows = await q.select('saldo', 'precio_unit');
  let qn = 0;
  let v = 0;
  for (const r of rows) {
    qn += num(r.saldo);
    v += num(r.saldo) * num(r.precio_unit);
  }
  if (qn > EPS) return round(v / qn, 4);
  const it = await db('alm_catalogo').where({ codigo: cod }).first('precio_ref');
  return num(it?.precio_ref);
}

/** Último precio de compra (CGI) del ítem; si no hay, el precio referencial. */
export async function ultimoPrecio(db: Db, cod: string): Promise<number> {
  const r = await db('alm_lotes')
    .where({ cod_item: cod })
    .where('doc_origen', 'like', 'CGI-%')
    .orderBy([{ column: 'fecha_ing', order: 'desc' }, { column: 'id_lote', order: 'desc' }])
    .first('precio_unit');
  if (r && num(r.precio_unit) > 0) return num(r.precio_unit);
  const it = await db('alm_catalogo').where({ codigo: cod }).first('precio_ref');
  return num(it?.precio_ref);
}

export async function altaLote(
  db: Db,
  usuario: string,
  p: { bod: string; cod: string; docOrigen: string; fechaIng: string; venc?: string | null; cant: number; pu: number; tipoMov: string; refer: string; nroLote?: string },
): Promise<string> {
  if (!(p.cant > 0)) fail('La cantidad del lote debe ser mayor a cero.');
  const id = await nuevoId(db, 'alm_lotes', 'id_lote', 'L');
  await db('alm_lotes').insert({
    id_lote: id,
    cod_bod: p.bod,
    cod_item: p.cod,
    doc_origen: p.docOrigen,
    fecha_ing: p.fechaIng,
    vencimiento: p.venc && isDate(p.venc) ? p.venc.slice(0, 10) : null,
    cant_inicial: p.cant,
    saldo: p.cant,
    precio_unit: p.pu,
    estado: 'ACTIVO',
    nro_lote: p.nroLote || null,
  });
  await movAdd(db, usuario, { fecha: p.fechaIng, bod: p.bod, cod: p.cod, tipo: p.tipoMov, doc: p.docOrigen, idLote: id, ce: p.cant, cs: 0, pu: p.pu, refer: p.refer });
  return id;
}

async function elegirLotes(db: Db, bod: string, cod: string, cant: number, fecha: string, idLote: string, permitirVencidos: boolean): Promise<LoteRow[]> {
  const q = db('alm_lotes')
    .where({ cod_bod: bod, cod_item: cod, estado: 'ACTIVO' })
    .where('saldo', '>', EPS)
    .orderByRaw('CASE WHEN vencimiento IS NULL THEN 1 ELSE 0 END, vencimiento, fecha_ing, id_lote');
  if (idLote) q.andWhere({ id_lote: idLote });
  let lotes: LoteRow[] = await q;
  if (!permitirVencidos) lotes = lotes.filter((l) => !loteVencido(l.vencimiento, fecha));
  const disp = lotes.reduce((t, l) => t + num(l.saldo), 0);
  if (disp + EPS < cant) {
    const it = await db('alm_catalogo').where({ codigo: cod }).first('descripcion');
    fail(
      `Existencia insuficiente de ${cod} - ${txt(it?.descripcion).slice(0, 40)}: disponible ${disp}${permitirVencidos ? '' : ' (no se cuentan lotes vencidos)'}, requerido ${cant}.`,
    );
  }
  return lotes;
}

/** Descarga `cant` del ítem por PEPS/FEFO. Devuelve el importe total valorado a precio de cada lote. */
export async function consumirPEPS(
  db: Db,
  usuario: string,
  p: { bod: string; cod: string; cant: number; fecha: string; tipoMov: string; doc: string; refer: string; idLote?: string; permitirVencidos?: boolean },
): Promise<number> {
  if (!(p.cant > 0)) fail('La cantidad a consumir debe ser mayor a cero.');
  const lotes = await elegirLotes(db, p.bod, p.cod, p.cant, p.fecha, p.idLote || '', !!p.permitirVencidos);
  let resto = p.cant;
  let impo = 0;
  for (const l of lotes) {
    if (resto <= EPS) break;
    const q = Math.min(num(l.saldo), resto);
    const nuevo = round(num(l.saldo) - q, 6);
    await db('alm_lotes')
      .where({ id_lote: l.id_lote })
      .update({ saldo: nuevo <= EPS ? 0 : nuevo, estado: nuevo <= EPS ? (p.tipoMov === 'BAJA' ? 'BAJA' : 'AGOTADO') : 'ACTIVO' });
    impo += round(q * num(l.precio_unit), 4);
    await movAdd(db, usuario, { fecha: p.fecha, bod: p.bod, cod: p.cod, tipo: p.tipoMov, doc: p.doc, idLote: l.id_lote, ce: 0, cs: q, pu: num(l.precio_unit), refer: p.refer });
    resto -= q;
  }
  return impo;
}

/** Mueve existencias entre bodegas conservando lote, vencimiento y costo (salida + ingreso). */
export async function transferirLotes(
  db: Db,
  usuario: string,
  p: { bodOri: string; bodDes: string; cod: string; cant: number; fecha: string; doc: string; refer: string },
) {
  const lotes = await elegirLotes(db, p.bodOri, p.cod, p.cant, p.fecha, '', false);
  let resto = p.cant;
  for (const l of lotes) {
    if (resto <= EPS) break;
    const q = Math.min(num(l.saldo), resto);
    const nuevo = round(num(l.saldo) - q, 6);
    await db('alm_lotes').where({ id_lote: l.id_lote }).update({ saldo: nuevo <= EPS ? 0 : nuevo, estado: nuevo <= EPS ? 'AGOTADO' : 'ACTIVO' });
    await movAdd(db, usuario, { fecha: p.fecha, bod: p.bodOri, cod: p.cod, tipo: 'TRANSF-SAL', doc: p.doc, idLote: l.id_lote, ce: 0, cs: q, pu: num(l.precio_unit), refer: p.refer });
    const id = await nuevoId(db, 'alm_lotes', 'id_lote', 'L');
    await db('alm_lotes').insert({
      id_lote: id,
      cod_bod: p.bodDes,
      cod_item: p.cod,
      doc_origen: p.doc,
      fecha_ing: l.fecha_ing,
      vencimiento: l.vencimiento,
      cant_inicial: q,
      saldo: q,
      precio_unit: l.precio_unit,
      estado: 'ACTIVO',
    });
    await movAdd(db, usuario, { fecha: p.fecha, bod: p.bodDes, cod: p.cod, tipo: 'TRANSF-ENT', doc: p.doc, idLote: id, ce: q, cs: 0, pu: num(l.precio_unit), refer: p.refer });
    resto -= q;
  }
}

/** Revierte todos los movimientos de un documento (anulación). Un ingreso no se anula si ya tuvo salidas. */
export async function anularMovimientos(db: Db, doc: string) {
  const movs = await db('alm_movimientos').where({ documento: doc }).andWhere((q) => q.whereNull('anulado').orWhere('anulado', '<>', 'SI')).orderBy('id_mov');
  for (const m of movs) {
    const lote = await db('alm_lotes').where({ id_lote: m.id_lote }).first();
    if (!lote) fail(`No se encontró el lote ${m.id_lote} del documento ${doc}.`);
    if (num(m.cant_sal) > 0) {
      await db('alm_lotes').where({ id_lote: m.id_lote }).update({ saldo: round(num(lote.saldo) + num(m.cant_sal), 6), estado: 'ACTIVO' });
    } else if (num(m.cant_ent) > 0) {
      if (Math.abs(num(lote.saldo) - num(lote.cant_inicial)) > EPS || lote.estado === 'BAJA')
        fail(`No se puede anular ${doc}: el lote ${m.id_lote} (${m.cod_item}) ya tiene salidas, bajas o transferencias posteriores.`);
      await db('alm_lotes').where({ id_lote: m.id_lote }).update({ saldo: 0, estado: 'ANULADO' });
    }
    await db('alm_movimientos').where({ id_mov: m.id_mov }).update({ anulado: 'SI' });
  }
}

/** Cierra un lote (cierre de gestión): registra su salida contable y lo deja en cero. */
export async function cerrarLote(db: Db, usuario: string, l: LoteRow, fecha: string, doc: string) {
  await db('alm_lotes').where({ id_lote: l.id_lote }).update({ estado: 'AGOTADO', saldo: 0 });
  await movAdd(db, usuario, { fecha, bod: l.cod_bod, cod: l.cod_item, tipo: 'CIERRE', doc, idLote: l.id_lote, ce: 0, cs: num(l.saldo), pu: num(l.precio_unit), refer: 'Cierre de gestión' });
}

export async function lotesDeItem(db: Db, bod: string, cod: string): Promise<LoteRow[]> {
  return db('alm_lotes').where({ cod_bod: bod, cod_item: cod, estado: 'ACTIVO' }).where('saldo', '>', EPS).orderByRaw('CASE WHEN vencimiento IS NULL THEN 1 ELSE 0 END, vencimiento, fecha_ing');
}

export interface KardexLinea {
  fecha: string;
  documento: string;
  detalle: string;
  entCant: number | null;
  entBs: number | null;
  salCant: number | null;
  salBs: number | null;
  saldoCant: number;
  saldoBs: number;
  puProm: number | null;
}

/** Tarjeta kardex valorada de un ítem (saldo con precio promedio ponderado informativo). */
export async function kardex(db: Db, bod: string | '', cod: string, desde: string, hasta: string): Promise<KardexLinea[]> {
  const q = db('alm_movimientos').where({ cod_item: cod }).andWhere((w) => w.whereNull('anulado').orWhere('anulado', '<>', 'SI')).andWhere('fecha', '<=', hasta);
  if (bod) q.andWhere({ cod_bod: bod });
  const movs = await q.orderBy([{ column: 'fecha' }, { column: 'id_mov' }]);
  let sc = 0;
  let sv = 0;
  const out: KardexLinea[] = [];
  const antes = movs.filter((m: any) => m.fecha < desde);
  for (const m of antes) {
    sc += num(m.cant_ent) - num(m.cant_sal);
    sv += num(m.imp_ent) - num(m.imp_sal);
  }
  out.push({ fecha: desde, documento: '', detalle: 'SALDO ANTERIOR', entCant: null, entBs: null, salCant: null, salBs: null, saldoCant: sc, saldoBs: round(sv, 2), puProm: sc > EPS ? round(sv / sc, 4) : null });
  for (const m of movs.filter((m: any) => m.fecha >= desde)) {
    sc += num(m.cant_ent) - num(m.cant_sal);
    sv += num(m.imp_ent) - num(m.imp_sal);
    out.push({
      fecha: m.fecha,
      documento: m.documento,
      detalle: m.tipo + (txt(m.referencia) ? ' - ' + txt(m.referencia) : ''),
      entCant: num(m.cant_ent) > 0 ? num(m.cant_ent) : null,
      entBs: num(m.cant_ent) > 0 ? num(m.imp_ent) : null,
      salCant: num(m.cant_sal) > 0 ? num(m.cant_sal) : null,
      salBs: num(m.cant_sal) > 0 ? num(m.imp_sal) : null,
      saldoCant: round(sc, 6),
      saldoBs: round(sv, 2),
      puProm: sc > EPS ? round(sv / sc, 4) : null,
    });
  }
  return out;
}

export interface ResumenMov {
  bod: string;
  cod: string;
  saldoIniCant: number;
  saldoIniBs: number;
  entCant: number;
  entBs: number;
  salCant: number;
  salBs: number;
}
export async function resumenMov(db: Db, bod: string | '', desde: string, hasta: string): Promise<Map<string, ResumenMov>> {
  const q = db('alm_movimientos').andWhere((w) => w.whereNull('anulado').orWhere('anulado', '<>', 'SI')).andWhere('fecha', '<=', hasta);
  if (bod) q.andWhere({ cod_bod: bod });
  const movs = await q;
  const d = new Map<string, ResumenMov>();
  for (const m of movs) {
    const k = `${m.cod_bod}|${m.cod_item}`;
    const v = d.get(k) ?? { bod: m.cod_bod, cod: m.cod_item, saldoIniCant: 0, saldoIniBs: 0, entCant: 0, entBs: 0, salCant: 0, salBs: 0 };
    if (m.fecha < desde || m.tipo === 'SALDO INICIAL') {
      v.saldoIniCant += num(m.cant_ent) - num(m.cant_sal);
      v.saldoIniBs += num(m.imp_ent) - num(m.imp_sal);
    } else {
      v.entCant += num(m.cant_ent);
      v.entBs += num(m.imp_ent);
      v.salCant += num(m.cant_sal);
      v.salBs += num(m.imp_sal);
    }
    d.set(k, v);
  }
  return d;
}

export async function saldosActuales(db: Db, bod: string | ''): Promise<Map<string, { cant: number; bs: number }>> {
  const q = db('alm_lotes').where({ estado: 'ACTIVO' }).where('saldo', '>', EPS);
  if (bod) q.andWhere({ cod_bod: bod });
  const d = new Map<string, { cant: number; bs: number }>();
  for (const l of await q) {
    const k = `${l.cod_bod}|${l.cod_item}`;
    const v = d.get(k) ?? { cant: 0, bs: 0 };
    v.cant += num(l.saldo);
    v.bs += num(l.saldo) * num(l.precio_unit);
    d.set(k, v);
  }
  return d;
}

export async function ultimoMovimiento(db: Db): Promise<Map<string, string>> {
  const rows = await db('alm_movimientos')
    .where((w) => w.whereNull('anulado').orWhere('anulado', '<>', 'SI'))
    .where('tipo', '<>', 'SALDO INICIAL')
    .groupBy('cod_bod', 'cod_item')
    .select('cod_bod', 'cod_item')
    .max({ f: 'fecha' });
  return new Map(rows.map((r: any) => [`${r.cod_bod}|${r.cod_item}`, r.f]));
}

export { bitacoraUsuario };
