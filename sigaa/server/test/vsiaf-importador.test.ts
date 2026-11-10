import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DBFFile, DELETED } from 'dbffile';
import { BdVsiaf, comentarioRespaldo, crearInstalacionSintetica, DbfTabla, errores, Fila, hacerRespaldo, ImportacionAbortada, Importador, Libro, restaurarRespaldo, sumarDias, TablaUfv, TABLAS_PUBLICAS } from './vsiaf-util2.js';
import { cargarDesdeCsv, rutaUfvIncluida } from './vsiaf-util.js';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const golden = (n: string) => JSON.parse(fs.readFileSync(path.join(aqui, 'fixtures/vsiaf', n), 'utf8'));
const UFV: TablaUfv = cargarDesdeCsv(rutaUfvIncluida());
const HOY = '2026-10-20';
const f = (n: number) => { const x = sumarDias(HOY, -n); return `${x.slice(8)}/${x.slice(5, 7)}/${x.slice(0, 4)}`; };

let raiz = '';
beforeEach(() => {
  raiz = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'vsiaf-')), 'vsiaf');
  crearInstalacionSintetica(raiz);
});

/** Libro desde filas tipo Excel (la fila 1 es el encabezado: los datos empiezan en la 2). */
const libro = (b: Record<string, Record<string, unknown>[]>): Libro =>
  Object.fromEntries(Object.entries(b).map(([k, rows]) => [k, rows.map((datos, i): Fila => ({ ref: i + 2, datos }))])) as Libro;
const imp = (extra: Record<string, unknown> = {}) => new Importador(new BdVsiaf(raiz), UFV, { unidadPorDefecto: '1', hoy: HOY, fechaCalculo: HOY, permitirIncorporacionEspecial: false, respaldar: false, ...extra });
const volcar = (dir = raiz) => {
  const db = new BdVsiaf(dir);
  return Object.fromEntries(TABLAS_PUBLICAS.map((t) => [t, [...db.tabla(t).registros(true)].map((r) => ({ deleted: r.borrado, v: r.valores }))]));
};
const mensajes = (r: { incidencias: { nivel: string; mensaje: string; hoja: string }[] }, nivel = 'ERROR') => r.incidencias.filter((i) => i.nivel === nivel && i.hoja !== '(UFV)').map((i) => i.mensaje);

const PRE = {
  OFICINAS: [{ oficina: 'ADMINISTRACION' }, { oficina: 'ALMACEN' }],
  RESPONSABLES: [{ oficina: 'ADMINISTRACION', responsable: 'ANA PEREZ MAMANI', cargo: 'JEFE', ci: '1', expedido: 'LPZ' }, { oficina: 'ALMACEN', responsable: 'CARLOS QUISPE', cargo: 'ENCARGADO' }],
  AUXILIARES: [{ grupo_contable: 15, auxiliar: 'LAPTOP' }, { grupo_contable: 2, auxiliar: 'ESCRITORIO' }],
};
const activo = (o: Record<string, unknown> = {}) => ({ codigo: 'A-1', descripcion: 'LAPTOP', grupo_contable: 15, auxiliar: 'LAPTOP', oficina: 'ADMINISTRACION', responsable: 'ANA PEREZ MAMANI', estado_bien: 'Bueno', fecha_incorporacion: f(30), costo_inicial: 1000, organismo_financiador: '111', estado_registro: 'APROBADO', ...o });

describe('contraste con el motor de referencia (Python)', () => {
  it('importación completa: unidades, oficinas, responsables, auxiliares, altas, revalúos, transferencias y bajas', () => {
    const g = golden('importacion_golden.json');
    const i = imp();
    const r = i.plan(libro(g.batch));
    expect(errores(r)).toBe(0);
    expect(r.conteos).toEqual(g.expected.counts);
    i.aplicar('prueba');
    expect(r.aplicado).toBe(true);
    const tablas = volcar();
    for (const t of Object.keys(g.expected.tables)) expect(tablas[t], `tabla ${t}`).toEqual(g.expected.tables[t]);
  });
  it('cálculos de vista previa idénticos', () => {
    const g = golden('importacion_golden.json');
    const r = imp().plan(libro(g.batch));
    const comp = JSON.parse(JSON.stringify(r.calculos));
    for (const hoja of Object.keys(g.expected.computed)) {
      expect(comp[hoja].length).toBe(g.expected.computed[hoja].length);
      comp[hoja].forEach((fila: Record<string, unknown>, n: number) => {
        const py = g.expected.computed[hoja][n];
        for (const [k, v] of Object.entries(py)) {
          const a = fila[k];
          if (typeof v === 'number' && typeof a === 'number') expect(Math.abs(a - v), `${hoja}[${n}].${k}`).toBeLessThan(1e-9);
          else if (k === 'incorporacion' || k.includes('fecha')) expect(String(a)).toBe(String(v));
          else expect(a, `${hoja}[${n}].${k}`).toEqual(v);
        }
      });
    }
  });
  it('las 28 validaciones dan las mismas incidencias (hoja, columna, nivel y mensaje)', () => {
    const g = golden('validaciones_golden.json');
    for (const caso of g.casos) {
      const r = imp().plan(libro(caso.batch));
      const ts = r.incidencias.filter((x) => x.hoja !== '(UFV)').map((x) => ({ hoja: x.hoja, ref: x.ref, columna: x.columna, nivel: x.nivel, mensaje: x.mensaje }));
      const py = caso.res.issues.filter((x: any) => x.hoja !== '(UFV)');
      expect(ts, JSON.stringify(caso.cambios)).toEqual(py);
      expect(() => imp().aplicar()).toThrow(ImportacionAbortada); // nada planificado → no se puede aplicar
    }
  });
  it('incorporación especial habilitada y «solo filas válidas»', () => {
    const ie = golden('incesp_golden.json');
    let i = imp({ permitirIncorporacionEspecial: true });
    i.plan(libro(ie.batch));
    i.aplicar();
    expect(volcar().ACTUAL).toEqual(ie.expected.tables.ACTUAL);
    raiz = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'vsiaf-')), 'vsiaf');
    crearInstalacionSintetica(raiz);
    const sv = golden('solovalidas_golden.json');
    i = imp({ soloValidas: true });
    const r = i.plan(libro(sv.batch));
    expect(r.conteos).toEqual(sv.expected.counts);
    i.aplicar();
    expect(volcar().ACTUAL).toEqual(sv.expected.tables.ACTUAL);
  });
});

describe('comportamiento', () => {
  it('campos del alta', () => {
    const i = imp();
    const r = i.plan(libro({ ...PRE, ACTIVOS: [activo({ codigo: 'ab-1', codigo_adicional: 'x9', cod_rube: 'R1', nro_convenio: 'C-5', observaciones: 'Obs ñ' })] }));
    expect(errores(r)).toBe(0);
    i.aplicar();
    const a = volcar().ACTUAL[0].v as Record<string, any>;
    expect(a).toMatchObject({ CODIGO: 'AB-1', CODIGOSEC: 'X9', ENTIDAD: '9999', UNIDAD: '1', CODCONT: 15, VIDAUTIL: 4, COSTO: 1000, DEPACU: 0, B_REV: false, BAND_UFV: false, BANDERAS: '0', CODESTADO: 1, ORG_FIN: '111', OBSERV: 'Obs ñ', USUAR: 'admin', API_ESTADO: 3 });
    const inc = sumarDias(HOY, -30);
    expect([a.DIA, a.MES, a.ANO]).toEqual([+inc.slice(8), +inc.slice(5, 7), +inc.slice(0, 4)]);
  });
  it('el estado por defecto de las altas es ELABORADO', () => {
    const i = imp();
    i.plan(libro({ ...PRE, ACTIVOS: [activo({ estado_registro: null })] }));
    i.aplicar();
    expect(volcar().ACTUAL[0].v.API_ESTADO).toBe(1);
  });
  it('un activo con código repetido (en el lote o en el VSIAF) es error, nunca se sobrescribe', () => {
    const r = imp().plan(libro({ ...PRE, ACTIVOS: [activo(), activo()] }));
    expect(mensajes(r).some((m) => /ya existe en la fila 2 de este libro/.test(m))).toBe(true);
    const i = imp();
    i.plan(libro({ ...PRE, ACTIVOS: [activo()] }));
    i.aplicar();
    const otra = imp().plan(libro({ ACTIVOS: [activo()] }));
    expect(mensajes(otra).some((m) => /ya existe en el VSIAF/.test(m))).toBe(true);
  });
  it('maestros existentes se reutilizan (no se duplican) y los códigos son correlativos', () => {
    const i = imp();
    i.plan(libro(PRE));
    i.aplicar();
    const j = imp();
    const r = j.plan(libro({ ...PRE, OFICINAS: [...PRE.OFICINAS, { oficina: 'TESORERIA' }], AUXILIARES: [...PRE.AUXILIARES, { grupo_contable: 15, auxiliar: 'IMPRESORA' }] }));
    expect(r.conteos).toEqual({ OFICINAS: 1, AUXILIARES: 1 });
    j.aplicar();
    const t = volcar();
    expect(t.OFICINA.map((x) => x.v.CODOFIC)).toEqual([1, 2, 3]);
    expect(t.AUXILIAR.filter((x) => x.v.CODCONT === 15).map((x) => x.v.CODAUX)).toEqual([1, 2]);
  });
  it('validar no escribe: los archivos quedan idénticos byte a byte', () => {
    const antes = Object.fromEntries(fs.readdirSync(path.join(raiz, 'dbfs')).map((n) => [n, fs.readFileSync(path.join(raiz, 'dbfs', n))]));
    imp().plan(libro({ ...PRE, ACTIVOS: [activo()] }));
    for (const [n, b] of Object.entries(antes)) expect(fs.readFileSync(path.join(raiz, 'dbfs', n)).equals(b), n).toBe(true);
  });
  it('un error cancela todo, salvo «solo filas válidas»', () => {
    const i = imp();
    const r = i.plan(libro({ ...PRE, ACTIVOS: [activo(), activo({ codigo: 'MAL', costo_inicial: 0 })] }));
    expect(errores(r)).toBe(1);
    expect(() => i.aplicar()).toThrow(/Corríjalos|error\(es\)/);
  });
  it('repetir una importación ya hecha falla por duplicados', () => {
    const lote = { ...PRE, ACTIVOS: [activo()] };
    const i = imp();
    i.plan(libro(lote));
    i.aplicar();
    const j = imp();
    const r = j.plan(libro({ ACTIVOS: lote.ACTIVOS }));
    expect(errores(r)).toBeGreaterThan(0);
    expect(() => j.aplicar()).toThrow(ImportacionAbortada);
  });
  it('gestión cerrada: no se escribe', () => {
    fs.mkdirSync(path.join(raiz, 'closeges'));
    const p = path.join(raiz, 'closeges', 'closeges.dbf');
    // tabla mínima con NOM_ARCH
    const t = path.join(raiz, 'closeges', 'x.dbf');
    void t;
    // se fabrica con el mismo escritor
    const { crearTabla } = require_dbf();
    crearTabla(p, [['NOM_ARCH', 'C', 12, 0]], 0x03, 64, 0x03);
    const tb = new DbfTabla(p);
    tb.agregar({ NOM_ARCH: 'ACTUAL' });
    tb.guardar();
    const i = imp();
    const r = i.plan(libro({ ...PRE, ACTIVOS: [activo()] }));
    expect(r.incidencias.some((x) => x.hoja === '(BD)' && /CERRADA/.test(x.mensaje))).toBe(true);
    expect(() => i.aplicar()).toThrow(/CERRADA/);
  });
  it('revalúo y baja solo sobre activos APROBADOS', () => {
    const i = imp();
    i.plan(libro({ ...PRE, ACTIVOS: [activo({ estado_registro: 'ELABORADO' })] }));
    i.aplicar();
    const r = imp().plan(libro({ REVALUOS: [{ codigo: 'A-1', fecha_revaluo: f(5), nuevo_costo: 2000, nueva_vida_util: 3, disposicion_respaldo: 'R-1' }], BAJAS: [{ codigo: 'A-1', fecha_baja: f(2), motivo_baja: 6, disposicion_respaldo: 'B-1' }] }));
    expect(mensajes(r).filter((m) => /está ELABORADO/.test(m)).length).toBe(2);
  });
  it('revalúo igual que el VSIAF: fecha base +1 día, B_REV, depacu 0 y resolución no repetible', () => {
    const i = imp();
    i.plan(libro({ ...PRE, ACTIVOS: [activo({ fecha_incorporacion: f(400) })] }));
    i.aplicar();
    const j = imp();
    const r = j.plan(libro({ REVALUOS: [{ codigo: 'A-1', fecha_revaluo: f(10), nuevo_costo: 1500, nueva_vida_util: 2, disposicion_respaldo: 'R-1/26', motivo: 'DONACION' }] }));
    expect(errores(r)).toBe(0);
    j.aplicar();
    const t = volcar();
    const base = sumarDias(HOY, -9);
    expect(t.ACTUAL[0].v).toMatchObject({ COSTO: 1500, VIDAUTIL: 2, B_REV: true, DEPACU: 0, DIA: +base.slice(8), MES: +base.slice(5, 7), ANO: +base.slice(0, 4) });
    expect(t.REVAL[0].v).toMatchObject({ COSTO: 1000, VIDAUTIL: 4, RESOLUCION: 'R-1/26', OBSERV: 'DONACION' });
    const dup = imp().plan(libro({ REVALUOS: [{ codigo: 'A-1', fecha_revaluo: f(5), nuevo_costo: 1700, nueva_vida_util: 2, disposicion_respaldo: 'r-1/26' }] }));
    expect(mensajes(dup).some((m) => /Ya existe un revalúo/.test(m))).toBe(true);
  });
  it('baja igual que el VSIAF: fila en BAJAS, registro de ACTUAL borrado con «DADO DE BAJA»', () => {
    const i = imp();
    i.plan(libro({ ...PRE, ACTIVOS: [activo({ fecha_incorporacion: f(40) })] }));
    i.aplicar();
    const j = imp();
    j.plan(libro({ BAJAS: [{ codigo: 'A-1', fecha_baja: f(3), motivo_baja: 'Inutilización', disposicion_respaldo: 'B-1', observaciones: 'NO ENCIENDE' }] }));
    j.aplicar();
    const t = volcar();
    expect(t.ACTUAL[0].deleted).toBe(true);
    expect(t.ACTUAL[0].v.OBSERV).toBe('DADO DE BAJA');
    expect(t.BAJAS[0].v).toMatchObject({ CODIGO: 'A-1', CODBAJA: 5, OBSERV: 'DADO DE BAJA', MOTIVO: 'NO ENCIENDE', RESOLUCION: 'B-1', DESCRIP: 'LAPTOP' });
  });
  it('«error de transcripción» (9) solo en la gestión de incorporación; fecha anterior a la base o activo inexistente son errores', () => {
    const i = imp();
    i.plan(libro({ ...PRE, ACTIVOS: [activo({ fecha_incorporacion: '15/03/2025' })] }));
    i.aplicar();
    const r = imp().plan(libro({ BAJAS: [{ codigo: 'A-1', fecha_baja: f(3), motivo_baja: 9, disposicion_respaldo: 'B-1' }, { codigo: 'A-1', fecha_baja: '01/01/2024', motivo_baja: 6, disposicion_respaldo: 'B-2' }, { codigo: 'NO', fecha_baja: f(3), motivo_baja: 6, disposicion_respaldo: 'B-3' }] }));
    const m = mensajes(r);
    expect(m.some((x) => /Error de transcripción/.test(x))).toBe(true);
    expect(m.some((x) => /anterior a la fecha base/.test(x))).toBe(true);
    expect(m.some((x) => /No existe el activo «NO»/.test(x))).toBe(true);
  });
  it('transferencia en la misma unidad y entre unidades (exige auxiliar de destino)', () => {
    const base = {
      UNIDADES: [{ unidad: '2', descripcion: 'OTRA UNIDAD' }],
      OFICINAS: [...PRE.OFICINAS, { unidad: '2', oficina: 'DIRECCION' }],
      RESPONSABLES: [...PRE.RESPONSABLES, { unidad: '2', oficina: 'DIRECCION', responsable: 'MARIA', cargo: 'DIRECTORA' }],
      AUXILIARES: [...PRE.AUXILIARES, { unidad: '2', grupo_contable: 2, auxiliar: 'ESCRITORIO' }],
      ACTIVOS: [activo({ codigo: 'E-1', grupo_contable: 2, auxiliar: 'ESCRITORIO' })],
    };
    const i = imp();
    i.plan(libro(base));
    i.aplicar();
    const sin = imp().plan(libro({ TRANSFERENCIAS: [{ unidad_origen: '1', codigo: 'E-1', unidad_destino: '2', oficina_destino: 'DIRECCION', responsable_destino: 'MARIA' }] }));
    expect(mensajes(sin).some((m) => /auxiliar de destino/.test(m))).toBe(true);
    const j = imp();
    const r = j.plan(libro({ TRANSFERENCIAS: [{ unidad_origen: '1', codigo: 'E-1', oficina_destino: 'ALMACEN', responsable_destino: 'CARLOS QUISPE' }, { unidad_origen: '1', codigo: 'E-1', unidad_destino: '2', oficina_destino: 'DIRECCION', responsable_destino: 'MARIA', auxiliar_destino: 'ESCRITORIO' }] }));
    expect(errores(r)).toBe(0);
    j.aplicar();
    const t = volcar();
    expect(t.TRASFE.map((x) => [x.v.UNIDAD, x.v.UNIDADINI, x.v.CODOFIC])).toEqual([['1', '1', 2], ['2', '1', 1]]);
    expect(t.ACTUAL[0].v).toMatchObject({ UNIDAD: '2', CODOFIC: 1, CODRESP: 1 });
  });
});

describe('respaldo y reversión', () => {
  it('el respaldo es un .zip plano restaurable con comentario cp1252', () => {
    const i = imp({ respaldar: true });
    i.plan(libro({ ...PRE, ACTIVOS: [activo()] }));
    const antes = volcar();
    i.aplicar('Importación de prueba');
    const zip = i.res.rutaRespaldo!;
    expect(zip).toMatch(/VSIMPXL\d{10}\.zip$/);
    expect(fs.existsSync(zip.replace(/\.zip$/, '.gtz'))).toBe(true);
    expect(comentarioRespaldo(zip)).toMatch(/^Backup de la entidad «9999» en fecha \d\d\/\d\d\/\d{4}: Importación de prueba$/);
    expect(volcar().ACTUAL.length).toBe(1);
    restaurarRespaldo(new BdVsiaf(raiz), zip);
    expect(volcar()).toEqual(antes);
  });
  it('si la escritura falla a mitad, la base queda exactamente como estaba', () => {
    const lote = libro({ ...PRE, ACTIVOS: [activo(), activo({ codigo: 'A-2' })] });
    for (const donde of ['op-3', 'op-6', 'antes-de-guardar', 'despues-de-guardar']) {
      raiz = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'vsiaf-')), 'vsiaf');
      crearInstalacionSintetica(raiz);
      const antes = Object.fromEntries(fs.readdirSync(path.join(raiz, 'dbfs')).map((n) => [n, fs.readFileSync(path.join(raiz, 'dbfs', n))]));
      const i = imp({ fallaSimulada: (d: string) => { if (d === donde) throw new Error('fallo simulado'); } });
      i.plan(lote);
      expect(() => i.aplicar(), donde).toThrow(/fallo simulado/);
      for (const [n, b] of Object.entries(antes)) expect(fs.readFileSync(path.join(raiz, 'dbfs', n)).equals(b), `${donde}: ${n}`).toBe(true);
      expect(fs.readdirSync(path.join(raiz, 'dbfs')).some((n) => n.endsWith('.vsiaf_imp_tmp'))).toBe(false);
    }
  });
  it('un lector independiente (dbffile) ve lo importado, con tildes y la marca de borrado', async () => {
    const i = imp();
    i.plan(libro({ ...PRE, ACTIVOS: [activo({ descripcion: 'LAPTOP ñandú á', observaciones: 'obs ñ' }), activo({ codigo: 'A-2', fecha_incorporacion: f(40) })], BAJAS: [{ codigo: 'A-2', fecha_baja: f(3), motivo_baja: 6, disposicion_respaldo: 'B-1' }] }));
    i.aplicar();
    const dbf = await DBFFile.open(path.join(raiz, 'dbfs', 'ACTUAL.DBF'), { encoding: 'cp1252', includeDeletedRecords: true });
    const filas: any[] = await dbf.readRecords();
    expect(filas.length).toBe(2);
    expect(filas[0]).toMatchObject({ CODIGO: 'A-1', DESCRIP: 'LAPTOP ñandú á', OBSERV: 'obs ñ', COSTO: 1000, CODCONT: 15 });
    expect(filas[1].CODIGO).toBe('A-2');
    expect(filas[1][DELETED]).toBe(true);
    const aux = await DBFFile.open(path.join(raiz, 'dbfs', 'AUXILIAR.DBF'), { encoding: 'cp850' });
    expect((await aux.readRecords()).map((x: any) => x.NOMAUX).sort()).toEqual(['ESCRITORIO', 'LAPTOP']);
  });
});

import { crearTabla } from '../src/vsiaf/dbf.js';
function require_dbf() { return { crearTabla }; }
void hacerRespaldo;
