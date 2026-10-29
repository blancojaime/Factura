Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

Public Module Helpers

    Public Function Cta(e As Entorno, codigo As String) As Integer
        Dim r = e.Ctx.CuentaPorCodigo(codigo)
        If r Is Nothing Then Throw New Exception("Cuenta no existe: " & codigo)
        Return CInt(r("Id"))
    End Function

    ''' <summary>Crea y guarda un comprobante simple de dos cuentas.</summary>
    Public Function Asiento(e As Entorno, tipo As String, fecha As Date, debeCod As String, haberCod As String, monto As Decimal, Optional glosa As String = "prueba", Optional moneda As String = "BS") As Integer
        Dim vs As New VoucherService(e.Ctx)
        Dim v = vs.Nuevo(tipo, fecha)
        v.Moneda = moneda
        v.Glosa = glosa
        v.Lines.Add(VoucherLine.Deb(Cta(e, debeCod), monto))
        v.Lines.Add(VoucherLine.Hab(Cta(e, haberCod), monto))
        Return vs.Guardar(v)
    End Function

    Public Const Caja As String = "1.1.1.01.001"
    Public Const Capital As String = "3.1.1.01.001"
    Public Const Ventas As String = "4.1.1.01.001"
    Public Const GastoLuz As String = "5.3.1.02.001"
    Public Const Banco As String = "1.1.1.02.001"
End Module

Public Module Fabrica
    Public Function Cliente(e As Entorno, Optional nombre As String = "Cliente Uno", Optional limite As Decimal = 0D, Optional proveedor As Boolean = False) As Integer
        Dim ts As New TerceroService(e.Ctx)
        Return ts.Guardar(New TerceroDto With {.Nombre = nombre, .Nit = "123", .EsCliente = Not proveedor, .EsProveedor = proveedor, .LimiteCredito = limite})
    End Function

    Public Function ItemNuevo(e As Entorno, codigo As String, Optional venc As Boolean = False, Optional servicio As Boolean = False) As Integer
        Dim inv As New InventarioService(e.Ctx)
        Return inv.GuardarItem(New ItemDto With {.Codigo = codigo, .Descripcion = "Item " & codigo, .ManejaVenc = venc, .EsServicio = servicio, .UtilidadPct = 20D})
    End Function

    Public Function Almacen(e As Entorno, Optional codigo As String = "ALM01") As Integer
        Return CInt(e.Ctx.Db.Scalar("SELECT Id FROM Almacen WHERE Codigo=@c", "c", codigo))
    End Function

    Public Function Fac(nro As String, Optional nit As String = "999") As FacturaDto
        Return New FacturaDto With {.NroFactura = nro, .Nit = nit, .Autorizacion = "A" & nro}
    End Function

    Public Function Compra(e As Entorno, prov As Integer, item As Integer, cant As Decimal, precio As Decimal, Optional factura As Boolean = True, Optional tipo As String = "CON", Optional fecha As Date = Nothing, Optional venc As Date? = Nothing, Optional nroFac As String = "C1") As DocumentoResultado
        Dim d As New DocumentoDto With {.Tipo = tipo, .Fecha = If(fecha = Nothing, New Date(2025, 3, 1), fecha), .TerceroId = prov, .AlmacenId = Almacen(e), .TC = 6.96D, .ConFactura = factura}
        If factura Then d.Factura = Fac(nroFac)
        d.Lines.Add(New DocLine With {.ItemId = item, .Cantidad = cant, .PrecioUnit = precio, .FechaVenc = venc})
        Return New CompraService(e.Ctx).Registrar(d)
    End Function

    Public Function Venta(e As Entorno, cli As Integer, item As Integer, cant As Decimal, precio As Decimal, Optional factura As Boolean = True, Optional tipo As String = "CON", Optional fecha As Date = Nothing, Optional aCuenta As Decimal = 0D, Optional nroFac As String = "V1") As DocumentoResultado
        Dim d As New DocumentoDto With {.Tipo = tipo, .Fecha = If(fecha = Nothing, New Date(2025, 3, 5), fecha), .TerceroId = cli, .AlmacenId = Almacen(e), .TC = 6.96D, .ConFactura = factura, .ACuenta = aCuenta}
        If factura Then d.Factura = Fac(nroFac)
        d.Lines.Add(New DocLine With {.ItemId = item, .Cantidad = cant, .PrecioUnit = precio})
        Return New VentaService(e.Ctx).Registrar(d)
    End Function

    Public Function Saldo(e As Entorno, codigo As String, Optional hasta As Date = Nothing) As Decimal
        Return New LedgerService(e.Ctx).SaldoCuenta(Cta(e, codigo), If(hasta = Nothing, New Date(2025, 12, 31), hasta))
    End Function
End Module
