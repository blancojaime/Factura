import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { FastifyInstance } from 'fastify';
import { dbDemo } from './helpers.js';
import { buildApp } from '../src/app.js';

const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==', 'base64');
let app: FastifyInstance;
let db: Awaited<ReturnType<typeof dbDemo>>;
let raiz = '', fotos = '', t = '';
const H = () => ({ authorization: `Bearer ${t}` });

beforeAll(async () => {
  raiz = fs.mkdtempSync(path.join(os.tmpdir(), 'audit-'));
  fotos = path.join(raiz, 'fotos');
  process.env.SIGAA_FOTOS_DIR = fotos;
  db = await dbDemo();
  app = await buildApp({ db, jwtSecret: 'test-secret', webDir: '/nonexistent' });
  await db('core_usuarios').update({ debe_cambiar: false });
  t = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'activos', clave: 'Activos2026' } })).json().token;
});
afterAll(async () => { await app.close(); await db.destroy(); delete process.env.SIGAA_FOTOS_DIR; });

describe('auditoría: subida de fotografías', () => {
  it('rechaza un número de foto manipulado y no escribe fuera de la carpeta', async () => {
    const cod = (await db('af_activos').first()).codigo;
    for (const n of ['..%2F..%2Fevil', '9', '0', 'x', '1%2F..%2Fz']) {
      const r = await app.inject({ method: 'PUT', url: `/api/af/activos/${encodeURIComponent(cod)}/foto/${n}`, headers: { ...H(), 'content-type': 'image/png' }, payload: PNG });
      expect(r.statusCode, n).toBe(422);
    }
    expect(fs.existsSync(path.join(raiz, 'evil_1.png'))).toBe(false);
    expect(fs.existsSync(fotos) ? fs.readdirSync(fotos) : []).toEqual([]);
  });
  it('solo acepta imágenes reales (por su contenido, no por lo que declare el cliente)', async () => {
    const cod = (await db('af_activos').first()).codigo;
    const falsa = await app.inject({ method: 'PUT', url: `/api/af/activos/${encodeURIComponent(cod)}/foto/1`, headers: { ...H(), 'content-type': 'image/png' }, payload: Buffer.from('<script>alert(1)</script>') });
    expect(falsa.statusCode).toBe(422);
    const ok = await app.inject({ method: 'PUT', url: `/api/af/activos/${encodeURIComponent(cod)}/foto/1`, headers: { ...H(), 'content-type': 'image/jpeg' }, payload: PNG });
    expect(ok.statusCode).toBe(200);
    expect(ok.json().archivo.endsWith('.png')).toBe(true); // el formato lo decide el contenido
  });
  it('un código con caracteres raros no puede salirse de la carpeta de fotos', async () => {
    await db('af_activos').where({ codigo: (await db('af_activos').first()).codigo }).update({ codigo: '../../x\\y' });
    const r = await app.inject({ method: 'PUT', url: `/api/af/activos/${encodeURIComponent('../../x\\y')}/foto/2`, headers: { ...H(), 'content-type': 'image/png' }, payload: PNG });
    expect(r.statusCode).toBe(200);
    expect(r.json().archivo).toMatch(/^[A-Za-z0-9._-]+$/);
    expect(fs.readdirSync(fotos).some((f) => f === r.json().archivo)).toBe(true);
  });
});

describe('auditoría: cabeceras', () => {
  it('la API no se guarda en caché y lleva cabeceras de seguridad', async () => {
    const r = await app.inject({ url: '/api/health' });
    expect(r.headers['x-content-type-options']).toBe('nosniff');
    expect(r.headers['x-frame-options']).toBe('SAMEORIGIN');
    const m = await app.inject({ url: '/api/auth/me', headers: H() });
    expect(m.headers['cache-control']).toBe('no-store');
  });
});

describe('auditoría: numeración de documentos', () => {
  it('operaciones simultáneas nunca reciben el mismo número', async () => {
    const { siguienteNro } = await import('../src/core/services.js');
    const nros = await Promise.all(Array.from({ length: 12 }, () => db.transaction((trx) => siguienteNro(trx, 'ZZT', 2026))));
    expect(new Set(nros).size).toBe(12);
    expect([...nros].sort()[0]).toBe('ZZT-0001/2026');
    expect([...nros].sort()[11]).toBe('ZZT-0012/2026');
    expect(await siguienteNro(db, 'ZZT', 2026)).toBe('ZZT-0013/2026');
  });
});

describe('auditoría: pasar a producción (vaciar datos de demostración)', () => {
  it('exige ser administrador y escribir ELIMINAR', async () => {
    const tadm = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'admin', clave: 'Admin2026' } })).json().token;
    expect((await app.inject({ method: 'POST', url: '/api/admin/produccion/vaciar', headers: H(), payload: { confirmar: 'ELIMINAR' } })).statusCode).toBe(403); // activos
    expect((await app.inject({ method: 'POST', url: '/api/admin/produccion/vaciar', headers: { authorization: `Bearer ${tadm}` }, payload: { confirmar: 'si' } })).statusCode).toBe(422);
    expect(Number((await db('af_activos').count({ n: '*' }).first() as any).n)).toBeGreaterThan(0);
  });
  it('conserva catálogos normativos y de la entidad, borra las operaciones y a los usuarios de demostración', async () => {
    const tadm = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'admin', clave: 'Admin2026' } })).json().token;
    const res = await app.inject({ method: 'GET', url: '/api/admin/produccion', headers: { authorization: `Bearer ${tadm}` } });
    expect(res.json().registros).toBeGreaterThan(0);
    const nFunc = Number((await db('core_funcionarios').count({ n: '*' }).first() as any).n);
    const r = await app.inject({ method: 'POST', url: '/api/admin/produccion/vaciar', headers: { authorization: `Bearer ${tadm}` }, payload: { confirmar: 'eliminar', conservarCatalogos: true } });
    expect(r.statusCode, r.body).toBe(200);
    if (process.env.TEST_DATABASE_URL) expect(r.json().respaldo).toBeNull(); // PostgreSQL: se respalda con pg_dump
    else { expect(r.json().respaldo).toMatch(/antes-de-produccion/); expect(fs.existsSync(r.json().respaldo)).toBe(true); }
    for (const t of ['af_activos', 'alm_ingresos', 'alm_lotes', 'com_vales', 'core_secuencias']) expect(Number((await db(t).count({ n: '*' }).first() as any).n), t).toBe(0);
    expect(Number((await db('core_funcionarios').count({ n: '*' }).first() as any).n)).toBe(nFunc);
    expect(Number((await db('af_cuentas').count({ n: '*' }).first() as any).n)).toBeGreaterThan(0);
    expect((await db('core_usuarios').select('usuario')).map((x: any) => x.usuario)).toEqual(['admin']);
    expect((await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'activos', clave: 'Activos2026' } })).statusCode).toBe(422);
    // el sistema sigue funcionando: la numeración vuelve a empezar
    const { siguienteNro } = await import('../src/core/services.js');
    expect(await siguienteNro(db, 'CGI', 2026)).toBe('CGI-0001/2026');
  });
  it('con la opción «quitar catálogos» también se vacían los de la entidad, pero no los normativos', async () => {
    const tadm = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'admin', clave: 'Admin2026' } })).json().token;
    const r = await app.inject({ method: 'POST', url: '/api/admin/produccion/vaciar', headers: { authorization: `Bearer ${tadm}` }, payload: { confirmar: 'ELIMINAR', conservarCatalogos: false } });
    expect(r.statusCode).toBe(200);
    for (const t of ['core_funcionarios', 'core_proveedores', 'af_edificios', 'com_vehiculos']) expect(Number((await db(t).count({ n: '*' }).first() as any).n), t).toBe(0);
    for (const t of ['af_cuentas', 'af_estados', 'alm_grupos', 'core_config']) expect(Number((await db(t).count({ n: '*' }).first() as any).n), t).toBeGreaterThan(0);
  });
});
