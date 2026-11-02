using System.Windows;
using System.Windows.Controls;
using ComexBol.Documentos;
using ComexBol.Presentation;
using Microsoft.Win32;

namespace ComexBol.App.Vistas;

public partial class ArancelView : UserControl
{
    public ArancelView() => InitializeComponent();
    CatalogoViewModel Vm => (CatalogoViewModel)DataContext;

    async void Importar_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog { Filter = "Arancel (*.pdf;*.md;*.csv)|*.pdf;*.md;*.csv", Title = "Arancel Aduanero: seleccione los 3 archivos PDF a la vez (Ctrl+clic)", Multiselect = true };
        if (dlg.ShowDialog() != true) return;
        var archivos = dlg.FileNames.OrderBy(f => f, StringComparer.OrdinalIgnoreCase).ToList();
        if (Vm.ArancelCargado && MessageBox.Show(Window.GetWindow(this)!, "Ya hay un arancel cargado. Al importar se REEMPLAZA todo el catálogo (incluidas las partidas agregadas o modificadas a mano). Sus operaciones no se alteran.\n\n¿Continuar?",
                "Reemplazar el arancel", MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) != MessageBoxResult.Yes) return;
        var version = archivos[0].EndsWith(".pdf", StringComparison.OrdinalIgnoreCase) ? ArancelPdf.DetectarVersion(archivos[0]) : null;
        var r = await Vm.ImportarAsync(archivos, version ?? DateTime.Today.Year.ToString());
        if (r is { Errores.Count: > 0 })
            MessageBox.Show(Window.GetWindow(this)!, string.Join("\n\n", r.Errores.Take(12).Select(x => x.Mensaje.Contains("pág.") || x.Mensaje.Contains("línea") ? x.Mensaje : $"Línea {x.Linea}: {x.Mensaje}"))
                + (r.Errores.Count > 12 ? $"\n\n… y {r.Errores.Count - 12} avisos más." : ""), "Avisos del arancel", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    async void Eliminar_Click(object s, RoutedEventArgs e)
    {
        if (Vm.Seleccionada is null) return;
        if (MessageBox.Show(Window.GetWindow(this)!, $"¿Eliminar la partida {Vm.Seleccionada.Codigo} del arancel?\n\nLas operaciones que ya la usan conservan su ítem, pero se avisará que la partida no existe en el catálogo.",
                "Confirmar eliminación", MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) == MessageBoxResult.Yes) await Vm.EliminarAsync();
    }
}
