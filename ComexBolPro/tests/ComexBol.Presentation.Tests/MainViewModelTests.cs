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

public class DecisionViewModelTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db; readonly MainViewModel _vm;
    public DecisionViewModelTests()
    {
        _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.Database.EnsureCreated();
        _vm = new MainViewModel(_db, () => new DateOnly(2026, 11, 2));
    }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    async Task OperacionTablets()
    {
        _vm.NuevaCarpeta = "IMP-DEC"; await _vm.NuevaImportacionCmd.ExecuteAsync();
        _vm.ItemPartida = "8471300010"; _vm.ItemDescripcion = "Tablets"; _vm.ItemValor = 40_000; _vm.ItemPesoBruto = 800;
        await _vm.AgregarItemCmd.ExecuteAsync();
        _db.Items.Single().AlicuotaGA = 0.10m; await _db.SaveChangesAsync();       // sin catálogo cargado en esta prueba
    }

    [Fact]
    public async Task Compara_Escenarios_Con_Las_Cifras_Del_Manual()
    {
        await OperacionTablets();
        var d = _vm.Decision; d.Unidades = 200; d.GastosLocalesBob = 4500; d.PrecioMercadoConIva = 2800;
        d.Escenarios.Add(new() { Nombre = "FOB + flete propio", Incoterm = Incoterm.FOB, ValorFactura = 40_000, Flete = 1800, Seguro = 150 });
        d.Escenarios.Add(new() { Nombre = "CIF del proveedor", Incoterm = Incoterm.CIF, ValorFactura = 42_000 });
        d.Escenarios.Add(new() { Nombre = "DAP del proveedor", Incoterm = Incoterm.DAP, ValorFactura = 44_000, DeduccionesPostFrontera = 1200 });
        await d.CompararCmd.ExecuteAsync();
        Assert.Equal(3, d.Resultados.Count);
        Assert.Equal("FOB + flete propio", d.Resultados[0].Nombre); Assert.True(d.Resultados[0].EsMejor);
        Assert.Equal("291.972,00", d.Resultados[0].CifBob.Replace(' ', ' ').Replace(" ", "."));
        Assert.All(d.Resultados, r => Assert.Equal("Viable", r.Veredicto));
    }

    [Fact]
    public async Task Contraste_Con_Dim_Detecta_Diferencias()
    {
        await OperacionTablets();
        _vm.Flete = 1800; _vm.Seguro = 150; await _vm.LiquidarCmd.ExecuteAsync();
        var d = _vm.Decision; d.DimGA = 29_197.20m; d.DimIVA = 47_982.68m;
        await d.ContrastarCmd.ExecuteAsync();
        Assert.All(d.Contraste, l => Assert.Equal("OK", l.Estado));
        d.DimIVA = 47_990m; await d.ContrastarCmd.ExecuteAsync();
        Assert.Contains(d.Contraste, l => l.Concepto == "IVA" && l.Estado == "REVISAR");
        Assert.Contains(_db.Bitacora, b => b.Categoria == "Contraste DIM");
    }

    [Fact]
    public async Task Sin_Operacion_O_Sin_Escenarios_Avisa_Sin_Romper()
    {
        await _vm.Decision.CompararCmd.ExecuteAsync();
        Assert.StartsWith("⚠", _vm.Decision.Mensaje);
    }
}

public class ExcelYPdfTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db; readonly MainViewModel _vm;
    public ExcelYPdfTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.Database.EnsureCreated(); _vm = new MainViewModel(_db, () => new DateOnly(2026, 11, 2)); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    [Fact]
    public async Task Excel_Contiene_Liquidacion_Con_Totales_Como_Formulas()
    {
        _vm.NuevaCarpeta = "IMP-XLS"; await _vm.NuevaImportacionCmd.ExecuteAsync();
        _vm.ItemPartida = "8471300010"; _vm.ItemDescripcion = "Tablets"; _vm.ItemValor = 40_000; _vm.ItemPesoBruto = 800;
        await _vm.AgregarItemCmd.ExecuteAsync();
        _db.Items.Single().AlicuotaGA = 0.10m; await _db.SaveChangesAsync();
        _vm.Flete = 1800; _vm.Seguro = 150; await _vm.LiquidarCmd.ExecuteAsync();

        var ruta = Path.Combine(Path.GetTempPath(), $"comex-{Guid.NewGuid():N}.xlsx");
        try
        {
            Assert.True(await _vm.ExportarExcelAsync(ruta));
            using var wb = new ClosedXML.Excel.XLWorkbook(ruta);
            Assert.Equal(new[] { "Resumen", "Ítems", "Liquidación", "Ruta crítica", "Bitácora" }, wb.Worksheets.Select(w => w.Name).ToArray());
            var l = wb.Worksheet("Liquidación");
            Assert.Equal(291_972.00, l.Cell(2, 4).GetDouble(), 2);                       // CIF del ítem
            Assert.Equal("SUM(E2:E2)", l.Cell(3, 5).FormulaA1);                          // total vivo
            Assert.Equal(12, wb.Worksheet("Ruta crítica").LastRowUsed()!.RowNumber() - 1);
        }
        finally { File.Delete(ruta); }
    }
}
