using System.IO;
using System.Windows;
using ComexBol.Data;
using ComexBol.Presentation;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.App;

public partial class App : Application
{
    void OnStartup(object sender, StartupEventArgs e)
    {
        var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ComexBolPro");
        Directory.CreateDirectory(dir);
        var db = new ComexDb(new DbContextOptionsBuilder<ComexDb>().UseSqlite($"Data Source={Path.Combine(dir, "comex.db")}").Options);
        db.Database.EnsureCreated();           // TODO: migraciones EF Core antes de la primera versión estable
        var vm = new MainViewModel(db, ocr: new ComexBol.Documentos.TesseractCliOcr());
        new MainWindow { DataContext = vm }.Show();
        _ = vm.CargarAsync();
    }
}
