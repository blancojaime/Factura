import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { dbDemo, admin } from './helpers.js';
import { crearInstalacionSintetica } from '../src/vsiaf/index.js';
import { guardarEquivalencias, importarLote, seleccionVsiaf } from '../src/vsiaf/servicio.js';
import { previsualizarDesdeVsiaf, traerDesdeVsiaf } from '../src/vsiaf/desde-vsiaf.js';
import { BusinessError } from '../src/core/errors.js';

let db: Awaited<ReturnType<typeof dbDemo>>;
let raiz = '';
const HOY = '2026-10-21';
let antes: any[] = [];

beforeAll(async () => {
  db = await dbDemo();
  raiz = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'vsiaf-desde-')), 'vsiaf');
  crearInstalacionSintetica(raiz);
  await guardarEquivalencias(db, admin, [{ tipo: 'org_fin', clave: '41/113', valor: '113' }, { tipo: 'org_fin', clave: 'RECURSOS ESPECÍFICOS', valor: '111' }]);
  await importarLote(db, admin, { ruta: raiz, unidad: '1', hoy: HOY, fechaCalculo: HOY, omitirProceso: true, permitirIncorporacionEspecial: false, confirmar: true });
  antes = await db('af_activos').orderBy('codigo');
  // Se vacía SIGAA para simular una base nueva: todo debe volver desde el VSIAF.
  await db('af_movimientos').delete(); await db('af_vsiaf_envios').delete(); await db('af_vsiaf_lotes').delete(); await db('af_asignaciones_det').delete(); await db('af_activos').delete();
});
afterAll(async () => db.destroy());

describe('importar del VSIAF a SIGAA', () => {
  it('la vista previa lee los activos y no escribe nada', async () => {
    const v = await previsualizarDesdeVsiaf(db, { ruta: raiz });
    expect(v.leidos).toBe(48);
    expect(v.nuevos).toBe(48);
    expect(v.yaExisten).toBe(0);
    expect(v.porGrupo.reduce((t, g) => t + g.cantidad, 0)).toBe(48);
    expect(Number((await db('af_activos').count({ n: '*' }).first() as any).n)).toBe(0);
  });
  it('exige confirmar y edificio', async () => {
    await expect(traerDesdeVsiaf(db, admin, { ruta: raiz, cod_edif: 1 })).rejects.toBeInstanceOf(BusinessError);
    await expect(traerDesdeVsiaf(db, admin, { ruta: raiz, confirmar: true })).rejects.toThrow(/edificio/);
  });
  it('trae los 48 activos con sus datos y quedan como ya enviados', async () => {
    const r = await traerDesdeVsiaf(db, admin, { ruta: raiz, cod_edif: 1, cod_amb: 0, confirmar: true });
    expect(r.importados).toBe(48);
    const ahora = await db('af_activos').orderBy('codigo');
    expect(ahora).toHaveLength(48);
    const muestra = antes[0];
    const x = ahora.find((a: any) => a.codigo === muestra.codigo || a.codigo === String(muestra.codigo).toUpperCase());
    expect(x, `activo ${muestra.codigo}`).toBeTruthy();
    expect(Number(x.valor)).toBeCloseTo(Number(muestra.valor), 2);
    expect(x.fecha_ingreso).toBe(muestra.fecha_ingreso);
    expect(x.descripcion).toBe(String(muestra.descripcion).slice(0, 150).trim());
    expect(x.observaciones).toMatch(/Importado del VSIAF/);
    expect((await seleccionVsiaf(db, { estado: 'PENDIENTES' })).length).toBe(0);
    expect((await db('af_movimientos').where({ codigo: x.codigo })).map((m: any) => m.tipo)).toContain('CODIFICACIÓN DIRECTA');
  });
  it('una segunda vez no hay nada nuevo', async () => {
    await expect(traerDesdeVsiaf(db, admin, { ruta: raiz, cod_edif: 1, confirmar: true })).rejects.toThrow(/No hay activos nuevos/);
    expect((await previsualizarDesdeVsiaf(db, { ruta: raiz })).yaExisten).toBe(48);
  });
});
