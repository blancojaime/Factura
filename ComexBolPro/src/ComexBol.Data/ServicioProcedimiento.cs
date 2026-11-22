using ComexBol.Core;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

public sealed record FilaProcedimiento(string Codigo, string Titulo, string Detalle, string Responsables, string Documentos, string Tiempo, string Normativa, string Consejo, string Fase,
    bool Hecho, bool Sugerido, string Nota, bool EsControl);

/// <summary>Guía paso a paso del manual de procedimientos (P-01…P-11) y lista de control del expediente (C-01…C-12), con avance por operación.</summary>
public sealed class ServicioProcedimiento(ComexDb db)
{
    public string Usuario { get; set; } = "";

    public async Task<IReadOnlyList<FilaProcedimiento>> ListarAsync(int opId)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Documentos).Include(o => o.Liquidaciones).FirstAsync(o => o.Id == opId);
        var perfil = await db.Perfiles.AsNoTracking().FirstOrDefaultAsync();
        var estados = (await db.EstadosPaso.AsNoTracking().Where(e => e.OperacionId == opId).ToListAsync()).ToDictionary(e => e.Codigo);
        bool Doc(TipoDocumento t) => op.Documentos.Any(d => d.Tipo == t);
        bool DimLista = !string.IsNullOrWhiteSpace(op.AduanaIngreso) && !string.IsNullOrWhiteSpace(op.AduanaDestino) && !string.IsNullOrWhiteSpace(op.NroDocEmbarque);
        var sug = new Dictionary<string, bool>
        {
            ["P-01"] = perfil is not null && !string.IsNullOrWhiteSpace(perfil.Nit), ["P-02"] = perfil is not null && !string.IsNullOrWhiteSpace(perfil.Nit),
            ["P-03"] = op.Items.Count > 0, ["P-04"] = Doc(TipoDocumento.Bancario), ["P-05"] = Doc(TipoDocumento.Embarque) && Doc(TipoDocumento.PackingList),
            ["P-06"] = !string.IsNullOrWhiteSpace(op.NroManifiesto), ["P-07"] = op.Bultos > 0 && op.PesoBrutoManifiestoKg > 0,
            ["P-08"] = op.CuestionarioRespondido && DimLista && op.Liquidaciones.Count > 0, ["P-09"] = op.Canal != "Sin asignar", ["P-10"] = op.FechaLevante is not null,
            ["P-11"] = op.GastoHonorariosAgencia + op.GastoAlmacenaje + op.GastoTransporteInterno + op.GastoOtros > 0,
            ["C-01"] = perfil is not null && !string.IsNullOrWhiteSpace(perfil.Nit), ["C-02"] = perfil is not null && !string.IsNullOrWhiteSpace(perfil.Nit),
            ["C-03"] = op.Items.Any(i => !string.IsNullOrWhiteSpace(i.Marca) || !string.IsNullOrWhiteSpace(i.Modelo)), ["C-04"] = Doc(TipoDocumento.Factura), ["C-05"] = Doc(TipoDocumento.Bancario),
            ["C-06"] = Doc(TipoDocumento.CertificadoOrigen), ["C-07"] = Doc(TipoDocumento.PackingList), ["C-08"] = Doc(TipoDocumento.Embarque),
            ["C-09"] = !string.IsNullOrWhiteSpace(op.NroManifiesto), ["C-10"] = op.Bultos > 0, ["C-11"] = op.CuestionarioRespondido && DimLista && !string.IsNullOrWhiteSpace(op.NroDim),
            ["C-12"] = op.FechaLevante is not null && !string.IsNullOrWhiteSpace(op.NroComprobantePago)
        };
        var lista = new List<FilaProcedimiento>();
        foreach (var p in GuiaProcedimiento.Pasos)
        {
            estados.TryGetValue(p.Codigo, out var e);
            lista.Add(new(p.Codigo, p.Proceso, p.Procedimiento, p.Responsables, p.Documentos, p.Tiempo, p.Normativa, p.Consejo, p.Fase, e?.Hecho ?? false, sug.GetValueOrDefault(p.Codigo), e?.Nota ?? "", false));
        }
        foreach (var c in GuiaProcedimiento.Control)
        {
            estados.TryGetValue(c.Codigo, out var e);
            lista.Add(new(c.Codigo, c.Documento, c.Criterio, c.Emisor, c.Etapa, c.Obligatoriedad, "", "", "Control del expediente", e?.Hecho ?? false, sug.GetValueOrDefault(c.Codigo), e?.Nota ?? "", true));
        }
        return lista;
    }

    public async Task MarcarAsync(int opId, string codigo, bool hecho, string nota = "", DateOnly? fecha = null)
    {
        if (!GuiaProcedimiento.Pasos.Any(p => p.Codigo == codigo) && !GuiaProcedimiento.Control.Any(c => c.Codigo == codigo)) throw new ArgumentException("Paso desconocido.");
        var e = await db.EstadosPaso.FirstOrDefaultAsync(x => x.OperacionId == opId && x.Codigo == codigo);
        if (e is null) { e = new() { OperacionId = opId, Codigo = codigo }; db.EstadosPaso.Add(e); }
        e.Hecho = hecho; e.Nota = nota ?? ""; e.Fecha = hecho ? (fecha ?? DateOnly.FromDateTime(DateTime.Today)) : null;
        if (hecho) db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = "Guía", Detalle = $"{codigo} cumplido.{(string.IsNullOrWhiteSpace(nota) ? "" : " " + nota)}", Usuario = Usuario });
        await db.SaveChangesAsync();
    }

    /// <summary>Avance global: pasos cumplidos o sugeridos por los datos del sistema.</summary>
    public static (int Hechos, int Total) Avance(IEnumerable<FilaProcedimiento> filas, bool control)
    { var l = filas.Where(f => f.EsControl == control).ToList(); return (l.Count(f => f.Hecho), l.Count); }
}
