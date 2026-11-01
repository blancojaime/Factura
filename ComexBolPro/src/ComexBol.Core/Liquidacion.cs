namespace ComexBol.Core;

public enum CriterioProrrateo { PorValor, PorPesoBruto }
public enum ModoRedondeo { DosDecimales, EnteroBs }

/// <summary>
/// Parámetros normativos. Son DATOS, no constantes de código: cambian por decreto y deben
/// versionarse en la tabla ParametrosNormativos (con vigencia) y validarse con el contador/despachante.
/// </summary>
public sealed record ParametrosTributarios
{
    /// <summary>IVA efectivo aduanero (13% nominal / 0.87 ≈ 14.94%).</summary>
    public decimal TasaIvaEfectiva { get; init; } = 0.1494m;
    public decimal MaxAlicuotaGA { get; init; } = 0.40m;
    public CriterioProrrateo Prorrateo { get; init; } = CriterioProrrateo.PorValor;
    public ModoRedondeo Redondeo { get; init; } = ModoRedondeo.DosDecimales;
    /// <summary>Umbral de bancarización (D.S. 772), en Bs.</summary>
    public decimal UmbralBancarizacionBob { get; init; } = 50_000m;
    /// <summary>Si no se declara seguro y el Incoterm no lo incluye: % presunto sobre FOB (0 = solo advertir).</summary>
    public decimal SeguroPresuntoPct { get; init; } = 0m;
}

public sealed record ItemImportacion(
    int Numero,
    string CodigoArancelario,          // NANDINA 10 dígitos
    string Descripcion,
    decimal ValorFactura,              // en la moneda de la factura
    decimal PesoBrutoKg,
    decimal PesoNetoKg,
    decimal AlicuotaGA,                // 0..0.40 (arancel general del NANDINA)
    decimal DesgravacionPreferencial = 0m, // 0..1 (p. ej. 1 = 100% desgravado por ACE/CAN)
    decimal AlicuotaIceAdValorem = 0m,
    decimal IceEspecificoPorUnidad = 0m,   // Bs por unidad
    decimal UnidadesIce = 0m,
    decimal IehdBsPorLitro = 0m,
    decimal Litros = 0m);

public sealed record OperacionImportacion(
    Incoterm Incoterm,
    string MonedaFactura,
    IReadOnlyList<ItemImportacion> Items,
    Money? GastosOrigen = null,              // EXW/FCA... hasta puerto/embarque
    Money? Flete = null,
    Money? Seguro = null,
    Money? OtrosGastosHastaFrontera = null,  // ASP-B, tránsito hasta frontera boliviana, etc.
    Money? DeduccionesPostFrontera = null,   // DAP/DPU/DDP: transporte interno, tributos incluidos en el precio
    decimal OtrasErogacionesBob = 0m);

public sealed record ItemLiquidado(
    int Numero, string CodigoArancelario,
    decimal ValorFobBob, decimal CifBob,
    decimal GA, decimal ICE, decimal IEHD, decimal OtrasErogaciones, decimal IVA)
{
    public decimal TotalTributos => GA + ICE + IEHD + IVA;
}

public sealed record LiquidacionResultado(
    decimal ValorFobBob,
    decimal AdicionesBob,
    decimal DeduccionesBob,
    decimal CifBob,
    decimal GA, decimal ICE, decimal IEHD, decimal IVA,
    decimal TotalTributos,
    bool RequiereBancarizacion,
    IReadOnlyList<ItemLiquidado> Items,
    IReadOnlyList<string> Advertencias);

public static class CalculadoraTributaria
{
    /// <summary>
    /// Liquidación de importación para el consumo.
    ///   Valor en aduana (CIF frontera) = Σ valor factura + adiciones no incluidas en el Incoterm − deducciones post-frontera
    ///   GA   = CIF_i × alícuota × (1 − desgravación preferencial)
    ///   ICE  = (CIF_i + GA_i) × alícuota ad valorem + tasa específica × unidades
    ///   IEHD = Bs/litro × litros
    ///   IVA  = TasaIvaEfectiva × (CIF_i + GA_i + ICE_i + IEHD_i + otras erogaciones_i)
    /// Los costos comunes se prorratean por ítem (valor o peso) y cada tributo se redondea por ítem; los totales son sumas.
    /// </summary>
    public static LiquidacionResultado Calcular(OperacionImportacion op, TipoCambioTable tc, ParametrosTributarios? p = null)
    {
        p ??= new();
        var adv = new List<string>();
        Validar(op, p);

        decimal R(decimal x) => p.Redondeo == ModoRedondeo.EnteroBs
            ? Math.Round(x, 0, MidpointRounding.AwayFromZero)
            : Math.Round(x, 2, MidpointRounding.AwayFromZero);
        decimal Bob(Money? m) => m is null ? 0m : tc.ABob(m);

        var cob = IncotermRules.Cobertura(op.Incoterm);
        var fobBob = op.Items.Sum(i => tc.ABob(new Money(i.ValorFactura, op.MonedaFactura)));

        // --- Adiciones: solo lo que el precio de factura NO incluye según el Incoterm ---
        decimal adiciones = 0m;
        void Adicionar(bool incluido, Money? monto, string nombre)
        {
            var bob = Bob(monto);
            if (incluido) { if (bob > 0) adv.Add($"{nombre} ignorado: ya incluido en el precio por Incoterm {op.Incoterm}."); return; }
            adiciones += bob;
        }
        Adicionar(cob.Origen, op.GastosOrigen, "Gastos de origen");
        Adicionar(cob.Flete, op.Flete, "Flete");
        if (!cob.Seguro && Bob(op.Seguro) == 0m)
        {
            if (p.SeguroPresuntoPct > 0) { adiciones += fobBob * p.SeguroPresuntoPct; adv.Add($"Seguro no declarado: se aplicó {p.SeguroPresuntoPct:P2} presunto."); }
            else adv.Add("Seguro no declarado: verifique póliza/certificado de transporte.");
        }
        else Adicionar(cob.Seguro, op.Seguro, "Seguro");
        // Gastos entre puerto de tránsito y frontera: siempre por cuenta del importador salvo que el vendedor los cubra (DAP/DPU/DDP).
        Adicionar(cob.Destino, op.OtrosGastosHastaFrontera, "Gastos hasta frontera");
        var deducciones = cob.Destino ? Bob(op.DeduccionesPostFrontera) : 0m;
        if (!cob.Destino && Bob(op.DeduccionesPostFrontera) > 0) adv.Add("Deducciones post-frontera ignoradas: solo aplican a DAP/DPU/DDP.");
        if (cob.Destino && deducciones == 0m) adv.Add($"Incoterm {op.Incoterm}: declare los costos posteriores a la frontera (y tributos en DDP) para excluirlos del valor en aduana.");

        var neto = adiciones - deducciones;
        var cifTotal = fobBob + neto;
        if (cifTotal <= 0) throw new InvalidOperationException("Valor en aduana no positivo tras deducciones.");

        // --- Prorrateo ---
        var pesoTotal = op.Items.Sum(i => i.PesoBrutoKg);
        bool porPeso = p.Prorrateo == CriterioProrrateo.PorPesoBruto && pesoTotal > 0;
        if (p.Prorrateo == CriterioProrrateo.PorPesoBruto && !porPeso) adv.Add("Sin pesos: prorrateo por valor.");

        var items = new List<ItemLiquidado>();
        foreach (var it in op.Items)
        {
            var fobI = tc.ABob(new Money(it.ValorFactura, op.MonedaFactura));
            var cuota = porPeso ? it.PesoBrutoKg / pesoTotal : fobI / fobBob;
            var cif = R(fobI + neto * cuota);
            var ga = R(cif * it.AlicuotaGA * (1m - it.DesgravacionPreferencial));
            var ice = R((cif + ga) * it.AlicuotaIceAdValorem + it.IceEspecificoPorUnidad * it.UnidadesIce);
            var iehd = R(it.IehdBsPorLitro * it.Litros);
            var otras = op.OtrasErogacionesBob * (cif / cifTotal);
            var iva = R(p.TasaIvaEfectiva * (cif + ga + ice + iehd + otras));
            items.Add(new(it.Numero, it.CodigoArancelario, R(fobI), cif, ga, ice, iehd, R(otras), iva));
        }

        var ga_ = items.Sum(i => i.GA); var ice_ = items.Sum(i => i.ICE);
        var iehd_ = items.Sum(i => i.IEHD); var iva_ = items.Sum(i => i.IVA);
        return new(R(fobBob), R(adiciones), R(deducciones), items.Sum(i => i.CifBob),
            ga_, ice_, iehd_, iva_, ga_ + ice_ + iehd_ + iva_,
            Bancarizacion.Requiere(fobBob, p), items, adv);
    }

    private static void Validar(OperacionImportacion op, ParametrosTributarios p)
    {
        if (op.Items.Count == 0) throw new ArgumentException("La operación no tiene ítems.");
        foreach (var i in op.Items)
        {
            if (i.CodigoArancelario.Length != 10 || !i.CodigoArancelario.All(char.IsDigit))
                throw new ArgumentException($"Ítem {i.Numero}: la partida NANDINA debe tener 10 dígitos.");
            if (i.ValorFactura <= 0) throw new ArgumentException($"Ítem {i.Numero}: valor de factura debe ser > 0.");
            if (i.AlicuotaGA < 0 || i.AlicuotaGA > p.MaxAlicuotaGA) throw new ArgumentException($"Ítem {i.Numero}: alícuota GA fuera de 0–{p.MaxAlicuotaGA:P0}.");
            if (i.DesgravacionPreferencial is < 0 or > 1) throw new ArgumentException($"Ítem {i.Numero}: desgravación fuera de 0–100%.");
        }
    }
}

public static class Bancarizacion
{
    /// <summary>D.S. 772: operaciones desde Bs 50.000 requieren respaldo de pago por entidad financiera.</summary>
    public static bool Requiere(decimal valorFobBob, ParametrosTributarios? p = null)
        => valorFobBob >= (p ?? new()).UmbralBancarizacionBob;
}
