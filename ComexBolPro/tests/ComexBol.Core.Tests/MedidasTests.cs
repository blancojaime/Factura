using ComexBol.Core;
using Xunit;

public class MedidasTests
{
    static TipoCambioTable Tc(DateOnly? f = null) => new(f ?? new DateOnly(2026, 11, 2), new Dictionary<string, decimal> { ["USD"] = 6.96m });
    static ItemImportacion Item(decimal valor, decimal ga, bool ben = false) => new(1, "8417209000", "Horno a gas", valor, 100, 90, ga, BeneficioDs5516: ben);
    static readonly DateOnly Antes = new(2026, 6, 1), Despues = new(2026, 11, 2), Vencido = new(2027, 2, 1);

    [Fact] public void Sin_Fecha_No_Se_Aplica_Ninguna_Medida()
    {
        var r = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", [Item(10_000m, 0.10m)], Flete: new(1_500m), Seguro: new(100m)), Tc());
        Assert.Equal(8_073.60m, r.GA);   // 10 % sobre CIF completo
    }

    [Fact] public void Antes_Del_6_De_Julio_Rige_El_Regimen_Anterior()
    {
        var r = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", [Item(10_000m, 0.10m)], Flete: new(1_500m), Seguro: new(100m), FechaDeclaracion: Antes), Tc());
        Assert.Equal(8_073.60m, r.GA);
    }

    [Fact] public void Ds5646_Reduce_5_Puntos_Y_Cambia_La_Base_Del_Ga()
    {
        // FOB 10.000, flete 1.500, seguro 100 → CIF 11.600 USD. Base GA = 10.000 + 10 % × 1.600 = 10.160 USD → ×6,96 = 70.713,60 Bs; alícuota 10 % → 5 %
        var r = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", [Item(10_000m, 0.10m)], Flete: new(1_500m), Seguro: new(100m), FechaDeclaracion: Despues), Tc());
        Assert.Equal(80_736.00m, r.CifBob);
        Assert.Equal(3_535.68m, r.GA);                                   // 70.713,60 × 5 %
        Assert.Equal(Math.Round(0.1494m * (80_736.00m + 3_535.68m), 2), r.IVA);   // el IVA sigue sobre el CIF completo + GA
        Assert.Equal(70_713.60m, r.Items[0].BaseGA); Assert.Equal(0.05m, r.Items[0].AlicuotaGAAplicada);
        Assert.Contains(r.Advertencias, a => a.Contains("D.S. 5646"));
    }

    [Fact] public void Carga_Y_Descarga_Entra_Completa_A_La_Base_Del_Ga_Y_Al_Cif()
    {
        var sin = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", [Item(10_000m, 0.10m)], Flete: new(1_500m), FechaDeclaracion: Despues), Tc());
        var con = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", [Item(10_000m, 0.10m)], Flete: new(1_500m), FechaDeclaracion: Despues, CargaDescarga: new(200m)), Tc());
        Assert.Equal(sin.CifBob + 200m * 6.96m, con.CifBob);
        Assert.Equal(sin.Items[0].BaseGA + 200m * 6.96m, con.Items[0].BaseGA);
    }

    [Fact] public void Ajustes_Art8_Integran_La_Base_Del_Ga()
    {
        var r = CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [Item(10_000m, 0.10m)], AdicionesArt8: new(1_000m), FechaDeclaracion: Despues), Tc());
        Assert.Equal(11_000m * 6.96m, r.Items[0].BaseGA);
    }

    [Fact] public void Alicuotas_Ds5646_Segun_La_Tabla()
    {
        foreach (var (a, e) in new[] { (0.40m, 0.35m), (0.35m, 0.30m), (0.30m, 0.25m), (0.25m, 0.20m), (0.20m, 0.15m), (0.15m, 0.10m), (0.10m, 0.05m), (0.05m, 0m), (0m, 0m) })
            Assert.Equal(e, MedidasArancelarias.AlicuotaGa(a, false, Despues).Alicuota);
        Assert.Equal(0.10m, MedidasArancelarias.AlicuotaGa(0.10m, false, new DateOnly(2028, 1, 2)).Alicuota);      // vencido el 31/12/2027
    }

    [Fact] public void Beneficio_Ds5516_Da_Cero_Hasta_El_31_De_Diciembre_Y_Luego_Cae_A_La_Rebaja_Del_5646()
    {
        Assert.Equal(0m, MedidasArancelarias.AlicuotaGa(0.10m, true, Despues).Alicuota);
        Assert.Equal(0m, MedidasArancelarias.AlicuotaGa(0.10m, true, new DateOnly(2026, 12, 31)).Alicuota);
        var (a, nota) = MedidasArancelarias.AlicuotaGa(0.10m, true, Vencido); Assert.Equal(0.05m, a); Assert.Contains("venció", nota);
        Assert.Equal(0.10m, MedidasArancelarias.AlicuotaGa(0.10m, true, new DateOnly(2026, 1, 5)).Alicuota);       // antes de la vigencia del D.S. 5516
    }

    [Fact] public void Beneficio_Por_Vencer_Advierte_Y_Vencido_Cobra()
    {
        var por = CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [Item(10_000m, 0.10m, true)], FechaDeclaracion: new DateOnly(2026, 12, 10)), Tc());
        Assert.Equal(0m, por.GA); Assert.Contains(por.Advertencias, a => a.Contains("vence el 31/12/2026"));
        var vencido = CalculadoraTributaria.Calcular(new(Incoterm.CIF, "USD", [Item(10_000m, 0.10m, true)], FechaDeclaracion: Vencido), Tc(Vencido));
        Assert.Equal(Math.Round(10_000m * 6.96m * 0.05m, 2), vencido.GA);
    }

    [Fact] public void Impacto_Compara_Regimen_Anterior_Ds5646_Y_Aplicado()
    {
        var op = new OperacionImportacion(Incoterm.FOB, "USD", [Item(10_000m, 0.10m, true)], Flete: new(1_500m), Seguro: new(100m), FechaDeclaracion: Despues);
        var f = ImpactoMedidas.Comparar(op, Tc(), new());
        var ga = f.Single(x => x.Concepto.StartsWith("Gravamen"));
        Assert.Equal(8_073.60m, ga.Anterior); Assert.Equal(3_535.68m, ga.ConDs5646); Assert.Equal(0m, ga.Aplicado); Assert.Equal(8_073.60m, ga.AhorroVsAnterior);
        var tot = f.Single(x => x.Concepto.StartsWith("TOTAL")); Assert.True(tot.Aplicado < tot.ConDs5646 && tot.ConDs5646 < tot.Anterior);
    }

    [Fact] public void Precio_Sugerido_Deja_El_Margen_Sobre_El_Precio()
    {
        var (sin, con) = Costeo.PrecioSugerido(700m, 0.30m); Assert.Equal(1_000m, sin); Assert.Equal(1_130m, con);
        Assert.Equal((0m, 0m), Costeo.PrecioSugerido(0m, 0.3m)); Assert.Equal((0m, 0m), Costeo.PrecioSugerido(100m, 1m));
    }

    [Fact] public void Importador_No_Habitual_Tiene_Topes_Por_Despacho_Y_Anual()
    {
        var d = new DatosDespacho("General", "10 - Importación a consumo", "Arica", "La Paz", "ADA", "Carretero", "CRT", 5, 100, "M", "DAV", "");
        var ok = Despacho.Validar(d, 100, 1, true, true, false, 0, regla: new("Ocasional", 1_500m, 1_000m));
        Assert.DoesNotContain(ok, h => h.Texto.Contains("no habitual"));
        Assert.Contains(Despacho.Validar(d, 100, 1, true, true, false, 0, regla: new("Ocasional", 2_500m, 0m)), h => h.Nivel == NivelHallazgo.Error && h.Texto.Contains("por despacho"));
        Assert.Contains(Despacho.Validar(d, 100, 1, true, true, false, 0, regla: new("Ocasional", 1_900m, 2_500m)), h => h.Nivel == NivelHallazgo.Error && h.Texto.Contains("acumulado anual"));
        Assert.DoesNotContain(Despacho.Validar(d, 100, 1, true, true, false, 0, regla: new("Habitual", 90_000m, 90_000m)), h => h.Texto.Contains("no habitual"));
    }

    [Fact] public void Guia_Tiene_11_Pasos_Y_12_Items_De_Control()
    {
        Assert.Equal(11, GuiaProcedimiento.Pasos.Count); Assert.Equal(12, GuiaProcedimiento.Control.Count);
        Assert.Equal(GuiaProcedimiento.Pasos.Count, GuiaProcedimiento.Pasos.Select(p => p.Codigo).Distinct().Count());
        Assert.All(GuiaProcedimiento.Pasos, p => { Assert.NotEmpty(p.Procedimiento); Assert.NotEmpty(p.Normativa); });
    }

    [Fact] public void Reproduce_El_Simulador_Del_Manual_De_Hornos_A_Gas()
    {
        // Hoja «3_Simulador» del manual: 4 modelos, flete 1.450 + seguro 180 USD, TC 6,96, GA 0 % por D.S. 5516, IVA 14,94 %.
        ItemImportacion H(int n, decimal q, decimal p, bool ben) => new(n, "8417209000", "Horno a gas", q * p, 100, 90, 0.10m, BeneficioDs5516: ben);
        ItemImportacion[] items(bool b) => [H(1, 4, 380m, b), H(2, 3, 620m, b), H(3, 2, 1_150m, b), H(4, 1, 2_400m, b)];
        var con = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", items(true), Flete: new(1_450m), Seguro: new(180m), FechaDeclaracion: new DateOnly(2026, 11, 20)), Tc(new DateOnly(2026, 11, 20)));
        Assert.Equal(9_710m * 6.96m, con.CifBob, 1);                         // 67.581,60 Bs
        Assert.Equal(0m, con.GA);
        Assert.Equal(1_450.67m * 6.96m, con.IVA, 1);                         // 10.096,7 Bs = USD 1.450,67 de la hoja del manual
        // «Sin beneficio» de la hoja: GA 10 % sobre el CIF completo (régimen anterior, sin decretos)
        var sin = CalculadoraTributaria.Calcular(new(Incoterm.FOB, "USD", items(false), Flete: new(1_450m), Seguro: new(180m)), Tc());
        Assert.Equal(971m * 6.96m, sin.GA, 1);
        Assert.Equal(2_566.74m * 6.96m, sin.TotalTributos, 1);
    }
}
