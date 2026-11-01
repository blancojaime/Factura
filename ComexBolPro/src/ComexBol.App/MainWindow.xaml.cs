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
        var dlg = new OpenFileDialog { Filter = "Arancel (*.md;*.csv)|*.md;*.csv", Title = "Arancel Aduanero (seleccione los 3 archivos .md a la vez, o un CSV)", Multiselect = true };
        if (dlg.ShowDialog() != true) return;
        var r = await Vm.ImportarCatalogoAsync(dlg.FileNames.OrderBy(f => f).ToList(), "2026");
        if (r is { Errores.Count: > 0 })
            MessageBox.Show(string.Join("\n", r.Errores.Take(15).Select(x => $"Línea {x.Linea}: {x.Mensaje}")), "Filas rechazadas");
    }

    async void ExportarExpediente_Click(object s, RoutedEventArgs e)
    {
        var dlg = new SaveFileDialog { Filter = "Markdown|*.md", FileName = $"Expediente-{Vm.Seleccionada?.Carpeta}.md" };
        if (dlg.ShowDialog() == true) await Vm.ExportarExpedienteAsync(dlg.FileName);
    }

    async void AbrirDocumento_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog { Filter = "Imágenes|*.jpg;*.jpeg;*.png" };
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
