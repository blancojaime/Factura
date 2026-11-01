using System.Globalization;
using System.Text.RegularExpressions;

namespace ComexBol.Core.Catalogo;

/// <summary>
/// Importa el "Arancel Aduanero de Importaciones" oficial (MEFP/ANB) convertido a Markdown desde el PDF.
/// El PDF original produce tablas con columnas corridas, celdas partidas con &lt;br&gt; y descripciones en varias líneas,
/// por eso el análisis es tolerante y SIEMPRE reporta lo que no pudo interpretar (nunca lo adivina en silencio).
/// </summary>
public static partial class ArancelMarkdown
{
    static readonly Regex RxCodigo = RxCodigoGen();
    static readonly Regex RxTipo = new(@"^(AP\s?y\s?C|AP|CITES|CCRT|CRTM|DJ|C\*|C|P)(?=$|\s|[A-ZÁÉÍÓÚ(])", RegexOptions.CultureInvariant);
    static readonly Regex RxLegal = new(@"^((Ley|D\.?\s?S\.?|R\.?\s?A\.?|Dec|Decreto|Resoluci|RAN|RD)\b|R\.?\s?M\.?\s?\d)", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
    static readonly Regex RxNumero = new(@"^\d+(?:[.,]\d+)?$");
    static readonly Regex RxEntidadParen = new(@"\(([^)]+)\)");

    [GeneratedRegex(@"\d{4}\.\d{2}\.\d{2}\.\d{2}")] private static partial Regex RxCodigoGen();

    public static ResultadoImportacion Parsear(IEnumerable<TextReader> archivos, string fuente = "ANB-2026")
    {
        var partidas = new List<PartidaNandina>(); var errores = new List<ErrorImportacion>();
        var vistos = new HashSet<string>(); int archivoN = 0; bool modoIce = false;
        var ice = new Dictionary<string, IReadOnlyList<decimal>>();
        foreach (var rd in archivos)
        {
            archivoN++; int n = 0; string? linea; modoIce = false;
            while ((linea = rd.ReadLine()) is not null)
            {
                n++;
                if (Regex.IsMatch(linea, @"^\s*#+\s*\**\s*AP[ÉE]NDICE\s+I\s*\**\s*$", RegexOptions.IgnoreCase)) modoIce = true;
                if (modoIce && linea.Contains("Índice de criterios")) modoIce = false;
                var t = linea.TrimStart();
                if (!t.StartsWith('|')) continue;
                var cuerpo = t.Replace("**", "");
                var celdas0 = CortarCeldas(cuerpo);
                var codigos = RxCodigo.Matches(celdas0[0]).Select(x => x.Value.Replace(".", "")).ToList();
                if (codigos.Count == 0) continue;                 // encabezados, subtítulos y notas
                var ref_ = $"archivo {archivoN}, línea {n}";
                foreach (var (codigo, celdas) in Expandir(celdas0, codigos))
                {
                    if (modoIce)
                    {
                        var tasas = celdas.Skip(2).SelectMany(c => c.Split("<br>")).Select(Limpiar).Where(x => RxNumero.IsMatch(x)).Select(x => decimal.Parse(x.Replace(',', '.'), CultureInfo.InvariantCulture) / 100m).ToList();
                        if (tasas.Count == 6) ice[codigo] = tasas;
                        else errores.Add(new(n, $"{ref_}: {codigo} — Apéndice ICE: solo {tasas.Count} tasas legibles de 6; ingrese la tasa ICE manualmente"));
                        continue;
                    }
                    if (!vistos.Add(codigo)) { errores.Add(new(n, $"{ref_}: código {codigo} repetido (se conserva el primero)")); continue; }
                    var p = Fila(celdas, codigo, fuente, out var problema);
                    if (p is null) { errores.Add(new(n, $"{ref_}: {codigo} — {problema}")); vistos.Remove(codigo); continue; }
                    if (problema is not null) errores.Add(new(n, $"{ref_}: {codigo} — advertencia: {problema}"));
                    partidas.Add(p);
                }
            }
        }
        for (int i = 0; i < partidas.Count; i++)
            if (ice.TryGetValue(partidas[i].Codigo, out var t)) partidas[i] = partidas[i] with { IceAntiguedad = t, ImpuestoEspecial = "ICE" };
        foreach (var c in ice.Keys.Where(k => !vistos.Contains(k)))
            errores.Add(new(0, $"Apéndice ICE: código {c} no existe en el arancel principal"));
        return new(partidas, errores);
    }

    static string[] CortarCeldas(string cuerpo)
    {
        var t = cuerpo.Trim();
        if (t.StartsWith('|')) t = t[1..];
        if (t.EndsWith('|')) t = t[..^1];
        return t.Split('|');
    }

    static string Limpiar(string s) => Regex.Replace(s.Replace("_", " ").Replace("<sup>", "").Replace("</sup>", ""), @"\s+", " ").Trim();

    /// <summary>Filas que agrupan varios códigos (8471.30.00.10&lt;br&gt;8471.30.00.90): cada columna trae sus valores separados por &lt;br&gt;.</summary>
    static IEnumerable<(string Codigo, string[] Celdas)> Expandir(string[] celdas, List<string> codigos)
    {
        if (codigos.Count == 1) { yield return (codigos[0], celdas); yield break; }
        int k = codigos.Count;
        var partes = celdas.Select(c => c.Split("<br>").Select(x => x.Trim()).ToList()).ToList();
        foreach (var l in partes) while (l.Count > 1 && l[^1].Length == 0) l.RemoveAt(l.Count - 1);
        for (int j = 0; j < k; j++)
        {
            var nueva = new string[celdas.Length];
            nueva[0] = codigos[j];
            for (int c = 1; c < celdas.Length; c++)
                nueva[c] = partes[c].Count == k ? partes[c][j]
                         : partes[c].Count == 1 ? partes[c][0]
                         : partes[c].Count % k == 0 ? string.Join("<br>", partes[c].Skip(j * (partes[c].Count / k)).Take(partes[c].Count / k))
                         : j < partes[c].Count ? partes[c][j] : "";
            yield return (codigos[j], nueva);
        }
    }

    static readonly Regex RxRomano = new(@"^(I|II|III|IV|V|VI|VII|VIII|IX|X)$");
    static readonly Regex RxUnidad = new(@"^(\d+ ?)?(u|kg|g|t|l|ml|m|m²|m2|m³|m3|cm³|c/t|kWh|par|pares|doc)$", RegexOptions.IgnoreCase);
    static readonly HashSet<string> FragmentosIce = ["I", "IC", "ICE", "E", "CE", "IE", "EHD", "HD", "IEHD", "ICE-IEHD"];

    static PartidaNandina? Fila(string[] celdas, string codigo, string fuente, out string? problema)
    {
        problema = null;
        if (celdas.Length < 3) celdas = [.. celdas, "", ""];

        var descPartes = celdas[1].Split("<br>").Select(Limpiar).Where(x => x.Length > 0).ToList();
        var tokens = celdas.Skip(2).SelectMany(c => c.Split("<br>")).Select(Limpiar).Where(t => t.Length > 0).ToList();
        string? gaTexto = null; bool iceEnDesc = false; string unidadEnDesc = "";
        while (descPartes.Count > 1 && FragmentosIce.Contains(descPartes[^1].ToUpperInvariant()) && descPartes[^1].Length <= 4) { descPartes.RemoveAt(descPartes.Count - 1); iceEnDesc = true; }
        if (tokens.Count > 1 && !RxNumero.IsMatch(tokens[0]) && RxNumero.IsMatch(tokens[1]) && tokens[0].Length > 3 && !RxUnidad.IsMatch(tokens[0]))
        { descPartes[^1] = descPartes[^1].Length <= 2 || descPartes[^1].EndsWith(" c") ? descPartes[^1] + tokens[0] : descPartes[^1] + " " + tokens[0]; tokens.RemoveAt(0); }
        if (tokens.Count > 0 && RxNumero.IsMatch(tokens[0])) { gaTexto = tokens[0]; tokens.RemoveAt(0); }
        else if (descPartes.Count > 1)
        {
            // El GA cayó dentro de la descripción; tras él puede haber basura del OCR ("l", "ii", "-Partes:") o la unidad.
            int idx = descPartes.FindLastIndex(x => RxNumero.IsMatch(x));
            if (idx >= 1 && descPartes.Skip(idx + 1).All(x => x.Length <= 2 || x.StartsWith('-') || Regex.IsMatch(x, @"^[iIlL1|. ]{1,6}$")))
            {
                gaTexto = descPartes[idx];
                unidadEnDesc = descPartes.Skip(idx + 1).FirstOrDefault(x => RxUnidad.IsMatch(x)) ?? "";
                descPartes.RemoveRange(idx, descPartes.Count - idx);
            }
        }
        if (gaTexto is null) { problema = $"GA no identificado (primer dato '{tokens.FirstOrDefault()}')"; return null; }
        var desc = string.Join(" ", descPartes);
        var ga = decimal.Parse(gaTexto.Replace(',', '.'), CultureInfo.InvariantCulture);
        if (ga is < 0 or > 40) { problema = $"GA {ga} fuera de 0–40"; return null; }
        var rest = tokens;

        // Marca ICE / IEHD (el original la parte en celdas: "IC" + "E").
        string especial = "";
        while (rest.Count > 0 && FragmentosIce.Contains(rest[0].ToUpperInvariant())) { especial += rest[0].ToUpperInvariant(); rest.RemoveAt(0); }
        especial = especial.Contains("IEHD") ? "IEHD" : (especial.Length > 0 || iceEnDesc) ? "ICE" : "";

        // Unidad de medida: primera ficha reconocible entre las 3 primeras.
        string unidad = "";
        for (int i = 0; i < Math.Min(3, rest.Count); i++)
        {
            var t = rest[i];
            if (RxNumero.IsMatch(t) && i + 1 < rest.Count && RxUnidad.IsMatch($"{t} {rest[i + 1]}")) { unidad = $"{t} {rest[i + 1]}"; rest.RemoveRange(i, 2); break; }
            if (RxUnidad.IsMatch(t)) { unidad = t; rest.RemoveAt(i); break; }
            if (RxTipo.IsMatch(t) || RxLegal.IsMatch(t)) break;
        }

        if (unidad.Length == 0) unidad = unidadEnDesc;

        string tipo = "", entidad = "", legal = ""; var prefs = new List<decimal>();
        foreach (var raw in rest)
        {
            var t = raw;
            if (RxNumero.IsMatch(t)) { prefs.Add(decimal.Parse(t.Replace(',', '.'), CultureInfo.InvariantCulture)); continue; }
            if (RxRomano.IsMatch(t) || t is "*" or "(*)" or "(*" or "*)") continue;      // llamadas de nota al pie
            if (tipo.Length == 0 && RxTipo.Match(t) is { Success: true } mt && !RxLegal.IsMatch(t))
            { tipo = Regex.IsMatch(mt.Value, @"^AP\s?y\s?C$") ? "AP y C" : mt.Value; t = t[mt.Length..].Trim(); if (t.Length == 0) continue; }
            if (RxLegal.IsMatch(t)) legal = (legal + " " + t).Trim();
            else entidad = (entidad + " " + t).Trim();
        }
        var auts = RxEntidadParen.Matches(entidad).Select(x => x.Groups[1].Value.Trim()).Distinct().ToList();
        if (auts.Count == 0 && entidad.Length > 0) auts.Add(entidad);
        if (tipo.Length == 0 && (entidad.Length > 0 || (legal.Length > 0 && !legal.StartsWith("RM", StringComparison.OrdinalIgnoreCase)))) problema = "documento sin tipo identificado";
        if (unidad.Length == 0) problema = (problema is null ? "" : problema + "; ") + "unidad de medida no identificada";

        return new PartidaNandina(codigo, desc, ga / 100m, unidad, tipo == "P", auts, fuente)
        { TipoDocumento = tipo, Entidad = entidad, DispLegal = legal, Preferencias = prefs, ImpuestoEspecial = especial };
    }
}
