Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports ContaBol.Core.Reports.Catalogo

Namespace Reports

    ''' <summary>Clientes, proveedores, ventas, compras, cuentas por cobrar/pagar e historiales.</summary>
    Public Module InformesComerciales

        Public Sub Registrar(l As List(Of ReporteCat))
            Const M As String = Catalogo.ModComercial
            Dim clase As ParamDef = PLista("clase", "Cuenta corriente de", "CXC|Clientes (por cobrar)", "CXP|Proveedores (por pagar)")
            l.Add(Rep("kardex_tercero", "Kardex de cliente / proveedor", M, "COM.REPORTES", AddressOf KardexTercero, PLista("clase", "Cuenta corriente de", "CXC|Cliente (por cobrar)", "CXP|Proveedor (por pagar)"), PRef("tercero", "Cliente / proveedor", ParamTipo.Tercero, True), PDesde(), PHasta()))
            l.Add(Rep("saldos_terceros", "Saldos por cobrar / por pagar", M, "COM.REPORTES", AddressOf SaldosTerceros, PLista("clase", "Cuenta corriente de", "CXC|Clientes (por cobrar)", "CXP|Proveedores (por pagar)"), PHasta()))
            l.Add(Rep("documentos_pendientes", "Notas pendientes de cobro / pago", M, "COM.REPORTES", AddressOf DocumentosPendientes, PLista("clase", "Documentos de", "CXC|Ventas a crédito", "CXP|Compras a crédito"), PHasta(), PRef("tercero", "Cliente / proveedor (opcional)", ParamTipo.Tercero)))
            l.Add(Rep("listado_terceros", "Listado de clientes / proveedores", M, "COM.REPORTES", AddressOf ListadoTerceros, PLista("clase", "Listar", "CXC|Clientes", "CXP|Proveedores")))
            l.Add(Rep("ventas_periodo", "Ventas del período", M, "COM.REPORTES", AddressOf VentasPeriodo, PDesde(), PHasta(), PRef("tercero", "Cliente (opcional)", ParamTipo.Cliente), PLista("tipo", "Tipo", "|(Todas)", "CON|Contado", "CRE|Crédito")))
            l.Add(Rep("compras_periodo", "Compras del período", M, "COM.REPORTES", AddressOf ComprasPeriodo, PDesde(), PHasta(), PRef("tercero", "Proveedor (opcional)", ParamTipo.Proveedor), PLista("tipo", "Tipo", "|(Todas)", "CON|Contado", "CRE|Crédito")))
            l.Add(Rep("cobros_pagos", "Cobros y pagos del período", M, "COM.REPORTES", AddressOf CobrosPagos, PLista("clase", "Movimientos de", "CXC|Cobros a clientes", "CXP|Pagos a proveedores"), PDesde(), PHasta()))
            l.Add(Rep("mas_vendidos", "Productos más vendidos", M, "COM.REPORTES", AddressOf MasVendidos, PDesde(), PHasta(), PEnt("top", "Cantidad de ítems a listar", 20)))
            l.Add(Rep("mas_comprados", "Productos más comprados", M, "COM.REPORTES", AddressOf MasComprados, PDesde(), PHasta(), PEnt("top", "Cantidad de ítems a listar", 20)))
            l.Add(Rep("mejores_clientes", "Mejores clientes", M, "COM.REPORTES", AddressOf MejoresClientes, PDesde(), PHasta(), PEnt("top", "Cantidad a listar", 20)))
            l.Add(Rep("mejores_proveedores", "Mejores proveedores", M, "COM.REPORTES", AddressOf MejoresProveedores, PDesde(), PHasta(), PEnt("top", "Cantidad a listar", 20)))
            l.Add(Rep("comisiones", "Comisiones de vendedores", M, "COM.REPORTES", AddressOf Comisiones, PDesde(), PHasta()))
            l.Add(Rep("nota_venta", "Nota de venta (impresión)", M, "COM.REPORTES", AddressOf NotaVenta, PEnt("id", "Id de venta", 0)))
            l.Add(Rep("nota_compra", "Nota de compra (impresión)", M, "COM.REPORTES", AddressOf NotaCompra, PEnt("id", "Id de compra", 0)))
        End Sub

        Public Function KardexTercero(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim clase As String = p.Texto("clase", "CXC")
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim t As TerceroDto = New TerceroService(ctx).Obtener(p.Entero("tercero"))
            If t Is Nothing Then Throw New InvalidOperationException("Seleccione el cliente o proveedor.")
            Dim rep As ReporteDef = Nuevo(ctx, If(clase = "CXC", "Kardex de cliente", "Kardex de proveedor"), Rango(d, h), "BS")
            rep.Subtitulo = t.Codigo & " - " & t.Nombre & If(t.Nit <> "", "  (NIT " & t.Nit & ")", "")
            rep.Col("Fecha", 1.6, Formato.Fecha).Col("Tipo", 1, Formato.Texto, Alinea.Centro).Col("Referencia", 1.8).Col("Detalle", 6).Col("Débitos", 2, Formato.Monto).Col("Créditos", 2, Formato.Monto).Col("Saldo", 2.2, Formato.Monto)
            Dim td As Decimal, th As Decimal, saldo As Decimal
            For Each r In New TerceroService(ctx).Kardex(t.Id, clase, d, h)
                If r.Detalle = "SALDO ANTERIOR" Then
                    rep.Fila(Nothing, "", "", r.Detalle, Nothing, Nothing, r.Saldo).Negrita = True
                Else
                    rep.Fila(r.Fecha, r.Tipo, r.Referencia, r.Detalle, r.Debe, r.Haber, r.Saldo)
                    td += r.Debe : th += r.Haber
                End If
                saldo = r.Saldo
            Next
            rep.Total("", "", "", "TOTALES / SALDO FINAL", td, th, saldo)
            rep.Notas.Add(If(clase = "CXC", "Saldo positivo: el cliente adeuda a la empresa. Negativo: anticipo del cliente.", "Saldo positivo: la empresa adeuda al proveedor. Negativo: anticipo entregado."))
            Return rep
        End Function

        Public Function SaldosTerceros(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim clase As String = p.Texto("clase", "CXC")
            Dim h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, If(clase = "CXC", "Cuentas por cobrar", "Cuentas por pagar"), "Saldos al " & h.ToString("dd/MM/yyyy"), "BS")
            rep.Col("Código", 1.6).Col("Nombre / razón social", 6).Col("NIT", 2).Col("Débitos", 2, Formato.Monto).Col("Créditos", 2, Formato.Monto).Col("Saldo", 2.2, Formato.Monto)
            Dim tot As Decimal
            For Each r As DataRow In New TerceroService(ctx).SaldosPorTercero(clase, h).Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Nombre"), r.GetS("Nit"), r.GetD("Debe"), r.GetD("Haber"), r.GetD("Saldo"))
                tot += r.GetD("Saldo")
            Next
            rep.Total("", "TOTAL", "", "", "", tot)
            Return rep
        End Function

        Public Function DocumentosPendientes(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim clase As String = p.Texto("clase", "CXC")
            Dim h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, If(clase = "CXC", "Notas de venta pendientes de cobro", "Compras pendientes de pago"), "Al " & h.ToString("dd/MM/yyyy"), "BS")
            rep.Col("Documento", 1.8).Col("Fecha", 1.6, Formato.Fecha).Col("Vence", 1.6, Formato.Fecha).Col("Detalle", 5).Col("Importe", 2, Formato.Monto).Col("Saldo", 2, Formato.Monto).Col("Días", 1, Formato.Entero)
            Dim tabla As String = If(clase = "CXC", "Venta", "Compra")
            Dim col As String = If(clase = "CXC", "ClienteId", "ProveedorId")
            Dim sql As String = "SELECT d.*, t.Nombre AS Tercero FROM " & tabla & " d INNER JOIN Tercero t ON t.Id = d." & col & " WHERE d.Estado='V' AND d.SaldoBs > 0 AND d.Fecha <= @h"
            Dim args As New List(Of Object) From {"h", h.Date}
            If p.Entero("tercero") <> 0 Then
                sql &= " AND d." & col & "=@t"
                args.AddRange({"t", p.Entero("tercero")})
            End If
            Dim dt As DataTable = ctx.Db.Query(sql & " ORDER BY t.Nombre, d.Fecha", args.ToArray())
            Dim actual As String = Nothing
            Dim sub1 As Decimal, total As Decimal
            For Each r As DataRow In dt.Rows
                If actual <> r.GetS("Tercero") Then
                    If actual IsNot Nothing Then rep.Subtotal("", "", "", "Subtotal " & actual, "", sub1, "")
                    actual = r.GetS("Tercero")
                    sub1 = 0D
                    rep.Grupo(actual)
                End If
                Dim venc As Date = If(ToDateOrNull(r.Cell("Vencimiento")), r.GetDt("Fecha"))
                rep.Fila(r.GetS("Tipo") & "-" & r.GetS("Numero"), r.GetDt("Fecha"), venc, r.GetS("Detalle"), r.GetD("TotalBs"), r.GetD("SaldoBs"), Math.Max(0, CInt((h.Date - venc.Date).TotalDays)))
                sub1 += r.GetD("SaldoBs") : total += r.GetD("SaldoBs")
            Next
            If actual IsNot Nothing Then rep.Subtotal("", "", "", "Subtotal " & actual, "", sub1, "")
            rep.Total("", "", "", "TOTAL PENDIENTE", "", total, "")
            Return rep
        End Function

        Public Function ListadoTerceros(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim clase As String = p.Texto("clase", "CXC")
            Dim rep As ReporteDef = Nuevo(ctx, If(clase = "CXC", "Listado de clientes", "Listado de proveedores"), "", "")
            rep.Horizontal = True
            rep.Col("Código", 1.6).Col("Nombre / razón social", 5).Col("NIT", 2).Col("Dirección", 4).Col("Teléfono", 2).Col("Actividad", 3).Col("Límite crédito", 2, Formato.Monto).Col("Estado", 1.2, Formato.Texto, Alinea.Centro)
            For Each r As DataRow In New TerceroService(ctx).Listar(clase).Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Nombre"), r.GetS("Nit"), r.GetS("Direccion"), r.GetS("Telefono"), r.GetS("Actividad"), r.GetD("LimiteCredito"), If(r.GetF("Activo"), "Activo", "Inactivo"))
            Next
            rep.Notas.Add("Total de registros: " & rep.Filas.Count)
            Return rep
        End Function

        Private Function Documentos(ctx As Contexto, p As Parametros_, esVenta As Boolean) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, If(esVenta, "Ventas del período", "Compras del período"), Rango(d, h), "BS")
            rep.Horizontal = True
            rep.Col("Doc.", 1.6).Col("Fecha", 1.6, Formato.Fecha).Col(If(esVenta, "Cliente", "Proveedor"), 5).Col("Nº factura", 1.6).Col("Subtotal", 2, Formato.Monto).Col("Descuento", 1.6, Formato.Monto).Col("Recargo", 1.6, Formato.Monto).Col("Total", 2, Formato.Monto).
                Col(If(esVenta, "Débito fiscal", "Crédito fiscal"), 1.8, Formato.Monto).Col("Saldo", 2, Formato.Monto).Col("Estado", 1.2, Formato.Texto, Alinea.Centro)
            Dim dt As DataTable = If(esVenta, New VentaService(ctx).Listar(d, h, p.Entero("tercero")), New CompraService(ctx).Listar(d, h, p.Entero("tercero")))
            Dim nombre As String = If(esVenta, "Cliente", "Proveedor")
            Dim tipo As String = p.Texto("tipo")
            Dim s As Decimal, de As Decimal, r2 As Decimal, t As Decimal, im As Decimal, sa As Decimal
            Dim fiscal As Decimal
            For Each r As DataRow In dt.Rows
                If tipo <> "" AndAlso r.GetS("Tipo") <> tipo Then Continue For
                Dim anulada As Boolean = r.GetS("Estado") = "A"
                fiscal = If(esVenta, If(r.GetF("ConFactura"), Math.Round(r.GetD("TotalBs") * ctx.Param.Dec(ParamKeys.IvaPct, 13D) / 100D, 2), 0D), r.GetD("CreditoFiscalBs"))
                rep.Fila(r.GetS("Tipo") & "-" & r.GetS("Numero"), r.GetDt("Fecha"), r.GetS(nombre), r.GetS("NroFactura"), r.GetD("SubtotalBs"), r.GetD("DescuentoBs"), r.GetD("RecargoBs"), r.GetD("TotalBs"), fiscal, r.GetD("SaldoBs"), If(anulada, "ANULADA", "Vigente"))
                If Not anulada Then
                    s += r.GetD("SubtotalBs") : de += r.GetD("DescuentoBs") : r2 += r.GetD("RecargoBs") : t += r.GetD("TotalBs") : im += fiscal : sa += r.GetD("SaldoBs")
                End If
            Next
            rep.Total("", "", "TOTALES (sin anuladas)", "", s, de, r2, t, im, sa, "")
            Return rep
        End Function

        Public Function VentasPeriodo(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Documentos(ctx, p, True)
        End Function

        Public Function ComprasPeriodo(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Documentos(ctx, p, False)
        End Function

        Public Function CobrosPagos(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim clase As String = p.Texto("clase", "CXC")
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, If(clase = "CXC", "Cobros a clientes", "Pagos a proveedores"), Rango(d, h), "BS")
            rep.Col("Fecha", 1.6, Formato.Fecha).Col(If(clase = "CXC", "Cliente", "Proveedor"), 5).Col("Detalle", 5).Col("Importe", 2.2, Formato.Monto)
            Dim dt As DataTable = ctx.Db.Query("SELECT m.Fecha, t.Nombre, m.Detalle, m.Debe, m.Haber FROM MovTercero m INNER JOIN Tercero t ON t.Id = m.TerceroId WHERE m.Clase=@c AND m.Vigente=1 AND m.Tipo IN ('COB','PAG','ANT') AND m.Fecha >= @d AND m.Fecha <= @h ORDER BY m.Fecha, m.Id", "c", clase, "d", d.Date, "h", h.Date)
            Dim tot As Decimal
            For Each r As DataRow In dt.Rows
                Dim imp As Decimal = If(clase = "CXC", r.GetD("Haber"), r.GetD("Debe"))
                rep.Fila(r.GetDt("Fecha"), r.GetS("Nombre"), r.GetS("Detalle"), imp)
                tot += imp
            Next
            rep.Total("", "", "TOTAL", tot)
            Return rep
        End Function

        Private Function Ranking(ctx As Contexto, titulo As String, d As Date, h As Date, top As Integer, sql As String, etiqueta1 As String) As ReporteDef
            Dim rep As ReporteDef = Nuevo(ctx, titulo, Rango(d, h), "BS")
            rep.Col("Nº", 0.8, Formato.Entero).Col("Código", 2).Col(etiqueta1, 6).Col("Cantidad / Operaciones", 2.2, Formato.Cantidad).Col("Importe Bs", 2.4, Formato.Monto)
            Dim dt As DataTable = ctx.Db.Query(sql, "d", d.Date, "h", h.Date)
            Dim filas = dt.Rows.Cast(Of DataRow)().OrderByDescending(Function(r) r.GetD("T")).Take(Math.Max(1, top)).ToList()
            Dim n As Integer = 0
            Dim tq As Decimal, tt As Decimal
            For Each r In filas
                n += 1
                Dim cod As String = "", nom As String = ""
                If r.Table.Columns.Contains("ItemId") Then
                    Dim it As ItemDto = New InventarioService(ctx).ObtenerItem(r.GetI("ItemId"))
                    If it IsNot Nothing Then
                        cod = it.Codigo
                        nom = it.Descripcion
                    End If
                Else
                    Dim t As TerceroDto = New TerceroService(ctx).Obtener(r.GetI("TerceroId"))
                    If t IsNot Nothing Then
                        cod = t.Codigo
                        nom = t.Nombre
                    End If
                End If
                rep.Fila(n, cod, nom, r.GetD("Q"), r.GetD("T"))
                tq += r.GetD("Q") : tt += r.GetD("T")
            Next
            rep.Total("", "", "TOTAL", tq, tt)
            Return rep
        End Function

        Public Function MasVendidos(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Ranking(ctx, "Productos más vendidos", p.Fecha("desde"), p.Fecha("hasta"), p.Entero("top", 20),
                           "SELECT d.ItemId, SUM(d.Cantidad) AS Q, SUM(d.ImporteBs) AS T FROM VentaDet d INNER JOIN Venta v ON v.Id = d.VentaId WHERE v.Estado='V' AND v.Fecha >= @d AND v.Fecha <= @h GROUP BY d.ItemId", "Producto")
        End Function

        Public Function MasComprados(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Ranking(ctx, "Productos más comprados", p.Fecha("desde"), p.Fecha("hasta"), p.Entero("top", 20),
                           "SELECT d.ItemId, SUM(d.Cantidad) AS Q, SUM(d.ImporteBs) AS T FROM CompraDet d INNER JOIN Compra v ON v.Id = d.CompraId WHERE v.Estado='V' AND v.Fecha >= @d AND v.Fecha <= @h GROUP BY d.ItemId", "Producto")
        End Function

        Public Function MejoresClientes(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Ranking(ctx, "Mejores clientes", p.Fecha("desde"), p.Fecha("hasta"), p.Entero("top", 20),
                           "SELECT ClienteId AS TerceroId, COUNT(*) AS Q, SUM(TotalBs) AS T FROM Venta WHERE Estado='V' AND Fecha >= @d AND Fecha <= @h GROUP BY ClienteId", "Cliente")
        End Function

        Public Function MejoresProveedores(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Ranking(ctx, "Mejores proveedores", p.Fecha("desde"), p.Fecha("hasta"), p.Entero("top", 20),
                           "SELECT ProveedorId AS TerceroId, COUNT(*) AS Q, SUM(TotalBs) AS T FROM Compra WHERE Estado='V' AND Fecha >= @d AND Fecha <= @h GROUP BY ProveedorId", "Proveedor")
        End Function

        Public Function Comisiones(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Comisiones de vendedores", Rango(d, h), "BS")
            rep.Col("Vendedor", 6).Col("Ventas", 1.4, Formato.Entero).Col("Importe vendido", 2.4, Formato.Monto).Col("% Comisión", 1.6, Formato.Porcentaje).Col("Comisión", 2.4, Formato.Monto)
            Dim dt As DataTable = ctx.Db.Query("SELECT VendedorId, COUNT(*) AS N, SUM(TotalBs) AS T FROM Venta WHERE Estado='V' AND Fecha >= @d AND Fecha <= @h AND VendedorId IS NOT NULL GROUP BY VendedorId", "d", d.Date, "h", h.Date)
            Dim tt As Decimal, tc As Decimal
            For Each r As DataRow In dt.Rows
                Dim v As DataTable = ctx.Db.Query("SELECT Nombre, ComisionPct FROM Vendedor WHERE Id=@i", "i", r.GetI("VendedorId"))
                If v.Rows.Count = 0 Then Continue For
                Dim pct As Decimal = v.Rows(0).GetD("ComisionPct")
                Dim com As Decimal = (r.GetD("T") * pct / 100D).R2()
                rep.Fila(v.Rows(0).GetS("Nombre"), r.GetI("N"), r.GetD("T"), pct, com)
                tt += r.GetD("T") : tc += com
            Next
            rep.Total("TOTAL", "", tt, "", tc)
            Return rep
        End Function

        Private Function Nota(ctx As Contexto, esVenta As Boolean, id As Integer) As ReporteDef
            Dim tabla As String = If(esVenta, "Venta", "Compra")
            Dim dt As DataTable = ctx.Db.Query("SELECT d.*, t.Nombre AS Tercero, t.Nit AS TNit, t.Direccion AS TDir FROM " & tabla & " d INNER JOIN Tercero t ON t.Id = d." & If(esVenta, "ClienteId", "ProveedorId") & " WHERE d.Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Throw New InvalidOperationException("Documento inexistente.")
            Dim r As DataRow = dt.Rows(0)
            Dim rep As ReporteDef = Nuevo(ctx, If(esVenta, "Nota de venta ", "Nota de compra ") & r.GetS("Tipo") & "-" & r.GetS("Numero"), "", "")
            rep.Moneda = If(r.GetS("Moneda") = "USD", "(Documento en dólares - T.C. " & ToDec(r("TC")).ToString("0.00", FormatoVal.Cultura) & "; importes en Bs)", "(Expresado en Bolivianos)")
            rep.Cabecera.Add(New KeyValuePair(Of String, String)(If(esVenta, "Cliente:", "Proveedor:"), r.GetS("Tercero")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Fecha:", r.GetDt("Fecha").ToString("dd/MM/yyyy")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("NIT / CI:", r.GetS("TNit")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Condición:", If(r.GetS("Tipo") = "CON", "Contado", "Crédito")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Dirección:", r.GetS("TDir")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Factura Nº:", If(r.GetF("ConFactura"), r.GetS("NroFactura"), "Sin factura")))
            If r.GetS("Detalle") <> "" Then rep.Cabecera.Add(New KeyValuePair(Of String, String)("Detalle:", r.GetS("Detalle")))
            If r.GetS("Estado") = "A" Then rep.Cabecera.Add(New KeyValuePair(Of String, String)("Estado:", "*** ANULADO ***"))
            rep.Col("Código", 2).Col("Descripción", 7).Col("Cantidad", 1.8, Formato.Cantidad).Col("P. unitario", 2, Formato.Monto).Col("Importe Bs", 2.2, Formato.Monto)
            Dim det As DataTable = If(esVenta, New VentaService(ctx).Detalle(id), New CompraService(ctx).Detalle(id))
            For Each x As DataRow In det.Rows
                rep.Fila(x.GetS("Codigo"), x.GetS("Descripcion"), x.GetD("Cantidad"), x.GetD("PrecioUnit"), x.GetD("ImporteBs"))
            Next
            rep.Subtotal("", "", "", "Subtotal", r.GetD("SubtotalBs"))
            If r.GetD("DescuentoBs") <> 0D Then rep.Fila("", "", "", "Descuento", -r.GetD("DescuentoBs"))
            If r.GetD("RecargoBs") <> 0D Then rep.Fila("", "", "", "Recargo", r.GetD("RecargoBs"))
            rep.Total("", "", "", "TOTAL", r.GetD("TotalBs"))
            If r.GetD("AnticipoBs") <> 0D Then rep.Fila("", "", "", "Anticipo aplicado", -r.GetD("AnticipoBs"))
            If r.GetS("Tipo") = "CRE" Then
                rep.Fila("", "", "", "A cuenta", -r.GetD("ACuentaBs"))
                rep.Subtotal("", "", "", "SALDO", r.GetD("SaldoBs"))
            End If
            rep.Texto("Son: " & NumeroLetras.Importe(r.GetD("TotalBs"), "BS")).Negrita = True
            rep.Firmas.AddRange(If(esVenta, {"Entregué conforme", "Recibí conforme"}, {"Recibido por", "Autorizado por"}))
            rep.NombreArchivo = "Nota_" & r.GetS("Tipo") & "_" & r.GetS("Numero")
            Return rep
        End Function

        Public Function NotaVenta(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Nota(ctx, True, p.Entero("id"))
        End Function

        Public Function NotaCompra(ctx As Contexto, p As Parametros_) As ReporteDef
            Return Nota(ctx, False, p.Entero("id"))
        End Function

    End Module

End Namespace
