Imports System.IO
Imports ContaBol.Core.Data

''' <summary>Pantalla de ingreso al sistema.</summary>
Public Class LoginForm
    Inherits Form

    Private ReadOnly _usuario As New TextBox()
    Private ReadOnly _clave As New TextBox()
    Private ReadOnly _error As New Label()
    Private ReadOnly _ingresar As Button = Tema.Boton("Ingresar", Tema.TipoBoton.Primario, 300)

    Public Sub New()
        Tema.Aplicar(Me)
        Text = "ContaBol - Ingreso"
        Icon = Escritorio.IconoApp()
        FormBorderStyle = FormBorderStyle.FixedDialog
        StartPosition = FormStartPosition.CenterScreen
        MaximizeBox = False
        MinimizeBox = False
        ClientSize = New Size(780, 470)
        BackColor = Color.White
        Dim izq As New Panel() With {.Dock = DockStyle.Left, .Width = 300, .BackColor = Tema.Azul}
        Dim logo As Image = Escritorio.Logo()
        If logo IsNot Nothing Then izq.Controls.Add(New PictureBox() With {.Image = logo, .SizeMode = PictureBoxSizeMode.Zoom, .Size = New Size(96, 96), .Location = New Point(40, 70), .BackColor = Color.Transparent})
        izq.Controls.Add(New Label() With {.Text = "ContaBol", .Font = New Font("Segoe UI Semibold", 26.0F), .ForeColor = Color.White, .AutoSize = True, .Location = New Point(36, 180)})
        izq.Controls.Add(New Label() With {.Text = "Sistema Contable Integrado" & vbCrLf & "Comercial · Costos · Bolivia", .Font = Tema.FuenteGrande, .ForeColor = Color.FromArgb(190, 208, 232), .AutoSize = True, .Location = New Point(40, 232)})
        izq.Controls.Add(New Label() With {.Text = "Multiempresa · Multigestión" & vbCrLf & "Reportes en PDF y Excel" & vbCrLf & "Respaldo y recuperación", .ForeColor = Color.FromArgb(150, 175, 210), .AutoSize = True, .Location = New Point(40, 340)})
        Controls.Add(izq)
        Dim t As New Label() With {.Text = "Iniciar sesión", .Font = New Font("Segoe UI Semibold", 18.0F), .ForeColor = Tema.Azul, .AutoSize = True, .Location = New Point(350, 70)}
        Dim l1 As New Label() With {.Text = "Usuario", .AutoSize = True, .Location = New Point(352, 140), .Font = Tema.FuenteNegrita}
        _usuario.Location = New Point(350, 164)
        _usuario.Width = 300
        _usuario.Font = New Font("Segoe UI", 11.0F)
        Dim l2 As New Label() With {.Text = "Contraseña", .AutoSize = True, .Location = New Point(352, 208), .Font = Tema.FuenteNegrita}
        _clave.Location = New Point(350, 232)
        _clave.Width = 300
        _clave.Font = New Font("Segoe UI", 11.0F)
        _clave.UseSystemPasswordChar = True
        _error.ForeColor = Tema.Rojo
        _error.AutoSize = False
        _error.Location = New Point(350, 272)
        _error.Size = New Size(340, 36)
        _ingresar.Location = New Point(350, 314)
        _ingresar.Height = 38
        Dim lnkDatos As New LinkLabel() With {.Text = "Carpeta de datos…", .AutoSize = True, .Location = New Point(350, 380), .LinkColor = Tema.AzulMedio}
        Dim lnkRestaurar As New LinkLabel() With {.Text = "Restaurar copia total…", .AutoSize = True, .Location = New Point(480, 380), .LinkColor = Tema.AzulMedio}
        Dim ruta As New Label() With {.Text = "Datos: " & Sesion.Config.RutaDatos, .AutoSize = False, .Size = New Size(400, 34), .Location = New Point(350, 404), .ForeColor = Tema.Gris, .Font = Tema.FuenteSubtitulo}
        Controls.AddRange({t, l1, _usuario, l2, _clave, _error, _ingresar, lnkDatos, lnkRestaurar, ruta})
        AcceptButton = _ingresar
        _usuario.Text = If(Sesion.Config.RecordarUsuario, Sesion.Config.UltimoUsuario, "")
        AddHandler Shown, Sub(o, e) If _usuario.Text = "" Then _usuario.Focus() Else _clave.Focus()
        AddHandler _ingresar.Click, Sub(o, e) Entrar()
        AddHandler lnkDatos.LinkClicked, Sub(o, e)
                                             If Program.ElegirCarpetaDatos(True) Then
                                                 Msg.Info("La carpeta de datos cambió. ContaBol se reiniciará para aplicar el cambio.")
                                                 Application.Restart()
                                                 Environment.Exit(0)
                                             End If
                                         End Sub
        AddHandler lnkRestaurar.LinkClicked, Sub(o, e) RestaurarTotal()
    End Sub

    Private Sub Entrar()
        _error.Text = ""
        Try
            Using Msg.Cursor_(True)
                Sesion.Usuario = Sesion.Sis.Autenticar(_usuario.Text, _clave.Text)
            End Using
            Sesion.Config.UltimoUsuario = Sesion.Usuario.Login
            Sesion.Config.Guardar()
            DialogResult = DialogResult.OK
        Catch ex As UnauthorizedAccessException
            _error.Text = ex.Message
            _clave.SelectAll()
            _clave.Focus()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub RestaurarTotal()
        Using d As New OpenFileDialog()
            d.Title = "Seleccione la copia total (.cbk)"
            d.Filter = "Copia de seguridad ContaBol (*.cbk)|*.cbk"
            If d.ShowDialog() <> DialogResult.OK Then Return
            Dim bs As New BackupService(Sesion.Sis)
            Dim v As BackupInfo = bs.Verificar(d.FileName)
            If Not v.Valido Then
                Msg.ErrorMsg("La copia no es válida: " & v.Mensaje)
                Return
            End If
            If v.Tipo <> "TOTAL" Then
                Msg.Aviso("Esta es una copia de una sola empresa. Restáurela desde Archivo > Copia de seguridad, dentro del sistema.")
                Return
            End If
            If Not Msg.Confirmar("Se reemplazarán TODOS los datos actuales por los de la copia del " & v.Fecha.ToString("dd/MM/yyyy HH:mm") & "." & vbCrLf & "Antes se guardará una copia de lo existente. ¿Continuar?", "Restaurar copia total", True) Then Return
            Try
                Sesion.Sis.Dispose()
                BackupService.RestaurarTotal(Sesion.Sis.Provider, Sesion.Config.RutaDatos, d.FileName)
                Msg.Info("Copia restaurada correctamente. ContaBol se reiniciará.")
                Application.Restart()
                Environment.Exit(0)
            Catch ex As Exception
                Msg.ErrorMsg(ex)
            End Try
        End Using
    End Sub
End Class

''' <summary>Cambio de contraseña (obligatorio en el primer ingreso de usuarios nuevos).</summary>
Public Module CambioClave
    Public Function Pedir(forzado As Boolean) As Boolean
        Dim campos As New List(Of CampoUI) From {
            New CampoUI With {.Clave = "nueva", .Titulo = "Nueva contraseña", .Tipo = TipoCampo.Clave, .Requerido = True, .Doble = True},
            New CampoUI With {.Clave = "confirma", .Titulo = "Repita la contraseña", .Tipo = TipoCampo.Clave, .Requerido = True, .Doble = True}}
        Using d As New FichaDialog("Cambiar contraseña", campos, Nothing,
            Sub(v)
                Dim n As String = ToStr(v("nueva")), c As String = ToStr(v("confirma"))
                If n <> c Then Throw New InvalidOperationException("Las contraseñas no coinciden.")
                If n.Equals("admin", StringComparison.OrdinalIgnoreCase) AndAlso Sesion.Usuario.Login.Equals("admin", StringComparison.OrdinalIgnoreCase) Then Throw New InvalidOperationException("Elija una contraseña distinta a la inicial.")
                Sesion.Sis.CambiarClave(Sesion.Usuario.Id, n, False)
            End Sub, If(forzado, "Por seguridad debe definir una contraseña personal antes de continuar.", "Mínimo 4 caracteres."), 560)
            Return d.ShowDialog() = DialogResult.OK
        End Using
    End Function
End Module

''' <summary>Selección de empresa y gestión: el corazón del trabajo multiempresa / multigestión.</summary>
Public Class EmpresaSelectorForm
    Inherits Form

    Private ReadOnly _empresas As New DataGridView()
    Private ReadOnly _gestiones As New DataGridView()
    Private ReadOnly _chkDefecto As New CheckBox() With {.Text = "Abrir siempre esta empresa y gestión al ingresar", .AutoSize = True}
    Public Property EmpresaId As Integer
    Public Property GestionId As Integer

    Public Sub New()
        Tema.Aplicar(Me)
        Text = "Seleccionar empresa y gestión"
        Icon = Escritorio.IconoApp()
        StartPosition = FormStartPosition.CenterScreen
        ClientSize = New Size(980, 560)
        MinimumSize = New Size(860, 480)
        KeyPreview = True
        Dim banner As Panel = Tema.Banner("Seleccionar empresa y gestión", "Trabaje con varias empresas y cambie de gestión cuando lo necesite")
        Dim cuerpo As New TableLayoutPanel() With {.Dock = DockStyle.Fill, .ColumnCount = 2, .RowCount = 2, .Padding = New Padding(14, 10, 14, 6)}
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 62))
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 38))
        cuerpo.RowStyles.Add(New RowStyle(SizeType.Absolute, 26))
        cuerpo.RowStyles.Add(New RowStyle(SizeType.Percent, 100))
        cuerpo.Controls.Add(New Label() With {.Text = "Empresas", .Font = Tema.FuenteGrande, .ForeColor = Tema.Azul, .AutoSize = True}, 0, 0)
        cuerpo.Controls.Add(New Label() With {.Text = "Gestiones de la empresa", .Font = Tema.FuenteGrande, .ForeColor = Tema.Azul, .AutoSize = True}, 1, 0)
        Tema.EstiloGrid(_empresas)
        Tema.ColTexto(_empresas, "Codigo", "Código", 80)
        Tema.ColTexto(_empresas, "RazonSocial", "Razón social", 260, True)
        Tema.ColTexto(_empresas, "Nit", "NIT", 100)
        Tema.ColTexto(_empresas, "Defecto", "Predet.", 60)
        _empresas.Margin = New Padding(0, 0, 10, 0)
        Tema.EstiloGrid(_gestiones)
        Tema.ColTexto(_gestiones, "Anio", "Gestión", 70)
        Tema.ColFecha(_gestiones, "FechaInicio", "Inicio", 90)
        Tema.ColFecha(_gestiones, "FechaFin", "Fin", 90)
        Tema.ColTexto(_gestiones, "EstadoTxt", "Estado", 80, True)
        cuerpo.Controls.Add(_empresas, 0, 1)
        cuerpo.Controls.Add(_gestiones, 1, 1)
        Dim pie As New FlowLayoutPanel() With {.Dock = DockStyle.Bottom, .Height = 96, .Padding = New Padding(14, 8, 14, 8), .BackColor = Color.White}
        Dim bAbrir As Button = Tema.Boton("Abrir", Tema.TipoBoton.Primario, 110)
        Dim bNueva As Button = Tema.Boton("Nueva empresa…", Tema.TipoBoton.Secundario, 140)
        Dim bEditar As Button = Tema.Boton("Datos de la empresa…", Tema.TipoBoton.Secundario, 170)
        Dim bSalir As Button = Tema.Boton("Salir", Tema.TipoBoton.Secundario, 80)
        pie.Controls.AddRange({bAbrir, bNueva, bEditar, bSalir})
        _chkDefecto.Margin = New Padding(8, 8, 0, 0)
        pie.Controls.Add(_chkDefecto)
        pie.SetFlowBreak(bSalir, True)
        Dim nota As New Label() With {.Text = "Cada empresa tiene su propio plan de cuentas, usuarios con permisos y una base de datos independiente por gestión.", .ForeColor = Tema.Gris, .AutoSize = True, .Margin = New Padding(0, 6, 0, 0)}
        pie.Controls.Add(nota)
        AddHandler pie.Paint, Sub(o, e) e.Graphics.DrawLine(New Pen(Tema.Borde), 0, 0, pie.Width, 0)
        Controls.Add(cuerpo)
        Controls.Add(banner)
        Controls.Add(pie)
        AddHandler _empresas.SelectionChanged, Sub(o, e) CargarGestiones()
        AddHandler _empresas.CellDoubleClick, Sub(o, e) If e.RowIndex >= 0 Then Abrir()
        AddHandler _gestiones.CellDoubleClick, Sub(o, e) If e.RowIndex >= 0 Then Abrir()
        AddHandler bAbrir.Click, Sub(o, e) Abrir()
        AddHandler bNueva.Click, Sub(o, e) NuevaEmpresa()
        AddHandler bEditar.Click, Sub(o, e) EditarEmpresa()
        AddHandler bSalir.Click, Sub(o, e) DialogResult = DialogResult.Cancel
        AddHandler KeyDown, Sub(o, e)
                                If e.KeyCode = Keys.Enter AndAlso Not (TypeOf ActiveControl Is Button) Then
                                    e.Handled = True
                                    Abrir()
                                End If
                            End Sub
        bNueva.Visible = Sesion.Usuario.EsAdmin
        bEditar.Visible = Sesion.Usuario.EsAdmin
        AddHandler Shown, Sub(o, e) CargarEmpresas()
    End Sub

    Private Sub CargarEmpresas(Optional seleccionar As Integer = 0)
        Dim dt As DataTable = Sesion.Sis.EmpresasDeUsuario(Sesion.Usuario)
        dt.Columns.Add("Defecto", GetType(String))
        For Each r As DataRow In dt.Rows
            r("Defecto") = If(r.GetF("EsDefecto"), "Sí", "")
        Next
        _empresas.DataSource = dt
        Dim idx As Integer = 0
        Dim buscar As Integer = If(seleccionar <> 0, seleccionar, Sesion.Config.UltimaEmpresaId)
        For i As Integer = 0 To _empresas.Rows.Count - 1
            If ToInt(CType(_empresas.Rows(i).DataBoundItem, DataRowView)("Id")) = buscar Then idx = i
        Next
        If _empresas.Rows.Count > 0 Then
            _empresas.CurrentCell = _empresas.Rows(idx).Cells(0)
            CargarGestiones()
        Else
            _gestiones.DataSource = Nothing
            Msg.Info(If(Sesion.Usuario.EsAdmin, "No hay empresas creadas. Use 'Nueva empresa…' para registrar la primera.", "Su usuario no tiene acceso a ninguna empresa. Solicítelo al administrador."))
        End If
    End Sub

    Private Function EmpresaActual() As DataRow
        If _empresas.CurrentRow Is Nothing Then Return Nothing
        Return CType(_empresas.CurrentRow.DataBoundItem, DataRowView).Row
    End Function

    Private Sub CargarGestiones()
        Dim e As DataRow = EmpresaActual()
        If e Is Nothing Then Return
        Dim dt As DataTable = Sesion.Sis.ListarGestiones(e.GetI("Id"))
        dt.Columns.Add("EstadoTxt", GetType(String))
        For Each r As DataRow In dt.Rows
            r("EstadoTxt") = If(r.GetS("Estado") = "A", "Abierta", "Cerrada")
        Next
        _gestiones.DataSource = dt
        Dim idx As Integer = 0
        For i As Integer = 0 To _gestiones.Rows.Count - 1
            Dim r As DataRowView = CType(_gestiones.Rows(i).DataBoundItem, DataRowView)
            If ToInt(r("Id")) = Sesion.Config.UltimaGestionId OrElse (ToFlag(r("EsDefecto")) AndAlso idx = 0) Then idx = i
        Next
        If _gestiones.Rows.Count > 0 Then _gestiones.CurrentCell = _gestiones.Rows(idx).Cells(0)
    End Sub

    Private Sub Abrir()
        Dim e As DataRow = EmpresaActual()
        If e Is Nothing OrElse _gestiones.CurrentRow Is Nothing Then
            Msg.Aviso("Seleccione una empresa y una gestión.")
            Return
        End If
        Dim g As DataRow = CType(_gestiones.CurrentRow.DataBoundItem, DataRowView).Row
        Try
            Using Msg.Cursor_(True)
                Sesion.AbrirContexto(e.GetI("Id"), g.GetI("Id"))
            End Using
            If _chkDefecto.Checked Then Sesion.Sis.MarcarDefecto(e.GetI("Id"), g.GetI("Id"))
            EmpresaId = e.GetI("Id")
            GestionId = g.GetI("Id")
            DialogResult = DialogResult.OK
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub NuevaEmpresa()
        Dim r As Tuple(Of Integer, Integer) = NuevaEmpresaDialog.Crear()
        If r IsNot Nothing Then CargarEmpresas(r.Item1)
    End Sub

    Private Sub EditarEmpresa()
        Dim e As DataRow = EmpresaActual()
        If e Is Nothing Then Return
        If NuevaEmpresaDialog.Editar(e.GetI("Id")) Then CargarEmpresas(e.GetI("Id"))
    End Sub
End Class

''' <summary>Alta y edición de empresas (datos fiscales + primera gestión).</summary>
Public Module NuevaEmpresaDialog

    Private Function CamposEmpresa(nueva As Boolean) As List(Of CampoUI)
        Dim l As New List(Of CampoUI)
        l.Add(CampoUI.Sec("Datos de la empresa"))
        Dim cod As CampoUI = CampoUI.Txt("Codigo", "Código corto", 12, True)
        cod.SoloLectura = Not nueva
        cod.Ayuda = "Identifica a la empresa (carpeta de datos). No se puede cambiar luego."
        l.Add(cod)
        l.Add(CampoUI.Txt("Nit", "NIT", 20))
        l.Add(CampoUI.Txt("RazonSocial", "Razón social", 150, True, True))
        l.Add(CampoUI.Txt("NombreComercial", "Nombre comercial", 100, False, True))
        l.Add(CampoUI.Txt("Direccion", "Dirección", 200, False, True))
        l.Add(CampoUI.Txt("Ciudad", "Ciudad", 60))
        l.Add(CampoUI.Txt("Telefono", "Teléfono", 40))
        l.Add(CampoUI.Txt("Email", "Correo electrónico", 100))
        l.Add(CampoUI.Txt("Actividad", "Actividad económica", 150))
        l.Add(CampoUI.Txt("RepLegal", "Representante legal", 100))
        l.Add(CampoUI.Txt("Matricula", "Matrícula de comercio", 30))
        If nueva Then
            l.Add(CampoUI.Sec("Primera gestión"))
            Dim anio As CampoUI = CampoUI.Ent("Anio", "Año de la gestión", True)
            anio.Defecto = Date.Today.Year
            l.Add(anio)
            l.Add(CampoUI.Lst("MesInicio", "Inicio del ejercicio fiscal", "1|Enero (comercial / servicios)", "4|Abril (industrial)", "7|Julio (agropecuario)", "10|Octubre (minero)"))
            l.Add(CampoUI.Lst("Correlativo", "Numeración de comprobantes", "M|Reinicia cada mes", "U|Continua en toda la gestión"))
            l.Add(CampoUI.Lst("Plantilla", "Plan de cuentas inicial", "C|Plan comercial boliviano (recomendado)", "V|Vacío (lo cargaré o importaré)"))
            Dim tc As CampoUI = CampoUI.Imp("Tc", "Tipo de cambio inicial", False, 2)
            tc.Defecto = 6.96D
            l.Add(tc)
        Else
            l.Add(CampoUI.Chk("Activa", "Empresa activa", True))
        End If
        Return l
    End Function

    Public Function Crear() As Tuple(Of Integer, Integer)
        Dim resultado As Tuple(Of Integer, Integer) = Nothing
        Using d As New FichaDialog("Nueva empresa", CamposEmpresa(True), Nothing,
            Sub(v)
                Dim e As New EmpresaInfo()
                DtoMapper.Aplicar(e, v)
                Dim opc As New NuevaGestionOpciones With {
                    .Anio = ToInt(v("Anio")), .MesInicio = ToInt(ToStr(v("MesInicio"))), .CorrelativoMensual = ToStr(v("Correlativo")) = "M",
                    .Plantilla = If(ToStr(v("Plantilla")) = "V", PlantillaPlan.Vacio, PlantillaPlan.Comercial), .TipoCambioInicial = If(ToDec(v("Tc")) > 0D, ToDec(v("Tc")), 6.96D)}
                Using Msg.Cursor_(True)
                    resultado = New EmpresaService(Sesion.Sis).CrearEmpresa(e, opc, Sesion.Usuario.Id)
                End Using
            End Sub, "Se creará la base de datos de la empresa con su plan de cuentas y parámetros.", 800)
            If d.ShowDialog() = DialogResult.OK Then Return resultado
        End Using
        Return Nothing
    End Function

    Public Function Editar(empresaId As Integer) As Boolean
        Dim e As EmpresaInfo = Sesion.Sis.ObtenerEmpresa(empresaId)
        If e Is Nothing Then Return False
        Using d As New FichaDialog("Datos de la empresa", CamposEmpresa(False), DtoMapper.ADiccionario(e),
            Sub(v)
                DtoMapper.Aplicar(e, v)
                Dim svc As New EmpresaService(Sesion.Sis)
                Using Msg.Cursor_(True)
                    svc.ActualizarEmpresa(e)
                End Using
            End Sub, e.Codigo, 800)
            Return d.ShowDialog() = DialogResult.OK
        End Using
    End Function
End Module
