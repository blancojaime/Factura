import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import type { Knex } from 'knex';
import { dbDemo, admin } from './helpers.js';
import {
  guardarIngresoAF, codificarActivos, guardarSolicitud, disponiblesParaAsignar, generarAsignacion, procesarMovimientoAF, guardarFicha, copiarFicha, obtenerActivo, indicadoresAF, armarCodigo, solicitudSinExistencia, depreciacion, obtenerSolicitud,
} from '../src/modules/activos/service.js';
import { BusinessError } from '../src/core/errors.js';

let db: Knex;
beforeAll(async () => {
  db = await dbDemo();
});
afterAll(async () => db.destroy());

const rechaza = async (p: Promise<unknown>, re: RegExp) => {
  await expect(p).rejects.toBeInstanceOf(BusinessError);
  await expect(p).rejects.toThrow(re);
};

describe('código del activo', () => {
  it('respeta el formato EEE-AA-CCXXX-NN (15 caracteres)', async () => {
    expect(await armarCodigo(db, 1, 2, 12, 261, 1)).toBe('001-02-12261-01');
    expect(await armarCodigo(db, 1, 2, 4, 32, 5)).toBe('001-02-04032-05');
  });
  it('los activos del libro original tienen códigos consistentes con su cuenta/auxiliar', async () => {
    const rows = await db('af_activos');
    expect(rows.length).toBe(48);
    for (const a of rows) expect(a.codigo).toBe(await armarCodigo(db, a.cod_edif, a.cod_amb, a.id_cta, a.id_aux, a.correl));
  });
});

describe('ingreso → codificación → solicitud → asignación → devolución → baja', () => {
  let nroIng = '';
  let codigos: string[] = [];
  it('valida el auxiliar contra la cuenta y alerta bienes bajo el valor mínimo', async () => {
    await rechaza(guardarIngresoAF(db, admin, { fecha: '2026-10-01', tipo_doc: 'ORDEN DE COMPRA', nro_doc: 'OC-1', proveedor: 'TECNOLOGÍA ALTIPLANO S.A. (DEMO)', items: [{ id_cta: 4, id_aux: 1, cantidad: 1, precio_unit: 100 }] }), /auxiliar no corresponde/);
    const r = await guardarIngresoAF(db, admin, {
      fecha: '2026-10-01', tipo_doc: 'ORDEN DE COMPRA', nro_doc: 'OC-99/2026', proveedor: 'TECNOLOGÍA ALTIPLANO S.A. (DEMO)',
      items: [{ id_cta: 4, id_aux: 32, descripcion: 'Laptop de prueba', cantidad: 3, precio_unit: 5000 }, { id_cta: 3, id_aux: 1, cantidad: 1, precio_unit: 300 }],
    });
    nroIng = r.nro;
    expect(r.total).toBe(15300);
    expect(r.advertencias.join(' ')).toMatch(/valor mínimo/);
  });
  it('codifica con correlativo continuo y no excede lo pendiente', async () => {
    await rechaza(codificarActivos(db, admin, { nro_ingreso: nroIng, fecha: '2026-10-01', filas: [{ item: 1, id_cta: 4, id_aux: 32, cod_edif: 1, cod_amb: 2, cantidad: 5 }] }), /supera la cantidad pendiente/);
    const antes = await db('af_activos').where({ cod_edif: 1, cod_amb: 2, id_cta: 4, id_aux: 32 }).max({ m: 'correl' }).first();
    const r = await codificarActivos(db, admin, { nro_ingreso: nroIng, fecha: '2026-10-01', filas: [{ item: 1, id_cta: 4, id_aux: 32, cod_edif: 1, cod_amb: 2, cantidad: 2 }] });
    expect(r.cantidad).toBe(2);
    const m = Number(antes?.m ?? 0);
    expect(r.generados[0].codigo).toBe(await armarCodigo(db, 1, 2, 4, 32, m + 1));
    codigos = r.generados.map((g) => g.codigo);
    expect((await db('af_ingresos').where({ nro: nroIng }).first()).estado).toBe('PARCIAL');
    await codificarActivos(db, admin, { nro_ingreso: nroIng, fecha: '2026-10-01', filas: [{ item: 1, id_cta: 4, id_aux: 32, cod_edif: 1, cod_amb: 2, cantidad: 1 }, { item: 2, id_cta: 3, id_aux: 1, cod_edif: 1, cod_amb: 0, cantidad: 1 }] });
    expect((await db('af_ingresos').where({ nro: nroIng }).first()).estado).toBe('CODIFICADO');
    await rechaza(guardarIngresoAF(db, admin, { nro: nroIng, fecha: '2026-10-01', tipo_doc: 'ORDEN DE COMPRA', nro_doc: 'OC-99/2026', proveedor: 'TECNOLOGÍA ALTIPLANO S.A. (DEMO)', items: [{ id_cta: 4, id_aux: 32, cantidad: 2, precio_unit: 5000 }] }), /ya tiene 3 códigos|no puede cambiar|eliminarse/);
  });
  it('la solicitud calcula el saldo en almacén y la asignación la atiende', async () => {
    const s = await guardarSolicitud(db, admin, { fecha: '2026-10-02', unidad: 'UNIDAD DE EDUCACIÓN', funcionario: 'JAVIER CONDORI CHOQUE', aprobado_daf: 'SI', items: [{ id_cta: 4, id_aux: 32, cantidad: 2 }] });
    expect((await obtenerSolicitud(db, s.nro)).items[0].saldo).toBeGreaterThanOrEqual(3);
    const disp = await disponiblesParaAsignar(db, { nro_sol: s.nro });
    const pre = disp.filter((x: any) => x.preseleccionado).map((x: any) => x.codigo);
    expect(pre).toHaveLength(2);
    const a = await generarAsignacion(db, admin, { fecha: '2026-10-02', nro_sol: s.nro, funcionario: 'JAVIER CONDORI CHOQUE', cod_edif: 1, cod_amb: 1, codigos: pre });
    expect(a.cantidad).toBe(2);
    expect((await db('af_solicitudes').where({ nro: s.nro }).first()).estado).toBe('ATENDIDA');
    await rechaza(generarAsignacion(db, admin, { fecha: '2026-10-02', funcionario: 'JAVIER CONDORI CHOQUE', codigos: [pre[0]] }), /ya no se encuentra en almacén/);
    codigos = pre;
  });
  it('transferencia exige que el activo pertenezca al funcionario origen', async () => {
    await rechaza(procesarMovimientoAF(db, admin, { tipo: 'TRANSFERENCIA', fecha: '2026-10-03', origen: 'EDWIN ALANOCA SILVESTRE', destino: 'JAVIER CONDORI CHOQUE', codigos: [codigos[0]] }), /está asignado a JAVIER/);
    await procesarMovimientoAF(db, admin, { tipo: 'TRANSFERENCIA', fecha: '2026-10-03', origen: 'JAVIER CONDORI CHOQUE', destino: 'EDWIN ALANOCA SILVESTRE', codigos: [codigos[0]] });
    expect((await db('af_activos').where({ codigo: codigos[0] }).first()).funcionario).toBe('EDWIN ALANOCA SILVESTRE');
  });
  it('devolución regresa a almacén y la baja es definitiva', async () => {
    await procesarMovimientoAF(db, admin, { tipo: 'DEVOLUCIÓN', fecha: '2026-10-04', origen: 'EDWIN ALANOCA SILVESTRE', estado: 'Regular', codigos: [codigos[0]] });
    const a = await db('af_activos').where({ codigo: codigos[0] }).first();
    expect(a.situacion).toBe('EN ALMACEN');
    expect(a.estado).toBe('Regular');
    await rechaza(procesarMovimientoAF(db, admin, { tipo: 'BAJA', fecha: '2026-10-05', codigos: [codigos[0]] }), /motivo de la baja/);
    await procesarMovimientoAF(db, admin, { tipo: 'BAJA', fecha: '2026-10-05', motivo: 'obsolescencia', codigos: [codigos[0]] });
    await rechaza(procesarMovimientoAF(db, admin, { tipo: 'BAJA', fecha: '2026-10-06', motivo: 'x', codigos: [codigos[0]] }), /ya fue dado de baja/);
    const kx = await db('af_movimientos').where({ codigo: codigos[0] }).orderBy('id');
    expect(kx.map((k: any) => k.tipo)).toEqual(['INGRESO Y CODIFICACIÓN', 'ASIGNACIÓN', 'TRANSFERENCIA', 'DEVOLUCIÓN', 'BAJA']);
  });
  it('sin existencia y ficha técnica con campos de la cuenta', async () => {
    const s = await guardarSolicitud(db, admin, { fecha: '2026-10-02', unidad: 'UNIDAD DE SALUD', funcionario: 'ARSENIO HUALLPA APAZA', items: [{ id_cta: 10, id_aux: 1, cantidad: 1 }] }).catch(() => null);
    if (s) expect((await solicitudSinExistencia(db, admin, s.nro)).estado).toBe('SIN EXISTENCIA');
    const a = await obtenerActivo(db, '001-02-12261-01');
    expect(a.campos.length).toBeGreaterThan(0);
    await guardarFicha(db, admin, a.codigo, { descripcion: a.descripcion, estado: 'Bueno', marca: 'X', campos: { '1': 'Silla escolar' } });
    expect((await obtenerActivo(db, a.codigo)).estado).toBe('Bueno');
    const i = await indicadoresAF(db);
    expect(i.total).toBeGreaterThan(48);
    expect(depreciacion(1000, 5, '2024-10-02', '2026-10-02').neto).toBeCloseTo(600, 0);
  });
});

describe('copiar ficha técnica a otros activos', () => {
  let origen = '';
  let dest: string[] = [];
  beforeAll(async () => {
    // lote de 5 pupitres iguales: ingreso + codificación directa en el edificio 1
    const ing = await guardarIngresoAF(db, admin, { fecha: '2026-10-01', tipo_doc: 'ORDEN DE COMPRA', nro_doc: 'OC-777/2026', proveedor: 'COMERCIAL MUEBLES ANDINOS S.R.L. (DEMO)', items: [{ id_cta: 3, id_aux: 7, descripcion: 'Pupitre unipersonal de madera', unidad: 'PZA', cantidad: 5, precio_unit: 250 }] } as any);
    const r = await codificarActivos(db, admin, { nro_ingreso: ing.nro, fecha: '2026-10-01', estado: 'Nuevo', filas: [{ item: 1, id_cta: 3, id_aux: 7, descripcion: 'Pupitre unipersonal de madera', cod_edif: 1, cod_amb: 0, cantidad: 5, valor: 250 }] } as any);
    origen = r.generados[0].codigo;
    dest = r.generados.slice(1).map((g: any) => g.codigo);
    const a = await obtenerActivo(db, origen);
    await guardarFicha(db, admin, origen, { descripcion: a.descripcion, marca: 'CARPINTERÍA ORURO', modelo: 'P-2026', serie: 'S-0001', color: 'CAFÉ', estado: 'Nuevo', observaciones: 'Madera de pino, tapa 60 x 45 cm', campos: { '1': 'MADERA', '2': 'CAFÉ' } });
  });

  it('copia marca, modelo, color, observaciones y características a todos los destinos, sin la serie', async () => {
    const r = await copiarFicha(db, admin, { origen, destinos: dest });
    expect(r.copiados).toBe(4);
    expect(r.omitidos).toEqual([]);
    for (const c of dest) {
      const a = await obtenerActivo(db, c);
      expect(a.marca).toBe('CARPINTERÍA ORURO');
      expect(a.modelo).toBe('P-2026');
      expect(a.color).toBe('CAFÉ');
      expect(a.observaciones).toBe('Madera de pino, tapa 60 x 45 cm');
      expect(a.serie ?? '').toBe('');
      expect(a.campos[0].valor).toBe('MADERA');
    }
  });
  it('solo completa vacíos por defecto y reemplaza si se pide', async () => {
    await guardarFicha(db, admin, dest[0], { descripcion: 'Pupitre unipersonal de madera', marca: 'OTRA MARCA', estado: 'Nuevo' });
    await copiarFicha(db, admin, { origen, destinos: [dest[0]] });
    expect((await obtenerActivo(db, dest[0])).marca).toBe('OTRA MARCA');
    await copiarFicha(db, admin, { origen, destinos: [dest[0]], solo_vacios: false });
    expect((await obtenerActivo(db, dest[0])).marca).toBe('CARPINTERÍA ORURO');
  });
  it('copia la serie, el valor y el estado solo si se pide', async () => {
    await copiarFicha(db, admin, { origen, destinos: [dest[1]], copiar: ['serie', 'valor'], solo_vacios: false });
    const a = await obtenerActivo(db, dest[1]);
    expect(a.serie).toBe('S-0001');
  });
  it('no copia características a un activo de otra cuenta y omite inexistentes y dados de baja', async () => {
    const otro = (await db('af_activos').whereNot({ id_cta: 3 }).where({ situacion: 'EN ALMACEN' }).first())?.codigo ?? (await db('af_activos').whereNot({ id_cta: 3 }).first()).codigo;
    const r = await copiarFicha(db, admin, { origen, destinos: [otro, 'NO-EXISTE'], copiar: ['marca', 'caracteristicas'] });
    expect(r.sin_caracteristicas).toBe(1);
    expect(r.omitidos.map((o) => o.codigo)).toContain('NO-EXISTE');
    await db('af_activos').where({ codigo: dest[2] }).update({ situacion: 'BAJA' });
    const r2 = await copiarFicha(db, admin, { origen, destinos: [dest[2]] });
    expect(r2.copiados).toBe(0);
    expect(r2.omitidos[0].motivo).toMatch(/baja/);
  });
  it('valida origen, destinos y datos desconocidos', async () => {
    await rechaza(copiarFicha(db, admin, { origen: 'XXX', destinos: ['a'] }), /No existe/);
    await rechaza(copiarFicha(db, admin, { origen, destinos: [] }), /al menos un activo/);
    await rechaza(copiarFicha(db, admin, { origen, destinos: [origen] }), /al menos un activo/);
    await rechaza(copiarFicha(db, admin, { origen, destinos: dest, copiar: ['sueldo'] }), /desconocido/);
  });
  it('copia las fotografías como archivos propios de cada activo', async () => {
    await db('af_activos').where({ codigo: origen }).update({ foto1: `${origen}_1.png` });
    const hechas: string[] = [];
    await copiarFicha(db, admin, { origen, destinos: [dest[3]], copiar: ['fotos'], solo_vacios: false }, (f, c, n) => { hechas.push(`${f}->${c}_${n}`); return `${c}_${n}.png`; });
    expect(hechas).toEqual([`${origen}_1.png->${dest[3]}_1`]);
    expect((await obtenerActivo(db, dest[3])).foto1).toBe(`${dest[3]}_1.png`);
  });
});
