using ComexBol.Core;
using ComexBol.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

public class AdministracionTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    public AdministracionTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    // ---------- Usuarios ----------
    [Fact] public async Task Crea_Autentica_Y_No_Guarda_La_Clave_En_Texto()
    {
        var s = new ServicioUsuarios(_db);
        Assert.False(await s.HayUsuariosAsync());
        var u = await s.CrearAsync("Jaime", "Jaime Blanco", "secreto123", ServicioUsuarios.Administrador);
        Assert.Equal("jaime", u.NombreUsuario); Assert.DoesNotContain("secreto123", u.ClaveHash); Assert.NotEqual("", u.Sal);
        Assert.NotNull(await s.AutenticarAsync("JAIME", "secreto123"));          // el usuario no distingue mayúsculas
        Assert.Null(await s.AutenticarAsync("jaime", "otra-clave"));
        Assert.Null(await s.AutenticarAsync("nadie", "secreto123"));
        Assert.NotNull(_db.Usuarios.Single().UltimoAcceso);
    }

    [Fact] public async Task Valida_Usuario_Clave_Y_Duplicados()
    {
        var s = new ServicioUsuarios(_db);
        await Assert.ThrowsAsync<ArgumentException>(() => s.CrearAsync("ab", "x", "secreto123"));
        await Assert.ThrowsAsync<ArgumentException>(() => s.CrearAsync("juan", "x", "123"));
        await s.CrearAsync("juan", "Juan", "secreto123");
        await Assert.ThrowsAsync<InvalidOperationException>(() => s.CrearAsync("JUAN", "otro", "secreto123"));
    }

    [Fact] public async Task Siempre_Queda_Un_Administrador_Activo_Y_Un_Usuario_Inactivo_No_Entra()
    {
        var s = new ServicioUsuarios(_db);
        var admin = await s.CrearAsync("admin", "Admin", "secreto123", ServicioUsuarios.Administrador);
        var op = await s.CrearAsync("oper", "Operador", "secreto123");
        await Assert.ThrowsAsync<InvalidOperationException>(() => s.SetActivoAsync(admin.Id, false));
        await Assert.ThrowsAsync<InvalidOperationException>(() => s.CambiarRolAsync(admin.Id, ServicioUsuarios.Operador));
        await s.SetActivoAsync(op.Id, false);
        Assert.Null(await s.AutenticarAsync("oper", "secreto123"));
        await s.CambiarClaveAsync(admin.Id, "nueva-clave");
        Assert.Null(await s.AutenticarAsync("admin", "secreto123")); Assert.NotNull(await s.AutenticarAsync("admin", "nueva-clave"));
    }

    [Fact] public void Pbkdf2_Propio_Coincide_Con_La_Implementacion_Estandar()
    {
        var sal = System.Security.Cryptography.RandomNumberGenerator.GetBytes(16);
        var esperado = System.Security.Cryptography.Rfc2898DeriveBytes.Pbkdf2("clave-de-prueba ñ", sal, 5_000, System.Security.Cryptography.HashAlgorithmName.SHA256, 32);
        Assert.Equal(esperado, ServicioUsuarios.Pbkdf2Sha256(System.Text.Encoding.UTF8.GetBytes("clave-de-prueba ñ"), sal, 5_000));
    }

    // ---------- Configuración ----------
    [Fact] public async Task Tipo_De_Cambio_Se_Actualiza_Y_Se_Usa_El_Vigente_A_La_Fecha()
    {
        var c = new ServicioConfiguracion(_db);
        await c.GuardarTipoCambioAsync(new DateOnly(2026, 11, 1), "usd", 6.96m);
        await c.GuardarTipoCambioAsync(new DateOnly(2026, 11, 5), "USD", 7.10m, "BCB");
        await c.GuardarTipoCambioAsync(new DateOnly(2026, 11, 5), "USD", 7.12m);      // misma fecha: actualiza, no duplica
        Assert.Equal(2, _db.TiposCambio.Count());
        Assert.Equal(6.96m, (await c.ObtenerTipoCambioAsync("USD", new DateOnly(2026, 11, 3)))!.BobPorUnidad);
        Assert.Equal(7.12m, (await c.ObtenerTipoCambioAsync("USD", new DateOnly(2026, 12, 1)))!.BobPorUnidad);
        Assert.Null(await c.ObtenerTipoCambioAsync("USD", new DateOnly(2026, 10, 1)));
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarTipoCambioAsync(new DateOnly(2026, 11, 1), "USD", 0m));
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarTipoCambioAsync(new DateOnly(2026, 11, 1), "US", 6.96m));
        await c.EliminarTipoCambioAsync(_db.TiposCambio.First().Id); Assert.Single(_db.TiposCambio);
    }

    [Fact] public async Task Ufv_Y_Parametros_Se_Guardan_Y_Se_Aplican()
    {
        var c = new ServicioConfiguracion(_db);
        await c.GuardarUfvAsync(new DateOnly(2026, 11, 1), 2.61m);
        Assert.Equal(2.61m, (await c.ObtenerUfvAsync(new DateOnly(2026, 11, 20)))!.ValorBob);
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarUfvAsync(new DateOnly(2026, 11, 2), 500m));

        Assert.Equal(0.1494m, (await c.ObtenerParametrosAsync()).TasaIvaEfectiva);        // valores por defecto sin configurar
        await c.GuardarParametrosAsync(new ParametrosTributarios { TasaIvaEfectiva = 0.15m, UmbralBancarizacionBob = 60_000m, Redondeo = ModoRedondeo.EnteroBs });
        var p = await c.ObtenerParametrosAsync();
        Assert.Equal(0.15m, p.TasaIvaEfectiva); Assert.Equal(60_000m, p.UmbralBancarizacionBob); Assert.Equal(ModoRedondeo.EnteroBs, p.Redondeo);
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarParametrosAsync(new ParametrosTributarios { TasaIvaEfectiva = 1.5m }));
    }

    [Fact] public async Task Perfil_Del_Importador_Y_Respaldo()
    {
        var c = new ServicioConfiguracion(_db);
        await c.GuardarPerfilAsync(new() { RazonSocial = "Jaime Blanco Villegas", Nit = "123456", TipoImportador = "Habitual" });
        await c.GuardarPerfilAsync(new() { RazonSocial = "Jaime Blanco Villegas - Importaciones", Nit = "123456", TipoImportador = "Ocasional" });
        Assert.Single(_db.Perfiles); Assert.Equal("Ocasional", (await c.ObtenerPerfilAsync()).TipoImportador);
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarPerfilAsync(new() { TipoImportador = "Otro" }));

        var destino = Path.Combine(Path.GetTempPath(), $"respaldo-{Guid.NewGuid():N}.db");
        try
        {
            await c.RespaldarAsync(destino);
            using var cn2 = new SqliteConnection($"Data Source={destino};Mode=ReadOnly"); cn2.Open();
            using var cmd = cn2.CreateCommand(); cmd.CommandText = "SELECT RazonSocial FROM Perfiles"; Assert.Equal("Jaime Blanco Villegas - Importaciones", cmd.ExecuteScalar());
        }
        finally { SqliteConnection.ClearAllPools(); if (File.Exists(destino)) File.Delete(destino); }
    }

    // ---------- Operaciones, ítems y catálogo ----------
    static readonly TipoCambioTable Tc = new(new DateOnly(2026, 11, 2), new Dictionary<string, decimal> { ["USD"] = 6.96m });

    [Fact] public async Task Un_Item_Invalido_No_Se_Guarda_Y_No_Bloquea_El_Calculo()
    {   // Hallazgo del usuario: ítems con partida inválida quedaban guardados y luego bloqueaban «Calcular».
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-VAL", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        await Assert.ThrowsAsync<ArgumentException>(() => s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "", Descripcion = "x", ValorFactura = 100 }));
        await Assert.ThrowsAsync<ArgumentException>(() => s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "84713", Descripcion = "x", ValorFactura = 100 }));
        await Assert.ThrowsAsync<ArgumentException>(() => s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "", ValorFactura = 100 }));
        await Assert.ThrowsAsync<ArgumentException>(() => s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "x", ValorFactura = 0 }));
        Assert.Empty(_db.Items);
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471.30.00.10", Descripcion = "Tablets", ValorFactura = 1000, AlicuotaGA = 0.10m });
        Assert.Equal("8471300010", _db.Items.Single().CodigoNandina);
        Assert.Equal(6_960m, (await s.LiquidarAsync(op.Id, Tc)).CifBob);
    }

    [Fact] public async Task Con_Arancel_Cargado_Se_Rechaza_Una_Partida_Inexistente()
    {
        await new ServicioCatalogo(_db).ImportarResultadoAsync(new([new("8471300010", "Tablets", 0.10m, "u", false, [], "T")], []), "t");
        var s = new ServicioOperaciones(_db); var op = await s.CrearImportacionAsync("IMP-X", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        var ex = await Assert.ThrowsAsync<ArgumentException>(() => s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "1234567890", Descripcion = "x", ValorFactura = 10 }));
        Assert.Contains("no existe en el arancel", ex.Message);
    }

    [Fact] public async Task Edita_Elimina_Items_Renumera_Y_Registra_El_Usuario()
    {
        var s = new ServicioOperaciones(_db) { Usuario = "jaime" };
        var op = await s.CrearImportacionAsync("IMP-ED", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        for (int i = 1; i <= 3; i++) await s.AgregarItemAsync(op.Id, new() { Numero = i, CodigoNandina = "8471300010", Descripcion = $"Item {i}", ValorFactura = 100 * i, AlicuotaGA = 0.1m });
        var segundo = _db.Items.AsNoTracking().Single(x => x.Numero == 2);
        segundo.ValorFactura = 999; segundo.Descripcion = "Corregido"; segundo.Marca = "Lenovo";
        await s.ActualizarItemAsync(segundo);
        Assert.Equal(999m, _db.Items.Single(x => x.Id == segundo.Id).ValorFactura);
        await s.EliminarItemAsync(_db.Items.Single(x => x.Numero == 1).Id);
        Assert.Equal(new[] { 1, 2 }, _db.Items.OrderBy(x => x.Numero).Select(x => x.Numero).ToArray());
        Assert.Equal("Corregido", _db.Items.Single(x => x.Numero == 1).Descripcion);
        Assert.All(_db.Bitacora.Where(b => b.Categoria == "Ítem"), b => Assert.Equal("jaime", b.Usuario));
    }

    [Fact] public async Task Elimina_Una_Operacion_Con_Todo_Su_Contenido()
    {
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-BORRAR", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "x", ValorFactura = 100, AlicuotaGA = 0.1m });
        await s.LiquidarAsync(op.Id, Tc);
        await new ServicioCostos(_db).GuardarAsync(new() { OperacionId = op.Id, Concepto = "Transporte", ProyectadoBob = 100 });
        var otra = await s.CrearImportacionAsync("IMP-QUEDA", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        await s.EliminarOperacionAsync(op.Id);
        Assert.Equal("IMP-QUEDA", _db.Operaciones.Single().Carpeta);
        Assert.Empty(_db.Items); Assert.Empty(_db.Liquidaciones); Assert.Empty(_db.Costos);
        Assert.DoesNotContain(_db.Etapas, e => e.OperacionId == op.Id);
        Assert.True(_db.Etapas.Any(e => e.OperacionId == otra.Id));
    }

    [Fact] public async Task Costos_Reales_Vs_Proyectados()
    {
        var s = new ServicioOperaciones(_db); var k = new ServicioCostos(_db);
        var op = await s.CrearImportacionAsync("IMP-COSTOS", Incoterm.FOB, "USD", new DateOnly(2026, 11, 2));
        op.Flete = 1800; op.Seguro = 150; await _db.SaveChangesAsync();
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "Tablets", ValorFactura = 40000, AlicuotaGA = 0.1m });
        await s.LiquidarAsync(op.Id, Tc);
        Assert.Equal(10, await k.CargarProyectadoDesdeLiquidacionAsync(op.Id, Tc));
        Assert.Equal(0, await k.CargarProyectadoDesdeLiquidacionAsync(op.Id, Tc));          // no duplica
        var gastos = (await k.ListarAsync(op.Id)).ToDictionary(c => c.Concepto);
        Assert.Equal(29_197.20m, gastos["Gravamen arancelario (GA)"].ProyectadoBob);
        Assert.Equal(47_982.68m, gastos["IVA importaciones"].ProyectadoBob);
        var ga = gastos["Gravamen arancelario (GA)"]; ga.RealBob = 29_500m; await k.GuardarAsync(ga);
        Assert.Equal(29_500m, (await k.ListarAsync(op.Id)).Single(c => c.Concepto == ga.Concepto).RealBob);
    }

    [Fact] public async Task Catalogo_Se_Puede_Mantener_Agregar_Editar_Eliminar()
    {
        var c = new ServicioCatalogo(_db);
        await c.ImportarResultadoAsync(new([new("8471300010", "Tablets", 0.10m, "u", false, [], "ANB-2026")], []), "2026");
        await c.GuardarPartidaAsync(new() { Codigo = "8999.99.99.99", Descripcion = "Producto nuevo", AlicuotaGA = 0.15m, Unidad = "u" }, true);
        var info = await c.InfoAsync(); Assert.Equal(2, info.Total); Assert.Equal(1, info.Manuales); Assert.Equal("2026", info.Version);
        await Assert.ThrowsAsync<InvalidOperationException>(() => c.GuardarPartidaAsync(new() { Codigo = "8999999999", Descripcion = "x" }, true));
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarPartidaAsync(new() { Codigo = "123", Descripcion = "x" }, true));
        await Assert.ThrowsAsync<ArgumentException>(() => c.GuardarPartidaAsync(new() { Codigo = "8471300010", Descripcion = "x", AlicuotaGA = 0.5m }, false));
        var p = (await c.ObtenerAsync("8471300010"))!; p.AlicuotaGA = 0.05m; await c.GuardarPartidaAsync(p, false);
        Assert.Equal(0.05m, (await c.ObtenerAsync("8471300010"))!.AlicuotaGA); Assert.EndsWith("(modificada)", (await c.ObtenerAsync("8471300010"))!.Fuente);
        await c.EliminarPartidaAsync("8999999999"); Assert.Equal(1, (await c.InfoAsync()).Total);
        Assert.Single(await c.ListarAsync("tablet")); Assert.Single(await c.ListarAsync(null));
    }
}
