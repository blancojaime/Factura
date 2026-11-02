using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using ComexBol.Presentation;
using Microsoft.Win32;

namespace ComexBol.App.Vistas;

public partial class OperacionesView : UserControl
{
    public OperacionesView() => InitializeComponent();
    MainViewModel Vm => (MainViewModel)DataContext;
    static Window? Ventana(DependencyObject d) => Window.GetWindow(d);

    static bool Confirmar(Window? w, string texto, string titulo = "Confirmar eliminación") =>
        MessageBox.Show(w!, texto, titulo, MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) == MessageBoxResult.Yes;

    async void EliminarOperacion_Click(object s, RoutedEventArgs e)
    {
        if (Vm.Seleccionada is null) { MessageBox.Show(Ventana(this)!, "Seleccione primero la operación que desea eliminar.", "COMEX JB", MessageBoxButton.OK, MessageBoxImage.Information); return; }
        if (Confirmar(Ventana(this), $"¿Eliminar la operación «{Vm.Seleccionada.Carpeta}» con TODO su contenido (ítems, liquidaciones, ruta, costos y bitácora)?\n\nEsta acción no se puede deshacer."))
            await Vm.EliminarOperacionAsync();
    }

    async void EliminarItem_Click(object s, RoutedEventArgs e)
    {
        if (Vm.ItemSeleccionado is null) { MessageBox.Show(Ventana(this)!, "Seleccione en la lista el ítem que desea eliminar.", "COMEX JB", MessageBoxButton.OK, MessageBoxImage.Information); return; }
        if (Confirmar(Ventana(this), $"¿Eliminar el ítem {Vm.ItemSeleccionado.Numero} (partida {Vm.ItemSeleccionado.Partida})?")) await Vm.EliminarItemAsync();
    }

    void GridItems_DoubleClick(object s, MouseButtonEventArgs e) { if (Vm.ItemSeleccionado is not null) Vm.EditarItemCmd.Execute(null); }

    // ---- Selector de partidas ----
    void Sugerencia_Elegida(object s, SelectionChangedEventArgs e)
    {
        if (ListaSugerencias.SelectedItem is SugerenciaPartida sug) { Vm.ElegirSugerencia(sug); ListaSugerencias.SelectedItem = null; TxtPartida.Focus(); TxtPartida.CaretIndex = TxtPartida.Text.Length; }
    }

    void TxtPartida_PreviewKeyDown(object s, KeyEventArgs e)
    {
        if (e.Key == Key.Down && Vm.MostrarSugerencias && Vm.Sugerencias.Count > 0) { ListaSugerencias.Focus(); ListaSugerencias.SelectedIndex = 0; e.Handled = true; }
        else if (e.Key == Key.Escape) Vm.MostrarSugerencias = false;
    }

    void ListaSugerencias_KeyDown(object s, KeyEventArgs e)
    {
        if (e.Key == Key.Escape) { Vm.MostrarSugerencias = false; TxtPartida.Focus(); }
    }

    // ---- Documento y OCR ----
    async void AbrirDocumento_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog { Filter = "Imágenes y PDF|*.jpg;*.jpeg;*.png;*.pdf", Title = "Factura u otro documento a leer" };
        if (dlg.ShowDialog() == true) await Vm.ProcesarDocumentoAsync(dlg.FileName);
    }

    void Cumplir_Click(object s, RoutedEventArgs e) { if (((Button)s).Tag is EtapaFila fila) Vm.CompletarEtapaCmd.Execute(fila); }

    // ---- Exportaciones ----
    async void ExportarExcel_Click(object s, RoutedEventArgs e)
    {
        if (Vm.Seleccionada is null) return;
        var dlg = new SaveFileDialog { Filter = "Excel|*.xlsx", FileName = $"Operacion-{Vm.Seleccionada.Carpeta}.xlsx" };
        if (dlg.ShowDialog() == true) await Vm.ExportarExcelAsync(dlg.FileName);
    }

    async void ExportarJson_Click(object s, RoutedEventArgs e)
    {
        if (Vm.Seleccionada is null) return;
        var dlg = new SaveFileDialog { Filter = "JSON|*.json", FileName = $"DMI-{Vm.Seleccionada.Carpeta}.json" };
        if (dlg.ShowDialog() == true) await Vm.ExportarJsonAsync(dlg.FileName);
    }

    async void ExportarExpediente_Click(object s, RoutedEventArgs e)
    {
        if (Vm.Seleccionada is null) return;
        var dlg = new SaveFileDialog { Filter = "Markdown|*.md", FileName = $"Expediente-{Vm.Seleccionada.Carpeta}.md" };
        if (dlg.ShowDialog() == true) await Vm.ExportarExpedienteAsync(dlg.FileName);
    }
}
