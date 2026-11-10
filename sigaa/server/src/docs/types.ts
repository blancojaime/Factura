import type { Db } from '../core/context.js';
import type { Params } from '../reports/types.js';
import { txt } from '../core/util.js';

export interface Documento {
  id: string;
  nombre: string;
  modulo: 'alm' | 'com' | 'af';
  /** Qué identifica al documento: número (ref) y parámetros adicionales. */
  ref: string;
  build(db: Db, ref: string, p: Params): Promise<Buffer>;
}
export const DOCS = new Map<string, Documento>();
export const registrarDoc = (...ds: Documento[]) => ds.forEach((d) => DOCS.set(d.id, d));

export const nomCargo = (n?: string, c?: string) => [txt(n), txt(c)].filter(Boolean).join(' — ');
export const casilla = (v: boolean) => (v ? '[X]' : '[  ]');
