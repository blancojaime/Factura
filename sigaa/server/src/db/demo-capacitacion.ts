/**
 * Crea la base de datos DEMOSTRATIVA para capacitación (datos de ejemplo de la entidad "Calamarca" + activos listos para practicar
 * el revalúo técnico). Uso:  npm run base:demo -w server -- ../distribucion/SIGAA_Base_Demostrativa_Capacitacion.sqlite
 * La base de DISTRIBUCIÓN (para clientes) es la vacía: npm run seed:vacia.
 */
import fs from 'node:fs';
import path from 'node:path';
import { connect } from './connect.js';
import { seedAll } from './seed.js';

const destino = path.resolve(process.argv[2] || 'SIGAA_Base_Demostrativa_Capacitacion.sqlite');
for (const x of ['', '-wal', '-shm', '-journal']) fs.rmSync(destino + x, { force: true });
fs.mkdirSync(path.dirname(destino), { recursive: true });
const db = connect({ url: `sqlite:${destino}` });
await seedAll(db, { demo: true });
// Activos para practicar el revalúo: 14 totalmente depreciados (Bs 1) de varias cuentas, con estados Bueno/Regular/Malo,
// más un caso NO operativo y uno en estado Nuevo (no elegibles) para mostrar el filtro de la bandeja.
const cods: string[] = (await db('af_activos').where('situacion', '!=', 'BAJA').orderBy(['id_cta', 'id_aux', 'codigo']).select('codigo')).map((r: any) => r.codigo);
const paso = Math.max(1, Math.floor(cods.length / 16));
const elegidos = cods.filter((_, i) => i % paso === 0).slice(0, 16);
const estados = ['Bueno', 'Regular', 'Malo'];
for (const [i, c] of elegidos.entries()) {
  const upd: Record<string, unknown> = { valor_libros: 1, estado: estados[i % 3], operativo: 'SI' };
  if (i === 14) upd.operativo = 'NO';
  if (i === 15) upd.estado = 'Nuevo';
  await db('af_activos').where({ codigo: c }).update(upd);
}
await db('core_usuarios').update({ debe_cambiar: false });
await db.raw('PRAGMA wal_checkpoint(TRUNCATE)');
await db.destroy();
for (const x of ['-wal', '-shm']) fs.rmSync(destino + x, { force: true });
console.log(`Base demostrativa creada: ${destino} (${elegidos.length} activos preparados para el revalúo)`);
