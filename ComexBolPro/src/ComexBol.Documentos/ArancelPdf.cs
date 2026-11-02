using System.Globalization;
using System.Text.RegularExpressions;
using ComexBol.Core.Catalogo;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Content;

namespace ComexBol.Documentos;

/// <summary>
/// Importa el Arancel Aduanero de Importaciones (PDF oficial MEFP/ANB) leyendo cada celda por coordenadas.
/// Cada página de tabla trae 14 líneas verticales que delimitan sus 13 columnas:
/// código | descripción | GA | ICE-IEHD | unidad | despacho en frontera | tipo doc | entidad | disp. legal |
/// pref. CAN/ACE36/ACE47/VEN | ACE22 Chile | ACE22 Protocolo | ACE66 México.
/// Las páginas del Apéndice I (ICE de vehículos por antigüedad) se leen con sus 6 columnas de tasas.
/// Lo que no puede interpretarse con certeza se informa con página y código; nunca se corrige en silencio.
/// </summary>
public static partial class ArancelPdf
{
    [GeneratedRegex(@"^\d{4}\.\d{2}\.\d{2}\.\d{2}$")] private static partial Regex RxCodigo();
    static readonly Regex RxNum = new(@"^\d+(?:[.,]\d+)?$");
    static readonly Regex RxRomano = new(@"^(I|II|III|IV|V|VI|VII|VIII|IX|X)$");

    sealed record Banda(double Techo, double Piso);

    /// <summary>Año del arancel según el encabezado del PDF («Arancel Aduanero de Importaciones 2026»), o null si no se encuentra.</summary>
    public static string? DetectarVersion(string pdf)
    {
        try
        {
            using var doc = PdfDocument.Open(pdf);
            foreach (var page in doc.GetPages().Take(3))
            {
                var m = Regex.Match(string.Join(" ", page.GetWords().Select(w => w.Text)), @"Importaciones\s+(20\d{2})");
                if (m.Success) return m.Groups[1].Value;
            }
        }
        catch (Exception) { }
        return null;
    }

    public static ResultadoImportacion Parsear(IEnumerable<string> pdfs, string fuente = "ANB-2026", IProgress<string>? progreso = null)
    {
        var partidas = new List<PartidaNandina>(); var errores = new List<ErrorImportacion>();
        var vistos = new HashSet<string>(); var ice = new Dictionary<string, IReadOnlyList<decimal>>(); var iceOMas = new Dictionary<string, bool>();
        int archivo = 0; var jerarquia = new Jerarquia();
        foreach (var ruta in pdfs)
        {
            archivo++;
            using var doc = PdfDocument.Open(ruta);
            foreach (var page in doc.GetPages())
            {
                if (page.Number % 25 == 0) progreso?.Report($"Leyendo arancel: archivo {archivo}, página {page.Number}…");
                try { Pagina(page, archivo, fuente, partidas, errores, vistos, ice, iceOMas, jerarquia); }
                catch (Exception ex) { errores.Add(new(page.Number, $"archivo {archivo}, pág. {page.Number}: no se pudo leer ({ex.Message})")); }
            }
        }
        for (int i = 0; i < partidas.Count; i++)
            if (ice.TryGetValue(partidas[i].Codigo, out var t)) partidas[i] = partidas[i] with { IceAntiguedad = t, IceUltimaEsOMas = iceOMas.GetValueOrDefault(partidas[i].Codigo), ImpuestoEspecial = "ICE" };
        foreach (var c in ice.Keys.Where(k => !vistos.Contains(k))) errores.Add(new(0, $"Apéndice ICE: código {c} no existe en el arancel principal"));
        return new(partidas, errores);
    }

    static void Pagina(Page page, int archivo, string fuente, List<PartidaNandina> partidas, List<ErrorImportacion> errores, HashSet<string> vistos, Dictionary<string, IReadOnlyList<decimal>> ice, Dictionary<string, bool> iceOMas, Jerarquia jerarquia)
    {
        var words = page.GetWords().ToList();
        if (!words.Any(w => RxCodigo().IsMatch(w.Text) && w.BoundingBox.Left < 200)) return;      // página sin filas de tabla

        // Líneas finas: verticales (columnas) y horizontales (filas)
        var segmentos = new List<(double X, double Inf, double Sup)>(); var horizontales = new List<double>();
        foreach (var path in page.ExperimentalAccess.Paths)
        {
            var r = path.GetBoundingRectangle(); if (r is null) continue;
            if (r.Value.Width < 1.2 && r.Value.Height > 8) segmentos.Add((Math.Round((r.Value.Left + r.Value.Right) / 2, 1), r.Value.Bottom, r.Value.Top));
            else if (r.Value.Height < 1.2 && r.Value.Width > 15) horizontales.Add(Math.Round((r.Value.Top + r.Value.Bottom) / 2, 1));
        }
        var filas = Agrupar(horizontales, 1.0).OrderByDescending(y => y).ToList();
        var encabezadosIce = words.Where(w => w.Text == "NUEVOS").ToList();
        bool esIce = encabezadosIce.Count > 0 && words.Any(w => w.Text.StartsWith("ANTIG", StringComparison.OrdinalIgnoreCase));
        double colCodigoFin = esIce ? 200 : 91;      // las tablas pequeñas del Apéndice ICE están centradas: su columna de código empieza más a la derecha

        // Jerarquía del arancel (partida → subpartidas → nivel de guiones) para dar a cada ítem una descripción completa.
        var rutas = new Dictionary<string, string>();
        if (!esIce)
        {
            var limites = new List<double> { page.Height }; limites.AddRange(filas); limites.Add(0);
            for (int b = 0; b + 1 < limites.Count; b++)
            {
                double top = limites[b], bot = limites[b + 1]; if (top - bot < 4) continue;
                var enBanda = words.Where(x => { var cy = (x.BoundingBox.Top + x.BoundingBox.Bottom) / 2; return cy < top && cy > bot; }).ToList();
                var codigos = enBanda.Where(x => x.BoundingBox.Right < 100 && Regex.IsMatch(x.Text, @"^\d")).OrderByDescending(x => x.BoundingBox.Top).ToList();
                var cortes = new List<(double T, double B, string Cod)>();
                if (codigos.Count <= 1) cortes.Add((top, bot, codigos.Count == 1 ? codigos[0].Text : ""));
                else
                    for (int k = 0; k < codigos.Count; k++)
                    {
                        double yk = (codigos[k].BoundingBox.Top + codigos[k].BoundingBox.Bottom) / 2;
                        double t = k == 0 ? top : (yk + (codigos[k - 1].BoundingBox.Top + codigos[k - 1].BoundingBox.Bottom) / 2) / 2;
                        double bb = k == codigos.Count - 1 ? bot : (yk + (codigos[k + 1].BoundingBox.Top + codigos[k + 1].BoundingBox.Bottom) / 2) / 2;
                        cortes.Add((t, bb, codigos[k].Text));
                    }
                foreach (var (t, bb, cod) in cortes)
                {
                    var desc = Texto(words, 91, 366, t, bb);
                    if (desc.Length == 0 || desc.Contains("DE LA MERCANCÍA") || desc.Contains("DESCRIPCIÓN")) continue;
                    var ruta = jerarquia.Registrar(cod, desc);
                    if (RxCodigo().IsMatch(cod)) rutas[cod.Replace(".", "")] = ruta;
                }
            }
        }

        // Cada fila de código define una banda entre las líneas horizontales que la rodean.
        foreach (var w in words.Where(w => RxCodigo().IsMatch(w.Text) && w.BoundingBox.Left < colCodigoFin + 2))
        {
            var yc = (w.BoundingBox.Top + w.BoundingBox.Bottom) / 2;
            var techo = filas.Where(y => y >= yc).DefaultIfEmpty(page.Height).Min();
            var piso = filas.Where(y => y < yc).DefaultIfEmpty(0).Max();
            // Filas consecutivas sin línea horizontal entre ellas: se parte la banda por la mitad entre sus códigos.
            foreach (var otro in words.Where(o => !ReferenceEquals(o, w) && RxCodigo().IsMatch(o.Text) && o.BoundingBox.Left < colCodigoFin + 2))
            {
                var yo = (otro.BoundingBox.Top + otro.BoundingBox.Bottom) / 2;
                if (yo < techo && yo > piso)
                {
                    if (yo > yc) techo = Math.Min(techo, (yo + yc) / 2); else piso = Math.Max(piso, (yo + yc) / 2);
                }
            }
            // Una página puede traer dos tablas con columnas desplazadas: se usan las líneas que cubren esta fila.
            List<double>? cols = null;
            if (!esIce)
            {
                List<double> propias = [];
                foreach (var tol in new[] { 1.0, 8.0, 20.0 })        // si la fila no tiene todas sus líneas, se amplía la búsqueda vertical
                {
                    propias = Agrupar(segmentos.Where(sg => sg.Inf <= yc + tol && sg.Sup >= yc - tol).Select(sg => sg.X), 1.5);
                    cols = propias.Count == 14 ? propias : AjustarPlantilla(propias);
                    if (cols is not null) break;
                }
                if (cols is null)
                {
                    if (propias.Count >= 10) errores.Add(new(page.Number, $"archivo {archivo}, pág. {page.Number}: {w.Text.Replace(".", "")} — no se reconocieron las 14 líneas de columnas ({propias.Count} halladas); fila omitida"));
                    continue;                 // con pocas líneas no es una tabla del arancel (índices y apéndices con códigos)
                }
            }
            string Celda(int c) => Texto(words, cols![c], cols[c + 1], techo, piso);
            var codigo = w.Text.Replace(".", ""); var donde = $"archivo {archivo}, pág. {page.Number}: {codigo}";

            if (esIce)
            {
                // Encabezado de la tabla a la que pertenece la fila: el "NUEVOS" más cercano por encima.
                var enc = encabezadosIce.Where(h => h.BoundingBox.Bottom >= yc).OrderBy(h => h.BoundingBox.Bottom - yc).FirstOrDefault();
                if (enc is null) { errores.Add(new(page.Number, $"{donde} — Apéndice ICE sin encabezado de tabla")); continue; }
                var etiquetas = EtiquetasAnios(words, enc);                       // (año, x centro, esOMás)
                var celdas = words.Where(x => RxNum.IsMatch(x.Text) && x.BoundingBox.Left > enc.BoundingBox.Left - 12 &&
                        (x.BoundingBox.Top + x.BoundingBox.Bottom) / 2 < techo && (x.BoundingBox.Top + x.BoundingBox.Bottom) / 2 > piso)
                    .Select(x => (Texto: x.Text, Cx: (x.BoundingBox.Left + x.BoundingBox.Right) / 2)).OrderBy(x => x.Cx).ToList();
                var tasasAnio = new SortedDictionary<int, decimal>(); bool omas = false;
                foreach (var (texto, cx) in celdas)
                {
                    var et = etiquetas.OrderBy(e => Math.Abs(e.Cx - cx)).First();
                    tasasAnio[et.Anio] = decimal.Parse(texto.Replace(',', '.'), CultureInfo.InvariantCulture) / 100m;
                    if (et.OMas) omas = true;
                }
                if (tasasAnio.Count > 0 && tasasAnio.Keys.SequenceEqual(Enumerable.Range(0, tasasAnio.Count))) { ice[codigo] = tasasAnio.Values.ToList(); iceOMas[codigo] = omas; }
                else if (tasasAnio.Count > 0) errores.Add(new(page.Number, $"{donde} — Apéndice ICE con columnas no consecutivas; ingrese el ICE manualmente"));
                continue;                  // sin números: fila prohibida (NA) o encabezado
            }

            if (!vistos.Add(codigo)) { errores.Add(new(page.Number, $"{donde} — código repetido (se conserva el primero)")); continue; }
            var gaTxt = Celda(2);
            if (!RxNum.IsMatch(gaTxt) || !decimal.TryParse(gaTxt.Replace(',', '.'), NumberStyles.Number, CultureInfo.InvariantCulture, out var ga) || ga is < 0 or > 40)
            { errores.Add(new(page.Number, $"{donde} — GA ilegible ('{gaTxt}')")); vistos.Remove(codigo); continue; }

            var desc = rutas.TryGetValue(codigo, out var rutaDesc) && rutaDesc.Length > 0 ? rutaDesc : Celda(1); var especial = Celda(3).ToUpperInvariant();
            especial = especial.Contains("IEHD") ? "IEHD" : especial.Contains("ICE") ? "ICE" : "";
            var unidad = Celda(4); var front = Celda(5);
            var tipo = Limpiar(Celda(6)); var entidad = Celda(7); var legal = Celda(8);
            if (tipo.Replace(" ", "") is "(*)" or "*") tipo = "";                       // llamada de nota, no un documento
            var autorizaciones = Regex.Matches(entidad, @"\(([^)]+)\)").Select(m => m.Groups[1].Value.Trim()).Distinct().ToList();
            if (autorizaciones.Count == 0 && entidad.Length > 0) autorizaciones.Add(entidad);
            if (unidad.Length == 0) errores.Add(new(page.Number, $"{donde} — advertencia: unidad de medida vacía"));

            decimal? Pct(string t) => RxNum.IsMatch(t) && decimal.TryParse(t.Replace(',', '.'), NumberStyles.Number, CultureInfo.InvariantCulture, out var v) ? v / 100m : null;
            var a = Celda(9); var chi = Celda(10); var prot = Celda(11); var mex = Celda(12);
            foreach (var (nombre, t) in new[] { ("CAN", a), ("Chile", chi), ("México", mex) })
                if (t.Length > 0 && !RxNum.IsMatch(t)) errores.Add(new(page.Number, $"{donde} — advertencia: preferencia {nombre} no numérica ('{t}')"));
            var prefs = new[] { a, chi, prot, mex }.Where(t => RxNum.IsMatch(t)).Select(t => decimal.Parse(t.Replace(',', '.'), CultureInfo.InvariantCulture)).ToList();
            partidas.Add(new PartidaNandina(codigo, desc, ga / 100m, unidad, tipo == "P", autorizaciones, fuente)
            {
                TipoDocumento = tipo, Entidad = entidad, DispLegal = legal, DespachoEnFrontera = front, ImpuestoEspecial = especial, Preferencias = prefs,
                PorAcuerdo = new(Pct(a), Pct(chi), RxRomano.IsMatch(prot) ? prot : (prot.Length > 0 ? prot : null), Pct(mex))
            });
        }
    }

    static readonly double[] Plantilla = [28, 91, 366, 388, 417, 451, 497, 531, 628, 730, 762, 790, 818, 879];
    static readonly double[] Tolerancia = [3, 3, 3, 3, 3, 3, 26, 26, 26, 26, 26, 26, 26, 3];

    /// <summary>Elige de las líneas verticales halladas las 14 de la tabla, comparándolas con la plantilla (tolerando desplazamientos por página y líneas extra).</summary>
    static List<double>? AjustarPlantilla(List<double> candidatas)
    {
        var res = new List<double>(); double previo = double.MinValue;
        for (int i = 0; i < Plantilla.Length; i++)
        {
            var mejor = candidatas.Where(c => c > previo + 5 && Math.Abs(c - Plantilla[i]) <= Tolerancia[i]).OrderBy(c => Math.Abs(c - Plantilla[i])).Cast<double?>().FirstOrDefault();
            if (mejor is null) return null;
            res.Add(mejor.Value); previo = mejor.Value;
        }
        return res;
    }

    record EtiquetaAnio(int Anio, double Cx, bool OMas);

    /// <summary>Etiquetas de antigüedad del encabezado (NUEVOS = 0; "1", "2"… o "&gt;=3") con su posición horizontal.</summary>
    static List<EtiquetaAnio> EtiquetasAnios(List<Word> words, Word nuevos)
    {
        var lista = new List<EtiquetaAnio> { new(0, (nuevos.BoundingBox.Left + nuevos.BoundingBox.Right) / 2, false) };
        var yEnc = nuevos.BoundingBox.Bottom;
        foreach (var w in words.Where(x => x.BoundingBox.Left > nuevos.BoundingBox.Right && Math.Abs(x.BoundingBox.Bottom - yEnc) < 40 && x.BoundingBox.Bottom < yEnc + 8))
        {
            var t = w.Text.Replace("≥", ">=");
            if (Regex.IsMatch(t, @"^[1-5]$")) lista.Add(new(int.Parse(t), (w.BoundingBox.Left + w.BoundingBox.Right) / 2, false));
            else if (Regex.IsMatch(t, @"^>=[1-5]$")) lista.Add(new(int.Parse(t[2..]), (w.BoundingBox.Left + w.BoundingBox.Right) / 2, true));
        }
        return lista;
    }

    static string Limpiar(string s) => Regex.Replace(s, @"\s+", " ").Trim();

    /// <summary>Texto de una celda: palabras cuyo centro cae dentro de [x0,x1) y de la banda vertical, en orden de lectura.</summary>
    static string Texto(List<Word> words, double x0, double x1, double techo, double piso)
    {
        var sel = words.Where(w =>
        {
            var cx = (w.BoundingBox.Left + w.BoundingBox.Right) / 2; var cy = (w.BoundingBox.Top + w.BoundingBox.Bottom) / 2;
            return cx >= x0 && cx < x1 && cy < techo && cy > piso;
        }).OrderByDescending(w => (w.BoundingBox.Top + w.BoundingBox.Bottom) / 2).ToList();
        // Agrupar en renglones (tolerancia 3 pt) y leer cada renglón de izquierda a derecha.
        var renglones = new List<List<Word>>();
        foreach (var w in sel)
        {
            var cy = (w.BoundingBox.Top + w.BoundingBox.Bottom) / 2;
            var r = renglones.FirstOrDefault(l => Math.Abs((l[0].BoundingBox.Top + l[0].BoundingBox.Bottom) / 2 - cy) < 3);
            if (r is null) renglones.Add([w]); else r.Add(w);
        }
        return Limpiar(string.Join(" ", renglones.SelectMany(l => l.OrderBy(w => w.BoundingBox.Left)).Select(w => w.Text)));
    }

    static List<double> Agrupar(IEnumerable<double> valores, double tol)
    {
        var res = new List<double>();
        foreach (var v in valores.OrderBy(v => v))
            if (res.Count == 0 || v - res[^1] > tol) res.Add(v);
        return res;
    }

    /// <summary>Pila de encabezados: partida (87.01) → subpartidas con 1, 2, 3… guiones. Cada ítem toma su ruta completa.</summary>
    sealed class Jerarquia
    {
        readonly List<string> _pila = [];
        static readonly Regex RxGuiones = new(@"^((?:-\s*)+)(.*)$", RegexOptions.Singleline);

        public string Registrar(string codigo, string desc)
        {
            desc = Regex.Replace(desc, @"\s+", " ").Trim();
            int nivel = 0; var texto = desc;
            if (Regex.IsMatch(codigo, @"^\d{2}\.\d{2}$")) { _pila.Clear(); nivel = 0; }          // encabezado de partida
            else
            {
                var m = RxGuiones.Match(desc);
                if (m.Success) { nivel = m.Groups[1].Value.Count(c => c == '-'); texto = m.Groups[2].Value.Trim(); }
                else nivel = Math.Max(1, _pila.Count);                                                // sin guiones: continúa el nivel actual
            }
            texto = texto.TrimEnd(':', ' ');
            if (nivel == 0) _pila.Add(texto);
            else
            {
                while (_pila.Count < nivel) _pila.Add("");
                if (_pila.Count > nivel) _pila.RemoveRange(nivel, _pila.Count - nivel);
                _pila.Add(texto);
            }
            return string.Join(" / ", _pila.Where(x => x.Length > 0));
        }
    }
}
