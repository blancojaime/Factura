using System.Windows;
using ComexBol.Data;
using ComexBol.Presentation;

namespace ComexBol.App;

public partial class LoginWindow : Window
{
    readonly LoginViewModel _vm;
    public Usuario? UsuarioAutenticado { get; private set; }

    public LoginWindow(ComexDb db)
    {
        InitializeComponent();
        _vm = new LoginViewModel(db);
        Loaded += async (_, _) =>
        {
            await _vm.InicializarAsync();
            if (_vm.PrimerUso)
            {
                TxtSub.Text = "Primer uso: cree el usuario administrador. Con él configurará el arancel, los tipos de cambio y los demás usuarios.";
                PanelNombre.Visibility = PanelRepetir.Visibility = Visibility.Visible; BtnIngresar.Content = "Crear administrador e ingresar"; TxtNombre.Focus();
            }
            else TxtUsuario.Focus();
        };
    }

    async void Ingresar_Click(object s, RoutedEventArgs e)
    {
        BtnIngresar.IsEnabled = false;
        try
        {
            var u = _vm.PrimerUso ? await _vm.CrearAdministradorAsync(TxtUsuario.Text, TxtNombre.Text, TxtClave.Password, TxtRepetir.Password) : await _vm.IngresarAsync(TxtUsuario.Text, TxtClave.Password);
            TxtMensaje.Text = _vm.Mensaje;
            if (u is null) { TxtClave.Clear(); TxtRepetir.Clear(); if (_vm.PrimerUso) TxtUsuario.Focus(); else TxtClave.Focus(); return; }
            UsuarioAutenticado = u; DialogResult = true;
        }
        finally { BtnIngresar.IsEnabled = true; }
    }
}
