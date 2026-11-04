/** Logo de la entidad: se sube desde la PC y se inserta en todos los reportes y documentos (PDF y Excel). */
import fs from 'node:fs';
import path from 'node:path';
import type { Db, Usuario } from './context.js';
import { fail } from './errors.js';
import { bitacora, cfg, setCfg } from './services.js';

export const LOGO_DIR = () => process.env.SIGAA_LOGO_DIR || path.join(path.dirname(process.env.SIGAA_FOTOS_DIR || path.resolve(process.cwd(), 'data/fotos')), 'logo');
export const LOGO_MAX = 3 * 1024 * 1024;

/** Detecta el formato por los primeros bytes (no se confía en la extensión ni en el tipo declarado). */
export function formatoImagen(b: Buffer): 'png' | 'jpg' | null {
  if (b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'png';
  if (b.length > 4 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'jpg';
  return null;
}

export async function rutaLogo(db: Db): Promise<string> {
  const r = (await cfg(db, 'Logo')).trim();
  return r && fs.existsSync(r) ? r : '';
}

export async function guardarLogo(db: Db, u: Usuario, buf: unknown) {
  if (!Buffer.isBuffer(buf) || !buf.length) fail('Seleccione una imagen del logo (JPG o PNG).');
  if (buf.length > LOGO_MAX) fail('El logo supera 3 MB. Use una imagen más liviana.');
  const ext = formatoImagen(buf);
  if (!ext) fail('El archivo no es una imagen JPG o PNG válida.');
  fs.mkdirSync(LOGO_DIR(), { recursive: true });
  for (const e of ['png', 'jpg']) fs.rmSync(path.join(LOGO_DIR(), `logo.${e}`), { force: true });
  const ruta = path.join(LOGO_DIR(), `logo.${ext}`);
  fs.writeFileSync(ruta, buf);
  await setCfg(db, 'Logo', ruta);
  await bitacora(db, u, 'SEGURIDAD', 'LOGO', '', `Logo cargado (${ext}, ${Math.round(buf.length / 1024)} KB)`);
  return { ruta };
}

export async function quitarLogo(db: Db, u: Usuario) {
  const actual = (await cfg(db, 'Logo')).trim();
  if (actual && path.dirname(actual) === LOGO_DIR()) fs.rmSync(actual, { force: true });
  await setCfg(db, 'Logo', '');
  await bitacora(db, u, 'SEGURIDAD', 'LOGO', '', 'Logo quitado');
}
