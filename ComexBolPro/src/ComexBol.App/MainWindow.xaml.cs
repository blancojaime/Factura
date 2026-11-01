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
        var dlg = new OpenFileDialog { Filter = "CSV|*.csv", Title = "Catálogo NANDINA (CSV)" };
        if (dlg.ShowDialog() != true) return;
        var r = await Vm.ImportarCatalogoAsync(dlg.FileName, DateTime.Today.ToString("yyyy.MM.dd"));
        if (r is { Errores.Count: > 0 })
            MessageBox.Show(string.Join("\n", r.Errores.Take(15).Select(x => $"Línea {x.Linea}: {x.Mensaje}")), "Filas rechazadas");
    }

    async void ExportarExpediente_Click(object s, RoutedEventArgs e)
    {
        var dlg = new SaveFileDialog { Filter = "Markdown|*.md", FileName = $"Expediente-{Vm.Seleccionada?.Carpeta}.md" };
        if (dlg.ShowDialog() == true) await Vm.ExportarExpedienteAsync(dlg.FileName);
    }

    void AbrirDocumento_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog { Filter = "Imágenes|*.jpg;*.jpeg;*.png" };
        if (dlg.ShowDialog() == true) Vm.DocumentoRuta = dlg.FileName;
    }

    void Cumplir_Click(object s, RoutedEventArgs e)
    {
        if (((Button)s).Tag is EtapaFila fila) Vm.CompletarEtapaCmd.Execute(fila);
    }
}
