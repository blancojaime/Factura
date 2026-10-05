import { BadRequestException, ConflictException, Injectable } from '@nestjs/common';
import { Ctx } from '../../common/auth';
import { AuditService } from '../../common/audit.service';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoRepo, num } from '../../common/proceso.repo';
import { cuadroComparativo, evaluarPropuestas, MARGENES_DEFECTO, OpcionesEvaluacion, PropuestaEvaluable, V1_ITEMS, verificarV1 } from '../../domain/evaluacion';
import { ActualizarPropuestaDto, PropuestaDto } from './dto';
import { Prisma } from '@prisma/client';

const ESTADOS_EDICION = ['PUBLICADO', 'EVALUACION'] as const;

@Injectable()
export class PropuestasService {
  constructor(private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService) {}

  private async margenes() {
    const cfg = await this.prisma.configInstitucional.findUnique({ where: { id: 1 } });
    return { ...MARGENES_DEFECTO, ...((cfg?.margenes as Record<string, number> | null) ?? {}) };
  }

  async listar(id: string) {
    const p = await this.repo.obtener(id);
    return { itemsV1: V1_ITEMS, propuestas: p.propuestas, evaluacion: p.evaluacion };
  }

  async crear(id: string, dto: PropuestaDto, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, [...ESTADOS_EDICION], 'registrar propuestas');
    if (dto.montoSubasta != null && p.tipoObjeto === 'BIENES') throw new BadRequestException('La subasta electrónica solo aplica a Obras y Servicios.');
    if (dto.montoSubasta != null && dto.montoSubasta > dto.montoOfertado) throw new BadRequestException('El monto de subasta no puede superar la oferta inicial.');
    const orden = (p.propuestas.at(-1)?.orden ?? 0) + 1;
    const margen = (await this.margenes())[dto.categoria];
    try {
      const nueva = await this.prisma.propuestaRupe.create({ data: { ...dto, procesoId: id, orden, margenProboliviaMype: margen } });
      await this.audit.registrar({ ctx, accion: 'PROPUESTA_REGISTRADA', entidad: 'propuesta', entidadId: nueva.id, posterior: { procesoId: id, nit: dto.nitProveedor, monto: dto.montoOfertado } });
      await this.invalidarEvaluacion(id);
      return nueva;
    } catch (e) {
      if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2002') throw new ConflictException('Ya existe una propuesta de ese NIT en el proceso.');
      throw e;
    }
  }

  async actualizar(id: string, propuestaId: string, dto: ActualizarPropuestaDto, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, [...ESTADOS_EDICION], 'modificar propuestas');
    const previo = p.propuestas.find((x) => x.id === propuestaId);
    if (!previo) throw new BadRequestException('La propuesta no pertenece al proceso.');
    const oferta = dto.montoOfertado ?? num(previo.montoOfertado);
    const subasta = dto.montoSubasta ?? (previo.montoSubasta == null ? undefined : num(previo.montoSubasta));
    if (subasta != null && p.tipoObjeto === 'BIENES') throw new BadRequestException('La subasta electrónica solo aplica a Obras y Servicios.');
    if (subasta != null && subasta > oferta) throw new BadRequestException('El monto de subasta no puede superar la oferta inicial.');
    const margen = dto.categoria ? (await this.margenes())[dto.categoria] : undefined;
    const nueva = await this.prisma.propuestaRupe.update({ where: { id: propuestaId }, data: { ...dto, ...(margen !== undefined ? { margenProboliviaMype: margen } : {}) } });
    await this.audit.registrar({ ctx, accion: 'PROPUESTA_ACTUALIZADA', entidad: 'propuesta', entidadId: propuestaId, previo, posterior: nueva });
    await this.invalidarEvaluacion(id);
    return nueva;
  }

  async eliminar(id: string, propuestaId: string, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, [...ESTADOS_EDICION], 'eliminar propuestas');
    const previo = p.propuestas.find((x) => x.id === propuestaId);
    if (!previo) throw new BadRequestException('La propuesta no pertenece al proceso.');
    await this.prisma.propuestaRupe.delete({ where: { id: propuestaId } });
    await this.audit.registrar({ ctx, accion: 'PROPUESTA_ELIMINADA', entidad: 'propuesta', entidadId: propuestaId, previo });
    await this.invalidarEvaluacion(id);
    return { eliminado: true };
  }

  async registrarV1(id: string, propuestaId: string, v1: Record<string, boolean>, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, [...ESTADOS_EDICION], 'registrar la verificación V-1');
    const previo = p.propuestas.find((x) => x.id === propuestaId);
    if (!previo) throw new BadRequestException('La propuesta no pertenece al proceso.');
    const validos = new Set(V1_ITEMS.map((i) => i.codigo));
    const limpio = Object.fromEntries(Object.entries(v1).filter(([k, v]) => validos.has(k) && typeof v === 'boolean'));
    const nueva = await this.prisma.propuestaRupe.update({ where: { id: propuestaId }, data: { v1: limpio, califica_v1: verificarV1(limpio).califica } });
    await this.audit.registrar({ ctx, accion: 'V1_REGISTRADO', entidad: 'propuesta', entidadId: propuestaId, previo: previo.v1, posterior: limpio });
    await this.invalidarEvaluacion(id);
    return nueva;
  }

  /** Un cambio en propuestas anula la evaluación calculada: debe recalcularse antes de recomendar. */
  private async invalidarEvaluacion(id: string) {
    await this.prisma.procesoAnpe.update({ where: { id }, data: { evaluacion: Prisma.DbNull } });
  }

  async evaluar(id: string, ctx: Ctx, opciones?: Partial<OpcionesEvaluacion>) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, ['EVALUACION'], 'ejecutar la evaluación');
    const propuestas: PropuestaEvaluable[] = p.propuestas.map((x) => ({
      id: x.id, nitProveedor: x.nitProveedor, razonSocial: x.razonSocial, montoOfertado: num(x.montoOfertado), montoSubasta: x.montoSubasta == null ? null : num(x.montoSubasta), plazoDias: x.plazoDias,
      categoria: x.categoria, v1: (x.v1 ?? {}) as Record<string, boolean>, puntajeTecnico: x.puntajeTecnico == null ? null : num(x.puntajeTecnico), orden: x.orden,
    }));
    const resultado = evaluarPropuestas(p.tipoObjeto, p.metodoSeleccion, num(p.precioReferencialTotal), propuestas, { margenes: await this.margenes(), ...opciones });
    await this.prisma.procesoAnpe.update({ where: { id }, data: { evaluacion: JSON.parse(JSON.stringify(resultado)) } });
    for (const x of p.propuestas) await this.prisma.propuestaRupe.update({ where: { id: x.id }, data: { califica_v1: verificarV1((x.v1 ?? {}) as Record<string, boolean>).califica } });
    await this.audit.registrar({ ctx, accion: 'EVALUACION_EJECUTADA', entidad: 'proceso', entidadId: id, posterior: { recomendadaId: resultado.recomendadaId, desierto: resultado.desierto, calificadas: resultado.estadisticas.ofertasCalificadas } });
    return { ...resultado, cuadro: cuadroComparativo(resultado) };
  }
}
