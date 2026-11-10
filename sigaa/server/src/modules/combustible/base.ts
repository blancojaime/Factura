/** Funciones base de Combustible: precios, rendimientos, lecturas, kardex de vales y turriles. */
import type { Db, Usuario } from '../../core/context.js';
import { fail } from '../../core/errors.js';
import { diasHabilesLS, isDate, nowIso, num, round, txt, addDays, today } from '../../core/util.js';
import { cfg, cfgNum, bitacora } from '../../core/services.js';

export const ALM_VALES = 'VALES';

export const audit = (db: Db, u: Usuario, accion: string, doc: string, detalle: string) => bitacora(db, u, 'COMBUSTIBLE', accion, doc, detalle);

/** Precio del combustible vigente a una fecha (último precio con vigencia ≤ fecha). */
export async function precioVigente(db: Db, combustible: string, fecha: string = today()): Promise<number> {
  const r = await db('com_precios').whereRaw('lower(combustible) = ?', [combustible.toLowerCase()]).where('vigente_desde', '<=', fecha).orderBy('vigente_desde', 'desc').first('precio');
  return num(r?.precio);
}

export async function rendimientoVehiculo(db: Db, v: { rendimiento?: number; tipo?: string }): Promise<number> {
  const r = num(v.rendimiento);
  if (r > 0) return r;
  const t = await db('com_tipos').where({ tipo: v.tipo ?? '' }).first('rendimiento_ref');
  return num(t?.rendimiento_ref);
}

/**
 * Litros máximos permitidos para una emisión.
 * Uso ejecutivo: días hábiles (lun-sáb) × LITROS_DIA_EJECUTIVO (DS 27327 art. 19).
 * Uso operativo: km u horas programados × rendimiento de referencia. Devuelve null si no se puede calcular.
 */
export async function litrosMaximos(db: Db, p: { placa: string; destino: string; desde?: string; hasta?: string; programado?: number }): Promise<number | null> {
  if (p.destino.toUpperCase() !== 'VEHICULO' || !txt(p.placa)) return null;
  const v = await db('com_vehiculos').where({ placa: p.placa }).first();
  if (!v) return null;
  if (v.uso === 'Ejecutivo') {
    if (isDate(p.desde) && isDate(p.hasta) && p.hasta! >= p.desde!) return diasHabilesLS(p.desde!, p.hasta!) * (await cfgNum(db, 'LITROS_DIA_EJECUTIVO', 16));
    return null;
  }
  const rend = await rendimientoVehiculo(db, v);
  if (num(p.programado) > 0 && rend > 0) return round(num(p.programado) * rend, 2);
  return null;
}

/** Última lectura de km/horómetro conocida de un vehículo hasta una fecha (descargos, viajes, despachos, emisiones). */
export async function ultimaLectura(db: Db, placa: string, hasta: string, excluirEmision = ''): Promise<number> {
  if (!placa) return 0;
  const m = async (q: any) => num((await q.first())?.m);
  const a = await m(db('com_descargo_lineas as l').join('com_descargos as d', 'd.nro', 'l.nro').where('d.placa', placa).where('l.fecha', '<=', hasta).max({ m: 'l.lectura_llegada' }));
  const b = await m(db('com_viajes_det').where({ placa, tipo: 'TRAMO' }).where('fecha', '<=', hasta).max({ m: 'km_final' }));
  const c = await m(db('com_kardex').where({ placa, tipo: 'DESPACHO' }).where('fecha', '<=', hasta).max({ m: 'lectura' }));
  const e = await m(db('com_emisiones').where({ placa }).whereNot({ estado: 'Anulado' }).where('fecha', '<=', hasta).modify((q) => excluirEmision && q.whereNot({ nro: excluirEmision })).max({ m: 'lectura_actual' }));
  return Math.max(a, b, c, e);
}

/** Descargos de vales vencidos (emisión sin descargar pasado el plazo) de un conductor. */
export async function descargosPendientes(db: Db, conductor: string, fecha: string): Promise<number> {
  const plazo = await cfgNum(db, 'DIAS_PLAZO_DESCARGO', 3);
  const rows = await db('com_emisiones').where({ conductor, estado: 'Emitido' }).select('hasta');
  return rows.filter((r: any) => r.hasta && addDays(r.hasta, plazo) < fecha).length;
}

export interface MovK {
  fecha: string;
  tipo: 'INGRESO' | 'SALIDA' | 'DEVOLUCIÓN' | 'BAJA' | 'DESPACHO';
  doc: string;
  almacen: string;
  item: string;
  ent?: number;
  sal?: number;
  cu: number;
  placa?: string;
  lectura?: number | null;
  detalle?: string;
}
export async function kardexAdd(db: Db, u: Usuario, movs: MovK[]) {
  for (const m of movs) {
    await db('com_kardex').insert({
      fecha: m.fecha, tipo: m.tipo, documento: m.doc, almacen: m.almacen, item: m.item, entrada: m.ent ?? 0, salida: m.sal ?? 0, costo_unit: m.cu,
      importe_entrada: round((m.ent ?? 0) * m.cu, 4), importe_salida: round((m.sal ?? 0) * m.cu, 4), placa: m.placa ?? null, lectura: m.lectura ?? null, detalle: m.detalle ?? '', usuario: u.usuario, registrado: nowIso(),
    });
  }
}
export const itemVale = (comb: string, corte: number) => `VALE ${comb.toUpperCase()} Bs ${corte}`;
export const itemTurril = (comb: string) => `${comb.toUpperCase()} (LITROS)`;

export async function totalesAlmacen(db: Db, almacen: string) {
  const r = await db('com_kardex').where({ almacen }).sum({ e: 'entrada', s: 'salida', ie: 'importe_entrada', is: 'importe_salida' }).first();
  return { e: num(r?.e), s: num(r?.s), ie: num(r?.ie), is: num(r?.is) };
}
export async function saldoTurril(db: Db, puesto: string): Promise<number> {
  const t = await totalesAlmacen(db, puesto);
  return round(t.e - t.s, 4);
}
export async function costoPromTurril(db: Db, puesto: string): Promise<number> {
  const t = await totalesAlmacen(db, puesto);
  return t.e - t.s > 1e-4 ? round((t.ie - t.is) / (t.e - t.s), 4) : 0;
}

/** Recalcula recibido y saldo de cada contrato a partir de los lotes recibidos. */
export async function recalcularContratos(db: Db) {
  const cs = await db('com_contratos');
  for (const c of cs) {
    const r = await db('com_lotes').where({ nro_contrato: c.nro }).sum({ t: 'monto' }).first();
    const rec = num(r?.t);
    await db('com_contratos').where({ nro: c.nro }).update({ recibido: rec, saldo: round(num(c.monto) - rec, 4) });
  }
}

export const cortesValidos = async (db: Db): Promise<number[]> => (await cfg(db, 'CORTES_VALE', '30,50,100')).split(',').map((s) => Number(s.trim())).filter(Boolean);
export { fail };
