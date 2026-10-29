Imports System.IO
Imports ContaBol.Core.Common
Imports ContaBol.Core.Reports
Imports ContaBol.Core.Services

''' <summary>Base de las pantallas de trabajo: tema, atajos y acceso al contexto (empresa/gestión) activo.</summary>
Public Class FormBase
    Inherits Form

    Public Sub New()
        Tema.Aplicar(Me)
        KeyPreview = True
        StartPosition = FormStartPosition.CenterParent
        ShowIcon = False
    End Sub

    Protected ReadOnly Property Ctx As Contexto
        Get
            Return Sesion.Ctx
        End Get
    End Property

    ''' <summary>Texto de la pestaña cuando se muestra dentro de la ventana principal.</summary>
    Public Overridable ReadOnly Property TextoPestana As String
        Get
            Return Text
        End Get
    End Property

    Public Overridable Sub Refrescar()
    End Sub

    ''' <summary>Ejecuta una acción mostrando los errores de forma amigable.</summary>
    Protected Function Intentar(accion As Action) As Boolean
        Try
            Using Msg.Cursor_(True)
                accion()
            End Using
            Return True
        Catch ex As Exception
            Msg.ErrorMsg(ex)
            Return False
        End Try
    End Function
End Class

''' <summary>Pantalla de listado con barra de herramientas estándar, búsqueda, exportación a PDF/Excel y mantenimiento.</summary>
Public MustInherit Class ListaForm
    Inherits FormBase

    Protected ReadOnly Grid As New DataGridView()
    Protected ReadOnly Barra As New FlowLayoutPanel()
    Private ReadOnly _txtBuscar As New TextBox()
    Private ReadOnly _estado As New Label()
    Private _tabla As DataTable
    Private _vista As DataTable
    Protected ReadOnly BotonNuevo As Button = Tema.Boton("Nuevo", Tema.TipoBoton.Primario, 84)
    Protected ReadOnly BotonEditar As Button = Tema.Boton("Editar", Tema.TipoBoton.Secundario, 84)
    Protected ReadOnly BotonEliminar As Button = Tema.Boton("Eliminar", Tema.TipoBoton.Peligro, 84)
    Protected ReadOnly BotonActualizar As Button = Tema.Boton("Actualizar", Tema.TipoBoton.Secundario, 92)
    Protected ReadOnly BotonPdf As Button = Tema.Boton("PDF", Tema.TipoBoton.Secundario, 64)
    Protected ReadOnly BotonExcel As Button = Tema.Boton("Excel", Tema.TipoBoton.Secundario, 64)

    Protected MustOverride ReadOnly Property TituloLista As String
    Protected Overridable ReadOnly Property SubtituloLista As String
        Get
            Return ""
        End Get
    End Property
    ''' <summary>Permiso requerido para crear, editar y eliminar (vacío = libre).</summary>
    Protected Overridable ReadOnly Property PermisoEdicion As String
        Get
            Return ""
        End Get
    End Property
    Protected Overridable ReadOnly Property PermiteNuevo As Boolean
        Get
            Return True
        End Get
    End Property
    Protected Overridable ReadOnly Property PermiteEliminar As Boolean
        Get
            Return True
        End Get
    End Property

    Protected MustOverride Function CargarDatos() As DataTable
    Protected MustOverride Sub ConfigurarColumnas()
    Protected Overridable Sub Nuevo()
    End Sub
    Protected Overridable Sub Editar(fila As DataRow)
    End Sub
    Protected Overridable Sub Eliminar(fila As DataRow)
    End Sub
    Protected Overridable Sub AgregarBotones()
    End Sub
    Protected Overridable Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
    End Sub

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return TituloLista
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = TituloLista
        Dim banner As Panel = Tema.Banner(TituloLista, SubtituloLista)
        Barra.Dock = DockStyle.Top
        Barra.Height = 46
        Barra.Padding = New Padding(12, 7, 12, 4)
        Barra.BackColor = Fondo_()
        Barra.WrapContents = False
        Dim puedeEditar As Boolean = PermisoEdicion = "" OrElse Sesion.Puede(PermisoEdicion)
        If PermiteNuevo Then Barra.Controls.Add(BotonNuevo)
        Barra.Controls.Add(BotonEditar)
        If PermiteEliminar Then Barra.Controls.Add(BotonEliminar)
        AgregarBotones()
        Barra.Controls.Add(BotonActualizar)
        Barra.Controls.Add(BotonPdf)
        Barra.Controls.Add(BotonExcel)
        BotonNuevo.Enabled = puedeEditar
        BotonEditar.Enabled = puedeEditar
        BotonEliminar.Enabled = puedeEditar
        Dim buscar As New Panel() With {.Dock = DockStyle.Right, .Width = 250, .Padding = New Padding(0, 3, 12, 0)}
        _txtBuscar.Dock = DockStyle.Fill
        buscar.Controls.Add(_txtBuscar)
        Dim lbl As New Label() With {.Text = "Buscar:", .Dock = DockStyle.Left, .Width = 52, .TextAlign = ContentAlignment.MiddleLeft}
        buscar.Controls.Add(lbl)
        Dim contenedorBarra As New Panel() With {.Dock = DockStyle.Top, .Height = 46}
        contenedorBarra.Controls.Add(Barra)
        contenedorBarra.Controls.Add(buscar)
        Tema.EstiloGrid(Grid)
        ConfigurarColumnas()
        _estado.Dock = DockStyle.Bottom
        _estado.Height = 24
        _estado.Padding = New Padding(12, 4, 0, 0)
        _estado.ForeColor = Tema.Gris
        Controls.Add(Grid)
        Controls.Add(_estado)
        Controls.Add(contenedorBarra)
        Controls.Add(banner)
        AddHandler BotonNuevo.Click, Sub(o, ev) Intentar(Sub()
                                                             Nuevo()
                                                             Refrescar()
                                                         End Sub)
        AddHandler BotonEditar.Click, Sub(o, ev) EditarActual()
        AddHandler BotonEliminar.Click, Sub(o, ev) EliminarActual()
        AddHandler BotonActualizar.Click, Sub(o, ev) Refrescar()
        AddHandler BotonPdf.Click, Sub(o, ev) Exportar(True)
        AddHandler BotonExcel.Click, Sub(o, ev) Exportar(False)
        AddHandler Grid.CellDoubleClick, Sub(o, ev) If ev.RowIndex >= 0 Then EditarActual()
        AddHandler Grid.KeyDown, Sub(o, ev)
                                     If ev.KeyCode = Keys.Enter Then
                                         ev.Handled = True
                                         EditarActual()
                                     ElseIf ev.KeyCode = Keys.Delete AndAlso BotonEliminar.Enabled AndAlso PermiteEliminar Then
                                         ev.Handled = True
                                         EliminarActual()
                                     End If
                                 End Sub
        AddHandler _txtBuscar.TextChanged, Sub(o, ev) AplicarFiltro()
        AddHandler Grid.CellFormatting, AddressOf FormatearCelda
        AddHandler KeyDown, Sub(o, ev)
                                If ev.KeyCode = Keys.F5 Then Refrescar()
                                If ev.KeyCode = Keys.F3 OrElse (ev.Control AndAlso ev.KeyCode = Keys.F) Then
                                    _txtBuscar.Focus()
                                    ev.Handled = True
                                End If
                            End Sub
        Refrescar()
    End Sub

    Private Shared Function Fondo_() As Color
        Return Tema.Fondo
    End Function

    Private Sub FormatearCelda(o As Object, e As DataGridViewCellFormattingEventArgs)
        If e.RowIndex < 0 OrElse e.RowIndex >= Grid.Rows.Count Then Return
        Dim v As DataRowView = TryCast(Grid.Rows(e.RowIndex).DataBoundItem, DataRowView)
        If v Is Nothing Then Return
        FilaColoreada(v.Row, e.CellStyle)
    End Sub

    Public Overrides Sub Refrescar()
        Dim id As Integer = 0
        Dim idx As Integer = If(Grid.CurrentRow Is Nothing, -1, Grid.CurrentRow.Index)
        Try
            Using Msg.Cursor_(True)
                _tabla = CargarDatos()
            End Using
        Catch ex As Exception
            Msg.ErrorMsg(ex)
            Return
        End Try
        AplicarFiltro()
        If idx >= 0 AndAlso idx < Grid.Rows.Count Then Grid.CurrentCell = Grid.Rows(idx).Cells(0)
    End Sub

    Private Sub AplicarFiltro()
        If _tabla Is Nothing Then Return
        Dim t As String = _txtBuscar.Text.Trim().ToLowerInvariant()
        If t = "" Then
            _vista = _tabla
        Else
            _vista = _tabla.Clone()
            For Each r As DataRow In _tabla.Rows
                For Each c As DataColumn In _tabla.Columns
                    If c.DataType Is GetType(String) OrElse c.DataType Is GetType(Object) Then
                        If ToStr(r(c)).ToLowerInvariant().Contains(t) Then
                            _vista.ImportRow(r)
                            Exit For
                        End If
                    End If
                Next
            Next
        End If
        Grid.DataSource = _vista
        _estado.Text = _vista.Rows.Count.ToString("N0") & " registro(s)" & If(t <> "", " (filtrado de " & _tabla.Rows.Count.ToString("N0") & ")", "")
    End Sub

    Protected Function FilaActual() As DataRow
        If Grid.CurrentRow Is Nothing Then Return Nothing
        Dim v As DataRowView = TryCast(Grid.CurrentRow.DataBoundItem, DataRowView)
        Return If(v Is Nothing, Nothing, v.Row)
    End Function

    Private Sub EditarActual()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then
            Msg.Aviso("Seleccione un registro de la lista.")
            Return
        End If
        Intentar(Sub()
                     Editar(f)
                     Refrescar()
                 End Sub)
    End Sub

    Private Sub EliminarActual()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then
            Msg.Aviso("Seleccione un registro de la lista.")
            Return
        End If
        If Not Msg.Confirmar("¿Desea eliminar el registro seleccionado?", "Eliminar", True) Then Return
        Intentar(Sub()
                     Eliminar(f)
                     Refrescar()
                 End Sub)
    End Sub

    ''' <summary>Reporte para exportar. Por defecto se arma con las columnas visibles de la grilla.</summary>
    Protected Overridable Function ReporteDeLista() As ReporteDef
        Return Exportacion.GridAReporte(Grid, TituloLista)
    End Function

    Private Sub Exportar(pdf As Boolean)
        Try
            Dim rep As ReporteDef = ReporteDeLista()
            If pdf Then Informes.GuardarPdf(rep) Else Informes.GuardarExcel(rep)
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class

Public Module Exportacion

    ''' <summary>Convierte lo que se ve en una grilla en un reporte (se exporta tal cual a PDF y Excel).</summary>
    Public Function GridAReporte(g As DataGridView, titulo As String, Optional subtitulo As String = "") As ReporteDef
        Dim rep As ReporteDef = BaseInforme.Nuevo(Sesion.Ctx, titulo, subtitulo, "")
        Dim cols As List(Of DataGridViewColumn) = g.Columns.Cast(Of DataGridViewColumn)().Where(Function(c) c.Visible).OrderBy(Function(c) c.DisplayIndex).ToList()
        Dim anchoTotal As Integer = cols.Sum(Function(c) c.Width)
        For Each c In cols
            Dim fmt As Formato = Formato.Texto
            Dim fs As String = c.DefaultCellStyle.Format
            If TypeOf c Is DataGridViewCheckBoxColumn Then
                fmt = Formato.Texto
            ElseIf fs = "dd/MM/yyyy" Then
                fmt = Formato.Fecha
            ElseIf fs.StartsWith("N") AndAlso fs.Length >= 2 AndAlso fs(1) = "0"c Then
                fmt = Formato.Entero
            ElseIf fs.StartsWith("N") Then
                fmt = Formato.Monto
            End If
            Dim alin As Alinea = If(c.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleRight, Alinea.Derecha, If(c.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter, Alinea.Centro, Alinea.Izquierda))
            rep.Col(c.HeaderText, Math.Max(0.5, c.Width / 60.0), fmt, alin)
        Next
        rep.Horizontal = anchoTotal > 760
        For Each row As DataGridViewRow In g.Rows
            Dim v As DataRowView = TryCast(row.DataBoundItem, DataRowView)
            Dim cel As New List(Of Object)
            For Each c In cols
                Dim val As Object = Nothing
                If v IsNot Nothing AndAlso c.DataPropertyName <> "" AndAlso v.Row.Table.Columns.Contains(c.DataPropertyName) Then
                    val = v.Row(c.DataPropertyName)
                    If IsNil(val) Then val = Nothing
                ElseIf v Is Nothing Then
                    val = row.Cells(c.Index).Value
                End If
                If TypeOf c Is DataGridViewCheckBoxColumn Then val = If(ToFlag(val), "Sí", "")
                cel.Add(val)
            Next
            rep.Fila(cel.ToArray())
        Next
        rep.Notas.Add("Total de registros: " & rep.Filas.Count.ToString("N0"))
        Return rep
    End Function
End Module
