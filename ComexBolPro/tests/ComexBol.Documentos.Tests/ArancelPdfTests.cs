using ComexBol.Core.Catalogo;
using ComexBol.Documentos;
using Xunit;

/// <summary>Pruebas con páginas REALES del Arancel 2026 (fixtures/arancel-muestra.pdf): tablas desplazadas, filas sin línea divisoria y Apéndice ICE.</summary>
public class ArancelPdfTests
{
    static readonly Lazy<ResultadoImportacion> Muestra = new(() =>
        ArancelPdf.Parsear([Path.Combine(AppContext.BaseDirectory, "fixtures", "arancel-muestra.pdf")]));
    static PartidaNandina P(string c) => Muestra.Value.Partidas.Single(p => p.Codigo == c);

    [Fact] public void Lee_Fila_Normal_Con_Certificado_Y_Preferencias_Por_Columna()
    {
        var p = P("0101210000");
        Assert.Equal(0.05m, p.AlicuotaGA); Assert.Equal("u", p.Unidad); Assert.Equal("C*", p.TipoDocumento);
        Assert.Equal("MDPRyA (SENASAG)", p.Entidad); Assert.Contains("SENASAG", p.Autorizaciones); Assert.Equal("Ley 830 - Dec. 515", p.DispLegal);
        Assert.Equal(1m, p.PorAcuerdo!.CanAce36Ace47Ven); Assert.Null(p.PorAcuerdo.Ace22Chile); Assert.Equal(1m, p.PorAcuerdo.Ace66Mexico);
    }

    [Fact] public void Pagina_Con_Dos_Tablas_Desplazadas_Se_Lee_Por_Fila()
    {   // pág. 29 del archivo 1: la tabla superior y la inferior tienen columnas desplazadas ~21 pt
        var p = P("0106190090");
        Assert.Equal(0.20m, p.AlicuotaGA); Assert.Equal("C* - CITES", p.TipoDocumento);
        Assert.Contains("D.S. 3048", p.DispLegal); Assert.Equal(1m, p.PorAcuerdo!.CanAce36Ace47Ven);   // «D.S.» ya no se confunde con una preferencia
    }

    [Fact] public void Filas_Contiguas_Sin_Linea_Divisoria_Se_Separan_Y_Son_Prohibidas()
    {   // pág. 66 del archivo 3: 8703.32.10.00 y 8703.32.90.00 comparten banda (antes se leía GA «10 10»)
        foreach (var c in new[] { "8703321000", "8703329000" }) { Assert.Equal(0.10m, P(c).AlicuotaGA); Assert.True(P(c).Prohibida); Assert.Equal("P", P(c).TipoDocumento); }
    }

    [Fact] public void Apendice_Ice_Con_Seis_Cuatro_Y_Dos_Columnas_Y_Mayor_O_Igual()
    {
        Assert.Equal(new[] { 0.15m, 0.20m, 0.25m, 0.30m, 0.40m, 0.50m }, P("8701210000").IceAntiguedad.ToArray());
        Assert.Equal(new[] { 0m, 0m, 0m, 0m }, P("8704322090").IceAntiguedad.ToArray());
        Assert.Equal(new[] { 0m, 0m }, P("8703221020").IceAntiguedad.ToArray());
        var omas = P("8705100019"); Assert.True(omas.IceUltimaEsOMas); Assert.Equal(4, omas.IceAntiguedad.Count);
        Assert.All(new[] { "8701210000", "8703221020" }, c => Assert.Equal("ICE", P(c).ImpuestoEspecial));
        Assert.Equal("", P("8701210000").TipoDocumento);       // la llamada de nota «( * )» no es un documento exigido
    }

    [Fact] public void La_Muestra_No_Descarta_Filas_Sin_Avisarlo() =>
        Assert.DoesNotContain(Muestra.Value.Errores, e => e.Mensaje.Contains("fila omitida") || e.Mensaje.Contains("página omitida"));

    [Fact] public void Arancel_Completo_Si_Se_Indica_La_Carpeta_Con_Los_3_Pdf()
    {
        var dir = Environment.GetEnvironmentVariable("COMEXBOL_ARANCEL_PDF_DIR");
        if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return;
        var r = ArancelPdf.Parsear(Directory.GetFiles(dir, "*.pdf").OrderBy(f => f).ToList());
        Assert.Equal(8132, r.Partidas.Count);
        Assert.Equal(97, r.Partidas.Select(p => p.Capitulo).Distinct().Count());
        Assert.Equal(76, r.Partidas.Count(p => p.Prohibida));
        Assert.Equal(180, r.Partidas.Count(p => p.IceAntiguedad.Count > 0));
        Assert.True(r.Errores.Count <= 5, string.Join("\n", r.Errores.Take(5).Select(e => e.Mensaje)));
    }
}
