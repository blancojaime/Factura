import { TipoObjeto } from './garantia';

/** Entrada del catálogo de productos de manufactura nacional (Compro Boliviano – CHB). */
export interface EntradaChb {
  id: string;
  codigoUnspsc: string;
  descripcion: string;
  productor?: string | null;
  vigente: boolean;
}

export interface ItemChbEntrada {
  codigoUnspsc: string;
  descripcion: string;
  /** Si existe producción nacional pero no satisface el requerimiento, explicar por qué. */
  incompatibilidadTecnica?: string | null;
}

export type ResultadoChb = 'NO_APLICA' | 'CUBIERTO_POR_CHB' | 'INCOMPATIBLE_CON_CHB' | 'SIMILAR_EN_CHB' | 'SIN_PRODUCCION_NACIONAL';

export interface ValidacionChb {
  resultado: ResultadoChb;
  coincidencias: EntradaChb[];
  /** Habilita contratación fuera del CHB vía D.S. 0181 previa justificación. */
  requiereExcepcion: boolean;
  /** Debe adjuntarse ficha del producto nacional. */
  requiereFichaChb: boolean;
  mensaje: string;
}

const soloDigitos = (s: string) => s.replace(/\D/g, '');

/**
 * Cruza el código UNSPSC con el catálogo de manufactura nacional (D.S. 4505).
 *  - Código exacto vigente  → debe adquirirse producción nacional (ficha CHB).
 *  - Código exacto + incompatibilidad técnica documentada → excepción.
 *  - Misma clase (6 primeros dígitos) sin coincidencia exacta → excepción con alerta (puede existir sustituto nacional).
 *  - Sin coincidencia en la clase → sin producción nacional → excepción.
 * Servicios y obras no se validan contra el catálogo de productos.
 */
export function validarItemChb(tipoObjeto: TipoObjeto, item: ItemChbEntrada, catalogo: EntradaChb[]): ValidacionChb {
  if (tipoObjeto === 'SERVICIOS')
    return { resultado: 'NO_APLICA', coincidencias: [], requiereExcepcion: false, requiereFichaChb: false, mensaje: 'Los servicios no se validan contra el catálogo de productos nacionales.' };

  const codigo = soloDigitos(item.codigoUnspsc);
  if (codigo.length !== 8)
    throw new Error(`Código UNSPSC inválido "${item.codigoUnspsc}": debe tener 8 dígitos.`);
  // UNSPSC: segmentos 10–60 = productos; 70–99 = servicios (incluye servicios de construcción).
  if (Number(codigo.slice(0, 2)) >= 70)
    return { resultado: 'NO_APLICA', coincidencias: [], requiereExcepcion: false, requiereFichaChb: false, mensaje: 'El código UNSPSC corresponde a un servicio (segmento ≥ 70): no se valida contra el catálogo de productos.' };

  const vigentes = catalogo.filter((c) => c.vigente);
  const exactas = vigentes.filter((c) => soloDigitos(c.codigoUnspsc) === codigo);
  if (exactas.length) {
    if (item.incompatibilidadTecnica?.trim())
      return {
        resultado: 'INCOMPATIBLE_CON_CHB', coincidencias: exactas, requiereExcepcion: true, requiereFichaChb: false,
        mensaje: 'Existe producción nacional pero se declara incompatibilidad técnica: se emitirá el Formulario de Justificación de Insuficiencia Técnica.',
      };
    return {
      resultado: 'CUBIERTO_POR_CHB', coincidencias: exactas, requiereExcepcion: false, requiereFichaChb: true,
      mensaje: 'Producto con manufactura nacional en el catálogo: la contratación debe priorizar el CHB y adjuntar la ficha.',
    };
  }
  const clase = codigo.slice(0, 6);
  const similares = vigentes.filter((c) => soloDigitos(c.codigoUnspsc).startsWith(clase));
  if (similares.length)
    return {
      resultado: 'SIMILAR_EN_CHB', coincidencias: similares, requiereExcepcion: true, requiereFichaChb: false,
      mensaje: 'No hay coincidencia exacta, pero existen productos nacionales de la misma clase: la justificación debe demostrar por qué no sustituyen al requerido.',
    };
  return {
    resultado: 'SIN_PRODUCCION_NACIONAL', coincidencias: [], requiereExcepcion: true, requiereFichaChb: false,
    mensaje: 'No existe inventario nacional para este código: se emitirá el Formulario de Justificación de Insuficiencia Técnica.',
  };
}

export interface JustificacionInsuficiencia {
  titulo: string;
  items: { codigoUnspsc: string; descripcion: string; resultado: ResultadoChb; fundamento: string }[];
  declaracion: string;
}

export function generarJustificacionInsuficiencia(
  objeto: string,
  items: { codigoUnspsc: string; descripcion: string; validacion: ValidacionChb; incompatibilidadTecnica?: string | null }[],
): JustificacionInsuficiencia {
  const afectados = items.filter((i) => i.validacion.requiereExcepcion);
  return {
    titulo: 'FORMULARIO DE JUSTIFICACIÓN DE INSUFICIENCIA TÉCNICA DE PRODUCCIÓN NACIONAL',
    items: afectados.map((i) => ({
      codigoUnspsc: i.codigoUnspsc,
      descripcion: i.descripcion,
      resultado: i.validacion.resultado,
      fundamento: i.incompatibilidadTecnica?.trim() || i.validacion.mensaje,
    })),
    declaracion: `La Unidad Solicitante declara que, para la contratación "${objeto}", los ítems listados no cuentan con oferta nacional en el catálogo de manufactura nacional que satisfaga las especificaciones técnicas requeridas, por lo que solicita habilitar su adquisición conforme al D.S. 0181 (NB-SABS).`,
  };
}
