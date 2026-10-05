/**
 * Detector de especificaciones técnicas dirigidas. Las NB-SABS prohíben consignar marcas,
 * patentes o características que identifiquen a un único proveedor, salvo referencia
 * expresa "o equivalente" para fines de calidad.
 */
export type Severidad = 'BLOQUEANTE' | 'ADVERTENCIA';
export interface Hallazgo {
  tipo: 'MARCA' | 'SIMBOLO_REGISTRO' | 'EXCLUSIVIDAD' | 'PATENTE' | 'SIN_EQUIVALENTE';
  severidad: Severidad;
  fragmento: string;
  sugerencia: string;
}
export interface AnalisisEspecificacion {
  valido: boolean;
  hallazgos: Hallazgo[];
}

/** Marcas comerciales frecuentes; la lista completa se administra en la tabla `marcas_registradas`. */
export const MARCAS_BASE = ['sika', 'toyota', 'nissan', 'hp', 'dell', 'lenovo', 'samsung', 'epson', 'canon', 'caterpillar', 'komatsu', 'cemex', 'holcim', 'soboce', 'fancesa', 'itaca', 'coboce', 'bosch', 'makita', 'stanley', 'cisco', 'microsoft', 'adobe', 'lg', 'apple', 'xerox', 'brother', 'ford', 'chevrolet', 'hyundai', 'kia', 'mitsubishi', 'ingersoll'];

const normalizar = (t: string) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const escapar = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const PATRONES_EXCLUSIVIDAD: { re: RegExp; tipo: Hallazgo['tipo']; severidad: Severidad; sugerencia: string }[] = [
  { re: /\b(unico|exclusivo|exclusiva|exclusivamente)\s+(proveedor|fabricante|distribuidor|importador|representante)\b/, tipo: 'EXCLUSIVIDAD', severidad: 'BLOQUEANTE', sugerencia: 'Elimine toda referencia a un proveedor o fabricante específico.' },
  { re: /\b(representante|distribuidor)\s+(oficial|autorizado|exclusivo)\b/, tipo: 'EXCLUSIVIDAD', severidad: 'BLOQUEANTE', sugerencia: 'No exija representación o distribución exclusiva; limita la competencia.' },
  { re: /\b(patente|patentado|patentada|propiedad\s+industrial)\b/, tipo: 'PATENTE', severidad: 'BLOQUEANTE', sugerencia: 'Describa la función y el desempeño requeridos, no una tecnología patentada.' },
  { re: /\b(solo|solamente)\s+(la\s+|el\s+)?(marca|modelo)\b/, tipo: 'EXCLUSIVIDAD', severidad: 'BLOQUEANTE', sugerencia: 'No restrinja a una marca o modelo; defina parámetros técnicos mínimos.' },
];

export function analizarEspecificacion(texto: string, marcas: string[] = MARCAS_BASE): AnalisisEspecificacion {
  const hallazgos: Hallazgo[] = [];
  const norm = normalizar(texto);
  const referencialEquivalente = /\b(o\s+equivalente|o\s+similar|o\s+superior|referencial)\b/.test(norm);

  for (const m of /[®™©]/g[Symbol.matchAll](texto)) {
    hallazgos.push({ tipo: 'SIMBOLO_REGISTRO', severidad: 'BLOQUEANTE', fragmento: m[0], sugerencia: 'Retire símbolos de marca registrada; describa las características técnicas genéricas.' });
  }

  const vistas = new Set<string>();
  for (const marca of marcas) {
    const re = new RegExp(`(^|[^a-z0-9])${escapar(normalizar(marca))}(?![a-z0-9])`);
    if (re.test(norm) && !vistas.has(marca)) {
      vistas.add(marca);
      hallazgos.push(
        referencialEquivalente
          ? { tipo: 'MARCA', severidad: 'ADVERTENCIA', fragmento: marca, sugerencia: `Se menciona la marca "${marca}" con salvedad de equivalencia; verifique que sea solo referencia de calidad y reemplácela por parámetros técnicos.` }
          : { tipo: 'SIN_EQUIVALENTE', severidad: 'BLOQUEANTE', fragmento: marca, sugerencia: `La marca "${marca}" aparece sin la expresión "o equivalente". Reemplácela por características técnicas objetivas.` },
      );
    }
  }

  for (const p of PATRONES_EXCLUSIVIDAD) {
    const m = p.re.exec(norm);
    if (m) hallazgos.push({ tipo: p.tipo, severidad: p.severidad, fragmento: m[0], sugerencia: p.sugerencia });
  }

  return { valido: !hallazgos.some((h) => h.severidad === 'BLOQUEANTE'), hallazgos };
}

/** Secciones mínimas del asistente según el tipo de objeto. */
export const SECCIONES_REQUERIMIENTO: Record<'BIENES' | 'SERVICIOS' | 'OBRAS', { clave: string; titulo: string; ayuda: string }[]> = {
  BIENES: [
    { clave: 'descripcion', titulo: 'Descripción general del bien', ayuda: 'Qué se requiere y para qué se usará. Sin marcas.' },
    { clave: 'caracteristicas', titulo: 'Características técnicas mínimas', ayuda: 'Parámetros medibles: resistencia, dimensiones, composición, normas.' },
    { clave: 'normas', titulo: 'Normas y certificaciones', ayuda: 'Normas IBNORCA/NB u otras aplicables.' },
    { clave: 'entrega', titulo: 'Lugar, plazo y condiciones de entrega', ayuda: 'Almacén, horarios, embalaje, plazo en días calendario.' },
    { clave: 'garantia', titulo: 'Garantía técnica y de calidad', ayuda: 'Tiempo de garantía, reposición por defectos.' },
  ],
  SERVICIOS: [
    { clave: 'objeto', titulo: 'Objeto del servicio', ayuda: 'Qué servicio y con qué finalidad.' },
    { clave: 'alcance', titulo: 'Alcance y actividades', ayuda: 'Actividades a ejecutar, delimitando lo excluido.' },
    { clave: 'productos', titulo: 'Productos o resultados esperados', ayuda: 'Entregables verificables.' },
    { clave: 'perfil', titulo: 'Perfil y experiencia requerida', ayuda: 'Experiencia general y específica proporcional al objeto.' },
    { clave: 'plazo', titulo: 'Plazo, lugar y forma de pago', ayuda: 'Plazo de ejecución, lugar, pagos contra productos.' },
  ],
  OBRAS: [
    { clave: 'descripcion', titulo: 'Descripción de la obra', ayuda: 'Localización, alcance y objetivo.' },
    { clave: 'computos', titulo: 'Cómputos métricos', ayuda: 'Resumen por módulo/ítem y referencia a planos y planilla de cantidades.' },
    { clave: 'especificaciones', titulo: 'Especificaciones técnicas por ítem', ayuda: 'Materiales, procedimiento, medición y forma de pago por ítem.' },
    { clave: 'plazo', titulo: 'Plazo de ejecución', ayuda: 'Días calendario y cronograma referencial.' },
    { clave: 'supervision', titulo: 'Supervisión y recepción', ayuda: 'Responsable de supervisión, recepción provisional y definitiva.' },
  ],
};

export function verificarCompletitud(tipo: keyof typeof SECCIONES_REQUERIMIENTO, secciones: Record<string, string | undefined>, minCaracteres = 20) {
  const faltantes = SECCIONES_REQUERIMIENTO[tipo].filter((s) => (secciones[s.clave] ?? '').trim().length < minCaracteres).map((s) => s.titulo);
  return { completo: faltantes.length === 0, faltantes };
}
