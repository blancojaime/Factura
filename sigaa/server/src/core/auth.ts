import crypto from 'node:crypto';
import type { Db, Usuario } from './context.js';
import { ROLES } from './context.js';
import { BusinessError, fail } from './errors.js';
import { nowIso } from './util.js';

const N = 16384;
export function hashClave(clave: string): string {
  const salt = crypto.randomBytes(16).toString('hex');
  const h = crypto.scryptSync(clave, salt, 32, { N }).toString('hex');
  return `scrypt$${salt}$${h}`;
}
export function verificarClave(clave: string, guardada: string): boolean {
  const [alg, salt, h] = guardada.split('$');
  if (alg !== 'scrypt' || !salt || !h) return false;
  const calc = crypto.scryptSync(clave, salt, 32, { N });
  const real = Buffer.from(h, 'hex');
  return calc.length === real.length && crypto.timingSafeEqual(calc, real);
}

export function validarClaveNueva(clave: string) {
  if (clave.length < 8) fail('La clave debe tener al menos 8 caracteres.');
  if (!/[A-Za-z]/.test(clave) || !/\d/.test(clave)) fail('La clave debe combinar letras y números.');
}

/** Bloqueo temporal tras intentos fallidos (en memoria del proceso): 5 intentos → 15 minutos. */
const MAX_INTENTOS = 5;
const BLOQUEO_MS = 15 * 60 * 1000;
const fallos = new Map<string, { n: number; hasta: number }>();
export const reiniciarBloqueos = () => fallos.clear();

export async function autenticar(db: Db, usuario: string, clave: string): Promise<{ user: Usuario; debeCambiar: boolean }> {
  const k = usuario.trim().toLowerCase();
  const f = fallos.get(k);
  if (f && f.hasta > Date.now()) throw new BusinessError(`Usuario bloqueado por intentos fallidos. Reintente en ${Math.ceil((f.hasta - Date.now()) / 60000)} minuto(s) o pida al administrador restablecer la clave.`);
  const r = await db('core_usuarios').whereRaw('lower(usuario) = ?', [k]).first();
  if (!r || r.estado !== 'ACTIVO' || !verificarClave(clave, r.clave_hash)) {
    const n = (f && f.hasta <= Date.now() && f.hasta > 0 ? 0 : f?.n ?? 0) + 1;
    fallos.set(k, { n, hasta: n >= MAX_INTENTOS ? Date.now() + BLOQUEO_MS : 0 });
    throw new BusinessError('Usuario o clave incorrectos.');
  }
  fallos.delete(k);
  await db('core_usuarios').where({ usuario: r.usuario }).update({ ultimo_acceso: nowIso() });
  return {
    user: { usuario: r.usuario, nombre: r.nombre, roles: String(r.roles).split(',').map((s: string) => s.trim()) },
    debeCambiar: !!r.debe_cambiar,
  };
}

export async function cambiarClave(db: Db, usuario: string, actual: string, nueva: string) {
  const r = await db('core_usuarios').where({ usuario }).first();
  if (!r || !verificarClave(actual, r.clave_hash)) fail('La clave actual no es correcta.');
  validarClaveNueva(nueva);
  await db('core_usuarios').where({ usuario }).update({ clave_hash: hashClave(nueva), debe_cambiar: false });
}

export async function crearUsuario(db: Db, d: { usuario: string; nombre: string; roles: string[]; clave: string }) {
  if (!/^[a-z0-9._-]{3,40}$/i.test(d.usuario)) fail('El usuario debe tener 3-40 caracteres (letras, números, . _ -).');
  for (const r of d.roles) if (!(ROLES as readonly string[]).includes(r)) fail(`Rol desconocido: ${r}`);
  validarClaveNueva(d.clave);
  if (await db('core_usuarios').where({ usuario: d.usuario }).first()) fail('El usuario ya existe.');
  await db('core_usuarios').insert({
    usuario: d.usuario,
    nombre: d.nombre,
    roles: d.roles.join(','),
    estado: 'ACTIVO',
    debe_cambiar: true,
    clave_hash: hashClave(d.clave),
  });
}

/** Garantiza que exista el usuario administrador inicial (clave por defecto que debe cambiarse al ingresar). */
export async function asegurarAdmin(db: Db) {
  const n = await db('core_usuarios').count({ n: '*' }).first();
  if (Number(n?.n) === 0) {
    const clave = process.env.SIGAA_ADMIN_PASSWORD || 'Admin2026';
    await db('core_usuarios').insert({
      usuario: 'admin',
      nombre: 'Administrador del sistema',
      roles: 'ADMIN',
      estado: 'ACTIVO',
      debe_cambiar: true,
      clave_hash: hashClave(clave),
    });
  }
}
