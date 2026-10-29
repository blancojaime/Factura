Imports System.Reflection

''' <summary>Identidad visual: sobria y formal (azul institucional, grises), pensada para jornadas largas de digitación.</summary>
Public Module Tema

    Public ReadOnly Azul As Color = Color.FromArgb(31, 58, 95)
    Public ReadOnly AzulOscuro As Color = Color.FromArgb(20, 40, 68)
    Public ReadOnly AzulMedio As Color = Color.FromArgb(46, 94, 150)
    Public ReadOnly AzulClaro As Color = Color.FromArgb(222, 231, 243)
    Public ReadOnly Fondo As Color = Color.FromArgb(244, 246, 249)
    Public ReadOnly Borde As Color = Color.FromArgb(213, 219, 228)
    Public ReadOnly ColorTexto As Color = Color.FromArgb(33, 37, 41)
    Public ReadOnly Gris As Color = Color.FromArgb(108, 117, 125)
    Public ReadOnly Verde As Color = Color.FromArgb(40, 120, 70)
    Public ReadOnly Rojo As Color = Color.FromArgb(176, 36, 36)
    Public ReadOnly Ambar As Color = Color.FromArgb(190, 120, 10)
    Public ReadOnly Blanco As Color = Color.White
    Public ReadOnly FilaAlterna As Color = Color.FromArgb(247, 249, 252)

    Public ReadOnly Fuente As New Font("Segoe UI", 9.5F)
    Public ReadOnly FuenteNegrita As New Font("Segoe UI Semibold", 9.5F)
    Public ReadOnly FuenteTitulo As New Font("Segoe UI Semibold", 15.0F)
    Public ReadOnly FuenteSubtitulo As New Font("Segoe UI", 9.0F)
    Public ReadOnly FuenteGrande As New Font("Segoe UI Semibold", 12.0F)
    Public ReadOnly FuenteKpi As New Font("Segoe UI Semibold", 18.0F)

    Public Enum TipoBoton
        Primario
        Secundario
        Peligro
        Exito
    End Enum

    Public Sub Aplicar(f As Form)
        f.Font = Fuente
        f.BackColor = Fondo
        f.ForeColor = ColorTexto
    End Sub

    Public Function Boton(texto As String, Optional tipo As TipoBoton = TipoBoton.Secundario, Optional ancho As Integer = 96) As Button
        Dim b As New Button()
        b.Text = texto
        b.AutoSize = False
        b.Size = New Size(ancho, 32)
        b.FlatStyle = FlatStyle.Flat
        b.Cursor = Cursors.Hand
        b.Font = Fuente
        b.UseVisualStyleBackColor = False
        b.Margin = New Padding(0, 0, 6, 0)
        Select Case tipo
            Case TipoBoton.Primario
                b.BackColor = Azul
                b.ForeColor = Color.White
                b.FlatAppearance.BorderColor = Azul
                b.FlatAppearance.MouseOverBackColor = AzulMedio
            Case TipoBoton.Peligro
                b.BackColor = Color.White
                b.ForeColor = Rojo
                b.FlatAppearance.BorderColor = Rojo
                b.FlatAppearance.MouseOverBackColor = Color.FromArgb(252, 235, 235)
            Case TipoBoton.Exito
                b.BackColor = Verde
                b.ForeColor = Color.White
                b.FlatAppearance.BorderColor = Verde
                b.FlatAppearance.MouseOverBackColor = Color.FromArgb(55, 140, 85)
            Case Else
                b.BackColor = Color.White
                b.ForeColor = Azul
                b.FlatAppearance.BorderColor = Borde
                b.FlatAppearance.MouseOverBackColor = AzulClaro
        End Select
        Return b
    End Function

    Public Function Etiqueta(texto As String, Optional negrita As Boolean = False) As Label
        Dim l As New Label()
        l.Text = texto
        l.AutoSize = True
        l.Anchor = AnchorStyles.Left
        l.Margin = New Padding(0, 6, 6, 0)
        If negrita Then l.Font = FuenteNegrita
        l.ForeColor = ColorTexto
        Return l
    End Function

    ''' <summary>Banda superior con título y subtítulo de la pantalla.</summary>
    Public Function Banner(titulo As String, Optional subtitulo As String = "") As Panel
        Dim p As New Panel()
        p.Dock = DockStyle.Top
        p.Height = If(subtitulo = "", 46, 62)
        p.BackColor = Color.White
        p.Padding = New Padding(16, 8, 16, 6)
        Dim barra As New Panel() With {.Dock = DockStyle.Left, .Width = 5, .BackColor = Azul}
        Dim t As New Label() With {.Text = titulo, .Font = FuenteTitulo, .ForeColor = Azul, .AutoSize = True, .Location = New Point(18, 6)}
        p.Controls.Add(t)
        If subtitulo <> "" Then
            Dim s As New Label() With {.Text = subtitulo, .Font = FuenteSubtitulo, .ForeColor = Gris, .AutoSize = True, .Location = New Point(20, 38)}
            p.Controls.Add(s)
        End If
        p.Controls.Add(barra)
        AddHandler p.Paint, Sub(o, e) e.Graphics.DrawLine(New Pen(Borde), 0, p.Height - 1, p.Width, p.Height - 1)
        Return p
    End Function

    Public Function Tarjeta() As Panel
        Dim p As New Panel() With {.BackColor = Color.White, .Padding = New Padding(10)}
        AddHandler p.Paint, Sub(o, e) e.Graphics.DrawRectangle(New Pen(Borde), 0, 0, p.Width - 1, p.Height - 1)
        Return p
    End Function

    Private Sub ActivarDoubleBuffer(g As Control)
        Try
            GetType(Control).GetProperty("DoubleBuffered", BindingFlags.Instance Or BindingFlags.NonPublic).SetValue(g, True, Nothing)
        Catch
        End Try
    End Sub

    Public Sub EstiloGrid(g As DataGridView, Optional editable As Boolean = False)
        ActivarDoubleBuffer(g)
        g.BackgroundColor = Color.White
        g.BorderStyle = BorderStyle.None
        g.CellBorderStyle = DataGridViewCellBorderStyle.SingleHorizontal
        g.GridColor = Color.FromArgb(230, 234, 240)
        g.EnableHeadersVisualStyles = False
        g.ColumnHeadersBorderStyle = DataGridViewHeaderBorderStyle.None
        g.ColumnHeadersDefaultCellStyle.BackColor = Azul
        g.ColumnHeadersDefaultCellStyle.ForeColor = Color.White
        g.ColumnHeadersDefaultCellStyle.Font = FuenteNegrita
        g.ColumnHeadersDefaultCellStyle.SelectionBackColor = Azul
        g.ColumnHeadersDefaultCellStyle.Padding = New Padding(4, 0, 4, 0)
        g.ColumnHeadersHeight = 32
        g.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing
        g.RowHeadersVisible = False
        g.DefaultCellStyle.Font = Fuente
        g.DefaultCellStyle.SelectionBackColor = Color.FromArgb(205, 224, 247)
        g.DefaultCellStyle.SelectionForeColor = ColorTexto
        g.DefaultCellStyle.Padding = New Padding(3, 1, 3, 1)
        g.AlternatingRowsDefaultCellStyle.BackColor = FilaAlterna
        g.RowTemplate.Height = 26
        g.AllowUserToAddRows = False
        g.AllowUserToDeleteRows = False
        g.AllowUserToResizeRows = False
        g.SelectionMode = DataGridViewSelectionMode.FullRowSelect
        g.MultiSelect = False
        g.ReadOnly = Not editable
        g.AutoGenerateColumns = False
        g.Dock = DockStyle.Fill
    End Sub

    Public Function ColTexto(g As DataGridView, campo As String, titulo As String, Optional ancho As Integer = 100, Optional fill As Boolean = False) As DataGridViewTextBoxColumn
        Dim c As New DataGridViewTextBoxColumn() With {.DataPropertyName = campo, .HeaderText = titulo, .Name = campo, .Width = ancho, .SortMode = DataGridViewColumnSortMode.Automatic}
        If fill Then
            c.AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill
            c.MinimumWidth = ancho
        End If
        g.Columns.Add(c)
        Return c
    End Function

    Public Function ColImporte(g As DataGridView, campo As String, titulo As String, Optional ancho As Integer = 100, Optional formato As String = "N2") As DataGridViewTextBoxColumn
        Dim c As DataGridViewTextBoxColumn = ColTexto(g, campo, titulo, ancho)
        c.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleRight
        c.DefaultCellStyle.Format = formato
        c.HeaderCell.Style.Alignment = DataGridViewContentAlignment.MiddleRight
        Return c
    End Function

    Public Function ColFecha(g As DataGridView, campo As String, titulo As String, Optional ancho As Integer = 90) As DataGridViewTextBoxColumn
        Dim c As DataGridViewTextBoxColumn = ColTexto(g, campo, titulo, ancho)
        c.DefaultCellStyle.Format = "dd/MM/yyyy"
        c.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        Return c
    End Function

    Public Function ColCheck(g As DataGridView, campo As String, titulo As String, Optional ancho As Integer = 60) As DataGridViewCheckBoxColumn
        Dim c As New DataGridViewCheckBoxColumn() With {.DataPropertyName = campo, .HeaderText = titulo, .Name = campo, .Width = ancho}
        g.Columns.Add(c)
        Return c
    End Function

End Module
