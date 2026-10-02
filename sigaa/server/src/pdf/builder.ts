/**
 * Generador de documentos PDF institucionales (pdfkit): encabezado de la entidad, datos clave-valor,
 * secciones, tablas con salto de página y repetición de encabezado, bloque de firmas y pie con paginación.
 */
import PDFDocument from 'pdfkit';
import fs from 'node:fs';
import { fmt2, fmtCant, fmtDate, fechaLiteral, today, txt } from '../core/util.js';
import type { Db } from '../core/context.js';
import { cfgAll } from '../core/services.js';

export interface Header {
  entidad: string;
  secretaria: string;
  unidad: string;
  gestion: string;
  municipio: string;
  departamento: string;
  logo?: string;
  cfg: Record<string, string>;
}
export async function loadHeader(db: Db, unidadKey: 'UnidadAlm' | 'UnidadAF' | 'combustible' = 'UnidadAlm'): Promise<Header> {
  const c = await cfgAll(db);
  const unidad = unidadKey === 'combustible' ? c.UnidadAF ? `${c.UnidadAF} - ALMACENES` : c.UnidadAlm : c[unidadKey] ?? '';
  return { entidad: c.Entidad ?? '', secretaria: c.Secretaria ?? '', unidad, gestion: c.Gestion ?? '', municipio: c.Municipio ?? '', departamento: c.Departamento ?? '', logo: c.Logo, cfg: c };
}

export interface Col {
  header: string;
  w?: number; // peso relativo del ancho
  align?: 'left' | 'right' | 'center';
  num?: 'money' | 'qty' | 'int';
}

const C = { primary: '#1F3A5F', light: '#E8EEF5', grey: '#F4F5F7', line: '#B8C0CC', text: '#1A1A1A', muted: '#5A6270', red: '#B3261E' };

export interface PdfOptions {
  titulo: string;
  subtitulo?: string;
  nro?: string;
  landscape?: boolean;
  header: Header;
  fechaDoc?: string;
}

export class PdfDoc {
  doc: PDFKit.PDFDocument;
  private opts: PdfOptions;
  private margin = 36;
  private numberFooter = true;

  constructor(opts: PdfOptions) {
    this.opts = opts;
    this.doc = new PDFDocument({ size: 'LETTER', layout: opts.landscape ? 'landscape' : 'portrait', margin: this.margin, bufferPages: true, info: { Title: opts.titulo, Author: opts.header.entidad, Creator: 'SIGAA' } });
    this.cabecera();
  }

  get width() {
    return this.doc.page.width - this.margin * 2;
  }
  private get bottom() {
    return this.doc.page.height - this.margin - 18;
  }

  private cabecera(conTitulo = true) {
    const d = this.doc;
    const h = this.opts.header;
    const x = this.margin;
    let tx = x;
    if (h.logo && fs.existsSync(h.logo)) {
      try {
        d.image(h.logo, x, this.margin, { fit: [46, 46] });
        tx = x + 54;
      } catch {
        /* logo inválido: se ignora */
      }
    }
    d.fillColor(C.primary).font('Helvetica-Bold').fontSize(10.5).text(h.entidad.toUpperCase(), tx, this.margin, { width: this.width - (tx - x) - 120 });
    d.fillColor(C.muted).font('Helvetica').fontSize(8).text(h.secretaria, tx, d.y, { width: this.width - (tx - x) - 120 });
    d.text(h.unidad, tx, d.y, { width: this.width - (tx - x) - 120 });
    d.fillColor(C.muted).fontSize(8).text(`Gestión ${h.gestion}`, x + this.width - 110, this.margin, { width: 110, align: 'right' });
    d.text(fmtDate(this.opts.fechaDoc ?? today()), x + this.width - 110, d.y, { width: 110, align: 'right' });
    const yy = Math.max(d.y, this.margin + 40) + 4;
    d.moveTo(x, yy).lineTo(x + this.width, yy).lineWidth(1.2).strokeColor(C.primary).stroke();
    d.y = yy + 8;
    d.x = x;
    if (conTitulo && this.opts.titulo) {
      d.fillColor(C.primary).font('Helvetica-Bold').fontSize(13).text(this.opts.titulo.toUpperCase(), x, d.y, { width: this.width, align: 'center' });
      if (this.opts.nro) d.fontSize(10).fillColor(C.text).text(`Nº ${this.opts.nro}`, x, d.y + 1, { width: this.width, align: 'center' });
      if (this.opts.subtitulo) d.font('Helvetica').fontSize(8.5).fillColor(C.muted).text(this.opts.subtitulo, x, d.y + 1, { width: this.width, align: 'center' });
      d.y += 8;
    }
    d.fillColor(C.text);
  }

  /** Inicia una página nueva con encabezado completo y un título propio (documentos de varias hojas). */
  pagina(titulo: string, nro?: string) {
    this.opts = { ...this.opts, titulo, nro };
    this.doc.addPage();
    this.cabecera(true);
    return this;
  }

  private ensure(h: number) {
    if (this.doc.y + h > this.bottom) {
      this.doc.addPage();
      this.cabeceraSimple();
    }
  }
  /** Encabezado reducido para páginas siguientes. */
  private cabeceraSimple() {
    const d = this.doc;
    d.fillColor(C.muted).font('Helvetica').fontSize(7.5).text(`${this.opts.header.entidad} — ${this.opts.titulo}${this.opts.nro ? ' Nº ' + this.opts.nro : ''}`, this.margin, this.margin - 8, { width: this.width });
    d.moveTo(this.margin, this.margin + 4).lineTo(this.margin + this.width, this.margin + 4).lineWidth(0.5).strokeColor(C.line).stroke();
    d.y = this.margin + 10;
    d.x = this.margin;
    d.fillColor(C.text);
  }

  espacio(n = 6) {
    this.doc.y += n;
    return this;
  }

  seccion(titulo: string) {
    this.ensure(26);
    const d = this.doc;
    const y = d.y + 2;
    d.rect(this.margin, y, this.width, 15).fill(C.primary);
    d.fillColor('#FFFFFF').font('Helvetica-Bold').fontSize(8.5).text(titulo.toUpperCase(), this.margin + 6, y + 3.5, { width: this.width - 12 });
    d.y = y + 19;
    d.x = this.margin;
    d.fillColor(C.text);
    return this;
  }

  parrafo(texto: string, o: { bold?: boolean; align?: 'left' | 'center' | 'right' | 'justify'; size?: number; color?: string } = {}) {
    const d = this.doc;
    d.font(o.bold ? 'Helvetica-Bold' : 'Helvetica').fontSize(o.size ?? 9).fillColor(o.color ?? C.text);
    const h = d.heightOfString(texto, { width: this.width, align: o.align ?? 'justify' });
    this.ensure(h + 4);
    d.text(texto, this.margin, d.y, { width: this.width, align: o.align ?? 'justify' });
    d.y += 4;
    d.fillColor(C.text);
    return this;
  }

  /** Pares etiqueta/valor; `cols` pares por fila (1 o 2). */
  kv(pares: ([string, unknown] | null)[], cols = 2) {
    const d = this.doc;
    const items = pares.filter(Boolean) as [string, unknown][];
    const cw = this.width / cols;
    for (let i = 0; i < items.length; i += cols) {
      const fila = items.slice(i, i + cols);
      d.font('Helvetica').fontSize(8.5);
      const alturas = fila.map(([k, v]) => {
        const lw = Math.min(cw * 0.42, 130);
        return Math.max(d.font('Helvetica-Bold').heightOfString(k, { width: lw - 4 }), d.font('Helvetica').heightOfString(String(v ?? ''), { width: cw - lw - 8 })) + 4;
      });
      const h = Math.max(...alturas);
      this.ensure(h);
      const y = d.y;
      fila.forEach(([k, v], j) => {
        const x = this.margin + j * cw;
        const lw = Math.min(cw * 0.42, 130);
        d.rect(x, y, cw - 4, h).fill(C.grey);
        d.fillColor(C.muted).font('Helvetica-Bold').fontSize(8).text(k, x + 4, y + 2.5, { width: lw - 4 });
        d.fillColor(C.text).font('Helvetica').fontSize(8.5).text(String(v ?? ''), x + lw, y + 2.5, { width: cw - lw - 8 });
      });
      d.y = y + h + 2;
    }
    d.x = this.margin;
    d.fillColor(C.text);
    return this;
  }

  tabla(cols: Col[], filas: unknown[][], o: { totales?: unknown[]; fontSize?: number; zebra?: boolean } = {}) {
    const d = this.doc;
    const fs0 = o.fontSize ?? 8;
    const pesos = cols.map((c) => c.w ?? 1);
    const tot = pesos.reduce((a, b) => a + b, 0);
    const ws = pesos.map((p) => (p / tot) * this.width);
    const fmt = (c: Col, v: unknown): string => {
      if (v === null || v === undefined || v === '') return '';
      if (typeof v === 'string' && isNaN(Number(v.replace(',', '.')))) return v; // rótulos como TOTAL en columnas numéricas
      if (c.num === 'money') return fmt2(v);
      if (c.num === 'qty') return fmtCant(v);
      if (c.num === 'int') return String(Math.round(Number(v)));
      return String(v);
    };
    const alignOf = (c: Col): 'left' | 'right' | 'center' => c.align ?? (c.num ? 'right' : 'left');
    const dibujaFila = (vals: string[], opts: { head?: boolean; bold?: boolean; fill?: string }) => {
      d.font(opts.head || opts.bold ? 'Helvetica-Bold' : 'Helvetica').fontSize(fs0);
      const h = Math.max(...vals.map((v, i) => d.heightOfString(v || ' ', { width: ws[i] - 6 }))) + 5;
      if (d.y + h > this.bottom) {
        d.addPage();
        this.cabeceraSimple();
        if (!opts.head) dibujaFila(cols.map((c) => c.header), { head: true, fill: C.primary });
      }
      const y = d.y;
      let x = this.margin;
      vals.forEach((v, i) => {
        if (opts.fill) d.rect(x, y, ws[i], h).fill(opts.fill);
        d.rect(x, y, ws[i], h).lineWidth(0.4).strokeColor(C.line).stroke();
        d.fillColor(opts.head ? '#FFFFFF' : C.text).font(opts.head || opts.bold ? 'Helvetica-Bold' : 'Helvetica').fontSize(fs0).text(v, x + 3, y + 2.5, { width: ws[i] - 6, align: opts.head ? 'center' : alignOf(cols[i]) });
        x += ws[i];
      });
      d.y = y + h;
      d.x = this.margin;
    };
    this.ensure(30);
    dibujaFila(cols.map((c) => c.header), { head: true, fill: C.primary });
    filas.forEach((f, i) => dibujaFila(cols.map((c, j) => fmt(c, f[j])), { fill: o.zebra !== false && i % 2 ? C.grey : undefined }));
    if (o.totales) dibujaFila(cols.map((c, j) => fmt(c, o.totales![j])), { bold: true, fill: C.light });
    d.y += 4;
    d.fillColor(C.text);
    return this;
  }

  /** Bloque de firmas: cada una con línea, nombre, cargo y rol. */
  firmas(f: { nombre?: string; cargo?: string; rol: string }[]) {
    const d = this.doc;
    this.ensure(70);
    d.y += 28;
    const n = f.length;
    const per = n > 4 ? 4 : n;
    const cw = this.width / per;
    for (let i = 0; i < n; i += per) {
      const fila = f.slice(i, i + per);
      const y = d.y;
      let hmax = 0;
      fila.forEach((s, j) => {
        const x = this.margin + j * cw + 12;
        const w = cw - 24;
        d.moveTo(x, y).lineTo(x + w, y).lineWidth(0.7).strokeColor(C.text).stroke();
        d.font('Helvetica-Bold').fontSize(7.5).fillColor(C.text).text(txt(s.nombre), x, y + 3, { width: w, align: 'center' });
        d.font('Helvetica').fontSize(7).fillColor(C.muted).text(txt(s.cargo), x, d.y, { width: w, align: 'center' });
        d.font('Helvetica-Bold').fontSize(7).fillColor(C.primary).text(s.rol, x, d.y, { width: w, align: 'center' });
        hmax = Math.max(hmax, d.y - y);
      });
      d.y = y + hmax + 24;
    }
    d.x = this.margin;
    d.fillColor(C.text);
    return this;
  }

  lugarFecha(fecha: string = today()) {
    return this.parrafo(`${this.opts.header.municipio}, ${fechaLiteral(fecha)}`, { align: 'left', size: 8.5, color: C.muted });
  }

  /** Marca de agua / aviso de color. */
  aviso(texto: string, color = C.red) {
    return this.parrafo(texto, { bold: true, color, align: 'center', size: 9 });
  }

  async buffer(): Promise<Buffer> {
    const d = this.doc;
    const range = d.bufferedPageRange();
    for (let i = 0; i < range.count; i++) {
      d.switchToPage(i);
      const y = d.page.height - this.margin + 4;
      d.fillColor(C.muted).font('Helvetica').fontSize(7);
      d.text(`SIGAA · ${this.opts.header.entidad}`, this.margin, y, { width: this.width / 2, align: 'left', lineBreak: false });
      d.text(`Página ${i + 1} de ${range.count}`, this.margin + this.width / 2, y, { width: this.width / 2, align: 'right', lineBreak: false });
    }
    const chunks: Buffer[] = [];
    return new Promise((resolve, reject) => {
      d.on('data', (c: Buffer) => chunks.push(c));
      d.on('end', () => resolve(Buffer.concat(chunks)));
      d.on('error', reject);
      d.end();
    });
  }
}
