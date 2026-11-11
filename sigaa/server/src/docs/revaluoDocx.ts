/** Informes Word (.docx) del revalúo técnico: Informe Técnico (estructura NC 4, inc. 7) y Anexos (cuadro comparativo, cotizaciones y asiento contable). */
import fs from 'node:fs';
import path from 'node:path';
import {
  AlignmentType, BorderStyle, Document, Footer, Header, ImageRun, PageNumber, PageOrientation, Packer, Paragraph, ShadingType, Table, TableCell, TableRow, TextRun, VerticalAlign, WidthType,
} from 'docx';
import type { Db } from '../core/context.js';
import { cfgAll } from '../core/services.js';
import { rutaLogo, formatoImagen } from '../core/logo.js';
import { fechaLiteral, fmt2, fmtDate, num, round, today, txt } from '../core/util.js';
import { FOTOS_DIR } from './activos.js';
import { FACTORES, obtenerLote } from '../modules/activos/revaluo.js';

const FUENTE = 'Calibri';
const AZUL = '1F3A5F';
const GRIS = 'EEF2F7';

/** Tamaño de una imagen PNG/JPG (para no deformarla). */
export function tamanoImagen(b: Buffer): { w: number; h: number } | null {
  if (formatoImagen(b) === 'png' && b.length > 24) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  if (formatoImagen(b) === 'jpg') {
    let i = 2;
    while (i + 9 < b.length) {
      if (b[i] !== 0xff) { i++; continue; }
      const m = b[i + 1];
      if (m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc) return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
      i += 2 + b.readUInt16BE(i + 2);
    }
  }
  return null;
}

function imagen(buf: Buffer, maxW: number, maxH: number): ImageRun | null {
  const t = formatoImagen(buf);
  if (t !== 'png' && t !== 'jpg') return null;
  const s = tamanoImagen(buf) || { w: 4, h: 3 };
  const k = Math.min(maxW / s.w, maxH / s.h);
  return new ImageRun({ type: t, data: buf, transformation: { width: Math.max(1, Math.round(s.w * k)), height: Math.max(1, Math.round(s.h * k)) } });
}

const run = (text: string, o: { b?: boolean; i?: boolean; size?: number; color?: string } = {}) => new TextRun({ text, bold: o.b, italics: o.i, size: o.size ?? 22, color: o.color, font: FUENTE });
const P = (text: string | TextRun[], o: { align?: (typeof AlignmentType)[keyof typeof AlignmentType]; after?: number; b?: boolean; size?: number; i?: boolean; indent?: number } = {}) =>
  new Paragraph({ alignment: o.align ?? AlignmentType.JUSTIFIED, spacing: { after: o.after ?? 120, line: 276 }, indent: o.indent ? { left: o.indent } : undefined, children: typeof text === 'string' ? [run(text, { b: o.b, size: o.size, i: o.i })] : text });
const H1 = (t: string) => new Paragraph({ spacing: { before: 240, after: 120 }, keepNext: true, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: AZUL, space: 2 } }, children: [run(t.toUpperCase(), { b: true, size: 24, color: AZUL })] });
const VI = (t: string) => new Paragraph({ spacing: { after: 60 }, indent: { left: 360, hanging: 240 }, alignment: AlignmentType.JUSTIFIED, children: [run('• ' + t)] });

const borde = { style: BorderStyle.SINGLE, size: 4, color: '9AA7B8' };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };
function celda(texto: string | (Paragraph | TextRun)[] | Paragraph[], w: number, o: { head?: boolean; align?: (typeof AlignmentType)[keyof typeof AlignmentType]; b?: boolean; size?: number; shade?: string } = {}) {
  const hijos = typeof texto === 'string'
    ? [new Paragraph({ alignment: o.align ?? AlignmentType.LEFT, children: [run(texto, { b: o.head || o.b, size: o.size ?? 18, color: o.head ? 'FFFFFF' : undefined })] })]
    : (texto as Paragraph[]);
  return new TableCell({ width: { size: w, type: WidthType.DXA }, borders: bordes, verticalAlign: VerticalAlign.CENTER, margins: { top: 50, bottom: 50, left: 80, right: 80 }, shading: o.head ? { type: ShadingType.CLEAR, fill: AZUL, color: 'auto' } : o.shade ? { type: ShadingType.CLEAR, fill: o.shade, color: 'auto' } : undefined, children: hijos });
}
function tabla(anchos: number[], cab: string[], filas: (string | Paragraph[])[][], o: { aligns?: ((typeof AlignmentType)[keyof typeof AlignmentType])[]; pie?: string[]; size?: number } = {}) {
  const total = anchos.reduce((a, b) => a + b, 0);
  const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: cab.map((c, i) => celda(c, anchos[i], { head: true, align: AlignmentType.CENTER, size: o.size })) })];
  for (const f of filas) rows.push(new TableRow({ cantSplit: true, children: f.map((c, i) => celda(c as any, anchos[i], { align: o.aligns?.[i], size: o.size })) }));
  if (o.pie) rows.push(new TableRow({ children: o.pie.map((c, i) => celda(c, anchos[i], { b: true, align: o.aligns?.[i], shade: GRIS, size: o.size })) }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: anchos, rows });
}

async function contexto(db: Db, id: number) {
  const l = await obtenerLote(db, id);
  const c = await cfgAll(db);
  const lp = await rutaLogo(db);
  const logo = lp ? fs.readFileSync(lp) : null;
  return { l, c, logo };
}

function encabezado(c: Record<string, string>, logo: Buffer | null, titulo: string, borrador: boolean) {
  const img = logo ? imagen(logo, 70, 70) : null;
  const t = new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [1500, 7860],
    borders: { top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' } },
    rows: [new TableRow({ children: [
      new TableCell({ width: { size: 1500, type: WidthType.DXA }, children: [new Paragraph({ children: img ? [img] : [run('')] })] }),
      new TableCell({ width: { size: 7860, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, children: [
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [run((c.Entidad || '').toUpperCase(), { b: true, size: 26, color: AZUL })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [run(c.Secretaria || 'Unidad Administrativa y Financiera', { size: 20 })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [run(c.UnidadAF || 'Unidad de Activos Fijos', { size: 20 })] }),
      ] }),
    ] })],
  });
  return [t, new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: borrador ? 40 : 200 }, children: [run(titulo, { b: true, size: 30, color: AZUL })] }),
    ...(borrador ? [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [run('DOCUMENTO PRELIMINAR (el lote aún no está aprobado)', { b: true, size: 18, color: 'B3261E' })] })] : [])];
}

function pie(c: Record<string, string>, nro: string) {
  return new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run(`${c.Sigla || ''} · ${nro} · Página `, { size: 16, color: '666666' }), new TextRun({ children: [PageNumber.CURRENT], size: 16, font: FUENTE, color: '666666' }), run(' de ', { size: 16, color: '666666' }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, font: FUENTE, color: '666666' })] })] });
}
const cabecera = (c: Record<string, string>, txtc: string) => new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run(`${c.Sigla || c.Entidad || ''} — ${txtc}`, { size: 16, color: '666666' })] })] });

function firmas(filas: { nombre: string; cargo: string; rol: string }[]) {
  const sinB = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  const n = Math.min(3, filas.length) || 1;
  const w = Math.floor(9360 / n);
  const grupos: typeof filas[] = [];
  for (let i = 0; i < filas.length; i += n) grupos.push(filas.slice(i, i + n));
  return new Table({
    width: { size: w * n, type: WidthType.DXA }, columnWidths: Array(n).fill(w),
    borders: { top: sinB, bottom: sinB, left: sinB, right: sinB, insideHorizontal: sinB, insideVertical: sinB },
    rows: grupos.map((g) => new TableRow({ cantSplit: true, children: Array.from({ length: n }, (_, k) => g[k]).map((f) => new TableCell({ width: { size: w, type: WidthType.DXA }, children: f ? [
      new Paragraph({ spacing: { before: 700 }, children: [] }),
      new Paragraph({ alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 6, color: '000000', space: 4 } }, spacing: { after: 20 }, children: [run(f.nombre || '................................', { b: true, size: 18 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 }, children: [run(f.cargo || '', { size: 16 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [run(f.rol, { b: true, size: 16, color: AZUL })] }),
    ] : [new Paragraph({ children: [] })] })) })),
  });
}

/** Integrantes de la comisión: una línea por persona, "Nombre | Cargo". */
export function comisionLista(texto: string) {
  return String(texto || '').split(/\r?\n/).map((s) => s.trim()).filter(Boolean).map((s) => { const [n, ...r] = s.split('|'); return { nombre: txt(n), cargo: txt(r.join('|')), rol: 'MIEMBRO DE LA COMISIÓN CALIFICADORA' }; });
}

function datosGenerales(l: any, c: Record<string, string>) {
  const lugar = `${c.Municipio || ''}${c.Departamento ? ', ' + c.Departamento : ''}`;
  return tabla([2400, 6960], ['Dato', 'Detalle'], [
    ['Lote / Informe', `${l.nro}${l.estado === 'APROBADO' ? ' (aprobado)' : ' (preliminar)'}`],
    ['Lugar y fecha', `${lugar}, ${fechaLiteral(l.estado === 'APROBADO' && l.fecha_aprob ? l.fecha_aprob : today())}`],
    ['Perito / responsable de la tasación', `${l.perito || '—'}${l.perito_cargo ? ' — ' + l.perito_cargo : ''}`],
    ['Resolución de aprobación', l.resolucion || '—'],
  ], { size: 20 });
}

// ───────── Entregable 1: Informe Técnico ─────────
export async function informeTecnicoDocx(db: Db, id: number): Promise<Buffer> {
  const { l, c, logo } = await contexto(db, id);
  const T = l.totales;
  const borrador = l.estado !== 'APROBADO';
  const nCot = l.items.reduce((s: number, i: any) => s + i.cotizaciones.length, 0);
  const nFotos = l.items.reduce((s: number, i: any) => s + [1, 2, 3, 4].filter((k) => i['foto' + k]).length, 0);
  const proveedores = [...new Set(l.items.flatMap((i: any) => i.cotizaciones.map((x: any) => txt(x.proveedor))).filter(Boolean))] as string[];
  const codigos = l.items.map((i: any) => i.codigo);
  const nMov = codigos.length ? Number(((await db('af_movimientos').whereIn('codigo', codigos).count({ n: '*' }).first()) as any).n) : 0;
  const porEstado = ['bueno', 'regular', 'malo'].map((e) => {
    const x = l.items.filter((i: any) => txt(i.estado_fisico).toLowerCase() === e);
    const fs2 = x.map((i: any) => i.factor).filter((f: any) => f != null);
    return { estado: e[0].toUpperCase() + e.slice(1), n: x.length, rango: `${FACTORES[e].min.toFixed(2)} – ${FACTORES[e].max.toFixed(2)}`, aplicado: fs2.length ? `${Math.min(...fs2).toFixed(2)} – ${Math.max(...fs2).toFixed(2)}` : '—' };
  });
  const cm = comisionLista(l.comision);
  const body: (Paragraph | Table)[] = [
    ...encabezado(c, logo, 'INFORME TÉCNICO DE REVALÚO DE ACTIVOS FIJOS', borrador),
    datosGenerales(l, c),
    H1('1. Antecedentes y justificación'),
    P(`${c.Entidad || 'La entidad'} mantiene registrados activos fijos que, por el transcurso del tiempo, se encuentran totalmente depreciados y figuran en libros con un valor residual de Bs 1,00 (un boliviano) pese a que continúan en uso y en estado físico Bueno, Regular o Malo operativo. Esta situación subvalúa el patrimonio institucional y distorsiona la información de los estados financieros.`),
    P(`En cumplimiento de la Norma de Contabilidad Nº 4 (Revalorización Técnica de Activos Fijos), la Unidad Administrativa y Financiera dispuso el revalúo técnico de ${T.activos} activo(s) fijo(s), seleccionados automáticamente por cumplir tres condiciones: (1) valor en libros neto de Bs 1; (2) estado físico Bueno, Regular o Malo; y (3) condición operativa. Se excluyeron los bienes en desuso, obsoletos inservibles o propuestos para baja.`),
    P(l.descripcion ? `Objeto del lote: ${l.descripcion}.` : ''),
    H1('2. Base legal'),
    VI('Norma de Contabilidad Nº 4 (NC 4) – Revalorización Técnica de Activos Fijos (Colegio de Auditores / Contadores de Bolivia), en particular su inciso 7 sobre el contenido del informe técnico.'),
    VI('Normas Básicas del Sistema de Administración de Bienes y Servicios (NB-SABS), aprobadas por D.S. Nº 0181.'),
    VI('Ley Nº 1178 de Administración y Control Gubernamentales (SAFCO) y Principios, Normas Generales y Básicas de Contabilidad Integrada.'),
    VI('Decreto Supremo Nº 24051 – Reglamento del Impuesto sobre las Utilidades de las Empresas (IUE), en lo aplicable a la depreciación de activos fijos.'),
    VI('NIC 16 / NIIF – Propiedades, planta y equipo: modelo de revaluación (valor razonable), como referencia técnica complementaria.'),
    H1('3. Bases técnicas'),
    P('Método comparativo o de consulta de mercado con factores de depreciación física:', { after: 60 }),
    VI(`Para cada activo se obtuvo de 1 a 3 cotizaciones del Valor a Nuevo (VN) de bienes idénticos o similares, con su respaldo (proforma, proveedor, fecha, NIT o enlace). En total se consideraron ${nCot} cotización(es)${proveedores.length ? ` de ${proveedores.length} fuente(s): ${proveedores.slice(0, 8).join(', ')}${proveedores.length > 8 ? ', entre otras' : ''}` : ''}.`),
    VI('Tratamiento de datos: el VN base de cada activo es el promedio simple o la mediana de sus cotizaciones, según lo decidido por el perito en la hoja de tasación.'),
    VI('Valor Técnico Revaluado (VTR) = VN base × coeficiente de conservación. El resultado no puede ser inferior a Bs 1,00.'),
    VI('La nueva vida útil residual fue determinada por el perito / comisión, justificada por la inspección física y el registro fotográfico de cada bien.'),
    P('Coeficientes de conservación por estado físico:', { after: 60 }),
    tabla([2200, 1400, 2800, 2960], ['Estado físico', 'Activos', 'Rango permitido', 'Factor aplicado (mín – máx)'], porEstado.map((e) => [e.estado, String(e.n), e.rango, e.aplicado]), { aligns: [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER], size: 20 }),
    H1('4. Documentación examinada'),
    VI('Inventario y registros auxiliares de activos fijos (código, cuenta, auxiliar, responsable, ubicación y valor en libros).'),
    VI(`Fichas técnicas y registro fotográfico: ${nFotos} fotografía(s) de ${T.activos} activo(s).`),
    VI(`Historial de movimientos y mantenimientos registrados en el kardex: ${nMov} movimiento(s).`),
    VI(`Cotizaciones y proformas de respaldo: ${nCot}.`),
    H1('5. Resultados del revalúo'),
    tabla([4400, 1200, 1900, 1860], ['Cuenta contable', 'Activos', 'Incremento (Bs)', 'Reserva'], l.por_cuenta.map((x: any) => [x.cuenta, String(x.activos), fmt2(x.incremento), 'Reserva por Revalúos Técnicos']), { aligns: [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT, AlignmentType.LEFT], pie: ['TOTAL', String(T.activos), fmt2(T.incremento), ''], size: 20 }),
    P(`El valor anterior de los ${T.activos} activo(s) era de Bs ${fmt2(T.valor_anterior)}; el Valor Técnico Revaluado asciende a Bs ${fmt2(T.vtr)}, lo que genera un incremento patrimonial de Bs ${fmt2(T.incremento)} imputable a la cuenta de patrimonio "Reserva por Revalúos Técnicos". El detalle por activo, con fotografías, cotizaciones y el asiento contable modelo, se presenta en el documento Anexos.`),
    H1('6. Conclusiones y recomendaciones'),
    VI(`Conclusión: los ${T.activos} activo(s) revaluados mantienen utilidad operativa y su valor de mercado ajustado por conservación supera ampliamente el valor residual de Bs 1,00 registrado en libros.`),
    VI('Recomendación 1: aprobar el revalúo mediante resolución de la Máxima Autoridad Ejecutiva y registrar el incremento en la cuenta "Reserva por Revalúos Técnicos".'),
    VI('Recomendación 2: actualizar el registro contable (VSIAF / SIGEP) con el nuevo valor y la nueva vida útil residual, y calcular la depreciación sobre esos nuevos valores desde la fecha del revalúo.'),
    VI('Recomendación 3: conservar los documentos de respaldo (cotizaciones, fotografías, hojas de tasación) para fines de control interno y auditoría.'),
    VI('Recomendación 4: repetir el revalúo cuando la normativa o el estado de los bienes lo requiera, y mantener actualizado el campo "Operativo" de cada activo.'),
    P(''),
    firmas([
      { nombre: l.perito, cargo: l.perito_cargo, rol: 'PERITO / RESPONSABLE DE LA TASACIÓN' },
      { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' },
      ...cm,
    ]),
  ];
  const doc = new Document({
    creator: c.Entidad || 'SIGAA', title: `Informe Técnico de Revalúo ${l.nro}`,
    styles: { default: { document: { run: { font: FUENTE, size: 22 } } } },
    sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1200, bottom: 1100, left: 1440, right: 1440 } } }, headers: { default: cabecera(c, 'Informe Técnico de Revalúo') }, footers: { default: pie(c, l.nro) }, children: body }],
  });
  return Packer.toBuffer(doc);
}

// ───────── Entregable 2: Anexos ─────────
function fotoParrafos(i: any): Paragraph[] {
  for (const k of [1, 2, 3, 4]) {
    const f = i['foto' + k];
    if (!f) continue;
    const p = path.join(FOTOS_DIR(), path.basename(f));
    if (!fs.existsSync(p)) continue;
    const img = imagen(fs.readFileSync(p), 90, 68);
    if (img) return [new Paragraph({ alignment: AlignmentType.CENTER, children: [img] })];
  }
  return [new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Sin foto', { i: true, size: 16, color: '888888' })] })];
}
const parr = (t: string, al: (typeof AlignmentType)[keyof typeof AlignmentType] = AlignmentType.LEFT, b = false) => [new Paragraph({ alignment: al, children: [run(t, { size: 16, b })] })];

export async function anexosDocx(db: Db, id: number): Promise<Buffer> {
  const { l, c, logo } = await contexto(db, id);
  const T = l.totales;
  const borrador = l.estado !== 'APROBADO';
  const anchos = [450, 1250, 1900, 1300, 1150, 1500, 950, 1100, 1100, 800]; // 11500 (hoja carta horizontal)
  const filas = l.items.map((i: any, n: number) => {
    const vn = i.cotizaciones.length ? `${fmt2(i.vn_base)} (${i.metodo === 'MEDIANA' ? 'mediana' : 'promedio'} de ${i.cotizaciones.length})` : '—';
    const vida = num(i.vida_anios) + num(i.vida_meses) / 12;
    return [
      parr(String(n + 1), AlignmentType.CENTER), parr(i.codigo),
      [new Paragraph({ children: [run(i.descripcion || '', { size: 16, b: true })] }), new Paragraph({ children: [run(i.auxiliar || '', { size: 15, color: '555555' })] })],
      parr(`${i.estado_fisico}; operativo: ${i.operativo === 'NO' ? 'No' : 'Sí'}`),
      fotoParrafos(i), parr(vn, AlignmentType.RIGHT), parr('1,00', AlignmentType.RIGHT), parr(fmt2(i.vtr), AlignmentType.RIGHT, true), parr(fmt2(i.incremento), AlignmentType.RIGHT),
      parr(vida ? vida.toLocaleString('es-BO', { maximumFractionDigits: 1 }) : '—', AlignmentType.CENTER),
    ];
  });
  const cot = l.items.flatMap((i: any) => i.cotizaciones.map((x: any, k: number) => [i.codigo, String(k + 1), x.proveedor, x.nit || '—', fmtDate(x.fecha), x.nro_proforma || '—', x.referencia || '—', fmt2(x.valor)]));
  const total = T.incremento;
  const debitos = l.por_cuenta.map((x: any) => [`Activo Fijo — ${x.cuenta}`, fmt2(x.incremento), '']);
  const glosa = `Por el revalúo técnico de ${T.activos} activo(s) fijo(s) totalmente depreciados (valor residual Bs 1) según Informe Técnico ${l.nro}${l.resolucion ? ' y Resolución ' + l.resolucion : ''}, conforme a la NC 4 (Revalorización Técnica).`;
  const body: (Paragraph | Table)[] = [
    ...encabezado(c, logo, 'ANEXOS DEL INFORME TÉCNICO DE REVALÚO', borrador),
    P(`Lote ${l.nro} · ${l.descripcion || ''}`, { align: AlignmentType.CENTER, after: 200 }),
    H1('Anexo 1. Cuadro comparativo de valores'),
    tabla(anchos, ['N°', 'Código', 'Auxiliar / descripción', 'Estado físico y funcional', 'Fotografía', 'Cotización de referencia VN (Bs)', 'Valor anterior (Bs)', 'VTR (Bs)', 'Incremento = VTR − 1 (Bs)', 'Vida útil restante (años)'], filas, {
      pie: ['', 'TOTAL', `${T.activos} activo(s)`, '', '', '', fmt2(T.valor_anterior), fmt2(T.vtr), fmt2(T.incremento), ''],
      aligns: [AlignmentType.CENTER, AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.RIGHT, AlignmentType.CENTER], size: 16,
    }),
    H1('Anexo 2. Detalle de cotizaciones (respaldo del Valor a Nuevo)'),
    cot.length ? tabla([1500, 500, 2400, 1200, 1200, 1300, 2300, 1100], ['Código', 'N°', 'Proveedor / fuente', 'NIT', 'Fecha', 'Proforma', 'Referencia / enlace', 'VN (Bs)'], cot, { size: 16, aligns: [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.LEFT, AlignmentType.LEFT, AlignmentType.RIGHT] }) : P('No hay cotizaciones registradas.'),
    H1('Anexo 3. Justificación técnica por activo'),
    tabla([1700, 1000, 1000, 7800], ['Código', 'Factor', 'Vida útil', 'Justificación técnica del perito'], l.items.map((i: any) => [i.codigo, i.factor == null ? '—' : Number(i.factor).toFixed(2), `${i.vida_anios}a ${i.vida_meses}m`, i.justificacion || '—']), { size: 16, aligns: [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.LEFT] }),
    H1('Anexo 4. Asiento contable modelo sugerido'),
    P('Modelo referencial; el registro definitivo corresponde a la Unidad de Contabilidad según el Plan de Cuentas vigente de la entidad.', { i: true, size: 18 }),
    tabla([6400, 2550, 2550], ['Cuenta', 'Debe (Bs)', 'Haber (Bs)'], [...debitos, ['Reserva por Revalúos Técnicos (Patrimonio)', '', fmt2(total)]], { aligns: [AlignmentType.LEFT, AlignmentType.RIGHT, AlignmentType.RIGHT], pie: ['SUMAS IGUALES', fmt2(total), fmt2(total)], size: 20 }),
    P(''),
    P([run('Glosa: ', { b: true }), run(glosa)]),
    P(''),
    firmas([{ nombre: l.perito, cargo: l.perito_cargo, rol: 'PERITO / RESPONSABLE DE LA TASACIÓN' }, { nombre: c.NombreCON, cargo: c.CargoCON, rol: 'CONTABILIDAD' }, { nombre: c.NombreRAF, cargo: c.CargoRAF, rol: 'RESPONSABLE DE ACTIVOS FIJOS' }, ...comisionLista(l.comision)]),
  ];
  const doc = new Document({
    creator: c.Entidad || 'SIGAA', title: `Anexos del Informe de Revalúo ${l.nro}`,
    styles: { default: { document: { run: { font: FUENTE, size: 22 } } } },
    sections: [{ properties: { page: { size: { width: 12240, height: 15840, orientation: PageOrientation.LANDSCAPE }, margin: { top: 1000, bottom: 900, left: 1000, right: 1000 } } }, headers: { default: cabecera(c, 'Anexos del Informe de Revalúo') }, footers: { default: pie(c, l.nro) }, children: body }],
  });
  return Packer.toBuffer(doc);
}
