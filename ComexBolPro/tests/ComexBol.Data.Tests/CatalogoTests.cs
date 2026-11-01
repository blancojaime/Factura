using ComexBol.Core;
using ComexBol.Core.Catalogo;
using ComexBol.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class CatalogoTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:");
    readonly ComexDb _db;
    public CatalogoTests()
    {
        _cn.Open();
        _db = new ComexDb(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options);
        _db.Database.EnsureCreated();
    }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    const string Csv = """
        Codigo;Descripcion;GA;Unidad;Prohibida;Autorizaciones;Fuente
        8471.30.00.00;Laptops;0;u;NO;;ANB-TEST
        2208300000;Whisky;40;l;NO;SENASAG|IBNORCA;ANB-TEST
        1234;Malo;10;u;NO;;ANB-TEST
        3004900000;Medicamento;55;kg;NO;AGEMED;ANB-TEST
        9999999999;Veneno;10;kg;SI;;ANB-TEST
        """;

    [Fact]
    public async Task Importa_Valida_Y_Reporta_Errores_Con_Linea()
    {
        var r = await new ServicioCatalogo(_db).ImportarCsvAsync(new StringReader(Csv), "2026.1");
        Assert.Equal(3, r.Importadas);
        Assert.Equal(new[] { 4, 5 }, r.Errores.Select(e => e.Linea).ToArray());
        Assert.False(r.SoloEjemplos);
    }

    [Fact]
    public async Task Busca_Por_Codigo_Y_Descripcion()
    {
        var c = new ServicioCatalogo(_db); await c.ImportarCsvAsync(new StringReader(Csv), "1");
        Assert.Single(await c.BuscarAsync("8471"));
        Assert.Single(await c.BuscarAsync("whis"));
    }

    [Fact]
    public async Task Aplica_GA_Exige_Autorizacion_Y_Bloquea_Prohibidas()
    {
        var c = new ServicioCatalogo(_db); await c.ImportarCsvAsync(new StringReader(Csv), "1");
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-C1", Incoterm.CIF, "USD", new DateOnly(2026, 11, 1));
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "2208300000", Descripcion = "Whisky", ValorFactura = 1000 });
        var avisos = await c.AplicarAOperacionAsync(op.Id);
        Assert.Equal(0.40m, _db.Items.Single().AlicuotaGA);
        Assert.Contains(avisos, a => a.Contains("SENASAG"));
        Assert.Contains(await s.ChecklistAsync(op.Id), x => x.Tipo == TipoDocumento.AutorizacionPrevia && !x.Presente);

        await s.AgregarItemAsync(op.Id, new() { Numero = 2, CodigoNandina = "9999999999", Descripcion = "x", ValorFactura = 1 });
        // 9999999999 fue rechazado como inválido por GA? no: es prohibida válida -> importada
        await Assert.ThrowsAsync<InvalidOperationException>(() => c.AplicarAOperacionAsync(op.Id));
    }

    [Fact]
    public void Capitulos_SA() => Assert.Equal("Café, té, yerba mate y especias", CapitulosSa.Titulo("0901210000"));
}
