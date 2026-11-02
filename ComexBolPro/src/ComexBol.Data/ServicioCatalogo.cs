using ComexBol.Core.Catalogo;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

public sealed record ResumenImportacionCatalogo(int Importadas, int Rechazadas, IReadOnlyList<ErrorImportacion> Errores, bool SoloEjemplos);

public sealed class ServicioCatalogo(ComexDb db)
{
    /// <summary>Importa el CSV simple y reemplaza TODO el catálogo.</summary>
    public async Task<ResumenImportacionCatalogo> ImportarCsvAsync(TextReader csv, string version)
        => await GuardarAsync(CatalogoCsv.Parsear(csv), version);

    /// <summary>Importa el Arancel oficial en Markdown (varios archivos = un solo arancel) y reemplaza TODO el catálogo.</summary>
    public async Task<ResumenImportacionCatalogo> ImportarArancelMarkdownAsync(IEnumerable<TextReader> archivos, string version)
        => await GuardarAsync(ArancelMarkdown.Parsear(archivos), version);

    static string Pct(decimal? f) => f is null ? "" : (f.Value * 100m).ToString("0.##", System.Globalization.CultureInfo.InvariantCulture);

    /// <summary>Preferencia impresa en el arancel para un acuerdo (en fracción), o null si no hay valor asignado.</summary>
    public static decimal? PreferenciaDe(PartidaCatalogo p, string acuerdo)
    {
        if (!p.PrefAsignada || string.IsNullOrWhiteSpace(acuerdo)) return null;
        var col = acuerdo.StartsWith("ACE 22", StringComparison.OrdinalIgnoreCase) ? p.PrefChile
                : acuerdo.StartsWith("ACE 66", StringComparison.OrdinalIgnoreCase) ? p.PrefMexico
                : p.PrefCan;      // CAN, ACE 36, ACE 47, VEN comparten columna
        return decimal.TryParse(col, System.Globalization.NumberStyles.Number, System.Globalization.CultureInfo.InvariantCulture, out var v) ? v / 100m : null;
    }

    async Task<ResumenImportacionCatalogo> GuardarAsync(ResultadoImportacion res, string version)
    {
        if (res.Partidas.Count == 0) return new(0, res.Errores.Count, res.Errores, false);
        await using var tx = await db.Database.BeginTransactionAsync();
        db.Partidas.RemoveRange(db.Partidas);
        await db.SaveChangesAsync();
        db.Partidas.AddRange(res.Partidas.Select(p => new PartidaCatalogo
        {
            Codigo = p.Codigo, Descripcion = p.Descripcion, AlicuotaGA = p.AlicuotaGA, Unidad = p.Unidad,
            Prohibida = p.Prohibida, Autorizaciones = string.Join('|', p.Autorizaciones), Fuente = p.Fuente, Version = version,
            TipoDocumento = p.TipoDocumento, Entidad = p.Entidad, DispLegal = p.DispLegal, ImpuestoEspecial = p.ImpuestoEspecial,
            IceAntiguedad = string.Join(';', p.IceAntiguedad.Select(x => x.ToString(System.Globalization.CultureInfo.InvariantCulture))),
            Preferencias = string.Join(';', p.Preferencias.Select(x => x.ToString(System.Globalization.CultureInfo.InvariantCulture))),
            PrefAsignada = p.PorAcuerdo is not null,
            PrefCan = Pct(p.PorAcuerdo?.CanAce36Ace47Ven), PrefChile = Pct(p.PorAcuerdo?.Ace22Chile),
            PrefProtocolo = p.PorAcuerdo?.Ace22Protocolo ?? "", PrefMexico = Pct(p.PorAcuerdo?.Ace66Mexico)
        }));
        await db.SaveChangesAsync(); await tx.CommitAsync();
        return new(res.Partidas.Count, res.Errores.Count, res.Errores, res.Partidas.All(p => p.EsEjemplo));
    }

    public Task<PartidaCatalogo?> ObtenerAsync(string codigo) => db.Partidas.AsNoTracking().FirstOrDefaultAsync(p => p.Codigo == codigo);

    /// <summary>Busca por prefijo de código (si el texto es numérico) o por palabras en la descripción.</summary>
    public async Task<IReadOnlyList<PartidaCatalogo>> BuscarAsync(string texto, int max = 50)
    {
        texto = texto.Trim();
        if (texto.Length == 0) return [];
        var q = db.Partidas.AsNoTracking();
        var digitos = new string(texto.Where(char.IsDigit).ToArray());
        if (digitos.Length > 0 && digitos.Length == texto.Replace(".", "").Replace(" ", "").Length)
            return await q.Where(p => p.Codigo.StartsWith(digitos)).OrderBy(p => p.Codigo).Take(max).ToListAsync();
        foreach (var palabra in texto.Split(' ', StringSplitOptions.RemoveEmptyEntries))
        { var w = palabra; q = q.Where(p => EF.Functions.Like(p.Descripcion, "%" + w + "%")); }
        return await q.OrderBy(p => p.Codigo).Take(max).ToListAsync();
    }

    /// <summary>
    /// Completa la alícuota GA de los ítems desde el catálogo y bloquea mercancías prohibidas.
    /// Devuelve avisos (partida no encontrada, fuente de ejemplo, autorizaciones exigidas).
    /// </summary>
    static string Mostrar(string pct) => pct.Length == 0 ? "—" : pct + " %";

    public async Task<IReadOnlyList<string>> AplicarAOperacionAsync(int opId)
    {
        var avisos = new List<string>();
        var items = await db.Items.Where(i => i.OperacionId == opId).ToListAsync();
        foreach (var it in items)
        {
            var p = await ObtenerAsync(it.CodigoNandina);
            if (p is null) { avisos.Add($"Ítem {it.Numero}: partida {it.CodigoNandina} no está en el catálogo cargado; GA no se modificó."); continue; }
            if (p.Prohibida) throw new InvalidOperationException($"Ítem {it.Numero}: la partida {p.Codigo} figura como mercancía prohibida.");
            it.AlicuotaGA = p.AlicuotaGA;
            if (p.Fuente.Equals("EJEMPLO", StringComparison.OrdinalIgnoreCase)) avisos.Add($"Ítem {it.Numero}: alícuota tomada de datos de EJEMPLO, no oficiales.");
            if (p.TipoDocumento.Length > 0 || p.Autorizaciones.Length > 0) avisos.Add($"Ítem {it.Numero}: documento adicional {p.TipoDocumento} — {(p.Entidad.Length > 0 ? p.Entidad : p.Autorizaciones.Replace("|", ", "))} {p.DispLegal}".Trim());
            if (p.PrefAsignada)
                avisos.Add($"Ítem {it.Numero}: preferencias del arancel — CAN/ACE 36/ACE 47/VEN: {Mostrar(p.PrefCan)} · ACE 22 Chile: {Mostrar(p.PrefChile)}{(p.PrefProtocolo.Length > 0 ? $" (Prot. {p.PrefProtocolo})" : "")} · ACE 66 México: {Mostrar(p.PrefMexico)}.");
            else if (p.Preferencias.Length > 0)
                avisos.Add($"Ítem {it.Numero}: preferencias impresas en el arancel NO asignables a una columna con certeza: {p.Preferencias.Replace(";", " / ")} %. Verifique en el arancel impreso.");
            if (!string.IsNullOrWhiteSpace(it.AcuerdoPreferencial))
            {
                var pref = PreferenciaDe(p, it.AcuerdoPreferencial);
                if (pref is null) avisos.Add($"Ítem {it.Numero}: el arancel no trae valor para {it.AcuerdoPreferencial}; verifique antes de aplicar desgravación.");
                else if (it.Desgravacion == 0) { it.Desgravacion = pref.Value; db.Operaciones.First(o => o.Id == opId).UsaPreferenciaArancelaria = true; avisos.Add($"Ítem {it.Numero}: desgravación {pref.Value:P0} tomada del arancel para {it.AcuerdoPreferencial}. Requiere Certificado de Origen."); }
                else if (it.Desgravacion != pref.Value) avisos.Add($"Ítem {it.Numero}: usted declaró {it.Desgravacion:P0} y el arancel indica {pref.Value:P0} para {it.AcuerdoPreferencial}.");
            }
            if (p.ImpuestoEspecial == "ICE")
            {
                var tasas = p.IceAntiguedad.Length == 0 ? [] : p.IceAntiguedad.Split(';').Select(x => decimal.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
                if (tasas.Length == 6) { it.AlicuotaIce = tasas[Math.Clamp(it.AntiguedadAnios, 0, 5)]; avisos.Add($"Ítem {it.Numero}: ICE {it.AlicuotaIce:P0} (Apéndice I, antigüedad {it.AntiguedadAnios} años)."); }
                else avisos.Add($"Ítem {it.Numero}: partida sujeta a ICE; la tasa no figura legible en el arancel: ingréselas manualmente.");
            }
            else if (p.ImpuestoEspecial == "IEHD") avisos.Add($"Ítem {it.Numero}: partida sujeta a IEHD (Bs/litro): ingrese la tasa vigente.");
            db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = "Catálogo", Detalle = $"Ítem {it.Numero}: GA {p.AlicuotaGA:P0} desde catálogo v{p.Version} ({p.Fuente})." });
        }
        await db.SaveChangesAsync();
        return avisos;
    }
}
