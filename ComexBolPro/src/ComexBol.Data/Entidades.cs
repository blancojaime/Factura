using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using ComexBol.Core;

namespace ComexBol.Data;

public enum TipoOperacion { Importacion, Exportacion }
public enum TipoDocumento { Factura, Embarque, PackingList, AutorizacionPrevia, Seguro, GastosPortuarios, FleteTerrestre, CertificadoOrigen, Bancario, Otro }

public class Operacion
{
    public int Id { get; set; }
    public string Carpeta { get; set; } = "";
    public TipoOperacion Tipo { get; set; }
    public Incoterm Incoterm { get; set; }
    public string MonedaFactura { get; set; } = "USD";
    public DateOnly FechaInicio { get; set; }
    // Costos en moneda de la factura
    public decimal Flete { get; set; }
    public decimal Seguro { get; set; }
    public decimal GastosOrigen { get; set; }
    public decimal OtrosGastosFrontera { get; set; }
    public decimal Deducciones { get; set; }
    public decimal OtrasErogacionesBob { get; set; }
    public bool UsaPreferenciaArancelaria { get; set; }
    public string? EntidadFinanciera { get; set; }
    public string? NroComprobantePago { get; set; }
    public List<ItemMercancia> Items { get; set; } = [];
    public List<EtapaRuta> Etapas { get; set; } = [];
    public List<LiquidacionGuardada> Liquidaciones { get; set; } = [];
    public List<Documento> Documentos { get; set; } = [];
    public List<EventoBitacora> Bitacora { get; set; } = [];
    public List<CostoOperacion> Costos { get; set; } = [];
}

public class ItemMercancia
{
    public int Id { get; set; }
    public int OperacionId { get; set; }
    public int Numero { get; set; }
    public string CodigoNandina { get; set; } = "";
    public string Descripcion { get; set; } = "";
    public string? PaisOrigen { get; set; }
    // Ficha técnica (evita observaciones por mala declaración): marca, modelo y serie
    public string Marca { get; set; } = "";
    public string Modelo { get; set; } = "";
    public string Serie { get; set; } = "";
    public decimal ValorFactura { get; set; }
    public decimal PesoBrutoKg { get; set; }
    public decimal PesoNetoKg { get; set; }
    public decimal Cantidad { get; set; }
    public decimal AlicuotaGA { get; set; }
    public decimal Desgravacion { get; set; }
    public decimal AlicuotaIce { get; set; }
    public decimal IceEspecificoPorUnidad { get; set; }
    public decimal UnidadesIce { get; set; }
    public decimal IehdBsPorLitro { get; set; }
    public decimal Litros { get; set; }
    public string AcuerdoPreferencial { get; set; } = "";   // CAN, ACE 22, ACE 36, ACE 47, ACE 66, VEN... (lo elige el usuario con el Certificado de Origen)
    public int AntiguedadAnios { get; set; }      // vehículos: 0 = nuevo (para el ICE del Apéndice I)

    public ItemImportacion ToCore() => new(Numero, CodigoNandina, Descripcion, ValorFactura, PesoBrutoKg, PesoNetoKg,
        AlicuotaGA, Desgravacion, AlicuotaIce, IceEspecificoPorUnidad, UnidadesIce, IehdBsPorLitro, Litros);
}

public class EtapaRuta
{
    public int Id { get; set; }
    public int OperacionId { get; set; }
    public string Codigo { get; set; } = "";
    public string Nombre { get; set; } = "";
    public string Responsable { get; set; } = "";
    public bool EsHitoLegal { get; set; }
    public bool EsCritica { get; set; }
    public int Holgura { get; set; }
    public DateOnly InicioPlan { get; set; }
    public DateOnly FinPlan { get; set; }
    public DateOnly? FinReal { get; set; }
    public string? Notas { get; set; }
}

/// <summary>Cada cálculo se guarda con versión, parámetros, tipo de cambio y resultado completo: reproducible y auditable.</summary>
public class LiquidacionGuardada
{
    public int Id { get; set; }
    public int OperacionId { get; set; }
    public int Version { get; set; }
    public DateTime CalculadaEn { get; set; }
    public DateOnly TipoCambioFecha { get; set; }
    public string TipoCambioJson { get; set; } = "";
    public string ParametrosJson { get; set; } = "";
    public string ResultadoJson { get; set; } = "";
    public decimal CifBob { get; set; }
    public decimal TotalTributos { get; set; }
}

public class Documento
{
    public int Id { get; set; }
    public int OperacionId { get; set; }
    public TipoDocumento Tipo { get; set; }
    public string NombreArchivo { get; set; } = "";
    public string Ruta { get; set; } = "";
    public string? Sha256 { get; set; }
    public string? OcrJson { get; set; }        // campos propuestos por OCR (pendientes de confirmar)
    public bool Validado { get; set; }          // el usuario revisó y confirmó
    public DateTime AgregadoEn { get; set; }
}

/// <summary>Diario del proceso: de aquí sale la documentación del expediente.</summary>
public class EventoBitacora
{
    public int Id { get; set; }
    public int OperacionId { get; set; }
    public DateTime Fecha { get; set; }
    public string Categoria { get; set; } = "";
    public string Detalle { get; set; } = "";
    public string Usuario { get; set; } = "";
}

public class ComexDb(Microsoft.EntityFrameworkCore.DbContextOptions<ComexDb> o) : Microsoft.EntityFrameworkCore.DbContext(o)
{
    /// <summary>
    /// Crea la base si no existe y agrega las columnas que falten (bases creadas con versiones anteriores).
    /// Solo agrega columnas: nunca borra ni modifica datos. Reemplaza a las migraciones mientras el modelo es joven.
    /// </summary>
    public void AsegurarEsquema()
    {
        Database.EnsureCreated();
        var cn = Database.GetDbConnection();
        if (cn.State != System.Data.ConnectionState.Open) cn.Open();
        // Tablas nuevas (EnsureCreated no las crea si la base ya existía): se ejecutan solo sus CREATE TABLE / CREATE INDEX.
        var tablasExistentes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using (var cmd = cn.CreateCommand())
        {
            cmd.CommandText = "SELECT name FROM sqlite_master WHERE type='table'";
            using var rd = cmd.ExecuteReader(); while (rd.Read()) tablasExistentes.Add(rd.GetString(0));
        }
        var faltan = Model.GetEntityTypes().Select(e => e.GetTableName()).Where(t => t is not null && !tablasExistentes.Contains(t!)).ToHashSet()!;
        if (faltan.Count > 0)
        {
            // El script usa el salto de línea del sistema (CRLF en Windows): se separa con una expresión regular y cada sentencia es idempotente.
            foreach (var raw in System.Text.RegularExpressions.Regex.Split(Database.GenerateCreateScript(), @";\s*\r?\n"))
            {
                var st = raw.Trim().TrimEnd(';'); if (st.Length == 0) continue;
                var crea = st.StartsWith("CREATE TABLE \"") ? faltan.Any(t => st.StartsWith($"CREATE TABLE \"{t}\""))
                    : st.StartsWith("CREATE ") && faltan.Any(t => st.Contains($" ON \"{t}\""));
                if (!crea) continue;
                st = st.Replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ").Replace("CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ").Replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ");
                using var c = cn.CreateCommand(); c.CommandText = st; c.ExecuteNonQuery();
            }
        }
        foreach (var et in Model.GetEntityTypes())
        {
            var tabla = et.GetTableName(); if (tabla is null) continue;
            var existentes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            using (var cmd = cn.CreateCommand())
            {
                cmd.CommandText = $"PRAGMA table_info(\"{tabla}\")";
                using var rd = cmd.ExecuteReader(); while (rd.Read()) existentes.Add(rd.GetString(1));
            }
            foreach (var prop in et.GetProperties())
            {
                var col = prop.GetColumnName(); if (existentes.Contains(col)) continue;
                var tipo = prop.GetColumnType();
                var def = prop.ClrType == typeof(string) ? "''" : prop.ClrType == typeof(bool) || prop.ClrType.IsPrimitive || prop.ClrType == typeof(decimal) || prop.ClrType.IsEnum ? "0" : "''";
                var nulo = Nullable.GetUnderlyingType(prop.ClrType) is not null || prop.IsNullable;
                using var alter = cn.CreateCommand();
                alter.CommandText = $"ALTER TABLE \"{tabla}\" ADD COLUMN \"{col}\" {tipo}{(nulo ? "" : $" NOT NULL DEFAULT {def}")}";
                alter.ExecuteNonQuery();
            }
        }
    }

    public Microsoft.EntityFrameworkCore.DbSet<Operacion> Operaciones => Set<Operacion>();
    public Microsoft.EntityFrameworkCore.DbSet<ItemMercancia> Items => Set<ItemMercancia>();
    public Microsoft.EntityFrameworkCore.DbSet<EtapaRuta> Etapas => Set<EtapaRuta>();
    public Microsoft.EntityFrameworkCore.DbSet<LiquidacionGuardada> Liquidaciones => Set<LiquidacionGuardada>();
    public Microsoft.EntityFrameworkCore.DbSet<Documento> Documentos => Set<Documento>();
    public Microsoft.EntityFrameworkCore.DbSet<EventoBitacora> Bitacora => Set<EventoBitacora>();
    public Microsoft.EntityFrameworkCore.DbSet<PartidaCatalogo> Partidas => Set<PartidaCatalogo>();
    public Microsoft.EntityFrameworkCore.DbSet<Usuario> Usuarios => Set<Usuario>();
    public Microsoft.EntityFrameworkCore.DbSet<TipoCambioRegistro> TiposCambio => Set<TipoCambioRegistro>();
    public Microsoft.EntityFrameworkCore.DbSet<UfvRegistro> Ufvs => Set<UfvRegistro>();
    public Microsoft.EntityFrameworkCore.DbSet<ParametroSistema> Parametros => Set<ParametroSistema>();
    public Microsoft.EntityFrameworkCore.DbSet<PerfilImportador> Perfiles => Set<PerfilImportador>();
    public Microsoft.EntityFrameworkCore.DbSet<CostoOperacion> Costos => Set<CostoOperacion>();

    protected override void OnModelCreating(Microsoft.EntityFrameworkCore.ModelBuilder b)
    {
        b.Entity<Operacion>().HasIndex(x => x.Carpeta).IsUnique();
        b.Entity<PartidaCatalogo>().HasKey(x => x.Codigo);
        b.Entity<Usuario>().HasIndex(x => x.NombreUsuario).IsUnique();
        b.Entity<TipoCambioRegistro>().HasIndex(x => new { x.Fecha, x.Moneda }).IsUnique();
        b.Entity<UfvRegistro>().HasIndex(x => x.Fecha).IsUnique();
        b.Entity<ParametroSistema>().HasKey(x => x.Clave);
        b.Entity<Operacion>().HasMany(x => x.Costos).WithOne().HasForeignKey(x => x.OperacionId);
        b.Entity<Operacion>().HasMany(x => x.Items).WithOne().HasForeignKey(x => x.OperacionId);
        b.Entity<Operacion>().HasMany(x => x.Etapas).WithOne().HasForeignKey(x => x.OperacionId);
        b.Entity<Operacion>().HasMany(x => x.Liquidaciones).WithOne().HasForeignKey(x => x.OperacionId);
        b.Entity<Operacion>().HasMany(x => x.Documentos).WithOne().HasForeignKey(x => x.OperacionId);
        b.Entity<Operacion>().HasMany(x => x.Bitacora).WithOne().HasForeignKey(x => x.OperacionId);
    }
}

public class PartidaCatalogo
{
    public string Codigo { get; set; } = "";           // PK, 10 dígitos
    public string Descripcion { get; set; } = "";
    public decimal AlicuotaGA { get; set; }
    public string Unidad { get; set; } = "";
    public bool Prohibida { get; set; }
    public string Autorizaciones { get; set; } = "";   // separadas por '|'
    public string Fuente { get; set; } = "";
    public string Version { get; set; } = "";
    public string TipoDocumento { get; set; } = "";        // AP, AP y C, C, C*, P, CITES, CCRT, CRTM, DJ
    public string Entidad { get; set; } = "";
    public string DispLegal { get; set; } = "";
    public string ImpuestoEspecial { get; set; } = "";     // ICE | IEHD | ""
    public string IceAntiguedad { get; set; } = "";        // "0.15;0.20;..." tasas por antigüedad (nuevo, 1, 2…; 2 a 6 columnas) o ""
    public bool IceUltimaEsOMas { get; set; }              // la última columna es «≥N años»
    public string DespachoFrontera { get; set; } = "";     // columna «Despacho en Frontera» del arancel
    public string Preferencias { get; set; } = "";         // porcentajes impresos tal cual
    public bool PrefAsignada { get; set; }                 // true = se pudo asignar a las columnas del arancel
    public string PrefCan { get; set; } = "";              // CAN / ACE 36 / ACE 47 / VEN (%)
    public string PrefChile { get; set; } = "";            // ACE 22 Chile (%)
    public string PrefProtocolo { get; set; } = "";        // ACE 22 Protocolo (n.º romano)
    public string PrefMexico { get; set; } = "";           // ACE 66 México (%)
}

public class Usuario
{
    public int Id { get; set; }
    public string NombreUsuario { get; set; } = "";
    public string NombreCompleto { get; set; } = "";
    public string Rol { get; set; } = "Operador";          // Administrador | Operador
    public string ClaveHash { get; set; } = "";
    public string Sal { get; set; } = "";
    public bool Activo { get; set; } = true;
    public DateTime? UltimoAcceso { get; set; }
}

public class TipoCambioRegistro
{
    public int Id { get; set; }
    public DateOnly Fecha { get; set; }
    public string Moneda { get; set; } = "USD";
    public decimal BobPorUnidad { get; set; }              // tipo de cambio oficial de venta (BCB)
    public string Fuente { get; set; } = "Manual";
}

public class UfvRegistro
{
    public int Id { get; set; }
    public DateOnly Fecha { get; set; }
    public decimal ValorBob { get; set; }
}

public class ParametroSistema
{
    public string Clave { get; set; } = "";
    public string Valor { get; set; } = "";
    public string Descripcion { get; set; } = "";
}

public class PerfilImportador
{
    public int Id { get; set; }
    public string RazonSocial { get; set; } = "";
    public string Nit { get; set; } = "";
    public string TipoImportador { get; set; } = "Habitual";   // Habitual | Ocasional
    public string Direccion { get; set; } = "";
    public string Ciudad { get; set; } = "";
    public string Telefono { get; set; } = "";
    public string Correo { get; set; } = "";
    public string AgenciaDespachante { get; set; } = "";
}

/// <summary>Hoja de costos: lo proyectado por el simulador frente a lo realmente pagado.</summary>
public class CostoOperacion
{
    public int Id { get; set; }
    public int OperacionId { get; set; }
    public string Concepto { get; set; } = "";
    public decimal ProyectadoBob { get; set; }
    public decimal? RealBob { get; set; }
    public string Nota { get; set; } = "";
}
