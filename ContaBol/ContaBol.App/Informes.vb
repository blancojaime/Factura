Imports System.Diagnostics
Imports System.IO
Imports ContaBol.Core.Common
Imports ContaBol.Core.Reports
Imports ContaBol.Core.Services

''' <summary>Punto único para ejecutar, previsualizar y exportar cualquier reporte (PDF y Excel).</summary>
Public Module Informes

    ''' <summary>Pide parámetros (si el reporte los tiene) y muestra el reporte.</summary>
    Public Sub Abrir(id As String, Optional valores As Dictionary(Of String, Object) = Nothing, Optional pedirParametros As Boolean = True)
        Dim cat As ReporteCat = Catalogo.Buscar(id)
        If cat Is Nothing Then
            Msg.ErrorMsg("El reporte '" & id & "' no existe.")
            Return
        End If
        If Sesion.Ctx Is Nothing Then
            Msg.Aviso("Primero abra una empresa y gestión.")
            Return
        End If
        If Not Sesion.Puede(cat.Permiso) Then
            Msg.Aviso("Su usuario no tiene permiso para el reporte: " & cat.Titulo)
            Return
        End If
        Dim vals As Dictionary(Of String, Object) = cat.ValoresPorDefecto(Sesion.Ctx)
        If valores IsNot Nothing Then
            For Each kv In valores
                vals(kv.Key) = kv.Value
            Next
        End If
        If pedirParametros AndAlso cat.Params.Count > 0 Then
            Using f As New ReportParamForm(cat, vals)
                If f.ShowDialog(Escritorio.Ventana()) <> DialogResult.OK Then Return
                vals = f.Valores
            End Using
        End If
        Try
            Dim rep As ReporteDef
            Using Msg.Cursor_(True)
                rep = cat.Ejecutar(Sesion.Ctx, vals)
            End Using
            Mostrar(rep)
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Public Sub Mostrar(rep As ReporteDef)
        Dim f As New ReportViewerForm(rep)
        Escritorio.AbrirPestana(f, rep.Titulo, Nothing)
    End Sub

    Private Function NombreSeguro(s As String) As String
        Dim r As String = s
        For Each c As Char In Path.GetInvalidFileNameChars()
            r = r.Replace(c, "_"c)
        Next
        Return r
    End Function

    Public Function RutaTemporal(rep As ReporteDef, ext As String) As String
        Dim d As String = Path.Combine(Path.GetTempPath(), "ContaBol")
        Directory.CreateDirectory(d)
        Return Path.Combine(d, NombreSeguro(rep.NombreArchivo) & "_" & Date.Now.ToString("yyyyMMdd_HHmmss") & ext)
    End Function

    Public Sub Abrir_(ruta As String)
        Try
            Process.Start(New ProcessStartInfo(ruta) With {.UseShellExecute = True})
        Catch ex As Exception
            Msg.Aviso("No se pudo abrir el archivo automáticamente. Se guardó en:" & vbCrLf & ruta)
        End Try
    End Sub

    Public Sub VerPdf(rep As ReporteDef)
        Dim ruta As String = RutaTemporal(rep, ".pdf")
        PdfExporter.Exportar(rep, ruta)
        Abrir_(ruta)
    End Sub

    Public Sub Imprimir(rep As ReporteDef)
        Dim ruta As String = RutaTemporal(rep, ".pdf")
        PdfExporter.Exportar(rep, ruta)
        Try
            Process.Start(New ProcessStartInfo(ruta) With {.UseShellExecute = True, .Verb = "print", .CreateNoWindow = True, .WindowStyle = ProcessWindowStyle.Hidden})
        Catch
            Abrir_(ruta)
        End Try
    End Sub

    Public Sub GuardarPdf(rep As ReporteDef)
        Using d As New SaveFileDialog()
            d.Title = "Guardar PDF"
            d.Filter = "Documento PDF (*.pdf)|*.pdf"
            d.FileName = NombreSeguro(rep.NombreArchivo) & "_" & Date.Today.ToString("yyyyMMdd") & ".pdf"
            d.InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
            If d.ShowDialog() <> DialogResult.OK Then Return
            Using Msg.Cursor_(True)
                PdfExporter.Exportar(rep, d.FileName)
            End Using
            If Msg.Confirmar("PDF guardado en:" & vbCrLf & d.FileName & vbCrLf & vbCrLf & "¿Desea abrirlo ahora?") Then Abrir_(d.FileName)
        End Using
    End Sub

    Public Sub GuardarExcel(rep As ReporteDef)
        Using d As New SaveFileDialog()
            d.Title = "Guardar Excel"
            d.Filter = "Libro de Excel (*.xlsx)|*.xlsx"
            d.FileName = NombreSeguro(rep.NombreArchivo) & "_" & Date.Today.ToString("yyyyMMdd") & ".xlsx"
            d.InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
            If d.ShowDialog() <> DialogResult.OK Then Return
            Using Msg.Cursor_(True)
                ExcelExporter.Exportar(rep, d.FileName)
            End Using
            If Msg.Confirmar("Excel guardado en:" & vbCrLf & d.FileName & vbCrLf & vbCrLf & "¿Desea abrirlo ahora?") Then Abrir_(d.FileName)
        End Using
    End Sub

End Module

''' <summary>Vista previa en pantalla del reporte con acceso directo a PDF, Excel e impresión.</summary>
Public Class ReportViewerForm
    Inherits FormBase

    Private ReadOnly _rep As ReporteDef
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _textos As New List(Of String())

    Public Sub New(rep As ReporteDef)
        _rep = rep
        Text = rep.Titulo
    End Sub

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return _rep.Titulo
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Dim banner As Panel = Tema.Banner(_rep.Titulo, String.Join("  ·  ", {_rep.Subtitulo, _rep.Periodo, _rep.Moneda}.Where(Function(s) s <> "")))
        Dim barra As New FlowLayoutPanel() With {.Dock = DockStyle.Top, .Height = 46, .Padding = New Padding(12, 7, 12, 4), .WrapContents = False}
        Dim bPdf As Button = Tema.Boton("Ver PDF", Tema.TipoBoton.Primario, 90)
        Dim bGuardarPdf As Button = Tema.Boton("Guardar PDF", Tema.TipoBoton.Secundario, 104)
        Dim bExcel As Button = Tema.Boton("Excel", Tema.TipoBoton.Secundario, 76)
        Dim bImprimir As Button = Tema.Boton("Imprimir", Tema.TipoBoton.Secundario, 84)
        Dim bCerrar As Button = Tema.Boton("Cerrar", Tema.TipoBoton.Secundario, 76)
        barra.Controls.AddRange({bPdf, bGuardarPdf, bExcel, bImprimir, bCerrar})
        If _rep.Cabecera.Count > 0 Then
            Dim p As New Panel() With {.Dock = DockStyle.Top, .Height = 22 * ((_rep.Cabecera.Count + 1) \ 2) + 14, .BackColor = Color.White, .Padding = New Padding(16, 6, 16, 4)}
            Dim t As New TableLayoutPanel() With {.Dock = DockStyle.Fill, .ColumnCount = 4}
            t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
            t.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 50))
            t.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 130))
            t.ColumnStyles.Add(New ColumnStyle(SizeType.Percent, 50))
            Dim i As Integer = 0
            For Each kv In _rep.Cabecera
                Dim col As Integer = (i Mod 2) * 2
                Dim fila As Integer = i \ 2
                t.Controls.Add(New Label() With {.Text = kv.Key, .Font = Tema.FuenteNegrita, .AutoSize = True, .Margin = New Padding(0, 2, 6, 2)}, col, fila)
                t.Controls.Add(New Label() With {.Text = kv.Value, .AutoSize = True, .Margin = New Padding(0, 2, 12, 2), .MaximumSize = New Size(380, 0)}, col + 1, fila)
                i += 1
            Next
            p.Controls.Add(t)
            Controls.Add(_grid)
            Controls.Add(p)
        Else
            Controls.Add(_grid)
        End If
        Controls.Add(barra)
        Controls.Add(banner)
        Tema.EstiloGrid(_grid)
        _grid.VirtualMode = True
        _grid.ColumnHeadersHeight = 34
        _grid.AlternatingRowsDefaultCellStyle.BackColor = Color.White
        Dim suma As Double = Math.Max(1.0, _rep.Columnas.Sum(Function(c) c.Peso))
        For i As Integer = 0 To _rep.Columnas.Count - 1
            Dim c As ColumnaRep = _rep.Columnas(i)
            Dim col As New DataGridViewTextBoxColumn() With {.HeaderText = c.Titulo, .Name = "c" & i, .SortMode = DataGridViewColumnSortMode.NotSortable}
            col.AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill
            col.FillWeight = CSng(c.Peso / suma * 100.0)
            col.MinimumWidth = 50
            col.DefaultCellStyle.Alignment = If(c.Alineacion = Alinea.Derecha, DataGridViewContentAlignment.MiddleRight, If(c.Alineacion = Alinea.Centro, DataGridViewContentAlignment.MiddleCenter, DataGridViewContentAlignment.MiddleLeft))
            col.HeaderCell.Style.Alignment = If(c.Alineacion = Alinea.Izquierda, DataGridViewContentAlignment.MiddleLeft, DataGridViewContentAlignment.MiddleCenter)
            _grid.Columns.Add(col)
        Next
        Dim n As Integer = _rep.Columnas.Count
        For Each f As FilaRep In _rep.Filas
            Dim t(n - 1) As String
            Select Case f.Tipo
                Case TipoFila.Grupo, TipoFila.Titulo, TipoFila.Texto
                    t(0) = If(f.Celdas.Count > 0, Convert.ToString(f.Celdas(0)), "")
                Case TipoFila.Salto
                    t(0) = "─────────────────────  (salto de página)  ─────────────────────"
                Case TipoFila.Vacia
                Case Else
                    For i As Integer = 0 To n - 1
                        t(i) = If(i < f.Celdas.Count, FormatoVal.Texto(f.Celdas(i), _rep.Columnas(i).Formato), "")
                    Next
                    If f.Nivel > 0 AndAlso n > 0 Then t(0) = New String(" "c, f.Nivel * 3) & t(0)
            End Select
            _textos.Add(t)
        Next
        _grid.RowCount = _textos.Count
        AddHandler _grid.CellValueNeeded, Sub(o, ev)
                                              If ev.RowIndex < _textos.Count AndAlso ev.ColumnIndex < n Then ev.Value = _textos(ev.RowIndex)(ev.ColumnIndex)
                                          End Sub
        AddHandler _grid.CellFormatting, AddressOf EstiloFila
        AddHandler bPdf.Click, Sub(o, ev) Hacer(Sub() Informes.VerPdf(_rep))
        AddHandler bGuardarPdf.Click, Sub(o, ev) Hacer(Sub() Informes.GuardarPdf(_rep))
        AddHandler bExcel.Click, Sub(o, ev) Hacer(Sub() Informes.GuardarExcel(_rep))
        AddHandler bImprimir.Click, Sub(o, ev) Hacer(Sub() Informes.Imprimir(_rep))
        AddHandler bCerrar.Click, Sub(o, ev) Escritorio.CerrarPestana(Me)
        AddHandler KeyDown, Sub(o, ev)
                                If ev.KeyCode = Keys.F9 Then Hacer(Sub() Informes.VerPdf(_rep))
                                If ev.Control AndAlso ev.KeyCode = Keys.P Then Hacer(Sub() Informes.Imprimir(_rep))
                            End Sub
    End Sub

    Private Sub Hacer(a As Action)
        Try
            Using Msg.Cursor_(True)
                a()
            End Using
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub EstiloFila(o As Object, e As DataGridViewCellFormattingEventArgs)
        If e.RowIndex < 0 OrElse e.RowIndex >= _rep.Filas.Count Then Return
        Dim f As FilaRep = _rep.Filas(e.RowIndex)
        Select Case f.Tipo
            Case TipoFila.Grupo, TipoFila.Titulo
                e.CellStyle.BackColor = Tema.AzulClaro
                e.CellStyle.Font = Tema.FuenteNegrita
            Case TipoFila.Subtotal
                e.CellStyle.Font = Tema.FuenteNegrita
                e.CellStyle.BackColor = Color.FromArgb(240, 244, 250)
            Case TipoFila.Total
                e.CellStyle.Font = Tema.FuenteNegrita
                e.CellStyle.BackColor = Tema.AzulClaro
            Case TipoFila.Texto
                If f.Negrita Then e.CellStyle.Font = Tema.FuenteNegrita
            Case TipoFila.Salto
                e.CellStyle.ForeColor = Tema.Gris
            Case Else
                If f.Negrita Then e.CellStyle.Font = Tema.FuenteNegrita
        End Select
    End Sub
End Class

''' <summary>Cuadro de parámetros generado a partir de la definición del reporte.</summary>
Public Class ReportParamForm
    Inherits Form

    Private ReadOnly _cat As ReporteCat
    Private ReadOnly _controles As New Dictionary(Of String, Control)
    Public ReadOnly Property Valores As Dictionary(Of String, Object)

    Public Sub New(cat As ReporteCat, iniciales As Dictionary(Of String, Object))
        _cat = cat
        Valores = New Dictionary(Of String, Object)(iniciales)
        Tema.Aplicar(Me)
        Text = cat.Titulo
        FormBorderStyle = FormBorderStyle.FixedDialog
        StartPosition = FormStartPosition.CenterParent
        MaximizeBox = False
        MinimizeBox = False
        ShowInTaskbar = False
        KeyPreview = True
        Dim banner As Panel = Tema.Banner(cat.Titulo, "Indique los parámetros del reporte")
        Dim cuerpo As New TableLayoutPanel() With {.ColumnCount = 2, .AutoSize = True, .Dock = DockStyle.Top, .Padding = New Padding(18, 14, 18, 8)}
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 190))
        cuerpo.ColumnStyles.Add(New ColumnStyle(SizeType.Absolute, 340))
        Dim fila As Integer = 0
        For Each p As ParamDef In cat.Params
            Dim l As New Label() With {.Text = p.Titulo & If(p.Requerido, " *", ""), .AutoSize = False, .Width = 186, .Height = 28, .TextAlign = ContentAlignment.MiddleLeft}
            Dim c As Control = Crear(p)
            c.Margin = New Padding(0, 3, 0, 3)
            _controles(p.Clave) = c
            cuerpo.Controls.Add(l, 0, fila)
            cuerpo.Controls.Add(c, 1, fila)
            fila += 1
        Next
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 54, .BackColor = Color.White, .Padding = New Padding(14, 10, 14, 10)}
        Dim ok As Button = Tema.Boton("Ver reporte", Tema.TipoBoton.Primario, 120)
        ok.Dock = DockStyle.Right
        Dim cancelar As Button = Tema.Boton("Cancelar")
        cancelar.Dock = DockStyle.Right
        pie.Controls.Add(ok)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(cancelar)
        Controls.Add(cuerpo)
        Controls.Add(banner)
        Controls.Add(pie)
        ClientSize = New Size(560, banner.Height + 30 + fila * 34 + pie.Height + 10)
        AddHandler ok.Click, Sub(o, e) Aceptar()
        AddHandler cancelar.Click, Sub(o, e) DialogResult = DialogResult.Cancel
        AddHandler KeyDown, Sub(o, e)
                                If e.KeyCode = Keys.Enter AndAlso Not (TypeOf ActiveControl Is Button) AndAlso Not (TypeOf ActiveControl Is PickerBusqueda) Then
                                    e.Handled = True
                                    e.SuppressKeyPress = True
                                    Aceptar()
                                ElseIf e.KeyCode = Keys.Escape Then
                                    DialogResult = DialogResult.Cancel
                                End If
                            End Sub
        AcceptButton = ok
        CancelButton = cancelar
    End Sub

    Private Function Crear(p As ParamDef) As Control
        Dim ini As Object = If(Valores.ContainsKey(p.Clave), Valores(p.Clave), Nothing)
        Dim ctx As Contexto = Sesion.Ctx
        Select Case p.Tipo
            Case ParamTipo.Fecha
                Dim d As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 130}
                Dim v As Date = If(ini Is Nothing, Date.Today, ToDate(ini))
                If v < d.MinDate Then v = Date.Today
                d.Value = v
                Return d
            Case ParamTipo.Mes
                Dim cb As New LookupCombo() With {.Width = 220}
                Dim opciones As New List(Of KeyValuePair(Of String, String))
                Dim m As Date = ctx.Gestion.FechaInicio
                For i As Integer = 0 To 11
                    Dim mm As Date = m.AddMonths(i)
                    opciones.Add(New KeyValuePair(Of String, String)(mm.Month.ToString(), NombreMes(mm.Month) & " " & mm.Year))
                Next
                cb.CargarLista(opciones)
                cb.ValorTexto = ToInt(ini).ToString()
                Return cb
            Case ParamTipo.Texto
                Return New TextBox() With {.Width = 300, .Text = ToStr(ini)}
            Case ParamTipo.Entero
                Return New NumericUpDown() With {.Minimum = 0, .Maximum = 1000000, .Value = Math.Max(0, ToInt(ini)), .Width = 100, .TextAlign = HorizontalAlignment.Right}
            Case ParamTipo.Importe
                Return New CampoImporte() With {.Width = 140, .Valor = ToDec(ini), .PermiteNegativo = True}
            Case ParamTipo.Bool
                Return New CheckBox() With {.AutoSize = True, .Checked = ToFlag(ini)}
            Case ParamTipo.Lista
                Dim cb As New LookupCombo() With {.Width = 330}
                cb.CargarLista(p.Opciones)
                cb.ValorTexto = ToStr(ini)
                Return cb
            Case ParamTipo.Cuenta
                Return New PickerCuenta() With {.Width = 330, .SoloMovimiento = False}
            Case ParamTipo.CuentaBanco
                Dim cb As New LookupCombo() With {.Width = 330}
                Dim dt As DataTable = New BancoService(ctx).CuentasBanco()
                If dt.Rows.Count = 0 Then
                    Dim pk As New PickerCuenta() With {.Width = 330, .SoloMovimiento = True}
                    Return pk
                End If
                Dim tt As New DataTable()
                tt.Columns.Add("Id", GetType(Integer))
                tt.Columns.Add("Texto", GetType(String))
                For Each r As DataRow In dt.Rows
                    tt.Rows.Add(r.GetI("Id"), r.GetS("Codigo") & "  " & r.GetS("Nombre"))
                Next
                cb.Cargar(tt, "Id", "Texto", False)
                Return cb
            Case ParamTipo.Tercero, ParamTipo.Cliente, ParamTipo.Proveedor
                Dim pb As New PickerBusqueda() With {.Width = 330}
                Dim clase As String = If(p.Tipo = ParamTipo.Cliente, "CXC", If(p.Tipo = ParamTipo.Proveedor, "CXP", ""))
                pb.Configurar("Buscar " & If(p.Tipo = ParamTipo.Proveedor, "proveedor", If(p.Tipo = ParamTipo.Cliente, "cliente", "cliente o proveedor")), Function() New TerceroService(ctx).Listar(clase),
                              {New ColumnaBusqueda("Codigo", "Código", 90), New ColumnaBusqueda("Nombre", "Nombre / razón social", 340), New ColumnaBusqueda("Nit", "NIT", 110)}, "Id", Function(r) r.GetS("Codigo") & " - " & r.GetS("Nombre"))
                Return pb
            Case ParamTipo.Item
                Dim pb As New PickerBusqueda() With {.Width = 330}
                pb.Configurar("Buscar ítem", Function() New InventarioService(ctx).ListarItems(), {New ColumnaBusqueda("Codigo", "Código", 110), New ColumnaBusqueda("Descripcion", "Descripción", 400)}, "Id", Function(r) r.GetS("Codigo") & " - " & r.GetS("Descripcion"))
                Return pb
            Case ParamTipo.Almacen
                Dim cb As New LookupCombo() With {.Width = 330}
                cb.Cargar(ctx.Db.Query("SELECT Id, Nombre FROM Almacen WHERE Activo=1 ORDER BY Nombre"), "Id", "Nombre", True, "(Todos)")
                Return cb
            Case ParamTipo.Empleado
                Dim pb As New PickerBusqueda() With {.Width = 330}
                pb.Configurar("Buscar empleado", Function() New PlanillaService(ctx).ListarEmpleados(), {New ColumnaBusqueda("Nombre", "Apellidos y nombres", 340), New ColumnaBusqueda("Ci", "C.I.", 100)}, "Id", Function(r) r.GetS("Nombre"))
                Return pb
            Case ParamTipo.Orden
                Dim pb As New PickerBusqueda() With {.Width = 330}
                pb.Configurar("Buscar orden de producción", Function() New ProduccionService(ctx).Listar(), {New ColumnaBusqueda("Numero", "Nº", 60), New ColumnaBusqueda("Producto", "Producto", 340), New ColumnaBusqueda("Estado", "Est.", 50)}, "Id", Function(r) "Orden " & r.GetS("Numero") & " - " & r.GetS("Producto"))
                Return pb
            Case ParamTipo.Comprobante
                Dim pb As New PickerBusqueda() With {.Width = 330}
                pb.Configurar("Buscar comprobante", Function() New VoucherService(ctx).Listar(ctx.Gestion.FechaInicio, ctx.Gestion.FechaFin),
                              {New ColumnaBusqueda("Tipo", "Tipo", 50), New ColumnaBusqueda("Numero", "Nº", 60), New ColumnaBusqueda("Fecha", "Fecha", 90), New ColumnaBusqueda("Glosa", "Glosa", 420)}, "Id", Function(r) r.GetS("Tipo") & "-" & r.GetS("Numero") & "  " & r.GetS("Glosa"))
                Return pb
            Case Else
                Return New TextBox() With {.Width = 200}
        End Select
    End Function

    Private Sub Aceptar()
        For Each p As ParamDef In _cat.Params
            Dim c As Control = _controles(p.Clave)
            Select Case p.Tipo
                Case ParamTipo.Fecha : Valores(p.Clave) = CType(c, DateTimePicker).Value.Date
                Case ParamTipo.Mes : Valores(p.Clave) = ToInt(CType(c, LookupCombo).ValorTexto)
                Case ParamTipo.Texto : Valores(p.Clave) = c.Text.Trim()
                Case ParamTipo.Entero : Valores(p.Clave) = CInt(CType(c, NumericUpDown).Value)
                Case ParamTipo.Importe : Valores(p.Clave) = CType(c, CampoImporte).Valor
                Case ParamTipo.Bool : Valores(p.Clave) = CType(c, CheckBox).Checked
                Case ParamTipo.Lista : Valores(p.Clave) = CType(c, LookupCombo).ValorTexto
                Case ParamTipo.Cuenta : Valores(p.Clave) = CType(c, PickerCuenta).CuentaId
                Case ParamTipo.CuentaBanco
                    If TypeOf c Is PickerCuenta Then Valores(p.Clave) = CType(c, PickerCuenta).CuentaId Else Valores(p.Clave) = CType(c, LookupCombo).ValorId
                Case ParamTipo.Almacen : Valores(p.Clave) = CType(c, LookupCombo).ValorId
                Case Else : Valores(p.Clave) = CType(c, PickerBusqueda).SeleccionId
            End Select
            If p.Requerido AndAlso (Not Valores.ContainsKey(p.Clave) OrElse ToInt(Valores(p.Clave)) = 0) AndAlso p.Tipo <> ParamTipo.Entero AndAlso p.Tipo <> ParamTipo.Mes AndAlso p.Tipo <> ParamTipo.Texto Then
                Msg.Aviso("Seleccione: " & p.Titulo)
                c.Focus()
                Return
            End If
        Next
        DialogResult = DialogResult.OK
    End Sub
End Class
