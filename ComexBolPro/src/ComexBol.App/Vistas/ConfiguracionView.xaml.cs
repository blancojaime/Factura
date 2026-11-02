using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using ComexBol.Presentation;
using Microsoft.Win32;

namespace ComexBol.App.Vistas;

public partial class ConfiguracionView : UserControl
{
    public ConfiguracionView() => InitializeComponent();
    ConfiguracionViewModel Vm => (ConfiguracionViewModel)DataContext;
    static bool Confirmar(DependencyObject d, string texto) =>
        MessageBox.Show(Window.GetWindow(d)!, texto, "Confirmar eliminación", MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) == MessageBoxResult.Yes;

    async void EliminarTc_Click(object s, RoutedEventArgs e) { if (Vm.TcSeleccionado is not null && Confirmar(this, $"¿Eliminar el tipo de cambio {Vm.TcSeleccionado.Moneda} del {Vm.TcSeleccionado.Fecha:dd/MM/yyyy}?")) await Vm.EliminarTcAsync(); }
    async void EliminarUfv_Click(object s, RoutedEventArgs e) { if (Vm.UfvSeleccionada is not null && Confirmar(this, $"¿Eliminar la UFV del {Vm.UfvSeleccionada.Fecha:dd/MM/yyyy}?")) await Vm.EliminarUfvAsync(); }

    async void CrearUsuario_Click(object s, RoutedEventArgs e)
    {
        await Vm.CrearUsuarioAsync(TxtNuevoUsuario.Text, TxtNuevoNombre.Text, TxtNuevaClave.Password, CmbRol.SelectedItem as string ?? "Operador");
        if (Vm.Mensaje.StartsWith("Usuario")) { TxtNuevoUsuario.Clear(); TxtNuevoNombre.Clear(); TxtNuevaClave.Clear(); }
    }

    async void CambiarClave_Click(object s, RoutedEventArgs e) { await Vm.CambiarClaveAsync(TxtClaveReset.Password); if (Vm.Mensaje.StartsWith("Clave")) TxtClaveReset.Clear(); }
    void AlternarActivo_Click(object s, RoutedEventArgs e) { }          // el comando hace el trabajo
    async void HacerAdmin_Click(object s, RoutedEventArgs e) => await Vm.CambiarRolAsync("Administrador");
    async void HacerOperador_Click(object s, RoutedEventArgs e) => await Vm.CambiarRolAsync("Operador");

    async void Respaldo_Click(object s, RoutedEventArgs e)
    {
        var dlg = new SaveFileDialog { Filter = "Base de datos COMEX JB|*.db", FileName = $"ComexJB-respaldo-{DateTime.Today:yyyyMMdd}.db", Title = "Guardar copia de seguridad" };
        if (dlg.ShowDialog() == true) await Vm.RespaldarAsync(dlg.FileName);
    }

    void AbrirCarpeta_Click(object s, RoutedEventArgs e)
    {
        var dir = Path.GetDirectoryName(Vm.RutaBaseDatos);
        if (!string.IsNullOrEmpty(dir) && Directory.Exists(dir)) Process.Start(new ProcessStartInfo("explorer.exe", $"\"{dir}\"") { UseShellExecute = true });
    }
}
