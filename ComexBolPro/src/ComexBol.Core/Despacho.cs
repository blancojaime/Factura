namespace ComexBol.Core;

public enum NivelHallazgo { Ok, Alerta, Error }
public sealed record Hallazgo(NivelHallazgo Nivel, string Texto);

public sealed record DatosDespacho(
    string TipoDespacho, string Regimen, string AduanaIngreso, string AduanaDestino, string CodigoDeclarante,
    string ModalidadTransporte, string NroDocEmbarque, int Bultos, decimal PesoBrutoManifiestoKg, string NroManifiesto,
    string NroDav, string NroDim);

public static class Despacho
{
    public static readonly string[] Tipos = ["General", "Anticipado", "Inmediato", "Menor cuantía", "Encomienda postal / Courier"];
    public static readonly string[] Regimenes = ["10 - Importación a consumo", "Admisión temporal para reexportación en el mismo estado", "Admisión temporal para perfeccionamiento activo (RITEX)", "Depósito de aduana", "Zona franca"];
    public static readonly string[] Modalidades = ["Marítimo / fluvial", "Carretero", "Aéreo", "Ferroviario", "Postal / courier"];

    /// <summary>Documento de embarque que corresponde a cada modalidad de transporte.</summary>
    public static string DocumentoEmbarque(string modalidad) => modalidad switch
    {
        "Marítimo / fluvial" => "B/L (Bill of Lading)", "Carretero" => "CRT / Carta de Porte Internacional", "Aéreo" => "Guía aérea (AWB)",
        "Ferroviario" => "TIF/DTA", "Postal / courier" => "Guía postal / courier", _ => "Documento de embarque"
    };

    public static string DocumentoManifiesto(string modalidad) => modalidad switch
    {
        "Carretero" => "MIC/DTA", "Ferroviario" => "TIF/DTA", "Aéreo" => "Manifiesto aéreo", "Marítimo / fluvial" => "Manifiesto marítimo (MIRA)", _ => "Manifiesto"
    };

    /// <summary>Valida la consistencia de la DIM antes de entregarla a la agencia despachante o transmitirla en el SUMA.</summary>
    public static IReadOnlyList<Hallazgo> Validar(DatosDespacho d, decimal pesoBrutoItemsKg, int numeroItems, bool hayLiquidacion, bool davResuelta,
        bool bancarizacionPendiente, int documentosFaltantes, decimal toleranciaPeso = 0.05m)
    {
        var h = new List<Hallazgo>();
        void Req(string valor, string nombre) { if (string.IsNullOrWhiteSpace(valor)) h.Add(new(NivelHallazgo.Error, $"Falta {nombre}.")); }
        Req(d.TipoDespacho, "el tipo de despacho"); Req(d.Regimen, "el régimen aduanero"); Req(d.AduanaIngreso, "la aduana de ingreso");
        Req(d.AduanaDestino, "la aduana de destino"); Req(d.CodigoDeclarante, "el código de declarante / agencia despachante");
        Req(d.ModalidadTransporte, "la modalidad de transporte"); Req(d.NroDocEmbarque, $"el número del documento de embarque ({DocumentoEmbarque(d.ModalidadTransporte)})");
        if (numeroItems == 0) h.Add(new(NivelHallazgo.Error, "La operación no tiene ítems."));
        if (d.Bultos <= 0) h.Add(new(NivelHallazgo.Error, "Indique la cantidad de bultos del manifiesto."));
        if (d.PesoBrutoManifiestoKg <= 0) h.Add(new(NivelHallazgo.Alerta, "Indique el peso bruto del manifiesto para cotejarlo con los ítems."));
        else if (pesoBrutoItemsKg > 0)
        {
            var dif = Math.Abs(pesoBrutoItemsKg - d.PesoBrutoManifiestoKg) / d.PesoBrutoManifiestoKg;
            h.Add(dif <= toleranciaPeso
                ? new(NivelHallazgo.Ok, $"Peso bruto de los ítems ({pesoBrutoItemsKg:N2} kg) concuerda con el manifiesto ({d.PesoBrutoManifiestoKg:N2} kg).")
                : new(NivelHallazgo.Error, $"Peso bruto de los ítems ({pesoBrutoItemsKg:N2} kg) difiere {dif:P1} del manifiesto ({d.PesoBrutoManifiestoKg:N2} kg): corrija antes de declarar."));
        }
        if (!hayLiquidacion) h.Add(new(NivelHallazgo.Error, "Calcule la liquidación antes de preparar la DIM."));
        if (!davResuelta) h.Add(new(NivelHallazgo.Alerta, "La DAV (valoración) no está completa: responda el cuestionario de la pestaña Valoración."));
        if (bancarizacionPendiente) h.Add(new(NivelHallazgo.Alerta, "Falta el respaldo bancario del pago (D.S. 772)."));
        if (documentosFaltantes > 0) h.Add(new(NivelHallazgo.Alerta, $"Faltan {documentosFaltantes} documento(s) soporte en el legajo."));
        if (string.IsNullOrWhiteSpace(d.NroDav)) h.Add(new(NivelHallazgo.Alerta, "Aún no registra el N.º de DAV transmitida."));
        if (!string.IsNullOrWhiteSpace(d.Regimen) && !d.Regimen.StartsWith("10")) h.Add(new(NivelHallazgo.Alerta, "Régimen distinto a importación a consumo: la liquidación de esta aplicación está calculada para consumo; verifique la diferencia tributaria con su despachante."));
        if (!h.Any(x => x.Nivel != NivelHallazgo.Ok)) h.Add(new(NivelHallazgo.Ok, "La DIM no presenta observaciones: lista para entregar a la agencia despachante."));
        return h;
    }

    public static readonly string[] Canales = ["Sin asignar", "Verde", "Amarillo", "Rojo"];

    /// <summary>Lista de tareas según el canal de selectividad asignado por la Aduana.</summary>
    public static IReadOnlyList<string> TareasCanal(string canal) => canal switch
    {
        "Verde" => ["Registrar el levante (sin revisión física ni documental previa al pago)", "Verificar el pago de tributos y el refrendo bancario", "Coordinar el retiro de la mercancía del recinto", "Archivar DIM, DAV y comprobantes en el expediente"],
        "Amarillo" => ["Cotejar factura comercial contra la DIM (valor, partida, cantidades)", "Cotejar documento de embarque y lista de empaque contra la DIM", "Verificar póliza de seguro y factura de flete contra la DAV", "Verificar certificado de origen (si se aplicó preferencia)", "Verificar autorizaciones previas (SENASAG, AGEMED, IBNORCA, otras)", "Entregar a la aduana el legajo completo y registrar observaciones", "Obtener el levante"],
        "Rojo" => ["Preparar la mercancía y el acceso para el reconocimiento físico", "Reunir documentos soporte originales para el reconocimiento documental", "Coordinar con la agencia despachante la presencia en la inspección", "Preparar muestras, catálogos y fichas técnicas (marca, modelo, serie)", "Registrar en la bitácora las observaciones del técnico aduanero", "Si hay Acta de Reconocimiento o Informe de Variación de Valor: preparar descargos", "Obtener el levante"],
        _ => []
    };

    public static readonly string[] PruebasDescargo =
    [
        "Factura comercial original", "Orden de compra / contrato con el proveedor", "Comprobante de pago al exterior (SWIFT, transferencia o carta de crédito)",
        "Estado de cuenta bancario con el débito", "Lista de precios vigente del fabricante o catálogo técnico", "Facturas anteriores del mismo proveedor y producto",
        "Póliza de seguro y factura de flete", "Declaración jurada de vinculación (si corresponde)"
    ];

    /// <summary>Borrador de respuesta al Acta de Reconocimiento / Informe de Variación de Valor. Es una plantilla: debe revisarla el despachante o un abogado.</summary>
    public static string PlantillaDescargo(string carpeta, string importador, string nit, string agencia, string nroDim, decimal valorDeclaradoUsd, string observacion, IEnumerable<string> pruebasAdjuntas)
    {
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Señores ADMINISTRACIÓN DE ADUANA — Referencia: DIM {(string.IsNullOrWhiteSpace(nroDim) ? "(N.º)" : nroDim)} · Carpeta {carpeta}");
        sb.AppendLine();
        sb.AppendLine($"{(string.IsNullOrWhiteSpace(importador) ? "(Importador)" : importador)}, NIT {(string.IsNullOrWhiteSpace(nit) ? "(NIT)" : nit)}, representado por la agencia despachante {(string.IsNullOrWhiteSpace(agencia) ? "(ADA)" : agencia)}, presenta DESCARGOS al Acta de Reconocimiento / Informe de Variación de Valor, en los siguientes términos:");
        sb.AppendLine();
        sb.AppendLine("1. OBSERVACIÓN DE LA ADMINISTRACIÓN");
        sb.AppendLine(string.IsNullOrWhiteSpace(observacion) ? "(Transcriba textualmente la observación o duda razonable planteada.)" : observacion);
        sb.AppendLine();
        sb.AppendLine("2. VALOR DECLARADO");
        sb.AppendLine($"El valor de transacción declarado es USD {valorDeclaradoUsd:N2}, determinado con el Primer Método de valoración (Decisión 571 de la CAN y Resolución 1684), sustentado en el precio realmente pagado o por pagar.");
        sb.AppendLine();
        sb.AppendLine("3. PRUEBAS QUE SE ADJUNTAN");
        int n = 1; foreach (var p in pruebasAdjuntas) sb.AppendLine($"   {n++}. {p}");
        sb.AppendLine();
        sb.AppendLine("4. PETITORIO");
        sb.AppendLine("Se solicita aceptar los descargos, mantener el valor declarado y disponer el levante de la mercancía.");
        sb.AppendLine();
        sb.AppendLine("Lugar y fecha: ____________________        Firma: ____________________");
        sb.AppendLine();
        sb.AppendLine("Nota: borrador generado por COMEX JB. Revíselo con su despachante o asesor legal antes de presentarlo.");
        return sb.ToString();
    }
}
