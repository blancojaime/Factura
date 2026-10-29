Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports ContaBol.Core.Reports.Catalogo

Namespace Reports

    ''' <summary>Activos fijos, planillas de sueldos y costos de producción.</summary>
    Public Module InformesOtros

        Public Sub Registrar(l As List(Of ReporteCat))
            l.Add(Rep("cuadro_activos", "Cuadro de activos fijos", Catalogo.ModActivos, "AF.REPORTES", AddressOf CuadroActivos, PHasta()))
            l.Add(Rep("depreciacion_periodo", "Depreciación de un período", Catalogo.ModActivos, "AF.REPORTES", AddressOf DepreciacionPeriodo, PMes()))
            l.Add(Rep("depreciacion_vista", "Vista previa de depreciación del mes", Catalogo.ModActivos, "AF.REPORTES", AddressOf VistaPreviaDepreciacion, PMes()))

            Const R As String = Catalogo.ModPlanillas
            l.Add(Rep("planilla_sueldos", "Planilla de sueldos y salarios", R, "RH.REPORTES", AddressOf PlanillaSueldos, PMes()))
            l.Add(Rep("planilla_rciva", "Planilla RC-IVA (dependientes)", R, "RH.REPORTES", AddressOf PlanillaRcIva, PMes()))
            l.Add(Rep("boletas_pago", "Boletas de pago", R, "RH.REPORTES", AddressOf BoletasPago, PMes(), PRef("empleado", "Empleado (vacío = todos)", ParamTipo.Empleado)))
            l.Add(Rep("planilla_aportes", "Resumen de aportes laborales y patronales", R, "RH.REPORTES", AddressOf Aportes, PMes()))
            l.Add(Rep("aguinaldo", "Aguinaldo de navidad", R, "RH.REPORTES", AddressOf Aguinaldo, PHasta()))
            l.Add(Rep("anticipos_sueldo", "Anticipos de sueldo del mes", R, "RH.REPORTES", AddressOf Anticipos, PMes()))
            l.Add(Rep("listado_empleados", "Listado de empleados", R, "RH.REPORTES", AddressOf ListadoEmpleados))

            Const C As String = Catalogo.ModCostos
            l.Add(Rep("hoja_costos", "Hoja de costos de la orden de producción", C, "COS.REPORTES", AddressOf HojaCostos, PRef("orden", "Orden de producción", ParamTipo.Orden, True)))
            l.Add(Rep("ordenes_produccion", "Órdenes de producción", C, "COS.REPORTES", AddressOf OrdenesProduccion, PLista("estado", "Estado", "|(Todas)", "A|Abiertas", "T|Terminadas")))
        End Sub

        Private Function AnioMes(ctx As Contexto, mes As Integer) As Integer
            Return If(mes >= ctx.Gestion.FechaInicio.Month, ctx.Gestion.FechaInicio.Year, ctx.Gestion.FechaInicio.Year + 1)
        End Function

        ' ---------- Activos fijos ----------
        Public Function CuadroActivos(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Cuadro de activos fijos", "Al " & h.ToString("dd/MM/yyyy"), "BS")
            rep.Horizontal = True
            rep.Col("Código", 1.8).Col("Activo", 5).Col("Fecha alta", 1.6, Formato.Fecha).Col("Valor original", 2, Formato.Monto).Col("Valor actualizado", 2, Formato.Monto).Col("% Dep.", 1.1, Formato.Porcentaje).Col("Dep. acumulada", 2, Formato.Monto).Col("Valor neto", 2, Formato.Monto).Col("Ubicación", 2.5)
            Dim a As Decimal, b As Decimal, c As Decimal, d As Decimal
            For Each r As DataRow In New ActivoFijoService(ctx).Cuadro(h).Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Nombre"), r.GetDt("FechaAlta"), r.GetD("ValorOriginal"), r.GetD("ValorActualizado"), r.GetD("PorcDep"), r.GetD("DepAcum"), r.GetD("ValorNeto"), r.GetS("Ubicacion"))
                a += r.GetD("ValorOriginal") : b += r.GetD("ValorActualizado") : c += r.GetD("DepAcum") : d += r.GetD("ValorNeto")
            Next
            rep.Total("", "TOTALES", "", a, b, "", c, d, "")
            rep.Firmas.AddRange({"Contador", "Responsable de activos"})
            Return rep
        End Function

        Public Function DepreciacionPeriodo(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim mes As Integer = p.Entero("mes")
            Dim per As String = AnioMes(ctx, mes).ToString() & "-" & mes.ToString("00")
            Dim rep As ReporteDef = Nuevo(ctx, "Depreciación de activos fijos", NombreMes(mes) & " " & AnioMes(ctx, mes), "BS")
            rep.Horizontal = True
            rep.Col("Código", 1.8).Col("Activo", 5).Col("Valor actualizado", 2, Formato.Monto).Col("Actualización valor", 2, Formato.Monto).Col("Actualización dep.", 2, Formato.Monto).Col("Depreciación del mes", 2, Formato.Monto).Col("Dep. acumulada", 2, Formato.Monto).Col("Valor neto", 2, Formato.Monto)
            Dim dt As DataTable = ctx.Db.Query("SELECT a.Codigo, a.Nombre, d.* FROM DepreciacionAF d INNER JOIN ActivoFijo a ON a.Id = d.ActivoId WHERE d.Periodo=@p ORDER BY a.Codigo", "p", per)
            Dim t(5) As Decimal
            For Each r As DataRow In dt.Rows
                rep.Fila(r.GetS("Codigo"), r.GetS("Nombre"), r.GetD("ValorAct"), r.GetD("ActualizaValor"), r.GetD("ActualizaDep"), r.GetD("DepPeriodo"), r.GetD("DepAcum"), r.GetD("ValorNeto"))
                t(0) += r.GetD("ValorAct") : t(1) += r.GetD("ActualizaValor") : t(2) += r.GetD("ActualizaDep") : t(3) += r.GetD("DepPeriodo") : t(4) += r.GetD("DepAcum") : t(5) += r.GetD("ValorNeto")
            Next
            rep.Total("", "TOTALES", t(0), t(1), t(2), t(3), t(4), t(5))
            If dt.Rows.Count = 0 Then rep.Notas.Add("No hay depreciación registrada para el período " & per & ".")
            Return rep
        End Function

        Public Function VistaPreviaDepreciacion(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim mes As Integer = p.Entero("mes")
            Dim rep As ReporteDef = Nuevo(ctx, "Vista previa de depreciación (no registrada)", NombreMes(mes) & " " & AnioMes(ctx, mes), "BS")
            rep.Horizontal = True
            rep.Col("Código", 1.8).Col("Activo", 5).Col("Valor anterior", 2, Formato.Monto).Col("Actualización valor", 2, Formato.Monto).Col("Valor actualizado", 2, Formato.Monto).Col("Actualización dep.", 2, Formato.Monto).Col("Depreciación del mes", 2, Formato.Monto).Col("Dep. acumulada", 2, Formato.Monto).Col("Valor neto", 2, Formato.Monto)
            Dim r As DepreciacionResultado = New ActivoFijoService(ctx).Depreciar(New Date(AnioMes(ctx, mes), mes, 1), False)
            For Each f In r.Filas
                rep.Fila(f.Codigo, f.Nombre, f.ValorAnterior, f.ActualizaValor, f.ValorActualizado, f.ActualizaDep, f.DepPeriodo, f.DepAcum, f.ValorNeto)
            Next
            rep.Total("", "TOTALES", r.Filas.Sum(Function(x) x.ValorAnterior), r.Filas.Sum(Function(x) x.ActualizaValor), r.Filas.Sum(Function(x) x.ValorActualizado), r.Filas.Sum(Function(x) x.ActualizaDep), r.Filas.Sum(Function(x) x.DepPeriodo), r.Filas.Sum(Function(x) x.DepAcum), r.Filas.Sum(Function(x) x.ValorNeto))
            If r.UfvFaltante Then rep.Notas.Add("No hay UFV cargada para la fecha de cierre del mes: no se actualizaron los valores.")
            Return rep
        End Function

        ' ---------- Planillas ----------
        Private Function Periodo(ctx As Contexto, p As Parametros_) As Tuple(Of PlanillaPeriodoInfo, List(Of FilaPlanilla), Integer, Integer)
            Dim mes As Integer = p.Entero("mes")
            Dim anio As Integer = AnioMes(ctx, mes)
            Dim ps As New PlanillaService(ctx)
            Dim per As PlanillaPeriodoInfo = ps.ObtenerPeriodo(anio, mes)
            If per Is Nothing Then Throw New InvalidOperationException("No existe planilla de " & NombreMes(mes) & " " & anio & ". Genérela en Planillas > Planilla de sueldos.")
            Return Tuple.Create(per, ps.Filas(per.Id), anio, mes)
        End Function

        Public Function PlanillaSueldos(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim t = Periodo(ctx, p)
            Dim rep As ReporteDef = Nuevo(ctx, "Planilla de sueldos y salarios", NombreMes(t.Item4) & " " & t.Item3 & If(t.Item1.Estado = "C", "", " (borrador)"), "BS")
            rep.Horizontal = True
            rep.Col("Nº", 0.7, Formato.Entero).Col("Apellidos y nombres", 4.2).Col("C.I.", 1.5).Col("Cargo", 2.5).Col("Días", 0.8, Formato.Entero).Col("Haber básico", 1.6, Formato.Monto).Col("Bono antig.", 1.5, Formato.Monto).Col("Horas extras", 1.4, Formato.Monto).
                Col("Otros ingr.", 1.4, Formato.Monto).Col("Total ganado", 1.7, Formato.Monto).Col("AFP", 1.5, Formato.Monto).Col("RC-IVA", 1.4, Formato.Monto).Col("Anticipos y otros", 1.5, Formato.Monto).Col("Total desc.", 1.6, Formato.Monto).Col("Líquido pagable", 1.8, Formato.Monto).Col("Firma", 2)
            Dim n As Integer = 0
            Dim tt(9) As Decimal
            For Each f In t.Item2
                n += 1
                Dim otros As Decimal = f.BonoProd + f.BonoDom + f.OtrosIngresos
                Dim antic As Decimal = f.Anticipo + f.Prestamo + f.OtrosDesc
                rep.Fila(n, f.Nombre, f.Ci, f.Cargo, f.Dias, f.Haber, f.BonoAntig, f.MontoHorasExtras, otros, f.TotalGanado, f.TotalAfp, f.RcIvaRet, antic, f.TotalDesc, f.Liquido, "")
                Dim v As Decimal() = {f.Haber, f.BonoAntig, f.MontoHorasExtras, otros, f.TotalGanado, f.TotalAfp, f.RcIvaRet, antic, f.TotalDesc, f.Liquido}
                For i As Integer = 0 To 9
                    tt(i) += v(i)
                Next
            Next
            rep.Total("", "TOTALES", "", "", "", tt(0), tt(1), tt(2), tt(3), tt(4), tt(5), tt(6), tt(7), tt(8), tt(9), "")
            rep.Firmas.AddRange({"Elaborado por", "Recursos Humanos", "Gerente General"})
            Return rep
        End Function

        Public Function PlanillaRcIva(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim t = Periodo(ctx, p)
            Dim rep As ReporteDef = Nuevo(ctx, "Planilla tributaria RC-IVA (dependientes)", NombreMes(t.Item4) & " " & t.Item3, "BS")
            rep.Horizontal = True
            rep.Col("Nº", 0.7, Formato.Entero).Col("Apellidos y nombres", 4.2).Col("C.I.", 1.5).Col("Total ganado", 1.7, Formato.Monto).Col("Aportes AFP", 1.6, Formato.Monto).Col("Ingreso neto", 1.7, Formato.Monto).Col("Mínimo no imponible", 1.8, Formato.Monto).Col("Base imponible", 1.7, Formato.Monto).
                Col("RC-IVA 13%", 1.5, Formato.Monto).Col("13% 2 SMN", 1.4, Formato.Monto).Col("Facturas F-110 (13%)", 1.7, Formato.Monto).Col("Saldo anterior act.", 1.7, Formato.Monto).Col("Retención del mes", 1.7, Formato.Monto).Col("Saldo a favor", 1.6, Formato.Monto)
            Dim n As Integer = 0
            Dim s(10) As Decimal
            For Each f In t.Item2
                n += 1
                rep.Fila(n, f.Nombre, f.Ci, f.TotalGanado, f.TotalAfp, f.IngresoNeto, f.MinimoNoImp, f.BaseImponible, f.RcIvaBruto, f.Cred2Smn, f.CredFacturas, f.SaldoAnteriorAct, f.RcIvaRet, f.SaldoSiguiente)
                Dim v As Decimal() = {f.TotalGanado, f.TotalAfp, f.IngresoNeto, f.BaseImponible, f.RcIvaBruto, f.Cred2Smn, f.CredFacturas, f.SaldoAnteriorAct, f.RcIvaRet, f.SaldoSiguiente}
                For i As Integer = 0 To 9
                    s(i) += v(i)
                Next
            Next
            rep.Total("", "TOTALES", "", s(0), s(1), s(2), "", s(3), s(4), s(5), s(6), s(7), s(8), s(9))
            rep.Notas.Add("Parámetros: mínimo no imponible = 4 SMN; crédito por 13% de 2 SMN; alícuota " & ctx.Param.Dec(ParamKeys.PlRcIvaPct, 13D) & "%. Verifique su vigencia en Parámetros > Planillas.")
            Return rep
        End Function

        Public Function BoletasPago(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim t = Periodo(ctx, p)
            Dim rep As ReporteDef = Nuevo(ctx, "Boleta de pago", NombreMes(t.Item4) & " " & t.Item3, "BS")
            rep.Col("Haberes", 4).Col("Importe", 2, Formato.Monto).Col("Descuentos", 4).Col("Importe", 2, Formato.Monto)
            Dim emp As Integer = p.Entero("empleado")
            Dim primero As Boolean = True
            For Each f In t.Item2
                If emp <> 0 AndAlso f.EmpleadoId <> emp Then Continue For
                If Not primero Then rep.Salto()
                primero = False
                rep.Grupo("BOLETA DE PAGO - " & NombreMes(t.Item4).ToUpperInvariant() & " " & t.Item3)
                rep.Texto("Empleado: " & f.Nombre & "     C.I.: " & f.Ci & "     Cargo: " & f.Cargo).Negrita = True
                rep.Texto("Fecha de ingreso: " & f.FechaIngreso.ToString("dd/MM/yyyy") & "     Días trabajados: " & f.Dias & "     Haber básico: " & f.HaberBasico.ToString("N2", FormatoVal.Cultura))
                Dim ing As New List(Of Tuple(Of String, Decimal))
                ing.Add(Tuple.Create("Haber básico (" & f.Dias & " días)", f.Haber))
                If f.BonoAntig <> 0D Then ing.Add(Tuple.Create("Bono de antigüedad", f.BonoAntig))
                If f.MontoHorasExtras <> 0D Then ing.Add(Tuple.Create("Horas extras (" & f.HorasExtras.ToString("0.##", FormatoVal.Cultura) & ")", f.MontoHorasExtras))
                If f.BonoProd <> 0D Then ing.Add(Tuple.Create("Bono de producción", f.BonoProd))
                If f.BonoDom <> 0D Then ing.Add(Tuple.Create("Dominical", f.BonoDom))
                If f.OtrosIngresos <> 0D Then ing.Add(Tuple.Create("Otros ingresos", f.OtrosIngresos))
                Dim des As New List(Of Tuple(Of String, Decimal))
                des.Add(Tuple.Create("AFP aporte laboral", f.AfpVejez + f.AfpRiesgo + f.AfpComision + f.AfpSolidario))
                If f.Ans <> 0D Then des.Add(Tuple.Create("Aporte nacional solidario", f.Ans))
                If f.RcIvaRet <> 0D Then des.Add(Tuple.Create("Retención RC-IVA", f.RcIvaRet))
                If f.Anticipo <> 0D Then des.Add(Tuple.Create("Anticipos", f.Anticipo))
                If f.Prestamo <> 0D Then des.Add(Tuple.Create("Préstamos", f.Prestamo))
                If f.OtrosDesc <> 0D Then des.Add(Tuple.Create("Otros descuentos", f.OtrosDesc))
                Dim n As Integer = Math.Max(ing.Count, des.Count)
                For i As Integer = 0 To n - 1
                    rep.Fila(If(i < ing.Count, ing(i).Item1, ""), If(i < ing.Count, CObj(ing(i).Item2), Nothing), If(i < des.Count, des(i).Item1, ""), If(i < des.Count, CObj(des(i).Item2), Nothing))
                Next
                rep.Subtotal("TOTAL GANADO", f.TotalGanado, "TOTAL DESCUENTOS", f.TotalDesc)
                rep.Total("LÍQUIDO PAGABLE", f.Liquido, "", Nothing)
                rep.Texto("Son: " & NumeroLetras.Importe(f.Liquido, "BS")).Negrita = True
                rep.Texto("Recibí conforme: ______________________________          Empleador: ______________________________")
            Next
            If rep.Filas.Count = 0 Then Throw New InvalidOperationException("No hay empleados en la planilla del mes.")
            rep.Titulo = "Boletas de pago"
            Return rep
        End Function

        Public Function Aportes(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim t = Periodo(ctx, p)
            Dim rep As ReporteDef = Nuevo(ctx, "Resumen de aportes laborales y patronales", NombreMes(t.Item4) & " " & t.Item3, "BS")
            rep.Col("Concepto", 8).Col("Base (total ganado)", 2.6, Formato.Monto).Col("Importe", 2.6, Formato.Monto)
            Dim tg As Decimal = t.Item2.Sum(Function(x) x.TotalGanado)
            rep.Grupo("APORTES LABORALES (descontados al trabajador) - AFP")
            rep.Fila("Aporte al seguro social obligatorio (vejez)", tg, t.Item2.Sum(Function(x) x.AfpVejez))
            rep.Fila("Riesgo común", tg, t.Item2.Sum(Function(x) x.AfpRiesgo))
            rep.Fila("Comisión AFP", tg, t.Item2.Sum(Function(x) x.AfpComision))
            rep.Fila("Aporte solidario", tg, t.Item2.Sum(Function(x) x.AfpSolidario))
            rep.Fila("Aporte nacional solidario (sobre sueldos altos)", tg, t.Item2.Sum(Function(x) x.Ans))
            rep.Subtotal("Total aportes laborales", "", t.Item2.Sum(Function(x) x.TotalAfp))
            rep.Grupo("APORTES PATRONALES (a cargo del empleador)")
            rep.Fila("Caja Nacional de Salud", tg, t.Item2.Sum(Function(x) x.PatCns))
            rep.Fila("Riesgo profesional", tg, t.Item2.Sum(Function(x) x.PatRiesgoProf))
            rep.Fila("Pro-vivienda", tg, t.Item2.Sum(Function(x) x.PatVivienda))
            rep.Fila("Aporte patronal solidario", tg, t.Item2.Sum(Function(x) x.PatSolidario))
            rep.Subtotal("Total aportes patronales", "", t.Item2.Sum(Function(x) x.TotalPatronal))
            rep.Grupo("OTRAS RETENCIONES")
            rep.Total("RC-IVA retenido a dependientes", "", t.Item2.Sum(Function(x) x.RcIvaRet))
            Return rep
        End Function

        Public Function Aguinaldo(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim h As Date = p.Fecha("hasta")
            Dim rep As ReporteDef = Nuevo(ctx, "Aguinaldo de navidad", "Gestión " & h.Year & " (al " & h.ToString("dd/MM/yyyy") & ")", "BS")
            rep.Col("Apellidos y nombres", 5).Col("C.I.", 1.6).Col("Ingreso", 1.6, Formato.Fecha).Col("Meses", 1, Formato.Entero).Col("Promedio 3 últimos sueldos", 2.4, Formato.Monto).Col("Aguinaldo", 2.2, Formato.Monto)
            Dim tot As Decimal
            For Each r As DataRow In New PlanillaService(ctx).Aguinaldo(h.Year, h).Rows
                rep.Fila(r.GetS("Nombre"), r.GetS("Ci"), r.GetDt("FechaIngreso"), r.GetI("Meses"), r.GetD("Promedio"), r.GetD("Aguinaldo"))
                tot += r.GetD("Aguinaldo")
            Next
            rep.Total("TOTAL", "", "", "", "", tot)
            rep.Firmas.AddRange({"Elaborado por", "Gerente General"})
            Return rep
        End Function

        Public Function Anticipos(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim mes As Integer = p.Entero("mes")
            Dim anio As Integer = AnioMes(ctx, mes)
            Dim rep As ReporteDef = Nuevo(ctx, "Anticipos de sueldo", NombreMes(mes) & " " & anio, "BS")
            rep.Col("Empleado", 6).Col("Fecha", 1.6, Formato.Fecha).Col("Detalle", 4).Col("Anticipo", 2, Formato.Monto).Col("A descontar", 2, Formato.Monto)
            Dim a As Decimal, b As Decimal
            For Each r As DataRow In New PlanillaService(ctx).Anticipos(anio, mes).Rows
                rep.Fila(r.GetS("Nombre"), r.GetDt("Fecha"), r.GetS("Detalle"), r.GetD("Monto"), r.GetD("Confirmado"))
                a += r.GetD("Monto") : b += r.GetD("Confirmado")
            Next
            rep.Total("TOTAL", "", "", a, b)
            Return rep
        End Function

        Public Function ListadoEmpleados(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim rep As ReporteDef = Nuevo(ctx, "Listado de empleados", "", "BS")
            rep.Horizontal = True
            rep.Col("Ítem", 0.9).Col("Apellidos y nombres", 5).Col("C.I.", 1.6).Col("Cargo", 3).Col("Ingreso", 1.6, Formato.Fecha).Col("Haber básico", 2, Formato.Monto).Col("NUA/CUA", 2).Col("AFP", 1.5).Col("Banco", 2).Col("Estado", 1.2, Formato.Texto, Alinea.Centro)
            For Each r As DataRow In New PlanillaService(ctx).ListarEmpleados().Rows
                rep.Fila(r.GetS("Item"), r.GetS("Nombre"), r.GetS("Ci"), r.GetS("Cargo"), r.GetDt("FechaIngreso"), r.GetD("Haber"), r.GetS("Nua"), r.GetS("Afp"), r.GetS("Banco"), If(r.GetS("Estado") = "A", "Activo", "Retirado"))
            Next
            Return rep
        End Function

        ' ---------- Producción ----------
        Public Function HojaCostos(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim ps As New ProduccionService(ctx)
            Dim o As DataRow = ps.Obtener(p.Entero("orden"))
            If o Is Nothing Then Throw New InvalidOperationException("Seleccione la orden de producción.")
            Dim id As Integer = o.GetI("Id")
            Dim rep As ReporteDef = Nuevo(ctx, "Hoja de costos - Orden de producción Nº " & o.GetS("Numero"), "", "BS")
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Producto:", o.GetS("ItemCodigo") & " - " & o.GetS("Producto")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Fecha:", o.GetDt("Fecha").ToString("dd/MM/yyyy")))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Cantidad:", o.GetD("Cantidad").ToString("0.####", FormatoVal.Cultura)))
            rep.Cabecera.Add(New KeyValuePair(Of String, String)("Estado:", If(o.GetS("Estado") = "T", "Terminada", "Abierta")))
            If o.GetS("Detalle") <> "" Then rep.Cabecera.Add(New KeyValuePair(Of String, String)("Detalle:", o.GetS("Detalle")))
            rep.Col("Fecha", 1.6, Formato.Fecha).Col("Concepto", 7).Col("Cantidad / horas", 2, Formato.Cantidad).Col("Costo unitario", 2, Formato.Monto).Col("Importe Bs", 2.4, Formato.Monto)
            rep.Grupo("1. MATERIA PRIMA DIRECTA")
            For Each r As DataRow In ps.DetalleMp(id).Rows
                rep.Fila(r.GetDt("Fecha"), r.GetS("Codigo") & " " & r.GetS("Descripcion"), r.GetD("Cantidad"), r.GetD("CostoUnitBs"), r.GetD("ImporteBs"))
            Next
            rep.Subtotal("", "Total materia prima", "", "", o.GetD("CostoMp"))
            rep.Grupo("2. MANO DE OBRA DIRECTA")
            For Each r As DataRow In ps.DetalleMod(id).Rows
                rep.Fila(Nothing, r.GetS("Nombre"), r.GetD("Horas"), r.GetD("CostoHora"), r.GetD("Monto"))
            Next
            rep.Subtotal("", "Total mano de obra directa", "", "", o.GetD("CostoMod"))
            rep.Grupo("3. COSTOS INDIRECTOS DE FABRICACIÓN")
            For Each r As DataRow In ps.DetalleCif(id).Rows
                rep.Fila(Nothing, r.GetS("Detalle"), Nothing, Nothing, r.GetD("Monto"))
            Next
            rep.Subtotal("", "Total costos indirectos", "", "", o.GetD("CostoCif"))
            Dim total As Decimal = o.GetD("CostoMp") + o.GetD("CostoMod") + o.GetD("CostoCif")
            rep.Total("", "COSTO TOTAL DE PRODUCCIÓN", "", "", total)
            Dim q As Decimal = o.GetD("Cantidad")
            If q > 0D Then rep.Total("", "COSTO UNITARIO DEL PRODUCTO", q, "", (total / q).R2())
            rep.Firmas.AddRange({"Jefe de producción", "Contador"})
            Return rep
        End Function

        Public Function OrdenesProduccion(ctx As Contexto, p As Parametros_) As ReporteDef
            Dim rep As ReporteDef = Nuevo(ctx, "Órdenes de producción", "", "BS")
            rep.Horizontal = True
            rep.Col("Orden", 1, Formato.Entero).Col("Fecha", 1.6, Formato.Fecha).Col("Producto", 5).Col("Cantidad", 1.6, Formato.Cantidad).Col("Materia prima", 2, Formato.Monto).Col("Mano de obra", 2, Formato.Monto).Col("CIF", 2, Formato.Monto).Col("Costo total", 2, Formato.Monto).Col("Costo unit.", 1.8, Formato.Monto).Col("Estado", 1.4, Formato.Texto, Alinea.Centro)
            Dim t(3) As Decimal
            For Each r As DataRow In New ProduccionService(ctx).Listar(p.Texto("estado")).Rows
                Dim total As Decimal = r.GetD("CostoMp") + r.GetD("CostoMod") + r.GetD("CostoCif")
                rep.Fila(r.GetI("Numero"), r.GetDt("Fecha"), r.GetS("Producto"), r.GetD("Cantidad"), r.GetD("CostoMp"), r.GetD("CostoMod"), r.GetD("CostoCif"), total, ToDec(r("CostoUnit")), If(r.GetS("Estado") = "T", "Terminada", "Abierta"))
                t(0) += r.GetD("CostoMp") : t(1) += r.GetD("CostoMod") : t(2) += r.GetD("CostoCif") : t(3) += total
            Next
            rep.Total("", "", "TOTALES", "", t(0), t(1), t(2), t(3), "", "")
            Return rep
        End Function

    End Module

End Namespace
