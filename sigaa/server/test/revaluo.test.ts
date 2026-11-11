import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import AdmZip from 'adm-zip';
import type { FastifyInstance } from 'fastify';
import { dbDemo, admin } from './helpers.js';
import { buildApp } from '../src/app.js';
import { calcularVtr, elegibles, crearLote, obtenerLote, guardarItem, agregarCotizacion, aprobarLote, marcarOperativo, quitarCotizacion } from '../src/modules/activos/revaluo.js';

let db: Awaited<ReturnType<typeof dbDemo>>;
let app: FastifyInstance;
let tok = '';
let dir = '';
let cods: string[] = [];
const H = () => ({ authorization: `Bearer ${tok}` });
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==', 'base64');

beforeAll(async () => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'reval-'));
  process.env.SIGAA_FOTOS_DIR = path.join(dir, 'fotos');
  fs.mkdirSync(process.env.SIGAA_FOTOS_DIR, { recursive: true });
  db = await dbDemo();
  await db('core_usuarios').update({ debe_cambiar: false });
  app = await buildApp({ db, jwtSecret: 'test-secret', webDir: '/nonexistent' });
  tok = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'activos', clave: 'Activos2026' } })).json().token;
  const todos = await db('af_activos').where('situacion', '!=', 'BAJA').orderBy('codigo').limit(6);
  cods = todos.map((a: any) => a.codigo);
  // 3 elegibles (Bueno/Regular/Malo), 1 no operativo, 1 con valor mayor a 1, 1 en estado Nuevo
  const estados = ['Bueno', 'Regular', 'Malo', 'Bueno', 'Bueno', 'Nuevo'];
  for (let i = 0; i < 6; i++) await db('af_activos').where({ codigo: cods[i] }).update({ valor_libros: i === 4 ? 500 : 1, estado: estados[i], operativo: i === 3 ? 'NO' : 'SI' });
  fs.writeFileSync(path.join(process.env.SIGAA_FOTOS_DIR!, 'f1.png'), PNG);
  await db('af_activos').where({ codigo: cods[0] }).update({ foto1: 'f1.png' });
});
afterAll(async () => { await app.close(); fs.rmSync(dir, { recursive: true, force: true }); });

describe('Revalúo técnico: cálculo', () => {
  it('promedio, mediana, mínimo Bs 1 y vacío', () => {
    expect(calcularVtr([1000, 1200, 1400], 'PROMEDIO', 0.8, 1)).toEqual({ vn_base: 1200, vtr: 960, incremento: 959 });
    expect(calcularVtr([1000, 1200, 3000], 'MEDIANA', 0.5, 1).vn_base).toBe(1200);
    expect(calcularVtr([100, 300], 'MEDIANA', 0.5, 1).vn_base).toBe(200);
    expect(calcularVtr([1], 'PROMEDIO', 0.15, 1).vtr).toBe(1);
    expect(calcularVtr([], 'PROMEDIO', 0.5, 1)).toEqual({ vn_base: 0, vtr: 0, incremento: 0 });
  });
});

describe('Revalúo técnico: bandeja y flujo', () => {
  it('la bandeja filtra por valor Bs 1, estado Bueno/Regular/Malo y operativo', async () => {
    const e = await elegibles(db);
    const c = e.map((a: any) => a.codigo);
    expect(c).toContain(cods[0]); expect(c).toContain(cods[1]); expect(c).toContain(cods[2]);
    expect(c).not.toContain(cods[3]); // no operativo
    expect(c).not.toContain(cods[4]); // valor 500
    expect(c).not.toContain(cods[5]); // estado Nuevo
    const porCta = await elegibles(db, { id_cta: -1 });
    expect(porCta).toHaveLength(0);
  });

  it('rechaza activos no elegibles y operativo NO exige motivo', async () => {
    await expect(crearLote(db, admin, { codigos: [cods[3]] })).rejects.toThrow(/elegibles/);
    await expect(marcarOperativo(db, admin, cods[0], 'NO', '')).rejects.toThrow(/motivo/);
  });

  let id = 0; let items: any[] = [];
  it('crea el lote, valida factores y cotizaciones, calcula y aprueba', async () => {
    const r = await crearLote(db, admin, { codigos: cods.slice(0, 3), perito: 'Ing. Perito Prueba', perito_cargo: 'Perito', comision: 'Ana Pérez | Jefa de Contabilidad\nLuis Mora | Técnico' });
    id = r.id; expect(r.nro).toMatch(/^REV-0001\//);
    // un activo en lote abierto sale de la bandeja
    expect((await elegibles(db)).map((a: any) => a.codigo)).not.toContain(cods[0]);
    await expect(crearLote(db, admin, { codigos: [cods[0]] })).rejects.toThrow(/otro lote/);
    let l = await obtenerLote(db, id); items = l.items;
    expect(items[0].factor).toBe(0.78); // Bueno
    await expect(guardarItem(db, admin, items[0].id, { factor: 0.95 })).rejects.toThrow(/entre 0.70 y 0.85/);
    await expect(guardarItem(db, admin, items[1].id, { factor: 0.7 })).rejects.toThrow(/entre 0.40 y 0.60/);
    await expect(aprobarLote(db, admin, id, {})).rejects.toThrow(/cotización/);
    // cotizaciones: validación y máximo 3
    await expect(agregarCotizacion(db, admin, items[0].id, { proveedor: 'X', fecha: '2026-01-05', valor: 100 })).rejects.toThrow(/respaldo/);
    for (const v of [1000, 1200, 1400]) await agregarCotizacion(db, admin, items[0].id, { proveedor: 'Muebles SRL', nit: '1020304050', fecha: '2026-01-05', valor: v });
    await expect(agregarCotizacion(db, admin, items[0].id, { proveedor: 'Otra', nit: '1', fecha: '2026-01-05', valor: 5 })).rejects.toThrow(/Máximo 3/);
    await guardarItem(db, admin, items[0].id, { factor: 0.8, vida_anios: 4, vida_meses: 6, justificacion: 'Buen estado, uso moderado' });
    l = await obtenerLote(db, id);
    expect(l.items[0]).toMatchObject({ vn_base: 1200, vtr: 960, incremento: 959 });
    // los otros dos
    await agregarCotizacion(db, admin, items[1].id, { proveedor: 'Tienda', referencia: 'https://ejemplo.bo/x', fecha: '2026-01-05', valor: 800 });
    await guardarItem(db, admin, items[1].id, { vida_anios: 2, justificacion: 'Desgaste visible pero funcional' });
    const c3 = await agregarCotizacion(db, admin, items[2].id, { proveedor: 'Tienda', nro_proforma: 'P-1', fecha: '2026-01-05', valor: 2 });
    await guardarItem(db, admin, items[2].id, { factor: 0.15, vida_meses: 8, justificacion: 'Operativo con fallas leves' });
    expect((await obtenerLote(db, id)).items[2].vtr).toBe(1); // mínimo Bs 1
    await quitarCotizacion(db, admin, c3.id); // sin cotización: falta
    await expect(aprobarLote(db, admin, id, {})).rejects.toThrow(/falta al menos 1 cotización/);
    await agregarCotizacion(db, admin, items[2].id, { proveedor: 'Tienda', nro_proforma: 'P-2', fecha: '2026-01-05', valor: 50 });
    l = await obtenerLote(db, id);
    expect(l.totales.incremento).toBeCloseTo(959 + 399 + 7.5 - 0 - 1 + 0 - 0, 0); // 960-1 + (800*.5=400-1) + (50*.15=7.5-1)
  });

  it('descarga los informes Word antes y después de aprobar; aprobación actualiza activos y kardex', async () => {
    const pre = await app.inject({ method: 'GET', url: `/api/af/revaluo/lotes/${id}/informe`, headers: H() });
    expect(pre.statusCode, pre.body.slice(0, 200)).toBe(200);
    expect(new AdmZip(pre.rawPayload).getEntry('word/document.xml')!.getData().toString()).toContain('PRELIMINAR');
    const r = await app.inject({ method: 'POST', url: `/api/af/revaluo/lotes/${id}/aprobar`, headers: H(), payload: { resolucion: 'RA-015/2026' } });
    expect(r.statusCode).toBe(200);
    const a = await db('af_activos').where({ codigo: cods[0] }).first();
    expect(Number(a.valor)).toBe(960); expect(Number(a.valor_libros)).toBe(960); expect(a.vida_residual).toBe(54); expect(a.revaluado).toMatch(/^\d{4}-/);
    const mov = await db('af_movimientos').where({ codigo: cods[0], tipo: 'REVALÚO' });
    expect(mov).toHaveLength(1); expect(mov[0].resolucion).toBe('RA-015/2026');
    // ya no es elegible y no se puede modificar
    expect((await elegibles(db)).map((x: any) => x.codigo)).not.toContain(cods[0]);
    await expect(guardarItem(db, admin, items[0].id, { vida_anios: 3 })).rejects.toThrow(/aprobado/);
    await expect(aprobarLote(db, admin, id, {})).rejects.toThrow(/aprobado/);
    const inf = await app.inject({ method: 'GET', url: `/api/af/revaluo/lotes/${id}/informe`, headers: H() });
    const xml = new AdmZip(inf.rawPayload).getEntry('word/document.xml')!.getData().toString();
    for (const t of ['NC 4', 'NB-SABS', 'D.S. Nº 0181', 'Ley Nº 1178', '24051', 'Reserva por Revalúos Técnicos', 'RA-015/2026', 'Ana Pérez']) expect(xml).toContain(t);
    expect(xml).not.toContain('PRELIMINAR');
    const an = await app.inject({ method: 'GET', url: `/api/af/revaluo/lotes/${id}/anexos`, headers: H() });
    const z = new AdmZip(an.rawPayload);
    const ax = z.getEntry('word/document.xml')!.getData().toString();
    for (const t of ['CUADRO COMPARATIVO', 'ASIENTO CONTABLE', 'SUMAS IGUALES', 'Activo Fijo']) expect(ax).toContain(t);
    if (process.env.REVAL_DUMP) { fs.writeFileSync(path.join(process.env.REVAL_DUMP, 'informe.docx'), inf.rawPayload); fs.writeFileSync(path.join(process.env.REVAL_DUMP, 'anexos.docx'), an.rawPayload); }
    expect(z.getEntries().some((e) => e.entryName.startsWith('word/media/'))).toBe(true); // foto incrustada
  });

  it('un usuario de consulta no puede crear lotes', async () => {
    const t = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'consulta', clave: 'Consulta2026' } })).json().token;
    const r = await app.inject({ method: 'POST', url: '/api/af/revaluo/lotes', headers: { authorization: `Bearer ${t}` }, payload: { codigos: [cods[1]] } });
    expect(r.statusCode).toBe(403);
  });
});
