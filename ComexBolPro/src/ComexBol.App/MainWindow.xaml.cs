using System.Windows;
using ComexBol.Presentation;

namespace ComexBol.App;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        if (Environment.GetCommandLineArgs().Contains("--ventana")) WindowState = WindowState.Normal;     // opción para pruebas y capturas: tamaño fijo en lugar de maximizada
        Loaded += async (_, _) => { if (DataContext is ShellViewModel sh) await sh.InicializarAsync(); };
    }
}
