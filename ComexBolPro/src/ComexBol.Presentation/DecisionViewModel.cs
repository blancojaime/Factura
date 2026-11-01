using System.Collections.ObjectModel;
using System.Globalization;
using System.Text.Json;
using ComexBol.Core;
using ComexBol.Data;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Presentation;

public sealed class EscenarioFila : ObservableObject
{
    string _n = ""; public string Nombre { get => _n; set => Set(ref _n, value); }
    Incoterm _i = Incoterm.FOB; public Incoterm Incoterm { get => _i; set => Set(ref _i, value); }
    decimal _v; public decimal ValorFactura { get => _v; set => Set(ref _v, value); }   // total de la oferta, en la moneda de la factura
    decimal _f; public decimal Flete { get => _f; set => Set(ref _f, value); }
    decimal _s; public decimal Seguro { get => _s; set => Set(ref _s, value); }
    decimal _d; public decimal DeduccionesPostFrontera { get => _d; set => Set(ref _d, value); }
}

public sealed record ResultadoEscenarioFila(string Nombre, string Incoterm, string CifBob, string Tributos, string CostoUnitario, string MargenPct, string Veredicto, bool EsMejor);
public sealed record LineaContraste(string Concepto, string App, string Dim, string Diferencia, string Estado);

/// <summary>Pantallas "Decisión" (escenarios + viabilidad) y "Contraste con DIM real" (prueba P-09).</summary>
public sealed class DecisionViewModel : ObservableObject
{
    static readonly CultureInfo Bo = CultureInfo.GetCultureInfo("es-BO");
    readonly ComexDb _db; readonly Func<int?> _opId; readonly Func<decimal> _tcUsd; readonly Func<DateOnly> _hoy;

    public DecisionViewModel(ComexDb db, Func<int?> operacionId, Func<decimal> tcUsd, Func<DateOnly> hoy)
    {
        _db = db; _opId = operacionId; _tcUsd = tcUsd; _hoy = hoy;
        AgregarEscenarioCmd = new(_ => { Escenarios.Add(new() { Nombre = $"Escenario {Escenarios.Count + 1}" }); return Task.CompletedTask; });
        QuitarEscenarioCmd = new(p => { if (p is EscenarioFila e) Escenarios.Remove(e); return Task.CompletedTask; });
        CompararCmd = new(_ => CompararAsync());
        ContrastarCmd = new(_ => ContrastarAsync());
    }

    public IReadOnlyList<Incoterm> Incoterms { get; } = Enum.GetValues<Incoterm>();
    public ObservableCollection<EscenarioFila> Escenarios { get; } = [];
    public ObservableCollection<ResultadoEscenarioFila> Resultados { get; } = [];
    public ObservableCollection<LineaContraste> Contraste { get; } = [];

    decimal _unidades = 1; public decimal Unidades { get => _unidades; set => Set(ref _unidades, value); }
    decimal _gastos; public decimal GastosLocalesBob { get => _gastos; set => Set(ref _gastos, value); }
    decimal _precio; public decimal PrecioMercadoConIva { get => _precio; set => Set(ref _precio, value); }
    decimal _objetivo = 15; public decimal MargenObjetivoPct { get => _objetivo; set => Set(ref _objetivo, value); }
    string _msg = ""; public string Mensaje { get => _msg; set => Set(ref _msg, value); }

    decimal _dimGa; public decimal DimGA { get => _dimGa; set => Set(ref _dimGa, value); }
    decimal _dimIce; public decimal DimICE { get => _dimIce; set => Set(ref _dimIce, value); }
    decimal _dimIehd; public decimal DimIEHD { get => _dimIehd; set => Set(ref _dimIehd, value); }
    decimal _dimIva; public decimal DimIVA { get => _dimIva; set => Set(ref _dimIva, value); }
    decimal _tol = 1; public decimal ToleranciaBs { get => _tol; set => Set(ref _tol, value); }

    public RelayCommand AgregarEscenarioCmd { get; }
    public RelayCommand QuitarEscenarioCmd { get; }
    public RelayCommand CompararCmd { get; }
    public RelayCommand ContrastarCmd { get; }

    static string F(decimal v) => v.ToString("N2", Bo);

    public async Task CompararAsync()
    {
        Resultados.Clear();
        try
        {
            var id = _opId() ?? throw new InvalidOperationException("Seleccione una operación con ítems.");
            if (Escenarios.Count == 0) throw new InvalidOperationException("Agregue al menos un escenario.");
            if (Unidades <= 0) throw new InvalidOperationException("Las unidades deben ser mayores que cero.");
            var op = await _db.Operaciones.AsNoTracking().Include(o => o.Items).FirstAsync(o => o.Id == id);
            var baseTotal = op.Items.Sum(i => i.ValorFactura);
            if (baseTotal <= 0) throw new InvalidOperationException("La operación no tiene ítems con valor.");
            var tc = new TipoCambioTable(_hoy(), new Dictionary<string, decimal> { [op.MonedaFactura] = _tcUsd() });
            Money? M(decimal v) => v == 0 ? null : new Money(v, op.MonedaFactura);

            var lista = Escenarios.Select(e =>
            {
                var k = e.ValorFactura / baseTotal;      // los ítems se escalan proporcionalmente a la oferta
                var items = op.Items.OrderBy(i => i.Numero).Select(i => i.ToCore() with { ValorFactura = i.ValorFactura * k }).ToList();
                return new Escenario(e.Nombre, new(e.Incoterm, op.MonedaFactura, items, null, M(e.Flete), M(e.Seguro), null, M(e.DeduccionesPostFrontera), op.OtrasErogacionesBob));
            }).ToList();

            var res = ComexBol.Core.Escenarios.Comparar(lista, tc, GastosLocalesBob, Unidades, PrecioMercadoConIva, MargenObjetivoPct / 100m);
            var mejor = res.First().Nombre;      // ordenado por costo unitario
            foreach (var r in res)
                Resultados.Add(new(r.Nombre, Escenarios.First(e => e.Nombre == r.Nombre).Incoterm.ToString(), F(r.Liquidacion.CifBob), F(r.Liquidacion.TotalTributos),
                    F(r.Viabilidad.CostoUnitario), r.Viabilidad.MargenPct.ToString("P1", Bo), r.Veredicto, r.Nombre == mejor));
            Mensaje = PrecioMercadoConIva <= 0 ? "Ingrese el precio de mercado para ver margen y veredicto." : $"Menor costo unitario: {mejor}";
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException) { Mensaje = "⚠ " + ex.Message; }
    }

    /// <summary>Compara la última liquidación guardada con los tributos que la Aduana efectivamente liquidó en la DIM.</summary>
    public async Task ContrastarAsync()
    {
        Contraste.Clear();
        try
        {
            var id = _opId() ?? throw new InvalidOperationException("Seleccione una operación liquidada.");
            var liq = await _db.Liquidaciones.Where(l => l.OperacionId == id).OrderByDescending(l => l.Version).FirstOrDefaultAsync()
                      ?? throw new InvalidOperationException("Primero calcule la liquidación de la operación.");
            var r = JsonSerializer.Deserialize<LiquidacionResultado>(liq.ResultadoJson)!;
            var dimTotal = DimGA + DimICE + DimIEHD + DimIVA;
            var filas = new (string, decimal, decimal)[] { ("Gravamen arancelario", r.GA, DimGA), ("ICE", r.ICE, DimICE), ("IEHD", r.IEHD, DimIEHD), ("IVA", r.IVA, DimIVA), ("TOTAL", r.TotalTributos, dimTotal) };
            int revisar = 0;
            foreach (var (c, app, dim) in filas)
            {
                var d = app - dim; var ok = Math.Abs(d) <= ToleranciaBs; if (!ok) revisar++;
                Contraste.Add(new(c, F(app), F(dim), F(d), ok ? "OK" : "REVISAR"));
            }
            Mensaje = revisar == 0 ? $"Coincide con la DIM (tolerancia Bs {F(ToleranciaBs)})." : $"{revisar} diferencia(s): revise parámetros (IVA efectivo, base del ICE, redondeo, valor en aduana).";
            _db.Bitacora.Add(new() { OperacionId = id, Fecha = DateTime.Now, Categoria = "Contraste DIM", Detalle = $"Liquidación v{liq.Version} vs DIM: total app {F(r.TotalTributos)} / DIM {F(dimTotal)} → {(revisar == 0 ? "coincide" : "diferencias")}." });
            await _db.SaveChangesAsync();
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException) { Mensaje = "⚠ " + ex.Message; }
    }
}
