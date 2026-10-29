Imports System.IO
Imports ClosedXML.Excel
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Plan de cuentas: alta, modificación, subcuentas, importación desde Excel/CSV y exportación.</summary>
Public Class PlanCuentasForm
    Inherits ListaForm

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Plan de cuentas"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Estructura jerárquica. Solo las cuentas de movimiento reciben imputaciones. Seleccione una cuenta y use 'Subcuenta' para crear hijas."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "CONT.PLAN"
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim bSub As Button = Tema.Boton("Subcuenta", Tema.TipoBoton.Secundario, 92)
        Dim bImp As Button = Tema.Boton("Importar…", Tema.TipoBoton.Secundario, 92)
        Barra.Controls.AddRange({bSub, bImp})
        AddHandler bSub.Click, Sub(o, e) NuevaSubcuenta()
        AddHandler bImp.Click, Sub(o, e) Importar()
        bSub.Enabled = Sesion.Puede("CONT.PLAN")
        bImp.Enabled = Sesion.Puede("CONT.PLAN")
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = Ctx.Db.Query("SELECT * FROM Cuenta ORDER BY Codigo")
        dt.Columns.Add("Desc", GetType(String))
        dt.Columns.Add("RubroTxt", GetType(String))
        dt.Columns.Add("MovTxt", GetType(String))
        dt.Columns.Add("MonTxt", GetType(String))
        dt.Columns.Add("AjTxt", GetType(String))
        dt.Columns.Add("PpTxt", GetType(String))
        dt.Columns.Add("BcoTxt", GetType(String))
        Dim rubros As String() = {"", "Activo", "Pasivo", "Patrimonio", "Ingreso", "Egreso", "Ord. deudora", "Ord. acreedora"}
        For Each r As DataRow In dt.Rows
            r("Desc") = New String(ChrW(160), Math.Max(0, (r.GetI("Nivel") - 1) * 4)) & r.GetS("Nombre")
            r("RubroTxt") = If(r.GetI("Rubro") < rubros.Length, rubros(r.GetI("Rubro")), "")
            r("MovTxt") = If(r.GetF("EsMovimiento"), "Sí", "")
            r("MonTxt") = If(r.GetS("Moneda") = "USD", "$us", "Bs")
            r("AjTxt") = If(r.GetF("Ajustable"), "Sí", "")
            r("PpTxt") = If(r.GetF("Presupuestable"), "Sí", "")
            r("BcoTxt") = If(r.GetF("EsBanco"), "Sí", "")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Codigo", "Código", 150)
        Tema.ColTexto(Grid, "Desc", "Descripción", 360, True)
        Tema.ColTexto(Grid, "RubroTxt", "Rubro", 90)
        Tema.ColTexto(Grid, "MovTxt", "Mov.", 46).DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        Tema.ColTexto(Grid, "MonTxt", "Mon.", 46).DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        Tema.ColTexto(Grid, "AjTxt", "Ajust.", 50).DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        Tema.ColTexto(Grid, "PpTxt", "Presup.", 56).DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        Tema.ColTexto(Grid, "BcoTxt", "Banco", 50).DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
        Tema.ColTexto(Grid, "CostoTipo", "F/V", 40).DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If Not fila.GetF("EsMovimiento") Then estilo.Font = Tema.FuenteNegrita
        If Not fila.GetF("Activa") Then estilo.ForeColor = Tema.Gris
    End Sub

    Private Function Campos(nueva As Boolean) As List(Of CampoUI)
        Dim l As New List(Of CampoUI)
        Dim cod As CampoUI = CampoUI.Txt("Codigo", "Código", 20, True)
        cod.Ayuda = "El primer dígito indica el rubro: 1 Activo, 2 Pasivo, 3 Patrimonio, 4 Ingreso, 5 Egreso."
        l.Add(cod)
        l.Add(CampoUI.Lst("Moneda", "Moneda de la cuenta", "BS|Bolivianos", "USD|Dólares (moneda extranjera)"))
        l.Add(CampoUI.Txt("Nombre", "Descripción", 120, True, True))
        l.Add(CampoUI.Chk("Ajustable", "Ajustable por inflación (UFV)"))
        l.Add(CampoUI.Chk("Presupuestable", "Presupuestable"))
        l.Add(CampoUI.Lst("CostoTipo", "Costo", "|No aplica", "F|Costo fijo", "V|Costo variable"))
        l.Add(CampoUI.Chk("EsBanco", "Cuenta bancaria (conciliación)"))
        l.Add(CampoUI.Chk("Activa", "Cuenta activa", True))
        Return l
    End Function

    Private Sub Abrir(dto As CuentaDto, titulo As String)
        Using d As New FichaDialog(titulo, Campos(dto.Id = 0), DtoMapper.ADiccionario(dto),
            Sub(v)
                DtoMapper.Aplicar(dto, v)
                Svc.Cuentas.Guardar(dto)
            End Sub, "Plan de cuentas de " & Ctx.Empresa.RazonSocial, 700)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Nuevo()
        Abrir(New CuentaDto(), "Nueva cuenta")
    End Sub

    Private Sub NuevaSubcuenta()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then
            Msg.Aviso("Seleccione la cuenta padre.")
            Return
        End If
        Dim cod As String = f.GetS("Codigo")
        Dim hijos As List(Of String) = Ctx.Cuentas().Rows.Cast(Of DataRow)().Where(Function(r) r.GetI("PadreId") = f.GetI("Id")).Select(Function(r) r.GetS("Codigo")).ToList()
        Dim sugerido As String = cod & "."
        If hijos.Count > 0 Then
            ' continúa la numeración del último hijo (ej. 1.1.1.01.003 -> 1.1.1.01.004)
            Dim ult As String = hijos.OrderBy(Function(x) x, StringComparer.Ordinal).Last()
            Dim m As System.Text.RegularExpressions.Match = System.Text.RegularExpressions.Regex.Match(ult, "^(.*?)(\d+)$")
            If m.Success Then sugerido = m.Groups(1).Value & (ToInt(m.Groups(2).Value) + 1).ToString(New String("0"c, m.Groups(2).Value.Length))
        End If
        Abrir(New CuentaDto With {.Codigo = sugerido, .Moneda = f.GetS("Moneda"), .Ajustable = f.GetF("Ajustable")}, "Nueva subcuenta de " & cod & " " & f.GetS("Nombre"))
        Refrescar()
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Dim c As New CuentaDto With {.Id = fila.GetI("Id"), .Codigo = fila.GetS("Codigo"), .Nombre = fila.GetS("Nombre"), .Moneda = fila.GetS("Moneda"), .Ajustable = fila.GetF("Ajustable"),
            .Presupuestable = fila.GetF("Presupuestable"), .CostoTipo = fila.GetS("CostoTipo"), .EsBanco = fila.GetF("EsBanco"), .EsMovimiento = fila.GetF("EsMovimiento"), .Activa = fila.GetF("Activa")}
        Abrir(c, "Modificar cuenta")
    End Sub

    Protected Overrides Sub Eliminar(fila As DataRow)
        Svc.Cuentas.Eliminar(fila.GetI("Id"))
    End Sub

    Private Sub Importar()
        Using d As New OpenFileDialog()
            d.Title = "Importar plan de cuentas"
            d.Filter = "Excel o CSV (*.xlsx;*.csv)|*.xlsx;*.csv"
            If d.ShowDialog() <> DialogResult.OK Then Return
            Dim lineas As New List(Of String)
            Try
                If d.FileName.EndsWith(".csv", StringComparison.OrdinalIgnoreCase) Then
                    For Each l As String In File.ReadAllLines(d.FileName, System.Text.Encoding.UTF8)
                        If l.Trim() <> "" AndAlso Not l.ToLowerInvariant().StartsWith("codigo") AndAlso Not l.ToLowerInvariant().StartsWith("código") Then lineas.Add(l.Replace(vbTab, ";").Replace(","c, ";"c))
                    Next
                Else
                    Using wb As New XLWorkbook(d.FileName)
                        For Each r In wb.Worksheet(1).RowsUsed()
                            Dim cod As String = r.Cell(1).GetString().Trim()
                            Dim nom As String = r.Cell(2).GetString().Trim()
                            If cod = "" OrElse nom = "" OrElse cod.ToLowerInvariant().StartsWith("c") AndAlso Not Char.IsDigit(cod(0)) Then Continue For
                            lineas.Add(cod & ";" & nom.Replace(";"c, ","c) & ";" & r.Cell(3).GetString().Trim())
                        Next
                    End Using
                End If
            Catch ex As Exception
                Msg.ErrorMsg(ex)
                Return
            End Try
            If lineas.Count = 0 Then
                Msg.Aviso("El archivo no contiene cuentas. Use las columnas: Código, Descripción y (opcional) indicadores U,A,B,F,V.")
                Return
            End If
            Dim reemplazar As Boolean = False
            If Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Comprobante") = 0 Then
                reemplazar = Msg.Confirmar("Se encontraron " & lineas.Count & " cuentas." & vbCrLf & vbCrLf & "SÍ = reemplazar todo el plan actual" & vbCrLf & "NO = agregar solo las cuentas que no existen", "Importar plan de cuentas")
            Else
                If Not Msg.Confirmar("Se agregarán las cuentas que no existen (" & lineas.Count & " en el archivo). ¿Continuar?") Then Return
            End If
            Intentar(Sub() Svc.Cuentas.ImportarPlan(lineas, reemplazar))
            Refrescar()
        End Using
    End Sub
End Class

''' <summary>Tipos de cambio del dólar y UFV por fecha (se cargan solo los días en que varían).</summary>
Public Class TipoCambioForm
    Inherits ListaForm

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Tipos de cambio y UFV"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "El sistema usa el último valor cargado hasta la fecha de cada operación. La UFV se usa para el ajuste por inflación y los activos fijos."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "CONT.TIPOCAMBIO"
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim b As Button = Tema.Boton("Cargar lista…", Tema.TipoBoton.Secundario, 112)
        Barra.Controls.Add(b)
        AddHandler b.Click, Sub(o, e) CargarLista()
        b.Enabled = Sesion.Puede("CONT.TIPOCAMBIO")
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Return Svc.TipoCambio.Listar()
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColFecha(Grid, "Fecha", "Fecha", 120)
        Tema.ColImporte(Grid, "Usd", "Dólar (Bs por US$)", 150, "N4")
        Tema.ColImporte(Grid, "Ufv", "UFV", 150, "N5")
        Tema.ColTexto(Grid, "Libre", "", 100, True)
    End Sub

    Private Function Campos() As List(Of CampoUI)
        Return New List(Of CampoUI) From {
            CampoUI.Fec("Fecha", "Fecha", True),
            CampoUI.Imp("Usd", "Dólar (Bs por US$)", False, 4),
            CampoUI.Imp("Ufv", "UFV", False, 5)}
    End Function

    Protected Overrides Sub Nuevo()
        Dim v As New Dictionary(Of String, Object) From {{"Fecha", Date.Today}, {"Usd", Svc.TipoCambio.Dolar(Date.Today)}, {"Ufv", Svc.TipoCambio.Ufv(Date.Today)}}
        Using d As New FichaDialog("Tipo de cambio y UFV", Campos(), v, Sub(x) Svc.TipoCambio.Guardar(ToDate(x("Fecha")), ToDec(x("Usd")), ToDec(x("Ufv"))), "Si ya existe la fecha, se actualiza.", 560)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Dim v As New Dictionary(Of String, Object) From {{"Fecha", fila.GetDt("Fecha")}, {"Usd", fila.GetD("Usd")}, {"Ufv", fila.GetD("Ufv")}}
        Using d As New FichaDialog("Tipo de cambio y UFV", Campos(), v, Sub(x) Svc.TipoCambio.Guardar(ToDate(x("Fecha")), ToDec(x("Usd")), ToDec(x("Ufv"))), "", 560)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Eliminar(fila As DataRow)
        Svc.TipoCambio.Eliminar(fila.GetDt("Fecha"))
    End Sub

    Private Sub CargarLista()
        Using f As New Form()
            Tema.Aplicar(f)
            f.Text = "Cargar tipos de cambio / UFV en bloque"
            f.StartPosition = FormStartPosition.CenterParent
            f.ClientSize = New Size(620, 440)
            f.FormBorderStyle = FormBorderStyle.FixedDialog
            f.MaximizeBox = False
            f.MinimizeBox = False
            Dim l As New Label() With {.Text = "Pegue una línea por fecha:  dd/MM/aaaa  valor-dólar  valor-UFV   (separados por espacio, tabulador o ;)" & vbCrLf & "Ejemplo:   15/01/2025   6.96   2.57410   ·   Deje en 0 el valor que no desea cambiar.", .AutoSize = False, .Location = New Point(14, 10), .Size = New Size(590, 44)}
            Dim t As New TextBox() With {.Multiline = True, .ScrollBars = ScrollBars.Both, .Location = New Point(14, 60), .Size = New Size(590, 320), .WordWrap = False, .Font = New Font("Consolas", 10.0F)}
            Dim ok As Button = Tema.Boton("Cargar", Tema.TipoBoton.Primario, 110)
            ok.Location = New Point(384, 392)
            Dim cancel As Button = Tema.Boton("Cancelar")
            cancel.Location = New Point(504, 392)
            cancel.Width = 100
            cancel.DialogResult = DialogResult.Cancel
            f.Controls.AddRange({l, t, ok, cancel})
            f.CancelButton = cancel
            AddHandler ok.Click, Sub(o, e)
                                     Dim n As Integer = 0
                                     Dim err As New List(Of String)
                                     Dim tc As New TipoCambioService(Ctx)
                                     For Each linea As String In t.Lines
                                         If linea.Trim() = "" Then Continue For
                                         Dim p As String() = linea.Split({" "c, vbTab(0), ";"c}, StringSplitOptions.RemoveEmptyEntries)
                                         Dim fecha As Date
                                         Dim usd As Decimal, ufv As Decimal
                                         If p.Length < 2 OrElse Not Date.TryParseExact(p(0), {"dd/MM/yyyy", "d/M/yyyy", "yyyy-MM-dd"}, Nothing, Globalization.DateTimeStyles.None, fecha) OrElse Not Numeros.Parse(p(1), usd) Then
                                             err.Add(linea)
                                             Continue For
                                         End If
                                         If p.Length > 2 Then Numeros.Parse(p(2), ufv)
                                         Try
                                             Dim actual As Decimal = tc.Dolar(fecha), actualU As Decimal = tc.Ufv(fecha)
                                             tc.Guardar(fecha, If(usd > 0D, usd, actual), If(ufv > 0D, ufv, actualU))
                                             n += 1
                                         Catch ex As Exception
                                             err.Add(linea & "  → " & ex.Message)
                                         End Try
                                     Next
                                     Msg.Info(n & " fecha(s) cargadas." & If(err.Count > 0, vbCrLf & vbCrLf & "No se pudieron leer " & err.Count & " línea(s):" & vbCrLf & String.Join(vbCrLf, err.Take(8)), ""))
                                     If err.Count = 0 Then f.DialogResult = DialogResult.OK
                                 End Sub
            f.ShowDialog(FindForm())
        End Using
        Refrescar()
    End Sub
End Class

''' <summary>Consulta y administración de comprobantes (buscar, abrir, imprimir, anular).</summary>
Public Class ComprobantesListaForm
    Inherits ListaForm

    Private ReadOnly _desde As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _tipo As New LookupCombo() With {.Width = 140}

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Consulta de comprobantes"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Doble clic para abrir y modificar. Los comprobantes no se eliminan: se anulan para conservar la numeración."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "CONT.MODIFICAR"
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
        Dim tipos As New List(Of KeyValuePair(Of String, String)) From {New KeyValuePair(Of String, String)("", "(Todos los tipos)")}
        For Each r As DataRow In Svc.Vouchers.Tipos().Rows
            tipos.Add(New KeyValuePair(Of String, String)(r.GetS("Codigo"), r.GetS("Nombre")))
        Next
        _tipo.CargarLista(tipos)
        Barra.Controls.AddRange({New Label() With {.Text = "Del", .AutoSize = True, .Margin = New Padding(10, 8, 4, 0)}, _desde, New Label() With {.Text = "al", .AutoSize = True, .Margin = New Padding(8, 8, 4, 0)}, _hasta, New Label() With {.Text = "Tipo", .AutoSize = True, .Margin = New Padding(10, 8, 4, 0)}, _tipo})
        AddHandler _desde.ValueChanged, Sub(o, e) Refrescar()
        AddHandler _hasta.ValueChanged, Sub(o, e) Refrescar()
        AddHandler _tipo.SelectionChangeCommitted, Sub(o, e) Refrescar()
        Dim bImp As Button = Tema.Boton("Imprimir", Tema.TipoBoton.Secundario, 84)
        Dim bAnular As Button = Tema.Boton("Anular", Tema.TipoBoton.Peligro, 80)
        Barra.Controls.AddRange({bImp, bAnular})
        AddHandler bImp.Click, Sub(o, e)
                                   Dim f As DataRow = FilaActual()
                                   If f IsNot Nothing Then Informes.Abrir("comprobante", New Dictionary(Of String, Object) From {{"id", f.GetI("Id")}}, False)
                               End Sub
        AddHandler bAnular.Click, Sub(o, e) Anular()
        bAnular.Enabled = Sesion.Puede("CONT.ANULAR")
        BotonNuevo.Text = "Nuevo"
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = Svc.Vouchers.Listar(_desde.Value.Date, _hasta.Value.Date, _tipo.ValorTexto)
        dt.Columns.Add("Comp", GetType(String))
        dt.Columns.Add("EstTxt", GetType(String))
        For Each r As DataRow In dt.Rows
            r("Comp") = r.GetS("Tipo") & "-" & r.GetS("Numero") & If(r.GetI("Mes") > 0, "/" & r.GetI("Mes").ToString("00"), "")
            r("EstTxt") = If(r.GetS("Estado") = "A", "ANULADO", "Vigente")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Comp", "Comprobante", 110)
        Tema.ColFecha(Grid, "Fecha", "Fecha")
        Tema.ColTexto(Grid, "Glosa", "Glosa", 400, True)
        Tema.ColImporte(Grid, "DebeBs", "Debe Bs", 110)
        Tema.ColImporte(Grid, "HaberBs", "Haber Bs", 110)
        Tema.ColTexto(Grid, "Origen", "Origen", 60)
        Tema.ColTexto(Grid, "EstTxt", "Estado", 80)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If fila.GetS("Estado") = "A" Then
            estilo.ForeColor = Tema.Rojo
            estilo.Font = New Font(Tema.Fuente, FontStyle.Strikeout)
        End If
    End Sub

    Protected Overrides Sub Nuevo()
        Escritorio.AbrirNueva(New ComprobanteForm(), Nothing)
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Escritorio.AbrirNueva(New ComprobanteForm(fila.GetI("Id")), Nothing)
    End Sub

    Private Sub Anular()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then Return
        If f.GetS("Estado") = "A" Then
            Msg.Info("El comprobante ya está anulado.")
            Return
        End If
        Dim motivo As String = Msg.Pedir("Motivo de la anulación del comprobante " & f.GetS("Comp") & ":", "Anular comprobante")
        If String.IsNullOrWhiteSpace(motivo) Then Return
        If Intentar(Sub() Svc.Vouchers.Anular(f.GetI("Id"), motivo)) Then Refrescar()
    End Sub
End Class
