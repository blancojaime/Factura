Imports System.Text

Namespace Common

    ''' <summary>Convierte importes a su expresión literal en español (formato "Son: ... 00/100 Bolivianos").</summary>
    Public Module NumeroLetras

        Private ReadOnly Unidades As String() = {"", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
            "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE",
            "VEINTE", "VEINTIUN", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO", "VEINTICINCO", "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"}
        Private ReadOnly Decenas As String() = {"", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"}
        Private ReadOnly Centenas As String() = {"", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"}

        Private Function Menor1000(n As Integer) As String
            If n = 0 Then Return ""
            If n = 100 Then Return "CIEN"
            Dim sb As New StringBuilder()
            Dim c As Integer = n \ 100
            Dim r As Integer = n Mod 100
            If c > 0 Then sb.Append(Centenas(c)).Append(" ")
            If r < 30 Then
                sb.Append(Unidades(r))
            Else
                Dim d As Integer = r \ 10
                Dim u As Integer = r Mod 10
                sb.Append(Decenas(d))
                If u > 0 Then sb.Append(" Y ").Append(Unidades(u))
            End If
            Return sb.ToString().Trim()
        End Function

        Public Function Entero(n As Long) As String
            If n = 0 Then Return "CERO"
            Dim sb As New StringBuilder()
            Dim millones As Long = n \ 1000000L
            Dim resto As Long = n Mod 1000000L
            If millones > 0 Then
                If millones = 1 Then
                    sb.Append("UN MILLON ")
                Else
                    sb.Append(Entero(millones)).Append(" MILLONES ")
                End If
            End If
            Dim miles As Integer = CInt(resto \ 1000)
            Dim cientos As Integer = CInt(resto Mod 1000)
            If miles > 0 Then
                If miles = 1 Then
                    sb.Append("MIL ")
                Else
                    sb.Append(Menor1000(miles).Replace("UNO", "UN")).Append(" MIL ")
                End If
            End If
            If cientos > 0 Then sb.Append(Menor1000(cientos))
            Return sb.ToString().Trim().Replace("  ", " ")
        End Function

        ''' <summary>"MIL QUINIENTOS 50/100 BOLIVIANOS"</summary>
        Public Function Importe(monto As Decimal, Optional moneda As String = "BS") As String
            Dim m As Decimal = Math.Abs(Math.Round(monto, 2, MidpointRounding.AwayFromZero))
            Dim ent As Long = CLng(Math.Floor(m))
            Dim cent As Integer = CInt(Math.Round((m - ent) * 100D, 0))
            Dim nombre As String = If(moneda = "USD", "DOLARES AMERICANOS", "BOLIVIANOS")
            Return Entero(ent) & " " & cent.ToString("00") & "/100 " & nombre
        End Function

    End Module

End Namespace
