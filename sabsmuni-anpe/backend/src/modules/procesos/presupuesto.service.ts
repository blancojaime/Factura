import { Injectable } from '@nestjs/common';
import { Ctx } from '../../common/auth';
import { AuditService } from '../../common/audit.service';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoCompleto, ProcesoRepo, num } from '../../common/proceso.repo';
import { bloqueSigep, construirGlosa, LineaPresupuesto, validarPreventivoC31 } from '../../domain/sigep';
import { PresupuestoDto } from './dto';

@Injectable()
export class PresupuestoService {
  constructor(private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService) {}

  lineas(p: ProcesoCompleto): (LineaPresupuesto & { c31: string | null })[] {
    return p.certificaciones.map((c) => ({ da: c.da, ue: c.ue, programa: c.programa, proyecto: c.proyecto, actividadObra: c.actividadObra, fuente: c.fuente, organismo: c.organismo, partida: c.partida, importe: num(c.importe), c31: c.c31PreventivoNumero }));
  }

  validar(p: ProcesoCompleto) {
    return validarPreventivoC31(this.lineas(p), p.items.map((i) => ({ partidaGasto: i.partidaGasto, cantidad: num(i.cantidad), precioUnitario: num(i.precioUnitario), precioTotal: num(i.precioTotal) })), num(p.precioReferencialTotal));
  }

  /** Datos de la pestaña "Captura SIGEP": interfaz espejo del C-31 + validación + bloque para copiar. */
  async captura(id: string) {
    const p = await this.repo.obtener(id);
    const cfg = await this.repo.config();
    const glosa = construirGlosa(p.objetoContratacion, p.codigo, cfg.nombreGam);
    const lineas = this.lineas(p);
    return {
      proceso: { codigo: p.codigo, cuce: p.cuceProvisorio, precioReferencial: num(p.precioReferencialTotal) },
      defaults: { da: cfg.da, ue: cfg.ue },
      lineas, glosa, validacion: this.validar(p),
      bloque: lineas.length ? bloqueSigep(lineas, glosa, lineas.find((l) => l.c31)?.c31) : '',
      camposEspejo: ['DA', 'UE', 'Programa', 'Proyecto', 'Actividad/Obra', 'Fuente', 'Organismo', 'Partida', 'Importe', 'Glosa'],
    };
  }

  async guardar(id: string, dto: PresupuestoDto, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, ['REQUERIMIENTO_VALIDADO'], 'registrar la certificación presupuestaria');
    await this.prisma.$transaction([
      this.prisma.certificacionPresupuesto.deleteMany({ where: { procesoId: id } }),
      this.prisma.certificacionPresupuesto.createMany({ data: dto.lineas.map((l) => ({ ...l, procesoId: id, c31PreventivoNumero: dto.c31PreventivoNumero ?? null })) }),
    ]);
    await this.audit.registrar({ ctx, accion: 'PRESUPUESTO_REGISTRADO', entidad: 'proceso', entidadId: id, previo: this.lineas(p), posterior: dto });
    return this.captura(id);
  }
}
