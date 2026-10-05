import { CalendarioBolivia, FechaISO } from './calendario-bolivia';

/** Rango de cuantías de la modalidad ANPE (Bs). */
export const ANPE_MIN = 50_001;
export const ANPE_MAX = 1_000_000;

export interface PlazosConfig {
  /** Días hábiles entre apertura y adjudicación (parametrizable por entidad en el DBC). */
  diasEvaluacion: number;
  /** Días hábiles para que el adjudicado presente documentos para contrato. */
  diasPresentacionDoc: number;
  /** Días hábiles para la suscripción del contrato/orden tras la presentación. */
  diasFirmaContrato: number;
}
export const PLAZOS_POR_DEFECTO: PlazosConfig = { diasEvaluacion: 2, diasPresentacionDoc: 4, diasFirmaContrato: 3 };

export function validarRangoAnpe(precioReferencial: number): string | null {
  if (!(precioReferencial >= ANPE_MIN && precioReferencial <= ANPE_MAX))
    return `El precio referencial (${precioReferencial}) está fuera del rango ANPE (Bs ${ANPE_MIN} a Bs ${ANPE_MAX}).`;
  return null;
}

/**
 * Art. 47 D.S. 0181 — plazo mínimo (en días hábiles) entre la publicación del DBC
 * y la presentación/apertura de propuestas:
 *   ANPE hasta Bs 200.000 ........ 4 días hábiles
 *   ANPE Bs 200.001 – 1.000.000 .. 8 días hábiles
 */
export function plazoMinimoDiasHabiles(precioReferencial: number): number {
  const err = validarRangoAnpe(precioReferencial);
  if (err) throw new Error(err);
  return precioReferencial <= 200_000 ? 4 : 8;
}

export interface CronogramaAnpe {
  fechaPublicacion: FechaISO;
  fechaApertura: FechaISO;
  fechaAdjudicacion: FechaISO;
  fechaPresentacionDoc: FechaISO;
  fechaContrato: FechaISO;
}

export interface ResultadoCronograma {
  cronograma: CronogramaAnpe;
  plazoMinimoDiasHabiles: number;
  diasHabilesPublicacionApertura: number;
}

export interface EntradaCronograma {
  fechaPublicacion: FechaISO;
  precioReferencial: number;
  /** Si se omite, la apertura se fija en el plazo mínimo legal. */
  fechaApertura?: FechaISO;
  plazos?: Partial<PlazosConfig>;
}

export function calcularCronograma(e: EntradaCronograma, cal: CalendarioBolivia): ResultadoCronograma {
  const minimo = plazoMinimoDiasHabiles(e.precioReferencial);
  const p = { ...PLAZOS_POR_DEFECTO, ...e.plazos };
  const motivo = cal.motivoInhabil(e.fechaPublicacion);
  if (motivo) throw new Error(`La fecha de publicación ${e.fechaPublicacion} no es hábil (${motivo}).`);
  const apertura = e.fechaApertura ?? cal.sumarDiasHabiles(e.fechaPublicacion, minimo);
  const adjudicacion = cal.sumarDiasHabiles(apertura, p.diasEvaluacion);
  const presentacion = cal.sumarDiasHabiles(adjudicacion, p.diasPresentacionDoc);
  const contrato = cal.sumarDiasHabiles(presentacion, p.diasFirmaContrato);
  const cronograma: CronogramaAnpe = {
    fechaPublicacion: e.fechaPublicacion,
    fechaApertura: apertura,
    fechaAdjudicacion: adjudicacion,
    fechaPresentacionDoc: presentacion,
    fechaContrato: contrato,
  };
  const errores = validarCronograma(cronograma, e.precioReferencial, cal);
  if (errores.length) throw new Error(errores.join(' '));
  return { cronograma, plazoMinimoDiasHabiles: minimo, diasHabilesPublicacionApertura: cal.contarDiasHabiles(e.fechaPublicacion, apertura) };
}

/** Devuelve la lista de incumplimientos normativos (vacía = cronograma válido). */
export function validarCronograma(c: CronogramaAnpe, precioReferencial: number, cal: CalendarioBolivia): string[] {
  const errores: string[] = [];
  const rango = validarRangoAnpe(precioReferencial);
  if (rango) errores.push(rango);
  const orden: (keyof CronogramaAnpe)[] = ['fechaPublicacion', 'fechaApertura', 'fechaAdjudicacion', 'fechaPresentacionDoc', 'fechaContrato'];
  for (const k of orden) {
    const motivo = cal.motivoInhabil(c[k]);
    if (motivo) errores.push(`${k} (${c[k]}) no es día hábil: ${motivo}.`);
  }
  for (let i = 1; i < orden.length; i++)
    if (c[orden[i]] <= c[orden[i - 1]]) errores.push(`${orden[i]} debe ser posterior a ${orden[i - 1]}.`);
  if (!rango) {
    const min = plazoMinimoDiasHabiles(precioReferencial);
    const real = cal.contarDiasHabiles(c.fechaPublicacion, c.fechaApertura);
    if (real < min)
      errores.push(`Plazo entre publicación y apertura de ${real} día(s) hábil(es); el mínimo según Art. 47 D.S. 0181 es ${min}.`);
  }
  return errores;
}
