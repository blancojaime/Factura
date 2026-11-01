using System.Globalization;
using System.Text.RegularExpressions;
using ComexBol.Data;

namespace ComexBol.Documentos;

public enum Confianza { Baja, Media, Alta }

/// <summary>Valor propuesto por el OCR, con la línea de origen para mostrarla resaltada en el visor.</summary>
public sealed record CampoOcr<T>(T Valor, Confianza Confianza, string LineaOrigen);

public sealed record CamposFactura
{
    public CampoOcr<string>? NumeroFactura { get; init; }
    public CampoOcr<string>? Proveedor { get; init; }
    public CampoOcr<string>? Incoterm { get; init; }
    public CampoOcr<string>? Moneda { get; init; }
    public CampoOcr<decimal>? ValorTotal { get; init; }
    public CampoOcr<decimal>? PesoBrutoKg { get; init; }
    public CampoOcr<decimal>? PesoNetoKg { get; init; }
    public CampoOcr<int>? Bultos { get; init; }
    public CampoOcr<DateOnly>? Fecha { get; init; }
}

/// <summary>
/// Extrae campos clave del texto OCR de facturas y listas de empaque (español/inglés).
/// Es un PROPONEDOR: ningún valor se aplica sin confirmación humana; el OCR se equivoca con dígitos.
/// </summary>
public static class ExtractorFactura
{
    const RegexOptions O = RegexOptions.IgnoreCase | RegexOptions.CultureInvariant;
    static readonly Regex RxNumero = new(@"(?:factura|invoice|inv\.?)\s*(?:comercial\s*)?(?:n[°º.o]*|no\.?|num(?:ero)?\.?|number|#)?\s*[:#\-]?\s*((?=[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{2,})", O);
    static readonly Regex RxProveedor = new(@"^\s*(?:proveedor|vendedor|seller|supplier|exporter|exportador|shipper|from)\s*[:\-]\s*(.+?)\s*$", O | RegexOptions.Multiline);
    static readonly Regex RxIncoterm = new(@"\b(EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b", O);
    static readonly Regex RxMoneda = new(@"\b(USD|US\$|EUR|BOB|CNY|RMB)\b", O);
    static readonly Regex RxTotal = new(@"(?:grand\s*total|total\s*(?:amount|general|factura|invoice)?|importe\s*total|valor\s*total)\s*[:\-]?\s*(?:USD|US\$|EUR|\$)?\s*(\d[\d.,]*)", O);
    static readonly Regex RxBruto = new(@"(?:peso\s*bruto|gross\s*weight|g\.?\s?w\.?)\s*[:\-]?\s*(\d[\d.,]*)\s*(kgs?|lbs?)?", O);
    static readonly Regex RxNeto = new(@"(?:peso\s*neto|net\s*weight|n\.?\s?w\.?)\s*[:\-]?\s*(\d[\d.,]*)\s*(kgs?|lbs?)?", O);
    static readonly Regex RxBultos1 = new(@"(?:bultos|packages|pkgs|cartons|cajas|pallets)\s*[:\-]?\s*(\d+)\b", O);
    static readonly Regex RxBultos2 = new(@"\b(\d+)\s*(?:bultos|packages|pkgs|cartons|cajas|pallets)\b", O);
    static readonly Regex RxFecha = new(@"(?:fecha|date)\s*[:\-]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}|\d{4}-\d{2}-\d{2})", O);

    public static CamposFactura Extraer(string texto)
    {
        var lineas = texto.Split('\n').Select(l => l.TrimEnd('\r')).ToArray();
        string Linea(Match m) => lineas.FirstOrDefault(l => l.Contains(m.Value.Trim(), StringComparison.Ordinal)) ?? m.Value;

        CampoOcr<string>? numero = null;
        if (RxNumero.Match(texto) is { Success: true } mn) numero = new(mn.Groups[1].Value.ToUpperInvariant(), Confianza.Media, Linea(mn));

        CampoOcr<string>? prov = null;
        if (RxProveedor.Match(texto) is { Success: true } mp) prov = new(mp.Groups[1].Value, Confianza.Alta, Linea(mp));
        else if (lineas.FirstOrDefault(l => l.Trim().Length >= 4 && !RxNumero.IsMatch(l)) is { } primera)
            prov = new(primera.Trim(), Confianza.Baja, primera);      // membrete: suele ser el emisor

        CampoOcr<string>? inco = null;
        if (RxIncoterm.Match(texto) is { Success: true } mi)
            inco = new(mi.Value.ToUpperInvariant(), Linea(mi).Contains("incoterm", StringComparison.OrdinalIgnoreCase) ? Confianza.Alta : Confianza.Media, Linea(mi));

        CampoOcr<string>? mon = null;
        if (RxMoneda.Match(texto) is { Success: true } mm) mon = new(mm.Value.ToUpperInvariant() is "US$" ? "USD" : mm.Value.ToUpperInvariant(), Confianza.Media, Linea(mm));

        CampoOcr<decimal>? total = null;
        if (RxTotal.Matches(texto).LastOrDefault() is { } mt && Numero.Parsear(mt.Groups[1].Value) is { } vt)
            total = new(vt, Confianza.Media, Linea(mt));

        CampoOcr<decimal>? Peso(Regex rx)
        {
            if (rx.Match(texto) is not { Success: true } m || Numero.Parsear(m.Groups[1].Value) is not { } v) return null;
            var lb = m.Groups[2].Value.StartsWith("lb", StringComparison.OrdinalIgnoreCase);
            return new(Math.Round(lb ? v * 0.45359237m : v, 3), lb ? Confianza.Baja : Confianza.Media, Linea(m));
        }

        CampoOcr<int>? bultos = null;
        var mb = RxBultos1.Match(texto); if (!mb.Success) mb = RxBultos2.Match(texto);
        if (mb.Success) bultos = new(int.Parse(mb.Groups[1].Value), Confianza.Media, Linea(mb));

        CampoOcr<DateOnly>? fecha = null;
        if (RxFecha.Match(texto) is { Success: true } mf && Numero.ParsearFecha(mf.Groups[1].Value) is { } df) fecha = new(df, Confianza.Media, Linea(mf));

        return new() { NumeroFactura = numero, Proveedor = prov, Incoterm = inco, Moneda = mon, ValorTotal = total,
            PesoBrutoKg = Peso(RxBruto), PesoNetoKg = Peso(RxNeto), Bultos = bultos, Fecha = fecha };
    }

    /// <summary>Clasifica el documento del legajo por palabras clave del texto y del nombre de archivo.</summary>
    public static TipoDocumento Clasificar(string texto, string nombreArchivo)
    {
        var t = (texto + " " + nombreArchivo).ToLowerInvariant();
        bool Tiene(params string[] k) => k.Any(t.Contains);
        if (Tiene("packing list", "lista de empaque", "lista de embalaje")) return TipoDocumento.PackingList;
        if (Tiene("bill of lading", "b/l", "conocimiento de embarque", "carta de porte", "air waybill", "guía aérea", "awb", "crt")) return TipoDocumento.Embarque;
        if (Tiene("certificado de origen", "certificate of origin")) return TipoDocumento.CertificadoOrigen;
        if (Tiene("póliza", "poliza", "insurance", "seguro")) return TipoDocumento.Seguro;
        if (Tiene("asp-b", "aspb", "gastos portuarios", "port charges")) return TipoDocumento.GastosPortuarios;
        if (Tiene("senasag", "agemed", "ibnorca", "autorización previa", "autorizacion previa", "vuce")) return TipoDocumento.AutorizacionPrevia;
        if (Tiene("swift", "transferencia", "comprobante de pago", "wire transfer")) return TipoDocumento.Bancario;
        if (Tiene("factura", "invoice")) return TipoDocumento.Factura;
        return TipoDocumento.Otro;
    }
}

static class Numero
{
    /// <summary>Acepta 10,000.50 y 10.000,50. Un único separador seguido de 3 dígitos se toma como miles.</summary>
    public static decimal? Parsear(string s)
    {
        s = s.Trim().TrimEnd('.', ',');
        int c = s.LastIndexOf(','), p = s.LastIndexOf('.');
        string norm;
        if (c >= 0 && p >= 0) norm = c > p ? s.Replace(".", "").Replace(',', '.') : s.Replace(",", "");
        else if (c >= 0 || p >= 0)
        {
            var sep = c >= 0 ? ',' : '.'; var i = s.LastIndexOf(sep);
            bool miles = s.Count(ch => ch == sep) > 1 || s.Length - i - 1 == 3;
            norm = miles ? s.Replace(sep.ToString(), "") : s.Replace(sep, '.');
        }
        else norm = s;
        return decimal.TryParse(norm, NumberStyles.Number, CultureInfo.InvariantCulture, out var v) ? v : null;
    }

    public static DateOnly? ParsearFecha(string s)
    {
        string[] fmts = ["d/M/yyyy", "d-M-yyyy", "d.M.yyyy", "yyyy-MM-dd"];
        return DateOnly.TryParseExact(s, fmts, CultureInfo.InvariantCulture, DateTimeStyles.None, out var d) ? d : null;
    }
}
