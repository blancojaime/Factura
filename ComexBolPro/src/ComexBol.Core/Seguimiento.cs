namespace ComexBol.Core;

public static class Seguimiento
{
    /// <summary>Semáforo de una etapa a una fecha dada. Alerta = faltan ≤ diasAlerta para el fin planificado.</summary>
    public static Semaforo Evaluar(DateOnly inicioPlan, DateOnly finPlan, DateOnly? finReal, DateOnly hoy, int diasAlerta = 2)
    {
        if (finReal is not null) return Semaforo.Cumplido;
        if (hoy > finPlan) return Semaforo.Vencido;
        if (finPlan.DayNumber - hoy.DayNumber <= diasAlerta) return Semaforo.Alerta;
        return hoy >= inicioPlan ? Semaforo.EnCurso : Semaforo.Pendiente;
    }
}

public sealed record Escenario(string Nombre, OperacionImportacion Operacion);

public sealed record ResultadoEscenario(
    string Nombre, LiquidacionResultado Liquidacion, ViabilidadImportacion Viabilidad, string Veredicto);

public static class Escenarios
{
    /// <summary>
    /// Compara escenarios (p. ej. FOB vs CIF vs DAP) y ordena por costo unitario.
    /// Veredicto: "Viable" si margen ≥ margenObjetivo, "Ajustado" si ≥ 0, "No viable" si es negativo.
    /// </summary>
    public static IReadOnlyList<ResultadoEscenario> Comparar(
        IEnumerable<Escenario> escenarios, TipoCambioTable tc, decimal gastosLocalesBob, decimal unidades,
        decimal precioMercadoConIva, decimal margenObjetivo = 0.15m, ParametrosTributarios? p = null)
        => escenarios.Select(e =>
        {
            var liq = CalculadoraTributaria.Calcular(e.Operacion, tc, p);
            var v = Viabilidad.Importacion(liq, gastosLocalesBob, unidades, precioMercadoConIva);
            var ver = v.MargenPct >= margenObjetivo ? "Viable" : v.MargenPct >= 0 ? "Ajustado" : "No viable";
            return new ResultadoEscenario(e.Nombre, liq, v, ver);
        }).OrderBy(r => r.Viabilidad.CostoUnitario).ToList();
}
