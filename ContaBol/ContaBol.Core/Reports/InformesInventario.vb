Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports ContaBol.Core.Reports.Catalogo

Namespace Reports

    ''' <summary>Ítems, kardex físico valorado, existencias, precios, vencimientos y movimientos de inventario.</summary>
    Public Module InformesInventario

        Public Sub Registrar(l As List(Of ReporteCat))
            Const M As String = Catalogo.ModInventarios
            l.Add(Rep("listado_items", "Listado de ítems", M, "INV.REPORTES", AddressOf ListadoItems, PBool("soloActivos", "Solo ítems activos", True)))
            l.Add(Rep("kardex_item", "Kardex físico valorado", M, "INV.REPORTES", AddressOf KardexItem, PRef("item", "Ítem", ParamTipo.Item, True), PRef("almacen", "Almacén (vacío = todos)", ParamTipo.Almacen), PDesde(), PHasta()))
            l.Add(Rep("existencias", "Existencias valoradas", M, "INV.REPORTES", AddressOf Existencias, PHasta(), PRef("almacen", "Almacén (vacío = todos)", ParamTipo.Almacen), PBool("soloStock", "Solo ítems con stock", True)))
            l.Add(Rep("sugerencia_compras", "Sugerencia de compras", M, "INV.REPORTES", AddressOf SugerenciaCompras))
            l.Add(Rep("por_vencer", "Productos vencidos y por vencer", M, "INV.REPORTES", AddressOf PorVencer, PFecha("hasta", "Vencimiento hasta", Function(c) CObj(Date.Today.AddDays(30))), PRef("almacen", "Almacén (vacío = todos)", ParamTipo.Almacen)))
            l.Add(Rep("lista_precios", "Lista de precios", M, "INV.REPORTES", AddressOf ListaPrecios, PLista("niveles", "Niveles", "A|Solo precio A", "ABC|Niveles A, B y C", "TODOS|Los siete niveles (A-G)")))
            l.Add(Rep("movimientos_inventario", "Movimientos de inventario", M, "INV.REPORTES", AddressOf MovimientosInventario, PDesde(), PHasta(), PLista("tipo", "Tipo", "|(Todos)", "COMP|Compras", "VENT|Ventas", "AJEN|Ajustes de entrada", "AJSA|Ajustes de salida", "STIN|Stock inicial", "TRAS|Traspasos", "PRMP|Consumo de materia prima", "PRPT|Producto terminado")))
        End Sub

        Public Function ListadoItems(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim rep As ReporteDef = Nuevo(ctx, "Listado de ítems", "", "")
            rep.Horizontal = True
            rep.Col("Código", 2).Col("Descripción", 6).Col("Un.", 0.9).Col("Tipo", 1.2).Col("Venc.", 0.8, Formato.Texto, Alinea.Centro).Col("Stock mín.", 1.5, Formato.Cantidad).Col("Stock actual", 1.6, Formato.Cantidad).Col("Costo prom.", 1.7, Formato.Monto).Col("Precio A", 1.6, Formato.Monto).Col("Estado", 1.2, Formato.Texto, Alinea.Centro)
            Dim unidades As New Dictionary(Of Integer, String)
            For Each u As DataRow In ctx.Db.Query("SELECT Id, Codigo FROM UnidadMedida").Rows
                unidades(u.GetI("Id")) = u.GetS("Codigo")
            Next
            For Each r As DataRow In New InventarioService(ctx).ListarItems("", p.Bool("soloActivos", True)).Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Descripcion"), If(unidades.ContainsKey(r.GetI("UnidadId")), unidades(r.GetI("UnidadId")), ""), If(r.GetF("EsServicio"), "Servicio", "Mercadería"),
                         If(r.GetF("ManejaVenc"), "Sí", ""), r.GetD("StockMin"), r.GetD("Stock"), r.GetD("CostoProm"), r.GetD("PrecioA"), If(r.GetF("Activo"), "Activo", "Inactivo"))
            Next
            rep.Notas.Add("Total de ítems: " & rep.Filas.Count)
            Return rep
        End Function

        Public Function KardexItem(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim inv As New InventarioService(ctx)
            Dim it As ItemDto = inv.ObtenerItem(p.Entero("item"))
            If it Is Nothing Then Throw New InvalidOperationException("Seleccione el ítem.")
            Dim alm As String = "Todos los almacenes"
            If p.Entero("almacen") <> 0 Then alm = ctx.Db.ScalarStr("SELECT Nombre FROM Almacen WHERE Id=@i", "i", p.Entero("almacen"))
            Dim rep As ReporteDef = Nuevo(ctx, "Kardex físico valorado", Rango(d, h), "BS")
            rep.Subtitulo = it.Codigo & " - " & it.Descripcion & "  ·  " & alm
            rep.Horizontal = True
            rep.Col("Fecha", 1.5, Formato.Fecha).Col("Documento", 1.5).Col("Detalle", 4).Col("Ent. cant.", 1.4, Formato.Cantidad).Col("Costo U.", 1.5, Formato.Monto).Col("Ent. total", 1.7, Formato.Monto).
                Col("Sal. cant.", 1.4, Formato.Cantidad).Col("Costo U.", 1.5, Formato.Monto).Col("Sal. total", 1.7, Formato.Monto).Col("Saldo cant.", 1.5, Formato.Cantidad).Col("Costo prom.", 1.5, Formato.Monto).Col("Saldo valor", 1.8, Formato.Monto)
            Dim te As Decimal, ts As Decimal, qe As Decimal, qs As Decimal
            Dim ult As KardexItemRow = Nothing
            For Each k In inv.Kardex(it.Id, p.Entero("almacen"), d, h)
                If k.Detalle = "SALDO INICIAL" Then
                    rep.Fila(Nothing, "", "SALDO INICIAL", Nothing, Nothing, Nothing, Nothing, Nothing, Nothing, k.SaldoCant, k.SaldoCosto, k.SaldoValor).Negrita = True
                Else
                    rep.Fila(k.Fecha, k.Documento, k.Detalle, If(k.EntCant <> 0D, CObj(k.EntCant), Nothing), If(k.EntCant <> 0D, CObj(k.EntCosto), Nothing), If(k.EntCant <> 0D, CObj(k.EntTotal), Nothing),
                             If(k.SalCant <> 0D, CObj(k.SalCant), Nothing), If(k.SalCant <> 0D, CObj(k.SalCosto), Nothing), If(k.SalCant <> 0D, CObj(k.SalTotal), Nothing), k.SaldoCant, k.SaldoCosto, k.SaldoValor)
                    te += k.EntTotal : ts += k.SalTotal : qe += k.EntCant : qs += k.SalCant
                End If
                ult = k
            Next
            rep.Total("", "", "TOTALES", qe, "", te, qs, "", ts, If(ult Is Nothing, 0D, ult.SaldoCant), "", If(ult Is Nothing, 0D, ult.SaldoValor))
            Return rep
        End Function

        Public Function Existencias(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim h As Date = p.Fecha("hasta")
            Dim alm As String = "Todos los almacenes"
            If p.Entero("almacen") <> 0 Then alm = ctx.Db.ScalarStr("SELECT Nombre FROM Almacen WHERE Id=@i", "i", p.Entero("almacen"))
            Dim rep As ReporteDef = Nuevo(ctx, "Existencias valoradas", "Al " & h.ToString("dd/MM/yyyy") & "  ·  " & alm, "BS")
            rep.Col("Código", 2).Col("Descripción", 6).Col("Un.", 1).Col("Existencia", 1.8, Formato.Cantidad).Col("Costo prom.", 1.8, Formato.Monto).Col("Valor total", 2.2, Formato.Monto)
            Dim tot As Decimal
            For Each r As DataRow In New InventarioService(ctx).Existencias(h, p.Entero("almacen"), p.Bool("soloStock", True)).Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Descripcion"), r.GetS("Unidad"), r.GetD("Stock"), r.GetD("CostoUnit"), r.GetD("Valor"))
                tot += r.GetD("Valor")
            Next
            rep.Total("", "TOTAL INVENTARIO", "", "", "", tot)
            Return rep
        End Function

        Public Function SugerenciaCompras(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim rep As ReporteDef = Nuevo(ctx, "Sugerencia de compras", "Ítems bajo el stock mínimo al " & Date.Today.ToString("dd/MM/yyyy"), "")
            rep.Col("Código", 2).Col("Descripción", 6).Col("Un.", 1).Col("Stock mínimo", 1.8, Formato.Cantidad).Col("Existencia", 1.8, Formato.Cantidad).Col("Cantidad a comprar", 2, Formato.Cantidad).Col("Costo prom.", 1.8, Formato.Monto)
            For Each r As DataRow In New InventarioService(ctx).SugerenciaCompras().Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Descripcion"), r.GetS("Unidad"), r.GetD("StockMin"), r.GetD("Stock"), r.GetD("Falta"), r.GetD("CostoUnit"))
            Next
            If rep.Filas.Count = 0 Then rep.Texto("Todos los ítems cuentan con stock sobre su mínimo.")
            Return rep
        End Function

        Public Function PorVencer(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Productos vencidos y por vencer", "Vencimiento hasta el " & h.ToString("dd/MM/yyyy"), "")
            rep.Col("Código", 2).Col("Descripción", 6).Col("Almacén", 3).Col("Vencimiento", 1.8, Formato.Fecha).Col("Cantidad", 1.8, Formato.Cantidad).Col("Días", 1.2, Formato.Entero)
            For Each r As DataRow In New InventarioService(ctx).PorVencer(h, p.Entero("almacen")).Rows
                Dim dias As Integer = r.GetI("Dias")
                rep.Fila(r.GetS("Codigo"), r.GetS("Descripcion"), r.GetS("Almacen"), r.GetDt("Vencimiento"), r.GetD("Cantidad"), dias).Negrita = dias < 0
            Next
            rep.Notas.Add("Días negativos = producto ya vencido.")
            Return rep
        End Function

        Public Function ListaPrecios(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim niv As String = p.Texto("niveles", "A")
            Dim rep As ReporteDef = Nuevo(ctx, "Lista de precios", "Vigente al " & Date.Today.ToString("dd/MM/yyyy"), "BS")
            rep.Col("Código", 2).Col("Descripción", 7).Col("Un.", 1)
            Dim letras As String = If(niv = "TODOS", "ABCDEFG", If(niv = "ABC", "ABC", "A"))
            For Each c As Char In letras
                rep.Col("Precio " & c, 1.8, Formato.Monto)
            Next
            Dim unidades As New Dictionary(Of Integer, String)
            For Each u As DataRow In ctx.Db.Query("SELECT Id, Codigo FROM UnidadMedida").Rows
                unidades(u.GetI("Id")) = u.GetS("Codigo")
            Next
            For Each r As DataRow In New InventarioService(ctx).ListarItems("", True).Rows
                Dim cel As New List(Of Object) From {r.GetS("Codigo"), r.GetS("Descripcion"), If(unidades.ContainsKey(r.GetI("UnidadId")), unidades(r.GetI("UnidadId")), "")}
                For Each c As Char In letras
                    cel.Add(r.GetD("Precio" & c))
                Next
                rep.Fila(cel.ToArray())
            Next
            If letras.Length > 3 Then rep.Horizontal = True
            Return rep
        End Function

        Public Function MovimientosInventario(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Movimientos de inventario", Rango(d, h), "BS")
            rep.Col("Documento", 1.6).Col("Fecha", 1.6, Formato.Fecha).Col("Tipo", 3).Col("Almacén", 2.5).Col("Detalle", 5).Col("Estado", 1.2, Formato.Texto, Alinea.Centro).Col("Total Bs", 2, Formato.Monto)
            Dim alm As New Dictionary(Of Integer, String)
            For Each a As DataRow In ctx.Db.Query("SELECT Id, Nombre FROM Almacen").Rows
                alm(a.GetI("Id")) = a.GetS("Nombre")
            Next
            Dim tot As Decimal
            For Each r As DataRow In New InventarioService(ctx).ListarMovimientos(d, h, p.Texto("tipo")).Rows
                Dim anul As Boolean = r.GetS("Estado") = "A"
                rep.Fila(r.GetS("Tipo") & "-" & r.GetS("Numero"), r.GetDt("Fecha"), InventarioService.NombreTipo(r.GetS("Tipo")), If(alm.ContainsKey(r.GetI("AlmacenId")), alm(r.GetI("AlmacenId")), ""), r.GetS("Detalle"), If(anul, "ANULADO", "Vigente"), r.GetD("TotalBs"))
                If Not anul Then tot += r.GetD("TotalBs")
            Next
            rep.Total("", "", "", "", "TOTAL (sin anulados)", "", tot)
            Return rep
        End Function

    End Module

End Namespace
