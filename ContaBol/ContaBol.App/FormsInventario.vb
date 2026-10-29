Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Services

Public Class ColCat
    Public Property Campo As String
    Public Property Titulo As String
    Public Property Ancho As Integer
    Public Property Tipo As String
    Public Sub New(campo As String, titulo As String, Optional ancho As Integer = 100, Optional tipo As String = "T")
        Me.Campo = campo
        Me.Titulo = titulo
        Me.Ancho = ancho
        Me.Tipo = tipo
    End Sub
End Class

''' <summary>Definición de un catálogo sencillo (almacenes, unidades, grupos, sucursales, vendedores, centros de costo...).</summary>
Public Class CatalogoDef
    Public Property Tabla As String
    Public Property Titulo As String
    Public Property Subtitulo As String = ""
    Public Property Permiso As String
    Public Property Orden As String = "Id"
    Public ReadOnly Property Campos As New List(Of CampoUI)
    Public ReadOnly Property Columnas As New List(Of ColCat)

    Private Shared Function Base(tabla As String, titulo As String, permiso As String, orden As String, Optional sub1 As String = "") As CatalogoDef
        Return New CatalogoDef With {.Tabla = tabla, .Titulo = titulo, .Permiso = permiso, .Orden = orden, .Subtitulo = sub1}
    End Function

    Public Shared Function Almacenes() As CatalogoDef
        Dim d As CatalogoDef = Base("Almacen", "Almacenes", "INV.ITEMS", "Codigo", "Depósitos donde se almacena la mercadería. Cada ítem tiene existencias por almacén.")
        d.Campos.AddRange({CampoUI.Txt("Codigo", "Código", 10, True), CampoUI.Txt("Nombre", "Nombre", 60, True), CampoUI.Txt("Direccion", "Dirección", 120, False, True), CampoUI.Chk("Activo", "Activo", True)})
        d.Columnas.AddRange({New ColCat("Codigo", "Código", 90), New ColCat("Nombre", "Nombre", 250), New ColCat("Direccion", "Dirección", 300), New ColCat("Activo", "Activo", 60, "B")})
        Return d
    End Function

    Public Shared Function Unidades() As CatalogoDef
        Dim d As CatalogoDef = Base("UnidadMedida", "Unidades de medida", "INV.ITEMS", "Codigo", "Kilos, litros, cajas, docenas...")
        d.Campos.AddRange({CampoUI.Txt("Codigo", "Código", 10, True), CampoUI.Txt("Nombre", "Descripción", 40, True)})
        d.Columnas.AddRange({New ColCat("Codigo", "Código", 100), New ColCat("Nombre", "Descripción", 300)})
        Return d
    End Function

    Public Shared Function GruposItem() As CatalogoDef
        Dim d As CatalogoDef = Base("GrupoItem", "Grupos de ítems", "INV.ITEMS", "Codigo", "Agrupan los ítems para organizar el inventario.")
        d.Campos.AddRange({CampoUI.Txt("Codigo", "Código", 10, True), CampoUI.Txt("Nombre", "Nombre", 60, True)})
        d.Columnas.AddRange({New ColCat("Codigo", "Código", 100), New ColCat("Nombre", "Nombre", 300)})
        Return d
    End Function

    Public Shared Function Sucursales() As CatalogoDef
        Dim d As CatalogoDef = Base("Sucursal", "Sucursales", "COM.TERCEROS", "Codigo", "Casa matriz y sucursales habilitadas en el SIN.")
        d.Campos.AddRange({CampoUI.Txt("Codigo", "Código SIN", 10, True), CampoUI.Txt("Nombre", "Nombre", 80, True), CampoUI.Txt("Direccion", "Dirección", 150, False, True), CampoUI.Chk("Activa", "Activa", True)})
        d.Columnas.AddRange({New ColCat("Codigo", "Código", 80), New ColCat("Nombre", "Nombre", 220), New ColCat("Direccion", "Dirección", 300), New ColCat("Activa", "Activa", 60, "B")})
        Return d
    End Function

    Public Shared Function Vendedores() As CatalogoDef
        Dim d As CatalogoDef = Base("Vendedor", "Vendedores", "COM.TERCEROS", "Nombre", "Se usan para calcular comisiones por ventas.")
        d.Campos.AddRange({CampoUI.Txt("Nombre", "Nombre completo", 80, True, True), CampoUI.Txt("Ci", "C.I.", 20), CampoUI.Txt("Telefono", "Teléfono", 40), CampoUI.Cant("ComisionPct", "Comisión (%)", 2), CampoUI.Chk("Activo", "Activo", True)})
        d.Columnas.AddRange({New ColCat("Nombre", "Nombre", 260), New ColCat("Ci", "C.I.", 100), New ColCat("Telefono", "Teléfono", 110), New ColCat("ComisionPct", "Comisión %", 90, "N"), New ColCat("Activo", "Activo", 60, "B")})
        Return d
    End Function

    Public Shared Function CentrosCosto() As CatalogoDef
        Dim d As CatalogoDef = Base("CentroCosto", "Centros de costo (departamentos y proyectos)", "CONT.CENTROS", "Codigo", "Permiten distribuir gastos por departamento o proyecto al contabilizar.")
        d.Campos.AddRange({CampoUI.Txt("Codigo", "Código", 15, True), CampoUI.Txt("Nombre", "Nombre", 80, True), CampoUI.Lst("Tipo", "Tipo", "D|Departamento", "P|Proyecto"), CampoUI.Chk("Activo", "Activo", True)})
        d.Columnas.AddRange({New ColCat("Codigo", "Código", 100), New ColCat("Nombre", "Nombre", 300), New ColCat("Tipo", "Tipo", 60), New ColCat("Activo", "Activo", 60, "B")})
        Return d
    End Function

    Public Shared Function GruposActivo() As CatalogoDef
        Dim d As CatalogoDef = Base("GrupoActivo", "Grupos de activos fijos", "AF.ACTIVOS", "Nombre", "Vida útil y porcentaje de depreciación (D.S. 24051). Las cuentas se asignan automáticamente al registrar activos.")
        d.Campos.AddRange({CampoUI.Txt("Nombre", "Nombre del grupo", 60, True, True), CampoUI.Ent("VidaUtilAnios", "Vida útil (años)", True), CampoUI.Cant("PorcDep", "Depreciación anual (%)", 2),
                           CampoUI.Cta("CuentaActivoId", "Cuenta del activo"), CampoUI.Cta("CuentaDepAcumId", "Cuenta depreciación acumulada"), CampoUI.Cta("CuentaGastoId", "Cuenta gasto de depreciación")})
        d.Columnas.AddRange({New ColCat("Nombre", "Grupo", 260), New ColCat("VidaUtilAnios", "Vida útil", 80, "N0"), New ColCat("PorcDep", "% Depreciación", 110, "N")})
        Return d
    End Function
End Class

''' <summary>Mantenimiento genérico de un catálogo (alta, edición, baja, exportación a PDF/Excel).</summary>
Public Class CatalogoForm
    Inherits ListaForm

    Private ReadOnly _def As CatalogoDef

    Public Sub New(def As CatalogoDef)
        _def = def
    End Sub

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return _def.Titulo
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return _def.Subtitulo
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return _def.Permiso
        End Get
    End Property

    Protected Overrides Function CargarDatos() As DataTable
        Return Ctx.Db.Query("SELECT * FROM " & _def.Tabla & " ORDER BY " & _def.Orden)
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        For i As Integer = 0 To _def.Columnas.Count - 1
            Dim c As ColCat = _def.Columnas(i)
            Select Case c.Tipo
                Case "B" : Tema.ColCheck(Grid, c.Campo, c.Titulo, c.Ancho)
                Case "N" : Tema.ColImporte(Grid, c.Campo, c.Titulo, c.Ancho)
                Case "N0" : Tema.ColImporte(Grid, c.Campo, c.Titulo, c.Ancho, "N0")
                Case Else : Tema.ColTexto(Grid, c.Campo, c.Titulo, c.Ancho, i = _def.Columnas.Count - 1 AndAlso c.Tipo = "T")
            End Select
        Next
    End Sub

    Private Function Valores(fila As DataRow) As Dictionary(Of String, Object)
        If fila Is Nothing Then Return Nothing
        Dim d As New Dictionary(Of String, Object)(StringComparer.OrdinalIgnoreCase)
        For Each c As DataColumn In fila.Table.Columns
            d(c.ColumnName) = If(IsNil(fila(c)), Nothing, fila(c))
        Next
        Return d
    End Function

    Private Sub Mostrar(fila As DataRow)
        Dim id As Integer = If(fila Is Nothing, 0, fila.GetI("Id"))
        Using d As New FichaDialog(If(id = 0, "Nuevo registro - ", "Modificar - ") & _def.Titulo, _def.Campos, Valores(fila), Sub(v) Guardar(id, v), "", 640)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Nuevo()
        Mostrar(Nothing)
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Mostrar(fila)
    End Sub

    Private Sub Guardar(id As Integer, v As Dictionary(Of String, Object))
        Ctx.RequiereGestionAbierta()
        Dim cols As New List(Of String)
        Dim args As New List(Of Object)
        For Each c As CampoUI In _def.Campos
            If c.Tipo = TipoCampo.Seccion Then Continue For
            cols.Add(c.Clave)
            args.Add("p_" & c.Clave)
            Dim x As Object = v(c.Clave)
            Select Case c.Tipo
                Case TipoCampo.Texto, TipoCampo.Memo, TipoCampo.Lista : args.Add(ToStr(x))
                Case TipoCampo.Entero : args.Add(ToInt(x))
                Case TipoCampo.Importe : args.Add(ToDec(x))
                Case TipoCampo.Cantidad : args.Add(ToDbl(x))
                Case TipoCampo.Bool : args.Add(If(ToFlag(x), 1, 0))
                Case TipoCampo.Cuenta, TipoCampo.Lookup : args.Add(OrNull(ToInt(x)))
                Case TipoCampo.Fecha, TipoCampo.FechaOpcional : args.Add(If(x Is Nothing, CObj(DBNull.Value), x))
                Case Else : args.Add(ToStr(x))
            End Select
        Next
        Try
            If id = 0 Then
                Ctx.Db.Execute("INSERT INTO " & _def.Tabla & " (" & String.Join(", ", cols.Select(Function(c) Ctx.Db.Provider.Quote(c))) & ") VALUES (" & String.Join(", ", cols.Select(Function(c) "@p_" & c)) & ")", args.ToArray())
            Else
                args.AddRange({"p_Id", id})
                Ctx.Db.Execute("UPDATE " & _def.Tabla & " SET " & String.Join(", ", cols.Select(Function(c) Ctx.Db.Provider.Quote(c) & "=@p_" & c)) & " WHERE Id=@p_Id", args.ToArray())
            End If
            Ctx.Audit("Catálogos", If(id = 0, "ALTA", "MODIFICACION"), _def.Titulo)
        Catch ex As Exception When EsDuplicado(ex)
            Throw New InvalidOperationException("Ya existe un registro con el mismo código. Use un código distinto.")
        End Try
        Ctx.InvalidarCuentas()
    End Sub

    Private Shared Function EsDuplicado(ex As Exception) As Boolean
        Dim m As String = ex.Message.ToLowerInvariant()
        Return m.Contains("duplicate") OrElse m.Contains("unique") OrElse m.Contains("duplicad") OrElse m.Contains("índice") OrElse m.Contains("indice")
    End Function

    Protected Overrides Sub Eliminar(fila As DataRow)
        Try
            Ctx.Db.Execute("DELETE FROM " & _def.Tabla & " WHERE Id=@i", "i", fila.GetI("Id"))
            Ctx.Audit("Catálogos", "BAJA", _def.Titulo)
        Catch ex As Exception
            Throw New InvalidOperationException("El registro está siendo utilizado y no puede eliminarse. Puede desactivarlo en su lugar.")
        End Try
    End Sub
End Class

''' <summary>Ítems de inventario: mercaderías y servicios, con cuentas contables y siete niveles de precio.</summary>
Public Class ItemsForm
    Inherits ListaForm

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Ítems de inventario"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Mercaderías, materias primas, productos terminados y servicios. El costo se calcula por promedio ponderado."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "INV.ITEMS"
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim bK As Button = Tema.Boton("Kardex", Tema.TipoBoton.Secundario, 76)
        Dim bP As Button = Tema.Boton("Precios desde costo", Tema.TipoBoton.Secundario, 150)
        Dim bS As Button = Tema.Boton("Stock inicial…", Tema.TipoBoton.Secundario, 112)
        Barra.Controls.AddRange({bK, bP, bS})
        AddHandler bK.Click, Sub(o, e)
                                 Dim f As DataRow = FilaActual()
                                 If f IsNot Nothing Then Informes.Abrir("kardex_item", New Dictionary(Of String, Object) From {{"item", f.GetI("Id")}})
                             End Sub
        AddHandler bP.Click, Sub(o, e)
                                 If Msg.Confirmar("Se calculará el Precio A de todos los ítems = costo promedio × (1 + utilidad %)." & vbCrLf & "¿Continuar?", "Actualizar precios") Then
                                     Dim n As Integer = 0
                                     If Intentar(Sub() n = Svc.Inventario.ActualizarPreciosDesdeCosto()) Then
                                         Msg.Info(n & " ítem(s) actualizados.")
                                         Refrescar()
                                     End If
                                 End If
                             End Sub
        AddHandler bS.Click, Sub(o, e) Escritorio.AbrirNueva(New MovimientoInvForm("STIN"), Nothing)
        bP.Enabled = Sesion.Puede("INV.ITEMS")
        bS.Enabled = Sesion.Puede("INV.MOVIMIENTOS")
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = Svc.Inventario.ListarItems()
        dt.Columns.Add("Un", GetType(String))
        dt.Columns.Add("TipoTxt", GetType(String))
        Dim u As New Dictionary(Of Integer, String)
        For Each r As DataRow In Ctx.Db.Query("SELECT Id, Codigo FROM UnidadMedida").Rows
            u(r.GetI("Id")) = r.GetS("Codigo")
        Next
        For Each r As DataRow In dt.Rows
            r("Un") = If(u.ContainsKey(r.GetI("UnidadId")), u(r.GetI("UnidadId")), "")
            r("TipoTxt") = If(r.GetF("EsServicio"), "Servicio", "Mercadería")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Codigo", "Código", 120)
        Tema.ColTexto(Grid, "Descripcion", "Descripción", 320, True)
        Tema.ColTexto(Grid, "Un", "Un.", 50)
        Tema.ColTexto(Grid, "TipoTxt", "Tipo", 90)
        Tema.ColImporte(Grid, "Stock", "Stock", 90, "N2")
        Tema.ColImporte(Grid, "CostoProm", "Costo prom. Bs", 110, "N4")
        Tema.ColImporte(Grid, "PrecioA", "Precio A", 90)
        Tema.ColCheck(Grid, "Activo", "Activo", 60)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If Not fila.GetF("EsServicio") AndAlso fila.GetD("StockMin") > 0D AndAlso fila.GetD("Stock") < fila.GetD("StockMin") Then estilo.ForeColor = Tema.Rojo
        If Not fila.GetF("Activo") Then estilo.ForeColor = Tema.Gris
    End Sub

    Private Function Campos() As List(Of CampoUI)
        Dim l As New List(Of CampoUI)
        l.Add(CampoUI.Sec("Datos generales"))
        l.Add(CampoUI.Txt("Codigo", "Código", 25, True))
        l.Add(CampoUI.Txt("CodBarra", "Código de barras", 40))
        l.Add(CampoUI.Txt("Descripcion", "Descripción", 150, True, True))
        l.Add(CampoUI.Txt("Abrev", "Descripción abreviada", 30))
        l.Add(CampoUI.Txt("Marca", "Marca", 40))
        l.Add(CampoUI.Lk("GrupoId", "Grupo", Function() Ctx.Db.Query("SELECT Id, Nombre FROM GrupoItem ORDER BY Nombre")))
        l.Add(CampoUI.Lk("UnidadId", "Unidad de medida", Function() Ctx.Db.Query("SELECT Id, Nombre FROM UnidadMedida ORDER BY Nombre")))
        l.Add(CampoUI.Chk("EsServicio", "Es un servicio (no controla stock)"))
        l.Add(CampoUI.Chk("ManejaVenc", "Controla fecha de vencimiento"))
        l.Add(CampoUI.Cant("StockMin", "Stock mínimo", 2))
        l.Add(CampoUI.Cant("UtilidadPct", "Utilidad sobre costo (%)", 2))
        l.Add(CampoUI.Lst("Moneda", "Moneda de precios", "BS|Bolivianos", "USD|Dólares"))
        l.Add(CampoUI.Chk("Activo", "Ítem activo", True))
        l.Add(CampoUI.Sec("Cuentas contables (si se dejan vacías se usan las del parámetro)"))
        l.Add(CampoUI.Cta("CuentaInvId", "Cuenta de inventario (activo)"))
        l.Add(CampoUI.Cta("CuentaIngId", "Cuenta de ingreso por ventas"))
        l.Add(CampoUI.Cta("CuentaCostoId", "Cuenta de costo de ventas"))
        l.Add(CampoUI.Sec("Precios de venta (siete niveles)"))
        For Each n As String In {"A", "B", "C", "D", "E", "F", "G"}
            l.Add(CampoUI.Imp("Precio" & n, "Precio " & n, False, 4))
        Next
        l.Add(CampoUI.Memo("Observacion", "Observaciones", 255))
        Return l
    End Function

    Private Sub Mostrar(id As Integer)
        Dim it As ItemDto = If(id = 0, New ItemDto(), Svc.Inventario.ObtenerItem(id))
        Using d As New FichaDialog(If(id = 0, "Nuevo ítem", "Modificar ítem"), Campos(), DtoMapper.ADiccionario(it),
            Sub(v)
                DtoMapper.Aplicar(it, v)
                Svc.Inventario.GuardarItem(it)
            End Sub, "El código acepta hasta 25 caracteres; también puede buscarse por código de barras.", 820)
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
        Svc.Inventario.EliminarItem(fila.GetI("Id"))
    End Sub
End Class

''' <summary>Ajustes de entrada y salida, stock inicial y traspasos entre almacenes (con asiento contable opcional).</summary>
Public Class MovimientoInvForm
    Inherits FormBase

    Private ReadOnly _tipoInicial As String
    Private ReadOnly _tipo As New LookupCombo() With {.Width = 220}
    Private ReadOnly _fecha As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _almacen As New LookupCombo() With {.Width = 220}
    Private ReadOnly _destino As New LookupCombo() With {.Width = 220}
    Private ReadOnly _lblDestino As New Label() With {.Text = "Almacén destino", .AutoSize = True}
    Private ReadOnly _moneda As New LookupCombo() With {.Width = 130}
    Private ReadOnly _tc As New CampoImporte() With {.Width = 70}
    Private ReadOnly _detalle As New TextBox() With {.MaxLength = 200, .Width = 520}
    Private ReadOnly _grid As New GridItems()
    Private ReadOnly _chkAsiento As New CheckBox() With {.Text = "Generar asiento contable", .AutoSize = True, .Checked = True}
    Private ReadOnly _contra As New PickerCuenta() With {.Width = 360}
    Private ReadOnly _lblContra As New Label() With {.Text = "Contracuenta", .AutoSize = True}
    Private ReadOnly _lblTotal As New Label()

    Public Sub New(Optional tipoInicial As String = "AJEN")
        _tipoInicial = tipoInicial
        Text = "Movimiento de inventario"
    End Sub

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Movimiento de inventario"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Dim banner As Panel = Tema.Banner("Movimientos de inventario", "Ajustes de entrada y salida, stock inicial y traspasos. Cada movimiento tiene su correlativo propio.")
        Dim cab As New Panel() With {.Dock = DockStyle.Top, .Height = 136, .BackColor = Color.White, .Padding = New Padding(16, 8, 16, 4)}
        AddHandler cab.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, cab.Height - 1, cab.Width, cab.Height - 1)
        _tipo.CargarLista({New KeyValuePair(Of String, String)("AJEN", "Ajuste de entrada"), New KeyValuePair(Of String, String)("AJSA", "Ajuste de salida (mermas, uso interno)"), New KeyValuePair(Of String, String)("STIN", "Stock inicial"), New KeyValuePair(Of String, String)("TRAS", "Traspaso entre almacenes")})
        _tipo.ValorTexto = _tipoInicial
        _moneda.CargarLista({New KeyValuePair(Of String, String)("BS", "Bolivianos"), New KeyValuePair(Of String, String)("USD", "Dólares")})
        Dim alm As DataTable = Ctx.Db.Query("SELECT Id, Nombre FROM Almacen WHERE Activo=1 ORDER BY Codigo")
        _almacen.Cargar(alm, "Id", "Nombre", False)
        _destino.Cargar(alm, "Id", "Nombre", False)
        _fecha.MinDate = Ctx.Gestion.FechaInicio
        _fecha.MaxDate = Ctx.Gestion.FechaFin
        If Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin Then _fecha.Value = Date.Today
        _tc.Valor = Svc.TipoCambio.Dolar(_fecha.Value)
        Dim lbls As New List(Of Label)
        Dim poner = Sub(titulo As String, c As Control, x As Integer, y As Integer)
                        Dim l As New Label() With {.Text = titulo, .AutoSize = True, .Location = New Point(x, y + 4)}
                        cab.Controls.Add(l)
                        c.Location = New Point(x + l.PreferredWidth + 6, y)
                        cab.Controls.Add(c)
                    End Sub
        poner("Tipo de movimiento", _tipo, 0, 8)
        poner("Fecha", _fecha, 400, 8)
        poner("T.C.", _tc, 560, 8)
        poner("Moneda", _moneda, 650, 8)
        poner("Almacén", _almacen, 0, 42)
        _lblDestino.Location = New Point(400, 46)
        _destino.Location = New Point(500, 42)
        cab.Controls.AddRange({_lblDestino, _destino})
        poner("Detalle", _detalle, 0, 76)
        _chkAsiento.Location = New Point(0, 108)
        _lblContra.Location = New Point(200, 110)
        _contra.Location = New Point(290, 106)
        cab.Controls.AddRange({_chkAsiento, _lblContra, _contra})
        _grid.MostrarStock = True
        _grid.PedirVencimiento = True
        _grid.SoloInventariables = True
        _grid.TextoPrecio = "Costo unit."
        _grid.AlmacenStock = Function() _almacen.ValorId
        _grid.Iniciar()
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 56, .BackColor = Color.White, .Padding = New Padding(16, 10, 16, 8)}
        AddHandler pie.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, 0, pie.Width, 0)
        Dim bGuardar As Button = Tema.Boton("Guardar (F10)", Tema.TipoBoton.Primario, 120)
        bGuardar.Dock = DockStyle.Right
        Dim bLista As Button = Tema.Boton("Ver movimientos", Tema.TipoBoton.Secundario, 130)
        bLista.Dock = DockStyle.Right
        _lblTotal.Dock = DockStyle.Left
        _lblTotal.AutoSize = False
        _lblTotal.Width = 420
        _lblTotal.TextAlign = ContentAlignment.MiddleLeft
        _lblTotal.Font = Tema.FuenteGrande
        pie.Controls.Add(bGuardar)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(bLista)
        pie.Controls.Add(_lblTotal)
        Controls.Add(_grid)
        Controls.Add(pie)
        Controls.Add(cab)
        Controls.Add(banner)
        AddHandler _tipo.SelectionChangeCommitted, Sub(o, ev) AjustarTipo()
        AddHandler _almacen.SelectionChangeCommitted, Sub(o, ev) _grid.RefrescarStock()
        AddHandler _fecha.ValueChanged, Sub(o, ev) _tc.Valor = Svc.TipoCambio.Dolar(_fecha.Value)
        AddHandler _grid.LineasCambiaron, Sub(o, ev) _lblTotal.Text = "Total: Bs " & (_grid.Subtotal() * If(_moneda.ValorTexto = "USD", _tc.Valor, 1D)).ToString("N2", FormatoVal.Cultura)
        AddHandler _moneda.SelectionChangeCommitted, Sub(o, ev) _grid.RaiseLineas()
        AddHandler bGuardar.Click, Sub(o, ev) Guardar()
        AddHandler bLista.Click, Sub(o, ev) Escritorio.AbrirNueva(New MovimientosListaForm(), "MovimientosListaForm")
        AddHandler KeyDown, Sub(o, ev)
                                If ev.KeyCode = Keys.F10 Then
                                    ev.Handled = True
                                    Guardar()
                                End If
                            End Sub
        AjustarTipo()
    End Sub

    Private Sub AjustarTipo()
        Dim t As String = _tipo.ValorTexto
        Dim tras As Boolean = t = "TRAS"
        _lblDestino.Visible = tras
        _destino.Visible = tras
        _chkAsiento.Visible = Not tras
        _lblContra.Visible = Not tras
        _contra.Visible = Not tras
        _grid.Enabled = True
        If t = "AJSA" Then _contra.CuentaId = Ctx.CuentaParamOpcional(ParamKeys.CtaMermas)
        If t = "AJEN" OrElse t = "STIN" Then _contra.CuentaId = 0
        _lblContra.Text = If(t = "AJSA", "Cuenta de gasto", "Contracuenta")
        _chkAsiento.Checked = t <> "STIN" AndAlso t <> "TRAS"
    End Sub

    Private Sub Guardar()
        Dim m As New MovInvDto With {.Tipo = _tipo.ValorTexto, .Fecha = _fecha.Value.Date, .AlmacenId = _almacen.ValorId, .AlmacenDestId = If(_tipo.ValorTexto = "TRAS", _destino.ValorId, 0),
            .Moneda = _moneda.ValorTexto, .TC = _tc.Valor, .Detalle = _detalle.Text.Trim(), .GenerarAsiento = _chkAsiento.Checked AndAlso _tipo.ValorTexto <> "TRAS", .ContracuentaId = _contra.CuentaId}
        Try
            For Each l In _grid.Lineas()
                m.Lines.Add(New MovLine With {.ItemId = l.ItemId, .Cantidad = l.Cantidad, .PrecioUnit = l.Precio, .FechaVenc = l.FechaVenc})
            Next
            If m.Lines.Count = 0 Then Throw New InvalidOperationException("Agregue al menos un ítem.")
            Dim r As MovResult
            Using Msg.Cursor_(True)
                r = Svc.Inventario.Registrar(m)
            End Using
            Msg.Info("Movimiento Nº " & r.Numero & " registrado correctamente." & vbCrLf & "Valor total: Bs " & r.TotalBs.ToString("N2", FormatoVal.Cultura))
            _grid.Limpiar()
            _detalle.Text = ""
            _grid.RecargarItems()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class

''' <summary>Historial de movimientos de inventario con opción de anular.</summary>
Public Class MovimientosListaForm
    Inherits ListaForm

    Private ReadOnly _desde As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Movimientos de inventario"
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "INV.MOVIMIENTOS"
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
        Dim bAnular As Button = Tema.Boton("Anular", Tema.TipoBoton.Peligro, 80)
        Barra.Controls.Add(bAnular)
        AddHandler bAnular.Click, Sub(o, e) Anular()
        bAnular.Enabled = Sesion.Puede("INV.MOVIMIENTOS")
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = Svc.Inventario.ListarMovimientos(_desde.Value.Date, _hasta.Value.Date)
        dt.Columns.Add("Doc", GetType(String))
        dt.Columns.Add("TipoTxt", GetType(String))
        dt.Columns.Add("EstTxt", GetType(String))
        For Each r As DataRow In dt.Rows
            r("Doc") = r.GetS("Tipo") & "-" & r.GetS("Numero")
            r("TipoTxt") = InventarioService.NombreTipo(r.GetS("Tipo"))
            r("EstTxt") = If(r.GetS("Estado") = "A", "ANULADO", "Vigente")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Doc", "Documento", 100)
        Tema.ColFecha(Grid, "Fecha", "Fecha")
        Tema.ColTexto(Grid, "TipoTxt", "Tipo", 190)
        Tema.ColTexto(Grid, "Detalle", "Detalle", 300, True)
        Tema.ColImporte(Grid, "TotalBs", "Total Bs", 110)
        Tema.ColTexto(Grid, "EstTxt", "Estado", 80)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If fila.GetS("Estado") = "A" Then estilo.ForeColor = Tema.Rojo
    End Sub

    Protected Overrides Sub Nuevo()
        Escritorio.AbrirNueva(New MovimientoInvForm("AJEN"), Nothing)
    End Sub

    Private Sub Anular()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then Return
        If f.GetS("Estado") = "A" Then Return
        If f.GetS("Tipo") = "VENT" OrElse f.GetS("Tipo") = "COMP" Then
            Msg.Aviso("Este movimiento proviene de una venta o compra. Anule el documento desde Ventas o Compras.")
            Return
        End If
        Dim motivo As String = Msg.Pedir("Motivo de la anulación:", "Anular movimiento")
        If String.IsNullOrWhiteSpace(motivo) Then Return
        If Intentar(Sub() Svc.Inventario.Anular(f.GetI("Id"), motivo)) Then Refrescar()
    End Sub
End Class
