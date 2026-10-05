import { Type } from 'class-transformer';
import { ArrayMaxSize, IsArray, IsBoolean, IsDateString, IsEnum, IsInt, IsNotEmpty, IsNumber, IsObject, IsOptional, IsString, Matches, Max, MaxLength, Min, MinLength, ValidateNested } from 'class-validator';
import { CategoriaProponente, MetodoSeleccion, TipoDocumento, TipoObjeto } from '@prisma/client';

export class CrearProcesoDto {
  @IsString() @MinLength(10) @MaxLength(500) objetoContratacion!: string;
  @IsEnum(TipoObjeto) tipoObjeto!: TipoObjeto;
  @IsEnum(MetodoSeleccion) metodoSeleccion!: MetodoSeleccion;
  @IsOptional() @IsInt() @Min(1) @Max(1500) plazoEjecucionDias?: number;
}
export class ActualizarProcesoDto {
  @IsOptional() @IsString() @MinLength(10) @MaxLength(500) objetoContratacion?: string;
  @IsOptional() @IsEnum(TipoObjeto) tipoObjeto?: TipoObjeto;
  @IsOptional() @IsEnum(MetodoSeleccion) metodoSeleccion?: MetodoSeleccion;
  @IsOptional() @IsInt() @Min(1) @Max(1500) plazoEjecucionDias?: number;
  @IsOptional() @IsString() @MaxLength(60) cuceProvisorio?: string;
}
export class ItemDto {
  /** Código UNSPSC de 8 dígitos */
  @Matches(/^\d{8}$/, { message: 'El código UNSPSC debe tener 8 dígitos' }) codigoUnspsc!: string;
  @Matches(/^\d{5}$/, { message: 'La partida de gasto debe tener 5 dígitos' }) partidaGasto!: string;
  @IsString() @MinLength(5) @MaxLength(2000) descripcionTecnica!: string;
  @IsString() @IsNotEmpty() @MaxLength(30) unidadMedida!: string;
  @IsNumber({ maxDecimalPlaces: 3 }) @Min(0.001) cantidad!: number;
  @IsNumber({ maxDecimalPlaces: 2 }) @Min(0.01) precioUnitario!: number;
  @IsOptional() @IsString() @MaxLength(1000) incompatibilidadTecnica?: string;
  @IsOptional() @IsString() fichaChbId?: string;
}
export class ActualizarItemDto {
  @IsOptional() @Matches(/^\d{8}$/) codigoUnspsc?: string;
  @IsOptional() @Matches(/^\d{5}$/) partidaGasto?: string;
  @IsOptional() @IsString() @MinLength(5) @MaxLength(2000) descripcionTecnica?: string;
  @IsOptional() @IsString() @MaxLength(30) unidadMedida?: string;
  @IsOptional() @IsNumber({ maxDecimalPlaces: 3 }) @Min(0.001) cantidad?: number;
  @IsOptional() @IsNumber({ maxDecimalPlaces: 2 }) @Min(0.01) precioUnitario?: number;
  @IsOptional() @IsString() @MaxLength(1000) incompatibilidadTecnica?: string;
  @IsOptional() @IsString() fichaChbId?: string;
}
export class RequerimientoDto {
  /** {clave de sección: texto} según el asistente del tipo de objeto */
  @IsObject() secciones!: Record<string, string>;
}
export class AnalizarTextoDto { @IsString() @MaxLength(20000) texto!: string }
export class CalcularCronogramaDto {
  @IsDateString({ strict: true }) fechaPublicacion!: string;
  @IsOptional() @IsDateString({ strict: true }) fechaApertura?: string;
  @IsOptional() @IsNumber() @Min(50001) precioReferencial?: number;
}
export class LineaPresupuestoDto {
  @IsString() da!: string; @IsString() ue!: string; @IsString() programa!: string; @IsString() proyecto!: string;
  @IsString() actividadObra!: string; @IsString() fuente!: string; @IsString() organismo!: string; @IsString() partida!: string;
  @IsNumber({ maxDecimalPlaces: 2 }) @Min(0.01) importe!: number;
}
export class PresupuestoDto {
  @IsArray() @ArrayMaxSize(50) @ValidateNested({ each: true }) @Type(() => LineaPresupuestoDto) lineas!: LineaPresupuestoDto[];
  @IsOptional() @IsString() @MaxLength(30) c31PreventivoNumero?: string;
}
export class PropuestaDto {
  @Matches(/^\d{6,15}$/, { message: 'NIT inválido (6 a 15 dígitos)' }) nitProveedor!: string;
  @IsString() @MinLength(3) @MaxLength(200) razonSocial!: string;
  @IsEnum(CategoriaProponente) categoria!: CategoriaProponente;
  @IsNumber({ maxDecimalPlaces: 2 }) @Min(0.01) montoOfertado!: number;
  @IsOptional() @IsNumber({ maxDecimalPlaces: 2 }) @Min(0.01) montoSubasta?: number;
  @IsInt() @Min(1) @Max(1500) plazoDias!: number;
  @IsOptional() @IsNumber() @Min(0) @Max(100) puntajeTecnico?: number;
}
export class ActualizarPropuestaDto {
  @IsOptional() @IsString() @MinLength(3) razonSocial?: string;
  @IsOptional() @IsEnum(CategoriaProponente) categoria?: CategoriaProponente;
  @IsOptional() @IsNumber({ maxDecimalPlaces: 2 }) @Min(0.01) montoOfertado?: number;
  @IsOptional() @IsNumber({ maxDecimalPlaces: 2 }) @Min(0.01) montoSubasta?: number;
  @IsOptional() @IsInt() @Min(1) plazoDias?: number;
  @IsOptional() @IsNumber() @Min(0) @Max(100) puntajeTecnico?: number;
}
export class V1Dto { @IsObject() v1!: Record<string, boolean> }
export class TransicionDto {
  @IsString() hacia!: string;
  @IsOptional() @IsString() @MaxLength(1000) observacion?: string;
  /** Solo en la adjudicación: si difiere de la recomendada, la observación es obligatoria. */
  @IsOptional() @IsString() propuestaId?: string;
}
export class ContratoDto {
  @IsDateString({ strict: true }) fechaFirma!: string;
  @IsOptional() @IsInt() @Min(1) plazoDias?: number;
  @IsOptional() @IsString() @MaxLength(40) numero?: string;
  @IsOptional() @IsString() @MaxLength(100) garantiaInstrumento?: string;
  @IsOptional() @IsString() @MaxLength(60) polizaNumero?: string;
  @IsOptional() @IsString() @MaxLength(120) polizaEntidad?: string;
  @IsOptional() @IsDateString({ strict: true }) polizaVigenciaHasta?: string;
}
export class RecepcionDto {
  @IsDateString({ strict: true }) fechaRecepcion!: string;
  @IsOptional() @IsString() @MaxLength(1000) observacion?: string;
}
export class SubirDocumentoDto { @IsEnum(TipoDocumento) tipo!: TipoDocumento }
export class GenerarOpcionesDto { @IsOptional() @IsBoolean() regenerar?: boolean }
