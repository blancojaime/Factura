import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import ExcelJS from 'exceljs';
import type { FastifyInstance } from 'fastify';
import { dbDemo, admin } from './helpers.js';
import { buildApp } from '../src/app.js';
import { estructuraImportacion, importarMaestro, plantillaImportacion } from '../src/modules/maestros-import.js';
import { setCfg } from '../src/core/services.js';
import { registrarRecepcion, emitirVales } from '../src/modules/combustible/vales.js';

let app: FastifyInstance;
let db: Awaited<ReturnType<typeof dbDemo>>;
const H = (t: string) => ({ authorization: `Bearer ${t}` });
const login = async (usuario: string, clave: string) => (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario, clave } })).json().token as string;
async function libro(cab: string[], filas: unknown[][]): Promise<Buffer> {
  const wb = new ExcelJS.Workbook(); const ws = wb.addWorksheet('DATOS'); ws.addRow(cab); filas.forEach((f) => ws.addRow(f));
  return Buffer.from(await wb.xlsx.writeBuffer());
}

beforeAll(async () => {
  db = await dbDemo();
  app = await buildApp({ db, jwtSecret: 'test-secret', webDir: '/nonexistent' });
  await db('core_usuarios').update({ debe_cambiar: false });
});
afterAll(async () => { await app.close(); await db.destroy(); });

describe('importación de catálogos desde Excel', () => {
  it('el catálogo de destinos se llama «Aperturas programáticas / destino»', async () => {
    expect(estructuraImportacion('proyectos').titulo).toBe('Aperturas programáticas / destino');
    expect(estructuraImportacion('aperturas').columnas.map((c) => c.encabezado)).toEqual(['Apertura', 'Descripción', 'Presupuesto Bs']);
    expect(estructuraImportacion('partidas').columnas.find((c) => c.obligatorio)?.encabezado).toBe('Partida');
  });
  it('la plantilla trae el encabezado y un ejemplo', async () => {
    const wb = new ExcelJS.Workbook(); await wb.xlsx.load((await plantillaImportacion('aperturas')) as any);
    expect(wb.worksheets.map((w) => w.name)).toEqual(['DATOS', 'INSTRUCCIONES']);
    expect((wb.getWorksheet('DATOS')!.getRow(1).values as any[]).slice(1)).toEqual(['Apertura', 'Descripción', 'Presupuesto Bs']);
  });
  it('aperturas con presupuesto: crea, luego actualiza por la clave y no duplica', async () => {
    const buf = await libro(['Apertura', 'Descripción', 'Presupuesto Bs'], [['99 9 001', 'Prueba uno', 1500.5], ['99 9 002', 'Prueba dos', '2.000,00']]);
    expect(await importarMaestro(db, admin, 'aperturas', buf)).toMatchObject({ importado: true, creados: 2, actualizados: 0 });
    const r = await importarMaestro(db, admin, 'aperturas', await libro(['Apertura', 'Descripción', 'Presupuesto Bs'], [['99 9 001', 'Prueba uno (nuevo)', 3000]]));
    expect(r).toMatchObject({ importado: true, creados: 0, actualizados: 1 });
    expect(await db('core_aperturas').where({ apertura: '99 9 001' }).first()).toMatchObject({ descripcion: 'Prueba uno (nuevo)', presupuesto: 3000 });
    expect(Number((await db('core_aperturas').where({ apertura: '99 9 002' }).first()).presupuesto)).toBe(2000);
  });
  it('partidas y destinos; los errores impiden importar todo', async () => {
    expect(await importarMaestro(db, admin, 'partidas', await libro(['Partida', 'Descripción'], [['99999', 'PARTIDA PRUEBA']]))).toMatchObject({ importado: true, creados: 1 });
    expect(await importarMaestro(db, admin, 'proyectos', await libro(['Apertura programática / destino'], [['DESTINO DE PRUEBA']]))).toMatchObject({ importado: true, creados: 1 });
    const mal = await importarMaestro(db, admin, 'aperturas', await libro(['Apertura', 'Presupuesto Bs'], [['88 8 001', 10], ['', 5], ['88 8 003', 'abc'], ['88 8 001', 1]]));
    expect(mal.importado).toBe(false);
    expect(mal.errores.map((e) => e.fila)).toEqual([3, 4, 5]);
    expect(await db('core_aperturas').where({ apertura: '88 8 001' }).first()).toBeUndefined();
    await expect(importarMaestro(db, admin, 'aperturas', await libro(['Descripción'], [['x']]))).rejects.toThrow(/Faltan columnas obligatorias/);
  });
  it('por la API: permisos y descarga de la plantilla', async () => {
    const tc = await login('consulta', 'Consulta2026');
    const r = await app.inject({ method: 'POST', url: '/api/maestros/partidas/importar', headers: { ...H(tc), 'content-type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }, payload: await libro(['Partida', 'Descripción'], [['1', 'x']]) });
    expect(r.statusCode).toBe(403);
    const ta = await login('admin', 'Admin2026');
    const p = await app.inject({ url: '/api/maestros/aperturas/importar/plantilla', headers: H(ta) });
    expect(p.statusCode).toBe(200);
    expect(p.headers['content-type']).toContain('spreadsheetml');
  });
});

describe('importación y envío al VSIAF reservados al administrador', () => {
  it('con la opción activada solo el administrador lo ve y lo ejecuta', async () => {
    const ta = await login('activos', 'Activos2026'), tadm = await login('admin', 'Admin2026');
    expect((await app.inject({ url: '/api/auth/me', headers: H(ta) })).json().vsiaf).toBe(true); // por defecto lo ve Activos Fijos
    expect((await app.inject({ url: '/api/af/vsiaf/lotes', headers: H(ta) })).statusCode).toBe(200);
    await setCfg(db, 'VsiafSoloAdmin', 'SI');
    expect((await app.inject({ url: '/api/auth/me', headers: H(ta) })).json().vsiaf).toBe(false);
    expect((await app.inject({ url: '/api/af/vsiaf/lotes', headers: H(ta) })).statusCode).toBe(403);
    expect((await app.inject({ method: 'POST', url: '/api/af/vsiaf/leer/previsualizar', headers: H(ta), payload: {} })).statusCode).toBe(403);
    expect((await app.inject({ method: 'POST', url: '/api/af/vsiaf/exportar/libro', headers: H(ta), payload: {} })).statusCode).toBe(403);
    expect((await app.inject({ url: '/api/auth/me', headers: H(tadm) })).json().vsiaf).toBe(true);
    expect((await app.inject({ url: '/api/af/vsiaf/lotes', headers: H(tadm) })).statusCode).toBe(200);
    await setCfg(db, 'VsiafSoloAdmin', 'NO');
    expect((await app.inject({ url: '/api/af/vsiaf/lotes', headers: H(ta) })).statusCode).toBe(200);
  });
});

describe('vale de combustible con QR', () => {
  it('el PDF del vale se genera con el recuadro de verificación (QR)', async () => {
    await registrarRecepcion(db, admin, { fecha: '2026-09-27', nro_contrato: 'GAMC-CONT-001/2026', factura: 'F-100', filas: [{ corte: 30, desde: 1001, hasta: 1020 }] });
    const r = await emitirVales(db, admin, { fecha: '2026-09-28', destino: 'VEHICULO', placa: '2345ABC', lectura: 1000, conductor: 'JOSÉ LUIS MAMANI CHOQUE', solicitante: 'Jefe', unidad: 'DESPACHO DEL EJECUTIVO MUNICIPAL', apertura: '00 0 001', trabajo: 'Comisión', desde: '2026-09-28', hasta: '2026-10-03', cantidades: { '30': 5 }, confirmar: true } as any);
    const nro = (r as any).data.nro as string;
    const t = await login('admin', 'Admin2026');
    const sin = await app.inject({ url: `/api/documentos/com-vale?ref=${encodeURIComponent(nro)}`, headers: H(t) });
    expect(sin.statusCode, sin.body).toBe(200);
    expect(sin.rawPayload.subarray(0, 4).toString()).toBe('%PDF');
    // El QR se incrusta como imagen (XObject) en el PDF
    expect(sin.rawPayload.toString('latin1')).toMatch(/\/Subtype \/Image/);
  });
});
