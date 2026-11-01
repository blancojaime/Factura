namespace ComexBol.Core;

public enum Incoterm { EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DAP, DPU, DDP }

/// <summary>Qué componentes ya vienen incluidos en el precio de factura según el Incoterm 2020.</summary>
public readonly record struct IncotermCobertura(
    bool Origen,      // carga/despacho de exportación en origen
    bool Flete,       // transporte principal
    bool Seguro,
    bool Destino);    // costos posteriores al ingreso a Bolivia (descarga, transporte interno, y en DDP, tributos)

public static class IncotermRules
{
    public static IncotermCobertura Cobertura(Incoterm i) => i switch
    {
        Incoterm.EXW => new(false, false, false, false),
        Incoterm.FCA or Incoterm.FAS or Incoterm.FOB => new(true, false, false, false),
        Incoterm.CFR or Incoterm.CPT => new(true, true, false, false),
        Incoterm.CIF or Incoterm.CIP => new(true, true, true, false),
        // El vendedor asume riesgo hasta destino: se trata el seguro como incluido (se advierte al usuario).
        Incoterm.DAP or Incoterm.DPU or Incoterm.DDP => new(true, true, true, true),
        _ => throw new ArgumentOutOfRangeException(nameof(i))
    };
}
