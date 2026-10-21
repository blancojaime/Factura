/**
 * Tabla de índices UFV (la misma que usa el VSIAF).
 *
 * El VSIAF no guarda las UFV en `dbfs`: están embebidas dentro de `tipocambio.app` (tabla TIPCAMB: DIA, MES, ANO, TC,
 * FEULT, USUAR) y se renuevan cada mes con el actualizador del Ministerio. Aquí se extrae esa tabla **solo para leerla**:
 * este módulo nunca modifica las UFV.
 *
 * Orden de búsqueda: `tipocambio.app` → `dbfs/tipcamb.dbf` → CSV incluido.
 */
import fs from 'node:fs';
import { buscarArchivo, DbfTabla } from './dbf.js';
import { Fecha, difDias, fechaValida, iso } from './fecha.js';
import { rutaRecurso } from './recursos.js';

export class UfvFaltante extends Error {}

export class TablaUfv {
  readonly primera: Fecha | null;
  readonly ultima: Fecha | null;
  constructor(private v: Map<Fecha, number>, readonly origen: string) {
    const dias = [...v.keys()].sort();
    this.primera = dias[0] ?? null;
    this.ultima = dias[dias.length - 1] ?? null;
  }
  get tamano(): number { return this.v.size; }
  tiene(d: Fecha): boolean { return this.v.has(d); }
  obtener(d: Fecha): number {
    const x = this.v.get(d);
    if (x === undefined) throw new UfvFaltante(`UFV no registrada para ${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`);
    return x;
  }
  /** Última fecha en que el índice varía (después el valor es plano / proyectado). */
  get ultimoCambio(): Fecha | null {
    const dias = [...this.v.keys()].sort();
    if (!dias.length) return null;
    for (let i = dias.length - 1; i > 0; i--) if (this.v.get(dias[i]) !== this.v.get(dias[i - 1])) return dias[i];
    return dias[0];
  }
  /** Días entre el último cambio de índice y `fecha` (para avisar de UFV desactualizadas). */
  diasDesdeUltimoCambio(fecha: Fecha): number | null { const c = this.ultimoCambio; return c ? difDias(c, fecha) : null; }
}

// Descriptor de campo «DIA» (N,2,0) al comienzo de la tabla TIPCAMB embebida.
const DESCRIPTOR_DIA = /DIA\0{8}N[\s\S]{4}\x02\0/g;

function analizarEmbebida(data: Buffer, inicio: number): Map<Fecha, number> {
  const nrec = data.readUInt32LE(inicio + 4);
  const hlen = data.readUInt16LE(inicio + 8);
  const rlen = data.readUInt16LE(inicio + 10);
  const out = new Map<Fecha, number>();
  const base = inicio + hlen;
  for (let i = 0; i < nrec; i++) {
    const r = data.subarray(base + i * rlen, base + (i + 1) * rlen);
    if (r.length < rlen || r[0] === 0x2a) continue;
    const y = Number(r.subarray(5, 9).toString('latin1')), m = Number(r.subarray(3, 5).toString('latin1')), d = Number(r.subarray(1, 3).toString('latin1'));
    const tc = Number(r.subarray(9, 17).toString('latin1'));
    if (!fechaValida(y, m, d) || Number.isNaN(tc)) continue;
    out.set(iso(y, m, d), tc);
  }
  return out;
}

export function cargarDesdeApp(ruta: string): TablaUfv {
  const data = fs.readFileSync(ruta);
  const texto = data.toString('latin1');
  let mejor: Map<Fecha, number> | null = null;
  const maxFecha = (m: Map<Fecha, number>) => [...m.keys()].sort().pop() ?? '';
  for (const m of texto.matchAll(DESCRIPTOR_DIA)) {
    const inicio = (m.index ?? 0) - 32;
    if (inicio < 0 || ![0x03, 0x30, 0x83, 0xf5].includes(data[inicio])) continue;
    let cand: Map<Fecha, number>;
    try { cand = analizarEmbebida(data, inicio); } catch { continue; }
    // el .app puede traer una copia vieja: se usa la más reciente
    if (cand.size && (!mejor || maxFecha(cand) > maxFecha(mejor) || (maxFecha(cand) === maxFecha(mejor) && cand.size > mejor.size))) mejor = cand;
  }
  if (!mejor) throw new Error(`No se encontró la tabla TIPCAMB dentro de ${ruta}`);
  return new TablaUfv(mejor, ruta);
}

export function cargarDesdeDbf(ruta: string): TablaUfv {
  const t = new DbfTabla(ruta);
  const v = new Map<Fecha, number>();
  for (const r of t.registros()) {
    const { ANO, MES, DIA, TC } = r.valores as Record<string, number | null>;
    if (ANO && MES && DIA && TC !== null && fechaValida(ANO, MES, DIA)) v.set(iso(ANO, MES, DIA), Number(TC));
  }
  return new TablaUfv(v, ruta);
}

export function cargarDesdeCsv(ruta: string): TablaUfv {
  const v = new Map<Fecha, number>();
  for (const linea of fs.readFileSync(ruta, 'utf8').split(/\r?\n/).slice(1)) {
    const [f, u] = linea.split(',');
    if (f && u) v.set(f.trim(), Number(u));
  }
  return new TablaUfv(v, ruta);
}

/** Carga las UFV con el mismo origen que el VSIAF; si no existe, usa el CSV incluido. */
export function cargarUfv(carpetaVsiaf?: string | null, carpetaDbfs?: string | null): TablaUfv {
  if (carpetaVsiaf) {
    const app = buscarArchivo(carpetaVsiaf, 'tipocambio.app');
    if (app) { try { return cargarDesdeApp(app); } catch { /* se prueba el siguiente origen */ } }
  }
  if (carpetaDbfs) {
    const p = buscarArchivo(carpetaDbfs, 'tipcamb.dbf');
    if (p) { try { return cargarDesdeDbf(p); } catch { /* se prueba el siguiente origen */ } }
  }
  return cargarDesdeCsv(rutaRecurso('ufv_embedded.csv'));
}
