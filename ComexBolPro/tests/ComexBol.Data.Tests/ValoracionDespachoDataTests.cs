using ComexBol.Core;
using ComexBol.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class ValoracionDespachoDataTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static TipoCambioTable Tc() => new(new DateOnly(2026, 11, 1), new Dictionary<string, decimal> { ["USD"] = 6.96m });
    public ValoracionDespachoDataTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    async Task<int> OpConItem(string carpeta, decimal valor = 40_000m, decimal cant = 200m, decimal peso = 800m)
    {
        var ops = new ServicioOperaciones(_db);
        var op = await ops.CrearImportacionAsync(carpeta, Incoterm.FOB, "USD", new DateOnly(2026, 11, 2));
        await ops.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "Tablets", ValorFactura = valor, Cantidad = cant, PesoBrutoKg = peso, PesoNetoKg = peso * .9m, AlicuotaGA = 0.10m });
        return op.Id;
    }

    [Fact] public async Task Ajustes_Art8_Guardados_Modifican_El_Valor_En_Aduana()
    {
        var id = await OpConItem("A-1"); var ops = new ServicioOperaciones(_db);
        var sin = await ops.LiquidarAsync(id, Tc());
        await new ServicioValoracion(_db).GuardarValoracionAsync(id, new(Respondido: true), new(Royalties: 1_000m, Comisiones: 500m, ArmadoPosterior: 200m), "royalty por licencia");
        var con = await ops.LiquidarAsync(id, Tc());
        Assert.Equal(sin.CifBob + (1_000m + 500m - 200m) * 6.96m, con.CifBob);
        Assert.Contains(con.Desglose!, l => l.Concepto.Contains("Art. 8"));
        Assert.Contains(_db.Bitacora, b => b.Categoria == "Valoración" && b.Detalle.Contains("valor de transacción aplicable"));
    }

    [Fact] public async Task Valoracion_Rechaza_Montos_Negativos_Y_Vinculacion_Inconsistente()
    {
        var id = await OpConItem("A-2"); var v = new ServicioValoracion(_db);
        await Assert.ThrowsAsync<ArgumentException>(() => v.GuardarValoracionAsync(id, new(Respondido: true), new(Royalties: -1), ""));
        await Assert.ThrowsAsync<ArgumentException>(() => v.GuardarValoracionAsync(id, new(VinculacionInfluyoPrecio: true, Respondido: true), new(), ""));
    }

    [Fact] public async Task Validador_Compara_Con_Operaciones_Anteriores_De_La_Misma_Partida()
    {
        await OpConItem("H-1", 20_000m, 200m);          // 100 por unidad
        await OpConItem("H-2", 20_800m, 200m);          // 104
        var id = await OpConItem("H-3", 10_000m, 200m); // 50 por unidad: muy barato
        var res = await new ServicioValoracion(_db).ValidarPreciosAsync(id, 0.30m);
        Assert.Equal(NivelRiesgoPrecio.Alto, res.Single().Evaluacion.Nivel); Assert.Equal(2, res.Single().Evaluacion.Muestras);
        var primero = await new ServicioValoracion(_db).ValidarPreciosAsync(_db.Operaciones.First(o => o.Carpeta == "H-1").Id, 0.30m);
        Assert.Equal(2, primero.Single().Evaluacion.Muestras); Assert.NotEqual(NivelRiesgoPrecio.SinReferencia, primero.Single().Evaluacion.Nivel);
    }

    [Fact] public async Task Costeo_Usa_Gastos_Locales_Y_Cantidad_Del_Item()
    {
        var id = await OpConItem("C-1", 40_000m, 200m);
        Assert.Null(await new ServicioValoracion(_db).CostearAsync(id, true));         // sin liquidación
        await new ServicioOperaciones(_db).LiquidarAsync(id, Tc());
        await new ServicioValoracion(_db).GuardarGastosAsync(id, new(HonorariosAgencia: 3_000m, Almacenaje: 1_500m, TransporteInterno: 2_500m), 5);
        var c = (await new ServicioValoracion(_db).CostearAsync(id, true))!;
        Assert.Equal(7_000m, c.GastosLocalesBob); Assert.Equal(200m, c.Items[0].Cantidad);
        Assert.Equal(Math.Round(c.Items[0].CostoNacionalizadoBob / 200m, 2), c.Items[0].CostoUnitarioBob);
        Assert.True(c.FactorGlobal > 1m);
        await Assert.ThrowsAsync<ArgumentException>(() => new ServicioValoracion(_db).GuardarGastosAsync(id, new(Otros: -1), 0));
    }

    [Fact] public async Task Despacho_Guarda_Valida_Y_Detecta_Inconsistencias()
    {
        var id = await OpConItem("D-1", peso: 800m); var d = new ServicioDespacho(_db);
        var h0 = await d.ValidarAsync(id, 0.05m);
        Assert.Contains(h0, h => h.Nivel == NivelHallazgo.Error && h.Texto.Contains("aduana de ingreso")); Assert.Contains(h0, h => h.Texto.Contains("liquidación"));
        await new ServicioOperaciones(_db).LiquidarAsync(id, Tc());
        await new ServicioValoracion(_db).GuardarValoracionAsync(id, new(Respondido: true), new(), "");
        await d.GuardarDatosAsync(id, new("General", "10 - Importación a consumo", "Arica", "La Paz", "ADA-1", "Marítimo / fluvial", "BL-77", 20, 1_200m, "M-1", "DAV-1", ""));
        var h1 = await d.ValidarAsync(id, 0.05m);
        Assert.Contains(h1, h => h.Nivel == NivelHallazgo.Error && h.Texto.Contains("difiere"));        // 800 kg vs 1.200 kg
        await d.GuardarDatosAsync(id, new("General", "10 - Importación a consumo", "Arica", "La Paz", "ADA-1", "Marítimo / fluvial", "BL-77", 20, 810m, "M-1", "DAV-1", ""));
        var h2 = await d.ValidarAsync(id, 0.05m);
        Assert.DoesNotContain(h2, h => h.Nivel == NivelHallazgo.Error);
        Assert.Contains(h2, h => h.Nivel == NivelHallazgo.Alerta && h.Texto.Contains("respaldo bancario"));  // FOB > Bs 50.000
        await Assert.ThrowsAsync<ArgumentException>(() => d.GuardarDatosAsync(id, new("Express", "", "", "", "", "", "", 0, 0, "", "", "")));
    }

    [Fact] public async Task Canal_Genera_Lista_De_Control_Que_Se_Reemplaza_Al_Cambiar()
    {
        var id = await OpConItem("K-1"); var d = new ServicioDespacho(_db);
        await d.AsignarCanalAsync(id, "Amarillo"); var t = await d.TareasAsync(id);
        Assert.Equal(Despacho.TareasCanal("Amarillo").Count, t.Count); Assert.All(t, x => Assert.False(x.Hecha));
        await d.MarcarTareaAsync(t[0].Id, true); Assert.True((await d.TareasAsync(id))[0].Hecha);
        await d.AsignarCanalAsync(id, "Rojo");
        Assert.Equal(Despacho.TareasCanal("Rojo").Count, (await d.TareasAsync(id)).Count);
        await d.AsignarCanalAsync(id, "Sin asignar"); Assert.Empty(await d.TareasAsync(id));
        await Assert.ThrowsAsync<ArgumentException>(() => d.AsignarCanalAsync(id, "Azul"));
        await d.RegistrarLevanteAsync(id, new DateOnly(2026, 11, 20)); Assert.Equal(new DateOnly(2026, 11, 20), _db.Operaciones.Single(o => o.Id == id).FechaLevante);
    }

    [Fact] public async Task Descargo_Usa_Perfil_Y_Datos_De_La_Operacion()
    {
        var id = await OpConItem("R-1");
        await new ServicioConfiguracion(_db).GuardarPerfilAsync(new() { RazonSocial = "ACME SRL", Nit = "1020304", TipoImportador = "Habitual" });
        var t = await new ServicioDespacho(_db).GenerarDescargoAsync(id, "Valor menor al referencial", Despacho.PruebasDescargo.Take(3));
        Assert.Contains("ACME SRL", t); Assert.Contains("1020304", t); Assert.Contains("40", t); Assert.Contains("Valor menor al referencial", t);
    }

    [Fact] public async Task Ajustes_Operativos_Se_Guardan_Y_Validan()
    {
        var c = new ServicioConfiguracion(_db);
        var def = await c.ObtenerAjustesAsync(); Assert.Equal(0.30m, def.TolerancePrecio); Assert.True(def.IvaRecuperable);
        await c.GuardarAjustesAsync(new(2.5m, 3, 0.25m, 0.02m, false));
        var a = await c.ObtenerAjustesAsync(); Assert.Equal(2.5m, a.AlmacenTarifaBsTonDia); Assert.Equal(3, a.AlmacenDiasLibres); Assert.False(a.IvaRecuperable); Assert.Equal(0.02m, a.TolerancePeso);
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarAjustesAsync(new(-1m)));
    }

    [Fact] public async Task Base_Antigua_Sin_Columnas_De_Despacho_Se_Actualiza()
    {
        var id = await OpConItem("M-1");
        _db.Database.ExecuteSqlRaw("ALTER TABLE Operaciones DROP COLUMN NroDim"); _db.Database.ExecuteSqlRaw("ALTER TABLE Operaciones DROP COLUMN AdRoyalties"); _db.Database.ExecuteSqlRaw("DROP TABLE TareasDespacho");
        _db.AsegurarEsquema();
        Assert.Equal("", _db.Operaciones.AsNoTracking().Single(o => o.Id == id).NroDim); Assert.Empty(_db.TareasDespacho.ToList());
    }
}
