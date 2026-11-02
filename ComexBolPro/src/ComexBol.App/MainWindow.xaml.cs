using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using ComexBol.Presentation;
using Microsoft.Win32;

namespace ComexBol.App;

public partial class MainWindow : Window
{
    MainViewModel Vm => (MainViewModel)DataContext;

    public MainWindow()
    {
        InitializeComponent();
        InputBindings.Add(new KeyBinding(new RelayCommand(() => Vm.LiquidarAsync()), Key.F5, ModifierKeys.None));
    }

    async void ImportarCatalogo_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog { Filter = "Arancel (*.pdf;*.md;*.csv)|*.pdf;*.md;*.csv", Title = "Arancel Aduanero 2026: seleccione los 3 archivos PDF a la vez (Ctrl+clic)", Multiselect = true };
        if (dlg.ShowDialog() != true) return;
        var r = await Vm.ImportarCatalogoAsync(dlg.FileNames.OrderBy(f => f).ToList(), "2026");
        if (r is { Errores.Count: > 0 })
            MessageBox.Show(string.Join("\n\n", r.Errores.Take(15).Select(x => x.Mensaje.Contains("pág.") || x.Mensaje.Contains("línea") ? x.Mensaje : $"Línea {x.Linea}: {x.Mensaje}"))
                + (r.Errores.Count > 15 ? $"\n\n… y {r.Errores.Count - 15} avisos más." : ""), "Avisos del arancel");
    }

    async void ExportarExpediente_Click(object s, RoutedEventArgs e)
    {
        var dlg = new SaveFileDialog { Filter = "Markdown|*.md", FileName = $"Expediente-{Vm.Seleccionada?.Carpeta}.md" };
        if (dlg.ShowDialog() == true) await Vm.ExportarExpedienteAsync(dlg.FileName);
    }

    async void ExportarExcel_Click(object s, RoutedEventArgs e)
    {
        var dlg = new SaveFileDialog { Filter = "Excel|*.xlsx", FileName = $"Operacion-{Vm.Seleccionada?.Carpeta}.xlsx" };
        if (dlg.ShowDialog() == true) await Vm.ExportarExcelAsync(dlg.FileName);
    }

    async void AbrirDocumento_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog { Filter = "Imágenes y PDF|*.jpg;*.jpeg;*.png;*.pdf" };
        if (dlg.ShowDialog() == true) await Vm.ProcesarDocumentoAsync(dlg.FileName);
    }

    void Cumplir_Click(object s, RoutedEventArgs e)
    {
        if (((Button)s).Tag is EtapaFila fila) Vm.CompletarEtapaCmd.Execute(fila);
    }
}

public sealed class HayElementosConverter : System.Windows.Data.IValueConverter
{
    public object Convert(object v, Type t, object p, System.Globalization.CultureInfo c) => v is int n && n > 0 ? Visibility.Visible : Visibility.Collapsed;
    public object ConvertBack(object v, Type t, object p, System.Globalization.CultureInfo c) => throw new NotSupportedException();
}
