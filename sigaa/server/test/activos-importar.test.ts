import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import ExcelJS from 'exceljs';
import { dbDemo, admin } from './helpers.js';
import { importarActivosExcel, plantillaActivos, COLUMNAS_ACTIVOS } from '../src/modules/activos/importar.js';
import { contenidoQr, stickersPdf } from '../src/docs/activos.js';

let db: Awaited<ReturnType<typeof dbDemo>>;
beforeAll(async () => { db = await dbDemo(); });
afterAll(async () => db.destroy());

async function libro(filas: Record<string, unknown>[]): Promise<Buffer> {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('DATOS');
  ws.addRow(COLUMNAS_ACTIVOS.map((c) => c.nombre));
  for (const f of filas) ws.addRow(COLUMNAS_ACTIVOS.map((c) => f[c.nombre] ?? null));
  return Buffer.from(await wb.xlsx.writeBuffer());
}
const base = { descripcion: 'PUPITRE BIPERSONAL', cuenta: 3, auxiliar: 'MESA', edificio: 'U.E. CARAZANI', valor: 350.5, fecha_ingreso: '15/03/2024' };

describe('importación de activos desde Excel', () => {
  it('la plantilla trae DATOS, INSTRUCCIONES y CATALOGOS', async () => {
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.load((await plantillaActivos(db)) as any);
    expect(wb.worksheets.map((w) => w.name)).toEqual(['DATOS', 'INSTRUCCIONES', 'CATALOGOS']);
    const cab = (wb.getWorksheet('DATOS')!.getRow(1).values as any[]).slice(1);
    expect(cab).toEqual(COLUMNAS_ACTIVOS.map((c) => c.nombre));
    expect(cab.slice(-3)).toEqual(['foto1', 'foto2', 'foto3']);
  });

  it('validar no guarda nada; importar crea los activos con su código y kardex', async () => {
    const antes = Number((await db('af_activos').count({ n: '*' }).first() as any).n);
    const buf = await libro([{ ...base, codigo: '001-01-30121-0001', foto1: 'a.jpg', foto2: 'b.png', color: 'CAFÉ' }, { ...base, descripcion: 'SILLA', foto1: 'c.jpg' }]);
    const v = await importarActivosExcel(db, admin, buf, false);
    expect(v.errores).toEqual([]);
    expect(v.importado).toBe(false);
    expect(v.creados).toHaveLength(2);
    expect(Number((await db('af_activos').count({ n: '*' }).first() as any).n)).toBe(antes);
    const r = await importarActivosExcel(db, admin, buf, true);
    expect(r.importado).toBe(true);
    expect(r.creados[0].codigo).toBe('001-01-30121-0001');
    expect(r.creados[0].fotos).toEqual([{ n: 1, archivo: 'a.jpg' }, { n: 2, archivo: 'b.png' }]);
    expect(r.creados[1].codigo).toMatch(/^001-00-03/);
    expect(Number((await db('af_activos').count({ n: '*' }).first() as any).n)).toBe(antes + 2);
    const a = await db('af_activos').where({ codigo: '001-01-30121-0001' }).first();
    expect(a).toMatchObject({ situacion: 'EN ALMACEN', color: 'CAFÉ', cod_edif: 1, valor: 350.5, fecha_ingreso: '2024-03-15' });
    expect((await db('af_movimientos').where({ codigo: '001-01-30121-0001' })).map((m: any) => m.tipo)).toEqual(['CODIFICACIÓN DIRECTA']);
  });

  it('con responsable queda asignado; los errores impiden importar todo', async () => {
    const fn = await db('core_funcionarios').first();
    const ok = await importarActivosExcel(db, admin, await libro([{ ...base, codigo: 'RESP-1', responsable: fn.nombre }]), true);
    expect(ok.importado).toBe(true);
    expect(await db('af_activos').where({ codigo: 'RESP-1' }).first()).toMatchObject({ situacion: 'ASIGNADO', funcionario: fn.nombre });
    const mal = await importarActivosExcel(db, admin, await libro([{ ...base, codigo: 'X-1' }, { ...base, cuenta: 99, edificio: 'NO EXISTE', valor: 'abc', foto1: 'a.gif' }, { ...base, codigo: 'RESP-1' }]), true);
    expect(mal.importado).toBe(false);
    const msgs = mal.errores.map((e) => `${e.fila}:${e.mensaje}`).join('\n');
    expect(msgs).toMatch(/3:.*cuenta/);
    expect(msgs).toMatch(/3:.*edificio/);
    expect(msgs).toMatch(/3:.*valor/);
    expect(msgs).toMatch(/3:.*JPG/);
    expect(msgs).toMatch(/4:.*ya existe/);
    expect(await db('af_activos').where({ codigo: 'X-1' }).first()).toBeUndefined();
  });
});

describe('QR de las etiquetas', () => {
  it('lleva entidad, edificio, auxiliar y código', () => {
    expect(contenidoQr('GOBIERNO AUTÓNOMO MUNICIPAL DE LAJA', 'UNIDAD EDUCATIVA LAJA', 'PUPITRE', '001-01-30121-0001').split('\n'))
      .toEqual(['GOBIERNO AUTÓNOMO MUNICIPAL DE LAJA', 'UNIDAD EDUCATIVA LAJA', 'PUPITRE', '001-01-30121-0001']);
  });
  it('la hoja de stickers se genera', async () => {
    const cods = (await db('af_activos').limit(3).select('codigo')).map((x: any) => x.codigo);
    const pdf = await stickersPdf(db, cods);
    expect(pdf.subarray(0, 4).toString()).toBe('%PDF');
  });
});
