Imports System.IO
Imports System.Data.OleDb
Imports System.Text
Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    ''' <summary>Origen de datos de una instalación de Orion4 (carpeta de una empresa/gestión con ORION.MDB, PRU.MDB e INVENT.MDB).</summary>
    Public Interface IOrionOrigen
        Function Existe(archivo As String, tabla As String) As Boolean
        Function Tabla(archivo As String, nombreTabla As String) As DataTable
    End Interface

    ''' <summary>Lee las bases .MDB de Orion4 con OleDb (requiere el motor Access Database Engine de Windows).</summary>
    Public Class OrionOleDbOrigen
        Implements IOrionOrigen

        Private ReadOnly _carpeta As String

        Public Sub New(carpeta As String)
            _carpeta = carpeta
        End Sub

        Private Function Ruta(archivo As String) As String
            For Each f As String In Directory.GetFiles(_carpeta, "*.mdb")
                If Path.GetFileNameWithoutExtension(f).Equals(archivo, StringComparison.OrdinalIgnoreCase) Then Return f
            Next
            Return Nothing
        End Function

        Public Function Existe(archivo As String, tabla As String) As Boolean Implements IOrionOrigen.Existe
            Dim r As String = Ruta(archivo)
            If r Is Nothing Then Return False
            Try
                Using cn As New OleDbConnection("Provider=" & AccessProvider.DetectProvider() & ";Data Source=" & r & ";Mode=Read;")
                    cn.Open()
                    Dim dt As DataTable = cn.GetSchema("Tables", New String() {Nothing, Nothing, tabla, "TABLE"})
                    Return dt.Rows.Count > 0
                End Using
            Catch
                Return False
            End Try
        End Function

        Public Function Tabla(archivo As String, tabla1 As String) As DataTable Implements IOrionOrigen.Tabla
            Dim r As String = Ruta(archivo)
            If r Is Nothing Then Throw New FileNotFoundException("No se encontró " & archivo & ".MDB en " & _carpeta)
            Using cn As New OleDbConnection("Provider=" & AccessProvider.DetectProvider() & ";Data Source=" & r & ";Mode=Read;")
                cn.Open()
                Using da As New OleDbDataAdapter("SELECT * FROM [" & tabla1 & "]", cn)
                    Dim dt As New DataTable()
                    da.Fill(dt)
                    Return dt
                End Using
            End Using
        End Function
    End Class

    Public Class ImportacionResultado
        Public Property EmpresaId As Integer
        Public Property GestionId As Integer
        Public Property Cuentas As Integer
        Public Property Comprobantes As Integer
        Public Property Terceros As Integer
        Public Property Items As Integer
        Public Property Facturas As Integer
        Public ReadOnly Property Avisos As New List(Of String)
    End Class

    ''' <summary>Migra los datos contables de una empresa/gestión de Orion4 a una nueva empresa de ContaBol.</summary>
    Public Class OrionImportService
        Private ReadOnly _sis As SistemaService

        Public Sub New(sis As SistemaService)
            _sis = sis
        End Sub

        Private Shared ReadOnly Meses As String() = {"ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"}

        Private Shared Function MesDe(texto As String, fecha As Date) As Integer
            Dim t As String = If(texto, "").Trim().ToUpperInvariant()
            For i As Integer = 0 To 11
                If t.StartsWith(Meses(i).Substring(0, 3)) Then Return i + 1
            Next
            Return fecha.Month
        End Function

        Private Shared Function Limpia(s As String) As String
            Return If(s, "").Replace(vbCr, " ").Replace(vbLf, " ").Trim()
        End Function

        Public Function Importar(origen As IOrionOrigen, codigoEmpresa As String, usuario As UsuarioInfo, Optional correlativoMensual As Boolean = True) As ImportacionResultado
            If Not usuario.Puede("ADM.IMPORTAR") Then Throw New UnauthorizedAccessException("No tiene permiso para importar datos.")
            Dim res As New ImportacionResultado()
            If Not origen.Existe("PRU", "CUENTAS") OrElse Not origen.Existe("PRU", "OFICINAS") Then Throw New InvalidOperationException("La carpeta no contiene una base de datos Orion4 válida (PRU.MDB).")
            Dim ofi As DataTable = origen.Tabla("PRU", "OFICINAS")
            If ofi.Rows.Count = 0 Then Throw New InvalidOperationException("No se encontraron los datos de la empresa (tabla OFICINAS).")
            Dim o As DataRow = ofi.Rows(0)
            Dim anio As Integer = ToInt(o.GetS("GESTION"))
            If anio < 1990 Then anio = Date.Today.Year
            Dim emp As New EmpresaInfo With {.Codigo = codigoEmpresa, .RazonSocial = Limpia(o.GetS("NOMBRES")), .Nit = Limpia(o.GetS("RUC")), .Direccion = Limpia(o.GetS("DIRECCION"))}
            Dim ids = New EmpresaService(_sis).CrearEmpresa(emp, New NuevaGestionOpciones With {.Anio = anio, .CorrelativoMensual = correlativoMensual, .Plantilla = PlantillaPlan.Vacio}, usuario.Id)
            res.EmpresaId = ids.Item1
            res.GestionId = ids.Item2
            Using c As Contexto = _sis.AbrirContexto(usuario, ids.Item1, ids.Item2)
                c.Db.InTx(Sub()
                              ImportarPlan(origen, c, res)
                              ImportarParametros(o, c, res)
                              ImportarTipoCambio(origen, c)
                              ImportarTerceros(origen, c, res)
                              ImportarItems(origen, c, res)
                              ImportarComprobantes(origen, c, res)
                              ImportarLibros(origen, c, res)
                          End Sub)
                c.Audit("Importación", "ORION4", res.Cuentas & " cuentas, " & res.Comprobantes & " comprobantes")
            End Using
            Return res
        End Function

        Private Sub ImportarPlan(origen As IOrionOrigen, c As Contexto, res As ImportacionResultado)
            Dim lineas As New List(Of String)
            Dim vistos As New HashSet(Of String)
            For Each r As DataRow In origen.Tabla("PRU", "CUENTAS").Rows
                Dim cod As String = Limpia(r.GetS("CODIGO"))
                If cod = "" OrElse Not vistos.Add(cod) Then Continue For
                If cod(0) < "1"c OrElse cod(0) > "7"c Then
                    res.Avisos.Add("Cuenta omitida (rubro inválido): " & cod)
                    Continue For
                End If
                Dim nombre As String = Limpia(r.GetS("NOMBRE")).TrimEnd(":"c, "|"c, " "c)
                If nombre = "" Then nombre = "Cuenta " & cod
                Dim flags As New StringBuilder()
                Dim usd As Boolean = Limpia(r.GetS("SUS")).ToUpperInvariant() = "SI"
                If usd Then flags.Append("U"c)
                Dim aj As String = Limpia(r.GetS("AJUSTABLE")).ToUpperInvariant()
                If (aj = "S" OrElse aj = "U") AndAlso Not usd AndAlso cod(0) <= "3"c Then flags.Append("A"c)
                If Limpia(r.GetS("PRESUPUESTO")).ToUpperInvariant() = "S" Then flags.Append("P"c)
                Dim cs As String = Limpia(r.GetS("COSTO")).ToUpperInvariant()
                If cs = "F" OrElse cs = "V" Then flags.Append(cs)
                lineas.Add(cod & ";" & nombre.Replace(";"c, ","c) & ";" & flags.ToString())
            Next
            EmpresaService.CargarPlan(c.Db, lineas)
            c.InvalidarCuentas()
            res.Cuentas = lineas.Count
        End Sub

        Private Shared Function CodigoSiExiste(c As Contexto, valor As String) As String
            Dim v As String = Limpia(valor)
            If v = "" OrElse v = "0" Then Return ""
            Return If(c.CuentaPorCodigo(v) IsNot Nothing, v, "")
        End Function

        Private Sub ImportarParametros(o As DataRow, c As Contexto, res As ImportacionResultado)
            c.Param.Guardar(ParamKeys.IvaPct, ToDec(o.Cell("piva")).ToString(Inv))
            c.Param.Guardar(ParamKeys.ItPct, ToDec(o.Cell("pite")).ToString(Inv))
            Dim mapa As String(,) = {
                {"CREDITO", ParamKeys.CtaCreditoFiscal}, {"DEBITO", ParamKeys.CtaDebitoFiscal}, {"IT", ParamKeys.CtaItGasto}, {"ITXP", ParamKeys.CtaItPagar},
                {"antcli", ParamKeys.CtaAnticipoCli}, {"antpro", ParamKeys.CtaAnticipoProv}, {"cinve", ParamKeys.CtaInventario},
                {"sysxpagar", ParamKeys.CtaSueldosPagar}, {"aporxpagar", ParamKeys.CtaAfpLaboralPagar}, {"aporpatronal", ParamKeys.CtaAfpPatronalPagar},
                {"agui", ParamKeys.CtaProvAguinaldo}, {"indem", ParamKeys.CtaProvIndem}, {"rciva", ParamKeys.CtaRcIvaPagar}}
            Dim asignadas As New HashSet(Of String)
            For i As Integer = 0 To mapa.GetLength(0) - 1
                Dim cod As String = CodigoSiExiste(c, o.GetS(mapa(i, 0)))
                c.Param.Guardar(mapa(i, 1), cod)
                If cod <> "" Then asignadas.Add(mapa(i, 1))
            Next
            ' Las demás cuentas de parámetros que no existan en el plan importado se limpian para que el sistema pida configurarlas.
            For Each kv In Seed.PlanBase.ParametrosPorDefecto()
                If kv.Key.StartsWith("CTA_", StringComparison.Ordinal) AndAlso Not asignadas.Contains(kv.Key) Then
                    c.Param.Guardar(kv.Key, If(c.CuentaPorCodigo(kv.Value) IsNot Nothing, kv.Value, ""))
                End If
            Next
            Dim faltan As New List(Of String)
            For Each k As String In {ParamKeys.CtaCaja, ParamKeys.CtaVentas, ParamKeys.CtaCostoVentas, ParamKeys.CtaCxc, ParamKeys.CtaCxp, ParamKeys.CtaResultadoGestion, ParamKeys.CtaResultadoAcum}
                If c.Param.Valor(k) = "" Then faltan.Add(k)
            Next
            If faltan.Count > 0 Then res.Avisos.Add("Configure en Administración > Parámetros las cuentas: " & String.Join(", ", faltan))
        End Sub

        Private Sub ImportarTipoCambio(origen As IOrionOrigen, c As Contexto)
            If Not origen.Existe("PRU", "TIPO") Then Return
            Dim tc As New TipoCambioService(c)
            For Each r As DataRow In origen.Tabla("PRU", "TIPO").Rows
                Dim f As Date = r.GetDt("FECHA")
                Dim v As Decimal = ToDec(r.Cell("TCAMBIO"))
                If f < c.Gestion.FechaInicio OrElse f > c.Gestion.FechaFin OrElse v <= 0D Then Continue For
                Dim n As Integer = c.Db.Execute("UPDATE TipoCambio SET Usd=@u WHERE Fecha=@f", "u", CDbl(v), "f", f.Date)
                If n = 0 Then c.Db.Execute("INSERT INTO TipoCambio (Fecha, Usd, Ufv) VALUES (@f, @u, 0)", "f", f.Date, "u", CDbl(v))
            Next
        End Sub

        Private Sub ImportarTerceros(origen As IOrionOrigen, c As Contexto, res As ImportacionResultado)
            Dim ts As New TerceroService(c)
            For Each par In {Tuple.Create("cli", True), Tuple.Create("PRO", False)}
                If Not origen.Existe("ORION", par.Item1) Then Continue For
                For Each r As DataRow In origen.Tabla("ORION", par.Item1).Rows
                    Dim nombre As String = Limpia(r.GetS("NOMBRE"))
                    If nombre = "" Then Continue For
                    Dim t As New TerceroDto With {.Codigo = If(par.Item2, "C", "P") & Limpia(r.GetS("CODIGO")).ToUpperInvariant(), .Nombre = nombre, .Nit = Limpia(r.GetS("RUC")), .Direccion = Limpia(r.GetS("DIRECCION")),
                        .Telefono = Limpia(r.GetS("TELEFONO")), .Actividad = Limpia(r.GetS("ACTIVIDAD")), .EsCliente = par.Item2, .EsProveedor = Not par.Item2,
                        .LimiteCredito = If(par.Item2, ToDec(r.Cell("limcre")), 0D), .Activo = Limpia(r.GetS("ESTADO")).ToUpperInvariant() <> "INACTIVO"}
                    Try
                        ts.Guardar(t)
                        res.Terceros += 1
                    Catch ex As Exception
                        res.Avisos.Add("Tercero omitido (" & nombre & "): " & ex.Message)
                    End Try
                Next
            Next
        End Sub

        Private Sub ImportarItems(origen As IOrionOrigen, c As Contexto, res As ImportacionResultado)
            If Not origen.Existe("ORION", "lista") Then Return
            Dim inv As New InventarioService(c)
            For Each r As DataRow In origen.Tabla("ORION", "lista").Rows
                Dim cod As String = Limpia(r.GetS("item")).ToUpperInvariant()
                If cod = "" Then Continue For
                Dim it As New ItemDto With {.Codigo = cod, .Descripcion = Limpia(r.GetS("descripcion")), .Abrev = Limpia(r.GetS("desabrev")), .ManejaVenc = Limpia(r.GetS("ven")).ToUpperInvariant() = "SI",
                    .Moneda = If(Limpia(r.GetS("moneda")).ToUpperInvariant().StartsWith("S"), "USD", "BS"), .UtilidadPct = ToDec(r.Cell("util")), .StockMin = ToDec(r.Cell("minima")),
                    .PrecioA = ToDec(r.Cell("precioa")), .PrecioB = ToDec(r.Cell("preciob")), .PrecioC = ToDec(r.Cell("precioc")), .PrecioD = ToDec(r.Cell("preciod")),
                    .PrecioE = ToDec(r.Cell("precioe")), .PrecioF = ToDec(r.Cell("preciof")), .PrecioG = ToDec(r.Cell("preciog"))}
                If it.Descripcion = "" Then it.Descripcion = cod
                Dim a As DataRow = c.CuentaPorCodigo(Limpia(r.GetS("activo")))
                If a IsNot Nothing Then it.CuentaInvId = a.GetI("Id")
                a = c.CuentaPorCodigo(Limpia(r.GetS("ingreso")))
                If a IsNot Nothing Then it.CuentaIngId = a.GetI("Id")
                a = c.CuentaPorCodigo(Limpia(r.GetS("costo")))
                If a IsNot Nothing Then it.CuentaCostoId = a.GetI("Id")
                Try
                    inv.GuardarItem(it)
                    res.Items += 1
                Catch ex As Exception
                    res.Avisos.Add("Ítem omitido (" & cod & "): " & ex.Message)
                End Try
            Next
        End Sub

        Private Sub ImportarComprobantes(origen As IOrionOrigen, c As Contexto, res As ImportacionResultado)
            Dim vs As New VoucherService(c)
            Dim dt As DataTable = origen.Tabla("PRU", "DIARIOS")
            Dim grupos = dt.Rows.Cast(Of DataRow)().GroupBy(Function(r) Limpia(r.GetS("TCOM")).ToUpperInvariant() & "|" & MesDe(r.GetS("MES"), r.GetDt("FECHA")) & "|" & r.GetI("NUMERO"))
            Dim tiposCreados As New Dictionary(Of String, String)
            For Each g In grupos.OrderBy(Function(x) x.First().GetDt("FECHA")).ThenBy(Function(x) x.First().GetI("NUMERO"))
                Dim primera As DataRow = g.First()
                Dim tcom As String = Limpia(primera.GetS("TCOM")).ToUpperInvariant()
                Dim tipo As String
                Select Case tcom
                    Case "DIARIO", "TRASPASO" : tipo = "T"
                    Case "INGRESO" : tipo = "I"
                    Case "EGRESO" : tipo = "E"
                    Case Else
                        If Not tiposCreados.TryGetValue(tcom, tipo) Then
                            Dim cod As String = If(tcom.Length >= 2, tcom.Substring(0, 2), "OT")
                            Dim n As Integer = 0
                            While c.Db.ScalarInt("SELECT COUNT(*) FROM TipoComprobante WHERE Codigo=@c", "c", cod) > 0
                                n += 1
                                cod = If(tcom.Length >= 1, tcom.Substring(0, 1), "O") & n.ToString()
                            End While
                            c.Db.Execute("INSERT INTO TipoComprobante (Codigo, Nombre, Sistema, Activo) VALUES (@c, @n, 0, 1)", "c", cod, "n", If(tcom = "", "Otros", tcom))
                            tiposCreados(tcom) = cod
                            tipo = cod
                        End If
                End Select
                Dim v As New Voucher With {.TipoCodigo = tipo, .Fecha = primera.GetDt("FECHA").Date, .Moneda = "BS", .NumeroFijo = primera.GetI("NUMERO"), .MesFijo = MesDe(primera.GetS("MES"), primera.GetDt("FECHA")), .Origen = "ORI"}
                v.TC = ToDec(primera.Cell("TC"))
                If v.TC <= 0D Then v.TC = c.Param.Dec(ParamKeys.TcDefecto, 6.96D)
                v.Glosa = Limpia(If(primera.GetS("glosa2") <> "", primera.GetS("glosa2"), primera.GetS("GLOSA")))
                If v.Glosa.Length > 255 Then v.Glosa = v.Glosa.Substring(0, 255)
                v.Cheque = Limpia(primera.GetS("CHEQUE"))
                v.Banco = Limpia(primera.GetS("BANCO"))
                Dim ok As Boolean = True
                For Each r As DataRow In g
                    Dim cod As String = Limpia(r.GetS("CODIGO"))
                    Dim cta As DataRow = c.CuentaPorCodigo(cod)
                    If cta Is Nothing Then
                        res.Avisos.Add("Comprobante " & tcom & " " & primera.GetI("NUMERO") & ": cuenta inexistente " & cod)
                        ok = False
                        Exit For
                    End If
                    Dim d As Decimal = ToDec(r.Cell("DEBE")).R2(), h As Decimal = ToDec(r.Cell("HABER")).R2()
                    If d = 0D AndAlso h = 0D Then Continue For
                    Dim l As New VoucherLine With {.CuentaId = cta.GetI("Id"), .Glosa = Limpia(r.GetS("DESCRIP"))}
                    If d <> 0D Then
                        l.Debe = d
                        l.DebeUsdFijo = ToDec(r.Cell("DEBESUS")).R2()
                    End If
                    If h <> 0D Then
                        l.Haber = h
                        l.HaberUsdFijo = ToDec(r.Cell("HASUS")).R2()
                    End If
                    If l.Debe < 0D OrElse l.Haber < 0D Then
                        ' importes negativos: se invierten de lado
                        Dim t As Decimal = l.Debe
                        l.Debe = -l.Haber
                        l.Haber = -t
                    End If
                    v.Lines.Add(l)
                Next
                If Not ok Then Continue For
                Dim dif As Decimal = v.TotalDebe - v.TotalHaber
                If Math.Abs(dif) > 0.05D Then
                    res.Avisos.Add("Comprobante " & tcom & " " & primera.GetI("NUMERO") & " (" & primera.GetDt("FECHA").ToString("dd/MM/yyyy") & ") no cuadra en Orion (diferencia " & dif.ToString("N2") & "): omitido")
                    Continue For
                End If
                Try
                    vs.Registrar(v)
                    res.Comprobantes += 1
                Catch ex As Exception
                    res.Avisos.Add("Comprobante " & tcom & " " & primera.GetI("NUMERO") & ": " & ex.Message)
                End Try
            Next
        End Sub

        Private Sub ImportarLibros(origen As IOrionOrigen, c As Contexto, res As ImportacionResultado)
            For Each par In {Tuple.Create("COMPRAS", "C"), Tuple.Create("VENTAS", "V")}
                If Not origen.Existe("PRU", par.Item1) Then Continue For
                For Each r As DataRow In origen.Tabla("PRU", par.Item1).Rows
                    Dim f As Date = r.GetDt("FECHA")
                    If f < c.Gestion.FechaInicio OrElse f > c.Gestion.FechaFin Then Continue For
                    Dim total As Decimal = ToDec(r.Cell("TOTAL")).R2()
                    Dim noSuj As Decimal = ToDec(r.Cell("ICE")).R2()
                    Dim exento As Decimal = ToDec(r.Cell("EXECENTOS")).R2()
                    Dim sub1 As Decimal = total - noSuj - exento
                    Dim imp As Decimal = ToDec(r.Cell("CREDITO")).R2()
                    c.Db.Execute("INSERT INTO FacturaIva (Libro, Fecha, Mes, NroFactura, Autorizacion, CodControl, Nit, RazonSocial, ImporteTotal, NoSujeto, Exento, TasaCero, Subtotal, Descuento, GiftCard, BaseCf, Impuesto, Estado, TipoOp, Dui, Sucursal, ComprobanteId, Origen, OrigenId, UsuarioId, Creado) " &
                                 "VALUES (@l, @f, @m, @nf, @au, '', @nit, @rs, @it, @ns, @ex, 0, @st, 0, 0, @bc, @im, 'V', '', '', @su, 0, 'ORI', 0, @u, @cr)",
                                 "l", par.Item2, "f", f.Date, "m", f.Month, "nf", Limpia(r.GetS("FACTURA")), "au", Limpia(r.GetS("ALFA")), "nit", Limpia(r.GetS("RUC")), "rs", Limpia(r.GetS("PROVEEDOR")),
                                 "it", total, "ns", noSuj, "ex", exento, "st", sub1, "bc", sub1, "im", imp, "su", Limpia(r.GetS("SUCU")), "u", c.Usuario.Id, "cr", Date.Now)
                    res.Facturas += 1
                Next
            Next
        End Sub

    End Class

End Namespace
