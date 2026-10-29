Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class ActivoDto
        Public Property Id As Integer
        Public Property Codigo As String = ""
        Public Property Nombre As String = ""
        Public Property GrupoId As Integer
        Public Property CuentaActivoId As Integer
        Public Property CuentaDepAcumId As Integer
        Public Property CuentaGastoId As Integer
        Public Property FechaAlta As Date = Date.Today
        Public Property ValorOriginal As Decimal
        Public Property UfvAlta As Decimal
        Public Property TcAlta As Decimal
        Public Property Cantidad As Decimal = 1D
        Public Property PorcDep As Decimal
        Public Property DepAcumInicial As Decimal
        Public Property ValorResidual As Decimal
        Public Property Ubicacion As String = ""
        Public Property Responsable As String = ""
        Public Property Serie As String = ""
        Public Property Marca As String = ""
        Public Property Estado As String = "A"
        Public Property TerceroId As Integer
        Public Property Factura As String = ""
        Public Property CentroCostoId As Integer
        Public Property Observacion As String = ""
    End Class

    Public Class DepreciacionFila
        Public Property ActivoId As Integer
        Public Property Codigo As String
        Public Property Nombre As String
        Public Property ValorAnterior As Decimal
        Public Property ActualizaValor As Decimal
        Public Property ValorActualizado As Decimal
        Public Property DepAnterior As Decimal
        Public Property ActualizaDep As Decimal
        Public Property DepPeriodo As Decimal
        Public Property DepAcum As Decimal
        Public Property ValorNeto As Decimal
    End Class

    Public Class DepreciacionResultado
        Public ReadOnly Property Filas As New List(Of DepreciacionFila)
        Public Property ComprobanteId As Integer
        Public Property Periodo As String
        Public Property UfvFaltante As Boolean
    End Class

    ''' <summary>Activos fijos: alta, depreciación mensual por línea recta con actualización por UFV, baja.</summary>
    Public Class ActivoFijoService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        Public Function Listar(Optional incluirBajas As Boolean = False) As DataTable
            Return Db.Query("SELECT * FROM ActivoFijo" & If(incluirBajas, "", " WHERE Estado='A'") & " ORDER BY Codigo")
        End Function

        Public Function Grupos() As DataTable
            Return Db.Query("SELECT * FROM GrupoActivo ORDER BY Nombre")
        End Function

        Public Function Obtener(id As Integer) As ActivoDto
            Dim dt As DataTable = Db.Query("SELECT * FROM ActivoFijo WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Dim r As DataRow = dt.Rows(0)
            Return New ActivoDto With {
                .Id = id, .Codigo = r.GetS("Codigo"), .Nombre = r.GetS("Nombre"), .GrupoId = r.GetI("GrupoId"), .CuentaActivoId = r.GetI("CuentaActivoId"),
                .CuentaDepAcumId = r.GetI("CuentaDepAcumId"), .CuentaGastoId = r.GetI("CuentaGastoId"), .FechaAlta = r.GetDt("FechaAlta"),
                .ValorOriginal = r.GetD("ValorOriginal"), .UfvAlta = r.GetD("UfvAlta"), .TcAlta = r.GetD("TcAlta"), .Cantidad = r.GetD("Cantidad"),
                .PorcDep = r.GetD("PorcDep"), .DepAcumInicial = r.GetD("DepAcumInicial"), .ValorResidual = r.GetD("ValorResidual"),
                .Ubicacion = r.GetS("Ubicacion"), .Responsable = r.GetS("Responsable"), .Serie = r.GetS("Serie"), .Marca = r.GetS("Marca"),
                .Estado = r.GetS("Estado"), .TerceroId = r.GetI("TerceroId"), .Factura = r.GetS("Factura"), .CentroCostoId = r.GetI("CentroCostoId"),
                .Observacion = r.GetS("Observacion")}
        End Function

        ''' <summary>Asigna al activo las cuentas y el porcentaje de su grupo.</summary>
        Public Sub AplicarGrupo(a As ActivoDto)
            If a.GrupoId = 0 Then Return
            Dim dt As DataTable = Db.Query("SELECT * FROM GrupoActivo WHERE Id=@i", "i", a.GrupoId)
            If dt.Rows.Count = 0 Then Return
            Dim g As DataRow = dt.Rows(0)
            a.PorcDep = g.GetD("PorcDep")
            If g.GetI("CuentaActivoId") <> 0 Then a.CuentaActivoId = g.GetI("CuentaActivoId")
            If g.GetI("CuentaDepAcumId") <> 0 Then a.CuentaDepAcumId = g.GetI("CuentaDepAcumId")
            If g.GetI("CuentaGastoId") <> 0 Then a.CuentaGastoId = g.GetI("CuentaGastoId")
        End Sub

        ''' <summary>Registra un activo. Con generarAsiento crea el comprobante de alta (Debe activo / Haber contracuenta), opcionalmente con factura de compra.</summary>
        Public Function Guardar(a As ActivoDto, Optional generarAsiento As Boolean = False, Optional contracuentaId As Integer = 0, Optional factura As FacturaDto = Nothing) As Integer
            _ctx.Requiere("AF.ACTIVOS")
            _ctx.RequiereGestionAbierta()
            a.Codigo = If(a.Codigo, "").Trim().ToUpperInvariant()
            If a.Codigo = "" Then Throw New ArgumentException("El código del activo es obligatorio.")
            If If(a.Nombre, "").Trim() = "" Then Throw New ArgumentException("El nombre del activo es obligatorio.")
            If a.CuentaActivoId = 0 OrElse a.CuentaDepAcumId = 0 OrElse a.CuentaGastoId = 0 Then Throw New ArgumentException("Seleccione las cuentas del activo, depreciación acumulada y gasto de depreciación (o elija un grupo).")
            If a.ValorOriginal <= 0D Then Throw New ArgumentException("El valor del activo debe ser mayor a cero.")
            If a.PorcDep < 0D OrElse a.PorcDep > 100D Then Throw New ArgumentException("El porcentaje de depreciación debe estar entre 0 y 100.")
            If a.DepAcumInicial < 0D OrElse a.DepAcumInicial > a.ValorOriginal Then Throw New ArgumentException("La depreciación acumulada inicial es inválida.")
            Dim dup As Object = Db.Scalar("SELECT Id FROM ActivoFijo WHERE Codigo=@c", "c", a.Codigo)
            If dup IsNot Nothing AndAlso ToInt(dup) <> a.Id Then Throw New InvalidOperationException("El código " & a.Codigo & " ya existe.")
            If a.UfvAlta <= 0D Then a.UfvAlta = New TipoCambioService(_ctx).Ufv(a.FechaAlta)
            If a.TcAlta <= 0D Then a.TcAlta = New TipoCambioService(_ctx).Dolar(a.FechaAlta)
            Return Db.InTx(Function()
                               If a.Id = 0 Then
                                   a.Id = Db.Insert("INSERT INTO ActivoFijo (Codigo, Nombre, GrupoId, CuentaActivoId, CuentaDepAcumId, CuentaGastoId, FechaAlta, ValorOriginal, UfvAlta, TcAlta, Cantidad, PorcDep, DepAcumInicial, ValorResidual, Ubicacion, Responsable, Serie, Marca, Estado, TerceroId, Factura, CentroCostoId, Observacion) " &
                                                    "VALUES (@c, @n, @g, @ca, @cd, @cg, @f, @v, @u, @tc, @q, @p, @di, @vr, @ub, @re, @se, @ma, 'A', @te, @fa, @cc, @ob)",
                                                    "c", a.Codigo, "n", a.Nombre, "g", OrNull(a.GrupoId), "ca", a.CuentaActivoId, "cd", a.CuentaDepAcumId, "cg", a.CuentaGastoId, "f", a.FechaAlta.Date,
                                                    "v", a.ValorOriginal, "u", CDbl(a.UfvAlta), "tc", CDbl(a.TcAlta), "q", CDbl(a.Cantidad), "p", CDbl(a.PorcDep), "di", a.DepAcumInicial, "vr", a.ValorResidual,
                                                    "ub", a.Ubicacion, "re", a.Responsable, "se", a.Serie, "ma", a.Marca, "te", OrNull(a.TerceroId), "fa", a.Factura, "cc", OrNull(a.CentroCostoId), "ob", a.Observacion)
                                   If generarAsiento Then
                                       If contracuentaId = 0 Then Throw New ArgumentException("Seleccione la contracuenta para el asiento de alta.")
                                       Dim vs As New VoucherService(_ctx)
                                       Dim v As Voucher = vs.Nuevo("T", a.FechaAlta)
                                       v.Glosa = "Alta de activo fijo " & a.Codigo & " " & a.Nombre
                                       v.Origen = "AF" : v.OrigenId = a.Id
                                       If factura IsNot Nothing Then
                                           factura.Libro = "C"
                                           factura.ImporteTotal = a.ValorOriginal
                                           If factura.Fecha = Date.MinValue Then factura.Fecha = a.FechaAlta
                                           Dim fs As New FacturaService(_ctx)
                                           For Each l In fs.LineasCompra(factura, a.CuentaActivoId, v.Glosa)
                                               v.Lines.Add(l)
                                           Next
                                           v.Facturas.Add(factura)
                                       Else
                                           v.Lines.Add(VoucherLine.Deb(a.CuentaActivoId, a.ValorOriginal, v.Glosa))
                                       End If
                                       v.Lines.Add(VoucherLine.Hab(contracuentaId, a.ValorOriginal, v.Glosa))
                                       vs.Registrar(v)
                                   End If
                                   _ctx.Audit("Activos fijos", "AF_NUEVO", a.Codigo & " " & a.Nombre & " Bs " & a.ValorOriginal.ToString("N2"))
                               Else
                                   Db.Execute("UPDATE ActivoFijo SET Codigo=@c, Nombre=@n, GrupoId=@g, CuentaActivoId=@ca, CuentaDepAcumId=@cd, CuentaGastoId=@cg, FechaAlta=@f, ValorOriginal=@v, UfvAlta=@u, TcAlta=@tc, Cantidad=@q, PorcDep=@p, DepAcumInicial=@di, ValorResidual=@vr, Ubicacion=@ub, Responsable=@re, Serie=@se, Marca=@ma, TerceroId=@te, Factura=@fa, CentroCostoId=@cc, Observacion=@ob WHERE Id=@i",
                                              "c", a.Codigo, "n", a.Nombre, "g", OrNull(a.GrupoId), "ca", a.CuentaActivoId, "cd", a.CuentaDepAcumId, "cg", a.CuentaGastoId, "f", a.FechaAlta.Date,
                                              "v", a.ValorOriginal, "u", CDbl(a.UfvAlta), "tc", CDbl(a.TcAlta), "q", CDbl(a.Cantidad), "p", CDbl(a.PorcDep), "di", a.DepAcumInicial, "vr", a.ValorResidual,
                                              "ub", a.Ubicacion, "re", a.Responsable, "se", a.Serie, "ma", a.Marca, "te", OrNull(a.TerceroId), "fa", a.Factura, "cc", OrNull(a.CentroCostoId), "ob", a.Observacion, "i", a.Id)
                                   _ctx.Audit("Activos fijos", "AF_MOD", a.Codigo)
                               End If
                               Return a.Id
                           End Function)
        End Function

        Public Sub Eliminar(id As Integer)
            _ctx.Requiere("AF.ACTIVOS")
            If Db.ScalarInt("SELECT COUNT(*) FROM DepreciacionAF WHERE ActivoId=@i", "i", id) > 0 Then Throw New InvalidOperationException("El activo tiene depreciaciones registradas. Use la baja del activo.")
            Db.Execute("DELETE FROM ActivoFijo WHERE Id=@i", "i", id)
        End Sub

        Public Shared Function Periodo(fecha As Date) As String
            Return fecha.ToString("yyyy-MM")
        End Function

        ''' <summary>Calcula (y opcionalmente registra) la depreciación del mes de la fecha indicada para todos los activos vigentes.</summary>
        Public Function Depreciar(fechaPeriodo As Date, registrar As Boolean) As DepreciacionResultado
            If registrar Then
                _ctx.Requiere("AF.DEPRECIAR")
                _ctx.RequiereGestionAbierta()
            End If
            Dim fin As Date = FinDeMes(fechaPeriodo)
            Dim per As String = Periodo(fin)
            If fin < _ctx.Gestion.FechaInicio.Date OrElse fin > _ctx.Gestion.FechaFin.Date Then Throw New InvalidOperationException("El período está fuera de la gestión.")
            Dim res As New DepreciacionResultado With {.Periodo = per}
            Dim tc As New TipoCambioService(_ctx)
            Dim ufvFin As Decimal = tc.Ufv(fin)
            res.UfvFaltante = ufvFin <= 0D
            Dim lineasActivo As New Dictionary(Of Integer, Decimal)
            Dim lineasDepAcumAct As New Dictionary(Of Integer, Decimal)
            Dim lineasGasto As New Dictionary(Of Integer, Decimal)
            Dim lineasDepAcumPer As New Dictionary(Of Integer, Decimal)
            Dim filas As New List(Of Tuple(Of ActivoDto, DepreciacionFila, Decimal, Decimal, Decimal))
            Dim activos As DataTable = Db.Query("SELECT Id FROM ActivoFijo WHERE Estado='A' AND FechaAlta <= @f ORDER BY Codigo", "f", fin)
            For Each r As DataRow In activos.Rows
                Dim a As ActivoDto = Obtener(r.GetI("Id"))
                If Db.ScalarInt("SELECT COUNT(*) FROM DepreciacionAF WHERE ActivoId=@a AND Periodo=@p", "a", a.Id, "p", per) > 0 Then Continue For
                ' un período anterior sin registrar interrumpe la secuencia (se exige orden cronológico)
                Dim prev As DataTable = Db.Query("SELECT * FROM DepreciacionAF WHERE ActivoId=@a AND Periodo < @p ORDER BY Periodo DESC", "a", a.Id, "p", per)
                Dim valorPrev As Decimal, depPrev As Decimal, ufvIni As Decimal
                If prev.Rows.Count > 0 Then
                    valorPrev = prev.Rows(0).GetD("ValorAct")
                    depPrev = prev.Rows(0).GetD("DepAcum")
                    ufvIni = ToDec(prev.Rows(0)("UfvFin"))
                Else
                    valorPrev = a.ValorOriginal
                    depPrev = a.DepAcumInicial
                    ufvIni = a.UfvAlta
                End If
                Dim factor As Decimal = 1D
                If ufvIni > 0D AndAlso ufvFin > 0D Then factor = ufvFin / ufvIni
                Dim valorAct As Decimal = (valorPrev * factor).R2()
                Dim actVal As Decimal = valorAct - valorPrev
                Dim actDep As Decimal = (depPrev * (factor - 1D)).R2()
                Dim dep As Decimal = (valorAct * a.PorcDep / 100D / 12D).R2()
                Dim maximo As Decimal = valorAct - a.ValorResidual - (depPrev + actDep)
                If maximo < 0D Then maximo = 0D
                If dep > maximo Then dep = maximo
                Dim acum As Decimal = depPrev + actDep + dep
                Dim f As New DepreciacionFila With {.ActivoId = a.Id, .Codigo = a.Codigo, .Nombre = a.Nombre, .ValorAnterior = valorPrev, .ActualizaValor = actVal, .ValorActualizado = valorAct,
                    .DepAnterior = depPrev, .ActualizaDep = actDep, .DepPeriodo = dep, .DepAcum = acum, .ValorNeto = valorAct - acum}
                res.Filas.Add(f)
                filas.Add(Tuple.Create(a, f, ufvIni, ufvFin, 0D))
            Next
            If Not registrar OrElse res.Filas.Count = 0 Then Return res
            Db.InTx(Sub()
                        Dim vs As New VoucherService(_ctx)
                        Dim v As Voucher = vs.Nuevo("T", fin)
                        v.Glosa = "Depreciación y actualización de activos fijos - período " & per
                        v.Origen = "AF"
                        Dim aj As Integer = _ctx.CuentaParam(ParamKeys.CtaAjusteInflIng)
                        Dim ajE As Integer = _ctx.CuentaParam(ParamKeys.CtaAjusteInflEgr)
                        Dim totActVal As Decimal = 0D, totActDep As Decimal = 0D
                        For Each t In filas
                            Dim a As ActivoDto = t.Item1
                            Dim f As DepreciacionFila = t.Item2
                            Add(lineasActivo, a.CuentaActivoId, f.ActualizaValor)
                            Add(lineasDepAcumAct, a.CuentaDepAcumId, f.ActualizaDep)
                            Add(lineasGasto, a.CuentaGastoId, f.DepPeriodo)
                            Add(lineasDepAcumPer, a.CuentaDepAcumId, f.DepPeriodo)
                            totActVal += f.ActualizaValor
                            totActDep += f.ActualizaDep
                        Next
                        ' Actualización del valor: Debe activo / Haber ajuste por inflación (ingreso)
                        For Each kv In lineasActivo
                            DebitoNeto(v, kv.Key, kv.Value)
                        Next
                        If totActVal >= 0D Then DebitoNeto(v, aj, -totActVal) Else DebitoNeto(v, ajE, -totActVal)
                        ' Actualización de la depreciación acumulada: Debe ajuste (gasto) / Haber dep. acumulada
                        For Each kv In lineasDepAcumAct
                            DebitoNeto(v, kv.Key, -kv.Value)
                        Next
                        If totActDep >= 0D Then DebitoNeto(v, ajE, totActDep) Else DebitoNeto(v, aj, totActDep)
                        ' Depreciación del período
                        For Each kv In lineasGasto
                            If kv.Value > 0D Then v.Lines.Add(VoucherLine.Deb(kv.Key, kv.Value, v.Glosa))
                        Next
                        For Each kv In lineasDepAcumPer
                            If kv.Value > 0D Then v.Lines.Add(VoucherLine.Hab(kv.Key, kv.Value, v.Glosa))
                        Next
                        v.Lines.RemoveAll(Function(l) l.Debe = 0D AndAlso l.Haber = 0D)
                        Dim vid As Integer = 0
                        If v.Lines.Count >= 2 Then
                            vid = vs.Registrar(v)
                        End If
                        res.ComprobanteId = vid
                        For Each t In filas
                            Dim f As DepreciacionFila = t.Item2
                            Db.Execute("INSERT INTO DepreciacionAF (ActivoId, Fecha, Periodo, UfvIni, UfvFin, ValorAct, ActualizaValor, DepPeriodo, ActualizaDep, DepAcum, ValorNeto, ComprobanteId) VALUES (@a, @f, @p, @ui, @uf, @va, @av, @dp, @ad, @da, @vn, @c)",
                                       "a", f.ActivoId, "f", fin, "p", per, "ui", CDbl(t.Item3), "uf", CDbl(t.Item4), "va", f.ValorActualizado, "av", f.ActualizaValor, "dp", f.DepPeriodo, "ad", f.ActualizaDep, "da", f.DepAcum, "vn", f.ValorNeto, "c", vid)
                        Next
                        _ctx.Audit("Activos fijos", "DEPRECIACION", per & " (" & filas.Count & " activos)")
                    End Sub)
            Return res
        End Function

        ' Agrega una línea al Debe si el monto es positivo, o al Haber (valor absoluto) si es negativo.
        Private Shared Sub DebitoNeto(v As Voucher, cuentaId As Integer, monto As Decimal)
            If monto > 0D Then
                v.Lines.Add(VoucherLine.Deb(cuentaId, monto, v.Glosa))
            ElseIf monto < 0D Then
                v.Lines.Add(VoucherLine.Hab(cuentaId, -monto, v.Glosa))
            End If
        End Sub

        Private Shared Sub Add(d As Dictionary(Of Integer, Decimal), k As Integer, v As Decimal)
            d(k) = (If(d.ContainsKey(k), d(k), 0D)) + v
        End Sub

        ''' <summary>Deshace la depreciación de un período (solo el último período registrado).</summary>
        Public Sub AnularDepreciacion(periodo As String)
            _ctx.Requiere("AF.DEPRECIAR")
            _ctx.RequiereGestionAbierta()
            If Db.ScalarInt("SELECT COUNT(*) FROM DepreciacionAF WHERE Periodo > @p", "p", periodo) > 0 Then Throw New InvalidOperationException("Solo puede anularse el último período depreciado.")
            Dim cids As DataTable = Db.Query("SELECT DISTINCT ComprobanteId FROM DepreciacionAF WHERE Periodo=@p", "p", periodo)
            Db.InTx(Sub()
                        Dim vs As New VoucherService(_ctx)
                        For Each r As DataRow In cids.Rows
                            If r.GetI("ComprobanteId") <> 0 Then vs.AnularInterno(r.GetI("ComprobanteId"), "Anulación depreciación " & periodo)
                        Next
                        Db.Execute("DELETE FROM DepreciacionAF WHERE Periodo=@p", "p", periodo)
                    End Sub)
        End Sub

        ''' <summary>Baja del activo: retira costo y depreciación acumulada, la diferencia va a pérdida por baja.</summary>
        Public Function Baja(id As Integer, fecha As Date, motivo As String, Optional generarAsiento As Boolean = True) As Integer
            _ctx.Requiere("AF.ACTIVOS")
            _ctx.RequiereGestionAbierta()
            Dim a As ActivoDto = Obtener(id)
            If a Is Nothing OrElse a.Estado <> "A" Then Throw New InvalidOperationException("El activo no está vigente.")
            Dim ult As DataTable = Db.Query("SELECT * FROM DepreciacionAF WHERE ActivoId=@a ORDER BY Periodo DESC", "a", id)
            Dim valor As Decimal = a.ValorOriginal, dep As Decimal = a.DepAcumInicial
            If ult.Rows.Count > 0 Then
                valor = ult.Rows(0).GetD("ValorAct")
                dep = ult.Rows(0).GetD("DepAcum")
            End If
            Return Db.InTx(Function()
                               Dim vid As Integer = 0
                               If generarAsiento Then
                                   Dim vs As New VoucherService(_ctx)
                                   Dim v As Voucher = vs.Nuevo("T", fecha)
                                   v.Glosa = "Baja de activo fijo " & a.Codigo & " " & a.Nombre & " - " & motivo
                                   v.Origen = "AF" : v.OrigenId = id
                                   If dep > 0D Then v.Lines.Add(VoucherLine.Deb(a.CuentaDepAcumId, dep, v.Glosa))
                                   If valor - dep > 0D Then v.Lines.Add(VoucherLine.Deb(_ctx.CuentaParam(ParamKeys.CtaBajaAf), valor - dep, v.Glosa))
                                   v.Lines.Add(VoucherLine.Hab(a.CuentaActivoId, valor, v.Glosa))
                                   vid = vs.Registrar(v)
                               End If
                               Db.Execute("UPDATE ActivoFijo SET Estado='B', FechaBaja=@f, MotivoBaja=@m WHERE Id=@i", "f", fecha.Date, "m", motivo, "i", id)
                               _ctx.Audit("Activos fijos", "AF_BAJA", a.Codigo & ": " & motivo)
                               Return vid
                           End Function)
        End Function

        ''' <summary>Cuadro de activos con último valor actualizado, depreciación acumulada y valor neto a una fecha.</summary>
        Public Function Cuadro(hasta As Date) As DataTable
            Dim res As New DataTable()
            res.Columns.Add("Codigo", GetType(String))
            res.Columns.Add("Nombre", GetType(String))
            res.Columns.Add("FechaAlta", GetType(Date))
            res.Columns.Add("ValorOriginal", GetType(Decimal))
            res.Columns.Add("ValorActualizado", GetType(Decimal))
            res.Columns.Add("PorcDep", GetType(Decimal))
            res.Columns.Add("DepAcum", GetType(Decimal))
            res.Columns.Add("ValorNeto", GetType(Decimal))
            res.Columns.Add("Ubicacion", GetType(String))
            res.Columns.Add("Estado", GetType(String))
            For Each r As DataRow In Listar(False).Rows
                Dim ult As DataTable = Db.Query("SELECT * FROM DepreciacionAF WHERE ActivoId=@a AND Fecha <= @h ORDER BY Periodo DESC", "a", r.GetI("Id"), "h", hasta.Date)
                Dim va As Decimal = r.GetD("ValorOriginal"), da As Decimal = r.GetD("DepAcumInicial")
                If ult.Rows.Count > 0 Then
                    va = ult.Rows(0).GetD("ValorAct")
                    da = ult.Rows(0).GetD("DepAcum")
                End If
                If r.GetDt("FechaAlta") > hasta.Date Then Continue For
                res.Rows.Add(r.GetS("Codigo"), r.GetS("Nombre"), r.GetDt("FechaAlta"), r.GetD("ValorOriginal"), va, r.GetD("PorcDep"), da, va - da, r.GetS("Ubicacion"), r.GetS("Estado"))
            Next
            Return res
        End Function

    End Class

End Namespace
