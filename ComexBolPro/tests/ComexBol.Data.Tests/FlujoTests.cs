using ComexBol.Core;
using ComexBol.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class FlujoTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:");
    readonly ComexDb _db;
    static readonly TipoCambioTable Tc = new(new DateOnly(2026, 11, 1), new Dictionary<string, decimal> { ["USD"] = 6.96m });

    public FlujoTests()
    {
        _cn.Open();
        _db = new ComexDb(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options);
        _db.Database.EnsureCreated();
    }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    async Task<Operacion> Caso()
    {
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-001", Incoterm.FOB, "USD", new DateOnly(2026, 11, 1));
        op.Flete = 1500; op.Seguro = 100; await _db.SaveChangesAsync();
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300000", Descripcion = "Laptops", ValorFactura = 10_000, PesoBrutoKg = 120, PesoNetoKg = 100, Cantidad = 50, AlicuotaGA = 0.10m });
        return op;
    }

    [Fact]
    public async Task Crea_Ruta_Con_Fechas_Y_Liquida_Con_Version()
    {
        var op = await Caso(); var s = new ServicioOperaciones(_db);
        Assert.Equal(12, _db.Etapas.Count(e => e.OperacionId == op.Id));
        var r1 = await s.LiquidarAsync(op.Id, Tc); await s.LiquidarAsync(op.Id, Tc);
        Assert.Equal(80_736.00m, r1.CifBob);
        Assert.Equal(new[] { 1, 2 }, _db.Liquidaciones.OrderBy(l => l.Version).Select(l => l.Version).ToArray());
    }

    [Fact]
    public async Task Semaforos_Y_Cumplimiento()
    {
        var op = await Caso(); var s = new ServicioOperaciones(_db);
        await s.CompletarEtapaAsync(op.Id, "I01", new DateOnly(2026, 11, 3));
        var est = await s.EstadoRutaAsync(op.Id, new DateOnly(2026, 11, 20));
        Assert.Equal(Semaforo.Cumplido, est.First(e => e.Etapa.Codigo == "I01").Semaforo);
        Assert.Contains(est, e => e.Semaforo == Semaforo.Vencido);
    }

    [Fact]
    public async Task Checklist_Y_Expediente_Documentan_El_Proceso()
    {
        var op = await Caso(); var s = new ServicioOperaciones(_db);
        await s.LiquidarAsync(op.Id, Tc);
        await s.AdjuntarDocumentoAsync(op.Id, TipoDocumento.Factura, "/tmp/inexistente-factura.pdf");
        var chk = await s.ChecklistAsync(op.Id);
        Assert.True(chk.First(c => c.Tipo == TipoDocumento.Factura).Presente);
        Assert.False(chk.First(c => c.Tipo == TipoDocumento.Seguro).Presente);
        var md = await s.GenerarExpedienteAsync(op.Id, new DateOnly(2026, 11, 5));
        Assert.Contains("# Expediente de importación IMP-001", md);
        Assert.Contains("**CIF**", md);
        Assert.Contains("## Bitácora", md);
    }

    [Fact]
    public void Escenarios_Ordenan_Por_Costo_Y_Dan_Veredicto()
    {
        ItemImportacion it = new(1, "8471300000", "Laptops", 10_000m, 120, 100, 0.10m);
        var res = Escenarios.Comparar([
            new("FOB + flete propio", new(Incoterm.FOB, "USD", [it], Flete: new(1500m), Seguro: new(100m))),
            new("CIF proveedor", new(Incoterm.CIF, "USD", [it with { ValorFactura = 11_000m }]))],
            Tc, gastosLocalesBob: 3_000m, unidades: 50m, precioMercadoConIva: 2_500m);
        Assert.Equal(2, res.Count);
        Assert.True(res[0].Viabilidad.CostoUnitario <= res[1].Viabilidad.CostoUnitario);
        Assert.All(res, r => Assert.Contains(r.Veredicto, new[] { "Viable", "Ajustado", "No viable" }));
    }
}
