/** Importación de catálogos desde Excel: estructura, plantilla descargable y carga con validación. */
import ExcelJS from 'exceljs';
import type { Db, Usuario } from '../core/context.js';
import { fail } from '../core/errors.js';
import { bitacora } from '../core/services.js';
import { sinTildes } from '../core/util.js';
import { comoNumero } from '../vsiaf/coercion.js';
import { limpiar, maestroPorKey, type MCol, type Maestro } from './maestros.js';

const EJEMPLOS: Record<string, Record<string, string | number>> = {
  proyectos: { nombre: 'FUNCIONAMIENTO ADMINISTRATIVO', estado: 'ACTIVO' },
  aperturas: { apertura: '00 0 001', descripcion: 'Funcionamiento del Ejecutivo Municipal', presupuesto: 60000 },
  partidas: { partida: '31120', descripcion: 'Gastos de capital y otros' },
};
const ejemplo = (m: Maestro, c: MCol): string | number => {
  const e = EJEMPLOS[m.key]?.[c.name];
  if (e !== undefined) return e;
  if (c.type === 'number') return 1;
  if (c.type === 'date') return '2026-01-31';
  if (c.type === 'select') return c.options?.[0] ?? '';
  return 'Texto';
};
const clave = (m: Maestro): string[] => (m.autoId ? [m.cols.find((c) => c.required && c.type === 'text')?.name ?? m.cols[0].name] : m.pk);
const tipoTxt = (c: MCol) => (c.type === 'number' ? 'Número' : c.type === 'date' ? 'Fecha (AAAA-MM-DD o fecha de Excel)' : c.type === 'select' ? `Una de: ${(c.options ?? []).join(', ') || 'lista del catálogo'}` : 'Texto');

/** Columnas que debe tener el Excel (la fila 1 son los encabezados). */
export function estructuraImportacion(key: string) {
  const m = maestroPorKey(key);
  const k = clave(m);
  return {
    key: m.key, titulo: m.titulo, claveUnica: k.map((n) => m.cols.find((c) => c.name === n)?.label ?? n),
    columnas: m.cols.filter((c) => !c.readonly).map((c) => ({ encabezado: c.label, obligatorio: !!c.required, tipo: tipoTxt(c), ejemplo: ejemplo(m, c) })),
    reglas: [
      'La fila 1 contiene los encabezados (no los cambie); los datos empiezan en la fila 2.',
      `Si ya existe un registro con el mismo valor de «${k.map((n) => m.cols.find((c) => c.name === n)?.label ?? n).join(' + ')}», se ACTUALIZA; si no existe, se CREA.`,
      'Si alguna fila tiene errores no se importa nada: corrija el Excel y vuelva a cargarlo.',
      'Se lee la primera hoja del libro. Números sin separador de miles (60000.50).',
    ],
  };
}

export async function plantillaImportacion(key: string): Promise<Buffer> {
  const m = maestroPorKey(key);
  const est = estructuraImportacion(key);
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('DATOS');
  const cols = m.cols.filter((c) => !c.readonly);
  ws.addRow(cols.map((c) => c.label));
  ws.addRow(cols.map((c) => ejemplo(m, c)));
  cols.forEach((c, i) => {
    const cell = ws.getCell(1, i + 1);
    cell.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: c.required ? 'FFC55A11' : 'FF1F3864' } };
    ws.getColumn(i + 1).width = Math.max(16, (c.width ?? 2) * 12);
  });
  ws.getRow(2).font = { italic: true, color: { argb: 'FF7A8699' } };
  ws.views = [{ state: 'frozen', ySplit: 1 }];
  const li = wb.addWorksheet('INSTRUCCIONES');
  li.getColumn(1).width = 110;
  [`Importación de «${m.titulo}»`, '', ...est.reglas, '', 'La fila 2 de la hoja DATOS es un ejemplo: bórrela o reemplácela por sus datos.', 'Los encabezados en naranja son obligatorios.'].forEach((t, i) => {
    const c = li.getCell(i + 1, 1); c.value = t; c.alignment = { wrapText: true };
    if (i === 0) c.font = { bold: true, size: 14, color: { argb: 'FF1F3864' } };
  });
  return Buffer.from(await wb.xlsx.writeBuffer());
}

const celdaATexto = (v: ExcelJS.CellValue): unknown => {
  if (v === null || v === undefined) return null;
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  if (typeof v === 'object') { const o = v as any; return o.result ?? o.text ?? (Array.isArray(o.richText) ? o.richText.map((r: any) => r.text).join('') : null); }
  return v;
};
const nk = (s: string) => sinTildes(s).toLowerCase().replace(/\(.*?\)/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

export async function importarMaestro(db: Db, u: Usuario, key: string, buf: Buffer) {
  const m = maestroPorKey(key);
  const cols = m.cols.filter((c) => !c.readonly);
  const wb = new ExcelJS.Workbook();
  try { await wb.xlsx.load(buf as any); } catch { fail('El archivo no es un libro de Excel (.xlsx) válido.'); }
  const ws = wb.worksheets[0];
  if (!ws) fail('El libro no tiene hojas.');
  // encabezados: por etiqueta o por nombre interno
  const cab = new Map<number, MCol>();
  ws.getRow(1).eachCell((cell, n) => {
    const h = nk(String(celdaATexto(cell.value) ?? ''));
    const c = cols.find((x) => nk(x.label) === h || nk(x.name) === h);
    if (c && !cab.has(n)) cab.set(n, c);
  });
  const faltan = cols.filter((c) => c.required && ![...cab.values()].includes(c));
  if (faltan.length) fail(`Faltan columnas obligatorias en la fila 1: ${faltan.map((c) => c.label).join(', ')}. Descargue la plantilla para ver la estructura.`);
  const k = clave(m);
  const errores: { fila: number; mensaje: string }[] = [];
  const filas: { n: number; v: Record<string, unknown> }[] = [];
  const vistos = new Set<string>();
  ws.eachRow({ includeEmpty: false }, (row, n) => {
    if (n === 1) return;
    const d: Record<string, unknown> = {};
    let alguno = false;
    for (const [col, c] of cab) {
      let v = celdaATexto(row.getCell(col).value);
      if (v !== null && v !== '') alguno = true;
      if (c.type === 'number' && typeof v === 'string') { try { v = comoNumero(v); } catch (e) { errores.push({ fila: n, mensaje: `${c.label}: ${(e as Error).message}` }); v = null; } }
      else if (typeof v === 'number' && c.type !== 'number') v = String(v);
      d[c.name] = v;
    }
    if (!alguno) return;
    try {
      const v = limpiar(m, d, true);
      const id = k.map((x) => String(v[x] ?? '')).join('|');
      if (vistos.has(id)) throw new Error(`Está repetido dentro del Excel (${id}).`);
      vistos.add(id);
      filas.push({ n, v });
    } catch (e) { errores.push({ fila: n, mensaje: String((e as Error).message).replace(/^Datos inválidos:\n?/, '').replace(/^- /gm, '').replace(/\n/g, ' ') }); }
  });
  if (!filas.length && !errores.length) fail('El Excel no tiene filas de datos (los datos empiezan en la fila 2).');
  if (errores.length) return { importado: false, creados: 0, actualizados: 0, errores: errores.sort((a, b) => a.fila - b.fila) };
  let creados = 0, actualizados = 0;
  await db.transaction(async (trx) => {
    for (const { v } of filas) {
      const w = Object.fromEntries(k.map((x) => [x, v[x]]));
      const ex = await trx(m.tabla).where(w).first();
      if (ex) { const up = { ...v }; for (const x of m.pk) delete up[x]; await trx(m.tabla).where(w).update(up); actualizados++; }
      else { await trx(m.tabla).insert(v); creados++; }
    }
    await bitacora(trx, u, 'CATÁLOGOS', `IMPORTACIÓN EXCEL ${m.titulo}`.slice(0, 80), '', `${creados} creado(s), ${actualizados} actualizado(s)`);
  });
  return { importado: true, creados, actualizados, errores: [] };
}
