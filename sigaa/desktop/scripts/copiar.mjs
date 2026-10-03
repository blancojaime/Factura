// Copia el servidor compilado, la web y los datos de ejemplo a dist/ para empaquetarlos juntos.
import fs from 'node:fs';
import path from 'node:path';
const raiz = path.resolve(import.meta.dirname, '../..');
const dist = path.resolve(import.meta.dirname, '../dist');
const copiar = (de, a) => {
  if (!fs.existsSync(de)) throw new Error(`Falta ${de}. Ejecute «npm run build» en la raíz del proyecto.`);
  fs.rmSync(a, { recursive: true, force: true });
  fs.cpSync(de, a, { recursive: true });
};
copiar(path.join(raiz, 'server/dist'), path.join(dist, 'server'));
copiar(path.join(raiz, 'web/dist'), path.join(dist, 'web'));
copiar(path.join(raiz, 'server/seed'), path.join(dist, 'seed'));
fs.writeFileSync(path.join(dist, 'server/package.json'), JSON.stringify({ type: 'module' }));
console.log('Recursos copiados a', dist);

// Dependencias del servidor: instalación limpia (solo producción) que se copia como recurso de la aplicación.
import { execSync } from 'node:child_process';
const deps = path.resolve(import.meta.dirname, '../build-deps');
fs.rmSync(deps, { recursive: true, force: true });
fs.mkdirSync(deps, { recursive: true });
const pkg = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, '../package.json'), 'utf8'));
fs.writeFileSync(path.join(deps, 'package.json'), JSON.stringify({ name: 'sigaa-deps', version: '1.0.0', private: true, dependencies: pkg.runtimeDeps }));
execSync('npm install --omit=dev --ignore-scripts --no-audit --no-fund', { cwd: deps, stdio: 'inherit' });
console.log('Dependencias del servidor listas en', deps);
