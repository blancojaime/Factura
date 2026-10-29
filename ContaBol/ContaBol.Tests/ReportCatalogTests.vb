Imports System.Data
Imports System.IO
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Reports
Imports ContaBol.Core.Services
Imports Xunit

Public Class ReportCatalogTests

    ''' <summary>Crea datos de todos los módulos para ejercitar cada reporte.</summary>
    Private Function Poblar(e As Entorno) As Dictionary(Of String, Integer)
        Dim ids As New Dictionary(Of String, Integer)
        Dim tc As New TipoCambioService(e.Ctx)
        tc.Guardar(New Date(2025, 1, 1), 6.96D, 2D)
        tc.Guardar(New Date(2025, 3, 31), 6.96D, 2.1D)
        Asiento(e, "AP", New Date(2025, 1, 1), Caja, Capital, 50000D, "Apertura")
        Asiento(e, "AP", New Date(2025, 1, 1), Banco, Capital, 20000D, "Apertura banco")
        ids("comp") = Asiento(e, "E", New Date(2025, 1, 15), GastoLuz, Caja, 500D, "Pago de luz")
        Dim prov = Cliente(e, "Proveedor SA", proveedor:=True)
        Dim cli = Cliente(e, "Cliente Uno")
        ids("tercero") = cli
        ids("prov") = prov
        Dim it = ItemNuevo(e, "A1", venc:=True)
        ids("item") = it
        Compra(e, prov, it, 20D, 100D, venc:=New Date(2025, 4, 20), tipo:="CRE")
        Dim v = Venta(e, cli, it, 5D, 250D, tipo:="CRE", aCuenta:=200D)
        ids("venta") = v.Id
        ids("compra") = e.Ctx.Db.ScalarInt("SELECT MIN(Id) FROM Compra")
        ' activos y planilla
        Dim afs As New ActivoFijoService(e.Ctx)
        Dim g = afs.Grupos().Rows.Cast(Of DataRow)().First(Function(r) r.GetS("Nombre") = "Equipo de Computación")
        Dim a As New ActivoDto With {.Codigo = "PC1", .Nombre = "Computadora", .GrupoId = g.GetI("Id"), .FechaAlta = New Date(2025, 1, 10), .ValorOriginal = 12000D}
        afs.AplicarGrupo(a)
        afs.Guardar(a, True, Cta(e, Capital))
        afs.Depreciar(New Date(2025, 1, 31), True)
        Dim ps As New PlanillaService(e.Ctx)
        ids("emp") = ps.GuardarEmpleado(New EmpleadoDto With {.Nombre = "Ana Mamani", .Ci = "111", .FechaIngreso = New Date(2020, 1, 1), .Haber = 6000D, .Cargo = "Contadora"})
        ps.GuardarAnticipo(ids("emp"), New Date(2025, 1, 15), 300D, 300D, "adelanto")
        Dim per = ps.AbrirPeriodo(2025, 1)
        ps.Cerrar(per)
        ' producción
        Dim pr As New ProduccionService(e.Ctx)
        Dim prod = ItemNuevo(e, "PT1")
        Dim orden = pr.Abrir(New Date(2025, 2, 1), prod, 10D, Almacen(e), Almacen(e, "PROD"), "Lote de prueba")
        ids("orden") = orden
        Dim lm As New List(Of MovLine) From {New MovLine With {.ItemId = it, .Cantidad = 2D}}
        pr.ConsumirMateriaPrima(orden, New Date(2025, 2, 2), lm)
        pr.AgregarManoObra(orden, ids("emp"), 8D)
        pr.AgregarCif(orden, "Energía eléctrica", 150D)
        pr.Cerrar(orden, New Date(2025, 2, 20), 10D)
        ' presupuesto
        Dim cs As New CuentaService(e.Ctx)
        Dim luz = e.Ctx.CuentaPorCodigo(GastoLuz)
        cs.Guardar(New CuentaDto With {.Id = luz.GetI("Id"), .Codigo = GastoLuz, .Nombre = luz.GetS("Nombre"), .Presupuestable = True})
        Dim m(11) As Decimal
        For i = 0 To 11
            m(i) = 600D
        Next
        Dim psv As New PresupuestoService(e.Ctx)
        psv.Guardar(luz.GetI("Id"), m)
        ' banco y centro de costo
        e.Ctx.Db.Execute("INSERT INTO CentroCosto (Codigo, Nombre, Tipo, Activo) VALUES ('ADM', 'Administración', 'D', 1)")
        ' libro de ventas con factura
        Venta(e, cli, it, 1D, 300D, nroFac:="V2", fecha:=New Date(2025, 3, 20))
        ids("banco") = Cta(e, Banco)
        ids("caja") = Cta(e, Caja)
        Return ids
    End Function

    <Fact>
    Public Sub TodosLosReportesDelCatalogoGeneranPdfYExcel()
        Using e As New Entorno()
            Dim ids = Poblar(e)
            Dim fallos As New List(Of String)
            Dim n As Integer = 0
            For Each r In Catalogo.Todos
                Try
                    Dim vals = r.ValoresPorDefecto(e.Ctx)
                    vals("hasta") = New Date(2025, 12, 31)
                    vals("desde") = New Date(2025, 1, 1)
                    For Each pd In r.Params
                        Select Case pd.Tipo
                            Case ParamTipo.Cuenta : vals(pd.Clave) = ids("caja")
                            Case ParamTipo.CuentaBanco : vals(pd.Clave) = ids("banco")
                            Case ParamTipo.Tercero, ParamTipo.Cliente : vals(pd.Clave) = ids("tercero")
                            Case ParamTipo.Item : vals(pd.Clave) = ids("item")
                            Case ParamTipo.Orden : vals(pd.Clave) = ids("orden")
                            Case ParamTipo.Comprobante : vals(pd.Clave) = ids("comp")
                            Case ParamTipo.Proveedor : vals(pd.Clave) = ids("prov")
                        End Select
                    Next
                    If r.Id = "nota_venta" Then vals("id") = ids("venta")
                    If r.Id = "nota_compra" Then vals("id") = ids("compra")
                    If r.Id = "comprobantes_rango" Then
                        vals("mes") = 1
                        vals("tipo") = "E"
                    End If
                    If r.Id.Contains("planilla") OrElse r.Id = "boletas_pago" OrElse r.Id = "anticipos_sueldo" Then vals("mes") = 1
                    If r.Id = "depreciacion_periodo" Then vals("mes") = 1
                    If r.Id = "depreciacion_vista" Then vals("mes") = 2
                    If r.Id = "kardex_tercero" Then vals("clase") = "CXC"
                    Dim rep = r.Ejecutar(e.Ctx, vals)
                    Dim pdf = PdfExporter.GenerarBytes(rep)
                    If pdf.Length < 1500 Then Throw New Exception("PDF vacío")
                    Dim xl = Path.Combine(Path.GetTempPath(), "contabol_" & r.Id & ".xlsx")
                    ExcelExporter.Exportar(rep, xl)
                    File.WriteAllBytes(Path.Combine(Path.GetTempPath(), "contabol_" & r.Id & ".pdf"), pdf)
                    n += 1
                Catch ex As Exception
                    fallos.Add(r.Id & ": " & ex.GetType().Name & " - " & ex.Message & " @ " & If(ex.StackTrace Is Nothing, "", ex.StackTrace.Split(vbLf(0))(0).Trim()))
                End Try
            Next
            Assert.True(fallos.Count = 0, "Reportes con error:" & vbLf & String.Join(vbLf, fallos))
            Assert.True(n >= 50, "Se esperaban al menos 50 reportes, hay " & n)
        End Using
    End Sub
End Class
