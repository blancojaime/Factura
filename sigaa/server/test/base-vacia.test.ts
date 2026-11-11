import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { connect } from '../src/db/connect.js';
import { seedAll } from '../src/db/seed.js';
import { TABLE_ORDER } from '../src/db/schema.js';
import { buildApp } from '../src/app.js';
import { tablasAVaciar } from '../src/core/produccion.js';

let db: ReturnType<typeof connect>;
let app: FastifyInstance;
beforeAll(async () => {
  const url = process.env.TEST_DATABASE_URL;
  db = connect({ url: url || 'sqlite::memory:' });
  if (url) for (const t of [...TABLE_ORDER].reverse()) await db.schema.dropTableIfExists(t);
  await seedAll(db, { demo: false });
  app = await buildApp({ db, jwtSecret: 'test-secret', webDir: '/nonexistent' });
});
afterAll(async () => { await app.close(); });

describe('Base de datos vacía para distribución', () => {
  it('no trae ningún dato operativo ni catálogo de la entidad', async () => {
    for (const t of tablasAVaciar(false)) {
      if (['core_bitacora', 'core_secuencias'].includes(t)) continue;
      expect(await db(t).first(), `la tabla ${t} debe estar vacía`).toBeUndefined();
    }
    expect((await db('core_usuarios')).map((u: any) => u.usuario)).toEqual(['admin']); // sin usuarios demo
  });
  it('trae los catálogos normativos (cuentas, estados, grupos, causales, tipos de vehículo)', async () => {
    for (const t of ['af_cuentas', 'af_auxiliares', 'af_campos', 'af_estados', 'alm_grupos', 'alm_subgrupos', 'alm_unidades_medida', 'alm_causales', 'alm_pasos', 'alm_docreq', 'com_tipos'])
      expect(Number((await db(t).count({ n: '*' }).first() as any).n), t).toBeGreaterThan(0);
    const est = (await db('af_estados')).map((e: any) => e.estado);
    for (const e of ['Bueno', 'Regular', 'Malo']) expect(est).toContain(e);
  });
  it('la configuración no trae los datos de la entidad de demostración', async () => {
    const c = Object.fromEntries((await db('core_config')).map((r: any) => [r.clave, r.valor]));
    expect(c.Entidad).toMatch(/NOMBRE DE LA ENTIDAD/);
    expect(JSON.stringify(c)).not.toMatch(/CALAMARCA|CALLISAYA|MAMANI APAZA/i);
    expect(c.NombreMAE).toBe(''); expect(c.CargoMAE).toBeTruthy();
    expect(c.ValorMinimo).toBe('500'); // los parámetros técnicos se conservan
  });
  it('el administrador entra con clave inicial y debe cambiarla; el sistema responde vacío', async () => {
    const l = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'admin', clave: 'Admin2026' } });
    expect(l.statusCode).toBe(200);
    expect(l.json().debeCambiar).toBe(true);
    await db('core_usuarios').update({ debe_cambiar: false });
    const t = (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario: 'admin', clave: 'Admin2026' } })).json().token;
    const h = { authorization: `Bearer ${t}` };
    expect((await app.inject({ method: 'GET', url: '/api/af/revaluo/bandeja', headers: h })).json()).toEqual([]);
    expect((await app.inject({ method: 'GET', url: '/api/af/revaluo/lotes', headers: h })).json()).toEqual([]);
    expect((await app.inject({ method: 'GET', url: '/api/af/meta', headers: h })).json().cuentas.length).toBeGreaterThan(0);
  });
  it('arrancar de nuevo sobre la base con datos no la reinicia ni duplica catálogos', async () => {
    const antes = Number((await db('af_cuentas').count({ n: '*' }).first() as any).n);
    await seedAll(db, { demo: false });
    expect(Number((await db('af_cuentas').count({ n: '*' }).first() as any).n)).toBe(antes);
  });
});
