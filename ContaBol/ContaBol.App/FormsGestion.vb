Imports System.IO
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Apertura de la siguiente gestión (como "Otra gestión" de Orion, pero también traslada existencias, cuentas corrientes y activos).</summary>
Public Module AperturaGestion

    Public Sub Ejecutar()
        If Sesion.Ctx Is Nothing Then Return
        Dim c As Contexto = Sesion.Ctx
        If Not Sesion.Puede("ADM.GESTIONES") Then
            Msg.Aviso("No tiene permiso para abrir gestiones.")
            Return
        End If
        Dim campos As New List(Of CampoUI)
        campos.Add(CampoUI.Sec("Nueva gestión"))
        Dim anio As CampoUI = CampoUI.Ent("Anio", "Año de la nueva gestión", True)
        campos.Add(anio)
        campos.Add(CampoUI.Imp("Tc", "Tipo de cambio inicial", False, 2))
        campos.Add(CampoUI.Chk("CerrarActual", "Cerrar la gestión actual al terminar", False))
        Dim v As New Dictionary(Of String, Object) From {{"Anio", c.Gestion.Anio + 1}, {"Tc", Svc.TipoCambio.Dolar(c.Gestion.FechaFin)}}
        Dim nuevaId As Integer = 0
        Dim opc As New NuevaGestionOpciones With {.MesInicio = c.Gestion.MesInicio, .CorrelativoMensual = c.Gestion.CorrelativoMensual}
        Using d As New FichaDialog("Apertura de nueva gestión", campos, v,
            Sub(x)
                opc.Anio = ToInt(x("Anio"))
                opc.TipoCambioInicial = If(ToDec(x("Tc")) > 0D, ToDec(x("Tc")), 6.96D)
                Using Msg.Cursor_(True)
                    nuevaId = Svc.Gestion.AbrirNuevaGestion(opc)
                End Using
                If ToFlag(x("CerrarActual")) Then Svc.Gestion.CerrarGestion()
            End Sub,
            "Se copian el plan de cuentas, parámetros, terceros, ítems, empleados y activos; y se generan: asiento de apertura (con el resultado de la gestión en resultados acumulados), existencias iniciales al costo promedio y saldos de clientes y proveedores.", 780)
            If d.ShowDialog() <> DialogResult.OK Then Return
        End Using
        If nuevaId <> 0 AndAlso Msg.Confirmar("La gestión " & opc.Anio & " fue creada correctamente." & vbCrLf & "¿Desea abrirla ahora?", "Apertura de gestión") Then
            Try
                Sesion.AbrirContexto(c.Empresa.Id, nuevaId)
            Catch ex As Exception
                Msg.ErrorMsg(ex)
            End Try
        End If
    End Sub
End Module

''' <summary>Ajuste por inflación (UFV), diferencia de cambio, asiento de cierre y cierre de la gestión.</summary>
Public Class CierreAjustesForm
    Inherits FormBase

    Private ReadOnly _fInfl As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _fDif As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _tcDif As New CampoImporte() With {.Width = 80}
    Private ReadOnly _fCierre As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _lblGrid As New Label()

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Cierre y ajustes"
        End Get
    End Property

    Private Function Grupo(titulo As String, alto As Integer) As GroupBox
        Dim g As New GroupBox() With {.Text = titulo, .Dock = DockStyle.Top, .Height = alto, .Padding = New Padding(14, 8, 14, 8), .Font = Tema.FuenteNegrita}
        Return g
    End Function

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Cierre y ajustes"
        Dim banner As Panel = Tema.Banner("Ajustes y cierre de gestión", "Realice los ajustes al final del período y luego el asiento de cierre. Siempre revise la vista previa antes de registrar.")
        Dim cuerpo As New Panel() With {.Dock = DockStyle.Top, .Height = 340, .BackColor = Color.White, .Padding = New Padding(14, 8, 14, 8)}
        Dim x As Integer = 14
        _fInfl.MinDate = Ctx.Gestion.FechaInicio
        _fInfl.MaxDate = Ctx.Gestion.FechaFin
        _fDif.MinDate = Ctx.Gestion.FechaInicio
        _fDif.MaxDate = Ctx.Gestion.FechaFin
        _fCierre.MinDate = Ctx.Gestion.FechaInicio
        _fCierre.MaxDate = Ctx.Gestion.FechaFin
        _fInfl.Value = Ctx.Gestion.FechaFin
        _fDif.Value = Ctx.Gestion.FechaFin
        _fCierre.Value = Ctx.Gestion.FechaFin
        _tcDif.Valor = Svc.TipoCambio.Dolar(Ctx.Gestion.FechaFin)
        ' 1. inflación
        Dim l1 As New Label() With {.Text = "1. Ajuste por inflación y tenencia de bienes (UFV)", .Font = Tema.FuenteNegrita, .ForeColor = Tema.Azul, .AutoSize = True, .Location = New Point(x, 10)}
        Dim d1 As New Label() With {.Text = "Actualiza las cuentas marcadas como 'ajustables' (inventarios, activos fijos, patrimonio...) con la variación de la UFV. Requiere la UFV de cada fecha.", .ForeColor = Tema.Gris, .AutoSize = True, .Location = New Point(x, 32)}
        Dim t1 As New Label() With {.Text = "Fecha de ajuste", .AutoSize = True, .Location = New Point(x, 62)}
        _fInfl.Location = New Point(x + 100, 58)
        Dim b1a As Button = Tema.Boton("Vista previa", Tema.TipoBoton.Secundario, 110)
        Dim b1b As Button = Tema.Boton("Registrar ajuste", Tema.TipoBoton.Primario, 130)
        b1a.Location = New Point(x + 230, 54)
        b1b.Location = New Point(x + 350, 54)
        ' 2. diferencia de cambio
        Dim l2 As New Label() With {.Text = "2. Diferencia de cambio (cuentas en moneda extranjera)", .Font = Tema.FuenteNegrita, .ForeColor = Tema.Azul, .AutoSize = True, .Location = New Point(x, 106)}
        Dim d2 As New Label() With {.Text = "Actualiza en bolivianos los saldos en dólares de activos y pasivos al tipo de cambio de cierre.", .ForeColor = Tema.Gris, .AutoSize = True, .Location = New Point(x, 128)}
        Dim t2 As New Label() With {.Text = "Fecha", .AutoSize = True, .Location = New Point(x, 158)}
        _fDif.Location = New Point(x + 50, 154)
        Dim t2b As New Label() With {.Text = "T.C. final", .AutoSize = True, .Location = New Point(x + 180, 158)}
        _tcDif.Location = New Point(x + 250, 154)
        Dim b2a As Button = Tema.Boton("Vista previa", Tema.TipoBoton.Secundario, 110)
        Dim b2b As Button = Tema.Boton("Registrar ajuste", Tema.TipoBoton.Primario, 130)
        b2a.Location = New Point(x + 350, 150)
        b2b.Location = New Point(x + 470, 150)
        ' 3. cierre
        Dim l3 As New Label() With {.Text = "3. Asiento de cierre de cuentas de resultado", .Font = Tema.FuenteNegrita, .ForeColor = Tema.Azul, .AutoSize = True, .Location = New Point(x, 202)}
        Dim d3 As New Label() With {.Text = "Salda ingresos y egresos contra 'Resultado de la gestión'. Es opcional: al abrir la nueva gestión el resultado pasa igualmente a resultados acumulados.", .ForeColor = Tema.Gris, .AutoSize = True, .Location = New Point(x, 224)}
        Dim t3 As New Label() With {.Text = "Fecha", .AutoSize = True, .Location = New Point(x, 254)}
        _fCierre.Location = New Point(x + 50, 250)
        Dim b3 As Button = Tema.Boton("Generar asiento de cierre", Tema.TipoBoton.Primario, 200)
        b3.Location = New Point(x + 180, 246)
        ' 4. cerrar gestión
        Dim b4 As Button = Tema.Boton("Cerrar la gestión (solo lectura)", Tema.TipoBoton.Exito, 230)
        b4.Location = New Point(x, 296)
        Dim b5 As Button = Tema.Boton("Reabrir gestión", Tema.TipoBoton.Secundario, 130)
        b5.Location = New Point(x + 246, 296)
        Dim b6 As Button = Tema.Boton("Abrir nueva gestión…", Tema.TipoBoton.Secundario, 170)
        b6.Location = New Point(x + 392, 296)
        cuerpo.Controls.AddRange({l1, d1, t1, _fInfl, b1a, b1b, l2, d2, t2, _fDif, t2b, _tcDif, b2a, b2b, l3, d3, t3, _fCierre, b3, b4, b5, b6})
        _lblGrid.Dock = DockStyle.Top
        _lblGrid.Height = 28
        _lblGrid.Padding = New Padding(14, 6, 0, 0)
        _lblGrid.Font = Tema.FuenteNegrita
        _lblGrid.Text = "Vista previa"
        Tema.EstiloGrid(_grid)
        Tema.ColTexto(_grid, "Codigo", "Código", 140)
        Tema.ColTexto(_grid, "Nombre", "Cuenta", 300, True)
        Tema.ColImporte(_grid, "SaldoBs", "Saldo Bs", 120)
        Tema.ColImporte(_grid, "SaldoUsd", "Saldo $us", 100)
        Tema.ColImporte(_grid, "Actualizado", "Saldo actualizado", 130)
        Tema.ColImporte(_grid, "Ajuste", "Ajuste", 120)
        Controls.Add(_grid)
        Controls.Add(_lblGrid)
        Controls.Add(cuerpo)
        Controls.Add(banner)
        AddHandler b1a.Click, Sub(o, ev) Inflacion(False)
        AddHandler b1b.Click, Sub(o, ev) Inflacion(True)
        AddHandler b2a.Click, Sub(o, ev) Cambio(False)
        AddHandler b2b.Click, Sub(o, ev) Cambio(True)
        AddHandler b3.Click, Sub(o, ev) GenerarCierre()
        AddHandler b4.Click, Sub(o, ev) CerrarGestion()
        AddHandler b5.Click, Sub(o, ev) Reabrir()
        AddHandler b6.Click, Sub(o, ev) AperturaGestion.Ejecutar()
        Dim p As Boolean = Sesion.Puede("CONT.AJUSTES") AndAlso Ctx.Gestion.Abierta
        b1b.Enabled = p
        b2b.Enabled = p
        b3.Enabled = Sesion.Puede("CONT.CIERRE") AndAlso Ctx.Gestion.Abierta
        b4.Enabled = Sesion.Puede("CONT.CIERRE") AndAlso Ctx.Gestion.Abierta
        b5.Enabled = Sesion.Usuario.EsAdmin AndAlso Not Ctx.Gestion.Abierta
        b6.Enabled = Sesion.Puede("ADM.GESTIONES")
    End Sub

    Private Sub Mostrar(r As AjusteResultado, titulo As String)
        Dim dt As New DataTable()
        dt.Columns.Add("Codigo", GetType(String))
        dt.Columns.Add("Nombre", GetType(String))
        For Each c As String In {"SaldoBs", "SaldoUsd", "Actualizado", "Ajuste"}
            dt.Columns.Add(c, GetType(Decimal))
        Next
        For Each f In r.Filas
            dt.Rows.Add(f.Codigo, f.Nombre, f.SaldoBs, f.SaldoUsd, f.Actualizado, f.Ajuste)
        Next
        _grid.DataSource = dt
        _lblGrid.Text = titulo & "  ·  " & r.Filas.Count & " cuenta(s)  ·  Efecto neto en resultados: Bs " & r.Total.ToString("N2", FormatoVal.Cultura)
    End Sub

    Private Sub Inflacion(registrar As Boolean)
        If registrar AndAlso Not Msg.Confirmar("Se generará el comprobante de ajuste por inflación al " & _fInfl.Value.ToString("dd/MM/yyyy") & ". ¿Continuar?", "Ajuste por inflación") Then Return
        Try
            Dim r As AjusteResultado
            Using Msg.Cursor_(True)
                r = Svc.Gestion.AjusteInflacion(_fInfl.Value.Date, registrar)
            End Using
            Mostrar(r, If(registrar, "Ajuste por inflación REGISTRADO", "Vista previa del ajuste por inflación"))
            If registrar Then Msg.Info("Ajuste registrado. Comprobante generado.")
            If r.Filas.Count = 0 Then Msg.Info("No hay saldos de cuentas ajustables para actualizar.")
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub Cambio(registrar As Boolean)
        If registrar AndAlso Not Msg.Confirmar("Se generará el comprobante de diferencia de cambio al T.C. " & _tcDif.Valor.ToString("0.00") & ". ¿Continuar?", "Diferencia de cambio") Then Return
        Try
            Dim r As AjusteResultado
            Using Msg.Cursor_(True)
                r = Svc.Gestion.DiferenciaCambio(_fDif.Value.Date, _tcDif.Valor, registrar)
            End Using
            Mostrar(r, If(registrar, "Diferencia de cambio REGISTRADA", "Vista previa de la diferencia de cambio"))
            If registrar Then Msg.Info("Ajuste registrado. Comprobante generado.")
            If r.Filas.Count = 0 Then Msg.Info("No hay diferencia por actualizar.")
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub GenerarCierre()
        If Not Msg.Confirmar("Se generará el asiento de cierre de las cuentas de resultado al " & _fCierre.Value.ToString("dd/MM/yyyy") & ". ¿Continuar?", "Asiento de cierre") Then Return
        Dim id As Integer
        If Intentar(Sub() id = Svc.Gestion.GenerarCierre(_fCierre.Value.Date)) Then
            If Msg.Confirmar("Asiento de cierre generado. ¿Desea verlo?") Then Escritorio.AbrirNueva(New ComprobanteForm(id), Nothing)
        End If
    End Sub

    Private Sub CerrarGestion()
        If Not Msg.Confirmar("Al cerrar la gestión " & Ctx.Gestion.Anio & " ya no se podrán registrar ni modificar operaciones (solo consultas y reportes)." & vbCrLf & "¿Desea cerrarla?", "Cerrar gestión", True) Then Return
        If Intentar(Sub() Svc.Gestion.CerrarGestion()) Then
            Msg.Info("Gestión cerrada.")
            Escritorio.Principal.ActualizarEstado()
            Escritorio.Principal.MostrarInicio()
        End If
    End Sub

    Private Sub Reabrir()
        If Intentar(Sub() Svc.Gestion.ReabrirGestion()) Then
            Msg.Info("Gestión reabierta.")
            Escritorio.Principal.ActualizarEstado()
            Escritorio.Principal.MostrarInicio()
        End If
    End Sub
End Class

''' <summary>Consolidación de varias empresas o gestiones en un balance de sumas y saldos único.</summary>
Public Class ConsolidarForm
    Inherits FormBase

    Private ReadOnly _lista As New CheckedListBox() With {.CheckOnClick = True}
    Private ReadOnly _desde As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _nivel As New NumericUpDown() With {.Minimum = 1, .Maximum = 9, .Value = 5, .Width = 60}
    Private ReadOnly _moneda As New LookupCombo() With {.Width = 160}
    Private _disp As List(Of GestionConsolidable)

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Consolidación"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Consolidación"
        Dim banner As Panel = Tema.Banner("Consolidación de empresas", "Suma los saldos por código de cuenta de las empresas/gestiones seleccionadas. Se recomienda que usen el mismo plan de cuentas.")
        Dim panel As New Panel() With {.Dock = DockStyle.Left, .Width = 420, .Padding = New Padding(14)}
        _lista.Dock = DockStyle.Fill
        panel.Controls.Add(_lista)
        panel.Controls.Add(New Label() With {.Text = "Marque las empresas y gestiones a consolidar", .Dock = DockStyle.Top, .Height = 26, .Font = Tema.FuenteNegrita})
        Dim der As New Panel() With {.Dock = DockStyle.Fill, .Padding = New Padding(20), .BackColor = Color.White}
        Dim y As Integer = 20
        Dim poner = Sub(t As String, c As Control)
                        der.Controls.Add(New Label() With {.Text = t, .AutoSize = True, .Location = New Point(20, y + 4)})
                        c.Location = New Point(180, y)
                        der.Controls.Add(c)
                        y += 38
                    End Sub
        _desde.Value = New Date(Date.Today.Year, 1, 1)
        _hasta.Value = New Date(Date.Today.Year, 12, 31)
        _moneda.CargarLista({New KeyValuePair(Of String, String)("BS", "Bolivianos"), New KeyValuePair(Of String, String)("USD", "Dólares")})
        poner("Desde", _desde)
        poner("Hasta", _hasta)
        poner("Hasta nivel de cuenta", _nivel)
        poner("Moneda", _moneda)
        Dim b As Button = Tema.Boton("Consolidar y ver reporte", Tema.TipoBoton.Primario, 220)
        b.Location = New Point(20, y + 10)
        der.Controls.Add(b)
        Controls.Add(der)
        Controls.Add(panel)
        Controls.Add(banner)
        Try
            _disp = New ConsolidacionService(Sesion.Sis, Sesion.Usuario).Disponibles()
            For Each g In _disp
                _lista.Items.Add(g.ToString())
            Next
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
        AddHandler b.Click, Sub(o, ev) Consolidar()
    End Sub

    Private Sub Consolidar()
        Dim sel As New List(Of GestionConsolidable)
        For i As Integer = 0 To _lista.Items.Count - 1
            If _lista.GetItemChecked(i) Then sel.Add(_disp(i))
        Next
        Try
            Dim usd As Boolean = _moneda.ValorTexto = "USD"
            Dim filas As List(Of BalanceRow)
            Using Msg.Cursor_(True)
                filas = New ConsolidacionService(Sesion.Sis, Sesion.Usuario).Balance(sel, _desde.Value.Date, _hasta.Value.Date, usd, CInt(_nivel.Value))
            End Using
            Dim rep As ReporteDef = BaseInforme.Nuevo(Ctx, "Balance de sumas y saldos consolidado", Rango(_desde.Value.Date, _hasta.Value.Date), If(usd, "USD", "BS"))
            rep.Empresa = "CONSOLIDADO: " & String.Join(" + ", sel.Select(Function(s) s.ToString()))
            rep.Nit = ""
            rep.Direccion = ""
            rep.Col("Código", 2.3).Col("Cuenta", 5.5).Col("Sumas Debe", 1.9, Formato.Monto).Col("Sumas Haber", 1.9, Formato.Monto).Col("Saldo Deudor", 1.9, Formato.Monto).Col("Saldo Acreedor", 1.9, Formato.Monto)
            Dim tD As Decimal, tH As Decimal, tSD As Decimal, tSH As Decimal
            For Each f In filas
                Dim r As FilaRep = rep.Fila(f.Codigo, f.Nombre, f.Debe, f.Haber, f.SaldoD, f.SaldoH)
                r.Nivel = Math.Max(0, f.Nivel - 1)
                r.Negrita = Not f.EsMovimiento
                If f.EsMovimiento Then
                    tD += f.Debe : tH += f.Haber : tSD += f.SaldoD : tSH += f.SaldoH
                End If
            Next
            rep.Total("", "TOTALES CONSOLIDADOS", tD, tH, tSD, tSH)
            Informes.Mostrar(rep)
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class

''' <summary>Migración desde un sistema Orion4 existente.</summary>
Public Module ImportarOrion

    Public Sub Ejecutar()
        If Not Sesion.Usuario.Puede("ADM.IMPORTAR") Then
            Msg.Aviso("No tiene permiso para importar datos.")
            Return
        End If
        Using d As New FolderBrowserDialog()
            d.Description = "Seleccione la carpeta de la empresa y gestión de Orion4 (la que contiene PRU.MDB, ORION.MDB e INVENT.MDB, ej. C:\orion4\GC25)."
            d.UseDescriptionForTitle = True
            If d.ShowDialog() <> DialogResult.OK Then Return
            Dim carpeta As String = d.SelectedPath
            Dim campos As New List(Of CampoUI) From {
                CampoUI.Txt("Codigo", "Código para la nueva empresa", 12, True),
                CampoUI.Lst("Correlativo", "Numeración de comprobantes en Orion", "M|Reinicia cada mes", "U|Continua en toda la gestión")}
            Dim codigo As String = Path.GetFileName(carpeta.TrimEnd(Path.DirectorySeparatorChar)).ToUpperInvariant()
            Dim res As ImportacionResultado = Nothing
            Using f As New FichaDialog("Importar desde Orion4", campos, New Dictionary(Of String, Object) From {{"Codigo", codigo}, {"Correlativo", "M"}},
                Sub(v)
                    Using Msg.Cursor_(True)
                        res = New OrionImportService(Sesion.Sis).Importar(New OrionOleDbOrigen(carpeta), ToStr(v("Codigo")), Sesion.Usuario, ToStr(v("Correlativo")) = "M")
                    End Using
                End Sub, "Carpeta: " & carpeta & vbCrLf & "Se creará una empresa nueva. Se importan plan de cuentas, comprobantes, tipos de cambio, clientes, proveedores, ítems y libros IVA.", 760)
                If f.ShowDialog() <> DialogResult.OK OrElse res Is Nothing Then Return
            End Using
            Dim resumen As String = "Importación completada." & vbCrLf & vbCrLf & "Cuentas: " & res.Cuentas & vbCrLf & "Comprobantes: " & res.Comprobantes & vbCrLf & "Clientes/proveedores: " & res.Terceros & vbCrLf & "Ítems: " & res.Items & vbCrLf & "Facturas IVA: " & res.Facturas
            If res.Avisos.Count > 0 Then resumen &= vbCrLf & vbCrLf & "Avisos (" & res.Avisos.Count & "):" & vbCrLf & String.Join(vbCrLf, res.Avisos.Take(15)) & If(res.Avisos.Count > 15, vbCrLf & "...", "")
            resumen &= vbCrLf & vbCrLf & "Las existencias de inventario no se migran: use Stock inicial. ¿Desea abrir la empresa importada ahora?"
            If Msg.Confirmar(resumen, "Importación desde Orion4") Then
                Try
                    Sesion.AbrirContexto(res.EmpresaId, res.GestionId)
                Catch ex As Exception
                    Msg.ErrorMsg(ex)
                End Try
            End If
        End Using
    End Sub
End Module

''' <summary>Utilitarios contables: cambio de cuenta, reordenar y renumerar comprobantes, recálculo de existencias y verificación.</summary>
Public Class UtilitariosForm
    Inherits FormBase

    Private ReadOnly _origen As New PickerCuenta() With {.Width = 400}
    Private ReadOnly _destino As New PickerCuenta() With {.Width = 400}
    Private ReadOnly _desde As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _tipoR As New LookupCombo() With {.Width = 180}
    Private ReadOnly _mesR As New LookupCombo() With {.Width = 180}
    Private ReadOnly _tipoN As New LookupCombo() With {.Width = 180}
    Private ReadOnly _mesN As New LookupCombo() With {.Width = 180}
    Private ReadOnly _n1 As New NumericUpDown() With {.Minimum = 1, .Maximum = 999999, .Value = 1, .Width = 90}
    Private ReadOnly _n2 As New NumericUpDown() With {.Minimum = 1, .Maximum = 999999, .Value = 2, .Width = 90}
    Private ReadOnly _txt As New TextBox() With {.Multiline = True, .ReadOnly = True, .ScrollBars = ScrollBars.Vertical, .Dock = DockStyle.Fill, .BackColor = Color.White}

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Utilitarios"
        End Get
    End Property

    Private Function Pagina(titulo As String) As TabPage
        Return New TabPage(titulo) With {.BackColor = Color.White, .Padding = New Padding(16)}
    End Function

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Utilitarios"
        Dim banner As Panel = Tema.Banner("Utilitarios contables", "Herramientas de corrección y mantenimiento. Todas las acciones quedan registradas en la auditoría.")
        Dim tabs As New TabControl() With {.Dock = DockStyle.Fill}
        Dim p1 As TabPage = Pagina("Cambio de cuenta")
        Dim p2 As TabPage = Pagina("Reordenar y renumerar")
        Dim p3 As TabPage = Pagina("Verificación y mantenimiento")
        tabs.TabPages.AddRange({p1, p2, p3})
        _desde.MinDate = Ctx.Gestion.FechaInicio
        _desde.MaxDate = Ctx.Gestion.FechaFin
        _hasta.MinDate = Ctx.Gestion.FechaInicio
        _hasta.MaxDate = Ctx.Gestion.FechaFin
        _desde.Value = Ctx.Gestion.FechaInicio
        _hasta.Value = Ctx.Gestion.FechaFin
        ' --- cambio de cuenta ---
        Dim t1 As New Label() With {.Text = "Traslada todos los movimientos de una cuenta a otra (útil cuando se contabilizó en la cuenta equivocada).", .AutoSize = True, .Location = New Point(16, 14), .ForeColor = Tema.Gris}
        p1.Controls.Add(t1)
        Dim y As Integer = 50
        Dim poner = Sub(pag As TabPage, tit As String, c As Control)
                        pag.Controls.Add(New Label() With {.Text = tit, .AutoSize = True, .Location = New Point(16, y + 4)})
                        c.Location = New Point(190, y)
                        pag.Controls.Add(c)
                        y += 38
                    End Sub
        poner(p1, "Cuenta de origen", _origen)
        poner(p1, "Cuenta de destino", _destino)
        poner(p1, "Desde la fecha", _desde)
        poner(p1, "Hasta la fecha", _hasta)
        Dim bCambio As Button = Tema.Boton("Trasladar movimientos", Tema.TipoBoton.Primario, 200)
        bCambio.Location = New Point(190, y + 6)
        p1.Controls.Add(bCambio)
        ' --- reordenar ---
        Dim tipos As New List(Of KeyValuePair(Of String, String))
        For Each r As DataRow In Svc.Vouchers.Tipos().Rows
            tipos.Add(New KeyValuePair(Of String, String)(r.GetS("Codigo"), r.GetS("Nombre")))
        Next
        Dim meses As New List(Of KeyValuePair(Of String, String))
        For i As Integer = 0 To 11
            Dim m As Date = Ctx.Gestion.FechaInicio.AddMonths(i)
            meses.Add(New KeyValuePair(Of String, String)(m.Month.ToString(), NombreMes(m.Month)))
        Next
        _tipoR.CargarLista(tipos)
        _mesR.CargarLista(meses)
        _tipoN.CargarLista(tipos)
        _mesN.CargarLista(meses)
        p2.Controls.Add(New Label() With {.Text = "Reordenar: renumera los comprobantes de un tipo (y mes) según su fecha, como 'Orden de comprobantes' de Orion. Reimprima luego los comprobantes afectados.", .AutoSize = False, .Size = New Size(760, 36), .Location = New Point(16, 12), .ForeColor = Tema.Gris})
        y = 56
        poner(p2, "Tipo de comprobante", _tipoR)
        poner(p2, "Mes", _mesR)
        Dim bOrd As Button = Tema.Boton("Reordenar por fecha", Tema.TipoBoton.Primario, 180)
        bOrd.Location = New Point(190, y)
        p2.Controls.Add(bOrd)
        y += 66
        p2.Controls.Add(New Label() With {.Text = "Cambiar numeración: intercambia los números de dos comprobantes del mismo tipo y mes.", .AutoSize = True, .Location = New Point(16, y), .ForeColor = Tema.Gris})
        y += 34
        poner(p2, "Tipo de comprobante", _tipoN)
        poner(p2, "Mes", _mesN)
        poner(p2, "Comprobante Nº", _n1)
        poner(p2, "intercambiar con Nº", _n2)
        Dim bNum As Button = Tema.Boton("Intercambiar numeración", Tema.TipoBoton.Primario, 200)
        bNum.Location = New Point(190, y)
        p2.Controls.Add(bNum)
        ' --- verificación ---
        Dim bVer As Button = Tema.Boton("Verificar contabilidad", Tema.TipoBoton.Primario, 190)
        Dim bRec As Button = Tema.Boton("Recalcular existencias y costos", Tema.TipoBoton.Secundario, 230)
        Dim bCom As Button = Tema.Boton("Compactar base de datos", Tema.TipoBoton.Secundario, 190)
        Dim barra As New FlowLayoutPanel() With {.Dock = DockStyle.Top, .Height = 46, .WrapContents = False}
        barra.Controls.AddRange({bVer, bRec, bCom})
        p3.Controls.Add(_txt)
        p3.Controls.Add(barra)
        Controls.Add(tabs)
        Controls.Add(banner)
        AddHandler bCambio.Click, Sub(o, ev)
                                      If _origen.CuentaId = 0 OrElse _destino.CuentaId = 0 Then
                                          Msg.Aviso("Seleccione la cuenta de origen y la de destino.")
                                          Return
                                      End If
                                      If Not Msg.Confirmar("Se trasladarán los movimientos de " & _origen.Text & " a " & _destino.Text & " entre las fechas indicadas. ¿Continuar?", "Cambio de cuenta", True) Then Return
                                      Dim n As Integer = 0
                                      If Intentar(Sub() n = Svc.Vouchers.CambiarCuenta(_origen.CuentaId, _destino.CuentaId, _desde.Value.Date, _hasta.Value.Date)) Then Msg.Info(n & " línea(s) trasladadas.")
                                  End Sub
        AddHandler bOrd.Click, Sub(o, ev)
                                   If Intentar(Sub() Svc.Vouchers.Reordenar(_tipoR.ValorTexto, ToInt(_mesR.ValorTexto))) Then Msg.Info("Comprobantes renumerados por fecha.")
                               End Sub
        AddHandler bNum.Click, Sub(o, ev)
                                   If Intentar(Sub() Svc.Vouchers.CambiarNumero(_tipoN.ValorTexto, ToInt(_mesN.ValorTexto), CInt(_n1.Value), CInt(_n2.Value))) Then Msg.Info("Numeración actualizada.")
                               End Sub
        AddHandler bVer.Click, Sub(o, ev) Verificar()
        AddHandler bRec.Click, Sub(o, ev)
                                   If Msg.Confirmar("Se reconstruirán existencias y costo promedio de todos los ítems desde sus movimientos. ¿Continuar?") Then
                                       If Intentar(Sub() Svc.Inventario.RecalcularTodo()) Then Msg.Info("Existencias recalculadas.")
                                   End If
                               End Sub
        AddHandler bCom.Click, Sub(o, ev) Compactar()
        bCambio.Enabled = Sesion.Puede("CONT.UTILES")
        bOrd.Enabled = bCambio.Enabled
        bNum.Enabled = bCambio.Enabled
    End Sub

    Private Sub Verificar()
        Dim sb As New System.Text.StringBuilder()
        Try
            Using Msg.Cursor_(True)
                sb.AppendLine("VERIFICACIÓN DE " & Ctx.Empresa.RazonSocial & " - Gestión " & Ctx.Gestion.Anio)
                sb.AppendLine(New String("="c, 70))
                Dim desc As Integer = Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Comprobante WHERE Estado='V' AND ABS(DebeBs - HaberBs) > 0.01")
                sb.AppendLine(If(desc = 0, "[OK] Todos los comprobantes vigentes cuadran en Bs.", "[ERROR] " & desc & " comprobante(s) descuadrados en Bs."))
                Dim bg As EstadoFinanciero = Svc.Ledger.BalanceGeneral(Ctx.Gestion.FechaFin, False, 9)
                sb.AppendLine(If(bg.Cuadra, "[OK] El balance general cuadra (Activo = Pasivo + Patrimonio).", "[ERROR] El balance no cuadra; diferencia Bs " & bg.Diferencia.ToString("N2")))
                Dim sin As Integer = Ctx.Db.ScalarInt("SELECT COUNT(*) FROM ComprobanteDet d WHERE Vigente=1 AND CuentaId NOT IN (SELECT Id FROM Cuenta)")
                sb.AppendLine(If(sin = 0, "[OK] Todas las líneas apuntan a cuentas existentes.", "[ERROR] " & sin & " línea(s) sin cuenta."))
                Dim faltan As New List(Of String)
                For Each kv In Ctx.Param.Todos()
                    If kv.Key.StartsWith("CTA_", StringComparison.Ordinal) AndAlso (kv.Value = "" OrElse Ctx.CuentaPorCodigo(kv.Value) Is Nothing) Then faltan.Add(kv.Key)
                Next
                sb.AppendLine(If(faltan.Count = 0, "[OK] Todas las cuentas de parámetros existen en el plan.", "[AVISO] Cuentas sin configurar o inexistentes: " & String.Join(", ", faltan)))
                Dim sinTc As Boolean = Not Svc.TipoCambio.Existe(Ctx.Gestion.FechaInicio)
                sb.AppendLine(If(sinTc, "[AVISO] No hay tipo de cambio cargado para el inicio de la gestión.", "[OK] Hay tipo de cambio al inicio de la gestión."))
                Dim ufv As Decimal = Svc.TipoCambio.Ufv(Ctx.Gestion.FechaFin)
                sb.AppendLine(If(ufv <= 0D, "[AVISO] No hay UFV cargada (necesaria para ajuste por inflación y activos fijos).", "[OK] Hay UFV cargada."))
                Dim negativos As Integer = Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Item WHERE Stock < 0")
                sb.AppendLine(If(negativos = 0, "[OK] No hay ítems con stock negativo.", "[AVISO] " & negativos & " ítem(s) con stock negativo."))
                Dim huer As Integer = Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Venta WHERE Estado='V' AND SaldoBs < 0") + Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Compra WHERE Estado='V' AND SaldoBs < 0")
                sb.AppendLine(If(huer = 0, "[OK] No hay documentos con saldo negativo.", "[ERROR] " & huer & " documento(s) con saldo negativo."))
                sb.AppendLine()
                sb.AppendLine("Comprobantes: " & Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Comprobante") & "   ·   Cuentas: " & Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Cuenta") & "   ·   Ítems: " & Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Item") & "   ·   Terceros: " & Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Tercero"))
                Dim fi As New FileInfo(Ctx.RutaGestion)
                sb.AppendLine("Archivo de datos: " & Ctx.RutaGestion & "  (" & Math.Round(fi.Length / 1048576.0, 1) & " MB; el límite de Access es 2.048 MB por archivo)")
            End Using
        Catch ex As Exception
            sb.AppendLine("Error en la verificación: " & ex.Message)
        End Try
        _txt.Text = sb.ToString()
    End Sub

    Private Sub Compactar()
        If Not Sesion.Usuario.EsAdmin Then
            Msg.Aviso("Solo el administrador puede compactar la base de datos.")
            Return
        End If
        If Not Msg.Confirmar("Se cerrará la gestión activa, se compactará y reparará su archivo de datos y se volverá a abrir." & vbCrLf & "Se recomienda tener una copia de seguridad reciente. ¿Continuar?", "Compactar base de datos") Then Return
        Dim emp As Integer = Ctx.Empresa.Id, ges As Integer = Ctx.Gestion.Id, ruta As String = Ctx.RutaGestion
        Dim principal As MainForm = Escritorio.Principal
        principal.BeginInvoke(Sub()
                                  Try
                                      Using Msg.Cursor_(True)
                                          principal.CerrarTodas()
                                          Sesion.CerrarContexto()
                                          Sesion.Sis.Provider.Compact(ruta)
                                          Sesion.AbrirContexto(emp, ges)
                                      End Using
                                      Msg.Info("Base de datos compactada correctamente.")
                                  Catch ex As Exception
                                      Msg.ErrorMsg(ex)
                                      Try
                                          If Sesion.Ctx Is Nothing Then Sesion.AbrirContexto(emp, ges)
                                      Catch
                                      End Try
                                  End Try
                              End Sub)
    End Sub
End Class

''' <summary>Centro de reportes: todos los informes del sistema (PDF/Excel) agrupados por módulo.</summary>
Public Class CentroReportesForm
    Inherits FormBase

    Private ReadOnly _arbol As New TreeView()
    Private ReadOnly _busca As New TextBox()
    Private ReadOnly _lblDesc As New Label()
    Private ReadOnly _btnAbrir As Button = Tema.Boton("Abrir reporte", Tema.TipoBoton.Primario, 150)

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Centro de reportes"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Centro de reportes"
        Dim banner As Panel = Tema.Banner("Centro de reportes", "Todos los informes del sistema. Cada uno se puede ver en pantalla, guardar en PDF, exportar a Excel o imprimir.")
        Dim top As New Panel() With {.Dock = DockStyle.Top, .Height = 44, .Padding = New Padding(14, 8, 14, 4)}
        top.Controls.Add(_busca)
        top.Controls.Add(New Label() With {.Text = "Buscar reporte:", .Dock = DockStyle.Left, .Width = 100, .TextAlign = ContentAlignment.MiddleLeft})
        _busca.Dock = DockStyle.Fill
        Dim der As New Panel() With {.Dock = DockStyle.Right, .Width = 340, .BackColor = Color.White, .Padding = New Padding(18)}
        _lblDesc.Dock = DockStyle.Top
        _lblDesc.Height = 150
        _lblDesc.Font = Tema.Fuente
        _btnAbrir.Dock = DockStyle.Top
        _btnAbrir.Height = 40
        der.Controls.Add(_btnAbrir)
        der.Controls.Add(New Panel() With {.Dock = DockStyle.Top, .Height = 12})
        der.Controls.Add(_lblDesc)
        _arbol.Dock = DockStyle.Fill
        _arbol.Font = New Font("Segoe UI", 10.5F)
        _arbol.ItemHeight = 26
        _arbol.ShowLines = False
        _arbol.FullRowSelect = True
        _arbol.HideSelection = False
        Controls.Add(_arbol)
        Controls.Add(der)
        Controls.Add(top)
        Controls.Add(banner)
        AddHandler _busca.TextChanged, Sub(o, ev) Llenar()
        AddHandler _arbol.AfterSelect, Sub(o, ev) Describir()
        AddHandler _arbol.NodeMouseDoubleClick, Sub(o, ev) Abrir()
        AddHandler _btnAbrir.Click, Sub(o, ev) Abrir()
        AddHandler _arbol.KeyDown, Sub(o, ev)
                                       If ev.KeyCode = Keys.Enter Then
                                           ev.Handled = True
                                           Abrir()
                                       End If
                                   End Sub
        Llenar()
    End Sub

    Private Sub Llenar()
        _arbol.BeginUpdate()
        _arbol.Nodes.Clear()
        Dim f As String = _busca.Text.Trim().ToLowerInvariant()
        For Each g In Catalogo.Todos.Where(Function(r) Sesion.Puede(r.Permiso) AndAlso (f = "" OrElse r.Titulo.ToLowerInvariant().Contains(f) OrElse r.Modulo.ToLowerInvariant().Contains(f))).GroupBy(Function(r) r.Modulo)
            Dim n As TreeNode = _arbol.Nodes.Add(g.Key)
            n.NodeFont = Tema.FuenteNegrita
            For Each r In g.OrderBy(Function(x) x.Titulo)
                Dim h As TreeNode = n.Nodes.Add(r.Titulo)
                h.Tag = r.Id
            Next
            n.Expand()
        Next
        _arbol.EndUpdate()
        Describir()
    End Sub

    Private Sub Describir()
        Dim id As String = TryCast(_arbol.SelectedNode?.Tag, String)
        If id Is Nothing Then
            _lblDesc.Text = "Seleccione un reporte de la lista."
            _btnAbrir.Enabled = False
            Return
        End If
        Dim r As ReporteCat = Catalogo.Buscar(id)
        _lblDesc.Text = r.Titulo & vbCrLf & vbCrLf & "Módulo: " & r.Modulo & vbCrLf & If(r.Params.Count > 0, "Parámetros: " & String.Join(", ", r.Params.Select(Function(p) p.Titulo)), "Sin parámetros.")
        _btnAbrir.Enabled = True
    End Sub

    Private Sub Abrir()
        Dim id As String = TryCast(_arbol.SelectedNode?.Tag, String)
        If id IsNot Nothing Then Informes.Abrir(id)
    End Sub
End Class

''' <summary>Información del sistema.</summary>
Public Class AcercaDeForm
    Inherits Form

    Public Sub New()
        Tema.Aplicar(Me)
        Text = "Acerca de ContaBol"
        FormBorderStyle = FormBorderStyle.FixedDialog
        StartPosition = FormStartPosition.CenterParent
        MaximizeBox = False
        MinimizeBox = False
        ShowInTaskbar = False
        ClientSize = New Size(620, 400)
        BackColor = Color.White
        Dim logo As Image = Escritorio.Logo()
        If logo IsNot Nothing Then Controls.Add(New PictureBox() With {.Image = logo, .SizeMode = PictureBoxSizeMode.Zoom, .Size = New Size(84, 84), .Location = New Point(28, 28)})
        Controls.Add(New Label() With {.Text = "ContaBol", .Font = New Font("Segoe UI Semibold", 24.0F), .ForeColor = Tema.Azul, .AutoSize = True, .Location = New Point(128, 24)})
        Controls.Add(New Label() With {.Text = "Sistema Contable Integrado · Versión 1.0", .Font = Tema.FuenteGrande, .ForeColor = Tema.Gris, .AutoSize = True, .Location = New Point(130, 72)})
        Dim texto As String = "Sistema contable comercial y de costos conforme a la normativa contable e impositiva de Bolivia (PCGA, IVA 13%, IT 3%, libros de compras y ventas, RC-IVA, ajuste por inflación con UFV)." & vbCrLf & vbCrLf &
            "• Multiempresa y multigestión: una base de datos Access independiente por empresa y gestión." & vbCrLf &
            "• Contabilidad bimonetaria (Bs/US$), inventarios con costo promedio y vencimientos, activos fijos, planillas y producción." & vbCrLf &
            "• Reportes en PDF y Excel en todos los módulos." & vbCrLf &
            "• Copias de seguridad verificables y recuperación." & vbCrLf & vbCrLf &
            "Datos: " & Sesion.Config.RutaDatos & vbCrLf & "Motor: " & Sesion.Sis.Provider.Nombre & vbCrLf & "Usuario: " & Sesion.Usuario.Nombre & vbCrLf & "Sistema operativo: " & Environment.OSVersion.VersionString
        Controls.Add(New Label() With {.Text = texto, .Location = New Point(28, 132), .Size = New Size(570, 220), .Font = Tema.Fuente})
        Dim ok As Button = Tema.Boton("Cerrar", Tema.TipoBoton.Primario, 100)
        ok.Location = New Point(500, 356)
        ok.DialogResult = DialogResult.OK
        Controls.Add(ok)
        AcceptButton = ok
    End Sub
End Class
