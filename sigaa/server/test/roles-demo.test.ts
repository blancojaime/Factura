import { describe, it, expect } from 'vitest';
import { dbDemo } from './helpers.js';
import { autenticar, USUARIOS_DEMO } from '../src/core/auth.js';
import { puedeEscribir } from '../src/core/context.js';

describe('usuarios demo por rol', () => {
  it('con datos demo existe un usuario por rol y debe cambiar la clave', async () => {
    const db = await dbDemo(true);
    for (const u of USUARIOS_DEMO) {
      const r = await autenticar(db, u.usuario, u.clave);
      expect(r.debeCambiar).toBe(true);
      expect(r.user.roles).toEqual(u.roles);
    }
    const alm = (await autenticar(db, 'almacen', 'Almacen2026')).user;
    expect(puedeEscribir(alm, 'alm')).toBe(true);
    expect(puedeEscribir(alm, 'com')).toBe(false);
    const con = (await autenticar(db, 'consulta', 'Consulta2026')).user;
    expect(['alm', 'com', 'af'].some((m) => puedeEscribir(con, m as any))).toBe(false);
  });
  it('sin datos demo solo existe el administrador', async () => {
    const db = await dbDemo(false);
    const n = await db('core_usuarios').count({ n: '*' }).first();
    expect(Number(n?.n)).toBe(1);
  });
});
