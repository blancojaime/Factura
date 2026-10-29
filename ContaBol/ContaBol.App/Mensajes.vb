Imports System.IO
Imports ContaBol.Core.Common

''' <summary>Mensajes al usuario en español, con tono claro y sin tecnicismos.</summary>
Public Module Msg

    Public Sub Info(texto As String, Optional titulo As String = "ContaBol")
        MessageBox.Show(texto, titulo, MessageBoxButtons.OK, MessageBoxIcon.Information)
    End Sub

    Public Sub Aviso(texto As String, Optional titulo As String = "Atención")
        MessageBox.Show(texto, titulo, MessageBoxButtons.OK, MessageBoxIcon.Warning)
    End Sub

    Public Sub ErrorMsg(texto As String, Optional titulo As String = "No se pudo completar la operación")
        MessageBox.Show(texto, titulo, MessageBoxButtons.OK, MessageBoxIcon.Error)
    End Sub

    ''' <summary>Muestra una excepción: los errores de negocio tal cual; los inesperados quedan además registrados en el log.</summary>
    Public Sub ErrorMsg(ex As Exception)
        If TypeOf ex Is InvalidOperationException OrElse TypeOf ex Is ArgumentException OrElse TypeOf ex Is UnauthorizedAccessException OrElse TypeOf ex Is InvalidDataException Then
            ErrorMsg(ex.Message)
        Else
            Registrar(ex)
            ErrorMsg("Ocurrió un error inesperado:" & vbCrLf & ex.Message & vbCrLf & vbCrLf & "El detalle se guardó en el registro de errores (" & RutaLog() & ").")
        End If
    End Sub

    Public Function Confirmar(texto As String, Optional titulo As String = "Confirmar", Optional peligro As Boolean = False) As Boolean
        Return MessageBox.Show(texto, titulo, MessageBoxButtons.YesNo, If(peligro, MessageBoxIcon.Warning, MessageBoxIcon.Question), If(peligro, MessageBoxDefaultButton.Button2, MessageBoxDefaultButton.Button1)) = DialogResult.Yes
    End Function

    Public Function RutaLog() As String
        Dim d As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ContaBol")
        Directory.CreateDirectory(d)
        Return Path.Combine(d, "errores.log")
    End Function

    Public Sub Registrar(ex As Exception)
        Try
            File.AppendAllText(RutaLog(), Date.Now.ToString("yyyy-MM-dd HH:mm:ss") & vbCrLf & ex.ToString() & vbCrLf & New String("-"c, 60) & vbCrLf)
        Catch
        End Try
    End Sub

    ''' <summary>Pide un texto al usuario.</summary>
    Public Function Pedir(pregunta As String, Optional titulo As String = "ContaBol", Optional defecto As String = "", Optional clave As Boolean = False) As String
        Using f As New Form()
            Tema.Aplicar(f)
            f.Text = titulo
            f.FormBorderStyle = FormBorderStyle.FixedDialog
            f.StartPosition = FormStartPosition.CenterParent
            f.MaximizeBox = False
            f.MinimizeBox = False
            f.ShowInTaskbar = False
            f.ClientSize = New Size(440, 150)
            Dim l As New Label() With {.Text = pregunta, .Location = New Point(16, 14), .Size = New Size(408, 44), .AutoSize = False}
            Dim t As New TextBox() With {.Location = New Point(16, 62), .Width = 408, .Text = defecto}
            If clave Then t.UseSystemPasswordChar = True
            Dim ok As Button = Tema.Boton("Aceptar", Tema.TipoBoton.Primario)
            ok.Location = New Point(244, 104)
            ok.DialogResult = DialogResult.OK
            Dim cancel As Button = Tema.Boton("Cancelar")
            cancel.Location = New Point(346, 104)
            cancel.Width = 78
            cancel.DialogResult = DialogResult.Cancel
            f.Controls.AddRange({l, t, ok, cancel})
            f.AcceptButton = ok
            f.CancelButton = cancel
            If f.ShowDialog() = DialogResult.OK Then Return t.Text
            Return Nothing
        End Using
    End Function

    Public Function Cursor_(espera As Boolean) As IDisposable
        Return New CursorEspera(espera)
    End Function

    Private Class CursorEspera
        Implements IDisposable
        Public Sub New(e As Boolean)
            Cursor.Current = If(e, Cursors.WaitCursor, Cursors.Default)
        End Sub
        Public Sub Dispose() Implements IDisposable.Dispose
            Cursor.Current = Cursors.Default
        End Sub
    End Class

End Module
