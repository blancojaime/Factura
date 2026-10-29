Imports ContaBol.Core.Common
Imports ContaBol.Core.Data

Namespace Services

    ''' <summary>Parámetros de la gestión (tabla Parametro) con caché en memoria.</summary>
    Public Class Parametros
        Private ReadOnly _db As Database
        Private ReadOnly _cache As New Dictionary(Of String, String)(StringComparer.OrdinalIgnoreCase)

        Public Sub New(db As Database)
            _db = db
            Recargar()
        End Sub

        Public Sub Recargar()
            _cache.Clear()
            For Each r As DataRow In _db.Query("SELECT Clave, Valor FROM Parametro").Rows
                _cache(r.GetS("Clave")) = r.GetS("Valor")
            Next
        End Sub

        Public Function Valor(clave As String, Optional defecto As String = "") As String
            Dim v As String = Nothing
            If _cache.TryGetValue(clave, v) Then Return v
            Return defecto
        End Function

        Public Function Dec(clave As String, Optional defecto As Decimal = 0D) As Decimal
            Dim v As String = Valor(clave, "")
            If v = "" Then Return defecto
            Return ToDec(v)
        End Function

        Public Function Entero(clave As String, Optional defecto As Integer = 0) As Integer
            Dim v As String = Valor(clave, "")
            If v = "" Then Return defecto
            Return ToInt(v)
        End Function

        Public Function Bool(clave As String, Optional defecto As Boolean = False) As Boolean
            Dim v As String = Valor(clave, "")
            If v = "" Then Return defecto
            Return ToFlag(v)
        End Function

        Public Sub Guardar(clave As String, valor As String)
            Dim n As Integer = _db.Execute("UPDATE Parametro SET Valor=@v WHERE Clave=@k", "v", If(valor, ""), "k", clave)
            If n = 0 Then _db.Execute("INSERT INTO Parametro (Clave, Valor) VALUES (@k, @v)", "k", clave, "v", If(valor, ""))
            _cache(clave) = If(valor, "")
        End Sub

        Public Function Todos() As Dictionary(Of String, String)
            Return New Dictionary(Of String, String)(_cache, StringComparer.OrdinalIgnoreCase)
        End Function
    End Class

End Namespace
