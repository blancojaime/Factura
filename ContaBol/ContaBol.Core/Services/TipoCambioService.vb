Imports ContaBol.Core.Common

Namespace Services

    ''' <summary>Tipos de cambio (USD) y UFV por fecha. Solo se cargan las fechas en que varían; se usa el último vigente.</summary>
    Public Class TipoCambioService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Public Function Dolar(fecha As Date) As Decimal
            Dim o As Object = _ctx.Db.Scalar("SELECT Usd FROM TipoCambio WHERE Fecha = (SELECT MAX(Fecha) FROM TipoCambio WHERE Fecha <= @f AND Usd > 0) AND Usd > 0", "f", fecha.Date)
            Dim v As Decimal = ToDec(o)
            If v <= 0 Then v = _ctx.Param.Dec(Domain.ParamKeys.TcDefecto, 6.96D)
            Return v
        End Function

        Public Function Ufv(fecha As Date) As Decimal
            Dim o As Object = _ctx.Db.Scalar("SELECT Ufv FROM TipoCambio WHERE Fecha = (SELECT MAX(Fecha) FROM TipoCambio WHERE Fecha <= @f AND Ufv > 0) AND Ufv > 0", "f", fecha.Date)
            Return ToDec(o)
        End Function

        ''' <summary>Existe un tipo de cambio cargado para la fecha exacta.</summary>
        Public Function Existe(fecha As Date) As Boolean
            Return _ctx.Db.ScalarInt("SELECT COUNT(*) FROM TipoCambio WHERE Fecha=@f", "f", fecha.Date) > 0
        End Function

        Public Sub Guardar(fecha As Date, usd As Decimal, ufv As Decimal)
            _ctx.Requiere("CONT.TIPOCAMBIO")
            If usd < 0 OrElse ufv < 0 Then Throw New ArgumentException("Los valores no pueden ser negativos.")
            If usd = 0 AndAlso ufv = 0 Then Throw New ArgumentException("Ingrese el tipo de cambio o la UFV.")
            Dim n As Integer = _ctx.Db.Execute("UPDATE TipoCambio SET Usd=@u, Ufv=@v WHERE Fecha=@f", "u", CDbl(usd), "v", CDbl(ufv), "f", fecha.Date)
            If n = 0 Then _ctx.Db.Execute("INSERT INTO TipoCambio (Fecha, Usd, Ufv) VALUES (@f, @u, @v)", "f", fecha.Date, "u", CDbl(usd), "v", CDbl(ufv))
            _ctx.Audit("Tipo de cambio", "TC_GUARDAR", fecha.ToString("dd/MM/yyyy") & " USD=" & usd & " UFV=" & ufv)
        End Sub

        Public Sub Eliminar(fecha As Date)
            _ctx.Requiere("CONT.TIPOCAMBIO")
            _ctx.Db.Execute("DELETE FROM TipoCambio WHERE Fecha=@f", "f", fecha.Date)
        End Sub

        Public Function Listar(Optional desde As Date? = Nothing, Optional hasta As Date? = Nothing) As DataTable
            Dim d As Date = If(desde, _ctx.Gestion.FechaInicio)
            Dim h As Date = If(hasta, _ctx.Gestion.FechaFin)
            Return _ctx.Db.Query("SELECT Fecha, Usd, Ufv FROM TipoCambio WHERE Fecha >= @d AND Fecha <= @h ORDER BY Fecha", "d", d.Date, "h", h.Date)
        End Function

        ''' <summary>Convierte un importe en la moneda dada a (Bs, USD) con redondeo contable.</summary>
        Public Shared Sub Convertir(importe As Decimal, moneda As String, tc As Decimal, ByRef bs As Decimal, ByRef usd As Decimal)
            If moneda = "USD" Then
                usd = importe.R2()
                bs = (importe * tc).R2()
            Else
                bs = importe.R2()
                usd = If(tc = 0D, 0D, (importe / tc).R2())
            End If
        End Sub
    End Class

End Namespace
