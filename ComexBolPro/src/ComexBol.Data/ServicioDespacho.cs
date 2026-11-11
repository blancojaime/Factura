using ComexBol.Core;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

/// <summary>Despacho aduanero: datos de la DIM, validación previa, canal de selectividad y descargos.</summary>
public sealed class ServicioDespacho(ComexDb db)
{
    public string Usuario { get; set; } = "";
    void Log(int opId, string cat, string detalle) => db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = cat, Detalle = detalle, Usuario = Usuario });

    public async Task GuardarDatosAsync(int opId, DatosDespacho d)
    {
        if (d.Bultos < 0 || d.PesoBrutoManifiestoKg < 0) throw new ArgumentException("Bultos y peso del manifiesto no pueden ser negativos.");
        if (!string.IsNullOrWhiteSpace(d.TipoDespacho) && !Despacho.Tipos.Contains(d.TipoDespacho)) throw new ArgumentException("Tipo de despacho no válido.");
        var op = await db.Operaciones.FirstAsync(o => o.Id == opId);
        op.TipoDespacho = d.TipoDespacho; op.Regimen = d.Regimen; op.AduanaIngreso = d.AduanaIngreso.Trim(); op.AduanaDestino = d.AduanaDestino.Trim(); op.CodigoDeclarante = d.CodigoDeclarante.Trim();
        op.ModalidadTransporte = d.ModalidadTransporte; op.NroDocEmbarque = d.NroDocEmbarque.Trim(); op.NroManifiesto = d.NroManifiesto.Trim(); op.Bultos = d.Bultos;
        op.PesoBrutoManifiestoKg = d.PesoBrutoManifiestoKg; op.NroDav = d.NroDav.Trim(); op.NroDim = d.NroDim.Trim();
        Log(opId, "Despacho", $"Datos de la DIM guardados: despacho {d.TipoDespacho}, régimen «{d.Regimen}», {d.AduanaIngreso} → {d.AduanaDestino}.");
        await db.SaveChangesAsync();
    }

    public async Task<IReadOnlyList<Hallazgo>> ValidarAsync(int opId, decimal toleranciaPeso)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Liquidaciones).FirstAsync(o => o.Id == opId);
        var faltan = (await new ServicioOperaciones(db).ChecklistAsync(opId)).Count(x => !x.Presente);
        var bancarizacion = false;
        var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault();
        if (ult is not null)
        {
            var r = System.Text.Json.JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson)!;
            bancarizacion = r.RequiereBancarizacion && string.IsNullOrWhiteSpace(op.NroComprobantePago);
        }
        var dav = op.CuestionarioRespondido && Valoracion.Descartar(op.Cuestionario(), op.Ajustes()).PrimerMetodoAplicable;
        return Despacho.Validar(op.DatosDim(), op.Items.Sum(i => i.PesoBrutoKg), op.Items.Count, ult is not null, dav, bancarizacion, faltan, toleranciaPeso);
    }

    /// <summary>Asigna el canal y genera su lista de control (reemplaza la lista del canal anterior).</summary>
    public async Task AsignarCanalAsync(int opId, string canal, string observacion = "")
    {
        if (!Despacho.Canales.Contains(canal)) throw new ArgumentException("Canal no válido.");
        var op = await db.Operaciones.FirstAsync(o => o.Id == opId);
        var previas = db.TareasDespacho.Where(t => t.OperacionId == opId); db.TareasDespacho.RemoveRange(previas);
        op.Canal = canal; op.ObservacionAduana = observacion ?? "";
        int n = 1; foreach (var t in Despacho.TareasCanal(canal)) db.TareasDespacho.Add(new() { OperacionId = opId, Canal = canal, Orden = n++, Texto = t });
        Log(opId, "Despacho", canal == "Sin asignar" ? "Canal sin asignar." : $"Canal {canal} asignado por la Aduana: lista de control generada.");
        await db.SaveChangesAsync();
    }

    public Task<List<TareaDespacho>> TareasAsync(int opId) => db.TareasDespacho.AsNoTracking().Where(t => t.OperacionId == opId).OrderBy(t => t.Orden).ToListAsync();

    public async Task MarcarTareaAsync(int tareaId, bool hecha)
    {
        var t = await db.TareasDespacho.FirstAsync(x => x.Id == tareaId); t.Hecha = hecha;
        if (hecha) Log(t.OperacionId, "Despacho", $"Canal {t.Canal}: «{t.Texto}» cumplido.");
        await db.SaveChangesAsync();
    }

    public async Task RegistrarLevanteAsync(int opId, DateOnly fecha)
    {
        var op = await db.Operaciones.FirstAsync(o => o.Id == opId); op.FechaLevante = fecha;
        Log(opId, "Despacho", $"Levante registrado el {fecha:dd/MM/yyyy}."); await db.SaveChangesAsync();
    }

    public async Task<string> GenerarDescargoAsync(int opId, string observacion, IEnumerable<string> pruebas)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).FirstAsync(o => o.Id == opId);
        var perfil = await db.Perfiles.AsNoTracking().FirstOrDefaultAsync() ?? new PerfilImportador();
        var valor = op.Items.Sum(i => i.ValorFactura);
        var texto = Despacho.PlantillaDescargo(op.Carpeta, perfil.RazonSocial, perfil.Nit, string.IsNullOrWhiteSpace(op.CodigoDeclarante) ? perfil.AgenciaDespachante : op.CodigoDeclarante, op.NroDim, valor, observacion, pruebas);
        Log(opId, "Despacho", "Borrador de descargos generado."); await db.SaveChangesAsync();
        return texto;
    }
}
