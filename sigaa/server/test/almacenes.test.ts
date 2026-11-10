import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import type { Knex } from 'knex';
import { dbDemo, admin } from './helpers.js';
import { stockDe, precioPromedio, kardex, consumirPEPS, altaLote } from '../src/modules/almacenes/stock.js';
import { guardarIngreso, confirmarIngreso, anularIngreso } from '../src/modules/almacenes/ingresos.js';
import { guardarSalida, aprobarSalida, entregarSalida, anularSalida, reglasPedido } from '../src/modules/almacenes/salidas.js';
import { nuevoInventario, guardarConteo, cerrarInventario, ingresarSobrantes } from '../src/modules/almacenes/inventarios.js';
import { guardarBaja, ejecutarBaja } from '../src/modules/almacenes/bajas.js';
import { guardarTransferencia, ejecutarTransferencia, calcularReposicion, verificarCierre } from '../src/modules/almacenes/otros.js';
import { BusinessError } from '../src/core/errors.js';

let db: Knex;
beforeAll(async () => {
  db = await dbDemo();
});
afterAll(async () => {
  await db.destroy();
});

const rechaza = async (p: Promise<unknown>, re: RegExp) => {
  await expect(p).rejects.toBeInstanceOf(BusinessError);
  await expect(p).rejects.toThrow(re);
};

describe('datos demo importados', () => {
  it('el kardex de cada ítem coincide con los lotes (integridad)', async () => {
    const c = await verificarCierre(db);
    expect(c.find((x) => x.n === 10)?.resultado).toBe('OK');
  });
  it('mantiene los saldos del libro original', async () => {
    expect(await stockDe(db, '01', '1-2-0000001')).toBe(286); // BOLÍGRAFO (inventario INV-0001)
    expect(await stockDe(db, '01', '1-1-0000001')).toBe(70);
  });
});

describe('ingreso → salida → anulación', () => {
  const cod = '1-1-0000003'; // CARTULINA, bodega 01
  it('rechaza un ingreso de compra sin factura', async () => {
    await rechaza(
      guardarIngreso(db, admin, { fecha: '2026-10-01', cod_bod: '01', tipo: 'COMPRA (ORDEN DE COMPRA / CONTRATO)', proveedor: 'COMERCIAL SAN MARTÍN', nro_oc: 'OC-1', unidad: 'UNIDAD DE BIENES Y SERVICIOS', items: [{ cod_item: cod, cantidad: 5, precio_unit: 25 }] }),
      /factura/i,
    );
  });
  it('un ingreso no suma existencias hasta confirmarse y exige documentos obligatorios', async () => {
    const antes = await stockDe(db, '01', cod);
    const r = await guardarIngreso(db, admin, {
      fecha: '2026-10-01', cod_bod: '01', tipo: 'COMPRA (ORDEN DE COMPRA / CONTRATO)', proveedor: 'COMERCIAL SAN MARTÍN', nro_oc: 'OC-100/2026', factura: '9988', unidad: 'UNIDAD DE BIENES Y SERVICIOS',
      items: [{ cod_item: cod, cantidad: 10, precio_unit: 30 }],
    });
    expect(await stockDe(db, '01', cod)).toBe(antes);
    await rechaza(confirmarIngreso(db, admin, r.nro), /documentos de respaldo obligatorios/);
    const docs = (await db('alm_ingresos_doc').where({ nro: r.nro })).map((d: any) => ({ documento: d.documento, estado: 'SI' }));
    await guardarIngreso(db, admin, {
      nro: r.nro, fecha: '2026-10-01', cod_bod: '01', tipo: 'COMPRA (ORDEN DE COMPRA / CONTRATO)', proveedor: 'COMERCIAL SAN MARTÍN', nro_oc: 'OC-100/2026', factura: '9988', unidad: 'UNIDAD DE BIENES Y SERVICIOS',
      items: [{ cod_item: cod, cantidad: 10, precio_unit: 30 }], docs,
    });
    await confirmarIngreso(db, admin, r.nro);
    expect(await stockDe(db, '01', cod)).toBe(antes + 10);
    // promedio ponderado: 14 a 25 + 10 a 30
    expect(await precioPromedio(db, '01', cod)).toBeCloseTo((14 * 25 + 10 * 30) / 24, 3);
    (globalThis as any).__cgi = r.nro;
  });
  it('el pedido de salida exige aprobación previa y descarga por PEPS', async () => {
    const s = await guardarSalida(db, admin, {
      fecha_pedido: '2026-10-05', cod_bod: '01', unidad: 'UNIDAD DE EDUCACIÓN', solicitante: 'ANA MARÍA QUISPE LIMACHI', superior: 'LUCIANA CRUZ VARGAS', justificacion: 'Prueba',
      items: [{ cod_item: cod, cant_pedida: 16 }],
    });
    await rechaza(entregarSalida(db, admin, s.nro), /APROBADO/);
    await aprobarSalida(db, admin, s.nro);
    const r = await entregarSalida(db, admin, s.nro);
    // 14 del lote antiguo a Bs 25 y 2 del nuevo a Bs 30
    expect(r.total).toBe(14 * 25 + 2 * 30);
    const k = await kardex(db, '01', cod, '2026-01-01', '2026-12-31');
    expect(k[k.length - 1].saldoCant).toBe(8);
    await anularSalida(db, admin, s.nro, 'error de registro');
    expect(await stockDe(db, '01', cod)).toBe(24);
  });
  it('no permite anular un ingreso con salidas posteriores', async () => {
    const nro = (globalThis as any).__cgi as string;
    const lote = await db('alm_lotes').where({ doc_origen: nro }).first();
    await consumirPEPS(db, 'admin', { bod: '01', cod, cant: 1, fecha: '2026-10-06', tipoMov: 'SALIDA', doc: 'X-1', refer: '', idLote: lote.id_lote });
    await rechaza(anularIngreso(db, admin, nro, 'prueba'), /salidas|bajas/);
  });
});

describe('reglas de pedido (Manual)', () => {
  it('advierte pedidos fuera del plazo o repetidos en el mes', async () => {
    const w = await reglasPedido(db, '2026-09-28', 'CARLOS HUANCA MAMANI', 'VS-9999/2026');
    expect(w.join('|')).toMatch(/fuera del plazo/);
    expect(w.join('|')).toMatch(/ya tiene/);
  });
  it('un pedido que incumple exige la excepción autorizada', async () => {
    await rechaza(
      guardarSalida(db, admin, { fecha_pedido: '2026-10-30', cod_bod: '03', unidad: 'UNIDAD DE OBRAS PÚBLICAS', solicitante: 'CARLOS HUANCA MAMANI', superior: 'PEDRO APAZA ROJAS', justificacion: 'x', items: [{ cod_item: '4-1-0000001', cant_pedida: 2 }] }),
      /no cumple las reglas/,
    );
  });
});

describe('FEFO: no entrega lotes vencidos', () => {
  it('prioriza el vencimiento más próximo y excluye vencidos', async () => {
    const cod2 = '5-2-0000003'; // guantes, bodega 04
    const base = await stockDe(db, '04', cod2);
    await altaLote(db, 'admin', { bod: '04', cod: cod2, docOrigen: 'T-1', fechaIng: '2026-01-01', venc: '2026-02-01', cant: 5, pu: 1, tipoMov: 'INGRESO', refer: '' });
    await altaLote(db, 'admin', { bod: '04', cod: cod2, docOrigen: 'T-2', fechaIng: '2026-01-02', venc: '2027-06-01', cant: 5, pu: 2, tipoMov: 'INGRESO', refer: '' });
    await altaLote(db, 'admin', { bod: '04', cod: cod2, docOrigen: 'T-3', fechaIng: '2026-01-03', venc: '2026-12-01', cant: 5, pu: 3, tipoMov: 'INGRESO', refer: '' });
    const imp = await consumirPEPS(db, 'admin', { bod: '04', cod: cod2, cant: 7, fecha: '2026-10-02', tipoMov: 'SALIDA', doc: 'T-S', refer: '' });
    expect(imp).toBe(5 * 3 + 2 * 2); // el lote vencido (T-1) se salta; primero 2026-12, luego 2027-06
    await rechaza(consumirPEPS(db, 'admin', { bod: '04', cod: cod2, cant: base + 100, fecha: '2026-10-02', tipoMov: 'SALIDA', doc: 'T-S2', refer: '' }), /insuficiente/);
  });
});

describe('inventario físico', () => {
  it('cierra con diferencias y genera el ingreso de sobrantes valorado al último precio', async () => {
    const inv = await nuevoInventario(db, admin, { fecha: '2026-10-07', cod_bod: '02', tipo: 'PROGRAMADO' });
    await rechaza(cerrarInventario(db, admin, inv.nro), /por contar/);
    const det = await db('alm_inventarios_det').where({ nro: inv.nro });
    await guardarConteo(db, admin, inv.nro, det.map((x: any, i: number) => ({ cod_item: x.cod_item, conteo: Number(x.saldo_sist) + (i === 0 ? 2 : 0) })));
    const cerrado = await cerrarInventario(db, admin, inv.nro);
    expect(cerrado.sobrante_bs).toBeGreaterThan(0);
    const s = await ingresarSobrantes(db, admin, inv.nro);
    expect(s.cgi).toMatch(/^CGI-/);
    await rechaza(ingresarSobrantes(db, admin, inv.nro), /ya generaron/);
  });
});

describe('transferencias y reposición', () => {
  it('transfiere conservando lotes y costo', async () => {
    const cod = '4-3-0000001';
    const o = await stockDe(db, '03', cod);
    const t = await guardarTransferencia(db, admin, { fecha: '2026-10-02', bod_origen: '03', bod_destino: '02', entrega: 'A', recibe: 'B', motivo: 'obra', items: [{ cod_item: cod, cantidad: 1 }] });
    await ejecutarTransferencia(db, admin, t.nro);
    expect(await stockDe(db, '03', cod)).toBe(o - 1);
    const rep = await calcularReposicion(db);
    expect(Array.isArray(rep)).toBe(true);
    const c = await verificarCierre(db);
    expect(c.find((x) => x.n === 10)?.resultado).toBe('OK');
  });
});

describe('baja de existencias', () => {
  it('exige resolución administrativa y pasos obligatorios', async () => {
    const b = await guardarBaja(db, admin, {
      fecha: '2026-10-02', cod_bod: '01', causal: 'Merma', responsable: 'MARIO', justificacion: 'merma natural', items: [{ cod_item: '1-1-0000002', cantidad: 2 }],
    });
    await rechaza(ejecutarBaja(db, admin, b.nro), /Resolución Administrativa/);
  });
});
