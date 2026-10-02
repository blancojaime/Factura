import ExcelJS from 'exceljs';
import { sinTildes } from '../../core/util.js';
import type { CobroInput } from './otros.js';

const val = (v: ExcelJS.CellValue): string => {
  if (v === null || v === undefined) return '';
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  if (typeof v === 'object') return String((v as any).result ?? (v as any).text ?? '');
  return String(v).trim();
};

/** Interpreta la primera hoja del Excel del proveedor, con o sin encabezado. */
export async function leerCobrosXlsx(buf: Buffer): Promise<CobroInput[]> {
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(buf as any);
  const ws = wb.worksheets[0];
  if (!ws) return [];
  let idx: Record<string, number> | null = null;
  const out: CobroInput[] = [];
  ws.eachRow((row) => {
    const c = Array.from({ length: row.cellCount }, (_, i) => val(row.getCell(i + 1).value));
    const cab = c.map((x) => sinTildes(x).toLowerCase());
    if (!idx && cab.some((x) => x.includes('vale')) && cab.some((x) => x.includes('monto') || x.includes('importe'))) {
      idx = {};
      cab.forEach((x, i) => {
        if (x.includes('vale')) idx!.vale = i; else if (x.includes('fecha')) idx!.fecha = i; else if (x.includes('placa')) idx!.placa = i;
        else if (x.includes('litro')) idx!.litros = i; else if (x.includes('monto') || x.includes('importe')) idx!.monto = i; else if (x.includes('factura')) idx!.factura = i;
      });
      return;
    }
    const g = (k: string, d: number) => c[idx ? idx[k] ?? -1 : d] ?? '';
    const nv = Number(g('vale', 0).replace(/\D/g, ''));
    const monto = Number(g('monto', 4).replace(',', '.'));
    if (!nv || isNaN(monto)) return;
    const f = g('fecha', 1);
    out.push({ nro_vale: nv, fecha: /^\d{4}-\d{2}-\d{2}/.test(f) ? f.slice(0, 10) : undefined, placa: g('placa', 2), litros: Number(g('litros', 3).replace(',', '.')) || undefined, monto, factura: g('factura', 5) });
  });
  return out;
}
