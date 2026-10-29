Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports ContaBol.Core.Reports.Catalogo

Namespace Reports

    ''' <summary>Libros de compras y ventas IVA (formato LCV del SIN) y resumen mensual de impuestos.</summary>
    Public Module InformesIva

        Public Sub Registrar(l As List(Of ReporteCat))
            Const M As String = Catalogo.ModIva
            l.Add(Rep("libro_compras", "Libro de compras IVA", M, "IVA.REPORTES", AddressOf LibroCompras, PDesdeMes(), PHastaMes()))
            l.Add(Rep("libro_ventas", "Libro de ventas IVA", M, "IVA.REPORTES", AddressOf LibroVentas, PDesdeMes(), PHastaMes()))
            l.Add(Rep("resumen_iva", "Resumen mensual de IVA e IT", M, "IVA.REPORTES", AddressOf ResumenIva, PMes(), PDec("saldo_anterior", "Saldo de crédito fiscal del período anterior")))
        End Sub

        Private Function PDesdeMes() As ParamDef
            Return PFecha("desde", "Desde", Function(c) CObj(New Date(If(Date.Today >= c.Gestion.FechaInicio AndAlso Date.Today <= c.Gestion.FechaFin, Date.Today.Year, c.Gestion.FechaInicio.Year), If(Date.Today >= c.Gestion.FechaInicio AndAlso Date.Today <= c.Gestion.FechaFin, Date.Today.Month, c.Gestion.FechaInicio.Month), 1)))
        End Function

        Private Function PHastaMes() As ParamDef
            Return PFecha("hasta", "Hasta", Function(c) CObj(FinDeMes(If(Date.Today >= c.Gestion.FechaInicio AndAlso Date.Today <= c.Gestion.FechaFin, Date.Today, c.Gestion.FechaInicio))))
        End Function

        Public Function LibroCompras(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Libro de compras IVA", Rango(d, h), "BS")
            rep.Subtitulo = "Registro de compras (Ley 843 · RND 10-0016-07 y 102100000011)"
            rep.Horizontal = True
            rep.Col("Nº", 0.8, Formato.Entero).Col("Fecha factura", 1.6, Formato.Fecha).Col("NIT proveedor", 1.9).Col("Nombre o razón social", 4).Col("Nº autorización / CUF", 2.6).
                Col("Nº factura", 1.4).Col("Nº DUI/DIM", 1.3).Col("Importe total compra", 1.9, Formato.Monto).Col("Importe no sujeto a CF", 1.7, Formato.Monto).Col("Subtotal", 1.8, Formato.Monto).
                Col("Descuentos", 1.5, Formato.Monto).Col("Base CF", 1.8, Formato.Monto).Col("Crédito fiscal", 1.7, Formato.Monto).Col("Tipo", 0.8, Formato.Texto, Alinea.Centro)
            Dim n As Integer = 0
            Dim t(5) As Decimal
            For Each r As DataRow In New FacturaService(ctx).Listar("C", d, h).Rows
                n += 1
                Dim anulada As Boolean = r.GetS("Estado") = "A"
                Dim z As Func(Of String, Decimal) = Function(c) If(anulada, 0D, r.GetD(c))
                rep.Fila(n, r.GetDt("Fecha"), r.GetS("Nit"), r.GetS("RazonSocial") & If(anulada, " (ANULADA)", ""), r.GetS("Autorizacion"), r.GetS("NroFactura"), r.GetS("Dui"),
                         z("ImporteTotal"), z("NoSujeto"), z("Subtotal"), z("Descuento") + z("GiftCard"), z("BaseCf"), z("Impuesto"), If(r.GetS("TipoOp") = "", "1", r.GetS("TipoOp")))
                t(0) += z("ImporteTotal") : t(1) += z("NoSujeto") : t(2) += z("Subtotal") : t(3) += z("Descuento") + z("GiftCard") : t(4) += z("BaseCf") : t(5) += z("Impuesto")
            Next
            rep.Total(Nothing, Nothing, "", "TOTALES", "", "", "", t(0), t(1), t(2), t(3), t(4), t(5), "")
            rep.Notas.Add("Tipo de compra: 1 = compras para mercado interno con destino a actividades gravadas · 2 = no gravadas · 3 = exportaciones · 4 = gravadas y no gravadas · 5 = mercado interno y exportaciones.")
            rep.Firmas.AddRange({"Contador", "Representante Legal"})
            Return rep
        End Function

        Public Function LibroVentas(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Libro de ventas IVA", Rango(d, h), "BS")
            rep.Subtitulo = "Registro de ventas (Ley 843 · RND 10-0016-07 y 102100000011)"
            rep.Horizontal = True
            rep.Col("Nº", 0.8, Formato.Entero).Col("Fecha factura", 1.6, Formato.Fecha).Col("Nº factura", 1.4).Col("Nº autorización / CUF", 2.6).Col("NIT / CI cliente", 1.8).Col("Nombre o razón social", 3.8).
                Col("Importe total venta", 1.8, Formato.Monto).Col("No sujeto IVA", 1.5, Formato.Monto).Col("Export. y exentas", 1.5, Formato.Monto).Col("Tasa cero", 1.2, Formato.Monto).
                Col("Subtotal", 1.7, Formato.Monto).Col("Descuentos", 1.4, Formato.Monto).Col("Base DF", 1.7, Formato.Monto).Col("Débito fiscal", 1.6, Formato.Monto).Col("Est.", 0.8, Formato.Texto, Alinea.Centro)
            Dim n As Integer = 0
            Dim t(7) As Decimal
            For Each r As DataRow In New FacturaService(ctx).Listar("V", d, h).Rows
                n += 1
                Dim anulada As Boolean = r.GetS("Estado") <> "V" AndAlso r.GetS("Estado") <> "C"
                Dim z As Func(Of String, Decimal) = Function(c) If(anulada, 0D, r.GetD(c))
                rep.Fila(n, r.GetDt("Fecha"), r.GetS("NroFactura"), r.GetS("Autorizacion"), r.GetS("Nit"), r.GetS("RazonSocial"), z("ImporteTotal"), z("NoSujeto"), z("Exento"), z("TasaCero"),
                         z("Subtotal"), z("Descuento") + z("GiftCard"), z("BaseCf"), z("Impuesto"), r.GetS("Estado"))
                t(0) += z("ImporteTotal") : t(1) += z("NoSujeto") : t(2) += z("Exento") : t(3) += z("TasaCero") : t(4) += z("Subtotal") : t(5) += z("Descuento") + z("GiftCard") : t(6) += z("BaseCf") : t(7) += z("Impuesto")
            Next
            rep.Total(Nothing, Nothing, "", "", "", "TOTALES", t(0), t(1), t(2), t(3), t(4), t(5), t(6), t(7), "")
            rep.Notas.Add("Estado: V = válida · A = anulada · E = extraviada · N = no utilizada · C = emitida en contingencia. Las facturas no válidas se muestran con importes en cero.")
            rep.Firmas.AddRange({"Contador", "Representante Legal"})
            Return rep
        End Function

        Public Function ResumenIva(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim mes As Integer = p.Entero("mes", Date.Today.Month)
            Dim fs As New FacturaService(ctx)
            Dim rg As Tuple(Of Date, Date) = fs.RangoMes(mes)
            Dim rep As ReporteDef = Nuevo(ctx, "Resumen mensual de IVA e IT", NombreMes(mes) & " " & rg.Item1.Year, "BS")
            rep.Col("Concepto", 8).Col("Base / Importe", 2.6, Formato.Monto).Col("Impuesto", 2.6, Formato.Monto)
            Dim v = fs.Totales("V", rg.Item1, rg.Item2)
            Dim c = fs.Totales("C", rg.Item1, rg.Item2)
            rep.Grupo("IMPUESTO AL VALOR AGREGADO (IVA " & fs.IvaPct.ToString("0.##", FormatoVal.Cultura) & "%)")
            rep.Fila("Ventas facturadas del mes (base del débito fiscal)", v.Item1, v.Item2)
            rep.Fila("Compras facturadas del mes (base del crédito fiscal)", c.Item1, c.Item2)
            Dim dif As Decimal = v.Item2 - c.Item2
            rep.Subtotal("Débito fiscal menos crédito fiscal del mes", "", dif)
            Dim sa As Decimal = p.Dec("saldo_anterior")
            rep.Fila("(-) Saldo de crédito fiscal del período anterior", "", sa)
            Dim neto As Decimal = dif - sa
            rep.Total(If(neto >= 0D, "IVA A PAGAR (Formulario 200)", "SALDO A FAVOR PARA EL PRÓXIMO PERÍODO"), "", Math.Abs(neto))
            rep.Vacia()
            rep.Grupo("IMPUESTO A LAS TRANSACCIONES (IT " & fs.ItPct.ToString("0.##", FormatoVal.Cultura) & "%)")
            Dim itCta As Integer = ctx.CuentaParamOpcional(ParamKeys.CtaItPagar)
            Dim itMes As Decimal = 0D
            If itCta <> 0 Then
                Dim m As MayorResult = New LedgerService(ctx).Mayor(itCta, rg.Item1, rg.Item2, False)
                itMes = m.TotalHaber
            End If
            Dim ventasBrutas As Decimal = ctx.Db.ScalarDec("SELECT SUM(HaberBs) - SUM(DebeBs) FROM ComprobanteDet WHERE Vigente=1 AND Fecha >= @d AND Fecha <= @h AND CuentaId=@c", "d", rg.Item1, "h", rg.Item2, "c", ctx.CuentaParamOpcional(ParamKeys.CtaVentas))
            rep.Fila("Ingresos por ventas contabilizados en el mes", ventasBrutas, "")
            rep.Total("IT devengado en el mes (Formulario 400)", "", itMes)
            rep.Notas.Add("El débito y crédito fiscal se toman de los libros de ventas y compras IVA del mes; el IT, de los asientos de devengamiento. Verifique con sus declaraciones juradas.")
            rep.Firmas.AddRange({"Contador", "Representante Legal"})
            Return rep
        End Function

    End Module

End Namespace
