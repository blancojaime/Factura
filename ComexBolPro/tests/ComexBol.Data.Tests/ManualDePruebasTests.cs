using ComexBol.Core;
using ComexBol.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Xunit;

/// <summary>Cada prueba corresponde a un caso de docs/04-Manual-de-Implementacion-y-Pruebas.md. Si cambia una cifra, cambie el manual.</summary>
public class ManualDePruebasTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static readonly TipoCambioTable Tc = new(new DateOnly(2026, 11, 2), new Dictionary<string, decimal> { ["USD"] = 6.96m });
    static string Muestra => Path.Combine(AppContext.BaseDirectory, "fixtures", "arancel-muestra.md");

    public ManualDePruebasTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.Database.EnsureCreated(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    static ItemImportacion It(string c, decimal v, decimal ga, decimal peso = 500, decimal ice = 0) => new(1, c, "x", v, peso, peso, ga, 0, ice);

    [Fact] public void Caso1_Tablets_FOB()
    {
        var r = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", [It("8471300010", 40000m, .10m, 800)], Flete: new(1800m), Seguro: new(150m)), Tc);
        Assert.Equal(278_400.00m, r.ValorFobBob); Assert.Equal(291_972.00m, r.CifBob);
        Assert.Equal(29_197.20m, r.GA); Assert.Equal(47_982.68m, r.IVA); Assert.Equal(77_179.88m, r.TotalTributos);
        var v = Viabilidad.Importacion(r, 4500m, 200m, 2800m);
        Assert.Equal(325_669.20m, v.CostoTotalPuestoEnAlmacen); Assert.Equal(1_628.35m, Math.Round(v.CostoUnitario, 2)); Assert.Equal(34.3m, Math.Round(v.MargenPct * 100, 1));
    }

    [Fact] public void Caso2_Escenarios_FOB_CIF_DAP()
    {
        var res = Escenarios.Comparar([
            new("FOB + flete propio", new(Incoterm.FOB, "USD", [It("8471300010", 40000m, .10m, 800)], Flete: new(1800m), Seguro: new(150m))),
            new("CIF del proveedor", new(Incoterm.CIF, "USD", [It("8471300010", 42000m, .10m, 800)])),
            new("DAP del proveedor", new(Incoterm.DAP, "USD", [It("8471300010", 44000m, .10m, 800)], DeduccionesPostFrontera: new(1200m)))],
            Tc, 4500m, 200m, 2800m);
        Assert.Equal(new[] { "FOB + flete propio", "CIF del proveedor", "DAP del proveedor" }, res.Select(x => x.Nombre).ToArray());
        Assert.Equal(new[] { 1628.35m, 1630.26m, 1660.88m }, res.Select(x => Math.Round(x.Viabilidad.CostoUnitario, 2)).ToArray());
        Assert.All(res, x => Assert.Equal("Viable", x.Veredicto));
    }

    [Fact] public void Caso3_Reproductores_CFR_Suma_Seguro()
    {
        var r = CalculadoraTributaria.Calcular(new(Incoterm.CFR, "USD", [It("0101210000", 25000m, .05m, 3000)], Seguro: new(250m)), Tc);
        Assert.Equal(175_740.00m, r.CifBob); Assert.Equal(8_787.00m, r.GA); Assert.Equal(27_568.33m, r.IVA); Assert.Equal(36_355.33m, r.TotalTributos);
    }

    [Fact] public async Task Caso4_Tractor_Usado_Ice_Por_Antiguedad()
    {
        var c = new ServicioCatalogo(_db); await c.ImportarArancelMarkdownAsync([new StreamReader(Muestra)], "2026");
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-TRACTOR", Incoterm.FOB, "USD", new DateOnly(2026, 11, 2));
        op.Flete = 2500; op.Seguro = 200; await _db.SaveChangesAsync();
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8701210000", Descripcion = "Tractor de carretera usado", ValorFactura = 20000, PesoBrutoKg = 4000, PesoNetoKg = 4000, AntiguedadAnios = 3 });
        await c.AplicarAOperacionAsync(op.Id);
        var r = await s.LiquidarAsync(op.Id, Tc);
        Assert.Equal(157_992.00m, r.CifBob); Assert.Equal(7_899.60m, r.GA); Assert.Equal(49_767.48m, r.ICE);
        Assert.Equal(32_219.47m, r.IVA); Assert.Equal(89_886.55m, r.TotalTributos);
    }

    [Fact] public void Caso5_Umbral_De_Bancarizacion()
    {
        var bajo = CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [It("8471300090", 7000m, .10m)]), Tc);
        Assert.Equal(48_720.00m, bajo.ValorFobBob); Assert.False(bajo.RequiereBancarizacion); Assert.Equal(12_878.64m, bajo.TotalTributos);
        var tope = CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [It("8471300090", 50000m / 6.96m, .10m)]), Tc);
        Assert.True(tope.RequiereBancarizacion); Assert.Equal(13_217.00m, tope.TotalTributos);
    }

    [Fact] public async Task Caso6_Whisky_Avisa_Que_El_Ice_Se_Ingresa_A_Mano()
    {
        var c = new ServicioCatalogo(_db); await c.ImportarArancelMarkdownAsync([new StreamReader(Muestra)], "2026");
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-WHISKY", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "2208300000", Descripcion = "Whisky", ValorFactura = 10000 });
        var avisos = await c.AplicarAOperacionAsync(op.Id);
        Assert.Equal(0.40m, _db.Items.Single().AlicuotaGA);
        Assert.Contains(avisos, a => a.Contains("ICE") && a.Contains("manualmente"));
        Assert.Contains(avisos, a => a.Contains("SENASAG"));
    }

    [Fact] public async Task Caso7_Prohibida_Bloquea_Y_Medicamento_Pide_Agemed()
    {
        var c = new ServicioCatalogo(_db); await c.ImportarArancelMarkdownAsync([new StreamReader(Muestra)], "2026");
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-MED", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "3004901000", Descripcion = "Plasma sintético", ValorFactura = 5000 });
        Assert.Contains(await c.AplicarAOperacionAsync(op.Id), a => a.Contains("AGEMED"));
        await s.AgregarItemAsync(op.Id, new() { Numero = 2, CodigoNandina = "8703231010", Descripcion = "Vehículo GLP", ValorFactura = 9000 });
        var ex = await Assert.ThrowsAsync<InvalidOperationException>(() => c.AplicarAOperacionAsync(op.Id));
        Assert.Contains("prohibida", ex.Message);
    }

    [Fact] public async Task Caso8_Seguimiento_De_La_Ruta_Con_Fechas()
    {
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-RUTA", Incoterm.FOB, "USD", new DateOnly(2026, 11, 2));
        var plan = (await s.EstadoRutaAsync(op.Id, new DateOnly(2026, 11, 2))).ToDictionary(e => e.Etapa.Codigo);
        Assert.Equal(new DateOnly(2026, 11, 4), plan["I01"].Etapa.FinPlan);
        await s.CompletarEtapaAsync(op.Id, "I01", new DateOnly(2026, 11, 4));
        var tarde = (await s.EstadoRutaAsync(op.Id, new DateOnly(2026, 11, 20))).ToDictionary(e => e.Etapa.Codigo);
        Assert.Equal(Semaforo.Cumplido, tarde["I01"].Semaforo);
        Assert.Equal(Semaforo.Vencido, tarde["I02"].Semaforo);
        Assert.Equal(Semaforo.Pendiente, tarde["I12"].Semaforo);
        Assert.Contains("## Bitácora", await s.GenerarExpedienteAsync(op.Id, new DateOnly(2026, 11, 20)));
    }

    [Fact] public async Task Caso9_Arancel_Oficial_Completo_Si_Se_Indica_La_Carpeta()
    {
        var dir = Environment.GetEnvironmentVariable("COMEXBOL_ARANCEL_DIR");
        if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return;      // opcional: apunta a la carpeta con los 3 .md
        var archivos = Directory.GetFiles(dir, "*.md").OrderBy(f => f).Select(f => (TextReader)new StreamReader(f)).ToList();
        var r = await new ServicioCatalogo(_db).ImportarArancelMarkdownAsync(archivos, "2026");
        Assert.Equal(8121, r.Importadas);
        Assert.Equal(97, _db.Partidas.Select(p => p.Codigo.Substring(0, 2)).Distinct().Count());
        Assert.Equal(7917, _db.Partidas.Count(p => p.PrefAsignada));      // el resto queda sin asignar por ambigüedad del Markdown
    }
}

public class PreferenciasTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static readonly TipoCambioTable Tc = new(new DateOnly(2026, 11, 2), new Dictionary<string, decimal> { ["USD"] = 6.96m });
    public PreferenciasTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.Database.EnsureCreated(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    [Fact] public async Task Caso15_Desgravacion_Exige_Acuerdo_Y_Certificado_De_Origen()
    {
        var s = new ServicioOperaciones(_db);
        var op = await s.CrearImportacionAsync("IMP-PREF", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        await Assert.ThrowsAsync<ArgumentException>(() => s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "x", ValorFactura = 1000, AlicuotaGA = .10m, Desgravacion = 1m }));
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8471300010", Descripcion = "Tablets", ValorFactura = 1000, AlicuotaGA = .10m, Desgravacion = 1m, AcuerdoPreferencial = "CAN" });
        var r = await s.LiquidarAsync(op.Id, Tc);
        Assert.Equal(6_960.00m, r.CifBob); Assert.Equal(0m, r.GA); Assert.Equal(1_039.82m, r.IVA);     // IVA 14,94 % sobre CIF; GA exonerado
        Assert.Contains(await s.ChecklistAsync(op.Id), x => x.Tipo == TipoDocumento.CertificadoOrigen && !x.Presente);
    }
}

public class PreferenciaDelArancelTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    static string Muestra => Path.Combine(AppContext.BaseDirectory, "fixtures", "arancel-muestra.md");
    public PreferenciaDelArancelTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.Database.EnsureCreated(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    async Task<(ServicioCatalogo c, ServicioOperaciones s, Operacion op)> Preparar()
    {
        var c = new ServicioCatalogo(_db); await c.ImportarArancelMarkdownAsync([new StreamReader(Muestra)], "2026");
        var s = new ServicioOperaciones(_db); var op = await s.CrearImportacionAsync("IMP-P", Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        return (c, s, op);
    }

    [Fact] public async Task Caso16_Acuerdo_Elegido_Toma_La_Preferencia_Del_Arancel()
    {
        var (c, s, op) = await Preparar();
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "0101210000", Descripcion = "Reproductor", ValorFactura = 1000, AcuerdoPreferencial = "CAN" });
        var avisos = await c.AplicarAOperacionAsync(op.Id);
        Assert.Equal(1m, _db.Items.Single().Desgravacion);
        Assert.Contains(avisos, a => a.Contains("tomada del arancel"));
        Assert.True(_db.Operaciones.Single().UsaPreferenciaArancelaria);
    }

    [Fact] public async Task Caso17_Mexico_Sin_Preferencia_En_Aceites_Y_Chile_50()
    {
        var (c, s, op) = await Preparar();
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "1507100000", Descripcion = "Aceite", ValorFactura = 1000, AcuerdoPreferencial = "ACE 66 (México)" });
        await s.AgregarItemAsync(op.Id, new() { Numero = 2, CodigoNandina = "2103901000", Descripcion = "Mayonesa", ValorFactura = 1000, AcuerdoPreferencial = "ACE 22 (Chile)" });
        await c.AplicarAOperacionAsync(op.Id);
        var it = _db.Items.OrderBy(i => i.Numero).ToList();
        Assert.Equal(0m, it[0].Desgravacion);       // México 0 % en aceites
        Assert.Equal(0.5m, it[1].Desgravacion);     // Chile 50 %
    }

    [Fact] public async Task Declarar_Distinto_Al_Arancel_Avisa()
    {
        var (c, s, op) = await Preparar();
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "2103901000", Descripcion = "Mayonesa", ValorFactura = 1000, AcuerdoPreferencial = "ACE 22 (Chile)", Desgravacion = 1m });
        Assert.Contains(await c.AplicarAOperacionAsync(op.Id), a => a.Contains("declaró") && a.Contains("50"));
    }
}

public class IceVariableYEsquemaTests : IDisposable
{
    readonly SqliteConnection _cn = new("Data Source=:memory:"); readonly ComexDb _db;
    public IceVariableYEsquemaTests() { _cn.Open(); _db = new(new DbContextOptionsBuilder<ComexDb>().UseSqlite(_cn).Options); _db.AsegurarEsquema(); }
    public void Dispose() { _db.Dispose(); _cn.Dispose(); }

    static ComexBol.Core.Catalogo.PartidaNandina Vehiculo(string codigo, decimal[] tasas, bool omas) =>
        new(codigo, "Vehículo de prueba", 0.10m, "u", false, [], "TEST") { ImpuestoEspecial = "ICE", IceAntiguedad = tasas, IceUltimaEsOMas = omas };

    async Task<(IReadOnlyList<string> avisos, ItemMercancia item)> Probar(decimal[] tasas, bool omas, int anios)
    {
        var c = new ServicioCatalogo(_db);
        await c.ImportarResultadoAsync(new([Vehiculo("8703221020", tasas, omas)], []), "t");
        var s = new ServicioOperaciones(_db); var op = await s.CrearImportacionAsync("IMP-" + Guid.NewGuid().ToString("N")[..6], Incoterm.CIF, "USD", new DateOnly(2026, 11, 2));
        await s.AgregarItemAsync(op.Id, new() { Numero = 1, CodigoNandina = "8703221020", Descripcion = "v", ValorFactura = 1000, AntiguedadAnios = anios });
        var avisos = await c.AplicarAOperacionAsync(op.Id);
        return (avisos, _db.Items.Single(i => i.OperacionId == op.Id));
    }

    [Fact] public async Task Tabla_De_Dos_Columnas_Usa_La_Tasa_De_Su_Antiguedad()
    {
        var (_, nuevo) = await Probar([0m, 0.15m], false, 0); Assert.Equal(0m, nuevo.AlicuotaIce);
        var (_, uno) = await Probar([0m, 0.15m], false, 1); Assert.Equal(0.15m, uno.AlicuotaIce);
    }

    [Fact] public async Task Antiguedad_Fuera_De_La_Tabla_No_Inventa_Tasa()
    {
        var (avisos, it) = await Probar([0m, 0.15m], false, 4);
        Assert.Equal(0m, it.AlicuotaIce); Assert.Contains(avisos, a => a.Contains("solo prevé tasa ICE hasta 1"));
    }

    [Fact] public async Task Columna_Mayor_O_Igual_Rige_Para_Mayores_Antiguedades()
    {
        var (avisos, it) = await Probar([0.10m, 0.15m, 0.20m, 0.25m], true, 5);
        Assert.Equal(0.25m, it.AlicuotaIce); Assert.Contains(avisos, a => a.Contains("3 años o más"));
    }

    [Fact] public void Base_Antigua_Recibe_Las_Columnas_Nuevas_Sin_Perder_Datos()
    {
        _db.Database.ExecuteSqlRaw("INSERT INTO Partidas (Codigo,Descripcion,AlicuotaGA,Unidad,Prohibida,Autorizaciones,Fuente,Version,TipoDocumento,Entidad,DispLegal,ImpuestoEspecial,IceAntiguedad,Preferencias,PrefAsignada,PrefCan,PrefChile,PrefProtocolo,PrefMexico,IceUltimaEsOMas,DespachoFrontera) VALUES ('0101210000','x',0.05,'u',0,'','t','1','','','','','','',0,'','','','',0,'')");
        _db.Database.ExecuteSqlRaw("ALTER TABLE Partidas DROP COLUMN DespachoFrontera");
        _db.Database.ExecuteSqlRaw("ALTER TABLE Partidas DROP COLUMN IceUltimaEsOMas");
        _db.AsegurarEsquema();
        var p = _db.Partidas.AsNoTracking().Single();
        Assert.Equal("", p.DespachoFrontera); Assert.False(p.IceUltimaEsOMas); Assert.Equal(0.05m, p.AlicuotaGA);
    }

    [Fact] public void Base_Antigua_Recibe_Las_Tablas_Nuevas()
    {
        _db.Database.ExecuteSqlRaw("DROP TABLE Costos"); _db.Database.ExecuteSqlRaw("DROP TABLE Usuarios"); _db.Database.ExecuteSqlRaw("DROP TABLE Parametros");
        _db.AsegurarEsquema(); _db.AsegurarEsquema();   // idempotente
        Assert.Empty(_db.Costos.ToList()); Assert.Empty(_db.Usuarios.ToList()); Assert.Empty(_db.Parametros.ToList());
    }
}
