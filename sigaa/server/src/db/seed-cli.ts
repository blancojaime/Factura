import { connect } from './connect.js';
import { seedAll } from './seed.js';
import { TABLE_ORDER } from './schema.js';

const db = connect();
const force = process.argv.includes('--force');
const sinDemo = process.argv.includes('--sin-demo');
if (force) {
  for (const t of [...TABLE_ORDER].reverse()) await db.schema.dropTableIfExists(t);
  console.log('Tablas eliminadas.');
}
await seedAll(db, { demo: !sinDemo });
console.log(`Base de datos lista (${sinDemo ? 'solo configuración y administrador' : 'con datos demo'}).`);
console.log('Usuario inicial: admin / Admin2026 (se exige cambiar la clave al ingresar).');
await db.destroy();
