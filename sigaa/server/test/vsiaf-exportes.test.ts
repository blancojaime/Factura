import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import ExcelJS from 'exceljs';
import type { FastifyInstance } from 'fastify';
import { dbDemo } from './helpers.js';
import { buildApp } from '../src/app.js';
import { crearInstalacionSintetica } from '../src/vsiaf/index.js';
import { COLUMNAS } from '../src/vsiaf/exportes.js';
import { ORDEN_HOJAS } from '../src/vsiaf/importador.js';

let app: FastifyInstance;
let db: Awaited<ReturnType<typeof dbDemo>>;
let raiz = '';
let t = '';
const H = () => ({ authorization: `Bearer ${t}` });
const leer = async (buf: Buffer) => { const wb = new ExcelJS.Workbook(); await wb.xlsx.load(buf as any); return wb; };

beforeAll(async () => {
  db = await dbDemo();
  raiz = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'vsiaf-exp-')), 'vsiaf');
  crearInstalacionSintetica(raiz);
  app = await buildApp({ db, jwtSecret: 'test-secret', webDir: '/nonexistent' });
  await db('core_usuarios').update({ debe_cambiar: false });
  t = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'activos', clave: 'Activos2026' } })).json().token;
  await app.inject({ method: 'PUT', url: '/api/af/vsiaf/equivalencias', headers: H(), payload: { items: [{ tipo: 'org_fin', clave: '41/113', valor: '113' }, { tipo: 'org_fin', clave: 'RECURSOS ESPECÍFICOS', valor: '111' }] } });
});
afterAll(async () => { await app.close(); await db.destroy(); });

describe('exportación a Excel del envío al VSIAF', () => {
  it('el libro tiene las hojas y encabezados del Importador Excel → VSIAF y las fechas dd/mm/aaaa', async () => {
    const r = await app.inject({ method: 'POST', url: '/api/af/vsiaf/exportar/libro', headers: H(), payload: { unidad: '1' } });
    expect(r.statusCode).toBe(200);
    expect(r.headers['content-type']).toContain('spreadsheetml');
    const wb = await leer(r.rawPayload);
    expect(wb.worksheets.map((w) => w.name)).toEqual(['LEEME', ...ORDEN_HOJAS]);
    for (const h of ORDEN_HOJAS) {
      const fila1 = (wb.getWorksheet(h)!.getRow(1).values as any[]).slice(1);
      expect(fila1, h).toEqual(COLUMNAS[h].map((c) => c.name));
    }
    const act = wb.getWorksheet('ACTIVOS')!;
    expect(act.rowCount).toBe(49); // encabezado + 48
    const cols = COLUMNAS.ACTIVOS.map((c) => c.name);
    const fila = act.getRow(2);
    expect(String(fila.getCell(cols.indexOf('fecha_incorporacion') + 1).value)).toMatch(/^\d{2}\/\d{2}\/\d{4}$/);
    expect(Number(fila.getCell(cols.indexOf('costo_inicial') + 1).value)).toBeGreaterThan(0);
    expect(String(fila.getCell(cols.indexOf('organismo_financiador') + 1).value)).toMatch(/^\d{3}$/);
  });

  it('no marca nada como enviado y se niega a exportar un libro vacío', async () => {
    expect((await db('af_vsiaf_envios').count({ n: '*' }).first() as any).n).toBe(0);
    const r = await app.inject({ method: 'POST', url: '/api/af/vsiaf/exportar/libro', headers: H(), payload: { unidad: '1', codigos: ['NO-EXISTE'] } });
    expect(r.statusCode).toBe(422);
  });

  it('el informe de validación trae RESUMEN, INCIDENCIAS y el cálculo', async () => {
    const r = await app.inject({ method: 'POST', url: '/api/af/vsiaf/exportar/informe', headers: H(), payload: { ruta: raiz, unidad: '1', hoy: '2026-10-21', fechaCalculo: '2026-10-21', omitirProceso: true, permitirIncorporacionEspecial: false } });
    expect(r.statusCode, r.body).toBe(200);
    const wb = await leer(r.rawPayload);
    const nombres = wb.worksheets.map((w) => w.name);
    expect(nombres).toEqual(expect.arrayContaining(['RESUMEN', 'INCIDENCIAS', 'TOTALES_POR_GRUPO', 'CALCULO_ACTIVOS']));
    expect(wb.getWorksheet('CALCULO_ACTIVOS')!.rowCount).toBe(49);
    expect(String(wb.getWorksheet('RESUMEN')!.getCell('B4').value)).toBeTruthy();
  });

  it('el informe de importación se arma con el resultado recibido y exige datos', async () => {
    expect((await app.inject({ method: 'POST', url: '/api/af/vsiaf/exportar/informe-importacion', headers: H(), payload: {} })).statusCode).toBe(422);
    const v = { sinErrores: true, errores: 0, avisos: 0, resumen: { activos: 1, transferencias: 0, bajas: 0, oficinas: 0, responsables: 0, auxiliares: 0 }, incidencias: [], pasoFinal: 'Re-indexar' };
    const r = await app.inject({ method: 'POST', url: '/api/af/vsiaf/exportar/informe-importacion', headers: H(), payload: { validacion: v, lote: 7, respaldo: 'x.zip' } });
    expect(r.statusCode).toBe(200);
    const wb = await leer(r.rawPayload);
    expect(String(wb.getWorksheet('RESUMEN')!.getCell('A1').value)).toContain('lote 7');
  });
});
