Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Registro de activos fijos con cálculo de depreciación por grupo y actualización por UFV.</summary>
Public Class ActivosForm
    Inherits ListaForm

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Activos fijos"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Al elegir el grupo se asignan automáticamente el porcentaje de depreciación (D.S. 24051) y las cuentas contables."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "AF.ACTIVOS"
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim bDep As Button = Tema.Boton("Depreciación…", Tema.TipoBoton.Secundario, 112)
        Dim bBaja As Button = Tema.Boton("Dar de baja", Tema.TipoBoton.Peligro, 100)
        Dim bGr As Button = Tema.Boton("Grupos…", Tema.TipoBoton.Secundario, 84)
        Barra.Controls.AddRange({bDep, bBaja, bGr})
        AddHandler bDep.Click, Sub(o, e) Escritorio.Abrir(Of DepreciacionForm)()
        AddHandler bBaja.Click, Sub(o, e) Baja()
        AddHandler bGr.Click, Sub(o, e) Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.GruposActivo()), "Cat_GrupoActivo")
        bDep.Enabled = Sesion.Puede("AF.DEPRECIAR")
        bBaja.Enabled = Sesion.Puede("AF.ACTIVOS")
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Dim dt As DataTable = Svc.ActivosFijos.Listar(True)
        dt.Columns.Add("Grupo", GetType(String))
        dt.Columns.Add("EstTxt", GetType(String))
        Dim g As New Dictionary(Of Integer, String)
        For Each r As DataRow In Svc.ActivosFijos.Grupos().Rows
            g(r.GetI("Id")) = r.GetS("Nombre")
        Next
        For Each r As DataRow In dt.Rows
            r("Grupo") = If(g.ContainsKey(r.GetI("GrupoId")), g(r.GetI("GrupoId")), "")
            r("EstTxt") = If(r.GetS("Estado") = "A", "Vigente", "Baja")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Codigo", "Código", 100)
        Tema.ColTexto(Grid, "Nombre", "Activo", 260, True)
        Tema.ColTexto(Grid, "Grupo", "Grupo", 170)
        Tema.ColFecha(Grid, "FechaAlta", "Alta")
        Tema.ColImporte(Grid, "ValorOriginal", "Valor original", 110)
        Tema.ColImporte(Grid, "PorcDep", "% Dep.", 64)
        Tema.ColTexto(Grid, "Ubicacion", "Ubicación", 130)
        Tema.ColTexto(Grid, "EstTxt", "Estado", 66)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If fila.GetS("Estado") <> "A" Then estilo.ForeColor = Tema.Gris
    End Sub

    Private Function Campos(nuevo As Boolean) As List(Of CampoUI)
        Dim l As New List(Of CampoUI)
        l.Add(CampoUI.Sec("Identificación"))
        l.Add(CampoUI.Txt("Codigo", "Código", 20, True))
        l.Add(CampoUI.Lk("GrupoId", "Grupo de activo", Function() Svc.ActivosFijos.Grupos(), "Nombre", True))
        l.Add(CampoUI.Txt("Nombre", "Nombre / descripción", 150, True, True))
        l.Add(CampoUI.Txt("Serie", "Nº de serie", 40))
        l.Add(CampoUI.Txt("Marca", "Marca / modelo", 40))
        l.Add(CampoUI.Txt("Ubicacion", "Ubicación", 80))
        l.Add(CampoUI.Txt("Responsable", "Responsable", 80))
        l.Add(CampoUI.Sec("Valores"))
        l.Add(CampoUI.Fec("FechaAlta", "Fecha de alta (compra)"))
        l.Add(CampoUI.Imp("ValorOriginal", "Valor de compra (Bs)", True))
        l.Add(CampoUI.Cant("PorcDep", "% depreciación anual (vacío = del grupo)", 2))
        l.Add(CampoUI.Cant("UfvAlta", "UFV a la fecha de alta (vacío = automática)", 5))
        l.Add(CampoUI.Imp("DepAcumInicial", "Depreciación acumulada inicial"))
        l.Add(CampoUI.Imp("ValorResidual", "Valor residual"))
        l.Add(CampoUI.Txt("Factura", "Factura de compra Nº", 30))
        l.Add(CampoUI.Sec("Cuentas contables (vacías = las del grupo)"))
        l.Add(CampoUI.Cta("CuentaActivoId", "Cuenta del activo"))
        l.Add(CampoUI.Cta("CuentaDepAcumId", "Depreciación acumulada"))
        l.Add(CampoUI.Cta("CuentaGastoId", "Gasto de depreciación"))
        If nuevo Then
            l.Add(CampoUI.Sec("Asiento de alta"))
            l.Add(CampoUI.Chk("GenerarAsiento", "Generar asiento (si fue comprado en esta gestión)", True))
            l.Add(CampoUI.Cta("Contra", "Contracuenta (caja, banco, proveedores)"))
        End If
        l.Add(CampoUI.Memo("Observacion", "Observaciones", 255))
        Return l
    End Function

    Private Sub Mostrar(id As Integer)
        Dim a As ActivoDto = If(id = 0, New ActivoDto With {.FechaAlta = If(Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin, Date.Today, Ctx.Gestion.FechaInicio)}, Svc.ActivosFijos.Obtener(id))
        Dim ini As Dictionary(Of String, Object) = DtoMapper.ADiccionario(a)
        If id = 0 Then
            ini("GenerarAsiento") = True
            ini("Contra") = Ctx.CuentaParamOpcional(ParamKeys.CtaCaja)
        End If
        Using d As New FichaDialog(If(id = 0, "Nuevo activo fijo", "Modificar activo fijo"), Campos(id = 0), ini,
            Sub(v)
                DtoMapper.Aplicar(a, v)
                Dim g As DataRow = Svc.ActivosFijos.Grupos().Rows.Cast(Of DataRow)().FirstOrDefault(Function(r) r.GetI("Id") = a.GrupoId)
                If g IsNot Nothing Then
                    If a.PorcDep = 0D Then a.PorcDep = g.GetD("PorcDep")
                    If a.CuentaActivoId = 0 Then a.CuentaActivoId = g.GetI("CuentaActivoId")
                    If a.CuentaDepAcumId = 0 Then a.CuentaDepAcumId = g.GetI("CuentaDepAcumId")
                    If a.CuentaGastoId = 0 Then a.CuentaGastoId = g.GetI("CuentaGastoId")
                End If
                Dim gen As Boolean = id = 0 AndAlso ToFlag(v("GenerarAsiento"))
                Svc.ActivosFijos.Guardar(a, gen, If(id = 0, ToInt(v("Contra")), 0))
            End Sub, "", 860)
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
        Svc.ActivosFijos.Eliminar(fila.GetI("Id"))
    End Sub

    Private Sub Baja()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then Return
        If f.GetS("Estado") <> "A" Then
            Msg.Info("El activo ya fue dado de baja.")
            Return
        End If
        Dim campos As New List(Of CampoUI) From {CampoUI.Fec("Fecha", "Fecha de baja"), CampoUI.Txt("Motivo", "Motivo (venta, obsolescencia, siniestro...)", 100, True, True), CampoUI.Chk("Asiento", "Generar asiento de baja", True)}
        Using d As New FichaDialog("Baja del activo " & f.GetS("Codigo"), campos, New Dictionary(Of String, Object) From {{"Fecha", Date.Today}, {"Asiento", True}},
            Sub(v) Svc.ActivosFijos.Baja(f.GetI("Id"), ToDate(v("Fecha")), ToStr(v("Motivo")), ToFlag(v("Asiento"))), "El costo y la depreciación acumulada se retiran; el valor neto se carga a pérdida por baja.", 640)
            d.ShowDialog(FindForm())
        End Using
        Refrescar()
    End Sub
End Class

''' <summary>Depreciación mensual de activos fijos con vista previa y asiento automático.</summary>
Public Class DepreciacionForm
    Inherits FormBase

    Private ReadOnly _mes As New LookupCombo() With {.Width = 220}
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _lblInfo As New Label()
    Private _ultimo As DepreciacionResultado

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Depreciación"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Depreciación de activos fijos"
        Dim banner As Panel = Tema.Banner("Depreciación y actualización de activos fijos", "Calcula la depreciación del mes por línea recta sobre el valor actualizado con UFV y genera el comprobante de traspaso.")
        Dim barra As New FlowLayoutPanel() With {.Dock = DockStyle.Top, .Height = 48, .Padding = New Padding(14, 8, 14, 4), .WrapContents = False}
        Dim meses As New List(Of KeyValuePair(Of String, String))
        For i As Integer = 0 To 11
            Dim m As Date = Ctx.Gestion.FechaInicio.AddMonths(i)
            meses.Add(New KeyValuePair(Of String, String)(m.ToString("yyyy-MM"), NombreMes(m.Month) & " " & m.Year))
        Next
        _mes.CargarLista(meses)
        Dim hoy As Date = If(Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin, Date.Today, Ctx.Gestion.FechaFin)
        _mes.ValorTexto = hoy.ToString("yyyy-MM")
        Dim bCalc As Button = Tema.Boton("Calcular (vista previa)", Tema.TipoBoton.Secundario, 170)
        Dim bReg As Button = Tema.Boton("Registrar y contabilizar", Tema.TipoBoton.Primario, 170)
        Dim bAnu As Button = Tema.Boton("Anular último período", Tema.TipoBoton.Peligro, 160)
        Dim bImp As Button = Tema.Boton("Imprimir", Tema.TipoBoton.Secundario, 84)
        barra.Controls.Add(New Label() With {.Text = "Período:", .AutoSize = True, .Margin = New Padding(0, 8, 6, 0)})
        barra.Controls.AddRange({_mes, bCalc, bReg, bAnu, bImp})
        _lblInfo.Dock = DockStyle.Bottom
        _lblInfo.Height = 28
        _lblInfo.Padding = New Padding(14, 6, 0, 0)
        _lblInfo.ForeColor = Tema.Gris
        Tema.EstiloGrid(_grid)
        Tema.ColTexto(_grid, "Codigo", "Código", 90)
        Tema.ColTexto(_grid, "Nombre", "Activo", 260, True)
        Tema.ColImporte(_grid, "ValorAnterior", "Valor anterior", 105)
        Tema.ColImporte(_grid, "ActualizaValor", "Actualiz. valor", 100)
        Tema.ColImporte(_grid, "ValorActualizado", "Valor actualizado", 110)
        Tema.ColImporte(_grid, "ActualizaDep", "Actualiz. dep.", 95)
        Tema.ColImporte(_grid, "DepPeriodo", "Dep. del mes", 100)
        Tema.ColImporte(_grid, "DepAcum", "Dep. acumulada", 110)
        Tema.ColImporte(_grid, "ValorNeto", "Valor neto", 105)
        Controls.Add(_grid)
        Controls.Add(_lblInfo)
        Controls.Add(barra)
        Controls.Add(banner)
        AddHandler bCalc.Click, Sub(o, ev) Calcular(False)
        AddHandler bReg.Click, Sub(o, ev) Calcular(True)
        AddHandler bAnu.Click, Sub(o, ev) Anular()
        AddHandler bImp.Click, Sub(o, ev) Informes.Abrir("depreciacion_periodo", New Dictionary(Of String, Object) From {{"mes", ToInt(_mes.ValorTexto.Substring(5))}}, False)
        bReg.Enabled = Sesion.Puede("AF.DEPRECIAR") AndAlso Ctx.Gestion.Abierta
        bAnu.Enabled = bReg.Enabled
    End Sub

    Private Sub Calcular(registrar As Boolean)
        Dim fecha As Date = New Date(ToInt(_mes.ValorTexto.Substring(0, 4)), ToInt(_mes.ValorTexto.Substring(5)), 1)
        If registrar AndAlso Not Msg.Confirmar("Se registrará la depreciación de " & NombreMes(fecha.Month) & " " & fecha.Year & " y se generará el asiento contable. ¿Continuar?", "Registrar depreciación") Then Return
        Try
            Using Msg.Cursor_(True)
                _ultimo = Svc.ActivosFijos.Depreciar(fecha, registrar)
            End Using
        Catch ex As Exception
            Msg.ErrorMsg(ex)
            Return
        End Try
        Dim dt As New DataTable()
        For Each c As String In {"Codigo", "Nombre"}
            dt.Columns.Add(c, GetType(String))
        Next
        For Each c As String In {"ValorAnterior", "ActualizaValor", "ValorActualizado", "ActualizaDep", "DepPeriodo", "DepAcum", "ValorNeto"}
            dt.Columns.Add(c, GetType(Decimal))
        Next
        For Each f In _ultimo.Filas
            dt.Rows.Add(f.Codigo, f.Nombre, f.ValorAnterior, f.ActualizaValor, f.ValorActualizado, f.ActualizaDep, f.DepPeriodo, f.DepAcum, f.ValorNeto)
        Next
        _grid.DataSource = dt
        If _ultimo.Filas.Count = 0 Then
            _lblInfo.Text = "No hay activos pendientes de depreciar en este período (ya fue registrado o no hay activos vigentes)."
        Else
            _lblInfo.Text = _ultimo.Filas.Count & " activo(s). Depreciación del mes: Bs " & _ultimo.Filas.Sum(Function(x) x.DepPeriodo).ToString("N2", FormatoVal.Cultura) & If(_ultimo.UfvFaltante, "   ·   ATENCIÓN: falta la UFV del cierre de mes; no se actualizó el valor.", "") & If(registrar, "   ·   REGISTRADO", "   ·   vista previa")
        End If
    End Sub

    Private Sub Anular()
        If Not Msg.Confirmar("Se anulará la depreciación del período " & _mes.Text & " (debe ser el último registrado) y su comprobante. ¿Continuar?", "Anular depreciación", True) Then Return
        If Intentar(Sub() Svc.ActivosFijos.AnularDepreciacion(_mes.ValorTexto)) Then
            Msg.Info("Depreciación anulada.")
            Calcular(False)
        End If
    End Sub
End Class

''' <summary>Empleados (dependientes) para planillas.</summary>
Public Class EmpleadosForm
    Inherits ListaForm

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Empleados"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "La fecha de ingreso determina automáticamente el bono de antigüedad en la planilla."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "RH.EMPLEADOS"
        End Get
    End Property

    Protected Overrides Function CargarDatos() As DataTable
        Return Svc.Planillas.ListarEmpleados()
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Item", "Ítem", 60)
        Tema.ColTexto(Grid, "Nombre", "Apellidos y nombres", 280, True)
        Tema.ColTexto(Grid, "Ci", "C.I.", 100)
        Tema.ColTexto(Grid, "Cargo", "Cargo", 160)
        Tema.ColFecha(Grid, "FechaIngreso", "Ingreso")
        Tema.ColImporte(Grid, "Haber", "Haber básico", 110)
        Tema.ColTexto(Grid, "Estado", "Est.", 40)
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If fila.GetS("Estado") <> "A" Then estilo.ForeColor = Tema.Gris
    End Sub

    Private Function Campos() As List(Of CampoUI)
        Dim l As New List(Of CampoUI)
        l.Add(CampoUI.Sec("Datos personales"))
        l.Add(CampoUI.Txt("Nombre", "Apellidos y nombres", 120, True, True))
        l.Add(CampoUI.Txt("Ci", "Cédula de identidad", 20))
        l.Add(CampoUI.Txt("Item", "Ítem / código", 10))
        l.Add(CampoUI.Fec("FechaNac", "Fecha de nacimiento", False))
        l.Add(CampoUI.Txt("Telefono", "Teléfono", 40))
        l.Add(CampoUI.Txt("Email", "Correo electrónico", 100))
        l.Add(CampoUI.Txt("Direccion", "Dirección", 150, False, True))
        l.Add(CampoUI.Sec("Datos laborales"))
        l.Add(CampoUI.Txt("Cargo", "Cargo", 60))
        l.Add(CampoUI.Fec("FechaIngreso", "Fecha de ingreso"))
        l.Add(CampoUI.Imp("Haber", "Haber básico mensual (Bs)", True))
        l.Add(CampoUI.Lst("Estado", "Estado", "A|Activo", "R|Retirado"))
        l.Add(CampoUI.Fec("FechaRetiro", "Fecha de retiro", False))
        l.Add(CampoUI.Chk("Eventual", "Personal eventual"))
        l.Add(CampoUI.Lk("CentroCostoId", "Centro de costo", Function() Ctx.Db.Query("SELECT Id, Nombre FROM CentroCosto WHERE Activo=1 ORDER BY Nombre")))
        l.Add(CampoUI.Sec("Seguridad social y pago"))
        l.Add(CampoUI.Txt("Nua", "NUA / CUA (AFP)", 20))
        l.Add(CampoUI.Txt("Afp", "AFP", 20))
        l.Add(CampoUI.Txt("Banco", "Banco", 40))
        l.Add(CampoUI.Txt("CuentaBanco", "Cuenta bancaria", 30))
        Return l
    End Function

    Private Sub Mostrar(id As Integer)
        Dim e As EmpleadoDto = If(id = 0, New EmpleadoDto(), Svc.Planillas.ObtenerEmpleado(id))
        Using d As New FichaDialog(If(id = 0, "Nuevo empleado", "Modificar empleado"), Campos(), DtoMapper.ADiccionario(e),
            Sub(v)
                DtoMapper.Aplicar(e, v)
                Svc.Planillas.GuardarEmpleado(e)
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
        Svc.Planillas.EliminarEmpleado(fila.GetI("Id"))
    End Sub
End Class

''' <summary>Planilla mensual de sueldos: cálculo automático de bono de antigüedad, AFP, RC-IVA y líquido pagable.</summary>
Public Class PlanillaForm
    Inherits FormBase

    Private ReadOnly _mes As New LookupCombo() With {.Width = 220}
    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _lblEstado As New Label()
    Private ReadOnly _lblTotales As New Label()
    Private _periodo As PlanillaPeriodoInfo
    Private _filas As New List(Of FilaPlanilla)
    Private _bCerrar As Button
    Private _bReabrir As Button
    Private _cargando As Boolean

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Planilla de sueldos"
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Planilla de sueldos"
        Dim banner As Panel = Tema.Banner("Planilla de sueldos y salarios", "Los conceptos se calculan solos: complete días, horas extras, bonos, facturas F-110 y descuentos. Al cerrar se genera el comprobante.")
        Dim barra As New FlowLayoutPanel() With {.Dock = DockStyle.Top, .Height = 48, .Padding = New Padding(14, 8, 14, 4), .WrapContents = False}
        Dim meses As New List(Of KeyValuePair(Of String, String))
        For i As Integer = 0 To 11
            Dim m As Date = Ctx.Gestion.FechaInicio.AddMonths(i)
            meses.Add(New KeyValuePair(Of String, String)(m.ToString("yyyy-MM"), NombreMes(m.Month) & " " & m.Year))
        Next
        _mes.CargarLista(meses)
        Dim hoy As Date = If(Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin, Date.Today, Ctx.Gestion.FechaFin)
        _mes.ValorTexto = hoy.ToString("yyyy-MM")
        Dim bAbrir As Button = Tema.Boton("Abrir / generar", Tema.TipoBoton.Primario, 130)
        _bCerrar = Tema.Boton("Cerrar y contabilizar", Tema.TipoBoton.Exito, 160)
        _bReabrir = Tema.Boton("Reabrir", Tema.TipoBoton.Secundario, 80)
        Dim bImp As Button = Tema.Boton("Planilla PDF", Tema.TipoBoton.Secundario, 100)
        Dim bBol As Button = Tema.Boton("Boletas", Tema.TipoBoton.Secundario, 80)
        Dim bRc As Button = Tema.Boton("RC-IVA", Tema.TipoBoton.Secundario, 80)
        Dim bAnt As Button = Tema.Boton("Anticipos…", Tema.TipoBoton.Secundario, 100)
        barra.Controls.Add(New Label() With {.Text = "Mes:", .AutoSize = True, .Margin = New Padding(0, 8, 6, 0)})
        barra.Controls.AddRange({_mes, bAbrir, _bCerrar, _bReabrir, bImp, bBol, bRc, bAnt})
        _lblEstado.Dock = DockStyle.Top
        _lblEstado.Height = 26
        _lblEstado.Padding = New Padding(14, 6, 0, 0)
        _lblEstado.Font = Tema.FuenteNegrita
        _lblTotales.Dock = DockStyle.Bottom
        _lblTotales.Height = 34
        _lblTotales.Padding = New Padding(14, 8, 0, 0)
        _lblTotales.BackColor = Color.White
        _lblTotales.Font = Tema.FuenteNegrita
        Tema.EstiloGrid(_grid, True)
        _grid.SelectionMode = DataGridViewSelectionMode.CellSelect
        _grid.EditMode = DataGridViewEditMode.EditOnEnter
        _grid.ColumnHeadersHeight = 44
        _grid.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing
        Tema.ColTexto(_grid, "Nombre", "Empleado", 220).ReadOnly = True
        Tema.ColImporte(_grid, "Dias", "Días", 50, "N0")
        Tema.ColImporte(_grid, "Haber", "Haber básico", 90).ReadOnly = True
        Tema.ColImporte(_grid, "BonoAntig", "Bono antig.", 85).ReadOnly = True
        Tema.ColImporte(_grid, "HorasExtras", "Horas extras", 70, "N1")
        Tema.ColImporte(_grid, "BonoProd", "Bono prod.", 80)
        Tema.ColImporte(_grid, "BonoDom", "Dominical", 80)
        Tema.ColImporte(_grid, "OtrosIngresos", "Otros ingr.", 80)
        Tema.ColImporte(_grid, "TotalGanado", "Total ganado", 95).ReadOnly = True
        Tema.ColImporte(_grid, "TotalAfp", "AFP", 80).ReadOnly = True
        Tema.ColImporte(_grid, "Facturas", "Facturas F-110", 90)
        Tema.ColImporte(_grid, "RcIvaRet", "RC-IVA", 80).ReadOnly = True
        Tema.ColImporte(_grid, "Anticipo", "Anticipos", 80)
        Tema.ColImporte(_grid, "Prestamo", "Préstamos", 80)
        Tema.ColImporte(_grid, "OtrosDesc", "Otros desc.", 80)
        Tema.ColImporte(_grid, "Liquido", "Líquido pagable", 105).ReadOnly = True
        For Each nombre As String In {"Haber", "BonoAntig", "TotalGanado", "TotalAfp", "RcIvaRet", "Liquido"}
            _grid.Columns(nombre).DefaultCellStyle.BackColor = Color.FromArgb(246, 247, 249)
        Next
        _grid.Columns("Liquido").DefaultCellStyle.Font = Tema.FuenteNegrita
        Controls.Add(_grid)
        Controls.Add(_lblTotales)
        Controls.Add(_lblEstado)
        Controls.Add(barra)
        Controls.Add(banner)
        AddHandler bAbrir.Click, Sub(o, ev) AbrirPeriodo()
        AddHandler _mes.SelectionChangeCommitted, Sub(o, ev) AbrirPeriodo()
        AddHandler _bCerrar.Click, Sub(o, ev) Cerrar()
        AddHandler _bReabrir.Click, Sub(o, ev) Reabrir()
        AddHandler bImp.Click, Sub(o, ev) Informes.Abrir("planilla_sueldos", Mes(), False)
        AddHandler bBol.Click, Sub(o, ev) Informes.Abrir("boletas_pago", Mes(), True)
        AddHandler bRc.Click, Sub(o, ev) Informes.Abrir("planilla_rciva", Mes(), False)
        AddHandler bAnt.Click, Sub(o, ev) Escritorio.AbrirNueva(New AnticiposForm(), "AnticiposForm")
        AddHandler _grid.CellEndEdit, AddressOf FinEdicion
        AddHandler _grid.CellParsing, Sub(o, ev)
                                          Dim d As Decimal
                                          If Numeros.Parse(ToStr(ev.Value), d) Then ev.Value = d Else ev.Value = 0D
                                          ev.ParsingApplied = True
                                      End Sub
        AddHandler _grid.DataError, Sub(o, ev) ev.ThrowException = False
        AbrirPeriodo()
    End Sub

    Private Function Mes() As Dictionary(Of String, Object)
        Return New Dictionary(Of String, Object) From {{"mes", ToInt(_mes.ValorTexto.Substring(5))}}
    End Function

    Private Sub AbrirPeriodo()
        Dim anio As Integer = ToInt(_mes.ValorTexto.Substring(0, 4)), mes As Integer = ToInt(_mes.ValorTexto.Substring(5))
        _periodo = Svc.Planillas.ObtenerPeriodo(anio, mes)
        If _periodo Is Nothing Then
            If Not Sesion.Puede("RH.PLANILLA") Then
                _filas = New List(Of FilaPlanilla)
                Mostrar()
                _lblEstado.Text = "No existe planilla para este mes."
                Return
            End If
            If Svc.Planillas.ListarEmpleados(True).Rows.Count = 0 Then
                Msg.Aviso("No hay empleados activos. Registre empleados en Planillas > Empleados.")
                _filas = New List(Of FilaPlanilla)
                Mostrar()
                Return
            End If
            If Not Msg.Confirmar("No existe la planilla de " & NombreMes(mes) & " " & anio & ". ¿Desea generarla con los empleados activos?", "Generar planilla") Then
                _filas = New List(Of FilaPlanilla)
                Mostrar()
                Return
            End If
            Try
                Using Msg.Cursor_(True)
                    _periodo = Svc.Planillas.AbrirPeriodo(anio, mes)
                End Using
            Catch ex As Exception
                Msg.ErrorMsg(ex)
                Return
            End Try
        End If
        _filas = Svc.Planillas.Filas(_periodo.Id)
        Mostrar()
    End Sub

    Private Sub Mostrar()
        _cargando = True
        _grid.Rows.Clear()
        For Each f In _filas
            Dim i As Integer = _grid.Rows.Add()
            Poner(_grid.Rows(i), f)
        Next
        _cargando = False
        Dim cerrada As Boolean = _periodo IsNot Nothing AndAlso _periodo.Estado = "C"
        _grid.ReadOnly = cerrada OrElse _periodo Is Nothing
        _bCerrar.Enabled = _periodo IsNot Nothing AndAlso Not cerrada AndAlso Sesion.Puede("RH.PLANILLA")
        _bReabrir.Enabled = cerrada AndAlso Sesion.Puede("RH.PLANILLA")
        If _periodo Is Nothing Then
            _lblEstado.Text = ""
        Else
            _lblEstado.Text = If(cerrada, "PLANILLA CERRADA y contabilizada", "Planilla abierta (borrador): edite los datos y luego ciérrela")
            _lblEstado.ForeColor = If(cerrada, Tema.Verde, Tema.Ambar)
        End If
        Totales()
    End Sub

    Private Sub Poner(r As DataGridViewRow, f As FilaPlanilla)
        r.Tag = f.EmpleadoId
        r.Cells("Nombre").Value = f.Nombre
        r.Cells("Dias").Value = f.Dias
        r.Cells("Haber").Value = f.Haber
        r.Cells("BonoAntig").Value = f.BonoAntig
        r.Cells("HorasExtras").Value = f.HorasExtras
        r.Cells("BonoProd").Value = f.BonoProd
        r.Cells("BonoDom").Value = f.BonoDom
        r.Cells("OtrosIngresos").Value = f.OtrosIngresos
        r.Cells("TotalGanado").Value = f.TotalGanado
        r.Cells("TotalAfp").Value = f.TotalAfp
        r.Cells("Facturas").Value = f.Facturas
        r.Cells("RcIvaRet").Value = f.RcIvaRet
        r.Cells("Anticipo").Value = f.Anticipo
        r.Cells("Prestamo").Value = f.Prestamo
        r.Cells("OtrosDesc").Value = f.OtrosDesc
        r.Cells("Liquido").Value = f.Liquido
    End Sub

    Private Sub FinEdicion(o As Object, e As DataGridViewCellEventArgs)
        If _cargando OrElse e.RowIndex < 0 OrElse _periodo Is Nothing Then Return
        Dim r As DataGridViewRow = _grid.Rows(e.RowIndex)
        Dim f As FilaPlanilla = _filas.FirstOrDefault(Function(x) x.EmpleadoId = CInt(r.Tag))
        If f Is Nothing Then Return
        f.Dias = ToInt(r.Cells("Dias").Value)
        f.HorasExtras = ToDec(r.Cells("HorasExtras").Value)
        f.BonoProd = ToDec(r.Cells("BonoProd").Value)
        f.BonoDom = ToDec(r.Cells("BonoDom").Value)
        f.OtrosIngresos = ToDec(r.Cells("OtrosIngresos").Value)
        f.Facturas = ToDec(r.Cells("Facturas").Value)
        f.Anticipo = ToDec(r.Cells("Anticipo").Value)
        f.Prestamo = ToDec(r.Cells("Prestamo").Value)
        f.OtrosDesc = ToDec(r.Cells("OtrosDesc").Value)
        Try
            Svc.Planillas.GuardarFila(_periodo, f)
            _cargando = True
            Poner(r, f)
            _cargando = False
            Totales()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub Totales()
        _lblTotales.Text = "Empleados: " & _filas.Count & "     Total ganado: Bs " & _filas.Sum(Function(x) x.TotalGanado).ToString("N2", FormatoVal.Cultura) & "     Descuentos: Bs " & _filas.Sum(Function(x) x.TotalDesc).ToString("N2", FormatoVal.Cultura) & "     LÍQUIDO PAGABLE: Bs " & _filas.Sum(Function(x) x.Liquido).ToString("N2", FormatoVal.Cultura) & "     Aportes patronales: Bs " & _filas.Sum(Function(x) x.TotalPatronal).ToString("N2", FormatoVal.Cultura)
    End Sub

    Private Sub Cerrar()
        If _periodo Is Nothing Then Return
        If Not Msg.Confirmar("Se cerrará la planilla y se generará el comprobante contable (sueldos, aportes y retenciones) más la provisión de aguinaldo e indemnización." & vbCrLf & "¿Continuar?", "Cerrar planilla") Then Return
        If Intentar(Sub() Svc.Planillas.Cerrar(_periodo)) Then
            Msg.Info("Planilla cerrada y contabilizada.")
            AbrirPeriodo()
        End If
    End Sub

    Private Sub Reabrir()
        If _periodo Is Nothing Then Return
        If Not Msg.Confirmar("Se anularán los comprobantes de la planilla y podrá corregir los datos. ¿Continuar?", "Reabrir planilla", True) Then Return
        If Intentar(Sub() Svc.Planillas.Reabrir(_periodo)) Then AbrirPeriodo()
    End Sub
End Class

''' <summary>Anticipos de sueldo del mes: se descuentan automáticamente al generar la planilla.</summary>
Public Class AnticiposForm
    Inherits ListaForm

    Private ReadOnly _mes As New LookupCombo() With {.Width = 200}

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Anticipos de sueldo"
        End Get
    End Property
    Protected Overrides ReadOnly Property PermisoEdicion As String
        Get
            Return "RH.PLANILLA"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "'A descontar' es el importe que se descuenta en la planilla del mismo mes."
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim meses As New List(Of KeyValuePair(Of String, String))
        For i As Integer = 0 To 11
            Dim m As Date = Ctx.Gestion.FechaInicio.AddMonths(i)
            meses.Add(New KeyValuePair(Of String, String)(m.ToString("yyyy-MM"), NombreMes(m.Month) & " " & m.Year))
        Next
        _mes.CargarLista(meses)
        _mes.ValorTexto = If(Date.Today >= Ctx.Gestion.FechaInicio AndAlso Date.Today <= Ctx.Gestion.FechaFin, Date.Today.ToString("yyyy-MM"), Ctx.Gestion.FechaInicio.ToString("yyyy-MM"))
        Barra.Controls.Add(New Label() With {.Text = "Mes", .AutoSize = True, .Margin = New Padding(10, 8, 4, 0)})
        Barra.Controls.Add(_mes)
        AddHandler _mes.SelectionChangeCommitted, Sub(o, e) Refrescar()
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Return Svc.Planillas.Anticipos(ToInt(_mes.ValorTexto.Substring(0, 4)), ToInt(_mes.ValorTexto.Substring(5)))
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Nombre", "Empleado", 280, True)
        Tema.ColFecha(Grid, "Fecha", "Fecha")
        Tema.ColTexto(Grid, "Detalle", "Detalle", 240)
        Tema.ColImporte(Grid, "Monto", "Anticipo", 110)
        Tema.ColImporte(Grid, "Confirmado", "A descontar", 110)
    End Sub

    Protected Overrides Sub Nuevo()
        Dim campos As New List(Of CampoUI) From {
            CampoUI.Lk("EmpleadoId", "Empleado", Function() Svc.Planillas.ListarEmpleados(True), "Nombre", True),
            CampoUI.Fec("Fecha", "Fecha"), CampoUI.Imp("Monto", "Importe entregado", True), CampoUI.Imp("Confirmado", "Importe a descontar en planilla"), CampoUI.Txt("Detalle", "Detalle", 100, False, True)}
        Using d As New FichaDialog("Nuevo anticipo de sueldo", campos, New Dictionary(Of String, Object) From {{"Fecha", Date.Today}},
            Sub(v)
                Dim m As Decimal = ToDec(v("Monto"))
                Dim c As Decimal = If(ToDec(v("Confirmado")) = 0D, m, ToDec(v("Confirmado")))
                Svc.Planillas.GuardarAnticipo(ToInt(v("EmpleadoId")), ToDate(v("Fecha")), m, c, ToStr(v("Detalle")))
            End Sub, "", 640)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Msg.Info("Para corregir un anticipo elimínelo y vuelva a registrarlo.")
    End Sub

    Protected Overrides Sub Eliminar(fila As DataRow)
        Svc.Planillas.EliminarAnticipo(fila.GetI("Id"))
    End Sub
End Class
