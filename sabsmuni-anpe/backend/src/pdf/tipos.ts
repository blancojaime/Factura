import { CategoriaProponente, TipoInstrumento, TipoObjeto } from '../domain/garantia';
import { MetodoSeleccion, ResultadoEvaluacion } from '../domain/evaluacion';
import { CronogramaAnpe } from '../domain/cronograma';
import { LineaPresupuesto } from '../domain/sigep';
import { JustificacionInsuficiencia } from '../domain/chb';

export type Bloque =
  | { t: 'h'; texto: string }
  | { t: 'p'; texto: string }
  | { t: 'nota'; texto: string }
  | { t: 'kv'; pares: [string, string][] }
  | { t: 'lista'; items: string[] }
  | { t: 'tabla'; columnas: string[]; filas: (string | number)[][]; anchos?: number[]; derecha?: number[] }
  | { t: 'clausula'; titulo: string; texto: string }
  | { t: 'salto' };

export interface DocSpec {
  titulo: string;
  subtitulo?: string;
  formulario?: string;
  horizontal?: boolean;
  bloques: Bloque[];
  firmas?: { cargo: string; nombre?: string }[];
}

export interface MetaPdf {
  entidad: string;
  codigoProceso: string;
  /** Hash del contenido lógico codificado en el QR. */
  hashContenido: string;
  urlVerificacion: string;
  version: number;
  marcaAgua?: string;
}

export interface DatosDoc {
  config: { nombreGam: string; nit: string; da: string; ue: string; ciudad: string; departamento: string; direccion: string; rpaNombre: string; rpaCargo: string };
  proceso: {
    id: string; codigo: string; cuce: string; objeto: string; tipoObjeto: TipoObjeto; metodo: MetodoSeleccion; precioReferencial: number; plazoEjecucionDias: number | null; estado: string;
    requerimiento: Record<string, string>; solicitante: { nombre: string; cargo?: string | null; unidad?: string | null } | null; rpa: { nombre: string; cargo?: string | null } | null;
    resolucionObs: string | null; resolucionFecha: string | null; propuestaAdjudicadaId: string | null;
  };
  items: { numero: number; codigoUnspsc: string; partida: string; descripcion: string; unidad: string; cantidad: number; precioUnitario: number; precioTotal: number; requiereExcepcionChb: boolean; resultadoChb: string | null }[];
  cronograma: CronogramaAnpe | null;
  plazoMinimoDias: number | null;
  certificaciones: (LineaPresupuesto & { c31: string | null })[];
  glosa: string;
  propuestas: { id: string; orden: number; nit: string; razonSocial: string; categoria: CategoriaProponente; monto: number; subasta: number | null; plazoDias: number; v1: Record<string, boolean>; v1Califica: boolean }[];
  evaluacion: ResultadoEvaluacion | null;
  contrato: {
    tipo: TipoInstrumento; numero: string; propuestaId: string; monto: number; plazoDias: number; fechaFirma: string; garantiaPorcentaje: number; garantiaMonto: number;
    garantiaInstrumento: string | null; polizaNumero: string | null; polizaEntidad: string | null; polizaVigenciaHasta: string | null; fechaRecepcion: string | null; observacionRecepcion: string | null;
  } | null;
  justificacionChb: JustificacionInsuficiencia | null;
  marcaAgua?: string;
}
