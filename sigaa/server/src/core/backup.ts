import fs from 'node:fs';
import path from 'node:path';
import type { Knex } from 'knex';
import { isPg } from '../db/connect.js';

/** Copia diaria automática de SQLite (VACUUM INTO) con retención de N días. PostgreSQL: usar pg_dump. */
export async function respaldar(db: Knex, dir: string, retener = 14): Promise<string | null> {
  if (isPg(db)) return null;
  fs.mkdirSync(dir, { recursive: true });
  const hoy = new Date().toISOString().slice(0, 10);
  const dest = path.join(dir, `sigaa-${hoy}.sqlite`);
  if (fs.existsSync(dest)) return null;
  await db.raw(`VACUUM INTO '${dest.replace(/'/g, "''")}'`);
  const viejos = fs.readdirSync(dir).filter((f) => /^sigaa-\d{4}-\d{2}-\d{2}\.sqlite$/.test(f)).sort().slice(0, -retener);
  for (const f of viejos) fs.unlinkSync(path.join(dir, f));
  return dest;
}

export function programarRespaldo(db: Knex, dir: string, log: (m: string) => void = console.log) {
  const hacer = () => respaldar(db, dir).then((d) => d && log(`Copia de seguridad: ${d}`)).catch((e) => log('Falló la copia automática: ' + e.message));
  void hacer();
  const t = setInterval(hacer, 6 * 3600 * 1000);
  t.unref();
}
