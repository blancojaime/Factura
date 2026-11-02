using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Markup;
using ComexBol.Data;
using ComexBol.Documentos;
using ComexBol.Presentation;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.App;

public partial class App : Application
{
    public static string CarpetaDatos { get; private set; } = "";
    ComexDb? _db;

    void OnStartup(object sender, StartupEventArgs e)
    {
        // Números, fechas y decimales siempre al estilo boliviano (1.234,56), sin importar la configuración regional del equipo.
        var cultura = CultureInfo.GetCultureInfo("es-BO");
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.DefaultThreadCurrentUICulture = cultura;
        FrameworkElement.LanguageProperty.OverrideMetadata(typeof(FrameworkElement), new FrameworkPropertyMetadata(XmlLanguage.GetLanguage(cultura.IetfLanguageTag)));

        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        CarpetaDatos = Path.Combine(local, "ComexJB"); Directory.CreateDirectory(CarpetaDatos);
        DispatcherUnhandledException += (_, ex) =>
        {
            try { File.AppendAllText(Path.Combine(CarpetaDatos, "errores.log"), $"{DateTime.Now:s} {ex.Exception}\n\n"); } catch { }
            MessageBox.Show("Ocurrió un error inesperado. Sus datos están guardados.\n\n" + ex.Exception.Message + $"\n\n(Detalle en {Path.Combine(CarpetaDatos, "errores.log")})", "COMEX JB", MessageBoxButton.OK, MessageBoxImage.Warning);
            ex.Handled = true;
        };

        MigrarDatosDeVersionAnterior(local);
        _db = new ComexDb(new DbContextOptionsBuilder<ComexDb>().UseSqlite($"Data Source={Path.Combine(CarpetaDatos, "comex.db")}").Options);
        _db.AsegurarEsquema();                 // crea la base o agrega columnas nuevas de versiones posteriores
        MostrarLogin();
    }

    /// <summary>La aplicación se llamaba «ComexBol Pro»: si hay datos de esa versión y aún no hay datos nuevos, se copian (los originales no se tocan).</summary>
    static void MigrarDatosDeVersionAnterior(string local)
    {
        var viejo = Path.Combine(local, "ComexBolPro", "comex.db"); var nuevo = Path.Combine(CarpetaDatos, "comex.db");
        if (File.Exists(viejo) && !File.Exists(nuevo)) { try { File.Copy(viejo, nuevo); } catch (IOException) { } }
    }

    void MostrarLogin()
    {
        var login = new LoginWindow(_db!);
        if (login.ShowDialog() != true || login.UsuarioAutenticado is null) { Shutdown(); return; }
        AbrirPrincipal(login.UsuarioAutenticado);
    }

    void AbrirPrincipal(Usuario usuario)
    {
        var shell = new ShellViewModel(_db!, usuario, ocr: new TesseractCliOcr());
        shell.Config.RutaBaseDatos = Path.Combine(CarpetaDatos, "comex.db");
        var ventana = new MainWindow { DataContext = shell };
        bool cerrandoSesion = false;
        shell.CerrarSesionSolicitada += () => { cerrandoSesion = true; ventana.Close(); MostrarLogin(); };
        ventana.Closed += (_, _) => { if (!cerrandoSesion) Shutdown(); };
        ventana.Show();
    }
}
