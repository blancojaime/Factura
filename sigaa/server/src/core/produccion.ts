/**
 * Pasar a producción: elimina los datos de demostración (todas las operaciones registradas) para empezar con la base limpia.
 * Siempre se conservan: la configuración, el administrador y los catálogos NORMATIVOS (cuentas contables, estados, grupos de
 * materiales, causales, pasos y tipos de vehículo). Los catálogos propios de la entidad (funcionarios, proveedores,
 * aperturas, partidas, bodegas, vehículos, edificios…) se conservan o se eliminan según la opción elegida.
 */
import fs from 'node:fs';
import path from 'node:path';
import { isPg } from '../db/connect.js';
import { TABLE_ORDER } from '../db/schema.js';
import { nowIso } from './util.js';
import { USUARIOS_DEMO } from './auth.js';
import type { Db, Usuario } from './context.js';
import { fail } from './errors.js';
import { bitacora } from './services.js';

const SIEMPRE = new Set(['core_config', 'core_usuarios', 'af_cuentas', 'af_auxiliares', 'af_campos', 'af_estados', 'alm_grupos', 'alm_subgrupos', 'alm_unidades_medida', 'alm_causales', 'alm_pasos', 'alm_docreq', 'com_tipos', 'af_vsiaf_equiv']);
const CATALOGOS_ENTIDAD = new Set(['core_unidades', 'core_funcionarios', 'core_proveedores', 'core_proyectos', 'core_aperturas', 'core_partidas', 'alm_bodegas', 'alm_catalogo', 'alm_extintores', 'alm_seguros',
  'com_vehiculos', 'com_conductores', 'com_puestos', 'com_contratos', 'com_precios', 'af_edificios', 'af_ambientes']);

/** Tablas que se vacían según la opción (las operaciones siempre; los catálogos de la entidad solo si no se conservan). */
export function tablasAVaciar(conservarCatalogos: boolean): string[] {
  return [...TABLE_ORDER].reverse().filter((t) => !SIEMPRE.has(t) && (!CATALOGOS_ENTIDAD.has(t) || !conservarCatalogos));
}

/** Copia de la base antes de borrar (SQLite). Con PostgreSQL devuelve null: se debe hacer con pg_dump. */
export async function respaldoPrevio(db: Db, dir: string): Promise<string | null> {
  if (isPg(db)) return null;
  fs.mkdirSync(dir, { recursive: true });
  const base = `sigaa-antes-de-produccion-${nowIso().replace(/[ :]/g, '-')}`;
  let dest = path.join(dir, `${base}.sqlite`);
  for (let i = 2; fs.existsSync(dest); i++) dest = path.join(dir, `${base}-${i}.sqlite`);
  await db.raw(`VACUUM INTO '${dest.replace(/'/g, "''")}'`);
  return dest;
}

export async function resumenProduccion(db: Db) {
  const n = async (t: string) => Number((await db(t).count({ n: '*' }).first() as any)?.n ?? 0);
  const operaciones = (await Promise.all(tablasAVaciar(true).filter((t) => !['core_bitacora', 'core_secuencias'].includes(t)).map(n))).reduce((a, b) => a + b, 0);
  const demo = await db('core_usuarios').whereIn('usuario', USUARIOS_DEMO.map((u) => u.usuario)).count({ n: '*' }).first() as any;
  return { registros: operaciones, usuariosDemo: Number(demo?.n ?? 0), activos: await n('af_activos'), ingresos: await n('alm_ingresos'), vales: await n('com_vales') };
}

export async function vaciarDatosDemo(db: Db, u: Usuario, d: { confirmar?: string; conservarCatalogos?: boolean }) {
  if (String(d.confirmar ?? '').trim().toUpperCase() !== 'ELIMINAR') fail('Para continuar escriba la palabra ELIMINAR en el cuadro de confirmación.');
  const conservar = d.conservarCatalogos !== false;
  const tablas = tablasAVaciar(conservar);
  await db.transaction(async (trx) => {
    for (const t of tablas) await trx(t).delete();
    await trx('core_usuarios').whereIn('usuario', USUARIOS_DEMO.map((x) => x.usuario)).delete();
  });
  await bitacora(db, u, 'SEGURIDAD', 'PASO A PRODUCCIÓN', '', `Datos de demostración eliminados (${tablas.length} tablas; catálogos de la entidad ${conservar ? 'conservados' : 'eliminados'})`);
  return { ok: true, tablas: tablas.length, conservarCatalogos: conservar };
}
