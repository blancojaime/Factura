/**
 * Calendario hábil de Bolivia. Las fechas viajan como cadenas ISO 'YYYY-MM-DD'
 * y se operan siempre en UTC para eliminar errores de zona horaria.
 *
 * Feriados nacionales incluidos (Ley 1180 y normas conexas):
 *  1 ene Año Nuevo · 22 ene Día del Estado Plurinacional · Lunes y Martes de Carnaval
 *  · Viernes Santo · 1 may Día del Trabajo · Corpus Christi · 21 jun Año Nuevo Andino
 *  Amazónico · 6 ago Día de la Patria · 2 nov Todos Santos · 25 dic Navidad.
 * Feriados departamentales/municipales o decretados ad hoc se inyectan con `extras`
 * (tabla `feriados` de la base de datos), porque cambian por decreto.
 */
export type FechaISO = string;

export interface Feriado {
  fecha: FechaISO;
  nombre: string;
}

const MS_DIA = 86_400_000;

export const parseFecha = (f: FechaISO): Date => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(f);
  if (!m) throw new Error(`Fecha inválida (se espera YYYY-MM-DD): ${f}`);
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  if (d.getUTCMonth() !== +m[2] - 1) throw new Error(`Fecha inexistente: ${f}`);
  return d;
};
export const formatFecha = (d: Date): FechaISO => d.toISOString().slice(0, 10);
export const sumarDiasCalendario = (f: FechaISO, n: number): FechaISO =>
  formatFecha(new Date(parseFecha(f).getTime() + n * MS_DIA));
export const diaSemana = (f: FechaISO): number => parseFecha(f).getUTCDay(); // 0=domingo

/** Domingo de Pascua (algoritmo anónimo gregoriano). */
export function pascua(anio: number): FechaISO {
  const a = anio % 19;
  const b = Math.floor(anio / 100);
  const c = anio % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31);
  const dia = ((h + l - 7 * m + 114) % 31) + 1;
  return formatFecha(new Date(Date.UTC(anio, mes - 1, dia)));
}

export function feriadosNacionales(anio: number): Feriado[] {
  const p = pascua(anio);
  const fijo = (mm: string, dd: string) => `${anio}-${mm}-${dd}`;
  return [
    { fecha: fijo('01', '01'), nombre: 'Año Nuevo' },
    { fecha: fijo('01', '22'), nombre: 'Día del Estado Plurinacional' },
    { fecha: sumarDiasCalendario(p, -48), nombre: 'Lunes de Carnaval' },
    { fecha: sumarDiasCalendario(p, -47), nombre: 'Martes de Carnaval' },
    { fecha: sumarDiasCalendario(p, -2), nombre: 'Viernes Santo' },
    { fecha: fijo('05', '01'), nombre: 'Día del Trabajo' },
    { fecha: sumarDiasCalendario(p, 60), nombre: 'Corpus Christi' },
    { fecha: fijo('06', '21'), nombre: 'Año Nuevo Andino Amazónico' },
    { fecha: fijo('08', '06'), nombre: 'Día de la Patria' },
    { fecha: fijo('11', '02'), nombre: 'Día de Todos Santos' },
    { fecha: fijo('12', '25'), nombre: 'Navidad' },
  ];
}

export class CalendarioBolivia {
  private readonly extras = new Map<FechaISO, string>();
  private readonly cache = new Map<number, Map<FechaISO, string>>();

  constructor(extras: Feriado[] = []) {
    extras.forEach((f) => this.extras.set(f.fecha, f.nombre));
  }

  private delAnio(anio: number): Map<FechaISO, string> {
    let m = this.cache.get(anio);
    if (!m) {
      m = new Map(feriadosNacionales(anio).map((f) => [f.fecha, f.nombre]));
      this.cache.set(anio, m);
    }
    return m;
  }

  nombreFeriado(f: FechaISO): string | undefined {
    return this.extras.get(f) ?? this.delAnio(parseFecha(f).getUTCFullYear()).get(f);
  }
  esFeriado(f: FechaISO): boolean {
    return this.nombreFeriado(f) !== undefined;
  }
  esFinDeSemana(f: FechaISO): boolean {
    const d = diaSemana(f);
    return d === 0 || d === 6;
  }
  esHabil(f: FechaISO): boolean {
    return !this.esFinDeSemana(f) && !this.esFeriado(f);
  }
  /** Motivo por el que una fecha no es hábil (para mensajes de validación). */
  motivoInhabil(f: FechaISO): string | null {
    if (this.esFinDeSemana(f)) return diaSemana(f) === 0 ? 'domingo' : 'sábado';
    return this.nombreFeriado(f) ?? null;
  }
  /** Primer día hábil igual o posterior a `f`. */
  proximoHabil(f: FechaISO): FechaISO {
    let c = f;
    while (!this.esHabil(c)) c = sumarDiasCalendario(c, 1);
    return c;
  }
  /** Suma `n` días hábiles; el día de partida no se cuenta (el día 1 es el siguiente hábil). */
  sumarDiasHabiles(f: FechaISO, n: number): FechaISO {
    if (!Number.isInteger(n) || n < 0) throw new Error('Los días hábiles deben ser un entero >= 0');
    let c = f;
    let restantes = n;
    while (restantes > 0) {
      c = sumarDiasCalendario(c, 1);
      if (this.esHabil(c)) restantes--;
    }
    return c;
  }
  /** Días hábiles transcurridos después de `desde` hasta `hasta` inclusive. */
  contarDiasHabiles(desde: FechaISO, hasta: FechaISO): number {
    if (hasta < desde) return -this.contarDiasHabiles(hasta, desde);
    let n = 0;
    let c = desde;
    while (c < hasta) {
      c = sumarDiasCalendario(c, 1);
      if (this.esHabil(c)) n++;
    }
    return n;
  }
}
