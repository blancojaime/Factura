Imports System.IO
Imports System.Reflection
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Acceso a la ventana principal desde cualquier pantalla (abrir/cerrar pestañas).</summary>
Public Module Escritorio

    Public Property Principal As MainForm

    Public Function Ventana() As IWin32Window
        Return Principal
    End Function

    ''' <summary>Abre una pantalla en una pestaña (o como diálogo si no hay ventana principal). Con clave, reutiliza la pestaña existente.</summary>
    Public Sub AbrirPestana(f As Form, titulo As String, clave As String)
        If Principal Is Nothing Then
            f.ShowDialog()
            Return
        End If
        Principal.AbrirPestana(f, titulo, clave)
    End Sub

    Public Sub CerrarPestana(f As Form)
        If Principal Is Nothing Then
            f.Close()
        Else
            Principal.CerrarPestana(f)
        End If
    End Sub

    ''' <summary>Abre una pantalla de trabajo única (si ya está abierta solo la activa).</summary>
    Public Sub Abrir(Of T As {FormBase, New})()
        If Sesion.Ctx Is Nothing Then
            Msg.Aviso("Primero abra una empresa y gestión (Archivo > Cambiar empresa o gestión).")
            Return
        End If
        Try
            If Principal IsNot Nothing AndAlso Principal.ActivarSiExiste(GetType(T).Name) Then Return
            Dim f As New T()
            AbrirPestana(f, f.TextoPestana, GetType(T).Name)
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Public Sub AbrirNueva(f As FormBase, Optional clave As String = Nothing)
        If Sesion.Ctx Is Nothing Then
            Msg.Aviso("Primero abra una empresa y gestión (Archivo > Cambiar empresa o gestión).")
            Return
        End If
        Try
            AbrirPestana(f, f.TextoPestana, clave)
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Public Function Logo() As Image
        Try
            Using s As Stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("ContaBol.App.Resources.contabol.png")
                If s IsNot Nothing Then Return New Bitmap(s)
            End Using
        Catch
        End Try
        Return Nothing
    End Function

    Public Function IconoApp() As Icon
        Try
            Return Icon.ExtractAssociatedIcon(Application.ExecutablePath)
        Catch
            Return Nothing
        End Try
    End Function

End Module
