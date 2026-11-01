using System.Globalization;
using System.Text;

namespace ComexBol.Core.Catalogo;

public sealed record PartidaNandina(
    string Codigo,                 // 10 dígitos
    string Descripcion,
    decimal AlicuotaGA,            // 0..1
    string Unidad,
    bool Prohibida,
    IReadOnlyList<string> Autorizaciones,   // SENASAG, AGEMED, IBNORCA, ...
    string Fuente)                 // "ANB-2022", "EJEMPLO"...
{
    /// <summary>AP, AP y C, C, C*, P (prohibida), CITES, CCRT, CRTM, DJ. Vacío = sin documento adicional.</summary>
    public string TipoDocumento { get; init; } = "";
    public string Entidad { get; init; } = "";
    public string DispLegal { get; init; } = "";
    /// <summary>Porcentajes de preferencia tal como figuran impresos (sin asignar a un acuerdo: las columnas se corren en el original).</summary>
    public IReadOnlyList<decimal> Preferencias { get; init; } = [];
    /// <summary>"ICE" o "IEHD" si la partida está sujeta a impuesto especial (la tasa NO viene en el arancel: se ingresa aparte).</summary>
    public string ImpuestoEspecial { get; init; } = "";
    /// <summary>Apéndice I (vehículos): alícuota ICE por antigüedad [nuevo, 1, 2, 3, 4, 5 años], en fracción (0.15 = 15 %). Vacío si no aplica.</summary>
    public IReadOnlyList<decimal> IceAntiguedad { get; init; } = [];
    public string Capitulo => Codigo[..2];
    public string Partida4 => Codigo[..4];
    public bool EsEjemplo => Fuente.Equals("EJEMPLO", StringComparison.OrdinalIgnoreCase);
}

public sealed record ErrorImportacion(int Linea, string Mensaje);
public sealed record ResultadoImportacion(IReadOnlyList<PartidaNandina> Partidas, IReadOnlyList<ErrorImportacion> Errores);

/// <summary>
/// Importa el arancel desde CSV (separador ',' o ';', UTF-8).
/// Columnas: Codigo;Descripcion;GA;Unidad;Prohibida;Autorizaciones;Fuente
///   GA en porcentaje (10 = 10 %), Prohibida = SI/NO, Autorizaciones separadas por '|'.
/// Las filas inválidas se reportan con su número de línea y NO se importan; nunca se corrigen en silencio.
/// </summary>
public static class CatalogoCsv
{
    public static ResultadoImportacion Parsear(TextReader reader, string fuenteDefecto = "ANB")
    {
        var partidas = new List<PartidaNandina>(); var errores = new List<ErrorImportacion>();
        var vistos = new HashSet<string>();
        var header = reader.ReadLine();
        if (header is null) return new(partidas, [new(1, "Archivo vacío")]);
        var sep = header.Count(c => c == ';') >= header.Count(c => c == ',') ? ';' : ',';
        var cols = Split(header, sep).Select(c => c.Trim().ToLowerInvariant()).ToList();
        foreach (var req in new[] { "codigo", "descripcion", "ga" })
            if (!cols.Contains(req)) return new(partidas, [new(1, $"Falta la columna obligatoria '{req}'")]);
        string Get(List<string> f, string c) { var i = cols.IndexOf(c); return i >= 0 && i < f.Count ? f[i].Trim() : ""; }

        int n = 1; string? line;
        while ((line = reader.ReadLine()) is not null)
        {
            n++;
            if (string.IsNullOrWhiteSpace(line)) continue;
            var f = Split(line, sep);
            var codigo = new string(Get(f, "codigo").Where(char.IsDigit).ToArray());
            if (codigo.Length != 10) { errores.Add(new(n, $"Código '{Get(f, "codigo")}' no tiene 10 dígitos")); continue; }
            if (!vistos.Add(codigo)) { errores.Add(new(n, $"Código {codigo} duplicado")); continue; }
            if (!decimal.TryParse(Get(f, "ga").Replace(',', '.'), NumberStyles.Number, CultureInfo.InvariantCulture, out var ga) || ga < 0 || ga > 40)
            { errores.Add(new(n, $"GA '{Get(f, "ga")}' fuera de 0–40")); continue; }
            var desc = Get(f, "descripcion");
            if (desc.Length == 0) { errores.Add(new(n, "Descripción vacía")); continue; }
            var prohibida = Get(f, "prohibida").ToUpperInvariant() is "SI" or "SÍ" or "S" or "1" or "TRUE";
            var aut = Get(f, "autorizaciones").Split('|', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            var fuente = Get(f, "fuente"); if (fuente.Length == 0) fuente = fuenteDefecto;
            partidas.Add(new(codigo, desc, ga / 100m, Get(f, "unidad"), prohibida, aut, fuente));
        }
        return new(partidas, errores);
    }

    static List<string> Split(string line, char sep)
    {
        var r = new List<string>(); var sb = new StringBuilder(); bool q = false;
        foreach (var c in line)
        {
            if (c == '"') q = !q;
            else if (c == sep && !q) { r.Add(sb.ToString()); sb.Clear(); }
            else sb.Append(c);
        }
        r.Add(sb.ToString()); return r;
    }
}

/// <summary>Capítulos del Sistema Armonizado (estándar OMA, comunes a todo arancel NANDINA). Los dos primeros dígitos de la partida.</summary>
public static class CapitulosSa
{
    public static string? Titulo(string codigo) => codigo.Length >= 2 && Tabla.TryGetValue(codigo[..2], out var t) ? t : null;

    public static readonly IReadOnlyDictionary<string, string> Tabla = new Dictionary<string, string>
    {
        ["01"]="Animales vivos",["02"]="Carne y despojos comestibles",["03"]="Pescados y crustáceos, moluscos",["04"]="Leche y productos lácteos; huevos; miel",
        ["05"]="Los demás productos de origen animal",["06"]="Plantas vivas y productos de la floricultura",["07"]="Hortalizas, plantas, raíces y tubérculos alimenticios",
        ["08"]="Frutas y frutos comestibles",["09"]="Café, té, yerba mate y especias",["10"]="Cereales",["11"]="Productos de la molinería; malta; almidón",
        ["12"]="Semillas y frutos oleaginosos; plantas industriales o medicinales",["13"]="Gomas, resinas y demás jugos y extractos vegetales",["14"]="Materias trenzables y demás productos vegetales",
        ["15"]="Grasas y aceites animales o vegetales",["16"]="Preparaciones de carne, pescado o crustáceos",["17"]="Azúcares y artículos de confitería",["18"]="Cacao y sus preparaciones",
        ["19"]="Preparaciones a base de cereales, harina, almidón o leche; pastelería",["20"]="Preparaciones de hortalizas, frutas u otros frutos",["21"]="Preparaciones alimenticias diversas",
        ["22"]="Bebidas, líquidos alcohólicos y vinagre",["23"]="Residuos de las industrias alimentarias; alimentos para animales",["24"]="Tabaco y sucedáneos del tabaco",
        ["25"]="Sal; azufre; tierras y piedras; yesos, cales y cementos",["26"]="Minerales, escorias y cenizas",["27"]="Combustibles minerales, aceites minerales y productos de su destilación",
        ["28"]="Productos químicos inorgánicos",["29"]="Productos químicos orgánicos",["30"]="Productos farmacéuticos",["31"]="Abonos",["32"]="Extractos curtientes o tintóreos; pinturas y barnices",
        ["33"]="Aceites esenciales; perfumería, cosmética o tocador",["34"]="Jabón, agentes de superficie, ceras, velas",["35"]="Materias albuminoideas; colas; enzimas",["36"]="Pólvora y explosivos; artículos de pirotecnia",
        ["37"]="Productos fotográficos o cinematográficos",["38"]="Productos diversos de las industrias químicas",["39"]="Plástico y sus manufacturas",["40"]="Caucho y sus manufacturas",
        ["41"]="Pieles (excepto la peletería) y cueros",["42"]="Manufacturas de cuero; artículos de viaje, bolsos",["43"]="Peletería y confecciones de peletería",["44"]="Madera, carbón vegetal y manufacturas de madera",
        ["45"]="Corcho y sus manufacturas",["46"]="Manufacturas de espartería o cestería",["47"]="Pasta de madera o de otras materias fibrosas celulósicas; desperdicios de papel",["48"]="Papel y cartón; manufacturas de pasta de celulosa, papel o cartón",
        ["49"]="Productos editoriales, de la prensa y de las demás industrias gráficas",["50"]="Seda",["51"]="Lana y pelo fino u ordinario",["52"]="Algodón",["53"]="Las demás fibras textiles vegetales",
        ["54"]="Filamentos sintéticos o artificiales",["55"]="Fibras sintéticas o artificiales discontinuas",["56"]="Guata, fieltro y tela sin tejer; cordeles, cuerdas",["57"]="Alfombras y demás revestimientos para el suelo",
        ["58"]="Tejidos especiales; encajes; bordados",["59"]="Telas impregnadas, recubiertas o estratificadas",["60"]="Tejidos de punto",["61"]="Prendas y complementos de vestir, de punto",
        ["62"]="Prendas y complementos de vestir, excepto los de punto",["63"]="Los demás artículos textiles confeccionados; prendería y trapos",["64"]="Calzado, polainas y artículos análogos",
        ["65"]="Sombreros, demás tocados y sus partes",["66"]="Paraguas, sombrillas, bastones",["67"]="Plumas y plumón preparados; flores artificiales",["68"]="Manufacturas de piedra, yeso, cemento, amianto, mica",
        ["69"]="Productos cerámicos",["70"]="Vidrio y sus manufacturas",["71"]="Perlas, piedras preciosas, metales preciosos; bisutería; monedas",["72"]="Fundición, hierro y acero",["73"]="Manufacturas de fundición, hierro o acero",
        ["74"]="Cobre y sus manufacturas",["75"]="Níquel y sus manufacturas",["76"]="Aluminio y sus manufacturas",["78"]="Plomo y sus manufacturas",["79"]="Cinc y sus manufacturas",["80"]="Estaño y sus manufacturas",
        ["81"]="Los demás metales comunes; cermets",["82"]="Herramientas, útiles, cuchillería y cubiertos de mesa, de metal común",["83"]="Manufacturas diversas de metal común",
        ["84"]="Reactores nucleares, calderas, máquinas, aparatos y artefactos mecánicos",["85"]="Máquinas, aparatos y material eléctrico; grabación o reproducción de sonido e imagen",
        ["86"]="Vehículos y material para vías férreas",["87"]="Vehículos automóviles, tractores y demás vehículos terrestres",["88"]="Aeronaves y aparatos espaciales",["89"]="Barcos y demás artefactos flotantes",
        ["90"]="Instrumentos y aparatos de óptica, fotografía, medida, control o precisión; médico-quirúrgicos",["91"]="Aparatos de relojería",["92"]="Instrumentos musicales",["93"]="Armas, municiones",
        ["94"]="Muebles; mobiliario médico-quirúrgico; artículos de cama; iluminación",["95"]="Juguetes, juegos y artículos para recreo o deporte",["96"]="Manufacturas diversas",["97"]="Objetos de arte o colección y antigüedades",
    };
}
