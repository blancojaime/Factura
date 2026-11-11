using System.Collections.ObjectModel;
using System.Globalization;
using System.Text.Json;
using ComexBol.Core;
using ComexBol.Data;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Presentation;

/// <summary>Base de los módulos por operación: acceso serializado a la base y manejo de avisos.</summary>
public abstract class ModuloOperacionVm(ComexDb db, Func<int?> operacionId) : ObservableObject
{
    protected readonly ComexDb Db = db; protected readonly Func<int?> OpId = operacionId;
    protected static CultureInfo Bo => Formato.Bo;
    protected static string F(decimal v) => v.ToString("N2", Bo);
    string _msg = ""; public string Mensaje { get => _msg; set => Set(ref _msg, value); }
    public bool HayOperacion => OpId() is not null;

    protected Task Seguro(Func<Task> accion) => DbGate.EjecutarAsync(async () =>
    {
        try { await accion(); }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or DbUpdateException) { Mensaje = "AVISO: " + ex.Message; }
    });
}

// ===================================================================== LIQUIDACIÓN DETALLADA Y COSTEO
public sealed record FilaTributoItem(string N, string Partida, string Fob, string Cif, string GA, string ICE, string IEHD, string IVA, string Total);
public sealed record FilaCosteo(string N, string Partida, string Cantidad, string Cif, string Tributos, string Gastos, string Costo, string Factor, string Unitario);

public sealed class LiquidacionDetalleViewModel : ModuloOperacionVm
{
    readonly ServicioValoracion _val; readonly ServicioConfiguracion _cfg; readonly ServicioOperaciones _ops;
    public LiquidacionDetalleViewModel(ComexDb db, Func<int?> opId) : base(db, opId)
    {
        _val = new(db); _cfg = new(db); _ops = new(db);
        GuardarGastosCmd = new(_ => GuardarGastosAsync());
        EstimarAlmacenajeCmd = new(_ => EstimarAlmacenajeAsync());
    }

    public ObservableCollection<LineaLiquidacion> Desglose { get; } = [];
    public ObservableCollection<FilaTributoItem> Items { get; } = [];
    public ObservableCollection<string> Pasos { get; } = [];
    public ObservableCollection<FilaCosteo> Costeo { get; } = [];
    string _resumen = ""; public string ResumenCosteo { get => _resumen; set => Set(ref _resumen, value); }
    string _flujo = ""; public string FlujoCaja { get => _flujo; set => Set(ref _flujo, value); }
    bool _hay; public bool HayLiquidacion { get => _hay; set => Set(ref _hay, value); }

    decimal _hon; public decimal Honorarios { get => _hon; set => Set(ref _hon, value); }
    decimal _alm; public decimal Almacenaje { get => _alm; set => Set(ref _alm, value); }
    decimal _tra; public decimal TransporteInterno { get => _tra; set => Set(ref _tra, value); }
    decimal _otr; public decimal OtrosGastos { get => _otr; set => Set(ref _otr, value); }
    int _dias; public int DiasAlmacenaje { get => _dias; set => Set(ref _dias, value); }
    public RelayCommand GuardarGastosCmd { get; }
    public RelayCommand EstimarAlmacenajeCmd { get; }

    public Task GuardarGastosAsync() => Seguro(async () =>
    {
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        await _val.GuardarGastosAsync(id, new(Honorarios, Almacenaje, TransporteInterno, OtrosGastos), DiasAlmacenaje);
        await CargarAsync(); Mensaje = "Gastos de despacho guardados; el costo nacionalizado se actualizó.";
    });

    /// <summary>Propone el almacenaje con la tarifa configurada del recinto; el usuario puede corregirlo.</summary>
    public Task EstimarAlmacenajeAsync() => Seguro(async () =>
    {
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        var a = await _cfg.ObtenerAjustesAsync();
        if (a.AlmacenTarifaBsTonDia <= 0) throw new InvalidOperationException("Configure la tarifa de almacenaje (Bs por tonelada y día) en Configuración → Parámetros tributarios.");
        var peso = (await Db.Items.AsNoTracking().Where(i => i.OperacionId == id).Select(i => i.PesoBrutoKg).ToListAsync()).Sum();
        Almacenaje = Costeo_.EstimarAlmacenaje(peso, DiasAlmacenaje, a.AlmacenDiasLibres, a.AlmacenTarifaBsTonDia);
        Mensaje = $"Almacenaje estimado: {DiasAlmacenaje} días ({a.AlmacenDiasLibres} libres) × {F(peso / 1000m)} t × Bs {F(a.AlmacenTarifaBsTonDia)}. Verifique con la tarifa de su recinto.";
    });
    static class Costeo_ { public static decimal EstimarAlmacenaje(decimal p, int d, int l, decimal t) => ComexBol.Core.Costeo.EstimarAlmacenaje(p, d, l, t); }

    public async Task CargarAsync()
    {
        Desglose.Clear(); Items.Clear(); Pasos.Clear(); Costeo.Clear(); ResumenCosteo = FlujoCaja = ""; HayLiquidacion = false;
        var id = OpId(); if (id is null) return;
        await Seguro(async () =>
        {
            var op = await Db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Liquidaciones).FirstAsync(o => o.Id == id);
            Honorarios = op.GastoHonorariosAgencia; Almacenaje = op.GastoAlmacenaje; TransporteInterno = op.GastoTransporteInterno; OtrosGastos = op.GastoOtros; DiasAlmacenaje = op.DiasAlmacenaje;
            var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault(); if (ult is null) return;
            HayLiquidacion = true;
            var r = JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson)!;
            if (r.Desglose is not null) foreach (var l in r.Desglose) Desglose.Add(new(l.Concepto + (string.IsNullOrEmpty(l.Nota) ? "" : $"  ·  {l.Nota}"), F(l.Bob), l.Concepto.StartsWith("Valor en aduana")));
            foreach (var i in r.Items) Items.Add(new(i.Numero.ToString(), i.CodigoArancelario, F(i.ValorFobBob), F(i.CifBob), F(i.GA), F(i.ICE), F(i.IEHD), F(i.IVA), F(i.TotalTributos)));
            Items.Add(new("", "TOTAL", F(r.ValorFobBob), F(r.CifBob), F(r.GA), F(r.ICE), F(r.IEHD), F(r.IVA), F(r.TotalTributos)));

            // Pasos de la fórmula: se reconstruye la operación con los mismos datos del cálculo guardado
            var p = JsonSerializer.Deserialize<ParametrosTributarios>(ult.ParametrosJson) ?? new();
            Money? M(decimal v) => v == 0 ? null : new Money(v, op.MonedaFactura);
            var core = new OperacionImportacion(op.Incoterm, op.MonedaFactura, op.Items.OrderBy(i => i.Numero).Select(i => i.ToCore()).ToList(), M(op.GastosOrigen), M(op.Flete), M(op.Seguro), M(op.OtrosGastosFrontera), M(op.Deducciones), op.OtrasErogacionesBob);
            foreach (var s in ExplicadorLiquidacion.Pasos(core, r, p, Bo)) Pasos.Add(s);

            var aj = await _cfg.ObtenerAjustesAsync();
            var c = await _val.CostearAsync(id.Value, aj.IvaRecuperable);
            if (c is not null)
            {
                foreach (var x in c.Items) Costeo.Add(new(x.Numero.ToString(), x.Codigo, x.Cantidad > 0 ? x.Cantidad.ToString("0.##", Bo) : "—", F(x.CifBob), F(x.TributosNoRecuperables), F(x.GastosProrrateados), F(x.CostoNacionalizadoBob), x.Factor.ToString("0.0000", Bo), x.Cantidad > 0 ? F(x.CostoUnitarioBob) : "indique la cantidad"));
                ResumenCosteo = $"Costo nacionalizado Bs {F(c.CostoTotalBob)} · factor de importación {c.FactorGlobal.ToString("0.0000", Bo)} (por cada Bs de FOB) · IVA como crédito fiscal Bs {F(c.IvaCreditoFiscalTotal)}" + (aj.IvaRecuperable ? "" : " (IVA tratado como costo)");
                FlujoCaja = $"Flujo de caja requerido: tributos Bs {F(r.TotalTributos)} + gastos de despacho Bs {F(c.GastosLocalesBob)} = Bs {F(c.CashFlowRequeridoBob)}";
            }
        });
    }
}

// ===================================================================== VALORACIÓN ADUANERA (DAV)
public sealed record FilaPrecio(string N, string Partida, string Descripcion, string PrecioUnitario, string Referencia, string Desviacion, string Riesgo, string Mensaje, string ColorHex);

public sealed class ValoracionViewModel : ModuloOperacionVm
{
    readonly ServicioValoracion _val; readonly ServicioConfiguracion _cfg;
    public ValoracionViewModel(ComexDb db, Func<int?> opId) : base(db, opId)
    {
        _val = new(db); _cfg = new(db);
        GuardarCmd = new(_ => GuardarAsync()); ValidarPreciosCmd = new(_ => ValidarPreciosAsync());
    }
    public string Usuario { set => _val.Usuario = value; }

    bool _vinc; public bool Vinculacion { get => _vinc; set { if (Set(ref _vinc, value) && !value) VinculacionInfluyo = false; PropiedadCambiada(nameof(PuedeInfluir)); } }
    public bool PuedeInfluir => Vinculacion;
    bool _infl; public bool VinculacionInfluyo { get => _infl; set => Set(ref _infl, value); }
    bool _rest; public bool Restricciones { get => _rest; set => Set(ref _rest, value); }
    bool _cond; public bool Condiciones { get => _cond; set => Set(ref _cond, value); }
    bool _rev; public bool Reversion { get => _rev; set => Set(ref _rev, value); }
    decimal _com; public decimal Comisiones { get => _com; set => Set(ref _com, value); }
    decimal _env; public decimal Envases { get => _env; set => Set(ref _env, value); }
    decimal _ass; public decimal Assists { get => _ass; set => Set(ref _ass, value); }
    decimal _roy; public decimal Royalties { get => _roy; set => Set(ref _roy, value); }
    decimal _rv; public decimal Reversiones { get => _rv; set => Set(ref _rv, value); }
    decimal _otr; public decimal OtrasAdiciones { get => _otr; set => Set(ref _otr, value); }
    decimal _arm; public decimal ArmadoPosterior { get => _arm; set => Set(ref _arm, value); }
    decimal _trp; public decimal TransportePosterior { get => _trp; set => Set(ref _trp, value); }
    decimal _imp; public decimal ImpuestosBolivia { get => _imp; set => Set(ref _imp, value); }
    string _notas = ""; public string Notas { get => _notas; set => Set(ref _notas, value); }

    string _res = ""; public string ResultadoDescarte { get => _res; set => Set(ref _res, value); }
    string _resColor = "#9AA3AD"; public string ResultadoColor { get => _resColor; set => Set(ref _resColor, value); }
    string _tot = ""; public string TotalesAjustes { get => _tot; set => Set(ref _tot, value); }
    public ObservableCollection<string> Observaciones { get; } = [];
    public ObservableCollection<FilaPrecio> Precios { get; } = [];
    public RelayCommand GuardarCmd { get; }
    public RelayCommand ValidarPreciosCmd { get; }

    CuestionarioValor Cuestionario(bool respondido = true) => new(Vinculacion, VinculacionInfluyo, Restricciones, Condiciones, Reversion, respondido);
    AjustesArt8 Ajustes() => new(Comisiones, Envases, Assists, Royalties, Reversiones, OtrasAdiciones, ArmadoPosterior, TransportePosterior, ImpuestosBolivia);

    void Evaluar(bool respondido)
    {
        var r = Valoracion.Descartar(Cuestionario(respondido), Ajustes());
        Observaciones.Clear(); foreach (var m in r.Motivos.Concat(r.Observaciones)) Observaciones.Add(m);
        ResultadoDescarte = !respondido ? "Cuestionario pendiente" : r.PrimerMetodoAplicable ? "Valor de transacción APLICABLE (Primer Método)" : "Valor de transacción NO aplicable: use métodos secuenciales";
        ResultadoColor = !respondido ? "#9AA3AD" : r.PrimerMetodoAplicable ? "#3CB07C" : "#D9534F";
        var a = Ajustes(); TotalesAjustes = $"Adiciones {F(a.TotalAdiciones)} − deducciones {F(a.TotalDeducciones)} = ajuste neto {F(a.TotalAdiciones - a.TotalDeducciones)} (moneda de la factura)";
    }

    public Task GuardarAsync() => Seguro(async () =>
    {
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        await _val.GuardarValoracionAsync(id, Cuestionario(), Ajustes(), Notas);
        Evaluar(true); Mensaje = "Valoración guardada. Pulse «Calcular (F5)» en Mercancías para que los ajustes del Art. 8 entren al valor en aduana.";
    });

    public Task ValidarPreciosAsync() => Seguro(async () =>
    {
        Precios.Clear();
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        var aj = await _cfg.ObtenerAjustesAsync();
        foreach (var e in await _val.ValidarPreciosAsync(id, aj.TolerancePrecio))
        {
            var v = e.Evaluacion;
            var color = v.Nivel switch { NivelRiesgoPrecio.Bajo => "#3CB07C", NivelRiesgoPrecio.Medio => "#F0A53A", NivelRiesgoPrecio.Alto => "#D9534F", _ => "#9AA3AD" };
            Precios.Add(new(e.Numero.ToString(), e.Partida, e.Descripcion.Length > 40 ? e.Descripcion[..40] + "…" : e.Descripcion, v.PrecioUnitario > 0 ? F(v.PrecioUnitario) : "—",
                v.Referencia is null ? "—" : F(v.Referencia.Value), v.Desviacion is null ? "—" : v.Desviacion.Value.ToString("P1", Bo), v.Nivel switch { NivelRiesgoPrecio.SinReferencia => "Sin referencia", var n => n.ToString() }, v.Mensaje, color));
        }
        Mensaje = Precios.Count == 0 ? "La operación no tiene ítems." : "Comparación con su historial de operaciones (misma partida y moneda).";
    });

    public async Task CargarAsync()
    {
        Precios.Clear(); Observaciones.Clear(); Mensaje = "";
        var id = OpId();
        if (id is null) { ResultadoDescarte = "Seleccione una operación"; ResultadoColor = "#9AA3AD"; TotalesAjustes = ""; return; }
        await Seguro(async () =>
        {
            var op = await Db.Operaciones.AsNoTracking().FirstAsync(o => o.Id == id);
            Vinculacion = op.Vinculacion; VinculacionInfluyo = op.VinculacionInfluyoPrecio; Restricciones = op.RestriccionesCesion; Condiciones = op.CondicionesNoCuantificables; Reversion = op.ReversionAlVendedor;
            Comisiones = op.AdComisiones; Envases = op.AdEnvases; Assists = op.AdAssists; Royalties = op.AdRoyalties; Reversiones = op.AdReversiones; OtrasAdiciones = op.AdOtros;
            ArmadoPosterior = op.DedArmadoPosterior; TransportePosterior = op.DedTransportePosterior; ImpuestosBolivia = op.DedImpuestosBolivia; Notas = op.NotasValoracion;
            Evaluar(op.CuestionarioRespondido);
        });
    }
}

// ===================================================================== DESPACHO ADUANERO (DIM)
public sealed record FilaHallazgo(string Nivel, string Texto, string ColorHex);
public sealed class FilaTareaDespacho(int id, string texto, bool hecha, Func<int, bool, Task> alCambiar) : ObservableObject
{
    public int Id { get; } = id; public string Texto { get; } = texto;
    bool _h = hecha; public bool Hecha { get => _h; set { if (Set(ref _h, value)) _ = alCambiar(Id, value); } }
}

public sealed class DespachoViewModel : ModuloOperacionVm
{
    readonly ServicioDespacho _srv; readonly ServicioConfiguracion _cfg; bool _cargando;
    public DespachoViewModel(ComexDb db, Func<int?> opId) : base(db, opId)
    {
        _srv = new(db); _cfg = new(db);
        GuardarCmd = new(_ => GuardarAsync()); ValidarCmd = new(_ => ValidarAsync()); AsignarCanalCmd = new(_ => AsignarCanalAsync()); LevanteCmd = new(_ => LevanteAsync());
    }
    public string Usuario { set => _srv.Usuario = value; }
    public IReadOnlyList<string> Tipos { get; } = Despacho.Tipos;
    public IReadOnlyList<string> Regimenes { get; } = Despacho.Regimenes;
    public IReadOnlyList<string> Modalidades { get; } = Despacho.Modalidades;
    public IReadOnlyList<string> Canales { get; } = Despacho.Canales;

    string _tipo = "General"; public string TipoDespacho { get => _tipo; set => Set(ref _tipo, value); }
    string _reg = Despacho.Regimenes[0]; public string Regimen { get => _reg; set => Set(ref _reg, value); }
    string _ai = ""; public string AduanaIngreso { get => _ai; set => Set(ref _ai, value); }
    string _ad = ""; public string AduanaDestino { get => _ad; set => Set(ref _ad, value); }
    string _cd = ""; public string CodigoDeclarante { get => _cd; set => Set(ref _cd, value); }
    string _mod = ""; public string Modalidad { get => _mod; set { if (Set(ref _mod, value)) { PropiedadCambiada(nameof(EtiquetaEmbarque)); PropiedadCambiada(nameof(EtiquetaManifiesto)); } } }
    public string EtiquetaEmbarque => $"N.º de {Despacho.DocumentoEmbarque(Modalidad)}";
    public string EtiquetaManifiesto => $"N.º de {Despacho.DocumentoManifiesto(Modalidad)}";
    string _nde = ""; public string NroDocEmbarque { get => _nde; set => Set(ref _nde, value); }
    string _nm = ""; public string NroManifiesto { get => _nm; set => Set(ref _nm, value); }
    int _b; public int Bultos { get => _b; set => Set(ref _b, value); }
    decimal _pm; public decimal PesoManifiesto { get => _pm; set => Set(ref _pm, value); }
    string _dav = ""; public string NroDav { get => _dav; set => Set(ref _dav, value); }
    string _dim = ""; public string NroDim { get => _dim; set => Set(ref _dim, value); }

    string _canal = "Sin asignar"; public string Canal { get => _canal; set { if (Set(ref _canal, value)) { PropiedadCambiada(nameof(ColorCanal)); } } }
    public string ColorCanal => Canal switch { "Verde" => "#3CB07C", "Amarillo" => "#F0A53A", "Rojo" => "#D9534F", _ => "#9AA3AD" };
    string _obs = ""; public string ObservacionAduana { get => _obs; set => Set(ref _obs, value); }
    DateTime? _lev; public DateTime? FechaLevante { get => _lev; set => Set(ref _lev, value); }
    string _estado = ""; public string EstadoDim { get => _estado; set => Set(ref _estado, value); }
    string _estadoColor = "#9AA3AD"; public string EstadoDimColor { get => _estadoColor; set => Set(ref _estadoColor, value); }

    public ObservableCollection<FilaHallazgo> Hallazgos { get; } = [];
    public ObservableCollection<FilaTareaDespacho> Tareas { get; } = [];
    public RelayCommand GuardarCmd { get; }
    public RelayCommand ValidarCmd { get; }
    public RelayCommand AsignarCanalCmd { get; }
    public RelayCommand LevanteCmd { get; }

    DatosDespacho Datos() => new(TipoDespacho, Regimen, AduanaIngreso, AduanaDestino, CodigoDeclarante, Modalidad, NroDocEmbarque, Bultos, PesoManifiesto, NroManifiesto, NroDav, NroDim);

    public Task GuardarAsync() => Seguro(async () =>
    {
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        await _srv.GuardarDatosAsync(id, Datos()); await ValidarAsync(); Mensaje = "Datos de la DIM guardados.";
    });

    public Task ValidarAsync() => Seguro(async () =>
    {
        Hallazgos.Clear();
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        var tol = (await _cfg.ObtenerAjustesAsync()).TolerancePeso;
        await _srv.GuardarDatosAsync(id, Datos());       // valida lo que el usuario ve en pantalla
        var h = await _srv.ValidarAsync(id, tol);
        foreach (var x in h) Hallazgos.Add(new(x.Nivel switch { NivelHallazgo.Ok => "OK", NivelHallazgo.Alerta => "ALERTA", _ => "ERROR" }, x.Texto,
            x.Nivel switch { NivelHallazgo.Ok => "#3CB07C", NivelHallazgo.Alerta => "#F0A53A", _ => "#D9534F" }));
        var err = h.Count(x => x.Nivel == NivelHallazgo.Error); var al = h.Count(x => x.Nivel == NivelHallazgo.Alerta);
        EstadoDim = err > 0 ? $"{err} error(es) y {al} alerta(s): corrija antes de declarar" : al > 0 ? $"{al} alerta(s): revise antes de declarar" : "DIM sin observaciones";
        EstadoDimColor = err > 0 ? "#D9534F" : al > 0 ? "#F0A53A" : "#3CB07C";
    });

    public Task AsignarCanalAsync() => Seguro(async () =>
    {
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        await _srv.AsignarCanalAsync(id, Canal, ObservacionAduana); await CargarTareasAsync(id);
        Mensaje = Canal == "Sin asignar" ? "Canal sin asignar." : $"Canal {Canal}: complete la lista de control.";
    });

    public Task LevanteAsync() => Seguro(async () =>
    {
        var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
        var f = FechaLevante ?? throw new InvalidOperationException("Indique la fecha del levante.");
        await _srv.RegistrarLevanteAsync(id, DateOnly.FromDateTime(f)); Mensaje = $"Levante registrado el {f:dd/MM/yyyy}.";
    });

    async Task CargarTareasAsync(int id)
    {
        Tareas.Clear();
        foreach (var t in await _srv.TareasAsync(id)) Tareas.Add(new(t.Id, t.Texto, t.Hecha, (tid, h) => Seguro(() => _srv.MarcarTareaAsync(tid, h))));
    }

    /// <summary>Genera el borrador de descargos (texto) para que la ventana lo guarde.</summary>
    public async Task<string?> GenerarDescargoAsync(string observacion)
    {
        string? texto = null;
        await Seguro(async () =>
        {
            var id = OpId() ?? throw new InvalidOperationException("Seleccione una operación.");
            texto = await _srv.GenerarDescargoAsync(id, observacion, Despacho.PruebasDescargo);
            Mensaje = "Borrador de descargos generado: revíselo con su despachante.";
        });
        return texto;
    }

    public async Task CargarAsync()
    {
        Hallazgos.Clear(); Tareas.Clear(); Mensaje = ""; EstadoDim = ""; EstadoDimColor = "#9AA3AD";
        var id = OpId(); if (id is null) return;
        await Seguro(async () =>
        {
            var op = await Db.Operaciones.AsNoTracking().FirstAsync(o => o.Id == id);
            TipoDespacho = op.TipoDespacho; Regimen = op.Regimen; AduanaIngreso = op.AduanaIngreso; AduanaDestino = op.AduanaDestino; CodigoDeclarante = op.CodigoDeclarante; Modalidad = op.ModalidadTransporte;
            NroDocEmbarque = op.NroDocEmbarque; NroManifiesto = op.NroManifiesto; Bultos = op.Bultos; PesoManifiesto = op.PesoBrutoManifiestoKg; NroDav = op.NroDav; NroDim = op.NroDim;
            Canal = op.Canal; ObservacionAduana = op.ObservacionAduana; FechaLevante = op.FechaLevante?.ToDateTime(TimeOnly.MinValue);
            await CargarTareasAsync(id.Value);
        });
    }
}
