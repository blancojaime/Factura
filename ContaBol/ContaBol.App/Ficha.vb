Imports System.Reflection
Imports ContaBol.Core.Common

Public Enum TipoCampo
    Texto
    Memo
    Entero
    Importe
    Cantidad
    Fecha
    FechaOpcional
    Bool
    Lista
    Lookup
    Cuenta
    Seccion
    Clave
End Enum

''' <summary>Definición de un campo de una ficha de captura (se dibuja automáticamente con alineación y teclado cómodos).</summary>
Public Class CampoUI
    Public Property Clave As String
    Public Property Titulo As String
    Public Property Tipo As TipoCampo = TipoCampo.Texto
    Public Property Requerido As Boolean
    Public Property Largo As Integer
    Public Property Doble As Boolean
    Public Property SoloLectura As Boolean
    Public Property Defecto As Object
    Public Property Ayuda As String = ""
    Public Property Opciones As List(Of KeyValuePair(Of String, String))
    Public Property Datos As Func(Of DataTable)
    Public Property CampoId As String = "Id"
    Public Property CampoTexto As String = "Nombre"
    Public Property ConVacio As Boolean = True
    Public Property SoloMovimiento As Boolean = True
    Public Property Decimales As Integer = 2

    Public Shared Function Sec(titulo As String) As CampoUI
        Return New CampoUI With {.Tipo = TipoCampo.Seccion, .Titulo = titulo, .Clave = "_sec_" & titulo, .Doble = True}
    End Function

    Public Shared Function Txt(clave As String, titulo As String, Optional largo As Integer = 100, Optional requerido As Boolean = False, Optional doble As Boolean = False) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Texto, .Largo = largo, .Requerido = requerido, .Doble = doble}
    End Function

    Public Shared Function Memo(clave As String, titulo As String, Optional largo As Integer = 255) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Memo, .Largo = largo, .Doble = True}
    End Function

    Public Shared Function Ent(clave As String, titulo As String, Optional requerido As Boolean = False) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Entero, .Requerido = requerido}
    End Function

    Public Shared Function Imp(clave As String, titulo As String, Optional requerido As Boolean = False, Optional decimales As Integer = 2) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Importe, .Requerido = requerido, .Decimales = decimales}
    End Function

    Public Shared Function Cant(clave As String, titulo As String, Optional decimales As Integer = 4) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Cantidad, .Decimales = decimales}
    End Function

    Public Shared Function Fec(clave As String, titulo As String, Optional requerido As Boolean = True) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = If(requerido, TipoCampo.Fecha, TipoCampo.FechaOpcional), .Requerido = requerido}
    End Function

    Public Shared Function Chk(clave As String, titulo As String, Optional defecto As Boolean = False) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Bool, .Defecto = defecto}
    End Function

    Public Shared Function Lst(clave As String, titulo As String, ParamArray opciones() As String) As CampoUI
        Dim c As New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Lista, .Opciones = New List(Of KeyValuePair(Of String, String))}
        For Each o As String In opciones
            Dim a As String() = o.Split("|"c)
            c.Opciones.Add(New KeyValuePair(Of String, String)(a(0), If(a.Length > 1, a(1), a(0))))
        Next
        If c.Opciones.Count > 0 Then c.Defecto = c.Opciones(0).Key
        Return c
    End Function

    Public Shared Function Lk(clave As String, titulo As String, datos As Func(Of DataTable), Optional campoTexto As String = "Nombre", Optional requerido As Boolean = False, Optional campoId As String = "Id") As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Lookup, .Datos = datos, .CampoTexto = campoTexto, .Requerido = requerido, .CampoId = campoId}
    End Function

    Public Shared Function Cta(clave As String, titulo As String, Optional soloMovimiento As Boolean = True, Optional requerido As Boolean = False) As CampoUI
        Return New CampoUI With {.Clave = clave, .Titulo = titulo, .Tipo = TipoCampo.Cuenta, .Doble = True, .SoloMovimiento = soloMovimiento, .Requerido = requerido}
    End Function
End Class

''' <summary>Convierte objetos DTO en diccionarios y viceversa por reflexión (para alimentar las fichas).</summary>
Public Module DtoMapper

    Public Function ADiccionario(obj As Object) As Dictionary(Of String, Object)
        Dim d As New Dictionary(Of String, Object)(StringComparer.OrdinalIgnoreCase)
        For Each p As PropertyInfo In obj.GetType().GetProperties()
            If p.CanRead AndAlso p.GetIndexParameters().Length = 0 Then d(p.Name) = p.GetValue(obj)
        Next
        Return d
    End Function

    Public Sub Aplicar(obj As Object, valores As Dictionary(Of String, Object))
        For Each p As PropertyInfo In obj.GetType().GetProperties()
            If Not p.CanWrite OrElse Not valores.ContainsKey(p.Name) Then Continue For
            Dim v As Object = valores(p.Name)
            Dim t As Type = p.PropertyType
            Try
                If t Is GetType(String) Then
                    p.SetValue(obj, If(v Is Nothing, "", Convert.ToString(v)))
                ElseIf t Is GetType(Integer) Then
                    p.SetValue(obj, ToInt(v))
                ElseIf t Is GetType(Decimal) Then
                    p.SetValue(obj, ToDec(v))
                ElseIf t Is GetType(Boolean) Then
                    p.SetValue(obj, ToFlag(v))
                ElseIf t Is GetType(Date) Then
                    p.SetValue(obj, If(v Is Nothing, Date.MinValue, ToDate(v)))
                ElseIf t Is GetType(Date?) Then
                    p.SetValue(obj, If(v Is Nothing, CType(Nothing, Date?), CType(ToDate(v), Date?)))
                End If
            Catch
            End Try
        Next
    End Sub
End Module

''' <summary>Ficha de captura generada a partir de una lista de campos. Enter pasa al siguiente campo; F10 o Ctrl+G guardan.</summary>
Public Class FichaDialog
    Inherits Form

    Private ReadOnly _campos As List(Of CampoUI)
    Private ReadOnly _controles As New Dictionary(Of String, Control)
    Private ReadOnly _guardar As Action(Of Dictionary(Of String, Object))
    Public ReadOnly Property Valores As New Dictionary(Of String, Object)

    Public Sub New(titulo As String, campos As IEnumerable(Of CampoUI), valores As Dictionary(Of String, Object), alGuardar As Action(Of Dictionary(Of String, Object)), Optional subtitulo As String = "", Optional anchoForm As Integer = 760)
        _campos = campos.ToList()
        _guardar = alGuardar
        Tema.Aplicar(Me)
        Text = titulo
        FormBorderStyle = FormBorderStyle.FixedDialog
        StartPosition = FormStartPosition.CenterParent
        MaximizeBox = False
        MinimizeBox = False
        ShowInTaskbar = False
        KeyPreview = True
        Dim banner As Panel = Tema.Banner(titulo, subtitulo)
        Dim cuerpo As New TableLayoutPanel() With {.ColumnCount = 4, .AutoSize = True, .Padding = New Padding(16, 12, 16, 8), .Dock = DockStyle.Top}
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 50))
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 50))
        Dim fila As Integer = 0, col As Integer = 0
        cuerpo.RowCount = 1
        For Each c As CampoUI In _campos
            If c.Tipo = TipoCampo.Seccion Then
                If col <> 0 Then
                    fila += 1
                    col = 0
                End If
                Dim l As New Label() With {.Text = c.Titulo.ToUpperInvariant(), .Font = Tema.FuenteNegrita, .ForeColor = Tema.Azul, .AutoSize = True, .Margin = New Padding(0, 12, 0, 2)}
                cuerpo.Controls.Add(l, 0, fila)
                cuerpo.SetColumnSpan(l, 4)
                fila += 1
                Continue For
            End If
            Dim ancho2 As Boolean = c.Doble OrElse c.Tipo = TipoCampo.Memo OrElse c.Tipo = TipoCampo.Cuenta
            If ancho2 AndAlso col <> 0 Then
                fila += 1
                col = 0
            End If
            Dim lab As New Label() With {.Text = c.Titulo & If(c.Requerido, " *", ""), .AutoSize = False, .Dock = DockStyle.Fill, .TextAlign = ContentAlignment.MiddleLeft, .Margin = New Padding(0, 2, 6, 2), .Height = 28}
            If c.Requerido Then lab.Font = Tema.FuenteNegrita
            Dim ctrl As Control = CrearControl(c)
            ctrl.Margin = New Padding(0, 3, 12, 3)
            ctrl.Dock = DockStyle.Fill
            _controles(c.Clave) = ctrl
            cuerpo.Controls.Add(lab, col, fila)
            cuerpo.Controls.Add(ctrl, col + 1, fila)
            If ancho2 Then
                cuerpo.SetColumnSpan(ctrl, 3)
                If c.Tipo = TipoCampo.Memo Then
                    ctrl.Height = 58
                    lab.TextAlign = ContentAlignment.TopLeft
                    lab.Padding = New Padding(0, 6, 0, 0)
                End If
                fila += 1
                col = 0
            Else
                col += 2
                If col >= 4 Then
                    col = 0
                    fila += 1
                End If
            End If
        Next
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 52, .BackColor = Color.White, .Padding = New Padding(14, 9, 14, 9)}
        Dim bGuardar As Button = Tema.Boton("Guardar (F10)", Tema.TipoBoton.Primario, 130)
        bGuardar.Dock = DockStyle.Right
        Dim bCancelar As Button = Tema.Boton("Cancelar", Tema.TipoBoton.Secundario, 96)
        bCancelar.Dock = DockStyle.Right
        pie.Controls.Add(bGuardar)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(bCancelar)
        AddHandler pie.Paint, Sub(o, e) e.Graphics.DrawLine(New Pen(Tema.Borde), 0, 0, pie.Width, 0)
        Controls.Add(cuerpo)
        Controls.Add(banner)
        Controls.Add(pie)
        ClientSize = New Size(anchoForm, 100)
        AddHandler Shown, Sub(o, e)
                              Dim alto As Integer = banner.Height + cuerpo.PreferredSize.Height + pie.Height + 6
                              ClientSize = New Size(anchoForm, Math.Min(alto, Screen.FromControl(Me).WorkingArea.Height - 80))
                              CenterToParent()
                          End Sub
        CargarValores(valores)
        AddHandler bGuardar.Click, Sub(o, e) Intentar()
        AddHandler bCancelar.Click, Sub(o, e) DialogResult = DialogResult.Cancel
        AddHandler KeyDown, AddressOf Teclas
        CancelButton = bCancelar
    End Sub

    Private Function CrearControl(c As CampoUI) As Control
        Select Case c.Tipo
            Case TipoCampo.Texto, TipoCampo.Clave
                Dim t As New TextBox()
                If c.Largo > 0 Then t.MaxLength = c.Largo
                If c.SoloLectura Then t.ReadOnly = True
                If c.Tipo = TipoCampo.Clave Then t.UseSystemPasswordChar = True
                Return t
            Case TipoCampo.Memo
                Dim t As New TextBox() With {.Multiline = True, .ScrollBars = ScrollBars.Vertical, .AcceptsReturn = True}
                If c.Largo > 0 Then t.MaxLength = c.Largo
                Return t
            Case TipoCampo.Entero
                Dim n As New NumericUpDown() With {.Minimum = -1000000000, .Maximum = 1000000000, .TextAlign = HorizontalAlignment.Right}
                Return n
            Case TipoCampo.Importe, TipoCampo.Cantidad
                Return New CampoImporte() With {.Decimales = c.Decimales, .PermiteNegativo = False}
            Case TipoCampo.Fecha
                Return New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy"}
            Case TipoCampo.FechaOpcional
                Return New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .ShowCheckBox = True, .Checked = False}
            Case TipoCampo.Bool
                Return New CheckBox() With {.Text = "", .AutoSize = True, .Anchor = AnchorStyles.Left}
            Case TipoCampo.Lista
                Dim cb As New LookupCombo()
                cb.CargarLista(c.Opciones)
                Return cb
            Case TipoCampo.Lookup
                Dim cb As New LookupCombo()
                cb.Cargar(c.Datos.Invoke(), c.CampoId, c.CampoTexto, Not c.Requerido OrElse True, "")
                Return cb
            Case TipoCampo.Cuenta
                Return New PickerCuenta() With {.SoloMovimiento = c.SoloMovimiento, .Requerida = c.Requerido}
            Case Else
                Return New TextBox()
        End Select
    End Function

    Private Sub CargarValores(vals As Dictionary(Of String, Object))
        For Each c As CampoUI In _campos
            If c.Tipo = TipoCampo.Seccion Then Continue For
            Dim v As Object = Nothing
            If vals IsNot Nothing AndAlso vals.ContainsKey(c.Clave) Then v = vals(c.Clave) Else v = c.Defecto
            Dim ctrl As Control = _controles(c.Clave)
            Select Case c.Tipo
                Case TipoCampo.Texto, TipoCampo.Memo, TipoCampo.Clave
                    ctrl.Text = ToStr(v)
                Case TipoCampo.Entero
                    CType(ctrl, NumericUpDown).Value = ToInt(v)
                Case TipoCampo.Importe, TipoCampo.Cantidad
                    CType(ctrl, CampoImporte).Valor = ToDec(v)
                Case TipoCampo.Fecha
                    Dim d As Date = If(v Is Nothing, Date.Today, ToDate(v))
                    If d = Date.MinValue Then d = Date.Today
                    CType(ctrl, DateTimePicker).Value = d
                Case TipoCampo.FechaOpcional
                    Dim dp As DateTimePicker = CType(ctrl, DateTimePicker)
                    Dim d As Date = If(v Is Nothing, Date.MinValue, ToDate(v))
                    If d > Date.MinValue Then
                        dp.Value = d
                        dp.Checked = True
                    Else
                        dp.Checked = False
                    End If
                Case TipoCampo.Bool
                    CType(ctrl, CheckBox).Checked = ToFlag(v)
                Case TipoCampo.Lista
                    CType(ctrl, LookupCombo).ValorTexto = ToStr(v)
                Case TipoCampo.Lookup
                    CType(ctrl, LookupCombo).ValorId = ToInt(v)
                Case TipoCampo.Cuenta
                    CType(ctrl, PickerCuenta).CuentaId = ToInt(v)
            End Select
        Next
    End Sub

    Private Function LeerValores() As Dictionary(Of String, Object)
        Dim d As New Dictionary(Of String, Object)(StringComparer.OrdinalIgnoreCase)
        For Each c As CampoUI In _campos
            If c.Tipo = TipoCampo.Seccion Then Continue For
            Dim ctrl As Control = _controles(c.Clave)
            Select Case c.Tipo
                Case TipoCampo.Texto, TipoCampo.Memo, TipoCampo.Clave
                    d(c.Clave) = ctrl.Text.Trim()
                Case TipoCampo.Entero
                    d(c.Clave) = CInt(CType(ctrl, NumericUpDown).Value)
                Case TipoCampo.Importe, TipoCampo.Cantidad
                    d(c.Clave) = CType(ctrl, CampoImporte).Valor
                Case TipoCampo.Fecha
                    d(c.Clave) = CType(ctrl, DateTimePicker).Value.Date
                Case TipoCampo.FechaOpcional
                    Dim dp As DateTimePicker = CType(ctrl, DateTimePicker)
                    d(c.Clave) = If(dp.Checked, CObj(dp.Value.Date), Nothing)
                Case TipoCampo.Bool
                    d(c.Clave) = CType(ctrl, CheckBox).Checked
                Case TipoCampo.Lista
                    d(c.Clave) = CType(ctrl, LookupCombo).ValorTexto
                Case TipoCampo.Lookup
                    d(c.Clave) = CType(ctrl, LookupCombo).ValorId
                Case TipoCampo.Cuenta
                    d(c.Clave) = CType(ctrl, PickerCuenta).CuentaId
            End Select
        Next
        Return d
    End Function

    Private Sub Teclas(o As Object, e As KeyEventArgs)
        If e.KeyCode = Keys.F10 OrElse (e.Control AndAlso e.KeyCode = Keys.G) Then
            e.Handled = True
            Intentar()
        ElseIf e.KeyCode = Keys.Enter AndAlso Not (TypeOf ActiveControl Is Button) Then
            Dim tb As TextBox = TryCast(ActiveControl, TextBox)
            If tb IsNot Nothing AndAlso tb.Multiline Then Return
            e.Handled = True
            e.SuppressKeyPress = True
            SelectNextControl(ActiveControl, True, True, True, True)
        End If
    End Sub

    Private Sub Intentar()
        Dim v As Dictionary(Of String, Object) = LeerValores()
        For Each c As CampoUI In _campos
            If Not c.Requerido OrElse c.Tipo = TipoCampo.Seccion Then Continue For
            Dim falta As Boolean = False
            Select Case c.Tipo
                Case TipoCampo.Texto, TipoCampo.Memo, TipoCampo.Clave : falta = ToStr(v(c.Clave)) = ""
                Case TipoCampo.Lookup, TipoCampo.Cuenta : falta = ToInt(v(c.Clave)) = 0
                Case TipoCampo.Importe, TipoCampo.Cantidad : falta = ToDec(v(c.Clave)) = 0D
            End Select
            If falta Then
                Msg.Aviso("Complete el campo obligatorio: " & c.Titulo)
                _controles(c.Clave).Focus()
                Return
            End If
        Next
        Try
            If _guardar IsNot Nothing Then _guardar(v)
            Valores.Clear()
            For Each kv In v
                Valores(kv.Key) = kv.Value
            Next
            DialogResult = DialogResult.OK
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class
