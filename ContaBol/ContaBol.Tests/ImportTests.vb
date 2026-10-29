Imports System.Data
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class FakeOrion
    Implements IOrionOrigen

    Public ReadOnly Tablas As New Dictionary(Of String, DataTable)(StringComparer.OrdinalIgnoreCase)

    Public Function Existe(archivo As String, tabla As String) As Boolean Implements IOrionOrigen.Existe
        Return Tablas.ContainsKey(archivo & "." & tabla)
    End Function

    Public Function Tabla(archivo As String, nombreTabla As String) As DataTable Implements IOrionOrigen.Tabla
        Return Tablas(archivo & "." & nombreTabla)
    End Function

    Public Shared Function Nueva(ParamArray cols() As String) As DataTable
        Dim dt As New DataTable()
        For Each c In cols
            dt.Columns.Add(c, GetType(Object))
        Next
        Return dt
    End Function
End Class

Public Class ImportTests

    Private Function Origen() As FakeOrion
        Dim o As New FakeOrion()
        Dim ofi = FakeOrion.Nueva("NOMBRES", "RUC", "DIRECCION", "GESTION", "piva", "pite", "CREDITO", "DEBITO", "IT", "ITXP", "antcli", "antpro", "cinve")
        ofi.Rows.Add("GMC S.R.L.", "131343022", "EL ALTO", "2025", 13, 3, "11205", "21402", "52101", "21401", "0", "0", "11301")
        o.Tablas("PRU.OFICINAS") = ofi
        Dim ct = FakeOrion.Nueva("CODIGO", "NOMBRE", "BS", "SUS", "PRESUPUESTO", "AJUSTABLE", "movi", "costo")
        ct.Rows.Add("1", "ACTIVO:", DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)
        ct.Rows.Add("11", "ACTIVO CORRIENTE:", DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)
        ct.Rows.Add("111", "ACTIVO DISPONIBLE:", DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)
        ct.Rows.Add("1110101", "Caja Moneda Nacional", " ", " ", DBNull.Value, "N", "S", DBNull.Value)
        ct.Rows.Add("1110103", "Caja Moneda Extranjera", " ", "SI", DBNull.Value, "S", "S", DBNull.Value)
        ct.Rows.Add("11205", "Credito Fiscal-IVA", "SI", DBNull.Value, DBNull.Value, "U", "S", DBNull.Value)
        ct.Rows.Add("11301", "Inventarios", DBNull.Value, DBNull.Value, DBNull.Value, "S", "S", DBNull.Value)
        ct.Rows.Add("2", "PASIVO:", DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)
        ct.Rows.Add("21402", ChrW(68) & "ebito Fiscal-IVA Ventas 13%", "SI", DBNull.Value, DBNull.Value, "U", "S", DBNull.Value)
        ct.Rows.Add("21401", "Impuesto a la Transacciones 3%", DBNull.Value, DBNull.Value, DBNull.Value, "U", "S", DBNull.Value)
        ct.Rows.Add("3", "PATRIMONIO NETO:", DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)
        ct.Rows.Add("311", "Capital Social ", "SI", DBNull.Value, DBNull.Value, DBNull.Value, "S", DBNull.Value)
        ct.Rows.Add("4", "CUENTAS DE INGRESO:", DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)
        ct.Rows.Add("41101", "Ingresos por Servicios", "SI", DBNull.Value, DBNull.Value, DBNull.Value, "S", DBNull.Value)
        ct.Rows.Add("5", "CUENTAS DE EGRESOS:", DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value, DBNull.Value)
        ct.Rows.Add("52101", "Servicio de Telefonia", "SI", DBNull.Value, DBNull.Value, DBNull.Value, "S", "F")
        o.Tablas("PRU.CUENTAS") = ct
        Dim tp = FakeOrion.Nueva("FECHA", "TCAMBIO")
        tp.Rows.Add(New Date(2025, 1, 2), 6.96)
        tp.Rows.Add(New Date(2025, 6, 4), 6.97)
        o.Tablas("PRU.TIPO") = tp
        Dim dr = FakeOrion.Nueva("FECHA", "TC", "NUMERO", "GLOSA", "DESCRIP", "NOMBRES", "DEBE", "HABER", "DEBESUS", "HASUS", "TCOM", "CHEQUE", "BANCO", "CODIGO", "glosa2", "MES")
        dr.Rows.Add(New Date(2025, 1, 2), 6.96, 1, DBNull.Value, DBNull.Value, "Caja", 1392, 0, 200, 0, "DIARIO", DBNull.Value, DBNull.Value, "1110101", "BALANCE INICIAL", "ENERO")
        dr.Rows.Add(New Date(2025, 1, 2), 6.96, 1, DBNull.Value, DBNull.Value, "Capital", 0, 1392, 0, 200, "DIARIO", DBNull.Value, DBNull.Value, "311", "BALANCE INICIAL", "ENERO")
        dr.Rows.Add(New Date(2025, 2, 10), 6.96, 1, DBNull.Value, "factura 15", "Caja", 1000, 0, 143.68, 0, "INGRESO", "123", "BNB", "1110101", "VENTA FEBRERO", "FEBRERO")
        dr.Rows.Add(New Date(2025, 2, 10), 6.96, 1, DBNull.Value, DBNull.Value, "DF", 0, 130, 0, 18.68, "INGRESO", "123", "BNB", "21402", "VENTA FEBRERO", "FEBRERO")
        dr.Rows.Add(New Date(2025, 2, 10), 6.96, 1, DBNull.Value, DBNull.Value, "Ventas", 0, 870, 0, 125, "INGRESO", "123", "BNB", "41101", "VENTA FEBRERO", "FEBRERO")
        ' comprobante descuadrado en Orion: se omite con aviso
        dr.Rows.Add(New Date(2025, 3, 1), 6.96, 2, DBNull.Value, DBNull.Value, "Caja", 100, 0, 0, 0, "EGRESO", DBNull.Value, DBNull.Value, "1110101", "ERROR", "MARZO")
        dr.Rows.Add(New Date(2025, 3, 1), 6.96, 2, DBNull.Value, DBNull.Value, "Tel", 0, 90, 0, 0, "EGRESO", DBNull.Value, DBNull.Value, "52101", "ERROR", "MARZO")
        ' cuenta inexistente
        dr.Rows.Add(New Date(2025, 3, 5), 6.96, 3, DBNull.Value, DBNull.Value, "X", 10, 0, 0, 0, "EGRESO", DBNull.Value, DBNull.Value, "99999", "ERROR2", "MARZO")
        o.Tablas("PRU.DIARIOS") = dr
        Dim cl = FakeOrion.Nueva("CODIGO", "NOMBRE", "RUC", "DIRECCION", "TELEFONO", "ACTIVIDAD", "limcre", "ESTADO")
        cl.Rows.Add("001", "Cliente Importado", "999", "Calle 1", "123", "Comercio", 25000, "ACTIVO")
        o.Tablas("ORION.cli") = cl
        Dim lista = FakeOrion.Nueva("item", "descripcion", "desabrev", "ven", "moneda", "util", "minima", "activo", "ingreso", "costo", "precioa", "preciob", "precioc", "preciod", "precioe", "preciof", "preciog")
        lista.Rows.Add("0001", "Producto uno", "P1", "NO", "BS", 20, 5, "11301", "41101", "52101", 12.5, 0, 0, 0, 0, 0, 0)
        o.Tablas("ORION.lista") = lista
        Dim comp = FakeOrion.Nueva("FACTURA", "FECHA", "RUC", "PROVEEDOR", "TOTAL", "ICE", "EXECENTOS", "CREDITO", "ALFA", "SUCU")
        comp.Rows.Add("777", New Date(2025, 2, 5), "555", "Proveedor X", 1130, 0, 0, 146.9, "AUT1", "0")
        o.Tablas("PRU.COMPRAS") = comp
        Return o
    End Function

    <Fact>
    Public Sub ImportaDatosDeOrion4AUnaNuevaEmpresa()
        Using e As New Entorno()
            Dim imp As New OrionImportService(e.Sistema)
            Dim r = imp.Importar(Origen(), "GMC", e.Usuario, True)
            Assert.Equal(16, r.Cuentas)
            Assert.Equal(2, r.Comprobantes)
            Assert.Equal(1, r.Terceros)
            Assert.Equal(1, r.Items)
            Assert.Equal(1, r.Facturas)
            Assert.Contains(r.Avisos, Function(a) a.Contains("no cuadra"))
            Assert.Contains(r.Avisos, Function(a) a.Contains("99999"))
            Using c = e.Sistema.AbrirContexto(e.Usuario, r.EmpresaId, r.GestionId)
                Assert.Equal("GMC S.R.L.", c.Param.Valor("EMP_NOMBRE"))
                Assert.Equal("13", c.Param.Valor("IVA_PCT"))
                Assert.Equal("11205", c.Param.Valor("CTA_CF_IVA"))
                Assert.Equal("1110103", c.CuentaPorCodigo("1110103").GetS("Codigo"))
                Assert.Equal("USD", c.CuentaPorCodigo("1110103").GetS("Moneda"))
                Assert.False(c.CuentaPorCodigo("1110103").GetF("Ajustable"))
                Assert.True(c.CuentaPorCodigo("11301").GetF("Ajustable"))
                Assert.Equal("Capital Social", c.CuentaPorCodigo("311").GetS("Nombre"))
                Assert.Equal("F", c.CuentaPorCodigo("52101").GetS("CostoTipo"))
                Assert.Equal(4, c.CuentaPorCodigo("1110101").GetI("Nivel"))   ' 1 > 11 > 111 > 1110101 (nivel según la jerarquía real)
                ' saldos
                Dim led As New LedgerService(c)
                Assert.Equal(2392D, led.SaldoCuenta(c.CuentaPorCodigo("1110101").GetI("Id"), New Date(2025, 12, 31)))
                Assert.Equal(130D, led.SaldoCuenta(c.CuentaPorCodigo("21402").GetI("Id"), New Date(2025, 12, 31)))
                ' importes en dólares conservados tal como estaban en Orion
                Assert.Equal(200D + 143.68D, led.SaldoCuenta(c.CuentaPorCodigo("1110101").GetI("Id"), New Date(2025, 12, 31), True))
                ' numeración conservada
                Dim vs As New VoucherService(c)
                Assert.True(vs.BuscarId("I", 1, 2) > 0)
                Assert.True(vs.BuscarId("T", 1, 1) > 0)
                Assert.True(led.BalanceGeneral(New Date(2025, 12, 31), False, 99).Cuadra)
                Assert.Equal(6.97D, New TipoCambioService(c).Dolar(New Date(2025, 8, 1)))
            End Using
        End Using
    End Sub

    <Fact>
    Public Sub NoImportaCarpetaInvalida()
        Using e As New Entorno()
            Dim imp As New OrionImportService(e.Sistema)
            Assert.Throws(Of InvalidOperationException)(Sub() imp.Importar(New FakeOrion(), "X", e.Usuario))
        End Using
    End Sub
End Class
