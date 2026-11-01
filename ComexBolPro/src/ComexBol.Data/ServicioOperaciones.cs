using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ComexBol.Core;
using Microsoft.EntityFrameworkCore;

namespace ComexBol.Data;

public sealed record EstadoEtapa(EtapaRuta Etapa, Semaforo Semaforo);

/// <summary>Orquesta el ciclo de vida de una importación: crear, liquidar, hacer seguimiento y documentar.</summary>
public sealed class ServicioOperaciones(ComexDb db)
{
    static readonly JsonSerializerOptions Json = new() { WriteIndented = true };

    Task Log(int opId, string cat, string detalle)
    {
        db.Bitacora.Add(new() { OperacionId = opId, Fecha = DateTime.Now, Categoria = cat, Detalle = detalle });
        return Task.CompletedTask;
    }

    public async Task<Operacion> CrearImportacionAsync(string carpeta, Incoterm incoterm, string moneda, DateOnly inicio)
    {
        var op = new Operacion { Carpeta = carpeta, Tipo = TipoOperacion.Importacion, Incoterm = incoterm, MonedaFactura = moneda, FechaInicio = inicio };
        foreach (var c in RutaCritica.Calcular(RutaCritica.PlantillaImportacion()))
            op.Etapas.Add(new()
            {
                Codigo = c.Etapa.Id, Nombre = c.Etapa.Nombre, Responsable = c.Etapa.Responsable, EsHitoLegal = c.Etapa.EsHitoLegal,
                EsCritica = c.EsCritica, Holgura = c.Holgura,
                InicioPlan = inicio.AddDays(c.ES), FinPlan = inicio.AddDays(c.EF)
            });
        db.Operaciones.Add(op);
        await db.SaveChangesAsync();
        await Log(op.Id, "Creación", $"Importación {carpeta} creada con Incoterm {incoterm}; ruta crítica estimada en {op.Etapas.Max(e => (e.FinPlan.DayNumber - inicio.DayNumber))} días.");
        await db.SaveChangesAsync();
        return op;
    }

    public async Task AgregarItemAsync(int opId, ItemMercancia item)
    {
        if (item.Desgravacion is < 0 or > 1) throw new ArgumentException("La desgravación debe estar entre 0 % y 100 %.");
        if (item.Desgravacion > 0 && string.IsNullOrWhiteSpace(item.AcuerdoPreferencial))
            throw new ArgumentException("Indique el acuerdo comercial que sustenta la desgravación (se exige Certificado de Origen).");
        item.OperacionId = opId;
        db.Items.Add(item);
        if (item.Desgravacion > 0) (await db.Operaciones.FirstAsync(o => o.Id == opId)).UsaPreferenciaArancelaria = true;
        await Log(opId, "Ítem", $"Ítem {item.Numero} {item.CodigoNandina} «{item.Descripcion}» por {item.ValorFactura:N2}." + (item.Desgravacion > 0 ? $" Preferencia {item.AcuerdoPreferencial} {item.Desgravacion:P0}." : ""));
        await db.SaveChangesAsync();
    }

    public async Task<LiquidacionResultado> LiquidarAsync(int opId, TipoCambioTable tc, ParametrosTributarios? p = null)
    {
        p ??= new();
        var op = await db.Operaciones.Include(o => o.Items).Include(o => o.Liquidaciones).SingleAsync(o => o.Id == opId);
        Money? M(decimal v) => v == 0 ? null : new Money(v, op.MonedaFactura);
        var core = new OperacionImportacion(op.Incoterm, op.MonedaFactura, op.Items.OrderBy(i => i.Numero).Select(i => i.ToCore()).ToList(),
            M(op.GastosOrigen), M(op.Flete), M(op.Seguro), M(op.OtrosGastosFrontera), M(op.Deducciones), op.OtrasErogacionesBob);
        var r = CalculadoraTributaria.Calcular(core, tc, p);

        var version = op.Liquidaciones.Count + 1;
        db.Liquidaciones.Add(new()
        {
            OperacionId = opId, Version = version, CalculadaEn = DateTime.Now, TipoCambioFecha = tc.Fecha,
            TipoCambioJson = JsonSerializer.Serialize(new { tc.Fecha, op.MonedaFactura }), ParametrosJson = JsonSerializer.Serialize(p, Json),
            ResultadoJson = JsonSerializer.Serialize(r, Json), CifBob = r.CifBob, TotalTributos = r.TotalTributos
        });
        await Log(opId, "Liquidación", $"v{version}: CIF Bs {r.CifBob:N2}, tributos Bs {r.TotalTributos:N2} (TC al {tc.Fecha}).");
        foreach (var a in r.Advertencias) await Log(opId, "Advertencia", a);
        await db.SaveChangesAsync();
        return r;
    }

    public async Task CompletarEtapaAsync(int opId, string codigo, DateOnly fecha, string? nota = null)
    {
        var e = await db.Etapas.SingleAsync(x => x.OperacionId == opId && x.Codigo == codigo);
        e.FinReal = fecha; e.Notas = nota;
        var desvio = fecha.DayNumber - e.FinPlan.DayNumber;
        await Log(opId, "Etapa", $"{e.Codigo} «{e.Nombre}» cumplida el {fecha} ({(desvio > 0 ? $"+{desvio} d de retraso" : "a tiempo")}).{(nota is null ? "" : " " + nota)}");
        await db.SaveChangesAsync();
    }

    public async Task<IReadOnlyList<EstadoEtapa>> EstadoRutaAsync(int opId, DateOnly hoy)
        => (await db.Etapas.Where(e => e.OperacionId == opId).OrderBy(e => e.InicioPlan).ThenBy(e => e.Codigo).ToListAsync())
            .Select(e => new EstadoEtapa(e, Seguimiento.Evaluar(e.InicioPlan, e.FinPlan, e.FinReal, hoy))).ToList();

    public async Task<Documento> AdjuntarDocumentoAsync(int opId, TipoDocumento tipo, string rutaArchivo)
    {
        var d = new Documento
        {
            OperacionId = opId, Tipo = tipo, NombreArchivo = Path.GetFileName(rutaArchivo), Ruta = rutaArchivo, AgregadoEn = DateTime.Now,
            Sha256 = File.Exists(rutaArchivo) ? Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(rutaArchivo))) : null
        };
        db.Documentos.Add(d);
        await Log(opId, "Documento", $"{tipo}: {d.NombreArchivo}");
        await db.SaveChangesAsync();
        return d;
    }

    /// <summary>Documentos que exige el legajo según el estado de la operación y cuáles faltan.</summary>
    public async Task<IReadOnlyList<(TipoDocumento Tipo, bool Presente, string Motivo)>> ChecklistAsync(int opId)
    {
        var op = await db.Operaciones.Include(o => o.Documentos).Include(o => o.Items).SingleAsync(o => o.Id == opId);
        var fobBob = op.Items.Sum(i => i.ValorFactura);
        var req = new List<(TipoDocumento, string)>
        {
            (TipoDocumento.Factura, "Factura comercial"), (TipoDocumento.Embarque, "B/L, CRT o guía aérea"),
            (TipoDocumento.PackingList, "Lista de empaque"), (TipoDocumento.Seguro, "Póliza/certificado de seguro"),
            (TipoDocumento.Bancario, "Respaldo de pago bancario"),
        };
        if (op.UsaPreferenciaArancelaria) req.Add((TipoDocumento.CertificadoOrigen, "Preferencia arancelaria solicitada"));
        if (op.Flete > 0) req.Add((TipoDocumento.FleteTerrestre, "Factura de flete"));
        var codigos = op.Items.Select(i => i.CodigoNandina).ToList();
        var exigidas = await db.Partidas.Where(p => codigos.Contains(p.Codigo) && p.TipoDocumento != "P" && (p.TipoDocumento != "" || p.Autorizaciones != "")).ToListAsync();
        if (exigidas.Count > 0)
            req.Add((TipoDocumento.AutorizacionPrevia, "Documento adicional: " + string.Join("; ", exigidas.Select(p => $"{p.TipoDocumento} {(p.Entidad != "" ? p.Entidad : p.Autorizaciones)}".Trim()).Distinct())));
        return req.Select(r => (r.Item1, op.Documentos.Any(d => d.Tipo == r.Item1), r.Item2)).ToList();
    }

    /// <summary>Expediente del proceso en Markdown (convertible a PDF/Word): resumen, ítems, liquidación, ruta, legajo y bitácora.</summary>
    public async Task<string> GenerarExpedienteAsync(int opId, DateOnly hoy)
    {
        var op = await db.Operaciones.Include(o => o.Items).Include(o => o.Liquidaciones).Include(o => o.Bitacora).SingleAsync(o => o.Id == opId);
        var sb = new StringBuilder();
        sb.AppendLine($"# Expediente de importación {op.Carpeta}\n");
        sb.AppendLine($"- Incoterm: **{op.Incoterm}** · Moneda: {op.MonedaFactura} · Inicio: {op.FechaInicio}");
        sb.AppendLine($"- Flete {op.Flete:N2} · Seguro {op.Seguro:N2} · Gastos origen {op.GastosOrigen:N2} · Gastos hasta frontera {op.OtrosGastosFrontera:N2}\n");
        sb.AppendLine("## Mercancías\n\n| N.º | Partida | Descripción | Valor | P. bruto kg |\n|---|---|---|---|---|");
        foreach (var i in op.Items.OrderBy(i => i.Numero)) sb.AppendLine($"| {i.Numero} | {i.CodigoNandina} | {i.Descripcion} | {i.ValorFactura:N2} | {i.PesoBrutoKg:N2} |");

        var ult = op.Liquidaciones.OrderByDescending(l => l.Version).FirstOrDefault();
        sb.AppendLine("\n## Liquidación vigente\n");
        if (ult is null) sb.AppendLine("_Sin liquidar._");
        else
        {
            var r = JsonSerializer.Deserialize<LiquidacionResultado>(ult.ResultadoJson)!;
            sb.AppendLine($"Versión {ult.Version} · calculada {ult.CalculadaEn:g} · TC al {ult.TipoCambioFecha}\n");
            sb.AppendLine($"| Concepto | Bs |\n|---|---|\n| FOB | {r.ValorFobBob:N2} |\n| Adiciones | {r.AdicionesBob:N2} |\n| Deducciones | {r.DeduccionesBob:N2} |\n| **CIF** | **{r.CifBob:N2}** |\n| GA | {r.GA:N2} |\n| ICE | {r.ICE:N2} |\n| IEHD | {r.IEHD:N2} |\n| IVA | {r.IVA:N2} |\n| **Total tributos** | **{r.TotalTributos:N2}** |");
            if (r.RequiereBancarizacion) sb.AppendLine("\n> Requiere bancarización (D.S. 772).");
        }

        sb.AppendLine("\n## Ruta crítica\n\n| Etapa | Plan | Real | Estado | Crítica |\n|---|---|---|---|---|");
        foreach (var s in await EstadoRutaAsync(opId, hoy))
            sb.AppendLine($"| {s.Etapa.Codigo} {s.Etapa.Nombre} | {s.Etapa.InicioPlan} → {s.Etapa.FinPlan} | {s.Etapa.FinReal?.ToString() ?? "—"} | {s.Semaforo} | {(s.Etapa.EsCritica ? "Sí" : "")} |");

        sb.AppendLine("\n## Legajo documental\n");
        foreach (var (t, ok, m) in await ChecklistAsync(opId)) sb.AppendLine($"- [{(ok ? "x" : " ")}] {t} — {m}");

        sb.AppendLine("\n## Bitácora\n");
        foreach (var e in op.Bitacora.OrderBy(e => e.Fecha)) sb.AppendLine($"- {e.Fecha:yyyy-MM-dd HH:mm} · **{e.Categoria}** · {e.Detalle}");
        return sb.ToString();
    }
}
