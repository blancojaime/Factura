namespace ComexBol.Core;

public sealed record GastosLocales(decimal HonorariosAgencia = 0m, decimal Almacenaje = 0m, decimal TransporteInterno = 0m, decimal Otros = 0m)
{
    public decimal Total => HonorariosAgencia + Almacenaje + TransporteInterno + Otros;
}

public sealed record CostoItem(int Numero, string Codigo, decimal Cantidad, decimal CifBob, decimal TributosNoRecuperables, decimal IvaCreditoFiscal,
    decimal GastosProrrateados, decimal CostoNacionalizadoBob, decimal Factor, decimal CostoUnitarioBob);

public sealed record CosteoResultado(IReadOnlyList<CostoItem> Items, decimal GastosLocalesBob, decimal CostoTotalBob, decimal FactorGlobal, decimal IvaCreditoFiscalTotal, decimal CashFlowRequeridoBob);

public static class Costeo
{
    /// <summary>
    /// Costo nacionalizado = CIF + GA + ICE + IEHD + gastos locales prorrateados (por CIF). El IVA de importación se trata como crédito fiscal (no es costo)
    /// salvo que el importador no pueda recuperarlo (<paramref name="ivaRecuperable"/> = false).
    /// Factor de importación = costo nacionalizado / valor FOB. Flujo de caja = tributos pagados en aduana + gastos locales.
    /// </summary>
    public static CosteoResultado Calcular(LiquidacionResultado r, IReadOnlyList<decimal> cantidades, GastosLocales gastos, bool ivaRecuperable = true)
    {
        var total = r.Items.Sum(i => i.CifBob);
        var lista = new List<CostoItem>();
        for (int k = 0; k < r.Items.Count; k++)
        {
            var i = r.Items[k]; var cant = k < cantidades.Count ? cantidades[k] : 0m;
            var cuota = total > 0 ? i.CifBob / total : 0m;
            var g = Math.Round(gastos.Total * cuota, 2, MidpointRounding.AwayFromZero);
            var noRec = i.GA + i.ICE + i.IEHD + (ivaRecuperable ? 0m : i.IVA);
            var costo = i.CifBob + noRec + g;
            lista.Add(new(i.Numero, i.CodigoArancelario, cant, i.CifBob, noRec, ivaRecuperable ? i.IVA : 0m, g, costo,
                i.ValorFobBob > 0 ? Math.Round(costo / i.ValorFobBob, 4) : 0m, cant > 0 ? Math.Round(costo / cant, 2, MidpointRounding.AwayFromZero) : 0m));
        }
        var costoTotal = lista.Sum(x => x.CostoNacionalizadoBob);
        return new(lista, gastos.Total, costoTotal, r.ValorFobBob > 0 ? Math.Round(costoTotal / r.ValorFobBob, 4) : 0m,
            lista.Sum(x => x.IvaCreditoFiscal), r.TotalTributos + gastos.Total);
    }

    /// <summary>Estimación de almacenaje: toneladas × días cobrables × tarifa (Bs por tonelada y día). Las tarifas las fija el concesionario: se configuran, no se suponen.</summary>
    public static decimal EstimarAlmacenaje(decimal pesoBrutoKg, int dias, int diasLibres, decimal tarifaBsPorTonDia)
        => Math.Round(Math.Max(0, dias - diasLibres) * (pesoBrutoKg / 1000m) * tarifaBsPorTonDia, 2, MidpointRounding.AwayFromZero);
}

/// <summary>Explica paso a paso cómo se obtuvo cada tributo (base legal y fórmula), para que el usuario pueda verificar el cálculo.</summary>
public static class ExplicadorLiquidacion
{
    public static IReadOnlyList<string> Pasos(OperacionImportacion op, LiquidacionResultado r, ParametrosTributarios p, System.Globalization.CultureInfo cul)
    {
        string F(decimal v) => v.ToString("N2", cul); string P(decimal v) => v.ToString("0.##%", cul);
        var l = new List<string>();
        l.Add($"Valor en aduana (CIF) = FOB {F(r.ValorFobBob)} + adiciones {F(r.AdicionesBob)} − deducciones {F(r.DeduccionesBob)} = {F(r.CifBob)} Bs (Decisión 571 CAN, arts. 1 y 8).");
        foreach (var it in op.Items)
        {
            var x = r.Items.FirstOrDefault(i => i.Numero == it.Numero); if (x is null) continue;
            l.Add($"Ítem {it.Numero} · {it.CodigoArancelario} · FOB {F(x.ValorFobBob)} → CIF {F(x.CifBob)} (incluye {F(x.CifBob - x.ValorFobBob)} de adiciones netas prorrateadas).");
            l.Add($"   GA  = CIF {F(x.CifBob)} × {P(it.AlicuotaGA)}{(it.DesgravacionPreferencial > 0 ? $" × (1 − {P(it.DesgravacionPreferencial)} preferencia)" : "")} = {F(x.GA)}");
            if (x.ICE > 0) l.Add($"   ICE = (CIF + GA {F(x.CifBob + x.GA)}) × {P(it.AlicuotaIceAdValorem)}{(it.IceEspecificoPorUnidad > 0 ? $" + {F(it.IceEspecificoPorUnidad)} × {it.UnidadesIce:0.##} unid." : "")} = {F(x.ICE)}");
            if (x.IEHD > 0) l.Add($"   IEHD = {F(it.IehdBsPorLitro)} Bs/litro × {it.Litros:0.##} litros = {F(x.IEHD)}");
            l.Add($"   IVA = {P(p.TasaIvaEfectiva)} × (CIF + GA + ICE + IEHD{(x.OtrasErogaciones > 0 ? " + otras erogaciones" : "")}) {F(x.CifBob + x.GA + x.ICE + x.IEHD + x.OtrasErogaciones)} = {F(x.IVA)}");
        }
        l.Add($"Total tributos = GA {F(r.GA)} + ICE {F(r.ICE)} + IEHD {F(r.IEHD)} + IVA {F(r.IVA)} = {F(r.TotalTributos)} Bs.");
        return l;
    }
}
