import type { Db, Usuario } from '../../core/context.js';
import { bitacora } from '../../core/services.js';
import { fail } from '../../core/errors.js';
import { txt } from '../../core/util.js';

export const bitacoraUsuario = (db: Db, u: Usuario, accion: string, doc: string, detalle: string) => bitacora(db, u, 'ALMACENES', accion, doc, detalle);

export async function bodegaNombre(db: Db, cod: string): Promise<string> {
  const r = await db('alm_bodegas').where({ cod }).first('nombre');
  return txt(r?.nombre);
}
export async function bodegaCod(db: Db, nombreOCod: string | undefined | null): Promise<string> {
  const v = txt(nombreOCod);
  if (!v) return '';
  const r = await db('alm_bodegas').where({ cod: v }).orWhere({ nombre: v }).first('cod');
  return txt(r?.cod);
}
export async function requerirBodega(db: Db, v: string | undefined | null): Promise<string> {
  const c = await bodegaCod(db, v);
  if (!c) fail('Seleccione una bodega válida.');
  return c;
}
export async function item(db: Db, cod: string) {
  return db('alm_catalogo').where({ codigo: cod }).first();
}
