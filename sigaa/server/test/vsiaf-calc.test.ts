import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cargarDesdeCsv, valuar, fechaFinVida, rutaUfvIncluida } from './vsiaf-util.js';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const UFV = cargarDesdeCsv(rutaUfvIncluida());
const d = (s: string) => `${s.slice(6, 10)}-${s.slice(3, 5)}-${s.slice(0, 2)}`;

describe('UFV del manual', () => {
  it('índices conocidos', () => {
    expect(UFV.obtener('2013-10-14')).toBe(1.87194);
    expect(UFV.obtener('2013-04-11')).toBe(1.82467);
    expect(UFV.obtener('2011-08-29')).toBe(1.66535);
    expect(UFV.obtener('2013-10-10')).toBe(1.87054);
  });
  it('rechaza fechas sin UFV', () => {
    expect(() => UFV.obtener('1980-01-01')).toThrow(/UFV no registrada/);
  });
});

describe('cálculo — ejemplos del manual (cifras exactas)', () => {
  it('620,00 · vida 10 · incorporación 11/04/2013 · cálculo 14/10/2013', () => {
    const v = valuar(UFV, 620, 0, 10, d('11/04/2013'), d('14/10/2013'));
    expect(v.factor).toBe(1.025906);
    expect(v.valorActualizado).toBe(636.06);
    expect(v.diasTotales).toBe(187);
    expect(v.depGestion).toBe(32.59);
    expect(v.valorNeto).toBe(603.47);
  });
  it('1.380,00 · vida 10 · incorporación 29/08/2011 · cálculo 10/10/2013', () => {
    const v = valuar(UFV, 1380, 0, 10, d('29/08/2011'), d('10/10/2013'));
    expect(v.factor).toBe(1.123211);
    expect(v.valorActualizado).toBe(1550.03);
    expect(v.diasTotales).toBe(774);
    expect(v.diasGestion).toBe(283);
    expect(v.depAcumulada).toBe(328.69);
    expect(v.valorNeto).toBe(1221.34);
    expect(Math.abs(v.depGestion - 120.16)).toBeLessThanOrEqual(0.03); // el manual muestra 120,1x
  });
  it('un día de depreciación: 5.500 · vida 5 → 3,01', () => {
    const v = valuar(UFV, 5500, 0, 5, d('10/10/2013'), d('10/10/2013'));
    expect(v.diasTotales).toBe(1);
    expect(v.depGestion).toBe(3.01);
  });
  it('vida terminada: dep. acumulada = valor actualizado, neto 0 y sin dep. de gestión', () => {
    const inc = '2010-01-01';
    expect(fechaFinVida(inc, 4)).toBe('2013-12-31');
    const v = valuar(UFV, 8000, 0, 4, inc, '2015-06-30');
    expect(v.depAcumulada).toBe(v.valorActualizado);
    expect(v.valorNeto).toBe(0);
    expect(v.depGestion).toBe(0);
  });
  it('grupos sin depreciación ni actualización (36, 40) y terrenos (34: actualiza, no deprecia)', () => {
    const v = valuar(UFV, 5000, 0, 0, '2013-04-11', '2013-10-14', false, false);
    expect(v.valorActualizado).toBe(5000);
    expect(v.depAcumulada).toBe(0);
    expect(v.valorNeto).toBe(5000);
    const t = valuar(UFV, 5000, 0, 0, '2013-04-11', '2013-10-14', false, true);
    expect(t.valorActualizado).toBe(5129.53);
    expect(t.depAcumulada).toBe(0);
  });
  it('identidades contables', () => {
    const v = valuar(UFV, 12345.67, 0, 8, '2018-03-15', '2026-10-20');
    expect(Math.abs(v.valorNeto - (v.valorActualizado - v.depAcumulada))).toBeLessThan(0.005);
    expect(Math.abs(v.actualizacionGestion - (v.valorActualizado - v.valorActualizadoIni))).toBeLessThan(0.005);
    expect(Math.abs(v.depAcumulada - (v.depAcumuladaIni + v.depGestion + v.actualizacionDep))).toBeLessThan(0.011);
  });
  it('instantánea de BAJAS del caso real del VSIAF (costo 1,00 · vida 4 · inc 21/09/2026 · baja 20/10/2026)', () => {
    const v = valuar(UFV, 1, 0, 4, '2026-09-21', '2026-10-20');
    expect(v.depGestion).toBe(0.02);
    expect(v.snapDepacu).toBe(0);
    expect(v.snapActua).toBe(1);
    expect(v.valorActualizadoIni).toBe(1); // COSBAJINI
    expect(v.depAcumuladaIni).toBe(0); // COSDAINI
    expect(v.valorActualizado).toBe(1); // COSACTBAJ
    expect(v.actualizacionDep).toBe(0); // ACTDABAJ
  });
});

describe('contraste con el motor de referencia (Python): 600 casos aleatorios', () => {
  const casos = JSON.parse(fs.readFileSync(path.join(aqui, 'fixtures/vsiaf/calc_golden.json'), 'utf8')) as any[];
  it('coincide cifra por cifra', () => {
    const difs: string[] = [];
    for (const c of casos) {
      const v: any = valuar(UFV, c.costo, c.dep, c.vida, c.inc, c.calc, c.depreciar, c.actualizar);
      const e = c.out;
      const mapa: Record<string, string> = { factor: 'factor', valorActualizado: 'valor_actualizado', valorActualizadoIni: 'valor_actualizado_ini', actualizacionGestion: 'actualizacion_gestion',
        depAcumulada: 'dep_acumulada', depAcumuladaIni: 'dep_acumulada_ini', depGestion: 'dep_gestion', actualizacionDep: 'actualizacion_dep', valorNeto: 'valor_neto',
        diasTotales: 'dias_totales', diasGestion: 'dias_gestion', snapDepacu: 'snap_depacu', snapActua: 'snap_actua', finVida: 'fin_vida' };
      for (const [k, py] of Object.entries(mapa)) {
        const a = v[k], b = e[py];
        const igual = typeof a === 'number' && typeof b === 'number' ? Math.abs(a - b) < 0.0051 && (k === 'factor' ? Math.abs(a - b) < 1e-9 : true) : a === b;
        if (!igual) difs.push(`${k}: ts=${a} py=${b} :: ${JSON.stringify({ costo: c.costo, dep: c.dep, vida: c.vida, inc: c.inc, calc: c.calc, depreciar: c.depreciar, actualizar: c.actualizar })}`);
      }
    }
    expect(difs.slice(0, 5)).toEqual([]);
  });
  it('idéntico al centavo (doble precisión como FoxPro; ROUND mitad arriba con Decimal)', () => {
    const difs: string[] = [];
    for (const c of casos) {
      const v: any = valuar(UFV, c.costo, c.dep, c.vida, c.inc, c.calc, c.depreciar, c.actualizar);
      for (const [k, py] of [['valorActualizado', 'valor_actualizado'], ['depAcumulada', 'dep_acumulada'], ['depGestion', 'dep_gestion'], ['valorNeto', 'valor_neto'], ['valorActualizadoIni', 'valor_actualizado_ini'], ['depAcumuladaIni', 'dep_acumulada_ini'], ['actualizacionDep', 'actualizacion_dep'], ['snapDepacu', 'snap_depacu'], ['snapActua', 'snap_actua']] as const) {
        if (Math.abs(v[k] - c.out[py]) > 1e-9) difs.push(`${k}: ts=${v[k]} py=${c.out[py]}`);
      }
    }
    expect(difs.slice(0, 5)).toEqual([]);
  });
});
