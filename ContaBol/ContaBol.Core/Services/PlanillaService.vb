Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class EmpleadoDto
        Public Property Id As Integer
        Public Property Item As String = ""
        Public Property Nombre As String = ""
        Public Property Ci As String = ""
        Public Property FechaIngreso As Date = Date.Today
        Public Property FechaNac As Date?
        Public Property Cargo As String = ""
        Public Property Haber As Decimal
        Public Property Nua As String = ""
        Public Property Afp As String = ""
        Public Property Banco As String = ""
        Public Property CuentaBanco As String = ""
        Public Property Estado As String = "A"
        Public Property CentroCostoId As Integer
        Public Property Email As String = ""
        Public Property Telefono As String = ""
        Public Property Direccion As String = ""
        Public Property Eventual As Boolean
        Public Property FechaRetiro As Date?
    End Class

    ''' <summary>Datos de entrada y resultados del cálculo de un empleado en un período.</summary>
    Public Class FilaPlanilla
        Public Property EmpleadoId As Integer
        Public Property Nombre As String
        Public Property Ci As String
        Public Property Cargo As String
        Public Property FechaIngreso As Date
        Public Property HaberBasico As Decimal
        ' entradas
        Public Property Dias As Integer = 30
        Public Property HorasExtras As Decimal
        Public Property BonoProd As Decimal
        Public Property BonoDom As Decimal
        Public Property OtrosIngresos As Decimal
        Public Property Facturas As Decimal
        Public Property SaldoAnterior As Decimal
        Public Property FactorUfvSaldo As Decimal = 1D
        Public Property Anticipo As Decimal
        Public Property Prestamo As Decimal
        Public Property OtrosDesc As Decimal
        ' resultados
        Public Property Haber As Decimal
        Public Property BonoAntig As Decimal
        Public Property MontoHorasExtras As Decimal
        Public Property TotalGanado As Decimal
        Public Property AfpVejez As Decimal
        Public Property AfpRiesgo As Decimal
        Public Property AfpComision As Decimal
        Public Property AfpSolidario As Decimal
        Public Property Ans As Decimal
        Public Property TotalAfp As Decimal
        Public Property IngresoNeto As Decimal
        Public Property MinimoNoImp As Decimal
        Public Property BaseImponible As Decimal
        Public Property RcIvaBruto As Decimal
        Public Property Cred2Smn As Decimal
        Public Property CredFacturas As Decimal
        Public Property SaldoAnteriorAct As Decimal
        Public Property RcIvaRet As Decimal
        Public Property SaldoSiguiente As Decimal
        Public Property TotalDesc As Decimal
        Public Property Liquido As Decimal
        Public Property PatCns As Decimal
        Public Property PatRiesgoProf As Decimal
        Public Property PatVivienda As Decimal
        Public Property PatSolidario As Decimal
        Public Property TotalPatronal As Decimal
        Public Property ProvAguinaldo As Decimal
        Public Property ProvIndem As Decimal
    End Class

    Public Class PlanillaPeriodoInfo
        Public Property Id As Integer
        Public Property Anio As Integer
        Public Property Mes As Integer
        Public Property Tipo As String
        Public Property TC As Decimal
        Public Property Estado As String
        Public Property ComprobanteId As Integer
        Public Property Smn As Decimal
    End Class

    ''' <summary>Planilla de sueldos: bono de antigüedad, aportes AFP, aporte nacional solidario, RC-IVA, aportes patronales y provisiones.</summary>
    Public Class PlanillaService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        ' ---------- Empleados ----------
        Public Function ListarEmpleados(Optional soloActivos As Boolean = False) As DataTable
            Return Db.Query("SELECT * FROM Empleado" & If(soloActivos, " WHERE Estado='A'", "") & " ORDER BY Nombre")
        End Function

        Public Function ObtenerEmpleado(id As Integer) As EmpleadoDto
            Dim dt As DataTable = Db.Query("SELECT * FROM Empleado WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Dim r As DataRow = dt.Rows(0)
            Return New EmpleadoDto With {
                .Id = id, .Item = r.GetS("Item"), .Nombre = r.GetS("Nombre"), .Ci = r.GetS("Ci"), .FechaIngreso = r.GetDt("FechaIngreso"), .FechaNac = ToDateOrNull(r.Cell("FechaNac")),
                .Cargo = r.GetS("Cargo"), .Haber = r.GetD("Haber"), .Nua = r.GetS("Nua"), .Afp = r.GetS("Afp"), .Banco = r.GetS("Banco"), .CuentaBanco = r.GetS("CuentaBanco"),
                .Estado = r.GetS("Estado"), .CentroCostoId = r.GetI("CentroCostoId"), .Email = r.GetS("Email"), .Telefono = r.GetS("Telefono"), .Direccion = r.GetS("Direccion"),
                .Eventual = r.GetF("Eventual"), .FechaRetiro = ToDateOrNull(r.Cell("FechaRetiro"))}
        End Function

        Public Function GuardarEmpleado(e As EmpleadoDto) As Integer
            _ctx.Requiere("RH.EMPLEADOS")
            _ctx.RequiereGestionAbierta()
            If If(e.Nombre, "").Trim() = "" Then Throw New ArgumentException("El nombre del empleado es obligatorio.")
            If e.Haber <= 0D Then Throw New ArgumentException("El haber básico debe ser mayor a cero.")
            If e.Id = 0 Then
                e.Id = Db.Insert("INSERT INTO Empleado (Item, Nombre, Ci, FechaIngreso, FechaNac, Cargo, Haber, Nua, Afp, Banco, CuentaBanco, Estado, CentroCostoId, Email, Telefono, Direccion, Eventual, FechaRetiro) VALUES (@it, @n, @ci, @fi, @fn, @ca, @h, @nua, @afp, @b, @cb, @es, @cc, @em, @te, @di, @ev, @fr)",
                                 "it", e.Item, "n", e.Nombre.Trim(), "ci", e.Ci, "fi", e.FechaIngreso.Date, "fn", OrNull(e.FechaNac), "ca", e.Cargo, "h", e.Haber, "nua", e.Nua, "afp", e.Afp, "b", e.Banco,
                                 "cb", e.CuentaBanco, "es", e.Estado, "cc", OrNull(e.CentroCostoId), "em", e.Email, "te", e.Telefono, "di", e.Direccion, "ev", If(e.Eventual, 1, 0), "fr", OrNull(e.FechaRetiro))
                _ctx.Audit("Planillas", "EMPLEADO_NUEVO", e.Nombre)
            Else
                Db.Execute("UPDATE Empleado SET Item=@it, Nombre=@n, Ci=@ci, FechaIngreso=@fi, FechaNac=@fn, Cargo=@ca, Haber=@h, Nua=@nua, Afp=@afp, Banco=@b, CuentaBanco=@cb, Estado=@es, CentroCostoId=@cc, Email=@em, Telefono=@te, Direccion=@di, Eventual=@ev, FechaRetiro=@fr WHERE Id=@i",
                           "it", e.Item, "n", e.Nombre.Trim(), "ci", e.Ci, "fi", e.FechaIngreso.Date, "fn", OrNull(e.FechaNac), "ca", e.Cargo, "h", e.Haber, "nua", e.Nua, "afp", e.Afp, "b", e.Banco,
                           "cb", e.CuentaBanco, "es", e.Estado, "cc", OrNull(e.CentroCostoId), "em", e.Email, "te", e.Telefono, "di", e.Direccion, "ev", If(e.Eventual, 1, 0), "fr", OrNull(e.FechaRetiro), "i", e.Id)
                _ctx.Audit("Planillas", "EMPLEADO_MOD", e.Nombre)
            End If
            Return e.Id
        End Function

        Public Sub EliminarEmpleado(id As Integer)
            _ctx.Requiere("RH.EMPLEADOS")
            If Db.ScalarInt("SELECT COUNT(*) FROM PlanillaDet WHERE EmpleadoId=@i", "i", id) > 0 Then Throw New InvalidOperationException("El empleado figura en planillas. Márquelo como retirado.")
            Db.Execute("DELETE FROM AnticipoSueldo WHERE EmpleadoId=@i", "i", id)
            Db.Execute("DELETE FROM Empleado WHERE Id=@i", "i", id)
        End Sub

        ' ---------- Cálculo ----------
        ''' <summary>Porcentaje del bono de antigüedad según años cumplidos (escala D.S. 21060).</summary>
        Public Shared Function PorcentajeAntiguedad(anios As Integer) As Decimal
            If anios >= 25 Then Return 50D
            If anios >= 20 Then Return 42D
            If anios >= 15 Then Return 34D
            If anios >= 11 Then Return 26D
            If anios >= 8 Then Return 18D
            If anios >= 5 Then Return 11D
            If anios >= 2 Then Return 5D
            Return 0D
        End Function

        Public Shared Function AniosCumplidos(ingreso As Date, al As Date) As Integer
            Dim a As Integer = al.Year - ingreso.Year
            If al < ingreso.AddYears(a) Then a -= 1
            Return Math.Max(0, a)
        End Function

        ''' <summary>Calcula todos los conceptos de una fila (función pura sobre parámetros).</summary>
        Public Sub Calcular(f As FilaPlanilla, fin As Date, smn As Decimal)
            Dim p As Parametros = _ctx.Param
            Dim diasMes As Decimal = p.Dec(ParamKeys.PlDiasMes, 30D)
            Dim dias As Decimal = Math.Max(0, Math.Min(f.Dias, CInt(diasMes)))
            f.Haber = (f.HaberBasico * dias / diasMes).R2()
            Dim anios As Integer = AniosCumplidos(f.FechaIngreso, fin)
            f.BonoAntig = (3D * smn * PorcentajeAntiguedad(anios) / 100D * dias / diasMes).R2()
            Dim valorHora As Decimal = f.HaberBasico / diasMes / 8D
            f.MontoHorasExtras = (f.HorasExtras * valorHora * 2D).R2()
            f.TotalGanado = f.Haber + f.BonoAntig + f.MontoHorasExtras + f.BonoProd + f.BonoDom + f.OtrosIngresos
            Dim ganado As Decimal = f.TotalGanado
            f.AfpVejez = (ganado * p.Dec(ParamKeys.PlAfpVejez, 10D) / 100D).R2()
            f.AfpRiesgo = (ganado * p.Dec(ParamKeys.PlAfpRiesgo, 1.71D) / 100D).R2()
            f.AfpComision = (ganado * p.Dec(ParamKeys.PlAfpComision, 0.5D) / 100D).R2()
            f.AfpSolidario = (ganado * p.Dec(ParamKeys.PlAfpSolidario, 0.5D) / 100D).R2()
            Dim t1 As Decimal = p.Dec(ParamKeys.PlAnsTramo1, 13000D), t2 As Decimal = p.Dec(ParamKeys.PlAnsTramo2, 25000D), t3 As Decimal = p.Dec(ParamKeys.PlAnsTramo3, 35000D)
            Dim ans As Decimal = 0D
            If ganado > t1 Then ans += (Math.Min(ganado, t2) - t1) * 0.01D
            If ganado > t2 Then ans += (Math.Min(ganado, t3) - t2) * 0.05D
            If ganado > t3 Then ans += (ganado - t3) * 0.1D
            f.Ans = ans.R2()
            f.TotalAfp = f.AfpVejez + f.AfpRiesgo + f.AfpComision + f.AfpSolidario + f.Ans
            f.IngresoNeto = f.TotalGanado - f.TotalAfp
            ' RC-IVA
            Dim pct As Decimal = p.Dec(ParamKeys.PlRcIvaPct, 13D) / 100D
            f.MinimoNoImp = p.Dec(ParamKeys.PlRcIvaMinSmn, 4D) * smn
            f.BaseImponible = Math.Max(0D, f.IngresoNeto - f.MinimoNoImp)
            f.RcIvaBruto = (f.BaseImponible * pct).R2()
            f.Cred2Smn = Math.Min(f.RcIvaBruto, (p.Dec(ParamKeys.PlRcIvaCredSmn, 2D) * smn * pct).R2())
            f.CredFacturas = (f.Facturas * pct).R2()
            f.SaldoAnteriorAct = (f.SaldoAnterior * f.FactorUfvSaldo).R2()
            Dim d As Decimal = f.RcIvaBruto - f.Cred2Smn - f.CredFacturas - f.SaldoAnteriorAct
            If d > 0D Then
                f.RcIvaRet = d
                f.SaldoSiguiente = 0D
            Else
                f.RcIvaRet = 0D
                f.SaldoSiguiente = -d
            End If
            f.TotalDesc = f.TotalAfp + f.RcIvaRet + f.Anticipo + f.Prestamo + f.OtrosDesc
            f.Liquido = f.TotalGanado - f.TotalDesc
            f.PatCns = (ganado * p.Dec(ParamKeys.PlPatCns, 10D) / 100D).R2()
            f.PatRiesgoProf = (ganado * p.Dec(ParamKeys.PlPatRiesgo, 1.71D) / 100D).R2()
            f.PatVivienda = (ganado * p.Dec(ParamKeys.PlPatVivienda, 2D) / 100D).R2()
            f.PatSolidario = (ganado * p.Dec(ParamKeys.PlPatSolidario, 3D) / 100D).R2()
            f.TotalPatronal = f.PatCns + f.PatRiesgoProf + f.PatVivienda + f.PatSolidario
            f.ProvAguinaldo = (ganado / 12D).R2()
            f.ProvIndem = (ganado / 12D).R2()
        End Sub

        ' ---------- Períodos ----------
        Public Function ObtenerPeriodo(anio As Integer, mes As Integer, Optional tipo As String = "S") As PlanillaPeriodoInfo
            Dim dt As DataTable = Db.Query("SELECT * FROM PlanillaPeriodo WHERE Anio=@a AND Mes=@m AND Tipo=@t", "a", anio, "m", mes, "t", tipo)
            If dt.Rows.Count = 0 Then Return Nothing
            Return LeerPeriodo(dt.Rows(0))
        End Function

        Private Shared Function LeerPeriodo(r As DataRow) As PlanillaPeriodoInfo
            Return New PlanillaPeriodoInfo With {.Id = r.GetI("Id"), .Anio = r.GetI("Anio"), .Mes = r.GetI("Mes"), .Tipo = r.GetS("Tipo"), .TC = ToDec(r("TC")), .Estado = r.GetS("Estado"), .ComprobanteId = r.GetI("ComprobanteId"), .Smn = r.GetD("Smn")}
        End Function

        ''' <summary>Crea el período (si no existe) y prepara una fila por cada empleado activo con sus anticipos del mes.</summary>
        Public Function AbrirPeriodo(anio As Integer, mes As Integer, Optional tipo As String = "S") As PlanillaPeriodoInfo
            _ctx.Requiere("RH.PLANILLA")
            _ctx.RequiereGestionAbierta()
            Dim existente As PlanillaPeriodoInfo = ObtenerPeriodo(anio, mes, tipo)
            If existente IsNot Nothing Then Return existente
            Dim fin As New Date(anio, mes, Date.DaysInMonth(anio, mes))
            If fin < _ctx.Gestion.FechaInicio.Date OrElse fin.AddDays(-Date.DaysInMonth(anio, mes) + 1) > _ctx.Gestion.FechaFin.Date Then Throw New InvalidOperationException("El mes está fuera de la gestión.")
            Dim smn As Decimal = _ctx.Param.Dec(ParamKeys.Smn, 0D)
            If smn <= 0D Then Throw New InvalidOperationException("Configure el salario mínimo nacional en Parámetros > Planillas.")
            Dim tc As Decimal = New TipoCambioService(_ctx).Dolar(fin)
            Return Db.InTx(Function()
                               Dim id As Integer = Db.Insert("INSERT INTO PlanillaPeriodo (Anio, Mes, Tipo, TC, Estado, ComprobanteId, Smn) VALUES (@a, @m, @t, @tc, 'A', 0, @s)", "a", anio, "m", mes, "t", tipo, "tc", CDbl(tc), "s", smn)
                               Dim periodo As PlanillaPeriodoInfo = ObtenerPeriodo(anio, mes, tipo)
                               Dim prev As Date = New Date(anio, mes, 1).AddMonths(-1)
                               For Each emp As DataRow In Db.Query("SELECT * FROM Empleado WHERE Estado='A' AND FechaIngreso <= @f AND Eventual=@ev ORDER BY Nombre", "f", fin, "ev", If(tipo = "E", 1, 0)).Rows
                                   Dim f As New FilaPlanilla With {.EmpleadoId = emp.GetI("Id"), .Nombre = emp.GetS("Nombre"), .Ci = emp.GetS("Ci"), .Cargo = emp.GetS("Cargo"), .FechaIngreso = emp.GetDt("FechaIngreso"), .HaberBasico = emp.GetD("Haber")}
                                   ' ingresó en el mes: días proporcionales
                                   If f.FechaIngreso.Year = anio AndAlso f.FechaIngreso.Month = mes Then f.Dias = Math.Max(1, 30 - f.FechaIngreso.Day + 1)
                                   f.Anticipo = Db.ScalarDec("SELECT SUM(Confirmado) FROM AnticipoSueldo WHERE EmpleadoId=@e AND Anio=@a AND Mes=@m", "e", f.EmpleadoId, "a", anio, "m", mes)
                                   Dim ant As DataTable = Db.Query("SELECT d.SaldoSiguiente FROM PlanillaDet d INNER JOIN PlanillaPeriodo p ON p.Id = d.PeriodoId WHERE d.EmpleadoId=@e AND p.Tipo=@t AND (p.Anio * 12 + p.Mes) < @k ORDER BY p.Anio DESC, p.Mes DESC", "e", f.EmpleadoId, "t", tipo, "k", anio * 12 + mes)
                                   If ant.Rows.Count > 0 Then f.SaldoAnterior = ant.Rows(0).GetD("SaldoSiguiente")
                                   Dim tcs As New TipoCambioService(_ctx)
                                   Dim u1 As Decimal = tcs.Ufv(New Date(anio, mes, 1).AddDays(-1)), u0 As Decimal = tcs.Ufv(New Date(anio, mes, 1).AddMonths(-1).AddDays(-1))
                                   If u1 > 0D AndAlso u0 > 0D Then f.FactorUfvSaldo = u1 / u0
                                   Calcular(f, fin, smn)
                                   Insertar(id, f)
                               Next
                               _ctx.Audit("Planillas", "PERIODO_ABIERTO", anio & "-" & mes.ToString("00"))
                               Return ObtenerPeriodo(anio, mes, tipo)
                           End Function)
        End Function

        Private Sub Insertar(periodoId As Integer, f As FilaPlanilla)
            Db.Execute("INSERT INTO PlanillaDet (PeriodoId, EmpleadoId, Dias, Haber, BonoAntig, HorasExtras, MontoHorasExtras, BonoProd, BonoDom, OtrosIngresos, TotalGanado, AfpVejez, AfpRiesgo, AfpComision, AfpSolidario, Ans, TotalAfp, IngresoNeto, MinimoNoImp, BaseImponible, RcIvaBruto, Cred2Smn, Facturas, CredFacturas, SaldoAnterior, SaldoAnteriorAct, RcIvaRet, SaldoSiguiente, Anticipo, Prestamo, OtrosDesc, TotalDesc, Liquido, PatCns, PatRiesgoProf, PatVivienda, PatSolidario, TotalPatronal, ProvAguinaldo, ProvIndem) " &
                       "VALUES (@p, @e, @di, @ha, @ba, @he, @mhe, @bp, @bd, @oi, @tg, @av, @ar, @ac, @as, @ans, @ta, @in, @mn, @bi, @rb, @c2, @fa, @cf, @sa, @saa, @rr, @ss, @an, @pr, @od, @td, @li, @pc, @prp, @pv, @ps, @tp, @pa, @pi)",
                       "p", periodoId, "e", f.EmpleadoId, "di", f.Dias, "ha", f.Haber, "ba", f.BonoAntig, "he", CDbl(f.HorasExtras), "mhe", f.MontoHorasExtras, "bp", f.BonoProd, "bd", f.BonoDom, "oi", f.OtrosIngresos,
                       "tg", f.TotalGanado, "av", f.AfpVejez, "ar", f.AfpRiesgo, "ac", f.AfpComision, "as", f.AfpSolidario, "ans", f.Ans, "ta", f.TotalAfp, "in", f.IngresoNeto, "mn", f.MinimoNoImp, "bi", f.BaseImponible,
                       "rb", f.RcIvaBruto, "c2", f.Cred2Smn, "fa", f.Facturas, "cf", f.CredFacturas, "sa", f.SaldoAnterior, "saa", f.SaldoAnteriorAct, "rr", f.RcIvaRet, "ss", f.SaldoSiguiente, "an", f.Anticipo,
                       "pr", f.Prestamo, "od", f.OtrosDesc, "td", f.TotalDesc, "li", f.Liquido, "pc", f.PatCns, "prp", f.PatRiesgoProf, "pv", f.PatVivienda, "ps", f.PatSolidario, "tp", f.TotalPatronal, "pa", f.ProvAguinaldo, "pi", f.ProvIndem)
        End Sub

        Public Function Filas(periodoId As Integer) As List(Of FilaPlanilla)
            Dim res As New List(Of FilaPlanilla)
            Dim dt As DataTable = Db.Query("SELECT d.*, e.Nombre AS ENombre, e.Ci AS ECi, e.Cargo AS ECargo, e.FechaIngreso AS EIngreso, e.Haber AS EHaber FROM PlanillaDet d INNER JOIN Empleado e ON e.Id = d.EmpleadoId WHERE d.PeriodoId=@p ORDER BY e.Nombre", "p", periodoId)
            For Each r As DataRow In dt.Rows
                res.Add(New FilaPlanilla With {
                    .EmpleadoId = r.GetI("EmpleadoId"), .Nombre = r.GetS("ENombre"), .Ci = r.GetS("ECi"), .Cargo = r.GetS("ECargo"), .FechaIngreso = r.GetDt("EIngreso"), .HaberBasico = r.GetD("EHaber"),
                    .Dias = r.GetI("Dias"), .HorasExtras = r.GetD("HorasExtras"), .BonoProd = r.GetD("BonoProd"), .BonoDom = r.GetD("BonoDom"), .OtrosIngresos = r.GetD("OtrosIngresos"),
                    .Facturas = r.GetD("Facturas"), .SaldoAnterior = r.GetD("SaldoAnterior"), .FactorUfvSaldo = If(r.GetD("SaldoAnterior") <> 0D, r.GetD("SaldoAnteriorAct") / r.GetD("SaldoAnterior"), 1D),
                    .Anticipo = r.GetD("Anticipo"), .Prestamo = r.GetD("Prestamo"), .OtrosDesc = r.GetD("OtrosDesc"),
                    .Haber = r.GetD("Haber"), .BonoAntig = r.GetD("BonoAntig"), .MontoHorasExtras = r.GetD("MontoHorasExtras"), .TotalGanado = r.GetD("TotalGanado"),
                    .AfpVejez = r.GetD("AfpVejez"), .AfpRiesgo = r.GetD("AfpRiesgo"), .AfpComision = r.GetD("AfpComision"), .AfpSolidario = r.GetD("AfpSolidario"), .Ans = r.GetD("Ans"),
                    .TotalAfp = r.GetD("TotalAfp"), .IngresoNeto = r.GetD("IngresoNeto"), .MinimoNoImp = r.GetD("MinimoNoImp"), .BaseImponible = r.GetD("BaseImponible"),
                    .RcIvaBruto = r.GetD("RcIvaBruto"), .Cred2Smn = r.GetD("Cred2Smn"), .CredFacturas = r.GetD("CredFacturas"), .SaldoAnteriorAct = r.GetD("SaldoAnteriorAct"),
                    .RcIvaRet = r.GetD("RcIvaRet"), .SaldoSiguiente = r.GetD("SaldoSiguiente"), .TotalDesc = r.GetD("TotalDesc"), .Liquido = r.GetD("Liquido"),
                    .PatCns = r.GetD("PatCns"), .PatRiesgoProf = r.GetD("PatRiesgoProf"), .PatVivienda = r.GetD("PatVivienda"), .PatSolidario = r.GetD("PatSolidario"),
                    .TotalPatronal = r.GetD("TotalPatronal"), .ProvAguinaldo = r.GetD("ProvAguinaldo"), .ProvIndem = r.GetD("ProvIndem")})
            Next
            Return res
        End Function

        ''' <summary>Guarda los ingresos/descuentos editados de una fila y recalcula.</summary>
        Public Sub GuardarFila(periodo As PlanillaPeriodoInfo, f As FilaPlanilla)
            _ctx.Requiere("RH.PLANILLA")
            _ctx.RequiereGestionAbierta()
            If periodo.Estado <> "A" Then Throw New InvalidOperationException("La planilla está cerrada.")
            Dim fin As New Date(periodo.Anio, periodo.Mes, Date.DaysInMonth(periodo.Anio, periodo.Mes))
            Calcular(f, fin, periodo.Smn)
            Db.InTx(Sub()
                        Db.Execute("DELETE FROM PlanillaDet WHERE PeriodoId=@p AND EmpleadoId=@e", "p", periodo.Id, "e", f.EmpleadoId)
                        Insertar(periodo.Id, f)
                    End Sub)
        End Sub

        ''' <summary>Cierra la planilla y genera el comprobante contable (sueldos, aportes laborales y patronales, retenciones).</summary>
        Public Function Cerrar(periodo As PlanillaPeriodoInfo, Optional provisionar As Boolean = True) As Integer
            _ctx.Requiere("RH.PLANILLA")
            _ctx.RequiereGestionAbierta()
            If periodo.Estado <> "A" Then Throw New InvalidOperationException("La planilla ya está cerrada.")
            Dim filas As List(Of FilaPlanilla) = Me.Filas(periodo.Id)
            If filas.Count = 0 Then Throw New InvalidOperationException("La planilla no tiene empleados.")
            Dim fin As New Date(periodo.Anio, periodo.Mes, Date.DaysInMonth(periodo.Anio, periodo.Mes))
            Return Db.InTx(Function()
                               Dim vs As New VoucherService(_ctx)
                               Dim v As Voucher = vs.Nuevo("T", fin)
                               v.Glosa = "Planilla de sueldos " & NombreMes(periodo.Mes) & " " & periodo.Anio
                               v.Origen = "PLA" : v.OrigenId = periodo.Id
                               Dim sumHaber As Decimal = filas.Sum(Function(x) x.Haber)
                               Dim sumBono As Decimal = filas.Sum(Function(x) x.BonoAntig)
                               Dim sumHe As Decimal = filas.Sum(Function(x) x.MontoHorasExtras)
                               Dim sumOtros As Decimal = filas.Sum(Function(x) x.BonoProd + x.BonoDom + x.OtrosIngresos)
                               Dim gasto = Sub(clave As String, monto As Decimal)
                                               If monto > 0D Then v.Lines.Add(VoucherLine.Deb(_ctx.CuentaParam(clave), monto, v.Glosa))
                                           End Sub
                               Dim pasivo = Sub(clave As String, monto As Decimal)
                                                If monto > 0D Then v.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(clave), monto, v.Glosa))
                                            End Sub
                               gasto(ParamKeys.CtaSueldos, sumHaber)
                               gasto(ParamKeys.CtaBonoAntig, sumBono)
                               gasto(ParamKeys.CtaHorasExtras, sumHe)
                               gasto(ParamKeys.CtaOtrosBonos, sumOtros)
                               gasto(ParamKeys.CtaGastoCns, filas.Sum(Function(x) x.PatCns))
                               gasto(ParamKeys.CtaGastoRiesgo, filas.Sum(Function(x) x.PatRiesgoProf))
                               gasto(ParamKeys.CtaGastoVivienda, filas.Sum(Function(x) x.PatVivienda))
                               gasto(ParamKeys.CtaGastoSolidario, filas.Sum(Function(x) x.PatSolidario))
                               pasivo(ParamKeys.CtaSueldosPagar, filas.Sum(Function(x) x.Liquido))
                               pasivo(ParamKeys.CtaAfpLaboralPagar, filas.Sum(Function(x) x.TotalAfp))
                               pasivo(ParamKeys.CtaRcIvaPagar, filas.Sum(Function(x) x.RcIvaRet))
                               pasivo(ParamKeys.CtaAnticipoPers, 0D)
                               Dim antPrest As Decimal = filas.Sum(Function(x) x.Anticipo + x.Prestamo)
                               pasivo(ParamKeys.CtaAnticipoPers, antPrest)
                               pasivo(ParamKeys.CtaAcreedores, filas.Sum(Function(x) x.OtrosDesc))
                               pasivo(ParamKeys.CtaAfpPatronalPagar, filas.Sum(Function(x) x.PatRiesgoProf))
                               pasivo(ParamKeys.CtaCnsPagar, filas.Sum(Function(x) x.PatCns))
                               pasivo(ParamKeys.CtaViviendaPagar, filas.Sum(Function(x) x.PatVivienda))
                               pasivo(ParamKeys.CtaSolidarioPagar, filas.Sum(Function(x) x.PatSolidario))
                               ' Los anticipos y préstamos al personal son un activo: su cobro se acredita (cuenta de activo), no un pasivo.
                               Dim vid As Integer = vs.Registrar(v)
                               Db.Execute("UPDATE PlanillaPeriodo SET Estado='C', ComprobanteId=@c, FechaCierre=@f WHERE Id=@i", "c", vid, "f", Date.Now, "i", periodo.Id)
                               If provisionar Then
                                   Dim vp As Voucher = vs.Nuevo("T", fin)
                                   vp.Glosa = "Provisión aguinaldo e indemnización " & NombreMes(periodo.Mes) & " " & periodo.Anio
                                   vp.Origen = "PLA" : vp.OrigenId = periodo.Id
                                   Dim ag As Decimal = filas.Sum(Function(x) x.ProvAguinaldo)
                                   Dim inde As Decimal = filas.Sum(Function(x) x.ProvIndem)
                                   If ag > 0D Then
                                       vp.Lines.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaGastoAguinaldo), ag, vp.Glosa))
                                       vp.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaProvAguinaldo), ag, vp.Glosa))
                                   End If
                                   If inde > 0D Then
                                       vp.Lines.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaGastoIndem), inde, vp.Glosa))
                                       vp.Lines.Add(VoucherLine.Hab(_ctx.CuentaParam(ParamKeys.CtaProvIndem), inde, vp.Glosa))
                                   End If
                                   If vp.Lines.Count >= 2 Then vs.Registrar(vp)
                               End If
                               _ctx.Audit("Planillas", "PLANILLA_CERRADA", periodo.Anio & "-" & periodo.Mes.ToString("00") & " líquido Bs " & filas.Sum(Function(x) x.Liquido).ToString("N2"))
                               Return vid
                           End Function)
        End Function

        Public Sub Reabrir(periodo As PlanillaPeriodoInfo)
            _ctx.Requiere("RH.PLANILLA")
            _ctx.RequiereGestionAbierta()
            If periodo.Estado <> "C" Then Return
            Db.InTx(Sub()
                        Dim vs As New VoucherService(_ctx)
                        Dim ids As DataTable = Db.Query("SELECT Id FROM Comprobante WHERE Origen='PLA' AND OrigenId=@o AND Estado='V'", "o", periodo.Id)
                        For Each r As DataRow In ids.Rows
                            vs.AnularInterno(r.GetI("Id"), "Reapertura de planilla")
                        Next
                        Db.Execute("UPDATE PlanillaPeriodo SET Estado='A', ComprobanteId=0 WHERE Id=@i", "i", periodo.Id)
                    End Sub)
        End Sub

        Public Sub EliminarPeriodo(periodo As PlanillaPeriodoInfo)
            _ctx.Requiere("RH.PLANILLA")
            If periodo.Estado <> "A" Then Throw New InvalidOperationException("Reabra la planilla antes de eliminarla.")
            Db.InTx(Sub()
                        Db.Execute("DELETE FROM PlanillaDet WHERE PeriodoId=@i", "i", periodo.Id)
                        Db.Execute("DELETE FROM PlanillaPeriodo WHERE Id=@i", "i", periodo.Id)
                    End Sub)
        End Sub

        ' ---------- Anticipos ----------
        Public Function Anticipos(anio As Integer, mes As Integer) As DataTable
            Return Db.Query("SELECT a.Id, a.EmpleadoId, e.Nombre, a.Fecha, a.Monto, a.Confirmado, a.Detalle FROM AnticipoSueldo a INNER JOIN Empleado e ON e.Id = a.EmpleadoId WHERE a.Anio=@a AND a.Mes=@m ORDER BY e.Nombre, a.Fecha", "a", anio, "m", mes)
        End Function

        Public Sub GuardarAnticipo(empleadoId As Integer, fecha As Date, monto As Decimal, confirmado As Decimal, detalle As String)
            _ctx.Requiere("RH.PLANILLA")
            If monto <= 0D Then Throw New ArgumentException("El monto debe ser mayor a cero.")
            Db.Execute("INSERT INTO AnticipoSueldo (EmpleadoId, Anio, Mes, Fecha, Monto, Confirmado, Detalle) VALUES (@e, @a, @m, @f, @mo, @c, @d)",
                       "e", empleadoId, "a", fecha.Year, "m", fecha.Month, "f", fecha.Date, "mo", monto, "c", confirmado, "d", detalle)
        End Sub

        Public Sub EliminarAnticipo(id As Integer)
            _ctx.Requiere("RH.PLANILLA")
            Db.Execute("DELETE FROM AnticipoSueldo WHERE Id=@i", "i", id)
        End Sub

        ''' <summary>Aguinaldo: promedio de los últimos 3 sueldos líquidos ganados × meses trabajados / 12.</summary>
        Public Function Aguinaldo(anio As Integer, hasta As Date) As DataTable
            Dim res As New DataTable()
            res.Columns.Add("Nombre", GetType(String))
            res.Columns.Add("Ci", GetType(String))
            res.Columns.Add("FechaIngreso", GetType(Date))
            res.Columns.Add("Meses", GetType(Integer))
            res.Columns.Add("Promedio", GetType(Decimal))
            res.Columns.Add("Aguinaldo", GetType(Decimal))
            For Each e As DataRow In ListarEmpleados(True).Rows
                Dim ing As Date = e.GetDt("FechaIngreso")
                Dim ini As New Date(anio, 1, 1)
                Dim desde As Date = If(ing > ini, ing, ini)
                Dim meses As Integer = Math.Max(0, Math.Min(12, (hasta.Year - desde.Year) * 12 + hasta.Month - desde.Month + 1))
                Dim tg As DataTable = Db.Query("SELECT d.TotalGanado FROM PlanillaDet d INNER JOIN PlanillaPeriodo p ON p.Id = d.PeriodoId WHERE d.EmpleadoId=@e AND p.Anio=@a AND p.Tipo='S' ORDER BY p.Mes DESC", "e", e.GetI("Id"), "a", anio)
                Dim top3 As List(Of Decimal) = tg.Rows.Cast(Of DataRow)().Take(3).Select(Function(r) r.GetD("TotalGanado")).ToList()
                Dim prom As Decimal = If(top3.Count = 0, e.GetD("Haber"), top3.Average())
                res.Rows.Add(e.GetS("Nombre"), e.GetS("Ci"), ing, meses, prom.R2(), (prom * meses / 12D).R2())
            Next
            Return res
        End Function

    End Class

End Namespace
