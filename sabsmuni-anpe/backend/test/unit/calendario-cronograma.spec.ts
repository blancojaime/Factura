import { CalendarioBolivia, feriadosNacionales, pascua } from '../../src/domain/calendario-bolivia';
import { calcularCronograma, plazoMinimoDiasHabiles, validarCronograma, validarRangoAnpe } from '../../src/domain/cronograma';

describe('Calendario de Bolivia', () => {
  it('calcula el Domingo de Pascua', () => {
    expect(pascua(2024)).toBe('2024-03-31');
    expect(pascua(2025)).toBe('2025-04-20');
    expect(pascua(2026)).toBe('2026-04-05');
  });
  it('deriva los feriados móviles (Carnaval, Viernes Santo, Corpus Christi)', () => {
    const f = Object.fromEntries(feriadosNacionales(2025).map((x) => [x.nombre, x.fecha]));
    expect(f['Lunes de Carnaval']).toBe('2025-03-03');
    expect(f['Martes de Carnaval']).toBe('2025-03-04');
    expect(f['Viernes Santo']).toBe('2025-04-18');
    expect(f['Corpus Christi']).toBe('2025-06-19');
    expect(f['Año Nuevo Andino Amazónico']).toBe('2025-06-21');
  });
  const cal = new CalendarioBolivia();
  it('excluye fines de semana y feriados', () => {
    expect(cal.esHabil('2025-03-03')).toBe(false); // carnaval
    expect(cal.esHabil('2025-03-08')).toBe(false); // sábado
    expect(cal.esHabil('2025-03-05')).toBe(true);
    expect(cal.proximoHabil('2025-03-03')).toBe('2025-03-05');
  });
  it('suma días hábiles sin contar el día de partida', () => {
    expect(cal.sumarDiasHabiles('2025-02-27', 1)).toBe('2025-02-28'); // jueves → viernes
    expect(cal.sumarDiasHabiles('2025-02-28', 1)).toBe('2025-03-05'); // viernes → miércoles (salta fin de semana + carnaval)
    expect(cal.sumarDiasHabiles('2025-04-16', 2)).toBe('2025-04-21'); // salta Viernes Santo
  });
  it('cuenta días hábiles y es inverso de sumar', () => {
    expect(cal.contarDiasHabiles('2025-02-28', '2025-03-05')).toBe(1);
    expect(cal.contarDiasHabiles('2025-06-02', cal.sumarDiasHabiles('2025-06-02', 8))).toBe(8);
  });
  it('respeta feriados adicionales (departamentales)', () => {
    const c = new CalendarioBolivia([{ fecha: '2025-09-14', nombre: 'Día de Cochabamba' }]);
    expect(c.esHabil('2025-09-15')).toBe(true); // lunes
    expect(c.sumarDiasHabiles('2025-09-12', 1)).toBe('2025-09-15');
    const c2 = new CalendarioBolivia([{ fecha: '2025-09-15', nombre: 'Feriado local' }]);
    expect(c2.sumarDiasHabiles('2025-09-12', 1)).toBe('2025-09-16');
  });
  it('rechaza fechas inválidas', () => {
    expect(() => cal.esHabil('2025-02-30')).toThrow();
    expect(() => cal.esHabil('25/02/2025')).toThrow();
  });
});

describe('Cronograma ANPE (Art. 47 D.S. 0181)', () => {
  const cal = new CalendarioBolivia();
  it('plazo mínimo: 4 días hasta Bs 200.000 y 8 días hasta Bs 1.000.000', () => {
    expect(plazoMinimoDiasHabiles(50_001)).toBe(4);
    expect(plazoMinimoDiasHabiles(180_000)).toBe(4);
    expect(plazoMinimoDiasHabiles(200_000)).toBe(4);
    expect(plazoMinimoDiasHabiles(200_000.01)).toBe(8);
    expect(plazoMinimoDiasHabiles(1_000_000)).toBe(8);
  });
  it('rechaza cuantías fuera de ANPE', () => {
    expect(() => plazoMinimoDiasHabiles(50_000)).toThrow(/rango ANPE/);
    expect(() => plazoMinimoDiasHabiles(1_000_000.01)).toThrow(/rango ANPE/);
    expect(validarRangoAnpe(75_000)).toBeNull();
  });
  it('calcula el cronograma completo para Bs 180.000 (4 d.h.)', () => {
    const r = calcularCronograma({ fechaPublicacion: '2025-06-02', precioReferencial: 180_000 }, cal);
    expect(r.cronograma.fechaApertura).toBe('2025-06-06');
    expect(r.diasHabilesPublicacionApertura).toBe(4);
    expect(r.cronograma.fechaAdjudicacion).toBe('2025-06-10');
    expect(r.cronograma.fechaPresentacionDoc).toBe('2025-06-16'); // 11,12,13,16 jun
    expect(r.cronograma.fechaContrato).toBe('2025-06-20'); // 17,18 jun; el 19 es Corpus Christi (feriado) → 20
  });
  it('salta feriados en el cómputo de 8 días hábiles', () => {
    const r = calcularCronograma({ fechaPublicacion: '2025-02-26', precioReferencial: 500_000 }, cal);
    // 27,28 feb, (3,4 mar carnaval) 5,6,7,10,11,12 mar => 8º hábil = 12 mar
    expect(r.cronograma.fechaApertura).toBe('2025-03-12');
  });
  it('rechaza publicación en día inhábil', () => {
    expect(() => calcularCronograma({ fechaPublicacion: '2025-06-07', precioReferencial: 180_000 }, cal)).toThrow(/sábado/);
  });
  it('detecta apertura antes del plazo mínimo', () => {
    const r = calcularCronograma({ fechaPublicacion: '2025-06-02', precioReferencial: 180_000 }, cal).cronograma;
    const errores = validarCronograma({ ...r, fechaApertura: '2025-06-05', fechaAdjudicacion: '2025-06-10' }, 180_000, cal);
    expect(errores.join(' ')).toMatch(/mínimo según Art\. 47/);
  });
  it('detecta desorden y fechas inhábiles', () => {
    const c = { fechaPublicacion: '2025-06-02', fechaApertura: '2025-06-07', fechaAdjudicacion: '2025-06-06', fechaPresentacionDoc: '2025-06-17', fechaContrato: '2025-06-18' };
    const e = validarCronograma(c, 180_000, cal).join(' ');
    expect(e).toMatch(/no es día hábil/);
    expect(e).toMatch(/debe ser posterior/);
  });
  it('acepta una apertura posterior al mínimo', () => {
    const r = calcularCronograma({ fechaPublicacion: '2025-06-02', precioReferencial: 180_000, fechaApertura: '2025-06-12' }, cal);
    expect(r.diasHabilesPublicacionApertura).toBe(8);
  });
});
