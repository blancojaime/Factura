using ComexBol.Core;
using Xunit;

public class CalculadoraTests
{
    static TipoCambioTable Tc() => new(new DateOnly(2026, 11, 1), new Dictionary<string, decimal> { ["USD"] = 6.96m });

    static ItemImportacion Item(int n, decimal valor, decimal ga, decimal peso = 100) =>
        new(n, "8471300000", "Equipo", valor, peso, peso * .9m, ga);

    [Fact]
    public void Fob_Con_Flete_Y_Seguro_Calcula_Cif_GA_E_Iva()
    {
        var op = new OperacionImportacion(Incoterm.FOB, "USD", [Item(1, 10_000m, 0.10m)],
            Flete: new(1_500m), Seguro: new(100m));
        var r = CalculadoraTributaria.Calcular(op, Tc());
        Assert.Equal(80_736.00m, r.CifBob);        // 11.600 × 6,96
        Assert.Equal(8_073.60m, r.GA);             // 10%
        Assert.Equal(13_268.15m, r.IVA);           // 14,94% × 88.809,60
        Assert.Equal(r.GA + r.IVA, r.TotalTributos);
        Assert.True(r.RequiereBancarizacion);
    }

    [Fact]
    public void Cif_Ignora_Flete_Ya_Incluido_Y_Advierte()
    {
        var op = new OperacionImportacion(Incoterm.CIF, "USD", [Item(1, 1_000m, 0m)], Flete: new(500m));
        var r = CalculadoraTributaria.Calcular(op, Tc());
        Assert.Equal(6_960.00m, r.CifBob);
        Assert.Contains(r.Advertencias, a => a.Contains("Flete ignorado"));
    }

    [Fact]
    public void Ddp_Deduce_Costos_Post_Frontera()
    {
        var op = new OperacionImportacion(Incoterm.DDP, "USD", [Item(1, 1_000m, 0m)], DeduccionesPostFrontera: new(200m));
        Assert.Equal(5_568.00m, CalculadoraTributaria.Calcular(op, Tc()).CifBob);
    }

    [Fact]
    public void Prorrateo_Reparte_Costos_Y_Suma_Exacta()
    {
        var op = new OperacionImportacion(Incoterm.FOB, "USD",
            [Item(1, 3_000m, 0.05m), Item(2, 1_000m, 0.20m)], Flete: new(400m), Seguro: new(40m));
        var r = CalculadoraTributaria.Calcular(op, Tc());
        Assert.Equal(r.Items.Sum(i => i.CifBob), r.CifBob);
        Assert.Equal((4_000m + 440m) * 6.96m, r.CifBob, 1);
    }

    [Fact]
    public void Ice_E_Iehd_Entran_En_Base_Del_Iva()
    {
        var it = Item(1, 1_000m, 0.10m) with { AlicuotaIceAdValorem = 0.10m, IehdBsPorLitro = 1.5m, Litros = 100m };
        var r = CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [it]), Tc());
        var cif = 6_960m; var ga = 696m; var ice = (cif + ga) * 0.10m; var iehd = 150m;
        Assert.Equal(Math.Round(0.1494m * (cif + ga + ice + iehd), 2), r.IVA);
    }

    [Fact]
    public void Desgravacion_Total_Anula_GA()
    {
        var it = Item(1, 1_000m, 0.20m) with { DesgravacionPreferencial = 1m };
        Assert.Equal(0m, CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [it]), Tc()).GA);
    }

    [Theory]
    [InlineData("123")]
    [InlineData("12345ABCDE")]
    public void Partida_Invalida_Se_Rechaza(string codigo)
    {
        var it = Item(1, 100m, 0m) with { CodigoArancelario = codigo };
        Assert.Throws<ArgumentException>(() => CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [it]), Tc()));
    }

    [Fact]
    public void Alicuota_Sobre_40_Se_Rechaza() =>
        Assert.Throws<ArgumentException>(() =>
            CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [Item(1, 100m, 0.41m)]), Tc()));

    [Fact]
    public void Bancarizacion_Umbral()
    {
        Assert.False(Bancarizacion.Requiere(49_999.99m));
        Assert.True(Bancarizacion.Requiere(50_000m));
    }

    [Fact]
    public void Cpm_Importacion_Tiene_Ruta_Critica_Y_Sin_Ciclos()
    {
        var cpm = RutaCritica.Calcular(RutaCritica.PlantillaImportacion());
        Assert.Contains(cpm, e => e.Etapa.Id == "I12" && e.EsCritica);
        Assert.All(cpm, e => Assert.True(e.Holgura >= 0));
        Assert.Equal(cpm.Max(e => e.EF), cpm.First(e => e.Etapa.Id == "I12").EF);
        RutaCritica.Calcular(RutaCritica.PlantillaExportacion());
    }

    [Fact]
    public void Cpm_Detecta_Ciclo() =>
        Assert.Throws<ArgumentException>(() => RutaCritica.Calcular([
            new("A","a",1,"x",["B"]), new("B","b",1,"x",["A"])]));

    [Fact]
    public void Viabilidad_Y_Cedeim()
    {
        var op = new OperacionImportacion(Incoterm.CIF, "USD", [Item(1, 1_000m, 0.10m)]);
        var liq = CalculadoraTributaria.Calcular(op, Tc());
        var v = Viabilidad.Importacion(liq, 500m, 100m, 150m);
        Assert.Equal(liq.CifBob + liq.GA + 500m, v.CostoTotalPuestoEnAlmacen);
        Assert.Equal(1_000m, Exportacion.CedeimEstimado(5_000m, 10_000m, 0.10m));
        Assert.Equal(0m, Almacenaje.Estimar(new(10, 5m), 8, 2_000m));
    }
}
