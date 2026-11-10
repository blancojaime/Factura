/** Utilidades numéricas, de fecha y de texto compartidas por todos los módulos. */

export const EPS = 1e-6;

export const num = (v: unknown): number => {
  if (v === null || v === undefined || v === '') return 0;
  const n = typeof v === 'number' ? v : parseFloat(String(v).replace(',', '.'));
  return Number.isFinite(n) ? n : 0;
};
export const round = (v: number, d = 2): number => {
  const f = Math.pow(10, d);
  return Math.round((v + Number.EPSILON) * f) / f;
};
export const txt = (v: unknown): string => (v === null || v === undefined ? '' : String(v).trim());

// ── Fechas (YYYY-MM-DD, calendario local) ──
const pad = (n: number) => String(n).padStart(2, '0');
export const isoDate = (d: Date): string => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const today = (): string => isoDate(new Date());
export const nowIso = (): string => {
  const d = new Date();
  return `${isoDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};
export const isDate = (v: unknown): boolean => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v) && !isNaN(Date.parse(v.slice(0, 10)));
export const toDate = (s: string): Date => {
  const [y, m, d] = s.slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d);
};
export const dateOnly = (v: unknown): string | null => (isDate(v) ? String(v).slice(0, 10) : null);
export const addDays = (s: string, n: number): string => {
  const d = toDate(s);
  d.setDate(d.getDate() + n);
  return isoDate(d);
};
export const diffDays = (a: string, b: string): number => Math.round((toDate(a).getTime() - toDate(b).getTime()) / 86400000);
export const year = (s: string): number => Number(s.slice(0, 4));
export const month = (s: string): number => Number(s.slice(5, 7));
export const fmtDate = (s?: string | null): string => (s && isDate(s) ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : '');

/** Días hábiles de lunes a viernes sumados a una fecha (plazos de publicación SICOES). */
export function sumarDiasHabiles(f: string, n: number): string {
  let d = toDate(f);
  let c = 0;
  while (c < n) {
    d.setDate(d.getDate() + 1);
    const w = d.getDay();
    if (w !== 0 && w !== 6) c++;
  }
  return isoDate(d);
}
/** Días hábiles lunes a sábado (domingo no laborable), ambos extremos incluidos. Equivale a NETWORKDAYS.INTL(…, 11). */
export function diasHabilesLS(desde: string, hasta: string): number {
  let c = 0;
  const d = toDate(desde);
  const h = toDate(hasta);
  while (d <= h) {
    if (d.getDay() !== 0) c++;
    d.setDate(d.getDate() + 1);
  }
  return c;
}

export const MESES = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'];
export const fechaLiteral = (s: string): string => `${Number(s.slice(8, 10))} de ${MESES[month(s) - 1].toLowerCase()} de ${year(s)}`;

export const fmt2 = (v: unknown): string =>
  num(v).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const fmtCant = (v: unknown): string =>
  num(v).toLocaleString('es-BO', { minimumFractionDigits: 0, maximumFractionDigits: 4 });

// ── Importe en letras (Bolivia: "SON: CIENTO VEINTE 50/100 BOLIVIANOS") ──
const UN = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE', 'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISÉIS', 'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE', 'VEINTE', 'VEINTIÚN', 'VEINTIDÓS', 'VEINTITRÉS', 'VEINTICUATRO', 'VEINTICINCO', 'VEINTISÉIS', 'VEINTISIETE', 'VEINTIOCHO', 'VEINTINUEVE'];
const DE = ['', '', '', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA'];
const CE = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS'];
function bajoMil(n: number): string {
  if (n === 0) return '';
  if (n === 100) return 'CIEN';
  const c = Math.floor(n / 100);
  const r = n % 100;
  let s = c ? CE[c] : '';
  if (r) {
    if (s) s += ' ';
    if (r < 30) s += UN[r];
    else {
      s += DE[Math.floor(r / 10)];
      if (r % 10) s += ' Y ' + UN[r % 10];
    }
  }
  return s;
}
export function enteroEnLetras(n: number): string {
  if (n === 0) return 'CERO';
  const mill = Math.floor(n / 1_000_000);
  const mil = Math.floor((n % 1_000_000) / 1000);
  const r = n % 1000;
  const p: string[] = [];
  if (mill) p.push(mill === 1 ? 'UN MILLÓN' : bajoMil(mill).replace(/UN$/, 'UN') + ' MILLONES');
  if (mil) p.push(mil === 1 ? 'MIL' : bajoMil(mil).replace(/UNO$/, 'UN') + ' MIL');
  if (r) p.push(bajoMil(r));
  return p.join(' ');
}
export function literal(monto: number, moneda = 'BOLIVIANOS'): string {
  const m = round(Math.abs(monto), 2);
  const ent = Math.floor(m);
  const cen = Math.round((m - ent) * 100);
  return `${enteroEnLetras(ent)} ${String(cen).padStart(2, '0')}/100 ${moneda}`;
}

export const sinTildes = (s: string): string => s.normalize('NFD').replace(/[̀-ͯ]/g, '');
export const norm = (s: unknown): string => sinTildes(txt(s)).toUpperCase();
