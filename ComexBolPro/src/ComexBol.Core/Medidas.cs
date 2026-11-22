namespace ComexBol.Core;

/// <summary>
/// Medidas arancelarias temporales de Bolivia (gestión 2026-2027), aplicadas según la FECHA de la declaración (aceptación de la DIM).
/// Fuente: textos de consulta de la Gaceta Oficial. Verifique siempre contra la Gaceta y con su despachante.
/// </summary>
public static class MedidasArancelarias
{
    /// <summary>D.S. 5646 (29/06/2026): reduce 5 puntos las alícuotas del GA del Arancel 2026 hasta el 31/12/2027 y modifica la base imponible del GA (art. 20 RLGA). Vigente desde el 06/07/2026.</summary>
    public static readonly DateOnly Ds5646Desde = new(2026, 7, 6);
    public static readonly DateOnly Ds5646Hasta = new(2027, 12, 31);
    /// <summary>D.S. 5516 (13/01/2026): GA 0 % para maquinaria y equipos de ciertas industrias (Anexos 3 y 4, por subpartida) hasta el 31/12/2026.</summary>
    public static readonly DateOnly Ds5516Desde = new(2026, 1, 13);
    public static readonly DateOnly Ds5516Hasta = new(2026, 12, 31);
    /// <summary>Fracción del transporte y seguro hasta la aduana de frontera que integra la base del GA desde el D.S. 5646.</summary>
    public const decimal FraccionTransporteSeguro = 0.10m;

    /// <summary>¿Rige la nueva base imponible del GA (valor de transacción + carga y descarga + 10 % de transporte y seguro)?</summary>
    public static bool RigeNuevaBaseGa(DateOnly? fecha) => fecha is { } f && f >= Ds5646Desde;

    /// <summary>
    /// Alícuota del GA aplicable. <paramref name="aranceBase"/> es la del Arancel 2026 cargado (antes de los decretos).
    /// Con fecha nula no se aplica ninguna medida (régimen anterior).
    /// </summary>
    public static (decimal Alicuota, string Nota) AlicuotaGa(decimal aranceBase, bool beneficioDs5516, DateOnly? fecha)
    {
        if (fecha is not { } f) return (aranceBase, "");
        if (beneficioDs5516 && f >= Ds5516Desde && f <= Ds5516Hasta) return (0m, "D.S. 5516: GA 0 % (vigente hasta 31/12/2026)");
        var vencido = beneficioDs5516 && f > Ds5516Hasta;
        if (f >= Ds5646Desde && f <= Ds5646Hasta)
        {
            var nueva = Math.Max(0m, aranceBase - 0.05m);
            return (nueva, (vencido ? "El beneficio D.S. 5516 venció el 31/12/2026. " : "") + $"D.S. 5646: {aranceBase:P0} → {nueva:P0} (−5 puntos hasta 31/12/2027)");
        }
        return (aranceBase, vencido ? "El beneficio D.S. 5516 venció el 31/12/2026." : "");
    }
}

public sealed record FilaImpacto(string Concepto, decimal Anterior, decimal ConDs5646, decimal Aplicado)
{
    public decimal AhorroVsAnterior => Anterior - Aplicado;
}

public static class ImpactoMedidas
{
    /// <summary>Compara la liquidación con el régimen anterior (arancel sin decretos y GA sobre CIF), con el D.S. 5646 y con lo realmente aplicado.</summary>
    public static IReadOnlyList<FilaImpacto> Comparar(OperacionImportacion op, TipoCambioTable tc, ParametrosTributarios p)
    {
        var anterior = CalculadoraTributaria.Calcular(op with { FechaDeclaracion = null, Items = op.Items.Select(i => i with { BeneficioDs5516 = false }).ToList() }, tc, p);
        var f = op.FechaDeclaracion ?? tc.Fecha;
        var d5646 = CalculadoraTributaria.Calcular(op with { FechaDeclaracion = f < MedidasArancelarias.Ds5646Desde ? MedidasArancelarias.Ds5646Desde : f, Items = op.Items.Select(i => i with { BeneficioDs5516 = false }).ToList() }, tc, p);
        var real = CalculadoraTributaria.Calcular(op, tc, p);
        return [new("Gravamen arancelario (GA)", anterior.GA, d5646.GA, real.GA), new("IVA importaciones", anterior.IVA, d5646.IVA, real.IVA),
                new("ICE / IEHD", anterior.ICE + anterior.IEHD, d5646.ICE + d5646.IEHD, real.ICE + real.IEHD), new("TOTAL TRIBUTOS", anterior.TotalTributos, d5646.TotalTributos, real.TotalTributos)];
    }
}
