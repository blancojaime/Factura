Imports System.Data
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class ActivosFijosTests

    Private Function NuevoActivo(e As Entorno, Optional valor As Decimal = 12000D, Optional grupoNombre As String = "Equipo de Computación", Optional alta As Date = Nothing) As Integer
        Dim afs As New ActivoFijoService(e.Ctx)
        Dim g = afs.Grupos().Rows.Cast(Of DataRow).First(Function(r) r.GetS("Nombre") = grupoNombre)
        Dim a As New ActivoDto With {.Codigo = "PC01", .Nombre = "Computadora", .GrupoId = g.GetI("Id"), .FechaAlta = If(alta = Nothing, New Date(2025, 1, 10), alta), .ValorOriginal = valor}
        afs.AplicarGrupo(a)
        Return afs.Guardar(a, True, Cta(e, Caja))
    End Function

    <Fact>
    Public Sub AltaGeneraAsientoYDepreciaSegunPorcentajeDelGrupo()
        Using e As New Entorno()
            Dim id = NuevoActivo(e)
            Assert.Equal(12000D, Saldo(e, "1.2.1.01.005"))
            Dim afs As New ActivoFijoService(e.Ctx)
            Dim r = afs.Depreciar(New Date(2025, 1, 31), True)
            Assert.Single(r.Filas)
            Assert.Equal(250D, r.Filas(0).DepPeriodo)       ' 12000 x 25% / 12
            Assert.True(r.UfvFaltante)                        ' sin UFV no se actualiza pero se deprecia
            Assert.Equal(250D, Saldo(e, "5.3.1.04.005"))
            Assert.Equal(250D, Saldo(e, "1.2.1.02.005"))
            ' mismo período no se repite
            Assert.Empty(afs.Depreciar(New Date(2025, 1, 31), True).Filas)
            afs.Depreciar(New Date(2025, 2, 28), True)
            Assert.Equal(500D, Saldo(e, "1.2.1.02.005"))
            Dim cuadro = afs.Cuadro(New Date(2025, 2, 28))
            Assert.Equal(11500D, CDec(cuadro.Rows(0)("ValorNeto")))
        End Using
    End Sub

    <Fact>
    Public Sub ActualizaPorUfvValorYDepreciacionAcumulada()
        Using e As New Entorno()
            Dim tc As New TipoCambioService(e.Ctx)
            tc.Guardar(New Date(2025, 1, 1), 6.96D, 2D)        ' UFV al alta
            tc.Guardar(New Date(2025, 1, 31), 6.96D, 2.1D)     ' +5%
            Dim id = NuevoActivo(e)
            Dim afs As New ActivoFijoService(e.Ctx)
            Dim r = afs.Depreciar(New Date(2025, 1, 31), True)
            Dim f = r.Filas(0)
            Assert.False(r.UfvFaltante)
            Assert.Equal(12600D, f.ValorActualizado)          ' 12000 x 2.1/2.0
            Assert.Equal(600D, f.ActualizaValor)
            Assert.Equal(262.5D, f.DepPeriodo)                ' 12600 x 25% / 12
            Assert.Equal(12600D, Saldo(e, "1.2.1.01.005"))
            Assert.Equal(262.5D, Saldo(e, "1.2.1.02.005"))
            Assert.Equal(600D, Saldo(e, "4.2.1.01.005"))      ' ajuste por inflación (ingreso)
            ' segundo mes sin variación de UFV
            tc.Guardar(New Date(2025, 2, 28), 6.96D, 2.1D)
            Dim r2 = afs.Depreciar(New Date(2025, 2, 28), True)
            Assert.Equal(0D, r2.Filas(0).ActualizaValor)
            Assert.Equal(525D, r2.Filas(0).DepAcum)
            ' el balance general cuadra con los asientos
            Assert.True(New LedgerService(e.Ctx).BalanceGeneral(New Date(2025, 12, 31), False, 99).Cuadra)
            ' solo puede anularse el último período
            Assert.Throws(Of InvalidOperationException)(Sub() afs.AnularDepreciacion("2025-01"))
            afs.AnularDepreciacion("2025-02")
            Assert.Equal(262.5D, Saldo(e, "1.2.1.02.005"))
        End Using
    End Sub

    <Fact>
    Public Sub TerrenoNoSeDeprecia_YBajaDelActivo()
        Using e As New Entorno()
            Dim afs As New ActivoFijoService(e.Ctx)
            Dim a As New ActivoDto With {.Codigo = "TER1", .Nombre = "Terreno", .CuentaActivoId = Cta(e, "1.2.1.01.001"), .CuentaDepAcumId = Cta(e, "1.2.1.02.002"), .CuentaGastoId = Cta(e, "5.3.1.04.002"), .FechaAlta = New Date(2025, 1, 1), .ValorOriginal = 50000D, .PorcDep = 0D}
            afs.Guardar(a, True, Cta(e, Capital))
            Assert.Equal(0D, afs.Depreciar(New Date(2025, 1, 31), True).Filas(0).DepPeriodo)
            Dim id2 = NuevoActivo(e)
            afs.Depreciar(New Date(2025, 1, 31), True)
            afs.Baja(id2, New Date(2025, 2, 15), "venta de equipo")
            Assert.Equal(0D, Saldo(e, "1.2.1.01.005"))
            Assert.Equal(0D, Saldo(e, "1.2.1.02.005"))
            Assert.Equal(11750D, Saldo(e, "5.6.1.01.002"))    ' pérdida por baja = valor neto
            Assert.Equal(1, afs.Listar().Rows.Count)           ' queda solo el terreno vigente
        End Using
    End Sub

    <Fact>
    Public Sub AltaConFacturaSeparaCreditoFiscal()
        Using e As New Entorno()
            Dim afs As New ActivoFijoService(e.Ctx)
            Dim g = afs.Grupos().Rows.Cast(Of DataRow).First(Function(r) r.GetS("Nombre") = "Vehículos")
            Dim a As New ActivoDto With {.Codigo = "VEH1", .Nombre = "Camioneta", .GrupoId = g.GetI("Id"), .FechaAlta = New Date(2025, 3, 1), .ValorOriginal = 100000D}
            afs.AplicarGrupo(a)
            afs.Guardar(a, True, Cta(e, Banco), New FacturaDto With {.NroFactura = "55", .Nit = "1", .Autorizacion = "A"})
            Assert.Equal(87000D, Saldo(e, "1.2.1.01.006"))
            Assert.Equal(13000D, Saldo(e, "1.1.2.03.001"))
            Assert.Equal(-100000D, Saldo(e, Banco))
        End Using
    End Sub
End Class
