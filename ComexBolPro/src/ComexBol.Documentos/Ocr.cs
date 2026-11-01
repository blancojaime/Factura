using System.Diagnostics;
using System.Text;

namespace ComexBol.Documentos;

public interface IMotorOcr
{
    Task<string> LeerTextoAsync(string rutaImagen, CancellationToken ct = default);
}

/// <summary>
/// OCR local con el ejecutable de Tesseract (sin DLL nativas que empaquetar). Windows: instalador UB-Mannheim,
/// con el paquete de idioma "spa". Se invoca sin shell y con ArgumentList (sin inyección de comandos).
/// </summary>
public sealed class TesseractCliOcr(string? ejecutable = null, string idiomas = "spa+eng") : IMotorOcr
{
    static readonly string[] Candidatos = [@"C:\Program Files\Tesseract-OCR\tesseract.exe", @"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe", "tesseract"];
    readonly string _exe = ejecutable ?? Candidatos.FirstOrDefault(File.Exists) ?? "tesseract";

    public async Task<string> LeerTextoAsync(string rutaImagen, CancellationToken ct = default)
    {
        var ext = Path.GetExtension(rutaImagen).ToLowerInvariant();
        if (ext == ".pdf") throw new NotSupportedException("Tesseract no lee PDF directamente: convierta las páginas a imagen (p. ej. pdftoppm) antes del OCR.");
        if (!File.Exists(rutaImagen)) throw new FileNotFoundException("No existe la imagen", rutaImagen);

        var psi = new ProcessStartInfo(_exe) { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true, StandardOutputEncoding = Encoding.UTF8 };
        foreach (var a in new[] { rutaImagen, "stdout", "-l", idiomas, "--psm", "6" }) psi.ArgumentList.Add(a);
        try
        {
            using var p = Process.Start(psi)!;
            var salida = p.StandardOutput.ReadToEndAsync(ct); var error = p.StandardError.ReadToEndAsync(ct);
            await p.WaitForExitAsync(ct);
            if (p.ExitCode != 0) throw new InvalidOperationException($"Tesseract falló ({p.ExitCode}): {(await error).Trim()}");
            return await salida;
        }
        catch (System.ComponentModel.Win32Exception)
        {
            throw new InvalidOperationException("No se encontró Tesseract. Instálelo (con idioma español) y reinicie la aplicación.");
        }
    }
}
