import { ConflictException, Injectable } from '@nestjs/common';
import { TipoDocumento } from '@prisma/client';
import { PDFDocument, PDFHexString, PDFName, PDFRef, StandardFonts, rgb } from 'pdf-lib';
import { Ctx } from '../../common/auth';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoRepo } from '../../common/proceso.repo';
import { StorageService } from '../../common/storage.service';
import { hashExpediente, sha256 } from '../../domain/integridad';
import { PdfService } from '../../pdf/pdf.service';
import { DocumentosService, urlVerificacion } from './documentos.service';

export const ORDEN_EXPEDIENTE: TipoDocumento[] = ['SOLICITUD_C1', 'JUSTIFICACION_CHB', 'PREVENTIVO_C31', 'DBC', 'INFORME_V1', 'CUADRO_COMPARATIVO', 'INFORME_EVALUACION', 'ACTA_ADJUDICACION', 'CONTRATO', 'ORDEN_COMPRA_SERVICIO', 'ACTA_RECEPCION', 'DEVENGADO_C31', 'OTRO'];
export const ETIQUETA_DOC: Record<string, string> = {
  SOLICITUD_C1: 'Solicitud de contratación y ET (C-1)', JUSTIFICACION_CHB: 'Justificación de insuficiencia técnica (CHB)', PREVENTIVO_C31: 'Preventivo C-31', DBC: 'Documento Base de Contratación',
  INFORME_V1: 'Verificación de documentos (V-1)', CUADRO_COMPARATIVO: 'Cuadro comparativo de ofertas', INFORME_EVALUACION: 'Informe de evaluación y recomendación', ACTA_ADJUDICACION: 'Resolución de adjudicación / Acta',
  CONTRATO: 'Contrato administrativo', ORDEN_COMPRA_SERVICIO: 'Orden de compra / servicio', ACTA_RECEPCION: 'Acta de recepción', DEVENGADO_C31: 'Devengado C-31', OTRO: 'Documento adjunto',
};

@Injectable()
export class ExpedienteService {
  constructor(private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly storage: StorageService, private readonly pdf: PdfService, private readonly docs: DocumentosService) {}

  /**
   * Compila el Expediente Único: portada-índice foliada + todos los documentos vigentes,
   * con folio "Fs. n/N" en cada página, marcadores navegables y sello SHA-256 del conjunto.
   */
  async generar(procesoId: string, ctx: Ctx) {
    const p = await this.repo.obtener(procesoId);
    const cfg = await this.repo.config();
    const todos = await this.prisma.documentoExpediente.findMany({ where: { procesoId, tipoDocumento: { not: 'EXPEDIENTE_UNICO' } }, orderBy: [{ version: 'desc' }] });
    const elegidos: typeof todos = [];
    for (const tipo of ORDEN_EXPEDIENTE) {
      const delTipo = todos.filter((d) => d.tipoDocumento === tipo);
      if (tipo === 'OTRO') elegidos.push(...[...delTipo].sort((a, b) => a.version - b.version));
      else if (delTipo[0]) elegidos.push(delTipo[0]); // versión más reciente
    }
    if (!elegidos.length) throw new ConflictException('No hay documentos para compilar el expediente.');

    const cargados: { d: (typeof todos)[number]; pdf: PDFDocument }[] = [];
    for (const d of elegidos) {
      const { buffer } = await this.docs.leerVerificado(d.id); // aborta si algún archivo fue alterado
      cargados.push({ d, pdf: await PDFDocument.load(buffer, { ignoreEncryption: true }) });
    }
    const sellados = cargados.map((c, i) => ({ orden: i + 1, tipo: c.d.tipoDocumento, version: c.d.version, hashSha256: c.d.hashSha256 }));
    const hashConjunto = hashExpediente(sellados);
    const version = ((await this.prisma.documentoExpediente.aggregate({ where: { procesoId, tipoDocumento: 'EXPEDIENTE_UNICO' }, _max: { version: true } }))._max.version ?? 0) + 1;

    const renderIndice = async (paginasIndice: number) => {
      let folio = paginasIndice + 1;
      const filas = cargados.map((c, i) => {
        const n = c.pdf.getPageCount();
        const fila = [i + 1, ETIQUETA_DOC[c.d.tipoDocumento], `v${c.d.version}`, n === 1 ? `${folio}` : `${folio}–${folio + n - 1}`, n, c.d.hashSha256];
        folio += n;
        return fila;
      });
      const total = folio - 1;
      const buf = await this.pdf.render({
        titulo: 'Expediente Único de Contratación', subtitulo: `${p.codigo} · ${p.objetoContratacion}`, formulario: 'Índice foliado', horizontal: true,
        bloques: [
          { t: 'kv', pares: [['Entidad', cfg.nombreGam], ['CUCE', p.cuceProvisorio], ['Documentos', String(cargados.length)], ['Total de folios', String(total)], ['Sello SHA-256 del expediente', hashConjunto]] },
          { t: 'tabla', columnas: ['N°', 'Documento', 'Versión', 'Folios', 'Págs.', 'SHA-256 del archivo'], anchos: [0.4, 3, 0.8, 0.9, 0.6, 6], filas },
          { t: 'nota', texto: 'El sello del expediente se calcula como SHA-256 de la lista ordenada de (orden | tipo | versión | hash) de cada documento. Cualquier modificación de un documento invalida el sello. Verifique escaneando el QR de cualquier página del índice.' },
        ],
        firmas: [{ cargo: 'Responsable de Contrataciones' }, { cargo: cfg.rpaCargo, nombre: cfg.rpaNombre }],
      }, { entidad: cfg.nombreGam, codigoProceso: p.codigo, hashContenido: hashConjunto, urlVerificacion: urlVerificacion(hashConjunto), version, marcaAgua: 'EXPEDIENTE' });
      return { buf, total, filas };
    };

    let nIdx = 1;
    let r = await renderIndice(nIdx);
    for (let i = 0; i < 4; i++) {
      const real = (await PDFDocument.load(r.buf)).getPageCount();
      if (real === nIdx) break;
      nIdx = real;
      r = await renderIndice(nIdx);
    }

    const out = await PDFDocument.create();
    const fuente = await out.embedFont(StandardFonts.HelveticaBold);
    const indice = await PDFDocument.load(r.buf);
    const destinos: { titulo: string; ref: PDFRef }[] = [];
    (await out.copyPages(indice, indice.getPageIndices())).forEach((pg) => out.addPage(pg));
    destinos.push({ titulo: 'Índice del expediente', ref: out.getPage(0).ref });
    for (const c of cargados) {
      const pgs = await out.copyPages(c.pdf, c.pdf.getPageIndices());
      pgs.forEach((pg, k) => { out.addPage(pg); if (k === 0) destinos.push({ titulo: `${ETIQUETA_DOC[c.d.tipoDocumento]} (v${c.d.version})`, ref: pg.ref }); });
    }
    const total = out.getPageCount();
    out.getPages().forEach((pg, i) => {
      const { width, height } = pg.getSize();
      const t = `Fs. ${i + 1}/${total}`;
      const w = fuente.widthOfTextAtSize(t, 9);
      pg.drawRectangle({ x: width - w - 24, y: height - 24, width: w + 12, height: 15, color: rgb(1, 1, 1), borderColor: rgb(0.12, 0.23, 0.37), borderWidth: 0.8 });
      pg.drawText(t, { x: width - w - 18, y: height - 20, size: 9, font: fuente, color: rgb(0.12, 0.23, 0.37) });
    });

    // Marcadores (outline) navegables
    const ctxPdf = out.context;
    const outlineRef = ctxPdf.nextRef();
    const refs = destinos.map(() => ctxPdf.nextRef());
    destinos.forEach((dst, i) => {
      const dict = ctxPdf.obj({ Title: PDFHexString.fromText(dst.titulo), Parent: outlineRef, Dest: [dst.ref, PDFName.of('Fit')] });
      if (i > 0) dict.set(PDFName.of('Prev'), refs[i - 1]);
      if (i < refs.length - 1) dict.set(PDFName.of('Next'), refs[i + 1]);
      ctxPdf.assign(refs[i], dict);
    });
    ctxPdf.assign(outlineRef, ctxPdf.obj({ Type: 'Outlines', First: refs[0], Last: refs[refs.length - 1], Count: refs.length }));
    out.catalog.set(PDFName.of('Outlines'), outlineRef);
    out.catalog.set(PDFName.of('PageMode'), PDFName.of('UseOutlines'));
    out.setTitle(`Expediente ${p.codigo}`); out.setSubject(`Sello SHA-256: ${hashConjunto}`); out.setProducer('SABSMUNI-ANPE');

    const final = Buffer.from(await out.save());
    const doc = await this.docs.persistir(procesoId, p.codigo, 'EXPEDIENTE_UNICO', version, final, hashConjunto, true, ctx);
    return { ...doc, hashExpediente: hashConjunto, folios: total, documentos: cargados.length, hashArchivo: sha256(final) };
  }
}
