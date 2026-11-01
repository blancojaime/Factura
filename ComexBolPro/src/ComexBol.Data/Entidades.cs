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
}

public class ItemMercancia
{
    public int Id { get; set; }
    public int OperacionId { get; set; }
    public int Numero { get; set; }
    public string CodigoNandina { get; set; } = "";
    public string Descripcion { get; set; } = "";
    public string? PaisOrigen { get; set; }
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
}

public class ComexDb(Microsoft.EntityFrameworkCore.DbContextOptions<ComexDb> o) : Microsoft.EntityFrameworkCore.DbContext(o)
{
    public Microsoft.EntityFrameworkCore.DbSet<Operacion> Operaciones => Set<Operacion>();
    public Microsoft.EntityFrameworkCore.DbSet<ItemMercancia> Items => Set<ItemMercancia>();
    public Microsoft.EntityFrameworkCore.DbSet<EtapaRuta> Etapas => Set<EtapaRuta>();
    public Microsoft.EntityFrameworkCore.DbSet<LiquidacionGuardada> Liquidaciones => Set<LiquidacionGuardada>();
    public Microsoft.EntityFrameworkCore.DbSet<Documento> Documentos => Set<Documento>();
    public Microsoft.EntityFrameworkCore.DbSet<EventoBitacora> Bitacora => Set<EventoBitacora>();
    public Microsoft.EntityFrameworkCore.DbSet<PartidaCatalogo> Partidas => Set<PartidaCatalogo>();

    protected override void OnModelCreating(Microsoft.EntityFrameworkCore.ModelBuilder b)
    {
        b.Entity<Operacion>().HasIndex(x => x.Carpeta).IsUnique();
        b.Entity<PartidaCatalogo>().HasKey(x => x.Codigo);
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
}
