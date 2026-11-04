import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import AdmZip from 'adm-zip';
import type { FastifyInstance } from 'fastify';
import { dbDemo } from './helpers.js';
import { buildApp } from '../src/app.js';

// PNG de 1×1 y JPEG mínimo válidos
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==', 'base64');
const JPG = Buffer.from('/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=', 'base64');

let app: FastifyInstance;
let db: Awaited<ReturnType<typeof dbDemo>>;
let dir = '';
const H = (t: string) => ({ authorization: `Bearer ${t}` });
const login = async (u: string, c: string) => (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: u, clave: c } })).json().token as string;
const put = (t: string, body: Buffer, tipo = 'image/png') => app.inject({ method: 'PUT', url: '/api/config/logo', headers: { ...H(t), 'content-type': tipo }, payload: body });

beforeAll(async () => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'logo-'));
  process.env.SIGAA_LOGO_DIR = dir;
  db = await dbDemo();
  app = await buildApp({ db, jwtSecret: 'test-secret', webDir: '/nonexistent' });
  await db('core_usuarios').update({ debe_cambiar: false });
});
afterAll(async () => { await app.close(); await db.destroy(); delete process.env.SIGAA_LOGO_DIR; });

describe('logo de la entidad', () => {
  it('solo el administrador lo sube; valida que sea JPG/PNG de verdad', async () => {
    const ta = await login('activos', 'Activos2026'), tadm = await login('admin', 'Admin2026');
    expect((await put(ta, PNG)).statusCode).toBe(403);
    expect((await put(tadm, Buffer.from('esto no es una imagen'), 'image/png')).statusCode).toBe(422);
    expect((await put(tadm, Buffer.alloc(3.5 * 1024 * 1024, 0xff), 'image/jpeg')).statusCode).toBe(422);
    expect((await app.inject({ url: '/api/config/logo', headers: H(tadm) })).statusCode).toBe(404);
  });
  it('se guarda, se muestra y se reemplaza', async () => {
    const t = await login('admin', 'Admin2026');
    expect((await put(t, PNG)).statusCode).toBe(200);
    const g = await app.inject({ url: '/api/config/logo', headers: H(t) });
    expect(g.statusCode).toBe(200);
    expect(g.headers['content-type']).toContain('image/png');
    expect((await db('core_config').where({ clave: 'Logo' }).first()).valor).toBe(path.join(dir, 'logo.png'));
    expect((await put(t, JPG, 'image/jpeg')).statusCode).toBe(200);
    expect(fs.existsSync(path.join(dir, 'logo.png'))).toBe(false);
    expect((await app.inject({ url: '/api/config/logo', headers: H(t) })).headers['content-type']).toContain('image/jpeg');
  });
  it('aparece en los reportes de Excel y en los PDF', async () => {
    const t = await login('admin', 'Admin2026');
    await put(t, PNG);
    const x = await app.inject({ url: '/api/reportes/alm-catalogo?formato=xlsx', headers: H(t) });
    expect(x.statusCode, x.body.slice(0, 200)).toBe(200);
    const medias = new AdmZip(x.rawPayload).getEntries().map((e) => e.entryName).filter((n) => n.startsWith('xl/media/'));
    expect(medias.length).toBeGreaterThan(0);
    const sin = await app.inject({ url: '/api/reportes/alm-catalogo?formato=pdf&cod_bod=01', headers: H(t) });
    expect(sin.statusCode).toBe(200);
    expect(sin.rawPayload.toString('latin1')).toMatch(/\/Subtype \/Image/);
  });
  it('al quitarlo vuelve a no haber logo', async () => {
    const t = await login('admin', 'Admin2026');
    expect((await app.inject({ method: 'DELETE', url: '/api/config/logo', headers: H(t) })).statusCode).toBe(200);
    expect((await app.inject({ url: '/api/config/logo', headers: H(t) })).statusCode).toBe(404);
    const x = await app.inject({ url: '/api/reportes/alm-catalogo?formato=xlsx', headers: H(t) });
    expect(new AdmZip(x.rawPayload).getEntries().some((e) => e.entryName.startsWith('xl/media/'))).toBe(false);
  });
});
