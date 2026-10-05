import { Body, Controller, Get, Header, Param, ParseUUIDPipe, Post, StreamableFile, UploadedFile, UseInterceptors, Res } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiConsumes, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Throttle } from '@nestjs/throttler';
import { Response } from 'express';
import { Ctx, CtxActual, Public, Roles } from '../../common/auth';
import { SubirDocumentoDto } from '../procesos/dto';
import { DocumentosService, TIPOS_GENERABLES } from './documentos.service';
import { ExpedienteService } from './expediente.service';
import { TipoGenerable } from '../../pdf/templates';
import { BadRequestException } from '@nestjs/common';

@ApiTags('Documentos y Expediente')
@Controller()
export class DocumentosController {
  constructor(private readonly docs: DocumentosService, private readonly expediente: ExpedienteService) {}

  @Get('procesos/:id/documentos') listar(@Param('id', ParseUUIDPipe) id: string) { return this.docs.listar(id); }

  @Roles('UNIDAD_SOLICITANTE', 'RESPONSABLE_PRESUPUESTO', 'RESPONSABLE_CONTRATACIONES', 'AUTORIDAD_RPA')
  @Post('procesos/:id/documentos/generar/:tipo') @ApiOperation({ summary: 'Genera (nueva versión) un PDF oficial con marca de agua, SHA-256 y QR' })
  generar(@Param('id', ParseUUIDPipe) id: string, @Param('tipo') tipo: string, @CtxActual() ctx: Ctx) {
    if (!TIPOS_GENERABLES.includes(tipo as TipoGenerable)) throw new BadRequestException(`Tipo no válido. Use uno de: ${TIPOS_GENERABLES.join(', ')}`);
    return this.docs.generar(id, tipo as TipoGenerable, ctx);
  }

  @Roles('UNIDAD_SOLICITANTE', 'RESPONSABLE_PRESUPUESTO', 'RESPONSABLE_CONTRATACIONES', 'AUTORIDAD_RPA')
  @Post('procesos/:id/documentos/subir') @ApiConsumes('multipart/form-data') @UseInterceptors(FileInterceptor('archivo', { limits: { fileSize: 20 * 1024 * 1024, files: 1 } }))
  subir(@Param('id', ParseUUIDPipe) id: string, @Body() dto: SubirDocumentoDto, @UploadedFile() archivo: Express.Multer.File, @CtxActual() ctx: Ctx) { return this.docs.subir(id, dto.tipo, archivo, ctx); }

  @Get('documentos/:id/descargar') @Header('Cache-Control', 'private, no-store')
  async descargar(@Param('id', ParseUUIDPipe) id: string, @Res({ passthrough: true }) res: Response) {
    const { doc, buffer } = await this.docs.leerVerificado(id);
    res.set({ 'Content-Type': 'application/pdf', 'Content-Disposition': `inline; filename="${doc.tipoDocumento}_v${doc.version}.pdf"`, 'X-Content-SHA256': doc.hashSha256 });
    return new StreamableFile(buffer);
  }

  @Roles('RESPONSABLE_CONTRATACIONES', 'AUTORIDAD_RPA')
  @Post('procesos/:id/expediente') @ApiOperation({ summary: 'Compila el Expediente Único foliado con índice, marcadores y sello criptográfico' })
  compilar(@Param('id', ParseUUIDPipe) id: string, @CtxActual() ctx: Ctx) { return this.expediente.generar(id, ctx); }

  /** Verificación pública del QR: sin autenticación, con límite de tasa. */
  @Public() @Throttle({ default: { limit: 30, ttl: 60_000 } }) @Get('verificar/:hash')
  verificar(@Param('hash') hash: string) { return this.docs.verificar(hash); }
}
