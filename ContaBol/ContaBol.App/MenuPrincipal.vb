Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Construye el menú principal y la barra de accesos rápidos.</summary>
Public Module MenuPrincipal

    Private Function Item(titulo As String, permiso As String, accion As Action, Optional atajo As Keys = Keys.None) As ToolStripMenuItem
        Dim m As New ToolStripMenuItem(titulo)
        If atajo <> Keys.None Then m.ShortcutKeys = atajo
        m.Enabled = permiso = "" OrElse Sesion.Puede(permiso)
        AddHandler m.Click, Sub(o, e)
                                Try
                                    accion()
                                Catch ex As Exception
                                    Msg.ErrorMsg(ex)
                                End Try
                            End Sub
        Return m
    End Function

    Private Function Rep(titulo As String, id As String, permiso As String) As ToolStripMenuItem
        Return Item(titulo, permiso, Sub() Informes.Abrir(id))
    End Function

    Private Function Sub_(titulo As String, ParamArray hijos() As ToolStripItem) As ToolStripMenuItem
        Dim m As New ToolStripMenuItem(titulo)
        m.DropDownItems.AddRange(hijos)
        Return m
    End Function

    Private Function Sep() As ToolStripSeparator
        Return New ToolStripSeparator()
    End Function

    Public Sub Construir(f As MainForm)
        Dim M As MenuStrip = f.Menu
        M.Items.Clear()

        Dim archivo As New ToolStripMenuItem("&Archivo")
        archivo.DropDownItems.AddRange({
            Item("Cambiar de empresa o gestión...", "", Sub()
                                                          f.CambiarEmpresaSolicitado = True
                                                          f.Close()
                                                      End Sub),
            Item("Nueva gestión (apertura)...", "ADM.GESTIONES", AddressOf AperturaGestion.Ejecutar),
            Item("Cerrar sesión", "", Sub()
                                          f.CerrarSesionSolicitado = True
                                          f.Close()
                                      End Sub),
            Sep(),
            Item("Cerrar pestaña actual", "", AddressOf f.CerrarActual, Keys.Control Or Keys.F4),
            Item("Salir", "", Sub()
                                  f.SalirSolicitado = True
                                  f.Close()
                              End Sub, Keys.Alt Or Keys.F4)})

        Dim cont As New ToolStripMenuItem("&Contabilidad")
        cont.DropDownItems.AddRange({
            Item("Plan de cuentas", "CONT.PLAN", Sub() Escritorio.Abrir(Of PlanCuentasForm)()),
            Item("Nuevo comprobante", "CONT.COMPROBANTES", Sub() Escritorio.AbrirNueva(New ComprobanteForm(), Nothing), Keys.Control Or Keys.N),
            Item("Comprobantes", "CONT.COMPROBANTES", Sub() Escritorio.Abrir(Of ComprobantesListaForm)()),
            Item("Tipos de cambio y UFV", "CONT.TIPOCAMBIO", Sub() Escritorio.Abrir(Of TipoCambioForm)()),
            Sep(),
            Sub_("Bancos",
                 Item("Conciliación bancaria", "CONT.BANCOS", Sub() Escritorio.Abrir(Of ConciliacionForm)()),
                 Rep("Libreta bancaria", "libreta_banco", "CONT.REPORTES")),
            Sub_("Centros de costo y presupuesto",
                 Item("Centros de costo", "CONT.CENTROS", Sub() Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.CentrosCosto()), "Catalogo.CentrosCosto")),
                 Item("Presupuesto", "CONT.PRESUPUESTO", Sub() Escritorio.Abrir(Of PresupuestoForm)()),
                 Rep("Ejecución presupuestaria", "ejecucion_presupuesto", "CONT.REPORTES"),
                 Rep("Gastos por centro de costo", "gastos_centros", "CONT.REPORTES")),
            Sep(),
            Item("Cierre y ajustes de gestión...", "CONT.AJUSTES", Sub() Escritorio.Abrir(Of CierreAjustesForm)()),
            Item("Consolidación de empresas...", "CONT.CONSOLIDAR", Sub() Escritorio.Abrir(Of ConsolidarForm)()),
            Item("Utilitarios contables...", "CONT.UTILES", Sub() Escritorio.Abrir(Of UtilitariosForm)())})

        Dim iva As New ToolStripMenuItem("&Libros IVA")
        iva.DropDownItems.AddRange({
            Item("Libro de compras (registro)", "IVA.COMPRAS", Sub() Escritorio.AbrirNueva(New FacturasIvaForm("C"), "FacturasIva.C")),
            Item("Libro de ventas (registro)", "IVA.VENTAS", Sub() Escritorio.AbrirNueva(New FacturasIvaForm("V"), "FacturasIva.V")),
            Sep(),
            Rep("Libro de compras IVA", "libro_compras", "IVA.REPORTES"),
            Rep("Libro de ventas IVA", "libro_ventas", "IVA.REPORTES"),
            Rep("Resumen mensual de IVA e IT", "resumen_iva", "IVA.REPORTES")})

        Dim com As New ToolStripMenuItem("C&omercial")
        com.DropDownItems.AddRange({
            Item("Clientes", "COM.TERCEROS", Sub() Escritorio.AbrirNueva(New TercerosForm("CXC"), "Terceros.CXC")),
            Item("Proveedores", "COM.TERCEROS", Sub() Escritorio.AbrirNueva(New TercerosForm("CXP"), "Terceros.CXP")),
            Sep(),
            Item("Nota de venta", "COM.VENTAS", Sub() Escritorio.AbrirNueva(New DocumentoForm(True), Nothing), Keys.F5),
            Item("Ventas realizadas", "COM.VENTAS", Sub() Escritorio.AbrirNueva(New DocumentosListaForm(True), "Docs.V")),
            Item("Nota de compra", "COM.COMPRAS", Sub() Escritorio.AbrirNueva(New DocumentoForm(False), Nothing), Keys.F6),
            Item("Compras realizadas", "COM.COMPRAS", Sub() Escritorio.AbrirNueva(New DocumentosListaForm(False), "Docs.C")),
            Sep(),
            Item("Cobros y pagos", "COM.COBROS", Sub() Escritorio.Abrir(Of CobroPagoForm)()),
            Sep(),
            Sub_("Reportes comerciales",
                 Rep("Saldos por cobrar / por pagar", "saldos_terceros", "COM.REPORTES"),
                 Rep("Kardex de cliente / proveedor", "kardex_tercero", "COM.REPORTES"),
                 Rep("Notas pendientes de cobro / pago", "documentos_pendientes", "COM.REPORTES"),
                 Rep("Ventas del período", "ventas_periodo", "COM.REPORTES"),
                 Rep("Compras del período", "compras_periodo", "COM.REPORTES"),
                 Rep("Cobros y pagos del período", "cobros_pagos", "COM.REPORTES"),
                 Rep("Productos más vendidos", "mas_vendidos", "COM.REPORTES"),
                 Rep("Mejores clientes", "mejores_clientes", "COM.REPORTES"),
                 Rep("Comisiones de vendedores", "comisiones", "COM.REPORTES"))})

        Dim inv As New ToolStripMenuItem("&Inventarios")
        inv.DropDownItems.AddRange({
            Item("Ítems y precios", "INV.ITEMS", Sub() Escritorio.Abrir(Of ItemsForm)()),
            Item("Ajustes, traspasos y stock inicial", "INV.MOVIMIENTOS", Sub() Escritorio.AbrirNueva(New MovimientoInvForm(), Nothing)),
            Item("Movimientos registrados", "INV.MOVIMIENTOS", Sub() Escritorio.Abrir(Of MovimientosListaForm)()),
            Sep(),
            Sub_("Tablas auxiliares",
                 Item("Almacenes", "INV.ITEMS", Sub() Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.Almacenes()), "Catalogo.Almacenes")),
                 Item("Unidades de medida", "INV.ITEMS", Sub() Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.Unidades()), "Catalogo.Unidades")),
                 Item("Grupos de ítems", "INV.ITEMS", Sub() Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.GruposItem()), "Catalogo.GruposItem")),
                 Item("Sucursales", "INV.ITEMS", Sub() Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.Sucursales()), "Catalogo.Sucursales")),
                 Item("Vendedores", "INV.ITEMS", Sub() Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.Vendedores()), "Catalogo.Vendedores"))),
            Sep(),
            Rep("Kardex físico valorado", "kardex_item", "INV.REPORTES"),
            Rep("Existencias valoradas", "existencias", "INV.REPORTES"),
            Rep("Lista de precios", "lista_precios", "INV.REPORTES"),
            Rep("Sugerencia de compras", "sugerencia_compras", "INV.REPORTES"),
            Rep("Productos vencidos y por vencer", "por_vencer", "INV.REPORTES"),
            Rep("Movimientos de inventario", "movimientos_inventario", "INV.REPORTES")})

        Dim af As New ToolStripMenuItem("Activos &fijos")
        af.DropDownItems.AddRange({
            Item("Registro de activos", "AF.ACTIVOS", Sub() Escritorio.Abrir(Of ActivosForm)()),
            Item("Depreciación y actualización", "AF.DEPRECIAR", Sub() Escritorio.Abrir(Of DepreciacionForm)()),
            Item("Grupos de activos", "AF.ACTIVOS", Sub() Escritorio.AbrirNueva(New CatalogoForm(CatalogoDef.GruposActivo()), "Catalogo.GruposActivo")),
            Sep(),
            Rep("Cuadro de activos fijos", "cuadro_activos", "AF.REPORTES"),
            Rep("Depreciación de un período", "depreciacion_periodo", "AF.REPORTES")})

        Dim rh As New ToolStripMenuItem("&Planillas")
        rh.DropDownItems.AddRange({
            Item("Empleados", "RH.EMPLEADOS", Sub() Escritorio.Abrir(Of EmpleadosForm)()),
            Item("Anticipos de sueldo", "RH.PLANILLA", Sub() Escritorio.Abrir(Of AnticiposForm)()),
            Item("Planilla de sueldos", "RH.PLANILLA", Sub() Escritorio.Abrir(Of PlanillaForm)()),
            Sep(),
            Rep("Planilla de sueldos y salarios", "planilla_sueldos", "RH.REPORTES"),
            Rep("Planilla RC-IVA", "planilla_rciva", "RH.REPORTES"),
            Rep("Boletas de pago", "boletas_pago", "RH.REPORTES"),
            Rep("Aportes laborales y patronales", "planilla_aportes", "RH.REPORTES"),
            Rep("Aguinaldo de navidad", "aguinaldo", "RH.REPORTES")})

        Dim cos As New ToolStripMenuItem("Cos&tos")
        cos.DropDownItems.AddRange({
            Item("Órdenes de producción", "COS.PRODUCCION", Sub() Escritorio.Abrir(Of ProduccionForm)()),
            Sep(),
            Rep("Órdenes de producción (listado)", "ordenes_produccion", "COS.REPORTES"),
            Rep("Hoja de costos", "hoja_costos", "COS.REPORTES")})

        Dim rpt As New ToolStripMenuItem("&Reportes")
        rpt.DropDownItems.AddRange({
            Item("Centro de reportes...", "", Sub() Escritorio.Abrir(Of CentroReportesForm)(), Keys.F9),
            Sep(),
            Rep("Libro diario", "libro_diario", "CONT.REPORTES"),
            Rep("Libro mayor", "libro_mayor", "CONT.REPORTES"),
            Rep("Balance de sumas y saldos", "sumas_saldos", "CONT.REPORTES"),
            Rep("Estado de resultados", "estado_resultados", "CONT.REPORTES"),
            Rep("Balance general", "balance_general", "CONT.REPORTES"),
            Rep("Flujo de efectivo", "flujo_efectivo", "CONT.REPORTES"),
            Rep("Índices financieros", "indices", "CONT.REPORTES")})

        Dim adm As New ToolStripMenuItem("A&dministración")
        adm.DropDownItems.AddRange({
            Item("Parámetros de la empresa", "ADM.PARAMETROS", Sub() Escritorio.Abrir(Of ParametrosForm)()),
            Item("Usuarios y permisos", "ADM.USUARIOS", Sub() Escritorio.Abrir(Of UsuariosForm)()),
            Item("Auditoría del sistema", "ADM.AUDITORIA", Sub() Escritorio.Abrir(Of AuditoriaForm)()),
            Sep(),
            Item("Copias de seguridad y restauración", "ADM.BACKUP", Sub() BackupForm.Mostrar()),
            Item("Importar desde Orion4...", "ADM.IMPORTAR", AddressOf ImportarOrion.Ejecutar)})

        Dim ayuda As New ToolStripMenuItem("A&yuda")
        ayuda.DropDownItems.Add(Item("Acerca de ContaBol", "", Sub()
                                                                  Using d As New AcercaDeForm()
                                                                      d.ShowDialog(f)
                                                                  End Using
                                                              End Sub))

        M.Items.AddRange({archivo, cont, iva, com, inv, af, rh, cos, rpt, adm, ayuda})
        For Each t As ToolStripMenuItem In M.Items
            t.ForeColor = Color.White
            For Each h As ToolStripItem In t.DropDownItems
                h.ForeColor = Tema.ColorTexto
            Next
        Next

        ' accesos rápidos
        f.Barra.Items.Clear()
        Dim acc = Sub(txt As String, permiso As String, a As Action)
                      Dim b As New ToolStripButton(txt) With {.DisplayStyle = ToolStripItemDisplayStyle.Text, .Enabled = permiso = "" OrElse Sesion.Puede(permiso), .ForeColor = Tema.Azul}
                      AddHandler b.Click, Sub(o, e)
                                              Try
                                                  a()
                                              Catch ex As Exception
                                                  Msg.ErrorMsg(ex)
                                              End Try
                                          End Sub
                      f.Barra.Items.Add(b)
                  End Sub
        acc("Comprobante", "CONT.COMPROBANTES", Sub() Escritorio.AbrirNueva(New ComprobanteForm(), Nothing))
        acc("Venta", "COM.VENTAS", Sub() Escritorio.AbrirNueva(New DocumentoForm(True), Nothing))
        acc("Compra", "COM.COMPRAS", Sub() Escritorio.AbrirNueva(New DocumentoForm(False), Nothing))
        acc("Libro de ventas", "IVA.VENTAS", Sub() Escritorio.AbrirNueva(New FacturasIvaForm("V"), "FacturasIva.V"))
        acc("Libro de compras", "IVA.COMPRAS", Sub() Escritorio.AbrirNueva(New FacturasIvaForm("C"), "FacturasIva.C"))
        acc("Ítems", "INV.ITEMS", Sub() Escritorio.Abrir(Of ItemsForm)())
        acc("Reportes", "", Sub() Escritorio.Abrir(Of CentroReportesForm)())
        acc("Respaldo", "ADM.BACKUP", Sub() BackupForm.Mostrar())
    End Sub
End Module
