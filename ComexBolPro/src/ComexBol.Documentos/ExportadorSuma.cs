using System.Text.Json;
using ClosedXML.Excel;
using ComexBol.Core;
using ComexBol.Data;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Documentos;

/// <summary>
/// Hoja de transcripción para el SUMA: ordena los datos de la operación en las secciones que se llenan al registrar la DAV y la DIM.
/// Es un borrador de trabajo: la numeración de casillas oficiales depende del instructivo vigente de la Aduana y no se asume aquí.
/// </summary>
public static class ExportadorSuma
{
    public static async Task ExportarAsync(ComexDb db, int opId, string ruta)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Liquidaciones).Include(o => o.Documentos).FirstAsync(o => o.Id == opId);
        var perfil = await db.Perfiles.AsNoTracking().FirstOrDefaultAsync() ?? new PerfilImportador();
        var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault();
        var liq = ult is null ? null : JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson);
        using var wb = new XLWorkbook();

        void Seccion(IXLWorksheet ws, ref int fila, string titulo, IEnumerable<(string, object?)> campos)
        {
            ws.Cell(fila, 1).Value = titulo; ws.Cell(fila, 1).Style.Font.Bold = true; ws.Cell(fila, 1).Style.Fill.BackgroundColor = XLColor.FromHtml("#D7ECEB"); ws.Range(fila, 1, fila, 3).Merge(); fila++;
            foreach (var (k, v) in campos) { ws.Cell(fila, 1).Value = k; ws.Cell(fila, 2).Value = XLCellValue.FromObject(v ?? ""); fila++; }
            fila++;
        }

        var d = wb.AddWorksheet("DAV"); int f = 1;
        d.Cell(f++, 1).Value = $"Datos para la Declaración Andina del Valor — carpeta {op.Carpeta}"; d.Cell(1, 1).Style.Font.Bold = true; d.Cell(1, 1).Style.Font.FontSize = 13; f++;
        Seccion(d, ref f, "1 · Importador", [("Razón social", perfil.RazonSocial), ("NIT", perfil.Nit), ("Tipo de importador", perfil.TipoImportador), ("Dirección", perfil.Direccion), ("Ciudad", perfil.Ciudad), ("Agencia despachante", perfil.AgenciaDespachante)]);
        Seccion(d, ref f, "2 · Transacción comercial", [("Incoterm", op.Incoterm.ToString()), ("Moneda de la factura", op.MonedaFactura), ("Valor total de la factura", op.Items.Sum(i => i.ValorFactura)), ("Entidad financiera del pago", op.EntidadFinanciera), ("N.º de comprobante de pago (SWIFT)", op.NroComprobantePago)]);
        Seccion(d, ref f, "3 · Cuestionario de la DAV", [("¿Existe vinculación comprador-vendedor?", op.Vinculacion ? "SÍ" : "NO"), ("¿Influyó en el precio?", op.VinculacionInfluyoPrecio ? "SÍ" : "NO"), ("¿Restricciones a la cesión o utilización?", op.RestriccionesCesion ? "SÍ" : "NO"),
            ("¿Condiciones o contraprestaciones no cuantificables?", op.CondicionesNoCuantificables ? "SÍ" : "NO"), ("¿Reversión al vendedor?", op.ReversionAlVendedor ? "SÍ" : "NO"), ("Cuestionario respondido en COMEX JB", op.CuestionarioRespondido ? "SÍ" : "NO")]);
        Seccion(d, ref f, $"4 · Ajustes al precio (moneda de la factura: {op.MonedaFactura})", [("Fletes y transporte internacional", op.Flete), ("Seguro", op.Seguro), ("Gastos de origen", op.GastosOrigen), ("Gastos hasta la frontera", op.OtrosGastosFrontera), ("Carga y descarga", op.CargaDescarga),
            ("Comisiones y corretajes", op.AdComisiones), ("Envases y embalajes", op.AdEnvases), ("Prestaciones (assists)", op.AdAssists), ("Cánones y licencias", op.AdRoyalties), ("Reversiones", op.AdReversiones), ("Otras adiciones", op.AdOtros),
            ("Deducción: armado posterior", op.DedArmadoPosterior), ("Deducción: transporte posterior", op.DedTransportePosterior), ("Deducción: impuestos en Bolivia", op.DedImpuestosBolivia)]);
        if (liq?.Desglose is not null) Seccion(d, ref f, "5 · Determinación del valor en aduana (Bs)", liq.Desglose.Select(l => (l.Concepto, (object?)l.Bob)));
        d.Column(1).Width = 58; d.Column(2).Width = 34;

        var m = wb.AddWorksheet("DIM-General"); f = 1;
        m.Cell(f++, 1).Value = $"Datos generales de la DIM — carpeta {op.Carpeta}"; m.Cell(1, 1).Style.Font.Bold = true; m.Cell(1, 1).Style.Font.FontSize = 13; f++;
        Seccion(m, ref f, "Declaración", [("Tipo de despacho", op.TipoDespacho), ("Régimen aduanero", op.Regimen), ("Fecha de aceptación de la DIM (para medidas arancelarias)", op.FechaDeclaracion?.ToString("yyyy-MM-dd")), ("Aduana de ingreso", op.AduanaIngreso), ("Aduana de destino", op.AduanaDestino),
            ("Código de declarante / ADA", op.CodigoDeclarante), ("N.º de DAV", op.NroDav), ("N.º de DIM", op.NroDim), ("Canal asignado", op.Canal), ("Fecha de levante", op.FechaLevante?.ToString("yyyy-MM-dd"))]);
        Seccion(m, ref f, "Transporte", [("Modalidad", op.ModalidadTransporte), (Despacho.DocumentoEmbarque(op.ModalidadTransporte), op.NroDocEmbarque), (Despacho.DocumentoManifiesto(op.ModalidadTransporte), op.NroManifiesto), ("Bultos", op.Bultos), ("Peso bruto del manifiesto (kg)", op.PesoBrutoManifiestoKg), ("Peso bruto de los ítems (kg)", op.Items.Sum(i => i.PesoBrutoKg))]);
        if (liq is not null) Seccion(m, ref f, "Liquidación de tributos (Bs)", [("Valor FOB", liq.ValorFobBob), ("CIF frontera", liq.CifBob), ("GA", liq.GA), ("ICE", liq.ICE), ("IEHD", liq.IEHD), ("IVA", liq.IVA), ("TOTAL TRIBUTOS", liq.TotalTributos)]);
        m.Column(1).Width = 58; m.Column(2).Width = 34;

        var it = wb.AddWorksheet("DIM-Ítems");
        string[] enc = ["Ítem", "Partida NANDINA", "Descripción comercial", "Marca", "Modelo", "Serie", "País de origen", "Cantidad", "Valor factura", "Peso bruto kg", "Peso neto kg", "Acuerdo", "Desgrav. %", "Beneficio D.S. 5516", "Alícuota GA aplicada", "Base imponible GA (Bs)", "CIF (Bs)", "GA (Bs)", "ICE (Bs)", "IEHD (Bs)", "IVA (Bs)"];
        for (int c = 0; c < enc.Length; c++) { it.Cell(1, c + 1).Value = enc[c]; it.Cell(1, c + 1).Style.Font.Bold = true; it.Cell(1, c + 1).Style.Fill.BackgroundColor = XLColor.FromHtml("#D7ECEB"); }
        int r = 2;
        foreach (var i in op.Items.OrderBy(x => x.Numero))
        {
            var x = liq?.Items.FirstOrDefault(y => y.Numero == i.Numero);
            object?[] v = [i.Numero, i.CodigoNandina, i.Descripcion, i.Marca, i.Modelo, i.Serie, i.PaisOrigen, i.Cantidad, i.ValorFactura, i.PesoBrutoKg, i.PesoNetoKg, i.AcuerdoPreferencial, i.Desgravacion * 100m, i.BeneficioDs5516 ? "SÍ" : "NO",
                x is not null ? x.AlicuotaGAAplicada : i.AlicuotaGA, x?.BaseGA, x?.CifBob, x?.GA, x?.ICE, x?.IEHD, x?.IVA];
            for (int c = 0; c < v.Length; c++) it.Cell(r, c + 1).Value = XLCellValue.FromObject(v[c] ?? ""); r++;
        }
        it.Columns().AdjustToContents();
        var n = wb.AddWorksheet("Nota");
        n.Cell(1, 1).Value = "Borrador de transcripción generado por COMEX JB. Verifique cada dato contra la normativa y el instructivo vigente del SUMA antes de declarar; la liquidación oficial la determina la Aduana Nacional.";
        n.Column(1).Width = 120; n.Cell(1, 1).Style.Alignment.WrapText = true;
        wb.SaveAs(ruta);
    }
}
