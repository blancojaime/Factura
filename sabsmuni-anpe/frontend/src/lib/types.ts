export type Rol = 'UNIDAD_SOLICITANTE' | 'RESPONSABLE_PRESUPUESTO' | 'RESPONSABLE_CONTRATACIONES' | 'AUTORIDAD_RPA' | 'ADMINISTRADOR_SISTEMA';
export interface Usuario { id: string; email: string; rol: Rol; nombre?: string }
export const ROL_ETIQUETA: Record<Rol, string> = {
  UNIDAD_SOLICITANTE: 'Unidad Solicitante', RESPONSABLE_PRESUPUESTO: 'Resp. de Presupuesto', RESPONSABLE_CONTRATACIONES: 'Resp. de Contrataciones / Comisión', AUTORIDAD_RPA: 'Autoridad RPA', ADMINISTRADOR_SISTEMA: 'Administrador',
};

export interface Item { id: string; numero: number; codigoUnspsc: string; partidaGasto: string; descripcionTecnica: string; unidadMedida: string; cantidad: number; precioUnitario: number; precioTotal: number; requiereExcepcionChb: boolean; resultadoChb: string | null; incompatibilidadTecnica: string | null }
export interface Propuesta { id: string; orden: number; nitProveedor: string; razonSocial: string; categoria: string; montoOfertado: number; montoSubasta: number | null; plazoDias: number; puntajeTecnico: number | null; v1: Record<string, boolean>; califica_v1: boolean; margenProboliviaMype: number }
export interface Transicion { hacia: string; permitido: boolean; motivos: string[] }
export interface Proceso {
  id: string; codigo: string; cuceProvisorio: string; objetoContratacion: string; tipoObjeto: 'BIENES' | 'SERVICIOS' | 'OBRAS'; metodoSeleccion: string; precioReferencialTotal: number;
  estadoFlujo: string; plazoEjecucionDias: number | null; requerimiento: Record<string, string> | null; evaluacion: Evaluacion | null; propuestaAdjudicadaId: string | null; resolucionObs: string | null;
  items: Item[]; propuestas: Propuesta[]; contrato: Record<string, unknown> | null; cronograma: Record<string, string> | null; certificaciones: unknown[];
  solicitante: { nombre: string } | null; secciones: { clave: string; titulo: string; ayuda: string }[]; transiciones: Transicion[];
}
export interface FilaEvaluacion { propuestaId: string; nitProveedor: string; razonSocial: string; montoOfertado: number; montoSubasta: number | null; precioFinal: number; margenPreferenciaPct: number; precioComparacion: number; diferenciaVsReferencialPct: number; plazoDias: number; v1Califica: boolean; v1Faltantes: string[]; puntajeTecnico: number | null; puntajeEconomico: number | null; puntajeTotal: number | null; estado: 'CALIFICA' | 'NO_CALIFICA'; motivos: string[]; posicion: number | null }
export interface Evaluacion { metodo: string; filas: FilaEvaluacion[]; recomendadaId: string | null; desierto: boolean; motivoDesierto: string | null; requiereDesempate: boolean; observaciones: string[]; estadisticas: { ofertasRecibidas: number; ofertasCalificadas: number } }
export interface Documento { id: string; tipoDocumento: string; version: number; hashSha256: string; hashContenido: string | null; generado: boolean; paginas: number | null; creadoEn: string }
export interface Hallazgo { tipo: string; severidad: 'BLOQUEANTE' | 'ADVERTENCIA'; fragmento: string; sugerencia: string; origen?: string }
