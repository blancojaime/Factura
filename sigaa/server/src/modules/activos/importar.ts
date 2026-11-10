/**
 * Importación de activos fijos ya existentes (inventario inicial) desde un libro de Excel, con fotografías
 * que se suben aparte desde una carpeta (los nombres van en las columnas foto1, foto2 y foto3).
 * El núcleo `insertarActivos` también lo usa la importación desde el VSIAF.
 */
import ExcelJS from 'exceljs';
import type { Db, Usuario } from '../../core/context.js';
import { fail } from '../../core/errors.js';
import { bitacora } from '../../core/services.js';
import { nowIso, num, round, today, txt, norm } from '../../core/util.js';
import { comoFecha, comoNumero } from '../../vsiaf/coercion.js';
import { armarCodigo, SIT_ALMACEN, SIT_ASIGNADO } from './service.js';

export interface FilaActivo {
  fila: number;
  codigo?: string;
  descripcion: string;
  id_cta: number;
  id_aux: number;
  auxiliar: string;
  cod_edif: number;
  cod_amb: number;
  estado: string;
  valor: number;
  fecha_ingreso: string;
  marca?: string;
  modelo?: string;
  serie?: string;
  color?: string;
  observaciones?: string;
  funcionario?: string;
  ci?: string;
  fotos?: (string | null)[];
}
export interface Creado { fila: number; codigo: string; fotos: { n: number; archivo: string }[] }

/** Inserta los activos (con su kardex) dentro de la transacción recibida. */
export async function insertarActivos(trx: Db, u: Usuario, filas: FilaActivo[], origen: string): Promise<Creado[]> {
  const correl = new Map<string, number>();
  const creados: Creado[] = [];
  const hoy = today();
  for (const f of filas) {
    const clave = `${f.cod_edif}|${f.cod_amb}|${f.id_cta}|${f.id_aux}`;
    if (!correl.has(clave)) {
      const r = await trx('af_activos').where({ cod_edif: f.cod_edif, cod_amb: f.cod_amb, id_cta: f.id_cta, id_aux: f.id_aux }).max({ m: 'correl' }).first();
      correl.set(clave, num(r?.m));
    }
    let c = correl.get(clave)! + 1;
    let codigo = txt(f.codigo).toUpperCase();
    if (!codigo) {
      codigo = await armarCodigo(trx, f.cod_edif, f.cod_amb, f.id_cta, f.id_aux, c);
      while (await trx('af_activos').where({ codigo }).first()) { c++; codigo = await armarCodigo(trx, f.cod_edif, f.cod_amb, f.id_cta, f.id_aux, c); }
    }
    correl.set(clave, c);
    const fotos = (f.fotos ?? []).slice(0, 3);
    await trx('af_activos').insert({
      codigo, cod_edif: f.cod_edif, cod_amb: f.cod_amb, id_cta: f.id_cta, id_aux: f.id_aux, auxiliar: f.auxiliar, correl: c, descripcion: f.descripcion, marca: f.marca || null, modelo: f.modelo || null,
      serie: f.serie || null, color: f.color || null, estado: f.estado, valor: round(f.valor, 2), fecha_ingreso: f.fecha_ingreso, fecha_codif: hoy,
      situacion: f.funcionario ? SIT_ASIGNADO : SIT_ALMACEN, funcionario: f.funcionario || null, ci_func: f.ci || null, nro_acta: f.funcionario ? origen : null, fecha_asig: f.funcionario ? f.fecha_ingreso : null,
      edif_actual: f.cod_edif, amb_actual: f.cod_amb, etq_impresa: 'NO', observaciones: f.observaciones || null,
    });
    const mov = (tipo: string, origenMov: string, destino: string, detalle: string) => trx('af_movimientos').insert({ fecha: f.fecha_ingreso, codigo, tipo, documento: origen, origen: origenMov, destino, detalle, usuario: u.usuario, fecha_reg: nowIso() });
    await mov('CODIFICACIÓN DIRECTA', 'INV. INICIAL', 'ALMACÉN', `Importado (${origen})`);
    if (f.funcionario) await mov('ASIGNACIÓN', 'ALMACÉN', f.funcionario, `Asignación inicial por importación (${origen})`);
    creados.push({ fila: f.fila, codigo, fotos: fotos.map((a, i) => (a ? { n: i + 1, archivo: a } : null)).filter(Boolean) as { n: number; archivo: string }[] });
  }
  return creados;
}

// ───────────── Estructura del Excel ─────────────
interface ColDef { nombre: string; obligatorio: boolean; descripcion: string; ejemplo: string | number }
export const COLUMNAS_ACTIVOS: ColDef[] = [
  { nombre: 'codigo', obligatorio: false, descripcion: 'Código del activo (máx. 20). Vacío = SIGAA lo genera (edificio-ambiente-cuenta+auxiliar-correlativo).', ejemplo: '001-01-30121-0001' },
  { nombre: 'descripcion', obligatorio: true, descripcion: 'Descripción del bien (máx. 240).', ejemplo: 'PUPITRE BIPERSONAL DE MADERA' },
  { nombre: 'cuenta', obligatorio: true, descripcion: 'Número o nombre de la cuenta contable (hoja CATALOGOS).', ejemplo: 3 },
  { nombre: 'auxiliar', obligatorio: true, descripcion: 'Número o nombre del auxiliar contable de esa cuenta (Mesa, Silla, Pupitre…).', ejemplo: 'PUPITRE' },
  { nombre: 'edificio', obligatorio: true, descripcion: 'Código o nombre del edificio / establecimiento.', ejemplo: 'U.E. CARAZANI' },
  { nombre: 'ambiente', obligatorio: false, descripcion: 'Código o nombre del ambiente. Vacío = «SIN ASIGNAR (ALMACÉN)».', ejemplo: 'AULA 2' },
  { nombre: 'estado', obligatorio: false, descripcion: 'Nuevo, Bueno, Regular, Malo o Pésimo. Vacío = Bueno.', ejemplo: 'Bueno' },
  { nombre: 'valor', obligatorio: true, descripcion: 'Valor en Bs (sin separador de miles).', ejemplo: 350.5 },
  { nombre: 'fecha_ingreso', obligatorio: false, descripcion: 'Fecha de ingreso dd/mm/aaaa. Vacío = hoy.', ejemplo: '15/03/2024' },
  { nombre: 'responsable', obligatorio: false, descripcion: 'Funcionario a cargo (debe existir en Catálogos → Funcionarios). Vacío = queda EN ALMACÉN.', ejemplo: 'EDWIN TONY CHUCA ORDOÑEZ' },
  { nombre: 'marca', obligatorio: false, descripcion: 'Marca.', ejemplo: '' },
  { nombre: 'modelo', obligatorio: false, descripcion: 'Modelo.', ejemplo: '' },
  { nombre: 'serie', obligatorio: false, descripcion: 'Número de serie.', ejemplo: '' },
  { nombre: 'color', obligatorio: false, descripcion: 'Color.', ejemplo: 'CAFÉ' },
  { nombre: 'observaciones', obligatorio: false, descripcion: 'Observaciones.', ejemplo: '' },
  { nombre: 'foto1', obligatorio: false, descripcion: 'Nombre del archivo de la foto 1 en la carpeta de fotos (JPG, PNG o WEBP).', ejemplo: 'pupitre_001.jpg' },
  { nombre: 'foto2', obligatorio: false, descripcion: 'Nombre del archivo de la foto 2.', ejemplo: '' },
  { nombre: 'foto3', obligatorio: false, descripcion: 'Nombre del archivo de la foto 3.', ejemplo: '' },
];
export const REGLAS_ACTIVOS = [
  'La fila 1 son los encabezados (no los cambie); los datos empiezan en la fila 2. Cada fila es UN activo.',
  'Si alguna fila tiene errores no se importa nada: corrija el Excel y vuelva a validar.',
  'Las fotos NO van dentro del Excel: póngalas todas en una carpeta y escriba en foto1, foto2 y foto3 el nombre exacto de cada archivo (con su extensión).',
  'Al importar se elige el Excel y la carpeta de fotos; SIGAA relaciona cada archivo con su activo por el nombre.',
  'Un código que ya existe en SIGAA se rechaza (no se sobrescribe).',
];

const nk = (s: unknown) => norm(s).replace(/\(.*?\)/g, '').replace(/[^A-Z0-9]+/g, ' ').trim();
const celda = (v: ExcelJS.CellValue): unknown => {
  if (v === null || v === undefined) return null;
  if (v instanceof Date) return v;
  if (typeof v === 'object') { const o = v as any; return o.result ?? o.text ?? (Array.isArray(o.richText) ? o.richText.map((r: any) => r.text).join('') : null); }
  return v;
};

export async function plantillaActivos(db: Db): Promise<Buffer> {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('DATOS');
  ws.addRow(COLUMNAS_ACTIVOS.map((c) => c.nombre));
  const cuenta = await db('af_cuentas').orderBy('id_cta').first();
  const aux = cuenta ? await db('af_auxiliares').where({ id_cta: cuenta.id_cta }).orderBy('id_aux').first() : null;
  const ed = await db('af_edificios').orderBy('cod_edif').first();
  const amb = ed ? await db('af_ambientes').where({ cod_edif: ed.cod_edif }).where('cod_amb', '>', 0).orderBy('cod_amb').first() : null;
  const fn = await db('core_funcionarios').orderBy('nombre').first();
  const ej: Record<string, unknown> = { cuenta: cuenta?.id_cta, auxiliar: aux?.auxiliar, edificio: ed?.edificio, ambiente: amb?.ambiente, responsable: fn?.nombre };
  ws.addRow(COLUMNAS_ACTIVOS.map((c) => ej[c.nombre] ?? c.ejemplo));
  COLUMNAS_ACTIVOS.forEach((c, i) => {
    const x = ws.getCell(1, i + 1);
    x.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    x.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: c.nombre.startsWith('foto') ? 'FF17693F' : c.obligatorio ? 'FFC55A11' : 'FF1F3864' } };
    x.note = c.descripcion;
    ws.getColumn(i + 1).width = Math.max(14, c.nombre.length + 6, c.nombre === 'descripcion' ? 40 : 0, c.nombre === 'responsable' ? 30 : 0);
  });
  ws.getRow(2).font = { italic: true, color: { argb: 'FF7A8699' } };
  ws.views = [{ state: 'frozen', ySplit: 1 }];
  const li = wb.addWorksheet('INSTRUCCIONES');
  li.getColumn(1).width = 28; li.getColumn(2).width = 12; li.getColumn(3).width = 100;
  li.addRow(['Importación de activos fijos desde Excel']).font = { bold: true, size: 14, color: { argb: 'FF1F3864' } };
  li.addRow([]);
  REGLAS_ACTIVOS.forEach((r) => li.addRow([r]));
  li.addRow([]);
  li.addRow(['Columna', 'Obligatoria', 'Descripción']).font = { bold: true };
  COLUMNAS_ACTIVOS.forEach((c) => li.addRow([c.nombre, c.obligatorio ? 'Sí' : 'No', c.descripcion]));
  const cat = wb.addWorksheet('CATALOGOS');
  const bloque = (col: number, titulo: string, filas: string[]) => { cat.getCell(1, col).value = titulo; cat.getCell(1, col).font = { bold: true }; filas.forEach((v, i) => { cat.getCell(i + 2, col).value = v; }); cat.getColumn(col).width = 36; };
  bloque(1, 'CUENTA (número - nombre)', (await db('af_cuentas').orderBy('id_cta')).map((c: any) => `${c.id_cta} - ${c.cuenta}`));
  bloque(2, 'AUXILIAR (cuenta: auxiliar)', (await db('af_auxiliares').orderBy(['id_cta', 'id_aux'])).map((a: any) => `${a.id_cta}: ${a.auxiliar}`));
  bloque(3, 'EDIFICIO (código - nombre)', (await db('af_edificios').orderBy('cod_edif')).map((e: any) => `${e.cod_edif} - ${e.edificio}`));
  bloque(4, 'AMBIENTE (edificio: ambiente)', (await db('af_ambientes').orderBy(['cod_edif', 'cod_amb'])).map((a: any) => `${a.cod_edif}: ${a.cod_amb} - ${a.ambiente}`));
  bloque(5, 'ESTADO', (await db('af_estados').orderBy('cod')).map((e: any) => e.estado));
  bloque(6, 'RESPONSABLE (Funcionarios)', (await db('core_funcionarios').where({ estado: 'ACTIVO' }).orderBy('nombre')).map((f: any) => f.nombre));
  return Buffer.from(await wb.xlsx.writeBuffer());
}

export function estructuraActivos() {
  return { titulo: 'Activos fijos', claveUnica: ['codigo'], columnas: COLUMNAS_ACTIVOS.map((c) => ({ encabezado: c.nombre, obligatorio: c.obligatorio, tipo: c.descripcion, ejemplo: c.ejemplo })), reglas: REGLAS_ACTIVOS };
}

class Deshacer extends Error { constructor(public resultado: unknown) { super('deshacer'); } }
const EXT_FOTO = /\.(jpe?g|png|webp)$/i;

export async function importarActivosExcel(db: Db, u: Usuario, buf: Buffer, confirmar: boolean) {
  const wb = new ExcelJS.Workbook();
  try { await wb.xlsx.load(buf as any); } catch { fail('El archivo no es un libro de Excel (.xlsx) válido.'); }
  const ws = wb.getWorksheet('DATOS') ?? wb.worksheets[0];
  if (!ws) fail('El libro no tiene hojas.');
  const cab = new Map<string, number>();
  ws.getRow(1).eachCell((c, n) => { const h = String(celda(c.value) ?? '').trim().toLowerCase().replace(/\s+/g, '_'); if (COLUMNAS_ACTIVOS.some((x) => x.nombre === h) && !cab.has(h)) cab.set(h, n); });
  const faltan = COLUMNAS_ACTIVOS.filter((c) => c.obligatorio && !cab.has(c.nombre)).map((c) => c.nombre);
  if (faltan.length) fail(`Faltan columnas obligatorias en la fila 1: ${faltan.join(', ')}. Descargue la plantilla para ver la estructura.`);

  const cuentas = await db('af_cuentas'), auxs = await db('af_auxiliares'), edifs = await db('af_edificios'), ambs = await db('af_ambientes'), estados = await db('af_estados'), funcs = await db('core_funcionarios');
  const errores: { fila: number; mensaje: string }[] = [];
  const filas: FilaActivo[] = [];
  const codigos = new Set<string>();
  const nombresFoto = new Set<string>();
  const buscar = <T,>(lista: T[], v: unknown, id: (x: T) => number, nombre: (x: T) => string): T | undefined => {
    const t = txt(v);
    const m = /^(\d+)\s*[-:]/.exec(t);
    if (/^\d+$/.test(t)) return lista.find((x) => id(x) === Number(t));
    if (m) { const p = lista.find((x) => id(x) === Number(m[1])); if (p) return p; }
    return lista.find((x) => nk(nombre(x)) === nk(t.replace(/^\d+\s*[-:]\s*/, '')));
  };
  ws.eachRow({ includeEmpty: false }, (row, n) => {
    if (n === 1) return;
    const v = (k: string) => (cab.has(k) ? celda(row.getCell(cab.get(k)!).value) : null);
    if (![...cab.keys()].some((k) => !['codigo'].includes(k) && txt(v(k)) !== '')) return;
    const er = (m: string) => errores.push({ fila: n, mensaje: m });
    const antes = errores.length;
    const descripcion = txt(v('descripcion'));
    if (!descripcion) er('La descripción es obligatoria.');
    if (descripcion.length > 240) er('La descripción admite 240 caracteres como máximo.');
    const cta = buscar(cuentas, v('cuenta'), (x: any) => x.id_cta, (x: any) => x.cuenta) as any;
    if (!cta) er(`La cuenta «${txt(v('cuenta'))}» no existe (vea la hoja CATALOGOS).`);
    const aux = cta ? (buscar(auxs.filter((a: any) => a.id_cta === cta.id_cta), v('auxiliar'), (x: any) => x.id_aux, (x: any) => x.auxiliar) as any) : undefined;
    if (cta && !aux) er(`El auxiliar «${txt(v('auxiliar'))}» no existe en la cuenta ${cta.id_cta} - ${cta.cuenta}.`);
    const ed = buscar(edifs, v('edificio'), (x: any) => x.cod_edif, (x: any) => x.edificio) as any;
    if (!ed) er(`El edificio «${txt(v('edificio'))}» no existe (vea la hoja CATALOGOS).`);
    let amb: any;
    if (ed) {
      const delEd = ambs.filter((a: any) => a.cod_edif === ed.cod_edif);
      amb = txt(v('ambiente')) ? buscar(delEd, v('ambiente'), (x: any) => x.cod_amb, (x: any) => x.ambiente) : delEd.find((a: any) => a.cod_amb === 0);
      if (!amb) er(txt(v('ambiente')) ? `El ambiente «${txt(v('ambiente'))}» no existe en el edificio ${ed.edificio}.` : `El edificio ${ed.edificio} no tiene el ambiente 0 (sin asignar).`);
    }
    const estTxt = txt(v('estado')) || 'Bueno';
    const est = estados.find((e: any) => nk(e.estado) === nk(estTxt)) as any;
    if (!est) er(`El estado «${estTxt}» no existe (Nuevo, Bueno, Regular, Malo, Pésimo).`);
    let valor = 0;
    try { valor = comoNumero(v('valor')) ?? NaN; } catch (e) { valor = NaN; }
    if (!Number.isFinite(valor) || valor < 0) er('El valor debe ser un número mayor o igual a 0.');
    let fecha = today();
    try { fecha = comoFecha(v('fecha_ingreso')) ?? today(); } catch (e) { er((e as Error).message); }
    let func: any;
    if (txt(v('responsable'))) { func = funcs.find((f: any) => nk(f.nombre) === nk(v('responsable'))); if (!func) er(`El responsable «${txt(v('responsable'))}» no está en Catálogos → Funcionarios.`); }
    const codigo = txt(v('codigo')).toUpperCase();
    if (codigo) {
      if (codigo.length > 20) er('El código admite 20 caracteres como máximo.');
      if (codigos.has(codigo)) er(`El código ${codigo} está repetido en el Excel.`);
      codigos.add(codigo);
    }
    const fotos = ['foto1', 'foto2', 'foto3'].map((k) => txt(v(k)) || null);
    for (const f of fotos) if (f) { if (!EXT_FOTO.test(f)) er(`La foto «${f}» debe ser JPG, PNG o WEBP.`); nombresFoto.add(f); }
    if (errores.length > antes) return;
    filas.push({ fila: n, codigo, descripcion, id_cta: cta.id_cta, id_aux: aux.id_aux, auxiliar: aux.auxiliar, cod_edif: ed.cod_edif, cod_amb: amb.cod_amb, estado: est.estado, valor, fecha_ingreso: fecha,
      marca: txt(v('marca')), modelo: txt(v('modelo')), serie: txt(v('serie')), color: txt(v('color')), observaciones: txt(v('observaciones')), funcionario: func?.nombre, ci: func?.ci, fotos });
  });
  if (!filas.length && !errores.length) fail('El Excel no tiene filas de datos (los datos empiezan en la fila 2).');
  if (codigos.size) {
    const ya = await db('af_activos').whereIn('codigo', [...codigos]).select('codigo');
    for (const y of ya) for (const f of filas.filter((x) => x.codigo === y.codigo)) errores.push({ fila: f.fila, mensaje: `El código ${y.codigo} ya existe en SIGAA.` });
  }
  if (errores.length) return { importado: false, total: filas.length, creados: [] as Creado[], errores: errores.sort((a, b) => a.fila - b.fila), fotosEsperadas: [...nombresFoto] };
  try {
    return await db.transaction(async (trx) => {
      const creados = await insertarActivos(trx, u, filas, 'IMPORT. EXCEL');
      const res = { importado: confirmar, total: filas.length, creados, errores: [] as { fila: number; mensaje: string }[], fotosEsperadas: [...nombresFoto] };
      if (!confirmar) throw new Deshacer(res);
      await bitacora(trx, u, 'ACTIVOS FIJOS', 'IMPORTACIÓN EXCEL', '', `${creados.length} activo(s) importados`);
      return res;
    });
  } catch (e) {
    if (e instanceof Deshacer) return e.resultado as { importado: boolean; total: number; creados: Creado[]; errores: { fila: number; mensaje: string }[]; fotosEsperadas: string[] };
    throw e;
  }
}
