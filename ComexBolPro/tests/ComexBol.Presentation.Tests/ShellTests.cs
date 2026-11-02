using ComexBol.Core;
using ComexBol.Core.Catalogo;
using ComexBol.Data;
using ComexBol.Presentation;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class ShellTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static readonly DateOnly Hoy = new(2026, 11, 2);
    public ShellTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    /// <summary>La búsqueda al escribir es asíncrona: se espera (hasta 3 s) a que se cumpla la condición.</summary>
    static async Task Esperar(Func<bool> condicion) { for (int i = 0; i < 60 && !condicion(); i++) await Task.Delay(50); }

    async Task CargarArancelMini()
    {
        PartidaNandina P(string c, string d, decimal ga, string u = "u") => new(c, d, ga, u, false, [], "TEST");
        await new ServicioCatalogo(_db).ImportarResultadoAsync(new([
            P("8471300010", "Máquinas automáticas para tratamiento de datos; portátiles / Tablet que incluya número IMEI", 0.10m),
            P("8471300090", "Máquinas automáticas para tratamiento de datos; portátiles / Las demás", 0.10m),
            P("0101210000", "Caballos, asnos, mulos y burdéganos, vivos. / Caballos / Reproductores de raza pura", 0.05m)], []), "2026");
    }

    async Task<MainViewModel> Operacion(string carpeta = "IMP-T1")
    {
        var vm = new MainViewModel(_db, () => Hoy) { UsuarioActual = "jaime" };
        vm.NuevaCarpeta = carpeta; await vm.NuevaImportacionCmd.ExecuteAsync(); return vm;
    }

    // ---------- Inicio de sesión ----------
    [Fact] public async Task Primer_Uso_Crea_Administrador_Y_Luego_Se_Ingresa_Con_Clave()
    {
        var l = new LoginViewModel(_db); await l.InicializarAsync(); Assert.True(l.PrimerUso);
        Assert.Null(await l.CrearAdministradorAsync("jaime", "Jaime Blanco", "clave123", "otra")); Assert.Contains("no coinciden", l.Mensaje);
        Assert.Null(await l.CrearAdministradorAsync("ja", "x", "clave123", "clave123")); Assert.NotEqual("", l.Mensaje);
        var admin = await l.CrearAdministradorAsync("jaime", "Jaime Blanco", "clave123", "clave123");
        Assert.Equal(ServicioUsuarios.Administrador, admin!.Rol);
        var l2 = new LoginViewModel(_db); await l2.InicializarAsync(); Assert.False(l2.PrimerUso);
        Assert.Null(await l2.IngresarAsync("jaime", "mala")); Assert.Contains("incorrectos", l2.Mensaje);
        Assert.NotNull(await l2.IngresarAsync("jaime", "clave123")); Assert.Equal("", l2.Mensaje);
    }

    [Fact] public async Task Shell_Navega_Y_Distingue_Administrador_De_Operador()
    {
        var adm = await new ServicioUsuarios(_db).CrearAsync("admin", "Admin", "clave123", ServicioUsuarios.Administrador);
        var op = await new ServicioUsuarios(_db).CrearAsync("oper", "", "clave123");
        var sa = new ShellViewModel(_db, adm, () => Hoy); var so = new ShellViewModel(_db, op, () => Hoy);
        Assert.True(sa.EsAdministrador); Assert.False(so.EsAdministrador); Assert.False(so.Catalogo.EsAdministrador); Assert.Equal("oper", so.NombreMostrado);
        await sa.InicializarAsync(); Assert.True(sa.EsPanel);
        await sa.Navegar("Operaciones"); Assert.True(sa.EsOperaciones && !sa.EsPanel);
        await sa.Navegar("Arancel"); Assert.True(sa.EsArancel); await sa.Navegar("Configuración"); Assert.True(sa.EsConfiguracion);
        bool cerro = false; sa.CerrarSesionSolicitada += () => cerro = true; sa.CerrarSesionCmd.Execute(null); Assert.True(cerro);
    }

    [Fact] public async Task Panel_Avisa_Lo_Que_Falta_Configurar()
    {
        var p = new PanelViewModel(_db, () => Hoy); await p.RefrescarAsync();
        Assert.Contains(p.Alertas, a => a.Contains("arancel no está cargado")); Assert.Contains(p.Alertas, a => a.Contains("tipo de cambio")); Assert.Equal("Sin registrar", p.TipoCambioHoy);
        await CargarArancelMini(); await new ServicioConfiguracion(_db).GuardarTipoCambioAsync(Hoy, "USD", 6.96m);
        await p.RefrescarAsync(); Assert.DoesNotContain(p.Alertas, a => a.Contains("arancel no está cargado") || a.Contains("tipo de cambio")); Assert.StartsWith("3 partidas", p.ArancelInfo.Replace("Bs ", ""));
    }

    // ---------- Selector de partidas ----------
    [Fact] public async Task Elegir_Partida_Rellena_La_Descripcion_Y_El_Resto_Es_Manual()
    {
        await CargarArancelMini(); var vm = await Operacion();
        vm.ItemPartida = "tablet"; await Esperar(() => vm.MostrarSugerencias);
        Assert.True(vm.MostrarSugerencias); var s = Assert.Single(vm.Sugerencias); Assert.Equal("8471300010", s.Codigo);
        vm.ElegirSugerencia(s);
        Assert.Equal("8471300010", vm.ItemPartida); Assert.Contains("Tablet que incluya número IMEI", vm.ItemDescripcion); Assert.Contains("GA 10%", vm.InfoPartida); Assert.False(vm.MostrarSugerencias);
        Assert.Equal(0m, vm.ItemValor);                       // valor, peso, etc. se digitan a mano
    }

    [Fact] public async Task Buscar_Por_Codigo_Parcial_Y_Escribir_El_Codigo_Completo_Muestra_Su_Informacion()
    {
        await CargarArancelMini(); var vm = await Operacion();
        vm.ItemPartida = "8471"; await Esperar(() => vm.Sugerencias.Count == 2); Assert.Equal(2, vm.Sugerencias.Count);
        vm.ItemPartida = "8471.30.00.90"; await Esperar(() => vm.InfoPartida.Length > 0); Assert.False(vm.MostrarSugerencias); Assert.Contains("GA 10%", vm.InfoPartida);
        vm.ItemPartida = "x"; await Esperar(() => !vm.MostrarSugerencias); Assert.False(vm.MostrarSugerencias);
    }

    // ---------- Ítems: validar, editar, eliminar ----------
    [Fact] public async Task Item_Invalido_Se_Rechaza_Con_Mensaje_Y_No_Queda_Guardado()
    {
        await CargarArancelMini(); var vm = await Operacion();
        vm.ItemPartida = "84713"; vm.ItemDescripcion = "x"; vm.ItemValor = 100; await vm.AgregarItemCmd.ExecuteAsync();
        Assert.StartsWith("AVISO", vm.Mensaje); Assert.Contains("10 dígitos", vm.Mensaje); Assert.Empty(vm.Items); Assert.Empty(_db.Items);
        vm.ItemPartida = "1234567890"; await vm.AgregarItemCmd.ExecuteAsync(); Assert.Contains("no existe en el arancel", vm.Mensaje); Assert.Empty(_db.Items);
    }

    [Fact] public async Task Editar_Un_Item_Y_Eliminarlo()
    {
        await CargarArancelMini(); var vm = await Operacion();
        vm.ItemPartida = "8471300010"; vm.ItemDescripcion = "Tablets"; vm.ItemValor = 1000; vm.ItemPesoBruto = 10; vm.ItemMarca = "Lenovo";
        await vm.AgregarItemCmd.ExecuteAsync();
        vm.ItemPartida = "8471300090"; vm.ItemDescripcion = "Laptops"; vm.ItemValor = 2000; await vm.AgregarItemCmd.ExecuteAsync();
        Assert.Equal(2, vm.Items.Count);

        vm.ItemSeleccionado = vm.Items[0]; await vm.EditarItemCmd.ExecuteAsync();
        Assert.True(vm.EnEdicion); Assert.Equal("Tablets", vm.ItemDescripcion); Assert.Equal("Lenovo", vm.ItemMarca); Assert.Equal("Guardar cambios del ítem", vm.TextoGuardarItem);
        vm.ItemValor = 1500; vm.ItemModelo = "Tab M10"; await vm.AgregarItemCmd.ExecuteAsync();
        Assert.False(vm.EnEdicion); Assert.Equal(2, _db.Items.Count()); Assert.Equal(1500m, _db.Items.Single(i => i.Numero == 1).ValorFactura); Assert.Equal("Tab M10", _db.Items.Single(i => i.Numero == 1).Modelo);
        Assert.Equal(0.10m, _db.Items.Single(i => i.Numero == 1).AlicuotaGA);          // el GA se vuelve a tomar del arancel

        vm.ItemSeleccionado = vm.Items[0]; await vm.EliminarItemCmd.ExecuteAsync();
        Assert.Single(vm.Items); Assert.Equal("Laptops", _db.Items.Single().Descripcion); Assert.Equal(1, _db.Items.Single().Numero);
        Assert.Contains(vm.Bitacora, b => b.Contains("Ítem eliminado") && b.Contains("[jaime]"));
    }

    [Fact] public async Task Eliminar_Una_Operacion_Equivocada()
    {
        var vm = await Operacion("IMP-ERRONEA"); vm.NuevaCarpeta = "IMP-BUENA"; await vm.NuevaImportacionCmd.ExecuteAsync();
        vm.Seleccionada = vm.Operaciones.First(o => o.Carpeta == "IMP-ERRONEA"); await vm.RefrescarAsync();
        await vm.EliminarOperacionAsync();
        Assert.Equal(new[] { "IMP-BUENA" }, vm.Operaciones.Select(o => o.Carpeta).ToArray()); Assert.Null(vm.Seleccionada); Assert.Contains("eliminada", vm.Mensaje);
        vm.FiltroOperaciones = "zzz"; Assert.Empty(vm.Operaciones); vm.FiltroOperaciones = "buena"; Assert.Single(vm.Operaciones);
    }

    // ---------- Tipo de cambio y costos ----------
    [Fact] public async Task El_Tipo_De_Cambio_Se_Propone_Desde_Configuracion_Y_Se_Aplica_Al_Calculo()
    {
        var vm0 = new MainViewModel(_db, () => Hoy); await vm0.CargarAsync(); Assert.Contains("Sin tipo de cambio", vm0.TcInfo);
        await new ServicioConfiguracion(_db).GuardarTipoCambioAsync(new DateOnly(2026, 10, 30), "USD", 7.00m, "BCB");
        await CargarArancelMini(); var vm = await Operacion(); Assert.Equal(7.00m, vm.TipoCambioUsd); Assert.Contains("30/10/2026", vm.TcInfo);
        vm.ItemPartida = "8471300010"; vm.ItemDescripcion = "x"; vm.ItemValor = 1000; vm.ItemPesoBruto = 5; await vm.AgregarItemCmd.ExecuteAsync();
        await vm.LiquidarCmd.ExecuteAsync();
        Assert.Contains(vm.Liquidacion, l => l.Concepto.StartsWith("CIF") && l.Monto == "7.000,00");
        vm.TipoCambioUsd = 7.20m; await vm.GuardarTcCmd.ExecuteAsync(); Assert.Equal(7.20m, (await new ServicioConfiguracion(_db).ObtenerTipoCambioAsync("USD", Hoy))!.BobPorUnidad);
    }

    [Fact] public async Task Los_Parametros_Y_La_Ufv_De_Configuracion_Se_Reflejan_En_La_Liquidacion()
    {
        var cfg = new ServicioConfiguracion(_db); await CargarArancelMini();
        await cfg.GuardarParametrosAsync(new ParametrosTributarios { UmbralBancarizacionBob = 5_000m }); await cfg.GuardarUfvAsync(Hoy, 2.5m);
        var vm = await Operacion(); vm.TipoCambioUsd = 7m;
        vm.ItemPartida = "8471300010"; vm.ItemDescripcion = "x"; vm.ItemValor = 1000; await vm.AgregarItemCmd.ExecuteAsync(); await vm.LiquidarCmd.ExecuteAsync();
        Assert.Contains(vm.Avisos, a => a.Contains("FOB desde Bs 5.000")); Assert.Contains(vm.Liquidacion, l => l.Concepto.StartsWith("CIF en UFV") && l.Monto == "2.800,00");
    }

    [Fact] public async Task Hoja_De_Costos_Proyectados_Vs_Reales_Desde_La_Ventana()
    {
        await CargarArancelMini(); var vm = await Operacion(); vm.TipoCambioUsd = 6.96m; vm.Flete = 1800; vm.Seguro = 150;
        vm.ItemPartida = "8471300010"; vm.ItemDescripcion = "Tablets"; vm.ItemValor = 40000; vm.ItemPesoBruto = 800; await vm.AgregarItemCmd.ExecuteAsync(); await vm.LiquidarCmd.ExecuteAsync();
        await vm.CargarProyectadoCmd.ExecuteAsync();
        var ga = vm.Costos.Single(c => c.Concepto.StartsWith("Gravamen")); Assert.Equal(29_197.20m, ga.Proyectado);
        ga.Real = 29_500m; Assert.Equal("302,80", ga.Diferencia);
        await vm.GuardarCostosCmd.ExecuteAsync(); Assert.Equal(29_500m, _db.Costos.Single(c => c.Concepto.StartsWith("Gravamen")).RealBob); Assert.Contains("Real registrado", vm.TotalesCostos);
        await vm.EliminarCostoCmd.ExecuteAsync(vm.Costos.Last()); Assert.Equal(9, vm.Costos.Count);
    }

    // ---------- Arancel (tabla) y configuración ----------
    [Fact] public async Task Tabla_Del_Arancel_Buscar_Agregar_Editar_Eliminar_Y_Importar()
    {
        var c = new CatalogoViewModel(_db); await c.CargarAsync(); Assert.False(c.ArancelCargado); Assert.Contains("NO está cargado", c.Info);
        await CargarArancelMini(); await c.CargarAsync(); Assert.True(c.ArancelCargado); Assert.Equal(3, c.Partidas.Count);
        c.Filtro = "caballos"; await Esperar(() => c.Partidas.Count == 1); Assert.Single(c.Partidas);

        c.NuevaCmd.Execute(null); Assert.True(c.EditorAbierto && c.EsNueva);
        c.Codigo = "9999.00.00.01"; c.Descripcion = "Producto nuevo de prueba"; c.GaPct = 15; c.Unidad = "kg"; await c.GuardarCmd.ExecuteAsync();
        Assert.Contains("agregada", c.Mensaje); Assert.Equal(4, (await new ServicioCatalogo(_db).InfoAsync()).Total);

        c.Filtro = "9999"; await Esperar(() => c.Partidas.Count == 1 && c.Partidas[0].Codigo == "9999000001"); c.Seleccionada = c.Partidas.Single(); Assert.False(c.EsNueva); Assert.Equal(15m, c.GaPct);
        c.GaPct = 20; await c.GuardarCmd.ExecuteAsync(); Assert.Equal(0.20m, (await new ServicioCatalogo(_db).ObtenerAsync("9999000001"))!.AlicuotaGA);
        c.GaPct = 80; await c.GuardarCmd.ExecuteAsync(); Assert.StartsWith("AVISO", c.Mensaje);
        c.Seleccionada = c.Partidas.Single(); await c.EliminarAsync(); Assert.Equal(3, (await new ServicioCatalogo(_db).InfoAsync()).Total);

        var csv = Path.Combine(Path.GetTempPath(), $"a-{Guid.NewGuid():N}.csv");
        await File.WriteAllTextAsync(csv, "Codigo;Descripcion;GA\n1111111111;Uno;5\n2222222222;Dos;10\n");
        try { var r = await c.ImportarAsync([csv], "2027"); Assert.Equal(2, r!.Importadas); Assert.Equal(2, c.Partidas.Count); } finally { File.Delete(csv); }
    }

    [Fact] public async Task Configuracion_Guarda_Tc_Ufv_Parametros_Perfil_Y_Usuarios()
    {
        var u = await new ServicioUsuarios(_db).CrearAsync("admin", "Admin", "clave123", ServicioUsuarios.Administrador);
        var c = new ConfiguracionViewModel(_db, () => Hoy) { UsuarioActualId = u.Id }; await c.CargarAsync();
        Assert.Equal(14.94m, c.IvaPct);
        c.TcValor = 6.96m; c.TcMoneda = "USD"; await c.GuardarTcCmd.ExecuteAsync(); Assert.Single(c.TiposCambio);
        c.TcValor = 0; await c.GuardarTcCmd.ExecuteAsync(); Assert.StartsWith("AVISO", c.Mensaje);
        c.TcSeleccionado = c.TiposCambio[0]; await c.EliminarTcAsync(); Assert.Empty(c.TiposCambio);
        c.UfvValor = 2.6m; await c.GuardarUfvCmd.ExecuteAsync(); Assert.Single(c.Ufvs);
        c.IvaPct = 13; c.UmbralBancarizacion = 70_000; await c.GuardarParametrosCmd.ExecuteAsync();
        Assert.Equal(0.13m, (await new ServicioConfiguracion(_db).ObtenerParametrosAsync()).TasaIvaEfectiva);
        await c.RestaurarParametrosCmd.ExecuteAsync(); Assert.Equal(14.94m, c.IvaPct);
        c.RazonSocial = "Jaime Blanco Villegas"; c.Nit = "1234567"; c.TipoImportador = "Habitual"; await c.GuardarPerfilCmd.ExecuteAsync(); Assert.Equal("Jaime Blanco Villegas", (await new ServicioConfiguracion(_db).ObtenerPerfilAsync()).RazonSocial);

        await c.CrearUsuarioAsync("maria", "María Pérez", "clave456", ServicioUsuarios.Operador); Assert.Equal(2, c.Usuarios.Count);
        c.UsuarioSeleccionado = c.Usuarios.Single(x => x.NombreUsuario == "maria"); await c.CambiarClaveAsync("nueva-clave"); Assert.NotNull(await new ServicioUsuarios(_db).AutenticarAsync("maria", "nueva-clave"));
        await c.AlternarActivoAsync(); Assert.False(c.Usuarios.Single(x => x.NombreUsuario == "maria").Activo);
        c.UsuarioSeleccionado = c.Usuarios.Single(x => x.NombreUsuario == "admin"); await c.AlternarActivoAsync(); Assert.Contains("propio usuario", c.Mensaje);
        var respaldo = Path.Combine(Path.GetTempPath(), $"r-{Guid.NewGuid():N}.db");
        try { await c.RespaldarAsync(respaldo); Assert.True(File.Exists(respaldo)); Assert.Contains("Respaldo guardado", c.Mensaje); } finally { SqliteConnection.ClearAllPools(); if (File.Exists(respaldo)) File.Delete(respaldo); }
    }
}
