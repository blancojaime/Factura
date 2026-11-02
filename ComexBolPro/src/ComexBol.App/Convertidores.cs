using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace ComexBol.App;

/// <summary>true → Collapsed, false → Visible (para banners del tipo «el arancel NO está cargado»).</summary>
public sealed class NegarBoolVisibilidad : IValueConverter
{
    public object Convert(object v, Type t, object p, CultureInfo c) => v is true ? Visibility.Collapsed : Visibility.Visible;
    public object ConvertBack(object v, Type t, object p, CultureInfo c) => throw new NotSupportedException();
}

/// <summary>Cantidad > 0 → Visible.</summary>
public sealed class HayElementosConverter : IValueConverter
{
    public object Convert(object v, Type t, object p, CultureInfo c) => v is int n && n > 0 ? Visibility.Visible : Visibility.Collapsed;
    public object ConvertBack(object v, Type t, object p, CultureInfo c) => throw new NotSupportedException();
}

/// <summary>«#RRGGBB» → pincel.</summary>
public sealed class ColorTextoConverter : IValueConverter
{
    public object Convert(object v, Type t, object p, CultureInfo c)
    {
        try { return new SolidColorBrush((Color)ColorConverter.ConvertFromString(v?.ToString() ?? "#9AA3AD")); }
        catch (FormatException) { return Brushes.Gray; }
    }
    public object ConvertBack(object v, Type t, object p, CultureInfo c) => throw new NotSupportedException();
}

/// <summary>true → «Nueva partida», false → «Modificar partida».</summary>
public sealed class TituloEditorConverter : IValueConverter
{
    public object Convert(object v, Type t, object p, CultureInfo c) => v is true ? "Nueva partida" : "Modificar partida";
    public object ConvertBack(object v, Type t, object p, CultureInfo c) => throw new NotSupportedException();
}
