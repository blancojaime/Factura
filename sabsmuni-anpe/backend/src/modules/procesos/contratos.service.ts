import { BadRequestException, ConflictException, Injectable } from '@nestjs/common';
import { Ctx } from '../../common/auth';
import { AuditService } from '../../common/audit.service';
import { CalendarioProvider } from '../../common/calendario.provider';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoRepo, num } from '../../common/proceso.repo';
import { calcularGarantiaCumplimiento, tipoInstrumentoContractual } from '../../domain/garantia';
import { DocumentosService } from '../documentos/documentos.service';
import { ContratoDto, RecepcionDto } from './dto';

@Injectable()
export class ContratosService {
  constructor(private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService, private readonly docs: DocumentosService, private readonly cal: CalendarioProvider) {}

  /** Previsualiza instrumento y garantía sin persistir. */
  async simular(id: string, plazoDias?: number) {
    const p = await this.repo.obtener(id);
    const ganador = p.propuestas.find((x) => x.id === p.propuestaAdjudicadaId);
    if (!ganador) throw new ConflictException('El proceso aún no tiene propuesta adjudicada.');
    const monto = num(ganador.montoSubasta ?? ganador.montoOfertado);
    const plazo = plazoDias ?? ganador.plazoDias;
    return { tipo: tipoInstrumentoContractual(p.tipoObjeto, plazo), monto, plazoDias: plazo, garantia: calcularGarantiaCumplimiento(monto, ganador.categoria) };
  }

  async generar(id: string, dto: ContratoDto, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, ['ADJUDICADO'], 'generar el contrato/orden');
    const ganador = p.propuestas.find((x) => x.id === p.propuestaAdjudicadaId);
    if (!ganador) throw new ConflictException('El proceso no tiene propuesta adjudicada.');
    const motivo = (await this.cal.cargar()).motivoInhabil(dto.fechaFirma);
    if (motivo) throw new BadRequestException(`La fecha de firma ${dto.fechaFirma} no es día hábil (${motivo}).`);
    const sim = await this.simular(id, dto.plazoDias);
    const numero = dto.numero ?? `${sim.tipo === 'CONTRATO' ? 'CTO' : sim.tipo === 'ORDEN_COMPRA' ? 'OC' : 'OS'}-${p.codigo}`;
    const data = {
      tipo: sim.tipo, numero, propuestaId: ganador.id, monto: sim.monto, plazoDias: sim.plazoDias, fechaFirma: new Date(dto.fechaFirma), garantiaPorcentaje: sim.garantia.porcentaje, garantiaMonto: sim.garantia.monto,
      garantiaInstrumento: dto.garantiaInstrumento ?? null, polizaNumero: dto.polizaNumero ?? null, polizaEntidad: dto.polizaEntidad ?? null, polizaVigenciaHasta: dto.polizaVigenciaHasta ? new Date(dto.polizaVigenciaHasta) : null,
    };
    await this.prisma.contrato.upsert({ where: { procesoId: id }, create: { procesoId: id, ...data }, update: data });
    await this.audit.registrar({ ctx, accion: 'CONTRATO_REGISTRADO', entidad: 'proceso', entidadId: id, previo: p.contrato, posterior: { ...data, garantia: sim.garantia } });
    const documento = await this.docs.generar(id, sim.tipo === 'CONTRATO' ? 'CONTRATO' : 'ORDEN_COMPRA_SERVICIO', ctx);
    return { ...sim, numero, documento };
  }

  async registrarRecepcion(id: string, dto: RecepcionDto, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, ['CONTRATO_FORMALIZADO'], 'registrar la recepción');
    if (!p.contrato) throw new ConflictException('No existe contrato/orden.');
    if (new Date(dto.fechaRecepcion) < p.contrato.fechaFirma) throw new BadRequestException('La recepción no puede ser anterior a la firma del contrato.');
    await this.prisma.contrato.update({ where: { procesoId: id }, data: { fechaRecepcion: new Date(dto.fechaRecepcion), observacionRecepcion: dto.observacion ?? null } });
    await this.audit.registrar({ ctx, accion: 'RECEPCION_REGISTRADA', entidad: 'proceso', entidadId: id, posterior: dto });
    return this.docs.generar(id, 'ACTA_RECEPCION', ctx);
  }
}
