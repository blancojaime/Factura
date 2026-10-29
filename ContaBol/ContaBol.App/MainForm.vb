Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Ventana principal: menú por módulos, accesos rápidos, pestañas de trabajo y barra de estado (empresa, gestión, usuario).</summary>
Public Class MainForm
    Inherits Form

    Public ReadOnly Menu As New MenuStrip()
    Public ReadOnly Barra As New ToolStrip()
    Private ReadOnly _tabs As New TabControl()
    Private ReadOnly _estado As New StatusStrip()
    Private ReadOnly _lblEmpresa As New ToolStripStatusLabel()
    Private ReadOnly _lblGestion As New ToolStripStatusLabel()
    Private ReadOnly _lblUsuario As New ToolStripStatusLabel()
    Private ReadOnly _lblTc As New ToolStripStatusLabel()
    Private ReadOnly _lblReloj As New ToolStripStatusLabel()
    Private ReadOnly _timer As New Timer() With {.Interval = 30000}
    Private _inicio As InicioPanel
    Private _paginaInicio As TabPage
    Public Property SalirSolicitado As Boolean
    Public Property CambiarEmpresaSolicitado As Boolean
    Public Property CerrarSesionSolicitado As Boolean

    Public Sub New()
        Tema.Aplicar(Me)
        Text = "ContaBol - Sistema Contable Integrado"
        Icon = Escritorio.IconoApp()
        WindowState = FormWindowState.Maximized
        MinimumSize = New Size(1000, 640)
        KeyPreview = True
        IsMdiContainer = False
        Menu.Dock = DockStyle.Top
        Menu.BackColor = Tema.Azul
        Menu.ForeColor = Color.White
        Menu.Font = Tema.Fuente
        Menu.Padding = New Padding(6, 3, 0, 3)
        Menu.Renderer = New RenderizadorMenu()
        Barra.Dock = DockStyle.Top
        Barra.GripStyle = ToolStripGripStyle.Hidden
        Barra.BackColor = Color.White
        Barra.Padding = New Padding(8, 3, 8, 3)
        Barra.Renderer = New ToolStripProfessionalRenderer() With {.RoundedEdges = False}
        _tabs.Dock = DockStyle.Fill
        _tabs.Padding = New Point(20, 5)
        _tabs.DrawMode = TabDrawMode.OwnerDrawFixed
        _tabs.SizeMode = TabSizeMode.Fixed
        _tabs.ItemSize = New Size(190, 28)
        _tabs.Font = Tema.Fuente
        _estado.BackColor = Tema.AzulOscuro
        _estado.SizingGrip = False
        For Each l As ToolStripStatusLabel In {_lblEmpresa, _lblGestion, _lblUsuario, _lblTc, _lblReloj}
            l.ForeColor = Color.White
            l.BorderSides = ToolStripStatusLabelBorderSides.Right
            l.BorderStyle = Border3DStyle.Etched
            l.Padding = New Padding(6, 0, 6, 0)
        Next
        _lblEmpresa.Spring = True
        _lblEmpresa.TextAlign = ContentAlignment.MiddleLeft
        _estado.Items.AddRange({_lblEmpresa, _lblGestion, _lblUsuario, _lblTc, _lblReloj})
        Controls.Add(_tabs)
        Controls.Add(Barra)
        Controls.Add(Menu)
        Controls.Add(_estado)
        MainMenuStrip = Menu
        AddHandler _tabs.DrawItem, AddressOf DibujarPestana
        AddHandler _tabs.MouseUp, AddressOf ClicPestana
        AddHandler _timer.Tick, Sub(o, e) ActualizarEstado()
        _timer.Start()
        MenuPrincipal.Construir(Me)
        Sesion.AlCambiarContexto = AddressOf AlCambiarContexto
        AddHandler KeyDown, Sub(o, e)
                                If e.Control AndAlso e.KeyCode = Keys.W Then
                                    If _tabs.SelectedTab IsNot Nothing AndAlso _tabs.SelectedTab IsNot _paginaInicio Then CerrarPagina(_tabs.SelectedTab)
                                    e.Handled = True
                                End If
                            End Sub
        AddHandler FormClosing, AddressOf AlCerrar
    End Sub

    Private Class RenderizadorMenu
        Inherits ToolStripProfessionalRenderer
        Public Sub New()
            MyBase.New(New ColoresMenu())
            RoundedEdges = False
        End Sub
    End Class

    Private Class ColoresMenu
        Inherits ProfessionalColorTable
        Public Overrides ReadOnly Property MenuItemSelected As Color
            Get
                Return Tema.AzulMedio
            End Get
        End Property
        Public Overrides ReadOnly Property MenuItemSelectedGradientBegin As Color
            Get
                Return Tema.AzulMedio
            End Get
        End Property
        Public Overrides ReadOnly Property MenuItemSelectedGradientEnd As Color
            Get
                Return Tema.AzulMedio
            End Get
        End Property
        Public Overrides ReadOnly Property MenuItemBorder As Color
            Get
                Return Tema.AzulMedio
            End Get
        End Property
        Public Overrides ReadOnly Property MenuBorder As Color
            Get
                Return Tema.Borde
            End Get
        End Property
        Public Overrides ReadOnly Property ToolStripDropDownBackground As Color
            Get
                Return Color.White
            End Get
        End Property
        Public Overrides ReadOnly Property ImageMarginGradientBegin As Color
            Get
                Return Color.FromArgb(246, 248, 251)
            End Get
        End Property
        Public Overrides ReadOnly Property ImageMarginGradientMiddle As Color
            Get
                Return Color.FromArgb(246, 248, 251)
            End Get
        End Property
        Public Overrides ReadOnly Property ImageMarginGradientEnd As Color
            Get
                Return Color.FromArgb(246, 248, 251)
            End Get
        End Property
        Public Overrides ReadOnly Property MenuStripGradientBegin As Color
            Get
                Return Tema.Azul
            End Get
        End Property
        Public Overrides ReadOnly Property MenuStripGradientEnd As Color
            Get
                Return Tema.Azul
            End Get
        End Property
    End Class

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        MostrarInicio()
        ActualizarEstado()
    End Sub

    ' ---------- Pestañas ----------
    Private Sub DibujarPestana(o As Object, e As DrawItemEventArgs)
        Dim pag As TabPage = _tabs.TabPages(e.Index)
        Dim r As Rectangle = _tabs.GetTabRect(e.Index)
        Dim activa As Boolean = e.Index = _tabs.SelectedIndex
        Using b As New SolidBrush(If(activa, Color.White, Tema.Fondo))
            e.Graphics.FillRectangle(b, r)
        End Using
        If activa Then
            Using p As New Pen(Tema.Azul, 3)
                e.Graphics.DrawLine(p, r.Left, r.Top + 1, r.Right, r.Top + 1)
            End Using
        End If
        Dim texto As String = pag.Text
        Dim tr As New Rectangle(r.Left + 8, r.Top + 4, r.Width - If(pag Is _paginaInicio, 12, 30), r.Height - 6)
        TextRenderer.DrawText(e.Graphics, texto, If(activa, Tema.FuenteNegrita, Tema.Fuente), tr, If(activa, Tema.Azul, Tema.Gris), TextFormatFlags.Left Or TextFormatFlags.VerticalCenter Or TextFormatFlags.EndEllipsis)
        If pag IsNot _paginaInicio Then
            TextRenderer.DrawText(e.Graphics, "×", Tema.FuenteGrande, New Rectangle(r.Right - 22, r.Top + 1, 20, r.Height - 2), Tema.Gris, TextFormatFlags.HorizontalCenter Or TextFormatFlags.VerticalCenter)
        End If
    End Sub

    Private Sub ClicPestana(o As Object, e As MouseEventArgs)
        For i As Integer = 0 To _tabs.TabPages.Count - 1
            Dim r As Rectangle = _tabs.GetTabRect(i)
            If Not r.Contains(e.Location) Then Continue For
            Dim pag As TabPage = _tabs.TabPages(i)
            If pag Is _paginaInicio Then Return
            If e.Button = MouseButtons.Middle OrElse (e.Button = MouseButtons.Left AndAlso e.X > r.Right - 24) Then CerrarPagina(pag)
            Return
        Next
    End Sub

    Private Sub CerrarPagina(pag As TabPage)
        If pag Is _paginaInicio Then Return
        For Each c As Control In pag.Controls.Cast(Of Control).ToList()
            Dim f As Form = TryCast(c, Form)
            If f IsNot Nothing Then
                f.Close()
                If Not f.IsDisposed Then Return
            End If
        Next
        QuitarPagina(pag)
    End Sub

    Private Sub QuitarPagina(pag As TabPage)
        If _tabs.TabPages.Contains(pag) Then
            Dim idx As Integer = _tabs.TabPages.IndexOf(pag)
            _tabs.TabPages.Remove(pag)
            If _tabs.TabPages.Count > 0 Then _tabs.SelectedIndex = Math.Max(0, Math.Min(idx - 1, _tabs.TabPages.Count - 1))
        End If
        pag.Dispose()
    End Sub

    Public Function ActivarSiExiste(clave As String) As Boolean
        For Each p As TabPage In _tabs.TabPages
            If p.Tag IsNot Nothing AndAlso p.Tag.ToString() = clave Then
                _tabs.SelectedTab = p
                Return True
            End If
        Next
        Return False
    End Function

    Public Sub AbrirPestana(f As Form, titulo As String, clave As String)
        If clave IsNot Nothing AndAlso ActivarSiExiste(clave) Then
            f.Dispose()
            Return
        End If
        Dim pag As New TabPage(titulo) With {.Tag = clave, .Padding = New Padding(0), .BackColor = Tema.Fondo}
        f.TopLevel = False
        f.FormBorderStyle = FormBorderStyle.None
        f.Dock = DockStyle.Fill
        pag.Controls.Add(f)
        _tabs.TabPages.Add(pag)
        _tabs.SelectedTab = pag
        AddHandler f.FormClosed, Sub(o, e) QuitarPagina(pag)
        f.Show()
        f.Focus()
    End Sub

    Public Sub CerrarPestana(f As Form)
        For Each p As TabPage In _tabs.TabPages
            If p.Controls.Contains(f) Then
                CerrarPagina(p)
                Return
            End If
        Next
        f.Close()
    End Sub

    Public Sub CerrarTodas()
        For Each p As TabPage In _tabs.TabPages.Cast(Of TabPage).ToList()
            If p IsNot _paginaInicio Then CerrarPagina(p)
        Next
    End Sub

    Public Sub CerrarActual()
        If _tabs.SelectedTab IsNot Nothing Then CerrarPagina(_tabs.SelectedTab)
    End Sub

    Public Function PestanaActual() As Form
        If _tabs.SelectedTab Is Nothing Then Return Nothing
        For Each c As Control In _tabs.SelectedTab.Controls
            Dim f As Form = TryCast(c, Form)
            If f IsNot Nothing Then Return f
        Next
        Return Nothing
    End Function

    ' ---------- Inicio ----------
    Public Sub MostrarInicio()
        If _paginaInicio IsNot Nothing AndAlso _tabs.TabPages.Contains(_paginaInicio) Then
            _tabs.TabPages.Remove(_paginaInicio)
            _paginaInicio.Dispose()
        End If
        _paginaInicio = New TabPage("Inicio") With {.BackColor = Tema.Fondo, .Padding = New Padding(0)}
        _inicio = New InicioPanel() With {.Dock = DockStyle.Fill}
        _paginaInicio.Controls.Add(_inicio)
        _tabs.TabPages.Insert(0, _paginaInicio)
        _tabs.SelectedTab = _paginaInicio
        _inicio.Cargar()
    End Sub

    Private Sub AlCambiarContexto()
        CerrarTodas()
        MostrarInicio()
        ActualizarEstado()
    End Sub

    Public Sub ActualizarEstado()
        Dim c As Contexto = Sesion.Ctx
        If c Is Nothing Then
            _lblEmpresa.Text = "Sin empresa abierta"
            _lblGestion.Text = ""
            Text = "ContaBol - Sistema Contable Integrado"
        Else
            _lblEmpresa.Text = "Empresa: " & c.Empresa.RazonSocial & "  (" & c.Empresa.Codigo & ")   ·   NIT " & c.Empresa.Nit
            _lblGestion.Text = "Gestión " & c.Gestion.Anio & If(c.Gestion.Abierta, "", " (CERRADA)")
            _lblGestion.ForeColor = If(c.Gestion.Abierta, Color.White, Color.FromArgb(255, 200, 120))
            Try
                _lblTc.Text = "T.C.: " & New TipoCambioService(c).Dolar(Date.Today).ToString("0.00", FormatoVal.Cultura)
            Catch
                _lblTc.Text = ""
            End Try
            Text = "ContaBol - " & c.Empresa.Titulo & " - Gestión " & c.Gestion.Anio
        End If
        _lblUsuario.Text = "Usuario: " & If(Sesion.Usuario Is Nothing, "", Sesion.Usuario.Nombre)
        _lblReloj.Text = Date.Now.ToString("dd/MM/yyyy HH:mm")
    End Sub

    Private Sub AlCerrar(o As Object, e As FormClosingEventArgs)
        If Not SalirSolicitado AndAlso Not CambiarEmpresaSolicitado AndAlso Not CerrarSesionSolicitado AndAlso e.CloseReason = CloseReason.UserClosing Then
            If Not Msg.Confirmar("¿Desea salir de ContaBol?", "Salir") Then
                e.Cancel = True
                Return
            End If
            SalirSolicitado = True
        End If
    End Sub
End Class
