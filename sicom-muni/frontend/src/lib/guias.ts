import type { TipoObjeto } from "./tipos";

/** Guia para redactar las Especificaciones Tecnicas (bienes) o los Terminos de Referencia (servicios, obras, consultorias). */
export const GUIA_ET: Record<TipoObjeto, { titulo: string; puntos: string[] }> = {
  BIEN: {
    titulo: "Especificaciones Técnicas (ET) del bien",
    puntos: ["Características técnicas y de calidad (dimensiones, materiales, normas aplicables)",
      "Cantidad y unidad de medida", "Garantía y condiciones de entrega", "Embalaje y forma de recepción",
      "No direccionar la compra a una marca o proveedor específico"],
  },
  SERVICIO_GENERAL: {
    titulo: "Términos de Referencia (TdR) del servicio",
    puntos: ["Objeto y alcance del servicio", "Actividades a ejecutar y resultados esperados",
      "Perfil y experiencia mínima del prestador", "Plazo, horarios y lugar de prestación", "Forma de supervisión y conformidad"],
  },
  CONSULTORIA: {
    titulo: "Términos de Referencia (TdR) de la consultoría",
    puntos: ["Antecedentes, objetivo general y específicos", "Productos / informes a entregar y cronograma",
      "Perfil profesional y experiencia requerida", "Supervisión, forma de pago y propiedad de los productos"],
  },
  OBRA: {
    titulo: "Especificaciones y TdR de la obra menor",
    puntos: ["Descripción de las actividades y volúmenes de obra", "Materiales y especificaciones técnicas",
      "Plazo de ejecución y ubicación", "Supervisión, seguridad y recepción de obra"],
  },
};
