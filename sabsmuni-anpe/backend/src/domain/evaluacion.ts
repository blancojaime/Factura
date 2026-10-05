import { aCentavos, deCentavos, redondear2, sumaExacta } from './money';
import { CategoriaProponente, TipoObjeto } from './garantia';

export type MetodoSeleccion = 'PRECIO_EVALUADO_MAS_BAJO' | 'CALIDAD_PROPUESTA_COSTO';

/** Márgenes de preferencia por defecto (%). Parametrizables por entidad. */
export const MARGENES_DEFECTO: Record<CategoriaProponente, number> = {
  NACIONAL_GENERAL: 10,
  MYPE_APP_OECA: 18,
  EXTRANJERO: 0,
};

/** Documentos del Formulario V-1 (verificación legal/administrativa) — criterio Presentó / No Presentó. */
export const V1_ITEMS: { codigo: string; descripcion: string }[] = [
  { codigo: 'V1-01', descripcion: 'Formulario A-1 · Presentación de Propuesta y Declaración Jurada' },
  { codigo: 'V1-02', descripcion: 'Formulario A-2 · Identificación del Proponente' },
  { codigo: 'V1-03', descripcion: 'Certificado de inscripción RUPE vigente' },
  { codigo: 'V1-04', descripcion: 'Propuesta económica (Formulario B-1)' },
  { codigo: 'V1-05', descripcion: 'Especificaciones técnicas / Propuesta técnica ofertada (Formulario C-1)' },
  { codigo: 'V1-06', descripcion: 'Garantía de Seriedad de Propuesta (cuando el DBC la exija)' },
];

export interface PropuestaEvaluable {
  id: string;
  nitProveedor: string;
  razonSocial: string;
  montoOfertado: number;
  /** Precio final tras la Subasta Electrónica (Obras y Servicios). */
  montoSubasta?: number | null;
  plazoDias: number;
  categoria: CategoriaProponente;
  /** codigo V-1 → presentó. Un código ausente cuenta como "No presentó". */
  v1: Record<string, boolean | undefined>;
  /** 0-100, solo para Calidad, Propuesta Técnica y Costo. */
  puntajeTecnico?: number | null;
  /** Orden de presentación (criterio final de desempate). */
  orden: number;
}

export interface OpcionesEvaluacion {
  margenes?: Partial<Record<CategoriaProponente, number>>;
  itemsV1?: { codigo: string; descripcion: string }[];
  /** Si true, las ofertas sobre el precio referencial se declaran no calificadas. */
  rechazarSobrePrecioReferencial?: boolean;
  /** Solo CPC. */
  pesoTecnico?: number;
  pesoEconomico?: number;
  umbralTecnico?: number;
}

export type EstadoEvaluacion = 'CALIFICA' | 'NO_CALIFICA';

export interface FilaEvaluacion {
  propuestaId: string;
  nitProveedor: string;
  razonSocial: string;
  montoOfertado: number;
  montoSubasta: number | null;
  precioFinal: number;
  margenPreferenciaPct: number;
  /** Precio de comparación = precio final reducido por el margen de preferencia. */
  precioComparacion: number;
  diferenciaVsReferencialPct: number;
  plazoDias: number;
  v1Califica: boolean;
  v1Faltantes: string[];
  puntajeTecnico: number | null;
  puntajeEconomico: number | null;
  puntajeTotal: number | null;
  estado: EstadoEvaluacion;
  motivos: string[];
  posicion: number | null;
}

export interface ResultadoEvaluacion {
  metodo: MetodoSeleccion;
  precioReferencial: number;
  filas: FilaEvaluacion[];
  recomendadaId: string | null;
  desierto: boolean;
  motivoDesierto: string | null;
  requiereDesempate: boolean;
  estadisticas: { ofertasRecibidas: number; ofertasCalificadas: number; menorPrecioFinal: number | null; mayorPrecioFinal: number | null; promedioPrecioFinal: number | null };
  observaciones: string[];
}

export function verificarV1(v1: Record<string, boolean | undefined>, items = V1_ITEMS) {
  const faltantes = items.filter((i) => v1[i.codigo] !== true).map((i) => i.codigo);
  return { califica: faltantes.length === 0, faltantes };
}

/** Precio de comparación: monto × (1 − margen%). El monto adjudicado sigue siendo el ofertado. */
export function aplicarMargenPreferencia(monto: number, margenPct: number): number {
  if (margenPct < 0 || margenPct >= 100) throw new Error('El margen de preferencia debe estar en [0, 100).');
  return deCentavos(Math.round((aCentavos(monto) * (100 - margenPct)) / 100));
}

export function evaluarPropuestas(
  tipoObjeto: TipoObjeto,
  metodo: MetodoSeleccion,
  precioReferencial: number,
  propuestas: PropuestaEvaluable[],
  opc: OpcionesEvaluacion = {},
): ResultadoEvaluacion {
  const margenes = { ...MARGENES_DEFECTO, ...opc.margenes };
  const pesoT = opc.pesoTecnico ?? 0.7;
  const pesoE = opc.pesoEconomico ?? 0.3;
  const umbral = opc.umbralTecnico ?? 70;
  if (metodo === 'CALIDAD_PROPUESTA_COSTO' && Math.abs(pesoT + pesoE - 1) > 1e-9) throw new Error('Los pesos técnico y económico deben sumar 1.');
  const observaciones: string[] = [];

  const filas: FilaEvaluacion[] = propuestas.map((p) => {
    const motivos: string[] = [];
    const v1 = verificarV1(p.v1, opc.itemsV1);
    if (!v1.califica) motivos.push(`No presentó: ${v1.faltantes.join(', ')}`);

    if (!(p.montoOfertado > 0)) motivos.push('Monto ofertado inválido.');
    let precioFinal = p.montoOfertado;
    if (p.montoSubasta != null) {
      if (tipoObjeto === 'BIENES') motivos.push('La subasta electrónica solo aplica a Obras y Servicios.');
      else if (p.montoSubasta > p.montoOfertado) motivos.push('El monto de subasta no puede superar la oferta inicial.');
      else if (!(p.montoSubasta > 0)) motivos.push('Monto de subasta inválido.');
      else precioFinal = p.montoSubasta;
    }
    if (precioFinal > precioReferencial) {
      const msg = 'La oferta supera el precio referencial.';
      if (opc.rechazarSobrePrecioReferencial) motivos.push(msg);
      else observaciones.push(`${p.razonSocial}: ${msg} Requiere certificación presupuestaria adicional.`);
    }
    if (!(p.plazoDias > 0)) motivos.push('Plazo de entrega/ejecución inválido.');

    const margen = margenes[p.categoria] ?? 0;
    const precioComparacion = aplicarMargenPreferencia(precioFinal, margen);

    let puntajeTecnico: number | null = null;
    if (metodo === 'CALIDAD_PROPUESTA_COSTO') {
      if (p.puntajeTecnico == null || p.puntajeTecnico < 0 || p.puntajeTecnico > 100) motivos.push('Falta puntaje técnico válido (0-100).');
      else if (p.puntajeTecnico < umbral) motivos.push(`Puntaje técnico ${p.puntajeTecnico} menor al umbral ${umbral}.`);
      puntajeTecnico = p.puntajeTecnico ?? null;
    }

    return {
      propuestaId: p.id,
      nitProveedor: p.nitProveedor,
      razonSocial: p.razonSocial,
      montoOfertado: p.montoOfertado,
      montoSubasta: p.montoSubasta ?? null,
      precioFinal,
      margenPreferenciaPct: margen,
      precioComparacion,
      diferenciaVsReferencialPct: redondear2(((precioFinal - precioReferencial) / precioReferencial) * 100),
      plazoDias: p.plazoDias,
      v1Califica: v1.califica,
      v1Faltantes: v1.faltantes,
      puntajeTecnico,
      puntajeEconomico: null,
      puntajeTotal: null,
      estado: motivos.length ? 'NO_CALIFICA' : 'CALIFICA',
      motivos,
      posicion: null,
    } as FilaEvaluacion;
  });

  const ordenDe = new Map(propuestas.map((p) => [p.id, p.orden]));
  const calificadas = filas.filter((f) => f.estado === 'CALIFICA');

  if (metodo === 'CALIDAD_PROPUESTA_COSTO' && calificadas.length) {
    const minimo = Math.min(...calificadas.map((f) => f.precioComparacion));
    for (const f of calificadas) {
      f.puntajeEconomico = redondear2((100 * minimo) / f.precioComparacion);
      f.puntajeTotal = redondear2(pesoT * (f.puntajeTecnico as number) + pesoE * f.puntajeEconomico);
    }
  }

  const comparador = (a: FilaEvaluacion, b: FilaEvaluacion): number => {
    if (metodo === 'CALIDAD_PROPUESTA_COSTO' && a.puntajeTotal !== b.puntajeTotal) return (b.puntajeTotal as number) - (a.puntajeTotal as number);
    if (metodo === 'PRECIO_EVALUADO_MAS_BAJO' && a.precioComparacion !== b.precioComparacion) return a.precioComparacion - b.precioComparacion;
    if (a.plazoDias !== b.plazoDias) return a.plazoDias - b.plazoDias;
    return (ordenDe.get(a.propuestaId) as number) - (ordenDe.get(b.propuestaId) as number);
  };
  calificadas.sort(comparador).forEach((f, i) => (f.posicion = i + 1));

  let requiereDesempate = false;
  if (calificadas.length > 1) {
    const [a, b] = calificadas;
    const mismoPuntaje = metodo === 'CALIDAD_PROPUESTA_COSTO' ? a.puntajeTotal === b.puntajeTotal : a.precioComparacion === b.precioComparacion;
    requiereDesempate = mismoPuntaje && a.plazoDias === b.plazoDias;
    if (requiereDesempate) observaciones.push('Empate en puntaje/precio y plazo entre las dos primeras posiciones: se aplicó el orden de presentación; la Comisión debe ratificarlo conforme al DBC.');
  }

  // Orden de salida: calificadas por posición y luego las no calificadas.
  const ordenadas = [...calificadas, ...filas.filter((f) => f.estado !== 'CALIFICA')];
  const precios = filas.map((f) => f.precioFinal);
  const desierto = calificadas.length === 0;
  return {
    metodo,
    precioReferencial,
    filas: ordenadas,
    recomendadaId: desierto ? null : calificadas[0].propuestaId,
    desierto,
    motivoDesierto: desierto ? (propuestas.length === 0 ? 'No se recibieron propuestas.' : 'Ninguna propuesta cumplió los requisitos de calificación.') : null,
    requiereDesempate,
    estadisticas: {
      ofertasRecibidas: propuestas.length,
      ofertasCalificadas: calificadas.length,
      menorPrecioFinal: precios.length ? Math.min(...precios) : null,
      mayorPrecioFinal: precios.length ? Math.max(...precios) : null,
      promedioPrecioFinal: precios.length ? deCentavos(Math.round(precios.reduce((a, p) => a + aCentavos(p), 0) / precios.length)) : null,
    },
    observaciones,
  };
}

/** Estructura tabular lista para UI y PDF (Cuadro Comparativo de Ofertas). */
export function cuadroComparativo(r: ResultadoEvaluacion) {
  const columnas = ['Pos.', 'Proponente', 'NIT', 'Oferta inicial', 'Subasta', 'Precio final', 'Margen %', 'Precio comparación', 'Dif. vs ref. %', 'Plazo (días)', 'V-1', 'Estado'];
  if (r.metodo === 'CALIDAD_PROPUESTA_COSTO') columnas.splice(11, 0, 'Pt. técnico', 'Pt. económico', 'Pt. total');
  const filas = r.filas.map((f) => {
    const base: (string | number)[] = [f.posicion ?? '—', f.razonSocial, f.nitProveedor, f.montoOfertado, f.montoSubasta ?? '—', f.precioFinal, f.margenPreferenciaPct, f.precioComparacion, f.diferenciaVsReferencialPct, f.plazoDias, f.v1Califica ? 'Presentó' : 'No presentó'];
    if (r.metodo === 'CALIDAD_PROPUESTA_COSTO') base.push(f.puntajeTecnico ?? '—', f.puntajeEconomico ?? '—', f.puntajeTotal ?? '—');
    base.push(f.estado === 'CALIFICA' ? 'Califica' : 'No califica');
    return base;
  });
  return { columnas, filas, totalOfertado: sumaExacta(r.filas.map((f) => f.precioFinal)) };
}
