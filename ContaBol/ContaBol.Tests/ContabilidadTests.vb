Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class ContabilidadTests

    <Fact>
    Public Sub CorrelativoMensualReiniciaCadaMes()
        Using e As New Entorno(mensual:=True)
            Dim a = Asiento(e, "I", New Date(2025, 1, 10), Caja, Capital, 100D)
            Dim b = Asiento(e, "I", New Date(2025, 1, 20), Caja, Capital, 100D)
            Dim c = Asiento(e, "I", New Date(2025, 2, 5), Caja, Capital, 100D)
            Dim d = Asiento(e, "E", New Date(2025, 1, 5), Capital, Caja, 10D)
            Dim vs As New VoucherService(e.Ctx)
            Assert.Equal(1, vs.Cargar(a).Numero)
            Assert.Equal(2, vs.Cargar(b).Numero)
            Assert.Equal(1, vs.Cargar(c).Numero)
            Assert.Equal(1, vs.Cargar(d).Numero)
            Assert.Equal(2, vs.Cargar(c).Mes)
            Assert.Equal(b, vs.BuscarId("I", 2, 1))
        End Using
    End Sub

    <Fact>
    Public Sub CorrelativoUnicoEsContinuo()
        Using e As New Entorno(mensual:=False)
            Asiento(e, "I", New Date(2025, 1, 10), Caja, Capital, 100D)
            Dim c = Asiento(e, "I", New Date(2025, 5, 5), Caja, Capital, 100D)
            Assert.Equal(2, New VoucherService(e.Ctx).Cargar(c).Numero)
            Assert.Equal(0, New VoucherService(e.Ctx).Cargar(c).Mes)
        End Using
    End Sub

    <Fact>
    Public Sub NoGuardaComprobanteDescuadrado()
        Using e As New Entorno()
            Dim vs As New VoucherService(e.Ctx)
            Dim v = vs.Nuevo("T", New Date(2025, 3, 1))
            v.Lines.Add(VoucherLine.Deb(Cta(e, Caja), 100D))
            v.Lines.Add(VoucherLine.Hab(Cta(e, Capital), 99D))
            Dim ex = Assert.Throws(Of InvalidOperationException)(Sub() vs.Guardar(v))
            Assert.Contains("no cuadra", ex.Message)
        End Using
    End Sub

    <Fact>
    Public Sub ValidaCuentasYFechas()
        Using e As New Entorno()
            Dim vs As New VoucherService(e.Ctx)
            Dim v = vs.Nuevo("T", New Date(2025, 3, 1))
            v.Lines.Add(VoucherLine.Deb(Cta(e, "1.1.1"), 100D))   ' grupo, no movimiento
            v.Lines.Add(VoucherLine.Hab(Cta(e, Capital), 100D))
            Assert.Throws(Of InvalidOperationException)(Sub() vs.Guardar(v))
            Dim v2 = vs.Nuevo("T", New Date(2025, 3, 1))
            v2.Fecha = New Date(2024, 12, 31)
            v2.Lines.Add(VoucherLine.Deb(Cta(e, Caja), 100D))
            v2.Lines.Add(VoucherLine.Hab(Cta(e, Capital), 100D))
            Dim ex = Assert.Throws(Of InvalidOperationException)(Sub() vs.Guardar(v2))
            Assert.Contains("fuera de la gestión", ex.Message)
            Dim v3 = vs.Nuevo("T", New Date(2025, 3, 1))
            v3.Lines.Add(New VoucherLine With {.CuentaId = Cta(e, Caja), .Debe = 10D, .Haber = 10D})
            v3.Lines.Add(VoucherLine.Hab(Cta(e, Capital), 0D))
            Assert.Throws(Of InvalidOperationException)(Sub() vs.Guardar(v3))
        End Using
    End Sub

    <Fact>
    Public Sub ComprobanteEnDolaresConvierteABolivianos()
        Using e As New Entorno()
            Dim id = Asiento(e, "I", New Date(2025, 3, 1), Caja, Capital, 100D, moneda:="USD")
            Dim v = New VoucherService(e.Ctx).Cargar(id)
            Assert.Equal("USD", v.Moneda)
            Assert.Equal(100D, v.Lines(0).Debe)
            Assert.Equal(696D, v.Lines(0).DebeBs)
            Assert.Equal(100D, v.Lines(0).DebeUsd)
        End Using
    End Sub

    <Fact>
    Public Sub UsaTipoCambioDeLaFecha()
        Using e As New Entorno()
            Dim tc As New TipoCambioService(e.Ctx)
            tc.Guardar(New Date(2025, 6, 1), 7.5D, 2.5D)
            Assert.Equal(6.96D, tc.Dolar(New Date(2025, 5, 31)))
            Assert.Equal(7.5D, tc.Dolar(New Date(2025, 6, 15)))
            Assert.Equal(2.5D, tc.Ufv(New Date(2025, 7, 1)))
            Dim vs As New VoucherService(e.Ctx)
            Assert.Equal(7.5D, vs.Nuevo("I", New Date(2025, 8, 1)).TC)
        End Using
    End Sub

    <Fact>
    Public Sub ModificarYAnularActualizaSaldos()
        Using e As New Entorno()
            Dim vs As New VoucherService(e.Ctx)
            Dim led As New LedgerService(e.Ctx)
            Dim id1 = Asiento(e, "I", New Date(2025, 1, 5), Caja, Capital, 1000D)
            Dim id2 = Asiento(e, "I", New Date(2025, 1, 6), Caja, Ventas, 500D)
            Assert.Equal(1500D, led.SaldoCuenta(Cta(e, Caja), New Date(2025, 12, 31)))
            Dim v = vs.Cargar(id2)
            v.Lines(0).Debe = 700D
            v.Lines(1).Haber = 700D
            vs.Guardar(v)
            Assert.Equal(1700D, led.SaldoCuenta(Cta(e, Caja), New Date(2025, 12, 31)))
            vs.Anular(id2, "error de digitación")
            Assert.Equal(1000D, led.SaldoCuenta(Cta(e, Caja), New Date(2025, 12, 31)))
            Assert.Equal("A", vs.Cargar(id2).Estado)
            Assert.Throws(Of InvalidOperationException)(Sub() vs.Guardar(vs.Cargar(id2)))
            ' el número anulado no se reutiliza
            Dim id3 = Asiento(e, "I", New Date(2025, 1, 7), Caja, Capital, 1D)
            Assert.Equal(3, vs.Cargar(id3).Numero)
        End Using
    End Sub

    <Fact>
    Public Sub MayorMuestraSaldoAnteriorYAcumulado()
        Using e As New Entorno()
            Asiento(e, "I", New Date(2025, 1, 5), Caja, Capital, 1000D)
            Asiento(e, "E", New Date(2025, 1, 10), GastoLuz, Caja, 200D)
            Asiento(e, "E", New Date(2025, 2, 10), GastoLuz, Caja, 100D)
            Dim led As New LedgerService(e.Ctx)
            Dim m = led.Mayor(Cta(e, Caja), New Date(2025, 2, 1), New Date(2025, 2, 28))
            Assert.Equal(800D, m.SaldoAnterior)
            Assert.Single(m.Movimientos)
            Assert.Equal(700D, m.SaldoFinal)
            Assert.Equal(100D, m.TotalHaber)
            ' mayor de una cuenta grupo incluye a sus hijas
            Dim g = led.Mayor(Cta(e, "1.1.1.01"), New Date(2025, 1, 1), New Date(2025, 12, 31))
            Assert.Equal(700D, g.SaldoFinal)
        End Using
    End Sub

    <Fact>
    Public Sub BalanceSumasYSaldosCuadraYAcumulaJerarquia()
        Using e As New Entorno()
            Asiento(e, "AP", New Date(2025, 1, 1), Caja, Capital, 5000D, "Apertura")
            Asiento(e, "I", New Date(2025, 1, 10), Caja, Ventas, 2000D)
            Asiento(e, "E", New Date(2025, 1, 15), GastoLuz, Caja, 300D)
            Asiento(e, "T", New Date(2025, 1, 20), Banco, Caja, 1000D)
            Dim led As New LedgerService(e.Ctx)
            Dim b = led.Balance(New Date(2025, 1, 1), New Date(2025, 12, 31))
            Dim totD = b.Where(Function(x) x.Nivel = 1).Sum(Function(x) x.SaldoD)
            Dim totH = b.Where(Function(x) x.Nivel = 1).Sum(Function(x) x.SaldoH)
            Assert.Equal(totD, totH)
            Dim sumasD = b.Where(Function(x) x.EsMovimiento).Sum(Function(x) x.Debe)
            Assert.Equal(8300D, sumasD)
            Dim activo = b.First(Function(x) x.Codigo = "1")
            Assert.Equal(5000D + 2000D - 300D, activo.SaldoD)
            Dim disp = b.First(Function(x) x.Codigo = "1.1.1")
            Assert.Equal(activo.SaldoD, disp.SaldoD)
            ' nivel limitado
            Assert.All(led.Balance(New Date(2025, 1, 1), New Date(2025, 12, 31), False, 2), Sub(x) Assert.True(x.Nivel <= 2))
            ' saldo anterior cuando el rango no inicia en la gestión
            Dim feb = led.Balance(New Date(2025, 2, 1), New Date(2025, 2, 28)).FirstOrDefault(Function(x) x.Codigo = Caja)
            Assert.NotNull(feb)
            Assert.Equal(5000D + 2000D - 300D - 1000D, feb.AntD)
        End Using
    End Sub

    <Fact>
    Public Sub EstadosFinancierosCuadran()
        Using e As New Entorno()
            Asiento(e, "AP", New Date(2025, 1, 1), Caja, Capital, 5000D, "Apertura")
            Asiento(e, "I", New Date(2025, 1, 10), Caja, Ventas, 2000D)
            Asiento(e, "E", New Date(2025, 1, 15), GastoLuz, Caja, 300D)
            Dim led As New LedgerService(e.Ctx)
            Dim er = led.EstadoResultados(New Date(2025, 1, 1), New Date(2025, 12, 31), False, 99, "C")
            Assert.Equal(2000D, er.Total1)
            Assert.Equal(300D, er.Total2)
            Assert.Equal(1700D, er.Lineas.Last().Importe)
            Dim er2 = led.EstadoResultados(New Date(2025, 1, 1), New Date(2025, 12, 31), False, 99, "I")
            Assert.Equal(1700D, er2.Lineas.Last().Importe)
            Dim bg = led.BalanceGeneral(New Date(2025, 12, 31), False, 99)
            Assert.True(bg.Cuadra, "Balance general no cuadra: " & bg.Diferencia)
            Assert.Equal(6700D, bg.Total1)
            Assert.Contains(bg.Lineas, Function(l) l.Texto.StartsWith("Resultado del período"))
        End Using
    End Sub

    <Fact>
    Public Sub ReordenarYCambiarNumeracion()
        Using e As New Entorno()
            Dim vs As New VoucherService(e.Ctx)
            Dim a = Asiento(e, "E", New Date(2025, 2, 15), GastoLuz, Caja, 10D)
            Dim b = Asiento(e, "E", New Date(2025, 2, 5), GastoLuz, Caja, 20D)
            Dim c = Asiento(e, "E", New Date(2025, 2, 22), GastoLuz, Caja, 30D)
            vs.Reordenar("E", 2)
            Assert.Equal(1, vs.Cargar(b).Numero)
            Assert.Equal(2, vs.Cargar(a).Numero)
            Assert.Equal(3, vs.Cargar(c).Numero)
            vs.CambiarNumero("E", 2, 1, 3)
            Assert.Equal(3, vs.Cargar(b).Numero)
            Assert.Equal(1, vs.Cargar(c).Numero)
        End Using
    End Sub

    <Fact>
    Public Sub CambiarCuentaTrasladaMovimientos()
        Using e As New Entorno()
            Asiento(e, "E", New Date(2025, 2, 15), GastoLuz, Caja, 10D)
            Asiento(e, "E", New Date(2025, 3, 15), GastoLuz, Caja, 10D)
            Dim vs As New VoucherService(e.Ctx)
            Dim n = vs.CambiarCuenta(Cta(e, GastoLuz), Cta(e, "5.3.1.02.002"), New Date(2025, 1, 1), New Date(2025, 2, 28))
            Assert.Equal(1, n)
            Dim led As New LedgerService(e.Ctx)
            Assert.Equal(10D, led.SaldoCuenta(Cta(e, "5.3.1.02.002"), New Date(2025, 12, 31)))
            Assert.Equal(10D, led.SaldoCuenta(Cta(e, GastoLuz), New Date(2025, 12, 31)))
        End Using
    End Sub

    <Fact>
    Public Sub ControlDePresupuestoBloqueaExceso()
        Using e As New Entorno()
            e.Ctx.Param.Guardar(ParamKeys.ControlPresupuesto, "1")
            Dim cs As New CuentaService(e.Ctx)
            Dim luz = e.Ctx.CuentaPorCodigo(GastoLuz)
            cs.Guardar(New CuentaDto With {.Id = luz.GetI("Id"), .Codigo = GastoLuz, .Nombre = luz.GetS("Nombre"), .Presupuestable = True})
            e.Ctx.Db.Execute("INSERT INTO Presupuesto (CuentaId, Mes, MontoBs) VALUES (@c, 1, 500)", "c", luz.GetI("Id"))
            Asiento(e, "E", New Date(2025, 1, 15), GastoLuz, Caja, 400D)
            Dim ex = Assert.Throws(Of InvalidOperationException)(Sub() Asiento(e, "E", New Date(2025, 1, 16), GastoLuz, Caja, 200D))
            Assert.Contains("presupuesto", ex.Message, StringComparison.OrdinalIgnoreCase)
        End Using
    End Sub

    <Fact>
    Public Sub PlanDeCuentasValidaJerarquia()
        Using e As New Entorno()
            Dim cs As New CuentaService(e.Ctx)
            ' nueva subcuenta convierte al padre en grupo
            Dim idHija = cs.Guardar(New CuentaDto With {.Codigo = "1.1.1.01.004", .Nombre = "Caja Sucursal"})
            Assert.True(e.Ctx.CuentaPorId(idHija).GetF("EsMovimiento"))
            Dim idNieta = cs.Guardar(New CuentaDto With {.Codigo = "1.1.1.01.004.01", .Nombre = "Caja Sucursal Norte"})
            Assert.False(e.Ctx.CuentaPorCodigo("1.1.1.01.004").GetF("EsMovimiento"))
            Assert.Equal(6, e.Ctx.CuentaPorId(idNieta).GetI("Nivel"))
            Assert.Throws(Of InvalidOperationException)(Sub() cs.Guardar(New CuentaDto With {.Codigo = "1.1.1.01.004", .Nombre = "Duplicada"}))
            Assert.Throws(Of ArgumentException)(Sub() cs.Guardar(New CuentaDto With {.Codigo = "9.1", .Nombre = "Mala"}))
            ' cuenta con movimientos no se elimina ni recibe hijos
            Asiento(e, "I", New Date(2025, 1, 5), Caja, Capital, 10D)
            Assert.Throws(Of InvalidOperationException)(Sub() cs.Eliminar(Cta(e, Caja)))
            Assert.Throws(Of InvalidOperationException)(Sub() cs.Guardar(New CuentaDto With {.Codigo = "1.1.1.01.001.01", .Nombre = "Hija de cuenta con movimiento"}))
            ' cuenta de parámetros no se elimina
            Assert.Throws(Of InvalidOperationException)(Sub() cs.Eliminar(Cta(e, "1.1.2.03.001")))
            ' eliminar la nieta devuelve movimiento al padre
            cs.Eliminar(idNieta)
            Assert.True(e.Ctx.CuentaPorCodigo("1.1.1.01.004").GetF("EsMovimiento"))
            ' búsqueda con comodines estilo Orion
            Assert.True(cs.Buscar("2.1.2*", True).Count > 3)
            Assert.Contains(cs.Buscar("*sueldos*", False), Function(r) r.GetS("Codigo") = "5.3.1.01.001")
        End Using
    End Sub

    <Fact>
    Public Sub LibroDeComprasCalculaCreditoFiscal()
        Using e As New Entorno()
            Dim fs As New FacturaService(e.Ctx)
            Dim vs As New VoucherService(e.Ctx)
            Dim v = vs.Nuevo("E", New Date(2025, 3, 10))
            Dim f As New FacturaDto With {.Libro = "C", .Fecha = v.Fecha, .NroFactura = "1234", .Nit = "1020304050", .Autorizacion = "AUT-1", .RazonSocial = "Proveedor SA", .ImporteTotal = 1500D}
            For Each l In fs.LineasCompra(f, Cta(e, GastoLuz), "Luz marzo")
                v.Lines.Add(l)
            Next
            v.Lines.Add(VoucherLine.Hab(Cta(e, Caja), 1500D))
            v.Facturas.Add(f)
            Dim id = vs.Guardar(v)
            Assert.Equal(195D, f.Impuesto)          ' 1500 * 13%
            Assert.Equal(1305D, v.Lines(0).Debe)
            Dim dt = fs.Listar("C", New Date(2025, 3, 1), New Date(2025, 3, 31))
            Assert.Equal(1, dt.Rows.Count)
            Assert.Equal(id, dt.Rows(0).GetI("ComprobanteId"))
            ' duplicado
            Dim dup As New FacturaDto With {.Libro = "C", .Fecha = v.Fecha, .NroFactura = "1234", .Nit = "1020304050", .Autorizacion = "AUT-1", .ImporteTotal = 10D}
            Assert.Throws(Of InvalidOperationException)(Sub() fs.Registrar(dup))
            ' el crédito fiscal se refleja en su cuenta
            Dim led As New LedgerService(e.Ctx)
            Assert.Equal(195D, led.SaldoCuenta(Cta(e, "1.1.2.03.001"), New Date(2025, 12, 31)))
            ' anular el comprobante anula la factura
            vs.Anular(id, "prueba")
            Assert.Equal("A", fs.Obtener(dt.Rows(0).GetI("Id")).Estado)
            Assert.Equal(0D, fs.Totales("C", New Date(2025, 3, 1), New Date(2025, 3, 31)).Item2)
            Assert.Contains("1020304050", fs.ExportarCsv("C", 3))
        End Using
    End Sub

End Class
