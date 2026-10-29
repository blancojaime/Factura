Namespace Domain

    Public Class EmpresaInfo
        Public Property Id As Integer
        Public Property Codigo As String
        Public Property RazonSocial As String
        Public Property NombreComercial As String
        Public Property Nit As String
        Public Property Direccion As String
        Public Property Ciudad As String
        Public Property Telefono As String
        Public Property Email As String
        Public Property Actividad As String
        Public Property RepLegal As String
        Public Property Matricula As String
        Public Property Carpeta As String
        Public Property Activa As Boolean = True
        Public Property EsDefecto As Boolean
        Public Property FechaCreacion As Date = Date.Today
        Public Property Observacion As String

        Public ReadOnly Property Titulo As String
            Get
                Return If(String.IsNullOrWhiteSpace(NombreComercial), RazonSocial, NombreComercial)
            End Get
        End Property
    End Class

    Public Class GestionInfo
        Public Property Id As Integer
        Public Property EmpresaId As Integer
        Public Property Anio As Integer
        Public Property FechaInicio As Date
        Public Property FechaFin As Date
        ''' <summary>Ruta relativa a la carpeta de datos.</summary>
        Public Property Archivo As String
        ''' <summary>A = abierta, C = cerrada.</summary>
        Public Property Estado As String = "A"
        Public Property CorrelativoMensual As Boolean = True
        Public Property MesInicio As Integer = 1
        Public Property EsDefecto As Boolean
        Public Property FechaCreacion As Date = Date.Today
        Public ReadOnly Property Abierta As Boolean
            Get
                Return Estado = "A"
            End Get
        End Property
    End Class

    Public Class UsuarioInfo
        Public Property Id As Integer
        Public Property Login As String
        Public Property Nombre As String
        Public Property Email As String
        Public Property Activo As Boolean = True
        Public Property EsAdmin As Boolean
        Public Property CambiarClave As Boolean
        Public Property UltimoAcceso As Date?
        Public Property Rol As String = ""
        Public ReadOnly Property Permisos As New HashSet(Of String)(StringComparer.OrdinalIgnoreCase)

        Public Function Puede(opcion As String) As Boolean
            Return EsAdmin OrElse Permisos.Contains(opcion)
        End Function
    End Class

    ''' <summary>Resultado de un cálculo de IVA sobre un importe total de factura.</summary>
    Public Structure ImpuestoFactura
        Public Base As Decimal
        Public Impuesto As Decimal
        Public Neto As Decimal
    End Structure

End Namespace
