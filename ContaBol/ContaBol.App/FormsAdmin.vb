Imports System.IO
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Parámetros de la empresa y gestión: impuestos, reglas contables y cuentas por defecto de cada proceso automático.</summary>
Public Class ParametrosForm
    Inherits FormBase

    Private Class Par
        Public Clave As String
        Public Titulo As String
        Public Tipo As Char
        Public Ayuda As String
        Public Control As Control
        Public Sub New(clave As String, titulo As String, tipo As Char, Optional ayuda As String = "")
            Me.Clave = clave
            Me.Titulo = titulo
            Me.Tipo = tipo
            Me.Ayuda = ayuda
        End Sub
    End Class

    Private ReadOnly _pars As New List(Of Par)

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Parámetros"
        End Get
    End Property

    Private Sub Agregar(pagina As TabPage, seccion As String, ParamArray ps() As Par)
        Dim panel As FlowLayoutPanel = CType(pagina.Controls(0), FlowLayoutPanel)
        If seccion <> "" Then panel.Controls.Add(New Label() With {.Text = seccion.ToUpperInvariant(), .Font = Tema.FuenteNegrita, .ForeColor = Tema.Azul, .AutoSize = True, .Margin = New Padding(0, 14, 0, 4), .Width = 760})
        For Each p As Par In ps
            Dim fila As New Panel() With {.Height = 30, .Width = 800}
            Dim l As New Label() With {.Text = p.Titulo, .AutoSize = False, .Location = New Point(0, 0), .Size = New Size(330, 28), .TextAlign = ContentAlignment.MiddleLeft}
            Dim valor As String = Ctx.Param.Valor(p.Clave)
            Dim c As Control
            Select Case p.Tipo
                Case "C"c
                    Dim pc As New PickerCuenta() With {.Width = 440, .SoloMovimiento = True}
                    Dim cta As DataRow = Ctx.CuentaPorCodigo(valor)
                    If cta IsNot Nothing Then pc.CuentaId = cta.GetI("Id")
                    c = pc
                Case "B"c
                    c = New CheckBox() With {.Checked = ToFlag(valor), .AutoSize = True}
                Case Else
                    Dim ci As New CampoImporte() With {.Width = 130, .Decimales = 4, .PermiteNegativo = False}
                    ci.Valor = ToDec(valor)
                    c = ci
            End Select
            c.Location = New Point(336, If(p.Tipo = "B"c, 5, 2))
            fila.Controls.AddRange({l, c})
            If p.Ayuda <> "" Then
                fila.Controls.Add(New Label() With {.Text = p.Ayuda, .AutoSize = True, .ForeColor = Tema.Gris, .Location = New Point(480, 6), .Font = Tema.FuenteSubtitulo})
            End If
            p.Control = c
            _pars.Add(p)
            panel.Controls.Add(fila)
        Next
    End Sub

    Private Shared Function NuevaPagina(titulo As String) As TabPage
        Dim p As New TabPage(titulo) With {.BackColor = Color.White}
        Dim f As New FlowLayoutPanel() With {.Dock = DockStyle.Fill, .FlowDirection = FlowDirection.TopDown, .WrapContents = False, .AutoScroll = True, .Padding = New Padding(20, 6, 10, 10)}
        p.Controls.Add(f)
        Return p
    End Function

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Parámetros"
        Dim banner As Panel = Tema.Banner("Parámetros de la empresa", Ctx.Empresa.RazonSocial & " · Gestión " & Ctx.Gestion.Anio)
        Dim tabs As New TabControl() With {.Dock = DockStyle.Fill}
        Dim p1 As TabPage = NuevaPagina("Impuestos y reglas")
        Dim p2 As TabPage = NuevaPagina("Cuentas del sistema comercial")
        Dim p3 As TabPage = NuevaPagina("Cierre, ajustes y activos")
        Dim p4 As TabPage = NuevaPagina("Producción y costos")
        Dim p5 As TabPage = NuevaPagina("Planillas y beneficios sociales")
        tabs.TabPages.AddRange({p1, p2, p3, p4, p5})
        Agregar(p1, "Impuestos", New Par(ParamKeys.IvaPct, "IVA (%)", "N"c, "Se aplica sobre el total de la factura (débito y crédito fiscal)"), New Par(ParamKeys.ItPct, "Impuesto a las transacciones - IT (%)", "N"c),
                New Par(ParamKeys.ItSinFactura, "Devengar IT también en ventas sin factura", "B"c, "El IT grava todo ingreso, con o sin factura"))
        Agregar(p1, "Reglas contables", New Par(ParamKeys.DescEnBase, "Descuentos y recargos modifican la base imponible", "B"c, "Recomendado: descuentos facturados reducen el IVA"),
                New Par(ParamKeys.ControlPresupuesto, "Controlar presupuesto al contabilizar", "B"c, "Bloquea gastos que superen el presupuesto de la cuenta"),
                New Par(ParamKeys.StockNegativo, "Permitir ventas sin stock suficiente", "B"c, "No recomendado: distorsiona el costo"),
                New Par(ParamKeys.TcDefecto, "Tipo de cambio por defecto (Bs/US$)", "N"c, "Se usa si no hay uno cargado a la fecha"))
        Agregar(p2, "Disponibilidades y cuentas corrientes", New Par(ParamKeys.CtaCaja, "Caja (por defecto en cobros y pagos)", "C"c), New Par(ParamKeys.CtaCxc, "Cuentas por cobrar clientes", "C"c), New Par(ParamKeys.CtaCxp, "Cuentas por pagar proveedores", "C"c),
                New Par(ParamKeys.CtaAnticipoCli, "Anticipos de clientes (pasivo)", "C"c), New Par(ParamKeys.CtaAnticipoProv, "Anticipos a proveedores (activo)", "C"c))
        Agregar(p2, "Ventas, compras e inventarios", New Par(ParamKeys.CtaInventario, "Inventario de mercaderías", "C"c), New Par(ParamKeys.CtaVentas, "Ventas (ingreso)", "C"c), New Par(ParamKeys.CtaCostoVentas, "Costo de ventas", "C"c),
                New Par(ParamKeys.CtaDescVentas, "Descuentos en ventas", "C"c), New Par(ParamKeys.CtaRecVentas, "Recargos en ventas", "C"c), New Par(ParamKeys.CtaDescCompras, "Descuentos en compras", "C"c), New Par(ParamKeys.CtaRecCompras, "Recargos en compras", "C"c), New Par(ParamKeys.CtaMermas, "Mermas y ajustes de inventario", "C"c))
        Agregar(p2, "Impuestos", New Par(ParamKeys.CtaCreditoFiscal, "Crédito fiscal IVA", "C"c), New Par(ParamKeys.CtaDebitoFiscal, "Débito fiscal IVA", "C"c), New Par(ParamKeys.CtaItGasto, "IT (gasto)", "C"c), New Par(ParamKeys.CtaItPagar, "IT por pagar", "C"c))
        Agregar(p3, "Cierre de gestión", New Par(ParamKeys.CtaResultadoGestion, "Resultado de la gestión", "C"c), New Par(ParamKeys.CtaResultadoAcum, "Resultados acumulados", "C"c))
        Agregar(p3, "Ajustes", New Par(ParamKeys.CtaAjusteInflIng, "Ajuste por inflación y tenencia de bienes (ingreso)", "C"c), New Par(ParamKeys.CtaAjusteInflEgr, "Ajuste por inflación y tenencia de bienes (gasto)", "C"c),
                New Par(ParamKeys.CtaDifCambioIng, "Diferencia de cambio (ingreso)", "C"c), New Par(ParamKeys.CtaDifCambioEgr, "Diferencia de cambio (gasto)", "C"c))
        Agregar(p3, "Activos fijos", New Par(ParamKeys.CtaBajaAf, "Pérdida por baja de activos fijos", "C"c))
        Agregar(p4, "Producción", New Par(ParamKeys.CtaMateriaPrima, "Materia prima", "C"c), New Par(ParamKeys.CtaProdTerminados, "Productos terminados", "C"c), New Par(ParamKeys.CtaMano, "Mano de obra directa (se capitaliza al cerrar la orden)", "C"c), New Par(ParamKeys.CtaCif, "Costos indirectos de fabricación (se capitalizan)", "C"c))
        Agregar(p5, "Salario y días", New Par(ParamKeys.Smn, "Salario mínimo nacional (Bs)", "N"c, "Base del bono de antigüedad y del RC-IVA"), New Par(ParamKeys.PlDiasMes, "Días del mes comercial", "N"c))
        Agregar(p5, "Aportes laborales AFP (% sobre el total ganado)", New Par(ParamKeys.PlAfpVejez, "Vejez", "N"c), New Par(ParamKeys.PlAfpRiesgo, "Riesgo común", "N"c), New Par(ParamKeys.PlAfpComision, "Comisión AFP", "N"c), New Par(ParamKeys.PlAfpSolidario, "Aporte solidario", "N"c))
        Agregar(p5, "Aporte nacional solidario (tramos de total ganado, Bs)", New Par(ParamKeys.PlAnsTramo1, "Desde (1%)", "N"c), New Par(ParamKeys.PlAnsTramo2, "Desde (5%)", "N"c), New Par(ParamKeys.PlAnsTramo3, "Desde (10%)", "N"c))
        Agregar(p5, "Aportes patronales (%)", New Par(ParamKeys.PlPatCns, "Caja Nacional de Salud", "N"c), New Par(ParamKeys.PlPatRiesgo, "Riesgo profesional", "N"c), New Par(ParamKeys.PlPatVivienda, "Pro-vivienda", "N"c), New Par(ParamKeys.PlPatSolidario, "Aporte patronal solidario", "N"c))
        Agregar(p5, "RC-IVA dependientes", New Par(ParamKeys.PlRcIvaPct, "Alícuota (%)", "N"c), New Par(ParamKeys.PlRcIvaMinSmn, "Mínimo no imponible (veces el SMN)", "N"c), New Par(ParamKeys.PlRcIvaCredSmn, "Crédito del 13% sobre (veces el SMN)", "N"c))
        Agregar(p5, "Cuentas de planillas", New Par(ParamKeys.CtaSueldos, "Sueldos y salarios (gasto)", "C"c), New Par(ParamKeys.CtaBonoAntig, "Bono de antigüedad", "C"c), New Par(ParamKeys.CtaHorasExtras, "Horas extras", "C"c), New Par(ParamKeys.CtaOtrosBonos, "Otros bonos y beneficios", "C"c),
                New Par(ParamKeys.CtaGastoCns, "Gasto aporte patronal CNS", "C"c), New Par(ParamKeys.CtaGastoRiesgo, "Gasto aporte riesgo profesional", "C"c), New Par(ParamKeys.CtaGastoVivienda, "Gasto aporte pro-vivienda", "C"c), New Par(ParamKeys.CtaGastoSolidario, "Gasto aporte patronal solidario", "C"c),
                New Par(ParamKeys.CtaSueldosPagar, "Sueldos por pagar", "C"c), New Par(ParamKeys.CtaAfpLaboralPagar, "AFP aportes laborales por pagar", "C"c), New Par(ParamKeys.CtaAfpPatronalPagar, "AFP aportes patronales por pagar", "C"c), New Par(ParamKeys.CtaCnsPagar, "CNS por pagar", "C"c),
                New Par(ParamKeys.CtaViviendaPagar, "Pro-vivienda por pagar", "C"c), New Par(ParamKeys.CtaSolidarioPagar, "Aporte solidario por pagar", "C"c), New Par(ParamKeys.CtaRcIvaPagar, "RC-IVA retenido por pagar", "C"c), New Par(ParamKeys.CtaAnticipoPers, "Anticipos y préstamos al personal (activo)", "C"c),
                New Par(ParamKeys.CtaAcreedores, "Acreedores varios (otros descuentos)", "C"c), New Par(ParamKeys.CtaGastoAguinaldo, "Gasto aguinaldos", "C"c), New Par(ParamKeys.CtaProvAguinaldo, "Provisión para aguinaldos", "C"c), New Par(ParamKeys.CtaGastoIndem, "Gasto indemnizaciones", "C"c), New Par(ParamKeys.CtaProvIndem, "Provisión para indemnizaciones", "C"c))
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 54, .BackColor = Color.White, .Padding = New Padding(14, 9, 14, 9)}
        Dim bGuardar As Button = Tema.Boton("Guardar parámetros", Tema.TipoBoton.Primario, 170)
        bGuardar.Dock = DockStyle.Right
        Dim bEmp As Button = Tema.Boton("Datos de la empresa…", Tema.TipoBoton.Secundario, 170)
        bEmp.Dock = DockStyle.Left
        pie.Controls.Add(bGuardar)
        pie.Controls.Add(bEmp)
        Controls.Add(tabs)
        Controls.Add(pie)
        Controls.Add(banner)
        AddHandler bGuardar.Click, Sub(o, ev) Guardar()
        AddHandler bEmp.Click, Sub(o, ev)
                                   If NuevaEmpresaDialog.Editar(Ctx.Empresa.Id) Then
                                       Msg.Info("Datos actualizados. Se verán reflejados en los reportes.")
                                       Ctx.Param.Recargar()
                                   End If
                               End Sub
        bGuardar.Enabled = Sesion.Puede("ADM.PARAMETROS")
        bEmp.Enabled = Sesion.Usuario.EsAdmin
    End Sub

    Private Sub Guardar()
        Try
            For Each p As Par In _pars
                Dim v As String
                Select Case p.Tipo
                    Case "C"c : v = Ctx.CodigoCuenta(CType(p.Control, PickerCuenta).CuentaId)
                    Case "B"c : v = If(CType(p.Control, CheckBox).Checked, "1", "0")
                    Case Else : v = CType(p.Control, CampoImporte).Valor.ToString(Inv)
                End Select
                Ctx.Param.Guardar(p.Clave, v)
            Next
            Ctx.Audit("Parámetros", "PARAMETROS_GUARDADOS", Ctx.Empresa.Codigo)
            Msg.Info("Parámetros guardados correctamente.")
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub
End Class

''' <summary>Usuarios del sistema y sus accesos por empresa.</summary>
Public Class UsuariosForm
    Inherits ListaForm

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Usuarios y permisos"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Cada usuario recibe acceso por empresa con un rol (Administrador, Contador, Auxiliar, Consulta) y permisos afinables. Las contraseñas se guardan cifradas."
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        Dim bP As Button = Tema.Boton("Accesos y permisos…", Tema.TipoBoton.Secundario, 170)
        Dim bC As Button = Tema.Boton("Restablecer clave", Tema.TipoBoton.Secundario, 130)
        Barra.Controls.AddRange({bP, bC})
        AddHandler bP.Click, Sub(o, e)
                                 Dim f As DataRow = FilaActual()
                                 If f IsNot Nothing Then
                                     Using d As New PermisosDialog(f.GetI("Id"), f.GetS("Nombre"))
                                         d.ShowDialog(FindForm())
                                     End Using
                                 End If
                             End Sub
        AddHandler bC.Click, Sub(o, e) RestablecerClave()
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        If Not Sesion.Usuario.EsAdmin Then Throw New UnauthorizedAccessException("Solo el administrador del sistema puede gestionar usuarios.")
        Dim dt As DataTable = Sesion.Sis.ListarUsuarios()
        dt.Columns.Add("Rol", GetType(String))
        For Each r As DataRow In dt.Rows
            r("Rol") = If(r.GetF("EsAdmin"), "Administrador del sistema", "")
        Next
        Return dt
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColTexto(Grid, "Login", "Usuario", 110)
        Tema.ColTexto(Grid, "Nombre", "Nombre completo", 260, True)
        Tema.ColTexto(Grid, "Email", "Correo", 180)
        Tema.ColTexto(Grid, "Rol", "Tipo", 170)
        Tema.ColCheck(Grid, "Activo", "Activo", 56)
        Tema.ColFecha(Grid, "UltimoAcceso", "Último acceso", 110).DefaultCellStyle.Format = "dd/MM/yyyy HH:mm"
    End Sub

    Protected Overrides Sub FilaColoreada(fila As DataRow, estilo As DataGridViewCellStyle)
        If Not fila.GetF("Activo") OrElse fila.GetI("Intentos") >= 5 Then estilo.ForeColor = Tema.Gris
    End Sub

    Protected Overrides Sub Nuevo()
        Dim campos As New List(Of CampoUI) From {CampoUI.Txt("Login", "Usuario (mín. 3 caracteres)", 30, True), CampoUI.Txt("Nombre", "Nombre completo", 100, True, True), CampoUI.Txt("Email", "Correo", 100, False, True),
            New CampoUI With {.Clave = "Clave", .Titulo = "Contraseña (mín. 4)", .Tipo = TipoCampo.Clave, .Requerido = True}, CampoUI.Chk("EsAdmin", "Administrador del sistema (acceso total)")}
        Dim nuevoId As Integer = 0
        Using d As New FichaDialog("Nuevo usuario", campos, Nothing, Sub(v) nuevoId = Sesion.Sis.CrearUsuario(ToStr(v("Login")), ToStr(v("Nombre")), ToStr(v("Clave")), ToFlag(v("EsAdmin")), ToStr(v("Email"))), "Después de crear el usuario asígnele acceso a las empresas.", 640)
            If d.ShowDialog(FindForm()) <> DialogResult.OK Then Return
        End Using
        If nuevoId <> 0 AndAlso Msg.Confirmar("¿Desea asignar ahora los accesos a empresas de este usuario?") Then
            Using p As New PermisosDialog(nuevoId, "")
                p.ShowDialog(FindForm())
            End Using
        End If
    End Sub

    Protected Overrides Sub Editar(fila As DataRow)
        Dim campos As New List(Of CampoUI) From {CampoUI.Txt("Nombre", "Nombre completo", 100, True, True), CampoUI.Txt("Email", "Correo", 100, False, True), CampoUI.Chk("Activo", "Usuario activo", True), CampoUI.Chk("EsAdmin", "Administrador del sistema")}
        Dim v As New Dictionary(Of String, Object) From {{"Nombre", fila.GetS("Nombre")}, {"Email", fila.GetS("Email")}, {"Activo", fila.GetF("Activo")}, {"EsAdmin", fila.GetF("EsAdmin")}}
        Using d As New FichaDialog("Modificar usuario " & fila.GetS("Login"), campos, v, Sub(x) Sesion.Sis.ActualizarUsuario(fila.GetI("Id"), ToStr(x("Nombre")), ToStr(x("Email")), ToFlag(x("Activo")), ToFlag(x("EsAdmin"))), "", 620)
            d.ShowDialog(FindForm())
        End Using
    End Sub

    Protected Overrides Sub Eliminar(fila As DataRow)
        Sesion.Sis.EliminarUsuario(fila.GetI("Id"))
    End Sub

    Private Sub RestablecerClave()
        Dim f As DataRow = FilaActual()
        If f Is Nothing Then Return
        Dim nueva As String = Msg.Pedir("Nueva contraseña para '" & f.GetS("Login") & "' (mínimo 4 caracteres):", "Restablecer contraseña", "", True)
        If String.IsNullOrEmpty(nueva) Then Return
        If Intentar(Sub() Sesion.Sis.CambiarClave(f.GetI("Id"), nueva, True)) Then
            Msg.Info("Contraseña restablecida. Se solicitará cambiarla en el próximo ingreso y se desbloqueó el usuario.")
            Refrescar()
        End If
    End Sub
End Class

''' <summary>Asignación de empresas, rol y permisos finos de un usuario.</summary>
Public Class PermisosDialog
    Inherits Form

    Private ReadOnly _userId As Integer
    Private ReadOnly _empresas As New ListBox()
    Private ReadOnly _arbol As New TreeView()
    Private ReadOnly _rol As New LookupCombo() With {.Width = 200}
    Private ReadOnly _estado As New Label()
    Private _empresasDt As DataTable
    Private _cargando As Boolean

    Public Sub New(userId As Integer, nombre As String)
        _userId = userId
        Tema.Aplicar(Me)
        Text = "Accesos y permisos" & If(nombre <> "", " - " & nombre, "")
        StartPosition = FormStartPosition.CenterParent
        ClientSize = New Size(900, 620)
        ShowInTaskbar = False
        Dim banner As Panel = Tema.Banner("Accesos y permisos", "Seleccione la empresa y marque lo que el usuario puede hacer en ella.")
        Dim izq As New Panel() With {.Dock = DockStyle.Left, .Width = 280, .Padding = New Padding(12)}
        izq.Controls.Add(_empresas)
        izq.Controls.Add(New Label() With {.Text = "Empresas del sistema", .Dock = DockStyle.Top, .Height = 24, .Font = Tema.FuenteNegrita})
        _empresas.Dock = DockStyle.Fill
        _empresas.DrawMode = DrawMode.OwnerDrawFixed
        _empresas.ItemHeight = 26
        Dim der As New Panel() With {.Dock = DockStyle.Fill, .Padding = New Padding(12)}
        Dim top As New FlowLayoutPanel() With {.Dock = DockStyle.Top, .Height = 40, .WrapContents = False}
        Dim bRol As Button = Tema.Boton("Aplicar rol", Tema.TipoBoton.Secundario, 100)
        top.Controls.Add(New Label() With {.Text = "Rol:", .AutoSize = True, .Margin = New Padding(0, 8, 6, 0)})
        top.Controls.AddRange({_rol, bRol})
        _rol.CargarLista(Permisos.Roles.Select(Function(r) New KeyValuePair(Of String, String)(r, r)))
        _estado.Dock = DockStyle.Top
        _estado.Height = 26
        _estado.Font = Tema.FuenteNegrita
        _arbol.Dock = DockStyle.Fill
        _arbol.CheckBoxes = True
        _arbol.BorderStyle = BorderStyle.FixedSingle
        _arbol.ItemHeight = 22
        der.Controls.Add(_arbol)
        der.Controls.Add(_estado)
        der.Controls.Add(top)
        Dim pie As New Panel() With {.Dock = DockStyle.Bottom, .Height = 52, .BackColor = Color.White, .Padding = New Padding(14, 9, 14, 9)}
        Dim bGuardar As Button = Tema.Boton("Guardar acceso", Tema.TipoBoton.Primario, 140)
        bGuardar.Dock = DockStyle.Right
        Dim bQuitar As Button = Tema.Boton("Quitar acceso a la empresa", Tema.TipoBoton.Peligro, 200)
        bQuitar.Dock = DockStyle.Left
        Dim bCerrar As Button = Tema.Boton("Cerrar", Tema.TipoBoton.Secundario, 90)
        bCerrar.Dock = DockStyle.Right
        pie.Controls.Add(bGuardar)
        pie.Controls.Add(New Panel() With {.Dock = DockStyle.Right, .Width = 8})
        pie.Controls.Add(bCerrar)
        pie.Controls.Add(bQuitar)
        Controls.Add(der)
        Controls.Add(izq)
        Controls.Add(pie)
        Controls.Add(banner)
        For Each g In Permisos.Todas.GroupBy(Function(o) o.Grupo)
            Dim n As TreeNode = _arbol.Nodes.Add(g.Key)
            For Each o In g
                Dim h As TreeNode = n.Nodes.Add(o.Titulo)
                h.Tag = o.Clave
            Next
            n.Expand()
        Next
        _empresasDt = Sesion.Sis.ListarEmpresas(True)
        For Each r As DataRow In _empresasDt.Rows
            _empresas.Items.Add(r.GetS("Codigo") & "  -  " & r.GetS("RazonSocial"))
        Next
        AddHandler _empresas.DrawItem, AddressOf DibujarEmpresa
        AddHandler _empresas.SelectedIndexChanged, Sub(o, e) CargarEmpresa()
        AddHandler _arbol.AfterCheck, AddressOf AlMarcar
        AddHandler bRol.Click, Sub(o, e) AplicarRol()
        AddHandler bGuardar.Click, Sub(o, e) Guardar()
        AddHandler bQuitar.Click, Sub(o, e) Quitar()
        AddHandler bCerrar.Click, Sub(o, e) Close()
        If _empresas.Items.Count > 0 Then _empresas.SelectedIndex = 0
    End Sub

    Private Function EmpresaId() As Integer
        If _empresas.SelectedIndex < 0 Then Return 0
        Return _empresasDt.Rows(_empresas.SelectedIndex).GetI("Id")
    End Function

    Private Function TieneAcceso(idx As Integer) As Boolean
        Return Sesion.Sis.Db.ScalarInt("SELECT COUNT(*) FROM UsuarioEmpresa WHERE UsuarioId=@u AND EmpresaId=@e", "u", _userId, "e", _empresasDt.Rows(idx).GetI("Id")) > 0
    End Function

    Private Sub DibujarEmpresa(o As Object, e As DrawItemEventArgs)
        If e.Index < 0 Then Return
        e.DrawBackground()
        Dim acceso As Boolean = TieneAcceso(e.Index)
        Dim col As Color = If((e.State And DrawItemState.Selected) = DrawItemState.Selected, Color.White, If(acceso, Tema.Verde, Tema.ColorTexto))
        TextRenderer.DrawText(e.Graphics, If(acceso, "✔ ", "   ") & _empresas.Items(e.Index).ToString(), Tema.Fuente, e.Bounds, col, TextFormatFlags.Left Or TextFormatFlags.VerticalCenter Or TextFormatFlags.EndEllipsis)
    End Sub

    Private Sub CargarEmpresa()
        Dim id As Integer = EmpresaId()
        If id = 0 Then Return
        _cargando = True
        Dim tiene As Boolean = Sesion.Sis.Db.ScalarInt("SELECT COUNT(*) FROM UsuarioEmpresa WHERE UsuarioId=@u AND EmpresaId=@e", "u", _userId, "e", id) > 0
        Dim perms As HashSet(Of String) = Sesion.Sis.PermisosDe(_userId, id)
        For Each g As TreeNode In _arbol.Nodes
            Dim todos As Boolean = True
            For Each h As TreeNode In g.Nodes
                h.Checked = perms.Contains(CStr(h.Tag))
                If Not h.Checked Then todos = False
            Next
            g.Checked = todos
        Next
        If tiene Then _rol.ValorTexto = Sesion.Sis.RolDe(_userId, id)
        _estado.Text = If(tiene, "El usuario tiene acceso a esta empresa.", "Sin acceso a esta empresa: elija un rol y guarde para otorgarlo.")
        _estado.ForeColor = If(tiene, Tema.Verde, Tema.Gris)
        _cargando = False
        _empresas.Invalidate()
    End Sub

    Private Sub AlMarcar(o As Object, e As TreeViewEventArgs)
        If _cargando Then Return
        _cargando = True
        If e.Node.Level = 0 Then
            For Each h As TreeNode In e.Node.Nodes
                h.Checked = e.Node.Checked
            Next
        End If
        _cargando = False
    End Sub

    Private Sub AplicarRol()
        Dim perms As New HashSet(Of String)(Permisos.PorRol(_rol.ValorTexto))
        _cargando = True
        For Each g As TreeNode In _arbol.Nodes
            Dim todos As Boolean = True
            For Each h As TreeNode In g.Nodes
                h.Checked = perms.Contains(CStr(h.Tag))
                If Not h.Checked Then todos = False
            Next
            g.Checked = todos
        Next
        _cargando = False
    End Sub

    Private Sub Guardar()
        Dim id As Integer = EmpresaId()
        If id = 0 Then Return
        Try
            Dim sel As New List(Of String)
            For Each g As TreeNode In _arbol.Nodes
                For Each h As TreeNode In g.Nodes
                    If h.Checked Then sel.Add(CStr(h.Tag))
                Next
            Next
            Sesion.Sis.AsignarEmpresa(_userId, id, _rol.ValorTexto)
            Sesion.Sis.EstablecerPermisos(_userId, id, sel)
            Msg.Info("Acceso guardado (" & sel.Count & " permisos).")
            CargarEmpresa()
        Catch ex As Exception
            Msg.ErrorMsg(ex)
        End Try
    End Sub

    Private Sub Quitar()
        Dim id As Integer = EmpresaId()
        If id = 0 Then Return
        If Not Msg.Confirmar("¿Quitar el acceso del usuario a esta empresa?", "Quitar acceso", True) Then Return
        Sesion.Sis.QuitarEmpresa(_userId, id)
        CargarEmpresa()
    End Sub
End Class

''' <summary>Bitácora de acciones de los usuarios.</summary>
Public Class AuditoriaForm
    Inherits ListaForm

    Private ReadOnly _desde As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}
    Private ReadOnly _hasta As New DateTimePicker() With {.Format = DateTimePickerFormat.Custom, .CustomFormat = "dd/MM/yyyy", .Width = 110}

    Protected Overrides ReadOnly Property TituloLista As String
        Get
            Return "Auditoría del sistema"
        End Get
    End Property
    Protected Overrides ReadOnly Property SubtituloLista As String
        Get
            Return "Registro de ingresos, altas, modificaciones, anulaciones, copias de seguridad y demás acciones de los usuarios."
        End Get
    End Property
    Protected Overrides ReadOnly Property PermiteNuevo As Boolean
        Get
            Return False
        End Get
    End Property
    Protected Overrides ReadOnly Property PermiteEliminar As Boolean
        Get
            Return False
        End Get
    End Property

    Protected Overrides Sub AgregarBotones()
        _desde.Value = Date.Today.AddDays(-7)
        _hasta.Value = Date.Today
        Barra.Controls.AddRange({New Label() With {.Text = "Del", .AutoSize = True, .Margin = New Padding(10, 8, 4, 0)}, _desde, New Label() With {.Text = "al", .AutoSize = True, .Margin = New Padding(8, 8, 4, 0)}, _hasta})
        AddHandler _desde.ValueChanged, Sub(o, e) Refrescar()
        AddHandler _hasta.ValueChanged, Sub(o, e) Refrescar()
        BotonEditar.Visible = False
    End Sub

    Protected Overrides Function CargarDatos() As DataTable
        Return Sesion.Sis.ConsultarAuditoria(_desde.Value.Date, _hasta.Value.Date, Ctx.Empresa.Id)
    End Function

    Protected Overrides Sub ConfigurarColumnas()
        Tema.ColFecha(Grid, "Fecha", "Fecha y hora", 140).DefaultCellStyle.Format = "dd/MM/yyyy HH:mm:ss"
        Tema.ColTexto(Grid, "Login", "Usuario", 90)
        Tema.ColTexto(Grid, "Modulo", "Módulo", 120)
        Tema.ColTexto(Grid, "Accion", "Acción", 190)
        Tema.ColTexto(Grid, "Detalle", "Detalle", 400, True)
        Tema.ColTexto(Grid, "Equipo", "Equipo", 110)
    End Sub
End Class

''' <summary>Copias de seguridad y restauración (por empresa o del sistema completo).</summary>
Public Class BackupForm
    Inherits FormBase

    Private ReadOnly _grid As New DataGridView()
    Private ReadOnly _lblCarpeta As New Label()
    Private ReadOnly _chkAuto As New CheckBox() With {.Text = "Hacer copia automática de la empresa al salir (una por día)", .AutoSize = True}
    Private ReadOnly _mantener As New NumericUpDown() With {.Minimum = 3, .Maximum = 100, .Value = 10, .Width = 60}

    Public Shared Sub Mostrar()
        Escritorio.Abrir(Of BackupForm)()
    End Sub

    Public Overrides ReadOnly Property TextoPestana As String
        Get
            Return "Copias de seguridad"
        End Get
    End Property

    Private ReadOnly Property Bs As BackupService
        Get
            Return New BackupService(Sesion.Sis)
        End Get
    End Property

    Protected Overrides Sub OnLoad(e As EventArgs)
        MyBase.OnLoad(e)
        Text = "Copias de seguridad"
        Dim banner As Panel = Tema.Banner("Copias de seguridad y recuperación", "Las copias son archivos .cbk comprimidos con verificación de integridad. Guárdelas también en un disco externo o en la nube.")
        Dim panel As New Panel() With {.Dock = DockStyle.Top, .Height = 170, .BackColor = Color.White, .Padding = New Padding(16, 10, 16, 6)}
        AddHandler panel.Paint, Sub(o, ev) ev.Graphics.DrawLine(New Pen(Tema.Borde), 0, panel.Height - 1, panel.Width, panel.Height - 1)
        Dim b1 As Button = Tema.Boton("Copia de esta empresa", Tema.TipoBoton.Primario, 190)
        Dim b2 As Button = Tema.Boton("Copia total del sistema", Tema.TipoBoton.Secundario, 190)
        Dim b3 As Button = Tema.Boton("Restaurar una copia…", Tema.TipoBoton.Secundario, 190)
        Dim b4 As Button = Tema.Boton("Verificar una copia…", Tema.TipoBoton.Secundario, 170)
        b1.Location = New Point(16, 12)
        b2.Location = New Point(214, 12)
        b3.Location = New Point(412, 12)
        b4.Location = New Point(610, 12)
        _lblCarpeta.AutoSize = True
        _lblCarpeta.Location = New Point(16, 56)
        Dim bCarpeta As Button = Tema.Boton("Cambiar carpeta…", Tema.TipoBoton.Secundario, 140)
        bCarpeta.Location = New Point(16, 80)
        Dim bAbrir As Button = Tema.Boton("Abrir carpeta", Tema.TipoBoton.Secundario, 120)
        bAbrir.Location = New Point(164, 80)
        _chkAuto.Location = New Point(16, 122)
        Dim lm As New Label() With {.Text = "Conservar las últimas", .AutoSize = True, .Location = New Point(480, 124)}
        _mantener.Location = New Point(615, 120)
        Dim lm2 As New Label() With {.Text = "copias por empresa", .AutoSize = True, .Location = New Point(682, 124)}
        panel.Controls.AddRange({b1, b2, b3, b4, _lblCarpeta, bCarpeta, bAbrir, _chkAuto, lm, _mantener, lm2})
        Tema.EstiloGrid(_grid)
        Tema.ColFecha(_grid, "Fecha", "Fecha", 140).DefaultCellStyle.Format = "dd/MM/yyyy HH:mm"
        Tema.ColTexto(_grid, "Tipo", "Tipo", 80)
        Tema.ColTexto(_grid, "Nombre", "Archivo", 520, True)
        Tema.ColImporte(_grid, "Tamano", "Tamaño (MB)", 100)
        Controls.Add(_grid)
        Controls.Add(panel)
        Controls.Add(banner)
        _chkAuto.Checked = Sesion.Config.BackupAutomatico
        _mantener.Value = Math.Max(3, Math.Min(100, Sesion.Config.MantenerCopias))
        AddHandler _chkAuto.CheckedChanged, Sub(o, ev)
                                                Sesion.Config.BackupAutomatico = _chkAuto.Checked
                                                Sesion.Config.Guardar()
                                            End Sub
        AddHandler _mantener.ValueChanged, Sub(o, ev)
                                               Sesion.Config.MantenerCopias = CInt(_mantener.Value)
                                               Sesion.Config.Guardar()
                                           End Sub
        AddHandler b1.Click, Sub(o, ev) CopiaEmpresa()
        AddHandler b2.Click, Sub(o, ev) CopiaTotal()
        AddHandler b3.Click, Sub(o, ev) Restaurar()
        AddHandler b4.Click, Sub(o, ev) Verificar()
        AddHandler bCarpeta.Click, Sub(o, ev) CambiarCarpeta()
        AddHandler bAbrir.Click, Sub(o, ev) Informes.Abrir_(Carpeta())
        AddHandler _grid.CellDoubleClick, Sub(o, ev) If ev.RowIndex >= 0 Then Informes.Abrir_(Path.GetDirectoryName(ToStr(CType(_grid.Rows(ev.RowIndex).DataBoundItem, DataRowView)("Archivo"))))
        Dim permiso As Boolean = Sesion.Puede("ADM.BACKUP")
        b1.Enabled = permiso
        b2.Enabled = permiso AndAlso Sesion.Usuario.EsAdmin
        b3.Enabled = Sesion.Puede("ADM.RESTAURAR")
        Cargar()
    End Sub

    Private Function Carpeta() As String
        Dim c As String = If(Sesion.Config.CarpetaBackup <> "" AndAlso Directory.Exists(Sesion.Config.CarpetaBackup), Sesion.Config.CarpetaBackup, Sesion.Sis.RutaBackups)
        Directory.CreateDirectory(c)
        Return c
    End Function

    Public Overrides Sub Refrescar()
        Cargar()
    End Sub

    Private Sub Cargar()
        _lblCarpeta.Text = "Carpeta de copias: " & Carpeta()
        Dim dt As New DataTable()
        dt.Columns.Add("Fecha", GetType(Date))
        dt.Columns.Add("Tipo", GetType(String))
        dt.Columns.Add("Nombre", GetType(String))
        dt.Columns.Add("Tamano", GetType(Decimal))
        dt.Columns.Add("Archivo", GetType(String))
        For Each f As String In Directory.GetFiles(Carpeta(), "*" & BackupService.Extension)
            Dim fi As New FileInfo(f)
            dt.Rows.Add(fi.LastWriteTime, If(fi.Name.Contains("_TOTAL_"), "TOTAL", "Empresa"), fi.Name, Math.Round(fi.Length / 1048576.0, 2), f)
        Next
        Dim v As DataView = dt.DefaultView
        v.Sort = "Fecha DESC"
        _grid.DataSource = v.ToTable()
    End Sub

    Private Sub CopiaEmpresa()
        Dim ruta As String = Nothing
        If Intentar(Sub() ruta = Bs.BackupEmpresa(Ctx.Empresa.Id, Carpeta(), "Copia manual")) Then
            Msg.Info("Copia creada correctamente:" & vbCrLf & ruta)
            Try
                Bs.Depurar(Math.Max(3, Sesion.Config.MantenerCopias))
            Catch
            End Try
            Cargar()
        End If
    End Sub

    Private Sub CopiaTotal()
        Dim ruta As String = Nothing
        If Intentar(Sub() ruta = Bs.BackupTotal(Carpeta(), "Copia total manual")) Then
            Msg.Info("Copia total creada:" & vbCrLf & ruta)
            Cargar()
        End If
    End Sub

    Private Sub CambiarCarpeta()
        Using d As New FolderBrowserDialog()
            d.Description = "Carpeta donde se guardarán las copias de seguridad (idealmente un disco externo o carpeta sincronizada)."
            d.UseDescriptionForTitle = True
            d.SelectedPath = Carpeta()
            If d.ShowDialog() = DialogResult.OK Then
                Sesion.Config.CarpetaBackup = d.SelectedPath
                Sesion.Config.Guardar()
                Cargar()
            End If
        End Using
    End Sub

    Private Sub Verificar()
        Using d As New OpenFileDialog()
            d.Filter = "Copia de seguridad ContaBol (*.cbk)|*.cbk"
            d.InitialDirectory = Carpeta()
            If d.ShowDialog() <> DialogResult.OK Then Return
            Dim v As BackupInfo = Nothing
            If Intentar(Sub() v = Bs.Verificar(d.FileName)) Then
                If v.Valido Then
                    Msg.Info("La copia es VÁLIDA e íntegra." & vbCrLf & vbCrLf & "Tipo: " & v.Tipo & vbCrLf & "Fecha: " & v.Fecha.ToString("dd/MM/yyyy HH:mm") & vbCrLf & "Empresa: " & v.EmpresaNombre & vbCrLf & If(v.Gestiones <> "", "Gestiones: " & v.Gestiones & vbCrLf, "") & "Tamaño: " & v.TamanoMb & " MB")
                Else
                    Msg.ErrorMsg("La copia está dañada o no es válida:" & vbCrLf & v.Mensaje)
                End If
            End If
        End Using
    End Sub

    Private Sub Restaurar()
        Using d As New OpenFileDialog()
            d.Filter = "Copia de seguridad ContaBol (*.cbk)|*.cbk"
            d.InitialDirectory = Carpeta()
            If d.ShowDialog() <> DialogResult.OK Then Return
            Dim archivo As String = d.FileName
            Dim v As BackupInfo = Nothing
            If Not Intentar(Sub() v = Bs.Verificar(archivo)) Then Return
            If Not v.Valido Then
                Msg.ErrorMsg("No se puede restaurar: la copia está dañada o no es válida." & vbCrLf & v.Mensaje)
                Return
            End If
            If v.Tipo = "TOTAL" Then
                Msg.Aviso("Esta es una copia TOTAL del sistema. Para restaurarla cierre sesión y use 'Restaurar copia total…' en la pantalla de ingreso.")
                Return
            End If
            Dim existe As Boolean = Sesion.Sis.Db.ScalarInt("SELECT COUNT(*) FROM Empresa WHERE Codigo=@c", "c", v.EmpresaCodigo) > 0
            Dim nuevoCodigo As String = ""
            Dim msgTxt As String = "Copia del " & v.Fecha.ToString("dd/MM/yyyy HH:mm") & " de: " & v.EmpresaNombre & " (gestiones " & v.Gestiones & ")" & vbCrLf & vbCrLf
            If existe Then
                Dim r As DialogResult = MessageBox.Show(msgTxt & "La empresa " & v.EmpresaCodigo & " ya existe." & vbCrLf & vbCrLf & "SÍ = reemplazar sus datos actuales por los de la copia (antes se guarda una copia de seguridad de lo actual)" & vbCrLf & "NO = restaurar como una empresa nueva (con otro código)" & vbCrLf & "Cancelar = no hacer nada", "Restaurar copia", MessageBoxButtons.YesNoCancel, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button3)
                If r = DialogResult.Cancel Then Return
                If r = DialogResult.No Then
                    nuevoCodigo = Msg.Pedir("Código de la nueva empresa (máx. 12 caracteres):", "Restaurar como empresa nueva", v.EmpresaCodigo & "2")
                    If String.IsNullOrWhiteSpace(nuevoCodigo) Then Return
                End If
            Else
                If Not Msg.Confirmar(msgTxt & "La empresa no existe en este sistema: se creará con todas sus gestiones. ¿Continuar?", "Restaurar copia") Then Return
            End If
            Dim empresaActual As Integer = Sesion.Ctx.Empresa.Id
            Dim gestionActual As Integer = Sesion.Ctx.Gestion.Id
            Dim cerrar As Boolean = existe AndAlso nuevoCodigo = "" AndAlso Sesion.Sis.Db.ScalarInt("SELECT COUNT(*) FROM Empresa WHERE Codigo=@c AND Id=@i", "c", v.EmpresaCodigo, "i", empresaActual) > 0
            Dim principal As MainForm = Escritorio.Principal
            ' La restauración se ejecuta fuera de este evento porque cierra las pestañas abiertas.
            principal.BeginInvoke(Sub()
                                      Try
                                          Using Msg.Cursor_(True)
                                              If cerrar Then
                                                  principal.CerrarTodas()
                                                  Sesion.CerrarContexto()
                                              End If
                                              Dim id As Integer = Bs.RestaurarEmpresa(archivo, nuevoCodigo)
                                              If cerrar Then Sesion.AbrirContexto(empresaActual, gestionActual)
                                          End Using
                                          Msg.Info("Restauración completada correctamente." & If(nuevoCodigo <> "", vbCrLf & "La nueva empresa aparece en Archivo > Cambiar empresa o gestión.", ""))
                                      Catch ex As Exception
                                          Msg.ErrorMsg(ex)
                                          If cerrar AndAlso Sesion.Ctx Is Nothing Then
                                              Try
                                                  Sesion.AbrirContexto(empresaActual, gestionActual)
                                              Catch
                                                  principal.CambiarEmpresaSolicitado = True
                                                  principal.Close()
                                              End Try
                                          End If
                                      End Try
                                  End Sub)
        End Using
    End Sub
End Class
