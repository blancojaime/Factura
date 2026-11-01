using System.Diagnostics;
using ComexBol.Data;
using ComexBol.Documentos;
using Xunit;

public class OcrTests
{
    const string Texto = """
        SHENZHEN TECH CO., LTD
        Commercial Invoice
        Invoice No: INV-88213
        Date: 15/10/2026
        Supplier: Shenzhen Tech Co., Ltd
        Incoterm: FOB Shenzhen
        Currency: USD
        Gross Weight: 1,250.50 kg
        Net Weight: 1,100.00 kg
        Packages: 24
        Total Amount: USD 10,000.00
        """;

    [Fact]
    public void Extrae_Campos_Clave_En_Ingles()
    {
        var c = ExtractorFactura.Extraer(Texto);
        Assert.Equal("INV-88213", c.NumeroFactura!.Valor);
        Assert.Equal("Shenzhen Tech Co., Ltd", c.Proveedor!.Valor);
        Assert.Equal("FOB", c.Incoterm!.Valor); Assert.Equal(Confianza.Alta, c.Incoterm.Confianza);
        Assert.Equal("USD", c.Moneda!.Valor);
        Assert.Equal(10_000.00m, c.ValorTotal!.Valor);
        Assert.Equal(1250.50m, c.PesoBrutoKg!.Valor); Assert.Equal(1100m, c.PesoNetoKg!.Valor);
        Assert.Equal(24, c.Bultos!.Valor);
        Assert.Equal(new DateOnly(2026, 10, 15), c.Fecha!.Valor);
    }

    [Fact]
    public void Extrae_En_Espanol_Con_Formato_Boliviano_Y_Libras()
    {
        var c = ExtractorFactura.Extraer("Factura N° 000123\nProveedor: Textiles Andinos SRL\nIncoterm CIF\nPeso bruto: 2.300,75 kg\nPeso neto: 500 lb\n12 bultos\nTotal general: USD 15.250,40");
        Assert.Equal("000123", c.NumeroFactura!.Valor);
        Assert.Equal(15_250.40m, c.ValorTotal!.Valor);
        Assert.Equal(2300.75m, c.PesoBrutoKg!.Valor);
        Assert.Equal(226.796m, c.PesoNetoKg!.Valor); Assert.Equal(Confianza.Baja, c.PesoNetoKg.Confianza);
        Assert.Equal(12, c.Bultos!.Valor);
    }

    [Fact]
    public void No_Inventa_Lo_Que_No_Esta() => Assert.Null(ExtractorFactura.Extraer("texto sin datos").ValorTotal);

    [Theory]
    [InlineData("PACKING LIST 2026", "x.png", TipoDocumento.PackingList)]
    [InlineData("BILL OF LADING", "x.png", TipoDocumento.Embarque)]
    [InlineData("", "factura-123.jpg", TipoDocumento.Factura)]
    [InlineData("hola", "foto.jpg", TipoDocumento.Otro)]
    public void Clasifica(string txt, string nombre, TipoDocumento esperado) => Assert.Equal(esperado, ExtractorFactura.Clasificar(txt, nombre));

    [Fact]
    public async Task Tesseract_Real_Lee_La_Factura_De_Ejemplo()
    {
        try { Process.Start(new ProcessStartInfo("tesseract", "--version") { RedirectStandardOutput = true, RedirectStandardError = true })!.WaitForExit(); }
        catch { return; }   // sin Tesseract instalado el test de integración no aplica
        var texto = await new TesseractCliOcr().LeerTextoAsync(Path.Combine(AppContext.BaseDirectory, "fixtures", "factura-ejemplo.png"));
        var c = ExtractorFactura.Extraer(texto);
        Assert.Equal("INV-88213", c.NumeroFactura?.Valor);
        Assert.Equal("FOB", c.Incoterm?.Valor);
        Assert.Equal(10_000m, c.ValorTotal?.Valor);
    }
}
