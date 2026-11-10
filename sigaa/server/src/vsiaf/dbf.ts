/**
 * Lectura / escritura mínima de tablas Visual FoxPro (.DBF + .FPT) para el VSIAF.
 *
 * Solo implementa lo que se necesita: agregar registros, modificar campos de un registro existente y
 * marcar/desmarcar registros como borrados. NO toca los índices (.CDX): después de importar hay que
 * ejecutar «Administradores → Re-indexar» dentro del VSIAF.
 *
 * Todo ocurre en memoria; `guardar()` vuelca el archivo de una sola vez (temporal + reemplazo), de modo que
 * una importación fallida no deja tablas a medias.
 */
import fs from 'node:fs';
import path from 'node:path';
import iconv from 'iconv-lite';
import Decimal from 'decimal.js';
import { Fecha, fechaValida, iso } from './fecha.js';

/** Byte 29 de la cabecera = «language driver». El VSIAF usa 0x03 (cp1252) y 0x02 (cp850) en AUXILIAR.DBF. */
const LANG_ENCODING: Record<number, string> = {
  0x00: 'cp1252', 0x01: 'cp437', 0x02: 'cp850', 0x03: 'cp1252', 0x04: 'macintosh', 0x64: 'cp852', 0x65: 'cp866', 0x66: 'cp865',
  0x78: 'cp950', 0x79: 'cp949', 0x7a: 'cp936', 0x7b: 'cp932', 0xc8: 'cp1250', 0xc9: 'cp1251', 0xca: 'cp1254', 0xcb: 'cp1253',
};
const EOF_MARK = 0x1a;

export class DbfError extends Error {}

export interface Campo { nombre: string; tipo: string; largo: number; decimales: number; offset: number }
export type Valor = string | number | boolean | null;
export interface Registro { recno: number; borrado: boolean; valores: Record<string, Valor> }
export type Especificacion = [nombre: string, tipo: string, largo: number, decimales: number][];

/** Busca `nombre` en `carpeta` sin distinguir mayúsculas (Windows sí, Linux no). */
export function buscarArchivo(carpeta: string, nombre: string): string | null {
  const directo = path.join(carpeta, nombre);
  if (fs.existsSync(directo)) return directo;
  const bajo = nombre.toLowerCase();
  try {
    for (const f of fs.readdirSync(carpeta)) if (f.toLowerCase() === bajo) return path.join(carpeta, f);
  } catch { /* carpeta inexistente */ }
  return null;
}

export function redondear(x: number | string | Decimal, nd = 2): number {
  return new Decimal(x).toDecimalPlaces(nd, Decimal.ROUND_HALF_UP).toNumber();
}

/** Buffer que crece por duplicación (agregar miles de registros sin copiar todo cada vez). */
class Crece {
  buf: Buffer;
  len: number;
  constructor(inicial: Buffer) { this.buf = Buffer.from(inicial); this.len = inicial.length; }
  asegurar(n: number) {
    if (n <= this.buf.length) return;
    const nuevo = Buffer.alloc(Math.max(n, this.buf.length * 2));
    this.buf.copy(nuevo, 0, 0, this.len);
    this.buf = nuevo;
  }
  truncar(n: number) { this.len = n; }
  agregar(b: Buffer | Uint8Array) { this.asegurar(this.len + b.length); Buffer.from(b).copy(this.buf, this.len); this.len += b.length; }
  ver(): Buffer { return this.buf.subarray(0, this.len); }
}

export class DbfTabla {
  readonly ruta: string;
  nrec = 0;
  hlen = 0;
  rlen = 0;
  lang = 0;
  version = 0;
  campos: Campo[] = [];
  mapa: Record<string, Campo> = {};
  codificacion: string;
  rutaMemo: string | null = null;
  private datos: Crece;
  private memo: Crece | null = null;
  private sucio = false;

  constructor(ruta: string, codificacion?: string) {
    this.ruta = ruta;
    this.datos = new Crece(fs.readFileSync(ruta));
    this.leerCabecera();
    this.codificacion = codificacion ?? LANG_ENCODING[this.lang] ?? 'cp1252';
    if (this.campos.some((f) => 'MGP'.includes(f.tipo))) {
      const base = ruta.replace(/\.[^.]*$/, '');
      for (const ext of ['.FPT', '.fpt', '.Fpt']) if (fs.existsSync(base + ext)) { this.rutaMemo = base + ext; break; }
      if (!this.rutaMemo) throw new DbfError(`${this.nombre}: falta el archivo de memo (.FPT)`);
      this.memo = new Crece(fs.readFileSync(this.rutaMemo));
    }
  }

  get nombre(): string { return path.basename(this.ruta); }
  get archivos(): string[] { return this.rutaMemo ? [this.ruta, this.rutaMemo] : [this.ruta]; }

  private leerCabecera() {
    const b = this.datos.ver();
    if (b.length < 33) throw new DbfError(`${this.ruta}: archivo DBF demasiado corto`);
    this.version = b[0];
    this.nrec = b.readUInt32LE(4);
    this.hlen = b.readUInt16LE(8);
    this.rlen = b.readUInt16LE(10);
    this.lang = b[29];
    const campos: Campo[] = [];
    let pos = 32;
    let off = 1;
    while (pos < b.length && b[pos] !== 0x0d) {
      const d = b.subarray(pos, pos + 32);
      const fin = d.indexOf(0);
      const nombre = d.subarray(0, fin < 0 || fin > 11 ? 11 : fin).toString('latin1').toUpperCase();
      campos.push({ nombre, tipo: String.fromCharCode(d[11]), largo: d[16], decimales: d[17], offset: off });
      off += d[16];
      pos += 32;
    }
    if (off !== this.rlen) throw new DbfError(`${this.ruta}: longitud de registro inconsistente (${off} != ${this.rlen})`);
    this.campos = campos;
    this.mapa = Object.fromEntries(campos.map((c) => [c.nombre, c]));
  }

  // ------------------------------------------------------------------ lectura
  private offReg(recno: number) { return this.hlen + (recno - 1) * this.rlen; }

  leer(recno: number): Registro {
    if (recno < 1 || recno > this.nrec) throw new DbfError(`${this.nombre}: registro ${recno} fuera de rango`);
    const o = this.offReg(recno);
    const raw = this.datos.ver().subarray(o, o + this.rlen);
    const valores: Record<string, Valor> = {};
    for (const f of this.campos) valores[f.nombre] = this.decodificar(f, raw);
    return { recno, borrado: raw[0] === 0x2a, valores };
  }

  *registros(incluirBorrados = false): Generator<Registro> {
    for (let n = 1; n <= this.nrec; n++) {
      const r = this.leer(n);
      if (r.borrado && !incluirBorrados) continue;
      yield r;
    }
  }

  private decodificar(f: Campo, rec: Buffer): Valor {
    const raw = rec.subarray(f.offset, f.offset + f.largo);
    switch (f.tipo) {
      case 'C': return iconv.decode(raw, this.codificacion).replace(/[ \0]+$/, '');
      case 'N': case 'F': {
        const s = raw.toString('latin1').trim();
        if (!s || s.replace(/\*/g, '') === '') return null;
        const v = Number(s);
        return Number.isNaN(v) ? null : v;
      }
      case 'D': {
        const s = raw.toString('latin1').trim();
        if (!s) return null;
        const y = Number(s.slice(0, 4)), m = Number(s.slice(4, 6)), d = Number(s.slice(6, 8));
        return fechaValida(y, m, d) ? iso(y, m, d) : null;
      }
      case 'L': { const c = raw.toString('latin1').trim().toUpperCase(); return c === 'T' || c === 'Y' ? true : c === 'F' || c === 'N' ? false : null; }
      case 'I': return raw.readInt32LE(0);
      case 'B': return raw.readDoubleLE(0);
      case 'M': return this.leerMemo(this.punteroMemo(f, raw));
      default: return null;
    }
  }

  // ------------------------------------------------------------------ memo
  private punteroMemo(f: Campo, raw: Buffer): number {
    if (f.largo === 4) return raw.readUInt32LE(0);
    const s = raw.toString('latin1').trim();
    return /^\d+$/.test(s) ? Number(s) : 0;
  }
  private tamBloque(): number { return this.memo!.ver().readUInt16BE(6) || 64; }
  private leerMemo(bloque: number): string | null {
    if (!bloque || !this.memo) return null;
    const m = this.memo.ver();
    const o = bloque * this.tamBloque();
    if (o + 8 > m.length) return null;
    const ln = m.readUInt32BE(o + 4);
    return iconv.decode(m.subarray(o + 8, o + 8 + ln), this.codificacion);
  }
  private escribirMemo(texto: string): number {
    const m = this.memo!;
    const data = iconv.encode(texto, this.codificacion);
    const bs = this.tamBloque();
    const bloque = m.ver().readUInt32BE(0);
    const nbloques = Math.floor((8 + data.length + bs - 1) / bs);
    const inicio = bloque * bs;
    if (m.len < inicio) { m.asegurar(inicio); m.buf.fill(0, m.len, inicio); m.len = inicio; }
    m.truncar(inicio);
    const cab = Buffer.alloc(8);
    cab.writeUInt32BE(1, 0);
    cab.writeUInt32BE(data.length, 4);
    m.agregar(cab);
    m.agregar(data);
    const relleno = nbloques * bs - 8 - data.length;
    if (relleno > 0) m.agregar(Buffer.alloc(relleno));
    m.buf.writeUInt32BE(bloque + nbloques, 0);
    return bloque;
  }

  // ------------------------------------------------------------------ codificación
  private codificar(f: Campo, v: unknown): Buffer {
    switch (f.tipo) {
      case 'C': {
        const s = v === null || v === undefined ? '' : String(v);
        const b = iconv.encode(s, this.codificacion);
        if (b.length > f.largo) throw new DbfError(`${this.nombre}.${f.nombre}: valor demasiado largo (${b.length} > ${f.largo})`);
        return Buffer.concat([b, Buffer.alloc(f.largo - b.length, 0x20)]);
      }
      case 'N': case 'F': {
        if (v === null || v === undefined || v === '') return Buffer.alloc(f.largo, 0x20);
        const d = new Decimal(v as number);
        const s = f.decimales ? d.toFixed(f.decimales, Decimal.ROUND_HALF_UP) : d.toFixed(0, Decimal.ROUND_HALF_UP);
        if (s.length > f.largo) throw new DbfError(`${this.nombre}.${f.nombre}: número fuera de rango (${s})`);
        return Buffer.from(s.padStart(f.largo, ' '), 'latin1');
      }
      case 'D': return v ? Buffer.from(String(v).replace(/-/g, ''), 'latin1') : Buffer.alloc(8, 0x20);
      case 'L': return Buffer.from(v === null || v === undefined ? '?' : v ? 'T' : 'F', 'latin1');
      case 'M': {
        if (v === null || v === undefined || String(v) === '') return f.largo === 4 ? Buffer.alloc(4) : Buffer.alloc(f.largo, 0x20);
        if (!this.memo) throw new DbfError(`${this.nombre}: la tabla no tiene archivo de memo`);
        const blk = this.escribirMemo(String(v));
        if (f.largo === 4) { const b = Buffer.alloc(4); b.writeUInt32LE(blk); return b; }
        return Buffer.from(String(blk).padStart(f.largo, ' '), 'latin1');
      }
      case 'I': { const b = Buffer.alloc(4); b.writeInt32LE(Number(v ?? 0)); return b; }
      default: throw new DbfError(`${this.nombre}.${f.nombre}: tipo de campo '${f.tipo}' no soportado para escritura`);
    }
  }

  private registroVacio(): Buffer {
    const rec = Buffer.alloc(this.rlen, 0x20);
    for (const f of this.campos) {
      if (f.tipo === 'L') rec[f.offset] = 0x46; // F
      else if ('IBYT'.includes(f.tipo)) rec.fill(0, f.offset, f.offset + f.largo);
    }
    return rec;
  }

  // ------------------------------------------------------------------ escritura
  agregar(valores: Record<string, unknown>): number {
    const rec = this.registroVacio();
    for (const [k, v] of Object.entries(valores)) {
      const f = this.mapa[k.toUpperCase()];
      if (!f) throw new DbfError(`${this.nombre}: no existe el campo ${k}`);
      this.codificar(f, v).copy(rec, f.offset);
    }
    const pos = this.offReg(this.nrec + 1);
    this.datos.truncar(pos);
    this.datos.agregar(rec);
    this.datos.agregar(Buffer.from([EOF_MARK]));
    this.nrec++;
    this.datos.buf.writeUInt32LE(this.nrec, 4);
    this.tocarCabecera();
    this.sucio = true;
    return this.nrec;
  }

  actualizar(recno: number, valores: Record<string, unknown>): void {
    if (recno < 1 || recno > this.nrec) throw new DbfError(`${this.nombre}: registro ${recno} fuera de rango`);
    const base = this.offReg(recno);
    for (const [k, v] of Object.entries(valores)) {
      const f = this.mapa[k.toUpperCase()];
      if (!f) throw new DbfError(`${this.nombre}: no existe el campo ${k}`);
      this.codificar(f, v).copy(this.datos.buf, base + f.offset);
    }
    this.tocarCabecera();
    this.sucio = true;
  }

  marcarBorrado(recno: number, borrado = true): void {
    this.datos.buf[this.offReg(recno)] = borrado ? 0x2a : 0x20;
    this.tocarCabecera();
    this.sucio = true;
  }

  /** Se respeta la convención que ya usa cada archivo (años desde 1900, o YY). */
  private tocarCabecera() {
    const t = new Date();
    const y = this.datos.buf[1];
    this.datos.buf[1] = y >= 100 ? t.getFullYear() - 1900 : t.getFullYear() % 100;
    this.datos.buf[2] = t.getMonth() + 1;
    this.datos.buf[3] = t.getDate();
  }

  get modificada(): boolean { return this.sucio; }

  guardar(): void {
    if (!this.sucio) return;
    escrituraAtomica(this.ruta, this.datos.ver());
    if (this.rutaMemo && this.memo) escrituraAtomica(this.rutaMemo, this.memo.ver());
    this.sucio = false;
  }
}

export function escrituraAtomica(ruta: string, datos: Buffer | Uint8Array): void {
  const tmp = ruta + '.vsiaf_imp_tmp';
  const fd = fs.openSync(tmp, 'w');
  try { fs.writeSync(fd, datos); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  try { fs.accessSync(ruta, fs.constants.W_OK); } catch { try { fs.chmodSync(ruta, 0o666); } catch { /* sin permiso para cambiarlo */ } }
  try { fs.renameSync(tmp, ruta); } catch (e) {
    try { fs.unlinkSync(tmp); } catch { /* ya no existe */ }
    throw new DbfError(`No se pudo escribir ${path.basename(ruta)}: está en uso (¿VSIAF abierto?) o sin permisos.`);
  }
}

/** Crea una tabla vacía (pruebas y generador de la base sintética de ensayo). */
export function crearTabla(ruta: string, spec: Especificacion, lang = 0x03, tamBloqueMemo = 64, version = 0xf5): void {
  const hlen = 32 + 32 * spec.length + 1;
  const rlen = 1 + spec.reduce((t, s) => t + s[2], 0);
  const cab = Buffer.alloc(32);
  const t = new Date();
  cab[0] = version;
  cab[1] = t.getFullYear() - 1900; cab[2] = t.getMonth() + 1; cab[3] = t.getDate();
  cab.writeUInt16LE(hlen, 8);
  cab.writeUInt16LE(rlen, 10);
  cab[29] = lang;
  const partes: Buffer[] = [cab];
  let off = 1;
  for (const [nombre, tipo, largo, dec] of spec) {
    const d = Buffer.alloc(32);
    d.write(nombre, 0, 'latin1');
    d[11] = tipo.charCodeAt(0);
    d.writeUInt32LE(off, 12);
    d[16] = largo;
    d[17] = dec;
    partes.push(d);
    off += largo;
  }
  partes.push(Buffer.from([0x0d, EOF_MARK]));
  fs.writeFileSync(ruta, Buffer.concat(partes));
  if (spec.some((s) => s[1] === 'M')) {
    const base = ruta.replace(/\.[^.]*$/, '');
    const nb = 512 / tamBloqueMemo;
    const hdr = Buffer.alloc(512);
    hdr.writeUInt32BE(nb, 0);
    hdr.writeUInt16BE(tamBloqueMemo, 6);
    fs.writeFileSync(base + '.FPT', hdr);
  }
}

export type { Fecha };
