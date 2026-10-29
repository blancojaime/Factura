Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class TerceroDto
        Public Property Id As Integer
        Public Property Codigo As String = ""
        Public Property Nombre As String = ""
        Public Property Nit As String = ""
        Public Property Direccion As String = ""
        Public Property Ciudad As String = ""
        Public Property Telefono As String = ""
        Public Property Email As String = ""
        Public Property Actividad As String = ""
        Public Property Contacto As String = ""
        Public Property EsCliente As Boolean = True
        Public Property EsProveedor As Boolean
        Public Property LimiteCredito As Decimal
        Public Property DiasCredito As Integer
        Public Property NivelPrecio As String = "A"
        Public Property CuentaCxcId As Integer
        Public Property CuentaCxpId As Integer
        Public Property CuentaAnticipoId As Integer
        Public Property Activo As Boolean = True
    End Class

    Public Class KardexTerceroRow
        Public Property Fecha As Date
        Public Property Tipo As String
        Public Property Referencia As String
        Public Property Detalle As String
        Public Property Debe As Decimal
        Public Property Haber As Decimal
        Public Property Saldo As Decimal
    End Class

    ''' <summary>Clientes y proveedores, con su cuenta corriente (cuentas por cobrar / por pagar).</summary>
    Public Class TerceroService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Public Function Listar(Optional clase As String = "", Optional texto As String = "", Optional soloActivos As Boolean = False) As DataTable
            Dim sql As String = "SELECT * FROM Tercero WHERE 1=1"
            If clase = "CXC" Then sql &= " AND EsCliente=1"
            If clase = "CXP" Then sql &= " AND EsProveedor=1"
            If soloActivos Then sql &= " AND Activo=1"
            Dim dt As DataTable = _ctx.Db.Query(sql & " ORDER BY Nombre")
            If texto <> "" Then
                Dim t As String = texto.ToLowerInvariant()
                For i As Integer = dt.Rows.Count - 1 To 0 Step -1
                    Dim r As DataRow = dt.Rows(i)
                    If Not (r.GetS("Nombre").ToLowerInvariant().Contains(t) OrElse r.GetS("Codigo").ToLowerInvariant().Contains(t) OrElse r.GetS("Nit").ToLowerInvariant().Contains(t)) Then dt.Rows.RemoveAt(i)
                Next
            End If
            Return dt
        End Function

        Public Function Obtener(id As Integer) As TerceroDto
            Dim dt As DataTable = _ctx.Db.Query("SELECT * FROM Tercero WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Dim r As DataRow = dt.Rows(0)
            Return New TerceroDto With {
                .Id = id, .Codigo = r.GetS("Codigo"), .Nombre = r.GetS("Nombre"), .Nit = r.GetS("Nit"), .Direccion = r.GetS("Direccion"),
                .Ciudad = r.GetS("Ciudad"), .Telefono = r.GetS("Telefono"), .Email = r.GetS("Email"), .Actividad = r.GetS("Actividad"),
                .Contacto = r.GetS("Contacto"), .EsCliente = r.GetF("EsCliente"), .EsProveedor = r.GetF("EsProveedor"),
                .LimiteCredito = r.GetD("LimiteCredito"), .DiasCredito = r.GetI("DiasCredito"), .NivelPrecio = If(r.GetS("NivelPrecio") = "", "A", r.GetS("NivelPrecio")),
                .CuentaCxcId = r.GetI("CuentaCxcId"), .CuentaCxpId = r.GetI("CuentaCxpId"), .CuentaAnticipoId = r.GetI("CuentaAnticipoId"), .Activo = r.GetF("Activo")}
        End Function

        Public Function SiguienteCodigo(esProveedor As Boolean) As String
            Dim n As Integer = _ctx.Siguiente(If(esProveedor, "TERC_PRO", "TERC_CLI"))
            Return If(esProveedor, "P", "C") & n.ToString("00000")
        End Function

        Public Function Guardar(t As TerceroDto) As Integer
            _ctx.Requiere("COM.TERCEROS")
            _ctx.RequiereGestionAbierta()
            t.Nombre = If(t.Nombre, "").Trim()
            If t.Nombre = "" Then Throw New ArgumentException("El nombre o razón social es obligatorio.")
            If Not t.EsCliente AndAlso Not t.EsProveedor Then Throw New ArgumentException("Seleccione si es cliente, proveedor o ambos.")
            If t.LimiteCredito < 0D Then Throw New ArgumentException("El límite de crédito no puede ser negativo.")
            If String.IsNullOrWhiteSpace(t.Codigo) Then t.Codigo = SiguienteCodigo(t.EsProveedor AndAlso Not t.EsCliente)
            t.Codigo = t.Codigo.Trim().ToUpperInvariant()
            Dim dup As Object = _ctx.Db.Scalar("SELECT Id FROM Tercero WHERE Codigo=@c", "c", t.Codigo)
            If dup IsNot Nothing AndAlso ToInt(dup) <> t.Id Then Throw New InvalidOperationException("El código " & t.Codigo & " ya existe.")
            If t.Id = 0 Then
                t.Id = _ctx.Db.Insert("INSERT INTO Tercero (Codigo, Nombre, Nit, Direccion, Ciudad, Telefono, Email, Actividad, Contacto, EsCliente, EsProveedor, LimiteCredito, DiasCredito, NivelPrecio, CuentaCxcId, CuentaCxpId, CuentaAnticipoId, Activo, Creado) VALUES (@c, @n, @nit, @d, @ci, @t, @e, @a, @co, @ecl, @epr, @l, @dc, @np, @cxc, @cxp, @ant, @ac, @cr)",
                    "c", t.Codigo, "n", t.Nombre, "nit", t.Nit, "d", t.Direccion, "ci", t.Ciudad, "t", t.Telefono, "e", t.Email, "a", t.Actividad, "co", t.Contacto,
                    "ecl", If(t.EsCliente, 1, 0), "epr", If(t.EsProveedor, 1, 0), "l", t.LimiteCredito, "dc", t.DiasCredito, "np", t.NivelPrecio,
                    "cxc", OrNull(t.CuentaCxcId), "cxp", OrNull(t.CuentaCxpId), "ant", OrNull(t.CuentaAnticipoId), "ac", If(t.Activo, 1, 0), "cr", Date.Now)
                _ctx.Audit("Terceros", "TERCERO_NUEVO", t.Codigo & " " & t.Nombre)
            Else
                _ctx.Db.Execute("UPDATE Tercero SET Codigo=@c, Nombre=@n, Nit=@nit, Direccion=@d, Ciudad=@ci, Telefono=@t, Email=@e, Actividad=@a, Contacto=@co, EsCliente=@ecl, EsProveedor=@epr, LimiteCredito=@l, DiasCredito=@dc, NivelPrecio=@np, CuentaCxcId=@cxc, CuentaCxpId=@cxp, CuentaAnticipoId=@ant, Activo=@ac WHERE Id=@i",
                    "c", t.Codigo, "n", t.Nombre, "nit", t.Nit, "d", t.Direccion, "ci", t.Ciudad, "t", t.Telefono, "e", t.Email, "a", t.Actividad, "co", t.Contacto,
                    "ecl", If(t.EsCliente, 1, 0), "epr", If(t.EsProveedor, 1, 0), "l", t.LimiteCredito, "dc", t.DiasCredito, "np", t.NivelPrecio,
                    "cxc", OrNull(t.CuentaCxcId), "cxp", OrNull(t.CuentaCxpId), "ant", OrNull(t.CuentaAnticipoId), "ac", If(t.Activo, 1, 0), "i", t.Id)
                _ctx.Audit("Terceros", "TERCERO_MOD", t.Codigo & " " & t.Nombre)
            End If
            Return t.Id
        End Function

        Public Sub Eliminar(id As Integer)
            _ctx.Requiere("COM.TERCEROS")
            Dim usos As Integer = _ctx.Db.ScalarInt("SELECT COUNT(*) FROM MovTercero WHERE TerceroId=@i", "i", id) +
                                  _ctx.Db.ScalarInt("SELECT COUNT(*) FROM Venta WHERE ClienteId=@i", "i", id) +
                                  _ctx.Db.ScalarInt("SELECT COUNT(*) FROM Compra WHERE ProveedorId=@i", "i", id)
            If usos > 0 Then Throw New InvalidOperationException("El registro tiene movimientos y no puede eliminarse. Márquelo como inactivo.")
            _ctx.Db.Execute("DELETE FROM Tercero WHERE Id=@i", "i", id)
            _ctx.Audit("Terceros", "TERCERO_ELIM", id.ToString())
        End Sub

        ''' <summary>Saldo de la cuenta corriente. CXC: positivo = el cliente nos debe. CXP: positivo = debemos al proveedor.</summary>
        Public Function Saldo(terceroId As Integer, clase As String, Optional hasta As Date? = Nothing) As Decimal
            Dim h As Date = If(hasta, Date.MaxValue.Date.AddYears(-1))
            Dim dt As DataTable = _ctx.Db.Query("SELECT SUM(Debe) AS D, SUM(Haber) AS H FROM MovTercero WHERE TerceroId=@t AND Clase=@c AND Vigente=1 AND Fecha <= @h", "t", terceroId, "c", clase, "h", h)
            Dim d As Decimal = dt.Rows(0).GetD("D"), hh As Decimal = dt.Rows(0).GetD("H")
            Return If(clase = "CXC", d - hh, hh - d)
        End Function

        Public Function Kardex(terceroId As Integer, clase As String, desde As Date, hasta As Date) As List(Of KardexTerceroRow)
            Dim signo As Decimal = If(clase = "CXC", 1D, -1D)
            Dim res As New List(Of KardexTerceroRow)
            Dim ant As DataTable = _ctx.Db.Query("SELECT SUM(Debe) AS D, SUM(Haber) AS H FROM MovTercero WHERE TerceroId=@t AND Clase=@c AND Vigente=1 AND Fecha < @d", "t", terceroId, "c", clase, "d", desde.Date)
            Dim saldo As Decimal = (ant.Rows(0).GetD("D") - ant.Rows(0).GetD("H")) * signo
            res.Add(New KardexTerceroRow With {.Fecha = desde.Date, .Tipo = "", .Detalle = "SALDO ANTERIOR", .Saldo = saldo})
            Dim dt As DataTable = _ctx.Db.Query("SELECT * FROM MovTercero WHERE TerceroId=@t AND Clase=@c AND Vigente=1 AND Fecha >= @d AND Fecha <= @h ORDER BY Fecha, Id", "t", terceroId, "c", clase, "d", desde.Date, "h", hasta.Date)
            For Each r As DataRow In dt.Rows
                saldo += (r.GetD("Debe") - r.GetD("Haber")) * signo
                res.Add(New KardexTerceroRow With {.Fecha = r.GetDt("Fecha"), .Tipo = r.GetS("Tipo"), .Referencia = r.GetS("Referencia"), .Detalle = r.GetS("Detalle"),
                    .Debe = r.GetD("Debe"), .Haber = r.GetD("Haber"), .Saldo = saldo})
            Next
            Return res
        End Function

        ''' <summary>Documentos de venta/compra a crédito con saldo pendiente.</summary>
        Public Function Pendientes(terceroId As Integer, clase As String) As DataTable
            If clase = "CXC" Then
                Return _ctx.Db.Query("SELECT Id, Tipo, Numero, Fecha, Vencimiento, TotalBs, SaldoBs, Detalle, NroFactura FROM Venta WHERE ClienteId=@t AND Estado='V' AND SaldoBs > 0 ORDER BY Fecha, Id", "t", terceroId)
            End If
            Return _ctx.Db.Query("SELECT Id, Tipo, Numero, Fecha, Vencimiento, TotalBs, SaldoBs, Detalle, NroFactura FROM Compra WHERE ProveedorId=@t AND Estado='V' AND SaldoBs > 0 ORDER BY Fecha, Id", "t", terceroId)
        End Function

        ''' <summary>Resumen de todos los terceros con saldo distinto de cero (cuentas por cobrar / por pagar).</summary>
        Public Function SaldosPorTercero(clase As String, hasta As Date) As DataTable
            Dim dt As DataTable = _ctx.Db.Query("SELECT m.TerceroId, SUM(m.Debe) AS D, SUM(m.Haber) AS H FROM MovTercero m WHERE m.Clase=@c AND m.Vigente=1 AND m.Fecha <= @h GROUP BY m.TerceroId", "c", clase, "h", hasta.Date)
            Dim res As New DataTable()
            res.Columns.Add("Codigo", GetType(String))
            res.Columns.Add("Nombre", GetType(String))
            res.Columns.Add("Nit", GetType(String))
            res.Columns.Add("Debe", GetType(Decimal))
            res.Columns.Add("Haber", GetType(Decimal))
            res.Columns.Add("Saldo", GetType(Decimal))
            For Each r As DataRow In dt.Rows
                Dim t As TerceroDto = Obtener(r.GetI("TerceroId"))
                If t Is Nothing Then Continue For
                Dim s As Decimal = If(clase = "CXC", r.GetD("D") - r.GetD("H"), r.GetD("H") - r.GetD("D"))
                If s = 0D Then Continue For
                res.Rows.Add(t.Codigo, t.Nombre, t.Nit, r.GetD("D"), r.GetD("H"), s)
            Next
            Dim v As DataView = res.DefaultView
            v.Sort = "Nombre"
            Return v.ToTable()
        End Function

        ''' <summary>Registra el saldo inicial (deuda o anticipo) de un cliente o proveedor y opcionalmente su asiento contable.</summary>
        Public Function SaldoInicial(terceroId As Integer, clase As String, fecha As Date, monto As Decimal, contracuentaId As Integer, generarAsiento As Boolean, Optional detalle As String = "Saldo inicial") As Integer
            _ctx.Requiere("COM.TERCEROS")
            Return SaldoInicialInterno(terceroId, clase, fecha, monto, contracuentaId, generarAsiento, detalle)
        End Function

        Friend Function SaldoInicialInterno(terceroId As Integer, clase As String, fecha As Date, monto As Decimal, contracuentaId As Integer, generarAsiento As Boolean, detalle As String) As Integer
            _ctx.RequiereGestionAbierta()
            If monto = 0D Then Throw New ArgumentException("Ingrese el saldo.")
            Dim t As TerceroDto = Obtener(terceroId)
            If t Is Nothing Then Throw New InvalidOperationException("Tercero inexistente.")
            Return _ctx.Db.InTx(Function()
                                    Dim vid As Integer = 0
                                    Dim cuentaCorriente As Integer = If(clase = "CXC", If(t.CuentaCxcId <> 0, t.CuentaCxcId, _ctx.CuentaParam(ParamKeys.CtaCxc)), If(t.CuentaCxpId <> 0, t.CuentaCxpId, _ctx.CuentaParam(ParamKeys.CtaCxp)))
                                    Dim ctaAnticipo As Integer = If(clase = "CXC", _ctx.CuentaParam(ParamKeys.CtaAnticipoCli), _ctx.CuentaParam(ParamKeys.CtaAnticipoProv))
                                    Dim abs As Decimal = Math.Abs(monto)
                                    If generarAsiento Then
                                        If contracuentaId = 0 Then Throw New ArgumentException("Seleccione la contracuenta del asiento.")
                                        Dim vs As New VoucherService(_ctx)
                                        Dim v As Voucher = vs.Nuevo("T", fecha)
                                        v.Glosa = detalle & " - " & t.Nombre
                                        v.Origen = "SIN"
                                        If clase = "CXC" Then
                                            If monto > 0D Then
                                                v.Lines.Add(VoucherLine.Deb(cuentaCorriente, abs, v.Glosa))
                                                v.Lines.Add(VoucherLine.Hab(contracuentaId, abs, v.Glosa))
                                            Else
                                                v.Lines.Add(VoucherLine.Deb(contracuentaId, abs, v.Glosa))
                                                v.Lines.Add(VoucherLine.Hab(ctaAnticipo, abs, v.Glosa))
                                            End If
                                        Else
                                            If monto > 0D Then
                                                v.Lines.Add(VoucherLine.Deb(contracuentaId, abs, v.Glosa))
                                                v.Lines.Add(VoucherLine.Hab(cuentaCorriente, abs, v.Glosa))
                                            Else
                                                v.Lines.Add(VoucherLine.Deb(ctaAnticipo, abs, v.Glosa))
                                                v.Lines.Add(VoucherLine.Hab(contracuentaId, abs, v.Glosa))
                                            End If
                                        End If
                                        vid = vs.Registrar(v)
                                    End If
                                    ' Cuenta corriente: CXC positivo = debe del cliente; CXP positivo = haber (deuda nuestra)
                                    Dim debe As Decimal = 0D, haber As Decimal = 0D
                                    If clase = "CXC" Then
                                        If monto > 0D Then debe = abs Else haber = abs
                                    Else
                                        If monto > 0D Then haber = abs Else debe = abs
                                    End If
                                    Dim tcv As Decimal = New TipoCambioService(_ctx).Dolar(fecha)
                                    Dim id As Integer = _ctx.Db.Insert("INSERT INTO MovTercero (TerceroId, Clase, Fecha, Tipo, DocTipo, DocId, Referencia, Detalle, Debe, Haber, TC, ComprobanteId, Vigente) VALUES (@t, @c, @f, 'SIN', 'SALDOINI', 0, '', @d, @de, @ha, @tc, @co, 1)",
                                                                       "t", terceroId, "c", clase, "f", fecha.Date, "d", detalle, "de", debe, "ha", haber, "tc", CDbl(tcv), "co", vid)
                                    ' Una deuda inicial pasa a ser un documento pendiente de cobro/pago
                                    If monto > 0D Then
                                        If clase = "CXC" Then
                                            _ctx.Db.Execute("INSERT INTO Venta (Tipo, Numero, Fecha, ClienteId, AlmacenId, Moneda, TC, Detalle, SubtotalBs, DescuentoBs, RecargoBs, TotalBs, AnticipoBs, ACuentaBs, SaldoBs, CostoBs, ConFactura, Estado, MovInvId, ComprobanteId, ComprobanteCostoId, ComprobanteItId, UsuarioId, Creado) VALUES ('SIN', @n, @f, @t, @a, 'BS', @tc, @d, @m, 0, 0, @m, 0, 0, @m, 0, 0, 'V', 0, @co, 0, 0, @u, @cr)",
                                                               "n", _ctx.Siguiente("VENTA_SIN"), "f", fecha.Date, "t", terceroId, "a", AlmacenDefecto(), "tc", CDbl(tcv), "d", detalle, "m", abs, "co", vid, "u", _ctx.Usuario.Id, "cr", Date.Now)
                                        Else
                                            _ctx.Db.Execute("INSERT INTO Compra (Tipo, Numero, Fecha, ProveedorId, AlmacenId, Moneda, TC, Detalle, SubtotalBs, DescuentoBs, RecargoBs, TotalBs, AnticipoBs, ACuentaBs, SaldoBs, CreditoFiscalBs, ConFactura, Estado, MovInvId, ComprobanteId, UsuarioId, Creado) VALUES ('SIN', @n, @f, @t, @a, 'BS', @tc, @d, @m, 0, 0, @m, 0, 0, @m, 0, 0, 'V', 0, @co, @u, @cr)",
                                                               "n", _ctx.Siguiente("COMPRA_SIN"), "f", fecha.Date, "t", terceroId, "a", AlmacenDefecto(), "tc", CDbl(tcv), "d", detalle, "m", abs, "co", vid, "u", _ctx.Usuario.Id, "cr", Date.Now)
                                        End If
                                    End If
                                    _ctx.Audit("Terceros", "SALDO_INICIAL", t.Nombre & " " & monto.ToString("N2"))
                                    Return id
                                End Function)
        End Function

        Friend Function AlmacenDefecto() As Integer
            Return _ctx.Db.ScalarInt("SELECT MIN(Id) FROM Almacen WHERE Activo=1")
        End Function

    End Class

End Namespace
