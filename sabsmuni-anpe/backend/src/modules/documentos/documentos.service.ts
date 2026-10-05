import { BadRequestException, ConflictException, Injectable, InternalServerErrorException, NotFoundException } from '@nestjs/common';
import { TipoDocumento } from '@prisma/client';
import { AuditService } from '../../common/audit.service';
import { Ctx } from '../../common/auth';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoCompleto, ProcesoRepo, isoFecha, num } from '../../common/proceso.repo';
import { StorageService } from '../../common/storage.service';
import { generarJustificacionInsuficiencia, validarItemChb } from '../../domain/chb';
import { ResultadoEvaluacion } from '../../domain/evaluacion';
import { jsonCanonico, sha256 } from '../../domain/integridad';
import { construirGlosa } from '../../domain/sigep';
import { plazoMinimoDiasHabiles } from '../../domain/cronograma';
import { PdfService } from '../../pdf/pdf.service';
import { PLANTILLAS, TipoGenerable } from '../../pdf/templates';
import { DatosDoc } from '../../pdf/tipos';

export const TIPOS_GENERABLES = Object.keys(PLANTILLAS) as TipoGenerable[];
const PUBLIC_URL = () => (process.env.PUBLIC_URL ?? 'http://localhost:3000').replace(/\/$/, '');
export const urlVerificacion = (hash: string) => `${PUBLIC_URL()}/verificar/${hash}`;

@Injectable()
export class DocumentosService {
  constructor(
    private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService,
    private readonly storage: StorageService, private readonly pdf: PdfService,
  ) {}

  /** Proyecta el proceso de base de datos al modelo plano que consumen las plantillas. */
  async construirDatos(p: ProcesoCompleto): Promise<DatosDoc> {
    const cfg = await this.repo.config();
    const catalogo = await this.prisma.catalogoChb.findMany();
    const entradas = catalogo.map((c) => ({ id: c.id, codigoUnspsc: c.codigoUnspsc, descripcion: c.descripcion, productor: c.productor, vigente: c.vigente }));
    const items = p.items.map((i) => ({ numero: i.numero, codigoUnspsc: i.codigoUnspsc, partida: i.partidaGasto, descripcion: i.descripcionTecnica, unidad: i.unidadMedida, cantidad: num(i.cantidad), precioUnitario: num(i.precioUnitario), precioTotal: num(i.precioTotal), requiereExcepcionChb: i.requiereExcepcionChb, resultadoChb: i.resultadoChb }));
    const justItems = p.items.filter((i) => i.requiereExcepcionChb).map((i) => ({
      codigoUnspsc: i.codigoUnspsc, descripcion: i.descripcionTecnica, incompatibilidadTecnica: i.incompatibilidadTecnica,
      validacion: validarItemChb(p.tipoObjeto, { codigoUnspsc: i.codigoUnspsc, descripcion: i.descripcionTecnica, incompatibilidadTecnica: i.incompatibilidadTecnica }, entradas),
    }));
    const c = p.cronograma;
    let plazoMin: number | null = null;
    try { plazoMin = plazoMinimoDiasHabiles(num(p.precioReferencialTotal)); } catch { /* fuera de rango ANPE */ }
    return {
      config: cfg,
      proceso: {
        id: p.id, codigo: p.codigo, cuce: p.cuceProvisorio, objeto: p.objetoContratacion, tipoObjeto: p.tipoObjeto, metodo: p.metodoSeleccion, precioReferencial: num(p.precioReferencialTotal),
        plazoEjecucionDias: p.plazoEjecucionDias, estado: p.estadoFlujo, requerimiento: (p.requerimiento ?? {}) as Record<string, string>, solicitante: p.solicitante, rpa: p.rpa,
        resolucionObs: p.resolucionObs, resolucionFecha: isoFecha(p.resolucionFecha), propuestaAdjudicadaId: p.propuestaAdjudicadaId,
      },
      items,
      cronograma: c ? { fechaPublicacion: isoFecha(c.fechaPublicacion)!, fechaApertura: isoFecha(c.fechaApertura)!, fechaAdjudicacion: isoFecha(c.fechaAdjudicacion)!, fechaPresentacionDoc: isoFecha(c.fechaPresentacionDoc)!, fechaContrato: isoFecha(c.fechaContrato)! } : null,
      plazoMinimoDias: plazoMin,
      certificaciones: p.certificaciones.map((x) => ({ da: x.da, ue: x.ue, programa: x.programa, proyecto: x.proyecto, actividadObra: x.actividadObra, fuente: x.fuente, organismo: x.organismo, partida: x.partida, importe: num(x.importe), c31: x.c31PreventivoNumero })),
      glosa: construirGlosa(p.objetoContratacion, p.codigo, cfg.nombreGam),
      propuestas: p.propuestas.map((x) => ({ id: x.id, orden: x.orden, nit: x.nitProveedor, razonSocial: x.razonSocial, categoria: x.categoria, monto: num(x.montoOfertado), subasta: x.montoSubasta == null ? null : num(x.montoSubasta), plazoDias: x.plazoDias, v1: (x.v1 ?? {}) as Record<string, boolean>, v1Califica: x.califica_v1 })),
      evaluacion: (p.evaluacion as unknown as ResultadoEvaluacion | null) ?? null,
      contrato: p.contrato ? {
        tipo: p.contrato.tipo, numero: p.contrato.numero, propuestaId: p.contrato.propuestaId, monto: num(p.contrato.monto), plazoDias: p.contrato.plazoDias, fechaFirma: isoFecha(p.contrato.fechaFirma)!,
        garantiaPorcentaje: num(p.contrato.garantiaPorcentaje), garantiaMonto: num(p.contrato.garantiaMonto), garantiaInstrumento: p.contrato.garantiaInstrumento, polizaNumero: p.contrato.polizaNumero,
        polizaEntidad: p.contrato.polizaEntidad, polizaVigenciaHasta: isoFecha(p.contrato.polizaVigenciaHasta), fechaRecepcion: isoFecha(p.contrato.fechaRecepcion), observacionRecepcion: p.contrato.observacionRecepcion,
      } : null,
      justificacionChb: justItems.length ? generarJustificacionInsuficiencia(p.objetoContratacion, justItems) : null,
    };
  }

  private requisitosPrevios(tipo: TipoGenerable, d: DatosDoc) {
    const falla = (m: string) => { throw new ConflictException(m); };
    if (!d.items.length && tipo !== 'ACTA_ADJUDICACION') falla('El proceso no tiene ítems.');
    if (['INFORME_V1', 'CUADRO_COMPARATIVO', 'INFORME_EVALUACION'].includes(tipo) && !d.evaluacion) falla('Ejecute primero la evaluación de propuestas.');
    if (tipo === 'JUSTIFICACION_CHB' && !d.justificacionChb) falla('Ningún ítem requiere excepción del catálogo CHB: no corresponde el formulario.');
    if (tipo === 'PREVENTIVO_C31' && !d.certificaciones.length) falla('Registre la certificación presupuestaria.');
    if (tipo === 'DBC' && !d.cronograma) falla('Defina el cronograma antes de generar el DBC.');
    if (['CONTRATO', 'ORDEN_COMPRA_SERVICIO', 'ACTA_RECEPCION'].includes(tipo) && !d.contrato) falla('Registre primero el contrato/orden.');
  }

  async generar(procesoId: string, tipoSolicitado: TipoGenerable, ctx: Ctx | undefined) {
    if (!TIPOS_GENERABLES.includes(tipoSolicitado)) throw new BadRequestException(`Tipo no generable: ${tipoSolicitado}`);
    const p = await this.repo.obtener(procesoId);
    const d = await this.construirDatos(p);
    let tipo = tipoSolicitado;
    if (d.contrato && (tipo === 'CONTRATO' || tipo === 'ORDEN_COMPRA_SERVICIO')) tipo = d.contrato.tipo === 'CONTRATO' ? 'CONTRATO' : 'ORDEN_COMPRA_SERVICIO';
    this.requisitosPrevios(tipo, d);
    const version = ((await this.prisma.documentoExpediente.aggregate({ where: { procesoId, tipoDocumento: tipo as TipoDocumento }, _max: { version: true } }))._max.version ?? 0) + 1;
    const hashContenido = sha256(jsonCanonico({ procesoId, tipo, version, datos: d }));
    const spec = PLANTILLAS[tipo](d);
    const buffer = await this.pdf.render(spec, { entidad: d.config.nombreGam, codigoProceso: d.proceso.codigo, hashContenido, urlVerificacion: urlVerificacion(hashContenido), version });
    return this.persistir(procesoId, p.codigo, tipo as TipoDocumento, version, buffer, hashContenido, true, ctx);
  }

  async subir(procesoId: string, tipo: TipoDocumento, archivo: Express.Multer.File | undefined, ctx: Ctx) {
    if (!archivo) throw new BadRequestException('Adjunte un archivo PDF.');
    if (archivo.buffer.subarray(0, 5).toString('latin1') !== '%PDF-') throw new BadRequestException('Solo se aceptan archivos PDF válidos.');
    if (tipo === 'EXPEDIENTE_UNICO') throw new BadRequestException('El expediente único solo se genera automáticamente.');
    const p = await this.repo.obtener(procesoId);
    const version = ((await this.prisma.documentoExpediente.aggregate({ where: { procesoId, tipoDocumento: tipo }, _max: { version: true } }))._max.version ?? 0) + 1;
    return this.persistir(procesoId, p.codigo, tipo, version, archivo.buffer, null, false, ctx);
  }

  async persistir(procesoId: string, codigoProceso: string, tipo: TipoDocumento, version: number, buffer: Buffer, hashContenido: string | null, generado: boolean, ctx?: Ctx) {
    const hashSha256 = sha256(buffer);
    const ruta = `${codigoProceso}/${tipo}_v${version}_${hashSha256.slice(0, 12)}.pdf`;
    await this.storage.guardar(ruta, buffer);
    const { PDFDocument } = await import('pdf-lib');
    const paginas = (await PDFDocument.load(buffer, { ignoreEncryption: true })).getPageCount();
    const doc = await this.prisma.documentoExpediente.create({ data: { procesoId, tipoDocumento: tipo, rutaArchivo: ruta, hashSha256, hashContenido, version, generado, paginas, creadoPor: ctx?.userId } });
    await this.audit.registrar({ ctx, accion: generado ? 'DOCUMENTO_GENERADO' : 'DOCUMENTO_SUBIDO', entidad: 'documento', entidadId: doc.id, posterior: { procesoId, tipo, version, hashSha256, paginas } });
    return doc;
  }

  listar(procesoId: string) {
    return this.prisma.documentoExpediente.findMany({ where: { procesoId }, orderBy: [{ tipoDocumento: 'asc' }, { version: 'desc' }], select: { id: true, tipoDocumento: true, version: true, hashSha256: true, hashContenido: true, generado: true, paginas: true, creadoEn: true } });
  }

  /** Lee el archivo y comprueba su integridad contra el hash registrado. */
  async leerVerificado(id: string) {
    const doc = await this.prisma.documentoExpediente.findUnique({ where: { id } });
    if (!doc) throw new NotFoundException('Documento no encontrado.');
    const buffer = await this.storage.leer(doc.rutaArchivo);
    if (sha256(buffer) !== doc.hashSha256) throw new InternalServerErrorException('ALERTA: el archivo almacenado no coincide con su hash SHA-256 (posible alteración).');
    return { doc, buffer };
  }

  /** Verificación pública (QR): acepta hash de archivo o de contenido. */
  async verificar(hash: string) {
    if (!/^[a-f0-9]{64}$/i.test(hash)) throw new BadRequestException('Hash inválido.');
    const h = hash.toLowerCase();
    const doc = await this.prisma.documentoExpediente.findFirst({ where: { OR: [{ hashSha256: h }, { hashContenido: h }] }, include: { proceso: { select: { codigo: true, objetoContratacion: true } } } });
    if (!doc) return { valido: false, mensaje: 'No existe ningún documento registrado con este hash.' };
    let integro = false;
    try { integro = sha256(await this.storage.leer(doc.rutaArchivo)) === doc.hashSha256; } catch { integro = false; }
    return { valido: integro, tipoDocumento: doc.tipoDocumento, version: doc.version, proceso: doc.proceso.codigo, objeto: doc.proceso.objetoContratacion, generadoEn: doc.creadoEn, hashSha256: doc.hashSha256, hashContenido: doc.hashContenido, paginas: doc.paginas, mensaje: integro ? 'Documento auténtico: el archivo coincide con el hash registrado.' : 'ALERTA: el archivo almacenado fue alterado o no está disponible.' };
  }
}
