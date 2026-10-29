Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class PlanillaTests

    <Fact>
    Public Sub BonoDeAntiguedadSegunEscala()
        Assert.Equal(0D, PlanillaService.PorcentajeAntiguedad(1))
        Assert.Equal(5D, PlanillaService.PorcentajeAntiguedad(2))
        Assert.Equal(11D, PlanillaService.PorcentajeAntiguedad(5))
        Assert.Equal(18D, PlanillaService.PorcentajeAntiguedad(8))
        Assert.Equal(26D, PlanillaService.PorcentajeAntiguedad(11))
        Assert.Equal(34D, PlanillaService.PorcentajeAntiguedad(15))
        Assert.Equal(42D, PlanillaService.PorcentajeAntiguedad(20))
        Assert.Equal(50D, PlanillaService.PorcentajeAntiguedad(30))
        Assert.Equal(4, PlanillaService.AniosCumplidos(New Date(2020, 6, 15), New Date(2025, 6, 14)))
        Assert.Equal(5, PlanillaService.AniosCumplidos(New Date(2020, 6, 15), New Date(2025, 6, 15)))
    End Sub

    <Fact>
    Public Sub CalculaSueldoConAfpYRcIva()
        Using e As New Entorno()
            Dim ps As New PlanillaService(e.Ctx)
            Dim f As New FilaPlanilla With {.HaberBasico = 20000D, .FechaIngreso = New Date(2020, 1, 1), .Dias = 30}
            ps.Calcular(f, New Date(2025, 1, 31), 2500D)
            Assert.Equal(20000D, f.Haber)
            Assert.Equal(825D, f.BonoAntig)                  ' 3 x 2500 x 11%
            Assert.Equal(20825D, f.TotalGanado)
            Assert.Equal(2082.5D, f.AfpVejez)
            Assert.Equal(2646.9D, Math.Round(f.AfpVejez + f.AfpRiesgo + f.AfpComision + f.AfpSolidario, 1))   ' 12.71%
            Assert.Equal(78.25D, f.Ans)                      ' 1% de (20825 - 13000)
            Assert.Equal(f.TotalGanado - f.TotalAfp, f.IngresoNeto)
            Assert.Equal(10000D, f.MinimoNoImp)              ' 4 x SMN
            Assert.Equal(f.IngresoNeto - 10000D, f.BaseImponible)
            Assert.Equal((f.BaseImponible * 0.13D).R2(), f.RcIvaBruto)
            Assert.Equal(650D, f.Cred2Smn)                   ' 13% de 2 SMN
            Assert.Equal(f.RcIvaBruto - 650D, f.RcIvaRet)
            Assert.Equal(f.TotalGanado - f.TotalAfp - f.RcIvaRet, f.Liquido)
            Assert.Equal(2082.5D, f.PatCns - 0D)             ' 10% patronal CNS
            ' facturas F-110 que superan el impuesto generan saldo a favor
            f.Facturas = 100000D
            ps.Calcular(f, New Date(2025, 1, 31), 2500D)
            Assert.Equal(0D, f.RcIvaRet)
            Assert.True(f.SaldoSiguiente > 0D)
            ' sueldo bajo: sin RC-IVA
            Dim g As New FilaPlanilla With {.HaberBasico = 3000D, .FechaIngreso = New Date(2024, 1, 1), .Dias = 15}
            ps.Calcular(g, New Date(2025, 1, 31), 2500D)
            Assert.Equal(1500D, g.Haber)
            Assert.Equal(0D, g.BaseImponible)
            Assert.Equal(0D, g.RcIvaRet)
        End Using
    End Sub

    <Fact>
    Public Sub PlanillaCierraGeneraAsientoCuadrado()
        Using e As New Entorno()
            Dim ps As New PlanillaService(e.Ctx)
            ps.GuardarEmpleado(New EmpleadoDto With {.Nombre = "Ana Mamani", .Ci = "111", .FechaIngreso = New Date(2020, 1, 1), .Haber = 5000D})
            ps.GuardarEmpleado(New EmpleadoDto With {.Nombre = "Luis Quispe", .Ci = "222", .FechaIngreso = New Date(2024, 3, 1), .Haber = 20000D})
            ps.GuardarAnticipo(1, New Date(2025, 1, 15), 500D, 500D, "anticipo")
            Dim per = ps.AbrirPeriodo(2025, 1)
            Dim filas = ps.Filas(per.Id)
            Assert.Equal(2, filas.Count)
            Assert.Equal(500D, filas.First(Function(x) x.Nombre = "Ana Mamani").Anticipo)
            Dim vid = ps.Cerrar(per)
            Assert.True(vid > 0)
            Dim tot = filas.Sum(Function(x) x.TotalGanado)
            Assert.Equal(filas.Sum(Function(x) x.Liquido), Saldo(e, "2.1.3.01.001"))
            Assert.Equal(filas.Sum(Function(x) x.TotalAfp), Saldo(e, "2.1.3.01.002"))
            Assert.Equal(filas.Sum(Function(x) x.PatCns), Saldo(e, "2.1.3.01.004"))
            Assert.Equal(-500D, Saldo(e, "1.1.2.02.002"))     ' anticipo descontado (acredita el activo)
            Assert.Equal(tot / 12D, Saldo(e, "2.1.3.02.001"), 1)   ' provisión aguinaldo
            Assert.True(New LedgerService(e.Ctx).BalanceGeneral(New Date(2025, 12, 31), False, 99).Cuadra)
            ' no se puede editar una planilla cerrada
            Assert.Throws(Of InvalidOperationException)(Sub() ps.GuardarFila(ps.ObtenerPeriodo(2025, 1), filas(0)))
            ps.Reabrir(ps.ObtenerPeriodo(2025, 1))
            Assert.Equal(0D, Saldo(e, "2.1.3.01.001"))
            ' febrero toma el saldo RC-IVA del mes anterior
            Dim p2 = ps.AbrirPeriodo(2025, 2)
            Assert.Equal(2, ps.Filas(p2.Id).Count)
        End Using
    End Sub

    <Fact>
    Public Sub RequiereSalarioMinimoConfigurado()
        Using e As New Entorno()
            e.Ctx.Param.Guardar(ParamKeys.Smn, "0")
            Dim ps As New PlanillaService(e.Ctx)
            ps.GuardarEmpleado(New EmpleadoDto With {.Nombre = "X", .Haber = 1000D, .FechaIngreso = New Date(2020, 1, 1)})
            Assert.Throws(Of InvalidOperationException)(Sub() ps.AbrirPeriodo(2025, 1))
        End Using
    End Sub
End Class
