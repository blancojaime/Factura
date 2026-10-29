Imports System.Text
Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class BalanceRow
        Public Property CuentaId As Integer
        Public Property Codigo As String
        Public Property Nombre As String
        Public Property Nivel As Integer
        Public Property Rubro As Integer
        Public Property Naturaleza As String
        Public Property EsMovimiento As Boolean
        Public Property AntD As Decimal
        Public Property AntH As Decimal
        Public Property Debe As Decimal
        Public Property Haber As Decimal
        Public Property SaldoD As Decimal
        Public Property SaldoH As Decimal
        ''' <summary>Saldo final neto (Debe - Haber).</summary>
        Public ReadOnly Property Neto As Decimal
            Get
                Return SaldoD - SaldoH
            End Get
        End Property
        ''' <summary>Saldo en el sentido natural de la cuenta (positivo si está en su naturaleza).</summary>
        Public ReadOnly Property Natural As Decimal
            Get
                Return If(Naturaleza = "D", Neto, -Neto)
            End Get
        End Property
    End Class

    Public Class MayorMov
        Public Property Fecha As Date
        Public Property ComprobanteId As Integer
        Public Property Comprobante As String
        Public Property CuentaCodigo As String
        Public Property Glosa As String
        Public Property Debe As Decimal
        Public Property Haber As Decimal
        Public Property Saldo As Decimal
    End Class

    Public Class MayorResult
        Public Property CuentaId As Integer
        Public Property Codigo As String
        Public Property Nombre As String
        Public Property Naturaleza As String
        Public Property SaldoAnterior As Decimal
        Public ReadOnly Property Movimientos As New List(Of MayorMov)
        Public Property TotalDebe As Decimal
        Public Property TotalHaber As Decimal
        Public Property SaldoFinal As Decimal
    End Class

    Public Class DiarioRow
        Public Property Fecha As Date
        Public Property ComprobanteId As Integer
        Public Property Comprobante As String
        Public Property GlosaComprobante As String
        Public Property CuentaCodigo As String
        Public Property CuentaNombre As String
        Public Property Glosa As String
        Public Property Debe As Decimal
        Public Property Haber As Decimal
    End Class

    ''' <summary>Línea de un estado financiero (T = título, D = detalle, S = subtotal, R = resultado).</summary>
    Public Class FsLine
        Public Property Tipo As String = "D"
        Public Property Codigo As String = ""
        Public Property Texto As String = ""
        Public Property Nivel As Integer
        Public Property Importe As Decimal
        Public Property ConImporte As Boolean = True
    End Class

    Public Class EstadoFinanciero
        Public ReadOnly Property Lineas As New List(Of FsLine)
        Public Property Cuadra As Boolean = True
        Public Property Diferencia As Decimal
        Public Property Total1 As Decimal
        Public Property Total2 As Decimal
    End Class

    ''' <summary>Libro diario, libro mayor, balance de sumas y saldos y estados financieros.</summary>
    Public Class LedgerService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private Shared Function ColDebe(usd As Boolean) As String
            Return If(usd, "DebeUsd", "DebeBs")
        End Function

        Private Shared Function ColHaber(usd As Boolean) As String
            Return If(usd, "HaberUsd", "HaberBs")
        End Function

        Private Function Sumas(whereFecha As String, usd As Boolean, ParamArray args() As Object) As Dictionary(Of Integer, Tuple(Of Decimal, Decimal))
            Dim dt As DataTable = _ctx.Db.Query("SELECT CuentaId, SUM(" & ColDebe(usd) & ") AS D, SUM(" & ColHaber(usd) & ") AS H FROM ComprobanteDet WHERE Vigente=1 AND " & whereFecha & " GROUP BY CuentaId", args)
            Dim d As New Dictionary(Of Integer, Tuple(Of Decimal, Decimal))
            For Each r As DataRow In dt.Rows
                d(r.GetI("CuentaId")) = Tuple.Create(r.GetD("D"), r.GetD("H"))
            Next
            Return d
        End Function

        ''' <summary>Balance de sumas y saldos por todas las cuentas con acumulación jerárquica.</summary>
        Public Function Balance(desde As Date, hasta As Date, Optional usd As Boolean = False, Optional nivelMax As Integer = 99, Optional soloConMovimiento As Boolean = True) As List(Of BalanceRow)
            Dim ant = Sumas("Fecha < @d", usd, "d", desde.Date)
            Dim mov = Sumas("Fecha >= @d AND Fecha <= @h", usd, "d", desde.Date, "h", hasta.Date)
            Dim filas As New Dictionary(Of Integer, BalanceRow)
            Dim orden As New List(Of BalanceRow)
            For Each c As DataRow In _ctx.Cuentas().Rows
                Dim b As New BalanceRow With {
                    .CuentaId = c.GetI("Id"), .Codigo = c.GetS("Codigo"), .Nombre = c.GetS("Nombre"), .Nivel = c.GetI("Nivel"),
                    .Rubro = c.GetI("Rubro"), .Naturaleza = c.GetS("Naturaleza"), .EsMovimiento = c.GetF("EsMovimiento")}
                filas(b.CuentaId) = b
                orden.Add(b)
            Next
            ' acumulación: cada cuenta con datos suma a sí misma y a todos sus ancestros
            Dim netoAnt As New Dictionary(Of Integer, Decimal)
            Dim sumD As New Dictionary(Of Integer, Decimal)
            Dim sumH As New Dictionary(Of Integer, Decimal)
            Dim ids As New HashSet(Of Integer)(ant.Keys)
            ids.UnionWith(mov.Keys)
            For Each id As Integer In ids
                Dim a As Decimal = 0D, d As Decimal = 0D, h As Decimal = 0D
                If ant.ContainsKey(id) Then a = ant(id).Item1 - ant(id).Item2
                If mov.ContainsKey(id) Then
                    d = mov(id).Item1
                    h = mov(id).Item2
                End If
                Dim cur As Integer = id
                Dim guard As Integer = 0
                While cur <> 0 AndAlso guard < 20
                    netoAnt(cur) = (If(netoAnt.ContainsKey(cur), netoAnt(cur), 0D)) + a
                    sumD(cur) = (If(sumD.ContainsKey(cur), sumD(cur), 0D)) + d
                    sumH(cur) = (If(sumH.ContainsKey(cur), sumH(cur), 0D)) + h
                    Dim r As DataRow = _ctx.CuentaPorId(cur)
                    cur = If(r Is Nothing, 0, r.GetI("PadreId"))
                    guard += 1
                End While
            Next
            Dim res As New List(Of BalanceRow)
            For Each b As BalanceRow In orden
                Dim na As Decimal = If(netoAnt.ContainsKey(b.CuentaId), netoAnt(b.CuentaId), 0D)
                b.AntD = If(na > 0D, na, 0D)
                b.AntH = If(na < 0D, -na, 0D)
                b.Debe = If(sumD.ContainsKey(b.CuentaId), sumD(b.CuentaId), 0D)
                b.Haber = If(sumH.ContainsKey(b.CuentaId), sumH(b.CuentaId), 0D)
                Dim fin As Decimal = na + b.Debe - b.Haber
                b.SaldoD = If(fin > 0D, fin, 0D)
                b.SaldoH = If(fin < 0D, -fin, 0D)
                If b.Nivel > nivelMax Then Continue For
                If soloConMovimiento AndAlso b.AntD = 0D AndAlso b.AntH = 0D AndAlso b.Debe = 0D AndAlso b.Haber = 0D Then Continue For
                res.Add(b)
            Next
            Return res
        End Function

        ''' <summary>Cuentas de movimiento que cuelgan de un código (o la misma cuenta si es de movimiento).</summary>
        Public Function HojasDe(cuentaId As Integer) As List(Of Integer)
            Dim c As DataRow = _ctx.CuentaPorId(cuentaId)
            Dim res As New List(Of Integer)
            If c Is Nothing Then Return res
            Dim cod As String = c.GetS("Codigo")
            For Each r As DataRow In _ctx.Cuentas().Rows
                If r.GetF("EsMovimiento") AndAlso (r.GetI("Id") = cuentaId OrElse EmpresaService.EsDescendiente(r.GetS("Codigo"), cod)) Then res.Add(r.GetI("Id"))
            Next
            Return res
        End Function

        Public Function Mayor(cuentaId As Integer, desde As Date, hasta As Date, Optional usd As Boolean = False) As MayorResult
            Dim c As DataRow = _ctx.CuentaPorId(cuentaId)
            If c Is Nothing Then Throw New InvalidOperationException("Cuenta inexistente.")
            Dim res As New MayorResult With {.CuentaId = cuentaId, .Codigo = c.GetS("Codigo"), .Nombre = c.GetS("Nombre"), .Naturaleza = c.GetS("Naturaleza")}
            Dim hojas As List(Of Integer) = HojasDe(cuentaId)
            If hojas.Count = 0 Then Return res
            Dim inList As String = String.Join(",", hojas)
            Dim signo As Decimal = If(res.Naturaleza = "D", 1D, -1D)
            Dim sa As DataTable = _ctx.Db.Query("SELECT SUM(" & ColDebe(usd) & ") AS D, SUM(" & ColHaber(usd) & ") AS H FROM ComprobanteDet WHERE Vigente=1 AND Fecha < @d AND CuentaId IN (" & inList & ")", "d", desde.Date)
            If sa.Rows.Count > 0 Then res.SaldoAnterior = (sa.Rows(0).GetD("D") - sa.Rows(0).GetD("H")) * signo
            Dim dt As DataTable = _ctx.Db.Query("SELECT ComprobanteId, Linea, CuentaId, Fecha, Glosa, " & ColDebe(usd) & " AS D, " & ColHaber(usd) & " AS H FROM ComprobanteDet WHERE Vigente=1 AND Fecha >= @d AND Fecha <= @h AND CuentaId IN (" & inList & ") ORDER BY Fecha, ComprobanteId, Linea", "d", desde.Date, "h", hasta.Date)
            Dim etiquetas As Dictionary(Of Integer, Tuple(Of String, String)) = EtiquetasComprobantes(desde, hasta)
            Dim saldo As Decimal = res.SaldoAnterior
            For Each r As DataRow In dt.Rows
                Dim d As Decimal = r.GetD("D"), h As Decimal = r.GetD("H")
                saldo += (d - h) * signo
                Dim et As Tuple(Of String, String) = Nothing
                etiquetas.TryGetValue(r.GetI("ComprobanteId"), et)
                Dim g As String = r.GetS("Glosa")
                If g = "" AndAlso et IsNot Nothing Then g = et.Item2
                res.Movimientos.Add(New MayorMov With {.Fecha = r.GetDt("Fecha"), .ComprobanteId = r.GetI("ComprobanteId"), .Comprobante = If(et Is Nothing, "", et.Item1),
                    .CuentaCodigo = _ctx.CodigoCuenta(r.GetI("CuentaId")), .Glosa = g, .Debe = d, .Haber = h, .Saldo = saldo})
                res.TotalDebe += d
                res.TotalHaber += h
            Next
            res.SaldoFinal = saldo
            Return res
        End Function

        Private Function EtiquetasComprobantes(desde As Date, hasta As Date) As Dictionary(Of Integer, Tuple(Of String, String))
            Dim d As New Dictionary(Of Integer, Tuple(Of String, String))
            Dim dt As DataTable = _ctx.Db.Query("SELECT c.Id, t.Codigo, c.Numero, c.Mes, c.Glosa FROM Comprobante c INNER JOIN TipoComprobante t ON t.Id = c.TipoId WHERE c.Fecha >= @d AND c.Fecha <= @h", "d", desde.Date, "h", hasta.Date)
            For Each r As DataRow In dt.Rows
                d(r.GetI("Id")) = Tuple.Create(r.GetS("Codigo") & "-" & r.GetI("Numero").ToString() & If(r.GetI("Mes") > 0, "/" & r.GetI("Mes").ToString("00"), ""), r.GetS("Glosa"))
            Next
            Return d
        End Function

        Public Function Diario(desde As Date, hasta As Date, Optional usd As Boolean = False, Optional tipoCodigo As String = "") As List(Of DiarioRow)
            Dim sql As String = "SELECT d.ComprobanteId, d.Linea, d.CuentaId, d.Fecha, d.Glosa, d." & ColDebe(usd) & " AS D, d." & ColHaber(usd) & " AS H, c.Glosa AS GlosaC, t.Codigo AS Tipo, c.Numero, c.Mes " &
                                "FROM (ComprobanteDet d INNER JOIN Comprobante c ON c.Id = d.ComprobanteId) INNER JOIN TipoComprobante t ON t.Id = c.TipoId " &
                                "WHERE d.Vigente=1 AND d.Fecha >= @d AND d.Fecha <= @h"
            Dim args As New List(Of Object) From {"d", desde.Date, "h", hasta.Date}
            If tipoCodigo <> "" Then
                sql &= " AND t.Codigo=@t"
                args.AddRange({"t", tipoCodigo})
            End If
            sql &= " ORDER BY d.Fecha, t.Codigo, c.Numero, d.Linea"
            Dim res As New List(Of DiarioRow)
            For Each r As DataRow In _ctx.Db.Query(sql, args.ToArray()).Rows
                res.Add(New DiarioRow With {
                    .Fecha = r.GetDt("Fecha"), .ComprobanteId = r.GetI("ComprobanteId"),
                    .Comprobante = r.GetS("Tipo") & "-" & r.GetI("Numero").ToString() & If(r.GetI("Mes") > 0, "/" & r.GetI("Mes").ToString("00"), ""),
                    .GlosaComprobante = r.GetS("GlosaC"), .CuentaCodigo = _ctx.CodigoCuenta(r.GetI("CuentaId")), .CuentaNombre = _ctx.NombreCuenta(r.GetI("CuentaId")),
                    .Glosa = r.GetS("Glosa"), .Debe = r.GetD("D"), .Haber = r.GetD("H")})
            Next
            Return res
        End Function

        ' ---------- Estados financieros ----------
        Private Shared Function TieneAncestro(b As BalanceRow, prefijo As String) As Boolean
            Return b.Codigo = prefijo OrElse EmpresaService.EsDescendiente(b.Codigo, prefijo)
        End Function

        Private Function Natural(b As BalanceRow, rubroDeudor As Boolean) As Decimal
            Return If(rubroDeudor, b.Neto, -b.Neto)
        End Function

        Private Sub AgregarDetalle(est As EstadoFinanciero, filas As IEnumerable(Of BalanceRow), nivelMax As Integer, deudor As Boolean, Optional nivelBase As Integer = 0)
            For Each b In filas
                If b.Nivel > nivelMax Then Continue For
                est.Lineas.Add(New FsLine With {.Tipo = If(b.EsMovimiento, "D", "T"), .Codigo = b.Codigo, .Texto = b.Nombre, .Nivel = b.Nivel - nivelBase, .Importe = Natural(b, deudor)})
            Next
        End Sub

        ''' <summary>Estado de resultados. formato "I" = ingresos - egresos; "C" = comercial (utilidad bruta / operativa).</summary>
        Public Function EstadoResultados(desde As Date, hasta As Date, usd As Boolean, nivelMax As Integer, Optional formato As String = "C") As EstadoFinanciero
            Dim bal As List(Of BalanceRow) = Balance(desde, hasta, usd, 99, True)
            Dim est As New EstadoFinanciero()
            Dim ingresos As Decimal = 0D, egresos As Decimal = 0D
            For Each b In bal.Where(Function(x) x.Nivel = 1)
                If b.Rubro = 4 Then ingresos += -b.Neto
                If b.Rubro = 5 Then egresos += b.Neto
            Next
            If formato = "I" Then
                est.Lineas.Add(New FsLine With {.Tipo = "T", .Texto = "INGRESOS", .ConImporte = False})
                AgregarDetalle(est, bal.Where(Function(x) x.Rubro = 4), nivelMax, False)
                est.Lineas.Add(New FsLine With {.Tipo = "S", .Texto = "TOTAL INGRESOS", .Importe = ingresos})
                est.Lineas.Add(New FsLine With {.Tipo = "T", .Texto = "EGRESOS (COSTOS Y GASTOS)", .ConImporte = False})
                AgregarDetalle(est, bal.Where(Function(x) x.Rubro = 5), nivelMax, True)
                est.Lineas.Add(New FsLine With {.Tipo = "S", .Texto = "TOTAL EGRESOS", .Importe = egresos})
            Else
                Dim seccion = Sub(titulo As String, prefijos As String(), deudor As Boolean, ByRef total As Decimal)
                                  Dim filas = bal.Where(Function(x) prefijos.Any(Function(p) TieneAncestro(x, p)) AndAlso x.Nivel > 2).ToList()
                                  Dim cabeceras = bal.Where(Function(x) prefijos.Contains(x.Codigo)).ToList()
                                  Dim tot As Decimal = 0D
                                  For Each cb In cabeceras
                                      tot += Natural(cb, deudor)
                                  Next
                                  est.Lineas.Add(New FsLine With {.Tipo = "T", .Texto = titulo, .ConImporte = False})
                                  AgregarDetalle(est, filas, nivelMax, deudor, 2)
                                  est.Lineas.Add(New FsLine With {.Tipo = "S", .Texto = "TOTAL " & titulo, .Importe = tot})
                                  total = tot
                              End Sub
                Dim ventas As Decimal = 0D, costo As Decimal = 0D, produccion As Decimal = 0D, admin As Decimal = 0D, comerc As Decimal = 0D, financ As Decimal = 0D, otrosG As Decimal = 0D, otrosI As Decimal = 0D
                seccion("INGRESOS OPERATIVOS", {"4.1"}, False, ventas)
                seccion("COSTO DE VENTAS", {"5.1", "5.2"}, True, costo)
                est.Lineas.Add(New FsLine With {.Tipo = "R", .Texto = "UTILIDAD BRUTA", .Importe = ventas - costo})
                seccion("GASTOS DE ADMINISTRACIÓN", {"5.3"}, True, admin)
                seccion("GASTOS DE COMERCIALIZACIÓN", {"5.4"}, True, comerc)
                est.Lineas.Add(New FsLine With {.Tipo = "R", .Texto = "UTILIDAD OPERATIVA", .Importe = ventas - costo - admin - comerc})
                seccion("OTROS INGRESOS", {"4.2"}, False, otrosI)
                seccion("GASTOS FINANCIEROS", {"5.5"}, True, financ)
                seccion("OTROS GASTOS", {"5.6"}, True, otrosG)
                ' cuentas de resultado fuera de los grupos estándar (planes personalizados)
                Dim conocidos As String() = {"4.1", "4.2", "5.1", "5.2", "5.3", "5.4", "5.5", "5.6"}
                For Each b In bal.Where(Function(x) x.Nivel = 2 AndAlso (x.Rubro = 4 OrElse x.Rubro = 5) AndAlso Not conocidos.Contains(x.Codigo))
                    est.Lineas.Add(New FsLine With {.Tipo = "D", .Codigo = b.Codigo, .Texto = b.Nombre & " (otros)", .Nivel = 1, .Importe = If(b.Rubro = 4, -b.Neto, b.Neto)})
                Next
            End If
            est.Lineas.Add(New FsLine With {.Tipo = "R", .Texto = If(ingresos - egresos >= 0D, "UTILIDAD NETA DEL PERÍODO", "PÉRDIDA NETA DEL PERÍODO"), .Importe = ingresos - egresos})
            est.Total1 = ingresos
            est.Total2 = egresos
            Return est
        End Function

        ''' <summary>Balance general acumulado desde el inicio de la gestión hasta la fecha, con el resultado aún no cerrado en patrimonio.</summary>
        Public Function BalanceGeneral(hasta As Date, usd As Boolean, nivelMax As Integer) As EstadoFinanciero
            Dim bal As List(Of BalanceRow) = Balance(_ctx.Gestion.FechaInicio, hasta, usd, 99, True)
            Dim est As New EstadoFinanciero()
            Dim activo As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 1).Sum(Function(x) x.Neto)
            Dim pasivo As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 2).Sum(Function(x) -x.Neto)
            Dim patri As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 3).Sum(Function(x) -x.Neto)
            Dim resultado As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 4).Sum(Function(x) -x.Neto) - bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 5).Sum(Function(x) x.Neto)
            est.Lineas.Add(New FsLine With {.Tipo = "T", .Texto = "ACTIVO", .ConImporte = False})
            AgregarDetalle(est, bal.Where(Function(x) x.Rubro = 1), nivelMax, True)
            est.Lineas.Add(New FsLine With {.Tipo = "S", .Texto = "TOTAL ACTIVO", .Importe = activo})
            est.Lineas.Add(New FsLine With {.Tipo = "T", .Texto = "PASIVO", .ConImporte = False})
            AgregarDetalle(est, bal.Where(Function(x) x.Rubro = 2), nivelMax, False)
            est.Lineas.Add(New FsLine With {.Tipo = "S", .Texto = "TOTAL PASIVO", .Importe = pasivo})
            est.Lineas.Add(New FsLine With {.Tipo = "T", .Texto = "PATRIMONIO", .ConImporte = False})
            AgregarDetalle(est, bal.Where(Function(x) x.Rubro = 3), nivelMax, False)
            If resultado <> 0D Then
                est.Lineas.Add(New FsLine With {.Tipo = "D", .Texto = "Resultado del período (aún no cerrado)", .Nivel = 2, .Importe = resultado})
            End If
            est.Lineas.Add(New FsLine With {.Tipo = "S", .Texto = "TOTAL PATRIMONIO", .Importe = patri + resultado})
            est.Lineas.Add(New FsLine With {.Tipo = "R", .Texto = "TOTAL PASIVO Y PATRIMONIO", .Importe = pasivo + patri + resultado})
            est.Total1 = activo
            est.Total2 = pasivo + patri + resultado
            est.Diferencia = (est.Total1 - est.Total2).R2()
            est.Cuadra = est.Diferencia = 0D
            Return est
        End Function

        ''' <summary>Resultado acumulado (ingresos - egresos) a una fecha.</summary>
        Public Function ResultadoAl(hasta As Date) As Decimal
            Dim bal = Balance(_ctx.Gestion.FechaInicio, hasta, False, 1, True)
            Return bal.Where(Function(x) x.Rubro = 4).Sum(Function(x) -x.Neto) - bal.Where(Function(x) x.Rubro = 5).Sum(Function(x) x.Neto)
        End Function

        ''' <summary>Saldo natural de una cuenta (incluye subcuentas) a una fecha.</summary>
        Public Function SaldoCuenta(cuentaId As Integer, hasta As Date, Optional usd As Boolean = False) As Decimal
            Dim m As MayorResult = Mayor(cuentaId, _ctx.Gestion.FechaInicio, hasta, usd)
            Return m.SaldoFinal
        End Function

    End Class

End Namespace
