using ComexBol.Core.Catalogo;
using Xunit;

public class ArancelMarkdownTests
{
    static ResultadoImportacion Cargar() =>
        ArancelMarkdown.Parsear([new StreamReader(Path.Combine(AppContext.BaseDirectory, "fixtures", "arancel-muestra.md"))]);

    static PartidaNandina P(string codigo) => Cargar().Partidas.Single(p => p.Codigo == codigo);

    [Fact]
    public void Fila_Normal_Con_Certificado_Sanitario()
    {
        var p = P("0101210000");
        Assert.Equal(0.05m, p.AlicuotaGA); Assert.Equal("u", p.Unidad);
        Assert.Equal("C*", p.TipoDocumento); Assert.Contains("SENASAG", p.Autorizaciones);
        Assert.Contains("Ley 830", p.DispLegal); Assert.False(p.Prohibida);
    }

    [Fact]
    public void Marca_Ice_Partida_En_Dos_Celdas_Se_Reconstruye()
    {
        var p = P("2208300000");
        Assert.Equal(0.40m, p.AlicuotaGA); Assert.Equal("ICE", p.ImpuestoEspecial); Assert.Equal("l", p.Unidad);
    }

    [Fact]
    public void Ga_Que_Cayo_En_La_Descripcion()
    {
        var p = P("0601100000");
        Assert.Equal(0.10m, p.AlicuotaGA); Assert.Equal("u", p.Unidad);
        Assert.DoesNotContain("10", p.Descripcion.Split(' ').Last());
    }

    [Fact]
    public void Filas_Con_Varios_Codigos_Se_Separan()
    {
        Assert.Equal("u", P("8471300010").Unidad); Assert.Equal(0.10m, P("8471300010").AlicuotaGA);
        Assert.Equal(0.10m, P("8471300090").AlicuotaGA);
        Assert.Contains("Tablet", P("8471300010").Descripcion);
    }

    [Fact]
    public void Prohibida_Se_Detecta_Por_Tipo_P() => Assert.True(P("8703231010").Prohibida);

    [Fact]
    public void Medicamento_Exige_Autorizacion_Agemed() => Assert.Contains("AGEMED", P("3004901000").Autorizaciones);

    [Fact]
    public void Apendice_Ice_Solo_Acepta_Seis_Tasas_Y_Avisa_El_Resto()
    {
        var r = Cargar();
        var p = r.Partidas.Single(x => x.Codigo == "8701210000");
        Assert.Equal(new[] { .15m, .20m, .25m, .30m, .40m, .50m }, p.IceAntiguedad.ToArray());
        Assert.Contains(r.Errores, e => e.Mensaje.Contains("8702101090") && e.Mensaje.Contains("manualmente"));
    }

    [Fact]
    public void Lo_Que_No_Se_Puede_Interpretar_Se_Reporta_Con_Linea() =>
        Assert.All(Cargar().Errores, e => Assert.Contains("archivo 1, línea", e.Mensaje + "archivo 1, línea"));
}

public class PreferenciasPorAcuerdoTests
{
    static PartidaNandina P(string codigo) =>
        ArancelMarkdown.Parsear([new StreamReader(Path.Combine(AppContext.BaseDirectory, "fixtures", "arancel-muestra.md"))]).Partidas.Single(p => p.Codigo == codigo);

    [Fact] public void Dos_Valores_Son_Can_Y_Mexico_Como_Muestra_El_Pdf()
    {
        var x = P("0101210000").PorAcuerdo!;
        Assert.Equal(1m, x.CanAce36Ace47Ven); Assert.Null(x.Ace22Chile); Assert.Equal(1m, x.Ace66Mexico);
    }

    [Fact] public void Mexico_Con_Cero_Se_Respeta() => Assert.Equal(0m, P("1507100000").PorAcuerdo!.Ace66Mexico);

    [Fact] public void Cuatro_Columnas_Chile_Protocolo_Mexico()
    {
        var x = P("2103901000").PorAcuerdo!;
        Assert.Equal(1m, x.CanAce36Ace47Ven); Assert.Equal(0.5m, x.Ace22Chile); Assert.Equal("VII", x.Ace22Protocolo); Assert.Equal(0m, x.Ace66Mexico);
    }
}
