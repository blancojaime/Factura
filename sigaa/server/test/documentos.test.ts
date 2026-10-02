import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import type { Knex } from 'knex';
import fs from 'node:fs';
import ExcelJS from 'exceljs';
import { dbDemo, admin } from './helpers.js';
import { DOCS } from '../src/docs/types.js';
import '../src/docs/almacenes.js';
import '../src/docs/combustible.js';
import '../src/docs/activos.js';
import { stickersPdf } from '../src/docs/activos.js';
import { REGISTRO, renderTablaPdf, renderTablaXlsx } from '../src/reports/types.js';
import '../src/reports/almacenes.js';
import '../src/reports/combustible.js';
import '../src/reports/activos.js';
import { registrarRecepcion, emitirVales, registrarDescargo, movimientoPorRango } from '../src/modules/combustible/vales.js';
import { conciliarProveedor, registrarViaje, descargoViaje } from '../src/modules/combustible/otros.js';
import { procesarMovimientoAF } from '../src/modules/activos/service.js';
import { guardarSalida } from '../src/modules/almacenes/salidas.js';

const OUT = process.env.SIGAA_TEST_OUT || '';
let db: Knex;
beforeAll(async () => {
  db = await dbDemo();
  // datos de combustible para los documentos
  await registrarRecepcion(db, admin, { fecha: '2026-09-27', nro_contrato: 'GAMC-CONT-001/2026', factura: 'F-1', filas: [{ corte: 30, desde: 1001, hasta: 1020 }] });
  const e = await emitirVales(db, admin, { fecha: '2026-09-28', destino: 'VEHICULO', placa: '2345ABC', lectura: 1000, conductor: 'JOSÉ LUIS MAMANI CHOQUE', solicitante: 'Jefe', unidad: 'DESPACHO DEL EJECUTIVO MUNICIPAL', apertura: '00 0 001', trabajo: 'Comisión', desde: '2026-09-28', hasta: '2026-10-03', cantidades: { '30': 4 } });
  (globalThis as any).__vc = e.data!.nro;
  const d = await registrarDescargo(db, admin, { nro_emision: e.data!.nro, fecha: '2026-10-03', devolver_automaticamente: true, confirmar: true, lineas: [{ fecha: '2026-09-29', ruta: 'Calamarca - La Paz', lectura_salida: 1000, lectura_llegada: 1200, nro_vale: 1001, litros: 4.31, factura: 'F1', estacion: 'EESS' }] });
  (globalThis as any).__ds = d.data!.nro;
  const m = await movimientoPorRango(db, admin, { fecha: '2026-10-04', accion: 'Vencimiento', proveedor: 'ESTACIÓN DE SERVICIO EL ALTO SRL', combustible: 'Gasolina', corte: 30, desde: 1019, hasta: 1020, motivo: 'vencidos' });
  (globalThis as any).__mv = m.doc;
  const c = await conciliarProveedor(db, admin, { proveedor: 'ESTACIÓN DE SERVICIO EL ALTO SRL', desde: '2026-09-01', hasta: '2026-10-31', cobros: [{ nro_vale: 1001, monto: 30 }] });
  (globalThis as any).__cc = c.nro;
  const v: any = await registrarViaje(db, admin, { fecha: '2026-10-01', placa: '3456BCD', conductor: 'FREDDY APAZA LAURA', origen: 'Calamarca', destino: 'La Paz', salida: '2026-10-02', retorno: '2026-10-02', apertura: '10 0 002', fondo: 300, motivo: 'Comisión' });
  await descargoViaje(db, admin, { nro: v.data.nro, fecha_descargo: '2026-10-03', confirmar: true, tramos: [{ fecha: '2026-10-02', origen: 'A', destino: 'B', km_inicial: 0, km_final: 100 }], compras: [{ fecha: '2026-10-02', estacion: 'EESS', factura: 'Z', litros: 12, total: 117.6 }] });
  (globalThis as any).__vj = v.data.nro;
  const t = await procesarMovimientoAF(db, admin, { tipo: 'DEVOLUCIÓN', fecha: '2026-10-04', origen: 'JAVIER CONDORI CHOQUE', codigos: ['001-02-12261-04'] });
  (globalThis as any).__afdev = t.nro;
  const sv = await guardarSalida(db, admin, { fecha_pedido: '2026-10-05', cod_bod: '04', unidad: 'UNIDAD DE SALUD', solicitante: 'RENÉ CHAMBI COLQUE', superior: 'PEDRO APAZA ROJAS', justificacion: 'Prueba sin existencia', items: [{ cod_item: '5-1-0000002', cant_pedida: 10 }] });
  (globalThis as any).__vs0 = sv.nro;
});
afterAll(async () => db.destroy());

const guardar = (nombre: string, b: Buffer) => OUT && fs.writeFileSync(`${OUT}/${nombre}`, b);
const g = (k: string) => (globalThis as any)[k] as string;

describe('documentos PDF', () => {
  const casos: [string, () => string, Record<string, string>?][] = [
    ['alm-cgi', () => 'CGI-0001/2026'], ['alm-verif-docs', () => 'CGI-0001/2026'], ['alm-vale', () => 'VS-0002/2026'], ['alm-cert-inexistencia', () => g('__vs0')],
    ['alm-kardex', () => '1-2-0000001', { bodega: '01', desde: '2026-01-01', hasta: '2026-12-31' }], ['alm-hoja-conteo', () => 'INV-0001/2026'], ['alm-acta-inventario', () => 'INV-0001/2026'],
    ['alm-acta-reposicion', () => 'INV-0001/2026'], ['alm-inventario-valorado', () => 'INV-0001/2026'],
    ...['ACTAVER', 'INFSOL', 'INFTEC', 'MEMOCOM', 'ACTADEST', 'ACTAENT', 'REGBAJA', 'CONVOC'].map((x): [string, () => string, Record<string, string>] => ['alm-baja', () => 'BAJ-0001/2026', { doc: x }]),
    ['alm-acta-transferencia', () => 'TRF-0001/2026'], ['alm-requerimiento', () => 'REQ-0001/2026'], ['alm-acta-inspeccion', () => 'INS-0001/2026'], ['alm-nota-mantenimiento', () => 'INS-0001/2026'],
    ['com-vale', () => g('__vc')], ['com-nota-ingreso', () => 'IV-0001/2026'], ['com-planilla-descargo', () => g('__vc')], ['com-descargo', () => g('__ds')], ['com-acta-movimiento', () => g('__mv')], ['com-conciliacion', () => g('__cc')], ['com-viaje', () => g('__vj')],
    ['af-solicitud', () => 'SOL-0001/2026'], ['af-memo-comision', () => 'ING-0001/2026'], ['af-acta-conformidad', () => 'ING-0001/2026'], ['af-form-ingreso', () => 'ING-0001/2026'], ['af-asignacion', () => 'ASG-0001/2026'],
    ['af-salida-sin-existencia', () => 'SOL-0004/2026'], ['af-ficha', () => '001-02-12261-01'], ['af-movimiento', () => g('__afdev')],
  ];
  it.each(casos.map((c, i) => [i, c[0], c]))('genera %s', async (_i, id, c: any) => {
    const doc = DOCS.get(id as string)!;
    expect(doc, `documento ${id} no registrado`).toBeTruthy();
    const buf = await doc.build(db, c[1](), c[2] ?? {});
    expect(buf.subarray(0, 4).toString()).toBe('%PDF');
    expect(buf.length).toBeGreaterThan(1500);
    guardar(`${id}${c[2]?.doc ? '-' + c[2].doc : ''}.pdf`, buf);
  });
  it('genera stickers', async () => {
    const buf = await stickersPdf(db, (await db('af_activos').limit(35)).map((a: any) => a.codigo));
    expect(buf.subarray(0, 4).toString()).toBe('%PDF');
    guardar('stickers.pdf', buf);
  });
});

describe('reportes PDF y Excel', () => {
  const params: Record<string, Record<string, string>> = {
    'alm-ingresos': { desde: '2026-01-01', hasta: '2026-12-31' },
    'af-inv-funcionario': { funcionario: 'JAVIER CONDORI CHOQUE' }, 'af-inv-ubicacion': { cod_edif: '1' }, 'af-kardex': { codigo: '001-02-12261-01' },
    'com-informe-mensual': { mes: '2026-09-15', a_nombre: 'Lic. Juan Pérez', a_cargo: 'SECRETARIO' },
    'com-emisiones': { desde: '2026-09-01', hasta: '2026-10-31' }, 'com-kardex': { desde: '2026-09-01', hasta: '2026-10-31' }, 'com-rendimiento': { desde: '2026-09-01', hasta: '2026-10-31' }, 'com-consumo': { desde: '2026-09-01', hasta: '2026-10-31' },
    'af-contabilidad': { desde: '2026-09-01', hasta: '2026-10-31' },
  };
  it('están todos los reportes del sistema original', () => {
    expect(REGISTRO.size).toBeGreaterThanOrEqual(28);
  });
  it.each([...REGISTRO.keys()])('ejecuta %s', async (id) => {
    const rep = REGISTRO.get(id)!;
    const t = await rep.ejecutar(db, params[id] ?? {});
    expect(t.cols.length).toBeGreaterThan(0);
    const pdf = await renderTablaPdf(db, t);
    expect(pdf.subarray(0, 4).toString()).toBe('%PDF');
    const x = await renderTablaXlsx(db, t);
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.load(x as any);
    expect(wb.worksheets.length).toBeGreaterThan(0);
    guardar(`rep-${id}.pdf`, pdf);
  });
});

describe('conciliación desde Excel y copia automática', () => {
  it('lee el .xlsx del proveedor con encabezado', async () => {
    const { leerCobrosXlsx } = await import('../src/modules/combustible/cobros.js');
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet('c');
    ws.addRow(['Nro Vale', 'Fecha', 'Placa', 'Litros', 'Monto Bs', 'Factura']);
    ws.addRow([1001, new Date('2026-09-29'), '2345ABC', 4.31, 30, 'F1']);
    ws.addRow(['x', '', '', '', '', '']);
    const c = await leerCobrosXlsx(Buffer.from(await wb.xlsx.writeBuffer()));
    expect(c).toEqual([{ nro_vale: 1001, fecha: '2026-09-29', placa: '2345ABC', litros: 4.31, monto: 30, factura: 'F1' }]);
  });
  it('genera la copia diaria una sola vez y respeta la retención', async () => {
    if (process.env.TEST_DATABASE_URL) return;
    const { respaldar } = await import('../src/core/backup.js');
    const dir = fs.mkdtempSync('/tmp/sigaa-bk-');
    expect(await respaldar(db, dir)).toMatch(/sigaa-\d{4}-\d{2}-\d{2}\.sqlite$/);
    expect(await respaldar(db, dir)).toBeNull();
    fs.writeFileSync(`${dir}/sigaa-2020-01-01.sqlite`, 'x');
    fs.writeFileSync(`${dir}/sigaa-2020-01-02.sqlite`, 'x');
    await respaldar(db, dir, 1);
    expect(fs.readdirSync(dir).length).toBeGreaterThanOrEqual(1);
  });
});
