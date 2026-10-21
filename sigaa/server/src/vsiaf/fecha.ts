/** Fechas sin zona horaria: se manejan como texto ISO `AAAA-MM-DD` y se calculan en UTC. */
export type Fecha = string;

const pad = (n: number, w = 2) => String(n).padStart(w, '0');
export const iso = (y: number, m: number, d: number): Fecha => `${pad(y, 4)}-${pad(m)}-${pad(d)}`;

export function fechaValida(y: number, m: number, d: number): boolean {
  if (!Number.isInteger(y) || !Number.isInteger(m) || !Number.isInteger(d) || y < 1 || m < 1 || m > 12 || d < 1) return false;
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

export function partes(f: Fecha): { y: number; m: number; d: number } {
  return { y: Number(f.slice(0, 4)), m: Number(f.slice(5, 7)), d: Number(f.slice(8, 10)) };
}
const toUtc = (f: Fecha) => { const { y, m, d } = partes(f); return Date.UTC(y, m - 1, d); };
const DIA = 86400000;
export const sumarDias = (f: Fecha, n: number): Fecha => { const t = new Date(toUtc(f) + n * DIA); return iso(t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()); };
/** Días de `a` a `b` (b − a). */
export const difDias = (a: Fecha, b: Fecha): number => Math.round((toUtc(b) - toUtc(a)) / DIA);
export const hoy = (): Fecha => { const t = new Date(); return iso(t.getFullYear(), t.getMonth() + 1, t.getDate()); };
export const dmy = (f: Fecha): string => { const { y, m, d } = partes(f); return `${pad(d)}/${pad(m)}/${y}`; };
/** Fecha válida; si no existe (29/02 en año no bisiesto) devuelve el 28/02. */
export const fechaSegura = (y: number, m: number, d: number): Fecha => (fechaValida(y, m, d) ? iso(y, m, d) : iso(y, m, 28));
