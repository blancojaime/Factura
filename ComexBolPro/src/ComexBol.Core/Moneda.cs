namespace ComexBol.Core;

/// <summary>Monto en una moneda ISO (USD, EUR, BOB...).</summary>
public sealed record Money(decimal Monto, string Moneda = "USD")
{
    public static Money Cero(string moneda = "USD") => new(0m, moneda);
}

/// <summary>
/// Tabla de tipos de cambio expresados como "BOB por 1 unidad de moneda".
/// El valor oficial (BCB, venta) NO está codificado: lo carga el usuario o el
/// sincronizador, y se guarda con su fecha para auditoría.
/// </summary>
public sealed class TipoCambioTable
{
    private readonly Dictionary<string, decimal> _bobPor = new(StringComparer.OrdinalIgnoreCase) { ["BOB"] = 1m };

    public DateOnly Fecha { get; }
    public TipoCambioTable(DateOnly fecha, IDictionary<string, decimal> bobPorMoneda)
    {
        Fecha = fecha;
        foreach (var (m, v) in bobPorMoneda)
        {
            if (v <= 0) throw new ArgumentException($"Tipo de cambio inválido para {m}: {v}");
            _bobPor[m] = v;
        }
    }

    public decimal ABob(Money m) =>
        _bobPor.TryGetValue(m.Moneda, out var tc)
            ? m.Monto * tc
            : throw new InvalidOperationException($"Sin tipo de cambio para {m.Moneda} al {Fecha}");
}

public static class Ufv
{
    /// <summary>Convierte Bs a UFV con el valor de la UFV de la fecha (dato publicado por el BCB).</summary>
    public static decimal DeBob(decimal bob, decimal valorUfvEnBob)
        => valorUfvEnBob > 0 ? bob / valorUfvEnBob : throw new ArgumentOutOfRangeException(nameof(valorUfvEnBob));
}
