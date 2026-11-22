namespace ComexBol.Core;

public sealed record PasoProcedimiento(string Fase, string Codigo, string Proceso, string Responsables, string Procedimiento, string Documentos, string Tiempo, string Normativa, string Consejo);
public sealed record ItemControl(string Codigo, string Etapa, string Documento, string Emisor, string Obligatoriedad, string Criterio);

/// <summary>
/// Guía de procedimientos de importación de maquinaria a Bolivia (11 pasos) y lista de control del expediente (12 ítems),
/// basadas en el «Manual de Procedimientos de Importación de Maquinaria a Bolivia (gestión 2026)» del usuario.
/// Los plazos y montos son referenciales del manual; deben confirmarse en la normativa vigente de la Aduana Nacional.
/// </summary>
public static class GuiaProcedimiento
{
    public static readonly IReadOnlyList<PasoProcedimiento> Pasos =
    [
        new("Fase 1 · Formalización y registro", "P-01", "Constitución y registro tributario", "Emprendedor / Contador",
            "Cédula de Identidad vigente; Matrícula de Comercio en SEPREC (unipersonal o SRL); NIT en el Régimen General del SIN (indispensable para importar maquinaria, emitir facturas y dar crédito fiscal).",
            "Cédula · Matrícula SEPREC · Certificado NIT (Régimen General)", "3 a 5 días hábiles", "Código de Comercio; Ley 843",
            "El Régimen Simplificado no sirve para importar maquinaria comercial ni dar crédito fiscal."),
        new("Fase 1 · Formalización y registro", "P-02", "Empadronamiento en la Aduana Nacional (SUMA)", "Emprendedor / Representante legal",
            "Inscribirse en el Padrón de Operadores de Comercio Exterior como Importador Habitual (compras de más de USD 4.000 FOB al año); cargar NIT, SEPREC, domicilio fiscal y croquis. Como no habitual (modalidad no presencial) el tope es USD 2.000 por despacho y USD 4.000 por año.",
            "Certificado de registro de operador · Usuario y clave SUMA", "1 a 2 días hábiles", "Reglamento de Operadores de Comercio Exterior; Art. 111 RLGA",
            "Sin registro activo la carga queda bloqueada. El Padrón de importadores habituales exige además garantía (consulte el monto vigente)."),
        new("Fase 2 · Compra internacional", "P-03", "Clasificación arancelaria y validación de beneficios", "Importador / Agencia despachante (ADA)",
            "Pedir ficha técnica, catálogo, dimensiones, peso y tipo de gas/energía; confirmar con el despachante la subpartida y si está en el Anexo del D.S. 5516 (GA 0 %) y la rebaja del D.S. 5646; pedir certificado de origen si el fabricante está en CAN, Mercosur o México.",
            "Ficha técnica · Informe de clasificación previa", "1 a 2 días hábiles", "Arancel 2026; D.S. 5516; D.S. 5646",
            "Hágalo ANTES de transferir dinero. El beneficio del D.S. 5516 vence el 31/12/2026."),
        new("Fase 2 · Compra internacional", "P-04", "Cotización, Incoterm y pago internacional", "Importador / Proveedor / Banco",
            "Acordar el Incoterm (FOB o CIF recomendados); exigir factura proforma detallada; pagar por transferencia SWIFT desde cuenta empresarial, respaldando el origen de fondos para la DAV.",
            "Proforma · Contrato · Comprobante SWIFT", "2 a 5 días hábiles", "Normativa ASFI/BCB; Acuerdo de Valoración OMC (DAV)",
            "Guarde el SWIFT original: la Aduana lo exige para demostrar el precio realmente pagado."),
        new("Fase 3 · Logística y tránsito", "P-05", "Producción, embalaje y embarque en origen", "Proveedor / Agente de carga",
            "Embalaje en madera tratada (NIMF-15), documentos finales de exportación y embarque marítimo (Arica/Iquique) o terrestre.",
            "Factura comercial · Packing list · B/L o CRT · Certificado de origen", "25–45 días (marítimo Asia) / 5–10 días (terrestre)", "Art. 111 RLGA; Art. 266 RLGA (origen)",
            "Revise en borrador que el B/L y la factura tengan el mismo nombre y NIT del importador."),
        new("Fase 3 · Logística y tránsito", "P-06", "DAM y tránsito", "Importador / ADA / Transportador",
            "Registrar la Declaración de Adquisición de Mercancías (DAM) en SUMA antes del arribo (el manual indica un máximo de 20 días tras el embarque marítimo); liberar el contenedor en puerto; el transportista emite el MIC/DTA hasta la Aduana Interior.",
            "DAM · MIC/DTA · CRT · Planilla de gastos portuarios", "4 a 7 días hábiles (puerto a El Alto)", "Art. 92 RLGA; Procedimiento de Tránsito",
            "Confirme el plazo vigente de la DAM en la Aduana: no pudo verificarse en fuentes oficiales."),
        new("Fase 4 · Despacho aduanero", "P-07", "Ingreso a depósito y Parte de Recepción", "Concesionario de depósito",
            "El concesionario descarga, pesa y verifica los bultos contra el MIC/DTA y emite el Parte de Recepción, que habilita el despacho.",
            "Parte de Recepción · Boleta de pesaje", "1 a 2 días hábiles", "Arts. 109 y 160 RLGA",
            "Si una caja llega golpeada o con faltante, exija que quede en las observaciones del Parte de Recepción."),
        new("Fase 4 · Despacho aduanero", "P-08", "DAV y validación de la DIM en SUMA", "ADA / Importador",
            "Llenar la DAV (precio, flete, seguro), elaborar la DIM aplicando el GA que corresponda y liquidando el IVA, y validarla en SUMA.",
            "DAV · DIM validada · Liquidación", "1 día hábil", "Art. 88 LGA; Art. 111 RLGA; D.S. 5516; D.S. 5646; Ley 843",
            "Verifique que la DIM consigne el código del beneficio o rebaja para que liquide el GA esperado."),
        new("Fase 4 · Despacho aduanero", "P-09", "Pago de tributos y canal de control", "Importador / Banco / SUMA",
            "Pagar los tributos liquidados dentro de los 3 días hábiles de validada la DIM; SUMA asigna el canal: Verde (levante inmediato), Amarillo (revisión documental) o Rojo (aforo físico y documental).",
            "Recibo de pago · Asignación de canal", "1 día (verde) / 2 a 4 días (amarillo o rojo)", "Arts. 10 y 106 RLGA; Procedimiento de Importación a Consumo",
            "En canal Rojo el técnico revisa placas y medidas: tenga catálogos a mano."),
        new("Fase 4 · Despacho aduanero", "P-10", "Levante y retiro de la mercancía", "Técnico aduanero / Concesionario / Importador",
            "Sin observaciones (o subsanadas) la Aduana autoriza el levante; pagar el almacenaje; obtener el Pase de Salida y trasladar la mercancía.",
            "DIM con levante · Factura de almacenaje · Pase de salida", "1 día hábil", "Arts. 114 y 115 RLGA",
            "La DIM pagada y con levante es el título de la mercancía: guarde copia en el local."),
        new("Fase 5 · Tienda y postventa", "P-11", "Recepción, costeo y facturación", "Administrador / Contador / Vendedores",
            "Verificar integridad de cada equipo; calcular el costo unitario real (CIF + tributos no recuperables + gastos); registrar el IVA pagado como crédito fiscal y facturar cada venta.",
            "Inventario valorado · Libro de compras y ventas · Facturas", "Permanente", "Ley 843; Normativa SIAT; Código de Comercio",
            "Exhiba copia de la DIM en el local ante controles."),
    ];

    public static readonly IReadOnlyList<ItemControl> Control =
    [
        new("C-01", "Habilitación previa", "NIT activo (Régimen General) y Matrícula SEPREC", "SIN / SEPREC", "Obligatorio", "Actividad económica vinculada a la importación y venta del bien."),
        new("C-02", "Habilitación previa", "Registro vigente en el Padrón de Operadores (SUMA)", "Aduana Nacional", "Obligatorio", "Estado «Activo» sin multas ni deudas tributarias pendientes."),
        new("C-03", "Compra y origen", "Ficha técnica del equipo", "Fabricante / Proveedor", "Obligatorio", "Especifica uso, potencia o consumo y energía/gas, que respalda la subpartida."),
        new("C-04", "Compra y origen", "Factura comercial sin enmiendas", "Proveedor exterior", "Obligatorio", "Incoterm, moneda, precio unitario y total idénticos al comprobante SWIFT."),
        new("C-05", "Compra y origen", "Comprobante de transferencia internacional (SWIFT)", "Banco en Bolivia", "Obligatorio", "A nombre del importador registrado, hacia el proveedor de la factura."),
        new("C-06", "Compra y origen", "Certificado de origen (CAN, Mercosur o México)", "Entidad autorizada de origen", "Condicional", "Original con firmas y sellos habilitados."),
        new("C-07", "Transporte y tránsito", "Lista de empaque por bulto", "Proveedor exterior", "Obligatorio", "Cajas, peso neto y bruto y medidas exactas de cada equipo."),
        new("C-08", "Transporte y tránsito", "Documento de embarque (B/L, CRT, AWB o TIF/DTA)", "Naviera / Transportista", "Obligatorio", "Consignado al importador, con destino a la aduana de destino."),
        new("C-09", "Transporte y tránsito", "DAM registrada", "Importador / ADA", "Obligatorio", "Registrada en SUMA antes del arribo y dentro del plazo vigente."),
        new("C-10", "Nacionalización", "Parte de Recepción del recinto aduanero", "Concesionario", "Obligatorio", "Sin discrepancias de peso o bultos respecto al manifiesto."),
        new("C-11", "Nacionalización", "DAV y DIM validadas", "ADA / Importador", "Obligatorio", "Subpartida correcta, beneficio o rebaja aplicados y IVA liquidado."),
        new("C-12", "Nacionalización y tienda", "Recibo de pago y DIM con levante", "Banco / Aduana", "Obligatorio", "Archivados en carpeta física como respaldo legal."),
    ];
}

/// <summary>Condiciones del importador según el padrón (habitual / no habitual).</summary>
public sealed record ReglaImportador(string TipoImportador, decimal FobUsdDespacho, decimal AcumuladoAnualUsd,
    decimal TopeDespachoUsd = 2_000m, decimal TopeAnualUsd = 4_000m);
