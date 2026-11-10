/** ¿Puede este usuario ver y usar el envío/importación con el VSIAF? (opción «VsiafSoloAdmin» de la configuración) */
import type { Db, Usuario } from '../core/context.js';
import { cfg } from '../core/services.js';
import { esAdmin } from '../core/context.js';

export async function vsiafSoloAdmin(db: Db): Promise<boolean> {
  return (await cfg(db, 'VsiafSoloAdmin', 'NO')).trim().toUpperCase() === 'SI';
}
export async function vsiafVisible(db: Db, u: Usuario): Promise<boolean> {
  return esAdmin(u) || !(await vsiafSoloAdmin(db));
}
