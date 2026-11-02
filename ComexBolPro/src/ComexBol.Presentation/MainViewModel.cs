using System.Collections.ObjectModel;
using System.Globalization;
using ComexBol.Core;
using ComexBol.Data;
using ComexBol.Documentos;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Presentation;

public sealed record EtapaFila(string Codigo, string Nombre, string Plan, string Real, Semaforo Semaforo, string ColorHex, bool EsCritica, bool EsHitoLegal);
public sealed record ItemFila(int Id, int Numero, string Partida, string Descripcion, string Valor, string GA, string Detalle);
public sealed record SugerenciaPartida(string Codigo, string Descripcion, string Corta, string Info);

public sealed class CostoFila : ObservableObject
{
    public int Id { get; set; }
    string _c = ""; public string Concepto { get => _c; set => Set(ref _c, value); }
    decimal _p; public decimal Proyectado { get => _p; set { if (Set(ref _p, value)) Cambio(); } }
    decimal? _r; public decimal? Real { get => _r; set { if (Set(ref _r, value)) Cambio(); } }
    string _n = ""; public string Nota { get => _n; set => Set(ref _n, value); }
    public string Diferencia => Real is null ? "" : (Real.Value - Proyectado).ToString("N2", Formato.Bo);
    void Cambio() { PropiedadCambiada(nameof(Diferencia)); }
}
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
    static CultureInfo Bo => Formato.Bo;
    readonly ComexDb _db; readonly Func<DateOnly> _hoy;
    readonly ServicioOperaciones _ops; readonly ServicioCatalogo _cat; readonly ServicioDocumentos? _docs; int _docIdPendiente;
    readonly ServicioConfiguracion _cfg; readonly ServicioCostos _costos; List<Operacion> _todas = []; int _busquedaSeq; bool _silenciar;

    public MainViewModel(ComexDb db, Func<DateOnly>? hoy = null, IMotorOcr? ocr = null)
    {
        _docs = ocr is null ? null : new(db, ocr);
        _db = db; _hoy = hoy ?? (() => DateOnly.FromDateTime(DateTime.Today));
        _ops = new(db); _cat = new(db); _cfg = new(db); _costos = new(db);
        Decision = new DecisionViewModel(db, () => Seleccionada?.Id, () => TipoCambioUsd, _hoy);
        CargarCmd = new(_ => CargarAsync());
        NuevaImportacionCmd = new(_ => NuevaImportacionAsync());
        AgregarItemCmd = new(_ => AgregarItemAsync(), _ => Seleccionada is not null);
        LiquidarCmd = new(_ => LiquidarAsync(), _ => Seleccionada is not null);
        ConfirmarPropuestaCmd = new(_ => ConfirmarPropuestaAsync(), _ => Propuesta.Count > 0);
        EditarItemCmd = new(_ => EditarItemAsync(), _ => ItemSeleccionado is not null);
        EliminarItemCmd = new(_ => EliminarItemAsync(), _ => ItemSeleccionado is not null);
        NuevoItemCmd = new(_ => { LimpiarFormularioItem(); return Task.CompletedTask; });
        GuardarTcCmd = new(_ => GuardarTcAsync());
        CargarProyectadoCmd = new(_ => CargarProyectadoAsync(), _ => Seleccionada is not null);
        AgregarCostoCmd = new(_ => { Costos.Add(new() { Concepto = "Nuevo costo" }); return Task.CompletedTask; }, _ => Seleccionada is not null);
        GuardarCostosCmd = new(_ => GuardarCostosFilasAsync(), _ => Seleccionada is not null);
        EliminarCostoCmd = new(p => EliminarCostoAsync(p as CostoFila), p => p is CostoFila);
        CompletarEtapaCmd = new(p => CompletarEtapaAsync((EtapaFila)p!), p => Seleccionada is not null && p is EtapaFila);
    }

    public DecisionViewModel Decision { get; }

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
    decimal _tc = 6.96m; public decimal TipoCambioUsd { get => _tc; set => Set(ref _tc, value); }   // se propone el de la tabla de configuración; el usuario lo confirma
    string _tcInfo = ""; public string TcInfo { get => _tcInfo; set => Set(ref _tcInfo, value); }
    string _usuario = ""; public string UsuarioActual { get => _usuario; set { if (Set(ref _usuario, value)) { _ops.Usuario = value; if (_docs is not null) _docs.Usuario = value; } } }
    string _filtroOps = ""; public string FiltroOperaciones { get => _filtroOps; set { if (Set(ref _filtroOps, value)) AplicarFiltroOperaciones(); } }
    ItemFila? _itemSel; public ItemFila? ItemSeleccionado { get => _itemSel; set { if (Set(ref _itemSel, value)) { EditarItemCmd.Refresh(); EliminarItemCmd.Refresh(); } } }
    bool _enEdicion; public bool EnEdicion { get => _enEdicion; set { if (Set(ref _enEdicion, value)) PropiedadCambiada(nameof(TextoGuardarItem)); } }
    int _itemEditId;
    public string TextoGuardarItem => EnEdicion ? "Guardar cambios del ítem" : "Agregar ítem";
    decimal _flete; public decimal Flete { get => _flete; set => Set(ref _flete, value); }
    decimal _seguro; public decimal Seguro { get => _seguro; set => Set(ref _seguro, value); }
    string _partida = "";
    public string ItemPartida
    {
        get => _partida;
        set { if (Set(ref _partida, value) && !_silenciar) _ = BuscarSugerenciasAsync(value); }
    }
    string _desc = ""; public string ItemDescripcion { get => _desc; set => Set(ref _desc, value); }
    string _marca = ""; public string ItemMarca { get => _marca; set => Set(ref _marca, value); }
    string _modelo = ""; public string ItemModelo { get => _modelo; set => Set(ref _modelo, value); }
    string _serie = ""; public string ItemSerie { get => _serie; set => Set(ref _serie, value); }
    string _pais = ""; public string ItemPais { get => _pais; set => Set(ref _pais, value); }
    string _infoPartida = ""; public string InfoPartida { get => _infoPartida; set => Set(ref _infoPartida, value); }
    bool _mostrarSug; public bool MostrarSugerencias { get => _mostrarSug; set => Set(ref _mostrarSug, value); }
    public ObservableCollection<SugerenciaPartida> Sugerencias { get; } = [];
    decimal _valor; public decimal ItemValor { get => _valor; set => Set(ref _valor, value); }
    public IReadOnlyList<string> Acuerdos { get; } = ["", "CAN", "ACE 22 (Chile)", "ACE 36 (Mercosur)", "ACE 47 (Cuba)", "ACE 66 (México)", "VEN (Venezuela)"];
    string _acuerdo = ""; public string ItemAcuerdo { get => _acuerdo; set => Set(ref _acuerdo, value); }
    decimal _desg; public decimal ItemDesgravacionPct { get => _desg; set => Set(ref _desg, value); }      // 0–100: % de rebaja del GA según el acuerdo
    int _antig; public int ItemAntiguedad { get => _antig; set => Set(ref _antig, value); }           // vehículos: años de antigüedad (0 = nuevo)
    decimal _icePct; public decimal ItemIcePct { get => _icePct; set => Set(ref _icePct, value); }        // ICE % ingresado a mano cuando el arancel no trae la tasa
    decimal _peso; public decimal ItemPesoBruto { get => _peso; set => Set(ref _peso, value); }

    string? _docRuta; public string? DocumentoRuta { get => _docRuta; set => Set(ref _docRuta, value); }

    // --- Salidas ---
    public ObservableCollection<ItemFila> Items { get; } = [];
    public ObservableCollection<CostoFila> Costos { get; } = [];
    string _totCostos = ""; public string TotalesCostos { get => _totCostos; set => Set(ref _totCostos, value); }
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
    public RelayCommand EditarItemCmd { get; }
    public RelayCommand EliminarItemCmd { get; }
    public RelayCommand NuevoItemCmd { get; }
    public RelayCommand GuardarTcCmd { get; }
    public RelayCommand CargarProyectadoCmd { get; }
    public RelayCommand AgregarCostoCmd { get; }
    public RelayCommand GuardarCostosCmd { get; }
    public RelayCommand EliminarCostoCmd { get; }
    public ObservableCollection<CampoPropuesto> Propuesta { get; } = [];

    void RefrescarComandos() { AgregarItemCmd.Refresh(); LiquidarCmd.Refresh(); CompletarEtapaCmd.Refresh(); CargarProyectadoCmd.Refresh(); AgregarCostoCmd.Refresh(); GuardarCostosCmd.Refresh(); }

    Task Seguro_(Func<Task> accion) => DbGate.EjecutarAsync(async () =>
    {
        try { await accion(); }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or DbUpdateException)
        { Mensaje = "AVISO: " + ex.Message; }
    });

    public Task CargarAsync() => Seguro_(async () =>
    {
        _todas = await _db.Operaciones.AsNoTracking().OrderByDescending(o => o.Id).ToListAsync();
        AplicarFiltroOperaciones();
        await CargarTipoCambioAsync();
        Mensaje = $"{_todas.Count} operaciones";
    });

    void AplicarFiltroOperaciones()
    {
        var f = (FiltroOperaciones ?? "").Trim();
        var seleccionada = Seleccionada?.Id;
        Operaciones.Clear();
        foreach (var o in _todas.Where(o => f.Length == 0 || o.Carpeta.Contains(f, StringComparison.OrdinalIgnoreCase))) Operaciones.Add(o);
        if (seleccionada is not null) Seleccionada = Operaciones.FirstOrDefault(o => o.Id == seleccionada);
    }

    /// <summary>Propone el tipo de cambio oficial registrado en Configuración para hoy (el más reciente hasta hoy).</summary>
    async Task CargarTipoCambioAsync()
    {
        var r = await _cfg.ObtenerTipoCambioAsync("USD", _hoy());
        if (r is not null) { TipoCambioUsd = r.BobPorUnidad; TcInfo = $"TC registrado al {r.Fecha:dd/MM/yyyy} ({r.Fuente})"; }
        else TcInfo = "Sin tipo de cambio registrado: regístrelo en Configuración";
    }

    public Task GuardarTcAsync() => Seguro_(async () =>
    {
        await _cfg.GuardarTipoCambioAsync(_hoy(), "USD", TipoCambioUsd, "Manual");
        TcInfo = $"TC registrado al {_hoy():dd/MM/yyyy} (Manual)"; Mensaje = $"Tipo de cambio {TipoCambioUsd.ToString("N2", Bo)} guardado para hoy";
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

    ItemMercancia ItemDelFormulario(int numero) => new()
    {
        Numero = numero, CodigoNandina = new string(ItemPartida.Where(char.IsDigit).ToArray()), Descripcion = ItemDescripcion, ValorFactura = ItemValor,
        PesoBrutoKg = ItemPesoBruto, PesoNetoKg = ItemPesoBruto, AntiguedadAnios = ItemAntiguedad, AlicuotaIce = ItemIcePct / 100m,
        AcuerdoPreferencial = ItemAcuerdo, Desgravacion = ItemDesgravacionPct / 100m, Marca = ItemMarca ?? "", Modelo = ItemModelo ?? "", Serie = ItemSerie ?? "", PaisOrigen = ItemPais ?? ""
    };

    void LimpiarFormularioItem()
    {
        _silenciar = true;
        ItemPartida = ItemDescripcion = ItemMarca = ItemModelo = ItemSerie = ItemPais = ""; ItemValor = ItemPesoBruto = ItemIcePct = ItemDesgravacionPct = 0; ItemAntiguedad = 0; ItemAcuerdo = "";
        _silenciar = false; InfoPartida = ""; Sugerencias.Clear(); MostrarSugerencias = false; EnEdicion = false; _itemEditId = 0; ItemSeleccionado = null;
    }

    /// <summary>Agrega el ítem del formulario, o guarda los cambios si se está editando uno existente.</summary>
    public Task AgregarItemAsync() => Seguro_(async () =>
    {
        var op = Seleccionada!;
        await GuardarCostosAsync(op.Id);          // el flete y el seguro digitados no deben perderse al refrescar la pantalla
        string aviso;
        if (EnEdicion)
        {
            var actual = await _db.Items.AsNoTracking().FirstAsync(i => i.Id == _itemEditId);
            var nuevo = ItemDelFormulario(actual.Numero); nuevo.Id = _itemEditId; nuevo.OperacionId = op.Id; nuevo.AlicuotaGA = actual.AlicuotaGA;
            await _ops.ActualizarItemAsync(nuevo); aviso = $"Ítem {actual.Numero} modificado";
        }
        else
        {
            var n = await _db.Items.CountAsync(i => i.OperacionId == op.Id) + 1;
            await _ops.AgregarItemAsync(op.Id, ItemDelFormulario(n)); aviso = $"Ítem {n} agregado";
        }
        var avisos = await _cat.AplicarAOperacionAsync(op.Id);
        LimpiarFormularioItem();
        await RefrescarAsync();
        foreach (var a in avisos) Avisos.Add(a);
        Mensaje = aviso + (Items.Count > 0 ? ". Recuerde calcular de nuevo la liquidación." : "");
    });

    public Task EditarItemAsync() => Seguro_(async () =>
    {
        var fila = ItemSeleccionado ?? throw new InvalidOperationException("Seleccione un ítem de la lista.");
        var it = await _db.Items.AsNoTracking().FirstAsync(i => i.Id == fila.Id);
        _silenciar = true;
        ItemPartida = it.CodigoNandina; ItemDescripcion = it.Descripcion; ItemValor = it.ValorFactura; ItemPesoBruto = it.PesoBrutoKg; ItemAntiguedad = it.AntiguedadAnios;
        ItemIcePct = it.AlicuotaIce * 100m; ItemAcuerdo = it.AcuerdoPreferencial; ItemDesgravacionPct = it.Desgravacion * 100m;
        ItemMarca = it.Marca; ItemModelo = it.Modelo; ItemSerie = it.Serie; ItemPais = it.PaisOrigen ?? "";
        _silenciar = false; Sugerencias.Clear(); MostrarSugerencias = false;
        _itemEditId = it.Id; EnEdicion = true; Mensaje = $"Editando el ítem {it.Numero}: modifique y pulse «Guardar cambios del ítem»";
        var p = await _cat.ObtenerAsync(it.CodigoNandina); InfoPartida = p is null ? "" : InfoDe(p);
    });

    /// <summary>Elimina el ítem seleccionado (la ventana pide confirmación antes de llamar).</summary>
    public Task EliminarItemAsync() => Seguro_(async () =>
    {
        var fila = ItemSeleccionado ?? throw new InvalidOperationException("Seleccione un ítem de la lista.");
        await _ops.EliminarItemAsync(fila.Id);
        LimpiarFormularioItem(); await RefrescarAsync();
        Mensaje = $"Ítem {fila.Numero} eliminado. Calcule de nuevo la liquidación.";
    });

    /// <summary>Elimina la operación seleccionada con todo su contenido (la ventana pide confirmación antes de llamar).</summary>
    public Task EliminarOperacionAsync() => Seguro_(async () =>
    {
        var op = Seleccionada ?? throw new InvalidOperationException("Seleccione una operación.");
        await _ops.EliminarOperacionAsync(op.Id);
        LimpiarFormularioItem(); Seleccionada = null;
        await CargarAsync(); await RefrescarAsync();
        Mensaje = $"Operación {op.Carpeta} eliminada";
    });

    // ---------- Selector de partidas ----------
    public static string InfoDe(PartidaCatalogo p)
    {
        var partes = new List<string> { $"GA {p.AlicuotaGA.ToString("P0", Bo)}", $"Unidad: {(p.Unidad.Length > 0 ? p.Unidad : "—")}" };
        if (p.Prohibida) partes.Add("MERCANCÍA PROHIBIDA");
        if (p.TipoDocumento.Length > 0 && !p.Prohibida) partes.Add($"Documento: {p.TipoDocumento} {p.Entidad}".Trim());
        if (p.ImpuestoEspecial.Length > 0) partes.Add(p.ImpuestoEspecial);
        return string.Join("  ·  ", partes);
    }

    async Task BuscarSugerenciasAsync(string? texto)
    {
        var seq = ++_busquedaSeq; var t = (texto ?? "").Trim();
        if (t.Length < 2) { Sugerencias.Clear(); MostrarSugerencias = false; InfoPartida = ""; return; }
        try
        {
            await Seguro_(async () =>
            {
                if (seq != _busquedaSeq) return;
                var res = await _cat.BuscarAsync(t, 15);
                if (seq != _busquedaSeq) return;
                Sugerencias.Clear();
                foreach (var p in res) Sugerencias.Add(new(p.Codigo, p.Descripcion, Formato.DescripcionCorta(p.Descripcion), InfoDe(p)));
                var exacta = res.Count == 1 && res[0].Codigo == new string(t.Where(char.IsDigit).ToArray());
                MostrarSugerencias = Sugerencias.Count > 0 && !exacta;
                InfoPartida = exacta ? InfoDe(res[0]) : "";
                if (exacta && string.IsNullOrWhiteSpace(ItemDescripcion)) ItemDescripcion = Formato.DescripcionCorta(res[0].Descripcion);
            });
        }
        catch (ObjectDisposedException) { }
    }

    /// <summary>El usuario eligió una partida de la lista: se completan el código y la descripción; el resto se llena a mano.</summary>
    public void ElegirSugerencia(SugerenciaPartida s)
    {
        _busquedaSeq++;
        _silenciar = true; ItemPartida = s.Codigo; _silenciar = false;
        ItemDescripcion = s.Corta; InfoPartida = s.Info; MostrarSugerencias = false;
    }

    async Task GuardarCostosAsync(int opId)
    {
        var o = await _db.Operaciones.FirstAsync(x => x.Id == opId);
        o.Flete = Flete; o.Seguro = Seguro; await _db.SaveChangesAsync();
    }

    public Task LiquidarAsync() => Seguro_(async () =>
    {
        var op = await _db.Operaciones.FirstAsync(o => o.Id == Seleccionada!.Id);
        op.Flete = Flete; op.Seguro = Seguro; await _db.SaveChangesAsync();
        var tc = new TipoCambioTable(_hoy(), new Dictionary<string, decimal> { ["USD"] = TipoCambioUsd });
        var r = await _ops.LiquidarAsync(op.Id, tc, await _cfg.ObtenerParametrosAsync());
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
        Mensaje = "Leyendo documento…";
        if (ruta.EndsWith(".pdf", StringComparison.OrdinalIgnoreCase))
        {
            var tmp = Directory.CreateTempSubdirectory("comexbol-vista-");
            DocumentoRuta = (await PdfRasterizador.AImagenesAsync(ruta, tmp.FullName, maxPaginas: 1, dpi: 110)).FirstOrDefault();   // el visor muestra la primera página
        }
        else DocumentoRuta = ruta;
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
        var id = Seleccionada!.Id;      // guardar antes: al recargar la lista, la ventana deselecciona la operación
        await _docs!.ConfirmarAsync(id, _docIdPendiente, V("incoterm"), V("moneda"), V("factura"), V("proveedor"));
        if (decimal.TryParse(V("valor"), NumberStyles.Number, CultureInfo.InvariantCulture, out var val)) ItemValor = val;
        if (decimal.TryParse(V("peso"), NumberStyles.Number, CultureInfo.InvariantCulture, out var pe)) ItemPesoBruto = pe;
        Propuesta.Clear(); ConfirmarPropuestaCmd.Refresh();
        await CargarAsync(); Seleccionada = Operaciones.First(o => o.Id == id);
        Mensaje = "Datos confirmados: complete partida y descripción y agregue el ítem";
    });

    public async Task<bool> ExportarExcelAsync(string ruta)
    {
        if (Seleccionada is null) return false;
        var ok = false;
        await Seguro_(async () => { await ExportadorExcel.ExportarAsync(_db, Seleccionada.Id, ruta, _hoy()); Mensaje = $"Excel guardado en {ruta}"; ok = true; });
        return ok;
    }

    public async Task<bool> ExportarJsonAsync(string ruta)
    {
        if (Seleccionada is null) return false;
        var ok = false;
        await Seguro_(async () => { await ExportadorJson.ExportarAsync(_db, Seleccionada.Id, ruta, _hoy()); Mensaje = $"Datos estructurados guardados en {ruta}"; ok = true; });
        return ok;
    }

    // ---------- Hoja de costos reales vs proyectados ----------
    void RecalcularTotalesCostos()
    {
        var p = Costos.Sum(c => c.Proyectado); var r = Costos.Where(c => c.Real is not null).Sum(c => c.Real!.Value);
        TotalesCostos = Costos.Count == 0 ? "" : $"Proyectado Bs {p.ToString("N2", Bo)}  ·  Real registrado Bs {r.ToString("N2", Bo)}  ·  Diferencia Bs {(r - Costos.Where(c => c.Real is not null).Sum(c => c.Proyectado)).ToString("N2", Bo)}";
    }

    public Task CargarProyectadoAsync() => Seguro_(async () =>
    {
        var tc = new TipoCambioTable(_hoy(), new Dictionary<string, decimal> { ["USD"] = TipoCambioUsd });
        var n = await _costos.CargarProyectadoDesdeLiquidacionAsync(Seleccionada!.Id, tc);
        await RefrescarAsync(); Mensaje = n == 0 ? "La hoja de costos ya tenía todos los conceptos" : $"{n} conceptos proyectados cargados: anote lo realmente pagado en «Real»";
    });

    public Task GuardarCostosFilasAsync() => Seguro_(async () =>
    {
        foreach (var f in Costos) await _costos.GuardarAsync(new() { Id = f.Id, OperacionId = Seleccionada!.Id, Concepto = f.Concepto, ProyectadoBob = f.Proyectado, RealBob = f.Real, Nota = f.Nota });
        await RefrescarAsync(); Mensaje = "Hoja de costos guardada";
    });

    public Task EliminarCostoAsync(CostoFila? f) => Seguro_(async () =>
    {
        if (f is null) return;
        if (f.Id != 0) await _costos.EliminarAsync(f.Id);
        Costos.Remove(f); RecalcularTotalesCostos();
    });

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

    static string NombreDocumento(TipoDocumento t) => t switch
    {
        TipoDocumento.Factura => "Factura comercial", TipoDocumento.Embarque => "Documento de embarque", TipoDocumento.PackingList => "Lista de empaque",
        TipoDocumento.AutorizacionPrevia => "Autorización previa", TipoDocumento.Seguro => "Seguro de transporte", TipoDocumento.GastosPortuarios => "Gastos portuarios",
        TipoDocumento.FleteTerrestre => "Factura de flete", TipoDocumento.CertificadoOrigen => "Certificado de origen", TipoDocumento.Bancario => "Respaldo bancario", _ => t.ToString()
    };

    static string Color(Semaforo s) => s switch
    {
        Semaforo.Cumplido => "#2E9E5B", Semaforo.EnCurso => "#2F7DD1", Semaforo.Alerta => "#E0A800",
        Semaforo.Vencido => "#D64545", _ => "#9AA3AD"
    };

    public async Task RefrescarAsync()
    {
        Items.Clear(); Etapas.Clear(); Liquidacion.Clear(); Legajo.Clear(); Bitacora.Clear(); Avisos.Clear(); Costos.Clear(); TotalesCostos = "";
        ResumenSemaforos = ProximoVencimiento = "";
        if (Seleccionada is null) return;
        await Seguro_(async () =>
        {
            var id = Seleccionada.Id; var hoy = _hoy();
            var op = await _db.Operaciones.AsNoTracking().Include(o => o.Items).Include(o => o.Bitacora).Include(o => o.Liquidaciones).FirstAsync(o => o.Id == id);
            Flete = op.Flete; Seguro = op.Seguro;
            // Sin respaldo del arancel, el GA podría estar mal: se avisa siempre, no solo al agregar el ítem.
            var codigos = op.Items.Select(i => i.CodigoNandina).ToList();
            var enCatalogo = (await _db.Partidas.Where(p => codigos.Contains(p.Codigo)).Select(p => p.Codigo).ToListAsync()).ToHashSet();
            if (!await _db.Partidas.AnyAsync()) Avisos.Add("El arancel NO está cargado: el gravamen arancelario no tiene respaldo. Use «Importar catálogo…» antes de registrar mercancías.");
            else foreach (var i in op.Items.Where(i => !enCatalogo.Contains(i.CodigoNandina)).OrderBy(i => i.Numero))
                Avisos.Add($"Ítem {i.Numero}: la partida {i.CodigoNandina} no existe en el arancel cargado; verifique el código (GA aplicado: {i.AlicuotaGA:P0}).");
            foreach (var i in op.Items.OrderBy(i => i.Numero))
                Items.Add(new(i.Id, i.Numero, i.CodigoNandina, i.Descripcion, i.ValorFactura.ToString("N2", Bo), i.AlicuotaGA.ToString("P0", Bo),
                    string.Join(" · ", new[] { i.Marca, i.Modelo, i.Serie, i.PaisOrigen }.Where(x => !string.IsNullOrWhiteSpace(x)))));

            var estado = await _ops.EstadoRutaAsync(id, hoy);
            foreach (var s in estado)
                Etapas.Add(new(s.Etapa.Codigo, s.Etapa.Nombre, $"{s.Etapa.InicioPlan:dd/MM} a {s.Etapa.FinPlan:dd/MM}",
                    s.Etapa.FinReal?.ToString("dd/MM") ?? "—", s.Semaforo, Color(s.Semaforo), s.Etapa.EsCritica, s.Etapa.EsHitoLegal));
            int N(Semaforo x) => estado.Count(s => s.Semaforo == x);
            ResumenSemaforos = $"Cumplidas {N(Semaforo.Cumplido)}  ·  En curso {N(Semaforo.EnCurso)}  ·  En alerta {N(Semaforo.Alerta)}  ·  Vencidas {N(Semaforo.Vencido)}";
            var prox = estado.Where(s => s.Etapa.FinReal is null).OrderBy(s => s.Etapa.FinPlan).FirstOrDefault();
            if (prox is not null) ProximoVencimiento = $"Próximo: {prox.Etapa.Nombre} — {prox.Etapa.FinPlan:dd/MM/yyyy}";

            var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault();
            if (ult is not null)
            {
                var r = System.Text.Json.JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson)!;
                string F(decimal v) => v.ToString("N2", Bo);
                Liquidacion.Add(new("Valor FOB", F(r.ValorFobBob))); Liquidacion.Add(new("(+) Adiciones", F(r.AdicionesBob)));
                Liquidacion.Add(new("(-) Deducciones", F(r.DeduccionesBob))); Liquidacion.Add(new("CIF aduana (Bs)", F(r.CifBob), true));
                Liquidacion.Add(new("Gravamen arancelario", F(r.GA))); Liquidacion.Add(new("ICE", F(r.ICE)));
                Liquidacion.Add(new("IEHD", F(r.IEHD))); Liquidacion.Add(new("IVA", F(r.IVA)));
                Liquidacion.Add(new("TOTAL TRIBUTOS", F(r.TotalTributos), true));
                var ufv = await _cfg.ObtenerUfvAsync(DateOnly.FromDateTime(ult.CalculadaEn));
                if (ufv is not null) Liquidacion.Add(new($"CIF en UFV (UFV {ufv.ValorBob.ToString("N5", Bo)})", Ufv.DeBob(r.CifBob, ufv.ValorBob).ToString("N2", Bo)));
                if (r.RequiereBancarizacion) Avisos.Add($"FOB desde Bs {(await _cfg.ObtenerParametrosAsync()).UmbralBancarizacionBob.ToString("N0", Bo)}: complete el respaldo bancario (D.S. 772).");
            }
            foreach (var (t, ok, m) in await _ops.ChecklistAsync(id)) Legajo.Add(new(NombreDocumento(t), ok, m));
            foreach (var e in op.Bitacora.OrderByDescending(e => e.Fecha).Take(100)) Bitacora.Add($"{e.Fecha:dd/MM HH:mm} · {e.Categoria} · {e.Detalle}" + (string.IsNullOrEmpty(e.Usuario) ? "" : $"  [{e.Usuario}]"));
            foreach (var c in await _costos.ListarAsync(id)) Costos.Add(new() { Id = c.Id, Concepto = c.Concepto, Proyectado = c.ProyectadoBob, Real = c.RealBob, Nota = c.Nota });
            RecalcularTotalesCostos();
        });
    }
}
