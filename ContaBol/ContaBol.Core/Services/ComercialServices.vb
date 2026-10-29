Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class DocLine
        Public Property ItemId As Integer
        Public Property Descripcion As String = ""
        Public Property Cantidad As Decimal
        ''' <summary>Precio unitario con impuestos incluidos, en la moneda del documento.</summary>
        Public Property PrecioUnit As Decimal
        Public Property FechaVenc As Date?
    End Class

    Public Class DocumentoDto
        ''' <summary>CON = contado, CRE = crédito</summary>
        Public Property Tipo As String = "CON"
        Public Property Fecha As Date = Date.Today
        Public Property TerceroId As Integer
        Public Property AlmacenId As Integer
        Public Property VendedorId As Integer
        Public Property Moneda As String = "BS"
        Public Property TC As Decimal = 6.96D
        Public Property Detalle As String = ""
        Public ReadOnly Property Lines As New List(Of DocLine)
        Public Property Descuento As Decimal
        Public Property Recargo As Decimal
        Public Property ConFactura As Boolean
        Public Property Factura As FacturaDto
        ''' <summary>Anticipo aplicado (Bs) contra el saldo a favor del cliente/proveedor.</summary>
        Public Property Anticipo As Decimal
        ''' <summary>Pago a cuenta en una operación a crédito (Bs).</summary>
        Public Property ACuenta As Decimal
        Public Property CuentaPagoId As Integer
        Public Property Vencimiento As Date?
        Public Property ForzarCredito As Boolean
    End Class

    Public Class DocumentoResultado
        Public Property Id As Integer
        Public Property Numero As Integer
        Public Property Total As Decimal
        Public Property ImpuestoFiscal As Decimal
        Public Property Costo As Decimal
        Public Property ComprobanteId As Integer
    End Class

    ''' <summary>Cálculo común de totales de ventas y compras (todo en bolivianos).</summary>
    Friend Class TotalesDoc
        Public Subtotal As Decimal
        Public Descuento As Decimal
        Public Recargo As Decimal
        Public FacturaTotal As Decimal
        Public Total As Decimal
        Public Impuesto As Decimal
        Public Neto As Decimal
        Public LineasBs As New List(Of Decimal)

        Public Shared Function Calcular(d As DocumentoDto, ivaPct As Decimal, descEnBase As Boolean) As TotalesDoc
            Dim t As New TotalesDoc()
            Dim f As Decimal = If(d.Moneda = "USD", d.TC, 1D)
            For Each l As DocLine In d.Lines
                If l.Cantidad <= 0D Then Throw New InvalidOperationException("Todas las cantidades deben ser mayores a cero.")
                If l.PrecioUnit < 0D Then Throw New InvalidOperationException("Los precios no pueden ser negativos.")
                Dim b As Decimal = (l.Cantidad * l.PrecioUnit * f).R2()
                t.LineasBs.Add(b)
                t.Subtotal += b
            Next
            If d.Descuento < 0D OrElse d.Recargo < 0D Then Throw New InvalidOperationException("Descuento y recargo no pueden ser negativos.")
            t.Descuento = (d.Descuento * f).R2()
            t.Recargo = (d.Recargo * f).R2()
            If t.Descuento > t.Subtotal + t.Recargo Then Throw New InvalidOperationException("El descuento supera el importe de la operación.")
            If descEnBase Then
                t.FacturaTotal = t.Subtotal - t.Descuento + t.Recargo
                t.Total = t.FacturaTotal
            Else
                t.FacturaTotal = t.Subtotal
                t.Total = t.Subtotal - t.Descuento + t.Recargo
            End If
            t.Impuesto = If(d.ConFactura, (t.FacturaTotal * ivaPct / 100D).R2(), 0D)
            t.Neto = t.FacturaTotal - t.Impuesto
            Return t
        End Function

        ''' <summary>Reparte un importe entre líneas en proporción a su valor, sin perder centavos.</summary>
        Public Shared Function Repartir(total As Decimal, pesos As List(Of Decimal)) As List(Of Decimal)
            Dim res As New List(Of Decimal)
            Dim suma As Decimal = pesos.Sum()
            Dim asignado As Decimal = 0D
            For i As Integer = 0 To pesos.Count - 1
                Dim v As Decimal
                If i = pesos.Count - 1 Then
                    v = total - asignado
                ElseIf suma = 0D Then
                    v = 0D
                Else
                    v = (total * pesos(i) / suma).R2()
                End If
                asignado += v
                res.Add(v)
            Next
            Return res
        End Function
    End Class

    ''' <summary>Ventas al contado y a crédito con inventario, IVA, IT, costo de venta y cuenta corriente del cliente.</summary>
    Public Class VentaService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        Public Function AnticipoDisponible(clienteId As Integer) As Decimal
            Dim s As Decimal = New TerceroService(_ctx).Saldo(clienteId, "CXC")
            Return If(s < 0D, -s, 0D)
        End Function

        Public Function Registrar(d As DocumentoDto) As DocumentoResultado
            _ctx.Requiere("COM.VENTAS")
            _ctx.RequiereGestionAbierta()
            If d.Tipo <> "CON" AndAlso d.Tipo <> "CRE" Then Throw New ArgumentException("Tipo de venta inválido.")
            If d.Lines.Count = 0 Then Throw New InvalidOperationException("Agregue al menos un ítem a la venta.")
            If d.Fecha.Date < _ctx.Gestion.FechaInicio.Date OrElse d.Fecha.Date > _ctx.Gestion.FechaFin.Date Then Throw New InvalidOperationException("La fecha está fuera de la gestión.")
            If d.TerceroId = 0 Then Throw New InvalidOperationException("Seleccione el cliente.")
            If d.AlmacenId = 0 Then Throw New InvalidOperationException("Seleccione el almacén.")
            If d.TC <= 0D Then Throw New InvalidOperationException("Tipo de cambio inválido.")
            Dim terceros As New TerceroService(_ctx)
            Dim cli As TerceroDto = terceros.Obtener(d.TerceroId)
            If cli Is Nothing OrElse Not cli.Activo Then Throw New InvalidOperationException("El cliente no existe o está inactivo.")
            Dim inv As New InventarioService(_ctx)
            Dim fs As New FacturaService(_ctx)
            Dim t As TotalesDoc = TotalesDoc.Calcular(d, fs.IvaPct, _ctx.Param.Bool(ParamKeys.DescEnBase, True))
            Dim enBase As Boolean = _ctx.Param.Bool(ParamKeys.DescEnBase, True)
            If d.Anticipo < 0D OrElse d.ACuenta < 0D Then Throw New InvalidOperationException("Anticipo y pago a cuenta no pueden ser negativos.")
            If d.Anticipo > t.Total Then Throw New InvalidOperationException("El anticipo aplicado supera el total de la venta.")
            If d.Anticipo > AnticipoDisponible(d.TerceroId) + 0.005D Then Throw New InvalidOperationException("El cliente no tiene saldo a favor suficiente (disponible Bs " & AnticipoDisponible(d.TerceroId).ToString("N2") & ").")
            Dim cobro As Decimal, cxc As Decimal
            If d.Tipo = "CON" Then
                cobro = t.Total - d.Anticipo
                cxc = 0D
            Else
                If d.ACuenta + d.Anticipo > t.Total Then Throw New InvalidOperationException("El pago a cuenta más el anticipo superan el total.")
                cobro = d.ACuenta
                cxc = t.Total - d.Anticipo - d.ACuenta
                If cxc > 0D AndAlso cli.LimiteCredito > 0D AndAlso Not d.ForzarCredito Then
                    Dim nuevo As Decimal = terceros.Saldo(d.TerceroId, "CXC") + cxc
                    If nuevo > cli.LimiteCredito Then
                        Throw New InvalidOperationException("Se supera el límite de crédito del cliente (Bs " & cli.LimiteCredito.ToString("N2") & "). Saldo resultante: Bs " & nuevo.ToString("N2") & ".")
                    End If
                End If
            End If
            Dim cuentaCobro As Integer = d.CuentaPagoId
            If cobro > 0D AndAlso cuentaCobro = 0 Then cuentaCobro = _ctx.CuentaParam(ParamKeys.CtaCaja)
            Dim cuentaCxc As Integer = If(cli.CuentaCxcId <> 0, cli.CuentaCxcId, _ctx.CuentaParam(ParamKeys.CtaCxc))
            If d.ConFactura AndAlso d.Factura Is Nothing Then Throw New InvalidOperationException("Ingrese los datos de la factura.")

            Return Db.InTx(Function()
                               Dim res As New DocumentoResultado()
                               Dim numero As Integer = _ctx.Siguiente("VENTA_" & d.Tipo)
                               res.Numero = numero
                               Dim ventaId As Integer = Db.Insert("INSERT INTO Venta (Tipo, Numero, Fecha, ClienteId, AlmacenId, VendedorId, Moneda, TC, Detalle, SubtotalBs, DescuentoBs, RecargoBs, TotalBs, AnticipoBs, ACuentaBs, SaldoBs, CostoBs, ConFactura, NroFactura, CuentaCobroId, Estado, MovInvId, ComprobanteId, ComprobanteCostoId, ComprobanteItId, Vencimiento, UsuarioId, Creado) " &
                                   "VALUES (@t, @n, @f, @c, @a, @v, @mo, @tc, @de, @st, @dc, @rc, @to, @an, @ac, @sa, 0, @cf, @nf, @cc, 'V', 0, 0, 0, 0, @ve, @u, @cr)",
                                   "t", d.Tipo, "n", numero, "f", d.Fecha.Date, "c", d.TerceroId, "a", d.AlmacenId, "v", OrNull(d.VendedorId), "mo", d.Moneda, "tc", CDbl(d.TC), "de", d.Detalle,
                                   "st", t.Subtotal, "dc", t.Descuento, "rc", t.Recargo, "to", t.Total, "an", d.Anticipo, "ac", If(d.Tipo = "CRE", d.ACuenta, t.Total - d.Anticipo),
                                   "sa", cxc, "cf", If(d.ConFactura, 1, 0), "nf", If(d.ConFactura AndAlso d.Factura IsNot Nothing, d.Factura.NroFactura, ""), "cc", OrNull(cuentaCobro),
                                   "ve", OrNull(d.Vencimiento), "u", _ctx.Usuario.Id, "cr", Date.Now)
                               res.Id = ventaId
                               ' Detalle y existencias
                               Dim mov As New MovInvDto With {.Tipo = "VENT", .Fecha = d.Fecha, .AlmacenId = d.AlmacenId, .TerceroId = d.TerceroId, .Moneda = d.Moneda, .TC = d.TC,
                                   .Detalle = "Venta " & d.Tipo & " Nº " & numero, .DocTipo = "VENTA", .DocId = ventaId}
                               Dim items As New Dictionary(Of Integer, ItemDto)
                               For Each l As DocLine In d.Lines
                                   Dim it As ItemDto = inv.ObtenerItem(l.ItemId)
                                   If it Is Nothing Then Throw New InvalidOperationException("Ítem inexistente en la venta.")
                                   items(l.ItemId) = it
                                   If Not it.EsServicio Then mov.Lines.Add(New MovLine With {.ItemId = l.ItemId, .Cantidad = l.Cantidad, .PrecioUnit = l.PrecioUnit})
                               Next
                               Dim movRes As MovResult = Nothing
                               If mov.Lines.Count > 0 Then
                                   movRes = inv.Aplicar(mov)
                                   Db.Execute("UPDATE Venta SET MovInvId=@m WHERE Id=@i", "m", movRes.MovId, "i", ventaId)
                               End If
                               Dim costoPorItem As New Dictionary(Of Integer, Decimal)
                               If movRes IsNot Nothing Then
                                   For Each ml In movRes.Lines
                                       costoPorItem(ml.ItemId) = (If(costoPorItem.ContainsKey(ml.ItemId), costoPorItem(ml.ItemId), 0D)) + ml.ImporteBs
                                   Next
                               End If
                               Dim linea As Integer = 0
                               Dim costoTotal As Decimal = 0D
                               For i As Integer = 0 To d.Lines.Count - 1
                                   Dim l As DocLine = d.Lines(i)
                                   linea += 1
                                   Dim cu As Decimal = 0D
                                   If movRes IsNot Nothing AndAlso Not items(l.ItemId).EsServicio Then
                                       Dim ml = movRes.Lines.FirstOrDefault(Function(x) x.ItemId = l.ItemId)
                                       If ml IsNot Nothing Then cu = ml.CostoUnitBs
                                   End If
                                   Db.Execute("INSERT INTO VentaDet (VentaId, Linea, ItemId, Descripcion, Cantidad, PrecioUnit, ImporteBs, CostoUnitBs) VALUES (@v, @l, @i, @d, @c, @p, @im, @cu)",
                                              "v", ventaId, "l", linea, "i", l.ItemId, "d", If(l.Descripcion <> "", l.Descripcion, items(l.ItemId).Descripcion), "c", CDbl(l.Cantidad), "p", CDbl(l.PrecioUnit), "im", t.LineasBs(i), "cu", CDbl(cu))
                               Next
                               costoTotal = If(movRes Is Nothing, 0D, movRes.TotalBs)
                               res.Costo = costoTotal
                               res.Total = t.Total
                               res.ImpuestoFiscal = t.Impuesto

                               Dim vs As New VoucherService(_ctx)
                               Dim glosa As String = "Venta " & If(d.Tipo = "CON", "contado", "crédito") & " Nº " & numero & " - " & cli.Nombre & If(d.Detalle <> "", " - " & d.Detalle, "")
                               ' ---- Comprobante de ingreso (o traspaso si no hubo caja) ----
                               Dim v As Voucher = vs.Nuevo(If(cobro > 0D, "I", "T"), d.Fecha)
                               v.Glosa = glosa : v.Origen = "VEN" : v.OrigenId = ventaId
                               If cobro > 0D Then v.Lines.Add(VoucherLine.Deb(cuentaCobro, cobro, glosa))
                               If d.Anticipo > 0D Then v.Lines.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaAnticipoCli), d.Anticipo, glosa))
                               If cxc > 0D Then v.Lines.Add(VoucherLine.Deb(cuentaCxc, cxc, glosa))
                               If Not enBase AndAlso t.Descuento > 0D Then v.Lines.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaDescVentas), t.Descuento, glosa))
                               Dim reparto As List(Of Decimal) = TotalesDoc.Repartir(t.Neto, t.LineasBs)
                               Dim porCuenta As New Dictionary(Of Integer, Decimal)
                               For i As Integer = 0 To d.Lines.Count - 1
                                   Dim it As ItemDto = items(d.Lines(i).ItemId)
                                   Dim cta As Integer = If(it.CuentaIngId <> 0, it.CuentaIngId, _ctx.CuentaParam(ParamKeys.CtaVentas))
                                   porCuenta(cta) = (If(porCuenta.ContainsKey(cta), porCuenta(cta), 0D)) + reparto(i)
                               Next
                               For Each kv In porCuenta
                                   If kv.Value <> 0D Then v.Lines.Add(VoucherLine.Hab(kv.Key, kv.Value, glosa))
                               Next
                               If t.Impuesto > 0D Then v.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaDebitoFiscal), t.Impuesto, glosa))
                               If Not enBase AndAlso t.Recargo > 0D Then v.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaRecVentas), t.Recargo, glosa))
                               Dim ingId As Integer = vs.Registrar(v)
                               res.ComprobanteId = ingId
                               Db.Execute("UPDATE Venta SET ComprobanteId=@c WHERE Id=@i", "c", ingId, "i", ventaId)

                               ' ---- Costo de venta ----
                               If costoTotal > 0D Then
                                   Dim vc As Voucher = vs.Nuevo("T", d.Fecha)
                                   vc.Glosa = "Costo de venta Nº " & numero & " - " & cli.Nombre
                                   vc.Origen = "VEN" : vc.OrigenId = ventaId
                                   Dim deb As New Dictionary(Of Integer, Decimal)
                                   Dim hab As New Dictionary(Of Integer, Decimal)
                                   For Each kv In costoPorItem
                                       Dim it As ItemDto = items(kv.Key)
                                       Dim cd As Integer = If(it.CuentaCostoId <> 0, it.CuentaCostoId, _ctx.CuentaParam(ParamKeys.CtaCostoVentas))
                                       Dim ch As Integer = If(it.CuentaInvId <> 0, it.CuentaInvId, _ctx.CuentaParam(ParamKeys.CtaInventario))
                                       deb(cd) = (If(deb.ContainsKey(cd), deb(cd), 0D)) + kv.Value
                                       hab(ch) = (If(hab.ContainsKey(ch), hab(ch), 0D)) + kv.Value
                                   Next
                                   For Each kv In deb
                                       vc.Lines.Add(VoucherLine.Deb(kv.Key, kv.Value, vc.Glosa))
                                   Next
                                   For Each kv In hab
                                       vc.Lines.Add(VoucherLine.Hab(kv.Key, kv.Value, vc.Glosa))
                                   Next
                                   ' el costo de ítems con totales redondeados por línea puede diferir en centavos: se cuadra con la cuenta de costo
                                   Dim dif As Decimal = vc.TotalDebe - vc.TotalHaber
                                   If dif <> 0D Then
                                       If dif > 0D Then vc.Lines.Add(VoucherLine.Hab(hab.Keys.First(), dif, vc.Glosa)) Else vc.Lines.Add(VoucherLine.Deb(deb.Keys.First(), -dif, vc.Glosa))
                                   End If
                                   Dim cid As Integer = vs.Registrar(vc)
                                   Db.Execute("UPDATE Venta SET ComprobanteCostoId=@c, CostoBs=@co WHERE Id=@i", "c", cid, "co", costoTotal, "i", ventaId)
                               End If

                               ' ---- Devengamiento del IT ----
                               If d.ConFactura OrElse _ctx.Param.Bool(ParamKeys.ItSinFactura, True) Then
                                   Dim itl As List(Of VoucherLine) = fs.LineasIt(t.FacturaTotal, "IT venta Nº " & numero)
                                   If itl.Count > 0 Then
                                       Dim vi As Voucher = vs.Nuevo("T", d.Fecha)
                                       vi.Glosa = "Devengamiento IT venta Nº " & numero & " - " & cli.Nombre
                                       vi.Origen = "VEN" : vi.OrigenId = ventaId
                                       vi.Lines.AddRange(itl)
                                       Dim iid As Integer = vs.Registrar(vi)
                                       Db.Execute("UPDATE Venta SET ComprobanteItId=@c WHERE Id=@i", "c", iid, "i", ventaId)
                                   End If
                               End If

                               ' ---- Libro de ventas IVA ----
                               If d.ConFactura Then
                                   Dim f As FacturaDto = d.Factura
                                   f.Libro = "V"
                                   f.Fecha = d.Fecha
                                   f.TerceroId = d.TerceroId
                                   If f.Nit = "" Then f.Nit = cli.Nit
                                   If f.RazonSocial = "" Then f.RazonSocial = cli.Nombre
                                   f.ImporteTotal = If(enBase, t.Subtotal + t.Recargo, t.Subtotal)
                                   f.Descuento = If(enBase, t.Descuento, 0D)
                                   f.ComprobanteId = ingId
                                   f.Origen = "VEN"
                                   f.OrigenId = ventaId
                                   fs.RegistrarInterno(f)
                               End If

                               ' ---- Cuenta corriente del cliente ----
                               Dim tcv As Decimal = d.TC
                               Dim mt = Sub(tipo As String, det As String, debe As Decimal, haber As Decimal)
                                            Db.Execute("INSERT INTO MovTercero (TerceroId, Clase, Fecha, Tipo, DocTipo, DocId, Referencia, Detalle, Debe, Haber, TC, ComprobanteId, Vigente) VALUES (@t, 'CXC', @f, @ty, 'VENTA', @d, @r, @de, @db, @ha, @tc, @c, 1)",
                                                       "t", d.TerceroId, "f", d.Fecha.Date, "ty", tipo, "d", ventaId, "r", d.Tipo & "-" & numero, "de", det, "db", debe, "ha", haber, "tc", CDbl(tcv), "c", ingId)
                                        End Sub
                               mt("VTA", "Venta " & If(d.Tipo = "CON", "al contado", "a crédito") & " Nº " & numero, t.Total, 0D)
                               If cobro > 0D Then mt("COB", "Pago " & If(d.Tipo = "CON", "contado", "a cuenta") & " venta Nº " & numero, 0D, cobro)

                               _ctx.Audit("Ventas", "VENTA_" & d.Tipo, "Nº " & numero & " " & cli.Nombre & " Bs " & t.Total.ToString("N2"))
                               Return res
                           End Function)
        End Function

        Public Sub Anular(ventaId As Integer, motivo As String)
            _ctx.Requiere("COM.VENTAS")
            _ctx.RequiereGestionAbierta()
            If String.IsNullOrWhiteSpace(motivo) Then Throw New ArgumentException("Indique el motivo de la anulación.")
            Dim dt As DataTable = Db.Query("SELECT * FROM Venta WHERE Id=@i", "i", ventaId)
            If dt.Rows.Count = 0 Then Throw New InvalidOperationException("Venta inexistente.")
            Dim v As DataRow = dt.Rows(0)
            If v.GetS("Estado") = "A" Then Return
            Dim creditoInicial As Decimal = If(v.GetS("Tipo") = "CRE", v.GetD("TotalBs") - v.GetD("AnticipoBs") - v.GetD("ACuentaBs"), 0D)
            If Math.Abs(v.GetD("SaldoBs") - creditoInicial) > 0.005D Then Throw New InvalidOperationException("La venta tiene cobros posteriores aplicados. Anule primero los cobros.")
            If v.GetS("Tipo") = "SIN" Then Throw New InvalidOperationException("Los saldos iniciales no se anulan desde ventas.")
            Db.InTx(Sub()
                        Dim inv As New InventarioService(_ctx)
                        Dim vs As New VoucherService(_ctx)
                        If v.GetI("MovInvId") <> 0 Then inv.AnularInterno(v.GetI("MovInvId"), "Anulación venta Nº " & v.GetS("Numero"))
                        For Each col As String In {"ComprobanteId", "ComprobanteCostoId", "ComprobanteItId"}
                            If v.GetI(col) <> 0 Then vs.AnularInterno(v.GetI(col), "Anulación venta Nº " & v.GetS("Numero") & ": " & motivo)
                        Next
                        Db.Execute("UPDATE MovTercero SET Vigente=0 WHERE DocTipo='VENTA' AND DocId=@i", "i", ventaId)
                        Db.Execute("UPDATE Venta SET Estado='A', SaldoBs=0 WHERE Id=@i", "i", ventaId)
                    End Sub)
            _ctx.Audit("Ventas", "VENTA_ANULADA", "Nº " & v.GetS("Numero") & ": " & motivo)
        End Sub

        Public Function Listar(desde As Date, hasta As Date, Optional clienteId As Integer = 0) As DataTable
            Dim sql As String = "SELECT v.*, t.Nombre AS Cliente FROM Venta v INNER JOIN Tercero t ON t.Id = v.ClienteId WHERE v.Fecha >= @d AND v.Fecha <= @h"
            Dim args As New List(Of Object) From {"d", desde.Date, "h", hasta.Date}
            If clienteId <> 0 Then
                sql &= " AND v.ClienteId=@c"
                args.AddRange({"c", clienteId})
            End If
            Return Db.Query(sql & " ORDER BY v.Fecha, v.Id", args.ToArray())
        End Function

        Public Function Detalle(ventaId As Integer) As DataTable
            Return Db.Query("SELECT d.*, i.Codigo FROM VentaDet d INNER JOIN Item i ON i.Id = d.ItemId WHERE d.VentaId=@v ORDER BY d.Linea", "v", ventaId)
        End Function

    End Class

    ''' <summary>Compras al contado y a crédito con inventario y crédito fiscal.</summary>
    Public Class CompraService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        Public Function AnticipoDisponible(proveedorId As Integer) As Decimal
            Dim s As Decimal = New TerceroService(_ctx).Saldo(proveedorId, "CXP")
            Return If(s < 0D, -s, 0D)
        End Function

        Public Function Registrar(d As DocumentoDto) As DocumentoResultado
            _ctx.Requiere("COM.COMPRAS")
            _ctx.RequiereGestionAbierta()
            If d.Tipo <> "CON" AndAlso d.Tipo <> "CRE" Then Throw New ArgumentException("Tipo de compra inválido.")
            If d.Lines.Count = 0 Then Throw New InvalidOperationException("Agregue al menos un ítem.")
            If d.Fecha.Date < _ctx.Gestion.FechaInicio.Date OrElse d.Fecha.Date > _ctx.Gestion.FechaFin.Date Then Throw New InvalidOperationException("La fecha está fuera de la gestión.")
            If d.TerceroId = 0 Then Throw New InvalidOperationException("Seleccione el proveedor.")
            If d.AlmacenId = 0 Then Throw New InvalidOperationException("Seleccione el almacén.")
            If d.TC <= 0D Then Throw New InvalidOperationException("Tipo de cambio inválido.")
            Dim prov As TerceroDto = New TerceroService(_ctx).Obtener(d.TerceroId)
            If prov Is Nothing OrElse Not prov.Activo Then Throw New InvalidOperationException("El proveedor no existe o está inactivo.")
            Dim inv As New InventarioService(_ctx)
            Dim fs As New FacturaService(_ctx)
            Dim t As TotalesDoc = TotalesDoc.Calcular(d, fs.IvaPct, True)
            If d.Anticipo < 0D OrElse d.ACuenta < 0D Then Throw New InvalidOperationException("Anticipo y pago a cuenta no pueden ser negativos.")
            If d.Anticipo > t.Total Then Throw New InvalidOperationException("El anticipo supera el total de la compra.")
            If d.Anticipo > AnticipoDisponible(d.TerceroId) + 0.005D Then Throw New InvalidOperationException("No hay anticipos al proveedor por ese monto (disponible Bs " & AnticipoDisponible(d.TerceroId).ToString("N2") & ").")
            Dim pago As Decimal, cxp As Decimal
            If d.Tipo = "CON" Then
                pago = t.Total - d.Anticipo
            Else
                If d.ACuenta + d.Anticipo > t.Total Then Throw New InvalidOperationException("El pago a cuenta más el anticipo superan el total.")
                pago = d.ACuenta
                cxp = t.Total - d.Anticipo - d.ACuenta
            End If
            Dim cuentaPago As Integer = d.CuentaPagoId
            If pago > 0D AndAlso cuentaPago = 0 Then cuentaPago = _ctx.CuentaParam(ParamKeys.CtaCaja)
            Dim cuentaCxp As Integer = If(prov.CuentaCxpId <> 0, prov.CuentaCxpId, _ctx.CuentaParam(ParamKeys.CtaCxp))
            If d.ConFactura AndAlso d.Factura Is Nothing Then Throw New InvalidOperationException("Ingrese los datos de la factura.")

            Return Db.InTx(Function()
                               Dim res As New DocumentoResultado()
                               Dim numero As Integer = _ctx.Siguiente("COMPRA_" & d.Tipo)
                               res.Numero = numero
                               Dim compraId As Integer = Db.Insert("INSERT INTO Compra (Tipo, Numero, Fecha, ProveedorId, AlmacenId, Moneda, TC, Detalle, SubtotalBs, DescuentoBs, RecargoBs, TotalBs, AnticipoBs, ACuentaBs, SaldoBs, CreditoFiscalBs, ConFactura, NroFactura, Autorizacion, CuentaPagoId, Estado, MovInvId, ComprobanteId, Vencimiento, UsuarioId, Creado) " &
                                   "VALUES (@t, @n, @f, @p, @a, @mo, @tc, @de, @st, @dc, @rc, @to, @an, @ac, @sa, @cf, @co, @nf, @au, @cp, 'V', 0, 0, @ve, @u, @cr)",
                                   "t", d.Tipo, "n", numero, "f", d.Fecha.Date, "p", d.TerceroId, "a", d.AlmacenId, "mo", d.Moneda, "tc", CDbl(d.TC), "de", d.Detalle, "st", t.Subtotal,
                                   "dc", t.Descuento, "rc", t.Recargo, "to", t.Total, "an", d.Anticipo, "ac", If(d.Tipo = "CRE", d.ACuenta, t.Total - d.Anticipo), "sa", cxp, "cf", t.Impuesto,
                                   "co", If(d.ConFactura, 1, 0), "nf", If(d.ConFactura AndAlso d.Factura IsNot Nothing, d.Factura.NroFactura, ""), "au", If(d.ConFactura AndAlso d.Factura IsNot Nothing, d.Factura.Autorizacion, ""),
                                   "cp", OrNull(cuentaPago), "ve", OrNull(d.Vencimiento), "u", _ctx.Usuario.Id, "cr", Date.Now)
                               res.Id = compraId
                               ' Valor neto (sin crédito fiscal) repartido en las líneas
                               Dim netos As List(Of Decimal) = TotalesDoc.Repartir(t.Neto, t.LineasBs)
                               Dim factorMon As Decimal = If(d.Moneda = "USD", d.TC, 1D)
                               Dim mov As New MovInvDto With {.Tipo = "COMP", .Fecha = d.Fecha, .AlmacenId = d.AlmacenId, .TerceroId = d.TerceroId, .Moneda = "BS", .TC = 1D,
                                   .Detalle = "Compra " & d.Tipo & " Nº " & numero, .DocTipo = "COMPRA", .DocId = compraId}
                               Dim items As New Dictionary(Of Integer, ItemDto)
                               Dim porCuenta As New Dictionary(Of Integer, Decimal)
                               For i As Integer = 0 To d.Lines.Count - 1
                                   Dim l As DocLine = d.Lines(i)
                                   Dim it As ItemDto = inv.ObtenerItem(l.ItemId)
                                   If it Is Nothing Then Throw New InvalidOperationException("Ítem inexistente en la compra.")
                                   items(l.ItemId) = it
                                   Dim cta As Integer
                                   If it.EsServicio Then
                                       cta = it.CuentaCostoId
                                       If cta = 0 Then Throw New InvalidOperationException("Configure la cuenta de costo/gasto del servicio '" & it.Codigo & "'.")
                                   Else
                                       cta = If(it.CuentaInvId <> 0, it.CuentaInvId, _ctx.CuentaParam(ParamKeys.CtaInventario))
                                       Dim costoUnit As Decimal = Math.Round(netos(i) / l.Cantidad, 6)
                                       mov.Lines.Add(New MovLine With {.ItemId = l.ItemId, .Cantidad = l.Cantidad, .PrecioUnit = costoUnit, .FechaVenc = l.FechaVenc})
                                   End If
                                   porCuenta(cta) = (If(porCuenta.ContainsKey(cta), porCuenta(cta), 0D)) + netos(i)
                               Next
                               If mov.Lines.Count > 0 Then
                                   Dim mr As MovResult = inv.Aplicar(mov)
                                   Db.Execute("UPDATE Compra SET MovInvId=@m WHERE Id=@i", "m", mr.MovId, "i", compraId)
                               End If
                               Dim linea As Integer = 0
                               For i As Integer = 0 To d.Lines.Count - 1
                                   Dim l As DocLine = d.Lines(i)
                                   linea += 1
                                   Db.Execute("INSERT INTO CompraDet (CompraId, Linea, ItemId, Descripcion, Cantidad, PrecioUnit, ImporteBs, FechaVenc) VALUES (@c, @l, @i, @d, @q, @p, @im, @fv)",
                                              "c", compraId, "l", linea, "i", l.ItemId, "d", If(l.Descripcion <> "", l.Descripcion, items(l.ItemId).Descripcion), "q", CDbl(l.Cantidad), "p", CDbl(l.PrecioUnit), "im", t.LineasBs(i), "fv", OrNull(l.FechaVenc))
                               Next
                               res.Total = t.Total
                               res.ImpuestoFiscal = t.Impuesto

                               Dim vs As New VoucherService(_ctx)
                               Dim glosa As String = "Compra " & If(d.Tipo = "CON", "contado", "crédito") & " Nº " & numero & " - " & prov.Nombre & If(d.Detalle <> "", " - " & d.Detalle, "")
                               Dim v As Voucher = vs.Nuevo(If(pago > 0D, "E", "T"), d.Fecha)
                               v.Glosa = glosa : v.Origen = "COM" : v.OrigenId = compraId
                               For Each kv In porCuenta
                                   If kv.Value <> 0D Then v.Lines.Add(VoucherLine.Deb(kv.Key, kv.Value, glosa))
                               Next
                               If t.Impuesto > 0D Then v.Lines.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaCreditoFiscal), t.Impuesto, glosa))
                               If pago > 0D Then v.Lines.Add(VoucherLine.Hab(cuentaPago, pago, glosa))
                               If d.Anticipo > 0D Then v.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaAnticipoProv), d.Anticipo, glosa))
                               If cxp > 0D Then v.Lines.Add(VoucherLine.Hab(cuentaCxp, cxp, glosa))
                               Dim cid As Integer = vs.Registrar(v)
                               res.ComprobanteId = cid
                               Db.Execute("UPDATE Compra SET ComprobanteId=@c WHERE Id=@i", "c", cid, "i", compraId)

                               If d.ConFactura Then
                                   Dim f As FacturaDto = d.Factura
                                   f.Libro = "C"
                                   f.TerceroId = d.TerceroId
                                   If f.Fecha = Date.MinValue OrElse f.Fecha = Date.Today AndAlso d.Fecha <> Date.Today Then f.Fecha = d.Fecha
                                   If f.Nit = "" Then f.Nit = prov.Nit
                                   If f.RazonSocial = "" Then f.RazonSocial = prov.Nombre
                                   f.ImporteTotal = t.Subtotal + t.Recargo
                                   f.Descuento = t.Descuento
                                   f.ComprobanteId = cid
                                   f.Origen = "COM"
                                   f.OrigenId = compraId
                                   fs.RegistrarInterno(f)
                               End If

                               Dim mt = Sub(tipo As String, det As String, debe As Decimal, haber As Decimal)
                                            Db.Execute("INSERT INTO MovTercero (TerceroId, Clase, Fecha, Tipo, DocTipo, DocId, Referencia, Detalle, Debe, Haber, TC, ComprobanteId, Vigente) VALUES (@t, 'CXP', @f, @ty, 'COMPRA', @d, @r, @de, @db, @ha, @tc, @c, 1)",
                                                       "t", d.TerceroId, "f", d.Fecha.Date, "ty", tipo, "d", compraId, "r", d.Tipo & "-" & numero, "de", det, "db", debe, "ha", haber, "tc", CDbl(d.TC), "c", cid)
                                        End Sub
                               mt("COM", "Compra " & If(d.Tipo = "CON", "al contado", "a crédito") & " Nº " & numero, 0D, t.Total)
                               If pago > 0D Then mt("PAG", "Pago " & If(d.Tipo = "CON", "contado", "a cuenta") & " compra Nº " & numero, pago, 0D)

                               _ctx.Audit("Compras", "COMPRA_" & d.Tipo, "Nº " & numero & " " & prov.Nombre & " Bs " & t.Total.ToString("N2"))
                               Return res
                           End Function)
        End Function

        Public Sub Anular(compraId As Integer, motivo As String)
            _ctx.Requiere("COM.COMPRAS")
            _ctx.RequiereGestionAbierta()
            If String.IsNullOrWhiteSpace(motivo) Then Throw New ArgumentException("Indique el motivo de la anulación.")
            Dim dt As DataTable = Db.Query("SELECT * FROM Compra WHERE Id=@i", "i", compraId)
            If dt.Rows.Count = 0 Then Throw New InvalidOperationException("Compra inexistente.")
            Dim c As DataRow = dt.Rows(0)
            If c.GetS("Estado") = "A" Then Return
            Dim creditoInicial As Decimal = If(c.GetS("Tipo") = "CRE", c.GetD("TotalBs") - c.GetD("AnticipoBs") - c.GetD("ACuentaBs"), 0D)
            If Math.Abs(c.GetD("SaldoBs") - creditoInicial) > 0.005D Then Throw New InvalidOperationException("La compra tiene pagos posteriores aplicados. Anule primero los pagos.")
            Db.InTx(Sub()
                        Dim inv As New InventarioService(_ctx)
                        Dim vs As New VoucherService(_ctx)
                        If c.GetI("MovInvId") <> 0 Then inv.AnularInterno(c.GetI("MovInvId"), "Anulación compra Nº " & c.GetS("Numero"))
                        If c.GetI("ComprobanteId") <> 0 Then vs.AnularInterno(c.GetI("ComprobanteId"), "Anulación compra Nº " & c.GetS("Numero") & ": " & motivo)
                        Db.Execute("UPDATE MovTercero SET Vigente=0 WHERE DocTipo='COMPRA' AND DocId=@i", "i", compraId)
                        Db.Execute("UPDATE Compra SET Estado='A', SaldoBs=0 WHERE Id=@i", "i", compraId)
                    End Sub)
            _ctx.Audit("Compras", "COMPRA_ANULADA", "Nº " & c.GetS("Numero") & ": " & motivo)
        End Sub

        Public Function Listar(desde As Date, hasta As Date, Optional proveedorId As Integer = 0) As DataTable
            Dim sql As String = "SELECT c.*, t.Nombre AS Proveedor FROM Compra c INNER JOIN Tercero t ON t.Id = c.ProveedorId WHERE c.Fecha >= @d AND c.Fecha <= @h"
            Dim args As New List(Of Object) From {"d", desde.Date, "h", hasta.Date}
            If proveedorId <> 0 Then
                sql &= " AND c.ProveedorId=@c"
                args.AddRange({"c", proveedorId})
            End If
            Return Db.Query(sql & " ORDER BY c.Fecha, c.Id", args.ToArray())
        End Function

        Public Function Detalle(compraId As Integer) As DataTable
            Return Db.Query("SELECT d.*, i.Codigo FROM CompraDet d INNER JOIN Item i ON i.Id = d.ItemId WHERE d.CompraId=@v ORDER BY d.Linea", "v", compraId)
        End Function
    End Class

    Public Class AplicacionDoc
        Public Property DocId As Integer
        Public Property Monto As Decimal
    End Class

    Public Class CobroPagoDto
        Public Property TerceroId As Integer
        ''' <summary>CXC = cobro a cliente, CXP = pago a proveedor</summary>
        Public Property Clase As String = "CXC"
        Public Property Fecha As Date = Date.Today
        Public Property Glosa As String = ""
        Public Property CuentaId As Integer
        Public Property Cheque As String = ""
        Public Property Banco As String = ""
        Public ReadOnly Property Aplicaciones As New List(Of AplicacionDoc)
        ''' <summary>Excedente que queda como anticipo del cliente/proveedor.</summary>
        Public Property AnticipoNuevo As Decimal
    End Class

    ''' <summary>Cobros a clientes y pagos a proveedores aplicados a documentos pendientes.</summary>
    Public Class CobroPagoService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Public Function Registrar(d As CobroPagoDto) As Integer
            _ctx.Requiere("COM.COBROS")
            _ctx.RequiereGestionAbierta()
            Dim db As Database = _ctx.Db
            Dim cxc As Boolean = d.Clase = "CXC"
            Dim terceros As New TerceroService(_ctx)
            Dim t As TerceroDto = terceros.Obtener(d.TerceroId)
            If t Is Nothing Then Throw New InvalidOperationException("Seleccione el " & If(cxc, "cliente", "proveedor") & ".")
            If d.Aplicaciones.Count = 0 AndAlso d.AnticipoNuevo <= 0D Then Throw New InvalidOperationException("Indique los documentos a cancelar o un anticipo.")
            If d.AnticipoNuevo < 0D Then Throw New InvalidOperationException("El anticipo no puede ser negativo.")
            Dim total As Decimal = d.Aplicaciones.Sum(Function(a) a.Monto) + d.AnticipoNuevo
            If total <= 0D Then Throw New InvalidOperationException("El importe debe ser mayor a cero.")
            Dim cuentaCaja As Integer = d.CuentaId
            If cuentaCaja = 0 Then cuentaCaja = _ctx.CuentaParam(ParamKeys.CtaCaja)
            Dim cuentaCc As Integer = If(cxc, If(t.CuentaCxcId <> 0, t.CuentaCxcId, _ctx.CuentaParam(ParamKeys.CtaCxc)), If(t.CuentaCxpId <> 0, t.CuentaCxpId, _ctx.CuentaParam(ParamKeys.CtaCxp)))
            Dim cuentaAnt As Integer = _ctx.CuentaParam(If(cxc, ParamKeys.CtaAnticipoCli, ParamKeys.CtaAnticipoProv))
            Dim tabla As String = If(cxc, "Venta", "Compra")
            Return db.InTx(Function()
                               ' Validar documentos
                               Dim refs As New List(Of String)
                               For Each a As AplicacionDoc In d.Aplicaciones
                                   If a.Monto <= 0D Then Throw New InvalidOperationException("Los importes aplicados deben ser mayores a cero.")
                                   Dim dt As DataTable = db.Query("SELECT SaldoBs, Estado, Tipo, Numero FROM " & tabla & " WHERE Id=@i", "i", a.DocId)
                                   If dt.Rows.Count = 0 Then Throw New InvalidOperationException("Documento inexistente.")
                                   If dt.Rows(0).GetS("Estado") <> "V" Then Throw New InvalidOperationException("No se puede cobrar/pagar un documento anulado.")
                                   If a.Monto > dt.Rows(0).GetD("SaldoBs") + 0.005D Then Throw New InvalidOperationException("El importe aplicado supera el saldo del documento Nº " & dt.Rows(0).GetS("Numero") & " (saldo Bs " & dt.Rows(0).GetD("SaldoBs").ToString("N2") & ").")
                                   refs.Add(dt.Rows(0).GetS("Tipo") & "-" & dt.Rows(0).GetS("Numero"))
                               Next
                               Dim vs As New VoucherService(_ctx)
                               Dim glosa As String = If(d.Glosa <> "", d.Glosa, If(cxc, "Cobro a ", "Pago a ") & t.Nombre & If(refs.Count > 0, " (" & String.Join(", ", refs) & ")", ""))
                               Dim v As Voucher = vs.Nuevo(If(cxc, "I", "E"), d.Fecha)
                               v.Glosa = glosa : v.Cheque = d.Cheque : v.Banco = d.Banco
                               v.Origen = If(cxc, "COB", "PAG")
                               Dim aplicado As Decimal = d.Aplicaciones.Sum(Function(a) a.Monto)
                               If cxc Then
                                   v.Lines.Add(VoucherLine.Deb(cuentaCaja, total, glosa))
                                   If aplicado > 0D Then v.Lines.Add(VoucherLine.Hab(cuentaCc, aplicado, glosa))
                                   If d.AnticipoNuevo > 0D Then v.Lines.Add(VoucherLine.Hab(cuentaAnt, d.AnticipoNuevo, glosa))
                               Else
                                   If aplicado > 0D Then v.Lines.Add(VoucherLine.Deb(cuentaCc, aplicado, glosa))
                                   If d.AnticipoNuevo > 0D Then v.Lines.Add(VoucherLine.Deb(cuentaAnt, d.AnticipoNuevo, glosa))
                                   v.Lines.Add(VoucherLine.Hab(cuentaCaja, total, glosa))
                               End If
                               Dim vid As Integer = vs.Registrar(v)
                               v.OrigenId = vid
                               db.Execute("UPDATE Comprobante SET OrigenId=@o WHERE Id=@i", "o", vid, "i", vid)
                               Dim tcv As Decimal = v.TC
                               For Each a As AplicacionDoc In d.Aplicaciones
                                   db.Execute("UPDATE " & tabla & " SET SaldoBs = SaldoBs - @m WHERE Id=@i", "m", a.Monto, "i", a.DocId)
                                   db.Execute("INSERT INTO Aplicacion (ComprobanteId, Clase, DocId, Fecha, Monto, Vigente) VALUES (@c, @cl, @d, @f, @m, 1)", "c", vid, "cl", d.Clase, "d", a.DocId, "f", d.Fecha.Date, "m", a.Monto)
                                   Dim cab As DataRow = db.Query("SELECT Tipo, Numero FROM " & tabla & " WHERE Id=@i", "i", a.DocId).Rows(0)
                                   db.Execute("INSERT INTO MovTercero (TerceroId, Clase, Fecha, Tipo, DocTipo, DocId, Referencia, Detalle, Debe, Haber, TC, ComprobanteId, Vigente) VALUES (@t, @cl, @f, @ty, @dt, @d, @r, @de, @db, @ha, @tc, @c, 1)",
                                              "t", d.TerceroId, "cl", d.Clase, "f", d.Fecha.Date, "ty", If(cxc, "COB", "PAG"), "dt", If(cxc, "COBRO", "PAGO"), "d", vid,
                                              "r", cab.GetS("Tipo") & "-" & cab.GetS("Numero"), "de", If(cxc, "Cobro ", "Pago ") & cab.GetS("Tipo") & "-" & cab.GetS("Numero"),
                                              "db", If(cxc, 0D, a.Monto), "ha", If(cxc, a.Monto, 0D), "tc", CDbl(tcv), "c", vid)
                               Next
                               If d.AnticipoNuevo > 0D Then
                                   db.Execute("INSERT INTO MovTercero (TerceroId, Clase, Fecha, Tipo, DocTipo, DocId, Referencia, Detalle, Debe, Haber, TC, ComprobanteId, Vigente) VALUES (@t, @cl, @f, 'ANT', @dt, @d, '', @de, @db, @ha, @tc, @c, 1)",
                                              "t", d.TerceroId, "cl", d.Clase, "f", d.Fecha.Date, "dt", If(cxc, "COBRO", "PAGO"), "d", vid, "de", "Anticipo", "db", If(cxc, 0D, d.AnticipoNuevo),
                                              "ha", If(cxc, d.AnticipoNuevo, 0D), "tc", CDbl(tcv), "c", vid)
                               End If
                               _ctx.Audit(If(cxc, "Cobros", "Pagos"), If(cxc, "COBRO", "PAGO"), t.Nombre & " Bs " & total.ToString("N2"))
                               Return vid
                           End Function)
        End Function

        ''' <summary>Anula un cobro/pago: restituye el saldo de los documentos y anula el comprobante.</summary>
        Public Sub Anular(comprobanteId As Integer, motivo As String)
            _ctx.Requiere("COM.COBROS")
            _ctx.RequiereGestionAbierta()
            Dim db As Database = _ctx.Db
            Dim apps As DataTable = db.Query("SELECT * FROM Aplicacion WHERE ComprobanteId=@c AND Vigente=1", "c", comprobanteId)
            Dim tieneAnt As Integer = db.ScalarInt("SELECT COUNT(*) FROM MovTercero WHERE ComprobanteId=@c AND Tipo='ANT' AND Vigente=1 AND DocTipo IN ('COBRO','PAGO')", "c", comprobanteId)
            If apps.Rows.Count = 0 AndAlso tieneAnt = 0 Then Throw New InvalidOperationException("El comprobante no corresponde a un cobro/pago.")
            db.InTx(Sub()
                        For Each a As DataRow In apps.Rows
                            Dim tabla As String = If(a.GetS("Clase") = "CXC", "Venta", "Compra")
                            db.Execute("UPDATE " & tabla & " SET SaldoBs = SaldoBs + @m WHERE Id=@i", "m", a.GetD("Monto"), "i", a.GetI("DocId"))
                        Next
                        db.Execute("UPDATE Aplicacion SET Vigente=0 WHERE ComprobanteId=@c", "c", comprobanteId)
                        db.Execute("UPDATE MovTercero SET Vigente=0 WHERE ComprobanteId=@c AND DocTipo IN ('COBRO','PAGO')", "c", comprobanteId)
                        Dim vs As New VoucherService(_ctx)
                        vs.AnularInterno(comprobanteId, motivo)
                    End Sub)
        End Sub

    End Class

End Namespace
