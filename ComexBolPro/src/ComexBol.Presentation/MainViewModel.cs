using System.Collections.ObjectModel;
using System.Globalization;
using ComexBol.Core;
using ComexBol.Data;
using ComexBol.Documentos;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Presentation;

public sealed record EtapaFila(string Codigo, string Nombre, string Plan, string Real, Semaforo Semaforo, string ColorHex, bool EsCritica, bool EsHitoLegal);
public sealed record ItemFila(int Numero, string Partida, string Descripcion, string Valor, string GA);
public sealed record LineaLiquidacion(string Concepto, string Monto, bool Destacada = false);
public sealed class CampoPropuesto(string clave, string nombre, string valor, string confianza, string origen) : ObservableObject
{
    public string Clave { get; } = clave; public string Nombre { get; } = nombre;
    string _v = valor; public string Valor { get => _v; set => Set(ref _v, value); }   // editable: el usuario corrige antes de confirmar
    public string Confianza { get; } = confianza; public string Origen { get; } = origen;
}
public sealed record LineaLegajo(string Documento, bool Presente, string Motivo);

/// <summary>Estado y comandos de la ventana principal. Sin referencias a WPF: probado en CI Linux.</summary>
public sealed class MainViewModel : ObservableObject
{
    static readonly CultureInfo Bo = CultureInfo.GetCultureInfo("es-BO");
    readonly ComexDb _db; readonly Func<DateOnly> _hoy;
    readonly ServicioOperaciones _ops; readonly ServicioCatalogo _cat; readonly ServicioDocumentos? _docs; int _docIdPendiente;

    public MainViewModel(ComexDb db, Func<DateOnly>? hoy = null, IMotorOcr? ocr = null)
    {
        _docs = ocr is null ? null : new(db, ocr);
        _db = db; _hoy = hoy ?? (() => DateOnly.FromDateTime(DateTime.Today));
        _ops = new(db); _cat = new(db);
        CargarCmd = new(_ => CargarAsync());
        NuevaImportacionCmd = new(_ => NuevaImportacionAsync());
        AgregarItemCmd = new(_ => AgregarItemAsync(), _ => Seleccionada is not null);
        LiquidarCmd = new(_ => LiquidarAsync(), _ => Seleccionada is not null);
        ConfirmarPropuestaCmd = new(_ => ConfirmarPropuestaAsync(), _ => Propuesta.Count > 0);
        CompletarEtapaCmd = new(p => CompletarEtapaAsync((EtapaFila)p!), p => Seleccionada is not null && p is EtapaFila);
    }

    // --- Lista y selección ---
    public ObservableCollection<Operacion> Operaciones { get; } = [];
    Operacion? _sel; public Operacion? Seleccionada
    {
        get => _sel;
        set { if (Set(ref _sel, value)) { _ = RefrescarAsync(); RefrescarComandos(); } }
    }

    // --- Entradas de captura ---
    string _nuevaCarpeta = ""; public string NuevaCarpeta { get => _nuevaCarpeta; set => Set(ref _nuevaCarpeta, value); }
    Incoterm _nuevoIncoterm = Incoterm.FOB; public Incoterm NuevoIncoterm { get => _nuevoIncoterm; set => Set(ref _nuevoIncoterm, value); }
    public IReadOnlyList<Incoterm> Incoterms { get; } = Enum.GetValues<Incoterm>();
    decimal _tc = 6.96m; public decimal TipoCambioUsd { get => _tc; set => Set(ref _tc, value); }   // el usuario confirma el TC oficial BCB del día
    decimal _flete; public decimal Flete { get => _flete; set => Set(ref _flete, value); }
    decimal _seguro; public decimal Seguro { get => _seguro; set => Set(ref _seguro, value); }
    string _partida = ""; public string ItemPartida { get => _partida; set => Set(ref _partida, value); }
    string _desc = ""; public string ItemDescripcion { get => _desc; set => Set(ref _desc, value); }
    decimal _valor; public decimal ItemValor { get => _valor; set => Set(ref _valor, value); }
    decimal _peso; public decimal ItemPesoBruto { get => _peso; set => Set(ref _peso, value); }

    string? _docRuta; public string? DocumentoRuta { get => _docRuta; set => Set(ref _docRuta, value); }

    // --- Salidas ---
    public ObservableCollection<ItemFila> Items { get; } = [];
    public ObservableCollection<EtapaFila> Etapas { get; } = [];
    public ObservableCollection<LineaLiquidacion> Liquidacion { get; } = [];
    public ObservableCollection<LineaLegajo> Legajo { get; } = [];
    public ObservableCollection<string> Bitacora { get; } = [];
    public ObservableCollection<string> Avisos { get; } = [];
    string _msg = "Listo"; public string Mensaje { get => _msg; set => Set(ref _msg, value); }
    string _res = ""; public string ResumenSemaforos { get => _res; set => Set(ref _res, value); }
    string _prox = ""; public string ProximoVencimiento { get => _prox; set => Set(ref _prox, value); }

    // --- Comandos ---
    public RelayCommand CargarCmd { get; }
    public RelayCommand NuevaImportacionCmd { get; }
    public RelayCommand AgregarItemCmd { get; }
    public RelayCommand LiquidarCmd { get; }
    public RelayCommand CompletarEtapaCmd { get; }
    public RelayCommand ConfirmarPropuestaCmd { get; }
    public ObservableCollection<CampoPropuesto> Propuesta { get; } = [];

    void RefrescarComandos() { AgregarItemCmd.Refresh(); LiquidarCmd.Refresh(); CompletarEtapaCmd.Refresh(); }

    async Task Seguro_(Func<Task> accion)
    {
        try { await accion(); }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or DbUpdateException)
        { Mensaje = "⚠ " + ex.Message; }
    }

    public Task CargarAsync() => Seguro_(async () =>
    {
        Operaciones.Clear();
        foreach (var o in await _db.Operaciones.AsNoTracking().OrderByDescending(o => o.Id).ToListAsync()) Operaciones.Add(o);
        Mensaje = $"{Operaciones.Count} operaciones";
    });

    public Task NuevaImportacionAsync() => Seguro_(async () =>
    {
        if (string.IsNullOrWhiteSpace(NuevaCarpeta)) throw new ArgumentException("Indique el N.º de carpeta.");
        var op = await _ops.CrearImportacionAsync(NuevaCarpeta.Trim(), NuevoIncoterm, "USD", _hoy());
        NuevaCarpeta = "";
        await CargarAsync();
        Seleccionada = Operaciones.First(o => o.Id == op.Id);
        await RefrescarAsync();
        Mensaje = $"Importación {op.Carpeta} creada";
    });

    public Task AgregarItemAsync() => Seguro_(async () =>
    {
        var op = Seleccionada!;
        var n = await _db.Items.CountAsync(i => i.OperacionId == op.Id) + 1;
        await _ops.AgregarItemAsync(op.Id, new() { Numero = n, CodigoNandina = new string(ItemPartida.Where(char.IsDigit).ToArray()), Descripcion = ItemDescripcion, ValorFactura = ItemValor, PesoBrutoKg = ItemPesoBruto, PesoNetoKg = ItemPesoBruto });
        var avisos = await _cat.AplicarAOperacionAsync(op.Id);
        ItemPartida = ItemDescripcion = ""; ItemValor = ItemPesoBruto = 0;
        await RefrescarAsync();
        foreach (var a in avisos) Avisos.Add(a);
        Mensaje = $"Ítem {n} agregado";
    });

    public Task LiquidarAsync() => Seguro_(async () =>
    {
        var op = await _db.Operaciones.FirstAsync(o => o.Id == Seleccionada!.Id);
        op.Flete = Flete; op.Seguro = Seguro; await _db.SaveChangesAsync();
        var tc = new TipoCambioTable(_hoy(), new Dictionary<string, decimal> { ["USD"] = TipoCambioUsd });
        var r = await _ops.LiquidarAsync(op.Id, tc);
        await RefrescarAsync();
        foreach (var a in r.Advertencias) Avisos.Add(a);
        Mensaje = $"Liquidado: tributos Bs {r.TotalTributos.ToString("N2", Bo)}";
    });

    public Task CompletarEtapaAsync(EtapaFila e) => Seguro_(async () =>
    {
        await _ops.CompletarEtapaAsync(Seleccionada!.Id, e.Codigo, _hoy());
        await RefrescarAsync();
        Mensaje = $"Etapa {e.Codigo} cumplida";
    });

    /// <summary>Muestra el documento, ejecuta OCR y deja la propuesta en pantalla. No modifica la operación.</summary>
    public Task ProcesarDocumentoAsync(string ruta) => Seguro_(async () =>
    {
        if (Seleccionada is null) throw new InvalidOperationException("Seleccione una operación.");
        if (_docs is null) throw new InvalidOperationException("OCR no configurado.");
        DocumentoRuta = ruta; Mensaje = "Leyendo documento…";
        var r = await _docs.ProcesarAsync(Seleccionada.Id, ruta);
        _docIdPendiente = r.Documento.Id; Propuesta.Clear();
        void Add<T>(string k, string n, CampoOcr<T>? c, Func<T, string> f) { if (c is not null) Propuesta.Add(new(k, n, f(c.Valor), c.Confianza.ToString(), c.LineaOrigen)); }
        Add("factura", "N.º factura", r.Campos.NumeroFactura, v => v); Add("proveedor", "Proveedor", r.Campos.Proveedor, v => v);
        Add("incoterm", "Incoterm", r.Campos.Incoterm, v => v); Add("moneda", "Moneda", r.Campos.Moneda, v => v);
        Add("valor", "Valor total", r.Campos.ValorTotal, v => v.ToString(CultureInfo.InvariantCulture));
        Add("peso", "Peso bruto kg", r.Campos.PesoBrutoKg, v => v.ToString(CultureInfo.InvariantCulture));
        ConfirmarPropuestaCmd.Refresh(); await RefrescarAsync();
        Mensaje = $"{r.Tipo}: {Propuesta.Count} campos propuestos — revise y confirme";
    });

    public Task ConfirmarPropuestaAsync() => Seguro_(async () =>
    {
        string? V(string k) => Propuesta.FirstOrDefault(p => p.Clave == k)?.Valor;
        await _docs!.ConfirmarAsync(Seleccionada!.Id, _docIdPendiente, V("incoterm"), V("moneda"), V("factura"), V("proveedor"));
        if (decimal.TryParse(V("valor"), NumberStyles.Number, CultureInfo.InvariantCulture, out var val)) ItemValor = val;
        if (decimal.TryParse(V("peso"), NumberStyles.Number, CultureInfo.InvariantCulture, out var pe)) ItemPesoBruto = pe;
        Propuesta.Clear(); ConfirmarPropuestaCmd.Refresh();
        await CargarAsync(); Seleccionada = Operaciones.First(o => o.Id == Seleccionada.Id);
        Mensaje = "Datos confirmados: complete partida y descripción y agregue el ítem";
    });

    public async Task<ResumenImportacionCatalogo?> ImportarCatalogoAsync(string rutaCsv, string version)
    {
        ResumenImportacionCatalogo? res = null;
        await Seguro_(async () =>
        {
            using var rd = new StreamReader(rutaCsv);
            res = await _cat.ImportarCsvAsync(rd, version);
            Mensaje = $"Catálogo: {res.Importadas} partidas, {res.Rechazadas} rechazadas" + (res.SoloEjemplos ? " — SOLO DATOS DE EJEMPLO" : "");
        });
        return res;
    }

    public async Task<string?> ExportarExpedienteAsync(string rutaMd)
    {
        if (Seleccionada is null) return null;
        string? md = null;
        await Seguro_(async () =>
        {
            md = await _ops.GenerarExpedienteAsync(Seleccionada.Id, _hoy());
            await File.WriteAllTextAsync(rutaMd, md);
            Mensaje = $"Expediente guardado en {rutaMd}";
        });
        return md;
    }

    static string Color(Semaforo s) => s switch
    {
        Semaforo.Cumplido => "#2E9E5B", Semaforo.EnCurso => "#2F7DD1", Semaforo.Alerta => "#E0A800",
        Semaforo.Vencido => "#D64545", _ => "#9AA3AD"
    };

    public async Task RefrescarAsync()
    {
        Items.Clear(); Etapas.Clear(); Liquidacion.Clear(); Legajo.Clear(); Bitacora.Clear(); Avisos.Clear();
        ResumenSemaforos = ProximoVencimiento = "";
        if (Seleccionada is null) return;
        await Seguro_(async () =>
        {
            var id = Seleccionada.Id; var hoy = _hoy();
            var op = await _db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Bitacora).Include(o => o.Liquidaciones).FirstAsync(o => o.Id == id);
            Flete = op.Flete; Seguro = op.Seguro;
            foreach (var i in op.Items.OrderBy(i => i.Numero))
                Items.Add(new(i.Numero, i.CodigoNandina, i.Descripcion, i.ValorFactura.ToString("N2", Bo), i.AlicuotaGA.ToString("P0", Bo)));

            var estado = await _ops.EstadoRutaAsync(id, hoy);
            foreach (var s in estado)
                Etapas.Add(new(s.Etapa.Codigo, s.Etapa.Nombre, $"{s.Etapa.InicioPlan:dd/MM} → {s.Etapa.FinPlan:dd/MM}",
                    s.Etapa.FinReal?.ToString("dd/MM") ?? "—", s.Semaforo, Color(s.Semaforo), s.Etapa.EsCritica, s.Etapa.EsHitoLegal));
            int N(Semaforo x) => estado.Count(s => s.Semaforo == x);
            ResumenSemaforos = $"🟢 {N(Semaforo.Cumplido)}  🔵 {N(Semaforo.EnCurso)}  🟡 {N(Semaforo.Alerta)}  🔴 {N(Semaforo.Vencido)}";
            var prox = estado.Where(s => s.Etapa.FinReal is null).OrderBy(s => s.Etapa.FinPlan).FirstOrDefault();
            if (prox is not null) ProximoVencimiento = $"Próximo: {prox.Etapa.Nombre} — {prox.Etapa.FinPlan:dd/MM/yyyy}";

            var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault();
            if (ult is not null)
            {
                var r = System.Text.Json.JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson)!;
                string F(decimal v) => v.ToString("N2", Bo);
                Liquidacion.Add(new("Valor FOB", F(r.ValorFobBob))); Liquidacion.Add(new("+ Adiciones", F(r.AdicionesBob)));
                Liquidacion.Add(new("− Deducciones", F(r.DeduccionesBob))); Liquidacion.Add(new("CIF aduana (Bs)", F(r.CifBob), true));
                Liquidacion.Add(new("Gravamen arancelario", F(r.GA))); Liquidacion.Add(new("ICE", F(r.ICE)));
                Liquidacion.Add(new("IEHD", F(r.IEHD))); Liquidacion.Add(new("IVA", F(r.IVA)));
                Liquidacion.Add(new("TOTAL TRIBUTOS", F(r.TotalTributos), true));
                if (r.RequiereBancarizacion) Avisos.Add("FOB ≥ Bs 50.000: complete el respaldo bancario (D.S. 772).");
            }
            foreach (var (t, ok, m) in await _ops.ChecklistAsync(id)) Legajo.Add(new(t.ToString(), ok, m));
            foreach (var e in op.Bitacora.OrderByDescending(e => e.Fecha).Take(100)) Bitacora.Add($"{e.Fecha:dd/MM HH:mm} · {e.Categoria} · {e.Detalle}");
        });
    }
}
