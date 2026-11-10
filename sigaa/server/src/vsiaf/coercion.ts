/** Conversión de celdas/valores de entrada (texto, número, fecha) con los mismos criterios del importador de referencia. */
import { Fecha, fechaValida, iso, sumarDias } from './fecha.js';

export const vacio = (v: unknown): boolean => v === null || v === undefined || (typeof v === 'string' && !v.trim());

export function comoTexto(v: unknown): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'boolean') return v ? 'SI' : 'NO';
  if (typeof v === 'number') return Number.isFinite(v) && v === Math.trunc(v) ? String(Math.trunc(v)) : String(v);
  if (v instanceof Date) { const d = String(v.getUTCDate()).padStart(2, '0'), m = String(v.getUTCMonth() + 1).padStart(2, '0'); return `${d}/${m}/${v.getUTCFullYear()}`; }
  return String(v).trim();
}

export function comoNumero(v: unknown): number | null {
  if (vacio(v)) return null;
  if (typeof v === 'boolean') throw new Error('no es un número');
  if (typeof v === 'number') return v;
  let s = String(v).trim().replace(/ /g, '').replace(/Bs/gi, '');
  if (!s) return null;
  if (s.includes(',') && s.includes('.')) s = s.lastIndexOf('.') > s.lastIndexOf(',') ? s.replace(/,/g, '') : s.replace(/\./g, '').replace(',', '.');
  else if (s.includes(',')) s = s.replace(',', '.');
  else if ((s.match(/\./g) ?? []).length > 1) s = s.replace(/\./g, '');
  const n = Number(s);
  if (!/^[+-]?(\d+\.?\d*|\.\d+)$/.test(s) || Number.isNaN(n)) throw new Error(`«${v}» no es un número válido`);
  return n;
}

export function comoFecha(v: unknown): Fecha | null {
  if (vacio(v)) return null;
  if (v instanceof Date) return iso(v.getUTCFullYear(), v.getUTCMonth() + 1, v.getUTCDate());
  if (typeof v === 'number') {
    if (v > 20000 && v < 80000) return sumarDias('1899-12-30', Math.floor(v)); // número de serie de Excel
    throw new Error(`«${v}» no es una fecha válida`);
  }
  const s = String(v).trim();
  let m = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/.exec(s);
  if (m && fechaValida(+m[3], +m[2], +m[1])) return iso(+m[3], +m[2], +m[1]);
  m = /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[T ].*)?$/.exec(s);
  if (m && fechaValida(+m[1], +m[2], +m[3])) return iso(+m[1], +m[2], +m[3]);
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{2})$/.exec(s);
  if (m) {
    const yy = +m[3];
    const y = yy >= 69 ? 1900 + yy : 2000 + yy;
    if (fechaValida(y, +m[2], +m[1])) return iso(y, +m[2], +m[1]);
  }
  throw new Error(`«${v}» no es una fecha válida (use dd/mm/aaaa)`);
}
