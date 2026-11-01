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
        if (!File.Exists(rutaImagen)) throw new FileNotFoundException("No existe el archivo", rutaImagen);
        if (Path.GetExtension(rutaImagen).Equals(".pdf", StringComparison.OrdinalIgnoreCase))
        {
            var tmp = Directory.CreateTempSubdirectory("comexbol-pdf-");
            try
            {
                var paginas = await PdfRasterizador.AImagenesAsync(rutaImagen, tmp.FullName, ct);
                var sb = new StringBuilder();
                foreach (var pag in paginas) sb.AppendLine(await LeerImagenAsync(pag, ct));
                return sb.ToString();
            }
            finally { try { tmp.Delete(true); } catch (IOException) { } }
        }
        return await LeerImagenAsync(rutaImagen, ct);
    }

    async Task<string> LeerImagenAsync(string rutaImagen, CancellationToken ct)
    {

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

/// <summary>Convierte un PDF en imágenes PNG (una por página) con pdftoppm (Poppler). Windows: poppler-windows, agregar bin\ al PATH.</summary>
public static class PdfRasterizador
{
    public static async Task<IReadOnlyList<string>> AImagenesAsync(string pdf, string carpetaSalida, CancellationToken ct = default, int dpi = 200, int maxPaginas = 20)
    {
        var psi = new ProcessStartInfo("pdftoppm") { RedirectStandardError = true, RedirectStandardOutput = true, UseShellExecute = false, CreateNoWindow = true };
        foreach (var a in new[] { "-r", dpi.ToString(), "-l", maxPaginas.ToString(), "-png", pdf, Path.Combine(carpetaSalida, "p") }) psi.ArgumentList.Add(a);
        try
        {
            using var p = Process.Start(psi)!;
            var err = p.StandardError.ReadToEndAsync(ct);
            await p.WaitForExitAsync(ct);
            if (p.ExitCode != 0) throw new InvalidOperationException($"No se pudo leer el PDF ({p.ExitCode}): {(await err).Trim()}");
        }
        catch (System.ComponentModel.Win32Exception)
        {
            throw new InvalidOperationException("Para leer PDF instale Poppler (pdftoppm) y agréguelo al PATH, o convierta el PDF a imagen.");
        }
        return Directory.GetFiles(carpetaSalida, "p-*.png").OrderBy(f => f, StringComparer.Ordinal).ToList();
    }
}
