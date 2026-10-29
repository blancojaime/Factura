Namespace Domain

    Public Class VoucherLine
        Public Property CuentaId As Integer
        Public Property Glosa As String = ""
        ''' <summary>Importes en la moneda del comprobante.</summary>
        Public Property Debe As Decimal
        Public Property Haber As Decimal
        Public Property CentroCostoId As Integer
        Public Property TerceroId As Integer
        Public Property Cheque As String = ""

        ' Calculados al guardar / leer
        Public Property DebeBs As Decimal
        Public Property HaberBs As Decimal
        Public Property DebeUsd As Decimal
        Public Property HaberUsd As Decimal

        Public Shared Function Deb(cuentaId As Integer, monto As Decimal, Optional glosa As String = "") As VoucherLine
            Return New VoucherLine With {.CuentaId = cuentaId, .Debe = monto, .Glosa = glosa}
        End Function

        Public Shared Function Hab(cuentaId As Integer, monto As Decimal, Optional glosa As String = "") As VoucherLine
            Return New VoucherLine With {.CuentaId = cuentaId, .Haber = monto, .Glosa = glosa}
        End Function
    End Class

    ''' <summary>Factura a registrar en el libro de compras o ventas IVA junto con un comprobante.</summary>
    Public Class FacturaDto
        Public Property Id As Integer
        ''' <summary>C = compras, V = ventas</summary>
        Public Property Libro As String = "C"
        Public Property Fecha As Date = Date.MinValue
        Public Property NroFactura As String = ""
        Public Property Autorizacion As String = ""
        Public Property CodControl As String = ""
        Public Property Nit As String = ""
        Public Property RazonSocial As String = ""
        Public Property TerceroId As Integer
        Public Property ImporteTotal As Decimal
        ''' <summary>Importe no sujeto a crédito/débito fiscal (ICE, IEHD, IPJ, tasas, otros no sujetos al IVA).</summary>
        Public Property NoSujeto As Decimal
        Public Property Exento As Decimal
        Public Property TasaCero As Decimal
        Public Property Descuento As Decimal
        Public Property GiftCard As Decimal
        ''' <summary>Compras: V=válida. Ventas: V=válida, A=anulada, E=extraviada, N=no utilizada, C=contingencia.</summary>
        Public Property Estado As String = "V"
        Public Property TipoOp As String = ""
        Public Property Dui As String = ""
        Public Property Sucursal As String = "0"
        ' Calculados
        Public Property Subtotal As Decimal
        Public Property BaseCf As Decimal
        Public Property Impuesto As Decimal
        Public Property ComprobanteId As Integer
        Public Property Origen As String = "MAN"
        Public Property OrigenId As Integer
    End Class

    Public Class Voucher
        Public Property Id As Integer
        Public Property TipoCodigo As String = "T"
        Public Property TipoNombre As String = ""
        Public Property Numero As Integer
        Public Property Mes As Integer
        Public Property Fecha As Date = Date.Today
        Public Property TC As Decimal = 6.96D
        Public Property Moneda As String = "BS"
        Public Property Glosa As String = ""
        Public Property Referencia As String = ""
        Public Property Cheque As String = ""
        Public Property Banco As String = ""
        Public Property Estado As String = "V"
        Public Property Origen As String = "MAN"
        Public Property OrigenId As Integer
        Public Property Observacion As String = ""
        Public Property UsuarioId As Integer
        Public ReadOnly Property Lines As New List(Of VoucherLine)
        Public ReadOnly Property Facturas As New List(Of FacturaDto)

        Public ReadOnly Property TotalDebe As Decimal
            Get
                Return Lines.Sum(Function(l) l.Debe)
            End Get
        End Property
        Public ReadOnly Property TotalHaber As Decimal
            Get
                Return Lines.Sum(Function(l) l.Haber)
            End Get
        End Property
        Public ReadOnly Property Diferencia As Decimal
            Get
                Return TotalDebe - TotalHaber
            End Get
        End Property
        Public ReadOnly Property Cuadra As Boolean
            Get
                Return Math.Abs(Diferencia) < 0.005D
            End Get
        End Property
    End Class

End Namespace
