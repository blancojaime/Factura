using System.Collections.ObjectModel;
using System.Globalization;
using ComexBol.Core;
using ComexBol.Core.Catalogo;
using ComexBol.Data;
using ComexBol.Documentos;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Presentation;

// =====================================================================================================  INICIO DE SESIÓN
public sealed class LoginViewModel(ComexDb db) : ObservableObject
{
    readonly ServicioUsuarios _usr = new(db);
    bool _primer; public bool PrimerUso { get => _primer; private set => Set(ref _primer, value); }
    string _msg = ""; public string Mensaje { get => _msg; set => Set(ref _msg, value); }
    string _u = ""; public string Usuario { get => _u; set => Set(ref _u, value); }
    string _n = ""; public string NombreCompleto { get => _n; set => Set(ref _n, value); }

    public async Task InicializarAsync() => PrimerUso = !await _usr.HayUsuariosAsync();

    public async Task<Usuario?> IngresarAsync(string usuario, string clave)
    {
        Usuario? u = null;
        await DbGate.EjecutarAsync(async () => u = await _usr.AutenticarAsync(usuario, clave));
        Mensaje = u is null ? "Usuario o clave incorrectos, o usuario desactivado." : "";
        return u;
    }

    /// <summary>Primer uso: crea el administrador con el que se configura todo lo demás.</summary>
    public async Task<Usuario?> CrearAdministradorAsync(string usuario, string nombre, string clave, string repetir)
    {
        Usuario? u = null;
        try
        {
            if (clave != repetir) throw new ArgumentException("Las dos claves no coinciden.");
            await DbGate.EjecutarAsync(async () => u = await _usr.CrearAsync(usuario, nombre, clave, ServicioUsuarios.Administrador));
            Mensaje = "";
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException) { Mensaje = ex.Message; }
        return u;
    }
}

// =====================================================================================================  PANEL
public sealed record ProximoVencimiento(string Carpeta, string Etapa, string Fecha, string Estado, string ColorHex);

public sealed class PanelViewModel(ComexDb db, Func<DateOnly> hoy) : ObservableObject
{
    public ObservableCollection<ProximoVencimiento> Proximos { get; } = [];
    public ObservableCollection<string> Alertas { get; } = [];
    string _ops = "0"; public string TotalOperaciones { get => _ops; set => Set(ref _ops, value); }
    string _alerta = "0"; public string EtapasEnAlerta { get => _alerta; set => Set(ref _alerta, value); }
    string _venc = "0"; public string EtapasVencidas { get => _venc; set => Set(ref _venc, value); }
    string _arancel = ""; public string ArancelInfo { get => _arancel; set => Set(ref _arancel, value); }
    string _tc = ""; public string TipoCambioHoy { get => _tc; set => Set(ref _tc, value); }
    string _ufv = ""; public string UfvHoy { get => _ufv; set => Set(ref _ufv, value); }

    public Task RefrescarAsync() => DbGate.EjecutarAsync(async () =>
    {
        var h = hoy(); var ops = new ServicioOperaciones(db); var cfg = new ServicioConfiguracion(db); var cat = new ServicioCatalogo(db);
        Proximos.Clear(); Alertas.Clear();
        var operaciones = await db.Operaciones.AsNoTracking().OrderByDescending(o => o.Id).ToListAsync();
        TotalOperaciones = operaciones.Count.ToString();
        int alerta = 0, vencidas = 0; var todos = new List<(string Carpeta, EstadoEtapa E)>();
        foreach (var o in operaciones)
            foreach (var e in await ops.EstadoRutaAsync(o.Id, h))
            {
                if (e.Etapa.FinReal is not null) continue;
                if (e.Semaforo == Semaforo.Alerta) alerta++; else if (e.Semaforo == Semaforo.Vencido) vencidas++;
                todos.Add((o.Carpeta, e));
            }
        EtapasEnAlerta = alerta.ToString(); EtapasVencidas = vencidas.ToString();
        foreach (var (carpeta, e) in todos.Where(x => x.E.Semaforo is Semaforo.Vencido or Semaforo.Alerta).OrderBy(x => x.E.Etapa.FinPlan).Take(10))
            Proximos.Add(new(carpeta, $"{e.Etapa.Codigo} {e.Etapa.Nombre}", e.Etapa.FinPlan.ToString("dd/MM/yyyy"), e.Semaforo == Semaforo.Vencido ? "Vencida" : "En alerta", e.Semaforo == Semaforo.Vencido ? "#D64545" : "#E0A800"));

        var info = await cat.InfoAsync();
        ArancelInfo = info.Total == 0 ? "No cargado" : $"{info.Total.ToString("N0", Formato.Bo)} partidas · versión {info.Version}";
        var tc = await cfg.ObtenerTipoCambioAsync("USD", h);
        TipoCambioHoy = tc is null ? "Sin registrar" : $"Bs {tc.BobPorUnidad.ToString("N2", Formato.Bo)} (al {tc.Fecha:dd/MM/yyyy})";
        var ufv = await cfg.ObtenerUfvAsync(h);
        UfvHoy = ufv is null ? "Sin registrar" : $"Bs {ufv.ValorBob.ToString("N5", Formato.Bo)} (al {ufv.Fecha:dd/MM/yyyy})";

        if (info.Total == 0) Alertas.Add("El arancel no está cargado: vaya a «Arancel» e importe los PDF oficiales.");
        if (tc is null) Alertas.Add("No hay tipo de cambio registrado: agréguelo en Configuración → Tipos de cambio.");
        else if (tc.Fecha < h.AddDays(-7)) Alertas.Add($"El último tipo de cambio registrado es del {tc.Fecha:dd/MM/yyyy}: actualícelo.");
        if (vencidas > 0) Alertas.Add($"{vencidas} etapa(s) vencida(s) en sus operaciones.");
        if (!await db.Perfiles.AnyAsync()) Alertas.Add("Complete el perfil del importador en Configuración.");
    });
}

// =====================================================================================================  ARANCEL (TABLA DE PARTIDAS)
public sealed class CatalogoViewModel : ObservableObject
{
    readonly ComexDb _db; readonly ServicioCatalogo _cat;
    public CatalogoViewModel(ComexDb db)
    {
        _db = db; _cat = new(db);
        BuscarCmd = new(_ => BuscarAsync()); NuevaCmd = new(_ => { NuevaPartida(); return Task.CompletedTask; });
        GuardarCmd = new(_ => GuardarAsync(), _ => EditorAbierto); CancelarCmd = new(_ => { EditorAbierto = false; return Task.CompletedTask; });
    }

    public bool EsAdministrador { get; set; } = true;
    public ObservableCollection<PartidaCatalogo> Partidas { get; } = [];
    string _filtro = ""; public string Filtro { get => _filtro; set { if (Set(ref _filtro, value)) _ = BuscarAsync(); } }
    string _info = ""; public string Info { get => _info; set => Set(ref _info, value); }
    string _msg = ""; public string Mensaje { get => _msg; set => Set(ref _msg, value); }
    string _resumen = ""; public string Resumen { get => _resumen; set => Set(ref _resumen, value); }
    bool _arancelCargado; public bool ArancelCargado { get => _arancelCargado; private set => Set(ref _arancelCargado, value); }

    PartidaCatalogo? _sel; public PartidaCatalogo? Seleccionada { get => _sel; set { if (Set(ref _sel, value) && value is not null) CargarEnEditor(value); } }

    // Editor
    bool _editor; public bool EditorAbierto { get => _editor; set { if (Set(ref _editor, value)) GuardarCmd.Refresh(); } }
    bool _esNueva; public bool EsNueva { get => _esNueva; private set => Set(ref _esNueva, value); }
    string _cod = ""; public string Codigo { get => _cod; set => Set(ref _cod, value); }
    string _desc = ""; public string Descripcion { get => _desc; set => Set(ref _desc, value); }
    decimal _ga; public decimal GaPct { get => _ga; set => Set(ref _ga, value); }
    string _uni = ""; public string Unidad { get => _uni; set => Set(ref _uni, value); }
    string _tipo = ""; public string TipoDocumento { get => _tipo; set => Set(ref _tipo, value); }
    string _ent = ""; public string Entidad { get => _ent; set => Set(ref _ent, value); }
    string _leg = ""; public string DispLegal { get => _leg; set => Set(ref _leg, value); }
    bool _proh; public bool Prohibida { get => _proh; set => Set(ref _proh, value); }
    string _esp = ""; public string ImpuestoEspecial { get => _esp; set => Set(ref _esp, value); }
    public IReadOnlyList<string> ImpuestosEspeciales { get; } = ["", "ICE", "IEHD"];
    public IReadOnlyList<string> TiposDocumento { get; } = ["", "AP", "AP y C", "C", "C*", "DJ", "CITES", "CCRT", "CRTM", "P"];

    public RelayCommand BuscarCmd { get; }
    public RelayCommand NuevaCmd { get; }
    public RelayCommand GuardarCmd { get; }
    public RelayCommand CancelarCmd { get; }

    public Task CargarAsync() => BuscarAsync();

    public Task BuscarAsync() => DbGate.EjecutarAsync(async () =>
    {
        try
        {
            var info = await _cat.InfoAsync(); ArancelCargado = info.Total > 0;
            Info = info.Total == 0 ? "El arancel NO está cargado. Use «Importar arancel…» con los PDF oficiales."
                : $"{info.Total.ToString("N0", Formato.Bo)} partidas · versión {info.Version} · {info.Prohibidas} prohibidas · {info.ConIce} con ICE/IEHD · {info.Manuales} agregadas a mano";
            var res = await _cat.ListarAsync(Filtro, 300);
            Partidas.Clear(); foreach (var p in res) Partidas.Add(p);
            Resumen = info.Total == 0 ? "" : res.Count >= 300 ? "Se muestran las primeras 300: escriba más texto para afinar la búsqueda." : $"{res.Count} resultado(s)";
        }
        catch (Exception ex) when (ex is InvalidOperationException or DbUpdateException) { Mensaje = "AVISO: " + ex.Message; }
    });

    void CargarEnEditor(PartidaCatalogo p)
    {
        Codigo = p.Codigo; Descripcion = p.Descripcion; GaPct = p.AlicuotaGA * 100m; Unidad = p.Unidad; TipoDocumento = p.TipoDocumento; Entidad = p.Entidad;
        DispLegal = p.DispLegal; Prohibida = p.Prohibida; ImpuestoEspecial = p.ImpuestoEspecial; EsNueva = false; EditorAbierto = true; Mensaje = "";
    }

    void NuevaPartida()
    {
        _sel = null; PropiedadCambiada(nameof(Seleccionada));
        Codigo = Descripcion = Unidad = TipoDocumento = Entidad = DispLegal = ImpuestoEspecial = ""; GaPct = 0; Prohibida = false; EsNueva = true; EditorAbierto = true; Mensaje = "";
    }

    public Task GuardarAsync() => DbGate.EjecutarAsync(async () =>
    {
        try
        {
            var p = new PartidaCatalogo { Codigo = Codigo, Descripcion = Descripcion, AlicuotaGA = GaPct / 100m, Unidad = Unidad ?? "", TipoDocumento = TipoDocumento ?? "", Entidad = Entidad ?? "", DispLegal = DispLegal ?? "", Prohibida = Prohibida, ImpuestoEspecial = ImpuestoEspecial ?? "" };
            if (!EsNueva) { var actual = await _cat.ObtenerAsync(Codigo); if (actual is not null) { p.Autorizaciones = actual.Autorizaciones; p.PrefCan = actual.PrefCan; p.PrefChile = actual.PrefChile; p.PrefProtocolo = actual.PrefProtocolo; p.PrefMexico = actual.PrefMexico; p.IceAntiguedad = actual.IceAntiguedad; p.IceUltimaEsOMas = actual.IceUltimaEsOMas; p.DespachoFrontera = actual.DespachoFrontera; } }
            await _cat.GuardarPartidaAsync(p, EsNueva);
            Mensaje = EsNueva ? $"Partida {Codigo} agregada" : $"Partida {Codigo} actualizada"; EditorAbierto = false;
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or DbUpdateException) { Mensaje = "AVISO: " + ex.Message; return; }
        await BuscarAsync();
    });

    /// <summary>Elimina la partida seleccionada (la ventana pide confirmación antes de llamar).</summary>
    public Task EliminarAsync() => DbGate.EjecutarAsync(async () =>
    {
        if (Seleccionada is null) return;
        var cod = Seleccionada.Codigo; await _cat.EliminarPartidaAsync(cod); EditorAbierto = false; Mensaje = $"Partida {cod} eliminada";
    }).ContinueWith(_ => BuscarAsync()).Unwrap();

    /// <summary>Importa el arancel: los PDF oficiales (recomendado), los .md convertidos o un .csv simple. Reemplaza todo el catálogo.</summary>
    public async Task<ResumenImportacionCatalogo?> ImportarAsync(IReadOnlyList<string> rutas, string version)
    {
        ResumenImportacionCatalogo? res = null;
        try
        {
            Mensaje = "Importando arancel…";
            if (rutas.All(r => r.EndsWith(".pdf", StringComparison.OrdinalIgnoreCase)))
            {
                var avance = new Progress<string>(m => Mensaje = m);
                var leido = await Task.Run(() => ArancelPdf.Parsear(rutas.OrderBy(r => r, StringComparer.OrdinalIgnoreCase).ToList(), "ANB-" + version, avance));
                await DbGate.EjecutarAsync(async () => res = await _cat.ImportarResultadoAsync(leido, version));
            }
            else
            {
                var lectores = rutas.Select(r => (TextReader)new StreamReader(r)).ToList();
                try
                {
                    await DbGate.EjecutarAsync(async () => res = rutas.All(r => r.EndsWith(".md", StringComparison.OrdinalIgnoreCase))
                        ? await _cat.ImportarArancelMarkdownAsync(lectores, version) : await _cat.ImportarCsvAsync(lectores[0], version));
                }
                finally { foreach (var l in lectores) l.Dispose(); }
            }
            Mensaje = $"Arancel importado: {res!.Importadas} partidas, {res.Rechazadas} avisos/rechazos" + (res.SoloEjemplos ? " — SOLO DATOS DE EJEMPLO" : "");
            _filtro = ""; PropiedadCambiada(nameof(Filtro));          // tras importar se muestra la tabla completa
            await BuscarAsync();
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or IOException or DbUpdateException) { Mensaje = "AVISO: " + ex.Message; }
        return res;
    }
}

// =====================================================================================================  CONFIGURACIÓN
public sealed class ConfiguracionViewModel : ObservableObject
{
    readonly ComexDb _db; readonly ServicioConfiguracion _cfg; readonly ServicioUsuarios _usr; readonly Func<DateOnly> _hoy;
    public ConfiguracionViewModel(ComexDb db, Func<DateOnly>? hoy = null)
    {
        _db = db; _cfg = new(db); _usr = new(db); _hoy = hoy ?? (() => DateOnly.FromDateTime(DateTime.Today));
        TcFecha = UfvFecha = _hoy().ToDateTime(TimeOnly.MinValue);
        GuardarTcCmd = new(_ => GuardarTcAsync()); GuardarUfvCmd = new(_ => GuardarUfvAsync());
        GuardarParametrosCmd = new(_ => GuardarParametrosAsync()); RestaurarParametrosCmd = new(_ => RestaurarParametrosAsync());
        GuardarPerfilCmd = new(_ => GuardarPerfilAsync());
        AlternarActivoCmd = new(_ => AlternarActivoAsync());
    }
    public RelayCommand AlternarActivoCmd { get; }

    public bool EsAdministrador { get; set; } = true;
    public int UsuarioActualId { get; set; }
    string _msg = ""; public string Mensaje { get => _msg; set => Set(ref _msg, value); }
    string _ruta = ""; public string RutaBaseDatos { get => _ruta; set => Set(ref _ruta, value); }

    Task Seguro(Func<Task> a) => DbGate.EjecutarAsync(async () =>
    {
        try { await a(); }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException or DbUpdateException or IOException) { Mensaje = "AVISO: " + ex.Message; }
    });

    public Task CargarAsync() => Seguro(async () =>
    {
        await RecargarTcAsync(); await RecargarUfvAsync(); await CargarParametrosAsync(); await CargarPerfilAsync(); await RecargarUsuariosAsync();
    });

    // ---------- Tipos de cambio ----------
    public ObservableCollection<TipoCambioRegistro> TiposCambio { get; } = [];
    public IReadOnlyList<string> Monedas => ServicioConfiguracion.Monedas;
    DateTime _tcF; public DateTime TcFecha { get => _tcF; set => Set(ref _tcF, value); }
    string _tcM = "USD"; public string TcMoneda { get => _tcM; set => Set(ref _tcM, value); }
    decimal _tcV; public decimal TcValor { get => _tcV; set => Set(ref _tcV, value); }
    string _tcFu = "BCB"; public string TcFuente { get => _tcFu; set => Set(ref _tcFu, value); }
    TipoCambioRegistro? _tcSel; public TipoCambioRegistro? TcSeleccionado { get => _tcSel; set { if (Set(ref _tcSel, value) && value is not null) { TcFecha = value.Fecha.ToDateTime(TimeOnly.MinValue); TcMoneda = value.Moneda; TcValor = value.BobPorUnidad; TcFuente = value.Fuente; } } }
    public RelayCommand GuardarTcCmd { get; }
    async Task RecargarTcAsync() { TiposCambio.Clear(); foreach (var t in await _cfg.ListarTiposCambioAsync()) TiposCambio.Add(t); }
    public Task GuardarTcAsync() => Seguro(async () => { await _cfg.GuardarTipoCambioAsync(DateOnly.FromDateTime(TcFecha), TcMoneda, TcValor, TcFuente); await RecargarTcAsync(); Mensaje = $"Tipo de cambio {TcMoneda} guardado"; });
    public Task EliminarTcAsync() => Seguro(async () => { if (TcSeleccionado is null) return; await _cfg.EliminarTipoCambioAsync(TcSeleccionado.Id); await RecargarTcAsync(); Mensaje = "Tipo de cambio eliminado"; });

    // ---------- UFV ----------
    public ObservableCollection<UfvRegistro> Ufvs { get; } = [];
    DateTime _uF; public DateTime UfvFecha { get => _uF; set => Set(ref _uF, value); }
    decimal _uV; public decimal UfvValor { get => _uV; set => Set(ref _uV, value); }
    UfvRegistro? _uSel; public UfvRegistro? UfvSeleccionada { get => _uSel; set { if (Set(ref _uSel, value) && value is not null) { UfvFecha = value.Fecha.ToDateTime(TimeOnly.MinValue); UfvValor = value.ValorBob; } } }
    public RelayCommand GuardarUfvCmd { get; }
    async Task RecargarUfvAsync() { Ufvs.Clear(); foreach (var u in await _cfg.ListarUfvAsync()) Ufvs.Add(u); }
    public Task GuardarUfvAsync() => Seguro(async () => { await _cfg.GuardarUfvAsync(DateOnly.FromDateTime(UfvFecha), UfvValor); await RecargarUfvAsync(); Mensaje = "UFV guardada"; });
    public Task EliminarUfvAsync() => Seguro(async () => { if (UfvSeleccionada is null) return; await _cfg.EliminarUfvAsync(UfvSeleccionada.Id); await RecargarUfvAsync(); Mensaje = "UFV eliminada"; });

    // ---------- Parámetros tributarios ----------
    decimal _iva; public decimal IvaPct { get => _iva; set => Set(ref _iva, value); }
    decimal _umb; public decimal UmbralBancarizacion { get => _umb; set => Set(ref _umb, value); }
    decimal _seg; public decimal SeguroPresuntoPct { get => _seg; set => Set(ref _seg, value); }
    decimal _maxGa; public decimal MaxGaPct { get => _maxGa; set => Set(ref _maxGa, value); }
    public IReadOnlyList<string> Redondeos { get; } = ["DosDecimales", "EnteroBs"];
    public IReadOnlyList<string> Prorrateos { get; } = ["PorValor", "PorPesoBruto"];
    string _red = "DosDecimales"; public string Redondeo { get => _red; set => Set(ref _red, value); }
    string _pro = "PorValor"; public string Prorrateo { get => _pro; set => Set(ref _pro, value); }
    public RelayCommand GuardarParametrosCmd { get; }
    public RelayCommand RestaurarParametrosCmd { get; }
    void Mostrar(ParametrosTributarios p) { IvaPct = p.TasaIvaEfectiva * 100m; UmbralBancarizacion = p.UmbralBancarizacionBob; SeguroPresuntoPct = p.SeguroPresuntoPct * 100m; MaxGaPct = p.MaxAlicuotaGA * 100m; Redondeo = p.Redondeo.ToString(); Prorrateo = p.Prorrateo.ToString(); }
    async Task CargarParametrosAsync() => Mostrar(await _cfg.ObtenerParametrosAsync());
    public Task GuardarParametrosAsync() => Seguro(async () =>
    {
        await _cfg.GuardarParametrosAsync(new ParametrosTributarios { TasaIvaEfectiva = IvaPct / 100m, UmbralBancarizacionBob = UmbralBancarizacion, SeguroPresuntoPct = SeguroPresuntoPct / 100m, MaxAlicuotaGA = MaxGaPct / 100m,
            Redondeo = Enum.Parse<ModoRedondeo>(Redondeo), Prorrateo = Enum.Parse<CriterioProrrateo>(Prorrateo) });
        Mensaje = "Parámetros guardados: se aplican a los próximos cálculos";
    });
    public Task RestaurarParametrosAsync() => Seguro(async () => { var d = new ParametrosTributarios(); Mostrar(d); await _cfg.GuardarParametrosAsync(d); Mensaje = "Parámetros restaurados a los valores por defecto"; });

    // ---------- Perfil del importador ----------
    string _rs = ""; public string RazonSocial { get => _rs; set => Set(ref _rs, value); }
    string _nit = ""; public string Nit { get => _nit; set => Set(ref _nit, value); }
    string _ti = "Habitual"; public string TipoImportador { get => _ti; set => Set(ref _ti, value); }
    public IReadOnlyList<string> TiposImportador { get; } = ["Habitual", "Ocasional"];
    string _dir = ""; public string Direccion { get => _dir; set => Set(ref _dir, value); }
    string _ciu = ""; public string Ciudad { get => _ciu; set => Set(ref _ciu, value); }
    string _tel = ""; public string Telefono { get => _tel; set => Set(ref _tel, value); }
    string _cor = ""; public string Correo { get => _cor; set => Set(ref _cor, value); }
    string _ag = ""; public string AgenciaDespachante { get => _ag; set => Set(ref _ag, value); }
    public RelayCommand GuardarPerfilCmd { get; }
    async Task CargarPerfilAsync() { var p = await _cfg.ObtenerPerfilAsync(); RazonSocial = p.RazonSocial; Nit = p.Nit; TipoImportador = p.TipoImportador; Direccion = p.Direccion; Ciudad = p.Ciudad; Telefono = p.Telefono; Correo = p.Correo; AgenciaDespachante = p.AgenciaDespachante; }
    public Task GuardarPerfilAsync() => Seguro(async () =>
    {
        await _cfg.GuardarPerfilAsync(new() { RazonSocial = RazonSocial ?? "", Nit = Nit ?? "", TipoImportador = TipoImportador, Direccion = Direccion ?? "", Ciudad = Ciudad ?? "", Telefono = Telefono ?? "", Correo = Correo ?? "", AgenciaDespachante = AgenciaDespachante ?? "" });
        Mensaje = "Perfil del importador guardado";
    });

    // ---------- Usuarios ----------
    public ObservableCollection<Usuario> Usuarios { get; } = [];
    public IReadOnlyList<string> Roles { get; } = [ServicioUsuarios.Administrador, ServicioUsuarios.Operador];
    Usuario? _uS; public Usuario? UsuarioSeleccionado { get => _uS; set => Set(ref _uS, value); }
    async Task RecargarUsuariosAsync() { Usuarios.Clear(); foreach (var u in await _usr.ListarAsync()) Usuarios.Add(u); }
    public Task CrearUsuarioAsync(string usuario, string nombre, string clave, string rol) => Seguro(async () =>
    { await _usr.CrearAsync(usuario, nombre, clave, rol); await RecargarUsuariosAsync(); Mensaje = $"Usuario «{usuario.Trim().ToLowerInvariant()}» creado"; });
    public Task CambiarClaveAsync(string nueva) => Seguro(async () =>
    { if (UsuarioSeleccionado is null) throw new InvalidOperationException("Seleccione un usuario."); await _usr.CambiarClaveAsync(UsuarioSeleccionado.Id, nueva); Mensaje = $"Clave de «{UsuarioSeleccionado.NombreUsuario}» cambiada"; });
    public Task AlternarActivoAsync() => Seguro(async () =>
    {
        var u = UsuarioSeleccionado ?? throw new InvalidOperationException("Seleccione un usuario.");
        if (u.Id == UsuarioActualId && u.Activo) throw new InvalidOperationException("No puede desactivar su propio usuario mientras lo usa.");
        var id = u.Id; await _usr.SetActivoAsync(id, !u.Activo); await RecargarUsuariosAsync(); Mensaje = "Usuario actualizado";
    });
    public Task CambiarRolAsync(string rol) => Seguro(async () =>
    {
        var u = UsuarioSeleccionado ?? throw new InvalidOperationException("Seleccione un usuario.");
        await _usr.CambiarRolAsync(u.Id, rol); await RecargarUsuariosAsync(); Mensaje = "Rol actualizado";
    });

    // ---------- Respaldo ----------
    public Task RespaldarAsync(string destino) => Seguro(async () => { await _cfg.RespaldarAsync(destino); Mensaje = $"Respaldo guardado en {destino}"; });
}

// =====================================================================================================  CASCARÓN (MENÚ + SESIÓN)
public sealed class ShellViewModel : ObservableObject
{
    public ShellViewModel(ComexDb db, Usuario usuario, Func<DateOnly>? hoy = null, IMotorOcr? ocr = null)
    {
        var h = hoy ?? (() => DateOnly.FromDateTime(DateTime.Today));
        Usuario = usuario; EsAdministrador = usuario.Rol == ServicioUsuarios.Administrador;
        Operaciones = new MainViewModel(db, h, ocr) { UsuarioActual = usuario.NombreUsuario };
        Catalogo = new CatalogoViewModel(db) { EsAdministrador = EsAdministrador };
        Config = new ConfiguracionViewModel(db, h) { EsAdministrador = EsAdministrador, UsuarioActualId = usuario.Id };
        Panel = new PanelViewModel(db, h);
        IrCmd = new(p => Navegar((string)p!));
        CerrarSesionCmd = new(_ => { CerrarSesionSolicitada?.Invoke(); return Task.CompletedTask; });
    }

    public Usuario Usuario { get; }
    public bool EsAdministrador { get; }
    public string NombreMostrado => string.IsNullOrWhiteSpace(Usuario.NombreCompleto) ? Usuario.NombreUsuario : Usuario.NombreCompleto;
    public string RolMostrado => Usuario.Rol;
    public MainViewModel Operaciones { get; }
    public CatalogoViewModel Catalogo { get; }
    public ConfiguracionViewModel Config { get; }
    public PanelViewModel Panel { get; }
    public RelayCommand IrCmd { get; }
    public RelayCommand CerrarSesionCmd { get; }
    public event Action? CerrarSesionSolicitada;

    string _seccion = "Panel"; public string Seccion { get => _seccion; private set { if (Set(ref _seccion, value)) { PropiedadCambiada(nameof(EsPanel)); PropiedadCambiada(nameof(EsOperaciones)); PropiedadCambiada(nameof(EsArancel)); PropiedadCambiada(nameof(EsConfiguracion)); PropiedadCambiada(nameof(EsAcerca)); } } }
    public bool EsPanel => Seccion == "Panel";
    public bool EsOperaciones => Seccion == "Operaciones";
    public bool EsArancel => Seccion == "Arancel";
    public bool EsConfiguracion => Seccion == "Configuración";
    public bool EsAcerca => Seccion == "Acerca";

    public async Task InicializarAsync()
    {
        await Operaciones.CargarAsync(); await Panel.RefrescarAsync(); await Catalogo.CargarAsync(); await Config.CargarAsync();
    }

    public async Task Navegar(string seccion)
    {
        Seccion = seccion;
        switch (seccion)
        {
            case "Panel": await Panel.RefrescarAsync(); break;
            case "Operaciones": await Operaciones.CargarAsync(); break;
            case "Arancel": await Catalogo.CargarAsync(); break;
            case "Configuración": await Config.CargarAsync(); break;
        }
    }
}
