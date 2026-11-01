namespace ComexBol.Core;

public enum Semaforo { Pendiente, EnCurso, Cumplido, Alerta, Vencido }

public sealed record Etapa(string Id, string Nombre, int DuracionDias, string Responsable,
    string[] Predecesores, bool EsHitoLegal = false);

public sealed record EtapaCpm(Etapa Etapa, int ES, int EF, int LS, int LF, int Holgura)
{
    public bool EsCritica => Holgura == 0;
}

public static class RutaCritica
{
    /// <summary>CPM clásico: pasada hacia adelante (ES/EF), hacia atrás (LS/LF), holgura = LS − ES.</summary>
    public static IReadOnlyList<EtapaCpm> Calcular(IReadOnlyList<Etapa> etapas)
    {
        var porId = etapas.ToDictionary(e => e.Id);
        foreach (var e in etapas)
            foreach (var pr in e.Predecesores)
                if (!porId.ContainsKey(pr)) throw new ArgumentException($"{e.Id}: predecesor inexistente '{pr}'.");

        // Orden topológico (Kahn) con detección de ciclos.
        var grado = etapas.ToDictionary(e => e.Id, e => e.Predecesores.Length);
        var sucesores = etapas.ToDictionary(e => e.Id, _ => new List<string>());
        foreach (var e in etapas) foreach (var pr in e.Predecesores) sucesores[pr].Add(e.Id);
        var cola = new Queue<string>(etapas.Where(e => grado[e.Id] == 0).Select(e => e.Id));
        var orden = new List<string>();
        while (cola.Count > 0)
        {
            var id = cola.Dequeue(); orden.Add(id);
            foreach (var s in sucesores[id]) if (--grado[s] == 0) cola.Enqueue(s);
        }
        if (orden.Count != etapas.Count) throw new ArgumentException("La red de etapas contiene un ciclo.");

        var es = new Dictionary<string, int>(); var ef = new Dictionary<string, int>();
        foreach (var id in orden)
        {
            var e = porId[id];
            es[id] = e.Predecesores.Length == 0 ? 0 : e.Predecesores.Max(p => ef[p]);
            ef[id] = es[id] + e.DuracionDias;
        }
        var fin = ef.Values.Max();
        var lf = new Dictionary<string, int>(); var ls = new Dictionary<string, int>();
        foreach (var id in Enumerable.Reverse(orden))
        {
            lf[id] = sucesores[id].Count == 0 ? fin : sucesores[id].Min(s => ls[s]);
            ls[id] = lf[id] - porId[id].DuracionDias;
        }
        return orden.Select(id => new EtapaCpm(porId[id], es[id], ef[id], ls[id], lf[id], ls[id] - es[id])).ToList();
    }

    /// <summary>
    /// Plantilla de importación. Duraciones = valores iniciales editables (días hábiles estimados), NO plazos legales.
    /// Los plazos legales (p. ej. vigencia de la DIM, almacenaje) viven en ParametrosNormativos con vigencia.
    /// </summary>
    public static IReadOnlyList<Etapa> PlantillaImportacion() => new Etapa[]
    {
        new("I01","Verificar mercancía prohibida/restringida y clasificar (NANDINA)",2,"Analista",[]),
        new("I02","Autorizaciones previas / certificaciones vía VUCE",10,"Importador",["I01"],true),
        new("I03","Orden de compra, proforma y contrato con Incoterm",3,"Importador",["I01"]),
        new("I04","Contratar flete y póliza de seguro",3,"Logística",["I03"]),
        new("I05","Emisión de documento de embarque (B/L, CRT, AWB)",2,"Proveedor/Transportista",["I02","I04"]),
        new("I06","Manifiesto internacional (MIC/DTA, TIF, manifiesto aéreo)",1,"Transportista",["I05"],true),
        new("I07","Tránsito aduanero hacia aduana de destino",12,"Transportista",["I06"],true),
        new("I08","Arribo y Parte de Recepción (PRM)",1,"Concesionario de depósito",["I07"],true),
        new("I09","DAV y DIM (general/anticipado/inmediato/DIMS)",2,"Despachante",["I05"],true),
        new("I10","Liquidación y pago de tributos",1,"Importador/Banco",["I09","I08"],true),
        new("I11","Sorteo de canal (verde/amarillo/rojo)",1,"ANB",["I10"],true),
        new("I12","Retiro con pase de salida y entrega",1,"Logística",["I11"]),
    };

    public static IReadOnlyList<Etapa> PlantillaExportacion() => new Etapa[]
    {
        new("E01","Registro de exportador (NIT / Padrón de operadores)",5,"Exportador",[]),
        new("E02","Certificado de origen y permisos previos",7,"Exportador",["E01"],true),
        new("E03","Factura de exportación y lista de empaque",2,"Exportador",["E01"]),
        new("E04","Transporte internacional y MIC/DTA o manifiesto aéreo",3,"Transportista",["E03"],true),
        new("E05","Declaración de Exportación (DEX)",1,"Despachante",["E02","E03"],true),
        new("E06","Aforo y canal en aduana de salida o planta",2,"ANB",["E05","E04"],true),
        new("E07","Salida física y certificado de salida",1,"Concesionario",["E06"],true),
        new("E08","Retorno de divisas y solicitud de CEDEIM",30,"Exportador/Banco",["E07"]),
    };
}
