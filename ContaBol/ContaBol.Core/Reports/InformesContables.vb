Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports ContaBol.Core.Reports.Catalogo

Namespace Reports

    ''' <summary>Libros contables, estados financieros, comprobantes, bancos, presupuesto y auditoría.</summary>
    Public Module InformesContables

        Public Sub Registrar(l As List(Of ReporteCat))
            Const M As String = Catalogo.ModContabilidad
            l.Add(Rep("plan_cuentas", "Plan de cuentas", M, "CONT.REPORTES", AddressOf PlanCuentas, PNivel(), PBool("soloMov", "Solo cuentas de movimiento")))
            l.Add(Rep("libro_diario", "Libro diario", M, "CONT.REPORTES", AddressOf LibroDiario, PDesde(), PHasta(), PMoneda(), PLista("tipo", "Tipo de comprobante", "|(Todos)", "I|Ingreso", "E|Egreso", "T|Traspaso", "AP|Apertura", "AJ|Ajuste", "CI|Cierre")))
            l.Add(Rep("libro_mayor", "Libro mayor de una cuenta", M, "CONT.REPORTES", AddressOf LibroMayor, PRef("cuenta", "Cuenta", ParamTipo.Cuenta, True), PDesde(), PHasta(), PMoneda(False)))
            l.Add(Rep("mayor_general", "Libro mayor (varias cuentas)", M, "CONT.REPORTES", AddressOf MayorGeneral, PTxt("desde_cod", "Cuenta desde (código)"), PTxt("hasta_cod", "Cuenta hasta (código)"), PDesde(), PHasta(), PMoneda(False)))
            l.Add(Rep("sumas_saldos", "Balance de sumas y saldos", M, "CONT.REPORTES", AddressOf SumasSaldos, PDesde(), PHasta(), PNivel(), PMoneda(False), PBool("soloMov", "Solo cuentas con movimiento", True)))
            l.Add(Rep("estado_resultados", "Estado de resultados", M, "CONT.REPORTES", AddressOf EstadoResultados, PDesde(), PHasta(), PNivel(), PMoneda(), PLista("formato", "Formato", "C|Comercial (utilidad bruta y operativa)", "I|Ingresos - Egresos")))
            l.Add(Rep("balance_general", "Balance general", M, "CONT.REPORTES", AddressOf BalanceGeneral, PHasta(), PNivel(), PMoneda()))
            l.Add(Rep("estado_cuentas", "Estado de cuentas (saldos por grupo)", M, "CONT.REPORTES", AddressOf EstadoCuentas, PTxt("prefijo", "Código de cuenta o grupo", "1.1.1"), PHasta(), PMoneda()))
            l.Add(Rep("flujo_efectivo", "Flujo de efectivo", M, "CONT.REPORTES", AddressOf FlujoEfectivo, PDesde(), PHasta()))
            l.Add(Rep("evolucion_patrimonio", "Evolución del patrimonio neto", M, "CONT.REPORTES", AddressOf EvolucionPatrimonio, PDesde(), PHasta()))
            l.Add(Rep("indices", "Índices financieros", M, "CONT.REPORTES", AddressOf Indices, PHasta()))
            l.Add(Rep("lista_comprobantes", "Listado de comprobantes", M, "CONT.REPORTES", AddressOf ListaComprobantes, PDesde(), PHasta(), PLista("tipo", "Tipo de comprobante", "|(Todos)", "I|Ingreso", "E|Egreso", "T|Traspaso", "AP|Apertura", "AJ|Ajuste", "CI|Cierre"), PBool("anulados", "Incluir anulados", True)))
            l.Add(Rep("comprobante", "Comprobante (impresión)", M, "CONT.REPORTES", AddressOf ComprobanteImpreso, PRef("id", "Comprobante", ParamTipo.Comprobante, True)))
            l.Add(Rep("comprobantes_rango", "Reimpresión de comprobantes por rango", M, "CONT.REPORTES", AddressOf ComprobantesRango, PLista("tipo", "Tipo de comprobante", "I|Ingreso", "E|Egreso", "T|Traspaso", "AP|Apertura", "AJ|Ajuste", "CI|Cierre"), PMes(), PEnt("desde_n", "Desde el Nº", 1), PEnt("hasta_n", "Hasta el Nº", 9999)))
            l.Add(Rep("libreta_banco", "Libreta bancaria", M, "CONT.REPORTES", AddressOf LibretaBanco, PRef("cuenta", "Cuenta bancaria", ParamTipo.CuentaBanco, True), PDesde(), PHasta()))
            l.Add(Rep("conciliacion", "Conciliación bancaria", M, "CONT.REPORTES", AddressOf Conciliacion, PRef("cuenta", "Cuenta bancaria", ParamTipo.CuentaBanco, True), PHasta(), PDec("extracto", "Saldo según extracto bancario")))
            l.Add(Rep("presupuesto", "Presupuesto asignado", M, "CONT.REPORTES", AddressOf PresupuestoAsignado))
            l.Add(Rep("ejecucion_presupuesto", "Ejecución presupuestaria", M, "CONT.REPORTES", AddressOf EjecucionPresupuesto, PMes("Hasta el mes")))
            l.Add(Rep("gastos_centros", "Gastos por centro de costo", M, "CONT.REPORTES", AddressOf GastosCentros, PDesde(), PHasta()))
            l.Add(Rep("tipos_cambio", "Tipos de cambio y UFV", M, "CONT.REPORTES", AddressOf TiposCambio, PDesde(), PHasta()))
            l.Add(Rep("auditoria", "Auditoría del sistema", Catalogo.ModAdmin, "ADM.AUDITORIA", AddressOf Auditoria, PDesde(), PHasta()))
        End Sub

        ' ---------- utilitarios ----------
        Private Function UsdDe(moneda As String) As Boolean
            Return moneda = "USD"
        End Function

        Private Function Ancestro(ctx As Contexto, cuentaId As Integer, nivel As Integer) As DataRow
            Dim r As DataRow = ctx.CuentaPorId(cuentaId)
            Dim guard As Integer = 0
            While r IsNot Nothing AndAlso r.GetI("Nivel") > nivel AndAlso guard < 20
                r = ctx.CuentaPorId(r.GetI("PadreId"))
                guard += 1
            End While
            Return r
        End Function

        Private Function ParteCodigo(rep As ReporteDef, ctx As Contexto) As ReporteDef
            Return rep
        End Function

        Private Function Sangria(b As BalanceRow) As Integer
            Return Math.Max(0, b.Nivel - 1)
        End Function

        ' ---------- Plan de cuentas ----------
        Public Function PlanCuentas(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim rep As ReporteDef = Nuevo(ctx, "Plan de cuentas", "", "")
            rep.Col("Código", 2.4).Col("Descripción", 7).Col("Rubro", 1.3).Col("Mov.", 0.8, Formato.Texto, Alinea.Centro).Col("Moneda", 1, Formato.Texto, Alinea.Centro).Col("Ajust.", 0.9, Formato.Texto, Alinea.Centro).Col("Presup.", 0.9, Formato.Texto, Alinea.Centro).Col("Costo", 0.9, Formato.Texto, Alinea.Centro)
            Dim nivelMax As Integer = p.Entero("nivel", 9)
            Dim rubros As String() = {"", "Activo", "Pasivo", "Patrimonio", "Ingreso", "Egreso", "Orden deudora", "Orden acreedora"}
            For Each c As DataRow In ctx.Cuentas().Rows
                If Not c.GetF("Activa") Then Continue For
                If c.GetI("Nivel") > nivelMax Then Continue For
                If p.Bool("soloMov") AndAlso Not c.GetF("EsMovimiento") Then Continue For
                Dim f As FilaRep = rep.Fila(c.GetS("Codigo"), c.GetS("Nombre"), If(c.GetI("Rubro") < rubros.Length, rubros(c.GetI("Rubro")), ""), If(c.GetF("EsMovimiento"), "Sí", ""),
                                            If(c.GetS("Moneda") = "USD", "$us", "Bs"), If(c.GetF("Ajustable"), "Sí", ""), If(c.GetF("Presupuestable"), "Sí", ""), c.GetS("CostoTipo"))
                f.Nivel = c.GetI("Nivel") - 1
                f.Negrita = Not c.GetF("EsMovimiento")
            Next
            rep.Notas.Add("Total de cuentas: " & rep.Filas.Count)
            Return rep
        End Function

        ' ---------- Libro diario ----------
        Public Function LibroDiario(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim moneda As String = p.Texto("moneda", "BS")
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Libro diario", Rango(d, h), moneda)
            Dim led As New LedgerService(ctx)
            Dim tipo As String = p.Texto("tipo")
            Dim bs As List(Of DiarioRow) = led.Diario(d, h, False, tipo)
            Dim us As List(Of DiarioRow) = If(moneda = "BS", Nothing, led.Diario(d, h, True, tipo))
            rep.Col("Código", 2.2).Col("Cuenta / Glosa", 6)
            If moneda = "BS" Then
                rep.Col("Debe Bs", 2, Formato.Monto).Col("Haber Bs", 2, Formato.Monto)
            ElseIf moneda = "USD" Then
                rep.Col("Debe $us", 2, Formato.Monto).Col("Haber $us", 2, Formato.Monto)
            Else
                rep.Col("Debe Bs", 2, Formato.Monto).Col("Haber Bs", 2, Formato.Monto).Col("Debe $us", 2, Formato.Monto).Col("Haber $us", 2, Formato.Monto)
                rep.Horizontal = True
            End If
            Dim fuente As List(Of DiarioRow) = If(moneda = "USD", us, bs)
            Dim idx As Integer = 0
            Dim actual As Integer = -1
            Dim sd As Decimal, sh As Decimal, sdu As Decimal, shu As Decimal
            Dim td As Decimal, th As Decimal, tdu As Decimal, thu As Decimal
            Dim cerrar = Sub()
                             If actual = -1 Then Return
                             If moneda = "AMBAS" Then
                                 rep.Subtotal("", "Suma del comprobante", sd, sh, sdu, shu)
                             Else
                                 rep.Subtotal("", "Suma del comprobante", sd, sh)
                             End If
                             sd = 0D : sh = 0D : sdu = 0D : shu = 0D
                         End Sub
            For Each r As DiarioRow In fuente
                If r.ComprobanteId <> actual Then
                    cerrar()
                    actual = r.ComprobanteId
                    rep.Grupo(r.Comprobante & "   " & r.Fecha.ToString("dd/MM/yyyy") & "   " & r.GlosaComprobante)
                End If
                Dim lin As String = r.CuentaNombre & If(r.Glosa <> "" AndAlso r.Glosa <> r.GlosaComprobante, "  -  " & r.Glosa, "")
                If moneda = "AMBAS" Then
                    Dim u As DiarioRow = If(idx < us.Count, us(idx), Nothing)
                    Dim du As Decimal = If(u Is Nothing, 0D, u.Debe), hu As Decimal = If(u Is Nothing, 0D, u.Haber)
                    rep.Fila(r.CuentaCodigo, lin, r.Debe, r.Haber, du, hu)
                    sdu += du : shu += hu : tdu += du : thu += hu
                Else
                    rep.Fila(r.CuentaCodigo, lin, r.Debe, r.Haber)
                End If
                sd += r.Debe : sh += r.Haber : td += r.Debe : th += r.Haber
                idx += 1
            Next
            cerrar()
            If moneda = "AMBAS" Then
                rep.Total("", "TOTAL GENERAL", td, th, tdu, thu)
            Else
                rep.Total("", "TOTAL GENERAL", td, th)
            End If
            Return rep
        End Function

        ' ---------- Libro mayor ----------
        Private Sub FilasMayor(rep As ReporteDef, m As MayorResult, incluirTitulo As Boolean)
            If incluirTitulo Then rep.Grupo(m.Codigo & "  " & m.Nombre)
            rep.Fila("", "", "SALDO ANTERIOR", Nothing, Nothing, m.SaldoAnterior).Negrita = True
            For Each x As MayorMov In m.Movimientos
                rep.Fila(x.Fecha, x.Comprobante, x.Glosa, x.Debe, x.Haber, x.Saldo)
            Next
            rep.Subtotal("", "", "TOTAL MOVIMIENTO / SALDO FINAL", m.TotalDebe, m.TotalHaber, m.SaldoFinal)
        End Sub

        Private Sub ColsMayor(rep As ReporteDef, usd As Boolean)
            Dim s As String = If(usd, " $us", " Bs")
            rep.Col("Fecha", 1.5, Formato.Fecha).Col("Comprob.", 1.6).Col("Glosa", 6).Col("Debe" & s, 2, Formato.Monto).Col("Haber" & s, 2, Formato.Monto).Col("Saldo" & s, 2.2, Formato.Monto)
        End Sub

        Public Function LibroMayor(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim usd As Boolean = UsdDe(p.Texto("moneda", "BS"))
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Libro mayor", Rango(d, h), If(usd, "USD", "BS"))
            ColsMayor(rep, usd)
            Dim m As MayorResult = New LedgerService(ctx).Mayor(p.Entero("cuenta"), d, h, usd)
            rep.Subtitulo = m.Codigo & " - " & m.Nombre
            FilasMayor(rep, m, False)
            rep.Notas.Add("Saldo en el sentido natural de la cuenta (" & If(m.Naturaleza = "D", "deudora", "acreedora") & ").")
            Return rep
        End Function

        Public Function MayorGeneral(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim usd As Boolean = UsdDe(p.Texto("moneda", "BS"))
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Libro mayor", Rango(d, h), If(usd, "USD", "BS"))
            ColsMayor(rep, usd)
            Dim cd As String = p.Texto("desde_cod").Trim(), ch As String = p.Texto("hasta_cod").Trim()
            Dim led As New LedgerService(ctx)
            Dim n As Integer = 0
            For Each c As DataRow In ctx.Cuentas().Rows
                If Not c.GetF("EsMovimiento") OrElse Not c.GetF("Activa") Then Continue For
                Dim cod As String = c.GetS("Codigo")
                If cd <> "" AndAlso String.CompareOrdinal(cod, cd) < 0 Then Continue For
                If ch <> "" AndAlso String.CompareOrdinal(cod, ch) > 0 AndAlso Not cod.StartsWith(ch, StringComparison.Ordinal) Then Continue For
                Dim m As MayorResult = led.Mayor(c.GetI("Id"), d, h, usd)
                If m.Movimientos.Count = 0 AndAlso m.SaldoAnterior = 0D Then Continue For
                FilasMayor(rep, m, True)
                rep.Vacia()
                n += 1
            Next
            rep.Notas.Add("Cuentas con movimiento: " & n)
            Return rep
        End Function

        ' ---------- Sumas y saldos ----------
        Public Function SumasSaldos(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim usd As Boolean = UsdDe(p.Texto("moneda", "BS"))
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Balance de sumas y saldos", Rango(d, h), If(usd, "USD", "BS"))
            Dim filas As List(Of BalanceRow) = New LedgerService(ctx).Balance(d, h, usd, p.Entero("nivel", 9), p.Bool("soloMov", True))
            Dim conAnt As Boolean = filas.Any(Function(b) b.AntD <> 0D OrElse b.AntH <> 0D)
            rep.Col("Código", 2.3).Col("Cuenta", 5.5)
            If conAnt Then rep.Col("Saldo ant. Deudor", 1.9, Formato.Monto).Col("Saldo ant. Acreedor", 1.9, Formato.Monto)
            rep.Col("Sumas Debe", 1.9, Formato.Monto).Col("Sumas Haber", 1.9, Formato.Monto).Col("Saldo Deudor", 1.9, Formato.Monto).Col("Saldo Acreedor", 1.9, Formato.Monto)
            If conAnt Then rep.Horizontal = True
            Dim tAD As Decimal, tAH As Decimal, tD As Decimal, tH As Decimal, tSD As Decimal, tSH As Decimal
            For Each b In filas
                Dim cel As New List(Of Object) From {b.Codigo, b.Nombre}
                If conAnt Then
                    cel.Add(b.AntD)
                    cel.Add(b.AntH)
                End If
                cel.AddRange({b.Debe, b.Haber, b.SaldoD, b.SaldoH})
                Dim f As FilaRep = rep.Fila(cel.ToArray())
                f.Nivel = Sangria(b)
                f.Negrita = Not b.EsMovimiento
                If b.EsMovimiento Then
                    tAD += b.AntD : tAH += b.AntH : tD += b.Debe : tH += b.Haber : tSD += b.SaldoD : tSH += b.SaldoH
                End If
            Next
            Dim tot As New List(Of Object) From {"", "TOTALES"}
            If conAnt Then tot.AddRange({tAD, tAH})
            tot.AddRange({tD, tH, tSD, tSH})
            rep.Total(tot.ToArray())
            If tSD <> tSH OrElse tD <> tH Then rep.Notas.Add("ATENCIÓN: las sumas no cuadran. Revise los comprobantes.")
            Return rep
        End Function

        ' ---------- Estados financieros ----------
        Private Sub AgregarFs(rep As ReporteDef, bs As EstadoFinanciero, us As EstadoFinanciero, ambas As Boolean)
            Dim dic As Dictionary(Of String, FsLine) = Nothing
            If ambas AndAlso us IsNot Nothing Then
                dic = New Dictionary(Of String, FsLine)
                For Each l In us.Lineas
                    dic(l.Codigo & "|" & l.Texto) = l
                Next
            End If
            For Each l In bs.Lineas
                Dim usv As Object = Nothing
                If dic IsNot Nothing Then
                    Dim x As FsLine = Nothing
                    If dic.TryGetValue(l.Codigo & "|" & l.Texto, x) AndAlso x.ConImporte Then usv = x.Importe
                End If
                Dim imp As Object = If(l.ConImporte, CObj(l.Importe), Nothing)
                Dim f As FilaRep
                Select Case l.Tipo
                    Case "T"
                        If l.Codigo = "" Then
                            f = rep.Grupo(l.Texto)
                        Else
                            f = If(ambas, rep.Fila(l.Codigo, l.Texto, imp, usv), rep.Fila(l.Codigo, l.Texto, imp))
                            f.Negrita = True
                            f.Nivel = Math.Max(0, l.Nivel - 1)
                        End If
                    Case "S"
                        f = If(ambas, rep.Subtotal("", l.Texto, imp, usv), rep.Subtotal("", l.Texto, imp))
                    Case "R"
                        f = If(ambas, rep.Total("", l.Texto, imp, usv), rep.Total("", l.Texto, imp))
                    Case Else
                        f = If(ambas, rep.Fila(l.Codigo, l.Texto, imp, usv), rep.Fila(l.Codigo, l.Texto, imp))
                        f.Nivel = Math.Max(0, l.Nivel - 1)
                End Select
            Next
        End Sub

        Public Function EstadoResultados(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim moneda As String = p.Texto("moneda", "BS")
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Estado de resultados", Rango(d, h), moneda)
            Dim led As New LedgerService(ctx)
            Dim niv As Integer = p.Entero("nivel", 9)
            Dim fmt As String = p.Texto("formato", "C")
            Dim ambas As Boolean = moneda = "AMBAS"
            Dim bs As EstadoFinanciero = led.EstadoResultados(d, h, moneda = "USD", niv, fmt)
            Dim us As EstadoFinanciero = If(ambas, led.EstadoResultados(d, h, True, niv, fmt), Nothing)
            rep.Col("Código", 2.2).Col("Descripción", 8)
            If ambas Then
                rep.Col("Bolivianos", 2.4, Formato.Monto).Col("Dólares", 2.4, Formato.Monto)
            Else
                rep.Col("Importe", 2.6, Formato.Monto)
            End If
            AgregarFs(rep, bs, us, ambas)
            rep.Firmas.AddRange({"Contador", "Gerente General"})
            Return rep
        End Function

        Public Function BalanceGeneral(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim moneda As String = p.Texto("moneda", "BS")
            Dim h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Balance general", "Al " & h.ToString("dd/MM/yyyy"), moneda)
            Dim led As New LedgerService(ctx)
            Dim niv As Integer = p.Entero("nivel", 9)
            Dim ambas As Boolean = moneda = "AMBAS"
            Dim bs As EstadoFinanciero = led.BalanceGeneral(h, moneda = "USD", niv)
            Dim us As EstadoFinanciero = If(ambas, led.BalanceGeneral(h, True, niv), Nothing)
            rep.Col("Código", 2.2).Col("Descripción", 8)
            If ambas Then
                rep.Col("Bolivianos", 2.4, Formato.Monto).Col("Dólares", 2.4, Formato.Monto)
            Else
                rep.Col("Importe", 2.6, Formato.Monto)
            End If
            AgregarFs(rep, bs, us, ambas)
            If Not bs.Cuadra Then rep.Notas.Add("ATENCIÓN: el balance no cuadra (diferencia " & bs.Diferencia.ToString("N2") & ").")
            rep.Firmas.AddRange({"Contador", "Gerente General"})
            Return rep
        End Function

        Public Function EstadoCuentas(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim moneda As String = p.Texto("moneda", "BS")
            Dim h As Date = p.Fecha("hasta")
            Dim pref As String = p.Texto("prefijo").Trim()
            Dim rep As ReporteDef = Nuevo(ctx, "Estado de cuentas", "Grupo " & pref & " al " & h.ToString("dd/MM/yyyy"), moneda)
            Dim led As New LedgerService(ctx)
            Dim bs As List(Of BalanceRow) = led.Balance(ctx.Gestion.FechaInicio, h, False, 99, True)
            Dim us As Dictionary(Of String, BalanceRow) = If(moneda = "BS", Nothing, led.Balance(ctx.Gestion.FechaInicio, h, True, 99, True).ToDictionary(Function(b) b.Codigo, Function(b) b))
            rep.Col("Código", 2.4).Col("Cuenta", 6)
            If moneda = "BS" Then
                rep.Col("Saldo Bs", 2.4, Formato.Monto)
            ElseIf moneda = "USD" Then
                rep.Col("Saldo $us", 2.4, Formato.Monto)
            Else
                rep.Col("Saldo Bs", 2.4, Formato.Monto).Col("Saldo $us", 2.4, Formato.Monto)
            End If
            For Each b In bs.Where(Function(x) x.Codigo = pref OrElse EmpresaService.EsDescendiente(x.Codigo, pref))
                Dim u As BalanceRow = Nothing
                If us IsNot Nothing Then us.TryGetValue(b.Codigo, u)
                Dim sUs As Decimal = If(u Is Nothing, 0D, u.Natural)
                Dim f As FilaRep
                If moneda = "BS" Then
                    f = rep.Fila(b.Codigo, b.Nombre, b.Natural)
                ElseIf moneda = "USD" Then
                    f = rep.Fila(b.Codigo, b.Nombre, sUs)
                Else
                    f = rep.Fila(b.Codigo, b.Nombre, b.Natural, sUs)
                End If
                f.Nivel = Math.Max(0, b.Nivel - 1)
                f.Negrita = Not b.EsMovimiento
            Next
            If rep.Filas.Count = 0 Then rep.Texto("No hay cuentas con saldo en el grupo indicado.")
            Return rep
        End Function

        Public Function FlujoEfectivo(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Flujo de efectivo", Rango(d, h), "BS")
            rep.Col("Concepto (cuenta de contrapartida)", 8).Col("Importe", 2.6, Formato.Monto)
            Dim caja As DataRow = Ancestro(ctx, ctx.CuentaParam(ParamKeys.CtaCaja), 3)
            Dim prefDisp As String = caja.GetS("Codigo")
            Dim led As New LedgerService(ctx)
            Dim ini As Decimal = led.Balance(ctx.Gestion.FechaInicio, d.AddDays(-1), False, 99, False).Where(Function(b) b.Codigo = prefDisp).Select(Function(b) b.Neto).FirstOrDefault()
            If d <= ctx.Gestion.FechaInicio Then ini = 0D
            Dim dt As DataTable = ctx.Db.Query("SELECT ComprobanteId, CuentaId, DebeBs, HaberBs FROM ComprobanteDet WHERE Vigente=1 AND Fecha >= @d AND Fecha <= @h ORDER BY ComprobanteId, Linea", "d", d.Date, "h", h.Date)
            Dim porGrupo As New Dictionary(Of String, Decimal)
            Dim cabeza As Integer = -1
            Dim lineas As New List(Of DataRow)
            Dim procesar = Sub()
                               If lineas.Count = 0 Then Return
                               Dim efectivo As Decimal = 0D
                               Dim otras As New List(Of Tuple(Of String, Decimal))
                               For Each r In lineas
                                   Dim c As DataRow = ctx.CuentaPorId(r.GetI("CuentaId"))
                                   Dim neto As Decimal = r.GetD("DebeBs") - r.GetD("HaberBs")
                                   If c.GetS("Codigo") = prefDisp OrElse EmpresaService.EsDescendiente(c.GetS("Codigo"), prefDisp) Then
                                       efectivo += neto
                                   Else
                                       Dim a As DataRow = Ancestro(ctx, c.GetI("Id"), 3)
                                       otras.Add(Tuple.Create(a.GetS("Codigo") & " " & a.GetS("Nombre"), -neto))
                                   End If
                               Next
                               If efectivo = 0D OrElse otras.Count = 0 Then Return
                               Dim suma As Decimal = otras.Sum(Function(x) Math.Abs(x.Item2))
                               If suma = 0D Then Return
                               For Each o In otras
                                   Dim asignado As Decimal = efectivo * Math.Abs(o.Item2) / suma
                                   porGrupo(o.Item1) = (If(porGrupo.ContainsKey(o.Item1), porGrupo(o.Item1), 0D)) + asignado
                               Next
                           End Sub
            For Each r As DataRow In dt.Rows
                If r.GetI("ComprobanteId") <> cabeza Then
                    procesar()
                    lineas.Clear()
                    cabeza = r.GetI("ComprobanteId")
                End If
                lineas.Add(r)
            Next
            procesar()
            rep.Fila("SALDO INICIAL DE DISPONIBLE", ini).Negrita = True
            rep.Grupo("ENTRADAS DE EFECTIVO")
            Dim totIn As Decimal, totOut As Decimal
            For Each kv In porGrupo.Where(Function(x) x.Value > 0D).OrderBy(Function(x) x.Key, StringComparer.Ordinal)
                rep.Fila(kv.Key, kv.Value.R2()).Nivel = 1
                totIn += kv.Value.R2()
            Next
            rep.Subtotal("Total entradas", totIn)
            rep.Grupo("SALIDAS DE EFECTIVO")
            For Each kv In porGrupo.Where(Function(x) x.Value < 0D).OrderBy(Function(x) x.Key, StringComparer.Ordinal)
                rep.Fila(kv.Key, kv.Value.R2()).Nivel = 1
                totOut += kv.Value.R2()
            Next
            rep.Subtotal("Total salidas", totOut)
            rep.Subtotal("VARIACIÓN NETA DEL PERÍODO", totIn + totOut)
            rep.Total("SALDO FINAL DE DISPONIBLE", ini + totIn + totOut)
            rep.Notas.Add("Método directo: el efectivo de cada comprobante se distribuye entre sus cuentas de contrapartida agrupadas por rubro. Disponible: " & prefDisp & ".")
            Return rep
        End Function

        Public Function EvolucionPatrimonio(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Evolución del patrimonio neto", Rango(d, h), "BS")
            rep.Col("Código", 2.4).Col("Cuenta", 6).Col("Saldo inicial", 2.2, Formato.Monto).Col("Aumentos", 2.2, Formato.Monto).Col("Disminuciones", 2.2, Formato.Monto).Col("Saldo final", 2.2, Formato.Monto)
            Dim bal As List(Of BalanceRow) = New LedgerService(ctx).Balance(d, h, False, 99, True)
            Dim t1 As Decimal, t2 As Decimal, t3 As Decimal, t4 As Decimal
            For Each b In bal.Where(Function(x) x.Rubro = 3 AndAlso x.EsMovimiento)
                Dim ini As Decimal = b.AntH - b.AntD
                rep.Fila(b.Codigo, b.Nombre, ini, b.Haber, b.Debe, ini + b.Haber - b.Debe)
                t1 += ini : t2 += b.Haber : t3 += b.Debe : t4 += ini + b.Haber - b.Debe
            Next
            Dim res As Decimal = New LedgerService(ctx).Balance(d, h, False, 1, True).Where(Function(x) x.Rubro = 4).Sum(Function(x) -x.Neto) - New LedgerService(ctx).Balance(d, h, False, 1, True).Where(Function(x) x.Rubro = 5).Sum(Function(x) x.Neto)
            If res <> 0D Then
                rep.Fila("", "Resultado del período (aún no cerrado)", 0D, If(res > 0D, res, 0D), If(res < 0D, -res, 0D), res)
                t2 += If(res > 0D, res, 0D) : t3 += If(res < 0D, -res, 0D) : t4 += res
            End If
            rep.Total("", "PATRIMONIO NETO", t1, t2, t3, t4)
            Return rep
        End Function

        Public Function Indices(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Índices financieros", "Al " & h.ToString("dd/MM/yyyy"), "BS")
            rep.Col("Índice", 4).Col("Fórmula", 5).Col("Resultado", 2, Formato.Texto, Alinea.Derecha).Col("Interpretación", 5)
            Dim led As New LedgerService(ctx)
            Dim bal As List(Of BalanceRow) = led.Balance(ctx.Gestion.FechaInicio, h, False, 99, True)
            Dim sal = Function(cod As String) As Decimal
                          Dim b = bal.FirstOrDefault(Function(x) x.Codigo = cod)
                          Return If(b Is Nothing, 0D, b.Natural)
                      End Function
            Dim n2 = Function(rubro As Integer) As String
                         Dim r = ctx.Cuentas().Rows.Cast(Of DataRow)().Where(Function(c) c.GetI("Rubro") = rubro AndAlso c.GetI("Nivel") = 2).OrderBy(Function(c) c.GetS("Codigo"), StringComparer.Ordinal).FirstOrDefault()
                         Return If(r Is Nothing, "", r.GetS("Codigo"))
                     End Function
            Dim activo As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 1).Sum(Function(x) x.Neto)
            Dim pasivo As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 2).Sum(Function(x) -x.Neto)
            Dim ac As Decimal = sal(n2(1)), pc As Decimal = sal(n2(2))
            Dim invCta As DataRow = Ancestro(ctx, ctx.CuentaParamOpcional(ParamKeys.CtaInventario), 3)
            Dim inv As Decimal = If(invCta Is Nothing, 0D, sal(invCta.GetS("Codigo")))
            Dim ingresos As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 4).Sum(Function(x) -x.Neto)
            Dim egresos As Decimal = bal.Where(Function(x) x.Nivel = 1 AndAlso x.Rubro = 5).Sum(Function(x) x.Neto)
            Dim util As Decimal = ingresos - egresos
            Dim patri As Decimal = activo - pasivo
            Dim razon = Function(a As Decimal, b As Decimal) As String
                            If b = 0D Then Return "n/d"
                            Return (a / b).ToString("0.00", FormatoVal.Cultura)
                        End Function
            Dim pct = Function(a As Decimal, b As Decimal) As String
                          If b = 0D Then Return "n/d"
                          Return (a / b * 100D).ToString("0.00", FormatoVal.Cultura) & "%"
                      End Function
            rep.Fila("Activo corriente", "Cuentas del grupo " & n2(1), ac.ToString("N2"), "")
            rep.Fila("Pasivo corriente", "Cuentas del grupo " & n2(2), pc.ToString("N2"), "")
            rep.Fila("Liquidez corriente", "Activo corriente / Pasivo corriente", razon(ac, pc), "Cuánto se dispone en el corto plazo por cada Bs de deuda corriente (≥ 1 es sano).")
            rep.Fila("Prueba ácida", "(Activo corriente - Inventarios) / Pasivo corriente", razon(ac - inv, pc), "Liquidez sin depender de la venta de inventarios.")
            rep.Fila("Capital de trabajo", "Activo corriente - Pasivo corriente", (ac - pc).ToString("N2"), "Recursos de corto plazo disponibles tras cubrir deudas corrientes.")
            rep.Fila("Endeudamiento", "Pasivo total / Activo total", razon(pasivo, activo), "Proporción de los activos financiada con deuda.")
            rep.Fila("Solvencia", "Activo total / Pasivo total", razon(activo, pasivo), "Respaldo de los activos frente a las deudas.")
            rep.Fila("Rentabilidad sobre ventas", "Resultado / Ingresos", pct(util, ingresos), "Utilidad generada por cada Bs vendido.")
            rep.Fila("Rentabilidad del activo (ROA)", "Resultado / Activo total", pct(util, activo), "Eficiencia en el uso de los activos.")
            rep.Fila("Rentabilidad del patrimonio (ROE)", "Resultado / Patrimonio neto", pct(util, patri), "Retorno para los propietarios.")
            Return rep
        End Function

        ' ---------- Comprobantes ----------
        Public Function ListaComprobantes(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Listado de comprobantes", Rango(d, h), "BS")
            rep.Col("Comprobante", 1.8).Col("Fecha", 1.6, Formato.Fecha).Col("Glosa", 8).Col("Debe Bs", 2, Formato.Monto).Col("Haber Bs", 2, Formato.Monto).Col("Estado", 1.2, Formato.Texto, Alinea.Centro).Col("Origen", 1.2, Formato.Texto, Alinea.Centro)
            Dim dt As DataTable = New VoucherService(ctx).Listar(d, h, p.Texto("tipo"), "", p.Bool("anulados", True))
            Dim td As Decimal, th As Decimal
            For Each r As DataRow In dt.Rows
                Dim anulado As Boolean = r.GetS("Estado") = "A"
                rep.Fila(Etiqueta(r.GetS("Tipo"), r.GetI("Numero"), r.GetI("Mes")), r.GetDt("Fecha"), r.GetS("Glosa"), r.GetD("DebeBs"), r.GetD("HaberBs"), If(anulado, "ANULADO", "Vigente"), r.GetS("Origen"))
                If Not anulado Then
                    td += r.GetD("DebeBs")
                    th += r.GetD("HaberBs")
                End If
            Next
            rep.Total("", "", "TOTAL (sin anulados)", td, th, "", "")
            Return rep
        End Function

        Private Sub ArmarComprobante(rep As ReporteDef, ctx As Contexto, v As Voucher)
            Dim tc As String = v.TC.ToString("0.00", FormatoVal.Cultura)
            rep.Cabecera.Clear()
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Comprobante:", v.TipoNombre & " Nº " & v.Numero & If(v.Mes > 0, " / " & NombreMes(v.Mes), "")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Fecha:", v.Fecha.ToString("dd/MM/yyyy")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Tipo de cambio:", tc & "  (" & If(v.Moneda = "USD", "Dólares", "Bolivianos") & ")"))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Estado:", If(v.Estado = "A", "ANULADO", "Vigente")))
            If v.Cheque <> "" OrElse v.Banco <> "" Then rep.Cabecera.Add(New KeyValuePair(Of String, String)("Cheque / Banco:", (v.Cheque & " " & v.Banco).Trim()))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Glosa:", v.Glosa))
        End Sub

        Public Function ComprobanteImpreso(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim vs As New VoucherService(ctx)
            Dim v As Voucher = vs.Cargar(p.Entero("id"))
            If v Is Nothing Then Throw New InvalidOperationException("Comprobante inexistente.")
            Dim rep As ReporteDef = Nuevo(ctx, "Comprobante de " & v.TipoNombre, "", "")
            rep.Moneda = ""
            rep.Col("Código", 2.4).Col("Cuenta", 5).Col("Glosa", 4.5).Col("Debe Bs", 2, Formato.Monto).Col("Haber Bs", 2, Formato.Monto).Col("Debe $us", 1.8, Formato.Monto).Col("Haber $us", 1.8, Formato.Monto)
            rep.Horizontal = True
            ArmarComprobante(rep, ctx, v)
            Dim tdB As Decimal, thB As Decimal, tdU As Decimal, thU As Decimal
            For Each l In v.Lines
                rep.Fila(ctx.CodigoCuenta(l.CuentaId), ctx.NombreCuenta(l.CuentaId), l.Glosa, l.DebeBs, l.HaberBs, l.DebeUsd, l.HaberUsd)
                tdB += l.DebeBs : thB += l.HaberBs : tdU += l.DebeUsd : thU += l.HaberUsd
            Next
            rep.Total("", "TOTALES", "", tdB, thB, tdU, thU)
            rep.Texto("Son: " & NumeroLetras.Importe(tdB, "BS")).Negrita = True
            rep.Firmas.AddRange({"Elaborado por", "Revisado por", "Aprobado por", "Recibí conforme"})
            rep.NombreArchivo = "Comprobante_" & v.TipoCodigo & "_" & v.Numero
            Return rep
        End Function

        Public Function ComprobantesRango(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim vs As New VoucherService(ctx)
            Dim tipo As String = p.Texto("tipo", "I")
            Dim mes As Integer = p.Entero("mes")
            Dim n1 As Integer = p.Entero("desde_n", 1), n2 As Integer = p.Entero("hasta_n", 9999)
            Dim rep As ReporteDef = Nuevo(ctx, "Comprobantes", "", "")
            rep.Moneda = ""
            rep.Horizontal = True
            rep.Col("Código", 2.4).Col("Cuenta", 5).Col("Glosa", 4.5).Col("Debe Bs", 2, Formato.Monto).Col("Haber Bs", 2, Formato.Monto).Col("Debe $us", 1.8, Formato.Monto).Col("Haber $us", 1.8, Formato.Monto)
            Dim primero As Boolean = True
            Dim n As Integer = 0
            For num As Integer = n1 To Math.Min(n2, n1 + 500)
                Dim id As Integer = vs.BuscarId(tipo, num, mes)
                If id = 0 Then Continue For
                Dim v As Voucher = vs.Cargar(id)
                If Not primero Then rep.Salto()
                primero = False
                rep.Titulo = "Comprobante de " & v.TipoNombre
                rep.Grupo(v.TipoNombre.ToUpperInvariant() & " Nº " & v.Numero & If(v.Mes > 0, " / " & NombreMes(v.Mes), "") & "   Fecha: " & v.Fecha.ToString("dd/MM/yyyy") & "   T.C.: " & v.TC.ToString("0.00", FormatoVal.Cultura) & If(v.Estado = "A", "   *** ANULADO ***", ""))
                rep.Texto("Glosa: " & v.Glosa)
                Dim tdB As Decimal, thB As Decimal, tdU As Decimal, thU As Decimal
                For Each l In v.Lines
                    rep.Fila(ctx.CodigoCuenta(l.CuentaId), ctx.NombreCuenta(l.CuentaId), l.Glosa, l.DebeBs, l.HaberBs, l.DebeUsd, l.HaberUsd)
                    tdB += l.DebeBs : thB += l.HaberBs : tdU += l.DebeUsd : thU += l.HaberUsd
                Next
                rep.Total("", "TOTALES", "", tdB, thB, tdU, thU)
                rep.Texto("Son: " & NumeroLetras.Importe(tdB, "BS"))
                n += 1
            Next
            If n = 0 Then Throw New InvalidOperationException("No se encontraron comprobantes en el rango indicado.")
            rep.Titulo = "Reimpresión de comprobantes"
            rep.Firmas.AddRange({"Elaborado por", "Revisado por", "Aprobado por"})
            rep.Notas.Add("Total de comprobantes impresos: " & n)
            Return rep
        End Function

        ' ---------- Bancos ----------
        Public Function LibretaBanco(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim c As DataRow = ctx.CuentaPorId(p.Entero("cuenta"))
            Dim rep As ReporteDef = Nuevo(ctx, "Libreta bancaria", Rango(d, h), "BS")
            rep.Subtitulo = c.GetS("Codigo") & " - " & c.GetS("Nombre")
            rep.Col("Fecha", 1.6, Formato.Fecha).Col("Comprob.", 1.6).Col("Cheque", 1.6).Col("Detalle", 6).Col("Depósitos", 2, Formato.Monto).Col("Retiros", 2, Formato.Monto).Col("Saldo", 2.2, Formato.Monto)
            Dim bs As New BancoService(ctx)
            Dim ant As Decimal = New LedgerService(ctx).SaldoCuenta(c.GetI("Id"), d.AddDays(-1))
            If d <= ctx.Gestion.FechaInicio Then ant = 0D
            Dim saldo As Decimal = ant
            rep.Fila(Nothing, "", "", "SALDO ANTERIOR", Nothing, Nothing, saldo).Negrita = True
            Dim td As Decimal, th As Decimal
            For Each x In bs.Partidas(c.GetI("Id"), d, h)
                saldo += x.Debe - x.Haber
                td += x.Debe : th += x.Haber
                rep.Fila(x.Fecha, x.Comprobante, x.Cheque, x.Glosa, x.Debe, x.Haber, saldo)
            Next
            rep.Total("", "", "", "TOTALES", td, th, saldo)
            Return rep
        End Function

        Public Function Conciliacion(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim h As Date = p.Fecha("hasta")
            Dim c As DataRow = ctx.CuentaPorId(p.Entero("cuenta"))
            Dim rep As ReporteDef = Nuevo(ctx, "Conciliación bancaria", "Al " & h.ToString("dd/MM/yyyy"), "BS")
            rep.Subtitulo = c.GetS("Codigo") & " - " & c.GetS("Nombre")
            rep.Col("Fecha", 1.6, Formato.Fecha).Col("Comprob.", 1.8).Col("Cheque", 1.8).Col("Detalle", 6).Col("Depósitos en tránsito", 2.2, Formato.Monto).Col("Cheques no cobrados", 2.2, Formato.Monto)
            Dim bs As New BancoService(ctx)
            For Each x In bs.Partidas(c.GetI("Id"), ctx.Gestion.FechaInicio, h).Where(Function(y) Not y.Conciliado)
                rep.Fila(x.Fecha, x.Comprobante, x.Cheque, x.Glosa, x.Debe, x.Haber)
            Next
            Dim r = bs.Resumen(c.GetI("Id"), h)
            rep.Total("", "", "", "PARTIDAS NO CONCILIADAS", r.Item2, r.Item3)
            rep.Vacia()
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Saldo según libros:", r.Item1.ToString("N2", FormatoVal.Cultura)))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("(-) Depósitos en tránsito:", r.Item2.ToString("N2", FormatoVal.Cultura)))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("(+) Cheques no cobrados:", r.Item3.ToString("N2", FormatoVal.Cultura)))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Saldo bancario esperado:", r.Item4.ToString("N2", FormatoVal.Cultura)))
            If p.Dec("extracto") <> 0D Then
                rep.Cabecera.Add(New KeyValuePair(Of String, String)("Saldo según extracto:", p.Dec("extracto").ToString("N2", FormatoVal.Cultura)))
                rep.Cabecera.Add(New KeyValuePair(Of String, String)("Diferencia sin explicar:", (p.Dec("extracto") - r.Item4).ToString("N2", FormatoVal.Cultura)))
            End If
            rep.Firmas.AddRange({"Contador", "Tesorería"})
            Return rep
        End Function

        ' ---------- Presupuesto ----------
        Public Function PresupuestoAsignado(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim rep As ReporteDef = Nuevo(ctx, "Presupuesto asignado", "", "BS")
            rep.Horizontal = True
            rep.Col("Código", 2).Col("Cuenta", 4.5)
            Dim ini As Date = ctx.Gestion.FechaInicio
            For i As Integer = 0 To 11
                rep.Col(NombreMes(ini.AddMonths(i).Month).Substring(0, 3), 1.5, Formato.Monto)
            Next
            rep.Col("Total", 2, Formato.Monto)
            Dim ps As New PresupuestoService(ctx)
            Dim tm(11) As Decimal
            For Each c As DataRow In ctx.Cuentas().Rows
                If Not c.GetF("Presupuestable") OrElse Not c.GetF("EsMovimiento") Then Continue For
                Dim m As Decimal() = ps.Obtener(c.GetI("Id"))
                Dim cel As New List(Of Object) From {c.GetS("Codigo"), c.GetS("Nombre")}
                For i As Integer = 0 To 11
                    cel.Add(m(i))
                    tm(i) += m(i)
                Next
                cel.Add(m.Sum())
                rep.Fila(cel.ToArray())
            Next
            Dim tot As New List(Of Object) From {"", "TOTAL"}
            For i As Integer = 0 To 11
                tot.Add(tm(i))
            Next
            tot.Add(tm.Sum())
            rep.Total(tot.ToArray())
            Return rep
        End Function

        Public Function EjecucionPresupuesto(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim mes As Integer = p.Entero("mes", ctx.Gestion.FechaInicio.Month)
            Dim rep As ReporteDef = Nuevo(ctx, "Ejecución presupuestaria", "Acumulado hasta " & NombreMes(mes), "BS")
            rep.Col("Código", 2.2).Col("Cuenta", 6).Col("Presupuesto", 2.2, Formato.Monto).Col("Ejecutado", 2.2, Formato.Monto).Col("Saldo por ejecutar", 2.2, Formato.Monto).Col("% Ejec.", 1.3, Formato.Porcentaje)
            Dim dt As DataTable = New PresupuestoService(ctx).Ejecucion(mes)
            Dim tp As Decimal, te As Decimal
            For Each r As DataRow In dt.Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Nombre"), r.GetD("Presupuesto"), r.GetD("Ejecutado"), r.GetD("Saldo"), r.GetD("Porcentaje"))
                tp += r.GetD("Presupuesto") : te += r.GetD("Ejecutado")
            Next
            rep.Total("", "TOTAL", tp, te, tp - te, If(tp <> 0D, Math.Round(te / tp * 100D, 1), 0D))
            Return rep
        End Function

        Public Function GastosCentros(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Gastos por centro de costo", Rango(d, h), "BS")
            rep.Col("Cuenta", 2.4).Col("Descripción", 6).Col("Costo F/V", 1.2, Formato.Texto, Alinea.Centro).Col("Importe", 2.4, Formato.Monto)
            Dim dt As DataTable = New CentroCostoService(ctx).GastosPorCentro(d, h)
            Dim actual As String = Nothing
            Dim sub1 As Decimal, total As Decimal
            For Each r As DataRow In dt.Rows
                If actual <> r.GetS("Centro") Then
                    If actual IsNot Nothing Then rep.Subtotal("", "Subtotal " & actual, "", sub1)
                    actual = r.GetS("Centro")
                    sub1 = 0D
                    rep.Grupo(actual)
                End If
                rep.Fila(r.GetS("Cuenta"), r.GetS("Nombre"), r.GetS("Tipo"), r.GetD("Importe"))
                sub1 += r.GetD("Importe") : total += r.GetD("Importe")
            Next
            If actual IsNot Nothing Then rep.Subtotal("", "Subtotal " & actual, "", sub1)
            rep.Total("", "TOTAL GASTOS", "", total)
            Return rep
        End Function

        Public Function TiposCambio(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Tipos de cambio y UFV", Rango(d, h), "")
            rep.Col("Fecha", 2, Formato.Fecha).Col("Tipo de cambio USD", 2.5, Formato.Precio).Col("UFV", 2.5, Formato.Precio)
            For Each r As DataRow In New TipoCambioService(ctx).Listar(d, h).Rows
                rep.Fila(r.GetDt("Fecha"), r.GetD("Usd"), r.GetD("Ufv"))
            Next
            Return rep
        End Function

        Public Function Auditoria(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim d As Date = p.Fecha("desde"), h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Auditoría del sistema", Rango(d, h), "")
            rep.Horizontal = True
            rep.Col("Fecha y hora", 2.4).Col("Usuario", 1.6).Col("Módulo", 2).Col("Acción", 2.4).Col("Detalle", 8).Col("Equipo", 2)
            For Each r As DataRow In ctx.Sistema.ConsultarAuditoria(d, h, ctx.Empresa.Id).Rows
                rep.Fila(r.GetDt("Fecha").ToString("dd/MM/yyyy HH:mm:ss"), r.GetS("Login"), r.GetS("Modulo"), r.GetS("Accion"), r.GetS("Detalle"), r.GetS("Equipo"))
            Next
            Return rep
        End Function

    End Module

End Namespace
