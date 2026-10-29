Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Introducción y modificación de comprobantes: captura por teclado, bimonetaria, con asientos de facturas IVA.</summary>
Public Class ComprobanteForm
    Inherits FormBase

    Private ReadOnly _tipo As New LookupCombo()
    Private ReadOnly _lblNumero As New Label()
    Private ReadOnly _lblEstado As New Label()
    Private ReadOnly _fecha As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _tc As New CampoImporte() With {.Width = 70}
    Private ReadOnly _moneda As New LookupCombo() With {.Width = 130}
    Private ReadOnly _glosa As New TextBox() With {.MaxLength = 255}
    Private ReadOnly _ref As New TextBox() With {.MaxLength = 80}
    Private ReadOnly _cheque As New TextBox() With {.MaxLength = 30, .Width = 110}
    Private ReadOnly _banco As New TextBox() With {.MaxLength = 60, .Width = 170}
    Private ReadOnly _grid As New GridEntrada()
    Private ReadOnly _lblDebe As New Label()
    Private ReadOnly _lblHaber As New Label()
    Private ReadOnly _lblDif As New Label()
    Private ReadOnly _lblSon As New Label()
    Private ReadOnly _chkImprimir As New CheckBox() With {.Text = "Imprimir al guardar", .AutoSize = True}
    Private ReadOnly _btnAnular As Button = Tema.Boton("Anular", Tema.TipoBoton.Peligro, 80)
    Private ReadOnly _btnGuardar As Button = Tema.Boton("Guardar (F10)", Tema.TipoBoton.Primario, 118)
    Private ReadOnly _btnFacturas As Button = Tema.Boton("Facturas IVA…", Tema.TipoBoton.Secundario, 120)
    Private ReadOnly _btnCuadrar As Button = Tema.Boton("Cuadrar (F9)", Tema.TipoBoton.Secundario, 104)
    Private ReadOnly _vs As New VoucherService(Sesion.Ctx)
    Private _facturas As New List(Of FacturaDto)
    Private _id As Integer
    Private _estado As String = "N"
    Private _origen As String = "MAN"
    Private _origenId As Integer
    Private _cargando As Boolean
    Private _tcManual As Boolean
    Private _colCod As DataGridViewTextBoxColumn
    Private _colCuenta As DataGridViewTextBoxColumn
    Private _colGlosa As DataGridViewTextBoxColumn
    Private _colDebe As DataGridViewTextBoxColumn
    Private _colHaber As DataGridViewTextBoxColumn
    Private _colEqD As DataGridViewTextBoxColumn
    Private _colEqH As DataGridViewTextBoxColumn
    Private _colCentro As DataGridViewComboBoxColumn
    Private _tieneCentros As Boolean
    Private _idInicial As Integer

    Public Sub New()
        Text = "Comprobantes"
    End Sub

    Public Sub New(id As Integer)
        Me.New()
        _idInicial = id
    End Sub

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Comprobante"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Dim banner As Panel = Tema.Banner("Introducción de comprobantes", "Ingresos, egresos y traspasos con partida doble. Enter avanza de campo · F4 busca cuentas · F9 cuadra · F10 guarda")
        ' ---- cabecera ----
        Dim cab As New Panel() With {.Dock = DockStyle.Top, .Height = 118, .BackColor = Color.White, .Padding = New Padding(16, 8, 16, 4)}
        AddHandler cab.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, cab.Height - 1, cab.Width, cab.Height - 1)
        Dim tipos As DataTable = _vs.Tipos()
        Dim tt As New DataTable()
        tt.Columns.Add("Id", GetType(String))
        tt.Columns.Add("Texto", GetType(String))
        For Each r As DataRow In tipos.Rows
            tt.Rows.Add(r.GetS("Codigo"), r.GetS("Nombre"))
        Next
        _tipo.DropDownStyle = ComboBoxStyle.DropDownList
        _tipo.AutoCompleteMode = AutoCompleteMode.None
        _tipo.DisplayMember = "Texto"
        _tipo.ValueMember = "Id"
        _tipo.DataSource = tt
        _tipo.Width = 160
        _moneda.CargarLista({New KeyValuePair(Of String, String)("BS", "Bolivianos (Bs)"), New KeyValuePair(Of String, String)("USD", "Dólares ($us)")})
        _lblNumero.Font = Tema.FuenteGrande
        _lblNumero.ForeColor = Tema.Azul
        _lblNumero.AutoSize = True
        _lblEstado.AutoSize = True
        _lblEstado.Font = Tema.FuenteNegrita
        PonerEnCab(cab, "Tipo", _tipo, 0, 0)
        _lblNumero.Location = New Point(206, 12)
        cab.Controls.Add(_lblNumero)
        PonerEnCab(cab, "Fecha", _fecha, 410, 0)
        PonerEnCab(cab, "T.C.", _tc, 560, 0)
        PonerEnCab(cab, "Moneda", _moneda, 660, 0)
        _lblEstado.Location = New Point(820, 12)
        cab.Controls.Add(_lblEstado)
        _glosa.Width = 640
        PonerEnCab(cab, "Glosa general", _glosa, 0, 1)
        _ref.Width = 200
        PonerEnCab(cab, "Recibido / Cancelado", _ref, 740, 1)
        PonerEnCab(cab, "Cheque Nº", _cheque, 0, 2)
        PonerEnCab(cab, "Banco", _banco, 220, 2)
        Dim bBuscar As Button = Tema.Boton("Buscar…", Tema.TipoBoton.Secundario, 84)
        Dim bAnt As Button = Tema.Boton("◀", Tema.TipoBoton.Secundario, 36)
        Dim bSig As Button = Tema.Boton("▶", Tema.TipoBoton.Secundario, 36)
        Dim bNuevo As Button = Tema.Boton("Nuevo (Ctrl+N)", Tema.TipoBoton.Secundario, 112)
        bBuscar.Location = New Point(560, 80)
        bAnt.Location = New Point(650, 80)
        bSig.Location = New Point(692, 80)
        bNuevo.Location = New Point(740, 80)
        cab.Controls.AddRange({bBuscar, bAnt, bSig, bNuevo})
        ' ---- pie ----
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 112, .BackColor = Color.White, .Padding = New Padding(16, 8, 16, 8)}
        AddHandler pie.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, 0, pie.Width, 0)
        For Each l As Label In {_lblDebe, _lblHaber, _lblDif}
            l.AutoSize = True
            l.Font = Tema.FuenteGrande
        Next
        _lblDebe.Location = New Point(16, 8)
        _lblHaber.Location = New Point(260, 8)
        _lblDif.Location = New Point(520, 8)
        _lblSon.Location = New Point(16, 38)
        _lblSon.AutoSize = True
        _lblSon.ForeColor = Tema.Gris
        _lblSon.Font = Tema.FuenteNegrita
        Dim botones As New FlowLayoutPanel() With {.Location = New Point(12, 66), .Size = New Size(1100, 40), .WrapContents = False}
        Dim bImprimir As Button = Tema.Boton("Imprimir", Tema.TipoBoton.Secundario, 84)
        Dim bCopiar As Button = Tema.Boton("Copiar a otra fecha", Tema.TipoBoton.Secundario, 140)
        botones.Controls.AddRange({_btnGuardar, _btnCuadrar, _btnFacturas, bImprimir, bCopiar, _btnAnular})
        _chkImprimir.Margin = New Padding(12, 8, 0, 0)
        botones.Controls.Add(_chkImprimir)
        pie.Controls.AddRange({_lblDebe, _lblHaber, _lblDif, _lblSon, botones})
        ' ---- grilla ----
        Tema.EstiloGrid(_grid, True)
        _grid.AllowUserToAddRows = True
        _grid.AllowUserToDeleteRows = True
        _grid.RowHeadersVisible = True
        _grid.RowHeadersWidth = 28
        _grid.RowHeadersDefaultCellStyle.BackColor = Tema.AzulClaro
        _grid.SelectionMode = DataGridViewSelectionMode.CellSelect
        _grid.MultiSelect = False
        _grid.EditMode = DataGridViewEditMode.EditOnEnter
        _grid.ColumnHeadersHeight = 30
        _grid.AutoSizeRowsMode = DataGridViewAutoSizeRowsMode.None
        _colCod = Tema.ColTexto(_grid, "cod", "Código de cuenta", 150)
        _colCuenta = Tema.ColTexto(_grid, "cuenta", "Cuenta", 300, True)
        _colCuenta.ReadOnly = True
        _colCuenta.DefaultCellStyle.ForeColor = Tema.Gris
        _colGlosa = Tema.ColTexto(_grid, "glosa", "Glosa de la línea (opcional)", 230)
        _colDebe = Tema.ColImporte(_grid, "debe", "Debe", 120)
        _colHaber = Tema.ColImporte(_grid, "haber", "Haber", 120)
        _colEqD = Tema.ColImporte(_grid, "eqd", "Debe $us", 90)
        _colEqH = Tema.ColImporte(_grid, "eqh", "Haber $us", 90)
        For Each c As DataGridViewTextBoxColumn In {_colEqD, _colEqH}
            c.ReadOnly = True
            c.DefaultCellStyle.ForeColor = Tema.Gris
            c.DefaultCellStyle.BackColor = Color.FromArgb(246, 247, 249)
            c.SortMode = DataGridViewColumnSortMode.NotSortable
        Next
        For Each c As DataGridViewColumn In _grid.Columns
            c.SortMode = DataGridViewColumnSortMode.NotSortable
        Next
        _colCentro = New DataGridViewComboBoxColumn() With {.Name = "centro", .HeaderText = "Centro de costo", .Width = 140, .FlatStyle = FlatStyle.Flat, .DisplayStyle = DataGridViewComboBoxDisplayStyle.Nothing}
        Dim cc As DataTable = Ctx.Db.Query("SELECT Id, Codigo, Nombre FROM CentroCosto WHERE Activo=1 ORDER BY Codigo")
        _tieneCentros = cc.Rows.Count > 0
        If _tieneCentros Then
            Dim cd As New DataTable()
            cd.Columns.Add("Id", GetType(Integer))
            cd.Columns.Add("Texto", GetType(String))
            cd.Rows.Add(0, "")
            For Each r As DataRow In cc.Rows
                cd.Rows.Add(r.GetI("Id"), r.GetS("Codigo") & " " & r.GetS("Nombre"))
            Next
            _colCentro.DataSource = cd
            _colCentro.DisplayMember = "Texto"
            _colCentro.ValueMember = "Id"
            _grid.Columns.Add(_colCentro)
        End If
        Controls.Add(_grid)
        Controls.Add(pie)
        Controls.Add(cab)
        Controls.Add(banner)
        ' ---- eventos ----
        AddHandler _tipo.SelectionChangeCommitted, Sub(o, ev) If _id = 0 Then ActualizarNumero()
        AddHandler _fecha.ValueChanged, Sub(o, ev) FechaCambio()
        AddHandler _tc.ValorCambiado, Sub(o, ev)
                                          If _tc.Focused Then _tcManual = True
                                          Recalcular()
                                      End Sub
        AddHandler _moneda.SelectionChangeCommitted, Sub(o, ev) Recalcular()
        AddHandler _grid.CellEndEdit, AddressOf FinEdicionCelda
        AddHandler _grid.CellParsing, AddressOf ParsearCelda
        AddHandler _grid.EditingControlShowing, AddressOf MostrarEditor
        AddHandler _grid.RowsRemoved, Sub(o, ev) Recalcular()
        AddHandler _grid.KeyDown, AddressOf TeclaGrid
        AddHandler _grid.DataError, Sub(o, ev) ev.ThrowException = False
        AddHandler _btnGuardar.Click, Sub(o, ev) Guardar()
        AddHandler _btnCuadrar.Click, Sub(o, ev) Cuadrar()
        AddHandler _btnFacturas.Click, Sub(o, ev) AgregarFactura()
        AddHandler _btnAnular.Click, Sub(o, ev) Anular()
        AddHandler bImprimir.Click, Sub(o, ev) Imprimir()
        AddHandler bCopiar.Click, Sub(o, ev) Copiar()
        AddHandler bNuevo.Click, Sub(o, ev) Nuevo()
        AddHandler bBuscar.Click, Sub(o, ev) Buscar()
        AddHandler bAnt.Click, Sub(o, ev) Navegar(False)
        AddHandler bSig.Click, Sub(o, ev) Navegar(True)
        AddHandler KeyDown, AddressOf TeclaForm
        _fecha.MinDate = Ctx.Gestion.FechaInicio
        _fecha.MaxDate = Ctx.Gestion.FechaFin
        If _idInicial <> 0 Then Cargar(_idInicial) Else Nuevo()
    End Sub

    Private Sub PonerEnCab(cab As Panel, titulo As String, c As Control, x As Integer, fila As Integer)
        Dim y As Integer = 10 + fila * 34
        If fila = 0 Then
            Dim l As New Label() With {.Text = titulo, .AutoSize = True, .Location = New Point(x + If(x = 0, 0, 0), y + 4)}
            cab.Controls.Add(l)
            c.Location = New Point(x + l.PreferredWidth + 6, y)
        Else
            Dim l As New Label() With {.Text = titulo, .AutoSize = True, .Location = New Point(x, y + 4)}
            cab.Controls.Add(l)
            c.Location = New Point(x + l.PreferredWidth + 8, y)
        End If
        cab.Controls.Add(c)
    End Sub

    ' ---------- Estado del comprobante ----------
    Private ReadOnly Property Editable As Boolean
        Get
            Return (_estado = "N" AndAlso Sesion.Puede("CONT.COMPROBANTES")) OrElse (_estado = "V" AndAlso Sesion.Puede("CONT.MODIFICAR"))
        End Get
    End Property

    Private Sub AplicarEstado()
        Dim ed As Boolean = Editable AndAlso Ctx.Gestion.Abierta
        _grid.ReadOnly = Not ed
        _grid.AllowUserToAddRows = ed
        _grid.AllowUserToDeleteRows = ed
        For Each c As Control In New Control() {_tipo, _fecha, _tc, _moneda, _glosa, _ref, _cheque, _banco}
            c.Enabled = ed
        Next
        If _id <> 0 Then _tipo.Enabled = False
        _btnGuardar.Enabled = ed
        _btnCuadrar.Enabled = ed
        _btnFacturas.Enabled = ed
        _btnAnular.Enabled = _estado = "V" AndAlso Sesion.Puede("CONT.ANULAR") AndAlso Ctx.Gestion.Abierta
        Select Case _estado
            Case "A"
                _lblEstado.Text = "ANULADO"
                _lblEstado.ForeColor = Tema.Rojo
            Case "V"
                _lblEstado.Text = If(_origen <> "MAN", "VIGENTE (generado por " & _origen & ")", "VIGENTE")
                _lblEstado.ForeColor = Tema.Verde
            Case Else
                _lblEstado.Text = "NUEVO"
                _lblEstado.ForeColor = Tema.AzulMedio
        End Select
    End Sub

    Public Sub Nuevo()
        Dim codTipo As String = If(_tipo.SelectedValue Is Nothing, "I", ToStr(_tipo.SelectedValue))
        Dim fecha As Date = If(_id = 0 AndAlso _fecha.Value.Date >= _fecha.MinDate, _fecha.Value.Date, If(Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin, Date.Today, Ctx.Gestion.FechaInicio))
        _cargando = True
        _id = 0
        _estado = "N"
        _origen = "MAN"
        _origenId = 0
        _facturas = New List(Of FacturaDto)
        _tipo.SelectedValue = codTipo
        _fecha.Value = fecha
        _tcManual = False
        _tc.Valor = Svc.TipoCambio.Dolar(fecha)
        _moneda.ValorTexto = "BS"
        _glosa.Text = ""
        _ref.Text = ""
        _cheque.Text = ""
        _banco.Text = ""
        _grid.Rows.Clear()
        _cargando = False
        ActualizarNumero()
        AplicarEstado()
        Recalcular()
        _glosa.Focus()
    End Sub

    Private Sub ActualizarNumero()
        If _id <> 0 Then Return
        Try
            Dim n As Integer = _vs.SiguienteNumero(ToStr(_tipo.SelectedValue), _fecha.Value.Date)
            _lblNumero.Text = "Nº " & n & If(Ctx.Gestion.CorrelativoMensual, "  ·  " & NombreMes(_fecha.Value.Month), "")
        Catch
            _lblNumero.Text = ""
        End Try
    End Sub

    Private Sub FechaCambio()
        If _cargando Then Return
        If _id = 0 Then
            If Not _tcManual Then _tc.Valor = Svc.TipoCambio.Dolar(_fecha.Value.Date)
            ActualizarNumero()
        End If
        Recalcular()
    End Sub

    Public Sub Cargar(id As Integer)
        Dim v As Voucher = _vs.Cargar(id)
        If v Is Nothing Then
            Msg.Aviso("El comprobante no existe.")
            Return
        End If
        _cargando = True
        _id = id
        _estado = v.Estado
        _origen = v.Origen
        _origenId = v.OrigenId
        _facturas = New List(Of FacturaDto)
        _tipo.SelectedValue = v.TipoCodigo
        _fecha.Value = v.Fecha
        _tcManual = True
        _tc.Valor = v.TC
        _moneda.ValorTexto = v.Moneda
        _glosa.Text = v.Glosa
        _ref.Text = v.Referencia
        _cheque.Text = v.Cheque
        _banco.Text = v.Banco
        _grid.Rows.Clear()
        For Each l As VoucherLine In v.Lines
            Dim i As Integer = _grid.Rows.Add()
            Dim r As DataGridViewRow = _grid.Rows(i)
            PonerCuenta(r, l.CuentaId)
            r.Cells(_colGlosa.Index).Value = l.Glosa
            If l.Debe <> 0D Then r.Cells(_colDebe.Index).Value = l.Debe
            If l.Haber <> 0D Then r.Cells(_colHaber.Index).Value = l.Haber
            If _tieneCentros Then r.Cells(_colCentro.Index).Value = l.CentroCostoId
        Next
        _lblNumero.Text = v.TipoNombre & " Nº " & v.Numero & If(v.Mes > 0, "  ·  " & NombreMes(v.Mes), "")
        _cargando = False
        AplicarEstado()
        Recalcular()
    End Sub

    ' ---------- Grilla ----------
    Private Sub PonerCuenta(r As DataGridViewRow, cuentaId As Integer)
        If cuentaId = 0 Then
            r.Cells(_colCod.Index).Value = Nothing
            r.Cells(_colCod.Index).Tag = Nothing
            r.Cells(_colCuenta.Index).Value = Nothing
        Else
            r.Cells(_colCod.Index).Value = Ctx.CodigoCuenta(cuentaId)
            r.Cells(_colCod.Index).Tag = cuentaId
            r.Cells(_colCuenta.Index).Value = Ctx.NombreCuenta(cuentaId)
        End If
    End Sub

    Private Function CuentaDeFila(r As DataGridViewRow) As Integer
        Dim t As Object = r.Cells(_colCod.Index).Tag
        Return If(t Is Nothing, 0, CInt(t))
    End Function

    Private Sub ResolverCuenta(r As DataGridViewRow)
        Dim txt As String = ToStr(r.Cells(_colCod.Index).Value).Trim()
        If txt = "" Then
            PonerCuenta(r, 0)
            Return
        End If
        Dim c As DataRow = Ctx.CuentaPorCodigo(txt)
        If c IsNot Nothing AndAlso c.GetF("EsMovimiento") AndAlso c.GetF("Activa") Then
            PonerCuenta(r, c.GetI("Id"))
            Return
        End If
        BuscarCuentaEn(r, txt)
    End Sub

    Private Sub BuscarCuentaEn(r As DataGridViewRow, patron As String)
        Using d As New CuentaPickerDialog(patron, True)
            If d.ShowDialog(FindForm()) = DialogResult.OK Then
                PonerCuenta(r, d.CuentaId)
            Else
                PonerCuenta(r, CuentaDeFila(r))
            End If
        End Using
    End Sub

    Private Sub FinEdicionCelda(o As Object, e As DataGridViewCellEventArgs)
        If _cargando OrElse e.RowIndex < 0 Then Return
        Dim r As DataGridViewRow = _grid.Rows(e.RowIndex)
        If r.IsNewRow Then Return
        If e.ColumnIndex = _colCod.Index Then
            ResolverCuenta(r)
        ElseIf e.ColumnIndex = _colDebe.Index Then
            If ToDec(r.Cells(_colDebe.Index).Value) <> 0D Then r.Cells(_colHaber.Index).Value = Nothing
        ElseIf e.ColumnIndex = _colHaber.Index Then
            If ToDec(r.Cells(_colHaber.Index).Value) <> 0D Then r.Cells(_colDebe.Index).Value = Nothing
        End If
        Recalcular()
    End Sub

    Private Sub ParsearCelda(o As Object, e As DataGridViewCellParsingEventArgs)
        If e.ColumnIndex <> _colDebe.Index AndAlso e.ColumnIndex <> _colHaber.Index Then Return
        Dim d As Decimal
        If Numeros.Parse(ToStr(e.Value), d) Then
            e.Value = If(d = 0D, CObj(Nothing), CObj(d))
        Else
            e.Value = Nothing
        End If
        e.ParsingApplied = True
    End Sub

    Private Sub MostrarEditor(o As Object, e As DataGridViewEditingControlShowingEventArgs)
        Dim tb As TextBox = TryCast(e.Control, TextBox)
        If tb Is Nothing Then Return
        RemoveHandler tb.KeyPress, AddressOf TeclaEditor
        RemoveHandler tb.KeyDown, AddressOf TeclaEditorDown
        AddHandler tb.KeyDown, AddressOf TeclaEditorDown
        If _grid.CurrentCell.ColumnIndex = _colDebe.Index OrElse _grid.CurrentCell.ColumnIndex = _colHaber.Index Then
            AddHandler tb.KeyPress, AddressOf TeclaEditor
            tb.SelectAll()
        ElseIf _grid.CurrentCell.ColumnIndex = _colCod.Index Then
            tb.SelectAll()
        End If
    End Sub

    Private Sub TeclaEditor(o As Object, e As KeyPressEventArgs)
        If Char.IsControl(e.KeyChar) OrElse Char.IsDigit(e.KeyChar) OrElse e.KeyChar = "."c OrElse e.KeyChar = ","c Then Return
        e.Handled = True
    End Sub

    Private Sub TeclaEditorDown(o As Object, e As KeyEventArgs)
        If _grid.CurrentCell Is Nothing Then Return
        If e.KeyCode = Keys.F4 AndAlso _grid.CurrentCell.ColumnIndex = _colCod.Index Then
            e.Handled = True
            Dim r As DataGridViewRow = _grid.CurrentRow
            Dim txt As String = CType(o, TextBox).Text
            _grid.EndEdit()
            BuscarCuentaEn(r, txt)
            Recalcular()
        End If
    End Sub

    Private Sub TeclaGrid(o As Object, e As KeyEventArgs)
        If e.KeyCode = Keys.F4 AndAlso _grid.CurrentCell IsNot Nothing AndAlso _grid.CurrentCell.ColumnIndex = _colCod.Index AndAlso _grid.CurrentRow IsNot Nothing AndAlso Not _grid.CurrentRow.IsNewRow Then
            e.Handled = True
            BuscarCuentaEn(_grid.CurrentRow, ToStr(_grid.CurrentCell.Value))
            Recalcular()
        ElseIf e.KeyCode = Keys.F4 AndAlso _grid.CurrentCell IsNot Nothing AndAlso _grid.CurrentRow IsNot Nothing AndAlso _grid.CurrentRow.IsNewRow Then
            e.Handled = True
            _grid.CurrentCell = _grid.Rows(_grid.Rows.Count - 1).Cells(_colCod.Index)
            _grid.BeginEdit(True)
            SendKeys.Send("{F4}")
        End If
    End Sub

    Private Sub TeclaForm(o As Object, e As KeyEventArgs)
        If e.KeyCode = Keys.F10 OrElse (e.Control AndAlso e.KeyCode = Keys.G) Then
            e.Handled = True
            Guardar()
        ElseIf e.KeyCode = Keys.F9 Then
            e.Handled = True
            Cuadrar()
        ElseIf e.Control AndAlso e.KeyCode = Keys.N Then
            e.Handled = True
            Nuevo()
        ElseIf e.Control AndAlso e.KeyCode = Keys.P Then
            e.Handled = True
            Imprimir()
        End If
    End Sub

    Private Function Moneda_() As String
        Return If(_moneda.ValorTexto = "", "BS", _moneda.ValorTexto)
    End Function

    Private Sub Recalcular()
        If _cargando Then Return
        Dim usd As Boolean = Moneda_() = "USD"
        Dim tc As Decimal = _tc.Valor
        If tc <= 0D Then tc = 1D
        _colEqD.HeaderText = If(usd, "Debe Bs", "Debe $us")
        _colEqH.HeaderText = If(usd, "Haber Bs", "Haber $us")
        Dim td As Decimal, th As Decimal
        For Each r As DataGridViewRow In _grid.Rows
            If r.IsNewRow Then Continue For
            Dim d As Decimal = ToDec(r.Cells(_colDebe.Index).Value), h As Decimal = ToDec(r.Cells(_colHaber.Index).Value)
            td += d : th += h
            r.Cells(_colEqD.Index).Value = If(d = 0D, CObj(Nothing), CObj(If(usd, (d * tc).R2(), (d / tc).R2())))
            r.Cells(_colEqH.Index).Value = If(h = 0D, CObj(Nothing), CObj(If(usd, (h * tc).R2(), (h / tc).R2())))
        Next
        Dim sim As String = If(usd, "$us ", "Bs ")
        _lblDebe.Text = "Total Debe: " & sim & td.ToString("N2", FormatoVal.Cultura)
        _lblHaber.Text = "Total Haber: " & sim & th.ToString("N2", FormatoVal.Cultura)
        Dim dif As Decimal = td - th
        If Math.Abs(dif) < 0.005D Then
            _lblDif.Text = If(td = 0D, "", "✔ Comprobante cuadrado")
            _lblDif.ForeColor = Tema.Verde
        Else
            _lblDif.Text = "Diferencia: " & sim & dif.ToString("N2", FormatoVal.Cultura)
            _lblDif.ForeColor = Tema.Rojo
        End If
        Dim totBs As Decimal = If(usd, (td * tc).R2(), td)
        _lblSon.Text = If(td > 0D, "Son: " & NumeroLetras.Importe(td, Moneda_()), "")
    End Sub

    Private Sub Cuadrar()
        _grid.EndEdit()
        Dim td As Decimal, th As Decimal
        For Each r As DataGridViewRow In _grid.Rows
            If r.IsNewRow Then Continue For
            td += ToDec(r.Cells(_colDebe.Index).Value)
            th += ToDec(r.Cells(_colHaber.Index).Value)
        Next
        Dim dif As Decimal = td - th
        If Math.Abs(dif) < 0.005D Then Return
        Dim fila As DataGridViewRow = _grid.CurrentRow
        If fila Is Nothing OrElse fila.IsNewRow OrElse ToDec(fila.Cells(_colDebe.Index).Value) <> 0D OrElse ToDec(fila.Cells(_colHaber.Index).Value) <> 0D Then
            Dim i As Integer = _grid.Rows.Add()
            fila = _grid.Rows(i)
        End If
        If dif > 0D Then fila.Cells(_colHaber.Index).Value = dif Else fila.Cells(_colDebe.Index).Value = -dif
        Recalcular()
        _grid.CurrentCell = fila.Cells(_colCod.Index)
        _grid.BeginEdit(True)
    End Sub

    ' ---------- Facturas IVA ----------
    Private Sub AgregarFactura()
        _grid.EndEdit()
        Dim codTipo As String = ToStr(_tipo.SelectedValue)
        If codTipo <> "E" AndAlso codTipo <> "I" Then
            Msg.Info("Las facturas se registran en comprobantes de EGRESO (libro de compras) o de INGRESO (libro de ventas).")
            Return
        End If
        If Moneda_() <> "BS" Then
            Msg.Info("Las facturas IVA se registran en bolivianos. Cambie la moneda del comprobante a Bolivianos.")
            Return
        End If
        Dim libro As String = If(codTipo = "E", "C", "V")
        Using d As New FacturaDialog(libro, True, Nothing, _fecha.Value.Date)
            If d.ShowDialog(FindForm()) <> DialogResult.OK Then Return
            Dim f As FacturaDto = d.Resultado
            Try
                Dim fs As New FacturaService(Ctx)
                Dim glosa As String = If(libro = "C", "Compra", "Venta") & " fact. " & f.NroFactura & " " & f.RazonSocial
                Dim lineas As List(Of VoucherLine) = If(libro = "C", fs.LineasCompra(f, d.CuentaId, glosa), fs.LineasVenta(f, d.CuentaId, glosa))
                If libro = "V" AndAlso d.ConIt Then lineas.AddRange(fs.LineasIt(f.ImporteTotal, "IT " & glosa))
                For Each l As VoucherLine In lineas
                    AgregarLinea(l)
                Next
                ' contrapartida sugerida (caja): se puede cambiar por banco u otra cuenta
                Dim dif As Decimal = TotalDebe() - TotalHaber()
                Dim caja As Integer = Ctx.CuentaParamOpcional(ParamKeys.CtaCaja)
                If Math.Abs(dif) > 0.005D AndAlso caja <> 0 Then
                    AgregarLinea(If(dif > 0D, VoucherLine.Hab(caja, dif, glosa), VoucherLine.Deb(caja, -dif, glosa)))
                End If
                _facturas.Add(f)
                If _glosa.Text.Trim() = "" Then _glosa.Text = glosa
                Recalcular()
            Catch ex As Exception
                Msg.ErrorMsg(ex)
            End Try
        End Using
    End Sub

    Private Sub AgregarLinea(l As VoucherLine)
        Dim i As Integer = _grid.Rows.Add()
        Dim r As DataGridViewRow = _grid.Rows(i)
        PonerCuenta(r, l.CuentaId)
        r.Cells(_colGlosa.Index).Value = l.Glosa
        If l.Debe <> 0D Then r.Cells(_colDebe.Index).Value = l.Debe
        If l.Haber <> 0D Then r.Cells(_colHaber.Index).Value = l.Haber
    End Sub

    Private Function TotalDebe() As Decimal
        Dim t As Decimal
        For Each r As DataGridViewRow In _grid.Rows
            If Not r.IsNewRow Then t += ToDec(r.Cells(_colDebe.Index).Value)
        Next
        Return t
    End Function

    Private Function TotalHaber() As Decimal
        Dim t As Decimal
        For Each r As DataGridViewRow In _grid.Rows
            If Not r.IsNewRow Then t += ToDec(r.Cells(_colHaber.Index).Value)
        Next
        Return t
    End Function

    ' ---------- Guardar ----------
    Private Function Armar() As Voucher
        _grid.EndEdit()
        Dim v As New Voucher()
        v.Id = _id
        v.TipoCodigo = ToStr(_tipo.SelectedValue)
        v.Fecha = _fecha.Value.Date
        v.TC = _tc.Valor
        v.Moneda = Moneda_()
        v.Glosa = _glosa.Text.Trim()
        v.Referencia = _ref.Text.Trim()
        v.Cheque = _cheque.Text.Trim()
        v.Banco = _banco.Text.Trim()
        v.Origen = _origen
        v.OrigenId = _origenId
        Dim n As Integer = 0
        For Each r As DataGridViewRow In _grid.Rows
            If r.IsNewRow Then Continue For
            n += 1
            Dim d As Decimal = ToDec(r.Cells(_colDebe.Index).Value), h As Decimal = ToDec(r.Cells(_colHaber.Index).Value)
            Dim cta As Integer = CuentaDeFila(r)
            If cta = 0 AndAlso d = 0D AndAlso h = 0D Then Continue For
            If cta = 0 Then Throw New InvalidOperationException("La línea " & n & " tiene importe pero no tiene cuenta.")
            Dim l As New VoucherLine With {.CuentaId = cta, .Glosa = ToStr(r.Cells(_colGlosa.Index).Value), .Debe = d, .Haber = h}
            If _tieneCentros Then l.CentroCostoId = ToInt(r.Cells(_colCentro.Index).Value)
            v.Lines.Add(l)
        Next
        If _id = 0 Then v.Facturas.AddRange(_facturas)
        Return v
    End Function

    Private Sub Guardar()
        If Not Editable Then Return
        Dim v As Voucher
        Try
            v = Armar()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
            Return
        End Try
        If v.Glosa = "" AndAlso Not Msg.Confirmar("El comprobante no tiene glosa. ¿Desea guardarlo así?") Then
            _glosa.Focus()
            Return
        End If
        Try
            Using Msg.Cursor_(True)
                Dim tcs As New TipoCambioService(Ctx)
                If Not tcs.Existe(v.Fecha) AndAlso _tcManual AndAlso Math.Abs(tcs.Dolar(v.Fecha) - v.TC) > 0.0001D Then
                    If Msg.Confirmar("No existe tipo de cambio guardado para el " & v.Fecha.ToString("dd/MM/yyyy") & "." & vbCrLf & "¿Desea guardar " & v.TC.ToString("0.00", FormatoVal.Cultura) & " como tipo de cambio de esa fecha?") Then tcs.Guardar(v.Fecha, v.TC, 0D)
                End If
                Dim idGuardado As Integer = _vs.Guardar(v)
                Dim num As String = v.TipoCodigo & "-" & v.Numero
                If _chkImprimir.Checked Then Informes.Abrir("comprobante", New Dictionary(Of String, Object) From {{"id", idGuardado}}, False)
                If _id = 0 Then
                    Nuevo()
                    _lblEstado.Text = "Guardado: " & num
                    _lblEstado.ForeColor = Tema.Verde
                Else
                    Cargar(idGuardado)
                End If
            End Using
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub Anular()
        If _id = 0 OrElse _estado <> "V" Then Return
        Dim motivo As String = Msg.Pedir("Motivo de la anulación del comprobante (quedará registrado):", "Anular comprobante")
        If String.IsNullOrWhiteSpace(motivo) Then Return
        If Intentar(Sub() _vs.Anular(_id, motivo)) Then Cargar(_id)
    End Sub

    Private Sub Imprimir()
        If _id = 0 Then
            Msg.Aviso("Guarde el comprobante antes de imprimirlo.")
            Return
        End If
        Informes.Abrir("comprobante", New Dictionary(Of String, Object) From {{"id", _id}}, False)
    End Sub

    Private Sub Copiar()
        If _id = 0 Then Return
        Dim f As String = Msg.Pedir("Fecha del nuevo comprobante (dd/MM/aaaa):", "Copiar comprobante", Date.Today.ToString("dd/MM/yyyy"))
        If f Is Nothing Then Return
        Dim d As Date
        If Not Date.TryParseExact(f, "dd/MM/yyyy", Nothing, Globalization.DateTimeStyles.None, d) Then
            Msg.Aviso("Fecha inválida.")
            Return
        End If
        Dim nuevoId As Integer = 0
        If Intentar(Sub() nuevoId = _vs.Copiar(_id, d)) Then Cargar(nuevoId)
    End Sub

    Private Sub Buscar()
        Dim dt As DataTable = _vs.Listar(Ctx.Gestion.FechaInicio, Ctx.Gestion.FechaFin)
        Using d As New BuscadorDialog("Buscar comprobante", dt, {New ColumnaBusqueda("Tipo", "Tipo", 50), New ColumnaBusqueda("Numero", "Nº", 55), New ColumnaBusqueda("Fecha", "Fecha", 90), New ColumnaBusqueda("DebeBs", "Importe Bs", 100, True), New ColumnaBusqueda("Estado", "Est.", 40), New ColumnaBusqueda("Glosa", "Glosa", 420)})
            If d.ShowDialog(FindForm()) = DialogResult.OK Then Cargar(d.FilaElegida.GetI("Id"))
        End Using
    End Sub

    Private Sub Navegar(siguiente As Boolean)
        If _id = 0 Then
            If Not siguiente Then
                ' desde "nuevo" ir al último comprobante del tipo
                Dim mes As Integer = If(Ctx.Gestion.CorrelativoMensual, _fecha.Value.Month, 0)
                Dim n As Integer = Ctx.Db.ScalarInt("SELECT MAX(Numero) FROM Comprobante WHERE TipoId=@t AND Mes=@m", "t", _vs.TipoId(ToStr(_tipo.SelectedValue)), "m", mes)
                If n > 0 Then Cargar(_vs.BuscarId(ToStr(_tipo.SelectedValue), n, _fecha.Value.Month))
            End If
            Return
        End If
        Dim v As Integer = _vs.Vecino(_id, siguiente)
        If v <> 0 Then
            Cargar(v)
        ElseIf siguiente Then
            Nuevo()
        End If
    End Sub
End Class
