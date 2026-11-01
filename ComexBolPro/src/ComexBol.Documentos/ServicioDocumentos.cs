using System.Text.Json;
using ComexBol.Core;
using ComexBol.Data;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Documentos;

public sealed record DocumentoProcesado(Documento Documento, TipoDocumento Tipo, CamposFactura Campos, string TextoOcr);

public sealed class ServicioDocumentos(ComexDb db, IMotorOcr ocr)
{
    ServicioOperaciones Ops => new(db);

    /// <summary>Adjunta la imagen al legajo, la clasifica, ejecuta OCR y guarda la PROPUESTA (sin aplicarla).</summary>
    public async Task<DocumentoProcesado> ProcesarAsync(int opId, string rutaImagen, CancellationToken ct = default)
    {
        var texto = await ocr.LeerTextoAsync(rutaImagen, ct);
        var tipo = ExtractorFactura.Clasificar(texto, Path.GetFileName(rutaImagen));
        var campos = ExtractorFactura.Extraer(texto);
        var doc = await Ops.AdjuntarDocumentoAsync(opId, tipo, rutaImagen);
        doc.OcrJson = JsonSerializer.Serialize(campos);
        db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = "OCR", Detalle = $"{doc.NombreArchivo} clasificado como {tipo}; propuesta pendiente de confirmación." });
        await db.SaveChangesAsync();
        return new(doc, tipo, campos, texto);
    }

    /// <summary>El usuario confirma (o corrige) los campos: recién entonces se escriben en la operación.</summary>
    public async Task ConfirmarAsync(int opId, int documentoId, string? incoterm, string? moneda, string? numeroFactura, string? proveedor)
    {
        var op = await db.Operaciones.FirstAsync(o => o.Id == opId);
        var doc = await db.Documentos.FirstAsync(d => d.Id == documentoId && d.OperacionId == opId);
        var cambios = new List<string>();
        if (incoterm is not null && Enum.TryParse<Incoterm>(incoterm, true, out var i) && i != op.Incoterm) { cambios.Add($"Incoterm {op.Incoterm}→{i}"); op.Incoterm = i; }
        if (!string.IsNullOrWhiteSpace(moneda) && moneda != op.MonedaFactura) { cambios.Add($"Moneda {op.MonedaFactura}→{moneda}"); op.MonedaFactura = moneda!; }
        if (!string.IsNullOrWhiteSpace(numeroFactura)) cambios.Add($"Factura N.º {numeroFactura}");
        if (!string.IsNullOrWhiteSpace(proveedor)) cambios.Add($"Proveedor {proveedor}");
        doc.Validado = true;
        db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = "OCR", Detalle = $"Confirmado por el usuario: {(cambios.Count == 0 ? "sin cambios" : string.Join("; ", cambios))}." });
        await db.SaveChangesAsync();
    }
}
