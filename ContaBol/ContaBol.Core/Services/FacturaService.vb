Imports System.Text
Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    ''' <summary>Libros de Compras y Ventas IVA (formato LCV del SIN) y asientos de crédito/débito fiscal e IT.</summary>
    Public Class FacturaService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Public ReadOnly Property IvaPct As Decimal
            Get
                Return _ctx.Param.Dec(ParamKeys.IvaPct, 13D)
            End Get
        End Property

        Public ReadOnly Property ItPct As Decimal
            Get
                Return _ctx.Param.Dec(ParamKeys.ItPct, 3D)
            End Get
        End Property

        ''' <summary>Calcula subtotal, base y crédito/débito fiscal. En Bolivia el IVA está incluido en el precio: impuesto = base × 13%.</summary>
        Public Sub Calcular(f As FacturaDto)
            If f.Estado <> "V" AndAlso f.Estado <> "C" AndAlso f.Libro = "V" Then
                f.ImporteTotal = 0D : f.NoSujeto = 0D : f.Exento = 0D : f.TasaCero = 0D : f.Descuento = 0D : f.GiftCard = 0D
                f.Subtotal = 0D : f.BaseCf = 0D : f.Impuesto = 0D
                Return
            End If
            f.Subtotal = (f.ImporteTotal - f.NoSujeto - f.Exento - f.TasaCero).R2()
            f.BaseCf = (f.Subtotal - f.Descuento - f.GiftCard).R2()
            If f.BaseCf < 0D Then f.BaseCf = 0D
            f.Impuesto = (f.BaseCf * IvaPct / 100D).R2()
        End Sub

        Private Sub Validar(f As FacturaDto)
            If f.Libro <> "C" AndAlso f.Libro <> "V" Then Throw New ArgumentException("Libro inválido.")
            If String.IsNullOrWhiteSpace(f.NroFactura) Then Throw New ArgumentException("Ingrese el número de factura.")
            If f.Fecha.Date < _ctx.Gestion.FechaInicio.Date OrElse f.Fecha.Date > _ctx.Gestion.FechaFin.Date Then
                Throw New ArgumentException("La fecha de la factura está fuera de la gestión.")
            End If
            If f.ImporteTotal < 0D Then Throw New ArgumentException("El importe total no puede ser negativo.")
            If f.Libro = "C" AndAlso f.ImporteTotal <= 0D Then Throw New ArgumentException("El importe total de la compra debe ser mayor a cero.")
            If f.NoSujeto + f.Exento + f.TasaCero > f.ImporteTotal Then Throw New ArgumentException("Los importes no sujetos/exentos superan el total de la factura.")
            If f.Descuento + f.GiftCard > f.Subtotal Then Throw New ArgumentException("Descuentos y gift card superan el subtotal.")
            If Duplicada(f) Then Throw New InvalidOperationException("La factura " & f.NroFactura & " ya fue registrada en el libro " & If(f.Libro = "C", "de compras", "de ventas") & ".")
        End Sub

        Public Function Duplicada(f As FacturaDto) As Boolean
            Dim sql As String = "SELECT COUNT(*) FROM FacturaIva WHERE Libro=@l AND NroFactura=@n AND Id <> @i"
            Dim args As New List(Of Object) From {"l", f.Libro, "n", f.NroFactura.Trim(), "i", f.Id}
            If f.Libro = "C" Then
                sql &= " AND Nit=@nit AND Autorizacion=@a"
                args.AddRange({"nit", If(f.Nit, "").Trim(), "a", If(f.Autorizacion, "").Trim()})
                ' Con autorización vacía se compara contra campos vacíos (NULL en Access): se consulta en memoria.
                If String.IsNullOrWhiteSpace(f.Autorizacion) OrElse String.IsNullOrWhiteSpace(f.Nit) Then
                    Dim dt As DataTable = _ctx.Db.Query("SELECT Nit, Autorizacion FROM FacturaIva WHERE Libro='C' AND NroFactura=@n AND Id <> @i", "n", f.NroFactura.Trim(), "i", f.Id)
                    For Each r As DataRow In dt.Rows
                        If r.GetS("Nit") = If(f.Nit, "").Trim() AndAlso r.GetS("Autorizacion") = If(f.Autorizacion, "").Trim() Then Return True
                    Next
                    Return False
                End If
            End If
            Return _ctx.Db.ScalarInt(sql, args.ToArray()) > 0
        End Function

        Public Function Registrar(f As FacturaDto) As Integer
            _ctx.Requiere(If(f.Libro = "C", "IVA.COMPRAS", "IVA.VENTAS"))
            Return RegistrarInterno(f)
        End Function

        Friend Function RegistrarInterno(f As FacturaDto) As Integer
            _ctx.RequiereGestionAbierta()
            Calcular(f)
            Validar(f)
            f.Id = _ctx.Db.Insert(
                "INSERT INTO FacturaIva (Libro, Fecha, Mes, NroFactura, Autorizacion, CodControl, Nit, RazonSocial, TerceroId, ImporteTotal, NoSujeto, Exento, TasaCero, Subtotal, Descuento, GiftCard, BaseCf, Impuesto, Estado, TipoOp, Dui, Sucursal, ComprobanteId, Origen, OrigenId, UsuarioId, Creado) " &
                "VALUES (@l, @f, @m, @nf, @au, @cc, @nit, @rs, @te, @it, @ns, @ex, @tc, @st, @de, @gc, @bc, @im, @es, @to, @du, @su, @co, @or, @oi, @us, @cr)",
                "l", f.Libro, "f", f.Fecha.Date, "m", f.Fecha.Month, "nf", f.NroFactura.Trim(), "au", f.Autorizacion, "cc", f.CodControl, "nit", f.Nit,
                "rs", f.RazonSocial, "te", OrNull(f.TerceroId), "it", f.ImporteTotal, "ns", f.NoSujeto, "ex", f.Exento, "tc", f.TasaCero, "st", f.Subtotal,
                "de", f.Descuento, "gc", f.GiftCard, "bc", f.BaseCf, "im", f.Impuesto, "es", f.Estado, "to", f.TipoOp, "du", f.Dui, "su", f.Sucursal,
                "co", f.ComprobanteId, "or", f.Origen, "oi", f.OrigenId, "us", _ctx.Usuario.Id, "cr", Date.Now)
            _ctx.Audit("Libros IVA", If(f.Libro = "C", "FACTURA_COMPRA", "FACTURA_VENTA"), f.NroFactura & " Bs " & f.ImporteTotal.ToString("N2"))
            Return f.Id
        End Function

        Public Sub Modificar(f As FacturaDto)
            _ctx.Requiere(If(f.Libro = "C", "IVA.COMPRAS", "IVA.VENTAS"))
            _ctx.RequiereGestionAbierta()
            If f.Id = 0 Then Throw New InvalidOperationException("Factura no registrada.")
            Calcular(f)
            Validar(f)
            _ctx.Db.Execute("UPDATE FacturaIva SET Fecha=@f, Mes=@m, NroFactura=@nf, Autorizacion=@au, CodControl=@cc, Nit=@nit, RazonSocial=@rs, TerceroId=@te, ImporteTotal=@it, NoSujeto=@ns, Exento=@ex, TasaCero=@tc, Subtotal=@st, Descuento=@de, GiftCard=@gc, BaseCf=@bc, Impuesto=@im, Estado=@es, TipoOp=@to, Dui=@du, Sucursal=@su WHERE Id=@i",
                            "f", f.Fecha.Date, "m", f.Fecha.Month, "nf", f.NroFactura.Trim(), "au", f.Autorizacion, "cc", f.CodControl, "nit", f.Nit, "rs", f.RazonSocial,
                            "te", OrNull(f.TerceroId), "it", f.ImporteTotal, "ns", f.NoSujeto, "ex", f.Exento, "tc", f.TasaCero, "st", f.Subtotal, "de", f.Descuento,
                            "gc", f.GiftCard, "bc", f.BaseCf, "im", f.Impuesto, "es", f.Estado, "to", f.TipoOp, "du", f.Dui, "su", f.Sucursal, "i", f.Id)
            _ctx.Audit("Libros IVA", "FACTURA_MOD", f.NroFactura)
        End Sub

        Public Sub Eliminar(id As Integer)
            Dim f As FacturaDto = Obtener(id)
            If f Is Nothing Then Return
            _ctx.Requiere(If(f.Libro = "C", "IVA.COMPRAS", "IVA.VENTAS"))
            _ctx.RequiereGestionAbierta()
            If f.ComprobanteId <> 0 Then
                Dim estado As String = _ctx.Db.ScalarStr("SELECT Estado FROM Comprobante WHERE Id=@i", "i", f.ComprobanteId)
                If estado = "V" Then Throw New InvalidOperationException("La factura pertenece a un comprobante vigente. Anule o modifique el comprobante, o use la opción 'Anular factura'.")
            End If
            _ctx.Db.Execute("DELETE FROM FacturaIva WHERE Id=@i", "i", id)
            _ctx.Audit("Libros IVA", "FACTURA_ELIM", f.NroFactura)
        End Sub

        Public Function Obtener(id As Integer) As FacturaDto
            Dim dt As DataTable = _ctx.Db.Query("SELECT * FROM FacturaIva WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Return Leer(dt.Rows(0))
        End Function

        Public Shared Function Leer(r As DataRow) As FacturaDto
            Return New FacturaDto With {
                .Id = r.GetI("Id"), .Libro = r.GetS("Libro"), .Fecha = r.GetDt("Fecha"), .NroFactura = r.GetS("NroFactura"),
                .Autorizacion = r.GetS("Autorizacion"), .CodControl = r.GetS("CodControl"), .Nit = r.GetS("Nit"), .RazonSocial = r.GetS("RazonSocial"),
                .TerceroId = r.GetI("TerceroId"), .ImporteTotal = r.GetD("ImporteTotal"), .NoSujeto = r.GetD("NoSujeto"), .Exento = r.GetD("Exento"),
                .TasaCero = r.GetD("TasaCero"), .Subtotal = r.GetD("Subtotal"), .Descuento = r.GetD("Descuento"), .GiftCard = r.GetD("GiftCard"),
                .BaseCf = r.GetD("BaseCf"), .Impuesto = r.GetD("Impuesto"), .Estado = r.GetS("Estado"), .TipoOp = r.GetS("TipoOp"), .Dui = r.GetS("Dui"),
                .Sucursal = r.GetS("Sucursal"), .ComprobanteId = r.GetI("ComprobanteId"), .Origen = r.GetS("Origen"), .OrigenId = r.GetI("OrigenId")}
        End Function

        Public Function Listar(libro As String, desde As Date, hasta As Date) As DataTable
            Return _ctx.Db.Query("SELECT * FROM FacturaIva WHERE Libro=@l AND Fecha >= @d AND Fecha <= @h ORDER BY Fecha, NroFactura", "l", libro, "d", desde.Date, "h", hasta.Date)
        End Function

        ''' <summary>Totales del período: (base, impuesto, importe total).</summary>
        Public Function Totales(libro As String, desde As Date, hasta As Date) As Tuple(Of Decimal, Decimal, Decimal)
            Dim dt As DataTable = Listar(libro, desde, hasta)
            Dim b As Decimal, i As Decimal, t As Decimal
            For Each r As DataRow In dt.Rows
                If r.GetS("Estado") = "A" AndAlso libro = "C" Then Continue For
                b += r.GetD("BaseCf") : i += r.GetD("Impuesto") : t += r.GetD("ImporteTotal")
            Next
            Return Tuple.Create(b, i, t)
        End Function

        ' ---------- Asientos ----------
        ''' <summary>Debe: gasto/activo por (total - crédito fiscal) y crédito fiscal. La contrapartida (caja/banco/proveedor) la agrega quien llama.</summary>
        Public Function LineasCompra(f As FacturaDto, cuentaGastoId As Integer, Optional glosa As String = "") As List(Of VoucherLine)
            Calcular(f)
            Dim l As New List(Of VoucherLine)
            Dim neto As Decimal = f.ImporteTotal - f.Impuesto
            l.Add(VoucherLine.Deb(cuentaGastoId, neto, glosa))
            If f.Impuesto > 0D Then l.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaCreditoFiscal), f.Impuesto, glosa))
            Return l
        End Function

        ''' <summary>Haber: ingreso por (total - débito fiscal) y débito fiscal. La contrapartida (caja/clientes) la agrega quien llama.</summary>
        Public Function LineasVenta(f As FacturaDto, cuentaIngresoId As Integer, Optional glosa As String = "") As List(Of VoucherLine)
            Calcular(f)
            Dim l As New List(Of VoucherLine)
            l.Add(VoucherLine.Hab(cuentaIngresoId, f.ImporteTotal - f.Impuesto, glosa))
            If f.Impuesto > 0D Then l.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaDebitoFiscal), f.Impuesto, glosa))
            Return l
        End Function

        ''' <summary>Devengamiento del IT sobre un importe de venta: Debe gasto IT / Haber IT por pagar.</summary>
        Public Function LineasIt(importeVenta As Decimal, Optional glosa As String = "") As List(Of VoucherLine)
            Dim l As New List(Of VoucherLine)
            Dim it As Decimal = (importeVenta * ItPct / 100D).R2()
            If it > 0D Then
                l.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaItGasto), it, glosa))
                l.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaItPagar), it, glosa))
            End If
            Return l
        End Function

        ' ---------- Exportación ----------
        ''' <summary>Genera el archivo CSV (separador ;) de compras o ventas del mes para carga en el sistema del SIN / Excel.</summary>
        Public Function ExportarCsv(libro As String, mes As Integer) As String
            Dim d As Date = New Date(_ctx.Gestion.Anio, 1, 1)
            Dim rango As Tuple(Of Date, Date) = RangoMes(mes)
            Dim dt As DataTable = Listar(libro, rango.Item1, rango.Item2)
            Dim sb As New StringBuilder()
            If libro = "C" Then
                sb.AppendLine("ESPECIFICACION;N;NIT PROVEEDOR;RAZON SOCIAL;CODIGO AUTORIZACION;NUMERO FACTURA;NUMERO DUI/DIM;FECHA FACTURA;IMPORTE TOTAL COMPRA;IMPORTE NO SUJETO A CF;SUBTOTAL;DESCUENTOS;IMPORTE GIFT CARD;IMPORTE BASE CF;CREDITO FISCAL;TIPO COMPRA;CODIGO CONTROL")
            Else
                sb.AppendLine("ESPECIFICACION;N;FECHA FACTURA;NUMERO FACTURA;CODIGO AUTORIZACION;NIT/CI CLIENTE;NOMBRE O RAZON SOCIAL;IMPORTE TOTAL VENTA;IMPORTE NO SUJETO IVA;EXPORTACIONES Y EXENTAS;TASA CERO;SUBTOTAL;DESCUENTOS;IMPORTE GIFT CARD;IMPORTE BASE DEBITO FISCAL;DEBITO FISCAL;ESTADO;CODIGO CONTROL")
            End If
            Dim n As Integer = 0
            For Each r As DataRow In dt.Rows
                n += 1
                Dim f As FacturaDto = Leer(r)
                If libro = "C" Then
                    sb.AppendLine(String.Join(";", {If(libro = "C", "2", "1"), n.ToString(), f.Nit, Limpia(f.RazonSocial), f.Autorizacion, f.NroFactura, f.Dui, f.Fecha.ToString("dd/MM/yyyy"),
                        Num(f.ImporteTotal), Num(f.NoSujeto), Num(f.Subtotal), Num(f.Descuento), Num(f.GiftCard), Num(f.BaseCf), Num(f.Impuesto), If(f.TipoOp = "", "1", f.TipoOp), f.CodControl}))
                Else
                    sb.AppendLine(String.Join(";", {"3", n.ToString(), f.Fecha.ToString("dd/MM/yyyy"), f.NroFactura, f.Autorizacion, f.Nit, Limpia(f.RazonSocial), Num(f.ImporteTotal), Num(f.NoSujeto),
                        Num(f.Exento), Num(f.TasaCero), Num(f.Subtotal), Num(f.Descuento), Num(f.GiftCard), Num(f.BaseCf), Num(f.Impuesto), f.Estado, f.CodControl}))
                End If
            Next
            Return sb.ToString()
        End Function

        Private Shared Function Num(d As Decimal) As String
            Return d.ToString("0.00", Inv)
        End Function

        Private Shared Function Limpia(s As String) As String
            Return If(s, "").Replace(";", ",").Replace(vbCr, " ").Replace(vbLf, " ")
        End Function

        Public Function RangoMes(mes As Integer) As Tuple(Of Date, Date)
            ' Mes calendario dentro de la gestión (la gestión puede iniciar en abril, etc.)
            Dim anio As Integer = If(mes >= _ctx.Gestion.FechaInicio.Month, _ctx.Gestion.FechaInicio.Year, _ctx.Gestion.FechaInicio.Year + 1)
            Dim ini As New Date(anio, mes, 1)
            Return Tuple.Create(ini, FinDeMes(ini))
        End Function

    End Class

End Namespace
