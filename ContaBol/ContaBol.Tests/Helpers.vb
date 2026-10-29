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
