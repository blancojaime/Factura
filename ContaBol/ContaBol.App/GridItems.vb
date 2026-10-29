Imports ContaBol.Core.Common
Imports ContaBol.Core.Services

Public Class LineaItem
    Public Property ItemId As Integer
    Public Property Codigo As String
    Public Property Descripcion As String
    Public Property Cantidad As Decimal
    Public Property Precio As Decimal
    Public Property FechaVenc As Date?
    Public ReadOnly Property Importe As Decimal
        Get
            Return (Cantidad * Precio).R2()
        End Get
    End Property
End Class

''' <summary>Grilla de ítems para ventas, compras y movimientos: código con búsqueda (F4), precio sugerido, importe y stock.</summary>
Public Class GridItems
    Inherits GridEntrada

    Public Event LineasCambiaron As EventHandler

    Private _colCod As DataGridViewTextBoxColumn
    Private _colDes As DataGridViewTextBoxColumn
    Private _colCant As DataGridViewTextBoxColumn
    Private _colPrecio As DataGridViewTextBoxColumn
    Private _colImporte As DataGridViewTextBoxColumn
    Private _colStock As DataGridViewTextBoxColumn
    Private _colVenc As DataGridViewTextBoxColumn
    Private _items As DataTable
    Private _cargando As Boolean

    ''' <summary>Cómo se obtiene el precio sugerido al elegir un ítem.</summary>
    Public Property PrecioDe As Func(Of ItemDto, Decimal)
    Public Property SoloInventariables As Boolean
    Public Property MostrarStock As Boolean
    Public Property PedirVencimiento As Boolean
    Public Property AlmacenStock As Func(Of Integer)
    Public Property TextoPrecio As String = "Precio unit."

    Public Sub Iniciar()
        Tema.EstiloGrid(Me, True)
        AllowUserToAddRows = True
        AllowUserToDeleteRows = True
        RowHeadersVisible = True
        RowHeadersWidth = 28
        SelectionMode = DataGridViewSelectionMode.CellSelect
        EditMode = DataGridViewEditMode.EditOnEnter
        ColumnHeadersHeight = 30
        _colCod = Tema.ColTexto(Me, "cod", "Código del ítem (F4 busca)", 160)
        _colDes = Tema.ColTexto(Me, "des", "Descripción", 320, True)
        _colDes.ReadOnly = True
        _colDes.DefaultCellStyle.ForeColor = Tema.Gris
        _colCant = Tema.ColImporte(Me, "cant", "Cantidad", 90, "N2")
        _colPrecio = Tema.ColImporte(Me, "precio", TextoPrecio, 110, "N4")
        _colImporte = Tema.ColImporte(Me, "importe", "Importe", 110)
        _colImporte.ReadOnly = True
        _colImporte.DefaultCellStyle.BackColor = Color.FromArgb(246, 247, 249)
        If MostrarStock Then
            _colStock = Tema.ColImporte(Me, "stock", "Stock", 80, "N2")
            _colStock.ReadOnly = True
            _colStock.DefaultCellStyle.ForeColor = Tema.Gris
        End If
        If PedirVencimiento Then
            _colVenc = Tema.ColTexto(Me, "venc", "Vence (dd/mm/aaaa)", 120)
            _colVenc.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        End If
        For Each c As DataGridViewColumn In Columns
            c.SortMode = DataGridViewColumnSortMode.NotSortable
        Next
        AddHandler CellEndEdit, AddressOf FinEdicion
        AddHandler CellParsing, AddressOf Parsear
        AddHandler EditingControlShowing, AddressOf MostrarEditor
        AddHandler RowsRemoved, Sub(o, e) RaiseEvent LineasCambiaron(Me, EventArgs.Empty)
        AddHandler DataError, Sub(o, e) e.ThrowException = False
        AddHandler KeyDown, AddressOf Teclas
    End Sub

    Public Sub RecargarItems()
        _items = Svc.Inventario.ListarItems("", True)
    End Sub

    Private Function Catalogo_() As DataTable
        If _items Is Nothing Then RecargarItems()
        Return _items
    End Function

    Private Function FilaItem(id As Integer) As DataRow
        Return Catalogo_().Rows.Cast(Of DataRow)().FirstOrDefault(Function(r) r.GetI("Id") = id)
    End Function

    Private Sub Parsear(o As Object, e As DataGridViewCellParsingEventArgs)
        If e.ColumnIndex = _colCant.Index OrElse e.ColumnIndex = _colPrecio.Index Then
            Dim d As Decimal
            If Numeros.Parse(ToStr(e.Value), d) Then e.Value = If(d = 0D, CObj(Nothing), CObj(d)) Else e.Value = Nothing
            e.ParsingApplied = True
        End If
    End Sub

    Private Sub MostrarEditor(o As Object, e As DataGridViewEditingControlShowingEventArgs)
        Dim tb As TextBox = TryCast(e.Control, TextBox)
        If tb Is Nothing Then Return
        RemoveHandler tb.KeyPress, AddressOf SoloNumero
        RemoveHandler tb.KeyDown, AddressOf TeclaEditor
        AddHandler tb.KeyDown, AddressOf TeclaEditor
        If CurrentCell.ColumnIndex = _colCant.Index OrElse CurrentCell.ColumnIndex = _colPrecio.Index Then AddHandler tb.KeyPress, AddressOf SoloNumero
        tb.SelectAll()
    End Sub

    Private Sub SoloNumero(o As Object, e As KeyPressEventArgs)
        If Char.IsControl(e.KeyChar) OrElse Char.IsDigit(e.KeyChar) OrElse e.KeyChar = "."c OrElse e.KeyChar = ","c Then Return
        e.Handled = True
    End Sub

    Private Sub TeclaEditor(o As Object, e As KeyEventArgs)
        If e.KeyCode = Keys.F4 AndAlso CurrentCell IsNot Nothing AndAlso CurrentCell.ColumnIndex = _colCod.Index Then
            e.Handled = True
            Dim txt As String = CType(o, TextBox).Text
            EndEdit()
            Buscar(CurrentRow, txt)
        End If
    End Sub

    Private Sub Teclas(o As Object, e As KeyEventArgs)
        If e.KeyCode = Keys.F4 AndAlso CurrentCell IsNot Nothing AndAlso CurrentCell.ColumnIndex = _colCod.Index AndAlso CurrentRow IsNot Nothing Then
            e.Handled = True
            If CurrentRow.IsNewRow Then
                Dim i As Integer = Rows.Count - 1
                CurrentCell = Rows(i).Cells(_colCod.Index)
            End If
            Buscar(CurrentRow, ToStr(CurrentCell.Value))
        End If
    End Sub

    Private Sub FinEdicion(o As Object, e As DataGridViewCellEventArgs)
        If _cargando OrElse e.RowIndex < 0 Then Return
        Dim r As DataGridViewRow = Rows(e.RowIndex)
        If r.IsNewRow Then Return
        If e.ColumnIndex = _colCod.Index Then Resolver(r)
        Totalizar(r)
        RaiseEvent LineasCambiaron(Me, EventArgs.Empty)
    End Sub

    Private Sub Resolver(r As DataGridViewRow)
        Dim txt As String = ToStr(r.Cells(_colCod.Index).Value).Trim()
        If txt = "" Then
            Poner(r, 0)
            Return
        End If
        Dim it As ItemDto = Svc.Inventario.BuscarItem(txt)
        If it IsNot Nothing AndAlso it.Activo AndAlso (Not SoloInventariables OrElse Not it.EsServicio) Then
            Poner(r, it.Id)
        Else
            Buscar(r, txt)
        End If
    End Sub

    Private Sub Buscar(r As DataGridViewRow, patron As String)
        Dim dt As DataTable = Catalogo_()
        Dim vista As DataTable = dt
        If SoloInventariables Then
            vista = dt.Clone()
            For Each x As DataRow In dt.Rows
                If Not x.GetF("EsServicio") Then vista.ImportRow(x)
            Next
        End If
        Using d As New BuscadorDialog("Buscar ítem", vista, {New ColumnaBusqueda("Codigo", "Código", 120), New ColumnaBusqueda("Descripcion", "Descripción", 380), New ColumnaBusqueda("Stock", "Stock", 80, True), New ColumnaBusqueda("PrecioA", "Precio A", 90, True)}, If(patron, ""))
            If d.ShowDialog(FindForm()) = DialogResult.OK Then
                Poner(r, d.FilaElegida.GetI("Id"))
                Totalizar(r)
                RaiseEvent LineasCambiaron(Me, EventArgs.Empty)
            Else
                Dim idActual As Object = r.Cells(_colCod.Index).Tag
                Poner(r, If(idActual Is Nothing, 0, CInt(idActual)))
            End If
        End Using
    End Sub

    Private Sub Poner(r As DataGridViewRow, itemId As Integer)
        If itemId = 0 Then
            r.Cells(_colCod.Index).Value = Nothing
            r.Cells(_colCod.Index).Tag = Nothing
            r.Cells(_colDes.Index).Value = Nothing
            Return
        End If
        Dim f As DataRow = FilaItem(itemId)
        If f Is Nothing Then
            RecargarItems()
            f = FilaItem(itemId)
        End If
        If f Is Nothing Then Return
        Dim cambio As Boolean = r.Cells(_colCod.Index).Tag Is Nothing OrElse CInt(r.Cells(_colCod.Index).Tag) <> itemId
        r.Cells(_colCod.Index).Value = f.GetS("Codigo")
        r.Cells(_colCod.Index).Tag = itemId
        r.Cells(_colDes.Index).Value = f.GetS("Descripcion")
        If cambio Then
            If PrecioDe IsNot Nothing AndAlso ToDec(r.Cells(_colPrecio.Index).Value) = 0D Then
                Dim it As ItemDto = Svc.Inventario.ObtenerItem(itemId)
                Dim p As Decimal = PrecioDe(it)
                If p <> 0D Then r.Cells(_colPrecio.Index).Value = p
            End If
            If ToDec(r.Cells(_colCant.Index).Value) = 0D Then r.Cells(_colCant.Index).Value = 1D
            If _colStock IsNot Nothing Then
                Dim alm As Integer = If(AlmacenStock Is Nothing, 0, AlmacenStock.Invoke())
                r.Cells(_colStock.Index).Value = If(f.GetF("EsServicio"), CObj(Nothing), CObj(Svc.Inventario.Stock(itemId, alm)))
            End If
        End If
    End Sub

    Private Sub Totalizar(r As DataGridViewRow)
        Dim c As Decimal = ToDec(r.Cells(_colCant.Index).Value), p As Decimal = ToDec(r.Cells(_colPrecio.Index).Value)
        r.Cells(_colImporte.Index).Value = If(c * p = 0D, CObj(Nothing), CObj((c * p).R2()))
    End Sub

    ''' <summary>Actualiza el stock mostrado cuando cambia el almacén.</summary>
    Public Sub RefrescarStock()
        If _colStock Is Nothing Then Return
        Dim alm As Integer = If(AlmacenStock Is Nothing, 0, AlmacenStock.Invoke())
        For Each r As DataGridViewRow In Rows
            If r.IsNewRow OrElse r.Cells(_colCod.Index).Tag Is Nothing Then Continue For
            Dim id As Integer = CInt(r.Cells(_colCod.Index).Tag)
            Dim f As DataRow = FilaItem(id)
            r.Cells(_colStock.Index).Value = If(f Is Nothing OrElse f.GetF("EsServicio"), CObj(Nothing), CObj(Svc.Inventario.Stock(id, alm)))
        Next
    End Sub

    Public Sub RaiseLineas()
        RaiseEvent LineasCambiaron(Me, EventArgs.Empty)
    End Sub

    Public Sub Limpiar()
        _cargando = True
        Rows.Clear()
        _cargando = False
        RaiseEvent LineasCambiaron(Me, EventArgs.Empty)
    End Sub

    Public Sub Agregar(itemId As Integer, cantidad As Decimal, precio As Decimal)
        Dim i As Integer = Rows.Add()
        Dim r As DataGridViewRow = Rows(i)
        _cargando = True
        Poner(r, itemId)
        r.Cells(_colCant.Index).Value = cantidad
        r.Cells(_colPrecio.Index).Value = precio
        Totalizar(r)
        _cargando = False
        RaiseEvent LineasCambiaron(Me, EventArgs.Empty)
    End Sub

    Public Function Lineas() As List(Of LineaItem)
        EndEdit()
        Dim res As New List(Of LineaItem)
        Dim n As Integer = 0
        For Each r As DataGridViewRow In Rows
            If r.IsNewRow Then Continue For
            n += 1
            Dim tag As Object = r.Cells(_colCod.Index).Tag
            Dim c As Decimal = ToDec(r.Cells(_colCant.Index).Value), p As Decimal = ToDec(r.Cells(_colPrecio.Index).Value)
            If tag Is Nothing Then
                If c <> 0D OrElse p <> 0D Then Throw New InvalidOperationException("La línea " & n & " tiene cantidad o precio pero no tiene ítem.")
                Continue For
            End If
            If c <= 0D Then Throw New InvalidOperationException("La línea " & n & ": ingrese la cantidad.")
            Dim l As New LineaItem With {.ItemId = CInt(tag), .Codigo = ToStr(r.Cells(_colCod.Index).Value), .Descripcion = ToStr(r.Cells(_colDes.Index).Value), .Cantidad = c, .Precio = p}
            If _colVenc IsNot Nothing Then
                Dim t As String = ToStr(r.Cells(_colVenc.Index).Value).Trim()
                If t <> "" Then
                    Dim d As Date
                    If Not Date.TryParseExact(t, {"dd/MM/yyyy", "d/M/yyyy", "dd/MM/yy"}, Nothing, Globalization.DateTimeStyles.None, d) Then Throw New InvalidOperationException("La línea " & n & ": fecha de vencimiento inválida (use dd/mm/aaaa).")
                    l.FechaVenc = d
                End If
            End If
            res.Add(l)
        Next
        Return res
    End Function

    Public Function Subtotal() As Decimal
        Dim t As Decimal
        For Each r As DataGridViewRow In Rows
            If r.IsNewRow Then Continue For
            t += ToDec(r.Cells(_colImporte.Index).Value)
        Next
        Return t
    End Function
End Class
