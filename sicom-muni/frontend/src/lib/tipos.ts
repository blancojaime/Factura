// Tipos que reflejan las respuestas de la API (los montos llegan como texto decimal).
export type Rol =
  | "ROL_SOLICITANTE" | "ROL_PRESUPUESTO" | "ROL_CONTRATACIONES" | "ROL_RPA" | "ROL_RECEPCION" | "ROL_ADMIN";

export type Estado =
  | "BORRADOR" | "SOLICITADO" | "CERTIFICADO_PRESUPUESTO" | "EN_COTIZACION" | "EVALUADO" | "ADJUDICADO"
  | "FORMALIZADO" | "RECEPCIONADO" | "DEVENGADO" | "ANULADO";

export type TipoObjeto = "BIEN" | "SERVICIO_GENERAL" | "CONSULTORIA" | "OBRA";

export interface Usuario {
  id: string; username: string; nombre_completo: string; cargo: string; rol: Rol; email: string; activo: boolean;
}

export interface Item {
  id: string; numero: number; codigo_unspsc: string; partida_id: string | null; partida_gasto: string;
  descripcion_especifica: string; unidad_medida: string; cantidad: string; precio_unitario_ref: string;
  subtotal: string; fuera_catalogo_chb: boolean;
  estado_chb: "NO_APLICA" | "COMPRA_CHB_OBLIGATORIA" | "EXCEPCION_INCOMPATIBILIDAD" | "SIN_COINCIDENCIA";
}

export interface Cotizacion {
  id: string; nit_ci: string; razon_social: string; correo: string; telefono: string;
  monto_total_ofertado: string | null; plazo_ofertado_dias: number; cumple_especificaciones: boolean;
  margen_preferencia_pct: string; observaciones: string; adjudicado: boolean; fecha_recepcion: string;
  registro_preferencia: string; registro_preferencia_valido: boolean; precio_evaluado: string | null;
  ranking: number | null; recomendada: boolean; motivo_descalificacion: string | null; sellada: boolean;
}

export interface Documento {
  id: string; tipo_doc: string; version: number; hash_sha256: string; hash_contenido: string;
  fecha_generacion: string; estado_tramite: string;
}

export interface Preventivo { partida_id: string; codigo_partida: string; descripcion: string; importe: string; estado: string }

export interface Recepcion {
  id: string; fecha_recepcion: string; conforme: boolean; observaciones: string; nro_nia: string | null;
  dias_retraso: number; detalle: Record<string, { cantidad_recibida: string; conforme: boolean }>;
}

export interface Contratacion {
  id: string; correlativo_interno: string; objeto_contratacion: string; tipo_objeto: TipoObjeto;
  monto_referencial_total: string; plazo_dias_calendario: number; metodo_formalizacion: string | null;
  cuce: string | null; preventivo_c31_nro: string | null; estado: Estado; requiere_excepcion_chb: boolean;
  justificacion_excepcion_chb: string | null; codigo_autorizacion_chb: string | null; created_by_id: string;
  created_at: string; updated_at: string; unidad_solicitante: string; justificacion: string;
  especificaciones_tecnicas: string; lugar_entrega: string; modalidad_cuantia: string | null;
  nro_formulario_110: string | null; fecha_limite_ofertas: string | null; ofertas_abiertas: boolean;
  motivo_cierre: string | null; ultima_observacion: string | null;
  items: Item[]; cotizaciones: Cotizacion[]; documentos: Documento[]; recepciones: Recepcion[];
  preventivos: Preventivo[]; acciones: string[]; mensaje_cuantia: string;
}

export type Resumen = Pick<Contratacion,
  "id" | "correlativo_interno" | "objeto_contratacion" | "tipo_objeto" | "monto_referencial_total" |
  "plazo_dias_calendario" | "metodo_formalizacion" | "estado" | "modalidad_cuantia" | "created_at" | "updated_at">;

export interface Partida {
  id: string; codigo_partida: string; descripcion: string; saldo_disponible: string; gestion: number;
  programa: string; proyecto: string; actividad: string; fuente: string; organismo: string; monto_aprobado: string;
}

export interface Catalogo {
  id: string; codigo_unspsc: string; descripcion_bien: string; unidad_medida: string;
  precio_referencial_nacional: string | null; activo: boolean;
}

export interface ConsultaCHB {
  codigo_unspsc: string; en_catalogo: boolean; descripcion_bien?: string; unidad_medida?: string;
  precio_referencial_nacional?: string | null; mensaje: string;
}

export interface Regla {
  modalidad: string | null; requiere_formulario_110: boolean; bloqueado: boolean; mensaje: string;
  metodo_formalizacion: string | null;
}

export interface BloqueSigep {
  encabezado: string[]; filas: string[][]; texto_pipe: string; texto_tsv: string; total: string;
  origen: "PREVENTIVO" | "PREVISTO";
}

export interface OfertaEval {
  id: string; razon_social: string; monto: string; plazo_dias: number; margen_aplicado_pct: string;
  precio_evaluado: string; elegible: boolean; motivo: string; ranking: number | null; recomendada: boolean;
  recibida: string;
}

export interface Evaluacion { hay_desempate: boolean; recomendada: string | null; ofertas: OfertaEval[] }

export interface Tablero { por_estado: Record<string, number>; pendientes: Resumen[]; total: number }

export interface Parametro { clave: string; valor: string; descripcion: string }

export interface AuditoriaFila {
  secuencia: number; usuario_id: string | null; accion: string; tabla_afectada: string; registro_id: string;
  datos_previos: unknown; datos_nuevos: unknown; ip: string; timestamp: string; hash_registro: string;
}
