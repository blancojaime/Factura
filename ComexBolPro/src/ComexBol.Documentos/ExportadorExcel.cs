using System.Text.Json;
using ClosedXML.Excel;
using ComexBol.Core;
using ComexBol.Data;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Documentos;

/// <summary>Libro Excel de la operación: resumen, ítems, liquidación por ítem, ruta y bitácora. Los totales son fórmulas vivas.</summary>
public static class ExportadorExcel
{
    public static async Task ExportarAsync(ComexDb db, int opId, string ruta, DateOnly hoy)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Etapas).Include(o => o.Bitacora).Include(o => o.Liquidaciones).FirstAsync(o => o.Id == opId);
        var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault();
        using var wb = new XLWorkbook();

        var r = wb.AddWorksheet("Resumen");
        r.Cell(1, 1).Value = $"Importación {op.Carpeta}"; r.Cell(1, 1).Style.Font.Bold = true; r.Cell(1, 1).Style.Font.FontSize = 14;
        var datos = new (string, object)[] { ("Incoterm", op.Incoterm.ToString()), ("Moneda factura", op.MonedaFactura), ("Inicio", op.FechaInicio.ToString("yyyy-MM-dd")),
            ("Flete", op.Flete), ("Seguro", op.Seguro), ("Gastos de origen", op.GastosOrigen), ("Gastos hasta frontera", op.OtrosGastosFrontera),
            ("Liquidación vigente", ult is null ? "sin liquidar" : $"v{ult.Version} · TC al {ult.TipoCambioFecha:yyyy-MM-dd}") };
        for (int i = 0; i < datos.Length; i++) { r.Cell(3 + i, 1).Value = datos[i].Item1; r.Cell(3 + i, 2).Value = XLCellValue.FromObject(datos[i].Item2); }
        r.Column(1).Style.Font.Bold = true; r.Columns().AdjustToContents();

        var it = wb.AddWorksheet("Ítems");
        string[] h = ["N.º", "Partida", "Descripción", "Valor factura", "Peso bruto kg", "GA %", "ICE %", "Antigüedad"];
        for (int c = 0; c < h.Length; c++) it.Cell(1, c + 1).Value = h[c];
        int f = 2;
        foreach (var i in op.Items.OrderBy(i => i.Numero))
        { it.Cell(f, 1).Value = i.Numero; it.Cell(f, 2).Value = i.CodigoNandina; it.Cell(f, 3).Value = i.Descripcion; it.Cell(f, 4).Value = i.ValorFactura; it.Cell(f, 5).Value = i.PesoBrutoKg; it.Cell(f, 6).Value = i.AlicuotaGA; it.Cell(f, 7).Value = i.AlicuotaIce; it.Cell(f, 8).Value = i.AntiguedadAnios; f++; }
        it.Cell(f, 3).Value = "TOTAL"; it.Cell(f, 4).FormulaA1 = $"SUM(D2:D{f - 1})"; it.Cell(f, 5).FormulaA1 = $"SUM(E2:E{f - 1})";
        it.Range(f, 1, f, 8).Style.Font.Bold = true;
        it.Range(2, 6, f, 7).Style.NumberFormat.Format = "0.00%"; it.Range(2, 4, f, 5).Style.NumberFormat.Format = "#,##0.00";

        if (ult is not null)
        {
            var res = JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson)!;
            var l = wb.AddWorksheet("Liquidación");
            string[] hl = ["N.º", "Partida", "FOB Bs", "CIF Bs", "GA", "ICE", "IEHD", "IVA", "Total tributos"];
            for (int c = 0; c < hl.Length; c++) l.Cell(1, c + 1).Value = hl[c];
            int g = 2;
            foreach (var x in res.Items)
            {
                l.Cell(g, 1).Value = x.Numero; l.Cell(g, 2).Value = x.CodigoArancelario; l.Cell(g, 3).Value = x.ValorFobBob; l.Cell(g, 4).Value = x.CifBob;
                l.Cell(g, 5).Value = x.GA; l.Cell(g, 6).Value = x.ICE; l.Cell(g, 7).Value = x.IEHD; l.Cell(g, 8).Value = x.IVA; l.Cell(g, 9).FormulaA1 = $"E{g}+F{g}+G{g}+H{g}"; g++;
            }
            l.Cell(g, 2).Value = "TOTAL";
            foreach (var col in "CDEFGHI") l.Range($"{col}{g}:{col}{g}").FirstCell().FormulaA1 = $"SUM({col}2:{col}{g - 1})";
            l.Range(g, 1, g, 9).Style.Font.Bold = true; l.Range(2, 3, g, 9).Style.NumberFormat.Format = "#,##0.00";
            l.Cell(g + 2, 2).Value = res.RequiereBancarizacion ? "Requiere bancarización (D.S. 772)" : "No requiere bancarización";
            foreach (var a in res.Advertencias.Select((t, k) => (t, k))) l.Cell(g + 3 + a.k, 2).Value = "⚠ " + a.t;
            l.Columns().AdjustToContents();
        }

        var ru = wb.AddWorksheet("Ruta crítica");
        string[] hr = ["Etapa", "Descripción", "Responsable", "Inicio plan", "Fin plan", "Fin real", "Estado", "Crítica"];
        for (int c = 0; c < hr.Length; c++) ru.Cell(1, c + 1).Value = hr[c];
        int k2 = 2;
        foreach (var e in op.Etapas.OrderBy(e => e.InicioPlan).ThenBy(e => e.Codigo))
        {
            ru.Cell(k2, 1).Value = e.Codigo; ru.Cell(k2, 2).Value = e.Nombre; ru.Cell(k2, 3).Value = e.Responsable;
            ru.Cell(k2, 4).Value = e.InicioPlan.ToDateTime(TimeOnly.MinValue); ru.Cell(k2, 5).Value = e.FinPlan.ToDateTime(TimeOnly.MinValue);
            if (e.FinReal is { } fr) ru.Cell(k2, 6).Value = fr.ToDateTime(TimeOnly.MinValue);
            ru.Cell(k2, 7).Value = Seguimiento.Evaluar(e.InicioPlan, e.FinPlan, e.FinReal, hoy).ToString(); ru.Cell(k2, 8).Value = e.EsCritica ? "Sí" : ""; k2++;
        }
        ru.Range(2, 4, k2, 6).Style.DateFormat.Format = "dd/MM/yyyy";

        var bi = wb.AddWorksheet("Bitácora");
        bi.Cell(1, 1).Value = "Fecha"; bi.Cell(1, 2).Value = "Categoría"; bi.Cell(1, 3).Value = "Detalle";
        int b = 2; foreach (var e in op.Bitacora.OrderBy(e => e.Fecha)) { bi.Cell(b, 1).Value = e.Fecha; bi.Cell(b, 2).Value = e.Categoria; bi.Cell(b, 3).Value = e.Detalle; b++; }

        foreach (var ws in wb.Worksheets) { ws.Row(1).Style.Font.Bold = true; if (ws.Name != "Resumen") ws.Row(1).Style.Fill.BackgroundColor = XLColor.FromHtml("#14304F"); if (ws.Name != "Resumen") ws.Row(1).Style.Font.FontColor = XLColor.White; ws.Columns().AdjustToContents(80); }
        wb.SaveAs(ruta);
    }
}
