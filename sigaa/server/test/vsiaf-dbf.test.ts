import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { DBFFile } from 'dbffile';
import { crearTabla, DbfError, DbfTabla, Especificacion } from '../src/vsiaf/dbf.js';
import { cargarDesdeApp, cargarDesdeDbf } from '../src/vsiaf/ufv.js';

const SPEC: Especificacion = [['CODIGO', 'C', 10, 0], ['COSTO', 'N', 12, 2], ['CANT', 'N', 3, 0], ['FECHA', 'D', 8, 0], ['OK', 'L', 1, 0], ['OBS', 'M', 10, 0]];
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'dbf-'));
function nueva(lang = 0x03) { const p = path.join(tmp(), 'T.DBF'); crearTabla(p, SPEC, lang); return p; }

describe('DBF/FPT', () => {
  it('ida y vuelta de todos los tipos y memo con tildes', () => {
    const p = nueva();
    const t = new DbfTabla(p);
    expect(t.agregar({ CODIGO: 'A-1', COSTO: 1234.567, CANT: 7, FECHA: '2026-03-09', OK: true, OBS: 'Ñandú á é' })).toBe(1);
    t.agregar({ CODIGO: 'A-2', COSTO: -5, CANT: 0, OK: false });
    t.guardar();
    const t2 = new DbfTabla(p);
    expect(t2.nrec).toBe(2);
    const r = t2.leer(1).valores;
    expect(r).toMatchObject({ CODIGO: 'A-1', COSTO: 1234.57, CANT: 7, FECHA: '2026-03-09', OK: true, OBS: 'Ñandú á é' });
    const r2 = t2.leer(2).valores;
    expect(r2).toMatchObject({ COSTO: -5, FECHA: null, OBS: null, OK: false });
    expect(fs.readFileSync(p).at(-1)).toBe(0x1a);
  });

  it('modifica, marca como borrado y rechaza desbordes y campos inexistentes', () => {
    const p = nueva();
    const t = new DbfTabla(p);
    t.agregar({ CODIGO: 'X', COSTO: 1, CANT: 1 });
    t.actualizar(1, { COSTO: 99.5, OBS: 'memo largo '.repeat(30) });
    t.marcarBorrado(1);
    t.guardar();
    const t2 = new DbfTabla(p);
    expect(t2.leer(1).borrado).toBe(true);
    expect(t2.leer(1).valores.COSTO).toBe(99.5);
    expect(String(t2.leer(1).valores.OBS)).toMatch(/^memo largo/);
    expect([...t2.registros()]).toEqual([]);
    expect([...t2.registros(true)].length).toBe(1);
    expect(() => t2.agregar({ CODIGO: 'DEMASIADO LARGO!!' })).toThrow(DbfError);
    expect(() => t2.agregar({ CODIGO: 'X', CANT: 12345 })).toThrow(DbfError);
    expect(() => t2.agregar({ NOEXISTE: 1 })).toThrow(DbfError);
  });

  it('AUXILIAR usa cp850 (Ñ = 0xA5)', () => {
    const p = nueva(0x02);
    const t = new DbfTabla(p);
    t.agregar({ CODIGO: 'Ñ' });
    t.guardar();
    expect(fs.readFileSync(p).includes(Buffer.from([0xa5]))).toBe(true);
    expect(new DbfTabla(p).leer(1).valores.CODIGO).toBe('Ñ');
  });

  it('sin guardar no se escribe nada', () => {
    const p = nueva();
    const antes = fs.readFileSync(p);
    const t = new DbfTabla(p);
    t.agregar({ CODIGO: 'Z' });
    expect(fs.readFileSync(p).equals(antes)).toBe(true);
  });

  it('muchos registros y memos se agregan sin degradarse', () => {
    const p = nueva();
    const t = new DbfTabla(p);
    for (let i = 0; i < 3000; i++) t.agregar({ CODIGO: `C${i}`, COSTO: i, CANT: i % 999, OBS: i % 3 === 0 ? `obs ${i} ñ` : null });
    t.guardar();
    const t2 = new DbfTabla(p);
    expect(t2.nrec).toBe(3000);
    expect(t2.leer(2999).valores).toMatchObject({ CODIGO: 'C2998', OBS: null });
    expect(t2.leer(2998).valores.OBS).toBe('obs 2997 ñ');
  });

  it('un lector DBF independiente (dbffile) lee lo escrito, memos incluidos', async () => {
    const p = nueva();
    const t = new DbfTabla(p);
    t.agregar({ CODIGO: 'IND', COSTO: 10.25, CANT: 3, FECHA: '2025-01-31', OK: true, OBS: 'observación' });
    t.agregar({ CODIGO: 'DOS', COSTO: 1, CANT: 1, OBS: 'segunda ñ' });
    t.guardar();
    const dbf = await DBFFile.open(p, { encoding: 'cp1252' });
    const filas: any[] = await dbf.readRecords();
    expect(filas.length).toBe(2);
    expect(filas[0]).toMatchObject({ CODIGO: 'IND', COSTO: 10.25, CANT: 3, OK: true, OBS: 'observación' });
    expect(new Date(filas[0].FECHA).toISOString().slice(0, 10)).toBe('2025-01-31');
    expect(filas[1].OBS).toBe('segunda ñ');
  });
});

describe('UFV embebidas en tipocambio.app', () => {
  const ESPEC_TC: Especificacion = [['DIA', 'N', 2, 0], ['MES', 'N', 2, 0], ['ANO', 'N', 4, 0], ['TC', 'N', 8, 5], ['FEULT', 'D', 8, 0], ['USUAR', 'C', 8, 0]];
  function tablaTc(valores: [number, number, number, number][]) {
    const p = path.join(tmp(), 'TIPCAMB.DBF');
    crearTabla(p, ESPEC_TC, 0x03, 64, 0x03);
    const t = new DbfTabla(p);
    for (const [d, m, a, tc] of valores) t.agregar({ DIA: d, MES: m, ANO: a, TC: tc });
    t.guardar();
    return fs.readFileSync(p);
  }
  it('extrae la copia más reciente cuando el .app trae dos', () => {
    const vieja = tablaTc([[1, 1, 2020, 2.1], [2, 1, 2020, 2.2]]);
    const nueva_ = tablaTc([[1, 1, 2020, 2.1], [2, 1, 2020, 2.2], [3, 1, 2020, 2.3], [4, 1, 2020, 2.4]]);
    const ruido = Buffer.from('MZ'.repeat(5000) + 'basura');
    const app = path.join(tmp(), 'tipocambio.app');
    fs.writeFileSync(app, Buffer.concat([ruido, vieja, ruido, nueva_, ruido]));
    const u = cargarDesdeApp(app);
    expect(u.tamano).toBe(4);
    expect(u.obtener('2020-01-04')).toBe(2.4);
    expect(u.ultima).toBe('2020-01-04');
  });
  it('lee tipcamb.dbf y falla con claridad si el .app no trae la tabla', () => {
    const dir = tmp();
    fs.writeFileSync(path.join(dir, 'tipcamb.dbf'), tablaTc([[5, 5, 2021, 2.5]]));
    expect(cargarDesdeDbf(path.join(dir, 'tipcamb.dbf')).obtener('2021-05-05')).toBe(2.5);
    const vacio = path.join(dir, 'x.app');
    fs.writeFileSync(vacio, Buffer.from('nada que ver'));
    expect(() => cargarDesdeApp(vacio)).toThrow(/No se encontró la tabla TIPCAMB/);
  });
});
