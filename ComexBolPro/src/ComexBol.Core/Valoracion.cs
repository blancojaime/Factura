namespace ComexBol.Core;

/// <summary>
/// Cuestionario de descarte del Primer Método (valor de transacción) — Decisión 571 de la CAN (arts. 1 y 8), Reglamento Comunitario (Res. 1684).
/// Cada respuesta «Sí» puede impedir el uso del valor de transacción o exigir un ajuste. La decisión final es del importador/despachante y de la Aduana.
/// </summary>
public sealed record CuestionarioValor(
    bool Vinculacion = false,                 // ¿comprador y vendedor están vinculados?
    bool VinculacionInfluyoPrecio = false,    // ¿la vinculación influyó en el precio? (si no, se debe poder demostrar con valores de prueba)
    bool RestriccionesCesion = false,         // ¿hay restricciones a la cesión o utilización de la mercancía (distintas de las legales o geográficas)?
    bool CondicionesNoCuantificables = false, // ¿el precio depende de condiciones o contraprestaciones cuyo valor no puede determinarse?
    bool ReversionAlVendedor = false,         // ¿parte del producto de la reventa/utilización posterior revierte al vendedor?
    bool Respondido = false);

public sealed record ResultadoDescarte(bool PrimerMetodoAplicable, IReadOnlyList<string> Motivos, IReadOnlyList<string> Observaciones);

/// <summary>Ajustes del Art. 8 del Acuerdo del Valor de la OMC / Decisión 571 (en la moneda de la factura).</summary>
public sealed record AjustesArt8(
    decimal Comisiones = 0m,        // comisiones y corretajes, salvo comisiones de compra
    decimal Envases = 0m,           // envases y embalajes no incluidos en el precio
    decimal Assists = 0m,           // prestaciones: matrices, moldes, planos, diseños realizados fuera del país de importación
    decimal Royalties = 0m,         // cánones y derechos de licencia que el comprador deba pagar como condición de la venta
    decimal Reversiones = 0m,       // parte del producto de reventa/utilización posterior que revierte al vendedor
    decimal OtrosAdiciones = 0m,
    decimal ArmadoPosterior = 0m,   // deducción: construcción, armado, montaje, mantenimiento o asistencia técnica posteriores a la importación
    decimal TransportePosterior = 0m, // deducción: transporte posterior al lugar de importación
    decimal ImpuestosBolivia = 0m)  // deducción: derechos e impuestos aplicables en Bolivia incluidos en el precio
{
    public decimal TotalAdiciones => Comisiones + Envases + Assists + Royalties + Reversiones + OtrosAdiciones;
    public decimal TotalDeducciones => ArmadoPosterior + TransportePosterior + ImpuestosBolivia;
}

public static class Valoracion
{
    public static ResultadoDescarte Descartar(CuestionarioValor c, AjustesArt8? ajustes = null)
    {
        var motivos = new List<string>(); var obs = new List<string>();
        if (!c.Respondido) { obs.Add("Responda el cuestionario para confirmar que el valor de transacción es aplicable."); return new(false, ["Cuestionario sin responder."], obs); }
        if (c.Vinculacion && c.VinculacionInfluyoPrecio) motivos.Add("La vinculación entre comprador y vendedor influyó en el precio (Decisión 571, art. 1.2).");
        if (c.Vinculacion && !c.VinculacionInfluyoPrecio) obs.Add("Existe vinculación pero no influyó en el precio: documente el examen de las circunstancias de la venta o valores de prueba (art. 1.2 b).");
        if (c.RestriccionesCesion) motivos.Add("Hay restricciones a la cesión o utilización de la mercancía distintas de las impuestas por ley o limitaciones geográficas (art. 1.1 a).");
        if (c.CondicionesNoCuantificables) motivos.Add("El precio está sujeto a condiciones o contraprestaciones cuyo valor no puede determinarse (art. 1.1 b).");
        if (c.ReversionAlVendedor)
        {
            if ((ajustes?.Reversiones ?? 0m) <= 0m) obs.Add("Hay reversión al vendedor: declare su importe en «Reversiones» (adición del art. 8.1 d); sin importe determinable no procede el valor de transacción.");
        }
        if (motivos.Count > 0) obs.Add("Corresponde aplicar los métodos secuenciales (2.º valor de mercancías idénticas, 3.º similares, 4.º deductivo, 5.º reconstruido, 6.º último recurso). Este sistema calcula solo con el primer método: consulte a su despachante.");
        return new(motivos.Count == 0, motivos, obs);
    }
}

public enum NivelRiesgoPrecio { SinReferencia, Bajo, Medio, Alto }
public sealed record EvaluacionPrecio(NivelRiesgoPrecio Nivel, decimal PrecioUnitario, decimal? Referencia, decimal? Desviacion, int Muestras, string Mensaje);

/// <summary>Validador previo de inconsistencias (riesgo de duda razonable): compara el precio unitario con la propia historia del importador.</summary>
public static class ValidadorPrecios
{
    public static EvaluacionPrecio Evaluar(decimal precioUnitario, IReadOnlyList<decimal> historicos, decimal tolerancia = 0.30m)
    {
        if (precioUnitario <= 0) return new(NivelRiesgoPrecio.SinReferencia, precioUnitario, null, null, 0, "Indique la cantidad para calcular el precio unitario.");
        if (historicos.Count == 0) return new(NivelRiesgoPrecio.SinReferencia, precioUnitario, null, null, 0, "Sin referencias históricas para esta partida: documente el precio con catálogo o lista del fabricante.");
        var orden = historicos.OrderBy(x => x).ToList(); var n = orden.Count;
        var mediana = n % 2 == 1 ? orden[n / 2] : (orden[n / 2 - 1] + orden[n / 2]) / 2m;
        var desv = (precioUnitario - mediana) / mediana;
        var nivel = Math.Abs(desv) <= tolerancia / 2m ? NivelRiesgoPrecio.Bajo : Math.Abs(desv) <= tolerancia ? NivelRiesgoPrecio.Medio : NivelRiesgoPrecio.Alto;
        var texto = desv < 0 ? "inferior" : "superior";
        var msg = nivel == NivelRiesgoPrecio.Bajo
            ? $"Precio coherente con su historial ({n} operación(es), mediana {mediana:N2})."
            : $"Precio {Math.Abs(desv):P0} {texto} a la mediana histórica ({mediana:N2}, {n} operación(es)): riesgo de duda razonable; prepare factura, pago bancario y catálogo.";
        return new(nivel, precioUnitario, mediana, desv, n, msg);
    }
}
