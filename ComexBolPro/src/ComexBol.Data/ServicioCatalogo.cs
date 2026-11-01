using ComexBol.Core.Catalogo;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

public sealed record ResumenImportacionCatalogo(int Importadas, int Rechazadas, IReadOnlyList<ErrorImportacion> Errores, bool SoloEjemplos);

public sealed class ServicioCatalogo(ComexDb db)
{
    /// <summary>Importa el CSV y reemplaza TODO el catálogo (el arancel se publica como versión completa).</summary>
    public async Task<ResumenImportacionCatalogo> ImportarCsvAsync(TextReader csv, string version)
    {
        var res = CatalogoCsv.Parsear(csv);
        if (res.Partidas.Count == 0) return new(0, res.Errores.Count, res.Errores, false);
        await using var tx = await db.Database.BeginTransactionAsync();
        db.Partidas.RemoveRange(db.Partidas);
        db.Partidas.AddRange(res.Partidas.Select(p => new PartidaCatalogo
        {
            Codigo = p.Codigo, Descripcion = p.Descripcion, AlicuotaGA = p.AlicuotaGA, Unidad = p.Unidad,
            Prohibida = p.Prohibida, Autorizaciones = string.Join('|', p.Autorizaciones), Fuente = p.Fuente, Version = version
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
            if (p.Autorizaciones.Length > 0) avisos.Add($"Ítem {it.Numero}: requiere autorización previa ({p.Autorizaciones.Replace("|", ", ")}) vía VUCE.");
            db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = "Catálogo", Detalle = $"Ítem {it.Numero}: GA {p.AlicuotaGA:P0} desde catálogo v{p.Version} ({p.Fuente})." });
        }
        await db.SaveChangesAsync();
        return avisos;
    }
}
