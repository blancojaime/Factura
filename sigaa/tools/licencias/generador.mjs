// Generador de claves de activación de SIGAA Escritorio (menú en pantalla). Ejecutar con GENERADOR_DE_CLAVES.bat
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { crearPar, emitirClave } from './emisor.mjs';

const aqui = import.meta.dirname;
const privDir = path.join(aqui, 'privada');
const privada = path.join(privDir, 'clave_privada.pem');
const publica = path.resolve(aqui, '../../desktop/licencia/publica.pem');
const registro = path.join(privDir, 'licencias_emitidas.csv');
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const pregunta = async (t, def = '') => ((await rl.question(def ? `${t} [${def}]: ` : `${t}: `)).trim() || def);

if (process.argv.includes('--crear-par-si-falta')) {
  if (!fs.existsSync(privada)) { const r = crearPar(privDir, publica); console.log('Se creó el par de claves de licenciamiento.\n  Privada (SECRETA, haga copia segura): ' + r.priv + '\n  Pública (va dentro de la aplicación): ' + r.pub); }
  rl.close(); process.exit(0);
}

console.log('\n=== SIGAA · Generador de claves de activación ===');
console.log('Uso exclusivo del proveedor. Guarde la carpeta "privada" en un lugar seguro: NO la comparta ni la suba a internet.\n');
for (;;) {
  console.log('1) Crear el par de claves (se hace UNA sola vez)\n2) Generar una clave de activación para un cliente\n3) Ver las licencias emitidas\n0) Salir');
  const op = await pregunta('Elija una opción', '2');
  try {
    if (op === '0') break;
    if (op === '1') { const r = crearPar(privDir, publica); console.log(`\nListo.\n  Privada (SECRETA): ${r.priv}\n  Pública: ${r.pub}\nAhora vuelva a crear el instalador (CREAR_INSTALADOR_ESCRITORIO.bat) para que la aplicación incluya la clave pública.\n`); }
    else if (op === '2') {
      if (!fs.existsSync(privada)) throw new Error('Primero cree el par de claves (opción 1).');
      const entidad = await pregunta('Nombre de la entidad (aparecerá en la licencia)');
      console.log('El ID del equipo lo muestra la ventana de activación del cliente (XXXX-XXXX-XXXX-XXXX). Escriba * para una clave válida en cualquier equipo.');
      const equipo = await pregunta('ID del equipo', '*');
      const vence = await pregunta('Vencimiento AAAA-MM-DD (vacío = perpetua)', '');
      const { clave, datos } = emitirClave(fs.readFileSync(privada, 'utf8'), { entidad, equipo, vence });
      fs.mkdirSync(privDir, { recursive: true });
      if (!fs.existsSync(registro)) fs.writeFileSync(registro, 'emitida;entidad;equipo;vence;tipo\n');
      fs.appendFileSync(registro, `${datos.i};${datos.n};${datos.m};${datos.e || 'perpetua'};${datos.t}\n`);
      console.log('\n--- CLAVE DE ACTIVACIÓN (envíela completa al cliente) ---\n' + clave + '\n---------------------------------------------------------\n');
    } else if (op === '3') console.log('\n' + (fs.existsSync(registro) ? fs.readFileSync(registro, 'utf8') : 'Aún no hay licencias emitidas.') + '\n');
  } catch (e) { console.log('\n⚠ ' + e.message + '\n'); }
}
rl.close();
