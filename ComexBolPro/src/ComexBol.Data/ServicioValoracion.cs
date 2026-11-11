using ComexBol.Core;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

public sealed record EvaluacionItemPrecio(int Numero, string Partida, string Descripcion, EvaluacionPrecio Evaluacion);

/// <summary>Valoración aduanera (DAV, Decisión 571): cuestionario de descarte, ajustes del Art. 8, validador de precios y costeo nacionalizado.</summary>
public sealed class ServicioValoracion(ComexDb db)
{
    public string Usuario { get; set; } = "";

    void Log(int opId, string detalle) => db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = "Valoración", Detalle = detalle, Usuario = Usuario });

    public async Task GuardarValoracionAsync(int opId, CuestionarioValor c, AjustesArt8 a, string notas)
    {
        foreach (var (v, n) in new[] { (a.Comisiones, "comisiones"), (a.Envases, "envases"), (a.Assists, "assists"), (a.Royalties, "royalties"), (a.Reversiones, "reversiones"), (a.OtrosAdiciones, "otras adiciones"),
                                       (a.ArmadoPosterior, "armado posterior"), (a.TransportePosterior, "transporte posterior"), (a.ImpuestosBolivia, "impuestos en Bolivia") })
            if (v < 0) throw new ArgumentException($"El monto de {n} no puede ser negativo.");
        if (c.VinculacionInfluyoPrecio && !c.Vinculacion) throw new ArgumentException("Indique primero que existe vinculación entre comprador y vendedor.");
        var op = await db.Operaciones.FirstAsync(o => o.Id == opId);
        op.CuestionarioRespondido = true; op.Vinculacion = c.Vinculacion; op.VinculacionInfluyoPrecio = c.Vinculacion && c.VinculacionInfluyoPrecio;
        op.RestriccionesCesion = c.RestriccionesCesion; op.CondicionesNoCuantificables = c.CondicionesNoCuantificables; op.ReversionAlVendedor = c.ReversionAlVendedor;
        op.AdComisiones = a.Comisiones; op.AdEnvases = a.Envases; op.AdAssists = a.Assists; op.AdRoyalties = a.Royalties; op.AdReversiones = a.Reversiones; op.AdOtros = a.OtrosAdiciones;
        op.DedArmadoPosterior = a.ArmadoPosterior; op.DedTransportePosterior = a.TransportePosterior; op.DedImpuestosBolivia = a.ImpuestosBolivia; op.NotasValoracion = notas ?? "";
        var r = Valoracion.Descartar(op.Cuestionario(), op.Ajustes());
        Log(opId, $"DAV: {(r.PrimerMetodoAplicable ? "valor de transacción aplicable" : "valor de transacción NO aplicable")}; adiciones Art. 8 {a.TotalAdiciones:N2}, deducciones {a.TotalDeducciones:N2} {op.MonedaFactura}. Recalcule la liquidación.");
        await db.SaveChangesAsync();
    }

    /// <summary>Compara el precio unitario de cada ítem con el de otras operaciones del mismo importador para la misma partida.</summary>
    public async Task<IReadOnlyList<EvaluacionItemPrecio>> ValidarPreciosAsync(int opId, decimal tolerancia)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).FirstAsync(o => o.Id == opId);
        var res = new List<EvaluacionItemPrecio>();
        foreach (var it in op.Items.OrderBy(i => i.Numero))
        {
            var unit = it.Cantidad > 0 ? it.ValorFactura / it.Cantidad : 0m;
            var mismaMoneda = db.Operaciones.Where(o => o.MonedaFactura == op.MonedaFactura && o.Id != opId).Select(o => o.Id);
            var otros = await db.Items.AsNoTracking().Where(x => x.CodigoNandina == it.CodigoNandina && x.Cantidad > 0 && mismaMoneda.Contains(x.OperacionId))
                .Select(x => x.ValorFactura / x.Cantidad).ToListAsync();
            res.Add(new(it.Numero, it.CodigoNandina, it.Descripcion, ValidadorPrecios.Evaluar(unit, otros, tolerancia)));
        }
        return res;
    }

    /// <summary>Costeo nacionalizado a partir de la última liquidación y los gastos locales de la operación.</summary>
    public async Task<CosteoResultado?> CostearAsync(int opId, bool ivaRecuperable)
    {
        var op = await db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Liquidaciones).FirstAsync(o => o.Id == opId);
        var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault(); if (ult is null) return null;
        var r = System.Text.Json.JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson)!;
        var cant = r.Items.Select(i => op.Items.FirstOrDefault(x => x.Numero == i.Numero)?.Cantidad ?? 0m).ToList();
        return Costeo.Calcular(r, cant, op.Gastos(), ivaRecuperable);
    }

    public async Task GuardarGastosAsync(int opId, GastosLocales g, int diasAlmacenaje)
    {
        if (g.HonorariosAgencia < 0 || g.Almacenaje < 0 || g.TransporteInterno < 0 || g.Otros < 0) throw new ArgumentException("Los gastos no pueden ser negativos.");
        var op = await db.Operaciones.FirstAsync(o => o.Id == opId);
        op.GastoHonorariosAgencia = g.HonorariosAgencia; op.GastoAlmacenaje = g.Almacenaje; op.GastoTransporteInterno = g.TransporteInterno; op.GastoOtros = g.Otros; op.DiasAlmacenaje = Math.Max(0, diasAlmacenaje);
        Log(opId, $"Gastos locales de despacho Bs {g.Total:N2} (agencia {g.HonorariosAgencia:N2}, almacén {g.Almacenaje:N2}, transporte {g.TransporteInterno:N2}, otros {g.Otros:N2}).");
        await db.SaveChangesAsync();
    }
}
