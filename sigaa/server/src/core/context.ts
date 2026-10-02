import type { Knex } from 'knex';

/** Conexión o transacción de Knex. Dentro de una transacción SIEMPRE se debe usar la transacción. */
export type Db = Knex | Knex.Transaction;

export type Modulo = 'core' | 'alm' | 'com' | 'af';

export interface Usuario {
  usuario: string;
  nombre: string;
  roles: string[];
}

export const ROLES = ['ADMIN', 'ALMACEN', 'COMBUSTIBLE', 'ACTIVOS', 'CONSULTA'] as const;
export type Rol = (typeof ROLES)[number];

/** Rol que habilita la escritura en cada módulo (ADMIN habilita todos). */
export const ROL_DE_MODULO: Record<Modulo, Rol | null> = { core: null, alm: 'ALMACEN', com: 'COMBUSTIBLE', af: 'ACTIVOS' };

export function puedeEscribir(u: Usuario, m: Modulo): boolean {
  if (u.roles.includes('ADMIN')) return true;
  const r = ROL_DE_MODULO[m];
  return !!r && u.roles.includes(r);
}
export const esAdmin = (u: Usuario): boolean => u.roles.includes('ADMIN');
