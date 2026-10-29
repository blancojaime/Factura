Imports System.Globalization

''' <summary>Utilidades de números tecleados por el usuario (acepta punto o coma como decimal).</summary>
Public Module Numeros

    Public Function Parse(texto As String, ByRef valor As Decimal) As Boolean
        valor = 0D
        If texto Is Nothing Then Return True
        Dim t As String = texto.Trim().Replace(" ", "")
        If t = "" Then Return True
        Dim ultimaComa As Integer = t.LastIndexOf(","c)
        Dim ultimoPunto As Integer = t.LastIndexOf("."c)
        Dim dec As Integer = Math.Max(ultimaComa, ultimoPunto)
        If dec >= 0 Then
            Dim entera As String = t.Substring(0, dec).Replace(",", "").Replace(".", "")
            Dim frac As String = t.Substring(dec + 1)
            ' 1.234 con tres decimales y un solo separador se interpreta como miles
            If frac.Length = 3 AndAlso t.Count(Function(c) c = "."c OrElse c = ","c) = 1 AndAlso entera.Length >= 1 AndAlso entera.Length <= 3 AndAlso entera <> "0" Then
                t = entera & frac
            Else
                t = entera & "." & frac
            End If
        End If
        Return Decimal.TryParse(t, NumberStyles.Number Or NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, valor)
    End Function
End Module

''' <summary>Grilla de captura rápida: Enter avanza a la siguiente celda editable y al final salta a la fila siguiente.</summary>
Public Class GridEntrada
    Inherits DataGridView

    Public Event EnterAlFinalDeFila As EventHandler

    Protected Overrides Function ProcessDialogKey(keyData As Keys) As Boolean
        If (keyData And Keys.KeyCode) = Keys.Enter AndAlso (keyData And Keys.Modifiers) = Keys.None Then
            MoverSiguiente()
            Return True
        End If
        Return MyBase.ProcessDialogKey(keyData)
    End Function

    Protected Overrides Function ProcessDataGridViewKey(e As KeyEventArgs) As Boolean
        If e.KeyCode = Keys.Enter AndAlso Not e.Control AndAlso Not e.Alt Then
            MoverSiguiente()
            Return True
        End If
        Return MyBase.ProcessDataGridViewKey(e)
    End Function

    Private Sub MoverSiguiente()
        If CurrentCell Is Nothing Then Return
        Dim fila As Integer = CurrentCell.RowIndex
        Dim col As Integer = CurrentCell.ColumnIndex
        If IsCurrentCellInEditMode Then
            If Not EndEdit() Then Return
        End If
        Dim siguiente As Integer = -1
        For i As Integer = col + 1 To Columns.Count - 1
            If Columns(i).Visible AndAlso Not Columns(i).ReadOnly Then
                siguiente = i
                Exit For
            End If
        Next
        If siguiente >= 0 Then
            CurrentCell = Rows(fila).Cells(siguiente)
            BeginEdit(True)
            Return
        End If
        RaiseEvent EnterAlFinalDeFila(Me, EventArgs.Empty)
        Dim primera As Integer = -1
        For i As Integer = 0 To Columns.Count - 1
            If Columns(i).Visible AndAlso Not Columns(i).ReadOnly Then
                primera = i
                Exit For
            End If
        Next
        Dim nf As Integer = fila + 1
        If nf >= Rows.Count Then
            If AllowUserToAddRows Then Rows.Add()
            If nf >= Rows.Count Then Return
        End If
        CurrentCell = Rows(nf).Cells(primera)
        BeginEdit(True)
    End Sub
End Class
