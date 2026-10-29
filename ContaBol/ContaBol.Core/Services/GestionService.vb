Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class AjusteFila
        Public Property CuentaId As Integer
        Public Property Codigo As String
        Public Property Nombre As String
        Public Property SaldoBs As Decimal
        Public Property SaldoUsd As Decimal
        Public Property Actualizado As Decimal
        Public Property Ajuste As Decimal
    End Class

    Public Class AjusteResultado
        Public ReadOnly Property Filas As New List(Of AjusteFila)
        Public Property ComprobanteId As Integer
        Public Property Total As Decimal
    End Class

    ''' <summary>Cierre de gestión, apertura de la siguiente gestión, ajuste por inflación (UFV) y diferencia de cambio.</summary>
    Public Class GestionService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        ' ---------- Cierre ----------
        ''' <summary>Genera el asiento de cierre de cuentas de resultado contra "Resultado de la gestión".</summary>
        Public Function GenerarCierre(Optional fecha As Date? = Nothing) As Integer
            _ctx.Requiere("CONT.CIERRE")
            _ctx.RequiereGestionAbierta()
            Dim f As Date = If(fecha, _ctx.Gestion.FechaFin)
            If Db.ScalarInt("SELECT COUNT(*) FROM Comprobante WHERE Origen='CIE' AND Estado='V'") > 0 Then Throw New InvalidOperationException("Ya existe un asiento de cierre vigente. Anúlelo para generarlo nuevamente.")
            Dim led As New LedgerService(_ctx)
            Dim bal As List(Of BalanceRow) = led.Balance(_ctx.Gestion.FechaInicio, f, False, 99, True)
            Dim vs As New VoucherService(_ctx)
            Dim v As Voucher = vs.Nuevo("CI", f)
            v.Glosa = "Cierre de cuentas de resultado - gestión " & _ctx.Gestion.Anio
            v.Origen = "CIE"
            Dim ing As Decimal = 0D, egr As Decimal = 0D
            For Each b In bal.Where(Function(x) x.EsMovimiento AndAlso (x.Rubro = 4 OrElse x.Rubro = 5))
                Dim neto As Decimal = b.Neto
                If neto > 0D Then
                    v.Lines.Add(VoucherLine.Hab(b.CuentaId, neto, v.Glosa))
                ElseIf neto < 0D Then
                    v.Lines.Add(VoucherLine.Deb(b.CuentaId, -neto, v.Glosa))
                End If
                If b.Rubro = 4 Then ing += -neto Else egr += neto
            Next
            If v.Lines.Count = 0 Then Throw New InvalidOperationException("No hay saldos en cuentas de resultado para cerrar.")
            Dim res As Decimal = ing - egr
            Dim cta As Integer = _ctx.CuentaParam(ParamKeys.CtaResultadoGestion)
            If res > 0D Then
                v.Lines.Add(VoucherLine.Hab(cta, res, v.Glosa))
            ElseIf res < 0D Then
                v.Lines.Add(VoucherLine.Deb(cta, -res, v.Glosa))
            End If
            Dim id As Integer = vs.Registrar(v)
            _ctx.Audit("Gestión", "CIERRE_RESULTADOS", "Resultado Bs " & res.ToString("N2"))
            Return id
        End Function

        Public Sub CerrarGestion()
            _ctx.Requiere("CONT.CIERRE")
            _ctx.Sistema.CambiarEstadoGestion(_ctx.Gestion.Id, "C")
            _ctx.Gestion.Estado = "C"
            _ctx.Audit("Gestión", "GESTION_CERRADA", _ctx.Gestion.Anio.ToString())
        End Sub

        Public Sub ReabrirGestion()
            If Not _ctx.Usuario.EsAdmin Then Throw New UnauthorizedAccessException("Solo un administrador puede reabrir una gestión cerrada.")
            _ctx.Sistema.CambiarEstadoGestion(_ctx.Gestion.Id, "A")
            _ctx.Gestion.Estado = "A"
            _ctx.Audit("Gestión", "GESTION_REABIERTA", _ctx.Gestion.Anio.ToString())
        End Sub

        ' ---------- Apertura de nueva gestión ----------
        Private Shared ReadOnly RefCuenta As String() = {"CuentaInvId", "CuentaIngId", "CuentaCostoId", "CuentaActivoId", "CuentaDepAcumId", "CuentaGastoId", "CuentaCxcId", "CuentaCxpId", "CuentaAnticipoId", "PadreId"}

        Private Shared Function CopiarTabla(src As Database, dst As Database, tabla As String, refs As Dictionary(Of String, String), mapas As Dictionary(Of String, Dictionary(Of Integer, Integer)),
                                            Optional filtro As String = "", Optional orden As String = "Id", Optional ajuste As Action(Of DataRow, Dictionary(Of String, Object)) = Nothing) As Dictionary(Of Integer, Integer)
            Dim result As New Dictionary(Of Integer, Integer)
            mapas(tabla) = result
            Dim dt As DataTable = src.Query("SELECT * FROM " & tabla & If(filtro <> "", " WHERE " & filtro, "") & " ORDER BY " & orden)
            For Each r As DataRow In dt.Rows
                Dim vals As New Dictionary(Of String, Object)
                For Each c As DataColumn In dt.Columns
                    If c.ColumnName.Equals("Id", StringComparison.OrdinalIgnoreCase) Then Continue For
                    Dim v As Object = r(c)
                    If refs IsNot Nothing AndAlso refs.ContainsKey(c.ColumnName) AndAlso Not IsNil(v) Then
                        Dim m As Dictionary(Of Integer, Integer) = Nothing
                        Dim nuevo As Integer = 0
                        If mapas.TryGetValue(refs(c.ColumnName), m) AndAlso m.TryGetValue(ToInt(v), nuevo) Then v = nuevo Else v = DBNull.Value
                    End If
                    vals(c.ColumnName) = v
                Next
                If ajuste IsNot Nothing Then ajuste(r, vals)
                Dim cols As List(Of String) = vals.Keys.ToList()
                Dim sql As String = "INSERT INTO " & tabla & " (" & String.Join(", ", cols.Select(Function(x) dst.Provider.Quote(x))) & ") VALUES (" & String.Join(", ", cols.Select(Function(x) "@p_" & x)) & ")"
                Dim args As New List(Of Object)
                For Each c As String In cols
                    args.Add("p_" & c)
                    args.Add(vals(c))
                Next
                Dim nid As Integer = dst.Insert(sql, args.ToArray())
                result(r.GetI("Id")) = nid
            Next
            Return result
        End Function

        Private Shared Function Refs(ParamArray pares() As String) As Dictionary(Of String, String)
            Dim d As New Dictionary(Of String, String)
            For i As Integer = 0 To pares.Length - 1 Step 2
                d(pares(i)) = pares(i + 1)
            Next
            Return d
        End Function

        ''' <summary>Crea la siguiente gestión copiando catálogos y trasladando saldos (apertura contable, existencias, cuentas por cobrar/pagar y activos fijos).</summary>
        Public Function AbrirNuevaGestion(opc As NuevaGestionOpciones) As Integer
            _ctx.Requiere("ADM.GESTIONES")
            If opc.Anio <= _ctx.Gestion.Anio Then Throw New InvalidOperationException("La nueva gestión debe ser posterior a la actual (" & _ctx.Gestion.Anio & ").")
            Dim sis As SistemaService = _ctx.Sistema
            Dim fin As Date = _ctx.Gestion.FechaFin
            Dim led As New LedgerService(_ctx)
            ' 1) saldos de cierre (Bs y USD) antes de crear nada
            Dim balBs As List(Of BalanceRow) = led.Balance(_ctx.Gestion.FechaInicio, fin, False, 99, True)
            Dim balUsd As List(Of BalanceRow) = led.Balance(_ctx.Gestion.FechaInicio, fin, True, 99, True)
            Dim usdPorCuenta As Dictionary(Of Integer, Decimal) = balUsd.ToDictionary(Function(b) b.CuentaId, Function(b) b.Neto)
            Dim resBs As Decimal = 0D, resUsd As Decimal = 0D
            For Each b In balBs.Where(Function(x) x.Nivel = 1 AndAlso (x.Rubro = 4 OrElse x.Rubro = 5))
                resBs += -b.Neto
            Next
            For Each b In balUsd.Where(Function(x) x.Nivel = 1 AndAlso (x.Rubro = 4 OrElse x.Rubro = 5))
                resUsd += -b.Neto
            Next
            Dim codResGestion As String = _ctx.Param.Valor(ParamKeys.CtaResultadoGestion)
            Dim codResAcum As String = _ctx.Param.Valor(ParamKeys.CtaResultadoAcum)
            If _ctx.CuentaPorCodigo(codResAcum) Is Nothing Then Throw New InvalidOperationException("Configure la cuenta de Resultados Acumulados en Parámetros.")
            Dim lineasApertura As New Dictionary(Of String, Tuple(Of Decimal, Decimal))
            For Each b In balBs.Where(Function(x) x.EsMovimiento AndAlso x.Rubro >= 1 AndAlso x.Rubro <= 3)
                Dim cod As String = b.Codigo
                If cod = codResGestion Then cod = codResAcum
                Dim u As Decimal = 0D
                usdPorCuenta.TryGetValue(b.CuentaId, u)
                Dim prev As Tuple(Of Decimal, Decimal) = Nothing
                If lineasApertura.TryGetValue(cod, prev) Then
                    lineasApertura(cod) = Tuple.Create(prev.Item1 + b.Neto, prev.Item2 + u)
                Else
                    lineasApertura(cod) = Tuple.Create(b.Neto, u)
                End If
            Next
            If resBs <> 0D OrElse resUsd <> 0D Then
                Dim prev As Tuple(Of Decimal, Decimal) = Nothing
                If lineasApertura.TryGetValue(codResAcum, prev) Then
                    lineasApertura(codResAcum) = Tuple.Create(prev.Item1 - resBs, prev.Item2 - resUsd)
                Else
                    lineasApertura(codResAcum) = Tuple.Create(-resBs, -resUsd)
                End If
            End If
            ' 2) existencias, saldos de terceros y activos del cierre
            Dim stock As DataTable = Db.Query("SELECT ItemId, AlmacenId, FechaVenc, SUM(Signo * Cantidad) AS Q FROM MovInvDet WHERE Vigente=1 AND Fecha <= @f GROUP BY ItemId, AlmacenId, FechaVenc", "f", fin)
            Dim items As DataTable = Db.Query("SELECT Id, Codigo, CostoProm FROM Item")
            Dim ts As New TerceroService(_ctx)
            Dim terceros As DataTable = Db.Query("SELECT Id, Codigo FROM Tercero")
            Dim saldosTerceros As New List(Of Tuple(Of String, String, Decimal))
            For Each t As DataRow In terceros.Rows
                For Each clase As String In {"CXC", "CXP"}
                    Dim s As Decimal = ts.Saldo(t.GetI("Id"), clase, fin)
                    If s <> 0D Then saldosTerceros.Add(Tuple.Create(t.GetS("Codigo"), clase, s))
                Next
            Next
            Dim ufvFin As Decimal = New TipoCambioService(_ctx).Ufv(fin)
            Dim tcFin As Decimal = New TipoCambioService(_ctx).Dolar(fin)

            ' 3) crear la gestión nueva y copiar catálogos
            Dim empSvc As New EmpresaService(sis)
            opc.Plantilla = PlantillaPlan.Vacio
            Dim nuevaId As Integer = empSvc.CrearGestion(_ctx.Empresa, opc)
            Dim nueva As GestionInfo = sis.ObtenerGestion(nuevaId)
            Using dst As New Database(sis.Provider, sis.RutaAbsoluta(nueva))
                dst.InTx(Sub()
                             Dim mapas As New Dictionary(Of String, Dictionary(Of Integer, Integer))
                             dst.Execute("DELETE FROM UnidadMedida")
                             dst.Execute("DELETE FROM Almacen")
                             dst.Execute("DELETE FROM Sucursal")
                             Dim pnew As New Parametros(dst)
                             For Each kv In _ctx.Param.Todos()
                                 If kv.Key = ParamKeys.EmpGestion OrElse kv.Key = "CORRELATIVO_MENSUAL" OrElse kv.Key = "MES_INICIO" Then Continue For
                                 pnew.Guardar(kv.Key, kv.Value)
                             Next
                             For Each t As DataRow In Db.Query("SELECT Codigo, Nombre FROM TipoComprobante").Rows
                                 If dst.ScalarInt("SELECT COUNT(*) FROM TipoComprobante WHERE Codigo=@c", "c", t.GetS("Codigo")) = 0 Then
                                     dst.Execute("INSERT INTO TipoComprobante (Codigo, Nombre, Sistema, Activo) VALUES (@c, @n, 0, 1)", "c", t.GetS("Codigo"), "n", t.GetS("Nombre"))
                                 End If
                             Next
                             CopiarTabla(Db, dst, "UnidadMedida", Nothing, mapas)
                             CopiarTabla(Db, dst, "Almacen", Nothing, mapas)
                             CopiarTabla(Db, dst, "Sucursal", Nothing, mapas)
                             CopiarTabla(Db, dst, "GrupoItem", Nothing, mapas)
                             CopiarTabla(Db, dst, "Vendedor", Nothing, mapas)
                             CopiarTabla(Db, dst, "CentroCosto", Nothing, mapas)
                             CopiarTabla(Db, dst, "Cuenta", Refs("PadreId", "Cuenta"), mapas, "", "Codigo")
                             Dim rc As Dictionary(Of String, String) = Refs("CuentaCxcId", "Cuenta", "CuentaCxpId", "Cuenta", "CuentaAnticipoId", "Cuenta")
                             CopiarTabla(Db, dst, "Tercero", rc, mapas)
                             CopiarTabla(Db, dst, "Item", Refs("GrupoId", "GrupoItem", "UnidadId", "UnidadMedida", "CuentaInvId", "Cuenta", "CuentaIngId", "Cuenta", "CuentaCostoId", "Cuenta"), mapas, "", "Id",
                                         Sub(r, vals)
                                             vals("Stock") = 0D
                                             vals("CostoProm") = 0D
                                             vals("UltimoCosto") = 0D
                                         End Sub)
                             CopiarTabla(Db, dst, "GrupoActivo", Refs("CuentaActivoId", "Cuenta", "CuentaDepAcumId", "Cuenta", "CuentaGastoId", "Cuenta"), mapas)
                             CopiarTabla(Db, dst, "Empleado", Refs("CentroCostoId", "CentroCosto"), mapas, "Estado='A'")
                             ' Activos fijos con valores actualizados al cierre
                             CopiarTabla(Db, dst, "ActivoFijo", Refs("GrupoId", "GrupoActivo", "CuentaActivoId", "Cuenta", "CuentaDepAcumId", "Cuenta", "CuentaGastoId", "Cuenta", "TerceroId", "Tercero", "CentroCostoId", "CentroCosto"), mapas, "Estado='A'", "Id",
                                         Sub(r, vals)
                                             Dim u As DataTable = Db.Query("SELECT * FROM DepreciacionAF WHERE ActivoId=@a ORDER BY Periodo DESC", "a", r.GetI("Id"))
                                             If u.Rows.Count > 0 Then
                                                 vals("ValorOriginal") = u.Rows(0).GetD("ValorAct")
                                                 vals("DepAcumInicial") = u.Rows(0).GetD("DepAcum")
                                                 If ToDec(u.Rows(0)("UfvFin")) > 0D Then vals("UfvAlta") = CDbl(ToDec(u.Rows(0)("UfvFin")))
                                             End If
                                         End Sub)
                             ' tipo de cambio y UFV de arranque
                             dst.Execute("DELETE FROM TipoCambio")
                             dst.Execute("INSERT INTO TipoCambio (Fecha, Usd, Ufv) VALUES (@f, @u, @v)", "f", nueva.FechaInicio, "u", CDbl(tcFin), "v", CDbl(ufvFin))
                         End Sub)
            End Using
            ' 4) asiento de apertura, existencias y subauxiliares en la gestión nueva
            Using nc As Contexto = sis.AbrirContexto(_ctx.Usuario, _ctx.Empresa.Id, nuevaId)
                nc.Db.InTx(Sub()
                               Dim vs As New VoucherService(nc)
                               Dim v As Voucher = vs.Nuevo("AP", nueva.FechaInicio)
                               v.Glosa = "Asiento de apertura de la gestión " & nueva.Anio & " (saldos al " & fin.ToString("dd/MM/yyyy") & ")"
                               v.Origen = "APE"
                               v.TC = tcFin
                               For Each kv In lineasApertura.OrderBy(Function(x) x.Key, StringComparer.Ordinal)
                                   Dim c As DataRow = nc.CuentaPorCodigo(kv.Key)
                                   If c Is Nothing Then Continue For
                                   Dim bs As Decimal = kv.Value.Item1.R2(), us As Decimal = kv.Value.Item2.R2()
                                   If bs = 0D Then Continue For
                                   Dim l As New VoucherLine With {.CuentaId = c.GetI("Id"), .Glosa = v.Glosa}
                                   If bs > 0D Then
                                       l.Debe = bs
                                       If us > 0D Then
                                           l.DebeUsdFijo = us
                                           l.HaberUsdFijo = 0D
                                       End If
                                   Else
                                       l.Haber = -bs
                                       If us < 0D Then
                                           l.HaberUsdFijo = -us
                                           l.DebeUsdFijo = 0D
                                       End If
                                   End If
                                   v.Lines.Add(l)
                               Next
                               If v.Lines.Count >= 2 Then vs.Registrar(v)
                               ' existencias iniciales (sin asiento: ya está en la apertura)
                               Dim inv As New InventarioService(nc)
                               Dim porAlmacen As New Dictionary(Of Integer, MovInvDto)
                               Dim mapaItems As New Dictionary(Of Integer, Integer)
                               For Each it As DataRow In items.Rows
                                   Dim n As DataRow = nc.Db.Query("SELECT Id FROM Item WHERE Codigo=@c", "c", it.GetS("Codigo")).Rows.Cast(Of DataRow)().FirstOrDefault()
                                   If n IsNot Nothing Then mapaItems(it.GetI("Id")) = n.GetI("Id")
                               Next
                               Dim mapaAlm As New Dictionary(Of Integer, Integer)
                               For Each a As DataRow In Db.Query("SELECT Id, Codigo FROM Almacen").Rows
                                   Dim n As DataRow = nc.Db.Query("SELECT Id FROM Almacen WHERE Codigo=@c", "c", a.GetS("Codigo")).Rows.Cast(Of DataRow)().FirstOrDefault()
                                   If n IsNot Nothing Then mapaAlm(a.GetI("Id")) = n.GetI("Id")
                               Next
                               Dim costos As Dictionary(Of Integer, Decimal) = items.Rows.Cast(Of DataRow)().ToDictionary(Function(r) r.GetI("Id"), Function(r) r.GetD("CostoProm"))
                               For Each r As DataRow In stock.Rows
                                   Dim q As Decimal = Math.Round(r.GetD("Q"), 6)
                                   If q <= 0D OrElse Not mapaItems.ContainsKey(r.GetI("ItemId")) OrElse Not mapaAlm.ContainsKey(r.GetI("AlmacenId")) Then Continue For
                                   Dim alm As Integer = mapaAlm(r.GetI("AlmacenId"))
                                   If Not porAlmacen.ContainsKey(alm) Then
                                       porAlmacen(alm) = New MovInvDto With {.Tipo = "STIN", .Fecha = nueva.FechaInicio, .AlmacenId = alm, .TC = 1D, .Detalle = "Existencias iniciales gestión " & nueva.Anio}
                                   End If
                                   porAlmacen(alm).Lines.Add(New MovLine With {.ItemId = mapaItems(r.GetI("ItemId")), .Cantidad = q, .PrecioUnit = costos(r.GetI("ItemId")), .FechaVenc = ToDateOrNull(r("FechaVenc"))})
                               Next
                               For Each m In porAlmacen.Values
                                   inv.Aplicar(m)
                               Next
                               ' cuentas por cobrar / pagar
                               Dim tsn As New TerceroService(nc)
                               For Each s In saldosTerceros
                                   Dim n As DataRow = nc.Db.Query("SELECT Id FROM Tercero WHERE Codigo=@c", "c", s.Item1).Rows.Cast(Of DataRow)().FirstOrDefault()
                                   If n IsNot Nothing Then tsn.SaldoInicialInterno(n.GetI("Id"), s.Item2, nueva.FechaInicio, s.Item3, 0, False, "Saldo inicial gestión anterior")
                               Next
                           End Sub)
                nc.Audit("Gestión", "GESTION_NUEVA", "Apertura " & nueva.Anio & " desde " & _ctx.Gestion.Anio)
            End Using
            _ctx.Audit("Gestión", "APERTURA_NUEVA_GESTION", nueva.Anio.ToString())
            Return nuevaId
        End Function

        ' ---------- Ajustes ----------
        Private Function UfvDe(tc As TipoCambioService, cache As Dictionary(Of Date, Decimal), fecha As Date, faltantes As HashSet(Of Date)) As Decimal
            Dim v As Decimal = 0D
            If cache.TryGetValue(fecha, v) Then Return v
            v = tc.Ufv(fecha)
            cache(fecha) = v
            If v <= 0D Then faltantes.Add(fecha)
            Return v
        End Function

        ''' <summary>Ajuste por inflación y tenencia de bienes con UFV sobre cuentas ajustables del balance. Con registrar=False solo calcula.</summary>
        Public Function AjusteInflacion(fecha As Date, registrar As Boolean) As AjusteResultado
            If registrar Then
                _ctx.Requiere("CONT.AJUSTES")
                _ctx.RequiereGestionAbierta()
                If Db.ScalarInt("SELECT COUNT(*) FROM Comprobante WHERE Origen='INFL' AND Estado='V'") > 0 Then Throw New InvalidOperationException("Ya existe un ajuste por inflación vigente en esta gestión. Anúlelo para volver a generarlo.")
            End If
            Dim tc As New TipoCambioService(_ctx)
            Dim ufvFin As Decimal = tc.Ufv(fecha)
            If ufvFin <= 0D Then Throw New InvalidOperationException("Cargue la UFV del " & fecha.ToString("dd/MM/yyyy") & " en Contabilidad > Tipos de cambio y UFV.")
            Dim res As New AjusteResultado()
            Dim cache As New Dictionary(Of Date, Decimal)
            Dim faltantes As New HashSet(Of Date)
            Dim dt As DataTable = Db.Query("SELECT d.CuentaId, d.Fecha, d.DebeBs, d.HaberBs, t.Codigo AS Tipo FROM (ComprobanteDet d INNER JOIN Comprobante c ON c.Id = d.ComprobanteId) INNER JOIN TipoComprobante t ON t.Id = c.TipoId WHERE d.Vigente=1 AND c.Origen <> 'INFL' AND d.Fecha <= @f", "f", fecha.Date)
            Dim saldo As New Dictionary(Of Integer, Decimal)
            Dim ajuste As New Dictionary(Of Integer, Decimal)
            For Each r As DataRow In dt.Rows
                Dim c As DataRow = _ctx.CuentaPorId(r.GetI("CuentaId"))
                If c Is Nothing OrElse Not c.GetF("Ajustable") OrElse c.GetI("Rubro") > 3 Then Continue For
                Dim net As Decimal = r.GetD("DebeBs") - r.GetD("HaberBs")
                If net = 0D Then Continue For
                Dim fm As Date = r.GetDt("Fecha")
                If r.GetS("Tipo") = "AP" Then fm = fm.AddDays(-1)
                Dim u As Decimal = UfvDe(tc, cache, fm, faltantes)
                If u <= 0D Then Continue For
                Dim id As Integer = r.GetI("CuentaId")
                saldo(id) = (If(saldo.ContainsKey(id), saldo(id), 0D)) + net
                ajuste(id) = (If(ajuste.ContainsKey(id), ajuste(id), 0D)) + net * (ufvFin / u - 1D)
            Next
            If faltantes.Count > 0 Then
                Throw New InvalidOperationException("Faltan valores de UFV para las fechas: " & String.Join(", ", faltantes.OrderBy(Function(x) x).Take(8).Select(Function(x) x.ToString("dd/MM/yyyy"))) & If(faltantes.Count > 8, " ...", "") & ". Cárguelos en Tipos de cambio y UFV.")
            End If
            For Each kv In ajuste.OrderBy(Function(x) _ctx.CodigoCuenta(x.Key), StringComparer.Ordinal)
                Dim a As Decimal = kv.Value.R2()
                If a = 0D Then Continue For
                res.Filas.Add(New AjusteFila With {.CuentaId = kv.Key, .Codigo = _ctx.CodigoCuenta(kv.Key), .Nombre = _ctx.NombreCuenta(kv.Key), .SaldoBs = saldo(kv.Key), .Actualizado = saldo(kv.Key) + a, .Ajuste = a})
            Next
            res.Total = res.Filas.Sum(Function(x) x.Ajuste)
            If Not registrar OrElse res.Filas.Count = 0 Then Return res
            Dim vs As New VoucherService(_ctx)
            Dim v As Voucher = vs.Nuevo("AJ", fecha)
            v.Glosa = "Ajuste por inflación y tenencia de bienes con UFV al " & fecha.ToString("dd/MM/yyyy")
            v.Origen = "INFL"
            For Each f In res.Filas
                Dim l As New VoucherLine With {.CuentaId = f.CuentaId, .Glosa = v.Glosa, .DebeUsdFijo = 0D, .HaberUsdFijo = 0D}
                If f.Ajuste > 0D Then l.Debe = f.Ajuste Else l.Haber = -f.Ajuste
                v.Lines.Add(l)
            Next
            If res.Total <> 0D Then
                Dim cp As New VoucherLine With {.Glosa = v.Glosa, .DebeUsdFijo = 0D, .HaberUsdFijo = 0D}
                If res.Total > 0D Then
                    cp.CuentaId = _ctx.CuentaParam(ParamKeys.CtaAjusteInflIng)
                    cp.Haber = res.Total
                Else
                    cp.CuentaId = _ctx.CuentaParam(ParamKeys.CtaAjusteInflEgr)
                    cp.Debe = -res.Total
                End If
                v.Lines.Add(cp)
            End If
            res.ComprobanteId = vs.Registrar(v)
            _ctx.Audit("Ajustes", "AJUSTE_INFLACION", fecha.ToString("dd/MM/yyyy") & " Bs " & res.Total.ToString("N2"))
            Return res
        End Function

        ''' <summary>Actualiza al tipo de cambio final las cuentas en moneda extranjera (activos y pasivos).</summary>
        Public Function DiferenciaCambio(fecha As Date, tcFinal As Decimal, registrar As Boolean) As AjusteResultado
            If registrar Then
                _ctx.Requiere("CONT.AJUSTES")
                _ctx.RequiereGestionAbierta()
            End If
            If tcFinal <= 0D Then Throw New ArgumentException("Ingrese el tipo de cambio final.")
            Dim led As New LedgerService(_ctx)
            Dim bs As List(Of BalanceRow) = led.Balance(_ctx.Gestion.FechaInicio, fecha, False, 99, True)
            Dim us As Dictionary(Of Integer, Decimal) = led.Balance(_ctx.Gestion.FechaInicio, fecha, True, 99, True).ToDictionary(Function(b) b.CuentaId, Function(b) b.Neto)
            Dim res As New AjusteResultado()
            For Each b In bs.Where(Function(x) x.EsMovimiento AndAlso x.Rubro <= 2)
                Dim c As DataRow = _ctx.CuentaPorId(b.CuentaId)
                If c.GetS("Moneda") <> "USD" Then Continue For
                Dim u As Decimal = 0D
                us.TryGetValue(b.CuentaId, u)
                Dim objetivo As Decimal = (u * tcFinal).R2()
                Dim adj As Decimal = objetivo - b.Neto
                If adj = 0D Then Continue For
                res.Filas.Add(New AjusteFila With {.CuentaId = b.CuentaId, .Codigo = b.Codigo, .Nombre = b.Nombre, .SaldoBs = b.Neto, .SaldoUsd = u, .Actualizado = objetivo, .Ajuste = adj})
            Next
            res.Total = res.Filas.Sum(Function(x) x.Ajuste)
            If Not registrar OrElse res.Filas.Count = 0 Then Return res
            Dim vs As New VoucherService(_ctx)
            Dim v As Voucher = vs.Nuevo("AJ", fecha)
            v.TC = tcFinal
            v.Glosa = "Diferencia de cambio al T.C. " & tcFinal.ToString("0.00", Inv) & " (" & fecha.ToString("dd/MM/yyyy") & ")"
            v.Origen = "DIFC"
            For Each f In res.Filas
                Dim l As New VoucherLine With {.CuentaId = f.CuentaId, .Glosa = v.Glosa, .DebeUsdFijo = 0D, .HaberUsdFijo = 0D}
                If f.Ajuste > 0D Then l.Debe = f.Ajuste Else l.Haber = -f.Ajuste
                v.Lines.Add(l)
            Next
            Dim cp As New VoucherLine With {.Glosa = v.Glosa, .DebeUsdFijo = 0D, .HaberUsdFijo = 0D}
            If res.Total >= 0D Then
                cp.CuentaId = _ctx.CuentaParam(ParamKeys.CtaDifCambioIng)
                cp.Haber = res.Total
            Else
                cp.CuentaId = _ctx.CuentaParam(ParamKeys.CtaDifCambioEgr)
                cp.Debe = -res.Total
            End If
            v.Lines.Add(cp)
            res.ComprobanteId = vs.Registrar(v)
            _ctx.Audit("Ajustes", "DIFERENCIA_CAMBIO", fecha.ToString("dd/MM/yyyy") & " TC " & tcFinal)
            Return res
        End Function

    End Class

End Namespace
