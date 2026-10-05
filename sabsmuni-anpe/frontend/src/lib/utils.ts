import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export const cn = (...i: ClassValue[]) => twMerge(clsx(i));
export const bs = (n: number | null | undefined) => (n == null ? '—' : 'Bs ' + n.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
export const fecha = (iso?: string | null) => (iso ? iso.slice(0, 10).split('-').reverse().join('/') : '—');
const DICCIONARIO: Record<string, string> = {
  BORRADOR: 'Borrador', REQUERIMIENTO_VALIDADO: 'Requerimiento validado', PRESUPUESTO_CERTIFICADO: 'Presupuesto certificado', DBC_ELABORADO: 'DBC elaborado', DBC_APROBADO: 'DBC aprobado',
  PUBLICADO: 'Publicado', EVALUACION: 'Evaluación', RECOMENDACION_EMITIDA: 'Recomendación emitida', ADJUDICADO: 'Adjudicado', DESIERTO: 'Desierto', CONTRATO_FORMALIZADO: 'Contrato formalizado',
  RECEPCION: 'Recepción', LIQUIDADO: 'Liquidado', CANCELADO: 'Cancelado',
  BIENES: 'Bienes', SERVICIOS: 'Servicios', OBRAS: 'Obras', PRECIO_EVALUADO_MAS_BAJO: 'Precio evaluado más bajo', CALIDAD_PROPUESTA_COSTO: 'Calidad, propuesta técnica y costo',
  NACIONAL_GENERAL: 'Nacional (general)', MYPE_APP_OECA: 'MyPE / APP / OECA', EXTRANJERO: 'Extranjero',
  CONTRATO: 'Contrato', ORDEN_COMPRA: 'Orden de compra', ORDEN_SERVICIO: 'Orden de servicio',
  SOLICITUD_C1: 'Solicitud C-1 y ET', JUSTIFICACION_CHB: 'Justificación CHB', PREVENTIVO_C31: 'Preventivo C-31', DBC: 'DBC', INFORME_V1: 'Verificación V-1', CUADRO_COMPARATIVO: 'Cuadro comparativo',
  INFORME_EVALUACION: 'Informe de evaluación', ACTA_ADJUDICACION: 'Resolución de adjudicación', ORDEN_COMPRA_SERVICIO: 'Orden de compra / servicio', ACTA_RECEPCION: 'Acta de recepción',
  DEVENGADO_C31: 'Devengado C-31', EXPEDIENTE_UNICO: 'Expediente único', OTRO: 'Documento adjunto',
  CUBIERTO_POR_CHB: 'Cubierto por CHB', NO_APLICA: 'No aplica', SIMILAR_EN_CHB: 'Similar en CHB', SIN_PRODUCCION_NACIONAL: 'Sin producción nacional', INCOMPATIBLE_CON_CHB: 'Incompatible con CHB',
};
export const etiqueta = (s: string) => DICCIONARIO[s] ?? s.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
