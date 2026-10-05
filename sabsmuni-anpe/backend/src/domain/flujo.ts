export type Rol = 'UNIDAD_SOLICITANTE' | 'RESPONSABLE_PRESUPUESTO' | 'RESPONSABLE_CONTRATACIONES' | 'AUTORIDAD_RPA' | 'ADMINISTRADOR_SISTEMA';

export type EstadoFlujo =
  | 'BORRADOR' | 'REQUERIMIENTO_VALIDADO' | 'PRESUPUESTO_CERTIFICADO' | 'DBC_ELABORADO' | 'DBC_APROBADO' | 'PUBLICADO'
  | 'EVALUACION' | 'RECOMENDACION_EMITIDA' | 'ADJUDICADO' | 'DESIERTO' | 'CONTRATO_FORMALIZADO' | 'RECEPCION' | 'LIQUIDADO' | 'CANCELADO';

/** Precondiciones calculadas por el servicio a partir de la base de datos. */
export interface ContextoFlujo {
  itemsCargados: boolean;
  requerimientoValido: boolean;       // ET sin hallazgos bloqueantes y completa
  excepcionesChbJustificadas: boolean;
  c31Valido: boolean;
  cronogramaValido: boolean;
  documentoDbcGenerado: boolean;
  evaluacionRealizada: boolean;
  hayRecomendacion: boolean;
  contratoGenerado: boolean;
  actaRecepcionGenerada: boolean;
}

interface Regla { desde: EstadoFlujo; hacia: EstadoFlujo; roles: Rol[]; requiere?: { campo: keyof ContextoFlujo; mensaje: string }[] }

const RC: Rol = 'RESPONSABLE_CONTRATACIONES', RPA: Rol = 'AUTORIDAD_RPA', RP: Rol = 'RESPONSABLE_PRESUPUESTO', US: Rol = 'UNIDAD_SOLICITANTE';

export const REGLAS: Regla[] = [
  { desde: 'BORRADOR', hacia: 'REQUERIMIENTO_VALIDADO', roles: [US], requiere: [
    { campo: 'itemsCargados', mensaje: 'Cargue al menos un ítem.' },
    { campo: 'requerimientoValido', mensaje: 'La especificación técnica/TdR tiene hallazgos bloqueantes o está incompleta.' },
    { campo: 'excepcionesChbJustificadas', mensaje: 'Hay ítems sin validar contra el catálogo CHB o sin su formulario de justificación de insuficiencia técnica.' } ] },
  { desde: 'REQUERIMIENTO_VALIDADO', hacia: 'BORRADOR', roles: [RP, RC] },
  { desde: 'REQUERIMIENTO_VALIDADO', hacia: 'PRESUPUESTO_CERTIFICADO', roles: [RP], requiere: [{ campo: 'c31Valido', mensaje: 'La certificación presupuestaria no cuadra aritméticamente con los ítems.' }] },
  { desde: 'PRESUPUESTO_CERTIFICADO', hacia: 'DBC_ELABORADO', roles: [RC], requiere: [
    { campo: 'cronogramaValido', mensaje: 'El cronograma no cumple los plazos del Art. 47 D.S. 0181.' },
    { campo: 'documentoDbcGenerado', mensaje: 'Genere el DBC antes de enviarlo a aprobación.' } ] },
  { desde: 'DBC_ELABORADO', hacia: 'PRESUPUESTO_CERTIFICADO', roles: [RPA] },
  { desde: 'DBC_ELABORADO', hacia: 'DBC_APROBADO', roles: [RPA] },
  { desde: 'DBC_APROBADO', hacia: 'PUBLICADO', roles: [RC] },
  { desde: 'PUBLICADO', hacia: 'EVALUACION', roles: [RC] },
  { desde: 'EVALUACION', hacia: 'RECOMENDACION_EMITIDA', roles: [RC], requiere: [{ campo: 'evaluacionRealizada', mensaje: 'Ejecute la evaluación de propuestas.' }] },
  { desde: 'RECOMENDACION_EMITIDA', hacia: 'ADJUDICADO', roles: [RPA], requiere: [{ campo: 'hayRecomendacion', mensaje: 'No hay propuesta recomendada para adjudicar.' }] },
  { desde: 'RECOMENDACION_EMITIDA', hacia: 'DESIERTO', roles: [RPA] },
  { desde: 'DESIERTO', hacia: 'PRESUPUESTO_CERTIFICADO', roles: [RC] }, // nueva convocatoria: reprogramar cronograma
  { desde: 'ADJUDICADO', hacia: 'CONTRATO_FORMALIZADO', roles: [RPA], requiere: [{ campo: 'contratoGenerado', mensaje: 'Genere el contrato u orden antes de formalizar.' }] },
  { desde: 'CONTRATO_FORMALIZADO', hacia: 'RECEPCION', roles: [RC], requiere: [{ campo: 'actaRecepcionGenerada', mensaje: 'Genere el Acta de Recepción.' }] },
  { desde: 'RECEPCION', hacia: 'LIQUIDADO', roles: [RC] },
];

const TERMINALES: EstadoFlujo[] = ['LIQUIDADO', 'CANCELADO'];

export interface ResultadoTransicion { permitido: boolean; motivos: string[] }

export function evaluarTransicion(desde: EstadoFlujo, hacia: EstadoFlujo, rol: Rol, ctx: ContextoFlujo): ResultadoTransicion {
  if (hacia === 'CANCELADO') {
    if (TERMINALES.includes(desde)) return { permitido: false, motivos: [`Un proceso en estado ${desde} no puede cancelarse.`] };
    return rol === RPA ? { permitido: true, motivos: [] } : { permitido: false, motivos: ['Solo la Autoridad RPA puede cancelar un proceso.'] };
  }
  const regla = REGLAS.find((r) => r.desde === desde && r.hacia === hacia);
  if (!regla) return { permitido: false, motivos: [`Transición no permitida: ${desde} → ${hacia}.`] };
  if (!regla.roles.includes(rol)) return { permitido: false, motivos: [`El rol ${rol} no puede ejecutar ${desde} → ${hacia} (requiere: ${regla.roles.join(' / ')}).`] };
  const motivos = (regla.requiere ?? []).filter((q) => !ctx[q.campo]).map((q) => q.mensaje);
  return { permitido: motivos.length === 0, motivos };
}

export const transicionesDesde = (desde: EstadoFlujo): EstadoFlujo[] =>
  [...new Set([...REGLAS.filter((r) => r.desde === desde).map((r) => r.hacia), ...(TERMINALES.includes(desde) ? [] : (['CANCELADO'] as EstadoFlujo[]))])];
