namespace ComexBol.Core;

public sealed record ViabilidadImportacion(
    decimal CostoTotalPuestoEnAlmacen, decimal CostoUnitario,
    decimal PrecioVentaNetoUnitario, decimal MargenUnitario, decimal MargenPct);

public static class Viabilidad
{
    /// <summary>
    /// Costo puesto en almacén = CIF + GA + ICE + IEHD + gastos locales (+ IVA si NO es recuperable como crédito fiscal).
    /// El precio de mercado se compara neto de IVA (débito fiscal) cuando el importador es sujeto del IVA.
    /// </summary>
    public static ViabilidadImportacion Importacion(
        LiquidacionResultado liq, decimal gastosLocalesBob, decimal unidades,
        decimal precioMercadoUnitarioConIva, bool ivaRecuperable = true, decimal tasaIvaNominal = 0.13m)
    {
        if (unidades <= 0) throw new ArgumentOutOfRangeException(nameof(unidades));
        var costo = liq.CifBob + liq.GA + liq.ICE + liq.IEHD + gastosLocalesBob + (ivaRecuperable ? 0m : liq.IVA);
        var unit = costo / unidades;
        var precioNeto = ivaRecuperable ? precioMercadoUnitarioConIva / (1m + tasaIvaNominal) : precioMercadoUnitarioConIva;
        var margen = precioNeto - unit;
        return new(Math.Round(costo, 2), Math.Round(unit, 4), Math.Round(precioNeto, 4), Math.Round(margen, 4),
            precioNeto == 0 ? 0 : Math.Round(margen / precioNeto, 4));
    }
}

public sealed record TarifaAlmacenaje(int DiasLibres, decimal BsPorToneladaDia, decimal MinimoBs = 0m);

public static class Almacenaje
{
    /// <summary>Estimación DAB/ASP-B: días libres + tarifa por tonelada-día. Las tarifas son del concesionario (parámetro).</summary>
    public static decimal Estimar(TarifaAlmacenaje t, int diasEnDeposito, decimal pesoBrutoKg)
    {
        var diasCobrables = Math.Max(0, diasEnDeposito - t.DiasLibres);
        var monto = diasCobrables * (pesoBrutoKg / 1000m) * t.BsPorToneladaDia;
        return diasCobrables == 0 ? 0m : Math.Max(Math.Round(monto, 2), t.MinimoBs);
    }
}

public static class Exportacion
{
    /// <summary>
    /// CEDEIM estimado = min(impuestos vinculados a la exportación, límite × valor FOB exportado).
    /// El límite porcentual es un parámetro normativo vigente a validar; se exige explícito para no ocultar la suposición.
    /// </summary>
    public static decimal CedeimEstimado(decimal impuestosVinculadosBob, decimal fobExportadoBob, decimal limiteSobreFob)
    {
        if (limiteSobreFob is < 0 or > 1) throw new ArgumentOutOfRangeException(nameof(limiteSobreFob));
        return Math.Round(Math.Min(impuestosVinculadosBob, fobExportadoBob * limiteSobreFob), 2);
    }
}
