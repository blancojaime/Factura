import { Body, Controller, Delete, Get, Param, ParseUUIDPipe, Patch, Post, Put, Query } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Ctx, CtxActual, Roles } from '../../common/auth';
import { ProcesoRepo, num } from '../../common/proceso.repo';
import { ActualizarItemDto, ActualizarProcesoDto, ActualizarPropuestaDto, AnalizarTextoDto, CalcularCronogramaDto, ContratoDto, CrearProcesoDto, ItemDto, PresupuestoDto, PropuestaDto, RecepcionDto, RequerimientoDto, TransicionDto, V1Dto } from './dto';
import { ContratosService } from './contratos.service';
import { CronogramaService } from './cronograma.service';
import { FlujoService } from './flujo.service';
import { PresupuestoService } from './presupuesto.service';
import { ProcesosService } from './procesos.service';
import { PropuestasService } from './propuestas.service';
import { RequerimientoService } from './requerimiento.service';
import { SECCIONES_REQUERIMIENTO } from '../../domain/especificaciones';

const US = 'UNIDAD_SOLICITANTE', RP = 'RESPONSABLE_PRESUPUESTO', RC = 'RESPONSABLE_CONTRATACIONES', RPA = 'AUTORIDAD_RPA' as const;

@ApiTags('Procesos ANPE')
@Controller()
export class ProcesosController {
  constructor(
    private readonly procesos: ProcesosService, private readonly repo: ProcesoRepo, private readonly req: RequerimientoService, private readonly crono: CronogramaService,
    private readonly pres: PresupuestoService, private readonly prop: PropuestasService, private readonly contratos: ContratosService, private readonly flujo: FlujoService,
  ) {}

  // ───── Procesos ─────
  @Get('procesos') listar(@CtxActual() ctx: Ctx, @Query('estado') estado?: string) { return this.procesos.listar(ctx, estado); }

  @Roles(US) @Post('procesos') @ApiOperation({ summary: 'Crea una solicitud de contratación ANPE en estado BORRADOR' })
  crear(@Body() dto: CrearProcesoDto, @CtxActual() ctx: Ctx) { return this.procesos.crear(dto, ctx); }

  @Get('procesos/:id') @ApiOperation({ summary: 'Detalle completo + transiciones disponibles para el rol' })
  async detalle(@Param('id', ParseUUIDPipe) id: string, @CtxActual() ctx: Ctx) {
    const p = await this.repo.obtener(id);
    return { ...p, secciones: SECCIONES_REQUERIMIENTO[p.tipoObjeto], transiciones: await this.flujo.disponibles(id, ctx) };
  }

  @Roles(US) @Patch('procesos/:id')
  actualizar(@Param('id', ParseUUIDPipe) id: string, @Body() dto: ActualizarProcesoDto, @CtxActual() ctx: Ctx) { return this.procesos.actualizar(id, dto, ctx); }

  @Roles(US, RP, RC, RPA) @Post('procesos/:id/transicion') @ApiOperation({ summary: 'Avanza el flujo; valida rol y precondiciones y emite los documentos del paso' })
  transicion(@Param('id', ParseUUIDPipe) id: string, @Body() dto: TransicionDto, @CtxActual() ctx: Ctx) { return this.flujo.transicionar(id, dto, ctx); }

  // ───── Ítems ─────
  @Roles(US) @Post('procesos/:id/items') agregarItem(@Param('id', ParseUUIDPipe) id: string, @Body() dto: ItemDto, @CtxActual() ctx: Ctx) { return this.procesos.agregarItem(id, dto, ctx); }
  @Roles(US) @Patch('procesos/:id/items/:itemId') actualizarItem(@Param('id', ParseUUIDPipe) id: string, @Param('itemId', ParseUUIDPipe) itemId: string, @Body() dto: ActualizarItemDto, @CtxActual() ctx: Ctx) { return this.procesos.actualizarItem(id, itemId, dto, ctx); }
  @Roles(US) @Delete('procesos/:id/items/:itemId') eliminarItem(@Param('id', ParseUUIDPipe) id: string, @Param('itemId', ParseUUIDPipe) itemId: string, @CtxActual() ctx: Ctx) { return this.procesos.eliminarItem(id, itemId, ctx); }

  // ───── Módulo A: requerimiento y CHB ─────
  @Post('requerimiento/analizar') @ApiOperation({ summary: 'Analiza un texto en vivo: marcas, exclusividad, patentes' })
  analizar(@Body() dto: AnalizarTextoDto) { return this.req.analizarTexto(dto.texto); }
  @Roles(US) @Put('procesos/:id/requerimiento') guardarRequerimiento(@Param('id', ParseUUIDPipe) id: string, @Body() dto: RequerimientoDto, @CtxActual() ctx: Ctx) { return this.req.guardarSecciones(id, dto.secciones, ctx); }
  @Roles(US) @Post('procesos/:id/requerimiento/validar') @ApiOperation({ summary: 'Valida ET/TdR y cruza cada ítem con el catálogo CHB (D.S. 4505); emite el formulario de insuficiencia si corresponde' })
  validarRequerimiento(@Param('id', ParseUUIDPipe) id: string, @CtxActual() ctx: Ctx) { return this.req.validar(id, ctx); }

  // ───── Módulo B: cronograma ─────
  @Roles(RC, RPA) @Post('procesos/:id/cronograma/calcular') @ApiOperation({ summary: 'Simula el cronograma (Art. 47 D.S. 0181) sin guardar' })
  async calcularCronograma(@Param('id', ParseUUIDPipe) id: string, @Body() dto: CalcularCronogramaDto) { return this.crono.calcular(dto, num((await this.repo.obtener(id)).precioReferencialTotal)); }
  @Roles(RC) @Put('procesos/:id/cronograma') guardarCronograma(@Param('id', ParseUUIDPipe) id: string, @Body() dto: CalcularCronogramaDto, @CtxActual() ctx: Ctx) { return this.crono.guardar(id, dto, ctx); }
  @Get('procesos/:id/cronograma') cronograma(@Param('id', ParseUUIDPipe) id: string) { return this.crono.obtener(id); }

  // ───── Módulo C: SIGEP ─────
  @Get('procesos/:id/sigep') captura(@Param('id', ParseUUIDPipe) id: string) { return this.pres.captura(id); }
  @Roles(RP) @Put('procesos/:id/presupuesto') guardarPresupuesto(@Param('id', ParseUUIDPipe) id: string, @Body() dto: PresupuestoDto, @CtxActual() ctx: Ctx) { return this.pres.guardar(id, dto, ctx); }

  // ───── Módulo D: propuestas y evaluación ─────
  @Get('procesos/:id/propuestas') propuestas(@Param('id', ParseUUIDPipe) id: string) { return this.prop.listar(id); }
  @Roles(RC) @Post('procesos/:id/propuestas') crearPropuesta(@Param('id', ParseUUIDPipe) id: string, @Body() dto: PropuestaDto, @CtxActual() ctx: Ctx) { return this.prop.crear(id, dto, ctx); }
  @Roles(RC) @Patch('procesos/:id/propuestas/:pid') actualizarPropuesta(@Param('id', ParseUUIDPipe) id: string, @Param('pid', ParseUUIDPipe) pid: string, @Body() dto: ActualizarPropuestaDto, @CtxActual() ctx: Ctx) { return this.prop.actualizar(id, pid, dto, ctx); }
  @Roles(RC) @Delete('procesos/:id/propuestas/:pid') eliminarPropuesta(@Param('id', ParseUUIDPipe) id: string, @Param('pid', ParseUUIDPipe) pid: string, @CtxActual() ctx: Ctx) { return this.prop.eliminar(id, pid, ctx); }
  @Roles(RC) @Put('procesos/:id/propuestas/:pid/v1') @ApiOperation({ summary: 'Registra el Formulario V-1 (Presentó / No presentó)' })
  v1(@Param('id', ParseUUIDPipe) id: string, @Param('pid', ParseUUIDPipe) pid: string, @Body() dto: V1Dto, @CtxActual() ctx: Ctx) { return this.prop.registrarV1(id, pid, dto.v1, ctx); }
  @Roles(RC) @Post('procesos/:id/evaluacion') @ApiOperation({ summary: 'Ejecuta la evaluación técnico-económica con márgenes de preferencia y devuelve el cuadro comparativo' })
  evaluar(@Param('id', ParseUUIDPipe) id: string, @CtxActual() ctx: Ctx) { return this.prop.evaluar(id, ctx); }

  // ───── Módulo E: contrato y recepción ─────
  @Roles(RC, RPA) @Get('procesos/:id/contrato/simular') simular(@Param('id', ParseUUIDPipe) id: string, @Query('plazoDias') plazo?: string) { return this.contratos.simular(id, plazo ? Number(plazo) : undefined); }
  @Roles(RC, RPA) @Post('procesos/:id/contrato') @ApiOperation({ summary: 'Genera contrato u orden (≤15 días calendario) con garantía de cumplimiento 7% / 3,5%' })
  contrato(@Param('id', ParseUUIDPipe) id: string, @Body() dto: ContratoDto, @CtxActual() ctx: Ctx) { return this.contratos.generar(id, dto, ctx); }
  @Roles(RC) @Post('procesos/:id/recepcion') recepcion(@Param('id', ParseUUIDPipe) id: string, @Body() dto: RecepcionDto, @CtxActual() ctx: Ctx) { return this.contratos.registrarRecepcion(id, dto, ctx); }
}
