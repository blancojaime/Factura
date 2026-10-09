import type { Estado, Rol } from "./tipos";

/** 18500 -> "18.500,00" (formato boliviano). */
export function bs(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  const n = typeof valor === "number" ? valor : Number(valor);
  if (Number.isNaN(n)) return String(valor);
  return n.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fecha(valor: string | null | undefined): string {
  if (!valor) return "—";
  const d = new Date(valor.length === 10 ? valor + "T00:00:00" : valor);
  return Number.isNaN(d.getTime()) ? valor : d.toLocaleDateString("es-BO", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function fechaHora(valor: string | null | undefined): string {
  if (!valor) return "—";
  const d = new Date(valor);
  return Number.isNaN(d.getTime())
    ? valor
    : d.toLocaleString("es-BO", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export const ESTADOS: Estado[] = [
  "BORRADOR", "SOLICITADO", "CERTIFICADO_PRESUPUESTO", "EN_COTIZACION", "EVALUADO", "ADJUDICADO",
  "FORMALIZADO", "RECEPCIONADO", "DEVENGADO", "ANULADO",
];

export const ESTADO_LABEL: Record<Estado, string> = {
  BORRADOR: "Borrador", SOLICITADO: "Solicitado", CERTIFICADO_PRESUPUESTO: "Presupuesto certificado",
  EN_COTIZACION: "En cotización", EVALUADO: "Evaluado", ADJUDICADO: "Adjudicado", FORMALIZADO: "Formalizado",
  RECEPCIONADO: "Recepcionado", DEVENGADO: "Devengado", ANULADO: "Anulado",
};

export const ESTADO_CLASE: Record<Estado, string> = {
  BORRADOR: "bg-slate-100 text-slate-700 ring-slate-300",
  SOLICITADO: "bg-sky-100 text-sky-800 ring-sky-300",
  CERTIFICADO_PRESUPUESTO: "bg-amber-100 text-amber-800 ring-amber-300",
  EN_COTIZACION: "bg-indigo-100 text-indigo-800 ring-indigo-300",
  EVALUADO: "bg-teal-100 text-teal-800 ring-teal-300",
  ADJUDICADO: "bg-violet-100 text-violet-800 ring-violet-300",
  FORMALIZADO: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  RECEPCIONADO: "bg-green-100 text-green-800 ring-green-300",
  DEVENGADO: "bg-green-200 text-green-900 ring-green-400",
  ANULADO: "bg-red-100 text-red-800 ring-red-300",
};

export const ROL_LABEL: Record<Rol, string> = {
  ROL_SOLICITANTE: "Unidad Solicitante", ROL_PRESUPUESTO: "Presupuesto", ROL_CONTRATACIONES: "Contrataciones",
  ROL_RPA: "Responsable del Proceso (RPA)", ROL_RECEPCION: "Recepción y Almacenes", ROL_ADMIN: "Administrador",
};

export const TIPO_OBJETO_LABEL: Record<string, string> = {
  BIEN: "Bien", SERVICIO_GENERAL: "Servicio general", CONSULTORIA: "Consultoría", OBRA: "Obra menor",
};

export const MODALIDAD_LABEL: Record<string, string> = {
  COMPRA_DIRECTA: "Compra directa (hasta Bs 20.000)",
  CONSULTA_PRECIOS_SICOES: "Consulta de precios SICOES (Bs 20.001 a 50.000)",
};

export const METODO_LABEL: Record<string, string> = {
  ORDEN_COMPRA: "Orden de Compra", ORDEN_SERVICIO: "Orden de Servicio", CONTRATO: "Contrato Administrativo",
};

export const TIPO_DOC_LABEL: Record<string, string> = {
  C1_SOLICITUD: "Formulario C-1 (solicitud)", INFORME_EXCEPCION_CHB: "Informe de excepción CHB",
  CERTIFICACION_C31: "Certificación C-31", FICHA_COTIZACION: "Ficha de cotización",
  CUADRO_COMPARATIVO: "Cuadro comparativo", NOTA_ADJUDICACION: "Nota de adjudicación",
  ORDEN_COMPRA_SERVICIO: "Orden de compra / servicio", CONTRATO_ADMINISTRATIVO: "Contrato administrativo",
  ACTA_RECEPCION_FORM500: "Acta de recepción (Form. 500)",
};

export const CHB_LABEL: Record<string, string> = {
  NO_APLICA: "No aplica", COMPRA_CHB_OBLIGATORIA: "Compra obligatoria en CHB",
  EXCEPCION_INCOMPATIBILIDAD: "Excepción (existe en CHB)", SIN_COINCIDENCIA: "Sin coincidencia en CHB",
};
