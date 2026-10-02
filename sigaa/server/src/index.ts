import { startServer } from './start.js';

const s = await startServer();
console.log(`SIGAA en ${s.url}`);
const salir = async () => {
  await s.close();
  process.exit(0);
};
process.on('SIGINT', salir);
process.on('SIGTERM', salir);
