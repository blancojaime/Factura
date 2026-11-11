using System.Globalization;
using ComexBol.Core;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

public sealed record AjustesOperativos(decimal AlmacenTarifaBsTonDia = 0m, int AlmacenDiasLibres = 0, decimal TolerancePrecio = 0.30m, decimal TolerancePeso = 0.05m, bool IvaRecuperable = true);

/// <summary>Mantenimiento de tipos de cambio, UFV, parámetros tributarios, perfil del importador y respaldo.</summary>
public sealed class ServicioConfiguracion(ComexDb db)
{
    static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
    public static readonly string[] Monedas = ["USD", "EUR", "BRL", "ARS", "CLP", "PEN", "CNY", "JPY", "GBP", "MXN"];

    // ---------- Tipos de cambio ----------
    public Task<List<TipoCambioRegistro>> ListarTiposCambioAsync(string? moneda = null, int max = 500) =>
        db.TiposCambio.AsNoTracking().Where(t => moneda == null || t.Moneda == moneda).OrderByDescending(t => t.Fecha).ThenBy(t => t.Moneda).Take(max).ToListAsync();

    public async Task<TipoCambioRegistro> GuardarTipoCambioAsync(DateOnly fecha, string moneda, decimal valor, string fuente = "Manual")
    {
        moneda = (moneda ?? "").Trim().ToUpperInvariant();
        if (moneda.Length != 3) throw new ArgumentException("Indique la moneda (código de 3 letras, p. ej. USD).");
        if (valor <= 0) throw new ArgumentException("El tipo de cambio debe ser mayor que cero.");
        if (valor > 1000) throw new ArgumentException("El tipo de cambio parece demasiado alto: revise que sean bolivianos por una unidad de moneda.");
        var r = await db.TiposCambio.FirstOrDefaultAsync(t => t.Fecha == fecha && t.Moneda == moneda);
        if (r is null) { r = new() { Fecha = fecha, Moneda = moneda }; db.TiposCambio.Add(r); }
        r.BobPorUnidad = valor; r.Fuente = string.IsNullOrWhiteSpace(fuente) ? "Manual" : fuente;
        await db.SaveChangesAsync(); return r;
    }

    public async Task EliminarTipoCambioAsync(int id)
    {
        var r = await db.TiposCambio.FindAsync(id); if (r is null) return;
        db.TiposCambio.Remove(r); await db.SaveChangesAsync();
    }

    /// <summary>Tipo de cambio vigente a una fecha: el más reciente con fecha menor o igual (null si no hay ninguno).</summary>
    public Task<TipoCambioRegistro?> ObtenerTipoCambioAsync(string moneda, DateOnly fecha) =>
        db.TiposCambio.AsNoTracking().Where(t => t.Moneda == moneda && t.Fecha <= fecha).OrderByDescending(t => t.Fecha).FirstOrDefaultAsync();

    // ---------- UFV ----------
    public Task<List<UfvRegistro>> ListarUfvAsync(int max = 500) => db.Ufvs.AsNoTracking().OrderByDescending(u => u.Fecha).Take(max).ToListAsync();

    public async Task<UfvRegistro> GuardarUfvAsync(DateOnly fecha, decimal valor)
    {
        if (valor <= 0 || valor > 100) throw new ArgumentException("El valor de la UFV debe estar entre 0 y 100 Bs (p. ej. 2,5).");
        var r = await db.Ufvs.FirstOrDefaultAsync(u => u.Fecha == fecha);
        if (r is null) { r = new() { Fecha = fecha }; db.Ufvs.Add(r); }
        r.ValorBob = valor; await db.SaveChangesAsync(); return r;
    }

    public async Task EliminarUfvAsync(int id)
    {
        var r = await db.Ufvs.FindAsync(id); if (r is null) return;
        db.Ufvs.Remove(r); await db.SaveChangesAsync();
    }

    public Task<UfvRegistro?> ObtenerUfvAsync(DateOnly fecha) =>
        db.Ufvs.AsNoTracking().Where(u => u.Fecha <= fecha).OrderByDescending(u => u.Fecha).FirstOrDefaultAsync();

    // ---------- Parámetros tributarios ----------
    const string KIva = "tasa_iva_efectiva", KUmbral = "umbral_bancarizacion", KRedondeo = "redondeo", KSeguro = "seguro_presunto_pct", KProrrateo = "prorrateo", KMaxGa = "max_alicuota_ga";

    public async Task<ParametrosTributarios> ObtenerParametrosAsync()
    {
        var d = await db.Parametros.AsNoTracking().ToDictionaryAsync(p => p.Clave, p => p.Valor);
        var def = new ParametrosTributarios();
        decimal Dec(string k, decimal x) => d.TryGetValue(k, out var v) && decimal.TryParse(v, NumberStyles.Number, Inv, out var r) ? r : x;
        return def with
        {
            TasaIvaEfectiva = Dec(KIva, def.TasaIvaEfectiva), UmbralBancarizacionBob = Dec(KUmbral, def.UmbralBancarizacionBob),
            SeguroPresuntoPct = Dec(KSeguro, def.SeguroPresuntoPct), MaxAlicuotaGA = Dec(KMaxGa, def.MaxAlicuotaGA),
            Redondeo = d.TryGetValue(KRedondeo, out var r) && Enum.TryParse<ModoRedondeo>(r, out var rr) ? rr : def.Redondeo,
            Prorrateo = d.TryGetValue(KProrrateo, out var pr) && Enum.TryParse<CriterioProrrateo>(pr, out var pp) ? pp : def.Prorrateo
        };
    }

    public async Task GuardarParametrosAsync(ParametrosTributarios p)
    {
        if (p.TasaIvaEfectiva is <= 0 or >= 1) throw new ArgumentException("El IVA efectivo debe estar entre 0 % y 100 % (p. ej. 14,94 % = 0,1494).");
        if (p.UmbralBancarizacionBob < 0) throw new ArgumentException("El umbral de bancarización no puede ser negativo.");
        if (p.SeguroPresuntoPct is < 0 or > 0.2m) throw new ArgumentException("El seguro presunto debe estar entre 0 % y 20 %.");
        if (p.MaxAlicuotaGA is <= 0 or > 1) throw new ArgumentException("La alícuota máxima del GA debe estar entre 0 % y 100 %.");
        await Poner(KIva, p.TasaIvaEfectiva.ToString(Inv), "IVA efectivo en importaciones (fracción: 0,1494 = 14,94 %)");
        await Poner(KUmbral, p.UmbralBancarizacionBob.ToString(Inv), "Monto desde el cual se exige respaldo bancario (D.S. 772), en Bs");
        await Poner(KSeguro, p.SeguroPresuntoPct.ToString(Inv), "Seguro presunto sobre FOB cuando no se declara (fracción)");
        await Poner(KMaxGa, p.MaxAlicuotaGA.ToString(Inv), "Alícuota máxima aceptada del gravamen arancelario (fracción)");
        await Poner(KRedondeo, p.Redondeo.ToString(), "Redondeo de tributos: DosDecimales | EnteroBs");
        await Poner(KProrrateo, p.Prorrateo.ToString(), "Reparto de flete/seguro entre ítems: PorValor | PorPesoBruto");
        await db.SaveChangesAsync();
    }

    // ---------- Ajustes operativos (almacén, tolerancias, crédito fiscal) ----------
    public async Task<AjustesOperativos> ObtenerAjustesAsync()
    {
        var d = await db.Parametros.AsNoTracking().ToDictionaryAsync(p => p.Clave, p => p.Valor);
        var def = new AjustesOperativos();
        decimal Dec(string k, decimal x) => d.TryGetValue(k, out var v) && decimal.TryParse(v, NumberStyles.Number, Inv, out var r) ? r : x;
        return new(Dec("almacen_tarifa_ton_dia", def.AlmacenTarifaBsTonDia), (int)Dec("almacen_dias_libres", def.AlmacenDiasLibres),
            Dec("tolerancia_precio", def.TolerancePrecio), Dec("tolerancia_peso", def.TolerancePeso), Dec("iva_recuperable", def.IvaRecuperable ? 1 : 0) != 0);
    }

    public async Task GuardarAjustesAsync(AjustesOperativos a)
    {
        if (a.AlmacenTarifaBsTonDia < 0 || a.AlmacenDiasLibres < 0) throw new ArgumentException("La tarifa y los días libres de almacén no pueden ser negativos.");
        if (a.TolerancePrecio is <= 0 or > 2) throw new ArgumentException("La tolerancia de precio debe estar entre 0 % y 200 %.");
        if (a.TolerancePeso is <= 0 or > 1) throw new ArgumentException("La tolerancia de peso debe estar entre 0 % y 100 %.");
        await Poner("almacen_tarifa_ton_dia", a.AlmacenTarifaBsTonDia.ToString(Inv), "Tarifa de almacenaje del recinto, Bs por tonelada y día (la fija el concesionario)");
        await Poner("almacen_dias_libres", a.AlmacenDiasLibres.ToString(Inv), "Días de almacenaje sin cobro");
        await Poner("tolerancia_precio", a.TolerancePrecio.ToString(Inv), "Desviación del precio unitario frente al historial desde la cual hay riesgo de duda razonable (fracción)");
        await Poner("tolerancia_peso", a.TolerancePeso.ToString(Inv), "Diferencia aceptada entre el peso de los ítems y el del manifiesto (fracción)");
        await Poner("iva_recuperable", a.IvaRecuperable ? "1" : "0", "El IVA de importación se recupera como crédito fiscal (1) o es costo (0)");
        await db.SaveChangesAsync();
    }

    async Task Poner(string clave, string valor, string descripcion)
    {
        var p = await db.Parametros.FindAsync(clave);
        if (p is null) db.Parametros.Add(new() { Clave = clave, Valor = valor, Descripcion = descripcion }); else { p.Valor = valor; p.Descripcion = descripcion; }
    }

    // ---------- Perfil del importador ----------
    public async Task<PerfilImportador> ObtenerPerfilAsync() => await db.Perfiles.AsNoTracking().FirstOrDefaultAsync() ?? new PerfilImportador();

    public async Task GuardarPerfilAsync(PerfilImportador perfil)
    {
        if (perfil.TipoImportador is not ("Habitual" or "Ocasional")) throw new ArgumentException("El tipo de importador debe ser Habitual u Ocasional.");
        var actual = await db.Perfiles.FirstOrDefaultAsync();
        if (actual is null) { perfil.Id = 0; db.Perfiles.Add(perfil); }
        else
        {
            actual.RazonSocial = perfil.RazonSocial.Trim(); actual.Nit = perfil.Nit.Trim(); actual.TipoImportador = perfil.TipoImportador; actual.Direccion = perfil.Direccion;
            actual.Ciudad = perfil.Ciudad; actual.Telefono = perfil.Telefono; actual.Correo = perfil.Correo; actual.AgenciaDespachante = perfil.AgenciaDespachante;
        }
        await db.SaveChangesAsync();
    }

    // ---------- Respaldo ----------
    /// <summary>Copia consistente de toda la base (operaciones, arancel, configuración) en un archivo nuevo.</summary>
    public async Task RespaldarAsync(string destino)
    {
        if (string.IsNullOrWhiteSpace(destino)) throw new ArgumentException("Indique el archivo de destino.");
        if (File.Exists(destino)) File.Delete(destino);
        await db.Database.ExecuteSqlRawAsync($"VACUUM INTO '{destino.Replace("'", "''")}'");
    }
}
