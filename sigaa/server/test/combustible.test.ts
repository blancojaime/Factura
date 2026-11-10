import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import type { Knex } from 'knex';
import { dbDemo, admin } from './helpers.js';
import { registrarRecepcion, emitirVales, registrarDescargo, movimientoPorRango, anularEmision, resumenVales, rangosTexto } from '../src/modules/combustible/vales.js';
import { ingresoTurril, despachoTurril, conciliarProveedor, registrarViaje, descargoViaje, tablero } from '../src/modules/combustible/otros.js';
import { litrosMaximos, saldoTurril } from '../src/modules/combustible/base.js';
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

const EMI = (extra: any = {}) => ({
  fecha: '2026-09-28', destino: 'VEHICULO' as const, placa: '2345ABC', lectura: 1000, conductor: 'JOSÉ LUIS MAMANI CHOQUE', solicitante: 'Jefe', unidad: 'DESPACHO DEL EJECUTIVO MUNICIPAL',
  apertura: '00 0 001', trabajo: 'Comisión', desde: '2026-09-28', hasta: '2026-10-03', cantidades: { '30': 5 }, ...extra,
});

describe('utilidades', () => {
  it('compacta rangos de numeración', () => {
    expect(rangosTexto([5, 1, 2, 3, 9, 10])).toBe('1-3, 5, 9-10');
  });
  it('litros máximos de uso ejecutivo = días hábiles (lun-sáb) × 16 L', async () => {
    // 28/09/2026 (lunes) a 03/10 (sábado) = 6 días
    expect(await litrosMaximos(db, { placa: '2345ABC', destino: 'VEHICULO', desde: '2026-09-28', hasta: '2026-10-03' })).toBe(96);
    // el domingo no cuenta
    expect(await litrosMaximos(db, { placa: '2345ABC', destino: 'VEHICULO', desde: '2026-09-28', hasta: '2026-10-04' })).toBe(96);
  });
});

describe('ciclo del vale: recepción → emisión → descargo → conciliación', () => {
  it('recibe un lote validando contrato y numeración', async () => {
    await rechaza(registrarRecepcion(db, admin, { fecha: '2026-09-27', nro_contrato: 'GAMC-CONT-001/2026', filas: [{ corte: 30, desde: 1, hasta: 10 }] }), /factura es obligatoria/);
    const r = await registrarRecepcion(db, admin, { fecha: '2026-09-27', nro_contrato: 'GAMC-CONT-001/2026', factura: 'F-100', filas: [{ corte: 30, desde: 1001, hasta: 1020 }, { corte: 50, desde: 2001, hasta: 2010 }] });
    expect(r.cantidad).toBe(30);
    expect(r.monto).toBe(20 * 30 + 10 * 50);
    await rechaza(registrarRecepcion(db, admin, { fecha: '2026-09-27', nro_contrato: 'GAMC-CONT-001/2026', factura: 'F-101', filas: [{ corte: 30, desde: 1015, hasta: 1025 }] }), /duplicada/);
    const ct = await db('com_contratos').where({ nro: 'GAMC-CONT-001/2026' }).first();
    expect(Number(ct.saldo)).toBe(50000 - 1100);
    await rechaza(registrarRecepcion(db, admin, { fecha: '2026-09-27', nro_contrato: 'GAMC-CONT-001/2026', factura: 'F-102', filas: [{ corte: 100, desde: 1, hasta: 1000 }] }), /supera el saldo/);
  });

  it('bloquea excedentes de litros sin justificación y emite con el vale correcto', async () => {
    // 100 vales... Bs 30 × 5 = 150 Bs ≈ 21.55 L (< 96 L): válido
    await rechaza(emitirVales(db, admin, EMI({ cantidades: { '30': 30 } })), /Solo hay 20 vales/);
    const r = await emitirVales(db, admin, EMI());
    expect(r.ok).toBe(true);
    expect(r.data!.monto).toBe(150);
    expect(r.data!.litros).toBeCloseTo(150 / 6.96, 2);
    expect(r.data!.detalle).toContain('1001-1005');
    (globalThis as any).__em = r.data!.nro;
    const sal = await db('com_kardex').where({ documento: r.data!.nro, tipo: 'SALIDA' }).first();
    expect(Number(sal.salida)).toBe(5);
  });

  it('el descargo exige vales de la emisión y marca el rendimiento fuera de tolerancia', async () => {
    const nro = (globalThis as any).__em as string;
    const base = { nro_emision: nro, fecha: '2026-10-03', devolver_automaticamente: true };
    // vale ajeno
    await rechaza(
      registrarDescargo(db, admin, { ...base, lineas: [{ fecha: '2026-09-29', lectura_salida: 1000, lectura_llegada: 1100, nro_vale: 1010, litros: 20, factura: 'A' }] }),
      /NO fue entregado/,
    );
    // lectura retrocede
    await rechaza(registrarDescargo(db, admin, { ...base, lineas: [{ fecha: '2026-09-29', lectura_salida: 900, lectura_llegada: 1000, nro_vale: 1001, litros: 21.5, factura: 'A' }] }), /MENOR que la última lectura/);
    // rendimiento: 21.5 L en 100 km = 0.215 L/km vs ref 0.12 (+79%) → requiere confirmar y queda Observado
    const lineas = [
      { fecha: '2026-09-29', lectura_salida: 1000, lectura_llegada: 1100, nro_vale: 1001, litros: 21.55, factura: 'F1', estacion: 'EESS' },
      { fecha: '2026-09-30', lectura_salida: 1100, lectura_llegada: 1100, nro_vale: 1002, litros: 21.55, factura: 'F2', estacion: 'EESS' },
    ];
    const p = await registrarDescargo(db, admin, { ...base, lineas });
    expect(p.ok).toBe(false);
    expect(p.requiereConfirmacion).toBe(true);
    expect(p.advertencias!.join(' ')).toMatch(/RENDIMIENTO FUERA DE TOLERANCIA/);
    const r = await registrarDescargo(db, admin, { ...base, lineas, confirmar: true });
    expect(r.data!.estado).toBe('Observado');
    const est = await db('com_vales').where({ proveedor: 'ESTACIÓN DE SERVICIO EL ALTO SRL', corte: 30 }).whereBetween('nro_vale', [1001, 1005]).orderBy('nro_vale');
    expect(est.map((v: any) => v.estado)).toEqual(['Utilizado', 'Utilizado', 'Disponible', 'Disponible', 'Disponible']); // los 3 sin usar vuelven al almacén
    const em = await db('com_emisiones').where({ nro }).first();
    expect(em.estado).toBe('Descargado');
  });

  it('concilia con lo cobrado por el proveedor', async () => {
    const prov = 'ESTACIÓN DE SERVICIO EL ALTO SRL';
    const r = await conciliarProveedor(db, admin, {
      proveedor: prov, desde: '2026-09-01', hasta: '2026-10-31',
      cobros: [
        { nro_vale: 1001, monto: 30, placa: '2345-ABC', factura: 'F1' }, // conforme (la placa se normaliza)
        { nro_vale: 1002, monto: 50 }, // monto diferente
        { nro_vale: 1010, monto: 30 }, // disponible = no entregado
        { nro_vale: 9999, monto: 30 }, // no registrado
        { nro_vale: 1001, monto: 30 }, // duplicado
      ],
    });
    expect(r.resumen['DUPLICADO']).toBe(2);
    expect(r.resumen['MONTO DIFERENTE']).toBe(1);
    expect(r.resumen['NO ENTREGADO']).toBe(1);
    expect(r.resumen['NO REGISTRADO']).toBe(1);
    const r2 = await conciliarProveedor(db, admin, { proveedor: prov, desde: '2026-09-01', hasta: '2026-10-31', cobros: [{ nro_vale: 1002, monto: 30 }] });
    expect(r2.conformes).toBe(1);
    expect(r2.total_pagar).toBe(30);
    const r3 = await conciliarProveedor(db, admin, { proveedor: prov, desde: '2026-09-01', hasta: '2026-10-31', cobros: [{ nro_vale: 1002, monto: 30 }] });
    expect(r3.resumen['YA CONCILIADO']).toBe(1);
  });
});

describe('anulación y movimientos de vales', () => {
  it('anular una emisión devuelve los vales; vencer/extraviar da de baja el kardex', async () => {
    const e = await emitirVales(db, admin, EMI({ fecha: '2026-10-05', desde: '2026-10-05', hasta: '2026-10-10', lectura: 1200, cantidades: { '30': 2 } }));
    const nro = e.data!.nro;
    expect(((await resumenVales(db)).lista.find((x) => x.corte === 30) as any).Entregado).toBe(2);
    await anularEmision(db, admin, nro, 'error');
    expect((await db('com_emisiones').where({ nro }).first()).estado).toBe('Anulado');
    const m = await movimientoPorRango(db, admin, { fecha: '2026-10-06', accion: 'Vencimiento', proveedor: 'ESTACIÓN DE SERVICIO EL ALTO SRL', combustible: 'Gasolina', corte: 30, desde: 1019, hasta: 1020, motivo: 'vencidos' });
    expect(m.cantidad).toBe(2);
    await rechaza(movimientoPorRango(db, admin, { fecha: '2026-10-06', accion: 'Devolución', proveedor: 'ESTACIÓN DE SERVICIO EL ALTO SRL', combustible: 'Gasolina', corte: 30, desde: 1019, hasta: 1020, motivo: 'x' }), /requiere: Entregado/);
  });
});

describe('turriles', () => {
  it('controla capacidad, saldo y rendimiento en despachos', async () => {
    await rechaza(ingresoTurril(db, admin, { fecha: '2026-10-01', puesto: 'PT-01', litros: 1500, precio: 9.8, factura: 'X' }), /capacidad/);
    await ingresoTurril(db, admin, { fecha: '2026-10-01', puesto: 'PT-01', litros: 800, precio: 9.8, factura: 'F-9' });
    expect(await saldoTurril(db, 'PT-01')).toBe(800);
    await rechaza(despachoTurril(db, admin, { fecha: '2026-10-02', puesto: 'PT-01', placa: '2345ABC', operador: 'JOSÉ LUIS MAMANI CHOQUE', litros: 30, lectura: 5000, apertura: '18 0 001', obra: 'x' }), /usa Gasolina/);
    const r = await despachoTurril(db, admin, { fecha: '2026-10-02', puesto: 'PT-01', placa: 'RETRO-01', operador: 'MARCO ANTONIO QUISPE', litros: 100, lectura: 500, apertura: '18 0 001', obra: 'Camino' });
    expect(r.saldo).toBe(700);
    expect(r.costo_unit).toBe(9.8);
    await rechaza(despachoTurril(db, admin, { fecha: '2026-10-03', puesto: 'PT-01', placa: 'RETRO-01', operador: 'MARCO ANTONIO QUISPE', litros: 10, lectura: 400, apertura: '18 0 001', obra: 'Camino' }), /MENOR que la última/);
  });
});

describe('viajes con fondo en avance', () => {
  it('registra y descarga un viaje calculando saldo y observando excesos', async () => {
    const v: any = await registrarViaje(db, admin, { fecha: '2026-10-01', placa: '3456BCD', conductor: 'FREDDY APAZA LAURA', origen: 'Calamarca', destino: 'La Paz', salida: '2026-10-02', retorno: '2026-10-02', apertura: '10 0 002', fondo: 300, motivo: 'Comisión' });
    expect(v.ok).toBe(true);
    const nro = (v as any).data.nro;
    const d = await descargoViaje(db, admin, {
      nro, fecha_descargo: '2026-10-03', tramos: [{ fecha: '2026-10-02', origen: 'Calamarca', destino: 'La Paz', km_inicial: 0, km_final: 100 }], compras: [{ fecha: '2026-10-02', estacion: 'EESS', factura: 'Z1', litros: 12, total: 117.6 }], confirmar: true,
    });
    expect((d as any).data.saldo).toBeCloseTo(182.4, 2);
  });
});

describe('tablero', () => {
  it('resume la gestión', async () => {
    const t = await tablero(db, 2026);
    expect(t.emisiones).toBeGreaterThanOrEqual(1);
    expect(t.mensual).toHaveLength(12);
  });
});
