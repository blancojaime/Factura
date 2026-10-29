Imports System.Globalization
Imports System.Runtime.CompilerServices

Namespace Common

    ''' <summary>Conversiones seguras de valores provenientes de la base de datos (Access u otros).</summary>
    Public Module Conv

        Public ReadOnly Inv As CultureInfo = CultureInfo.InvariantCulture

        Public Function IsNil(o As Object) As Boolean
            Return o Is Nothing OrElse o Is DBNull.Value
        End Function

        Public Function ToDec(o As Object) As Decimal
            If IsNil(o) Then Return 0D
            If TypeOf o Is Decimal Then Return CDec(o)
            If TypeOf o Is Double Then Return CDec(Math.Round(CDbl(o), 6))
            If TypeOf o Is String Then
                Dim d As Decimal
                If Decimal.TryParse(CStr(o), NumberStyles.Any, Inv, d) Then Return d
                Return 0D
            End If
            Try
                Return Convert.ToDecimal(o, Inv)
            Catch
                Return 0D
            End Try
        End Function

        Public Function ToDbl(o As Object) As Double
            If IsNil(o) Then Return 0R
            If TypeOf o Is Double Then Return CDbl(o)
            If TypeOf o Is String Then
                Dim d As Double
                If Double.TryParse(CStr(o), NumberStyles.Any, Inv, d) Then Return d
                Return 0R
            End If
            Try
                Return Convert.ToDouble(o, Inv)
            Catch
                Return 0R
            End Try
        End Function

        Public Function ToInt(o As Object) As Integer
            If IsNil(o) Then Return 0
            If TypeOf o Is Integer Then Return CInt(o)
            If TypeOf o Is String Then
                Dim i As Integer
                If Integer.TryParse(CStr(o), NumberStyles.Any, Inv, i) Then Return i
                Return 0
            End If
            Try
                Return Convert.ToInt32(o, Inv)
            Catch
                Return 0
            End Try
        End Function

        Public Function ToLng(o As Object) As Long
            If IsNil(o) Then Return 0
            Try
                Return Convert.ToInt64(o, Inv)
            Catch
                Return 0
            End Try
        End Function

        Public Function ToStr(o As Object) As String
            If IsNil(o) Then Return ""
            Return Convert.ToString(o, Inv)
        End Function

        Public Function ToFlag(o As Object) As Boolean
            If IsNil(o) Then Return False
            If TypeOf o Is Boolean Then Return CBool(o)
            If TypeOf o Is String Then
                Dim s As String = CStr(o).Trim().ToUpperInvariant()
                Return s = "1" OrElse s = "S" OrElse s = "SI" OrElse s = "TRUE" OrElse s = "-1"
            End If
            Return ToInt(o) <> 0
        End Function

        Public Function ToDate(o As Object) As Date
            If IsNil(o) Then Return Date.MinValue
            If TypeOf o Is Date Then Return CDate(o)
            If TypeOf o Is String Then
                Dim d As Date
                If Date.TryParse(CStr(o), Inv, DateTimeStyles.None, d) Then Return d
                If Date.TryParse(CStr(o), New CultureInfo("es-BO"), DateTimeStyles.None, d) Then Return d
                Return Date.MinValue
            End If
            Try
                Return Convert.ToDateTime(o, Inv)
            Catch
                Return Date.MinValue
            End Try
        End Function

        Public Function ToDateOrNull(o As Object) As Date?
            If IsNil(o) Then Return Nothing
            Dim d As Date = ToDate(o)
            If d = Date.MinValue Then Return Nothing
            Return d
        End Function

        ''' <summary>Redondeo contable a 2 decimales (hacia afuera del cero).</summary>
        <Extension>
        Public Function R2(d As Decimal) As Decimal
            Return Math.Round(d, 2, MidpointRounding.AwayFromZero)
        End Function

        <Extension>
        Public Function R4(d As Decimal) As Decimal
            Return Math.Round(d, 4, MidpointRounding.AwayFromZero)
        End Function

        ''' <summary>Valor o DBNull para parámetros opcionales.</summary>
        Public Function OrNull(v As Integer?) As Object
            If v.HasValue AndAlso v.Value <> 0 Then Return v.Value
            Return DBNull.Value
        End Function

        Public Function OrNull(v As Date?) As Object
            If v.HasValue Then Return v.Value
            Return DBNull.Value
        End Function

        Public Function OrNull(s As String) As Object
            If String.IsNullOrWhiteSpace(s) Then Return DBNull.Value
            Return s
        End Function

        <Extension>
        Public Function Cell(r As DataRow, col As String) As Object
            If r.Table.Columns.Contains(col) Then Return r(col)
            Return DBNull.Value
        End Function

        <Extension>
        Public Function GetS(r As DataRow, col As String) As String
            Return ToStr(r.Cell(col))
        End Function

        <Extension>
        Public Function GetD(r As DataRow, col As String) As Decimal
            Return ToDec(r.Cell(col))
        End Function

        <Extension>
        Public Function GetI(r As DataRow, col As String) As Integer
            Return ToInt(r.Cell(col))
        End Function

        <Extension>
        Public Function GetDt(r As DataRow, col As String) As Date
            Return ToDate(r.Cell(col))
        End Function

        <Extension>
        Public Function GetF(r As DataRow, col As String) As Boolean
            Return ToFlag(r.Cell(col))
        End Function

        Public ReadOnly MesesES As String() = {"", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"}

        Public Function NombreMes(m As Integer) As String
            If m < 1 OrElse m > 12 Then Return ""
            Return MesesES(m)
        End Function

        Public Function FinDeMes(d As Date) As Date
            Return New Date(d.Year, d.Month, Date.DaysInMonth(d.Year, d.Month))
        End Function

        Public Function InicioDeMes(d As Date) As Date
            Return New Date(d.Year, d.Month, 1)
        End Function

    End Module

End Namespace
