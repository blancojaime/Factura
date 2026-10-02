import type { Db } from '../core/context.js';
import type { Col } from '../pdf/builder.js';
import { PdfDoc, loadHeader } from '../pdf/builder.js';
import { tablaAExcel } from '../pdf/xlsx.js';
import { cfg } from '../core/services.js';
import { BusinessError } from '../core/errors.js';

export type Params = Record<string, string | undefined>;

export interface Firma {
  nombre?: string;
  cargo?: string;
  rol: string;
}
export interface Tabla {
  titulo: string;
  subtitulo?: string;
  cols: Col[];
  filas: unknown[][];
  totales?: unknown[];
  landscape?: boolean;
  firmas?: Firma[];
  /** Tablas adicionales (secciones) que se agregan después de la principal. */
  extra?: { titulo: string; cols: Col[]; filas: unknown[][]; totales?: unknown[] }[];
  unidad?: 'UnidadAlm' | 'UnidadAF' | 'combustible';
  nota?: string;
}

export interface Reporte {
  id: string;
  nombre: string;
  modulo: 'alm' | 'com' | 'af';
  /** Parámetros que acepta (para construir el formulario en la interfaz). */
  params: { name: string; label: string; type: 'date' | 'text' | 'bodega' | 'select' | 'funcionario' | 'edificio'; options?: string[] }[];
  ejecutar(db: Db, p: Params): Promise<Tabla>;
}

export const REGISTRO = new Map<string, Reporte>();
export const registrar = (...rs: Reporte[]) => rs.forEach((r) => REGISTRO.set(r.id, r));

export async function renderTablaPdf(db: Db, t: Tabla): Promise<Buffer> {
  const header = await loadHeader(db, t.unidad ?? 'UnidadAlm');
  const pdf = new PdfDoc({ titulo: t.titulo, subtitulo: t.subtitulo, header, landscape: t.landscape });
  if (t.nota) pdf.parrafo(t.nota, { size: 8, align: 'left' });
  pdf.tabla(t.cols, t.filas, { totales: t.totales });
  for (const e of t.extra ?? []) {
    pdf.seccion(e.titulo).tabla(e.cols, e.filas, { totales: e.totales });
  }
  if (t.firmas?.length) pdf.firmas(t.firmas);
  return pdf.buffer();
}

export async function renderTablaXlsx(db: Db, t: Tabla): Promise<Buffer> {
  const entidad = await cfg(db, 'Entidad');
  const base = { entidad, titulo: t.titulo, subtitulo: t.subtitulo, cols: t.cols, filas: t.filas, totales: t.totales };
  return tablaAExcel([base, ...(t.extra ?? []).map((e) => ({ entidad, titulo: e.titulo, cols: e.cols, filas: e.filas, totales: e.totales }))]);
}

export async function ejecutarReporte(db: Db, id: string, p: Params): Promise<{ rep: Reporte; tabla: Tabla }> {
  const rep = REGISTRO.get(id);
  if (!rep) throw new BusinessError(`El reporte "${id}" no existe.`);
  return { rep, tabla: await rep.ejecutar(db, p) };
}

export const sumCol = (filas: unknown[][], i: number) => filas.reduce((t, f) => t + (Number(f[i]) || 0), 0);
