import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma.service';
import { CalendarioBolivia } from '../domain/calendario-bolivia';

@Injectable()
export class CalendarioProvider {
  constructor(private readonly prisma: PrismaService) {}
  /** Calendario nacional + feriados departamentales/decretados cargados por el administrador. */
  async cargar(): Promise<CalendarioBolivia> {
    const extras = await this.prisma.feriado.findMany();
    return new CalendarioBolivia(extras.map((f) => ({ fecha: f.fecha.toISOString().slice(0, 10), nombre: f.descripcion })));
  }
}
