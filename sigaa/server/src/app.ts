import Fastify, { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import fastifyJwt from '@fastify/jwt';
import fastifyStatic from '@fastify/static';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import type { Knex } from 'knex';
import { BusinessError, Forbidden, fail } from './core/errors.js';
import { Modulo, Usuario, ROLES, esAdmin, puedeEscribir } from './core/context.js';
import { autenticar, cambiarClave, crearUsuario, hashClave, validarClaveNueva } from './core/auth.js';
import { cfgAll, gestion, setCfg, bitacora } from './core/services.js';
import { dateOnly, txt, today } from './core/util.js';
import { isPg } from './db/connect.js';
import { registerAlmacenes } from './routes/almacenes.js';
import { registerCombustible } from './routes/combustible.js';
import { registerActivos } from './routes/activos.js';
import { registerCatalogos } from './routes/catalogos.js';
import { dashboardAlm } from './modules/almacenes/dashboard.js';
import { tablero } from './modules/combustible/otros.js';
import { resumenVales } from './modules/combustible/vales.js';
import { indicadoresAF } from './modules/activos/service.js';
import { DEFAULT_CONFIG } from './db/defaults.js';

declare module 'fastify' {
  interface FastifyRequest {
    usuario: Usuario;
  }
}
declare module '@fastify/jwt' {
  interface FastifyJWT {
    payload: { u: string; n: string; r: string[]; dc?: boolean };
    user: { u: string; n: string; r: string[]; dc?: boolean };
  }
}

export interface AppOptions {
  db: Knex;
  jwtSecret?: string;
  webDir?: string;
  logger?: boolean;
}

export type Ctx = { db: Knex; app: FastifyInstance; w: (m: Modulo) => (req: FastifyRequest) => Promise<void> };

export async function buildApp(opts: AppOptions): Promise<FastifyInstance> {
  const { db } = opts;
  const app = Fastify({ logger: opts.logger ?? false, bodyLimit: 12 * 1024 * 1024 });
  const secret = opts.jwtSecret || process.env.SIGAA_JWT_SECRET || crypto.randomBytes(32).toString('hex');
  await app.register(fastifyJwt, { secret, sign: { expiresIn: '10h' } });

  app.addContentTypeParser(/^image\/.*/, { parseAs: 'buffer' }, (_req, body, done) => done(null, body));

  app.setErrorHandler((err: any, req, reply) => {
    if (err instanceof BusinessError) return reply.code(err.status).send({ error: err.message });
    if (err.validation || err.statusCode === 400) return reply.code(400).send({ error: err.message });
    if (err.statusCode && err.statusCode < 500) return reply.code(err.statusCode).send({ error: err.message });
    req.log.error(err);
    return reply.code(500).send({ error: 'Error interno del servidor. Revise el registro del sistema.' });
  });

  // ── Autenticación ──
  app.addHook('onRequest', async (req, reply) => {
    const url = req.url.split('?')[0];
    if (!url.startsWith('/api/') || url === '/api/auth/login' || url === '/api/health') return;
    // Los PDF/Excel/fotos se abren en pestañas nuevas: se admite el token por query (solo GET).
    const q = (req.query as any)?.access_token;
    if (q && req.method === 'GET') req.headers.authorization = `Bearer ${q}`;
    try {
      await req.jwtVerify();
    } catch {
      return reply.code(401).send({ error: 'Sesión no válida o expirada. Ingrese nuevamente.' });
    }
    const t = req.user;
    const fila = await db('core_usuarios').where({ usuario: t.u }).first('estado', 'roles', 'nombre');
    if (!fila || fila.estado !== 'ACTIVO') return reply.code(401).send({ error: 'El usuario ya no está activo.' });
    req.usuario = { usuario: t.u, nombre: fila.nombre, roles: String(fila.roles).split(',').map((s: string) => s.trim()) };
    if (t.dc && !url.startsWith('/api/auth/')) return reply.code(403).send({ error: 'Debe cambiar su clave antes de continuar.', cambiarClave: true });
  });

  const w = (m: Modulo) => async (req: FastifyRequest) => {
    if (!puedeEscribir(req.usuario, m)) throw new Forbidden(`Su rol (${req.usuario.roles.join(', ')}) no permite modificar este módulo.`);
  };
  const admin = async (req: FastifyRequest) => {
    if (!esAdmin(req.usuario)) throw new Forbidden('Se requiere un usuario ADMINISTRADOR.');
  };
  const ctx: Ctx = { db, app, w };

  app.get('/api/health', async () => ({ ok: true, fecha: today() }));

  // ── Sesión ──
  app.post('/api/auth/login', async (req) => {
    const b = req.body as { usuario?: string; clave?: string };
    if (!b?.usuario || !b?.clave) fail('Ingrese usuario y clave.');
    const { user, debeCambiar } = await autenticar(db, b.usuario, b.clave);
    const token = app.jwt.sign({ u: user.usuario, n: user.nombre, r: user.roles, dc: debeCambiar });
    await bitacora(db, user, 'SEGURIDAD', 'INICIO DE SESIÓN', user.usuario, '');
    return { token, usuario: user, debeCambiar, gestion: await gestion(db) };
  });
  app.get('/api/auth/me', async (req) => ({ usuario: req.usuario, gestion: await gestion(db), entidad: (await cfgAll(db)).Entidad }));
  app.post('/api/auth/cambiar-clave', async (req) => {
    const b = req.body as { actual?: string; nueva?: string };
    await cambiarClave(db, req.usuario.usuario, b?.actual ?? '', b?.nueva ?? '');
    await bitacora(db, req.usuario, 'SEGURIDAD', 'CAMBIO DE CLAVE', req.usuario.usuario, '');
    const token = app.jwt.sign({ u: req.usuario.usuario, n: req.usuario.nombre, r: req.usuario.roles, dc: false });
    return { ok: true, token };
  });

  // ── Administración ──
  app.get('/api/config', async () => {
    const rows = await db('core_config').orderBy(['modulo', 'clave']);
    return rows;
  });
  app.put('/api/config', { preHandler: admin }, async (req) => {
    const b = req.body as Record<string, string>;
    const validas = new Set(DEFAULT_CONFIG.map((c) => c.clave));
    for (const [k, v] of Object.entries(b)) {
      if (!validas.has(k)) continue;
      if (k === 'Gestion' && !/^\d{4}$/.test(String(v))) fail('La gestión debe tener 4 dígitos.');
      await setCfg(db, k, String(v ?? ''));
    }
    await bitacora(db, req.usuario, 'SEGURIDAD', 'CONFIGURACIÓN', '', Object.keys(b).join(', '));
    return { ok: true };
  });
  app.get('/api/usuarios', { preHandler: admin }, async () => db('core_usuarios').select('usuario', 'nombre', 'roles', 'estado', 'debe_cambiar', 'ultimo_acceso').orderBy('usuario'));
  app.post('/api/usuarios', { preHandler: admin }, async (req) => {
    const b = req.body as { usuario: string; nombre: string; roles: string[]; clave: string };
    await crearUsuario(db, { usuario: b.usuario, nombre: b.nombre, roles: b.roles ?? ['CONSULTA'], clave: b.clave });
    await bitacora(db, req.usuario, 'SEGURIDAD', 'ALTA DE USUARIO', b.usuario, (b.roles ?? []).join(','));
    return { ok: true };
  });
  app.put('/api/usuarios/:usuario', { preHandler: admin }, async (req) => {
    const { usuario } = req.params as { usuario: string };
    const b = req.body as { nombre?: string; roles?: string[]; estado?: string; clave?: string };
    const ex = await db('core_usuarios').where({ usuario }).first();
    if (!ex) fail('El usuario no existe.');
    const upd: Record<string, unknown> = {};
    if (b.nombre) upd.nombre = b.nombre;
    if (b.roles) {
      for (const r of b.roles) if (!(ROLES as readonly string[]).includes(r)) fail(`Rol desconocido: ${r}`);
      upd.roles = b.roles.join(',');
    }
    if (b.estado) upd.estado = b.estado === 'INACTIVO' ? 'INACTIVO' : 'ACTIVO';
    if (b.clave) {
      validarClaveNueva(b.clave);
      upd.clave_hash = hashClave(b.clave);
      upd.debe_cambiar = true;
    }
    if (usuario === req.usuario.usuario && (upd.estado === 'INACTIVO' || (upd.roles && !String(upd.roles).includes('ADMIN')))) fail('No puede quitarse a sí mismo el acceso de administrador.');
    await db('core_usuarios').where({ usuario }).update(upd);
    await bitacora(db, req.usuario, 'SEGURIDAD', 'MODIFICACIÓN DE USUARIO', usuario, Object.keys(upd).filter((k) => k !== 'clave_hash').join(','));
    return { ok: true };
  });
  app.get('/api/bitacora', { preHandler: admin }, async (req) => {
    const q = req.query as Record<string, string>;
    const qb = db('core_bitacora').orderBy('id', 'desc').limit(Math.min(Number(q.limite) || 300, 2000));
    if (q.modulo) qb.where({ modulo: q.modulo });
    if (q.usuario) qb.where({ usuario: q.usuario });
    if (dateOnly(q.desde)) qb.where('fecha', '>=', q.desde);
    if (dateOnly(q.hasta)) qb.where('fecha', '<=', q.hasta + ' 23:59:59');
    return qb;
  });
  app.get('/api/backup', { preHandler: admin }, async (req, reply) => {
    if (isPg(db)) fail('La copia de seguridad de PostgreSQL se realiza con pg_dump en el servidor de base de datos.');
    const tmp = path.join(process.env.TMPDIR || '/tmp', `sigaa-backup-${Date.now()}.sqlite`);
    await db.raw(`VACUUM INTO '${tmp.replace(/'/g, "''")}'`);
    const buf = fs.readFileSync(tmp);
    fs.unlinkSync(tmp);
    await bitacora(db, req.usuario, 'SEGURIDAD', 'COPIA DE SEGURIDAD', '', `${buf.length} bytes`);
    return reply.header('content-type', 'application/octet-stream').header('content-disposition', `attachment; filename="sigaa-respaldo-${today()}.sqlite"`).send(buf);
  });

  // ── Tablero general (los tres módulos) ──
  app.get('/api/dashboard', async () => {
    const [alm, com, vales, af] = await Promise.all([dashboardAlm(db), tablero(db), resumenVales(db), indicadoresAF(db)]);
    const alertas = [...alm.alertas];
    for (const t of vales.alertas) alertas.push({ modulo: 'com', nivel: 'aviso', texto: t, ruta: '/combustible/recepcion' });
    if (com.descargos_vencidos) alertas.push({ modulo: 'com', nivel: 'critico', texto: `${com.descargos_vencidos} descargo(s) de vales vencido(s) sin presentar.`, ruta: '/combustible/descargo' });
    if (af.stickers_pendientes) alertas.push({ modulo: 'af', nivel: 'info', texto: `${af.stickers_pendientes} activo(s) con sticker pendiente de impresión.`, ruta: '/activos/etiquetas' });
    if (af.sin_fotografia) alertas.push({ modulo: 'af', nivel: 'info', texto: `${af.sin_fotografia} activo(s) sin fotografía.`, ruta: '/activos/fichas' });
    if (af.solicitudes_pendientes) alertas.push({ modulo: 'af', nivel: 'aviso', texto: `${af.solicitudes_pendientes} solicitud(es) de activos pendiente(s).`, ruta: '/activos/solicitudes' });
    return { gestion: await gestion(db), almacenes: alm.indicadores, combustible: { ...com, vales: vales.lista }, activos: af, alertas };
  });

  await registerCatalogos(ctx);
  await registerAlmacenes(ctx);
  await registerCombustible(ctx);
  await registerActivos(ctx);

  // ── Aplicación web (SPA) ──
  const webDir = path.resolve(opts.webDir ?? path.resolve(process.cwd(), '../web/dist'));
  if (fs.existsSync(path.join(webDir, 'index.html'))) {
    await app.register(fastifyStatic, { root: webDir });
    app.setNotFoundHandler((req, reply) => {
      if (req.url.startsWith('/api/')) return reply.code(404).send({ error: 'Recurso no encontrado.' });
      return reply.sendFile('index.html');
    });
  } else {
    app.setNotFoundHandler((req, reply) => reply.code(404).send({ error: 'Recurso no encontrado.' }));
  }
  void txt;
  return app;
}

export const sendFile = (reply: FastifyReply, buf: Buffer, tipo: string, nombre: string, inline = true) =>
  reply.header('content-type', tipo).header('content-disposition', `${inline ? 'inline' : 'attachment'}; filename="${nombre}"`).send(buf);
