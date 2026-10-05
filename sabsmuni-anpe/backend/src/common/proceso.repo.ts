import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from './prisma.service';
import { EstadoFlujo } from '../domain/flujo';

export const incluirProceso = {
  items: { orderBy: { numero: 'asc' } },
  cronograma: true,
  certificaciones: true,
  propuestas: { orderBy: { orden: 'asc' } },
  contrato: true,
  solicitante: { select: { id: true, nombre: true, cargo: true, unidad: true, email: true } },
  rpa: { select: { id: true, nombre: true, cargo: true, email: true } },
} satisfies Prisma.ProcesoAnpeInclude;

export type ProcesoCompleto = Prisma.ProcesoAnpeGetPayload<{ include: typeof incluirProceso }>;

export const num = (d: Prisma.Decimal | number | null | undefined): number => (d == null ? 0 : Number(d));
export const isoFecha = (d: Date | null | undefined): string | null => (d ? d.toISOString().slice(0, 10) : null);

@Injectable()
export class ProcesoRepo {
  constructor(readonly prisma: PrismaService) {}

  async obtener(id: string): Promise<ProcesoCompleto> {
    const p = await this.prisma.procesoAnpe.findUnique({ where: { id }, include: incluirProceso });
    if (!p) throw new NotFoundException('Proceso no encontrado.');
    return p;
  }

  /** Las operaciones de edición solo proceden en los estados donde la normativa lo permite. */
  exigirEstado(p: { estadoFlujo: EstadoFlujo | string }, permitidos: EstadoFlujo[], operacion: string): void {
    if (!permitidos.includes(p.estadoFlujo as EstadoFlujo))
      throw new ConflictException(`No se puede ${operacion} en estado ${p.estadoFlujo} (permitido en: ${permitidos.join(', ')}).`);
  }

  async config() {
    const c = await this.prisma.configInstitucional.findUnique({ where: { id: 1 } });
    if (!c) throw new NotFoundException('Falta la configuración institucional (ejecute el seed o configúrela como administrador).');
    return c;
  }
}
