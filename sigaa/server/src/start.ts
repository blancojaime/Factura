import path from 'node:path';
import { connect } from './db/connect.js';
import { seedAll } from './db/seed.js';
import { buildApp } from './app.js';
import { programarRespaldo } from './core/backup.js';
import { isPg } from './db/connect.js';

export interface StartOptions {
  /** postgres://… o sqlite:ruta (por defecto DATABASE_URL o sqlite:./data/sigaa.sqlite) */
  databaseUrl?: string;
  port?: number;
  host?: string;
  /** carpeta con la aplicación web compilada */
  webDir?: string;
  /** carpeta de fotografías de activos fijos */
  fotosDir?: string;
  /** cargar datos de demostración si la base está vacía */
  demo?: boolean;
  logger?: boolean;
  jwtSecret?: string;
}

/** Inicia SIGAA (API + aplicación web). Lo usan el servidor, el escritorio (Electron) y las pruebas. */
export async function startServer(o: StartOptions = {}) {
  if (o.fotosDir) process.env.SIGAA_FOTOS_DIR = o.fotosDir;
  const db = connect({ url: o.databaseUrl });
  await seedAll(db, { demo: o.demo ?? process.env.SIGAA_DEMO === '1' });
  if (!isPg(db) && process.env.SIGAA_BACKUP !== '0') programarRespaldo(db, process.env.SIGAA_BACKUP_DIR || path.resolve(o.fotosDir ? path.dirname(o.fotosDir) : 'data', 'respaldos'));
  const app = await buildApp({ db, logger: o.logger ?? true, webDir: o.webDir ?? process.env.SIGAA_WEB_DIR ?? path.resolve(process.cwd(), '../web/dist'), jwtSecret: o.jwtSecret });
  const port = o.port ?? Number(process.env.PORT || 3000);
  const host = o.host ?? process.env.HOST ?? '0.0.0.0';
  await app.listen({ port, host });
  const address = app.server.address();
  const realPort = typeof address === 'object' && address ? address.port : port;
  return {
    port: realPort,
    url: `http://${host === '0.0.0.0' ? 'localhost' : host}:${realPort}`,
    async close() {
      await app.close();
      await db.destroy();
    },
  };
}
