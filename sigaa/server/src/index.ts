import { startServer } from './start.js';

const s = await startServer();
console.log(`SIGAA en ${s.url}`);
const salir = async () => {
  await s.close();
  process.exit(0);
};
process.on('SIGINT', salir);
process.on('SIGTERM', salir);
// Un error inesperado en una operación no debe tumbar el servicio para todos los usuarios: se registra y se sigue.
process.on('unhandledRejection', (e) => console.error('Promesa rechazada sin manejar:', e));
process.on('uncaughtException', (e) => console.error('Error no capturado:', e));
