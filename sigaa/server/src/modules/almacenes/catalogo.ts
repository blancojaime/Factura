import type { Db, Usuario } from '../../core/context.js';
import { Errores, fail, NotFound } from '../../core/errors.js';
import { nowIso, num, txt } from '../../core/util.js';
import { cfg } from '../../core/services.js';
import { bitacoraUsuario, requerirBodega } from './helpers.js';
import { stockDe } from './stock.js';

export interface ItemInput {
  codigo?: string;
  grupo: number;
  subgrupo: number;
  descripcion: string;
  unidad: string;
  partida?: string;
  cod_bod: string;
  stock_min?: number;
  stock_max?: number;
  perecible?: string;
  peligroso?: string;
  ubicacion?: string;
  precio_ref?: number;
  estado?: string;
}

/** Código del ítem: Grupo-Subgrupo-Correlativo (7 dígitos), p. ej. 1-2-0000003. */
export async function armarCodigo(db: Db, grupo: number, sub: number, corr: number): Promise<string> {
  const sep = (await cfg(db, 'SepCodigoAlm', '-')) || '-';
  return `${grupo}${sep}${sub}${sep}${String(corr).padStart(7, '0')}`;
}

export async function proximoCorrelativo(db: Db, grupo: number, sub: number): Promise<number> {
  const r = await db('alm_catalogo').where({ grupo, subgrupo: sub }).max({ m: 'correlativo' }).first();
  return num(r?.m) + 1;
}

export async function guardarItem(db: Db, u: Usuario, d: ItemInput) {
  const e = new Errores();
  e.add(!d.grupo || !d.subgrupo, 'Seleccione el subgrupo (grupo-subgrupo).');
  e.add(!txt(d.descripcion), 'Registre la descripción específica del ítem.');
  e.add(!txt(d.unidad), 'Seleccione la unidad de medida.');
  e.add(num(d.stock_min) < 0 || num(d.stock_max) < 0, 'Los stocks mínimo y máximo no pueden ser negativos.');
  e.add(num(d.stock_max) > 0 && num(d.stock_min) > num(d.stock_max), 'El stock mínimo no puede ser mayor que el máximo.');
  e.throwIfAny('Datos del ítem incompletos:');
  const bod = await requerirBodega(db, d.cod_bod);
  if (!(await db('alm_subgrupos').where({ grupo: d.grupo, subgrupo: d.subgrupo }).first())) fail('El subgrupo no existe.');
  const desc = txt(d.descripcion).toUpperCase();
  return db.transaction(async (trx) => {
    const dup = await trx('alm_catalogo').whereRaw('upper(descripcion) = ?', [desc]).andWhere({ cod_bod: bod }).modify((q) => d.codigo && q.whereNot({ codigo: d.codigo })).first();
    if (dup) fail(`Ya existe un ítem con esa descripción en la bodega (${dup.codigo}).`);
    const base = {
      descripcion: desc,
      unidad: txt(d.unidad).toUpperCase(),
      partida: txt(d.partida),
      cod_bod: bod,
      stock_min: num(d.stock_min),
      stock_max: num(d.stock_max),
      perecible: txt(d.perecible) === 'SI' ? 'SI' : 'NO',
      peligroso: txt(d.peligroso) === 'SI' ? 'SI' : 'NO',
      ubicacion: txt(d.ubicacion),
      precio_ref: num(d.precio_ref),
      estado: txt(d.estado) === 'INACTIVO' ? 'INACTIVO' : 'ACTIVO',
    };
    if (d.codigo) {
      const ex = await trx('alm_catalogo').where({ codigo: d.codigo }).first();
      if (!ex) throw new NotFound('El ítem no existe.');
      await trx('alm_catalogo').where({ codigo: d.codigo }).update(base);
      await bitacoraUsuario(trx, u, 'MODIFICACIÓN DE ÍTEM', d.codigo, desc);
      return { codigo: d.codigo };
    }
    const corr = await proximoCorrelativo(trx, d.grupo, d.subgrupo);
    const codigo = await armarCodigo(trx, d.grupo, d.subgrupo, corr);
    await trx('alm_catalogo').insert({ codigo, grupo: d.grupo, subgrupo: d.subgrupo, correlativo: corr, ...base, fecha_reg: nowIso() });
    await bitacoraUsuario(trx, u, 'ALTA DE ÍTEM', codigo, desc);
    return { codigo };
  });
}

export async function listarCatalogo(db: Db, f: { bod?: string; q?: string; estado?: string; subgrupo?: string } = {}) {
  const q = db('alm_catalogo as c')
    .leftJoin('alm_bodegas as b', 'b.cod', 'c.cod_bod')
    .leftJoin(
      db('alm_lotes').where({ estado: 'ACTIVO' }).groupBy('cod_item').select('cod_item').sum({ existencia: 'saldo' }).as('s'),
      's.cod_item',
      'c.codigo',
    )
    .select('c.*', 'b.nombre as bodega', db.raw('coalesce(s.existencia, 0) as existencia'))
    .orderBy('c.codigo');
  if (f.bod) q.where('c.cod_bod', f.bod);
  if (f.estado) q.where('c.estado', f.estado);
  if (f.subgrupo) {
    const [g, s] = f.subgrupo.split('-').map(Number);
    q.where('c.grupo', g).where('c.subgrupo', s);
  }
  if (f.q) {
    const like = `%${f.q.toUpperCase()}%`;
    q.where((w) => w.whereRaw('upper(c.descripcion) like ?', [like]).orWhere('c.codigo', 'like', `%${f.q}%`));
  }
  return q;
}

export async function obtenerItem(db: Db, codigo: string) {
  const it = await db('alm_catalogo').where({ codigo }).first();
  if (!it) throw new NotFound('El ítem no existe.');
  return { ...it, existencia: await stockDe(db, '', codigo) };
}
