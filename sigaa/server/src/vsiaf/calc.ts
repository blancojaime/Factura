/**
 * Motor de cálculo equivalente al del VSIAF (actualización por UFV + depreciación).
 *
 * Reglas (deducidas del manual del VSIAF 2.0, de sus ejemplos numéricos y de las rutinas ffactor / vvalact / ddepgestion /
 * ddeprecia / act_da_gestion del sistema):
 *  - factor            = UFV(fecha de cálculo) / UFV(fecha de incorporación)  (6 decimales); 1 si el grupo no se actualiza.
 *                        Si el activo se deprecia y ya pasó su vida útil, la UFV final es la de la fecha en que termina.
 *  - valor actualizado = costo × factor
 *  - % depreciación    = 1 / vida útil (si el grupo se deprecia)
 *  - días              = días corridos *inclusive* (11/04 → 14/10 = 187 días)
 *  - dep. gestión      = valor actualizado × % × días de la gestión / 365
 *  - dep. acumulada    = dep. acumulada inicial × factor + valor actualizado × % × días totales / 365 (tope: valor actualizado)
 *  - valor neto        = valor actualizado − dep. acumulada
 * Aritmética en doble precisión (igual que FoxPro, que es el lenguaje del VSIAF) y redondeo a 2 decimales «mitad hacia arriba» con
 * `Decimal` sobre la representación decimal más corta del resultado (como el ROUND de FoxPro): así no aparecen centavos fantasma.
 */
import Decimal from 'decimal.js';
import { Fecha, difDias, fechaSegura, partes, sumarDias, iso } from './fecha.js';
import { TablaUfv } from './ufv.js';

const FACTOR_DECIMALES = 6;
const DIAS_ANIO = 365;
/** ROUND(x, 2) de FoxPro: mitad hacia arriba sobre el valor decimal más corto del resultado. */
export const redondeo2 = (x: number): number => new Decimal(String(x)).toDecimalPlaces(2, Decimal.ROUND_HALF_UP).toNumber();
const r2 = redondeo2;

const esEntero = (x: number) => Math.abs(x - Math.round(x)) < 1e-9;

/** Último día depreciable (FFECHAVUTIL del VSIAF). */
export function fechaFinVida(inc: Fecha, vida: number): Fecha {
  const { y, m, d } = partes(inc);
  if (esEntero(vida)) {
    const v = Math.round(vida);
    if (m === 2 && d === 29) return fechaSegura(y + v, 2, 28);
    return sumarDias(fechaSegura(y + v, m, d), -1);
  }
  return sumarDias(inc, Math.trunc(DIAS_ANIO * vida));
}

/** Fecha cuya UFV se usa como índice final al terminar la vida útil (TCVUTIL). */
export function fechaUfvVida(inc: Fecha, vida: number): Fecha {
  const { y, m, d } = partes(inc);
  if (esEntero(vida)) return fechaSegura(y + Math.round(vida), m, d);
  return sumarDias(inc, Math.trunc(DIAS_ANIO * vida));
}

export const diasInclusive = (desde: Fecha, hasta: Fecha): number => Math.max(0, difDias(desde, hasta) + 1);

export interface Valuacion {
  costo: number;
  depAcuInicialEntrada: number;
  factor: number;
  ufvIncorporacion: number;
  ufvCalculo: number;
  pctDeprecia: number;
  diasTotales: number;
  diasGestion: number;
  finVida: Fecha | null;
  valorActualizadoIni: number;
  actualizacionGestion: number;
  valorActualizado: number;
  depAcumuladaIni: number;
  depGestion: number;
  actualizacionDep: number;
  depAcumulada: number;
  valorNeto: number;
  /** Instantáneas que el VSIAF guarda en REVAL / BAJAS. */
  snapDepacu: number;
  snapActua: number;
}

export function valuar(ufv: TablaUfv, costo: number, depAcuInicial: number, vida: number, inc: Fecha, calc: Fecha, depreciar = true, actualizar = true): Valuacion {
  vida = Number(vida || 0);
  const depOn = !!depreciar && vida > 0;
  const pct = depOn ? 1.0 / vida : 0.0;
  const fin = depOn ? fechaFinVida(inc, vida) : null;
  let ufvVida: number | null = null;
  const ufvInc = ufv.obtener(inc);

  const ufvEn = (d: Fecha): number => {
    if (depOn && fin !== null && d > fin) {
      if (ufvVida === null) ufvVida = ufv.obtener(fechaUfvVida(inc, vida));
      return ufvVida;
    }
    return ufv.obtener(d);
  };
  const factorEn = (d: Fecha): number => (!actualizar ? 1.0 : Number((ufvEn(d) / ufvInc).toFixed(FACTOR_DECIMALES)));

  const empaquetar = (o: Omit<Valuacion, 'snapDepacu' | 'snapActua'>): Valuacion => {
    const snapDepacu = r2(o.depAcumulada - o.depGestion);
    return { ...o, snapDepacu, snapActua: r2(o.valorActualizado - snapDepacu) };
  };

  if (calc < inc) {
    return empaquetar({ costo, depAcuInicialEntrada: depAcuInicial, factor: 1, ufvIncorporacion: ufvInc, ufvCalculo: ufvInc, pctDeprecia: pct, diasTotales: 0, diasGestion: 0, finVida: fin,
      valorActualizadoIni: costo, actualizacionGestion: 0, valorActualizado: costo, depAcumuladaIni: depAcuInicial, depGestion: 0, actualizacionDep: 0, depAcumulada: depAcuInicial, valorNeto: r2(costo - depAcuInicial) });
  }

  const factor = factorEn(calc);
  const valact = r2(costo * factor);
  const fin2 = fin !== null ? (calc < fin ? calc : fin) : calc;
  const dTot = depOn ? diasInclusive(inc, fin2) : 0;
  const inicioAnio = iso(partes(calc).y, 1, 1);
  const dGes = depOn ? diasInclusive(inc > inicioAnio ? inc : inicioAnio, fin2) : 0;
  const depGes = r2((valact * pct * dGes) / DIAS_ANIO);
  let depAcu = r2(depAcuInicial * factor) + r2((valact * pct * dTot) / DIAS_ANIO);
  if (valact > 0) depAcu = Math.min(depAcu, valact);

  // Situación al inicio de la gestión
  let valactIni: number;
  let depIni: number;
  if (partes(inc).y < partes(calc).y) {
    const finAnt = iso(partes(calc).y - 1, 12, 31);
    const fPrev = factorEn(finAnt);
    valactIni = r2(costo * fPrev);
    const finPrev = fin !== null ? (finAnt < fin ? finAnt : fin) : finAnt;
    const dPrev = depOn ? diasInclusive(inc, finPrev) : 0;
    depIni = r2(depAcuInicial * fPrev) + r2((valactIni * pct * dPrev) / DIAS_ANIO);
    if (valactIni > 0) depIni = Math.min(depIni, valactIni);
  } else {
    valactIni = costo;
    depIni = depAcuInicial;
  }

  return empaquetar({
    costo, depAcuInicialEntrada: depAcuInicial, factor, ufvIncorporacion: ufvInc, ufvCalculo: ufvEn(calc), pctDeprecia: pct,
    diasTotales: dTot, diasGestion: dGes, finVida: fin,
    valorActualizadoIni: valactIni,
    actualizacionGestion: r2(valact - valactIni),
    valorActualizado: valact,
    depAcumuladaIni: depIni, depGestion: depGes,
    actualizacionDep: r2(depAcu - depIni - depGes),
    depAcumulada: depAcu, valorNeto: r2(valact - depAcu),
  });
}
