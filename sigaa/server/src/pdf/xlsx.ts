/** Exportación a Excel (exceljs) de reportes tabulares. */
import ExcelJS from 'exceljs';
import type { Col } from './builder.js';

export interface TablaXlsx {
  titulo: string;
  subtitulo?: string;
  entidad?: string;
  cols: Col[];
  filas: unknown[][];
  totales?: unknown[];
  hoja?: string;
}

export async function tablaAExcel(tablas: TablaXlsx | TablaXlsx[]): Promise<Buffer> {
  const wb = new ExcelJS.Workbook();
  wb.creator = 'SIGAA';
  wb.created = new Date();
  for (const t of Array.isArray(tablas) ? tablas : [tablas]) {
    const ws = wb.addWorksheet((t.hoja || t.titulo).replace(/[\\/*?:[\]]/g, ' ').slice(0, 31) || 'Reporte');
    const n = t.cols.length;
    let r = 1;
    if (t.entidad) {
      ws.mergeCells(r, 1, r, n);
      ws.getCell(r, 1).value = t.entidad;
      ws.getCell(r, 1).font = { bold: true, size: 12, color: { argb: 'FF1F3A5F' } };
      r++;
    }
    ws.mergeCells(r, 1, r, n);
    ws.getCell(r, 1).value = t.titulo;
    ws.getCell(r, 1).font = { bold: true, size: 13 };
    r++;
    if (t.subtitulo) {
      ws.mergeCells(r, 1, r, n);
      ws.getCell(r, 1).value = t.subtitulo;
      ws.getCell(r, 1).font = { italic: true, color: { argb: 'FF5A6270' } };
      r++;
    }
    r++;
    const head = ws.getRow(r);
    t.cols.forEach((c, i) => {
      const cell = head.getCell(i + 1);
      cell.value = c.header;
      cell.font = { bold: true, color: { argb: 'FFFFFFFF' } };
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1F3A5F' } };
      cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
    });
    const first = r + 1;
    const put = (vals: unknown[], bold = false) => {
      r++;
      const row = ws.getRow(r);
      t.cols.forEach((c, i) => {
        const cell = row.getCell(i + 1);
        const v = vals[i];
        cell.value = v === undefined || v === null || v === '' ? null : c.num && !isNaN(Number(v)) ? Number(v) : (v as ExcelJS.CellValue);
        if (c.num === 'money') cell.numFmt = '#,##0.00';
        else if (c.num === 'qty') cell.numFmt = '#,##0.####';
        else if (c.num === 'int') cell.numFmt = '0';
        if (c.align || c.num) cell.alignment = { horizontal: c.align ?? 'right' };
        if (bold) cell.font = { bold: true };
        cell.border = { top: { style: 'hair' }, bottom: { style: 'hair' }, left: { style: 'hair' }, right: { style: 'hair' } };
      });
    };
    r = head.number;
    for (const f of t.filas) put(f);
    if (t.totales) put(t.totales, true);
    t.cols.forEach((c, i) => {
      const maxLen = Math.max(c.header.length, ...t.filas.slice(0, 200).map((f) => String(f[i] ?? '').length));
      ws.getColumn(i + 1).width = Math.min(Math.max(10, maxLen + 2, (c.w ?? 1) * 6), 60);
    });
    ws.views = [{ state: 'frozen', ySplit: head.number }];
    ws.autoFilter = { from: { row: head.number, column: 1 }, to: { row: Math.max(head.number, first + t.filas.length - 1), column: n } };
  }
  return Buffer.from(await wb.xlsx.writeBuffer());
}
