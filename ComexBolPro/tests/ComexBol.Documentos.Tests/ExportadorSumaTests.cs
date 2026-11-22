using ClosedXML.Excel;
using ComexBol.Core;
using ComexBol.Data;
using ComexBol.Documentos;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class ExportadorSumaTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static TipoCambioTable Tc() => new(new DateOnly(2026, 11, 2), new Dictionary<string, decimal> { ["USD"] = 6.96m });
    public ExportadorSumaTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    async Task<int> Op(string c, DateOnly? fecha, bool beneficio)
    {
        var ops = new ServicioOperaciones(_db); var op = await ops.CrearImportacionAsync(c, Incoterm.FOB, "USD", new DateOnly(2026, 11, 2));
        op.Flete = 1_500m; op.Seguro = 100m; op.FechaDeclaracion = fecha; await _db.SaveChangesAsync();
        await ops.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8417209000", Descripcion = "Horno a gas", ValorFactura = 10_000m, Cantidad = 5, PesoBrutoKg = 300, PesoNetoKg = 280, AlicuotaGA = 0.10m, BeneficioDs5516 = beneficio });
        return op.Id;
    }

    [Fact] public async Task Hoja_Suma_Exporta_Dav_Dim_Y_Items()
    {
        var id = await Op("G", new DateOnly(2026, 11, 2), true);
        await new ServicioConfiguracion(_db).GuardarPerfilAsync(new() { RazonSocial = "ACME SRL", Nit = "555", TipoImportador = "Habitual" });
        await new ServicioValoracion(_db).GuardarValoracionAsync(id, new(Respondido: true), new(Royalties: 300m), "");
        await new ServicioDespacho(_db).GuardarDatosAsync(id, new("General", "10 - Importación a consumo", "Tambo Quemado", "La Paz", "ADA-1", "Carretero", "CRT-9", 12, 305m, "MIC-1", "DAV-1", "DIM-1"));
        await new ServicioOperaciones(_db).LiquidarAsync(id, Tc());
        var ruta = Path.Combine(Path.GetTempPath(), $"suma-{Guid.NewGuid():N}.xlsx");
        try
        {
            await ExportadorSuma.ExportarAsync(_db, id, ruta);
            using var wb = new XLWorkbook(ruta);
            Assert.Equal("DAV|DIM-General|DIM-Ítems|Nota", string.Join("|", wb.Worksheets.Select(w => w.Name)));
            var txt = string.Join("|", wb.Worksheet("DAV").CellsUsed().Select(c => c.GetString())); Assert.Contains("ACME SRL", txt); Assert.Contains("Cánones y licencias", txt);
            Assert.Contains("Tambo Quemado", string.Join("|", wb.Worksheet("DIM-General").CellsUsed().Select(c => c.GetString())));
            var it = wb.Worksheet("DIM-Ítems"); Assert.Equal("8417209000", it.Cell(2, 2).GetString()); Assert.Equal("SÍ", it.Cell(2, 14).GetString()); Assert.Equal(0d, it.Cell(2, 18).GetDouble());   // GA 0 por D.S. 5516
        }
        finally { File.Delete(ruta); }
    }

}
