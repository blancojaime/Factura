using ComexBol.Core;
using ComexBol.Core.Catalogo;
using ComexBol.Data;
using ComexBol.Presentation;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class ModulosAduanerosTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static readonly DateOnly Hoy = new(2026, 11, 2);
    public ModulosAduanerosTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    async Task<MainViewModel> OpConItem(decimal cantidad = 200)
    {
        await new ServicioCatalogo(_db).ImportarResultadoAsync(new([new("8471300010", "Tablet", 0.10m, "u", false, [], "TEST")], []), "2026");
        await new ServicioConfiguracion(_db).GuardarTipoCambioAsync(Hoy, "USD", 6.96m);
        var vm = new MainViewModel(_db, () => Hoy) { UsuarioActual = "jaime" };
        vm.NuevaCarpeta = "IMP-M1"; await vm.NuevaImportacionCmd.ExecuteAsync();
        vm.ItemPartida = "8471300010"; vm.ItemDescripcion = "Tablets"; vm.ItemValor = 40_000m; vm.ItemPesoBruto = 800m; vm.ItemCantidad = cantidad; vm.Flete = 1_800m; vm.Seguro = 150m;
        await vm.AgregarItemCmd.ExecuteAsync(); await vm.LiquidarCmd.ExecuteAsync();
        return vm;
    }

    [Fact] public async Task Liquidacion_Muestra_Desglose_Items_Formulas_Y_Costeo_Por_Unidad()
    {
        var vm = await OpConItem();
        Assert.Contains(vm.Detalle.Desglose, l => l.Concepto.StartsWith("Valor en aduana") && l.Monto == "291.972,00");
        Assert.Contains(vm.Detalle.Desglose, l => l.Concepto.Contains("Flete") && l.Monto == "12.528,00");
        Assert.Equal("TOTAL", vm.Detalle.Items.Last().Partida); Assert.Equal("77.179,88", vm.Detalle.Items.Last().Total);
        Assert.Contains(vm.Detalle.Pasos, p => p.Contains("GA") && p.Contains("29.197,20"));
        Assert.Single(vm.Detalle.Costeo); Assert.Equal("200", vm.Detalle.Costeo[0].Cantidad);
        Assert.Contains("Flujo de caja requerido", vm.Detalle.FlujoCaja);
        vm.Detalle.Honorarios = 3_000m; vm.Detalle.TransporteInterno = 2_000m; await vm.Detalle.GuardarGastosCmd.ExecuteAsync();
        Assert.Equal("5.000,00", vm.Detalle.Costeo[0].Gastos); Assert.Contains("5.000,00", vm.Detalle.FlujoCaja);
    }

    [Fact] public async Task Estimar_Almacenaje_Exige_Tarifa_Y_Calcula_Con_Ella()
    {
        var vm = await OpConItem(); vm.Detalle.DiasAlmacenaje = 10;
        await vm.Detalle.EstimarAlmacenajeCmd.ExecuteAsync(); Assert.Contains("Configure la tarifa", vm.Detalle.Mensaje);
        await new ServicioConfiguracion(_db).GuardarAjustesAsync(new(5m, 4, 0.30m, 0.05m, true));
        await vm.Detalle.EstimarAlmacenajeCmd.ExecuteAsync(); Assert.Equal(6m * 0.8m * 5m, vm.Detalle.Almacenaje);   // 6 días × 0,8 t × 5
    }

    [Fact] public async Task Valoracion_Guarda_Evalua_Y_Los_Ajustes_Cambian_El_Cif()
    {
        var vm = await OpConItem(); var v = vm.Valoracion;
        Assert.Equal("Cuestionario pendiente", v.ResultadoDescarte);
        v.Royalties = 1_000m; v.Vinculacion = true; v.VinculacionInfluyo = true;
        await v.GuardarCmd.ExecuteAsync(); Assert.Contains("NO aplicable", v.ResultadoDescarte); Assert.Equal("#D9534F", v.ResultadoColor);
        v.VinculacionInfluyo = false; await v.GuardarCmd.ExecuteAsync(); Assert.Contains("APLICABLE", v.ResultadoDescarte);
        await vm.LiquidarCmd.ExecuteAsync();
        Assert.Contains(vm.Detalle.Desglose, l => l.Concepto.Contains("Art. 8") && l.Monto == "6.960,00");
        Assert.Contains(vm.Detalle.Desglose, l => l.Concepto.StartsWith("Valor en aduana") && l.Monto == "298.932,00");
        v.Vinculacion = false; Assert.False(v.VinculacionInfluyo);
    }

    [Fact] public async Task Valoracion_Valida_Precios_Contra_El_Historial()
    {
        var vm = await OpConItem(200);                                   // 200 por unidad
        var ops = new ServicioOperaciones(_db);
        var o2 = await ops.CrearImportacionAsync("IMP-M0", Incoterm.FOB, "USD", Hoy);
        await ops.AgregarItemAsync(o2.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "Tablets", ValorFactura = 80_000m, Cantidad = 200m, AlicuotaGA = 0.10m });   // 400 por unidad
        await vm.Valoracion.ValidarPreciosCmd.ExecuteAsync();
        var f = Assert.Single(vm.Valoracion.Precios); Assert.Equal("Alto", f.Riesgo); Assert.Equal("#D9534F", f.ColorHex); Assert.Contains("inferior", f.Mensaje);
    }

    [Fact] public async Task Despacho_Valida_Canal_Y_Descargo_Desde_La_Pantalla()
    {
        var vm = await OpConItem(); var d = vm.Despacho;
        await d.ValidarCmd.ExecuteAsync(); Assert.Contains("error", d.EstadoDim); Assert.Contains(d.Hallazgos, h => h.Nivel == "ERROR" && h.Texto.Contains("aduana de ingreso"));
        d.AduanaIngreso = "Tambo Quemado"; d.AduanaDestino = "La Paz"; d.CodigoDeclarante = "ADA-9"; d.Modalidad = "Carretero"; d.NroDocEmbarque = "CRT-5"; d.Bultos = 40; d.PesoManifiesto = 805m; d.NroDav = "DAV-1";
        Assert.Equal("N.º de CRT", d.EtiquetaEmbarque); Assert.Equal("N.º de MIC/DTA", d.EtiquetaManifiesto);
        await d.GuardarCmd.ExecuteAsync();
        Assert.DoesNotContain(d.Hallazgos, h => h.Nivel == "ERROR"); Assert.Contains(d.Hallazgos, h => h.Texto.Contains("concuerda"));
        d.Canal = "Rojo"; await d.AsignarCanalCmd.ExecuteAsync(); Assert.Equal(Despacho.TareasCanal("Rojo").Count, d.Tareas.Count); Assert.Equal("#D9534F", d.ColorCanal);
        d.Tareas[0].Hecha = true; await Task.Delay(200);
        Assert.True((await new ServicioDespacho(_db).TareasAsync(vm.Seleccionada!.Id))[0].Hecha);
        var texto = await d.GenerarDescargoAsync("Duda sobre el valor"); Assert.Contains("Duda sobre el valor", texto); Assert.Contains("IMP-M1", texto);
        d.FechaLevante = new DateTime(2026, 11, 20); await d.LevanteCmd.ExecuteAsync(); Assert.Contains("20/11/2026", d.Mensaje);
        // persistencia al cambiar de operación y volver
        await vm.RefrescarAsync(); Assert.Equal("Tambo Quemado", d.AduanaIngreso); Assert.Equal("Rojo", d.Canal);
    }

    [Fact] public async Task Configuracion_Guarda_Ajustes_Operativos()
    {
        var c = new ConfiguracionViewModel(_db, () => Hoy); await c.CargarAsync();
        c.AlmacenTarifa = 3m; c.AlmacenDiasLibres = 2; c.TolerancePrecioPct = 25m; c.IvaRecuperable = false;
        await c.GuardarParametrosCmd.ExecuteAsync();
        var a = await new ServicioConfiguracion(_db).ObtenerAjustesAsync(); Assert.Equal(3m, a.AlmacenTarifaBsTonDia); Assert.Equal(0.25m, a.TolerancePrecio); Assert.False(a.IvaRecuperable);
    }
}
