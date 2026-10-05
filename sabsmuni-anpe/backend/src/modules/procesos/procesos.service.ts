import { BadRequestException, ConflictException, ForbiddenException, Injectable } from '@nestjs/common';
import { Ctx } from '../../common/auth';
import { AuditService } from '../../common/audit.service';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoRepo, incluirProceso, num } from '../../common/proceso.repo';
import { multiplicar, sumaExacta } from '../../domain/money';
import { ANPE_MAX, ANPE_MIN } from '../../domain/cronograma';
import { ActualizarItemDto, ActualizarProcesoDto, CrearProcesoDto, ItemDto } from './dto';

@Injectable()
export class ProcesosService {
  constructor(private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService) {}

  async crear(dto: CrearProcesoDto, ctx: Ctx) {
    const anio = new Date().getFullYear();
    const p = await this.prisma.$transaction(async (tx) => {
      await tx.$executeRaw`SELECT pg_advisory_xact_lock(7002)`;
      const n = (await tx.procesoAnpe.count({ where: { codigo: { startsWith: `ANPE-${anio}-` } } })) + 1;
      const codigo = `ANPE-${anio}-${String(n).padStart(4, '0')}`;
      return tx.procesoAnpe.create({ data: { ...dto, codigo, cuceProvisorio: `PROV-${anio}-${String(n).padStart(4, '0')}`, idSolicitante: ctx.userId } });
    });
    await this.audit.registrar({ ctx, accion: 'PROCESO_CREADO', entidad: 'proceso', entidadId: p.id, posterior: { codigo: p.codigo, objeto: p.objetoContratacion } });
    return p;
  }

  listar(ctx: Ctx, estado?: string) {
    return this.prisma.procesoAnpe.findMany({
      where: { ...(ctx.rol === 'UNIDAD_SOLICITANTE' ? { idSolicitante: ctx.userId } : {}), ...(estado ? { estadoFlujo: estado as never } : {}) },
      orderBy: { creadoEn: 'desc' }, take: 200,
      select: { id: true, codigo: true, objetoContratacion: true, tipoObjeto: true, metodoSeleccion: true, precioReferencialTotal: true, estadoFlujo: true, creadoEn: true, solicitante: { select: { nombre: true } } },
    });
  }

  private async propio(id: string, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    if (ctx.rol === 'UNIDAD_SOLICITANTE' && p.idSolicitante !== ctx.userId) throw new ForbiddenException('Solo la unidad solicitante propietaria puede modificar este proceso.');
    return p;
  }

  async actualizar(id: string, dto: ActualizarProcesoDto, ctx: Ctx) {
    const antes = await this.propio(id, ctx);
    this.repo.exigirEstado(antes, ['BORRADOR'], 'modificar los datos generales');
    const despues = await this.prisma.procesoAnpe.update({ where: { id }, data: dto });
    await this.audit.registrar({ ctx, accion: 'PROCESO_ACTUALIZADO', entidad: 'proceso', entidadId: id, previo: dto && Object.fromEntries(Object.keys(dto).map((k) => [k, (antes as never)[k]])), posterior: dto });
    return despues;
  }

  private async recalcularTotal(procesoId: string): Promise<number> {
    const items = await this.prisma.itemContratacion.findMany({ where: { procesoId }, select: { precioTotal: true } });
    const total = sumaExacta(items.map((i) => num(i.precioTotal)));
    await this.prisma.procesoAnpe.update({ where: { id: procesoId }, data: { precioReferencialTotal: total } });
    return total;
  }

  async agregarItem(id: string, dto: ItemDto, ctx: Ctx) {
    const p = await this.propio(id, ctx);
    this.repo.exigirEstado(p, ['BORRADOR'], 'agregar ítems');
    const total = multiplicar(dto.cantidad, dto.precioUnitario);
    const nuevoTotal = sumaExacta([...p.items.map((i) => num(i.precioTotal)), total]);
    if (nuevoTotal > ANPE_MAX) throw new BadRequestException(`El precio referencial total (${nuevoTotal}) excede el máximo ANPE (Bs ${ANPE_MAX}). Debe tramitarse como Licitación Pública.`);
    const numero = (p.items.at(-1)?.numero ?? 0) + 1;
    const item = await this.prisma.itemContratacion.create({ data: { ...dto, procesoId: id, numero, precioTotal: total } });
    await this.recalcularTotal(id);
    await this.audit.registrar({ ctx, accion: 'ITEM_AGREGADO', entidad: 'item', entidadId: item.id, posterior: { procesoId: id, numero, total } });
    return item;
  }

  async actualizarItem(id: string, itemId: string, dto: ActualizarItemDto, ctx: Ctx) {
    const p = await this.propio(id, ctx);
    this.repo.exigirEstado(p, ['BORRADOR'], 'modificar ítems');
    const previo = p.items.find((i) => i.id === itemId);
    if (!previo) throw new BadRequestException('El ítem no pertenece al proceso.');
    const cantidad = dto.cantidad ?? num(previo.cantidad), pu = dto.precioUnitario ?? num(previo.precioUnitario);
    const item = await this.prisma.itemContratacion.update({ where: { id: itemId }, data: { ...dto, precioTotal: multiplicar(cantidad, pu), resultadoChb: null, requiereExcepcionChb: false } });
    const total = await this.recalcularTotal(id);
    if (total > ANPE_MAX) throw new BadRequestException(`El precio referencial total (${total}) excede el máximo ANPE.`);
    await this.audit.registrar({ ctx, accion: 'ITEM_ACTUALIZADO', entidad: 'item', entidadId: itemId, previo, posterior: item });
    return item;
  }

  async eliminarItem(id: string, itemId: string, ctx: Ctx) {
    const p = await this.propio(id, ctx);
    this.repo.exigirEstado(p, ['BORRADOR'], 'eliminar ítems');
    const previo = p.items.find((i) => i.id === itemId);
    if (!previo) throw new BadRequestException('El ítem no pertenece al proceso.');
    await this.prisma.itemContratacion.delete({ where: { id: itemId } });
    await this.recalcularTotal(id);
    await this.audit.registrar({ ctx, accion: 'ITEM_ELIMINADO', entidad: 'item', entidadId: itemId, previo });
    return { eliminado: true };
  }

  static rangoAnpe = { min: ANPE_MIN, max: ANPE_MAX };
  static incluir = incluirProceso;
}
