import path from 'node:path';
import { connect } from './db/connect.js';
import { seedAll } from './db/seed.js';
import { buildApp } from './app.js';

const db = connect();
// Crea el esquema si no existe. Los datos demo solo se cargan con SIGAA_DEMO=1 o con `npm run seed`.
await seedAll(db, { demo: process.env.SIGAA_DEMO === '1' });

const app = await buildApp({ db, logger: true, webDir: process.env.SIGAA_WEB_DIR || path.resolve(process.cwd(), '../web/dist') });
const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || '0.0.0.0';
await app.listen({ port, host });
console.log(`SIGAA en http://${host === '0.0.0.0' ? 'localhost' : host}:${port}`);

const salir = async () => {
  await app.close();
  await db.destroy();
  process.exit(0);
};
process.on('SIGINT', salir);
process.on('SIGTERM', salir);
