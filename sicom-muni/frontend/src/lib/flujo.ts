import type { Estado, Rol } from "./tipos";

/** Que debe hacer cada rol cuando un tramite esta en cada estado (para el tablero y las sugerencias). */
export const ACCION_PENDIENTE: Record<Rol, Partial<Record<Estado, string>>> = {
  ROL_SOLICITANTE: { BORRADOR: "Completar y enviar la solicitud" },
  ROL_PRESUPUESTO: { SOLICITADO: "Verificar saldo y certificar presupuesto", RECEPCIONADO: "Registrar el devengado" },
  ROL_CONTRATACIONES: { EN_COTIZACION: "Gestionar cotizaciones y evaluar ofertas" },
  ROL_RPA: {
    CERTIFICADO_PRESUPUESTO: "Aprobar el inicio del proceso", EVALUADO: "Adjudicar o declarar desierto",
    ADJUDICADO: "Formalizar (orden o contrato)",
  },
  ROL_RECEPCION: { FORMALIZADO: "Verificar y registrar la recepción" },
  ROL_ADMIN: {},
};

/** Secuencia normal del tramite (para la linea de tiempo). */
export const SECUENCIA: Estado[] = [
  "BORRADOR", "SOLICITADO", "CERTIFICADO_PRESUPUESTO", "EN_COTIZACION", "EVALUADO", "ADJUDICADO",
  "FORMALIZADO", "RECEPCIONADO", "DEVENGADO",
];

export interface NavItem { href: string; etiqueta: string; roles?: Rol[] }

export const NAV: NavItem[] = [
  { href: "/", etiqueta: "Inicio" },
  { href: "/contrataciones", etiqueta: "Contrataciones" },
  { href: "/contrataciones/nueva", etiqueta: "Nueva solicitud", roles: ["ROL_SOLICITANTE"] },
  { href: "/presupuesto", etiqueta: "Presupuesto", roles: ["ROL_PRESUPUESTO", "ROL_RPA", "ROL_ADMIN", "ROL_CONTRATACIONES"] },
  { href: "/admin/usuarios", etiqueta: "Usuarios", roles: ["ROL_ADMIN"] },
  { href: "/admin/parametros", etiqueta: "Parámetros del GAM", roles: ["ROL_ADMIN"] },
  { href: "/admin/catalogo", etiqueta: "Catálogo CHB", roles: ["ROL_ADMIN"] },
  { href: "/admin/auditoria", etiqueta: "Auditoría", roles: ["ROL_ADMIN"] },
];
