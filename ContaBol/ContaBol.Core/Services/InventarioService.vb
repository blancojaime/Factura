Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class ItemDto
        Public Property Id As Integer
        Public Property Codigo As String = ""
        Public Property Descripcion As String = ""
        Public Property Abrev As String = ""
        Public Property GrupoId As Integer
        Public Property UnidadId As Integer
        Public Property EsServicio As Boolean
        Public Property ManejaVenc As Boolean
        Public Property Moneda As String = "BS"
        Public Property UtilidadPct As Decimal
        Public Property StockMin As Decimal
        Public Property CuentaInvId As Integer
        Public Property CuentaIngId As Integer
        Public Property CuentaCostoId As Integer
        Public Property PrecioA As Decimal
        Public Property PrecioB As Decimal
        Public Property PrecioC As Decimal
        Public Property PrecioD As Decimal
        Public Property PrecioE As Decimal
        Public Property PrecioF As Decimal
        Public Property PrecioG As Decimal
        Public Property CodBarra As String = ""
        Public Property Marca As String = ""
        Public Property Activo As Boolean = True
        Public Property Observacion As String = ""

        Public Function Precio(nivel As String) As Decimal
            Select Case If(nivel, "A").ToUpperInvariant()
                Case "B" : Return PrecioB
                Case "C" : Return PrecioC
                Case "D" : Return PrecioD
                Case "E" : Return PrecioE
                Case "F" : Return PrecioF
                Case "G" : Return PrecioG
                Case Else : Return PrecioA
            End Select
        End Function
    End Class

    Public Class MovLine
        Public Property ItemId As Integer
        Public Property Cantidad As Decimal
        ''' <summary>Precio/costo unitario en la moneda del movimiento.</summary>
        Public Property PrecioUnit As Decimal
        Public Property FechaVenc As Date?
        Public Property Lote As String = ""
    End Class

    Public Class MovInvDto
        Public Property Tipo As String = "AJEN"
        Public Property Fecha As Date = Date.Today
        Public Property AlmacenId As Integer
        Public Property AlmacenDestId As Integer
        Public Property TerceroId As Integer
        Public Property Moneda As String = "BS"
        Public Property TC As Decimal = 6.96D
        Public Property Detalle As String = ""
        Public Property DocTipo As String = ""
        Public Property DocId As Integer
        Public ReadOnly Property Lines As New List(Of MovLine)
        Public Property GenerarAsiento As Boolean
        Public Property ContracuentaId As Integer
    End Class

    Public Class MovResultLine
        Public Property ItemId As Integer
        Public Property Cantidad As Decimal
        Public Property CostoUnitBs As Decimal
        Public Property ImporteBs As Decimal
    End Class

    Public Class MovResult
        Public Property MovId As Integer
        Public Property Numero As Integer
        Public Property TotalBs As Decimal
        Public ReadOnly Property Lines As New List(Of MovResultLine)
    End Class

    Public Class KardexItemRow
        Public Property Fecha As Date
        Public Property Documento As String
        Public Property Detalle As String
        Public Property EntCant As Decimal
        Public Property EntCosto As Decimal
        Public Property EntTotal As Decimal
        Public Property SalCant As Decimal
        Public Property SalCosto As Decimal
        Public Property SalTotal As Decimal
        Public Property SaldoCant As Decimal
        Public Property SaldoCosto As Decimal
        Public Property SaldoValor As Decimal
    End Class

    ''' <summary>Control de inventarios multi-almacén, costo promedio ponderado, vencimientos (FEFO) y kardex físico valorado.</summary>
    Public Class InventarioService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        Public Shared Function Signo(tipo As String) As Integer
            Select Case tipo
                Case "COMP", "AJEN", "STIN", "PRPT" : Return 1
                Case "VENT", "AJSA", "PRMP" : Return -1
                Case Else : Return 0 ' TRAS: ambos
            End Select
        End Function

        Public Shared Function NombreTipo(tipo As String) As String
            Select Case tipo
                Case "COMP" : Return "Compra"
                Case "VENT" : Return "Venta"
                Case "AJEN" : Return "Ajuste de entrada"
                Case "AJSA" : Return "Ajuste de salida"
                Case "STIN" : Return "Stock inicial"
                Case "TRAS" : Return "Traspaso"
                Case "PRMP" : Return "Consumo de materia prima"
                Case "PRPT" : Return "Producto terminado"
                Case Else : Return tipo
            End Select
        End Function

        ' ---------- Ítems ----------
        Public Function ListarItems(Optional texto As String = "", Optional soloActivos As Boolean = False) As DataTable
            Dim dt As DataTable = Db.Query("SELECT * FROM Item" & If(soloActivos, " WHERE Activo=1", "") & " ORDER BY Codigo")
            If texto <> "" Then
                Dim t As String = texto.ToLowerInvariant()
                For i As Integer = dt.Rows.Count - 1 To 0 Step -1
                    Dim r As DataRow = dt.Rows(i)
                    If Not (r.GetS("Codigo").ToLowerInvariant().Contains(t) OrElse r.GetS("Descripcion").ToLowerInvariant().Contains(t) OrElse r.GetS("CodBarra").ToLowerInvariant().Contains(t)) Then dt.Rows.RemoveAt(i)
                Next
            End If
            Return dt
        End Function

        Public Function ObtenerItem(id As Integer) As ItemDto
            Dim dt As DataTable = Db.Query("SELECT * FROM Item WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Return LeerItem(dt.Rows(0))
        End Function

        Public Function BuscarItem(codigoOBarra As String) As ItemDto
            Dim dt As DataTable = Db.Query("SELECT * FROM Item WHERE Codigo=@c", "c", If(codigoOBarra, "").Trim().ToUpperInvariant())
            If dt.Rows.Count = 0 Then dt = Db.Query("SELECT * FROM Item WHERE CodBarra=@c", "c", If(codigoOBarra, "").Trim())
            If dt.Rows.Count = 0 Then Return Nothing
            Return LeerItem(dt.Rows(0))
        End Function

        Private Shared Function LeerItem(r As DataRow) As ItemDto
            Return New ItemDto With {
                .Id = r.GetI("Id"), .Codigo = r.GetS("Codigo"), .Descripcion = r.GetS("Descripcion"), .Abrev = r.GetS("Abrev"), .GrupoId = r.GetI("GrupoId"),
                .UnidadId = r.GetI("UnidadId"), .EsServicio = r.GetF("EsServicio"), .ManejaVenc = r.GetF("ManejaVenc"), .Moneda = r.GetS("Moneda"),
                .UtilidadPct = r.GetD("UtilidadPct"), .StockMin = r.GetD("StockMin"), .CuentaInvId = r.GetI("CuentaInvId"), .CuentaIngId = r.GetI("CuentaIngId"),
                .CuentaCostoId = r.GetI("CuentaCostoId"), .PrecioA = r.GetD("PrecioA"), .PrecioB = r.GetD("PrecioB"), .PrecioC = r.GetD("PrecioC"),
                .PrecioD = r.GetD("PrecioD"), .PrecioE = r.GetD("PrecioE"), .PrecioF = r.GetD("PrecioF"), .PrecioG = r.GetD("PrecioG"),
                .CodBarra = r.GetS("CodBarra"), .Marca = r.GetS("Marca"), .Activo = r.GetF("Activo"), .Observacion = r.GetS("Observacion")}
        End Function

        Public Function GuardarItem(it As ItemDto) As Integer
            _ctx.Requiere("INV.ITEMS")
            _ctx.RequiereGestionAbierta()
            it.Codigo = If(it.Codigo, "").Trim().ToUpperInvariant()
            If it.Codigo = "" Then Throw New ArgumentException("El código del ítem es obligatorio.")
            If If(it.Descripcion, "").Trim() = "" Then Throw New ArgumentException("La descripción del ítem es obligatoria.")
            If it.Codigo.Length > 25 Then Throw New ArgumentException("El código admite hasta 25 caracteres.")
            Dim dup As Object = Db.Scalar("SELECT Id FROM Item WHERE Codigo=@c", "c", it.Codigo)
            If dup IsNot Nothing AndAlso ToInt(dup) <> it.Id Then Throw New InvalidOperationException("El código " & it.Codigo & " ya existe.")
            If it.UnidadId = 0 Then it.UnidadId = ToInt(Db.Scalar("SELECT MIN(Id) FROM UnidadMedida"))
            If it.Id = 0 Then
                If it.CuentaInvId = 0 AndAlso Not it.EsServicio Then it.CuentaInvId = _ctx.CuentaParamOpcional(ParamKeys.CtaInventario)
                If it.CuentaIngId = 0 Then it.CuentaIngId = _ctx.CuentaParamOpcional(ParamKeys.CtaVentas)
                If it.CuentaCostoId = 0 Then it.CuentaCostoId = _ctx.CuentaParamOpcional(ParamKeys.CtaCostoVentas)
                it.Id = Db.Insert("INSERT INTO Item (Codigo, Descripcion, Abrev, GrupoId, UnidadId, EsServicio, ManejaVenc, Moneda, UtilidadPct, StockMin, CuentaInvId, CuentaIngId, CuentaCostoId, PrecioA, PrecioB, PrecioC, PrecioD, PrecioE, PrecioF, PrecioG, CodBarra, Marca, Activo, Stock, CostoProm, UltimoCosto, Observacion) " &
                                  "VALUES (@c, @d, @ab, @g, @u, @es, @mv, @mo, @ut, @sm, @ci, @cg, @cc, @pa, @pb, @pc, @pd, @pe, @pf, @pg, @cb, @ma, @ac, 0, 0, 0, @ob)",
                                  "c", it.Codigo, "d", it.Descripcion, "ab", it.Abrev, "g", OrNull(it.GrupoId), "u", it.UnidadId, "es", If(it.EsServicio, 1, 0), "mv", If(it.ManejaVenc, 1, 0),
                                  "mo", it.Moneda, "ut", CDbl(it.UtilidadPct), "sm", CDbl(it.StockMin), "ci", OrNull(it.CuentaInvId), "cg", OrNull(it.CuentaIngId), "cc", OrNull(it.CuentaCostoId),
                                  "pa", CDbl(it.PrecioA), "pb", CDbl(it.PrecioB), "pc", CDbl(it.PrecioC), "pd", CDbl(it.PrecioD), "pe", CDbl(it.PrecioE), "pf", CDbl(it.PrecioF), "pg", CDbl(it.PrecioG),
                                  "cb", it.CodBarra, "ma", it.Marca, "ac", If(it.Activo, 1, 0), "ob", it.Observacion)
                _ctx.Audit("Inventarios", "ITEM_NUEVO", it.Codigo & " " & it.Descripcion)
            Else
                Db.Execute("UPDATE Item SET Codigo=@c, Descripcion=@d, Abrev=@ab, GrupoId=@g, UnidadId=@u, EsServicio=@es, ManejaVenc=@mv, Moneda=@mo, UtilidadPct=@ut, StockMin=@sm, CuentaInvId=@ci, CuentaIngId=@cg, CuentaCostoId=@cc, PrecioA=@pa, PrecioB=@pb, PrecioC=@pc, PrecioD=@pd, PrecioE=@pe, PrecioF=@pf, PrecioG=@pg, CodBarra=@cb, Marca=@ma, Activo=@ac, Observacion=@ob WHERE Id=@i",
                           "c", it.Codigo, "d", it.Descripcion, "ab", it.Abrev, "g", OrNull(it.GrupoId), "u", it.UnidadId, "es", If(it.EsServicio, 1, 0), "mv", If(it.ManejaVenc, 1, 0),
                           "mo", it.Moneda, "ut", CDbl(it.UtilidadPct), "sm", CDbl(it.StockMin), "ci", OrNull(it.CuentaInvId), "cg", OrNull(it.CuentaIngId), "cc", OrNull(it.CuentaCostoId),
                           "pa", CDbl(it.PrecioA), "pb", CDbl(it.PrecioB), "pc", CDbl(it.PrecioC), "pd", CDbl(it.PrecioD), "pe", CDbl(it.PrecioE), "pf", CDbl(it.PrecioF), "pg", CDbl(it.PrecioG),
                           "cb", it.CodBarra, "ma", it.Marca, "ac", If(it.Activo, 1, 0), "ob", it.Observacion, "i", it.Id)
                _ctx.Audit("Inventarios", "ITEM_MOD", it.Codigo)
            End If
            Return it.Id
        End Function

        Public Sub EliminarItem(id As Integer)
            _ctx.Requiere("INV.ITEMS")
            If Db.ScalarInt("SELECT COUNT(*) FROM MovInvDet WHERE ItemId=@i", "i", id) > 0 Then Throw New InvalidOperationException("El ítem tiene movimientos. Márquelo como inactivo.")
            Db.Execute("DELETE FROM Item WHERE Id=@i", "i", id)
            _ctx.Audit("Inventarios", "ITEM_ELIM", id.ToString())
        End Sub

        ''' <summary>Precio de venta sugerido = costo promedio × (1 + utilidad%).</summary>
        Public Function ActualizarPreciosDesdeCosto(Optional itemId As Integer = 0) As Integer
            _ctx.Requiere("INV.ITEMS")
            Dim dt As DataTable = Db.Query("SELECT Id, CostoProm, UtilidadPct FROM Item WHERE EsServicio=0 AND CostoProm > 0" & If(itemId <> 0, " AND Id=" & itemId, ""))
            Dim n As Integer = 0
            Db.InTx(Sub()
                        For Each r As DataRow In dt.Rows
                            Dim p As Decimal = (r.GetD("CostoProm") * (1D + r.GetD("UtilidadPct") / 100D)).R2()
                            Db.Execute("UPDATE Item SET PrecioA=@p WHERE Id=@i", "p", CDbl(p), "i", r.GetI("Id"))
                            n += 1
                        Next
                    End Sub)
            _ctx.Audit("Inventarios", "PRECIOS_ACTUALIZADOS", n & " ítems")
            Return n
        End Function

        ' ---------- Existencias ----------
        Public Function Stock(itemId As Integer, Optional almacenId As Integer = 0, Optional hasta As Date? = Nothing) As Decimal
            Dim sql As String = "SELECT SUM(Signo * Cantidad) FROM MovInvDet WHERE ItemId=@i AND Vigente=1"
            Dim args As New List(Of Object) From {"i", itemId}
            If almacenId <> 0 Then
                sql &= " AND AlmacenId=@a"
                args.AddRange({"a", almacenId})
            End If
            If hasta.HasValue Then
                sql &= " AND Fecha <= @h"
                args.AddRange({"h", hasta.Value.Date})
            End If
            Return Math.Round(Db.ScalarDec(sql, args.ToArray()), 6)
        End Function

        ''' <summary>Existencias valoradas por ítem (y almacén) a una fecha.</summary>
        Public Function Existencias(hasta As Date, Optional almacenId As Integer = 0, Optional soloConStock As Boolean = False) As DataTable
            Dim res As New DataTable()
            res.Columns.Add("Codigo", GetType(String))
            res.Columns.Add("Descripcion", GetType(String))
            res.Columns.Add("Unidad", GetType(String))
            res.Columns.Add("Stock", GetType(Decimal))
            res.Columns.Add("CostoUnit", GetType(Decimal))
            res.Columns.Add("Valor", GetType(Decimal))
            res.Columns.Add("StockMin", GetType(Decimal))
            Dim unidades As New Dictionary(Of Integer, String)
            For Each u As DataRow In Db.Query("SELECT Id, Codigo FROM UnidadMedida").Rows
                unidades(u.GetI("Id")) = u.GetS("Codigo")
            Next
            Dim sql As String = "SELECT ItemId, SUM(Signo * Cantidad) AS Q FROM MovInvDet WHERE Vigente=1 AND Fecha <= @h"
            Dim args As New List(Of Object) From {"h", hasta.Date}
            If almacenId <> 0 Then
                sql &= " AND AlmacenId=@a"
                args.AddRange({"a", almacenId})
            End If
            sql &= " GROUP BY ItemId"
            Dim q As New Dictionary(Of Integer, Decimal)
            For Each r As DataRow In Db.Query(sql, args.ToArray()).Rows
                q(r.GetI("ItemId")) = Math.Round(r.GetD("Q"), 6)
            Next
            For Each it As DataRow In Db.Query("SELECT * FROM Item WHERE EsServicio=0 ORDER BY Codigo").Rows
                Dim s As Decimal = 0D
                q.TryGetValue(it.GetI("Id"), s)
                If soloConStock AndAlso s = 0D Then Continue For
                Dim costo As Decimal = it.GetD("CostoProm")
                res.Rows.Add(it.GetS("Codigo"), it.GetS("Descripcion"), If(unidades.ContainsKey(it.GetI("UnidadId")), unidades(it.GetI("UnidadId")), ""), s, costo, (s * costo).R2(), it.GetD("StockMin"))
            Next
            Return res
        End Function

        Public Function SugerenciaCompras() As DataTable
            Dim ex As DataTable = Existencias(Date.Today.AddYears(100), 0, False)
            Dim res As DataTable = ex.Clone()
            res.Columns.Add("Falta", GetType(Decimal))
            For Each r As DataRow In ex.Rows
                If r.GetD("StockMin") > 0D AndAlso r.GetD("Stock") < r.GetD("StockMin") Then
                    Dim n As DataRow = res.NewRow()
                    For Each c As DataColumn In ex.Columns
                        n(c.ColumnName) = r(c.ColumnName)
                    Next
                    n("Falta") = r.GetD("StockMin") - r.GetD("Stock")
                    res.Rows.Add(n)
                End If
            Next
            Return res
        End Function

        ''' <summary>Lotes con vencimiento anterior o igual a la fecha (vencidos o por vencer) con saldo positivo.</summary>
        Public Function PorVencer(hasta As Date, Optional almacenId As Integer = 0) As DataTable
            Dim sql As String = "SELECT ItemId, AlmacenId, FechaVenc, SUM(Signo * Cantidad) AS Q FROM MovInvDet WHERE Vigente=1 AND FechaVenc IS NOT NULL"
            Dim args As New List(Of Object)
            If almacenId <> 0 Then
                sql &= " AND AlmacenId=@a"
                args.AddRange({"a", almacenId})
            End If
            sql &= " GROUP BY ItemId, AlmacenId, FechaVenc"
            Dim res As New DataTable()
            res.Columns.Add("Codigo", GetType(String))
            res.Columns.Add("Descripcion", GetType(String))
            res.Columns.Add("Almacen", GetType(String))
            res.Columns.Add("Vencimiento", GetType(Date))
            res.Columns.Add("Cantidad", GetType(Decimal))
            res.Columns.Add("Dias", GetType(Integer))
            Dim alm As New Dictionary(Of Integer, String)
            For Each a As DataRow In Db.Query("SELECT Id, Nombre FROM Almacen").Rows
                alm(a.GetI("Id")) = a.GetS("Nombre")
            Next
            For Each r As DataRow In Db.Query(sql, args.ToArray()).Rows
                Dim q As Decimal = Math.Round(r.GetD("Q"), 6)
                Dim fv As Date = r.GetDt("FechaVenc")
                If q <= 0D OrElse fv > hasta.Date Then Continue For
                Dim it As ItemDto = ObtenerItem(r.GetI("ItemId"))
                res.Rows.Add(it.Codigo, it.Descripcion, If(alm.ContainsKey(r.GetI("AlmacenId")), alm(r.GetI("AlmacenId")), ""), fv, q, CInt((fv - Date.Today).TotalDays))
            Next
            Dim v As DataView = res.DefaultView
            v.Sort = "Vencimiento, Codigo"
            Return v.ToTable()
        End Function

        ' ---------- Movimientos ----------
        Private Function CostoUnitario(l As MovLine, moneda As String, tc As Decimal) As Decimal
            Dim c As Decimal = If(moneda = "USD", l.PrecioUnit * tc, l.PrecioUnit)
            Return Math.Round(c, 6)
        End Function

        ''' <summary>Registra un ajuste, traspaso o stock inicial (con asiento opcional).</summary>
        Public Function Registrar(m As MovInvDto) As MovResult
            _ctx.Requiere("INV.MOVIMIENTOS")
            If m.Tipo <> "AJEN" AndAlso m.Tipo <> "AJSA" AndAlso m.Tipo <> "STIN" AndAlso m.Tipo <> "TRAS" Then Throw New ArgumentException("Tipo de movimiento no permitido.")
            Return Db.InTx(Function()
                               Dim r As MovResult = Aplicar(m)
                               If m.GenerarAsiento AndAlso m.Tipo <> "TRAS" Then
                                   If m.ContracuentaId = 0 Then Throw New ArgumentException("Seleccione la contracuenta para el asiento contable.")
                                   Dim vs As New VoucherService(_ctx)
                                   Dim v As Voucher = vs.Nuevo("T", m.Fecha)
                                   v.Glosa = NombreTipo(m.Tipo) & " Nº " & r.Numero & If(m.Detalle <> "", " - " & m.Detalle, "")
                                   v.Origen = "INV"
                                   v.OrigenId = r.MovId
                                   Dim grupos = r.Lines.GroupBy(Function(l) CuentaInventario(l.ItemId))
                                   For Each g In grupos
                                       Dim imp As Decimal = g.Sum(Function(l) l.ImporteBs)
                                       If imp = 0D Then Continue For
                                       If Signo(m.Tipo) > 0 Then
                                           v.Lines.Add(VoucherLine.Deb(g.Key, imp, v.Glosa))
                                       Else
                                           v.Lines.Add(VoucherLine.Hab(g.Key, imp, v.Glosa))
                                       End If
                                   Next
                                   If Signo(m.Tipo) > 0 Then
                                       v.Lines.Add(VoucherLine.Hab(m.ContracuentaId, r.TotalBs, v.Glosa))
                                   Else
                                       v.Lines.Add(VoucherLine.Deb(m.ContracuentaId, r.TotalBs, v.Glosa))
                                   End If
                                   If v.Lines.Count >= 2 AndAlso r.TotalBs > 0D Then
                                       Dim vid As Integer = vs.Registrar(v)
                                       Db.Execute("UPDATE MovInv SET ComprobanteId=@c WHERE Id=@i", "c", vid, "i", r.MovId)
                                   End If
                               End If
                               _ctx.Audit("Inventarios", "MOV_" & m.Tipo, "Nº " & r.Numero & " Bs " & r.TotalBs.ToString("N2"))
                               Return r
                           End Function)
        End Function

        Friend Function CuentaInventario(itemId As Integer) As Integer
            Dim it As ItemDto = ObtenerItem(itemId)
            If it IsNot Nothing AndAlso it.CuentaInvId <> 0 Then Return it.CuentaInvId
            Return _ctx.CuentaParam(ParamKeys.CtaInventario)
        End Function

        ''' <summary>Núcleo de registro de movimientos de inventario (sin permisos ni asientos). Debe ejecutarse dentro de una transacción.</summary>
        Friend Function Aplicar(m As MovInvDto) As MovResult
            _ctx.RequiereGestionAbierta()
            If m.Lines.Count = 0 Then Throw New InvalidOperationException("Agregue al menos un ítem.")
            If m.AlmacenId = 0 Then Throw New InvalidOperationException("Seleccione el almacén.")
            If m.Tipo = "TRAS" Then
                If m.AlmacenDestId = 0 Then Throw New InvalidOperationException("Seleccione el almacén destino.")
                If m.AlmacenDestId = m.AlmacenId Then Throw New InvalidOperationException("El almacén origen y destino deben ser distintos.")
            End If
            If m.Fecha.Date < _ctx.Gestion.FechaInicio.Date OrElse m.Fecha.Date > _ctx.Gestion.FechaFin.Date Then Throw New InvalidOperationException("La fecha está fuera de la gestión.")
            Dim res As New MovResult()
            Dim numero As Integer = _ctx.Siguiente("MOV_" & m.Tipo)
            Dim movId As Integer = Db.Insert("INSERT INTO MovInv (Tipo, Numero, Fecha, AlmacenId, AlmacenDestId, TerceroId, Moneda, TC, Detalle, Estado, DocTipo, DocId, ComprobanteId, UsuarioId, Creado, TotalBs) VALUES (@t, @n, @f, @a, @ad, @te, @mo, @tc, @d, 'V', @dt, @di, 0, @u, @cr, 0)",
                                             "t", m.Tipo, "n", numero, "f", m.Fecha.Date, "a", m.AlmacenId, "ad", OrNull(m.AlmacenDestId), "te", OrNull(m.TerceroId), "mo", m.Moneda,
                                             "tc", CDbl(m.TC), "d", m.Detalle, "dt", m.DocTipo, "di", m.DocId, "u", _ctx.Usuario.Id, "cr", Date.Now)
            res.MovId = movId
            res.Numero = numero
            Dim sg As Integer = Signo(m.Tipo)
            Dim linea As Integer = 0
            Dim pendientesSalida As New Dictionary(Of String, Decimal) ' clave item|almacen: cantidad ya consumida en este mismo movimiento
            For Each l As MovLine In m.Lines
                If l.Cantidad <= 0D Then Throw New InvalidOperationException("La cantidad debe ser mayor a cero.")
                Dim item As DataRow = Db.Query("SELECT * FROM Item WHERE Id=@i", "i", l.ItemId).Rows.Cast(Of DataRow)().FirstOrDefault()
                If item Is Nothing Then Throw New InvalidOperationException("Ítem inexistente.")
                If item.GetF("EsServicio") Then Continue For
                Dim cod As String = item.GetS("Codigo")
                If sg > 0 Then
                    Dim costo As Decimal = CostoUnitario(l, m.Moneda, m.TC)
                    If costo < 0D Then Throw New InvalidOperationException("El precio de " & cod & " no puede ser negativo.")
                    If item.GetF("ManejaVenc") AndAlso Not l.FechaVenc.HasValue AndAlso m.Tipo <> "STIN" Then
                        Throw New InvalidOperationException("El ítem " & cod & " maneja fecha de vencimiento: ingrésela.")
                    End If
                    linea += 1
                    InsertarDet(movId, linea, l.ItemId, m.AlmacenId, m.Fecha, 1, l.Cantidad, l.PrecioUnit, costo, l.FechaVenc, l.Lote)
                    ActualizarCacheEntrada(item, l.Cantidad, costo)
                    res.Lines.Add(New MovResultLine With {.ItemId = l.ItemId, .Cantidad = l.Cantidad, .CostoUnitBs = costo, .ImporteBs = (l.Cantidad * costo).R2()})
                Else
                    ' salida o traspaso
                    Dim costoSalida As Decimal = Math.Round(item.GetD("CostoProm"), 6)
                    Dim disponible As Decimal = Stock(l.ItemId, m.AlmacenId)
                    Dim clave As String = l.ItemId & "|" & m.AlmacenId
                    Dim yaUsado As Decimal = 0D
                    pendientesSalida.TryGetValue(clave, yaUsado)
                    If disponible - yaUsado < l.Cantidad AndAlso Not _ctx.Param.Bool(ParamKeys.StockNegativo) Then
                        Throw New InvalidOperationException("Stock insuficiente de " & cod & " " & item.GetS("Descripcion") & ": disponible " & (disponible - yaUsado).ToString("N2") & ", solicitado " & l.Cantidad.ToString("N2") & ".")
                    End If
                    pendientesSalida(clave) = yaUsado + l.Cantidad
                    Dim restante As Decimal = l.Cantidad
                    If item.GetF("ManejaVenc") Then
                        For Each lote In LotesDisponibles(l.ItemId, m.AlmacenId)
                            If restante <= 0D Then Exit For
                            Dim tomar As Decimal = Math.Min(restante, lote.Item2)
                            linea += 1
                            InsertarDet(movId, linea, l.ItemId, m.AlmacenId, m.Fecha, -1, tomar, l.PrecioUnit, costoSalida, lote.Item1, "")
                            If m.Tipo = "TRAS" Then
                                linea += 1
                                InsertarDet(movId, linea, l.ItemId, m.AlmacenDestId, m.Fecha, 1, tomar, l.PrecioUnit, costoSalida, lote.Item1, "")
                            End If
                            restante -= tomar
                        Next
                    End If
                    If restante > 0D Then
                        linea += 1
                        InsertarDet(movId, linea, l.ItemId, m.AlmacenId, m.Fecha, -1, restante, l.PrecioUnit, costoSalida, Nothing, "")
                        If m.Tipo = "TRAS" Then
                            linea += 1
                            InsertarDet(movId, linea, l.ItemId, m.AlmacenDestId, m.Fecha, 1, restante, l.PrecioUnit, costoSalida, Nothing, "")
                        End If
                    End If
                    If m.Tipo <> "TRAS" Then
                        Db.Execute("UPDATE Item SET Stock = Stock - @q WHERE Id=@i", "q", CDbl(l.Cantidad), "i", l.ItemId)
                    End If
                    res.Lines.Add(New MovResultLine With {.ItemId = l.ItemId, .Cantidad = l.Cantidad, .CostoUnitBs = costoSalida, .ImporteBs = (l.Cantidad * costoSalida).R2()})
                End If
            Next
            res.TotalBs = res.Lines.Sum(Function(x) x.ImporteBs)
            Db.Execute("UPDATE MovInv SET TotalBs=@t WHERE Id=@i", "t", res.TotalBs, "i", movId)
            Return res
        End Function

        Private Sub InsertarDet(movId As Integer, linea As Integer, itemId As Integer, almacenId As Integer, fecha As Date, signo As Integer, cant As Decimal, precio As Decimal, costo As Decimal, venc As Date?, lote As String)
            Db.Execute("INSERT INTO MovInvDet (MovId, Linea, ItemId, AlmacenId, Fecha, Signo, Cantidad, PrecioUnit, CostoUnitBs, ImporteBs, FechaVenc, Lote, Vigente) VALUES (@m, @l, @i, @a, @f, @s, @c, @p, @co, @im, @v, @lo, 1)",
                       "m", movId, "l", linea, "i", itemId, "a", almacenId, "f", fecha.Date, "s", signo, "c", CDbl(cant), "p", CDbl(precio), "co", CDbl(costo),
                       "im", (cant * costo).R2(), "v", OrNull(venc), "lo", lote)
        End Sub

        Private Sub ActualizarCacheEntrada(item As DataRow, cant As Decimal, costo As Decimal)
            Dim stock As Decimal = Math.Round(item.GetD("Stock"), 6)
            Dim cp As Decimal = item.GetD("CostoProm")
            Dim nuevo As Decimal
            If stock > 0D Then
                nuevo = Math.Round((stock * cp + cant * costo) / (stock + cant), 6)
            Else
                nuevo = costo
            End If
            Db.Execute("UPDATE Item SET Stock=@s, CostoProm=@c, UltimoCosto=@u WHERE Id=@i", "s", CDbl(stock + cant), "c", CDbl(nuevo), "u", CDbl(costo), "i", item.GetI("Id"))
        End Sub

        ''' <summary>Lotes con saldo, ordenados por vencimiento más próximo (FEFO). Importe: (fecha, cantidad).</summary>
        Private Function LotesDisponibles(itemId As Integer, almacenId As Integer) As List(Of Tuple(Of Date?, Decimal))
            Dim dt As DataTable = Db.Query("SELECT FechaVenc, SUM(Signo * Cantidad) AS Q FROM MovInvDet WHERE ItemId=@i AND AlmacenId=@a AND Vigente=1 GROUP BY FechaVenc", "i", itemId, "a", almacenId)
            Dim l As New List(Of Tuple(Of Date?, Decimal))
            For Each r As DataRow In dt.Rows
                Dim q As Decimal = Math.Round(r.GetD("Q"), 6)
                If q > 0D AndAlso Not IsNil(r("FechaVenc")) Then l.Add(Tuple.Create(ToDateOrNull(r("FechaVenc")), q))
            Next
            Return l.OrderBy(Function(x) x.Item1).ToList()
        End Function

        ''' <summary>Anula un movimiento y recalcula existencias y costo promedio de los ítems afectados.</summary>
        Public Sub Anular(movId As Integer, motivo As String)
            _ctx.Requiere("INV.MOVIMIENTOS")
            AnularInterno(movId, motivo)
        End Sub

        Friend Sub AnularInterno(movId As Integer, motivo As String)
            _ctx.RequiereGestionAbierta()
            Dim dt As DataTable = Db.Query("SELECT * FROM MovInv WHERE Id=@i", "i", movId)
            If dt.Rows.Count = 0 Then Throw New InvalidOperationException("Movimiento inexistente.")
            Dim h As DataRow = dt.Rows(0)
            If h.GetS("Estado") = "A" Then Return
            Dim dets As DataTable = Db.Query("SELECT ItemId, AlmacenId, Signo, SUM(Cantidad) AS Q FROM MovInvDet WHERE MovId=@m AND Vigente=1 GROUP BY ItemId, AlmacenId, Signo", "m", movId)
            If Not _ctx.Param.Bool(ParamKeys.StockNegativo) Then
                For Each d As DataRow In dets.Rows
                    If d.GetI("Signo") > 0 AndAlso Stock(d.GetI("ItemId"), d.GetI("AlmacenId")) < d.GetD("Q") Then
                        Dim it As ItemDto = ObtenerItem(d.GetI("ItemId"))
                        Throw New InvalidOperationException("No se puede anular: el stock actual de " & it.Codigo & " es menor a lo ingresado en este movimiento (ya fue vendido o trasladado).")
                    End If
                Next
            End If
            Db.InTx(Sub()
                        Db.Execute("UPDATE MovInv SET Estado='A' WHERE Id=@i", "i", movId)
                        Db.Execute("UPDATE MovInvDet SET Vigente=0 WHERE MovId=@i", "i", movId)
                        For Each id As Integer In dets.Rows.Cast(Of DataRow)().Select(Function(r) r.GetI("ItemId")).Distinct()
                            RecalcularItem(id)
                        Next
                        Dim cid As Integer = h.GetI("ComprobanteId")
                        If cid <> 0 Then
                            Dim vsv As New VoucherService(_ctx)
                            vsv.AnularInterno(cid, "Anulación movimiento de inventario: " & motivo)
                        End If
                    End Sub)
            _ctx.Audit("Inventarios", "MOV_ANULADO", h.GetS("Tipo") & " Nº " & h.GetS("Numero") & ": " & motivo)
        End Sub

        ''' <summary>Reconstruye existencia y costo promedio ponderado de un ítem desde sus movimientos vigentes.</summary>
        Public Sub RecalcularItem(itemId As Integer)
            Dim dt As DataTable = Db.Query("SELECT Signo, Cantidad, CostoUnitBs FROM MovInvDet WHERE ItemId=@i AND Vigente=1 ORDER BY Fecha, Id", "i", itemId)
            Dim stock As Decimal = 0D, costo As Decimal = 0D, ultimo As Decimal = 0D
            ' Los traspasos (salida+entrada al mismo costo) se neutralizan: solo se consideran los movimientos que cambian la existencia total.
            For Each r As DataRow In dt.Rows
                Dim q As Decimal = r.GetD("Cantidad")
                Dim c As Decimal = r.GetD("CostoUnitBs")
                If r.GetI("Signo") > 0 Then
                    If stock > 0D Then costo = Math.Round((stock * costo + q * c) / (stock + q), 6) Else costo = c
                    stock += q
                    ultimo = c
                Else
                    stock -= q
                End If
            Next
            Db.Execute("UPDATE Item SET Stock=@s, CostoProm=@c, UltimoCosto=@u WHERE Id=@i", "s", CDbl(Math.Round(stock, 6)), "c", CDbl(costo), "u", CDbl(ultimo), "i", itemId)
        End Sub

        Public Sub RecalcularTodo()
            _ctx.Requiere("INV.MOVIMIENTOS")
            For Each r As DataRow In Db.Query("SELECT Id FROM Item WHERE EsServicio=0").Rows
                RecalcularItem(r.GetI("Id"))
            Next
            _ctx.Audit("Inventarios", "RECALCULO", "Existencias y costos recalculados")
        End Sub

        ' ---------- Kardex ----------
        Public Function Kardex(itemId As Integer, almacenId As Integer, desde As Date, hasta As Date) As List(Of KardexItemRow)
            Dim res As New List(Of KardexItemRow)
            Dim sqlAnt As String = "SELECT Signo, Cantidad, CostoUnitBs FROM MovInvDet WHERE ItemId=@i AND Vigente=1 AND Fecha < @d"
            Dim sqlMov As String = "SELECT d.Id, d.MovId, d.Fecha, d.Signo, d.Cantidad, d.CostoUnitBs, d.AlmacenId FROM MovInvDet d WHERE d.ItemId=@i AND d.Vigente=1 AND d.Fecha >= @d AND d.Fecha <= @h"
            Dim args As New List(Of Object) From {"i", itemId, "d", desde.Date}
            Dim argsM As New List(Of Object) From {"i", itemId, "d", desde.Date, "h", hasta.Date}
            If almacenId <> 0 Then
                sqlAnt &= " AND AlmacenId=" & almacenId
                sqlMov &= " AND d.AlmacenId=" & almacenId
            End If
            ' Saldo y valor al inicio (valorado a costo promedio móvil)
            Dim qty As Decimal = 0D, valor As Decimal = 0D
            ' Para el costo promedio de arranque se reconstruye el histórico completo del ítem (global) hasta la fecha desde.
            Dim hist As DataTable = Db.Query("SELECT Signo, Cantidad, CostoUnitBs, AlmacenId FROM MovInvDet WHERE ItemId=@i AND Vigente=1 AND Fecha < @d ORDER BY Fecha, Id", "i", itemId, "d", desde.Date)
            Dim stockG As Decimal = 0D, costoG As Decimal = 0D
            For Each r As DataRow In hist.Rows
                Dim q As Decimal = r.GetD("Cantidad")
                Dim c As Decimal = r.GetD("CostoUnitBs")
                If r.GetI("Signo") > 0 Then
                    If stockG > 0D Then costoG = (stockG * costoG + q * c) / (stockG + q) Else costoG = c
                    stockG += q
                Else
                    stockG -= q
                End If
                If almacenId = 0 OrElse r.GetI("AlmacenId") = almacenId Then qty += r.GetI("Signo") * q
            Next
            valor = (qty * costoG).R2()
            res.Add(New KardexItemRow With {.Fecha = desde.Date, .Documento = "", .Detalle = "SALDO INICIAL", .SaldoCant = qty, .SaldoCosto = If(qty <> 0D, costoG, 0D), .SaldoValor = valor})
            Dim movs As Dictionary(Of Integer, Tuple(Of String, String)) = EtiquetasMov()
            For Each r As DataRow In Db.Query(sqlMov & " ORDER BY d.Fecha, d.Id", argsM.ToArray()).Rows
                Dim q As Decimal = r.GetD("Cantidad")
                Dim c As Decimal = r.GetD("CostoUnitBs")
                Dim imp As Decimal = (q * c).R2()
                Dim et As Tuple(Of String, String) = Nothing
                movs.TryGetValue(r.GetI("MovId"), et)
                Dim row As New KardexItemRow With {.Fecha = r.GetDt("Fecha"), .Documento = If(et Is Nothing, "", et.Item1), .Detalle = If(et Is Nothing, "", et.Item2)}
                If r.GetI("Signo") > 0 Then
                    row.EntCant = q : row.EntCosto = c : row.EntTotal = imp
                    qty += q : valor += imp
                Else
                    row.SalCant = q : row.SalCosto = c : row.SalTotal = imp
                    qty -= q : valor -= imp
                End If
                row.SaldoCant = qty
                row.SaldoValor = valor
                row.SaldoCosto = If(qty <> 0D, Math.Round(valor / qty, 4), 0D)
                res.Add(row)
            Next
            Return res
        End Function

        Private Function EtiquetasMov() As Dictionary(Of Integer, Tuple(Of String, String))
            Dim d As New Dictionary(Of Integer, Tuple(Of String, String))
            For Each r As DataRow In Db.Query("SELECT Id, Tipo, Numero, Detalle FROM MovInv").Rows
                d(r.GetI("Id")) = Tuple.Create(r.GetS("Tipo") & "-" & r.GetS("Numero"), NombreTipo(r.GetS("Tipo")) & If(r.GetS("Detalle") <> "", ": " & r.GetS("Detalle"), ""))
            Next
            Return d
        End Function

        Public Function ListarMovimientos(desde As Date, hasta As Date, Optional tipo As String = "") As DataTable
            Dim sql As String = "SELECT Id, Tipo, Numero, Fecha, AlmacenId, Detalle, Estado, TotalBs, ComprobanteId FROM MovInv WHERE Fecha >= @d AND Fecha <= @h"
            Dim args As New List(Of Object) From {"d", desde.Date, "h", hasta.Date}
            If tipo <> "" Then
                sql &= " AND Tipo=@t"
                args.AddRange({"t", tipo})
            End If
            Return Db.Query(sql & " ORDER BY Fecha, Id", args.ToArray())
        End Function

    End Class

End Namespace
