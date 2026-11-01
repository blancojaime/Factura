using ComexBol.Core;
using ComexBol.Data;
using ComexBol.Presentation;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class MainViewModelTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:");
    readonly ComexDb _db;
    readonly MainViewModel _vm;
    public MainViewModelTests()
    {
        _cn.Open();
        _db = new ComexDb(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options);
        _db.Database.EnsureCreated();
        _vm = new MainViewModel(_db, () => new DateOnly(2026, 11, 1));
    }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    [Fact]
    public async Task Flujo_Completo_De_La_Ventana()
    {
        _vm.NuevaCarpeta = "IMP-UI-1"; _vm.NuevoIncoterm = Incoterm.FOB;
        await _vm.NuevaImportacionCmd.ExecuteAsync();
        Assert.Equal("IMP-UI-1", _vm.Seleccionada?.Carpeta);
        Assert.Equal(12, _vm.Etapas.Count);

        _vm.ItemPartida = "8471.30.00.00"; _vm.ItemDescripcion = "Laptops"; _vm.ItemValor = 10_000; _vm.ItemPesoBruto = 120;
        await _vm.AgregarItemCmd.ExecuteAsync();
        Assert.Single(_vm.Items);

        _vm.Flete = 1500; _vm.Seguro = 100;
        await _vm.LiquidarCmd.ExecuteAsync();
        Assert.Contains(_vm.Liquidacion, l => l.Concepto.StartsWith("CIF") && l.Monto.Contains("80"));
        Assert.Contains("Liquidado", _vm.Mensaje);

        await _vm.CompletarEtapaCmd.ExecuteAsync(_vm.Etapas.First());
        Assert.Equal(Semaforo.Cumplido, _vm.Etapas.First().Semaforo);
        Assert.NotEmpty(_vm.Bitacora);
        Assert.False(_vm.Legajo.First(l => l.Documento == "Factura").Presente);
    }

    [Fact]
    public async Task Errores_Se_Muestran_Sin_Romper_La_Ventana()
    {
        _vm.NuevaCarpeta = " ";
        await _vm.NuevaImportacionCmd.ExecuteAsync();
        Assert.StartsWith("⚠", _vm.Mensaje);
        Assert.False(_vm.LiquidarCmd.CanExecute(null));
    }
}

public class OcrViewModelTests : IDisposable
{
    sealed class OcrFalso(string t) : ComexBol.Documentos.IMotorOcr { public Task<string> LeerTextoAsync(string r, CancellationToken ct = default) => Task.FromResult(t); }
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    public OcrViewModelTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.Database.EnsureCreated(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    [Fact]
    public async Task Ocr_Propone_Y_Solo_Aplica_Al_Confirmar()
    {
        var vm = new MainViewModel(_db, () => new DateOnly(2026, 11, 1), new OcrFalso("Invoice No: INV-1\nSupplier: ACME\nIncoterm: CIF\nCurrency: USD\nGross Weight: 80 kg\nTotal Amount: USD 5,000.00"));
        vm.NuevaCarpeta = "IMP-OCR"; vm.NuevoIncoterm = Incoterm.FOB; await vm.NuevaImportacionCmd.ExecuteAsync();
        await vm.ProcesarDocumentoAsync("/tmp/factura-x.png");
        Assert.Equal(Incoterm.FOB, _db.Operaciones.Single().Incoterm);              // aún no se aplicó nada
        Assert.True(vm.ConfirmarPropuestaCmd.CanExecute(null));
        vm.Propuesta.First(p => p.Clave == "valor").Valor = "5200";                  // el usuario corrige
        await vm.ConfirmarPropuestaCmd.ExecuteAsync();
        Assert.Equal(Incoterm.CIF, _db.Operaciones.Single().Incoterm);
        Assert.Equal(5200m, vm.ItemValor);
        Assert.True(_db.Documentos.Single().Validado);
        Assert.Contains(_db.Bitacora, b => b.Categoria == "OCR" && b.Detalle.Contains("Confirmado"));
        Assert.True(vm.Legajo.First(l => l.Documento == "Factura").Presente);
    }
}
