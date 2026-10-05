import { BadRequestException, ConflictException, Injectable } from '@nestjs/common';
import { EstadoFlujo as EstadoPrisma, Prisma } from '@prisma/client';
import { Ctx } from '../../common/auth';
import { AuditService } from '../../common/audit.service';
import { CalendarioProvider } from '../../common/calendario.provider';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoCompleto, ProcesoRepo, isoFecha, num } from '../../common/proceso.repo';
import { validarCronograma, validarRangoAnpe } from '../../domain/cronograma';
import { ResultadoEvaluacion } from '../../domain/evaluacion';
import { ContextoFlujo, EstadoFlujo, evaluarTransicion, transicionesDesde } from '../../domain/flujo';
import { TipoGenerable } from '../../pdf/templates';
import { DocumentosService } from '../documentos/documentos.service';
import { TransicionDto } from './dto';
import { PresupuestoService } from './presupuesto.service';
import { RequerimientoService } from './requerimiento.service';

/** Documentos oficiales que se emiten automáticamente al cruzar cada transición. */
const DOCUMENTOS_AL_TRANSITAR: Partial<Record<EstadoFlujo, TipoGenerable[]>> = {
  REQUERIMIENTO_VALIDADO: ['SOLICITUD_C1'],
  PRESUPUESTO_CERTIFICADO: ['PREVENTIVO_C31'],
  DBC_ELABORADO: ['DBC'],
  RECOMENDACION_EMITIDA: ['INFORME_V1', 'CUADRO_COMPARATIVO', 'INFORME_EVALUACION'],
  ADJUDICADO: ['ACTA_ADJUDICACION'],
  DESIERTO: ['ACTA_ADJUDICACION'],
};

@Injectable()
export class FlujoService {
  constructor(
    private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService, private readonly cal: CalendarioProvider,
    private readonly docs: DocumentosService, private readonly req: RequerimientoService, private readonly pres: PresupuestoService,
  ) {}

  async contexto(p: ProcesoCompleto, hacia?: EstadoFlujo): Promise<ContextoFlujo> {
    const tiposDoc = new Set((await this.prisma.documentoExpediente.findMany({ where: { procesoId: p.id }, select: { tipoDocumento: true }, distinct: ['tipoDocumento'] })).map((d) => d.tipoDocumento));
    const estadoReq = p.estadoFlujo === 'BORRADOR' ? await this.req.evaluar(p) : null;
    const cal = await this.cal.cargar();
    const c = p.cronograma;
    const evaluacion = p.evaluacion as unknown as ResultadoEvaluacion | null;
    const itemsValidados = p.items.length > 0 && p.items.every((i) => i.resultadoChb !== null);
    return {
      itemsCargados: p.items.length > 0,
      rangoAnpeValido: validarRangoAnpe(num(p.precioReferencialTotal)) === null,
      requerimientoValido: estadoReq ? estadoReq.valido : true,
      excepcionesChbJustificadas: p.estadoFlujo !== 'BORRADOR' || (itemsValidados && (!p.items.some((i) => i.requiereExcepcionChb) || tiposDoc.has('JUSTIFICACION_CHB'))),
      c31Valido: this.pres.validar(p).valido,
      cronogramaValido: !!c && validarCronograma({ fechaPublicacion: isoFecha(c.fechaPublicacion)!, fechaApertura: isoFecha(c.fechaApertura)!, fechaAdjudicacion: isoFecha(c.fechaAdjudicacion)!, fechaPresentacionDoc: isoFecha(c.fechaPresentacionDoc)!, fechaContrato: isoFecha(c.fechaContrato)! }, num(p.precioReferencialTotal), cal).length === 0,
      documentoDbcGenerado: tiposDoc.has('DBC') || hacia === 'DBC_ELABORADO', // se emite al transitar
      evaluacionRealizada: !!evaluacion,
      hayRecomendacion: !!evaluacion?.recomendadaId,
      contratoGenerado: !!p.contrato && (tiposDoc.has('CONTRATO') || tiposDoc.has('ORDEN_COMPRA_SERVICIO')),
      actaRecepcionGenerada: tiposDoc.has('ACTA_RECEPCION'),
    };
  }

  async disponibles(id: string, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    const estados = transicionesDesde(p.estadoFlujo as EstadoFlujo);
    return Promise.all(estados.map(async (hacia) => {
      const r = evaluarTransicion(p.estadoFlujo as EstadoFlujo, hacia, ctx.rol, await this.contexto(p, hacia));
      return { hacia, ...r };
    }));
  }

  async transicionar(id: string, dto: TransicionDto, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    const desde = p.estadoFlujo as EstadoFlujo;
    const hacia = dto.hacia as EstadoFlujo;
    const r = evaluarTransicion(desde, hacia, ctx.rol, await this.contexto(p, hacia));
    if (!r.permitido) throw new ConflictException({ message: 'Transición no permitida.', motivos: r.motivos });

    const evaluacion = p.evaluacion as unknown as ResultadoEvaluacion | null;
    const datos: Record<string, unknown> = {};
    if (hacia === 'DBC_APROBADO') datos.idRpa = ctx.userId;
    if (hacia === 'DESIERTO') {
      if (!dto.observacion?.trim()) throw new BadRequestException('Declarar desierto exige fundamentar la observación.');
      Object.assign(datos, { resolucionObs: dto.observacion, resolucionFecha: new Date(), propuestaAdjudicadaId: null, idRpa: ctx.userId });
    }
    if (hacia === 'ADJUDICADO') {
      const elegida = dto.propuestaId ?? evaluacion?.recomendadaId;
      const fila = evaluacion?.filas.find((f) => f.propuestaId === elegida);
      if (!fila || fila.estado !== 'CALIFICA') throw new BadRequestException('Solo puede adjudicarse a una propuesta que califica en la evaluación vigente.');
      if (elegida !== evaluacion?.recomendadaId && !dto.observacion?.trim()) throw new BadRequestException('Adjudicar a una propuesta distinta de la recomendada exige fundamentar la observación.');
      Object.assign(datos, { propuestaAdjudicadaId: elegida, resolucionObs: dto.observacion ?? null, resolucionFecha: new Date(), idRpa: ctx.userId });
    }
    if (hacia === 'CANCELADO') Object.assign(datos, { resolucionObs: dto.observacion ?? 'Proceso cancelado', resolucionFecha: new Date() });

    if (desde === 'DESIERTO' && hacia === 'PRESUPUESTO_CERTIFICADO') {
      // Nueva convocatoria: se descartan propuestas y resolución previas (quedan en la auditoría y el expediente).
      await this.prisma.propuestaRupe.deleteMany({ where: { procesoId: id } });
      Object.assign(datos, { evaluacion: Prisma.DbNull, resolucionObs: null, resolucionFecha: null, propuestaAdjudicadaId: null });
    }
    if (Object.keys(datos).length) await this.prisma.procesoAnpe.update({ where: { id }, data: datos });
    for (const tipo of DOCUMENTOS_AL_TRANSITAR[hacia] ?? []) await this.docs.generar(id, tipo, ctx);
    const despues = await this.prisma.procesoAnpe.update({ where: { id }, data: { estadoFlujo: hacia as EstadoPrisma } });
    await this.audit.registrar({ ctx, accion: 'TRANSICION_ESTADO', entidad: 'proceso', entidadId: id, previo: { estado: desde }, posterior: { estado: hacia, observacion: dto.observacion ?? null, propuestaId: datos.propuestaAdjudicadaId ?? null } });
    return despues;
  }
}
