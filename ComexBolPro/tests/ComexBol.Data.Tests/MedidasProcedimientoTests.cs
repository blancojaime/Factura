using ComexBol.Core;
using ComexBol.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class MedidasProcedimientoTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static TipoCambioTable Tc() => new(new DateOnly(2026, 11, 2), new Dictionary<string, decimal> { ["USD"] = 6.96m });
    public MedidasProcedimientoTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    async Task<int> Op(string c, DateOnly? fecha, bool beneficio = false, decimal valor = 10_000m)
    {
        var ops = new ServicioOperaciones(_db); var op = await ops.CrearImportacionAsync(c, Incoterm.FOB, "USD", new DateOnly(2026, 11, 2));
        op.Flete = 1_500m; op.Seguro = 100m; op.FechaDeclaracion = fecha; await _db.SaveChangesAsync();
        await ops.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8417209000", Descripcion = "Horno a gas", ValorFactura = valor, Cantidad = 5, PesoBrutoKg = 300, PesoNetoKg = 280, AlicuotaGA = 0.10m, BeneficioDs5516 = beneficio });
        return op.Id;
    }

    [Fact] public async Task La_Fecha_De_La_Dim_Decide_Las_Medidas_En_La_Liquidacion_Guardada()
    {
        var a = await new ServicioOperaciones(_db).LiquidarAsync(await Op("A", null), Tc());
        var b = await new ServicioOperaciones(_db).LiquidarAsync(await Op("B", new DateOnly(2026, 11, 2)), Tc());
        var c = await new ServicioOperaciones(_db).LiquidarAsync(await Op("C", new DateOnly(2026, 11, 2), true), Tc());
        Assert.Equal(8_073.60m, a.GA); Assert.Equal(3_535.68m, b.GA); Assert.Equal(0m, c.GA);
        Assert.True(c.TotalTributos < b.TotalTributos && b.TotalTributos < a.TotalTributos);
    }

    [Fact] public async Task El_Beneficio_Del_Item_Se_Guarda_Y_Se_Actualiza()
    {
        var id = await Op("D", new DateOnly(2026, 11, 2));
        var it = _db.Items.Single(i => i.OperacionId == id); it.BeneficioDs5516 = true;
        await new ServicioOperaciones(_db).ActualizarItemAsync(it); _db.ChangeTracker.Clear();
        Assert.True(_db.Items.AsNoTracking().Single(i => i.OperacionId == id).BeneficioDs5516);
    }

    [Fact] public async Task Importador_Ocasional_Se_Valida_Con_Topes_Por_Despacho_Y_Anual()
    {
        await new ServicioConfiguracion(_db).GuardarPerfilAsync(new() { RazonSocial = "X", Nit = "1", TipoImportador = "Ocasional" });
        var grande = await Op("E", null, false, 8_000m);
        var h = await new ServicioDespacho(_db).ValidarAsync(grande, 0.05m);
        Assert.Contains(h, x => x.Nivel == NivelHallazgo.Error && x.Texto.Contains("no habitual"));
        await new ServicioConfiguracion(_db).GuardarPerfilAsync(new() { RazonSocial = "X", Nit = "1", TipoImportador = "Habitual" });
        Assert.DoesNotContain(await new ServicioDespacho(_db).ValidarAsync(grande, 0.05m), x => x.Texto.Contains("no habitual"));
    }

    [Fact] public async Task Guia_Lista_Pasos_Marca_Y_Sugiere_Con_Los_Datos_Del_Sistema()
    {
        var id = await Op("F", new DateOnly(2026, 11, 2)); var s = new ServicioProcedimiento(_db) { Usuario = "jaime" };
        var l = await s.ListarAsync(id);
        Assert.Equal(23, l.Count); Assert.Equal(11, l.Count(x => !x.EsControl)); Assert.True(l.Single(x => x.Codigo == "P-03").Sugerido); Assert.False(l.Single(x => x.Codigo == "P-10").Sugerido);
        await s.MarcarAsync(id, "P-01", true, "NIT vigente");
        var l2 = await s.ListarAsync(id); Assert.True(l2.Single(x => x.Codigo == "P-01").Hecho); Assert.Equal("NIT vigente", l2.Single(x => x.Codigo == "P-01").Nota);
        Assert.Contains(_db.Bitacora, b => b.Categoria == "Guía" && b.Detalle.Contains("P-01"));
        await s.MarcarAsync(id, "P-01", false); Assert.False((await s.ListarAsync(id)).Single(x => x.Codigo == "P-01").Hecho);
        await Assert.ThrowsAsync<ArgumentException>(() => s.MarcarAsync(id, "P-99", true));
        Assert.Equal((0, 11), ServicioProcedimiento.Avance(await s.ListarAsync(id), false));
    }

    [Fact] public async Task Base_Antigua_Recibe_Los_Campos_Y_La_Tabla_De_Pasos()
    {
        var id = await Op("H", null);
        _db.Database.ExecuteSqlRaw("ALTER TABLE Operaciones DROP COLUMN FechaDeclaracion"); _db.Database.ExecuteSqlRaw("ALTER TABLE Items DROP COLUMN BeneficioDs5516"); _db.Database.ExecuteSqlRaw("DROP TABLE EstadosPaso");
        _db.AsegurarEsquema(); _db.ChangeTracker.Clear();
        Assert.Null(_db.Operaciones.AsNoTracking().Single(o => o.Id == id).FechaDeclaracion); Assert.False(_db.Items.AsNoTracking().Single().BeneficioDs5516); Assert.Empty(_db.EstadosPaso.ToList());
    }

    [Fact] public async Task Ajustes_Operativos_Incluyen_Margen_E_Iva_De_Venta()
    {
        var c = new ServicioConfiguracion(_db); var d = await c.ObtenerAjustesAsync(); Assert.Equal(0.30m, d.MargenObjetivo); Assert.Equal(0.13m, d.IvaVenta);
        await c.GuardarAjustesAsync(new(MargenObjetivo: 0.25m, IvaVenta: 0.13m)); Assert.Equal(0.25m, (await c.ObtenerAjustesAsync()).MargenObjetivo);
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarAjustesAsync(new(MargenObjetivo: 1m)));
    }
}
