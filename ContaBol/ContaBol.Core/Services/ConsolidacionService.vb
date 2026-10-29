Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain

Namespace Services

    Public Class GestionConsolidable
        Public Property EmpresaId As Integer
        Public Property GestionId As Integer
        Public Property Empresa As String
        Public Property Anio As Integer
        Public Overrides Function ToString() As String
            Return Empresa & " - " & Anio
        End Function
    End Class

    ''' <summary>Consolidación de varias empresas/gestiones: suma los saldos por código de cuenta (se recomienda el mismo plan de cuentas).</summary>
    Public Class ConsolidacionService
        Private ReadOnly _sis As SistemaService
        Private ReadOnly _usuario As UsuarioInfo

        Public Sub New(sis As SistemaService, usuario As UsuarioInfo)
            _sis = sis
            _usuario = usuario
        End Sub

        Public Function Disponibles() As List(Of GestionConsolidable)
            Dim res As New List(Of GestionConsolidable)
            For Each e As DataRow In _sis.EmpresasDeUsuario(_usuario).Rows
                For Each g As DataRow In _sis.ListarGestiones(e.GetI("Id")).Rows
                    res.Add(New GestionConsolidable With {.EmpresaId = e.GetI("Id"), .GestionId = g.GetI("Id"), .Empresa = e.GetS("RazonSocial"), .Anio = g.GetI("Anio")})
                Next
            Next
            Return res
        End Function

        ''' <summary>Balance de sumas y saldos consolidado de las gestiones indicadas en el rango de fechas.</summary>
        Public Function Balance(seleccion As IEnumerable(Of GestionConsolidable), desde As Date, hasta As Date, usd As Boolean, nivelMax As Integer) As List(Of BalanceRow)
            Dim lista As List(Of GestionConsolidable) = seleccion.ToList()
            If lista.Count < 2 Then Throw New InvalidOperationException("Seleccione al menos dos empresas/gestiones para consolidar.")
            Dim acum As New Dictionary(Of String, BalanceRow)(StringComparer.OrdinalIgnoreCase)
            For Each g In lista
                Using c As Contexto = _sis.AbrirContexto(_usuario, g.EmpresaId, g.GestionId)
                    c.Requiere("CONT.CONSOLIDAR")
                    Dim desdeG As Date = If(desde < c.Gestion.FechaInicio, c.Gestion.FechaInicio, desde)
                    For Each b In New LedgerService(c).Balance(desdeG, hasta, usd, 99, True)
                        Dim x As BalanceRow = Nothing
                        If Not acum.TryGetValue(b.Codigo, x) Then
                            x = New BalanceRow With {.Codigo = b.Codigo, .Nombre = b.Nombre, .Nivel = b.Nivel, .Rubro = b.Rubro, .Naturaleza = b.Naturaleza, .EsMovimiento = b.EsMovimiento}
                            acum(b.Codigo) = x
                        End If
                        Dim antNeto As Decimal = (x.AntD - x.AntH) + (b.AntD - b.AntH)
                        x.AntD = If(antNeto > 0D, antNeto, 0D)
                        x.AntH = If(antNeto < 0D, -antNeto, 0D)
                        x.Debe += b.Debe
                        x.Haber += b.Haber
                        Dim fin As Decimal = (x.SaldoD - x.SaldoH) + (b.SaldoD - b.SaldoH)
                        x.SaldoD = If(fin > 0D, fin, 0D)
                        x.SaldoH = If(fin < 0D, -fin, 0D)
                    Next
                End Using
            Next
            Return acum.Values.Where(Function(b) b.Nivel <= nivelMax).OrderBy(Function(b) b.Codigo, StringComparer.Ordinal).ToList()
        End Function
    End Class

End Namespace
