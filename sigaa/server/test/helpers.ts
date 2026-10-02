import { connect } from '../src/db/connect.js';
import { seedAll } from '../src/db/seed.js';
import type { Usuario } from '../src/core/context.js';

export const admin: Usuario = { usuario: 'admin', nombre: 'Administrador', roles: ['ADMIN'] };

export async function dbDemo(demo = true) {
  const db = connect({ url: 'sqlite::memory:' });
  await seedAll(db, { demo });
  return db;
}
