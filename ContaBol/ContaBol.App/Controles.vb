Imports System.ComponentModel
Imports System.Globalization
Imports ContaBol.Core.Common
Imports ContaBol.Core.Reports
Imports ContaBol.Core.Services

''' <summary>Cuadro de texto para importes: alineado a la derecha, acepta punto o coma, formatea al salir.</summary>
Public Class CampoImporte
    Inherits TextBox

    Private _decimales As Integer = 2
    Private _valor As Decimal

    Public Event ValorCambiado As EventHandler

    Public Sub New()
        TextAlign = HorizontalAlignment.Right
        Text = FormatoVal.Texto(0D, Formato.Monto)
    End Sub

    <DefaultValue(2)>
    Public Property Decimales As Integer
        Get
            Return _decimales
        End Get
        Set(value As Integer)
            _decimales = value
            Refrescar()
        End Set
    End Property

    <DefaultValue(False)>
    Public Property PermiteNegativo As Boolean

    <Browsable(False), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)>
    Public Property Valor As Decimal
        Get
            Dim d As Decimal
            If Decimal.TryParse(Text, NumberStyles.Number Or NumberStyles.AllowLeadingSign, FormatoVal.Cultura, d) Then Return d
            Return 0D
        End Get
        Set(value As Decimal)
            _valor = value
            Refrescar()
        End Set
    End Property

    Private Sub Refrescar()
        Text = _valor.ToString("#,##0." & New String("0"c, Math.Max(0, _decimales)), FormatoVal.Cultura).TrimEnd("."c, ","c)
    End Sub

    Private ReadOnly Property SepDecimal As Char
        Get
            Return FormatoVal.Cultura.NumberFormat.NumberDecimalSeparator(0)
        End Get
    End Property

    Protected Overrides Sub OnEnter(e As EventArgs)
        MyBase.OnEnter(e)
        Dim d As Decimal = Valor
        Text = If(d = 0D, "", d.ToString("0." & New String("#"c, Math.Max(1, _decimales)), FormatoVal.Cultura))
        SelectAll()
    End Sub

    Protected Overrides Sub OnLeave(e As EventArgs)
        MyBase.OnLeave(e)
        _valor = Valor
        Refrescar()
        RaiseEvent ValorCambiado(Me, EventArgs.Empty)
    End Sub

    Protected Overrides Sub OnTextChanged(e As EventArgs)
        MyBase.OnTextChanged(e)
        If Focused Then RaiseEvent ValorCambiado(Me, EventArgs.Empty)
    End Sub

    Protected Overrides Sub OnKeyPress(e As KeyPressEventArgs)
        If Char.IsControl(e.KeyChar) Then
            MyBase.OnKeyPress(e)
            Return
        End If
        If Char.IsDigit(e.KeyChar) Then
            MyBase.OnKeyPress(e)
            Return
        End If
        If e.KeyChar = "."c OrElse e.KeyChar = ","c Then
            If _decimales > 0 AndAlso Not Text.Contains(SepDecimal) Then
                e.KeyChar = SepDecimal
                MyBase.OnKeyPress(e)
                Return
            End If
            e.Handled = True
            Return
        End If
        If e.KeyChar = "-"c AndAlso PermiteNegativo AndAlso SelectionStart = 0 AndAlso Not Text.Contains("-"c) Then
            MyBase.OnKeyPress(e)
            Return
        End If
        e.Handled = True
    End Sub
End Class

''' <summary>Lista desplegable con autocompletado para catálogos (muestra texto, devuelve el Id).</summary>
Public Class LookupCombo
    Inherits ComboBox

    Public Sub New()
        DropDownStyle = ComboBoxStyle.DropDown
        AutoCompleteMode = AutoCompleteMode.SuggestAppend
        AutoCompleteSource = AutoCompleteSource.ListItems
        FlatStyle = FlatStyle.Flat
        BackColor = Color.White
    End Sub

    Public Sub Cargar(dt As DataTable, idCol As String, textoCol As String, Optional conVacio As Boolean = True, Optional textoVacio As String = "")
        Dim t As New DataTable()
        t.Columns.Add("Id", GetType(Integer))
        t.Columns.Add("Texto", GetType(String))
        If conVacio Then t.Rows.Add(0, textoVacio)
        For Each r As DataRow In dt.Rows
            t.Rows.Add(ToInt(r(idCol)), ToStr(r(textoCol)))
        Next
        DisplayMember = "Texto"
        ValueMember = "Id"
        DataSource = t
        If t.Rows.Count > 0 Then SelectedIndex = 0
    End Sub

    Public Sub CargarLista(opciones As IEnumerable(Of KeyValuePair(Of String, String)))
        Dim t As New DataTable()
        t.Columns.Add("Id", GetType(String))
        t.Columns.Add("Texto", GetType(String))
        For Each kv In opciones
            t.Rows.Add(kv.Key, kv.Value)
        Next
        DisplayMember = "Texto"
        ValueMember = "Id"
        DropDownStyle = ComboBoxStyle.DropDownList
        AutoCompleteMode = AutoCompleteMode.None
        DataSource = t
        If t.Rows.Count > 0 Then SelectedIndex = 0
    End Sub

    <Browsable(False), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)>
    Public Property ValorId As Integer
        Get
            If SelectedValue Is Nothing Then Return 0
            Return ToInt(SelectedValue)
        End Get
        Set(value As Integer)
            If DataSource Is Nothing Then Return
            SelectedValue = value
            If SelectedIndex < 0 AndAlso Items.Count > 0 Then SelectedIndex = 0
        End Set
    End Property

    <Browsable(False), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)>
    Public Property ValorTexto As String
        Get
            If SelectedValue Is Nothing Then Return ""
            Return ToStr(SelectedValue)
        End Get
        Set(value As String)
            If DataSource Is Nothing Then Return
            SelectedValue = If(value, "")
            If SelectedIndex < 0 AndAlso Items.Count > 0 Then SelectedIndex = 0
        End Set
    End Property

    Protected Overrides Sub OnLeave(e As EventArgs)
        MyBase.OnLeave(e)
        If SelectedIndex < 0 AndAlso Text <> "" Then
            Dim i As Integer = FindString(Text)
            If i >= 0 Then SelectedIndex = i
        End If
    End Sub
End Class

''' <summary>Selector de una cuenta del plan: código con validación al salir, nombre visible y búsqueda con * como comodín (F4).</summary>
Public Class PickerCuenta
    Inherits Panel

    Private ReadOnly _cod As New TextBox()
    Private ReadOnly _nom As New Label()
    Private ReadOnly _btn As Button = Tema.Boton("…", Tema.TipoBoton.Secundario, 28)
    Private _id As Integer
    Public Event CuentaCambiada As EventHandler

    Public Property SoloMovimiento As Boolean = True
    Public Property Requerida As Boolean

    Public Sub New()
        Height = 26
        Width = 380
        _cod.Width = 132
        _cod.Dock = DockStyle.Left
        _nom.Dock = DockStyle.Fill
        _nom.TextAlign = ContentAlignment.MiddleLeft
        _nom.Padding = New Padding(6, 0, 0, 0)
        _nom.ForeColor = Tema.Gris
        _nom.AutoEllipsis = True
        _btn.Dock = DockStyle.Right
        _btn.Height = 24
        _btn.Margin = New Padding(0)
        Controls.Add(_nom)
        Controls.Add(_btn)
        Controls.Add(_cod)
        AddHandler _btn.Click, Sub(o, e) Buscar(_cod.Text)
        AddHandler _nom.DoubleClick, Sub(o, e) Buscar("")
        AddHandler _cod.KeyDown, AddressOf CodKeyDown
        AddHandler _cod.Leave, Sub(o, e) Resolver()
    End Sub

    Private Sub CodKeyDown(o As Object, e As KeyEventArgs)
        If e.KeyCode = Keys.F4 OrElse e.KeyCode = Keys.F2 OrElse (e.KeyCode = Keys.Down AndAlso e.Alt) Then
            e.Handled = True
            Buscar(_cod.Text)
        ElseIf e.KeyCode = Keys.Enter Then
            Resolver()
        End If
    End Sub

    Private Sub Resolver()
        If Sesion.Ctx Is Nothing Then Return
        Dim t As String = _cod.Text.Trim()
        If t = "" Then
            Asignar(0)
            Return
        End If
        Dim r As DataRow = Sesion.Ctx.CuentaPorCodigo(t)
        If r IsNot Nothing AndAlso (r.GetF("EsMovimiento") OrElse Not SoloMovimiento) Then
            Asignar(r.GetI("Id"))
        Else
            Buscar(t)
        End If
    End Sub

    Private Sub Buscar(patron As String)
        If Sesion.Ctx Is Nothing Then Return
        Using d As New CuentaPickerDialog(patron, SoloMovimiento)
            If d.ShowDialog(FindForm()) = DialogResult.OK Then
                Asignar(d.CuentaId)
            Else
                Asignar(_id)
            End If
        End Using
    End Sub

    Private Sub Asignar(id As Integer)
        Dim cambio As Boolean = id <> _id
        _id = id
        If id = 0 OrElse Sesion.Ctx Is Nothing Then
            _cod.Text = ""
            _nom.Text = ""
        Else
            _cod.Text = Sesion.Ctx.CodigoCuenta(id)
            _nom.Text = Sesion.Ctx.NombreCuenta(id)
        End If
        If cambio Then RaiseEvent CuentaCambiada(Me, EventArgs.Empty)
    End Sub

    <Browsable(False), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)>
    Public Property CuentaId As Integer
        Get
            Return _id
        End Get
        Set(value As Integer)
            Asignar(value)
        End Set
    End Property

    Public Overrides Property Text As String
        Get
            Return _cod.Text
        End Get
        Set(value As String)
            _cod.Text = value
        End Set
    End Property
End Class

''' <summary>Búsqueda de cuentas al estilo Orion (código o descripción, con * como comodín) pero con filtrado en vivo.</summary>
Public Class CuentaPickerDialog
    Inherits Form

    Private ReadOnly _txt As New TextBox()
    Private ReadOnly _porCodigo As New RadioButton() With {.Text = "Por código", .Checked = True, .AutoSize = True}
    Private ReadOnly _porNombre As New RadioButton() With {.Text = "Por descripción", .AutoSize = True}
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _soloMov As Boolean
    Private _lista As List(Of DataRow)
    Public Property CuentaId As Integer

    Public Sub New(patronInicial As String, soloMovimiento As Boolean)
        _soloMov = soloMovimiento
        Tema.Aplicar(Me)
        Text = "Plan de cuentas - buscar cuenta"
        Size = New Size(760, 520)
        StartPosition = FormStartPosition.CenterParent
        MinimizeBox = False
        ShowInTaskbar = False
        KeyPreview = True
        Dim top As New Panel() With {.Dock = DockStyle.Top, .Height = 74, .Padding = New Padding(12, 10, 12, 4), .BackColor = Color.White}
        Dim l As New Label() With {.Text = "Escriba parte del código o del nombre. Use * como comodín (ej.: 2*, *sueldos*).", .AutoSize = True, .Location = New Point(12, 10), .ForeColor = Tema.Gris}
        _txt.Location = New Point(12, 36)
        _txt.Width = 330
        _porCodigo.Location = New Point(356, 38)
        _porNombre.Location = New Point(450, 38)
        top.Controls.AddRange({l, _txt, _porCodigo, _porNombre})
        Tema.EstiloGrid(_grid)
        Tema.ColTexto(_grid, "Codigo", "Código", 170)
        Tema.ColTexto(_grid, "Nombre", "Descripción", 360, True)
        Tema.ColTexto(_grid, "Moneda", "Mon.", 50)
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 46, .Padding = New Padding(12, 7, 12, 7)}
        Dim ok As Button = Tema.Boton("Seleccionar", Tema.TipoBoton.Primario, 110)
        ok.Dock = DockStyle.Right
        Dim cancelar As Button = Tema.Boton("Cancelar")
        cancelar.Dock = DockStyle.Right
        pie.Controls.Add(ok)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(cancelar)
        Controls.Add(_grid)
        Controls.Add(top)
        Controls.Add(pie)
        AddHandler _txt.TextChanged, Sub(o, e) Filtrar()
        AddHandler _porCodigo.CheckedChanged, Sub(o, e) Filtrar()
        AddHandler _grid.CellDoubleClick, Sub(o, e) If e.RowIndex >= 0 Then Aceptar()
        AddHandler ok.Click, Sub(o, e) Aceptar()
        AddHandler cancelar.Click, Sub(o, e) DialogResult = DialogResult.Cancel
        AddHandler Me.KeyDown, AddressOf Teclas
        AddHandler _txt.KeyDown, AddressOf Teclas
        AddHandler Shown, Sub(o, e)
                              _txt.Text = If(patronInicial, "").Trim()
                              _txt.Focus()
                              _txt.SelectionStart = _txt.Text.Length
                              Filtrar()
                          End Sub
    End Sub

    Private Sub Teclas(o As Object, e As KeyEventArgs)
        Select Case e.KeyCode
            Case Keys.Enter
                e.Handled = True
                e.SuppressKeyPress = True
                Aceptar()
            Case Keys.Escape
                DialogResult = DialogResult.Cancel
            Case Keys.Down
                If _grid.Rows.Count > 0 Then
                    Dim i As Integer = Math.Min(_grid.Rows.Count - 1, If(_grid.CurrentRow Is Nothing, 0, _grid.CurrentRow.Index + 1))
                    _grid.CurrentCell = _grid.Rows(i).Cells(0)
                    e.Handled = True
                End If
            Case Keys.Up
                If _grid.Rows.Count > 0 Then
                    Dim i As Integer = Math.Max(0, If(_grid.CurrentRow Is Nothing, 0, _grid.CurrentRow.Index - 1))
                    _grid.CurrentCell = _grid.Rows(i).Cells(0)
                    e.Handled = True
                End If
        End Select
    End Sub

    Private Sub Filtrar()
        Dim cs As New CuentaService(Sesion.Ctx)
        _lista = cs.Buscar(_txt.Text, _porCodigo.Checked, _soloMov)
        Dim dt As New DataTable()
        dt.Columns.Add("Id", GetType(Integer))
        dt.Columns.Add("Codigo", GetType(String))
        dt.Columns.Add("Nombre", GetType(String))
        dt.Columns.Add("Moneda", GetType(String))
        For Each r As DataRow In _lista.Take(1500)
            dt.Rows.Add(r.GetI("Id"), r.GetS("Codigo"), r.GetS("Nombre"), If(r.GetS("Moneda") = "USD", "$us", "Bs"))
        Next
        _grid.DataSource = dt
        If _grid.Rows.Count > 0 Then _grid.CurrentCell = _grid.Rows(0).Cells(0)
    End Sub

    Private Sub Aceptar()
        If _grid.CurrentRow Is Nothing Then Return
        CuentaId = ToInt(CType(_grid.CurrentRow.DataBoundItem, DataRowView)("Id"))
        DialogResult = DialogResult.OK
    End Sub
End Class

Public Class ColumnaBusqueda
    Public Property Campo As String
    Public Property Titulo As String
    Public Property Ancho As Integer = 120
    Public Property Importe As Boolean
    Public Sub New(campo As String, titulo As String, Optional ancho As Integer = 120, Optional importe As Boolean = False)
        Me.Campo = campo
        Me.Titulo = titulo
        Me.Ancho = ancho
        Me.Importe = importe
    End Sub
End Class

''' <summary>Diálogo genérico de búsqueda sobre una tabla (clientes, ítems, empleados...) con filtro "contiene".</summary>
Public Class BuscadorDialog
    Inherits Form

    Private ReadOnly _txt As New TextBox()
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _datos As DataTable
    Private ReadOnly _cols As List(Of ColumnaBusqueda)
    Public Property FilaElegida As DataRow

    Public Sub New(titulo As String, datos As DataTable, columnas As IEnumerable(Of ColumnaBusqueda), Optional inicial As String = "")
        _datos = datos
        _cols = columnas.ToList()
        Tema.Aplicar(Me)
        Text = titulo
        Size = New Size(820, 540)
        StartPosition = FormStartPosition.CenterParent
        MinimizeBox = False
        ShowInTaskbar = False
        KeyPreview = True
        Dim top As New Panel() With {.Dock = DockStyle.Top, .Height = 64, .Padding = New Padding(12, 10, 12, 4), .BackColor = Color.White}
        Dim l As New Label() With {.Text = "Escriba para filtrar (busca en todas las columnas). Enter o doble clic para seleccionar.", .AutoSize = True, .Location = New Point(12, 8), .ForeColor = Tema.Gris}
        _txt.Location = New Point(12, 30)
        _txt.Width = 420
        top.Controls.AddRange({l, _txt})
        Tema.EstiloGrid(_grid)
        For i As Integer = 0 To _cols.Count - 1
            Dim c As ColumnaBusqueda = _cols(i)
            If c.Importe Then
                Tema.ColImporte(_grid, c.Campo, c.Titulo, c.Ancho)
            ElseIf i = _cols.Count - 1 Then
                Tema.ColTexto(_grid, c.Campo, c.Titulo, c.Ancho, True)
            Else
                Tema.ColTexto(_grid, c.Campo, c.Titulo, c.Ancho)
            End If
        Next
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 46, .Padding = New Padding(12, 7, 12, 7)}
        Dim ok As Button = Tema.Boton("Seleccionar", Tema.TipoBoton.Primario, 110)
        ok.Dock = DockStyle.Right
        Dim cancelar As Button = Tema.Boton("Cancelar")
        cancelar.Dock = DockStyle.Right
        pie.Controls.Add(ok)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(cancelar)
        Controls.Add(_grid)
        Controls.Add(top)
        Controls.Add(pie)
        AddHandler _txt.TextChanged, Sub(o, e) Filtrar()
        AddHandler _grid.CellDoubleClick, Sub(o, e) If e.RowIndex >= 0 Then Aceptar()
        AddHandler ok.Click, Sub(o, e) Aceptar()
        AddHandler cancelar.Click, Sub(o, e) DialogResult = DialogResult.Cancel
        AddHandler Me.KeyDown, AddressOf Teclas
        AddHandler _txt.KeyDown, AddressOf Teclas
        AddHandler Shown, Sub(o, e)
                              _txt.Text = inicial
                              _txt.Focus()
                              _txt.SelectionStart = _txt.Text.Length
                              Filtrar()
                          End Sub
    End Sub

    Private Sub Teclas(o As Object, e As KeyEventArgs)
        Select Case e.KeyCode
            Case Keys.Enter
                e.Handled = True
                e.SuppressKeyPress = True
                Aceptar()
            Case Keys.Escape
                DialogResult = DialogResult.Cancel
            Case Keys.Down
                If _grid.Rows.Count > 0 Then
                    Dim i As Integer = Math.Min(_grid.Rows.Count - 1, If(_grid.CurrentRow Is Nothing, 0, _grid.CurrentRow.Index + 1))
                    _grid.CurrentCell = _grid.Rows(i).Cells(0)
                    e.Handled = True
                End If
            Case Keys.Up
                If _grid.Rows.Count > 0 Then
                    Dim i As Integer = Math.Max(0, If(_grid.CurrentRow Is Nothing, 0, _grid.CurrentRow.Index - 1))
                    _grid.CurrentCell = _grid.Rows(i).Cells(0)
                    e.Handled = True
                End If
        End Select
    End Sub

    Private Sub Filtrar()
        Dim t As String = _txt.Text.Trim().ToLowerInvariant()
        Dim res As DataTable = _datos.Clone()
        Dim n As Integer = 0
        For Each r As DataRow In _datos.Rows
            Dim ok As Boolean = t = ""
            If Not ok Then
                For Each c As ColumnaBusqueda In _cols
                    If ToStr(r(c.Campo)).ToLowerInvariant().Contains(t) Then
                        ok = True
                        Exit For
                    End If
                Next
            End If
            If ok Then
                res.ImportRow(r)
                n += 1
                If n >= 2000 Then Exit For
            End If
        Next
        _grid.DataSource = res
        If _grid.Rows.Count > 0 Then _grid.CurrentCell = _grid.Rows(0).Cells(0)
    End Sub

    Private Sub Aceptar()
        If _grid.CurrentRow Is Nothing Then Return
        FilaElegida = CType(_grid.CurrentRow.DataBoundItem, DataRowView).Row
        DialogResult = DialogResult.OK
    End Sub
End Class

''' <summary>Control de selección por búsqueda (cliente, proveedor, ítem, empleado...). F4, Enter o clic para buscar; Supr para limpiar.</summary>
Public Class PickerBusqueda
    Inherits Panel

    Private ReadOnly _txt As New TextBox()
    Private ReadOnly _btn As Button = Tema.Boton("…", Tema.TipoBoton.Secundario, 28)
    Private _id As Integer
    Private _proveedor As Func(Of DataTable)
    Private _cols As List(Of ColumnaBusqueda)
    Private _idCampo As String = "Id"
    Private _formato As Func(Of DataRow, String)
    Private _titulo As String = "Buscar"
    Public Event SeleccionCambiada As EventHandler
    Public Property FilaSeleccionada As DataRow

    Public Sub New()
        Height = 26
        Width = 360
        _txt.ReadOnly = True
        _txt.BackColor = Color.White
        _txt.Dock = DockStyle.Fill
        _btn.Dock = DockStyle.Right
        _btn.Height = 24
        Controls.Add(_txt)
        Controls.Add(_btn)
        AddHandler _btn.Click, Sub(o, e) Abrir("")
        AddHandler _txt.Click, Sub(o, e) Abrir("")
        AddHandler _txt.KeyDown, AddressOf TeclaDown
        AddHandler _txt.KeyPress, AddressOf TeclaPress
    End Sub

    Public Sub Configurar(titulo As String, proveedor As Func(Of DataTable), columnas As IEnumerable(Of ColumnaBusqueda), idCampo As String, formato As Func(Of DataRow, String))
        _titulo = titulo
        _proveedor = proveedor
        _cols = columnas.ToList()
        _idCampo = idCampo
        _formato = formato
    End Sub

    Private Sub TeclaDown(o As Object, e As KeyEventArgs)
        If e.KeyCode = Keys.F4 OrElse e.KeyCode = Keys.F2 OrElse e.KeyCode = Keys.Enter OrElse e.KeyCode = Keys.Down Then
            e.Handled = True
            e.SuppressKeyPress = True
            Abrir("")
        ElseIf e.KeyCode = Keys.Delete OrElse e.KeyCode = Keys.Back Then
            e.Handled = True
            Limpiar()
        End If
    End Sub

    Private Sub TeclaPress(o As Object, e As KeyPressEventArgs)
        If Not Char.IsControl(e.KeyChar) Then
            e.Handled = True
            Abrir(e.KeyChar.ToString())
        End If
    End Sub

    Public Sub Abrir(inicial As String)
        If _proveedor Is Nothing Then Return
        Dim dt As DataTable
        Try
            dt = _proveedor()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
            Return
        End Try
        Using d As New BuscadorDialog(_titulo, dt, _cols, inicial)
            If d.ShowDialog(FindForm()) = DialogResult.OK Then Asignar(d.FilaElegida)
        End Using
    End Sub

    Private Sub Asignar(r As DataRow)
        Dim nuevo As Integer = If(r Is Nothing, 0, ToInt(r(_idCampo)))
        Dim cambio As Boolean = nuevo <> _id
        _id = nuevo
        FilaSeleccionada = r
        _txt.Text = If(r Is Nothing, "", _formato(r))
        If cambio Then RaiseEvent SeleccionCambiada(Me, EventArgs.Empty)
    End Sub

    Public Sub Limpiar()
        Asignar(Nothing)
    End Sub

    <Browsable(False), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)>
    Public Property SeleccionId As Integer
        Get
            Return _id
        End Get
        Set(value As Integer)
            If value = 0 OrElse _proveedor Is Nothing Then
                Asignar(Nothing)
                Return
            End If
            Dim dt As DataTable = _proveedor()
            Dim r As DataRow = dt.Rows.Cast(Of DataRow)().FirstOrDefault(Function(x) ToInt(x(_idCampo)) = value)
            Asignar(r)
        End Set
    End Property
End Class
