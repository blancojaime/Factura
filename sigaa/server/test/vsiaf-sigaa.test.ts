import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { FastifyInstance } from 'fastify';
import { dbDemo, admin } from './helpers.js';
import { buildApp } from '../src/app.js';
import { procesarMovimientoAF, guardarIngresoAF, codificarActivos } from '../src/modules/activos/service.js';
import { crearInstalacionSintetica, BdVsiaf } from '../src/vsiaf/index.js';
import { SIN_FUENTE } from '../src/vsiaf/adaptador.js';
import { guardarEquivalencias, importarLote, validarLote, listarLotes, seleccionVsiaf, enviosDeActivo, infoDestino, guardarConfigVsiaf } from '../src/vsiaf/servicio.js';
import { BusinessError } from '../src/core/errors.js';

let db: Awaited<ReturnType<typeof dbDemo>>;
let raiz = '';
const HOY = '2026-10-21';
const base = () => ({ ruta: raiz, unidad: '1', hoy: HOY, fechaCalculo: HOY, omitirProceso: true, permitirIncorporacionEspecial: false });
const filasActual = () => [...new BdVsiaf(raiz).tabla('ACTUAL').registros(true)];
const rechaza = async (p: Promise<unknown>, re: RegExp) => { await expect(p).rejects.toBeInstanceOf(BusinessError); await expect(p).rejects.toThrow(re); };

beforeAll(async () => {
  db = await dbDemo();
  raiz = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'vsiaf-sigaa-')), 'vsiaf');
  crearInstalacionSintetica(raiz);
});
afterAll(async () => db.destroy());

describe('envío de los activos de SIGAA al VSIAF (datos de demostración)', () => {
  it('sin equivalencias: faltan los organismos financiadores y se informa con sugerencias', async () => {
    const v = await validarLote(db, admin, base());
    expect(v.sinErrores).toBe(false);
    expect(v.resumen.activos).toBe(48);
    const claves = v.faltantes.filter((f) => f.tipo === 'org_fin').map((f) => f.clave).sort();
    expect(claves).toEqual(['41/113', 'RECURSOS ESPECÍFICOS']);
    expect(v.faltantes.find((f) => f.clave === '41/113')?.sugerencia).toBe('113');
    const inc = v.incidencias.filter((i) => i.nivel === 'ERROR');
    expect(inc.length).toBeGreaterThan(0);
    expect(inc.every((i) => i.codigo && /organismo|obligatorio/i.test(i.mensaje + i.etiqueta))).toBe(true);
    expect(() => fs.readdirSync(path.join(raiz, 'dbfs'))).not.toThrow();
    expect(filasActual().length).toBe(0); // validar no escribe
  });

  it('las equivalencias se validan y se guardan', async () => {
    await rechaza(guardarEquivalencias(db, admin, [{ tipo: 'org_fin', clave: 'X', valor: '99' }]), /3 dígitos/);
    await rechaza(guardarEquivalencias(db, admin, [{ tipo: 'raro', clave: 'X', valor: 'Y' }]), /desconocido/);
    await rechaza(guardarEquivalencias(db, admin, [{ tipo: 'estado', clave: 'Nuevo', valor: 'Excelente' }]), /Bueno, Regular o Malo/);
    const r = await guardarEquivalencias(db, admin, [
      { tipo: 'org_fin', clave: 'RECURSOS ESPECÍFICOS', valor: '111' }, { tipo: 'org_fin', clave: '41/113', valor: '113' }, { tipo: 'org_fin', clave: SIN_FUENTE, valor: '111' },
    ]);
    expect(r.length).toBe(3);
  });

  it('con equivalencias el envío valida sin errores y calcula la vista previa y los totales por grupo', async () => {
    const v = await validarLote(db, admin, base());
    expect(v.errores, JSON.stringify(v.incidencias.filter((i) => i.nivel === 'ERROR').slice(0, 5))).toBe(0);
    expect(v.conteos.ACTIVOS).toBe(48);
    expect(v.calculos.ACTIVOS.length).toBe(48);
    const total = v.totalesPorGrupo.reduce((t: number, g: any) => t + g.costo_historico, 0);
    const sigaa = (await db('af_activos').sum({ s: 'valor' }).first()) as any;
    expect(Math.abs(total - Number(sigaa.s))).toBeLessThan(0.01);
    expect(v.totalesPorGrupo.every((g: any) => g.grupo && g.cantidad > 0)).toBe(true);
    // los activos EN ALMACÉN van a la oficina «ALMACÉN»
    expect(v.resumen.oficinas).toBeGreaterThan(1);
    expect(v.pasoFinal).toMatch(/Re-indexar/);
  });

  it('importar exige confirmación y escribe los 48 activos con sus maestros', async () => {
    await rechaza(importarLote(db, admin, { ...base(), estadoRegistro: 'APROBADO' }), /Confirme/);
    const r = await importarLote(db, admin, { ...base(), estadoRegistro: 'APROBADO', confirmar: true });
    expect(r.conteos.ACTIVOS).toBe(48);
    expect(r.respaldo).toMatch(/VSIMPXL/);
    const filas = filasActual();
    expect(filas.length).toBe(48);
    const v = filas[0].valores as any;
    expect(v).toMatchObject({ ENTIDAD: '9999', UNIDAD: '1', API_ESTADO: 3, B_REV: false, BANDERAS: '0' });
    const bd = new BdVsiaf(raiz);
    const ofis = [...bd.tabla('OFICINA').registros()].map((x) => String(x.valores.NOMOFIC));
    expect(ofis).toContain('ALMACÉN');
    expect(ofis.some((o) => o.includes(' / '))).toBe(true);
    const lotes = await listarLotes(db);
    expect(lotes[0]).toMatchObject({ resultado: 'IMPORTADO', unidad: '1' });
    expect((await db('af_vsiaf_envios').where({ tipo: 'ACTIVO' })).length).toBe(48);
    const obs = filas.map((f) => String(f.valores.OBSERV ?? '')).find((o) => o.includes('Ingreso ING-'));
    expect(obs).toBeTruthy();
  });

  it('un activo ya enviado no se reenvía: no queda nada pendiente', async () => {
    const v = await validarLote(db, admin, base());
    expect(v.resumen.activos).toBe(0);
    await rechaza(importarLote(db, admin, { ...base(), confirmar: true }), /nada que enviar/);
    expect((await seleccionVsiaf(db, {})).length).toBe(0);
    expect((await seleccionVsiaf(db, { estado: 'ENVIADOS' })).length).toBe(48);
    expect((await enviosDeActivo(db, '001-02-12261-01')).length).toBe(1);
  });

  it('un cambio de responsable en SIGAA viaja como transferencia', async () => {
    const a = await db('af_activos').where({ situacion: 'ASIGNADO' }).first();
    const otro = await db('core_funcionarios').whereNot({ nombre: a.funcionario }).first();
    await procesarMovimientoAF(db, admin, { tipo: 'TRANSFERENCIA', fecha: '2026-10-20', origen: a.funcionario, destino: otro.nombre, codigos: [a.codigo], motivo: 'Cambio de cargo' });
    const v = await validarLote(db, admin, base());
    expect(v.resumen.transferencias).toBe(1);
    expect(v.errores, JSON.stringify(v.incidencias.filter((i) => i.nivel === 'ERROR'))).toBe(0);
    await importarLote(db, admin, { ...base(), confirmar: true });
    const tr = [...new BdVsiaf(raiz).tabla('TRASFE').registros()];
    expect(tr.length).toBe(1);
    expect(String(tr[0].valores.CODIGO)).toBe(a.codigo);
    expect((await validarLote(db, admin, base())).resumen.transferencias).toBe(0);
    expect((await enviosDeActivo(db, a.codigo)).map((e: any) => e.tipo)).toEqual(['ACTIVO', 'TRANSFERENCIA']);
  });

  it('la baja exige resolución y motivo (1–9) y se envía como BAJA', async () => {
    const a = await db('af_activos').where({ situacion: 'ASIGNADO' }).whereNot({ codigo: (await db('af_activos').where({ situacion: 'ASIGNADO' }).first()).codigo }).first();
    await rechaza(procesarMovimientoAF(db, admin, { tipo: 'BAJA', fecha: '2026-10-21', codigos: [a.codigo], motivo: 'Inutilizable', resolucion: 'R'.repeat(17) }), /16 caracteres/);
    await rechaza(procesarMovimientoAF(db, admin, { tipo: 'BAJA', fecha: '2026-10-21', codigos: [a.codigo], motivo: 'Inutilizable', motivo_cod: 12 }), /1 al 9/);
    // sin resolución ni motivo del VSIAF: el envío lo detecta
    const b = await db('af_activos').where({ situacion: 'ASIGNADO' }).whereNot({ codigo: a.codigo }).whereNot({ funcionario: null }).first();
    await procesarMovimientoAF(db, admin, { tipo: 'BAJA', fecha: '2026-10-21', codigos: [b.codigo], motivo: 'Sin dato' });
    let v = await validarLote(db, admin, base());
    expect(v.resumen.bajas).toBe(1);
    expect(v.faltantes.map((f) => f.tipo)).toEqual(expect.arrayContaining(['baja_resolucion', 'baja_motivo']));
    expect(v.sinErrores).toBe(false);
    // se corrige en SIGAA: segunda baja completa
    await procesarMovimientoAF(db, admin, { tipo: 'BAJA', fecha: '2026-10-21', codigos: [a.codigo], motivo: 'Deterioro irreparable', resolucion: 'RA-45/2026', motivo_cod: 5 });
    await db('af_movimientos').where({ codigo: b.codigo, tipo: 'BAJA' }).update({ resolucion: 'RA-46/2026', motivo_cod: 6 });
    v = await validarLote(db, admin, base());
    expect(v.errores, JSON.stringify(v.incidencias.filter((i) => i.nivel === 'ERROR'))).toBe(0);
    const r = await importarLote(db, admin, { ...base(), confirmar: true });
    expect(r.conteos.BAJAS).toBe(2);
    const bajas = [...new BdVsiaf(raiz).tabla('BAJAS').registros()].map((x) => x.valores as any);
    expect(bajas.find((x) => x.CODIGO === a.codigo)).toMatchObject({ CODBAJA: 5, RESOLUCION: 'RA-45/2026', OBSERV: 'DADO DE BAJA', MOTIVO: 'Deterioro irreparable' });
    const borrados = filasActual().filter((x) => x.borrado).map((x) => x.valores.CODIGO);
    expect(borrados).toEqual(expect.arrayContaining([a.codigo, b.codigo]));
  });

  it('un activo nuevo de SIGAA viaja solo en el siguiente envío', async () => {
    const ing = await guardarIngresoAF(db, admin, { fecha: '2026-10-21', tipo_doc: 'ORDEN DE COMPRA', nro_doc: 'OC-9/2026', proveedor: 'COMERCIAL MUEBLES ANDINOS S.R.L. (DEMO)', org_fin: '113', items: [{ id_cta: 3, id_aux: 7, descripcion: 'Pupitre', cantidad: 2, precio_unit: 300 }] } as any);
    await codificarActivos(db, admin, { nro_ingreso: ing.nro, fecha: '2026-10-21', estado: 'Nuevo', filas: [{ item: 1, id_cta: 3, id_aux: 7, descripcion: 'Pupitre', cod_edif: 1, cod_amb: 0, cantidad: 2, valor: 300 }] } as any);
    const v = await validarLote(db, admin, base());
    expect(v.resumen.activos).toBe(2);
    expect(v.errores, JSON.stringify(v.incidencias.filter((i) => i.nivel === 'ERROR'))).toBe(0); // el organismo viene del propio ingreso (org_fin)
    await importarLote(db, admin, { ...base(), confirmar: true });
    expect(filasActual().length).toBe(50);
  });

  it('la configuración y el destino se leen; una carpeta que no es del VSIAF da un mensaje claro', async () => {
    await guardarConfigVsiaf(db, admin, { ruta: raiz, unidad: '1', usuario: 'admin' });
    const d: any = await infoDestino(db);
    expect(d).toMatchObject({ encontrada: true, entidad: '9999', gestionCerrada: false });
    expect(d.unidades[0].unidad).toBe('1');
    const mal: any = await infoDestino(db, os.tmpdir());
    expect(mal.encontrada).toBe(false);
    await rechaza(guardarConfigVsiaf(db, admin, { unidad: '1234567' }), /5 caracteres/);
  });
});

describe('API /api/af/vsiaf: permisos', () => {
  let app: FastifyInstance;
  let dbA: Awaited<ReturnType<typeof dbDemo>>;
  const H = (t: string) => ({ authorization: `Bearer ${t}` });
  const login = async (usuario: string, clave: string) => (await app.inject({ method: 'POST', url: '/api/auth/login', payload: { usuario, clave } })).json().token as string;
  beforeAll(async () => {
    dbA = await dbDemo();
    app = await buildApp({ db: dbA, jwtSecret: 'test-secret', webDir: '/nonexistent' });
    await dbA('core_usuarios').update({ debe_cambiar: false });
  });
  afterAll(async () => { await app.close(); await dbA.destroy(); });

  it('solo Activos Fijos (o ADMIN) valida e importa; los demás roles no', async () => {
    for (const [u, c] of [['consulta', 'Consulta2026'], ['almacen', 'Almacen2026'], ['combustible', 'Combustible2026']]) {
      const t = await login(u, c);
      expect((await app.inject({ method: 'POST', url: '/api/af/vsiaf/validar', headers: H(t), payload: {} })).statusCode, u).toBe(403);
      expect((await app.inject({ method: 'PUT', url: '/api/af/vsiaf/equivalencias', headers: H(t), payload: { items: [] } })).statusCode, u).toBe(403);
      expect((await app.inject({ url: '/api/af/vsiaf/lotes', headers: H(t) })).statusCode, u).toBe(200); // consultar sí
    }
    const ta = await login('activos', 'Activos2026');
    const r = await app.inject({ method: 'PUT', url: '/api/af/vsiaf/equivalencias', headers: H(ta), payload: { items: [{ tipo: 'org_fin', clave: '41/113', valor: '113' }] } });
    expect(r.statusCode).toBe(200);
    expect(r.json().items.length).toBe(1);
    const p = await app.inject({ method: 'POST', url: '/api/af/vsiaf/pendientes', headers: H(ta), payload: { unidad: '1' } });
    expect(p.statusCode).toBe(200);
    expect(p.json().resumen.activos).toBe(48);
    expect((await app.inject({ method: 'POST', url: '/api/af/vsiaf/importar', headers: H(ta), payload: { ruta: os.tmpdir() } })).statusCode).toBe(422);
  });
});

describe('migración de bases existentes', () => {
  it.skipIf(!!process.env.TEST_DATABASE_URL)('createSchema agrega las columnas nuevas a una base que ya existía', async () => {
    const d = await dbDemo();
    await d.schema.alterTable('af_movimientos', (t) => { t.dropColumn('resolucion'); t.dropColumn('motivo_cod'); });
    await d.schema.alterTable('af_ingresos', (t) => t.dropColumn('org_fin'));
    expect(await d.schema.hasColumn('af_movimientos', 'resolucion')).toBe(false);
    const { createSchema } = await import('../src/db/schema.js');
    await createSchema(d);
    expect(await d.schema.hasColumn('af_movimientos', 'resolucion')).toBe(true);
    expect(await d.schema.hasColumn('af_movimientos', 'motivo_cod')).toBe(true);
    expect(await d.schema.hasColumn('af_ingresos', 'org_fin')).toBe(true);
    await d.destroy();
  });
});
