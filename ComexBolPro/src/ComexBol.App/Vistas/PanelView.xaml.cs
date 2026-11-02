using System.Windows;
using System.Windows.Controls;
using ComexBol.Presentation;

namespace ComexBol.App.Vistas;

public partial class PanelView : UserControl
{
    public PanelView() { InitializeComponent(); Loaded += (_, _) => { if (Window.GetWindow(this)?.DataContext is ShellViewModel sh) TxtSaludo.Text = $"Bienvenido, {sh.NombreMostrado}"; }; }
    ShellViewModel? Shell => Window.GetWindow(this)?.DataContext as ShellViewModel;
    async void IrOperaciones_Click(object s, RoutedEventArgs e) { if (Shell is { } sh) await sh.Navegar("Operaciones"); }
    async void IrArancel_Click(object s, RoutedEventArgs e) { if (Shell is { } sh) await sh.Navegar("Arancel"); }
}
