import { createHash } from 'crypto';

export const sha256 = (data: Buffer | string): string => createHash('sha256').update(data).digest('hex');

/** JSON canónico (claves ordenadas) para hashes reproducibles. */
export function jsonCanonico(valor: unknown): string {
  if (valor === null || typeof valor !== 'object') return JSON.stringify(valor === undefined ? null : valor);
  if (valor instanceof Date) return JSON.stringify(valor.toISOString());
  if (Array.isArray(valor)) return '[' + valor.map(jsonCanonico).join(',') + ']';
  const o = valor as Record<string, unknown>;
  return '{' + Object.keys(o).sort().filter((k) => o[k] !== undefined).map((k) => JSON.stringify(k) + ':' + jsonCanonico(o[k])).join(',') + '}';
}

export const GENESIS = '0'.repeat(64);
/** Cadena de hashes de auditoría: cada registro sella al anterior. */
export const hashRegistroAuditoria = (hashPrevio: string, registro: unknown): string => sha256(hashPrevio + jsonCanonico(registro));

export function verificarCadena<T extends { hash: string; hashPrevio: string }>(registros: T[], payloadDe: (r: T) => unknown): { integra: boolean; falloEn: number | null } {
  let previo = GENESIS;
  for (let i = 0; i < registros.length; i++) {
    const r = registros[i];
    if (r.hashPrevio !== previo || hashRegistroAuditoria(previo, payloadDe(r)) !== r.hash) return { integra: false, falloEn: i };
    previo = r.hash;
  }
  return { integra: true, falloEn: null };
}

export interface DocumentoSellado { orden: number; tipo: string; version: number; hashSha256: string }
/** Sello del Expediente Único: hash sobre la lista ordenada de (tipo, versión, hash) de cada documento. */
export const hashExpediente = (docs: DocumentoSellado[]): string =>
  sha256([...docs].sort((a, b) => a.orden - b.orden).map((d) => `${d.orden}|${d.tipo}|v${d.version}|${d.hashSha256}`).join('\n'));
