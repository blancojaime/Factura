/**
 * Respaldo compatible con «Respaldos BD → Restaurar» del VSIAF: `.zip` **plano** con todos los archivos de `dbfs` más un `.gtz`
 * con el comentario (texto cp1252): «Backup de la entidad «<ENTIDAD>» en fecha dd/mm/aaaa: <descripción>».
 */
import fs from 'node:fs';
import path from 'node:path';
import AdmZip from 'adm-zip';
import iconv from 'iconv-lite';
import { buscarArchivo } from './dbf.js';
import { BdVsiaf } from './instalacion.js';

export function hacerRespaldo(db: BdVsiaf, descripcion: string, ahora = new Date()): string {
  const bdir = buscarArchivo(db.carpeta, 'backups') ?? path.join(db.carpeta, 'backups');
  fs.mkdirSync(bdir, { recursive: true });
  const p2 = (n: number) => String(n).padStart(2, '0');
  const sello = `${p2(ahora.getDate())}${p2(ahora.getMonth() + 1)}${p2(ahora.getFullYear() % 100)}${p2(ahora.getHours())}${p2(ahora.getMinutes())}`;
  const base = `VSIMPXL${sello}`;
  const zpath = path.join(bdir, base + '.zip');
  const comentario = `Backup de la entidad «${db.entidad}» en fecha ${p2(ahora.getDate())}/${p2(ahora.getMonth() + 1)}/${ahora.getFullYear()}: ${descripcion}`;
  const cp = iconv.encode(comentario, 'cp1252');
  const zip = new AdmZip();
  for (const fn of fs.readdirSync(db.dbfs).sort()) {
    const fp = path.join(db.dbfs, fn);
    if (fs.statSync(fp).isFile() && !fn.endsWith('.vsiaf_imp_tmp')) zip.addFile(fn, fs.readFileSync(fp));
  }
  // El comentario del .zip va en el registro final («end of central directory»): se escribe en cp1252, no en UTF-8.
  const buf = zip.toBuffer();
  const eocd = buf.length - 22;
  if (buf.readUInt32LE(eocd) !== 0x06054b50) throw new Error('No se pudo construir el respaldo (.zip).');
  const cab = Buffer.from(buf.subarray(0, buf.length - 2));
  const len = Buffer.alloc(2);
  len.writeUInt16LE(cp.length);
  fs.writeFileSync(zpath, Buffer.concat([cab, len, cp]));
  fs.writeFileSync(path.join(bdir, base + '.gtz'), cp);
  return zpath;
}

/** Restaura un respaldo creado por este módulo (o por el VSIAF) sobre la carpeta `dbfs`. */
export function restaurarRespaldo(db: BdVsiaf, rutaZip: string): number {
  const zip = new AdmZip(rutaZip);
  let n = 0;
  for (const e of zip.getEntries()) {
    if (e.isDirectory) continue;
    fs.writeFileSync(path.join(db.dbfs, path.basename(e.entryName)), e.getData());
    n++;
  }
  db.recargar();
  return n;
}

/** Comentario guardado en el respaldo (cp1252). */
export function comentarioRespaldo(rutaZip: string): string {
  const b = fs.readFileSync(rutaZip);
  const eocd = b.length - 22 - 0;
  // buscar el registro final desde el final del archivo
  for (let i = b.length - 22; i >= Math.max(0, b.length - 22 - 65535); i--) {
    if (b.readUInt32LE(i) === 0x06054b50) { const n = b.readUInt16LE(i + 20); return iconv.decode(b.subarray(i + 22, i + 22 + n), 'cp1252'); }
  }
  void eocd;
  return '';
}
