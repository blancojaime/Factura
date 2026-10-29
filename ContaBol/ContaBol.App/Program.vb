Imports System.IO
Imports System.Threading
Imports ContaBol.Core.Data

Public Module Program

    <STAThread>
    Public Sub Main()
        Application.EnableVisualStyles()
        Application.SetCompatibleTextRenderingDefault(False)
        Application.SetHighDpiMode(HighDpiMode.SystemAware)
        AddHandler Application.ThreadException, Sub(o, e)
                                                    Msg.ErrorMsg(e.Exception)
                                                End Sub
        AddHandler AppDomain.CurrentDomain.UnhandledException, Sub(o, e)
                                                                   Msg.Registrar(CType(e.ExceptionObject, Exception))
                                                               End Sub
        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException)
        Sesion.Config = AppSettings.Cargar()
        Try
            AccessProvider.DetectProvider()
        Catch ex As Exception
            MessageBox.Show(ex.Message, "ContaBol - Motor de base de datos", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Return
        End Try
        If Sesion.Config.RutaDatos = "" OrElse Not Directory.Exists(Sesion.Config.RutaDatos) Then
            If Not ElegirCarpetaDatos(False) Then Return
        End If
        Try
            Sesion.Sis = SistemaService.Abrir(New AccessProvider(), Sesion.Config.RutaDatos)
        Catch ex As Exception
            Msg.Registrar(ex)
            MessageBox.Show("No se pudo abrir la base de datos del sistema en:" & vbCrLf & Sesion.Config.RutaDatos & vbCrLf & vbCrLf & ex.Message, "ContaBol", MessageBoxButtons.OK, MessageBoxIcon.Error)
            Return
        End Try
        Do
            If Sesion.Usuario Is Nothing Then
                Using login As New LoginForm()
                    If login.ShowDialog() <> DialogResult.OK Then Exit Do
                End Using
                If Sesion.Usuario.CambiarClave Then
                    If Not CambioClave.Pedir(True) Then
                        Sesion.Usuario = Nothing
                        Continue Do
                    End If
                    Sesion.Usuario.CambiarClave = False
                End If
            End If
            If Not AbrirEmpresaInicial() Then Exit Do
            Dim main As New MainForm()
            Escritorio.Principal = main
            Application.Run(main)
            Escritorio.Principal = Nothing
            If main.CambiarEmpresaSolicitado Then
                CopiaAlSalir(False)
                Sesion.CerrarContexto()
                Continue Do
            End If
            If main.CerrarSesionSolicitado Then
                CopiaAlSalir(False)
                Sesion.CerrarContexto()
                Sesion.Usuario = Nothing
                Continue Do
            End If
            Exit Do
        Loop
        CopiaAlSalir(True)
        Sesion.CerrarContexto()
        Try
            Sesion.Sis?.Dispose()
        Catch
        End Try
    End Sub

    ''' <summary>Si hay una empresa/gestión predeterminada (o la última usada) la abre directamente; si no, muestra el selector.</summary>
    Private Function AbrirEmpresaInicial() As Boolean
        If Sesion.Ctx Is Nothing Then
            Try
                Dim e As DataTable = Sesion.Sis.EmpresasDeUsuario(Sesion.Usuario)
                Dim def As DataRow = e.Rows.Cast(Of DataRow)().FirstOrDefault(Function(r) r.GetF("EsDefecto"))
                If def IsNot Nothing Then
                    Dim g As DataRow = Sesion.Sis.ListarGestiones(def.GetI("Id")).Rows.Cast(Of DataRow)().FirstOrDefault(Function(r) r.GetF("EsDefecto"))
                    If g IsNot Nothing Then
                        Sesion.AbrirContexto(def.GetI("Id"), g.GetI("Id"))
                        Return True
                    End If
                End If
            Catch
            End Try
        End If
        If Sesion.Ctx IsNot Nothing Then Return True
        Using f As New EmpresaSelectorForm()
            Return f.ShowDialog() = DialogResult.OK
        End Using
    End Function

    ''' <summary>Elige o crea la carpeta donde se guardan los datos (puede ser una carpeta compartida de red para trabajo multiusuario).</summary>
    Public Function ElegirCarpetaDatos(cambio As Boolean) As Boolean
        Using d As New FolderBrowserDialog()
            d.Description = If(cambio, "Seleccione la nueva carpeta de datos de ContaBol.", "Seleccione la carpeta donde ContaBol guardará sus datos (empresas, gestiones y copias de seguridad)." & vbCrLf & "Para trabajar en red, elija una carpeta compartida accesible desde todos los equipos.")
            d.UseDescriptionForTitle = True
            d.ShowNewFolderButton = True
            Dim sugerida As String = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "ContaBol")
            d.InitialDirectory = If(Directory.Exists(sugerida), sugerida, Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments))
            If cambio = False AndAlso Not Directory.Exists(sugerida) Then
                Try
                    Directory.CreateDirectory(sugerida)
                    d.InitialDirectory = sugerida
                    d.SelectedPath = sugerida
                Catch
                End Try
            End If
            If d.ShowDialog() <> DialogResult.OK Then Return False
            Sesion.Config.RutaDatos = d.SelectedPath
            Sesion.Config.Guardar()
            Return True
        End Using
    End Function

    Private Sub CopiaAlSalir(definitiva As Boolean)
        If Sesion.Sis Is Nothing OrElse Sesion.Ctx Is Nothing OrElse Not Sesion.Config.BackupAutomatico Then Return
        If Not Sesion.Usuario.Puede("ADM.BACKUP") Then Return
        Try
            Dim bs As New BackupService(Sesion.Sis)
            Dim destino As String = If(Sesion.Config.CarpetaBackup <> "" AndAlso Directory.Exists(Sesion.Config.CarpetaBackup), Sesion.Config.CarpetaBackup, "")
            ' una copia automática por empresa y por día
            Dim hoy As Object = Sesion.Sis.Db.Scalar("SELECT MAX(Fecha) FROM RegistroBackup WHERE EmpresaId=@e AND Tipo='EMPRESA' AND Resultado='OK'", "e", Sesion.Ctx.Empresa.Id)
            If hoy IsNot Nothing AndAlso ToDate(hoy).Date = Date.Today Then Return
            Dim empresaId As Integer = Sesion.Ctx.Empresa.Id
            Sesion.CerrarContexto()
            bs.BackupEmpresa(empresaId, destino, "Copia automática al salir")
            bs.Depurar(Math.Max(3, Sesion.Config.MantenerCopias))
        Catch ex As Exception
            Msg.Registrar(ex)
        End Try
    End Sub
End Module
