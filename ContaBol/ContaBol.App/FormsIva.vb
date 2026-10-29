Imports System.IO
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Registro de una factura en el libro de compras o ventas IVA, con cálculo en vivo del crédito/débito fiscal.</summary>
Public Class FacturaDialog
    Inherits Form

    Private ReadOnly _libro As String
    Private ReadOnly _conCuenta As Boolean
    Private ReadOnly _fecha As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy"}
    Private ReadOnly _nro As New TextBox() With {.MaxLength = 20}
    Private ReadOnly _aut As New TextBox() With {.MaxLength = 60}
    Private ReadOnly _ctl As New TextBox() With {.MaxLength = 20}
    Private ReadOnly _nit As New TextBox() With {.MaxLength = 20}
    Private ReadOnly _razon As New TextBox() With {.MaxLength = 150}
    Private ReadOnly _tercero As New PickerBusqueda()
    Private ReadOnly _total As New CampoImporte()
    Private ReadOnly _noSuj As New CampoImporte()
    Private ReadOnly _exento As New CampoImporte()
    Private ReadOnly _cero As New CampoImporte()
    Private ReadOnly _desc As New CampoImporte()
    Private ReadOnly _gift As New CampoImporte()
    Private ReadOnly _estado As New LookupCombo()
    Private ReadOnly _tipo As New LookupCombo()
    Private ReadOnly _dui As New TextBox() With {.MaxLength = 25}
    Private ReadOnly _cuenta As New PickerCuenta()
    Private ReadOnly _chkIt As New CheckBox() With {.Text = "Registrar también el devengamiento del IT", .AutoSize = True, .Checked = True}
    Private ReadOnly _lblSub As New Label()
    Private ReadOnly _lblBase As New Label()
    Private ReadOnly _lblImp As New Label()
    Private _factura As FacturaDto
    Private ReadOnly _fs As New FacturaService(Sesion.Ctx)

    Public ReadOnly Property Resultado As FacturaDto
        Get
            Return _factura
        End Get
    End Property
    Public ReadOnly Property CuentaId As Integer
        Get
            Return _cuenta.CuentaId
        End Get
    End Property
    Public ReadOnly Property ConIt As Boolean
        Get
            Return _chkIt.Checked
        End Get
    End Property

    ''' <summary>conCuenta = True cuando la factura se integra a un comprobante (pide la cuenta de gasto o de ingreso).</summary>
    Public Sub New(libro As String, conCuenta As Boolean, Optional existente As FacturaDto = Nothing, Optional fechaSugerida As Date? = Nothing)
        _libro = libro
        _conCuenta = conCuenta
        Dim esC As Boolean = libro = "C"
        Tema.Aplicar(Me)
        Text = If(esC, "Registro de factura de compra", "Registro de factura de venta")
        FormBorderStyle = FormBorderStyle.FixedDialog
        StartPosition = FormStartPosition.CenterParent
        MaximizeBox = False
        MinimizeBox = False
        ShowInTaskbar = False
        KeyPreview = True
        Dim banner As Panel = Tema.Banner(Text, If(esC, "Libro de compras IVA - crédito fiscal " & _fs.IvaPct.ToString("0.##") & "%", "Libro de ventas IVA - débito fiscal " & _fs.IvaPct.ToString("0.##") & "%"))
        Dim t As New TableLayoutPanel() With {.ColumnCount = 4, .Dock = DockStyle.Top, .AutoSize = True, .Padding = New Padding(16, 10, 16, 6)}
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 140))
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 50))
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 140))
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 50))
        Dim fila As Integer = 0
        _tercero.Configurar(If(esC, "Buscar proveedor", "Buscar cliente"), Function() _fs_Terceros(esC), {New ColumnaBusqueda("Codigo", "Código", 90), New ColumnaBusqueda("Nombre", "Nombre / razón social", 340), New ColumnaBusqueda("Nit", "NIT", 110)}, "Id", Function(r) r.GetS("Codigo") & " - " & r.GetS("Nombre"))
        Agregar(t, fila, If(esC, "Proveedor (opcional)", "Cliente (opcional)"), _tercero, True)
        fila += 1
        Agregar(t, fila, "Fecha de la factura", _fecha) : Agregar(t, fila, "Nº de factura *", _nro, False, 2)
        fila += 1
        Agregar(t, fila, "NIT / CI", _nit) : Agregar(t, fila, "Nº autorización / CUF", _aut, False, 2)
        fila += 1
        Agregar(t, fila, "Nombre o razón social *", _razon, True)
        fila += 1
        Agregar(t, fila, "Código de control", _ctl)
        If esC Then
            Agregar(t, fila, "Nº DUI / DIM", _dui, False, 2)
            fila += 1
            _tipo.CargarLista({New KeyValuePair(Of String, String)("1", "1 - Compras gravadas (mercado interno)"), New KeyValuePair(Of String, String)("2", "2 - Compras no gravadas"), New KeyValuePair(Of String, String)("3", "3 - Exportaciones"),
                               New KeyValuePair(Of String, String)("4", "4 - Gravadas y no gravadas"), New KeyValuePair(Of String, String)("5", "5 - Mercado interno y exportaciones")})
            Agregar(t, fila, "Tipo de compra", _tipo, True)
        Else
            Dim lst As New List(Of KeyValuePair(Of String, String)) From {New KeyValuePair(Of String, String)("V", "V - Válida"), New KeyValuePair(Of String, String)("A", "A - Anulada"), New KeyValuePair(Of String, String)("E", "E - Extraviada"), New KeyValuePair(Of String, String)("N", "N - No utilizada"), New KeyValuePair(Of String, String)("C", "C - Contingencia")}
            _estado.CargarLista(lst)
            Agregar(t, fila, "Estado de la factura", _estado, False, 2)
        End If
        fila += 1
        Dim sep As New Label() With {.Text = "IMPORTES", .Font = Tema.FuenteNegrita, .ForeColor = Tema.Azul, .AutoSize = True, .Margin = New Padding(0, 10, 0, 2)}
        t.Controls.Add(sep, 0, fila)
        t.SetColumnSpan(sep, 4)
        fila += 1
        Agregar(t, fila, "Importe total *", _total) : Agregar(t, fila, If(esC, "Importe no sujeto a CF", "No sujeto a IVA (ICE, IEHD...)"), _noSuj, False, 2)
        fila += 1
        If Not esC Then
            Agregar(t, fila, "Exportaciones y exentas", _exento) : Agregar(t, fila, "Ventas a tasa cero", _cero, False, 2)
            fila += 1
        End If
        Agregar(t, fila, "Descuentos y rebajas", _desc) : Agregar(t, fila, "Gift card", _gift, False, 2)
        fila += 1
        Dim resumen As New Panel() With {.Height = 70, .Dock = DockStyle.Fill, .BackColor = Tema.AzulClaro, .Margin = New Padding(0, 8, 10, 4)}
        _lblSub.Location = New Point(12, 8)
        _lblBase.Location = New Point(12, 26)
        _lblImp.Location = New Point(12, 44)
        _lblSub.AutoSize = True
        _lblBase.AutoSize = True
        _lblImp.AutoSize = True
        _lblImp.Font = Tema.FuenteGrande
        _lblImp.ForeColor = Tema.Azul
        resumen.Controls.AddRange({_lblSub, _lblBase, _lblImp})
        t.Controls.Add(resumen, 0, fila)
        t.SetColumnSpan(resumen, 4)
        fila += 1
        If conCuenta Then
            Dim sep2 As New Label() With {.Text = "ASIENTO CONTABLE", .Font = Tema.FuenteNegrita, .ForeColor = Tema.Azul, .AutoSize = True, .Margin = New Padding(0, 6, 0, 2)}
            t.Controls.Add(sep2, 0, fila)
            t.SetColumnSpan(sep2, 4)
            fila += 1
            _cuenta.SoloMovimiento = True
            Agregar(t, fila, If(esC, "Cuenta de gasto / activo *", "Cuenta de ingreso *"), _cuenta, True)
            fila += 1
            If Not esC Then
                t.Controls.Add(_chkIt, 1, fila)
                t.SetColumnSpan(_chkIt, 3)
                fila += 1
            End If
        End If
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 52, .BackColor = Color.White, .Padding = New Padding(14, 9, 14, 9)}
        Dim ok As Button = Tema.Boton(If(conCuenta, "Agregar al comprobante", "Guardar"), Tema.TipoBoton.Primario, 170)
        ok.Dock = DockStyle.Right
        Dim cancelar As Button = Tema.Boton("Cancelar")
        cancelar.Dock = DockStyle.Right
        pie.Controls.Add(ok)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(cancelar)
        Controls.Add(t)
        Controls.Add(banner)
        Controls.Add(pie)
        ClientSize = New Size(780, 100)
        AddHandler Shown, Sub(o, e)
                              ClientSize = New Size(780, banner.Height + t.PreferredSize.Height + pie.Height + 8)
                              CenterToParent()
                          End Sub
        _factura = If(existente, New FacturaDto With {.Libro = libro, .Fecha = If(fechaSugerida, Date.Today)})
        Cargar()
        For Each c As CampoImporte In {_total, _noSuj, _exento, _cero, _desc, _gift}
            AddHandler c.ValorCambiado, Sub(o, e) Recalcular()
        Next
        AddHandler _tercero.SeleccionCambiada, Sub(o, e)
                                                   If _tercero.FilaSeleccionada IsNot Nothing Then
                                                       _nit.Text = _tercero.FilaSeleccionada.GetS("Nit")
                                                       _razon.Text = _tercero.FilaSeleccionada.GetS("Nombre")
                                                   End If
                                               End Sub
        AddHandler ok.Click, Sub(o, e) Aceptar()
        AddHandler cancelar.Click, Sub(o, e) DialogResult = DialogResult.Cancel
        AddHandler KeyDown, Sub(o, e)
                                If e.KeyCode = Keys.F10 Then Aceptar()
                                If e.KeyCode = Keys.Enter AndAlso Not (TypeOf ActiveControl Is Button) Then
                                    e.Handled = True
                                    e.SuppressKeyPress = True
                                    SelectNextControl(ActiveControl, True, True, True, True)
                                End If
                            End Sub
        CancelButton = cancelar
    End Sub

    Private Shared Sub Agregar(t As TableLayoutPanel, fila As Integer, titulo As String, c As Control, Optional doble As Boolean = False, Optional col As Integer = 0)
        Dim l As New Label() With {.Text = titulo, .AutoSize = False, .Dock = DockStyle.Fill, .TextAlign = ContentAlignment.MiddleLeft, .Height = 28}
        c.Dock = DockStyle.Fill
        c.Margin = New Padding(0, 3, 10, 3)
        t.Controls.Add(l, col, fila)
        t.Controls.Add(c, col + 1, fila)
        If doble Then t.SetColumnSpan(c, 3)
    End Sub

    Private Function _fs_Terceros(esC As Boolean) As DataTable
        Return Svc.Terceros.Listar(If(esC, "CXP", "CXC"), "", True)
    End Function

    Private Sub Cargar()
        Dim f As FacturaDto = _factura
        Dim d As Date = f.Fecha
        If d = Date.MinValue OrElse d < Sesion.Ctx.Gestion.FechaInicio OrElse d > Sesion.Ctx.Gestion.FechaFin Then d = If(Date.Today >= Sesion.Ctx.Gestion.FechaInicio AndAlso Date.Today <= Sesion.Ctx.Gestion.FechaFin, Date.Today, Sesion.Ctx.Gestion.FechaInicio)
        _fecha.MinDate = Sesion.Ctx.Gestion.FechaInicio
        _fecha.MaxDate = Sesion.Ctx.Gestion.FechaFin
        _fecha.Value = d
        _nro.Text = f.NroFactura
        _aut.Text = f.Autorizacion
        _ctl.Text = f.CodControl
        _nit.Text = f.Nit
        _razon.Text = f.RazonSocial
        _total.Valor = f.ImporteTotal
        _noSuj.Valor = f.NoSujeto
        _exento.Valor = f.Exento
        _cero.Valor = f.TasaCero
        _desc.Valor = f.Descuento
        _gift.Valor = f.GiftCard
        _dui.Text = f.Dui
        If _libro = "C" Then _tipo.ValorTexto = If(f.TipoOp = "", "1", f.TipoOp) Else _estado.ValorTexto = If(f.Estado = "", "V", f.Estado)
        If f.TerceroId <> 0 Then _tercero.SeleccionId = f.TerceroId
        Recalcular()
    End Sub

    Private Sub Leer()
        Dim f As FacturaDto = _factura
        f.Libro = _libro
        f.Fecha = _fecha.Value.Date
        f.NroFactura = _nro.Text.Trim()
        f.Autorizacion = _aut.Text.Trim()
        f.CodControl = _ctl.Text.Trim()
        f.Nit = _nit.Text.Trim()
        f.RazonSocial = _razon.Text.Trim()
        f.TerceroId = _tercero.SeleccionId
        f.ImporteTotal = _total.Valor
        f.NoSujeto = _noSuj.Valor
        f.Exento = _exento.Valor
        f.TasaCero = _cero.Valor
        f.Descuento = _desc.Valor
        f.GiftCard = _gift.Valor
        f.Dui = _dui.Text.Trim()
        If _libro = "C" Then
            f.TipoOp = _tipo.ValorTexto
            f.Estado = "V"
        Else
            f.Estado = _estado.ValorTexto
        End If
    End Sub

    Private Sub Recalcular()
        Dim f As New FacturaDto With {.Libro = _libro, .ImporteTotal = _total.Valor, .NoSujeto = _noSuj.Valor, .Exento = _exento.Valor, .TasaCero = _cero.Valor, .Descuento = _desc.Valor, .GiftCard = _gift.Valor, .Estado = If(_libro = "V" AndAlso _estado.ValorTexto <> "", _estado.ValorTexto, "V")}
        _fs.Calcular(f)
        _lblSub.Text = "Subtotal: " & f.Subtotal.ToString("N2", FormatoVal.Cultura)
        _lblBase.Text = "Importe base para " & If(_libro = "C", "crédito", "débito") & " fiscal: " & f.BaseCf.ToString("N2", FormatoVal.Cultura)
        _lblImp.Text = If(_libro = "C", "Crédito fiscal: ", "Débito fiscal: ") & f.Impuesto.ToString("N2", FormatoVal.Cultura) & " Bs"
    End Sub

    Private Sub Aceptar()
        Try
            Leer()
            If _factura.NroFactura = "" Then Throw New ArgumentException("Ingrese el número de factura.")
            If _factura.RazonSocial = "" Then Throw New ArgumentException("Ingrese el nombre o razón social.")
            If _conCuenta Then
                If _cuenta.CuentaId = 0 Then Throw New ArgumentException("Seleccione la cuenta contable.")
                _fs.Calcular(_factura)
                If _fs.Duplicada(_factura) Then Throw New InvalidOperationException("La factura " & _factura.NroFactura & " ya fue registrada.")
            Else
                If _factura.Id = 0 Then _fs.Registrar(_factura) Else _fs.Modificar(_factura)
            End If
            DialogResult = DialogResult.OK
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class

''' <summary>Libros de compras y ventas IVA: registro, corrección, anulación y exportación (formato LCV).</summary>
Public Class FacturasIvaForm
    Inherits ListaForm

    Private ReadOnly _libro As String
    Private ReadOnly _desde As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}

    Public Sub New(libro As String)
        _libro = libro
    End Sub

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return If(_libro = "C", "Libro de compras IVA", "Libro de ventas IVA")
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Registre facturas, corrija datos o anúlelas. Los totales respetan el formato LCV del SIN."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return If(_libro = "C", "IVA.COMPRAS", "IVA.VENTAS")
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim ini As Date = Sesion.Ctx.Gestion.FechaInicio
        Dim hoy As Date = If(Date.Today >= ini AndAlso Date.Today <= Sesion.Ctx.Gestion.FechaFin, Date.Today, ini)
        _desde.MinDate = ini
        _desde.MaxDate = Sesion.Ctx.Gestion.FechaFin
        _hasta.MinDate = ini
        _hasta.MaxDate = Sesion.Ctx.Gestion.FechaFin
        _desde.Value = InicioDeMes(hoy)
        _hasta.Value = FinDeMes(hoy)
        Dim l1 As New Label() With {.Text = "Del", .AutoSize = True, .Margin = New Padding(10, 8, 4, 0)}
        Dim l2 As New Label() With {.Text = "al", .AutoSize = True, .Margin = New Padding(8, 8, 4, 0)}
        Barra.Controls.AddRange({l1, _desde, l2, _hasta})
        AddHandler _desde.ValueChanged, Sub(o, e) Refrescar()
        AddHandler _hasta.ValueChanged, Sub(o, e) Refrescar()
        Dim bAnular As Button = Tema.Boton("Anular factura", Tema.TipoBoton.Peligro, 120)
        Dim bCsv As Button = Tema.Boton("Exportar LCV (CSV)", Tema.TipoBoton.Secundario, 140)
        Dim bLibro As Button = Tema.Boton("Libro PDF/Excel", Tema.TipoBoton.Secundario, 120)
        Barra.Controls.AddRange({bAnular, bCsv, bLibro})
        AddHandler bAnular.Click, Sub(o, e) Anular()
        AddHandler bCsv.Click, Sub(o, e) ExportarCsv()
        AddHandler bLibro.Click, Sub(o, e) Informes.Abrir(If(_libro = "C", "libro_compras", "libro_ventas"), New Dictionary(Of String, Object) From {{"desde", _desde.Value.Date}, {"hasta", _hasta.Value.Date}}, False)
        bAnular.Enabled = Sesion.Puede(PermisoEdicion)
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Return Svc.Facturas.Listar(_libro, _desde.Value.Date, _hasta.Value.Date)
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColFecha(Grid, "Fecha", "Fecha")
        Tema.ColTexto(Grid, "NroFactura", "Nº factura", 100)
        Tema.ColTexto(Grid, "Nit", "NIT / CI", 110)
        Tema.ColTexto(Grid, "RazonSocial", "Razón social", 250, True)
        Tema.ColTexto(Grid, "Autorizacion", "Autorización / CUF", 140)
        Tema.ColImporte(Grid, "ImporteTotal", "Importe total", 105)
        Tema.ColImporte(Grid, "BaseCf", If(_libro = "C", "Base CF", "Base DF"), 100)
        Tema.ColImporte(Grid, "Impuesto", If(_libro = "C", "Crédito fiscal", "Débito fiscal"), 100)
        Tema.ColTexto(Grid, "Estado", "Est.", 40)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If fila.GetS("Estado") <> "V" AndAlso fila.GetS("Estado") <> "C" Then estilo.ForeColor = Tema.Rojo
    End Sub

    Protected Overrides Sub Nuevo()
        Using d As New FacturaDialog(_libro, False, Nothing, _hasta.Value.Date)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Dim f As FacturaDto = Svc.Facturas.Obtener(fila.GetI("Id"))
        If f.ComprobanteId <> 0 AndAlso Not Msg.Confirmar("Esta factura pertenece a un comprobante. Los cambios de importes no modifican el asiento contable." & vbCrLf & "¿Desea editar de todos modos?") Then Return
        Using d As New FacturaDialog(_libro, False, f)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Eliminar(fila As DataRow)
        Dim fs As New FacturaService(Ctx)
        fs.Eliminar(fila.GetI("Id"))
    End Sub

    Private Sub Anular()
        Dim fila As DataRow = FilaActual()
        If fila Is Nothing Then Return
        If Not Msg.Confirmar("¿Anular la factura " & fila.GetS("NroFactura") & "? Quedará en el libro con importes en cero.", "Anular factura", True) Then Return
        Intentar(Sub()
                     Dim fs As New FacturaService(Ctx)
                     Dim f As FacturaDto = fs.Obtener(fila.GetI("Id"))
                     f.Estado = "A"
                     If _libro = "C" Then
                         Ctx.Db.Execute("UPDATE FacturaIva SET Estado='A' WHERE Id=@i", "i", f.Id)
                     Else
                         fs.Modificar(f)
                     End If
                     Refrescar()
                 End Sub)
    End Sub

    Private Sub ExportarCsv()
        Using d As New SaveFileDialog()
            d.Filter = "Archivo CSV (*.csv)|*.csv"
            d.FileName = If(_libro = "C", "Compras_", "Ventas_") & _desde.Value.ToString("yyyyMM") & ".csv"
            If d.ShowDialog() <> DialogResult.OK Then Return
            Intentar(Sub()
                         Dim txt As String = Svc.Facturas.ExportarCsv(_libro, _desde.Value.Month)
                         File.WriteAllText(d.FileName, txt, New System.Text.UTF8Encoding(True))
                         Msg.Info("Archivo generado:" & vbCrLf & d.FileName)
                     End Sub)
        End Using
    End Sub

    Protected Overrides Function ReporteDeLista() As ContaBol.Core.Reports.ReporteDef
        Dim p As New Dictionary(Of String, Object) From {{"desde", _desde.Value.Date}, {"hasta", _hasta.Value.Date}}
        Return Catalogo.Buscar(If(_libro = "C", "libro_compras", "libro_ventas")).Ejecutar(Ctx, p)
    End Function
End Class
