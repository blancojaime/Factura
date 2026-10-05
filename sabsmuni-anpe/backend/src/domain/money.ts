/**
 * Aritmética monetaria exacta. Todo cálculo se hace en centavos enteros para
 * evitar errores de coma flotante (0.1 + 0.2) que provocarían rechazos en SIGEP.
 */
export const aCentavos = (bs: number): number => Math.round((bs + Number.EPSILON) * 100);
export const deCentavos = (c: number): number => c / 100;
export const redondear2 = (bs: number): number => deCentavos(aCentavos(bs));

export const sumaExacta = (valores: number[]): number =>
  deCentavos(valores.reduce((acc, v) => acc + aCentavos(v), 0));

/** cantidad × precio unitario, redondeado a centavos. */
export const multiplicar = (cantidad: number, precioUnitario: number): number =>
  deCentavos(Math.round((cantidad * aCentavos(precioUnitario) + Number.EPSILON)));

/** monto × porcentaje/100 redondeado a centavos. */
export const porcentajeDe = (monto: number, porcentaje: number): number =>
  deCentavos(Math.round((aCentavos(monto) * porcentaje) / 100 + Number.EPSILON));

export const formatoBs = (bs: number): string =>
  'Bs ' + bs.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const UNIDADES = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve', 'veinte', 'veintiuno', 'veintidós', 'veintitrés', 'veinticuatro', 'veinticinco', 'veintiséis', 'veintisiete', 'veintiocho', 'veintinueve'];
const DECENAS = ['', '', '', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa'];
const CENTENAS = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos'];

function menorQueMil(n: number): string {
  if (n === 0) return '';
  if (n === 100) return 'cien';
  const c = Math.floor(n / 100);
  const r = n % 100;
  const partes: string[] = [];
  if (c) partes.push(CENTENAS[c]);
  if (r < 30) {
    if (r) partes.push(UNIDADES[r]);
  } else {
    const d = Math.floor(r / 10);
    const u = r % 10;
    partes.push(u ? `${DECENAS[d]} y ${UNIDADES[u]}` : DECENAS[d]);
  }
  return partes.join(' ');
}

/** Literal para contratos: 180000.50 → "ciento ochenta mil 50/100 bolivianos". */
export function montoEnLetras(bs: number): string {
  const c = aCentavos(bs);
  const entero = Math.floor(c / 100);
  const cent = c % 100;
  let texto: string;
  if (entero === 0) texto = 'cero';
  else {
    const millones = Math.floor(entero / 1_000_000);
    const miles = Math.floor((entero % 1_000_000) / 1000);
    const resto = entero % 1000;
    const p: string[] = [];
    if (millones) p.push(millones === 1 ? 'un millón' : `${menorQueMil(millones)} millones`);
    if (miles) p.push(miles === 1 ? 'mil' : `${menorQueMil(miles).replace(/uno$/, 'un')} mil`);
    if (resto) p.push(menorQueMil(resto));
    texto = p.join(' ');
  }
  return `${texto} ${String(cent).padStart(2, '0')}/100 bolivianos`;
}
