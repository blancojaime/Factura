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
        vm.NuevaCarpeta = "IMP-M1"; await vm.NuevaImportacionCmd.ExecuteAsync(); vm.FechaDim = new DateTime(2026, 6, 1);
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

    [Fact] public async Task Operacion_Nueva_Propone_La_Fecha_De_Hoy_Y_Aplica_El_Ds5646_Con_Impacto_Y_Precio_Sugerido()
    {
        var vm = await OpConItem(200);
        vm.FechaDim = null; await Task.CompletedTask;
        // se vuelve a crear con la fecha por defecto: hoy (2026-11-02) → rige el D.S. 5646
        var v2 = new MainViewModel(_db, () => Hoy) { UsuarioActual = "jaime" }; v2.NuevaCarpeta = "IMP-N2"; await v2.NuevaImportacionCmd.ExecuteAsync();
        Assert.Equal(new DateTime(2026, 11, 2), v2.FechaDim); Assert.Contains("D.S. 5646", v2.AvisoMedidas);
        v2.ItemPartida = "8471300010"; v2.ItemDescripcion = "Tablets"; v2.ItemValor = 40_000m; v2.ItemPesoBruto = 800m; v2.ItemCantidad = 200m; v2.Flete = 1_800m; v2.Seguro = 150m;
        await v2.AgregarItemCmd.ExecuteAsync(); await v2.LiquidarCmd.ExecuteAsync();
        // base GA = 278.400 + 10 % × 13.572 = 279.757,20 ; GA 5 % = 13.987,86 ; IVA = 14,94 % × (291.972 + 13.987,86)
        Assert.Contains(v2.Detalle.Items, i => i.Partida == "TOTAL" && i.GA == "13.987,86");
        var tot = v2.Detalle.Impacto.Single(x => x.Destacada); Assert.Equal("77.179,88", tot.Anterior); Assert.NotEqual(tot.Anterior, tot.Aplicado);
        Assert.Contains(v2.Detalle.Impacto, x => x.Concepto.StartsWith("Gravamen") && x.Anterior == "29.197,20" && x.ConDs5646 == "13.987,86");
        var c = v2.Detalle.Costeo.Single(); Assert.NotEqual("—", c.PrecioSinIva); Assert.Contains("margen 30", v2.Detalle.ResumenCosteo);
        Assert.Contains(v2.Detalle.Pasos, p => p.Contains("D.S. 5646"));
    }

    [Fact] public async Task Beneficio_Ds5516_Del_Item_Se_Marca_Desde_El_Formulario()
    {
        var vm = new MainViewModel(_db, () => Hoy) { UsuarioActual = "jaime" };
        await new ServicioCatalogo(_db).ImportarResultadoAsync(new([new("8417209000", "Hornos de panadería, no eléctricos", 0.10m, "u", false, [], "TEST")], []), "2026");
        vm.NuevaCarpeta = "IMP-B"; await vm.NuevaImportacionCmd.ExecuteAsync();
        vm.ItemPartida = "8417209000"; vm.ItemDescripcion = "Horno a gas"; vm.ItemValor = 10_000m; vm.ItemCantidad = 5; vm.ItemBeneficio = true; vm.Flete = 1_000m;
        await vm.AgregarItemCmd.ExecuteAsync(); await vm.LiquidarCmd.ExecuteAsync();
        Assert.Contains(vm.Detalle.Items, i => i.Partida == "TOTAL" && i.GA == "0,00");
        Assert.Contains(vm.Detalle.Pasos, p => p.Contains("D.S. 5516") || p.Contains("GA"));
        var g = vm.Guia; Assert.Equal(11, g.Pasos.Count); Assert.Equal(12, g.Control.Count); Assert.Contains("0 de 11", g.Avance);
        g.Pasos[0].Hecho = true; await Task.Delay(300); Assert.Contains("1 de 11", g.Avance);
    }
}

public class DecisionConMedidasTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static readonly DateOnly Hoy = new(2026, 11, 2);
    public DecisionConMedidasTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    [Fact] public async Task Escenarios_Comparan_Origenes_Con_Preferencia_Y_Beneficio_Segun_La_Fecha_De_La_Dim()
    {
        await new ServicioCatalogo(_db).ImportarResultadoAsync(new([new("8412900000", "Partes de motores", 0.10m, "u", false, [], "TEST")], []), "2026");
        await new ServicioConfiguracion(_db).GuardarTipoCambioAsync(Hoy, "USD", 6.96m);
        var vm = new MainViewModel(_db, () => Hoy) { UsuarioActual = "jaime" }; vm.NuevaCarpeta = "IMP-ESC"; await vm.NuevaImportacionCmd.ExecuteAsync();   // fecha de DIM = hoy (D.S. 5646)
        vm.ItemPartida = "8412900000"; vm.ItemDescripcion = "Partes"; vm.ItemValor = 20_000m; vm.ItemCantidad = 10; vm.ItemPesoBruto = 500; await vm.AgregarItemCmd.ExecuteAsync();
        var d = vm.Decision; d.Unidades = 10; d.PrecioMercadoConIva = 4_000m;
        d.AgregarEscenarioCmd.Execute(null); d.AgregarEscenarioCmd.Execute(null); d.AgregarEscenarioCmd.Execute(null);
        foreach (var e in d.Escenarios) { e.Incoterm = Incoterm.CIF; e.ValorFactura = 20_000m; }
        d.Escenarios[0].Nombre = "China (arancel 2026)";
        d.Escenarios[1].Nombre = "Brasil con Certificado de Origen"; d.Escenarios[1].DesgravacionPct = 100;
        d.Escenarios[2].Nombre = "China con beneficio D.S. 5516"; d.Escenarios[2].Beneficio = true;
        await d.CompararCmd.ExecuteAsync();
        var por = d.Resultados.ToDictionary(r => r.Nombre);
        Assert.Equal("6.960,00", por["China (arancel 2026)"].Ga.Replace(" ", ""));      // 20.000 × 6,96 = 139.200 × 5 % (10 % − 5 puntos del D.S. 5646)
        Assert.Equal("0,00", por["Brasil con Certificado de Origen"].Ga); Assert.Equal("0,00", por["China con beneficio D.S. 5516"].Ga);
        Assert.NotEqual(por["China (arancel 2026)"].Tributos, por["Brasil con Certificado de Origen"].Tributos);
    }
}
