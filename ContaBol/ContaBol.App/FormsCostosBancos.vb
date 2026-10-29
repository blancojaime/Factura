Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Órdenes de producción: costos de materia prima, mano de obra y costos indirectos hasta producto terminado.</summary>
Public Class ProduccionForm
    Inherits ListaForm

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Órdenes de producción"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Abra una orden, cargue la materia prima, la mano de obra y los costos indirectos, y ciérrela para ingresar el producto terminado con su costo."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "COS.PRODUCCION"
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim bG As Button = Tema.Boton("Gestionar orden", Tema.TipoBoton.Secundario, 130)
        Dim bH As Button = Tema.Boton("Hoja de costos", Tema.TipoBoton.Secundario, 120)
        Barra.Controls.AddRange({bG, bH})
        AddHandler bG.Click, Sub(o, e)
                                 Dim f As DataRow = FilaActual()
                                 If f IsNot Nothing Then Gestionar(f.GetI("Id"))
                             End Sub
        AddHandler bH.Click, Sub(o, e)
                                 Dim f As DataRow = FilaActual()
                                 If f IsNot Nothing Then Informes.Abrir("hoja_costos", New Dictionary(Of String, Object) From {{"orden", f.GetI("Id")}}, False)
                             End Sub
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = Svc.Produccion.Listar()
        dt.Columns.Add("EstTxt", GetType(String))
        dt.Columns.Add("Total", GetType(Decimal))
        For Each r As DataRow In dt.Rows
            r("EstTxt") = If(r.GetS("Estado") = "T", "Terminada", "Abierta")
            r("Total") = r.GetD("CostoMp") + r.GetD("CostoMod") + r.GetD("CostoCif")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Numero", "Orden", 60)
        Tema.ColFecha(Grid, "Fecha", "Fecha")
        Tema.ColTexto(Grid, "Producto", "Producto", 260, True)
        Tema.ColImporte(Grid, "Cantidad", "Cantidad", 80, "N2")
        Tema.ColImporte(Grid, "CostoMp", "Materia prima", 100)
        Tema.ColImporte(Grid, "CostoMod", "Mano de obra", 100)
        Tema.ColImporte(Grid, "CostoCif", "CIF", 90)
        Tema.ColImporte(Grid, "Total", "Costo total", 105)
        Tema.ColTexto(Grid, "EstTxt", "Estado", 80)
    End Sub

    Protected Overrides Sub Nuevo()
        Dim campos As New List(Of CampoUI) From {
            CampoUI.Fec("Fecha", "Fecha de apertura"),
            CampoUI.Lk("ItemId", "Producto a fabricar", Function() Svc.Inventario.ListarItems("", True), "Descripcion", True),
            CampoUI.Cant("Cantidad", "Cantidad a producir", 2),
            CampoUI.Lk("AlmacenMpId", "Almacén de materia prima", Function() Ctx.Db.Query("SELECT Id, Nombre FROM Almacen WHERE Activo=1 ORDER BY Codigo"), "Nombre", True),
            CampoUI.Lk("AlmacenPtId", "Almacén de producto terminado", Function() Ctx.Db.Query("SELECT Id, Nombre FROM Almacen WHERE Activo=1 ORDER BY Codigo"), "Nombre", True),
            CampoUI.Txt("Detalle", "Detalle / observaciones", 200, False, True)}
        Dim nuevoId As Integer = 0
        Using d As New FichaDialog("Nueva orden de producción", campos, New Dictionary(Of String, Object) From {{"Fecha", Date.Today}},
            Sub(v) nuevoId = Svc.Produccion.Abrir(ToDate(v("Fecha")), ToInt(v("ItemId")), ToDec(v("Cantidad")), ToInt(v("AlmacenMpId")), ToInt(v("AlmacenPtId")), ToStr(v("Detalle"))), "", 720)
            If d.ShowDialog(FindForm()) <> DialogResult.OK Then Return
        End Using
        If nuevoId <> 0 Then Gestionar(nuevoId)
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Gestionar(fila.GetI("Id"))
    End Sub

    Protected Overrides Sub Eliminar(fila As DataRow)
        Svc.Produccion.Eliminar(fila.GetI("Id"))
    End Sub

    Private Sub Gestionar(id As Integer)
        Using f As New OrdenProduccionDialog(id)
            f.ShowDialog(FindForm())
        End Using
        Refrescar()
    End Sub
End Class

''' <summary>Gestión de una orden: materia prima, mano de obra, costos indirectos y cierre.</summary>
Public Class OrdenProduccionDialog
    Inherits Form

    Private ReadOnly _id As Integer
    Private ReadOnly _tabs As New TabControl()
    Private ReadOnly _gMp As New DataGridView()
    Private ReadOnly _gMod As New DataGridView()
    Private ReadOnly _gCif As New DataGridView()
    Private ReadOnly _lblResumen As New Label()
    Private ReadOnly _bCerrar As Button = Tema.Boton("Cerrar orden (producto terminado)", Tema.TipoBoton.Exito, 250)
    Private ReadOnly _barraMp As New FlowLayoutPanel()
    Private ReadOnly _barraMod As New FlowLayoutPanel()
    Private ReadOnly _barraCif As New FlowLayoutPanel()

    Public Sub New(id As Integer)
        _id = id
        Tema.Aplicar(Me)
        Text = "Orden de producción"
        StartPosition = FormStartPosition.CenterParent
        ClientSize = New Size(960, 640)
        MinimumSize = New Size(860, 560)
        ShowInTaskbar = False
        Dim banner As Panel = Tema.Banner("Orden de producción", "")
        _lblResumen.Dock = DockStyle.Top
        _lblResumen.Height = 56
        _lblResumen.Padding = New Padding(16, 8, 16, 0)
        _lblResumen.Font = Tema.FuenteGrande
        _lblResumen.BackColor = Color.White
        _tabs.Dock = DockStyle.Fill
        Dim pMp As New TabPage("1. Materia prima")
        Dim pMod As New TabPage("2. Mano de obra directa")
        Dim pCif As New TabPage("3. Costos indirectos de fabricación")
        _tabs.TabPages.AddRange({pMp, pMod, pCif})
        For Each g As DataGridView In {_gMp, _gMod, _gCif}
            Tema.EstiloGrid(g)
        Next
        Tema.ColFecha(_gMp, "Fecha", "Fecha")
        Tema.ColTexto(_gMp, "Codigo", "Código", 110)
        Tema.ColTexto(_gMp, "Descripcion", "Descripción", 300, True)
        Tema.ColImporte(_gMp, "Cantidad", "Cantidad", 90, "N2")
        Tema.ColImporte(_gMp, "CostoUnitBs", "Costo unit.", 100, "N4")
        Tema.ColImporte(_gMp, "ImporteBs", "Importe", 110)
        Tema.ColTexto(_gMod, "Nombre", "Empleado", 340, True)
        Tema.ColImporte(_gMod, "Horas", "Horas", 80, "N2")
        Tema.ColImporte(_gMod, "CostoHora", "Costo por hora", 110)
        Tema.ColImporte(_gMod, "Monto", "Importe", 110)
        Tema.ColTexto(_gCif, "Detalle", "Detalle", 480, True)
        Tema.ColImporte(_gCif, "Monto", "Importe", 120)
        Dim bMp As Button = Tema.Boton("Consumir materia prima…", Tema.TipoBoton.Primario, 200)
        Dim bMod As Button = Tema.Boton("Agregar horas…", Tema.TipoBoton.Primario, 140)
        Dim bModDel As Button = Tema.Boton("Quitar", Tema.TipoBoton.Peligro, 80)
        Dim bCif As Button = Tema.Boton("Agregar gasto…", Tema.TipoBoton.Primario, 140)
        Dim bCifDel As Button = Tema.Boton("Quitar", Tema.TipoBoton.Peligro, 80)
        For Each b As FlowLayoutPanel In {_barraMp, _barraMod, _barraCif}
            b.Dock = DockStyle.Top
            b.Height = 44
            b.Padding = New Padding(8, 6, 8, 4)
        Next
        _barraMp.Controls.Add(bMp)
        _barraMod.Controls.AddRange({bMod, bModDel})
        _barraCif.Controls.AddRange({bCif, bCifDel})
        pMp.Controls.Add(_gMp)
        pMp.Controls.Add(_barraMp)
        pMod.Controls.Add(_gMod)
        pMod.Controls.Add(_barraMod)
        pCif.Controls.Add(_gCif)
        pCif.Controls.Add(_barraCif)
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 56, .BackColor = Color.White, .Padding = New Padding(14, 10, 14, 8)}
        _bCerrar.Dock = DockStyle.Left
        Dim bHoja As Button = Tema.Boton("Hoja de costos", Tema.TipoBoton.Secundario, 130)
        bHoja.Dock = DockStyle.Right
        Dim bSalir As Button = Tema.Boton("Cerrar ventana", Tema.TipoBoton.Secundario, 120)
        bSalir.Dock = DockStyle.Right
        pie.Controls.Add(_bCerrar)
        pie.Controls.Add(bHoja)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(bSalir)
        Controls.Add(_tabs)
        Controls.Add(pie)
        Controls.Add(_lblResumen)
        Controls.Add(banner)
        AddHandler bMp.Click, Sub(o, e) ConsumirMp()
        AddHandler bMod.Click, Sub(o, e) AgregarMod()
        AddHandler bModDel.Click, Sub(o, e) QuitarMod()
        AddHandler bCif.Click, Sub(o, e) AgregarCif()
        AddHandler bCifDel.Click, Sub(o, e) QuitarCif()
        AddHandler _bCerrar.Click, Sub(o, e) CerrarOrden()
        AddHandler bHoja.Click, Sub(o, e) Informes.Abrir("hoja_costos", New Dictionary(Of String, Object) From {{"orden", _id}}, False)
        AddHandler bSalir.Click, Sub(o, e) Close()
        AddHandler Shown, Sub(o, e) Cargar()
    End Sub

    Private Sub Cargar()
        Dim o As DataRow = Svc.Produccion.Obtener(_id)
        If o Is Nothing Then
            Close()
            Return
        End If
        Dim cerrada As Boolean = o.GetS("Estado") = "T"
        Text = "Orden de producción Nº " & o.GetS("Numero") & " - " & o.GetS("Producto")
        Dim total As Decimal = o.GetD("CostoMp") + o.GetD("CostoMod") + o.GetD("CostoCif")
        _lblResumen.Text = o.GetS("Producto") & "  ·  Cantidad " & o.GetD("Cantidad").ToString("0.##", FormatoVal.Cultura) & If(cerrada, "  ·  TERMINADA", "  ·  ABIERTA") & vbCrLf &
            "Materia prima Bs " & o.GetD("CostoMp").ToString("N2", FormatoVal.Cultura) & "   +   Mano de obra Bs " & o.GetD("CostoMod").ToString("N2", FormatoVal.Cultura) & "   +   CIF Bs " & o.GetD("CostoCif").ToString("N2", FormatoVal.Cultura) & "   =   COSTO TOTAL Bs " & total.ToString("N2", FormatoVal.Cultura)
        _gMp.DataSource = Svc.Produccion.DetalleMp(_id)
        _gMod.DataSource = Svc.Produccion.DetalleMod(_id)
        _gCif.DataSource = Svc.Produccion.DetalleCif(_id)
        For Each b As FlowLayoutPanel In {_barraMp, _barraMod, _barraCif}
            b.Enabled = Not cerrada AndAlso Sesion.Puede("COS.PRODUCCION")
        Next
        _bCerrar.Enabled = Not cerrada AndAlso Sesion.Puede("COS.PRODUCCION")
    End Sub

    Private Sub Ejecutar(accion As Action)
        Try
            Using Msg.Cursor_(True)
                accion()
            End Using
            Cargar()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub ConsumirMp()
        Dim o As DataRow = Svc.Produccion.Obtener(_id)
        Using f As New Form()
            Tema.Aplicar(f)
            f.Text = "Consumo de materia prima"
            f.StartPosition = FormStartPosition.CenterParent
            f.ClientSize = New Size(820, 460)
            f.ShowInTaskbar = False
            Dim fecha As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110, .Location = New Point(70, 12)}
            fecha.MinDate = Ctx_().Gestion.FechaInicio
            fecha.MaxDate = Ctx_().Gestion.FechaFin
            If Date.Today >= fecha.MinDate AndAlso Date.Today <= fecha.MaxDate Then fecha.Value = Date.Today
            Dim g As New GridItems() With {.MostrarStock = True, .SoloInventariables = True, .TextoPrecio = "(no se usa)"}
            g.AlmacenStock = Function() o.GetI("AlmacenMpId")
            g.Iniciar()
            g.Dock = DockStyle.None
            g.Location = New Point(12, 48)
            g.Size = New Size(796, 350)
            Dim ok As Button = Tema.Boton("Registrar consumo", Tema.TipoBoton.Primario, 160)
            ok.Location = New Point(648, 412)
            f.Controls.AddRange({New Label() With {.Text = "Fecha", .AutoSize = True, .Location = New Point(12, 16)}, fecha, New Label() With {.Text = "Se descuenta del almacén de materia prima al costo promedio. Ingrese código y cantidad.", .AutoSize = True, .Location = New Point(200, 16), .ForeColor = Tema.Gris}, g, ok})
            AddHandler ok.Click, Sub(s, e)
                                     Try
                                         Dim lineas As New List(Of MovLine)
                                         For Each l In g.Lineas()
                                             lineas.Add(New MovLine With {.ItemId = l.ItemId, .Cantidad = l.Cantidad})
                                         Next
                                         If lineas.Count = 0 Then Throw New InvalidOperationException("Agregue al menos un ítem.")
                                         Svc.Produccion.ConsumirMateriaPrima(_id, fecha.Value.Date, lineas)
                                         f.DialogResult = DialogResult.OK
                                     Catch ex As Exception
                                         Msg.ErrorMsg(ex)
                                     End Try
                                 End Sub
            f.ShowDialog(Me)
        End Using
        Cargar()
    End Sub

    Private Function Ctx_() As Contexto
        Return Sesion.Ctx
    End Function

    Private Sub AgregarMod()
        Dim campos As New List(Of CampoUI) From {
            CampoUI.Lk("EmpleadoId", "Empleado", Function() Svc.Planillas.ListarEmpleados(True), "Nombre", True),
            CampoUI.Cant("Horas", "Horas trabajadas en la orden", 2),
            CampoUI.Imp("CostoHora", "Costo por hora (vacío = haber / 240)")}
        Using d As New FichaDialog("Mano de obra directa", campos, Nothing, Sub(v) Svc.Produccion.AgregarManoObra(_id, ToInt(v("EmpleadoId")), ToDec(v("Horas")), ToDec(v("CostoHora"))), "", 620)
            d.ShowDialog(Me)
        End Using
        Cargar()
    End Sub

    Private Sub QuitarMod()
        If _gMod.CurrentRow Is Nothing Then Return
        Dim id As Integer = ToInt(CType(_gMod.CurrentRow.DataBoundItem, DataRowView)("Id"))
        Ejecutar(Sub() Svc.Produccion.QuitarManoObra(id))
    End Sub

    Private Sub AgregarCif()
        Dim campos As New List(Of CampoUI) From {CampoUI.Txt("Detalle", "Detalle del gasto (energía, depreciación, alquiler...)", 100, True, True), CampoUI.Imp("Monto", "Importe (sin crédito fiscal)", True)}
        Using d As New FichaDialog("Costo indirecto de fabricación", campos, Nothing, Sub(v) Svc.Produccion.AgregarCif(_id, ToStr(v("Detalle")), ToDec(v("Monto"))), "", 620)
            d.ShowDialog(Me)
        End Using
        Cargar()
    End Sub

    Private Sub QuitarCif()
        If _gCif.CurrentRow Is Nothing Then Return
        Dim id As Integer = ToInt(CType(_gCif.CurrentRow.DataBoundItem, DataRowView)("Id"))
        Ejecutar(Sub() Svc.Produccion.QuitarCif(id))
    End Sub

    Private Sub CerrarOrden()
        Dim o As DataRow = Svc.Produccion.Obtener(_id)
        Dim campos As New List(Of CampoUI) From {CampoUI.Fec("Fecha", "Fecha de cierre"), CampoUI.Cant("Cantidad", "Cantidad terminada", 2)}
        Using d As New FichaDialog("Cerrar orden de producción", campos, New Dictionary(Of String, Object) From {{"Fecha", Date.Today}, {"Cantidad", o.GetD("Cantidad")}},
            Sub(v)
                Svc.Produccion.Cerrar(_id, ToDate(v("Fecha")), ToDec(v("Cantidad")))
            End Sub, "El producto terminado ingresa al almacén con el costo total / cantidad, y se genera el comprobante de capitalización.", 640)
            d.ShowDialog(Me)
        End Using
        Cargar()
    End Sub
End Class

''' <summary>Presupuesto mensual por cuenta y control de su ejecución.</summary>
Public Class PresupuestoForm
    Inherits FormBase

    Private ReadOnly _cuentas As New DataGridView()
    Private ReadOnly _meses As New DataGridView()
    Private ReadOnly _lbl As New Label()
    Private _cuentaId As Integer
    Private _cargando As Boolean

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Presupuesto"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Presupuesto"
        Dim banner As Panel = Tema.Banner("Asignación presupuestaria", "Presupueste las cuentas marcadas como 'presupuestables' en el plan de cuentas. Con el control activado en Parámetros no se podrá exceder el monto.")
        Dim barra As New FlowLayoutPanel() With {.Dock = DockStyle.Top, .Height = 46, .Padding = New Padding(12, 7, 12, 4), .WrapContents = False}
        Dim bGuardar As Button = Tema.Boton("Guardar presupuesto", Tema.TipoBoton.Primario, 150)
        Dim bDist As Button = Tema.Boton("Distribuir monto anual", Tema.TipoBoton.Secundario, 160)
        Dim bAsig As Button = Tema.Boton("Reporte asignado", Tema.TipoBoton.Secundario, 130)
        Dim bEjec As Button = Tema.Boton("Ejecución", Tema.TipoBoton.Secundario, 100)
        barra.Controls.AddRange({bGuardar, bDist, bAsig, bEjec})
        Dim split As New SplitContainer() With {.Dock = DockStyle.Fill, .Orientation = Orientation.Horizontal, .SplitterDistance = 300}
        Tema.EstiloGrid(_cuentas)
        Tema.ColTexto(_cuentas, "Codigo", "Código", 150)
        Tema.ColTexto(_cuentas, "Nombre", "Cuenta presupuestable", 360, True)
        Tema.ColImporte(_cuentas, "Total", "Presupuesto anual", 130)
        Tema.EstiloGrid(_meses, True)
        _meses.SelectionMode = DataGridViewSelectionMode.CellSelect
        _meses.EditMode = DataGridViewEditMode.EditOnEnter
        _meses.ColumnHeadersHeight = 32
        For i As Integer = 0 To 11
            Dim m As Date = Ctx.Gestion.FechaInicio.AddMonths(i)
            Dim c As DataGridViewTextBoxColumn = Tema.ColImporte(_meses, "m" & (i + 1), NombreMes(m.Month).Substring(0, 3) & " " & m.Year.ToString().Substring(2), 80)
            c.AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill
        Next
        _meses.Rows.Add()
        _meses.AllowUserToAddRows = False
        _lbl.Dock = DockStyle.Top
        _lbl.Height = 28
        _lbl.Padding = New Padding(8, 6, 0, 0)
        _lbl.Font = Tema.FuenteNegrita
        split.Panel1.Controls.Add(_cuentas)
        split.Panel2.Controls.Add(_meses)
        split.Panel2.Controls.Add(_lbl)
        Controls.Add(split)
        Controls.Add(barra)
        Controls.Add(banner)
        AddHandler _cuentas.SelectionChanged, Sub(o, ev) AlSeleccionar()
        AddHandler _meses.CellParsing, Sub(o, ev)
                                           Dim d As Decimal
                                           If Numeros.Parse(ToStr(ev.Value), d) Then ev.Value = d Else ev.Value = 0D
                                           ev.ParsingApplied = True
                                       End Sub
        AddHandler _meses.DataError, Sub(o, ev) ev.ThrowException = False
        AddHandler bGuardar.Click, Sub(o, ev) Guardar()
        AddHandler bDist.Click, Sub(o, ev) Distribuir()
        AddHandler bAsig.Click, Sub(o, ev) Informes.Abrir("presupuesto")
        AddHandler bEjec.Click, Sub(o, ev) Informes.Abrir("ejecucion_presupuesto")
        bGuardar.Enabled = Sesion.Puede("CONT.PRESUPUESTO")
        bDist.Enabled = bGuardar.Enabled
        CargarCuentas()
    End Sub

    Private Sub CargarCuentas()
        Dim dt As New DataTable()
        dt.Columns.Add("Id", GetType(Integer))
        dt.Columns.Add("Codigo", GetType(String))
        dt.Columns.Add("Nombre", GetType(String))
        dt.Columns.Add("Total", GetType(Decimal))
        For Each c As DataRow In Ctx.Cuentas().Rows
            If Not c.GetF("Presupuestable") OrElse Not c.GetF("EsMovimiento") Then Continue For
            dt.Rows.Add(c.GetI("Id"), c.GetS("Codigo"), c.GetS("Nombre"), Svc.Presupuesto.Obtener(c.GetI("Id")).Sum())
        Next
        _cuentas.DataSource = dt
        If dt.Rows.Count = 0 Then _lbl.Text = "No hay cuentas presupuestables. Marque la opción 'Presupuestable' en Contabilidad > Plan de cuentas."
        AlSeleccionar()
    End Sub

    Private Sub AlSeleccionar()
        If _cuentas.CurrentRow Is Nothing Then
            _cuentaId = 0
            Return
        End If
        Dim r As DataRowView = CType(_cuentas.CurrentRow.DataBoundItem, DataRowView)
        _cuentaId = ToInt(r("Id"))
        Dim m As Decimal() = Svc.Presupuesto.Obtener(_cuentaId)
        _cargando = True
        For i As Integer = 0 To 11
            _meses.Rows(0).Cells(i).Value = m(i)
        Next
        _cargando = False
        _lbl.Text = ToStr(r("Codigo")) & " - " & ToStr(r("Nombre")) & "   (ingrese el monto presupuestado por mes en Bs)"
    End Sub

    Private Function Leer() As Decimal()
        _meses.EndEdit()
        Dim m(11) As Decimal
        For i As Integer = 0 To 11
            m(i) = ToDec(_meses.Rows(0).Cells(i).Value)
        Next
        Return m
    End Function

    Private Sub Guardar()
        If _cuentaId = 0 Then Return
        If Intentar(Sub() Svc.Presupuesto.Guardar(_cuentaId, Leer())) Then
            Dim idx As Integer = _cuentas.CurrentRow.Index
            CargarCuentas()
            If idx < _cuentas.Rows.Count Then _cuentas.CurrentCell = _cuentas.Rows(idx).Cells(0)
        End If
    End Sub

    Private Sub Distribuir()
        If _cuentaId = 0 Then Return
        Dim s As String = Msg.Pedir("Monto anual a distribuir en partes iguales (Bs):", "Distribuir presupuesto")
        Dim d As Decimal
        If s Is Nothing OrElse Not Numeros.Parse(s, d) OrElse d <= 0D Then Return
        For i As Integer = 0 To 11
            _meses.Rows(0).Cells(i).Value = (d / 12D).R2()
        Next
    End Sub
End Class

''' <summary>Conciliación bancaria: marque los movimientos que ya figuran en el extracto del banco.</summary>
Public Class ConciliacionForm
    Inherits FormBase

    Private ReadOnly _cuenta As New LookupCombo() With {.Width = 380}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _extracto As New CampoImporte() With {.Width = 130}
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _lbl As New Label()
    Private _partidas As List(Of PartidaConciliacion)
    Private _cargando As Boolean

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Conciliación bancaria"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Conciliación bancaria"
        Dim banner As Panel = Tema.Banner("Bancos y conciliación bancaria", "Marque con ✔ los movimientos que ya aparecen en el extracto. Los no marcados son depósitos en tránsito y cheques no cobrados.")
        Dim barra As New FlowLayoutPanel() With {.Dock = DockStyle.Top, .Height = 48, .Padding = New Padding(12, 8, 12, 4), .WrapContents = False}
        Dim bancos As DataTable = Svc.Bancos.CuentasBanco()
        If bancos.Rows.Count = 0 Then
            Msg.Aviso("No hay cuentas marcadas como bancarias. En Plan de cuentas edite las cuentas de bancos y marque 'Cuenta bancaria'.")
        End If
        Dim t As New DataTable()
        t.Columns.Add("Id", GetType(Integer))
        t.Columns.Add("Texto", GetType(String))
        For Each r As DataRow In bancos.Rows
            t.Rows.Add(r.GetI("Id"), r.GetS("Codigo") & "  " & r.GetS("Nombre"))
        Next
        _cuenta.Cargar(t, "Id", "Texto", False)
        _hasta.MinDate = Ctx.Gestion.FechaInicio
        _hasta.MaxDate = Ctx.Gestion.FechaFin
        _hasta.Value = If(Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin, Date.Today, Ctx.Gestion.FechaFin)
        Dim bVer As Button = Tema.Boton("Cargar movimientos", Tema.TipoBoton.Primario, 150)
        Dim bImp As Button = Tema.Boton("Imprimir conciliación", Tema.TipoBoton.Secundario, 150)
        Dim bLib As Button = Tema.Boton("Libreta bancaria", Tema.TipoBoton.Secundario, 120)
        barra.Controls.Add(New Label() With {.Text = "Cuenta:", .AutoSize = True, .Margin = New Padding(0, 8, 6, 0)})
        barra.Controls.AddRange({_cuenta, New Label() With {.Text = "Hasta:", .AutoSize = True, .Margin = New Padding(10, 8, 6, 0)}, _hasta, bVer, bImp, bLib})
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 76, .BackColor = Color.White, .Padding = New Padding(16, 8, 16, 6)}
        AddHandler pie.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, 0, pie.Width, 0)
        _lbl.AutoSize = True
        _lbl.Font = Tema.FuenteNegrita
        _lbl.Location = New Point(16, 8)
        Dim lE As New Label() With {.Text = "Saldo según extracto bancario:", .AutoSize = True, .Location = New Point(16, 44)}
        _extracto.Location = New Point(220, 40)
        pie.Controls.AddRange({_lbl, lE, _extracto})
        Tema.EstiloGrid(_grid, True)
        _grid.SelectionMode = DataGridViewSelectionMode.CellSelect
        Tema.ColFecha(_grid, "Fecha", "Fecha").ReadOnly = True
        Tema.ColTexto(_grid, "Comp", "Comprobante", 100).ReadOnly = True
        Tema.ColTexto(_grid, "Cheque", "Cheque", 90).ReadOnly = True
        Tema.ColTexto(_grid, "Glosa", "Detalle", 300, True).ReadOnly = True
        Tema.ColImporte(_grid, "Debe", "Depósitos", 110).ReadOnly = True
        Tema.ColImporte(_grid, "Haber", "Retiros / cheques", 120).ReadOnly = True
        Dim chk As DataGridViewCheckBoxColumn = Tema.ColCheck(_grid, "Conc", "Conciliado", 90)
        chk.DataPropertyName = ""
        Controls.Add(_grid)
        Controls.Add(pie)
        Controls.Add(barra)
        Controls.Add(banner)
        AddHandler bVer.Click, Sub(o, ev) Cargar()
        AddHandler _cuenta.SelectionChangeCommitted, Sub(o, ev) Cargar()
        AddHandler _hasta.ValueChanged, Sub(o, ev) Cargar()
        AddHandler _extracto.ValorCambiado, Sub(o, ev) Resumen()
        AddHandler bImp.Click, Sub(o, ev) Informes.Abrir("conciliacion", New Dictionary(Of String, Object) From {{"cuenta", _cuenta.ValorId}, {"hasta", _hasta.Value.Date}, {"extracto", _extracto.Valor}}, False)
        AddHandler bLib.Click, Sub(o, ev) Informes.Abrir("libreta_banco", New Dictionary(Of String, Object) From {{"cuenta", _cuenta.ValorId}, {"hasta", _hasta.Value.Date}})
        AddHandler _grid.CurrentCellDirtyStateChanged, Sub(o, ev)
                                                           If _grid.IsCurrentCellDirty Then _grid.CommitEdit(DataGridViewDataErrorContexts.Commit)
                                                       End Sub
        AddHandler _grid.CellValueChanged, AddressOf CambioMarca
        If t.Rows.Count > 0 Then Cargar()
    End Sub

    Private Sub Cargar()
        If _cuenta.ValorId = 0 Then Return
        _cargando = True
        _grid.Rows.Clear()
        _partidas = Svc.Bancos.Partidas(_cuenta.ValorId, Ctx.Gestion.FechaInicio, _hasta.Value.Date)
        For Each p In _partidas
            Dim i As Integer = _grid.Rows.Add()
            Dim r As DataGridViewRow = _grid.Rows(i)
            r.Tag = p.DetId
            r.Cells("Fecha").Value = p.Fecha
            r.Cells("Comp").Value = p.Comprobante
            r.Cells("Cheque").Value = p.Cheque
            r.Cells("Glosa").Value = p.Glosa
            r.Cells("Debe").Value = p.Debe
            r.Cells("Haber").Value = p.Haber
            r.Cells("Conc").Value = p.Conciliado
        Next
        _cargando = False
        Resumen()
    End Sub

    Private Sub CambioMarca(o As Object, e As DataGridViewCellEventArgs)
        If _cargando OrElse e.RowIndex < 0 OrElse e.ColumnIndex <> _grid.Columns("Conc").Index Then Return
        Dim r As DataGridViewRow = _grid.Rows(e.RowIndex)
        Dim marcado As Boolean = ToFlag(r.Cells("Conc").Value)
        If Intentar(Sub() Svc.Bancos.Marcar({CInt(r.Tag)}, marcado, _hasta.Value.Date)) Then
            Dim p As PartidaConciliacion = _partidas.First(Function(x) x.DetId = CInt(r.Tag))
            p.Conciliado = marcado
            Resumen()
        End If
    End Sub

    Private Sub Resumen()
        If _cuenta.ValorId = 0 Then Return
        Try
            Dim r = Svc.Bancos.Resumen(_cuenta.ValorId, _hasta.Value.Date)
            _lbl.Text = "Saldo en libros: " & r.Item1.ToString("N2", FormatoVal.Cultura) & "   ·   Depósitos en tránsito: " & r.Item2.ToString("N2", FormatoVal.Cultura) & "   ·   Cheques no cobrados: " & r.Item3.ToString("N2", FormatoVal.Cultura) & "   ·   Saldo bancario esperado: " & r.Item4.ToString("N2", FormatoVal.Cultura) &
                If(_extracto.Valor <> 0D, "   ·   Diferencia con extracto: " & (_extracto.Valor - r.Item4).ToString("N2", FormatoVal.Cultura), "")
        Catch
        End Try
    End Sub
End Class
