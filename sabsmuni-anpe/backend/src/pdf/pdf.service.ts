import { Injectable } from '@nestjs/common';
import PDFDocument from 'pdfkit';
import * as QRCode from 'qrcode';
import { Bloque, DocSpec, MetaPdf } from './tipos';

const COLOR = { tinta: '#1f2937', gris: '#6b7280', linea: '#d1d5db', cabecera: '#1e3a5f', zebra: '#f3f4f6' };
const M = 50;

@Injectable()
export class PdfService {
  /** Renderiza un documento oficial con encabezado institucional, marca de agua, folio, hash y QR de verificación. */
  async render(spec: DocSpec, meta: MetaPdf): Promise<Buffer> {
    const qr = await QRCode.toBuffer(meta.urlVerificacion, { margin: 0, width: 120, errorCorrectionLevel: 'M' });
    const doc = new PDFDocument({
      size: 'LETTER', layout: spec.horizontal ? 'landscape' : 'portrait', margins: { top: 90, bottom: 70, left: M, right: M }, bufferPages: true,
      info: { Title: spec.titulo, Author: meta.entidad, Subject: `${meta.codigoProceso} v${meta.version}`, Keywords: `sha256:${meta.hashContenido}` },
    });
    const chunks: Buffer[] = [];
    doc.on('data', (c: Buffer) => chunks.push(c));
    const fin = new Promise<Buffer>((ok) => doc.on('end', () => ok(Buffer.concat(chunks))));

    const ancho = () => doc.page.width - 2 * M;
    const asegurar = (alto: number) => { if (doc.y + alto > doc.page.height - doc.page.margins.bottom) doc.addPage(); };

    // Título
    doc.font('Helvetica-Bold').fontSize(14).fillColor(COLOR.cabecera).text(spec.titulo.toUpperCase(), { align: 'center' });
    if (spec.subtitulo) doc.moveDown(0.2).font('Helvetica').fontSize(10).fillColor(COLOR.gris).text(spec.subtitulo, { align: 'center' });
    if (spec.formulario) doc.moveDown(0.2).font('Helvetica-Oblique').fontSize(9).fillColor(COLOR.gris).text(`Formulario ${spec.formulario}`, { align: 'center' });
    doc.moveDown(0.8).fillColor(COLOR.tinta);

    for (const b of spec.bloques) this.bloque(doc, b, ancho, asegurar);

    if (spec.firmas?.length) {
      asegurar(110);
      doc.moveDown(3);
      const n = spec.firmas.length;
      const w = ancho() / n;
      const y = doc.y;
      spec.firmas.forEach((f, i) => {
        const x = M + i * w;
        doc.moveTo(x + 15, y).lineTo(x + w - 15, y).strokeColor(COLOR.tinta).lineWidth(0.7).stroke();
        doc.font('Helvetica-Bold').fontSize(9).fillColor(COLOR.tinta).text(f.nombre ?? '________________', x, y + 4, { width: w, align: 'center' });
        doc.font('Helvetica').fontSize(8).fillColor(COLOR.gris).text(f.cargo, x, doc.y, { width: w, align: 'center' });
      });
    }

    // Encabezado, pie, marca de agua y QR en todas las páginas
    const rango = doc.bufferedPageRange();
    for (let i = rango.start; i < rango.start + rango.count; i++) {
      doc.switchToPage(i);
      const w = doc.page.width, h = doc.page.height;
      const mb = doc.page.margins.bottom; doc.page.margins.bottom = 0; // evita saltos de página al escribir en el pie
      doc.save().rotate(-35, { origin: [w / 2, h / 2] }).fillOpacity(0.06).font('Helvetica-Bold').fontSize(54).fillColor(COLOR.cabecera)
        .text(meta.marcaAgua ?? 'DOCUMENTO CONTROLADO', 0, h / 2 - 30, { width: w, align: 'center', lineBreak: false }).restore();
      doc.fillOpacity(1);
      doc.font('Helvetica-Bold').fontSize(9).fillColor(COLOR.cabecera).text(meta.entidad.toUpperCase(), M, 30, { lineBreak: false });
      doc.font('Helvetica').fontSize(8).fillColor(COLOR.gris).text(`Proceso ${meta.codigoProceso}`, M, 42, { lineBreak: false });
      doc.moveTo(M, 62).lineTo(w - M, 62).strokeColor(COLOR.cabecera).lineWidth(1.2).stroke();
      doc.moveTo(M, h - 62).lineTo(w - M, h - 62).strokeColor(COLOR.linea).lineWidth(0.6).stroke();
      doc.font('Helvetica').fontSize(6.5).fillColor(COLOR.gris);
      doc.text(`SHA-256 contenido: ${meta.hashContenido}`, M, h - 56, { width: w - 2 * M - 60, lineBreak: false });
      doc.text(`Verificar: ${meta.urlVerificacion}`, M, h - 46, { width: w - 2 * M - 60, lineBreak: false });
      doc.text(`Versión ${meta.version} · Página ${i - rango.start + 1} de ${rango.count}`, M, h - 36, { width: w - 2 * M - 60, lineBreak: false });
      doc.image(qr, w - M - 44, h - 58, { width: 44, height: 44 });
      doc.page.margins.bottom = mb;
    }
    doc.end();
    return fin;
  }

  private bloque(doc: PDFKit.PDFDocument, b: Bloque, ancho: () => number, asegurar: (n: number) => void) {
    doc.fillColor(COLOR.tinta);
    switch (b.t) {
      case 'h':
        asegurar(40);
        doc.moveDown(0.6).font('Helvetica-Bold').fontSize(11).fillColor(COLOR.cabecera).text(b.texto);
        doc.moveTo(M, doc.y + 1).lineTo(M + ancho(), doc.y + 1).strokeColor(COLOR.linea).lineWidth(0.5).stroke();
        doc.moveDown(0.4).fillColor(COLOR.tinta);
        break;
      case 'p':
        doc.font('Helvetica').fontSize(9.5).text(b.texto, { align: 'justify' }).moveDown(0.5);
        break;
      case 'nota':
        doc.font('Helvetica-Oblique').fontSize(8).fillColor(COLOR.gris).text(b.texto, { align: 'justify' }).moveDown(0.5).fillColor(COLOR.tinta);
        break;
      case 'clausula':
        asegurar(50);
        doc.font('Helvetica-Bold').fontSize(9.5).text(b.titulo.toUpperCase(), { continued: false }).moveDown(0.15);
        doc.font('Helvetica').fontSize(9.5).text(b.texto, { align: 'justify' }).moveDown(0.6);
        break;
      case 'lista':
        doc.font('Helvetica').fontSize(9.5);
        b.items.forEach((it) => { asegurar(16); doc.text(`•  ${it}`, { indent: 10, align: 'left' }); });
        doc.moveDown(0.5);
        break;
      case 'kv': {
        const w1 = 170;
        for (const [k, v] of b.pares) {
          doc.font('Helvetica').fontSize(9.5);
          doc.font('Helvetica-Bold').fontSize(9);
          const altoK = doc.heightOfString(k, { width: w1 - 8 });
          doc.font('Helvetica').fontSize(9.5);
          const alto = Math.max(doc.heightOfString(v || '—', { width: ancho() - w1 }), altoK, 12) + 4;
          asegurar(alto);
          const y = doc.y;
          doc.font('Helvetica-Bold').fontSize(9).fillColor(COLOR.gris).text(k, M, y, { width: w1 - 8 });
          doc.font('Helvetica').fontSize(9.5).fillColor(COLOR.tinta).text(v || '—', M + w1, y, { width: ancho() - w1 });
          doc.y = y + alto;
        }
        doc.x = M; doc.moveDown(0.4);
        break;
      }
      case 'tabla':
        this.tabla(doc, b, ancho, asegurar);
        break;
      case 'salto':
        doc.addPage();
        break;
    }
    doc.x = M;
  }

  private tabla(doc: PDFKit.PDFDocument, b: Extract<Bloque, { t: 'tabla' }>, ancho: () => number, asegurar: (n: number) => void) {
    const total = ancho();
    const pesos = b.anchos ?? b.columnas.map(() => 1);
    const suma = pesos.reduce((a, c) => a + c, 0);
    const w = pesos.map((p) => (p / suma) * total);
    const derecha = new Set(b.derecha ?? []);
    const fs = b.columnas.length > 8 ? 7 : 8.5;
    const fila = (celdas: (string | number)[], cab: boolean, zebra: boolean) => {
      doc.font(cab ? 'Helvetica-Bold' : 'Helvetica').fontSize(fs);
      const textos = celdas.map((c) => (typeof c === 'number' ? c.toLocaleString('es-BO', { minimumFractionDigits: Number.isInteger(c) ? 0 : 2, maximumFractionDigits: 2 }) : String(c)));
      const alto = Math.max(...textos.map((t, i) => doc.heightOfString(t, { width: w[i] - 6 }))) + 6;
      if (doc.y + alto > doc.page.height - doc.page.margins.bottom) { doc.addPage(); if (!cab) fila(b.columnas, true, false); }
      const y = doc.y;
      if (cab) doc.rect(M, y, total, alto).fill(COLOR.cabecera);
      else if (zebra) doc.rect(M, y, total, alto).fill(COLOR.zebra);
      let x = M;
      textos.forEach((t, i) => {
        doc.fillColor(cab ? '#ffffff' : COLOR.tinta).font(cab ? 'Helvetica-Bold' : 'Helvetica').fontSize(fs).text(t, x + 3, y + 3, { width: w[i] - 6, align: derecha.has(i) && !cab ? 'right' : 'left', lineBreak: true });
        x += w[i];
      });
      doc.moveTo(M, y + alto).lineTo(M + total, y + alto).strokeColor(COLOR.linea).lineWidth(0.4).stroke();
      doc.y = y + alto; doc.x = M;
    };
    asegurar(40);
    fila(b.columnas, true, false);
    b.filas.forEach((f, i) => fila(f, false, i % 2 === 1));
    doc.moveDown(0.6).fillColor(COLOR.tinta);
  }
}
