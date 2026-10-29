Imports System.Data
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class GestionTests

    <Fact>
    Public Sub CierreDeGestionTraspasaResultadoYBalanceCuadra()
        Using e As New Entorno()
            Asiento(e, "AP", New Date(2025, 1, 1), Caja, Capital, 10000D, "Apertura")
            Asiento(e, "I", New Date(2025, 2, 1), Caja, Ventas, 3000D)
            Asiento(e, "E", New Date(2025, 2, 5), GastoLuz, Caja, 1200D)
            Dim gs As New GestionService(e.Ctx)
            gs.GenerarCierre()
            Assert.Equal(0D, Saldo(e, Ventas))
            Assert.Equal(0D, Saldo(e, GastoLuz))
            Assert.Equal(1800D, Saldo(e, "3.2.1.01.002"))   ' utilidad de la gestión
            Assert.Throws(Of InvalidOperationException)(Sub() gs.GenerarCierre())
            Dim bg = New LedgerService(e.Ctx).BalanceGeneral(New Date(2025, 12, 31), False, 99)
            Assert.True(bg.Cuadra)
            Assert.DoesNotContain(bg.Lineas, Function(l) l.Texto.StartsWith("Resultado del período"))
            ' gestión cerrada no admite cambios
            gs.CerrarGestion()
            Assert.Throws(Of InvalidOperationException)(Sub() Asiento(e, "I", New Date(2025, 3, 1), Caja, Ventas, 1D))
            gs.ReabrirGestion()
            Asiento(e, "I", New Date(2025, 3, 1), Caja, Ventas, 1D)
        End Using
    End Sub

    <Fact>
    Public Sub NuevaGestionTrasladaSaldosExistenciasCuentasYActivos()
        Using e As New Entorno()
            Dim prov = Cliente(e, "Prov", proveedor:=True)
            Dim cli = Cliente(e, "Cliente Uno")
            Dim it = ItemNuevo(e, "A1")
            Asiento(e, "AP", New Date(2025, 1, 1), Caja, Capital, 50000D, "Apertura")
            Compra(e, prov, it, 10D, 100D, tipo:="CRE")                        ' 1000 por pagar, inventario 870
            Dim v = Venta(e, cli, it, 4D, 250D, tipo:="CRE", aCuenta:=100D)     ' 1000 - 100 = 900 por cobrar
            ' activo fijo
            Dim afs As New ActivoFijoService(e.Ctx)
            Dim g = afs.Grupos().Rows.Cast(Of DataRow)().First(Function(r) r.GetS("Nombre") = "Equipo de Computación")
            Dim a As New ActivoDto With {.Codigo = "PC1", .Nombre = "PC", .GrupoId = g.GetI("Id"), .FechaAlta = New Date(2025, 1, 15), .ValorOriginal = 12000D}
            afs.AplicarGrupo(a)
            afs.Guardar(a, True, Cta(e, Capital))
            afs.Depreciar(New Date(2025, 1, 31), True)
            afs.Depreciar(New Date(2025, 2, 28), True)
            Dim led As New LedgerService(e.Ctx)
            Dim utilidad = led.ResultadoAl(New Date(2025, 12, 31))
            Dim invAntes = New InventarioService(e.Ctx).Stock(it)
            Dim gs As New GestionService(e.Ctx)
            Dim nuevaId = gs.AbrirNuevaGestion(New NuevaGestionOpciones With {.Anio = 2026, .CorrelativoMensual = True})
            Using nc = e.Sistema.AbrirContexto(e.Usuario, e.Ctx.Empresa.Id, nuevaId)
                Dim nl As New LedgerService(nc)
                Dim bg = nl.BalanceGeneral(New Date(2026, 12, 31), False, 99)
                Assert.True(bg.Cuadra, "Balance de la nueva gestión no cuadra: " & bg.Diferencia)
                ' el activo y el patrimonio de apertura coinciden con el cierre anterior
                Dim bgAnt = led.BalanceGeneral(New Date(2025, 12, 31), False, 99)
                Assert.Equal(bgAnt.Total1, bg.Total1)
                Assert.Equal(bgAnt.Total2, bg.Total2)
                ' cuentas de resultado empiezan en cero y la utilidad pasa a resultados acumulados
                Assert.Equal(0D, nl.SaldoCuenta(nc.CuentaPorCodigo(Ventas).GetI("Id"), New Date(2026, 12, 31)))
                Assert.Equal(62000D, nl.SaldoCuenta(nc.CuentaPorCodigo(Capital).GetI("Id"), New Date(2026, 12, 31)))   ' 50000 + 12000 aporte en especie
                Assert.Equal(utilidad, nl.SaldoCuenta(nc.CuentaPorCodigo("3.2.1.01.001").GetI("Id"), New Date(2026, 12, 31)))
                ' existencias
                Dim ni = New InventarioService(nc)
                Dim itNuevo = ni.BuscarItem("A1")
                Assert.Equal(invAntes, ni.Stock(itNuevo.Id))
                Assert.Equal(87D, ToDec(nc.Db.Scalar("SELECT CostoProm FROM Item WHERE Id=@i", "i", itNuevo.Id)))
                ' cuentas por cobrar y por pagar como documentos pendientes
                Dim nts As New TerceroService(nc)
                Dim cliN = nts.Listar("CXC").Rows.Cast(Of DataRow)().First(Function(r) r.GetS("Nombre") = "Cliente Uno")
                Assert.Equal(900D, nts.Saldo(cliN.GetI("Id"), "CXC"))
                Assert.Equal(1, nts.Pendientes(cliN.GetI("Id"), "CXC").Rows.Count)
                Dim provN = nts.Listar("CXP").Rows.Cast(Of DataRow)().First(Function(r) r.GetS("Nombre") = "Prov")
                Assert.Equal(1000D, nts.Saldo(provN.GetI("Id"), "CXP"))
                ' el cobro del saldo se contabiliza normalmente
                Dim cp As New CobroPagoService(nc)
                Dim d As New CobroPagoDto With {.TerceroId = cliN.GetI("Id"), .Clase = "CXC", .Fecha = New Date(2026, 1, 20)}
                d.Aplicaciones.Add(New AplicacionDoc With {.DocId = CInt(nts.Pendientes(cliN.GetI("Id"), "CXC").Rows(0)("Id")), .Monto = 900D})
                cp.Registrar(d)
                Assert.Equal(0D, nts.Saldo(cliN.GetI("Id"), "CXC"))
                ' activo fijo con valor y depreciación acumulada trasladados
                Dim afN = New ActivoFijoService(nc).Listar().Rows(0)
                Assert.Equal(12000D, afN.GetD("ValorOriginal"))
                Assert.Equal(500D, afN.GetD("DepAcumInicial"))
                Dim dep = New ActivoFijoService(nc).Depreciar(New Date(2026, 1, 31), False)
                Assert.Equal(250D, dep.Filas(0).DepPeriodo)
                Assert.Equal(750D, dep.Filas(0).DepAcum)
                ' correlativos de comprobantes reinician
                Assert.Equal(1, New VoucherService(nc).Cargar(nc.Db.ScalarInt("SELECT Id FROM Comprobante WHERE Origen='APE'")).Numero)
            End Using
            Assert.Equal(2, e.Sistema.ListarGestiones(e.Ctx.Empresa.Id).Rows.Count)
        End Using
    End Sub

    <Fact>
    Public Sub AjusteDeInflacionConUfvActualizaCuentasAjustables()
        Using e As New Entorno()
            Dim tc As New TipoCambioService(e.Ctx)
            tc.Guardar(New Date(2024, 12, 31), 6.96D, 2D)
            tc.Guardar(New Date(2025, 6, 30), 6.96D, 2.2D)
            tc.Guardar(New Date(2025, 12, 31), 6.96D, 2.4D)
            Asiento(e, "AP", New Date(2025, 1, 1), "1.2.1.01.001", Capital, 10000D, "Apertura")   ' terreno (ajustable) vs capital (ajustable)
            Asiento(e, "AP", New Date(2025, 1, 1), Caja, Capital, 5000D, "Caja inicial")
            Asiento(e, "T", New Date(2025, 6, 30), "1.2.1.01.002", Caja, 5000D)
            Dim gs As New GestionService(e.Ctx)
            Dim prev = gs.AjusteInflacion(New Date(2025, 12, 31), False)
            Assert.Equal(3, prev.Filas.Count)       ' terreno, edificio y capital (ajustables)
            ' terreno: 10000 x (2.4/2.0 - 1) = 2000 ; edificio: 5000 x (2.4/2.2 - 1) = 454.55
            Dim terreno = prev.Filas.First(Function(f) f.Codigo = "1.2.1.01.001")
            Assert.Equal(2000D, terreno.Ajuste)
            Dim edif = prev.Filas.First(Function(f) f.Codigo = "1.2.1.01.002")
            Assert.Equal(454.55D, edif.Ajuste)
            Assert.Equal(0D, Saldo(e, "4.2.1.01.005"))        ' vista previa no registra
            Dim r = gs.AjusteInflacion(New Date(2025, 12, 31), True)
            Assert.True(r.ComprobanteId > 0)
            Assert.Equal(12000D, Saldo(e, "1.2.1.01.001"))
            Assert.Equal(18000D, Saldo(e, Capital))                ' capital 15000 actualizado +20%
            Assert.Equal(545.45D, Saldo(e, "5.5.1.01.004"))        ' 3000 (capital) - 2000 (terreno) - 454.55 (edificio): el efectivo no se ajusta
            Assert.True(New LedgerService(e.Ctx).BalanceGeneral(New Date(2025, 12, 31), False, 99).Cuadra)
            Assert.Throws(Of InvalidOperationException)(Sub() gs.AjusteInflacion(New Date(2025, 12, 31), True))
        End Using
    End Sub

    <Fact>
    Public Sub AjusteDeInflacionExigeUfv()
        Using e As New Entorno()
            Asiento(e, "AP", New Date(2025, 1, 1), "1.2.1.01.001", Capital, 10000D, "Apertura")
            Dim gs As New GestionService(e.Ctx)
            Dim ex = Assert.Throws(Of InvalidOperationException)(Sub() gs.AjusteInflacion(New Date(2025, 12, 31), False))
            Assert.Contains("UFV", ex.Message)
        End Using
    End Sub

    <Fact>
    Public Sub DiferenciaDeCambioActualizaCuentasEnDolares()
        Using e As New Entorno()
            ' 1000 USD a 6.96 = 6960 Bs en caja M/E contra capital
            Asiento(e, "AP", New Date(2025, 1, 1), "1.1.1.01.002", Capital, 1000D, "Apertura USD", "USD")
            Assert.Equal(6960D, Saldo(e, "1.1.1.01.002"))
            Dim gs As New GestionService(e.Ctx)
            Dim r = gs.DiferenciaCambio(New Date(2025, 12, 31), 7D, True)
            Assert.Equal(40D, r.Total)                         ' 1000 x (7.00 - 6.96)
            Assert.Equal(7000D, Saldo(e, "1.1.1.01.002"))
            Assert.Equal(40D, Saldo(e, "4.2.1.01.004"))
            ' en dólares el saldo no cambia
            Dim led As New LedgerService(e.Ctx)
            Assert.Equal(1000D, led.SaldoCuenta(Cta(e, "1.1.1.01.002"), New Date(2025, 12, 31), True))
            Assert.True(led.BalanceGeneral(New Date(2025, 12, 31), False, 99).Cuadra)
        End Using
    End Sub
End Class
