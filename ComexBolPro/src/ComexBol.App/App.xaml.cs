using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Markup;
using ComexBol.Data;
using ComexBol.Presentation;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.App;

public partial class App : Application
{
    void OnStartup(object sender, StartupEventArgs e)
    {
        // Números, fechas y decimales siempre al estilo boliviano (1.234,56), sin importar la configuración regional del equipo.
        var cultura = CultureInfo.GetCultureInfo("es-BO");
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.DefaultThreadCurrentUICulture = cultura;
        FrameworkElement.LanguageProperty.OverrideMetadata(typeof(FrameworkElement), new FrameworkPropertyMetadata(XmlLanguage.GetLanguage(cultura.IetfLanguageTag)));
        DispatcherUnhandledException += (_, ex) =>
        {
            try { File.AppendAllText(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ComexBolPro", "errores.log"), $"{DateTime.Now:s} {ex.Exception}\n\n"); } catch { }
            MessageBox.Show("Ocurrió un error inesperado. Sus datos están guardados.\n\n" + ex.Exception.Message + "\n\n(Detalle en %LocalAppData%\\ComexBolPro\\errores.log)", "ComexBol Pro", MessageBoxButton.OK, MessageBoxImage.Warning);
            ex.Handled = true;
        };
        var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ComexBolPro");
        Directory.CreateDirectory(dir);
        var db = new ComexDb(new DbContextOptionsBuilder<ComexDb>().UseSqlite($"Data Source={Path.Combine(dir, "comex.db")}").Options);
        db.AsegurarEsquema();                 // crea la base o agrega columnas nuevas de versiones posteriores
        var vm = new MainViewModel(db, ocr: new ComexBol.Documentos.TesseractCliOcr());
        new MainWindow { DataContext = vm }.Show();
        _ = vm.CargarAsync();
    }
}
