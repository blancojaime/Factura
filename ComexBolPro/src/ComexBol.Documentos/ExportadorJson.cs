using System.Text.Json;
using System.Text.Json.Serialization;
using ComexBol.Core;
using ComexBol.Data;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Documentos;

/// <summary>
/// Exporta la operación como JSON estructurado: los datos que el despachante o el importador transcriben a la DMI en el SUMA.
/// Es un borrador de trabajo; la numeración de casillas oficiales depende del instructivo vigente de la Aduana y no se asume aquí.
/// </summary>
public static class ExportadorJson
{
    static readonly JsonSerializerOptions Opciones = new() { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping, DefaultIgnoreCondition = JsonIgnoreCondition.Never };

    public static async Task ExportarAsync(ComexDb db, int opId, string ruta, DateOnly hoy)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Liquidaciones).Include(o => o.Documentos).FirstAsync(o => o.Id == opId);
        var perfil = await db.Perfiles.AsNoTracking().FirstOrDefaultAsync();
        var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault();
        var liq = ult is null ? null : JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson);
        var json = new
        {
            formato = "comex-jb/borrador-dmi/2", generado = DateTime.Now.ToString("s"), advertencia = "Borrador de trabajo: verifique cada dato contra la normativa y el instructivo vigente del SUMA.",
            importador = perfil is null ? null : new { perfil.RazonSocial, perfil.Nit, perfil.TipoImportador, perfil.AgenciaDespachante },
            operacion = new { op.Carpeta, tipo = op.Tipo.ToString(), incoterm = op.Incoterm.ToString(), moneda = op.MonedaFactura, inicio = op.FechaInicio.ToString("yyyy-MM-dd"), op.Flete, op.Seguro, op.GastosOrigen, op.OtrosGastosFrontera },
            valoracion = new
            {
                metodo = "Primer método: valor de transacción (Decisión 571 CAN)", cuestionarioRespondido = op.CuestionarioRespondido,
                vinculacion = op.Vinculacion, vinculacionInfluyoPrecio = op.VinculacionInfluyoPrecio, restriccionesCesion = op.RestriccionesCesion,
                condicionesNoCuantificables = op.CondicionesNoCuantificables, reversionAlVendedor = op.ReversionAlVendedor,
                valorDeTransaccionAplicable = Valoracion.Descartar(op.Cuestionario(), op.Ajustes()).PrimerMetodoAplicable,
                adiciones = new { comisiones = op.AdComisiones, envases = op.AdEnvases, assists = op.AdAssists, royalties = op.AdRoyalties, reversiones = op.AdReversiones, otras = op.AdOtros },
                deducciones = new { armadoPosterior = op.DedArmadoPosterior, transportePosterior = op.DedTransportePosterior, impuestosBolivia = op.DedImpuestosBolivia },
                notas = op.NotasValoracion, desgloseValorBob = liq?.Desglose?.Select(l => new { l.Concepto, l.Bob })
            },
            despacho = new
            {
                op.TipoDespacho, op.Regimen, op.AduanaIngreso, op.AduanaDestino, codigoDeclarante = op.CodigoDeclarante, modalidadTransporte = op.ModalidadTransporte,
                documentoEmbarque = new { tipo = Despacho.DocumentoEmbarque(op.ModalidadTransporte), numero = op.NroDocEmbarque }, manifiesto = new { numero = op.NroManifiesto, op.Bultos, pesoBrutoKg = op.PesoBrutoManifiestoKg },
                op.NroDav, op.NroDim, canal = op.Canal, levante = op.FechaLevante?.ToString("yyyy-MM-dd")
            },
            bancarizacion = new { requerida = liq?.RequiereBancarizacion, op.EntidadFinanciera, op.NroComprobantePago },
            items = op.Items.OrderBy(i => i.Numero).Select(i => new
            {
                i.Numero, partidaNandina = i.CodigoNandina, descripcion = i.Descripcion, i.Marca, i.Modelo, i.Serie, paisOrigen = i.PaisOrigen,
                valorFactura = i.ValorFactura, pesoBrutoKg = i.PesoBrutoKg, pesoNetoKg = i.PesoNetoKg, gravamenArancelarioPct = i.AlicuotaGA * 100m,
                acuerdoPreferencial = i.AcuerdoPreferencial, desgravacionPct = i.Desgravacion * 100m, icePct = i.AlicuotaIce * 100m
            }),
            liquidacion = liq is null ? null : new { version = ult!.Version, tipoCambioFecha = ult.TipoCambioFecha.ToString("yyyy-MM-dd"), liq.ValorFobBob, liq.AdicionesBob, liq.DeduccionesBob, liq.CifBob, liq.GA, liq.ICE, liq.IEHD, liq.IVA, liq.TotalTributos },
            documentos = op.Documentos.Select(d => new { tipo = d.Tipo.ToString(), archivo = d.NombreArchivo, sha256 = d.Sha256, validado = d.Validado })
        };
        await File.WriteAllTextAsync(ruta, JsonSerializer.Serialize(json, Opciones));
    }
}
