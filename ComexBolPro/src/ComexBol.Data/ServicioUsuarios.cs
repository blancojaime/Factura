using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

/// <summary>Usuarios del sistema. Las claves se guardan con PBKDF2-SHA256 (120.000 iteraciones) y sal aleatoria; nunca en texto.</summary>
public sealed class ServicioUsuarios(ComexDb db)
{
    public const string Administrador = "Administrador", Operador = "Operador";
    const int Iteraciones = 120_000;

    public Task<bool> HayUsuariosAsync() => db.Usuarios.AnyAsync();
    public Task<List<Usuario>> ListarAsync() => db.Usuarios.AsNoTracking().OrderBy(u => u.NombreUsuario).ToListAsync();

    static (string Hash, string Sal) Derivar(string clave, byte[]? sal = null)
    {
        sal ??= RandomNumberGenerator.GetBytes(16);
        var h = Pbkdf2Sha256(System.Text.Encoding.UTF8.GetBytes(clave), sal, Iteraciones);
        return (Convert.ToBase64String(h), Convert.ToBase64String(sal));
    }

    /// <summary>
    /// PBKDF2 (RFC 8018) con HMAC-SHA256 y 32 bytes de salida, implementado sobre HMAC para no depender de la función
    /// de derivación del sistema operativo. Produce exactamente el mismo resultado que Rfc2898DeriveBytes.Pbkdf2.
    /// </summary>
    public static byte[] Pbkdf2Sha256(byte[] clave, byte[] sal, int iteraciones)
    {
        using var hmac = new HMACSHA256(clave);
        var bloque = new byte[sal.Length + 4]; Buffer.BlockCopy(sal, 0, bloque, 0, sal.Length); bloque[^1] = 1;      // sal || INT(1)
        var u = hmac.ComputeHash(bloque); var resultado = (byte[])u.Clone();
        for (int i = 1; i < iteraciones; i++)
        {
            u = hmac.ComputeHash(u);
            for (int j = 0; j < resultado.Length; j++) resultado[j] ^= u[j];
        }
        return resultado;
    }

    static void ValidarClave(string clave)
    {
        if (string.IsNullOrEmpty(clave) || clave.Length < 6) throw new ArgumentException("La clave debe tener al menos 6 caracteres.");
    }

    public async Task<Usuario> CrearAsync(string nombreUsuario, string nombreCompleto, string clave, string rol = Operador)
    {
        nombreUsuario = (nombreUsuario ?? "").Trim().ToLowerInvariant();
        if (nombreUsuario.Length < 3 || nombreUsuario.Any(c => !(char.IsLetterOrDigit(c) || c is '.' or '_' or '-')))
            throw new ArgumentException("El usuario debe tener al menos 3 caracteres (letras, números, punto, guion).");
        ValidarClave(clave);
        if (rol is not (Administrador or Operador)) throw new ArgumentException("Rol inválido.");
        if (await db.Usuarios.AnyAsync(u => u.NombreUsuario == nombreUsuario)) throw new InvalidOperationException($"Ya existe el usuario «{nombreUsuario}».");
        var (h, s) = Derivar(clave);
        var u = new Usuario { NombreUsuario = nombreUsuario, NombreCompleto = (nombreCompleto ?? "").Trim(), Rol = rol, ClaveHash = h, Sal = s };
        db.Usuarios.Add(u); await db.SaveChangesAsync(); return u;
    }

    /// <summary>Devuelve el usuario si las credenciales son válidas y está activo; null en caso contrario (sin revelar cuál falló).</summary>
    public async Task<Usuario?> AutenticarAsync(string nombreUsuario, string clave)
    {
        var nombre = (nombreUsuario ?? "").Trim().ToLowerInvariant();
        var u = await db.Usuarios.FirstOrDefaultAsync(x => x.NombreUsuario == nombre);
        if (u is null || !u.Activo) { Derivar(clave ?? ""); return null; }          // costo similar para no delatar si el usuario existe
        var (h, _) = Derivar(clave ?? "", Convert.FromBase64String(u.Sal));
        if (!CryptographicOperations.FixedTimeEquals(Convert.FromBase64String(h), Convert.FromBase64String(u.ClaveHash))) return null;
        u.UltimoAcceso = DateTime.Now; await db.SaveChangesAsync(); return u;
    }

    public async Task CambiarClaveAsync(int id, string nueva)
    {
        ValidarClave(nueva);
        var u = await db.Usuarios.FirstAsync(x => x.Id == id);
        (u.ClaveHash, u.Sal) = Derivar(nueva); await db.SaveChangesAsync();
    }

    public async Task CambiarRolAsync(int id, string rol)
    {
        var u = await db.Usuarios.FirstAsync(x => x.Id == id);
        if (rol is not (Administrador or Operador)) throw new ArgumentException("Rol inválido.");
        if (u.Rol == Administrador && rol != Administrador) await ExigirOtroAdministradorAsync(id);
        u.Rol = rol; await db.SaveChangesAsync();
    }

    public async Task SetActivoAsync(int id, bool activo)
    {
        var u = await db.Usuarios.FirstAsync(x => x.Id == id);
        if (!activo && u.Rol == Administrador && u.Activo) await ExigirOtroAdministradorAsync(id);
        u.Activo = activo; await db.SaveChangesAsync();
    }

    async Task ExigirOtroAdministradorAsync(int id)
    {
        if (!await db.Usuarios.AnyAsync(x => x.Id != id && x.Rol == Administrador && x.Activo))
            throw new InvalidOperationException("Debe quedar al menos un administrador activo.");
    }
}
