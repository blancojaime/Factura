import { connect } from '../src/db/connect.js';
import { seedAll } from '../src/db/seed.js';
import { TABLE_ORDER } from '../src/db/schema.js';
import type { Usuario } from '../src/core/context.js';

export const admin: Usuario = { usuario: 'admin', nombre: 'Administrador', roles: ['ADMIN'] };

/**
 * Base de pruebas: SQLite en memoria por defecto; con TEST_DATABASE_URL=postgres://... se prueba contra PostgreSQL
 * (ejecutar con --no-file-parallelism: cada archivo recrea el esquema).
 */
export async function dbDemo(demo = true) {
  const url = process.env.TEST_DATABASE_URL;
  const db = connect({ url: url || 'sqlite::memory:' });
  if (url) for (const t of [...TABLE_ORDER].reverse()) await db.schema.dropTableIfExists(t);
  await seedAll(db, { demo });
  return db;
}
