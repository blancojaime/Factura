import { aCentavos, deCentavos, multiplicar, sumaExacta } from './money';

export interface LineaPresupuesto {
  da: string; ue: string; programa: string; proyecto: string; actividadObra: string;
  fuente: string; organismo: string; partida: string; importe: number;
}
export interface ItemMonto { partidaGasto: string; cantidad: number; precioUnitario: number; precioTotal: number }

/** Dígitos esperados por campo de la estructura programática SIGEP. */
const FORMATO: Record<keyof Omit<LineaPresupuesto, 'importe'>, RegExp> = {
  da: /^\d{1,3}$/, ue: /^\d{1,3}$/, programa: /^\d{1,2}$/, proyecto: /^\d{1,4}$/,
  actividadObra: /^\d{1,3}$/, fuente: /^\d{1,2}$/, organismo: /^\d{1,3}$/, partida: /^\d{5}$/,
};
const ETIQUETA: Record<keyof Omit<LineaPresupuesto, 'importe'>, string> = {
  da: 'DA', ue: 'UE', programa: 'Programa', proyecto: 'Proyecto', actividadObra: 'Actividad/Obra', fuente: 'Fuente', organismo: 'Organismo', partida: 'Partida',
};

export interface ValidacionC31 { valido: boolean; errores: string[]; totalCertificado: number; totalItems: number; porPartida: { partida: string; items: number; certificado: number; diferencia: number }[] }

/** Validación aritmética previa a la transcripción al SIGEP: evita rechazos contables. */
export function validarPreventivoC31(lineas: LineaPresupuesto[], items: ItemMonto[], precioReferencialTotal: number): ValidacionC31 {
  const errores: string[] = [];
  if (!lineas.length) errores.push('No hay líneas de certificación presupuestaria.');
  lineas.forEach((l, i) => {
    (Object.keys(FORMATO) as (keyof typeof FORMATO)[]).forEach((k) => {
      if (!FORMATO[k].test(String(l[k] ?? ''))) errores.push(`Línea ${i + 1}: ${ETIQUETA[k]} "${l[k] ?? ''}" no tiene el formato SIGEP esperado.`);
    });
    if (!(l.importe > 0)) errores.push(`Línea ${i + 1}: el importe debe ser mayor a cero.`);
  });
  items.forEach((it, i) => {
    const esperado = multiplicar(it.cantidad, it.precioUnitario);
    if (aCentavos(esperado) !== aCentavos(it.precioTotal))
      errores.push(`Ítem ${i + 1}: cantidad × precio unitario = ${esperado.toFixed(2)} no coincide con el total ${it.precioTotal.toFixed(2)}.`);
  });
  const totalItems = sumaExacta(items.map((i) => i.precioTotal));
  const totalCertificado = sumaExacta(lineas.map((l) => l.importe));
  if (aCentavos(totalItems) !== aCentavos(precioReferencialTotal))
    errores.push(`La suma de ítems (${totalItems.toFixed(2)}) no coincide con el precio referencial (${precioReferencialTotal.toFixed(2)}).`);
  if (aCentavos(totalCertificado) !== aCentavos(totalItems))
    errores.push(`El total certificado (${totalCertificado.toFixed(2)}) no coincide con el total de ítems (${totalItems.toFixed(2)}).`);

  const partidas = [...new Set([...items.map((i) => i.partidaGasto), ...lineas.map((l) => l.partida)])].sort();
  const porPartida = partidas.map((p) => {
    const it = sumaExacta(items.filter((i) => i.partidaGasto === p).map((i) => i.precioTotal));
    const ce = sumaExacta(lineas.filter((l) => l.partida === p).map((l) => l.importe));
    return { partida: p, items: it, certificado: ce, diferencia: deCentavos(aCentavos(ce) - aCentavos(it)) };
  });
  porPartida.filter((p) => p.diferencia !== 0).forEach((p) => errores.push(`Partida ${p.partida}: certificado ${p.certificado.toFixed(2)} ≠ ítems ${p.items.toFixed(2)}.`));
  return { valido: errores.length === 0, errores, totalCertificado, totalItems, porPartida };
}

const sinAcentos = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '');
/** Glosa estandarizada (mayúsculas, sin tildes, máx. 250 caracteres). */
export function construirGlosa(objeto: string, codigoProceso: string, entidad: string, modalidad = 'ANPE'): string {
  const base = sinAcentos(`PREVENTIVO PARA LA CONTRATACION DE ${objeto} - ${modalidad} ${codigoProceso} - ${entidad}`).toUpperCase().replace(/\s+/g, ' ').trim();
  return base.length > 250 ? base.slice(0, 247) + '...' : base;
}

/** Bloque de texto tabulado listo para pegar/transcribir en el formulario C-31. */
export function bloqueSigep(lineas: LineaPresupuesto[], glosa: string, c31Numero?: string | null): string {
  const cab = ['DA', 'UE', 'PROG', 'PROY', 'ACT', 'FTE', 'ORG', 'PARTIDA', 'IMPORTE'].join('\t');
  const filas = lineas.map((l) => [l.da, l.ue, l.programa, l.proyecto, l.actividadObra, l.fuente, l.organismo, l.partida, l.importe.toFixed(2)].join('\t'));
  const total = sumaExacta(lineas.map((l) => l.importe)).toFixed(2);
  return [`C-31 PREVENTIVO${c31Numero ? ' N° ' + c31Numero : ''}`, cab, ...filas, `TOTAL\t\t\t\t\t\t\t\t${total}`, `GLOSA: ${glosa}`].join('\n');
}
