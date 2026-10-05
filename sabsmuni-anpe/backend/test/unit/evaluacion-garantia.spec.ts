import { aplicarMargenPreferencia, cuadroComparativo, evaluarPropuestas, PropuestaEvaluable, V1_ITEMS, verificarV1 } from '../../src/domain/evaluacion';
import { calcularGarantiaCumplimiento, tipoInstrumentoContractual } from '../../src/domain/garantia';
import { montoEnLetras, multiplicar, sumaExacta } from '../../src/domain/money';

const v1Completo = Object.fromEntries(V1_ITEMS.map((i) => [i.codigo, true]));
const p = (id: string, monto: number, extra: Partial<PropuestaEvaluable> = {}): PropuestaEvaluable => ({
  id, nitProveedor: '100' + id, razonSocial: 'Empresa ' + id, montoOfertado: monto, plazoDias: 10, categoria: 'NACIONAL_GENERAL', v1: v1Completo, orden: Number(id.replace(/\D/g, '')) || 1, ...extra,
});

describe('Aritmética monetaria', () => {
  it('suma sin errores de coma flotante', () => {
    expect(sumaExacta([0.1, 0.2])).toBe(0.3);
    expect(multiplicar(3, 19.99)).toBe(59.97);
  });
  it('convierte montos a letras', () => {
    expect(montoEnLetras(180000)).toBe('ciento ochenta mil 00/100 bolivianos');
    expect(montoEnLetras(21000.5)).toBe('veintiún mil 50/100 bolivianos'.replace('veintiún', 'veintiun'));
    expect(montoEnLetras(1_000_000)).toBe('un millón 00/100 bolivianos');
  });
});

describe('Margen de preferencia', () => {
  it('reduce el precio de comparación sin alterar el monto', () => {
    expect(aplicarMargenPreferencia(100_000, 10)).toBe(90_000);
    expect(aplicarMargenPreferencia(100_000, 18)).toBe(82_000);
    expect(aplicarMargenPreferencia(100_000, 0)).toBe(100_000);
  });
  it('valida el rango del margen', () => {
    expect(() => aplicarMargenPreferencia(100, 100)).toThrow();
    expect(() => aplicarMargenPreferencia(100, -1)).toThrow();
  });
});

describe('Formulario V-1', () => {
  it('lista faltantes ("No presentó")', () => {
    expect(verificarV1({ ...v1Completo, 'V1-03': false })).toEqual({ califica: false, faltantes: ['V1-03'] });
    expect(verificarV1(v1Completo).califica).toBe(true);
    expect(verificarV1({}).faltantes).toHaveLength(V1_ITEMS.length);
  });
});

describe('Evaluación — Precio Evaluado Más Bajo', () => {
  it('recomienda el menor precio de comparación considerando margen MyPE', () => {
    const r = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 200_000, [
      p('1', 170_000), // general 10% → 153.000
      p('2', 185_000, { categoria: 'MYPE_APP_OECA' }), // 18% → 151.700  ← gana
      p('3', 160_000, { categoria: 'EXTRANJERO' }), // 0% → 160.000
    ]);
    expect(r.recomendadaId).toBe('2');
    expect(r.filas.map((f) => [f.propuestaId, f.precioComparacion, f.posicion])).toEqual([['2', 151_700, 1], ['1', 153_000, 2], ['3', 160_000, 3]]);
    expect(r.filas[0].montoOfertado).toBe(185_000); // el monto contractual no se reduce
  });
  it('descalifica por V-1 y deja desierto si nadie califica', () => {
    const r = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 100_000, [p('1', 90_000, { v1: { ...v1Completo, 'V1-01': false } })]);
    expect(r.desierto).toBe(true);
    expect(r.recomendadaId).toBeNull();
    expect(r.filas[0].motivos[0]).toMatch(/V1-01/);
  });
  it('declara desierto sin propuestas', () => {
    const r = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 100_000, []);
    expect(r.motivoDesierto).toMatch(/No se recibieron/);
  });
  it('desempata por plazo y luego por orden de presentación', () => {
    const r = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 100_000, [p('1', 80_000, { plazoDias: 12 }), p('2', 80_000, { plazoDias: 9 })]);
    expect(r.recomendadaId).toBe('2');
    expect(r.requiereDesempate).toBe(false);
    const r2 = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 100_000, [p('1', 80_000), p('2', 80_000)]);
    expect(r2.recomendadaId).toBe('1');
    expect(r2.requiereDesempate).toBe(true);
  });
  it('observa ofertas sobre el precio referencial y las rechaza si se configura', () => {
    const o = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 100_000, [p('1', 105_000)]);
    expect(o.filas[0].estado).toBe('CALIFICA');
    expect(o.observaciones[0]).toMatch(/supera el precio referencial/);
    const x = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 100_000, [p('1', 105_000)], { rechazarSobrePrecioReferencial: true });
    expect(x.desierto).toBe(true);
  });
});

describe('Subasta electrónica (Obras y Servicios)', () => {
  it('usa el monto de subasta como precio final', () => {
    const r = evaluarPropuestas('OBRAS', 'PRECIO_EVALUADO_MAS_BAJO', 500_000, [p('1', 450_000, { montoSubasta: 420_000 }), p('2', 430_000, { montoSubasta: 425_000 })]);
    expect(r.recomendadaId).toBe('1');
    expect(r.filas[0].precioFinal).toBe(420_000);
  });
  it('rechaza subasta superior a la oferta y subasta en bienes', () => {
    const a = evaluarPropuestas('OBRAS', 'PRECIO_EVALUADO_MAS_BAJO', 500_000, [p('1', 450_000, { montoSubasta: 460_000 })]);
    expect(a.filas[0].motivos.join()).toMatch(/no puede superar/);
    const b = evaluarPropuestas('BIENES', 'PRECIO_EVALUADO_MAS_BAJO', 500_000, [p('1', 450_000, { montoSubasta: 440_000 })]);
    expect(b.filas[0].motivos.join()).toMatch(/solo aplica a Obras y Servicios/);
  });
});

describe('Evaluación — Calidad, Propuesta Técnica y Costo', () => {
  it('pondera técnica 70% + económica 30% y aplica umbral', () => {
    const r = evaluarPropuestas('SERVICIOS', 'CALIDAD_PROPUESTA_COSTO', 100_000, [
      p('1', 100_000, { puntajeTecnico: 90, categoria: 'EXTRANJERO' }),
      p('2', 80_000, { puntajeTecnico: 80, categoria: 'EXTRANJERO' }),
      p('3', 50_000, { puntajeTecnico: 60, categoria: 'EXTRANJERO' }), // bajo umbral
    ]);
    const f = Object.fromEntries(r.filas.map((x) => [x.propuestaId, x]));
    expect(f['3'].estado).toBe('NO_CALIFICA');
    expect(f['2'].puntajeEconomico).toBe(100);
    expect(f['2'].puntajeTotal).toBe(86); // 0.7*80 + 0.3*100
    expect(f['1'].puntajeEconomico).toBe(80);
    expect(f['1'].puntajeTotal).toBe(87); // 0.7*90 + 0.3*80
    expect(r.recomendadaId).toBe('1');
  });
  it('exige pesos que sumen 1', () => {
    expect(() => evaluarPropuestas('SERVICIOS', 'CALIDAD_PROPUESTA_COSTO', 1, [], { pesoTecnico: 0.5, pesoEconomico: 0.4 })).toThrow();
  });
  it('genera el cuadro comparativo con columnas de puntaje', () => {
    const r = evaluarPropuestas('SERVICIOS', 'CALIDAD_PROPUESTA_COSTO', 100_000, [p('1', 90_000, { puntajeTecnico: 85 })]);
    const c = cuadroComparativo(r);
    expect(c.columnas).toContain('Pt. total');
    expect(c.filas[0]).toHaveLength(c.columnas.length);
  });
});

describe('Garantía de cumplimiento e instrumento contractual', () => {
  it('7% general y 3,5% MyPE exactos', () => {
    expect(calcularGarantiaCumplimiento(180_000, 'NACIONAL_GENERAL')).toMatchObject({ porcentaje: 7, monto: 12_600 });
    expect(calcularGarantiaCumplimiento(180_000, 'MYPE_APP_OECA')).toMatchObject({ porcentaje: 3.5, monto: 6_300 });
    expect(calcularGarantiaCumplimiento(123_456.78, 'NACIONAL_GENERAL').monto).toBe(8_641.97);
  });
  it('orden de compra/servicio para plazos ≤ 15 días calendario', () => {
    expect(tipoInstrumentoContractual('BIENES', 15)).toBe('ORDEN_COMPRA');
    expect(tipoInstrumentoContractual('SERVICIOS', 10)).toBe('ORDEN_SERVICIO');
    expect(tipoInstrumentoContractual('BIENES', 16)).toBe('CONTRATO');
    expect(tipoInstrumentoContractual('OBRAS', 10)).toBe('CONTRATO');
  });
});
