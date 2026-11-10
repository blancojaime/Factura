/** Ubicación de los datos incluidos (UFV y catálogos de respaldo): carpeta `seed/vsiaf`. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const candidatos = [process.env.SIGAA_SEED_DIR, path.resolve(aqui, '../../seed'), path.resolve(aqui, '../seed'), path.resolve(aqui, '../../../seed')]
  .filter((d): d is string => !!d)
  .map((d) => path.join(d, 'vsiaf'));
export const CARPETA_VSIAF = candidatos.find((d) => fs.existsSync(path.join(d, 'catalogos.json'))) ?? candidatos[0];
export const rutaRecurso = (archivo: string) => path.join(CARPETA_VSIAF, archivo);
