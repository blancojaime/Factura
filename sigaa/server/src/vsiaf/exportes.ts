/** Exportación a Excel: libro del «Importador Excel → VSIAF» e informe de validación/importación. */
import ExcelJS from 'exceljs';
import type { Libro, Hoja } from './importador.js';
import { ORDEN_HOJAS } from './importador.js';
import type { ValidacionLote } from './servicio.js';

interface Col { name: string; req: boolean; width: number }
const U: Col = { name: 'unidad', req: false, width: 9 };
/** Encabezados idénticos a los del libro del Importador (los obligatorios van en naranja). */
export const COLUMNAS: Record<Hoja, Col[]> = {
  UNIDADES: [{ name: 'unidad', req: true, width: 9 }, { name: 'descripcion', req: true, width: 40 }, { name: 'ciudad', req: false, width: 18 }],
  OFICINAS: [U, { name: 'oficina', req: true, width: 40 }, { name: 'observacion', req: false, width: 30 }],
  RESPONSABLES: [U, { name: 'oficina', req: true, width: 34 }, { name: 'responsable', req: true, width: 34 }, { name: 'cargo', req: true, width: 34 }, { name: 'ci', req: false, width: 14 }, { name: 'expedido', req: false, width: 10 }, { name: 'observacion', req: false, width: 25 }],
  AUXILIARES: [U, { name: 'grupo_contable', req: true, width: 36 }, { name: 'auxiliar', req: true, width: 34 }, { name: 'observacion', req: false, width: 25 }],
  ACTIVOS: [U, { name: 'codigo', req: true, width: 18 }, { name: 'codigo_adicional', req: false, width: 16 }, { name: 'descripcion', req: true, width: 45 }, { name: 'grupo_contable', req: true, width: 32 }, { name: 'auxiliar', req: true, width: 22 }, { name: 'oficina', req: true, width: 28 }, { name: 'responsable', req: true, width: 30 }, { name: 'estado_bien', req: true, width: 11 }, { name: 'fecha_incorporacion', req: true, width: 14 }, { name: 'costo_inicial', req: true, width: 14 }, { name: 'vida_util', req: false, width: 10 }, { name: 'dep_acumulada_inicial', req: false, width: 14 }, { name: 'cod_rube', req: false, width: 14 }, { name: 'organismo_financiador', req: true, width: 12 }, { name: 'nro_convenio', req: false, width: 12 }, { name: 'observaciones', req: false, width: 30 }, { name: 'estado_registro', req: false, width: 12 }, { name: 'incorporacion_especial', req: false, width: 12 }],
  REVALUOS: [U, { name: 'codigo', req: true, width: 18 }, { name: 'fecha_revaluo', req: true, width: 14 }, { name: 'nuevo_costo', req: true, width: 14 }, { name: 'nueva_vida_util', req: true, width: 10 }, { name: 'disposicion_respaldo', req: true, width: 18 }, { name: 'motivo', req: false, width: 40 }],
  TRANSFERENCIAS: [{ name: 'unidad_origen', req: false, width: 9 }, { name: 'codigo', req: true, width: 18 }, { name: 'unidad_destino', req: false, width: 9 }, { name: 'oficina_destino', req: true, width: 30 }, { name: 'responsable_destino', req: true, width: 30 }, { name: 'auxiliar_destino', req: false, width: 22 }],
  BAJAS: [U, { name: 'codigo', req: true, width: 18 }, { name: 'fecha_baja', req: true, width: 14 }, { name: 'motivo_baja', req: true, width: 30 }, { name: 'disposicion_respaldo', req: true, width: 18 }, { name: 'observaciones', req: false, width: 40 }],
};

const AZUL = 'FF1F3864', NARANJA = 'FFC55A11', BLANCO = 'FFFFFFFF';
const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;
const celda = (v: unknown): ExcelJS.CellValue => {
  if (v === null || v === undefined) return null;
  if (typeof v === 'string') { const m = ISO.exec(v); return m ? `${m[3]}/${m[2]}/${m[1]}` : v; }
  return v as ExcelJS.CellValue;
};
function encabezado(ws: ExcelJS.Worksheet, cols: { name: string; req: boolean; width: number }[]) {
  ws.addRow(cols.map((c) => c.name));
  cols.forEach((c, i) => {
    const x = ws.getCell(1, i + 1);
    x.font = { bold: true, color: { argb: BLANCO } };
    x.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: c.req ? NARANJA : AZUL } };
    ws.getColumn(i + 1).width = c.width;
  });
  ws.views = [{ state: 'frozen', ySplit: 1 }];
}

/** Libro con las mismas hojas y columnas que el del Importador Excel → VSIAF. */
export async function libroExcel(libro: Libro, nota: string): Promise<Buffer> {
  const wb = new ExcelJS.Workbook();
  const l = wb.addWorksheet('LEEME');
  l.getColumn(1).width = 130;
  [['Libro generado por SIGAA para el «Importador Excel → VSIAF»', 't'], [nota, ''], ['Las hojas se procesan en el orden: UNIDADES → OFICINAS → RESPONSABLES → AUXILIARES → ACTIVOS → REVALUOS → TRANSFERENCIAS → BAJAS.', ''], ['Después de importar: abra el VSIAF → Administradores → Re-indexar y revise el Reporte 6.', '']].forEach(([t, k], i) => {
    const c = l.getCell(i + 1, 1); c.value = t; c.alignment = { wrapText: true, vertical: 'top' };
    if (k === 't') c.font = { bold: true, size: 16, color: { argb: AZUL } };
  });
  for (const h of ORDEN_HOJAS) {
    const ws = wb.addWorksheet(h);
    const cols = COLUMNAS[h];
    encabezado(ws, cols);
    for (const f of libro[h] ?? []) ws.addRow(cols.map((c) => celda(f.datos[c.name])));
  }
  return Buffer.from(await wb.xlsx.writeBuffer());
}

function hojaTabla(wb: ExcelJS.Workbook, nombre: string, filas: Record<string, unknown>[], numericas: string[] = []) {
  const ws = wb.addWorksheet(nombre);
  const claves = [...new Set(filas.flatMap((f) => Object.keys(f)))];
  encabezado(ws, claves.map((k) => ({ name: k, req: false, width: Math.max(12, Math.min(40, k.length + 4)) })));
  for (const f of filas) ws.addRow(claves.map((k) => celda(f[k])));
  claves.forEach((k, i) => { if (numericas.includes(k)) ws.getColumn(i + 1).numFmt = '#,##0.00'; });
  return ws;
}

/** Informe de validación / importación (RESUMEN, INCIDENCIAS, CÁLCULO por hoja y totales por grupo). */
export async function informeExcel(v: ValidacionLote, titulo: string, extra: [string, unknown][] = []): Promise<Buffer> {
  const wb = new ExcelJS.Workbook();
  const r = wb.addWorksheet('RESUMEN');
  r.getColumn(1).width = 42; r.getColumn(2).width = 40;
  r.getCell(1, 1).value = titulo; r.getCell(1, 1).font = { bold: true, size: 14, color: { argb: AZUL } };
  const filas: [string, unknown][] = [...extra, ['Resultado', v.sinErrores ? 'Sin errores' : 'Con errores'], ['Errores', v.errores], ['Avisos', v.avisos],
    ['Activos', v.resumen.activos], ['Transferencias', v.resumen.transferencias], ['Bajas', v.resumen.bajas], ['Oficinas nuevas', v.resumen.oficinas], ['Responsables nuevos', v.resumen.responsables], ['Auxiliares nuevos', v.resumen.auxiliares], ['Paso final', v.pasoFinal]];
  filas.forEach(([k, x], i) => { r.getCell(i + 3, 1).value = k; r.getCell(i + 3, 1).font = { bold: true }; r.getCell(i + 3, 2).value = celda(x); r.getCell(i + 3, 2).alignment = { wrapText: true, vertical: 'top' }; });
  hojaTabla(wb, 'INCIDENCIAS', v.incidencias.map((i) => ({ nivel: i.nivel, tipo: i.tipo, codigo: i.codigo, campo: i.etiqueta, mensaje: i.mensaje })));
  if (v.faltantes.length) hojaTabla(wb, 'EQUIVALENCIAS_FALTANTES', v.faltantes.map((f) => ({ tipo: f.tipo, 'valor SIGAA': f.clave, detalle: f.detalle, sugerencia: f.sugerencia ?? '' })));
  if (v.omitidos.length) hojaTabla(wb, 'OMITIDOS', v.omitidos.map((o) => ({ codigo: o.codigo, motivo: o.motivo })));
  const calc = ['costo_historico', 'actualizacion_gestion', 'costo_total_actualizado', 'dep_gestion', 'actualizacion_dep_acumulada', 'dep_acumulada', 'valor_neto'];
  if (v.totalesPorGrupo.length) hojaTabla(wb, 'TOTALES_POR_GRUPO', v.totalesPorGrupo, calc);
  for (const [k, n] of [['ACTIVOS', 'CALCULO_ACTIVOS'], ['REVALUOS', 'CALCULO_REVALUOS'], ['TRANSFERENCIAS', 'CALCULO_TRANSFERENCIAS'], ['BAJAS', 'CALCULO_BAJAS']] as const) {
    const f = v.calculos[k]; if (f?.length) hojaTabla(wb, n, f, calc);
  }
  return Buffer.from(await wb.xlsx.writeBuffer());
}
