import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { dbDemo } from './helpers.js';
import { buildApp } from '../src/app.js';
import { crearUsuario } from '../src/core/auth.js';

let app: FastifyInstance;
let db: Awaited<ReturnType<typeof dbDemo>>;
let admin = '';
const H = (t: string) => ({ authorization: `Bearer ${t}` });

async function login(usuario: string, clave: string) {
  const r = await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario, clave } });
  return { status: r.statusCode, body: r.json() as any };
}

beforeAll(async () => {
  db = await dbDemo();
  app = await buildApp({ db, jwtSecret: 'test-secret', webDir: '/nonexistent' });
  await crearUsuario(db, { usuario: 'consulta', nombre: 'Consulta', roles: ['CONSULTA'], clave: 'Consulta2026' });
  await crearUsuario(db, { usuario: 'almacen', nombre: 'Almacén', roles: ['ALMACEN'], clave: 'Almacen2026' });
});
afterAll(async () => {
  await app.close();
  await db.destroy();
});

describe('seguridad', () => {
  it('rechaza solicitudes sin sesión', async () => {
    expect((await app.inject({ url: '/api/dashboard' })).statusCode).toBe(401);
  });
  it('rechaza credenciales inválidas', async () => {
    expect((await login('admin', 'xxx')).status).toBe(422);
  });
  it('obliga a cambiar la clave inicial', async () => {
    const l = await login('admin', 'Admin2026');
    expect(l.status).toBe(200);
    expect(l.body.debeCambiar).toBe(true);
    const bloq = await app.inject({ url: '/api/dashboard', headers: H(l.body.token) });
    expect(bloq.statusCode).toBe(403);
    const mala = await app.inject({ method: 'POST', url: '/api/auth/cambiar-clave', headers: H(l.body.token), payload: { actual: 'Admin2026', nueva: 'corta' } });
    expect(mala.statusCode).toBe(422);
    const ok = await app.inject({ method: 'POST', url: '/api/auth/cambiar-clave', headers: H(l.body.token), payload: { actual: 'Admin2026', nueva: 'NuevaClave2026' } });
    expect(ok.statusCode).toBe(200);
    admin = ok.json().token;
    expect((await app.inject({ url: '/api/dashboard', headers: H(admin) })).statusCode).toBe(200);
  });
  it('los roles limitan la escritura por módulo', async () => {
    // el usuario debe cambiar su clave inicial: se simula quitando la bandera
    await db('core_usuarios').update({ debe_cambiar: false });
    const c = (await login('consulta', 'Consulta2026')).body.token;
    const a = (await login('almacen', 'Almacen2026')).body.token;
    const payloadVale = { cantidades: {} };
    expect((await app.inject({ method: 'POST', url: '/api/com/emisiones', headers: H(c), payload: payloadVale })).statusCode).toBe(403);
    expect((await app.inject({ method: 'POST', url: '/api/com/emisiones', headers: H(a), payload: payloadVale })).statusCode).toBe(403); // ALMACEN no escribe en combustible
    const r = await app.inject({ method: 'POST', url: '/api/alm/catalogo', headers: H(a), payload: { grupo: 1, subgrupo: 2, descripcion: 'regla 30 cm', unidad: 'UNIDAD', cod_bod: '01', precio_ref: 2 } });
    expect(r.statusCode).toBe(200);
    expect(r.json().codigo).toMatch(/^1-2-\d{7}$/);
    expect((await app.inject({ url: '/api/usuarios', headers: H(a) })).statusCode).toBe(403);
  });
});

describe('API de los tres módulos', () => {
  let t = '';
  beforeAll(async () => {
    t = (await login('almacen', 'Almacen2026')).body.token;
    await db('core_usuarios').where({ usuario: 'admin' }).update({ debe_cambiar: false });
    admin = (await login('admin', 'NuevaClave2026')).body.token;
  });
  it('tablero unificado con alertas', async () => {
    const r = (await app.inject({ url: '/api/dashboard', headers: H(admin) })).json();
    expect(r.almacenes.items).toBeGreaterThan(30);
    expect(r.activos.total).toBe(48);
    expect(r.combustible.mensual).toHaveLength(12);
    expect(Array.isArray(r.alertas)).toBe(true);
  });
  it('devuelve errores de negocio como 422 con mensaje', async () => {
    const r = await app.inject({ method: 'POST', url: '/api/alm/ingresos', headers: H(t), payload: { fecha: '2026-10-01', cod_bod: '01', tipo: 'CAJA CHICA', items: [] } });
    expect(r.statusCode).toBe(422);
    expect(r.json().error).toMatch(/factura/i);
  });
  it('lista catálogos maestros con metadatos y valida los datos', async () => {
    const meta = (await app.inject({ url: '/api/maestros', headers: H(t) })).json();
    expect(meta.length).toBeGreaterThanOrEqual(25);
    const l = (await app.inject({ url: '/api/maestros/vehiculos', headers: H(t) })).json();
    expect(l.length).toBe(4);
    const mal = await app.inject({ method: 'POST', url: '/api/maestros/bodegas', headers: H(t), payload: { cod: '09' } });
    expect(mal.statusCode).toBe(422);
    const ok = await app.inject({ method: 'POST', url: '/api/maestros/bodegas', headers: H(t), payload: { cod: '09', nombre: 'BODEGA NUEVA' } });
    expect(ok.statusCode).toBe(200);
    const enUso = await app.inject({ method: 'DELETE', url: '/api/maestros/bodegas/01', headers: H(t) });
    expect(enUso.statusCode).toBe(422);
    expect((await app.inject({ method: 'DELETE', url: '/api/maestros/bodegas/09', headers: H(t) })).statusCode).toBe(200);
    // un usuario de almacén no puede modificar catálogos de combustible
    expect((await app.inject({ method: 'POST', url: '/api/maestros/precios', headers: H(t), payload: { combustible: 'Diésel', precio: 9, vigente_desde: '2026-10-01' } })).statusCode).toBe(403);
  });
  it('no expone tablas de seguridad por la lista de valores', async () => {
    expect((await app.inject({ url: '/api/ref/core_usuarios.clave_hash', headers: H(t) })).statusCode).toBe(404);
    expect((await app.inject({ url: '/api/ref/core_unidades.nombre', headers: H(t) })).statusCode).toBe(200);
  });
  it('sirve reportes en JSON, PDF y Excel', async () => {
    const j = await app.inject({ url: '/api/reportes/alm-inventario?formato=json', headers: H(t) });
    expect(j.json().filas.length).toBeGreaterThan(10);
    const p = await app.inject({ url: '/api/reportes/alm-inventario?formato=pdf', headers: H(t) });
    expect(p.headers['content-type']).toBe('application/pdf');
    expect(p.rawPayload.subarray(0, 4).toString()).toBe('%PDF');
    const x = await app.inject({ url: '/api/reportes/af-inventario-general?formato=xlsx', headers: H(t) });
    expect(x.headers['content-type']).toContain('spreadsheetml');
    // token por query para abrir en una pestaña nueva
    const tok = await app.inject({ url: `/api/reportes/alm-catalogo?formato=pdf&access_token=${t}` });
    expect(tok.statusCode).toBe(200);
  });
  it('sirve documentos PDF y registra la impresión', async () => {
    const r = await app.inject({ url: '/api/documentos/alm-cgi?ref=CGI-0001%2F2026', headers: H(t) });
    expect(r.statusCode).toBe(200);
    expect(r.rawPayload.subarray(0, 4).toString()).toBe('%PDF');
    const bit = await app.inject({ url: '/api/bitacora?modulo=ALMACENES&limite=5', headers: H(admin) });
    expect(bit.json()[0].accion).toBe('IMPRESIÓN');
    expect((await app.inject({ url: '/api/documentos/alm-cgi', headers: H(t) })).statusCode).toBe(422);
  });
  it('flujo de salida de almacén por HTTP', async () => {
    const g = await app.inject({ method: 'POST', url: '/api/alm/salidas', headers: H(t), payload: { fecha_pedido: '2026-10-05', cod_bod: '02', unidad: 'UNIDAD DE OBRAS PÚBLICAS', solicitante: 'LUCIANA CRUZ VARGAS', superior: 'PEDRO APAZA ROJAS', justificacion: 'x', items: [{ cod_item: '3-1-0000002', cant_pedida: 2 }] } });
    expect(g.statusCode).toBe(200);
    const n = encodeURIComponent(g.json().nro);
    expect((await app.inject({ method: 'POST', url: `/api/alm/salidas/${n}/entregar`, headers: H(t) })).statusCode).toBe(422);
    expect((await app.inject({ method: 'POST', url: `/api/alm/salidas/${n}/aprobar-entregar`, headers: H(t) })).statusCode).toBe(200);
    const d = (await app.inject({ url: `/api/alm/salidas/${n}`, headers: H(t) })).json();
    expect(d.estado).toBe('ENTREGADO');
    expect(d.total).toBeGreaterThan(0);
  });
  it('conteo ciego oculta el saldo del sistema mientras se cuenta', async () => {
    const i = await app.inject({ method: 'POST', url: '/api/alm/inventarios', headers: H(t), payload: { fecha: '2026-10-06', cod_bod: '02', tipo: 'SORPRESIVO' } });
    const n = encodeURIComponent(i.json().nro);
    const d = (await app.inject({ url: `/api/alm/inventarios/${n}`, headers: H(t) })).json();
    expect(d.items[0].saldo_sist).toBeNull();
  });
  it('respaldo de la base de datos (solo ADMIN)', async () => {
    expect((await app.inject({ url: '/api/backup', headers: H(t) })).statusCode).toBe(403);
    const r = await app.inject({ url: '/api/backup', headers: H(admin) });
    if (process.env.TEST_DATABASE_URL) return expect(r.statusCode).toBe(422); // PostgreSQL: se usa pg_dump
    expect(r.statusCode).toBe(200);
    expect(r.rawPayload.subarray(0, 15).toString()).toBe('SQLite format 3');
  });
});
