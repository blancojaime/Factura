using System.Globalization;

namespace ComexBol.Presentation;

/// <summary>Formato numérico boliviano fijo (1.234,56) para no depender de la configuración regional del equipo.</summary>
public static class Formato
{
    public static CultureInfo Bo { get; } = Crear();
    static CultureInfo Crear()
    {
        var c = (CultureInfo)CultureInfo.InvariantCulture.Clone();
        c.NumberFormat.NumberDecimalSeparator = ","; c.NumberFormat.NumberGroupSeparator = ".";
        c.NumberFormat.CurrencyDecimalSeparator = ","; c.NumberFormat.CurrencyGroupSeparator = ".";
        c.NumberFormat.PercentDecimalSeparator = ","; c.NumberFormat.PercentGroupSeparator = ".";
        c.NumberFormat.PercentPositivePattern = 1;     // "10%"
        c.DateTimeFormat.ShortDatePattern = "dd/MM/yyyy";
        return c;
    }

    /// <summary>
    /// Descripción resumida para llenar el formulario: la ruta completa del arancel («Partida / subpartida / ítem») con el encabezado
    /// acortado, porque el texto de la partida suele ser larguísimo.
    /// </summary>
    public static string DescripcionCorta(string completa, int max = 200)
    {
        if (string.IsNullOrWhiteSpace(completa)) return "";
        var partes = completa.Split(" / ", StringSplitOptions.RemoveEmptyEntries).Select(x => x.Trim()).ToList();
        if (partes.Count > 1)
        {
            var enc = partes[0]; var corte = enc.IndexOfAny([';', '(']);
            if (corte > 20) enc = enc[..corte].Trim();
            if (enc.Length > 60) { enc = enc[..60]; enc = enc[..Math.Max(enc.LastIndexOf(' '), 20)].TrimEnd(',', ' ') + "..."; }
            partes[0] = enc.TrimEnd('.', ' ');
        }
        var s = string.Join(" / ", partes);
        return s.Length <= max ? s : s[..(max - 3)].TrimEnd() + "...";
    }
}
