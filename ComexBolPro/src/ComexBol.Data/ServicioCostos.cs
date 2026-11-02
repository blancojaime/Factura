using ComexBol.Core;
using Microsoft.EntityFrameworkCore;
using System.Text.Json;

namespace ComexBol.Data;

/// <summary>Hoja de costos reales vs proyectados de una operación (Módulo 4 de la propuesta).</summary>
public sealed class ServicioCostos(ComexDb db)
{
    public Task<List<CostoOperacion>> ListarAsync(int opId) => db.Costos.AsNoTracking().Where(c => c.OperacionId == opId).OrderBy(c => c.Id).ToListAsync();

    public async Task<CostoOperacion> GuardarAsync(CostoOperacion c)
    {
        if (string.IsNullOrWhiteSpace(c.Concepto)) throw new ArgumentException("Indique el concepto del costo.");
        if (c.ProyectadoBob < 0 || c.RealBob < 0) throw new ArgumentException("Los montos no pueden ser negativos.");
        if (c.Id == 0) db.Costos.Add(c);
        else { var e = await db.Costos.FirstAsync(x => x.Id == c.Id); e.Concepto = c.Concepto.Trim(); e.ProyectadoBob = c.ProyectadoBob; e.RealBob = c.RealBob; e.Nota = c.Nota ?? ""; }
        await db.SaveChangesAsync(); return c;
    }

    public async Task EliminarAsync(int id)
    {
        var c = await db.Costos.FindAsync(id); if (c is null) return;
        db.Costos.Remove(c); await db.SaveChangesAsync();
    }

    /// <summary>Carga como "proyectado" los tributos y costos de la última liquidación (no duplica conceptos ya cargados).</summary>
    public async Task<int> CargarProyectadoDesdeLiquidacionAsync(int opId, TipoCambioTable tc)
    {
        var liq = await db.Liquidaciones.Where(l => l.OperacionId == opId).OrderByDescending(l => l.Version).FirstOrDefaultAsync()
                  ?? throw new InvalidOperationException("Primero calcule la liquidación de la operación.");
        var r = JsonSerializer.Deserialize<LiquidacionResultado>(liq.ResultadoJson)!;
        var op = await db.Operaciones.AsNoTracking().FirstAsync(o => o.Id == opId);
        decimal Bob(decimal v) => v == 0 ? 0 : tc.ABob(new Money(v, op.MonedaFactura));
        var filas = new (string, decimal)[]
        {
            ("Valor de la mercancía (FOB)", r.ValorFobBob), ("Flete y seguro internacionales", Bob(op.Flete) + Bob(op.Seguro)), ("Gravamen arancelario (GA)", r.GA),
            ("Impuesto a los Consumos Específicos (ICE)", r.ICE), ("IEHD", r.IEHD), ("IVA importaciones", r.IVA),
            ("Agencia despachante", 0m), ("Almacenaje / recinto aduanero", 0m), ("Transporte interno", 0m), ("Otros gastos", 0m)
        };
        var existentes = (await ListarAsync(opId)).Select(c => c.Concepto).ToHashSet();
        int n = 0;
        foreach (var (concepto, monto) in filas.Where(f => !existentes.Contains(f.Item1))) { db.Costos.Add(new() { OperacionId = opId, Concepto = concepto, ProyectadoBob = Math.Round(monto, 2) }); n++; }
        await db.SaveChangesAsync(); return n;
    }
}
