import { porcentajeDe } from './money';

export type TipoObjeto = 'BIENES' | 'SERVICIOS' | 'OBRAS';
export type TipoInstrumento = 'CONTRATO' | 'ORDEN_COMPRA' | 'ORDEN_SERVICIO';
export type CategoriaProponente = 'NACIONAL_GENERAL' | 'MYPE_APP_OECA' | 'EXTRANJERO';

export const GARANTIA_GENERAL_PCT = 7;
export const GARANTIA_MYPE_PCT = 3.5;
export const LIMITE_ORDEN_DIAS_CALENDARIO = 15;

export interface GarantiaCumplimiento {
  porcentaje: number;
  monto: number;
  modalidades: string[];
}

/** Garantía de Cumplimiento de Contrato: 7% general, 3,5% para MyPE/APP/OECA. */
export function calcularGarantiaCumplimiento(montoContrato: number, categoria: CategoriaProponente): GarantiaCumplimiento {
  if (!(montoContrato > 0)) throw new Error('El monto del contrato debe ser mayor a cero.');
  const porcentaje = categoria === 'MYPE_APP_OECA' ? GARANTIA_MYPE_PCT : GARANTIA_GENERAL_PCT;
  return {
    porcentaje,
    monto: porcentajeDe(montoContrato, porcentaje),
    modalidades: ['Boleta de Garantía', 'Póliza de Seguro de Caución a Primer Requerimiento', 'Retención de pagos parciales (si el DBC lo admite)'],
  };
}

/**
 * Plazo ≤ 15 días calendario → Orden de Compra (bienes) / Orden de Servicio (servicios).
 * Las obras siempre se formalizan mediante Contrato.
 */
export function tipoInstrumentoContractual(tipoObjeto: TipoObjeto, plazoDiasCalendario: number): TipoInstrumento {
  if (!Number.isInteger(plazoDiasCalendario) || plazoDiasCalendario <= 0) throw new Error('El plazo debe ser un entero positivo de días calendario.');
  if (tipoObjeto === 'OBRAS' || plazoDiasCalendario > LIMITE_ORDEN_DIAS_CALENDARIO) return 'CONTRATO';
  return tipoObjeto === 'BIENES' ? 'ORDEN_COMPRA' : 'ORDEN_SERVICIO';
}
