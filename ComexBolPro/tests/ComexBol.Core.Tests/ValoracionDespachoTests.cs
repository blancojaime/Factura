using ComexBol.Core;
using Xunit;

public class ValoracionDespachoTests
{
    static TipoCambioTable Tc() => new(new DateOnly(2026, 11, 1), new Dictionary<string, decimal> { ["USD"] = 6.96m });
    static ItemImportacion Item(int n, decimal valor, decimal ga) => new(n, "8471300010", "Equipo", valor, 100, 90, ga);

    [Fact] public void Cuestionario_Sin_Responder_No_Es_Aplicable() => Assert.False(Valoracion.Descartar(new()).PrimerMetodoAplicable);

    [Fact] public void Vinculacion_Que_Influyo_Descarta_El_Primer_Metodo()
    {
        var r = Valoracion.Descartar(new(Vinculacion: true, VinculacionInfluyoPrecio: true, Respondido: true));
        Assert.False(r.PrimerMetodoAplicable); Assert.Contains(r.Observaciones, o => o.Contains("métodos secuenciales"));
    }

    [Fact] public void Vinculacion_Sin_Influencia_Es_Aplicable_Con_Observacion()
    {
        var r = Valoracion.Descartar(new(Vinculacion: true, Respondido: true));
        Assert.True(r.PrimerMetodoAplicable); Assert.Contains(r.Observaciones, o => o.Contains("valores de prueba"));
    }

    [Fact] public void Restricciones_Y_Condiciones_Descartan()
    {
        Assert.False(Valoracion.Descartar(new(RestriccionesCesion: true, Respondido: true)).PrimerMetodoAplicable);
        Assert.False(Valoracion.Descartar(new(CondicionesNoCuantificables: true, Respondido: true)).PrimerMetodoAplicable);
        Assert.True(Valoracion.Descartar(new(Respondido: true)).PrimerMetodoAplicable);
    }

    [Fact] public void Reversion_Sin_Importe_Pide_Declararlo()
        => Assert.Contains(Valoracion.Descartar(new(ReversionAlVendedor: true, Respondido: true)).Observaciones, o => o.Contains("Reversiones"));

    [Fact] public void Ajustes_Art8_Suman_Y_Restan_Sin_Importar_El_Incoterm()
    {
        var a = new AjustesArt8(Comisiones: 100, Royalties: 200, Assists: 300, ArmadoPosterior: 50);
        Assert.Equal(600m, a.TotalAdiciones); Assert.Equal(50m, a.TotalDeducciones);
        var op = new OperacionImportacion(Incoterm.CIF, "USD", [Item(1, 10_000m, 0.10m)], AdicionesArt8: new(a.TotalAdiciones), DeduccionesArt8: new(a.TotalDeducciones));
        var r = CalculadoraTributaria.Calcular(op, Tc());
        Assert.Equal((10_000m + 600m - 50m) * 6.96m, r.CifBob);       // 73.416,00
        Assert.Contains(r.Desglose!, l => l.Concepto.Contains("Art. 8") && l.Bob > 0);
        Assert.Contains(r.Desglose!, l => l.Concepto.Contains("Deducciones del Art. 8") && l.Bob < 0);
        Assert.Equal(r.CifBob, r.Desglose!.Last().Bob);
    }

    [Fact] public void Desglose_Lista_Flete_Y_Seguro_Con_Fob()
    {
        var op = new OperacionImportacion(Incoterm.FOB, "USD", [Item(1, 10_000m, 0.10m)], Flete: new(1_500m), Seguro: new(100m));
        var r = CalculadoraTributaria.Calcular(op, Tc());
        Assert.Contains(r.Desglose!, l => l.Concepto == "(+) Flete" && l.Bob == 1500m * 6.96m);
        Assert.Contains(r.Desglose!, l => l.Concepto == "(+) Seguro");
    }

    [Fact] public void Validador_De_Precios_Clasifica_El_Riesgo()
    {
        var hist = new decimal[] { 100, 104, 96 };
        Assert.Equal(NivelRiesgoPrecio.Bajo, ValidadorPrecios.Evaluar(105, hist).Nivel);
        Assert.Equal(NivelRiesgoPrecio.Medio, ValidadorPrecios.Evaluar(125, hist).Nivel);
        var alto = ValidadorPrecios.Evaluar(50, hist); Assert.Equal(NivelRiesgoPrecio.Alto, alto.Nivel); Assert.Contains("inferior", alto.Mensaje);
        Assert.Equal(NivelRiesgoPrecio.SinReferencia, ValidadorPrecios.Evaluar(50, []).Nivel);
    }

    [Fact] public void Costeo_Prorratea_Gastos_Trata_El_Iva_Como_Credito_Y_Calcula_Factor()
    {
        var op = new OperacionImportacion(Incoterm.FOB, "USD", [Item(1, 10_000m, 0.10m), Item(2, 30_000m, 0.05m)], Flete: new(4_000m), Seguro: new(400m));
        var r = CalculadoraTributaria.Calcular(op, Tc());
        var c = Costeo.Calcular(r, [100, 300], new(HonorariosAgencia: 4_000m, Almacenaje: 1_000m));
        Assert.Equal(5_000m, c.GastosLocalesBob);
        Assert.Equal(5_000m, c.Items.Sum(i => i.GastosProrrateados), 1);
        var it = c.Items[0];
        Assert.Equal(it.CifBob + r.Items[0].GA + it.GastosProrrateados, it.CostoNacionalizadoBob);   // sin IVA
        Assert.Equal(r.Items.Sum(i => i.IVA), c.IvaCreditoFiscalTotal);
        Assert.Equal(Math.Round(it.CostoNacionalizadoBob / 100m, 2), it.CostoUnitarioBob);
        Assert.Equal(r.TotalTributos + 5_000m, c.CashFlowRequeridoBob);
        var sinCredito = Costeo.Calcular(r, [100, 300], new(), ivaRecuperable: false);
        Assert.True(sinCredito.CostoTotalBob > c.CostoTotalBob - 5_000m);
    }

    [Fact] public void Almacenaje_Usa_Dias_Cobrables_Y_Toneladas()
    {
        Assert.Equal(1_000m * 2m * 5m * 0, Costeo.EstimarAlmacenaje(2_000m, 10, 10, 5m));
        Assert.Equal(3m * 2m * 5m, Costeo.EstimarAlmacenaje(2_000m, 8, 5, 5m));
    }

    [Fact] public void Explicador_Muestra_Formula_De_Cada_Tributo()
    {
        var p = new ParametrosTributarios();
        var op = new OperacionImportacion(Incoterm.FOB, "USD", [Item(1, 10_000m, 0.10m)], Flete: new(1_500m), Seguro: new(100m));
        var r = CalculadoraTributaria.Calcular(op, Tc(), p);
        var pasos = ExplicadorLiquidacion.Pasos(op, r, p, new System.Globalization.CultureInfo("es-BO"));
        Assert.Contains(pasos, x => x.Contains("GA") && x.Contains("10%")); Assert.Contains(pasos, x => x.Contains("IVA") && x.Contains("14,94%"));
        Assert.Contains(pasos, x => x.StartsWith("Total tributos"));
    }

    static DatosDespacho Dim(string embarque = "BL-1", int bultos = 10, decimal peso = 1000) =>
        new("General", "10 - Importación a consumo", "Arica", "La Paz", "ADA-123", "Marítimo / fluvial", embarque, bultos, peso, "MANI-1", "DAV-1", "");

    [Fact] public void Dim_Completa_Y_Coherente_No_Tiene_Observaciones()
    {
        var h = Despacho.Validar(Dim(), 1_020m, 1, true, true, false, 0);
        Assert.DoesNotContain(h, x => x.Nivel == NivelHallazgo.Error); Assert.Contains(h, x => x.Texto.Contains("concuerda"));
    }

    [Fact] public void Dim_Detecta_Peso_Distinto_Y_Campos_Faltantes()
    {
        var h = Despacho.Validar(Dim(peso: 1_000m), 1_500m, 1, true, true, false, 0);
        Assert.Contains(h, x => x.Nivel == NivelHallazgo.Error && x.Texto.Contains("difiere"));
        var vacia = Despacho.Validar(new("", "", "", "", "", "", "", 0, 0, "", "", ""), 0, 0, false, false, true, 3);
        Assert.True(vacia.Count(x => x.Nivel == NivelHallazgo.Error) >= 8);
        Assert.Contains(vacia, x => x.Texto.Contains("respaldo bancario")); Assert.Contains(vacia, x => x.Texto.Contains("3 documento"));
    }

    [Fact] public void Documento_De_Embarque_Segun_Modalidad()
    {
        Assert.Equal("B/L (Bill of Lading)", Despacho.DocumentoEmbarque("Marítimo / fluvial"));
        Assert.Equal("CRT / Carta de Porte Internacional", Despacho.DocumentoEmbarque("Carretero"));
        Assert.Equal("Guía aérea (AWB)", Despacho.DocumentoEmbarque("Aéreo")); Assert.Equal("TIF/DTA", Despacho.DocumentoEmbarque("Ferroviario"));
    }

    [Fact] public void Canales_Tienen_Tareas_Y_Rojo_Incluye_Descargos()
    {
        Assert.Empty(Despacho.TareasCanal("Sin asignar")); Assert.True(Despacho.TareasCanal("Verde").Count >= 3);
        Assert.Contains(Despacho.TareasCanal("Rojo"), t => t.Contains("descargos")); Assert.Contains(Despacho.TareasCanal("Amarillo"), t => t.Contains("Cotejar factura"));
    }

    [Fact] public void Plantilla_De_Descargo_Incluye_Datos_Y_Pruebas()
    {
        var t = Despacho.PlantillaDescargo("IMP-1", "ACME SRL", "123", "ADA Uno", "DIM-9", 40_000m, "Valor inferior al referencial", Despacho.PruebasDescargo.Take(2));
        Assert.Contains("ACME SRL", t); Assert.Contains("DIM-9", t); Assert.Contains("40", t); Assert.Contains("1. Factura comercial original", t); Assert.Contains("borrador", t);
    }
}
