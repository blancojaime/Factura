Imports System.IO
Imports System.Text.Json

''' <summary>Preferencias del equipo (se guardan en %AppData%\ContaBol\settings.json). Los datos contables viven en la carpeta de datos.</summary>
Public Class AppSettings
    Public Property RutaDatos As String = ""
    Public Property UltimoUsuario As String = ""
    Public Property UltimaEmpresaId As Integer
    Public Property UltimaGestionId As Integer
    Public Property BackupAutomatico As Boolean = True
    Public Property CarpetaBackup As String = ""
    Public Property MantenerCopias As Integer = 10
    Public Property RecordarUsuario As Boolean = True

    Private Shared Function Archivo() As String
        Dim d As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ContaBol")
        Directory.CreateDirectory(d)
        Return Path.Combine(d, "settings.json")
    End Function

    Public Shared Function Cargar() As AppSettings
        Try
            If File.Exists(Archivo()) Then
                Dim s As AppSettings = JsonSerializer.Deserialize(Of AppSettings)(File.ReadAllText(Archivo()))
                If s IsNot Nothing Then Return s
            End If
        Catch
        End Try
        Return New AppSettings()
    End Function

    Public Sub Guardar()
        Try
            File.WriteAllText(Archivo(), JsonSerializer.Serialize(Me, New JsonSerializerOptions With {.WriteIndented = True}))
        Catch
        End Try
    End Sub
End Class
