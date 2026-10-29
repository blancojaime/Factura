Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class ComercialTests

    <Fact>
    Public Sub CompraConFacturaSeparaCreditoFiscalYValorizaInventario()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Proveedor SA", proveedor:=True)
            Dim it = ItemNuevo(e, "A1")
            Dim r = Compra(e, prov, it, 10D, 100D)       ' total 1000
            Assert.Equal(1000D, r.Total)
            Assert.Equal(130D, r.ImpuestoFiscal)
            Assert.Equal(870D, Saldo(e, "1.1.3.01.001"))   ' inventario neto de IVA
            Assert.Equal(130D, Saldo(e, "1.1.2.03.001"))   ' crédito fiscal
            Assert.Equal(-1000D, Saldo(e, Caja))          ' pagó contado
            Dim inv As New InventarioService(e.Ctx)
            Assert.Equal(10D, inv.Stock(it))
            Assert.Equal(87D, ToDec(e.Ctx.Db.Scalar("SELECT CostoProm FROM Item WHERE Id=@i", "i", it)))
        End Using
    End Sub

    <Fact>
    Public Sub VentaContadoConFacturaGeneraIvaItYCostoComoEnElManual()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Proveedor SA", proveedor:=True)
            Dim cli = Cliente(e)
            Dim it = ItemNuevo(e, "A1")
            Compra(e, prov, it, 10D, 100D)
            Dim r = Venta(e, cli, it, 5D, 200D)           ' Bs 1000 con factura
            Assert.Equal(1000D, r.Total)
            Assert.Equal(130D, r.ImpuestoFiscal)
            Assert.Equal(435D, r.Costo)                    ' 5 x 87
            Assert.Equal(0D, Saldo(e, Caja))               ' -1000 compra + 1000 venta
            Assert.Equal(130D, Saldo(e, "2.1.2.01.001"))   ' débito fiscal
            Assert.Equal(870D, Saldo(e, "4.1.1.01.001"))   ' ventas netas
            Assert.Equal(30D, Saldo(e, "5.3.1.03.001"))    ' IT gasto 3%
            Assert.Equal(30D, Saldo(e, "2.1.2.01.002"))    ' IT por pagar
            Assert.Equal(435D, Saldo(e, "5.1.1.01.001"))   ' costo de ventas
            Assert.Equal(435D, Saldo(e, "1.1.3.01.001"))   ' inventario restante 5 x 87
            Assert.Equal(5D, New InventarioService(e.Ctx).Stock(it))
            ' libro de ventas
            Dim fs As New FacturaService(e.Ctx)
            Dim lv = fs.Listar("V", New Date(2025, 3, 1), New Date(2025, 3, 31))
            Assert.Equal(1, lv.Rows.Count)
            Assert.Equal(130D, lv.Rows(0).GetD("Impuesto"))
            Assert.Equal(870D, lv.Rows(0).GetD("BaseCf") - lv.Rows(0).GetD("Impuesto"))
            ' 3 comprobantes: ingreso, costo, IT
            Dim vta = e.Ctx.Db.Query("SELECT * FROM Venta").Rows(0)
            Assert.True(vta.GetI("ComprobanteId") > 0 AndAlso vta.GetI("ComprobanteCostoId") > 0 AndAlso vta.GetI("ComprobanteItId") > 0)
            ' el balance general cuadra
            Dim bg = New LedgerService(e.Ctx).BalanceGeneral(New Date(2025, 12, 31), False, 99)
            Assert.True(bg.Cuadra)
        End Using
    End Sub

    <Fact>
    Public Sub VentaSinFacturaNoGeneraDebitoFiscal()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim cli = Cliente(e)
            Dim it = ItemNuevo(e, "A1")
            Compra(e, prov, it, 10D, 100D, factura:=False)
            Venta(e, cli, it, 2D, 200D, factura:=False)
            Assert.Equal(0D, Saldo(e, "2.1.2.01.001"))
            Assert.Equal(400D, Saldo(e, "4.1.1.01.001"))
            Assert.Equal(12D, Saldo(e, "5.3.1.03.001"))   ' IT sin factura (parámetro por defecto)
            Assert.Equal(0, New FacturaService(e.Ctx).Listar("V", New Date(2025, 1, 1), New Date(2025, 12, 31)).Rows.Count)
            ' con parámetro desactivado no devenga IT
            e.Ctx.Param.Guardar(ParamKeys.ItSinFactura, "0")
            Venta(e, cli, it, 1D, 200D, factura:=False)
            Assert.Equal(12D, Saldo(e, "5.3.1.03.001"))
        End Using
    End Sub

    <Fact>
    Public Sub StockInsuficienteImpideLaVenta()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim cli = Cliente(e)
            Dim it = ItemNuevo(e, "A1")
            Compra(e, prov, it, 3D, 100D)
            Dim ex = Assert.Throws(Of InvalidOperationException)(Sub() Venta(e, cli, it, 4D, 200D))
            Assert.Contains("Stock insuficiente", ex.Message)
            ' la transacción se revierte completamente
            Assert.Equal(0, e.Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Venta"))
            Assert.Equal(3D, New InventarioService(e.Ctx).Stock(it))
        End Using
    End Sub

    <Fact>
    Public Sub VentaAlCreditoYCobrosParciales()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim cli = Cliente(e)
            Dim it = ItemNuevo(e, "A1")
            Compra(e, prov, it, 10D, 100D)
            Dim r = Venta(e, cli, it, 5D, 200D, tipo:="CRE", aCuenta:=300D)
            Dim ts As New TerceroService(e.Ctx)
            Assert.Equal(700D, ts.Saldo(cli, "CXC"))
            Assert.Equal(700D, Saldo(e, "1.1.2.01.001"))
            Dim cp As New CobroPagoService(e.Ctx)
            Dim d As New CobroPagoDto With {.TerceroId = cli, .Clase = "CXC", .Fecha = New Date(2025, 3, 20)}
            d.Aplicaciones.Add(New AplicacionDoc With {.DocId = r.Id, .Monto = 500D})
            Dim vid = cp.Registrar(d)
            Assert.Equal(200D, ts.Saldo(cli, "CXC"))
            Assert.Equal(200D, ToDec(e.Ctx.Db.Scalar("SELECT SaldoBs FROM Venta WHERE Id=@i", "i", r.Id)))
            ' sobrepago
            Dim d2 As New CobroPagoDto With {.TerceroId = cli, .Clase = "CXC", .Fecha = New Date(2025, 3, 21)}
            d2.Aplicaciones.Add(New AplicacionDoc With {.DocId = r.Id, .Monto = 250D})
            Assert.Throws(Of InvalidOperationException)(Sub() cp.Registrar(d2))
            ' no se puede anular la venta con cobros; sí anulando el cobro primero
            Dim vsv As New VentaService(e.Ctx)
            Assert.Throws(Of InvalidOperationException)(Sub() vsv.Anular(r.Id, "x"))
            cp.Anular(vid, "cheque rebotado")
            Assert.Equal(700D, ts.Saldo(cli, "CXC"))
            vsv.Anular(r.Id, "devolución total")
            Assert.Equal(0D, ts.Saldo(cli, "CXC"))
            Assert.Equal(10D, New InventarioService(e.Ctx).Stock(it))
            Assert.Equal(0D, Saldo(e, "1.1.2.01.001"))
            Assert.Equal(0D, Saldo(e, "4.1.1.01.001"))
            Assert.Equal(0D, Saldo(e, "5.1.1.01.001"))
            Assert.Equal(0D, Saldo(e, "5.3.1.03.001"))
            Assert.Equal(0D, Saldo(e, "2.1.2.01.001"))
            Assert.Equal("A", e.Ctx.Db.ScalarStr("SELECT Estado FROM FacturaIva WHERE Libro='V'"))
        End Using
    End Sub

    <Fact>
    Public Sub LimiteDeCreditoYAnticipos()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim cli = Cliente(e, "Con límite", limite:=500D)
            Dim it = ItemNuevo(e, "A1")
            Compra(e, prov, it, 10D, 100D)
            Assert.Throws(Of InvalidOperationException)(Sub() Venta(e, cli, it, 5D, 200D, tipo:="CRE"))
            ' anticipo del cliente
            Dim cp As New CobroPagoService(e.Ctx)
            Dim d As New CobroPagoDto With {.TerceroId = cli, .Clase = "CXC", .Fecha = New Date(2025, 3, 2), .AnticipoNuevo = 300D}
            cp.Registrar(d)
            Dim vsr As New VentaService(e.Ctx)
            Assert.Equal(300D, vsr.AnticipoDisponible(cli))
            Assert.Equal(300D, Saldo(e, "2.1.1.02.001"))
            ' venta contado de 400 usando 300 de anticipo
            Dim dd As New DocumentoDto With {.Tipo = "CON", .Fecha = New Date(2025, 3, 5), .TerceroId = cli, .AlmacenId = Almacen(e), .TC = 6.96D, .Anticipo = 300D}
            dd.Lines.Add(New DocLine With {.ItemId = it, .Cantidad = 2D, .PrecioUnit = 200D})
            vsr.Registrar(dd)
            Assert.Equal(0D, vsr.AnticipoDisponible(cli))
            Assert.Equal(0D, Saldo(e, "2.1.1.02.001"))
            Assert.Equal(0D, New TerceroService(e.Ctx).Saldo(cli, "CXC"))
            ' anticipo mayor al disponible
            dd.Anticipo = 50D
            Assert.Throws(Of InvalidOperationException)(Sub() vsr.Registrar(dd))
        End Using
    End Sub

    <Fact>
    Public Sub CompraAlCreditoYPagoAProveedor()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim it = ItemNuevo(e, "A1")
            Dim r = Compra(e, prov, it, 10D, 100D, tipo:="CRE")
            Dim ts As New TerceroService(e.Ctx)
            Assert.Equal(1000D, ts.Saldo(prov, "CXP"))
            Assert.Equal(1000D, Saldo(e, "2.1.1.01.001"))    ' saldo acreedor natural = deuda
        End Using
    End Sub

    <Fact>
    Public Sub CuentaPorPagarTieneSaldoAcreedor()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim it = ItemNuevo(e, "A1")
            Dim r = Compra(e, prov, it, 10D, 100D, tipo:="CRE")
            Dim cp As New CobroPagoService(e.Ctx)
            Dim d As New CobroPagoDto With {.TerceroId = prov, .Clase = "CXP", .Fecha = New Date(2025, 3, 15), .Cheque = "123"}
            d.Aplicaciones.Add(New AplicacionDoc With {.DocId = r.Id, .Monto = 400D})
            cp.Registrar(d)
            Assert.Equal(600D, New TerceroService(e.Ctx).Saldo(prov, "CXP"))
            Assert.Equal(600D, ToDec(e.Ctx.Db.Scalar("SELECT SaldoBs FROM Compra WHERE Id=@i", "i", r.Id)))
            Assert.Equal(-400D, Saldo(e, Caja))
            Dim k = New TerceroService(e.Ctx).Kardex(prov, "CXP", New Date(2025, 1, 1), New Date(2025, 12, 31))
            Assert.Equal(600D, k.Last().Saldo)
        End Using
    End Sub

    <Fact>
    Public Sub CostoPromedioPonderadoYKardex()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim cli = Cliente(e)
            Dim it = ItemNuevo(e, "A1")
            Compra(e, prov, it, 10D, 100D, factura:=False, fecha:=New Date(2025, 3, 1))      ' 10 @100
            Compra(e, prov, it, 10D, 200D, factura:=False, fecha:=New Date(2025, 3, 2), nroFac:="C2")  ' 10 @200 -> PMP 150
            Dim inv As New InventarioService(e.Ctx)
            Assert.Equal(150D, ToDec(e.Ctx.Db.Scalar("SELECT CostoProm FROM Item WHERE Id=@i", "i", it)))
            Venta(e, cli, it, 4D, 300D, factura:=False, fecha:=New Date(2025, 3, 3))          ' sale a 150
            Dim k = inv.Kardex(it, 0, New Date(2025, 3, 1), New Date(2025, 3, 31))
            Assert.Equal(4, k.Count)   ' saldo inicial + 3 mov
            Assert.Equal(16D, k.Last().SaldoCant)
            Assert.Equal(2400D, k.Last().SaldoValor)
            Assert.Equal(150D, k.Last().SaldoCosto)
            Assert.Equal(600D, k.Last().SalTotal)
            ' kardex posterior parte del saldo
            Dim k2 = inv.Kardex(it, 0, New Date(2025, 3, 3), New Date(2025, 3, 31))
            Assert.Equal(20D, k2.First().SaldoCant)
            Assert.Equal(3000D, k2.First().SaldoValor)
            ' recalculo reproduce el mismo costo
            inv.RecalcularItem(it)
            Assert.Equal(150D, ToDec(e.Ctx.Db.Scalar("SELECT CostoProm FROM Item WHERE Id=@i", "i", it)))
            Assert.Equal(16D, inv.Stock(it))
        End Using
    End Sub

    <Fact>
    Public Sub VencimientosUsanFefoYReportanPorVencer()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim cli = Cliente(e)
            Dim it = ItemNuevo(e, "LECHE", venc:=True)
            Compra(e, prov, it, 10D, 10D, factura:=False, venc:=New Date(2025, 6, 30), nroFac:="C1")
            Compra(e, prov, it, 10D, 10D, factura:=False, venc:=New Date(2025, 4, 30), nroFac:="C2", fecha:=New Date(2025, 3, 2))
            Venta(e, cli, it, 12D, 20D, factura:=False)
            ' FEFO: consume 10 del lote de abril y 2 del de junio
            Dim inv As New InventarioService(e.Ctx)
            Dim pv = inv.PorVencer(New Date(2025, 12, 31))
            Assert.Equal(1, pv.Rows.Count)
            Assert.Equal(8D, pv.Rows(0).GetD("Cantidad"))
            Assert.Equal(New Date(2025, 6, 30), pv.Rows(0).GetDt("Vencimiento"))
            ' compra de ítem con vencimiento sin fecha
            Assert.Throws(Of InvalidOperationException)(Sub() Compra(e, prov, it, 1D, 10D, factura:=False, nroFac:="C3"))
        End Using
    End Sub

    <Fact>
    Public Sub TraspasoEntreAlmacenesConservaCosto()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim it = ItemNuevo(e, "A1")
            Compra(e, prov, it, 10D, 100D, factura:=False)
            Dim inv As New InventarioService(e.Ctx)
            Dim dest = Almacen(e, "PROD")
            Dim m As New MovInvDto With {.Tipo = "TRAS", .Fecha = New Date(2025, 3, 10), .AlmacenId = Almacen(e), .AlmacenDestId = dest, .TC = 6.96D}
            m.Lines.Add(New MovLine With {.ItemId = it, .Cantidad = 4D})
            inv.Registrar(m)
            Assert.Equal(6D, inv.Stock(it, Almacen(e)))
            Assert.Equal(4D, inv.Stock(it, dest))
            Assert.Equal(10D, inv.Stock(it))
            Assert.Equal(100D, ToDec(e.Ctx.Db.Scalar("SELECT CostoProm FROM Item WHERE Id=@i", "i", it)))
            ' no se puede traspasar más de lo disponible
            m.Lines(0).Cantidad = 7D
            Assert.Throws(Of InvalidOperationException)(Sub() inv.Registrar(m))
        End Using
    End Sub

    <Fact>
    Public Sub AjustesGeneranAsientoContable()
        Using e As New Entorno()
            Dim it = ItemNuevo(e, "A1")
            Dim inv As New InventarioService(e.Ctx)
            Dim m As New MovInvDto With {.Tipo = "STIN", .Fecha = New Date(2025, 1, 1), .AlmacenId = Almacen(e), .TC = 6.96D, .GenerarAsiento = True, .ContracuentaId = Cta(e, Capital)}
            m.Lines.Add(New MovLine With {.ItemId = it, .Cantidad = 10D, .PrecioUnit = 50D})
            inv.Registrar(m)
            Assert.Equal(500D, Saldo(e, "1.1.3.01.001"))
            Assert.Equal(500D, Saldo(e, Capital))
            Dim s As New MovInvDto With {.Tipo = "AJSA", .Fecha = New Date(2025, 2, 1), .AlmacenId = Almacen(e), .TC = 6.96D, .GenerarAsiento = True, .ContracuentaId = Cta(e, "5.4.1.01.005"), .Detalle = "merma"}
            s.Lines.Add(New MovLine With {.ItemId = it, .Cantidad = 2D})
            inv.Registrar(s)
            Assert.Equal(400D, Saldo(e, "1.1.3.01.001"))
            Assert.Equal(100D, Saldo(e, "5.4.1.01.005"))
            ' anular el ajuste de salida repone el stock
            Dim mov = e.Ctx.Db.Query("SELECT Id FROM MovInv WHERE Tipo='AJSA'").Rows(0).GetI("Id")
            inv.Anular(mov, "error")
            Assert.Equal(10D, inv.Stock(it))
            Assert.Equal(500D, Saldo(e, "1.1.3.01.001"))
        End Using
    End Sub

    <Fact>
    Public Sub SaldoInicialDeClientesGeneraAsiento()
        Using e As New Entorno()
            Dim cli = Cliente(e)
            Dim ts As New TerceroService(e.Ctx)
            ts.SaldoInicial(cli, "CXC", New Date(2025, 1, 1), 4500D, Cta(e, Capital), True)
            Assert.Equal(4500D, ts.Saldo(cli, "CXC"))
            Assert.Equal(4500D, Saldo(e, "1.1.2.01.001"))
            Assert.Equal(1, ts.Pendientes(cli, "CXC").Rows.Count)
            ' cobro del saldo inicial
            Dim cp As New CobroPagoService(e.Ctx)
            Dim d As New CobroPagoDto With {.TerceroId = cli, .Clase = "CXC", .Fecha = New Date(2025, 2, 1)}
            d.Aplicaciones.Add(New AplicacionDoc With {.DocId = CInt(ts.Pendientes(cli, "CXC").Rows(0)("Id")), .Monto = 4500D})
            cp.Registrar(d)
            Assert.Equal(0D, ts.Saldo(cli, "CXC"))
            Assert.Equal(0, ts.Pendientes(cli, "CXC").Rows.Count)
        End Using
    End Sub

    <Fact>
    Public Sub ServiciosNoAfectanInventarioPeroSiVentas()
        Using e As New Entorno()
            Dim cli = Cliente(e)
            Dim srv = ItemNuevo(e, "SRV1", servicio:=True)
            Venta(e, cli, srv, 1D, 1130D)
            Assert.Equal(1130D, Saldo(e, Caja))
            Assert.Equal(0D, Saldo(e, "5.1.1.01.001"))
            Assert.Equal(983.1D, Saldo(e, "4.1.1.01.001"))   ' 1130 - 13% (146.90)
        End Using
    End Sub

End Class
