import { BadRequestException, Injectable } from '@nestjs/common';
import { Ctx } from '../../common/auth';
import { AuditService } from '../../common/audit.service';
import { CalendarioProvider } from '../../common/calendario.provider';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoRepo, isoFecha, num } from '../../common/proceso.repo';
import { calcularCronograma, PlazosConfig } from '../../domain/cronograma';
import { CalcularCronogramaDto } from './dto';

@Injectable()
export class CronogramaService {
  constructor(private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService, private readonly cal: CalendarioProvider) {}

  private async plazos(): Promise<Partial<PlazosConfig> | undefined> {
    return ((await this.prisma.configInstitucional.findUnique({ where: { id: 1 } }))?.plazos as Partial<PlazosConfig> | null) ?? undefined;
  }

  /** Cálculo sin persistir: alimenta el simulador de la interfaz. */
  async calcular(dto: CalcularCronogramaDto, precioProceso?: number) {
    const precio = dto.precioReferencial ?? precioProceso;
    if (!precio) throw new BadRequestException('Indique el precio referencial.');
    try {
      return calcularCronograma({ fechaPublicacion: dto.fechaPublicacion, fechaApertura: dto.fechaApertura, precioReferencial: precio, plazos: await this.plazos() }, await this.cal.cargar());
    } catch (e) {
      throw new BadRequestException((e as Error).message);
    }
  }

  async obtener(id: string) {
    const p = await this.repo.obtener(id);
    return p.cronograma && { ...p.cronograma, fechaPublicacion: isoFecha(p.cronograma.fechaPublicacion), fechaApertura: isoFecha(p.cronograma.fechaApertura), fechaAdjudicacion: isoFecha(p.cronograma.fechaAdjudicacion), fechaPresentacionDoc: isoFecha(p.cronograma.fechaPresentacionDoc), fechaContrato: isoFecha(p.cronograma.fechaContrato) };
  }

  async guardar(id: string, dto: CalcularCronogramaDto, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, ['PRESUPUESTO_CERTIFICADO', 'DBC_ELABORADO'], 'definir el cronograma');
    const r = await this.calcular({ ...dto, precioReferencial: undefined }, num(p.precioReferencialTotal));
    const c = r.cronograma;
    const data = { fechaPublicacion: new Date(c.fechaPublicacion), fechaApertura: new Date(c.fechaApertura), fechaAdjudicacion: new Date(c.fechaAdjudicacion), fechaPresentacionDoc: new Date(c.fechaPresentacionDoc), fechaContrato: new Date(c.fechaContrato) };
    await this.prisma.cronogramaAnpe.upsert({ where: { procesoId: id }, create: { procesoId: id, ...data }, update: data });
    await this.audit.registrar({ ctx, accion: 'CRONOGRAMA_DEFINIDO', entidad: 'proceso', entidadId: id, previo: p.cronograma, posterior: c });
    return r;
  }
}
