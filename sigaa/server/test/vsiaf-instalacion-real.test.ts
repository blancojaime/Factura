/**
 * Pruebas de integración contra una instalación REAL del VSIAF (opcional).
 * Defina VSIAF_SAMPLE_DIR con la carpeta que contiene `dbfs` (una COPIA de C:\vsiaf). Siempre se trabaja sobre otra copia temporal.
 *   VSIAF_SAMPLE_DIR=/ruta/a/vsiaf npx vitest run test/vsiaf-instalacion-real.test.ts
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { BdVsiaf, cargarUfv, errores, Importador, valuar, sumarDias } from '../src/vsiaf/index.js';

const MUESTRA = process.env.VSIAF_SAMPLE_DIR;
const fecha = (a: unknown, m: unknown, d: unknown) => `${String(a).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

describe.skipIf(!MUESTRA)('instalación real del VSIAF (copia)', () => {
  let copia = '';
  beforeEach(() => {
    copia = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'vsiaf-real-')), 'vsiaf');
    fs.cpSync(MUESTRA!, copia, { recursive: true });
  });

  it('las UFV se extraen de tipocambio.app', () => {
    const u = cargarUfv(copia);
    expect(u.origen.toLowerCase().endsWith('tipocambio.app')).toBe(true);
    expect(u.obtener('2013-10-14')).toBe(1.87194);
  });

  it('el motor reproduce las instantáneas que guardó el VSIAF en BAJAS y REVAL', () => {
    const db = new BdVsiaf(copia);
    const u = cargarUfv(copia);
    for (const r of db.tabla('BAJAS').registros()) {
      const v = r.valores as Record<string, number>;
      const x = valuar(u, v.COSTO, 0, v.VIDAUTIL, fecha(v.ANO, v.MES, v.DIA), fecha(v.A_BAJA, v.M_BAJA, v.D_BAJA));
      expect(x.depGestion).toBe(v.DEPGESTION);
      expect([x.snapDepacu, x.snapActua]).toEqual([v.DEPACU, v.ACTUA]);
      expect([x.valorActualizadoIni, x.depAcumuladaIni, x.valorActualizado, x.actualizacionDep]).toEqual([v.COSBAJINI, v.COSDAINI, v.COSACTBAJ, v.ACTDABAJ]);
    }
    for (const r of db.tabla('REVAL').registros()) {
      const v = r.valores as Record<string, number>;
      const x = valuar(u, v.COSTO, v.DEPACU_ANT, v.VIDAUTIL, fecha(v.ANO, v.MES, v.DIA), fecha(v.A_REVAL, v.M_REVAL, v.D_REVAL));
      expect([x.depGestion, x.snapDepacu, x.snapActua]).toEqual([v.DEPGESTION, v.DEPACU, v.ACTUA]);
    }
  });

  it('una importación sobre la copia conserva los activos originales', () => {
    const db = new BdVsiaf(copia);
    const antes = new Set([...db.tabla('ACTUAL').registros()].map((r) => String(r.valores.CODIGO).trim()));
    const u = cargarUfv(copia);
    const hoy = new Date().toISOString().slice(0, 10);
    const dmy = (f: string) => `${f.slice(8)}/${f.slice(5, 7)}/${f.slice(0, 4)}`;
    const i = new Importador(db, u, { unidadPorDefecto: '901', hoy, respaldar: true, permitirIncorporacionEspecial: false });
    const r = i.plan({
      UNIDADES: [{ ref: 2, datos: { unidad: '901', descripcion: 'UNIDAD DE ENSAYO' } }],
      OFICINAS: [{ ref: 2, datos: { oficina: 'ADMINISTRACION' } }],
      RESPONSABLES: [{ ref: 2, datos: { oficina: 'ADMINISTRACION', responsable: 'ANA PEREZ', cargo: 'JEFE' } }],
      AUXILIARES: [{ ref: 2, datos: { grupo_contable: 15, auxiliar: 'LAPTOP' } }],
      ACTIVOS: [{ ref: 2, datos: { codigo: 'ENSAYO-1', descripcion: 'LAPTOP DE ENSAYO', grupo_contable: 15, auxiliar: 'LAPTOP', oficina: 'ADMINISTRACION', responsable: 'ANA PEREZ', estado_bien: 'Bueno', fecha_incorporacion: dmy(sumarDias(hoy, -10)), costo_inicial: 5000, organismo_financiador: '111' } }],
    });
    expect(errores(r), JSON.stringify(r.incidencias.filter((x) => x.nivel === 'ERROR'))).toBe(0);
    i.aplicar('Ensayo sobre copia');
    const despues = new Set([...new BdVsiaf(copia).tabla('ACTUAL').registros()].map((x) => String(x.valores.CODIGO).trim()));
    for (const c of antes) expect(despues.has(c)).toBe(true);
    expect(despues.has('ENSAYO-1')).toBe(true);
  });
});
