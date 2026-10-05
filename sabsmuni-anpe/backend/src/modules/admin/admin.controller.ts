import { BadRequestException, Body, Controller, Delete, Get, NotFoundException, Param, ParseIntPipe, Patch, Post, Put, Query } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { NombreRol } from '@prisma/client';
import * as bcrypt from 'bcryptjs';
import { IsBoolean, IsDateString, IsEmail, IsEnum, IsObject, IsOptional, IsString, Matches, MaxLength, MinLength } from 'class-validator';
import { AuditService } from '../../common/audit.service';
import { Ctx, CtxActual, Roles } from '../../common/auth';
import { PrismaService } from '../../common/prisma.service';

const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{10,}$/;
const MSG_PASSWORD = 'La contraseña debe tener al menos 10 caracteres, con letras y números.';

class CrearUsuarioDto {
  @IsEmail() email!: string; @IsString() @MinLength(3) nombre!: string; @IsOptional() @IsString() cargo?: string; @IsOptional() @IsString() unidad?: string;
  @IsEnum(NombreRol) rol!: NombreRol; @Matches(PASSWORD_RE, { message: MSG_PASSWORD }) password!: string;
}
class ActualizarUsuarioDto {
  @IsOptional() @IsString() @MinLength(3) nombre?: string; @IsOptional() @IsString() cargo?: string; @IsOptional() @IsString() unidad?: string;
  @IsOptional() @IsEnum(NombreRol) rol?: NombreRol; @IsOptional() @IsBoolean() activo?: boolean; @IsOptional() @Matches(PASSWORD_RE, { message: MSG_PASSWORD }) password?: string;
}
class ConfigDto {
  @IsString() nombreGam!: string; @IsString() nit!: string; @IsString() da!: string; @IsString() ue!: string; @IsString() ciudad!: string; @IsString() departamento!: string;
  @IsString() direccion!: string; @IsString() rpaNombre!: string; @IsString() rpaCargo!: string; @IsOptional() @IsObject() margenes?: Record<string, number>; @IsOptional() @IsObject() plazos?: Record<string, number>;
}
class ChbDto { @Matches(/^\d{8}$/) codigoUnspsc!: string; @IsString() @MinLength(3) descripcion!: string; @IsOptional() @IsString() productor?: string; @IsOptional() @IsString() fichaUrl?: string; @IsOptional() @IsBoolean() vigente?: boolean }
class PartidaDto { @Matches(/^\d{5}$/) codigo!: string; @IsString() descripcion!: string; @IsString() grupo!: string }
class FeriadoDto { @IsDateString({ strict: true }) fecha!: string; @IsString() @MaxLength(120) descripcion!: string; @IsOptional() @IsString() ambito?: string }
class MarcaDto { @IsString() @MinLength(2) @MaxLength(60) nombre!: string }

@ApiTags('Administración')
@Controller()
export class AdminController {
  constructor(private readonly prisma: PrismaService, private readonly audit: AuditService) {}

  // ───── Usuarios ─────
  @Roles('ADMINISTRADOR_SISTEMA') @Get('usuarios')
  usuarios() {
    return this.prisma.usuario.findMany({ select: { id: true, email: true, nombre: true, cargo: true, unidad: true, activo: true, rol: { select: { nombre: true } } }, orderBy: { nombre: 'asc' } });
  }

  @Roles('ADMINISTRADOR_SISTEMA') @Post('usuarios')
  async crearUsuario(@Body() dto: CrearUsuarioDto, @CtxActual() ctx: Ctx) {
    const rol = await this.prisma.rol.findUniqueOrThrow({ where: { nombre: dto.rol } });
    const u = await this.prisma.usuario.create({ data: { email: dto.email.toLowerCase(), nombre: dto.nombre, cargo: dto.cargo, unidad: dto.unidad, rolId: rol.id, passwordHash: await bcrypt.hash(dto.password, 12) }, select: { id: true, email: true, nombre: true } });
    await this.audit.registrar({ ctx, accion: 'USUARIO_CREADO', entidad: 'usuario', entidadId: u.id, posterior: { email: u.email, rol: dto.rol } });
    return u;
  }

  @Roles('ADMINISTRADOR_SISTEMA') @Patch('usuarios/:id')
  async actualizarUsuario(@Param('id') id: string, @Body() dto: ActualizarUsuarioDto, @CtxActual() ctx: Ctx) {
    if (id === ctx.userId && (dto.activo === false || (dto.rol && dto.rol !== 'ADMINISTRADOR_SISTEMA'))) throw new BadRequestException('No puede desactivarse ni quitarse el rol de administrador a sí mismo.');
    const previo = await this.prisma.usuario.findUnique({ where: { id }, include: { rol: true } });
    if (!previo) throw new NotFoundException('Usuario no encontrado.');
    const { rol, password, ...resto } = dto;
    const u = await this.prisma.usuario.update({
      where: { id }, select: { id: true, email: true, nombre: true, activo: true },
      data: { ...resto, ...(rol ? { rolId: (await this.prisma.rol.findUniqueOrThrow({ where: { nombre: rol } })).id } : {}), ...(password ? { passwordHash: await bcrypt.hash(password, 12) } : {}) },
    });
    if (dto.activo === false || password) await this.prisma.sesion.updateMany({ where: { usuarioId: id, revocadaEn: null }, data: { revocadaEn: new Date() } });
    await this.audit.registrar({ ctx, accion: 'USUARIO_ACTUALIZADO', entidad: 'usuario', entidadId: id, previo: { rol: previo.rol.nombre, activo: previo.activo }, posterior: { rol: dto.rol, activo: dto.activo, passwordCambiada: !!password } });
    return u;
  }

  // ───── Configuración institucional ─────
  @Get('config') config() { return this.prisma.configInstitucional.findUnique({ where: { id: 1 } }); }

  @Roles('ADMINISTRADOR_SISTEMA') @Put('config')
  async guardarConfig(@Body() dto: ConfigDto, @CtxActual() ctx: Ctx) {
    const previo = await this.prisma.configInstitucional.findUnique({ where: { id: 1 } });
    const data = { ...dto, margenes: dto.margenes ?? undefined, plazos: dto.plazos ?? undefined };
    const c = await this.prisma.configInstitucional.upsert({ where: { id: 1 }, create: { id: 1, ...data }, update: data });
    await this.audit.registrar({ ctx, accion: 'CONFIG_ACTUALIZADA', entidad: 'config', entidadId: '1', previo, posterior: c });
    return c;
  }

  // ───── Catálogos ─────
  @Get('catalogos/chb') chb(@Query('q') q?: string) {
    return this.prisma.catalogoChb.findMany({ where: q ? { OR: [{ codigoUnspsc: { startsWith: q } }, { descripcion: { contains: q, mode: 'insensitive' } }] } : {}, orderBy: { codigoUnspsc: 'asc' }, take: 200 });
  }
  @Roles('ADMINISTRADOR_SISTEMA') @Post('catalogos/chb')
  async agregarChb(@Body() dto: ChbDto, @CtxActual() ctx: Ctx) {
    const c = await this.prisma.catalogoChb.create({ data: { ...dto, productor: dto.productor ?? null } });
    await this.audit.registrar({ ctx, accion: 'CHB_AGREGADO', entidad: 'catalogo_chb', entidadId: c.id, posterior: c });
    return c;
  }
  @Roles('ADMINISTRADOR_SISTEMA') @Patch('catalogos/chb/:id')
  async chbVigencia(@Param('id') id: string, @Body() dto: { vigente: boolean }, @CtxActual() ctx: Ctx) {
    const c = await this.prisma.catalogoChb.update({ where: { id }, data: { vigente: !!dto.vigente } });
    await this.audit.registrar({ ctx, accion: 'CHB_VIGENCIA', entidad: 'catalogo_chb', entidadId: id, posterior: { vigente: c.vigente } });
    return c;
  }
  @Get('catalogos/partidas') partidas() { return this.prisma.catalogoPartida.findMany({ orderBy: { codigo: 'asc' } }); }
  @Roles('ADMINISTRADOR_SISTEMA') @Post('catalogos/partidas')
  async partida(@Body() dto: PartidaDto, @CtxActual() ctx: Ctx) {
    const p = await this.prisma.catalogoPartida.upsert({ where: { codigo: dto.codigo }, create: dto, update: dto });
    await this.audit.registrar({ ctx, accion: 'PARTIDA_GUARDADA', entidad: 'catalogo_partida', entidadId: dto.codigo, posterior: dto });
    return p;
  }
  @Get('catalogos/feriados') feriados() { return this.prisma.feriado.findMany({ orderBy: { fecha: 'asc' } }); }
  @Roles('ADMINISTRADOR_SISTEMA') @Post('catalogos/feriados')
  async feriado(@Body() dto: FeriadoDto, @CtxActual() ctx: Ctx) {
    const f = await this.prisma.feriado.upsert({ where: { fecha: new Date(dto.fecha) }, create: { fecha: new Date(dto.fecha), descripcion: dto.descripcion, ambito: dto.ambito ?? 'DEPARTAMENTAL' }, update: { descripcion: dto.descripcion } });
    await this.audit.registrar({ ctx, accion: 'FERIADO_GUARDADO', entidad: 'feriado', entidadId: String(f.id), posterior: dto });
    return f;
  }
  @Roles('ADMINISTRADOR_SISTEMA') @Delete('catalogos/feriados/:id')
  async quitarFeriado(@Param('id', ParseIntPipe) id: number, @CtxActual() ctx: Ctx) {
    await this.prisma.feriado.delete({ where: { id } });
    await this.audit.registrar({ ctx, accion: 'FERIADO_ELIMINADO', entidad: 'feriado', entidadId: String(id) });
    return { eliminado: true };
  }
  @Roles('ADMINISTRADOR_SISTEMA') @Post('catalogos/marcas')
  async marca(@Body() dto: MarcaDto, @CtxActual() ctx: Ctx) {
    const m = await this.prisma.marcaRegistrada.upsert({ where: { nombre: dto.nombre.toLowerCase() }, create: { nombre: dto.nombre.toLowerCase() }, update: {} });
    await this.audit.registrar({ ctx, accion: 'MARCA_AGREGADA', entidad: 'marca', entidadId: String(m.id), posterior: m });
    return m;
  }

  // ───── Auditoría ─────
  @Roles('ADMINISTRADOR_SISTEMA', 'AUTORIDAD_RPA') @Get('auditoria')
  auditoria(@Query('entidad') entidad?: string, @Query('entidadId') entidadId?: string, @Query('limite') limite?: string) {
    return this.audit.consultar({ entidad, entidadId, limite: limite ? Number(limite) : undefined });
  }
  /** Recorre la cadena de hashes: detecta cualquier alteración o borrado de registros. */
  @Roles('ADMINISTRADOR_SISTEMA', 'AUTORIDAD_RPA') @Get('auditoria/verificar')
  verificar() { return this.audit.verificarIntegridad(); }
}
