Imports ContaBol.Core.Common
Imports ContaBol.Core.Services

Namespace Reports

    Public Enum ParamTipo
        Fecha
        Mes
        Texto
        Entero
        Importe
        Bool
        Lista
        Cuenta
        Tercero
        Cliente
        Proveedor
        Item
        Almacen
        Empleado
        CuentaBanco
        Orden
        Comprobante
    End Enum

    Public Class ParamDef
        Public Property Clave As String
        Public Property Titulo As String
        Public Property Tipo As ParamTipo
        Public Property Defecto As Func(Of Contexto, Object)
        ''' <summary>Opciones para ParamTipo.Lista: (valor, texto).</summary>
        Public ReadOnly Property Opciones As New List(Of KeyValuePair(Of String, String))
        Public Property Requerido As Boolean
        Public Property Ayuda As String = ""
    End Class

    ''' <summary>Parámetros ya resueltos de una ejecución de reporte.</summary>
    Public Class Parametros_
        Private ReadOnly _d As Dictionary(Of String, Object)

        Public Sub New(d As Dictionary(Of String, Object))
            _d = d
        End Sub

        Public Function Tiene(clave As String) As Boolean
            Return _d.ContainsKey(clave) AndAlso _d(clave) IsNot Nothing
        End Function

        Public Function Fecha(clave As String) As Date
            Return If(Tiene(clave), ToDate(_d(clave)), Date.Today)
        End Function

        Public Function Entero(clave As String, Optional defecto As Integer = 0) As Integer
            Return If(Tiene(clave), ToInt(_d(clave)), defecto)
        End Function

        Public Function Texto(clave As String, Optional defecto As String = "") As String
            Return If(Tiene(clave), ToStr(_d(clave)), defecto)
        End Function

        Public Function Dec(clave As String) As Decimal
            Return If(Tiene(clave), ToDec(_d(clave)), 0D)
        End Function

        Public Function Bool(clave As String, Optional defecto As Boolean = False) As Boolean
            Return If(Tiene(clave), ToFlag(_d(clave)), defecto)
        End Function
    End Class

    Public Class ReporteCat
        Public Property Id As String
        Public Property Titulo As String
        Public Property Modulo As String
        Public Property Permiso As String
        Public Property Descripcion As String = ""
        Public ReadOnly Property Params As New List(Of ParamDef)
        Public Property Construir As Func(Of Contexto, Parametros_, ReporteDef)

        Public Function Ejecutar(ctx As Contexto, valores As Dictionary(Of String, Object)) As ReporteDef
            ctx.Requiere(Permiso)
            For Each p As ParamDef In Params
                If p.Requerido AndAlso (Not valores.ContainsKey(p.Clave) OrElse valores(p.Clave) Is Nothing OrElse (TypeOf valores(p.Clave) Is Integer AndAlso CInt(valores(p.Clave)) = 0 AndAlso p.Tipo <> ParamTipo.Entero AndAlso p.Tipo <> ParamTipo.Mes)) Then
                    Throw New InvalidOperationException("Seleccione: " & p.Titulo)
                End If
            Next
            Dim rep As ReporteDef = Construir(ctx, New Parametros_(valores))
            rep.Usuario = ctx.Usuario.Login
            If rep.Empresa = "" Then
                rep.Empresa = ctx.Param.Valor(Domain.ParamKeys.EmpNombre)
                rep.Nit = ctx.Param.Valor(Domain.ParamKeys.EmpNit)
                rep.Direccion = ctx.Param.Valor(Domain.ParamKeys.EmpDireccion)
                rep.Gestion = ctx.Gestion.Anio.ToString()
            End If
            Return rep
        End Function

        Public Function ValoresPorDefecto(ctx As Contexto) As Dictionary(Of String, Object)
            Dim d As New Dictionary(Of String, Object)
            For Each p As ParamDef In Params
                d(p.Clave) = If(p.Defecto IsNot Nothing, p.Defecto(ctx), Nothing)
            Next
            Return d
        End Function
    End Class

    ''' <summary>Catálogo central de reportes: cada módulo del sistema consume los mismos informes (PDF, Excel, pantalla).</summary>
    Public Module Catalogo

        Private _todos As List(Of ReporteCat)

        Public Const ModContabilidad As String = "Contabilidad"
        Public Const ModIva As String = "Libros IVA"
        Public Const ModComercial As String = "Clientes y proveedores"
        Public Const ModInventarios As String = "Inventarios"
        Public Const ModActivos As String = "Activos fijos"
        Public Const ModPlanillas As String = "Planillas"
        Public Const ModCostos As String = "Costos y producción"
        Public Const ModAdmin As String = "Administración"

        Public ReadOnly Property Todos As List(Of ReporteCat)
            Get
                If _todos Is Nothing Then
                    _todos = New List(Of ReporteCat)
                    InformesContables.Registrar(_todos)
                    InformesIva.Registrar(_todos)
                    InformesComerciales.Registrar(_todos)
                    InformesInventario.Registrar(_todos)
                    InformesOtros.Registrar(_todos)
                End If
                Return _todos
            End Get
        End Property

        Public Function Buscar(id As String) As ReporteCat
            Return Todos.FirstOrDefault(Function(r) r.Id.Equals(id, StringComparison.OrdinalIgnoreCase))
        End Function

        Public Function DeModulo(modulo As String) As List(Of ReporteCat)
            Return Todos.Where(Function(r) r.Modulo = modulo).ToList()
        End Function

        ' ---------- Constructores de parámetros ----------
        Public Function PFecha(clave As String, titulo As String, Optional defecto As Func(Of Contexto, Object) = Nothing) As ParamDef
            Return New ParamDef With {.Clave = clave, .Titulo = titulo, .Tipo = ParamTipo.Fecha, .Defecto = defecto}
        End Function

        Public Function PDesde() As ParamDef
            Return PFecha("desde", "Desde", Function(c) CObj(c.Gestion.FechaInicio))
        End Function

        Public Function PHasta() As ParamDef
            Return PFecha("hasta", "Hasta", Function(c) CObj(If(Date.Today > c.Gestion.FechaFin OrElse Date.Today < c.Gestion.FechaInicio, c.Gestion.FechaFin, Date.Today)))
        End Function

        Public Function PMes(Optional titulo As String = "Mes") As ParamDef
            Return New ParamDef With {.Clave = "mes", .Titulo = titulo, .Tipo = ParamTipo.Mes, .Defecto = Function(c) CObj(If(Date.Today >= c.Gestion.FechaInicio AndAlso Date.Today <= c.Gestion.FechaFin, Date.Today.Month, c.Gestion.FechaInicio.Month))}
        End Function

        Public Function PMoneda(Optional conAmbas As Boolean = True) As ParamDef
            Dim p As New ParamDef With {.Clave = "moneda", .Titulo = "Moneda", .Tipo = ParamTipo.Lista, .Defecto = Function(c) CObj("BS")}
            p.Opciones.Add(New KeyValuePair(Of String, String)("BS", "Bolivianos"))
            p.Opciones.Add(New KeyValuePair(Of String, String)("USD", "Dólares"))
            If conAmbas Then p.Opciones.Add(New KeyValuePair(Of String, String)("AMBAS", "Bimonetario (Bs y $us)"))
            Return p
        End Function

        Public Function PNivel(Optional defecto As Integer = 9) As ParamDef
            Return New ParamDef With {.Clave = "nivel", .Titulo = "Hasta nivel de cuenta", .Tipo = ParamTipo.Entero, .Defecto = Function(c) CObj(defecto)}
        End Function

        Public Function PBool(clave As String, titulo As String, Optional defecto As Boolean = False) As ParamDef
            Return New ParamDef With {.Clave = clave, .Titulo = titulo, .Tipo = ParamTipo.Bool, .Defecto = Function(c) CObj(defecto)}
        End Function

        Public Function PLista(clave As String, titulo As String, ParamArray opciones() As String) As ParamDef
            Dim p As New ParamDef With {.Clave = clave, .Titulo = titulo, .Tipo = ParamTipo.Lista}
            For Each o As String In opciones
                Dim a As String() = o.Split("|"c)
                p.Opciones.Add(New KeyValuePair(Of String, String)(a(0), If(a.Length > 1, a(1), a(0))))
            Next
            If p.Opciones.Count > 0 Then
                Dim primero As String = p.Opciones(0).Key
                p.Defecto = Function(c) CObj(primero)
            End If
            Return p
        End Function

        Public Function PEnt(clave As String, titulo As String, Optional defecto As Integer = 0) As ParamDef
            Return New ParamDef With {.Clave = clave, .Titulo = titulo, .Tipo = ParamTipo.Entero, .Defecto = Function(c) CObj(defecto)}
        End Function

        Public Function PTxt(clave As String, titulo As String, Optional defecto As String = "") As ParamDef
            Return New ParamDef With {.Clave = clave, .Titulo = titulo, .Tipo = ParamTipo.Texto, .Defecto = Function(c) CObj(defecto)}
        End Function

        Public Function PDec(clave As String, titulo As String) As ParamDef
            Return New ParamDef With {.Clave = clave, .Titulo = titulo, .Tipo = ParamTipo.Importe, .Defecto = Function(c) CObj(0D)}
        End Function

        Public Function PRef(clave As String, titulo As String, tipo As ParamTipo, Optional requerido As Boolean = False) As ParamDef
            Return New ParamDef With {.Clave = clave, .Titulo = titulo, .Tipo = tipo, .Requerido = requerido, .Defecto = Function(c) CObj(0)}
        End Function

        Public Function Rep(id As String, titulo As String, modulo As String, permiso As String, construir As Func(Of Contexto, Parametros_, ReporteDef), ParamArray ps() As ParamDef) As ReporteCat
            Dim r As New ReporteCat With {.Id = id, .Titulo = titulo, .Modulo = modulo, .Permiso = permiso, .Construir = construir}
            r.Params.AddRange(ps)
            Return r
        End Function

    End Module

    ''' <summary>Utilitarios comunes para armar reportes.</summary>
    Public Module BaseInforme

        Public Function Nuevo(ctx As Contexto, titulo As String, Optional periodo As String = "", Optional moneda As String = "BS") As ReporteDef
            Dim r As New ReporteDef With {
                .Titulo = titulo, .Periodo = periodo, .Empresa = ctx.Param.Valor(Domain.ParamKeys.EmpNombre), .Nit = ctx.Param.Valor(Domain.ParamKeys.EmpNit),
                .Direccion = ctx.Param.Valor(Domain.ParamKeys.EmpDireccion), .Gestion = ctx.Gestion.Anio.ToString(), .Usuario = ctx.Usuario.Login, .Hoja = titulo, .NombreArchivo = titulo.Replace(" ", "_")}
            r.Moneda = TextoMoneda(moneda)
            Return r
        End Function

        Public Function TextoMoneda(moneda As String) As String
            Select Case moneda
                Case "USD" : Return "(Expresado en Dólares Americanos)"
                Case "AMBAS" : Return "(Expresado en Bolivianos y Dólares Americanos)"
                Case "" : Return ""
                Case Else : Return "(Expresado en Bolivianos)"
            End Select
        End Function

        Public Function Rango(d As Date, h As Date) As String
            Return "Del " & d.ToString("dd/MM/yyyy") & " al " & h.ToString("dd/MM/yyyy")
        End Function

        Public Function Etiqueta(tipo As String, numero As Integer, mes As Integer) As String
            Return tipo & "-" & numero.ToString() & If(mes > 0, "/" & mes.ToString("00"), "")
        End Function

    End Module

End Namespace
