/** Acceso a la instalación del VSIAF: ubicación, catálogos y tablas. */
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { buscarArchivo, DbfTabla } from './dbf.js';
import { rutaRecurso } from './recursos.js';

export const CLAVE_REGISTRO = 'HKCU\\SOFTWARE\\MEFP\\SIAF'; // APPinstall, APPDBFS, APPIncEsp, ...
export const TABLAS = ['ACTUAL', 'REVAL', 'BAJAS', 'TRASFE', 'OFICINA', 'RESP', 'AUXILIAR', 'UNIDADADMIN'] as const;

/** Normaliza texto para comparar: sin acentos, mayúsculas, espacios simples. */
export function norm(s: unknown): string {
  if (s === null || s === undefined) return '';
  return String(s).replace(/¥/g, 'Ñ').trim().normalize('NFD').replace(/\p{Mn}/gu, '').replace(/\s+/g, ' ').toUpperCase();
}

export interface Catalogos {
  grupos: { codcont: number; nombre: string; vida_util: number; depreciar: boolean; actualizar: boolean }[];
  estados: { codigo: number; nombre: string }[];
  motivos_baja: { codigo: number; nombre: string }[];
  organismos_financiadores: { codigo: string; nombre: string; sigla: string }[];
  departamentos: { codigo: number; nombre: string; sigla: string }[];
}
let _catalogos: Catalogos | null = null;
export function catalogosIncluidos(): Catalogos {
  return (_catalogos ??= JSON.parse(fs.readFileSync(rutaRecurso('catalogos.json'), 'utf8')) as Catalogos);
}

// ───────────── Windows (solo lectura) ─────────────
function leerRegistro(valor: string): string | null {
  if (process.platform !== 'win32') return null;
  try {
    const out = execFileSync('reg', ['query', CLAVE_REGISTRO, '/v', valor], { encoding: 'utf8', timeout: 10000, windowsHide: true });
    const m = new RegExp(`${valor}\\s+REG_\\w+\\s+(.*)`, 'i').exec(out);
    return m ? m[1].trim() || null : null;
  } catch { return null; }
}

/**
 * ¿Tiene este equipo habilitadas las Incorporaciones Especiales? (solo lectura)
 * La habilita la Dirección General de Contabilidad Fiscal mediante una llave con vigencia; el módulo la respeta y NUNCA la modifica.
 */
export const incorporacionEspecialHabilitada = (): boolean => leerRegistro('APPIncEsp') === '1';

export function vsiafAbierto(): boolean {
  if (process.platform !== 'win32') return false;
  try {
    const out = execFileSync('tasklist', ['/FI', 'IMAGENAME eq vsiaf.exe', '/NH'], { encoding: 'utf8', timeout: 15000, windowsHide: true });
    return out.toLowerCase().includes('vsiaf.exe');
  } catch { return false; }
}

/** Carpeta de instalación del VSIAF (la que contiene vsiaf.exe y dbfs). */
export function detectarInstalacion(): string | null {
  const cands: string[] = [];
  const reg = leerRegistro('APPinstall');
  if (reg) cands.push(reg);
  cands.push('C:\\vsiaf', 'D:\\vsiaf', path.join(process.env.HOME ?? '', 'vsiaf'));
  for (let c of cands) {
    c = c.replace(/[\\/]+$/, '');
    if (fs.existsSync(path.join(c, 'dbfs')) || buscarArchivo(c, 'dbfs')) return c;
  }
  return null;
}

export class InstalacionError extends Error {}

/** Una instalación del VSIAF (carpeta raíz + carpeta `dbfs`). */
export class BdVsiaf {
  readonly carpeta: string;
  readonly dbfs: string;
  readonly catalogos: Catalogos;
  private tablas = new Map<string, DbfTabla>();

  constructor(carpeta: string, dbfs?: string) {
    this.carpeta = carpeta;
    this.dbfs = dbfs ?? buscarArchivo(carpeta, 'dbfs') ?? path.join(carpeta, 'dbfs');
    if (!fs.existsSync(this.dbfs) || !fs.statSync(this.dbfs).isDirectory()) throw new InstalacionError(`No se encontró la carpeta de datos (dbfs) en ${carpeta}`);
    for (const t of ['ACTUAL', 'CODCONT', 'UNIDADADMIN']) {
      if (!buscarArchivo(this.dbfs, t + '.DBF')) throw new InstalacionError(`Falta la tabla ${t}.DBF en ${this.dbfs}: no parece una base del VSIAF`);
    }
    this.catalogos = catalogosIncluidos();
  }

  tabla(nombre: string): DbfTabla {
    const k = nombre.toUpperCase();
    let t = this.tablas.get(k);
    if (!t) {
      const p = buscarArchivo(this.dbfs, k + '.DBF');
      if (!p) throw new InstalacionError(`Falta la tabla ${k}.DBF en ${this.dbfs}`);
      t = new DbfTabla(p);
      this.tablas.set(k, t);
    }
    return t;
  }
  existeTabla(nombre: string): boolean { return !!buscarArchivo(this.dbfs, nombre.toUpperCase() + '.DBF'); }

  /** Todos los archivos que el módulo puede modificar (para el respaldo y la reversión). */
  archivosAfectados(): string[] { return TABLAS.flatMap((t) => this.tabla(t).archivos); }
  guardarTodo(): void { for (const t of this.tablas.values()) t.guardar(); }
  /** Descarta lo cargado en memoria (tras una reversión) para volver a leer del disco. */
  recargar(): void { this.tablas.clear(); }

  get entidad(): string {
    for (const r of this.tabla('CONFIG').registros()) if (String(r.valores.ENTIDAD ?? '').trim()) return String(r.valores.ENTIDAD).trim();
    throw new InstalacionError('config.dbf no tiene la entidad: abra el VSIAF y seleccione la entidad primero');
  }
  get entidadNombre(): string {
    for (const r of this.tabla('CONFIG').registros()) if (String(r.valores.ENTIDAD ?? '').trim()) return String(r.valores.DESCENT ?? '').trim();
    return '';
  }
  get usuarioPorDefecto(): string {
    for (const r of this.tabla('CONFIG').registros()) {
      const u = String(r.valores.USUARIO ?? '').trim();
      if (u && u.toUpperCase() !== 'VSIAF') return u.slice(0, 8);
    }
    return 'admin';
  }
  /** Si `closeges\closeges.dbf` tiene un registro `NOM_ARCH = 'ACTUAL'`, la base está cerrada (solo lectura). */
  gestionCerrada(): boolean {
    const carp = buscarArchivo(this.carpeta, 'closeges');
    const p = carp ? buscarArchivo(carp, 'closeges.dbf') : null;
    if (!p) return false;
    for (const r of new DbfTabla(p).registros()) if (String(r.valores.NOM_ARCH ?? '').trim().toUpperCase() === 'ACTUAL') return true;
    return false;
  }

  unidades(): { unidad: string; descripcion: string; ciudad: string; estado: number }[] {
    const ent = this.entidad;
    return [...this.tabla('UNIDADADMIN').registros()]
      .filter((r) => String(r.valores.ENTIDAD ?? '').trim() === ent)
      .map((r) => ({ unidad: String(r.valores.UNIDAD ?? '').trim(), descripcion: String(r.valores.DESCRIP ?? '').trim(), ciudad: String(r.valores.CIUDAD ?? '').trim(), estado: Number(r.valores.ESTADOUNI ?? 0) }));
  }

  // Catálogos: la base primero; si no existen, los incluidos.
  grupos(): Catalogos['grupos'] {
    return [...this.tabla('CODCONT').registros()]
      .map((r) => ({ codcont: Number(r.valores.CODCONT), nombre: String(r.valores.NOMBRE ?? '').replace(/¥/g, 'Ñ'), vida_util: Number(r.valores.VIDAUTIL ?? 0), depreciar: !!r.valores.DEPRECIAR, actualizar: !!r.valores.ACTUALIZAR }))
      .sort((a, b) => a.codcont - b.codcont);
  }
  estados(): Catalogos['estados'] {
    return this.existeTabla('ESTADO') ? [...this.tabla('ESTADO').registros()].map((r) => ({ codigo: Number(r.valores.CODESTADO), nombre: String(r.valores.NOMESTADO ?? '').trim() })) : this.catalogos.estados;
  }
  motivosBaja(): Catalogos['motivos_baja'] {
    return this.existeTabla('BAJA') ? [...this.tabla('BAJA').registros()].map((r) => ({ codigo: Number(r.valores.CODBAJA), nombre: String(r.valores.DESCBAJA ?? '').trim() })) : this.catalogos.motivos_baja;
  }
  organismos(): Catalogos['organismos_financiadores'] {
    return this.existeTabla('ORGANISMO_FIN') ? [...this.tabla('ORGANISMO_FIN').registros()].map((r) => ({ codigo: String(r.valores.OF ?? '').trim(), nombre: String(r.valores.DES ?? '').trim(), sigla: String(r.valores.SIGLA ?? '').trim() })) : this.catalogos.organismos_financiadores;
  }
  departamentos(): Catalogos['departamentos'] {
    return this.existeTabla('CLA_DEPTS') ? [...this.tabla('CLA_DEPTS').registros()].map((r) => ({ codigo: Number(r.valores.CODIGO), nombre: String(r.valores.DESC ?? '').trim(), sigla: String(r.valores.SIGLA ?? '').trim() })) : this.catalogos.departamentos;
  }
}
