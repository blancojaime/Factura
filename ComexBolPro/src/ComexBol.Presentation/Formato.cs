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
}
