import { Injectable } from '@nestjs/common';
import { promises as fs } from 'fs';
import * as path from 'path';

/** Almacenamiento en volumen local. Las rutas relativas se validan para impedir path traversal. */
@Injectable()
export class StorageService {
  readonly raiz = path.resolve(process.env.STORAGE_DIR ?? './storage');

  private resolver(ruta: string): string {
    const abs = path.resolve(this.raiz, ruta);
    if (!abs.startsWith(this.raiz + path.sep)) throw new Error('Ruta de almacenamiento inválida.');
    return abs;
  }
  async guardar(ruta: string, datos: Buffer): Promise<void> {
    const abs = this.resolver(ruta);
    await fs.mkdir(path.dirname(abs), { recursive: true });
    await fs.writeFile(abs, datos, { flag: 'wx' }); // jamás sobrescribe: los documentos son inmutables
  }
  leer(ruta: string): Promise<Buffer> { return fs.readFile(this.resolver(ruta)); }
}
