Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Clientes o proveedores con su cuenta corriente.</summary>
Public Class TercerosForm
    Inherits ListaForm

    Private ReadOnly _clase As String

    Public Sub New(clase As String)
        _clase = clase
    End Sub

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return If(_clase = "CXC", "Clientes", "Proveedores")
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return If(_clase = "CXC", "Registre clientes con su límite de crédito, nivel de precio y cuentas contables. El saldo muestra lo que adeudan.", "Registre proveedores. El saldo muestra lo que la empresa les adeuda.")
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "COM.TERCEROS"
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim bK As Button = Tema.Boton("Estado de cuenta", Tema.TipoBoton.Secundario, 130)
        Dim bS As Button = Tema.Boton("Saldo inicial…", Tema.TipoBoton.Secundario, 110)
        Barra.Controls.AddRange({bK, bS})
        AddHandler bK.Click, Sub(o, e)
                                 Dim f As DataRow = FilaActual()
                                 If f IsNot Nothing Then Informes.Abrir("kardex_tercero", New Dictionary(Of String, Object) From {{"clase", _clase}, {"tercero", f.GetI("Id")}})
                             End Sub
        AddHandler bS.Click, Sub(o, e) SaldoInicial()
        bS.Enabled = Sesion.Puede("COM.TERCEROS")
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = Svc.Terceros.Listar(_clase)
        dt.Columns.Add("Saldo", GetType(Decimal))
        Dim saldos As New Dictionary(Of String, Decimal)
        For Each r As DataRow In Svc.Terceros.SaldosPorTercero(_clase, Ctx.Gestion.FechaFin).Rows
            saldos(r.GetS("Codigo")) = r.GetD("Saldo")
        Next
        For Each r As DataRow In dt.Rows
            Dim s As Decimal = 0D
            saldos.TryGetValue(r.GetS("Codigo"), s)
            r("Saldo") = s
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Codigo", "Código", 90)
        Tema.ColTexto(Grid, "Nombre", "Nombre / razón social", 300, True)
        Tema.ColTexto(Grid, "Nit", "NIT / CI", 110)
        Tema.ColTexto(Grid, "Telefono", "Teléfono", 110)
        Tema.ColTexto(Grid, "Ciudad", "Ciudad", 100)
        If _clase = "CXC" Then Tema.ColImporte(Grid, "LimiteCredito", "Límite crédito", 110)
        Tema.ColImporte(Grid, "Saldo", "Saldo Bs", 110)
        Tema.ColCheck(Grid, "Activo", "Activo", 56)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If Not fila.GetF("Activo") Then estilo.ForeColor = Tema.Gris
    End Sub

    Private Function Campos() As List(Of CampoUI)
        Dim l As New List(Of CampoUI)
        l.Add(CampoUI.Sec("Datos generales"))
        l.Add(CampoUI.Txt("Codigo", "Código (vacío = automático)", 20))
        l.Add(CampoUI.Txt("Nit", "NIT / CI", 20))
        l.Add(CampoUI.Txt("Nombre", "Nombre o razón social", 150, True, True))
        l.Add(CampoUI.Txt("Direccion", "Dirección", 200, False, True))
        l.Add(CampoUI.Txt("Ciudad", "Ciudad", 60))
        l.Add(CampoUI.Txt("Telefono", "Teléfono", 40))
        l.Add(CampoUI.Txt("Email", "Correo electrónico", 100))
        l.Add(CampoUI.Txt("Actividad", "Actividad", 100))
        l.Add(CampoUI.Txt("Contacto", "Persona de contacto", 80, False, True))
        l.Add(CampoUI.Sec("Condiciones comerciales"))
        l.Add(CampoUI.Chk("EsCliente", "Es cliente", _clase = "CXC"))
        l.Add(CampoUI.Chk("EsProveedor", "Es proveedor", _clase = "CXP"))
        l.Add(CampoUI.Imp("LimiteCredito", "Límite de crédito (Bs)"))
        l.Add(CampoUI.Ent("DiasCredito", "Días de crédito"))
        l.Add(CampoUI.Lst("NivelPrecio", "Nivel de precio", "A|Precio A", "B|Precio B", "C|Precio C", "D|Precio D", "E|Precio E", "F|Precio F", "G|Precio G"))
        l.Add(CampoUI.Chk("Activo", "Activo", True))
        l.Add(CampoUI.Sec("Cuentas contables (opcional: si se dejan vacías se usan las generales)"))
        l.Add(CampoUI.Cta("CuentaCxcId", "Cuenta por cobrar"))
        l.Add(CampoUI.Cta("CuentaCxpId", "Cuenta por pagar"))
        l.Add(CampoUI.Cta("CuentaAnticipoId", "Cuenta de anticipos"))
        Return l
    End Function

    Private Sub Mostrar(id As Integer)
        Dim t As TerceroDto = If(id = 0, New TerceroDto With {.EsCliente = _clase = "CXC", .EsProveedor = _clase = "CXP"}, Svc.Terceros.Obtener(id))
        Using d As New FichaDialog(If(id = 0, "Nuevo " & If(_clase = "CXC", "cliente", "proveedor"), "Modificar " & If(_clase = "CXC", "cliente", "proveedor")), Campos(), DtoMapper.ADiccionario(t),
            Sub(v)
                DtoMapper.Aplicar(t, v)
                Svc.Terceros.Guardar(t)
            End Sub, "", 820)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Nuevo()
        Mostrar(0)
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Mostrar(fila.GetI("Id"))
    End Sub

    Protected Overrides Sub Eliminar(fila As DataRow)
        Svc.Terceros.Eliminar(fila.GetI("Id"))
    End Sub

    Private Sub SaldoInicial()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then
            Msg.Aviso("Seleccione un registro.")
            Return
        End If
        Dim campos As New List(Of CampoUI) From {
            CampoUI.Fec("Fecha", "Fecha del saldo"),
            CampoUI.Lst("Tipo", "Naturaleza del saldo", If(_clase = "CXC", "D|Deuda del cliente (por cobrar)", "D|Deuda con el proveedor (por pagar)"), If(_clase = "CXC", "A|Anticipo recibido del cliente", "A|Anticipo entregado al proveedor")),
            CampoUI.Imp("Monto", "Importe (Bs)", True),
            CampoUI.Chk("Asiento", "Generar asiento contable", False),
            CampoUI.Cta("Contra", "Contracuenta del asiento"),
            CampoUI.Txt("Detalle", "Detalle", 100, False, True)}
        Dim ini As New Dictionary(Of String, Object) From {{"Fecha", Ctx.Gestion.FechaInicio}, {"Tipo", "D"}, {"Detalle", "Saldo inicial"}}
        Using d As New FichaDialog("Saldo inicial - " & f.GetS("Nombre"), campos, ini,
            Sub(v)
                If ToFlag(v("Asiento")) AndAlso ToInt(v("Contra")) = 0 Then Throw New InvalidOperationException("Seleccione la contracuenta del asiento.")
                Dim monto As Decimal = ToDec(v("Monto"))
                If ToStr(v("Tipo")) = "A" Then monto = -monto
                Svc.Terceros.SaldoInicial(f.GetI("Id"), _clase, ToDate(v("Fecha")), monto, ToInt(v("Contra")), ToFlag(v("Asiento")), ToStr(v("Detalle")))
            End Sub, "Si el saldo ya está incluido en el asiento de apertura, no marque 'Generar asiento'.", 700)
            d.ShowDialog(FindForm())
        End Using
        Refrescar()
    End Sub
End Class

''' <summary>Venta o compra al contado y a crédito con inventario, IVA, IT y cuenta corriente.</summary>
Public Class DocumentoForm
    Inherits FormBase

    Private ReadOnly _esVenta As Boolean
    Private ReadOnly _rbContado As New RadioButton() With {.Text = "Contado", .Checked = True, .AutoSize = True}
    Private ReadOnly _rbCredito As New RadioButton() With {.Text = "Crédito", .AutoSize = True}
    Private ReadOnly _fecha As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _tercero As New PickerBusqueda() With {.Width = 420}
    Private ReadOnly _almacen As New LookupCombo() With {.Width = 200}
    Private ReadOnly _vendedor As New LookupCombo() With {.Width = 200}
    Private ReadOnly _moneda As New LookupCombo() With {.Width = 120}
    Private ReadOnly _tc As New CampoImporte() With {.Width = 70}
    Private ReadOnly _detalle As New TextBox() With {.MaxLength = 200, .Width = 420}
    Private ReadOnly _chkFactura As New CheckBox() With {.Text = "Con factura", .AutoSize = True}
    Private ReadOnly _fFecha As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _fNro As New TextBox() With {.MaxLength = 20, .Width = 100}
    Private ReadOnly _fAut As New TextBox() With {.MaxLength = 60, .Width = 190}
    Private ReadOnly _fCtl As New TextBox() With {.MaxLength = 20, .Width = 110}
    Private ReadOnly _fNit As New TextBox() With {.MaxLength = 20, .Width = 110}
    Private ReadOnly _fRazon As New TextBox() With {.MaxLength = 150, .Width = 260}
    Private ReadOnly _grid As New GridItems()
    Private ReadOnly _desc As New CampoImporte() With {.Width = 110}
    Private ReadOnly _rec As New CampoImporte() With {.Width = 110}
    Private ReadOnly _anticipo As New CampoImporte() With {.Width = 110}
    Private ReadOnly _acuenta As New CampoImporte() With {.Width = 110}
    Private ReadOnly _cuentaPago As New PickerCuenta() With {.Width = 360}
    Private ReadOnly _venc As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _lblSub As New Label()
    Private ReadOnly _lblTotal As New Label()
    Private ReadOnly _lblImp As New Label()
    Private ReadOnly _lblSaldo As New Label()
    Private ReadOnly _lblInfoTercero As New Label()
    Private ReadOnly _lblNumero As New Label()
    Private ReadOnly _panelFactura As New Panel()
    Private ReadOnly _lblAntic As New Label()
    Private _nivelPrecio As String = "A"
    Private _anticipoDisp As Decimal

    Public Sub New(esVenta As Boolean)
        _esVenta = esVenta
        Text = If(esVenta, "Ventas", "Compras")
    End Sub

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return If(_esVenta, "Nueva venta", "Nueva compra")
        End Get
    End Property

    Private Sub Poner(cont As Control, titulo As String, c As Control, x As Integer, y As Integer)
        Dim l As New Label() With {.Text = titulo, .AutoSize = True, .Location = New Point(x, y + 4)}
        cont.Controls.Add(l)
        c.Location = New Point(x + l.PreferredWidth + 6, y)
        cont.Controls.Add(c)
    End Sub

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Dim banner As Panel = Tema.Banner(If(_esVenta, "Ventas al contado y a crédito", "Compras al contado y a crédito"),
                                          If(_esVenta, "Genera automáticamente: ingreso con débito fiscal, costo de venta, devengamiento del IT, libro de ventas y cuenta corriente del cliente.", "Genera automáticamente: egreso con crédito fiscal, ingreso a inventario, libro de compras y cuenta corriente del proveedor."))
        ' ------ cabecera ------
        Dim cab As New Panel() With {.Dock = DockStyle.Top, .Height = 164, .BackColor = Color.White, .Padding = New Padding(16, 6, 16, 4)}
        AddHandler cab.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, cab.Height - 1, cab.Width, cab.Height - 1)
        Dim pTipo As New FlowLayoutPanel() With {.Location = New Point(0, 6), .Size = New Size(210, 30), .WrapContents = False}
        pTipo.Controls.AddRange({_rbContado, _rbCredito})
        cab.Controls.Add(pTipo)
        Poner(cab, "Fecha", _fecha, 220, 6)
        _lblNumero.AutoSize = True
        _lblNumero.Font = Tema.FuenteGrande
        _lblNumero.ForeColor = Tema.Azul
        _lblNumero.Location = New Point(420, 8)
        cab.Controls.Add(_lblNumero)
        _tercero.Configurar(If(_esVenta, "Buscar cliente", "Buscar proveedor"), Function() Svc.Terceros.Listar(If(_esVenta, "CXC", "CXP"), "", True),
                            {New ColumnaBusqueda("Codigo", "Código", 90), New ColumnaBusqueda("Nombre", "Nombre / razón social", 340), New ColumnaBusqueda("Nit", "NIT", 110)}, "Id", Function(r) r.GetS("Codigo") & " - " & r.GetS("Nombre"))
        Poner(cab, If(_esVenta, "Cliente", "Proveedor"), _tercero, 0, 40)
        Poner(cab, "Almacén", _almacen, 560, 40)
        If _esVenta Then Poner(cab, "Vendedor", _vendedor, 0, 74) Else _vendedor.Visible = False
        _moneda.CargarLista({New KeyValuePair(Of String, String)("BS", "Bolivianos"), New KeyValuePair(Of String, String)("USD", "Dólares")})
        Poner(cab, "Moneda", _moneda, If(_esVenta, 320, 0), 74)
        Poner(cab, "T.C.", _tc, If(_esVenta, 480, 190), 74)
        Poner(cab, "Detalle", _detalle, If(_esVenta, 590, 300), 74)
        _lblInfoTercero.AutoSize = True
        _lblInfoTercero.ForeColor = Tema.Gris
        _lblInfoTercero.Location = New Point(0, 108)
        cab.Controls.Add(_lblInfoTercero)
        _chkFactura.Location = New Point(0, 132)
        cab.Controls.Add(_chkFactura)
        _panelFactura.Location = New Point(110, 126)
        _panelFactura.Size = New Size(1200, 32)
        cab.Controls.Add(_panelFactura)
        Dim xf As Integer = 0
        Dim pf = Sub(titulo As String, c As Control)
                     Dim l As New Label() With {.Text = titulo, .AutoSize = True, .Location = New Point(xf, 7)}
                     _panelFactura.Controls.Add(l)
                     c.Location = New Point(xf + l.PreferredWidth + 4, 3)
                     _panelFactura.Controls.Add(c)
                     xf += l.PreferredWidth + c.Width + 14
                 End Sub
        If Not _esVenta Then pf("Fecha fact.", _fFecha)
        pf("Nº factura", _fNro)
        pf("Autorización/CUF", _fAut)
        pf("Cód. control", _fCtl)
        pf("NIT", _fNit)
        pf("Razón social", _fRazon)
        _panelFactura.Enabled = False
        ' ------ grilla ------
        _grid.MostrarStock = _esVenta
        _grid.PedirVencimiento = Not _esVenta
        _grid.SoloInventariables = False
        _grid.TextoPrecio = If(_esVenta, "Precio venta", "Precio compra")
        _grid.AlmacenStock = Function() _almacen.ValorId
        _grid.PrecioDe = AddressOf PrecioSugerido
        _grid.Iniciar()
        ' ------ pie ------
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 150, .BackColor = Color.White, .Padding = New Padding(16, 6, 16, 6)}
        AddHandler pie.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, 0, pie.Width, 0)
        Dim t As New TableLayoutPanel() With {.Location = New Point(560, 4), .Size = New Size(520, 126), .ColumnCount = 4}
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
        t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
        Dim agregar = Sub(titulo As String, c As Control, col As Integer, fila As Integer)
                          t.Controls.Add(New Label() With {.Text = titulo, .AutoSize = False, .Dock = DockStyle.Fill, .TextAlign = ContentAlignment.MiddleLeft}, col, fila)
                          c.Dock = DockStyle.Fill
                          t.Controls.Add(c, col + 1, fila)
                      End Sub
        _lblSub.TextAlign = ContentAlignment.MiddleRight
        _lblTotal.TextAlign = ContentAlignment.MiddleRight
        _lblTotal.Font = Tema.FuenteGrande
        _lblTotal.ForeColor = Tema.Azul
        _lblSaldo.TextAlign = ContentAlignment.MiddleRight
        agregar("Subtotal", _lblSub, 0, 0)
        agregar("Descuento", _desc, 2, 0)
        agregar("TOTAL", _lblTotal, 0, 1)
        agregar("Recargo", _rec, 2, 1)
        agregar("Anticipo aplicado (Bs)", _anticipo, 0, 2)
        agregar("A cuenta (Bs)", _acuenta, 2, 2)
        agregar("Saldo a crédito", _lblSaldo, 0, 3)
        pie.Controls.Add(t)
        _lblImp.AutoSize = True
        _lblImp.Location = New Point(16, 10)
        _lblImp.Font = Tema.FuenteNegrita
        _lblImp.ForeColor = Tema.Azul
        pie.Controls.Add(_lblImp)
        _lblAntic.AutoSize = True
        _lblAntic.ForeColor = Tema.Gris
        _lblAntic.Location = New Point(16, 36)
        pie.Controls.Add(_lblAntic)
        Poner(pie, If(_esVenta, "Cobrar en", "Pagar con"), _cuentaPago, 0, 62)
        Poner(pie, "Vence", _venc, 0, 94)
        Dim bGuardar As Button = Tema.Boton("Guardar (F10)", Tema.TipoBoton.Primario, 120)
        Dim bNuevo As Button = Tema.Boton("Limpiar", Tema.TipoBoton.Secundario, 80)
        Dim bLista As Button = Tema.Boton("Ver documentos", Tema.TipoBoton.Secundario, 130)
        bGuardar.Location = New Point(1100, 20)
        bNuevo.Location = New Point(1100, 60)
        bLista.Location = New Point(1100, 98)
        pie.Controls.AddRange({bGuardar, bNuevo, bLista})
        Controls.Add(_grid)
        Controls.Add(pie)
        Controls.Add(cab)
        Controls.Add(banner)
        ' ------ datos ------
        _almacen.Cargar(Ctx.Db.Query("SELECT Id, Nombre FROM Almacen WHERE Activo=1 ORDER BY Codigo"), "Id", "Nombre", False)
        If _esVenta Then _vendedor.Cargar(Ctx.Db.Query("SELECT Id, Nombre FROM Vendedor WHERE Activo=1 ORDER BY Nombre"), "Id", "Nombre", True, "(sin vendedor)")
        _fecha.MinDate = Ctx.Gestion.FechaInicio
        _fecha.MaxDate = Ctx.Gestion.FechaFin
        _fFecha.MinDate = Ctx.Gestion.FechaInicio
        _fFecha.MaxDate = Ctx.Gestion.FechaFin
        _venc.MinDate = Ctx.Gestion.FechaInicio
        _venc.MaxDate = Ctx.Gestion.FechaFin.AddYears(2)
        If Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin Then
            _fecha.Value = Date.Today
            _fFecha.Value = Date.Today
        End If
        _venc.Value = If(_fecha.Value.AddDays(30) <= _venc.MaxDate, _fecha.Value.AddDays(30), _venc.MaxDate)
        _tc.Valor = Svc.TipoCambio.Dolar(_fecha.Value)
        _cuentaPago.CuentaId = Ctx.CuentaParamOpcional(ParamKeys.CtaCaja)
        ' ------ eventos ------
        AddHandler _rbCredito.CheckedChanged, Sub(o, ev) AjustarTipo()
        AddHandler _chkFactura.CheckedChanged, Sub(o, ev)
                                                   _panelFactura.Enabled = _chkFactura.Checked
                                                   Totales()
                                               End Sub
        AddHandler _fecha.ValueChanged, Sub(o, ev)
                                            _tc.Valor = Svc.TipoCambio.Dolar(_fecha.Value)
                                            _fFecha.Value = _fecha.Value
                                        End Sub
        AddHandler _almacen.SelectionChangeCommitted, Sub(o, ev) _grid.RefrescarStock()
        AddHandler _tercero.SeleccionCambiada, AddressOf TerceroCambio
        AddHandler _grid.LineasCambiaron, Sub(o, ev) Totales()
        For Each c As CampoImporte In {_desc, _rec, _anticipo, _acuenta}
            AddHandler c.ValorCambiado, Sub(o, ev) Totales()
        Next
        AddHandler _moneda.SelectionChangeCommitted, Sub(o, ev) Totales()
        AddHandler bGuardar.Click, Sub(o, ev) Guardar()
        AddHandler bNuevo.Click, Sub(o, ev) Limpiar()
        AddHandler bLista.Click, Sub(o, ev) Escritorio.AbrirNueva(New DocumentosListaForm(_esVenta), If(_esVenta, "VentasLista", "ComprasLista"))
        AddHandler KeyDown, Sub(o, ev)
                                If ev.KeyCode = Keys.F10 Then
                                    ev.Handled = True
                                    Guardar()
                                End If
                            End Sub
        AjustarTipo()
        ActualizarNumero()
        Totales()
        _tercero.Focus()
    End Sub

    Private Function PrecioSugerido(it As ItemDto) As Decimal
        Dim usd As Boolean = _moneda.ValorTexto = "USD"
        Dim tc As Decimal = If(_tc.Valor > 0D, _tc.Valor, 1D)
        Dim enBs As Decimal
        If _esVenta Then
            Dim p As Decimal = it.Precio(_nivelPrecio)
            enBs = If(it.Moneda = "USD", p * tc, p)
        Else
            Dim f As DataRow = Ctx.Db.Query("SELECT UltimoCosto, CostoProm FROM Item WHERE Id=@i", "i", it.Id).Rows.Cast(Of DataRow)().FirstOrDefault()
            If f Is Nothing Then Return 0D
            enBs = If(f.GetD("UltimoCosto") <> 0D, f.GetD("UltimoCosto"), f.GetD("CostoProm"))
            If _chkFactura.Checked Then enBs = (enBs / (1D - Svc.Facturas.IvaPct / 100D)).R2()
        End If
        Return If(usd, (enBs / tc).R2(), enBs)
    End Function

    Private Sub TerceroCambio(o As Object, e As EventArgs)
        Dim t As TerceroDto = If(_tercero.SeleccionId = 0, Nothing, Svc.Terceros.Obtener(_tercero.SeleccionId))
        _anticipoDisp = 0D
        If t Is Nothing Then
            _lblInfoTercero.Text = ""
            _nivelPrecio = "A"
        Else
            _nivelPrecio = If(t.NivelPrecio = "", "A", t.NivelPrecio)
            Dim clase As String = If(_esVenta, "CXC", "CXP")
            Dim saldo As Decimal = Svc.Terceros.Saldo(t.Id, clase)
            _anticipoDisp = If(saldo < 0D, -saldo, 0D)
            _lblInfoTercero.Text = If(saldo >= 0D, If(_esVenta, "Saldo por cobrar: Bs ", "Saldo por pagar: Bs "), "Anticipo disponible: Bs ") & Math.Abs(saldo).ToString("N2", FormatoVal.Cultura) &
                If(_esVenta AndAlso t.LimiteCredito > 0D, "   ·   Límite de crédito: Bs " & t.LimiteCredito.ToString("N2", FormatoVal.Cultura), "") & "   ·   NIT: " & t.Nit
            If t.DiasCredito > 0 Then _venc.Value = If(_fecha.Value.AddDays(t.DiasCredito) <= _venc.MaxDate, _fecha.Value.AddDays(t.DiasCredito), _venc.MaxDate)
            If _fNit.Text = "" Then _fNit.Text = t.Nit
            If _fRazon.Text = "" Then _fRazon.Text = t.Nombre
        End If
        _lblAntic.Text = If(_anticipoDisp > 0D, "Anticipo disponible para aplicar: Bs " & _anticipoDisp.ToString("N2", FormatoVal.Cultura), "")
        Totales()
    End Sub

    Private Sub AjustarTipo()
        Dim cred As Boolean = _rbCredito.Checked
        _acuenta.Enabled = cred
        _venc.Enabled = cred
        If Not cred Then _acuenta.Valor = 0D
        ActualizarNumero()
        Totales()
    End Sub

    Private Sub ActualizarNumero()
        Dim clave As String = If(_esVenta, "VENTA_", "COMPRA_") & If(_rbCredito.Checked, "CRE", "CON")
        Dim sig As Integer = Ctx.Db.ScalarInt("SELECT Valor FROM Secuencia WHERE Clave=@k", "k", clave) + 1
        _lblNumero.Text = If(_esVenta, "Venta ", "Compra ") & If(_rbCredito.Checked, "a crédito", "al contado") & " Nº " & sig
    End Sub

    Private Sub Totales()
        Dim usd As Boolean = _moneda.ValorTexto = "USD"
        Dim sim As String = If(usd, "$us ", "Bs ")
        Dim tc As Decimal = If(_tc.Valor > 0D, _tc.Valor, 1D)
        Dim sub1 As Decimal = _grid.Subtotal()
        Dim total As Decimal = sub1 - _desc.Valor + _rec.Valor
        Dim totalBs As Decimal = If(usd, (total * tc).R2(), total)
        _lblSub.Text = sim & sub1.ToString("N2", FormatoVal.Cultura)
        _lblTotal.Text = sim & total.ToString("N2", FormatoVal.Cultura)
        If _chkFactura.Checked Then
            Dim imp As Decimal = (totalBs * Svc.Facturas.IvaPct / 100D).R2()
            _lblImp.Text = If(_esVenta, "Débito fiscal ", "Crédito fiscal ") & Svc.Facturas.IvaPct.ToString("0.##") & "%: Bs " & imp.ToString("N2", FormatoVal.Cultura) & "    ·    " & If(_esVenta, "Venta neta: Bs ", "Costo neto: Bs ") & (totalBs - imp).ToString("N2", FormatoVal.Cultura)
        Else
            _lblImp.Text = "Sin factura: no genera " & If(_esVenta, "débito fiscal.", "crédito fiscal.")
        End If
        Dim saldo As Decimal = totalBs - _anticipo.Valor - If(_rbCredito.Checked, _acuenta.Valor, 0D)
        _lblSaldo.Text = If(_rbCredito.Checked, "Bs " & Math.Max(0D, saldo).ToString("N2", FormatoVal.Cultura), "-")
        If usd Then _lblTotal.Text &= "  (Bs " & totalBs.ToString("N2", FormatoVal.Cultura) & ")"
    End Sub

    Private Sub Limpiar()
        _grid.Limpiar()
        _desc.Valor = 0D
        _rec.Valor = 0D
        _anticipo.Valor = 0D
        _acuenta.Valor = 0D
        _detalle.Text = ""
        _fNro.Text = ""
        _fAut.Text = ""
        _fCtl.Text = ""
        _fNit.Text = ""
        _fRazon.Text = ""
        _chkFactura.Checked = False
        _tercero.Limpiar()
        _rbContado.Checked = True
        ActualizarNumero()
        Totales()
        _tercero.Focus()
    End Sub

    Private Sub Guardar()
        Dim d As New DocumentoDto With {.Tipo = If(_rbCredito.Checked, "CRE", "CON"), .Fecha = _fecha.Value.Date, .TerceroId = _tercero.SeleccionId, .AlmacenId = _almacen.ValorId,
            .VendedorId = If(_esVenta, _vendedor.ValorId, 0), .Moneda = _moneda.ValorTexto, .TC = _tc.Valor, .Detalle = _detalle.Text.Trim(), .Descuento = _desc.Valor, .Recargo = _rec.Valor,
            .ConFactura = _chkFactura.Checked, .Anticipo = _anticipo.Valor, .ACuenta = If(_rbCredito.Checked, _acuenta.Valor, 0D), .CuentaPagoId = _cuentaPago.CuentaId}
        If _rbCredito.Checked Then d.Vencimiento = _venc.Value.Date
        Try
            For Each l In _grid.Lineas()
                d.Lines.Add(New DocLine With {.ItemId = l.ItemId, .Descripcion = l.Descripcion, .Cantidad = l.Cantidad, .PrecioUnit = l.Precio, .FechaVenc = l.FechaVenc})
            Next
            If d.Lines.Count = 0 Then Throw New InvalidOperationException("Agregue al menos un ítem.")
            If d.ConFactura Then
                d.Factura = New FacturaDto With {.NroFactura = _fNro.Text.Trim(), .Autorizacion = _fAut.Text.Trim(), .CodControl = _fCtl.Text.Trim(), .Nit = _fNit.Text.Trim(), .RazonSocial = _fRazon.Text.Trim(), .Fecha = If(_esVenta, _fecha.Value.Date, _fFecha.Value.Date)}
                If d.Factura.NroFactura = "" Then Throw New InvalidOperationException("Ingrese el número de factura.")
            End If
            Dim r As DocumentoResultado
            Using Msg.Cursor_(True)
                r = If(_esVenta, Svc.Ventas.Registrar(d), Svc.Compras.Registrar(d))
            End Using
            Dim msg1 As String = If(_esVenta, "Venta", "Compra") & " Nº " & r.Numero & " registrada." & vbCrLf & "Total: Bs " & r.Total.ToString("N2", FormatoVal.Cultura) &
                If(r.ImpuestoFiscal > 0D, vbCrLf & If(_esVenta, "Débito fiscal: Bs ", "Crédito fiscal: Bs ") & r.ImpuestoFiscal.ToString("N2", FormatoVal.Cultura), "") &
                If(_esVenta AndAlso r.Costo > 0D, vbCrLf & "Costo de venta: Bs " & r.Costo.ToString("N2", FormatoVal.Cultura), "")
            If Msg.Confirmar(msg1 & vbCrLf & vbCrLf & "¿Desea imprimir la nota?", If(_esVenta, "Venta registrada", "Compra registrada")) Then Informes.Abrir(If(_esVenta, "nota_venta", "nota_compra"), New Dictionary(Of String, Object) From {{"id", r.Id}}, False)
            Limpiar()
            _grid.RecargarItems()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class

''' <summary>Listado de ventas o compras del período: ver nota, anular, nueva.</summary>
Public Class DocumentosListaForm
    Inherits ListaForm

    Private ReadOnly _esVenta As Boolean
    Private ReadOnly _desde As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}

    Public Sub New(esVenta As Boolean)
        _esVenta = esVenta
    End Sub

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return If(_esVenta, "Ventas registradas", "Compras registradas")
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Doble clic para ver la nota. Para corregir un documento, anúlelo y regístrelo nuevamente (se conserva la numeración)."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return If(_esVenta, "COM.VENTAS", "COM.COMPRAS")
        End Get
    End Property
    Protected Overrides ReadOnly Property PermiteEliminar As Boolean
        Get
            Return False
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        _desde.MinDate = Ctx.Gestion.FechaInicio
        _desde.MaxDate = Ctx.Gestion.FechaFin
        _hasta.MinDate = Ctx.Gestion.FechaInicio
        _hasta.MaxDate = Ctx.Gestion.FechaFin
        _desde.Value = Ctx.Gestion.FechaInicio
        _hasta.Value = Ctx.Gestion.FechaFin
        Barra.Controls.AddRange({New Label() With {.Text = "Del", .AutoSize = True, .Margin = New Padding(10, 8, 4, 0)}, _desde, New Label() With {.Text = "al", .AutoSize = True, .Margin = New Padding(8, 8, 4, 0)}, _hasta})
        AddHandler _desde.ValueChanged, Sub(o, e) Refrescar()
        AddHandler _hasta.ValueChanged, Sub(o, e) Refrescar()
        Dim bNota As Button = Tema.Boton("Ver nota", Tema.TipoBoton.Secundario, 84)
        Dim bAnular As Button = Tema.Boton("Anular", Tema.TipoBoton.Peligro, 80)
        Barra.Controls.AddRange({bNota, bAnular})
        AddHandler bNota.Click, Sub(o, e) VerNota()
        AddHandler bAnular.Click, Sub(o, e) Anular()
        bAnular.Enabled = Sesion.Puede(PermisoEdicion)
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = If(_esVenta, Svc.Ventas.Listar(_desde.Value.Date, _hasta.Value.Date), Svc.Compras.Listar(_desde.Value.Date, _hasta.Value.Date))
        dt.Columns.Add("Doc", GetType(String))
        dt.Columns.Add("Tercero", GetType(String))
        dt.Columns.Add("EstTxt", GetType(String))
        For Each r As DataRow In dt.Rows
            r("Doc") = r.GetS("Tipo") & "-" & r.GetS("Numero")
            r("Tercero") = If(_esVenta, r.GetS("Cliente"), r.GetS("Proveedor"))
            r("EstTxt") = If(r.GetS("Estado") = "A", "ANULADA", "Vigente")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Doc", "Documento", 90)
        Tema.ColFecha(Grid, "Fecha", "Fecha")
        Tema.ColTexto(Grid, "Tercero", If(_esVenta, "Cliente", "Proveedor"), 280, True)
        Tema.ColTexto(Grid, "NroFactura", "Factura", 90)
        Tema.ColImporte(Grid, "TotalBs", "Total Bs", 110)
        Tema.ColImporte(Grid, "SaldoBs", "Saldo Bs", 110)
        Tema.ColTexto(Grid, "EstTxt", "Estado", 80)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If fila.GetS("Estado") = "A" Then estilo.ForeColor = Tema.Rojo
    End Sub

    Protected Overrides Sub Nuevo()
        Escritorio.AbrirNueva(New DocumentoForm(_esVenta), Nothing)
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Informes.Abrir(If(_esVenta, "nota_venta", "nota_compra"), New Dictionary(Of String, Object) From {{"id", fila.GetI("Id")}}, False)
    End Sub

    Private Sub VerNota()
        Dim f As DataRow = FilaActual()
        If f IsNot Nothing Then Editar(f)
    End Sub

    Private Sub Anular()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then Return
        If f.GetS("Estado") = "A" Then Return
        Dim motivo As String = Msg.Pedir("Motivo de la anulación del documento " & f.GetS("Doc") & ":", "Anular")
        If String.IsNullOrWhiteSpace(motivo) Then Return
        If Intentar(Sub()
                        If _esVenta Then Svc.Ventas.Anular(f.GetI("Id"), motivo) Else Svc.Compras.Anular(f.GetI("Id"), motivo)
                    End Sub) Then
            Msg.Info("Documento anulado: se revirtieron inventario, asientos y cuenta corriente.")
            Refrescar()
        End If
    End Sub
End Class

''' <summary>Cobros a clientes y pagos a proveedores aplicados a documentos pendientes, con distribución automática.</summary>
Public Class CobroPagoForm
    Inherits FormBase

    Private ReadOnly _rbCobro As New RadioButton() With {.Text = "Cobro a cliente", .Checked = True, .AutoSize = True}
    Private ReadOnly _rbPago As New RadioButton() With {.Text = "Pago a proveedor", .AutoSize = True}
    Private ReadOnly _tercero As New PickerBusqueda() With {.Width = 420}
    Private ReadOnly _fecha As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _cuenta As New PickerCuenta() With {.Width = 380}
    Private ReadOnly _cheque As New TextBox() With {.MaxLength = 30, .Width = 120}
    Private ReadOnly _banco As New TextBox() With {.MaxLength = 60, .Width = 160}
    Private ReadOnly _glosa As New TextBox() With {.MaxLength = 200, .Width = 520}
    Private ReadOnly _importe As New CampoImporte() With {.Width = 130}
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _lblInfo As New Label()
    Private ReadOnly _lblResumen As New Label()
    Private _pend As DataTable

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Cobros y pagos"
        End Get
    End Property

    Private Function Clase() As String
        Return If(_rbCobro.Checked, "CXC", "CXP")
    End Function

    Private Sub Poner(cont As Control, titulo As String, c As Control, x As Integer, y As Integer)
        Dim l As New Label() With {.Text = titulo, .AutoSize = True, .Location = New Point(x, y + 4)}
        cont.Controls.Add(l)
        c.Location = New Point(x + l.PreferredWidth + 6, y)
        cont.Controls.Add(c)
    End Sub

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Cobros y pagos"
        Dim banner As Panel = Tema.Banner("Cobros a clientes y pagos a proveedores", "Aplique el importe a los documentos pendientes; el excedente queda como anticipo. Genera el comprobante de ingreso o egreso.")
        Dim cab As New Panel() With {.Dock = DockStyle.Top, .Height = 150, .BackColor = Color.White, .Padding = New Padding(16, 8, 16, 4)}
        AddHandler cab.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, cab.Height - 1, cab.Width, cab.Height - 1)
        Dim pt As New FlowLayoutPanel() With {.Location = New Point(0, 6), .Size = New Size(380, 30), .WrapContents = False}
        pt.Controls.AddRange({_rbCobro, _rbPago})
        cab.Controls.Add(pt)
        Poner(cab, "Fecha", _fecha, 420, 6)
        Poner(cab, "Cliente", _tercero, 0, 40)
        Poner(cab, If(_rbCobro.Checked, "Depositar en", "Pagar desde"), _cuenta, 0, 74)
        Poner(cab, "Cheque Nº", _cheque, 520, 74)
        Poner(cab, "Banco", _banco, 720, 74)
        Poner(cab, "Glosa", _glosa, 0, 108)
        _fecha.MinDate = Ctx.Gestion.FechaInicio
        _fecha.MaxDate = Ctx.Gestion.FechaFin
        If Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin Then _fecha.Value = Date.Today
        _cuenta.CuentaId = Ctx.CuentaParamOpcional(ParamKeys.CtaCaja)
        ConfigurarTercero()
        _lblInfo.AutoSize = True
        _lblInfo.ForeColor = Tema.Gris
        _lblInfo.Dock = DockStyle.Top
        _lblInfo.Padding = New Padding(16, 8, 0, 4)
        Tema.EstiloGrid(_grid, True)
        _grid.RowHeadersVisible = False
        Tema.ColTexto(_grid, "Doc", "Documento", 100).ReadOnly = True
        Tema.ColFecha(_grid, "Fecha", "Fecha").ReadOnly = True
        Tema.ColFecha(_grid, "Venc", "Vence").ReadOnly = True
        Tema.ColTexto(_grid, "Detalle", "Detalle", 260, True).ReadOnly = True
        Tema.ColImporte(_grid, "Total", "Total Bs", 110).ReadOnly = True
        Tema.ColImporte(_grid, "Saldo", "Saldo Bs", 110).ReadOnly = True
        Dim colAp As DataGridViewTextBoxColumn = Tema.ColImporte(_grid, "Aplicar", "Aplicar Bs", 120)
        colAp.DefaultCellStyle.BackColor = Color.FromArgb(255, 252, 232)
        _grid.EditMode = DataGridViewEditMode.EditOnEnter
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 108, .BackColor = Color.White, .Padding = New Padding(16, 8, 16, 8)}
        AddHandler pie.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, 0, pie.Width, 0)
        Poner(pie, "Importe recibido / pagado", _importe, 0, 6)
        Dim bDist As Button = Tema.Boton("Distribuir (más antiguos primero)", Tema.TipoBoton.Secundario, 220)
        bDist.Location = New Point(300, 4)
        pie.Controls.Add(bDist)
        _lblResumen.AutoSize = True
        _lblResumen.Font = Tema.FuenteGrande
        _lblResumen.ForeColor = Tema.Azul
        _lblResumen.Location = New Point(0, 44)
        pie.Controls.Add(_lblResumen)
        Dim bReg As Button = Tema.Boton("Registrar (F10)", Tema.TipoBoton.Primario, 140)
        bReg.Location = New Point(1000, 20)
        pie.Controls.Add(bReg)
        Controls.Add(_grid)
        Controls.Add(_lblInfo)
        Controls.Add(pie)
        Controls.Add(cab)
        Controls.Add(banner)
        AddHandler _rbCobro.CheckedChanged, Sub(o, ev) CambioClase()
        AddHandler _tercero.SeleccionCambiada, Sub(o, ev) CargarPendientes()
        AddHandler bDist.Click, Sub(o, ev) Distribuir()
        AddHandler bReg.Click, Sub(o, ev) Registrar()
        AddHandler _importe.ValorCambiado, Sub(o, ev) Resumen()
        AddHandler _grid.CellEndEdit, Sub(o, ev) Resumen()
        AddHandler _grid.CellParsing, Sub(o, ev)
                                          If ev.ColumnIndex = _grid.Columns("Aplicar").Index Then
                                              Dim d As Decimal
                                              If Numeros.Parse(ToStr(ev.Value), d) Then ev.Value = If(d = 0D, CObj(Nothing), CObj(d)) Else ev.Value = Nothing
                                              ev.ParsingApplied = True
                                          End If
                                      End Sub
        AddHandler _grid.DataError, Sub(o, ev) ev.ThrowException = False
        AddHandler KeyDown, Sub(o, ev)
                                If ev.KeyCode = Keys.F10 Then
                                    ev.Handled = True
                                    Registrar()
                                End If
                            End Sub
        CargarPendientes()
    End Sub

    Private Sub ConfigurarTercero()
        Dim c As String = Clase()
        _tercero.Configurar(If(c = "CXC", "Buscar cliente", "Buscar proveedor"), Function() Svc.Terceros.Listar(Clase(), "", True),
                            {New ColumnaBusqueda("Codigo", "Código", 90), New ColumnaBusqueda("Nombre", "Nombre / razón social", 340), New ColumnaBusqueda("Nit", "NIT", 110)}, "Id", Function(r) r.GetS("Codigo") & " - " & r.GetS("Nombre"))
    End Sub

    Private Sub CambioClase()
        _tercero.Limpiar()
        ConfigurarTercero()
        CargarPendientes()
    End Sub

    Private Sub CargarPendientes()
        _grid.Rows.Clear()
        _pend = Nothing
        If _tercero.SeleccionId = 0 Then
            _lblInfo.Text = "Seleccione el " & If(Clase() = "CXC", "cliente", "proveedor") & " para ver sus documentos pendientes."
            Resumen()
            Return
        End If
        _pend = Svc.Terceros.Pendientes(_tercero.SeleccionId, Clase())
        For Each r As DataRow In _pend.Rows
            Dim i As Integer = _grid.Rows.Add()
            Dim row As DataGridViewRow = _grid.Rows(i)
            row.Tag = r.GetI("Id")
            row.Cells("Doc").Value = r.GetS("Tipo") & "-" & r.GetS("Numero")
            row.Cells("Fecha").Value = r.GetDt("Fecha")
            Dim v As Date? = ToDateOrNull(r.Cell("Vencimiento"))
            row.Cells("Venc").Value = If(v.HasValue, CObj(v.Value), CObj(r.GetDt("Fecha")))
            row.Cells("Detalle").Value = r.GetS("Detalle")
            row.Cells("Total").Value = r.GetD("TotalBs")
            row.Cells("Saldo").Value = r.GetD("SaldoBs")
        Next
        Dim saldo As Decimal = Svc.Terceros.Saldo(_tercero.SeleccionId, Clase())
        _lblInfo.Text = If(saldo >= 0D, "Saldo: Bs ", "Anticipo vigente: Bs ") & Math.Abs(saldo).ToString("N2", FormatoVal.Cultura) & "   ·   " & _pend.Rows.Count & " documento(s) pendiente(s)"
        Resumen()
    End Sub

    Private Function TotalAplicado() As Decimal
        Dim t As Decimal
        For Each r As DataGridViewRow In _grid.Rows
            t += ToDec(r.Cells("Aplicar").Value)
        Next
        Return t
    End Function

    Private Sub Resumen()
        Dim ap As Decimal = TotalAplicado()
        Dim imp As Decimal = If(_importe.Valor > 0D, _importe.Valor, ap)
        Dim ant As Decimal = Math.Max(0D, imp - ap)
        _lblResumen.Text = "Aplicado a documentos: Bs " & ap.ToString("N2", FormatoVal.Cultura) & "      Excedente como anticipo: Bs " & ant.ToString("N2", FormatoVal.Cultura)
        _lblResumen.ForeColor = If(imp < ap - 0.005D, Tema.Rojo, Tema.Azul)
    End Sub

    Private Sub Distribuir()
        If _grid.Rows.Count = 0 Then Return
        Dim resto As Decimal = _importe.Valor
        If resto <= 0D Then
            Msg.Aviso("Ingrese primero el importe recibido o pagado.")
            _importe.Focus()
            Return
        End If
        For Each r As DataGridViewRow In _grid.Rows
            Dim saldo As Decimal = ToDec(r.Cells("Saldo").Value)
            Dim x As Decimal = Math.Min(saldo, resto)
            r.Cells("Aplicar").Value = If(x > 0D, CObj(x), Nothing)
            resto -= x
        Next
        Resumen()
    End Sub

    Private Sub Registrar()
        _grid.EndEdit()
        Dim d As New CobroPagoDto With {.TerceroId = _tercero.SeleccionId, .Clase = Clase(), .Fecha = _fecha.Value.Date, .Glosa = _glosa.Text.Trim(), .CuentaId = _cuenta.CuentaId, .Cheque = _cheque.Text.Trim(), .Banco = _banco.Text.Trim()}
        Dim ap As Decimal = 0D
        For Each r As DataGridViewRow In _grid.Rows
            Dim m As Decimal = ToDec(r.Cells("Aplicar").Value)
            If m > 0D Then
                d.Aplicaciones.Add(New AplicacionDoc With {.DocId = CInt(r.Tag), .Monto = m})
                ap += m
            End If
        Next
        Dim imp As Decimal = If(_importe.Valor > 0D, _importe.Valor, ap)
        If imp < ap - 0.005D Then
            Msg.Aviso("El importe recibido es menor al total aplicado a documentos.")
            Return
        End If
        d.AnticipoNuevo = Math.Max(0D, imp - ap)
        Try
            Dim id As Integer
            Using Msg.Cursor_(True)
                id = Svc.CobrosPagos.Registrar(d)
            End Using
            If Msg.Confirmar(If(Clase() = "CXC", "Cobro", "Pago") & " registrado correctamente (comprobante generado)." & vbCrLf & "¿Desea imprimir el comprobante?", "Registrado") Then Informes.Abrir("comprobante", New Dictionary(Of String, Object) From {{"id", id}}, False)
            _importe.Valor = 0D
            _cheque.Text = ""
            _glosa.Text = ""
            CargarPendientes()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class
