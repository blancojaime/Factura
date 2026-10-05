import { DatosDoc, DocSpec } from '../tipos';
import { formatoBs, montoEnLetras } from '../../domain/money';
import { V1_ITEMS, cuadroComparativo } from '../../domain/evaluacion';
import { SECCIONES_REQUERIMIENTO } from '../../domain/especificaciones';
import { bloqueSigep } from '../../domain/sigep';

export type TipoGenerable =
  | 'SOLICITUD_C1' | 'JUSTIFICACION_CHB' | 'PREVENTIVO_C31' | 'DBC' | 'INFORME_V1' | 'CUADRO_COMPARATIVO'
  | 'INFORME_EVALUACION' | 'ACTA_ADJUDICACION' | 'CONTRATO' | 'ORDEN_COMPRA_SERVICIO' | 'ACTA_RECEPCION';

const NOTA_MODELO = 'Documento generado paramétricamente por SABSMUNI-ANPE conforme a las NB-SABS (D.S. 0181). Debe contrastarse con el modelo oficial vigente del Órgano Rector antes de su publicación o suscripción.';
const fecha = (iso: string | null | undefined) => (iso ? iso.split('-').reverse().join('/') : '—');
const TIPO: Record<string, string> = { BIENES: 'Bienes', SERVICIOS: 'Servicios Generales', OBRAS: 'Obras' };
const METODO: Record<string, string> = { PRECIO_EVALUADO_MAS_BAJO: 'Precio Evaluado Más Bajo', CALIDAD_PROPUESTA_COSTO: 'Calidad, Propuesta Técnica y Costo' };
const CAT: Record<string, string> = { NACIONAL_GENERAL: 'Nacional (general)', MYPE_APP_OECA: 'MyPE / APP / OECA', EXTRANJERO: 'Extranjero' };

const tablaItems = (d: DatosDoc) => ({
  t: 'tabla' as const,
  columnas: ['N°', 'UNSPSC', 'Partida', 'Descripción técnica', 'Unidad', 'Cant.', 'P. unitario', 'P. total'],
  anchos: [0.5, 1.1, 0.9, 4, 0.9, 0.9, 1.2, 1.3], derecha: [5, 6, 7],
  filas: d.items.map((i) => [i.numero, i.codigoUnspsc, i.partida, i.descripcion, i.unidad, i.cantidad, i.precioUnitario, i.precioTotal]),
});
const objetoKV = (d: DatosDoc): [string, string][] => [
  ['Entidad', d.config.nombreGam], ['Proceso', d.proceso.codigo], ['CUCE', d.proceso.cuce], ['Objeto de contratación', d.proceso.objeto],
  ['Modalidad / tipo', `ANPE · ${TIPO[d.proceso.tipoObjeto]}`], ['Precio referencial', `${formatoBs(d.proceso.precioReferencial)} (${montoEnLetras(d.proceso.precioReferencial)})`],
];
const sec = (d: DatosDoc) => SECCIONES_REQUERIMIENTO[d.proceso.tipoObjeto].map((s) => ({ t: 'clausula' as const, titulo: s.titulo, texto: d.proceso.requerimiento[s.clave]?.trim() || '(sin información)' }));

function solicitudC1(d: DatosDoc): DocSpec {
  return {
    titulo: 'Solicitud de Contratación y Especificaciones Técnicas', formulario: 'C-1', subtitulo: `${d.config.nombreGam}`,
    bloques: [
      { t: 'h', texto: '1. Datos generales' }, { t: 'kv', pares: [...objetoKV(d), ['Unidad solicitante', d.proceso.solicitante?.unidad ?? '—'], ['Plazo de entrega/ejecución', d.proceso.plazoEjecucionDias ? `${d.proceso.plazoEjecucionDias} días calendario` : '—']] },
      { t: 'h', texto: '2. Detalle de ítems requeridos' }, tablaItems(d),
      { t: 'p', texto: `Total: ${formatoBs(d.proceso.precioReferencial)}` },
      { t: 'h', texto: d.proceso.tipoObjeto === 'SERVICIOS' ? '3. Términos de Referencia' : '3. Especificaciones Técnicas' }, ...sec(d),
      { t: 'nota', texto: 'Las especificaciones no consignan marcas ni características que dirijan la contratación; fueron analizadas automáticamente por el validador de especificaciones.' },
    ],
    firmas: [{ cargo: d.proceso.solicitante?.cargo ?? 'Unidad Solicitante', nombre: d.proceso.solicitante?.nombre }],
  };
}

function justificacionChb(d: DatosDoc): DocSpec {
  const j = d.justificacionChb;
  return {
    titulo: j?.titulo ?? 'Justificación de insuficiencia técnica', formulario: 'CHB-J', subtitulo: 'D.S. 4505 · Habilitación de contratación vía D.S. 0181',
    bloques: [
      { t: 'kv', pares: objetoKV(d) },
      { t: 'h', texto: 'Ítems sin oferta nacional suficiente' },
      { t: 'tabla', columnas: ['UNSPSC', 'Descripción', 'Resultado CHB', 'Fundamento'], anchos: [1, 3, 1.6, 4], filas: (j?.items ?? []).map((i) => [i.codigoUnspsc, i.descripcion, i.resultado.replace(/_/g, ' '), i.fundamento]) },
      { t: 'p', texto: j?.declaracion ?? '' }, { t: 'nota', texto: NOTA_MODELO },
    ],
    firmas: [{ cargo: d.proceso.solicitante?.cargo ?? 'Unidad Solicitante', nombre: d.proceso.solicitante?.nombre }, { cargo: d.config.rpaCargo, nombre: d.config.rpaNombre }],
  };
}

function preventivoC31(d: DatosDoc): DocSpec {
  const total = d.certificaciones.reduce((a, c) => a + c.importe, 0);
  return {
    titulo: 'Certificación Presupuestaria · Preventivo C-31', formulario: 'C-31 (SIGEP)', horizontal: true,
    bloques: [
      { t: 'kv', pares: [...objetoKV(d), ['N° Preventivo C-31', d.certificaciones.find((c) => c.c31)?.c31 ?? 'Pendiente de registro en SIGEP'], ['Glosa', d.glosa]] },
      { t: 'tabla', columnas: ['DA', 'UE', 'Prog.', 'Proy.', 'Act./Obra', 'Fte.', 'Org.', 'Partida', 'Importe (Bs)'], derecha: [8],
        filas: [...d.certificaciones.map((c) => [c.da, c.ue, c.programa, c.proyecto, c.actividadObra, c.fuente, c.organismo, c.partida, c.importe]), ['', '', '', '', '', '', '', 'TOTAL', total]] },
      { t: 'h', texto: 'Bloque de transcripción SIGEP' }, { t: 'nota', texto: bloqueSigep(d.certificaciones, d.glosa, d.certificaciones.find((c) => c.c31)?.c31).replace(/\t/g, '  ') },
    ],
    firmas: [{ cargo: 'Responsable de Presupuesto' }, { cargo: 'Responsable de Contrataciones' }],
  };
}

function dbc(d: DatosDoc): DocSpec {
  const c = d.cronograma;
  const eval_ = d.proceso.metodo === 'PRECIO_EVALUADO_MAS_BAJO'
    ? 'Se adjudicará a la propuesta calificada que presente el Precio Evaluado Más Bajo, aplicando los márgenes de preferencia vigentes.'
    : 'Se evaluará la propuesta técnica (puntaje mínimo 70) y la propuesta económica; el puntaje total pondera 70% técnico y 30% económico.';
  return {
    titulo: 'Documento Base de Contratación', subtitulo: `Modalidad ANPE · ${TIPO[d.proceso.tipoObjeto]}`, formulario: 'DBC',
    bloques: [
      { t: 'h', texto: 'PARTE I · INFORMACIÓN GENERAL A LOS PROPONENTES' },
      { t: 'kv', pares: [...objetoKV(d), ['Método de selección y adjudicación', METODO[d.proceso.metodo]], ['Forma de adjudicación', 'Por el total'], ['Plazo de entrega/ejecución', d.proceso.plazoEjecucionDias ? `${d.proceso.plazoEjecucionDias} días calendario` : 'Según propuesta'],
        ['Convocatoria / RUPE', 'Publicación en el SICOES; proponentes inscritos en el RUPE.'], ['Garantía de cumplimiento', '7% del monto del contrato (3,5% para MyPE, APP y OECA).']] },
      { t: 'h', texto: 'Cronograma de plazos (Art. 47 D.S. 0181)' },
      { t: 'tabla', columnas: ['Actividad', 'Fecha'], anchos: [4, 2], filas: c ? [
        ['Publicación del DBC', fecha(c.fechaPublicacion)], [`Presentación y apertura de propuestas (mínimo ${d.plazoMinimoDias ?? '—'} días hábiles)`, fecha(c.fechaApertura)],
        ['Adjudicación o declaratoria desierta', fecha(c.fechaAdjudicacion)], ['Presentación de documentos para la formalización', fecha(c.fechaPresentacionDoc)], ['Suscripción de contrato u orden', fecha(c.fechaContrato)]] : [['Sin cronograma', '—']] },
      { t: 'h', texto: 'PARTE II · CONDICIONES DE LA CONTRATACIÓN' },
      { t: 'clausula', titulo: 'Documentos requeridos (Formulario V-1: Presentó / No presentó)', texto: 'La verificación de documentos se realiza con el criterio "Presentó / No presentó". La ausencia de cualquiera de los siguientes documentos descalifica la propuesta:' },
      { t: 'lista', items: V1_ITEMS.map((i) => `${i.codigo} · ${i.descripcion}`) },
      { t: 'clausula', titulo: 'Criterio de evaluación', texto: eval_ },
      { t: 'clausula', titulo: 'Margen de preferencia', texto: 'Se aplican los márgenes de preferencia nacional: 10% para proponentes nacionales y 18% para MyPE, APP y OECA, sobre el precio de comparación. El monto contractual es el ofertado.' },
      ...(d.proceso.tipoObjeto !== 'BIENES' ? [{ t: 'clausula' as const, titulo: 'Subasta electrónica', texto: 'Las propuestas económicas de Obras y Servicios se registrarán tras la subasta electrónica; el precio final no podrá superar la oferta inicial.' }] : []),
      { t: 'clausula', titulo: 'Formalización', texto: 'La contratación se formaliza mediante contrato; cuando el plazo sea igual o menor a quince (15) días calendario, mediante orden de compra u orden de servicio.' },
      { t: 'h', texto: 'ESPECIFICACIONES TÉCNICAS' }, tablaItems(d), ...sec(d), { t: 'nota', texto: NOTA_MODELO },
    ],
    firmas: [{ cargo: 'Responsable de Contrataciones' }, { cargo: d.config.rpaCargo, nombre: d.config.rpaNombre }],
  };
}

function informeV1(d: DatosDoc): DocSpec {
  return {
    titulo: 'Verificación de Documentos de las Propuestas', formulario: 'V-1', horizontal: true,
    bloques: [
      { t: 'kv', pares: objetoKV(d).slice(0, 4) },
      { t: 'tabla', columnas: ['Proponente', 'NIT', ...V1_ITEMS.map((i) => i.codigo), 'Resultado'],
        filas: d.propuestas.map((p) => [p.razonSocial, p.nit, ...V1_ITEMS.map((i) => (p.v1[i.codigo] ? 'Presentó' : 'No presentó')), p.v1Califica ? 'CUMPLE' : 'NO CUMPLE']) },
      { t: 'lista', items: V1_ITEMS.map((i) => `${i.codigo}: ${i.descripcion}`) },
    ],
    firmas: [{ cargo: 'Responsable de Contrataciones / Comisión de Calificación' }],
  };
}

function cuadro(d: DatosDoc): DocSpec {
  const e = d.evaluacion;
  const c = e ? cuadroComparativo(e) : { columnas: ['—'], filas: [] };
  return {
    titulo: 'Cuadro Comparativo de Ofertas', horizontal: true, subtitulo: METODO[d.proceso.metodo],
    bloques: [
      { t: 'kv', pares: [['Proceso', d.proceso.codigo], ['Objeto', d.proceso.objeto], ['Precio referencial', formatoBs(d.proceso.precioReferencial)]] },
      { t: 'tabla', columnas: c.columnas, filas: c.filas, derecha: [3, 4, 5, 6, 7, 8] },
      ...(e ? [{ t: 'kv' as const, pares: [['Ofertas recibidas', String(e.estadisticas.ofertasRecibidas)] as [string, string], ['Ofertas calificadas', String(e.estadisticas.ofertasCalificadas)] as [string, string], ['Precio final más bajo', e.estadisticas.menorPrecioFinal != null ? formatoBs(e.estadisticas.menorPrecioFinal) : '—'] as [string, string]] }] : []),
      ...(e?.observaciones.length ? [{ t: 'lista' as const, items: e.observaciones }] : []),
    ],
    firmas: [{ cargo: 'Comisión de Calificación / Responsable de Contrataciones' }],
  };
}

function informeEvaluacion(d: DatosDoc): DocSpec {
  const e = d.evaluacion;
  const rec = e?.filas.find((f) => f.propuestaId === e.recomendadaId);
  return {
    titulo: 'Informe de Evaluación y Recomendación', subtitulo: `Dirigido a: ${d.config.rpaNombre} · ${d.config.rpaCargo}`,
    bloques: [
      { t: 'h', texto: '1. Antecedentes' }, { t: 'kv', pares: objetoKV(d) },
      { t: 'h', texto: '2. Resultados de la evaluación' },
      { t: 'p', texto: e ? `Se recibieron ${e.estadisticas.ofertasRecibidas} propuesta(s); ${e.estadisticas.ofertasCalificadas} superaron la verificación del Formulario V-1 y los criterios de la evaluación (${METODO[e.metodo]}).` : 'Sin evaluación registrada.' },
      ...(e ? [{ t: 'tabla' as const, columnas: ['Pos.', 'Proponente', 'Precio final', 'Margen %', 'Precio comparación', 'Estado'], anchos: [0.6, 3, 1.5, 1, 1.8, 3], derecha: [2, 3, 4],
        filas: e.filas.map((f) => [f.posicion ?? '—', f.razonSocial, f.precioFinal, f.margenPreferenciaPct, f.precioComparacion, f.estado === 'CALIFICA' ? 'Califica' : `No califica: ${f.motivos.join('; ')}`]) }] : []),
      { t: 'h', texto: '3. Recomendación' },
      { t: 'p', texto: rec ? `Se recomienda al RPA adjudicar a ${rec.razonSocial} (NIT ${rec.nitProveedor}) por un monto de ${formatoBs(rec.precioFinal)} (${montoEnLetras(rec.precioFinal)}) y plazo de ${rec.plazoDias} días.` : `Se recomienda declarar DESIERTO el proceso. Motivo: ${e?.motivoDesierto ?? '—'}` },
      ...(e?.observaciones.length ? [{ t: 'lista' as const, items: e.observaciones }] : []),
    ],
    firmas: [{ cargo: 'Responsable de Contrataciones / Comisión de Calificación' }],
  };
}

function actaAdjudicacion(d: DatosDoc): DocSpec {
  const ganador = d.propuestas.find((p) => p.id === d.proceso.propuestaAdjudicadaId);
  const desierto = !ganador;
  return {
    titulo: desierto ? 'Resolución de Declaratoria Desierta' : 'Resolución de Adjudicación', subtitulo: `Proceso ${d.proceso.codigo}`,
    bloques: [
      { t: 'kv', pares: objetoKV(d) },
      { t: 'p', texto: desierto
        ? `El Responsable del Proceso de Contratación (RPA), ${d.config.rpaNombre}, en uso de sus atribuciones, DECLARA DESIERTO el proceso ${d.proceso.codigo}. Fundamento: ${d.proceso.resolucionObs ?? '—'}.`
        : `El Responsable del Proceso de Contratación (RPA), ${d.config.rpaNombre}, en uso de sus atribuciones y conforme al Informe de Evaluación y Recomendación, ADJUDICA el proceso ${d.proceso.codigo} a ${ganador!.razonSocial} (NIT ${ganador!.nit}) por ${formatoBs(ganador!.subasta ?? ganador!.monto)} (${montoEnLetras(ganador!.subasta ?? ganador!.monto)}), plazo ${ganador!.plazoDias} días.${d.proceso.resolucionObs ? ' Observación: ' + d.proceso.resolucionObs : ''}` },
      { t: 'p', texto: `Fecha de resolución: ${fecha(d.proceso.resolucionFecha)}. Notifíquese a los proponentes y publíquese en el SICOES.` },
    ],
    firmas: [{ cargo: d.config.rpaCargo, nombre: d.config.rpaNombre }],
  };
}

function contrato(d: DatosDoc): DocSpec {
  const c = d.contrato!;
  const p = d.propuestas.find((x) => x.id === c.propuestaId);
  const esOrden = c.tipo !== 'CONTRATO';
  const etiqueta = c.tipo === 'CONTRATO' ? 'CONTRATO ADMINISTRATIVO' : c.tipo === 'ORDEN_COMPRA' ? 'ORDEN DE COMPRA' : 'ORDEN DE SERVICIO';
  const cl = (titulo: string, texto: string) => ({ t: 'clausula' as const, titulo, texto });
  return {
    titulo: etiqueta, subtitulo: `N° ${c.numero} · ${d.proceso.codigo}`, formulario: esOrden ? 'OC/OS' : 'CONTRATO',
    bloques: [
      cl('Cláusula primera · Partes', `${d.config.nombreGam}, NIT ${d.config.nit}, con domicilio en ${d.config.direccion}, ${d.config.ciudad}, representada legalmente por ${d.config.rpaNombre} (${d.config.rpaCargo}), en adelante la ENTIDAD; y ${p?.razonSocial ?? '—'}, NIT ${p?.nit ?? '—'}, en adelante el PROVEEDOR.`),
      cl('Cláusula segunda · Antecedentes', `El proceso ${d.proceso.codigo} (CUCE ${d.proceso.cuce}) en la modalidad ANPE fue adjudicado conforme a la resolución del RPA de fecha ${fecha(d.proceso.resolucionFecha)}.`),
      cl('Cláusula tercera · Objeto', `El PROVEEDOR se obliga a ejecutar: ${d.proceso.objeto}, conforme a las especificaciones técnicas y a la propuesta adjudicada.`),
      cl('Cláusula cuarta · Monto', `El monto total es de ${formatoBs(c.monto)} (${montoEnLetras(c.monto)}), incluidos impuestos de ley. Los pagos se realizan contra conformidad de recepción.`),
      cl('Cláusula quinta · Plazo', `El plazo de entrega/ejecución es de ${c.plazoDias} día(s) calendario, computables desde la fecha de suscripción (${fecha(c.fechaFirma)}).`),
      cl('Cláusula sexta · Garantía de cumplimiento', `El PROVEEDOR presenta garantía de cumplimiento por ${formatoBs(c.garantiaMonto)} (${c.garantiaPorcentaje}% del monto del instrumento), mediante ${c.garantiaInstrumento ?? 'instrumento a definir'}${c.polizaNumero ? `, N° ${c.polizaNumero}` : ''}${c.polizaEntidad ? `, emitida por ${c.polizaEntidad}` : ''}${c.polizaVigenciaHasta ? `, con vigencia hasta el ${fecha(c.polizaVigenciaHasta)}` : ''}.`),
      cl('Cláusula séptima · Obligaciones del proveedor', 'Cumplir el objeto con la calidad y condiciones ofertadas; reponer sin costo lo observado; mantener vigente la garantía; no ceder ni subcontratar sin autorización de la ENTIDAD.'),
      cl('Cláusula octava · Obligaciones de la entidad', 'Facilitar las condiciones para el cumplimiento, efectuar la recepción en los plazos del DBC y pagar el monto pactado contra conformidad.'),
      cl('Cláusula novena · Multas', 'El retraso injustificado se sanciona con la multa por día calendario establecida en el DBC y las NB-SABS, sin perjuicio de la ejecución de la garantía.'),
      cl('Cláusula décima · Resolución', 'La ENTIDAD podrá resolver por incumplimiento del PROVEEDOR o por causas de fuerza mayor, conforme a las NB-SABS.'),
      cl('Cláusula undécima · Controversias', 'Las partes buscarán resolver sus controversias por conciliación y, en su defecto, ante la jurisdicción ordinaria del domicilio de la ENTIDAD.'),
      cl('Cláusula duodécima · Conformidad', 'Las partes manifiestan su conformidad y suscriben el presente instrumento en dos ejemplares de igual valor.'),
      { t: 'nota', texto: NOTA_MODELO },
    ],
    firmas: [{ cargo: d.config.rpaCargo, nombre: d.config.rpaNombre }, { cargo: 'PROVEEDOR', nombre: p?.razonSocial }],
  };
}

function actaRecepcion(d: DatosDoc): DocSpec {
  const c = d.contrato;
  return {
    titulo: 'Acta de Recepción y Conformidad', subtitulo: `Proceso ${d.proceso.codigo}`, formulario: 'REC',
    bloques: [
      { t: 'kv', pares: [...objetoKV(d), ['Instrumento', c ? `${c.tipo.replace(/_/g, ' ')} N° ${c.numero}` : '—'], ['Monto contratado', c ? formatoBs(c.monto) : '—'], ['Fecha de recepción', fecha(c?.fechaRecepcion)]] },
      { t: 'p', texto: `Se deja constancia de la recepción de lo contratado, verificado conforme a las especificaciones técnicas. ${c?.observacionRecepcion ? 'Observaciones: ' + c.observacionRecepcion : 'Sin observaciones.'}` },
      { t: 'tabla', columnas: ['N°', 'Descripción', 'Unidad', 'Cantidad recibida'], anchos: [0.5, 5, 1, 1.5], derecha: [3], filas: d.items.map((i) => [i.numero, i.descripcion, i.unidad, i.cantidad]) },
    ],
    firmas: [{ cargo: 'Comisión / Responsable de Recepción' }, { cargo: 'Unidad Solicitante', nombre: d.proceso.solicitante?.nombre }, { cargo: 'PROVEEDOR' }],
  };
}

export const PLANTILLAS: Record<TipoGenerable, (d: DatosDoc) => DocSpec> = {
  SOLICITUD_C1: solicitudC1, JUSTIFICACION_CHB: justificacionChb, PREVENTIVO_C31: preventivoC31, DBC: dbc, INFORME_V1: informeV1, CUADRO_COMPARATIVO: cuadro,
  INFORME_EVALUACION: informeEvaluacion, ACTA_ADJUDICACION: actaAdjudicacion, CONTRATO: contrato, ORDEN_COMPRA_SERVICIO: contrato, ACTA_RECEPCION: actaRecepcion,
};
