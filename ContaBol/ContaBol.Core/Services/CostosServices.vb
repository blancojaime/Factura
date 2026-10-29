Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    ''' <summary>Órdenes de producción: materia prima, mano de obra directa y costos indirectos hasta producto terminado.</summary>
    Public Class ProduccionService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        Public Function Listar(Optional estado As String = "") As DataTable
            Return Db.Query("SELECT o.*, i.Codigo AS ItemCodigo, i.Descripcion AS Producto FROM OrdenProd o INNER JOIN Item i ON i.Id = o.ItemId" & If(estado <> "", " WHERE o.Estado='" & estado.Replace("'", "") & "'", "") & " ORDER BY o.Numero DESC")
        End Function

        Public Function Obtener(id As Integer) As DataRow
            Dim dt As DataTable = Db.Query("SELECT o.*, i.Codigo AS ItemCodigo, i.Descripcion AS Producto FROM OrdenProd o INNER JOIN Item i ON i.Id = o.ItemId WHERE o.Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Return dt.Rows(0)
        End Function

        Public Function Abrir(fecha As Date, itemId As Integer, cantidad As Decimal, almacenMpId As Integer, almacenPtId As Integer, detalle As String) As Integer
            _ctx.Requiere("COS.PRODUCCION")
            _ctx.RequiereGestionAbierta()
            If cantidad <= 0D Then Throw New ArgumentException("La cantidad a producir debe ser mayor a cero.")
            If almacenMpId = 0 OrElse almacenPtId = 0 Then Throw New ArgumentException("Seleccione los almacenes de materia prima y de productos terminados.")
            Dim it As ItemDto = New InventarioService(_ctx).ObtenerItem(itemId)
            If it Is Nothing OrElse it.EsServicio Then Throw New ArgumentException("Seleccione el producto a fabricar (ítem de inventario).")
            Dim num As Integer = _ctx.Siguiente("ORDEN_PROD")
            Dim id As Integer = Db.Insert("INSERT INTO OrdenProd (Numero, Fecha, ItemId, Cantidad, Estado, AlmacenMpId, AlmacenPtId, Detalle, CostoMp, CostoMod, CostoCif, CostoTotal, CostoUnit, ComprobanteId) VALUES (@n, @f, @i, @c, 'A', @am, @ap, @d, 0, 0, 0, 0, 0, 0)",
                                          "n", num, "f", fecha.Date, "i", itemId, "c", CDbl(cantidad), "am", almacenMpId, "ap", almacenPtId, "d", detalle)
            _ctx.Audit("Producción", "ORDEN_NUEVA", "Orden " & num & " " & it.Descripcion)
            Return id
        End Function

        Private Function Abierta(ordenId As Integer) As DataRow
            Dim o As DataRow = Obtener(ordenId)
            If o Is Nothing Then Throw New InvalidOperationException("Orden inexistente.")
            If o.GetS("Estado") <> "A" Then Throw New InvalidOperationException("La orden ya está cerrada.")
            Return o
        End Function

        ''' <summary>Consume materia prima del almacén: sale de inventario al costo promedio y se acumula en la orden.</summary>
        Public Function ConsumirMateriaPrima(ordenId As Integer, fecha As Date, lineas As IEnumerable(Of MovLine)) As Decimal
            _ctx.Requiere("COS.PRODUCCION")
            _ctx.RequiereGestionAbierta()
            Dim o As DataRow = Abierta(ordenId)
            Return Db.InTx(Function()
                               Dim inv As New InventarioService(_ctx)
                               Dim m As New MovInvDto With {.Tipo = "PRMP", .Fecha = fecha, .AlmacenId = o.GetI("AlmacenMpId"), .TC = 1D, .Detalle = "Materia prima orden " & o.GetS("Numero"), .DocTipo = "ORDEN", .DocId = ordenId}
                               m.Lines.AddRange(lineas)
                               Dim r As MovResult = inv.Aplicar(m)
                               Db.Execute("UPDATE OrdenProd SET CostoMp = CostoMp + @c WHERE Id=@i", "c", r.TotalBs, "i", ordenId)
                               _ctx.Audit("Producción", "ORDEN_MP", "Orden " & o.GetS("Numero") & " Bs " & r.TotalBs.ToString("N2"))
                               Return r.TotalBs
                           End Function)
        End Function

        Public Function AgregarManoObra(ordenId As Integer, empleadoId As Integer, horas As Decimal, Optional costoHora As Decimal = 0D) As Decimal
            _ctx.Requiere("COS.PRODUCCION")
            Abierta(ordenId)
            If horas <= 0D Then Throw New ArgumentException("Las horas deben ser mayores a cero.")
            Dim emp As EmpleadoDto = New PlanillaService(_ctx).ObtenerEmpleado(empleadoId)
            If emp Is Nothing Then Throw New ArgumentException("Seleccione el empleado.")
            If costoHora <= 0D Then costoHora = (emp.Haber / 30D / 8D).R2()
            Dim monto As Decimal = (horas * costoHora).R2()
            Db.InTx(Sub()
                        Db.Execute("INSERT INTO OrdenProdMod (OrdenId, EmpleadoId, Horas, CostoHora, Monto) VALUES (@o, @e, @h, @c, @m)", "o", ordenId, "e", empleadoId, "h", CDbl(horas), "c", costoHora, "m", monto)
                        Db.Execute("UPDATE OrdenProd SET CostoMod = CostoMod + @m WHERE Id=@i", "m", monto, "i", ordenId)
                    End Sub)
            Return monto
        End Function

        Public Sub AgregarCif(ordenId As Integer, detalle As String, monto As Decimal)
            _ctx.Requiere("COS.PRODUCCION")
            Abierta(ordenId)
            If monto <= 0D Then Throw New ArgumentException("El monto debe ser mayor a cero.")
            If If(detalle, "").Trim() = "" Then Throw New ArgumentException("Ingrese el detalle del gasto.")
            Db.InTx(Sub()
                        Db.Execute("INSERT INTO OrdenProdCif (OrdenId, Detalle, Monto) VALUES (@o, @d, @m)", "o", ordenId, "d", detalle, "m", monto)
                        Db.Execute("UPDATE OrdenProd SET CostoCif = CostoCif + @m WHERE Id=@i", "m", monto, "i", ordenId)
                    End Sub)
        End Sub

        Public Sub QuitarManoObra(id As Integer)
            _ctx.Requiere("COS.PRODUCCION")
            Dim r As DataTable = Db.Query("SELECT OrdenId, Monto FROM OrdenProdMod WHERE Id=@i", "i", id)
            If r.Rows.Count = 0 Then Return
            Abierta(r.Rows(0).GetI("OrdenId"))
            Db.InTx(Sub()
                        Db.Execute("UPDATE OrdenProd SET CostoMod = CostoMod - @m WHERE Id=@o", "m", r.Rows(0).GetD("Monto"), "o", r.Rows(0).GetI("OrdenId"))
                        Db.Execute("DELETE FROM OrdenProdMod WHERE Id=@i", "i", id)
                    End Sub)
        End Sub

        Public Sub QuitarCif(id As Integer)
            _ctx.Requiere("COS.PRODUCCION")
            Dim r As DataTable = Db.Query("SELECT OrdenId, Monto FROM OrdenProdCif WHERE Id=@i", "i", id)
            If r.Rows.Count = 0 Then Return
            Abierta(r.Rows(0).GetI("OrdenId"))
            Db.InTx(Sub()
                        Db.Execute("UPDATE OrdenProd SET CostoCif = CostoCif - @m WHERE Id=@o", "m", r.Rows(0).GetD("Monto"), "o", r.Rows(0).GetI("OrdenId"))
                        Db.Execute("DELETE FROM OrdenProdCif WHERE Id=@i", "i", id)
                    End Sub)
        End Sub

        Public Function DetalleMp(ordenId As Integer) As DataTable
            Return Db.Query("SELECT d.Fecha, i.Codigo, i.Descripcion, d.Cantidad, d.CostoUnitBs, d.ImporteBs FROM (MovInvDet d INNER JOIN MovInv m ON m.Id = d.MovId) INNER JOIN Item i ON i.Id = d.ItemId WHERE m.DocTipo='ORDEN' AND m.DocId=@o AND m.Tipo='PRMP' AND d.Vigente=1 ORDER BY d.Fecha, d.Id", "o", ordenId)
        End Function

        Public Function DetalleMod(ordenId As Integer) As DataTable
            Return Db.Query("SELECT m.Id, e.Nombre, m.Horas, m.CostoHora, m.Monto FROM OrdenProdMod m INNER JOIN Empleado e ON e.Id = m.EmpleadoId WHERE m.OrdenId=@o ORDER BY m.Id", "o", ordenId)
        End Function

        Public Function DetalleCif(ordenId As Integer) As DataTable
            Return Db.Query("SELECT Id, Detalle, Monto FROM OrdenProdCif WHERE OrdenId=@o ORDER BY Id", "o", ordenId)
        End Function

        ''' <summary>Cierra la orden: ingresa el producto terminado al almacén con su costo y capitaliza MP, MOD y CIF.</summary>
        Public Function Cerrar(ordenId As Integer, fecha As Date, cantidadTerminada As Decimal) As Integer
            _ctx.Requiere("COS.PRODUCCION")
            _ctx.RequiereGestionAbierta()
            Dim o As DataRow = Abierta(ordenId)
            If cantidadTerminada <= 0D Then Throw New ArgumentException("Ingrese la cantidad terminada.")
            Dim mp As Decimal = o.GetD("CostoMp"), md As Decimal = o.GetD("CostoMod"), cif As Decimal = o.GetD("CostoCif")
            Dim total As Decimal = mp + md + cif
            If total <= 0D Then Throw New InvalidOperationException("La orden no tiene costos registrados.")
            Return Db.InTx(Function()
                               Dim inv As New InventarioService(_ctx)
                               Dim unit As Decimal = Math.Round(total / cantidadTerminada, 6)
                               Dim m As New MovInvDto With {.Tipo = "PRPT", .Fecha = fecha, .AlmacenId = o.GetI("AlmacenPtId"), .TC = 1D, .Detalle = "Producto terminado orden " & o.GetS("Numero"), .DocTipo = "ORDEN", .DocId = ordenId}
                               m.Lines.Add(New MovLine With {.ItemId = o.GetI("ItemId"), .Cantidad = cantidadTerminada, .PrecioUnit = unit})
                               inv.Aplicar(m)
                               Dim vs As New VoucherService(_ctx)
                               Dim v As Voucher = vs.Nuevo("T", fecha)
                               v.Glosa = "Cierre orden de producción Nº " & o.GetS("Numero") & " - " & o.GetS("Producto")
                               v.Origen = "PRO" : v.OrigenId = ordenId
                               Dim itemPt As ItemDto = inv.ObtenerItem(o.GetI("ItemId"))
                               Dim ctaPt As Integer = If(itemPt.CuentaInvId <> 0, itemPt.CuentaInvId, _ctx.CuentaParam(ParamKeys.CtaProdTerminados))
                               v.Lines.Add(VoucherLine.Deb(ctaPt, total, v.Glosa))
                               ' Materia prima: se acredita la cuenta de inventario de cada ítem consumido
                               Dim porCuenta As New Dictionary(Of Integer, Decimal)
                               For Each r As DataRow In DetalleMp(ordenId).Rows
                                   Dim it As DataRow = Db.Query("SELECT i.Id FROM Item i WHERE i.Codigo=@c", "c", r.GetS("Codigo")).Rows(0)
                                   Dim cta As Integer = inv.CuentaInventario(it.GetI("Id"))
                                   porCuenta(cta) = (If(porCuenta.ContainsKey(cta), porCuenta(cta), 0D)) + r.GetD("ImporteBs")
                               Next
                               Dim sumMp As Decimal = porCuenta.Values.Sum()
                               If mp - sumMp <> 0D AndAlso porCuenta.Count > 0 Then porCuenta(porCuenta.Keys.First()) += mp - sumMp
                               For Each kv In porCuenta
                                   If kv.Value > 0D Then v.Lines.Add(VoucherLine.Hab(kv.Key, kv.Value, v.Glosa))
                               Next
                               If md > 0D Then v.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaMano), md, v.Glosa))
                               If cif > 0D Then v.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaCif), cif, v.Glosa))
                               Dim vid As Integer = vs.Registrar(v)
                               Db.Execute("UPDATE OrdenProd SET Estado='T', FechaCierre=@f, ComprobanteId=@c, CostoTotal=@t, CostoUnit=@u, Cantidad=@q WHERE Id=@i", "f", fecha.Date, "c", vid, "t", total, "u", CDbl(unit), "q", CDbl(cantidadTerminada), "i", ordenId)
                               _ctx.Audit("Producción", "ORDEN_CERRADA", "Orden " & o.GetS("Numero") & " costo Bs " & total.ToString("N2"))
                               Return vid
                           End Function)
        End Function

        Public Sub Eliminar(ordenId As Integer)
            _ctx.Requiere("COS.PRODUCCION")
            Abierta(ordenId)
            If Db.ScalarInt("SELECT COUNT(*) FROM MovInv WHERE DocTipo='ORDEN' AND DocId=@o AND Estado='V'", "o", ordenId) > 0 Then Throw New InvalidOperationException("La orden tiene consumos de materia prima. Anúlelos primero.")
            Db.InTx(Sub()
                        Db.Execute("DELETE FROM OrdenProdMod WHERE OrdenId=@o", "o", ordenId)
                        Db.Execute("DELETE FROM OrdenProdCif WHERE OrdenId=@o", "o", ordenId)
                        Db.Execute("DELETE FROM OrdenProd WHERE Id=@o", "o", ordenId)
                    End Sub)
        End Sub
    End Class

    ''' <summary>Centros de costo / departamentos y distribución del gasto.</summary>
    Public Class CentroCostoService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        ''' <summary>Gastos (rubro 5) acumulados por centro de costo y cuenta en un período.</summary>
        Public Function GastosPorCentro(desde As Date, hasta As Date) As DataTable
            Dim res As New DataTable()
            res.Columns.Add("Centro", GetType(String))
            res.Columns.Add("Cuenta", GetType(String))
            res.Columns.Add("Nombre", GetType(String))
            res.Columns.Add("Tipo", GetType(String))
            res.Columns.Add("Importe", GetType(Decimal))
            Dim centros As New Dictionary(Of Integer, String)
            For Each c As DataRow In _ctx.Db.Query("SELECT Id, Codigo, Nombre FROM CentroCosto").Rows
                centros(c.GetI("Id")) = c.GetS("Codigo") & " " & c.GetS("Nombre")
            Next
            Dim dt As DataTable = _ctx.Db.Query("SELECT CentroCostoId, CuentaId, SUM(DebeBs) AS D, SUM(HaberBs) AS H FROM ComprobanteDet WHERE Vigente=1 AND Fecha >= @d AND Fecha <= @h GROUP BY CentroCostoId, CuentaId", "d", desde.Date, "h", hasta.Date)
            For Each r As DataRow In dt.Rows
                Dim c As DataRow = _ctx.CuentaPorId(r.GetI("CuentaId"))
                If c Is Nothing OrElse c.GetI("Rubro") <> 5 Then Continue For
                Dim imp As Decimal = r.GetD("D") - r.GetD("H")
                If imp = 0D Then Continue For
                Dim cid As Integer = r.GetI("CentroCostoId")
                res.Rows.Add(If(cid <> 0 AndAlso centros.ContainsKey(cid), centros(cid), "(Sin centro de costo)"), c.GetS("Codigo"), c.GetS("Nombre"), c.GetS("CostoTipo"), imp)
            Next
            Dim v As DataView = res.DefaultView
            v.Sort = "Centro, Cuenta"
            Return v.ToTable()
        End Function
    End Class

    ''' <summary>Presupuesto mensual por cuenta y su ejecución.</summary>
    Public Class PresupuestoService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Public Function Obtener(cuentaId As Integer) As Decimal()
            Dim m(11) As Decimal
            For Each r As DataRow In _ctx.Db.Query("SELECT Mes, MontoBs FROM Presupuesto WHERE CuentaId=@c", "c", cuentaId).Rows
                Dim i As Integer = r.GetI("Mes")
                If i >= 1 AndAlso i <= 12 Then m(i - 1) = r.GetD("MontoBs")
            Next
            Return m
        End Function

        Public Sub Guardar(cuentaId As Integer, meses As Decimal())
            _ctx.Requiere("CONT.PRESUPUESTO")
            _ctx.RequiereGestionAbierta()
            If meses Is Nothing OrElse meses.Length <> 12 Then Throw New ArgumentException("Se requieren 12 montos mensuales.")
            _ctx.Db.InTx(Sub()
                             _ctx.Db.Execute("DELETE FROM Presupuesto WHERE CuentaId=@c", "c", cuentaId)
                             For i As Integer = 0 To 11
                                 If meses(i) <> 0D Then _ctx.Db.Execute("INSERT INTO Presupuesto (CuentaId, Mes, MontoBs) VALUES (@c, @m, @v)", "c", cuentaId, "m", i + 1, "v", meses(i))
                             Next
                         End Sub)
            _ctx.Audit("Presupuesto", "PRESUPUESTO_GUARDADO", _ctx.CodigoCuenta(cuentaId))
        End Sub

        ''' <summary>Presupuesto vs ejecución acumulado hasta un mes (1-12 calendario de la gestión).</summary>
        Public Function Ejecucion(hastaMes As Integer) As DataTable
            Dim res As New DataTable()
            res.Columns.Add("Codigo", GetType(String))
            res.Columns.Add("Nombre", GetType(String))
            res.Columns.Add("Presupuesto", GetType(Decimal))
            res.Columns.Add("Ejecutado", GetType(Decimal))
            res.Columns.Add("Saldo", GetType(Decimal))
            res.Columns.Add("Porcentaje", GetType(Decimal))
            Dim fin As Date = New FacturaService(_ctx).RangoMes(hastaMes).Item2
            For Each c As DataRow In _ctx.Cuentas().Rows
                If Not c.GetF("Presupuestable") OrElse Not c.GetF("EsMovimiento") Then Continue For
                Dim presu As Decimal = 0D
                For Each r As DataRow In _ctx.Db.Query("SELECT Mes, MontoBs FROM Presupuesto WHERE CuentaId=@c", "c", c.GetI("Id")).Rows
                    ' meses presupuestarios corresponden al orden dentro de la gestión: 1 = primer mes
                    If r.GetI("Mes") <= IndiceMes(fin) Then presu += r.GetD("MontoBs")
                Next
                Dim dt As DataTable = _ctx.Db.Query("SELECT SUM(DebeBs) AS D, SUM(HaberBs) AS H FROM ComprobanteDet WHERE CuentaId=@c AND Vigente=1 AND Fecha <= @h", "c", c.GetI("Id"), "h", fin)
                Dim ej As Decimal = dt.Rows(0).GetD("D") - dt.Rows(0).GetD("H")
                If c.GetS("Naturaleza") = "A" Then ej = -ej
                res.Rows.Add(c.GetS("Codigo"), c.GetS("Nombre"), presu, ej, presu - ej, If(presu <> 0D, Math.Round(ej / presu * 100D, 1), 0D))
            Next
            Return res
        End Function

        Private Function IndiceMes(fin As Date) As Integer
            Dim ini As Date = _ctx.Gestion.FechaInicio
            Return (fin.Year - ini.Year) * 12 + fin.Month - ini.Month + 1
        End Function
    End Class

    Public Class PartidaConciliacion
        Public Property DetId As Integer
        Public Property Fecha As Date
        Public Property Comprobante As String
        Public Property Cheque As String
        Public Property Glosa As String
        Public Property Debe As Decimal
        Public Property Haber As Decimal
        Public Property Conciliado As Boolean
    End Class

    ''' <summary>Libreta bancaria y conciliación de cuentas de banco.</summary>
    Public Class BancoService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Public Function CuentasBanco() As DataTable
            Return _ctx.Db.Query("SELECT * FROM Cuenta WHERE EsBanco=1 AND Activa=1 ORDER BY Codigo")
        End Function

        Public Function Partidas(cuentaId As Integer, desde As Date, hasta As Date) As List(Of PartidaConciliacion)
            Dim led As New LedgerService(_ctx)
            Dim res As New List(Of PartidaConciliacion)
            Dim dt As DataTable = _ctx.Db.Query("SELECT d.Id, d.ComprobanteId, d.Fecha, d.Glosa, d.DebeBs, d.HaberBs, d.Cheque, d.Conciliado, c.Cheque AS ChequeC, c.Numero, t.Codigo AS Tipo FROM (ComprobanteDet d INNER JOIN Comprobante c ON c.Id = d.ComprobanteId) INNER JOIN TipoComprobante t ON t.Id = c.TipoId WHERE d.CuentaId=@c AND d.Vigente=1 AND d.Fecha >= @d AND d.Fecha <= @h ORDER BY d.Fecha, d.Id", "c", cuentaId, "d", desde.Date, "h", hasta.Date)
            For Each r As DataRow In dt.Rows
                res.Add(New PartidaConciliacion With {.DetId = r.GetI("Id"), .Fecha = r.GetDt("Fecha"), .Comprobante = r.GetS("Tipo") & "-" & r.GetS("Numero"),
                    .Cheque = If(r.GetS("Cheque") <> "", r.GetS("Cheque"), r.GetS("ChequeC")), .Glosa = r.GetS("Glosa"), .Debe = r.GetD("DebeBs"), .Haber = r.GetD("HaberBs"), .Conciliado = r.GetF("Conciliado")})
            Next
            Return res
        End Function

        Public Sub Marcar(detIds As IEnumerable(Of Integer), conciliado As Boolean, fecha As Date)
            _ctx.Requiere("CONT.BANCOS")
            _ctx.Db.InTx(Sub()
                             For Each id As Integer In detIds
                                 If conciliado Then
                                     _ctx.Db.Execute("UPDATE ComprobanteDet SET Conciliado=1, FechaConcil=@f WHERE Id=@i", "f", fecha.Date, "i", id)
                                 Else
                                     _ctx.Db.Execute("UPDATE ComprobanteDet SET Conciliado=0, FechaConcil=NULL WHERE Id=@i", "i", id)
                                 End If
                             Next
                         End Sub)
        End Sub

        ''' <summary>Saldo en libros, partidas no conciliadas y saldo bancario esperado a una fecha.</summary>
        Public Function Resumen(cuentaId As Integer, hasta As Date) As Tuple(Of Decimal, Decimal, Decimal, Decimal)
            Dim libros As Decimal = New LedgerService(_ctx).SaldoCuenta(cuentaId, hasta)
            Dim dt As DataTable = _ctx.Db.Query("SELECT SUM(DebeBs) AS D, SUM(HaberBs) AS H FROM ComprobanteDet WHERE CuentaId=@c AND Vigente=1 AND Conciliado=0 AND Fecha <= @h", "c", cuentaId, "h", hasta.Date)
            Dim depTransito As Decimal = dt.Rows(0).GetD("D")     ' depósitos aún no acreditados en el banco
            Dim chequesNoCobrados As Decimal = dt.Rows(0).GetD("H")
            Dim banco As Decimal = libros - depTransito + chequesNoCobrados
            Return Tuple.Create(libros, depTransito, chequesNoCobrados, banco)
        End Function
    End Class

End Namespace
