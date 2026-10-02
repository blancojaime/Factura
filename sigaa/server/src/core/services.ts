import type { Db, Usuario } from './context.js';
import { nowIso, num, txt, year, today } from './util.js';
import { fail } from './errors.js';

// ───────── Configuración ─────────
export async function cfg(db: Db, clave: string, def = ''): Promise<string> {
  const r = await db('core_config').where({ clave }).first('valor');
  return r && r.valor !== null && r.valor !== undefined ? String(r.valor) : def;
}
export async function cfgNum(db: Db, clave: string, def = 0): Promise<number> {
  const v = await cfg(db, clave, '');
  return v === '' ? def : num(v);
}
export async function cfgAll(db: Db): Promise<Record<string, string>> {
  const rows = await db('core_config').select('clave', 'valor');
  return Object.fromEntries(rows.map((r: any) => [r.clave, r.valor ?? '']));
}
export async function setCfg(db: Db, clave: string, valor: string, modulo = 'core', descripcion?: string) {
  const ex = await db('core_config').where({ clave }).first('clave');
  if (ex) await db('core_config').where({ clave }).update({ valor });
  else await db('core_config').insert({ clave, valor, modulo, descripcion: descripcion ?? null });
}
export async function gestion(db: Db): Promise<number> {
  const g = await cfgNum(db, 'Gestion', 0);
  return g > 2000 ? g : year(today());
}

// ───────── Numeración correlativa por gestión: CGI-0001/2026 ─────────
export async function siguienteNro(db: Db, prefijo: string, g?: number): Promise<string> {
  const gest = g ?? (await gestion(db));
  const row = await db('core_secuencias').where({ prefijo, gestion: gest }).first();
  let n: number;
  if (row) {
    n = Number(row.ultimo) + 1;
    await db('core_secuencias').where({ prefijo, gestion: gest }).update({ ultimo: n });
  } else {
    n = 1;
    await db('core_secuencias').insert({ prefijo, gestion: gest, ultimo: 1 });
  }
  return `${prefijo}-${String(n).padStart(4, '0')}/${gest}`;
}
/** Registra en la secuencia un número ya existente (carga de datos históricos). */
export async function registrarNro(db: Db, nro: string) {
  const m = /^([A-Z]+)-(\d+)\/(\d{4})$/.exec(nro);
  if (!m) return;
  const [, prefijo, n, g] = m;
  const row = await db('core_secuencias').where({ prefijo, gestion: Number(g) }).first();
  if (!row) await db('core_secuencias').insert({ prefijo, gestion: Number(g), ultimo: Number(n) });
  else if (Number(row.ultimo) < Number(n)) await db('core_secuencias').where({ prefijo, gestion: Number(g) }).update({ ultimo: Number(n) });
}
/** Id correlativo con prefijo de una letra (L000001, M000001, ...). */
export async function siguienteId(db: Db, tabla: string, col: string, letra: string, ancho = 6): Promise<() => string> {
  const r = await db(tabla).max({ m: col }).first();
  let n = r?.m ? Number(String(r.m).slice(letra.length)) : 0;
  return () => `${letra}${String(++n).padStart(ancho, '0')}`;
}

// ───────── Bitácora / auditoría ─────────
export async function bitacora(db: Db, u: Pick<Usuario, 'usuario'> | string, modulo: string, accion: string, documento = '', detalle = '') {
  await db('core_bitacora').insert({
    fecha: nowIso(),
    usuario: typeof u === 'string' ? u : u.usuario,
    modulo,
    accion,
    documento,
    detalle: String(detalle).slice(0, 2000),
  });
}

export async function requerir<T>(v: T | undefined | null, msg: string): Promise<T> {
  if (v === undefined || v === null) fail(msg);
  return v;
}
export const nom = (u: Usuario | string): string => (typeof u === 'string' ? u : u.nombre || u.usuario);
export { txt };
