Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    ''' <summary>Comprobantes contables: registro, modificación, anulación, correlativos (mensual o único) y utilitarios.</summary>
    Public Class VoucherService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Private ReadOnly Property Db As Database
            Get
                Return _ctx.Db
            End Get
        End Property

        Public Function Tipos() As DataTable
            Return Db.Query("SELECT * FROM TipoComprobante WHERE Activo=1 ORDER BY Id")
        End Function

        Public Function TipoId(codigo As String) As Integer
            Dim o As Object = Db.Scalar("SELECT Id FROM TipoComprobante WHERE Codigo=@c", "c", codigo)
            If o Is Nothing Then Throw New InvalidOperationException("Tipo de comprobante inexistente: " & codigo)
            Return ToInt(o)
        End Function

        Public Sub AgregarTipo(codigo As String, nombre As String)
            _ctx.Requiere("CONT.COMPROBANTES")
            codigo = If(codigo, "").Trim().ToUpperInvariant()
            If codigo = "" OrElse nombre Is Nothing OrElse nombre.Trim() = "" Then Throw New ArgumentException("Código y nombre son obligatorios.")
            If Db.ScalarInt("SELECT COUNT(*) FROM TipoComprobante WHERE Codigo=@c", "c", codigo) > 0 Then Throw New InvalidOperationException("Ya existe un tipo con ese código.")
            Db.Execute("INSERT INTO TipoComprobante (Codigo, Nombre, Sistema, Activo) VALUES (@c, @n, 0, 1)", "c", codigo, "n", nombre.Trim())
        End Sub

        Public Function SiguienteNumero(tipoCodigo As String, fecha As Date) As Integer
            Dim mes As Integer = If(_ctx.Gestion.CorrelativoMensual, fecha.Month, 0)
            Return Db.ScalarInt("SELECT MAX(Numero) FROM Comprobante WHERE TipoId=@t AND Mes=@m", "t", TipoId(tipoCodigo), "m", mes) + 1
        End Function

        Public Function Nuevo(tipoCodigo As String, fecha As Date) As Voucher
            Dim tc As New TipoCambioService(_ctx)
            Dim v As New Voucher With {.TipoCodigo = tipoCodigo, .Fecha = fecha.Date, .TC = tc.Dolar(fecha), .UsuarioId = _ctx.Usuario.Id}
            v.Mes = If(_ctx.Gestion.CorrelativoMensual, fecha.Month, 0)
            v.Numero = SiguienteNumero(tipoCodigo, fecha)
            Return v
        End Function

        ' ---------- Validación y cálculo ----------
        Private Sub CalcularMontos(v As Voucher)
            For Each l As VoucherLine In v.Lines
                Dim bs As Decimal, usd As Decimal
                TipoCambioService.Convertir(l.Debe, v.Moneda, v.TC, bs, usd)
                l.DebeBs = bs
                l.DebeUsd = usd
                TipoCambioService.Convertir(l.Haber, v.Moneda, v.TC, bs, usd)
                l.HaberBs = bs
                l.HaberUsd = usd
            Next
            AjustarRedondeo(v, False)
            AjustarRedondeo(v, True)
        End Sub

        ''' <summary>Absorbe diferencias de centavos por redondeo en la línea de mayor importe del lado que corresponde.</summary>
        Private Sub AjustarRedondeo(v As Voucher, usd As Boolean)
            Dim d As Decimal = v.Lines.Sum(Function(l) If(usd, l.DebeUsd, l.DebeBs))
            Dim h As Decimal = v.Lines.Sum(Function(l) If(usd, l.HaberUsd, l.HaberBs))
            Dim dif As Decimal = d - h
            If dif = 0D Then Return
            If Math.Abs(dif) > 0.05D Then
                If usd Then Return ' la diferencia en dólares no impide guardar si Bs cuadra (se informa en reportes)
                Throw New InvalidOperationException("El comprobante no cuadra: Debe " & d.ToString("N2") & " / Haber " & h.ToString("N2") & ".")
            End If
            ' dif > 0: sobra debe -> reducir la mayor línea del debe ; dif < 0: reducir la mayor del haber
            If dif > 0 Then
                Dim m = v.Lines.Where(Function(l) If(usd, l.DebeUsd, l.DebeBs) > 0).OrderByDescending(Function(l) If(usd, l.DebeUsd, l.DebeBs)).FirstOrDefault()
                If m IsNot Nothing Then
                    If usd Then m.DebeUsd -= dif Else m.DebeBs -= dif
                End If
            Else
                Dim m = v.Lines.Where(Function(l) If(usd, l.HaberUsd, l.HaberBs) > 0).OrderByDescending(Function(l) If(usd, l.HaberUsd, l.HaberBs)).FirstOrDefault()
                If m IsNot Nothing Then
                    If usd Then m.HaberUsd += dif Else m.HaberBs += dif
                End If
            End If
        End Sub

        Private Sub Validar(v As Voucher)
            If v.Lines.Count < 2 Then Throw New InvalidOperationException("El comprobante debe tener al menos dos líneas.")
            If v.TC <= 0D Then Throw New InvalidOperationException("El tipo de cambio debe ser mayor a cero.")
            If v.Moneda <> "BS" AndAlso v.Moneda <> "USD" Then Throw New InvalidOperationException("Moneda inválida.")
            If v.Fecha < _ctx.Gestion.FechaInicio.Date OrElse v.Fecha > _ctx.Gestion.FechaFin.Date Then
                Throw New InvalidOperationException("La fecha " & v.Fecha.ToString("dd/MM/yyyy") & " está fuera de la gestión (" & _ctx.Gestion.FechaInicio.ToString("dd/MM/yyyy") & " - " & _ctx.Gestion.FechaFin.ToString("dd/MM/yyyy") & ").")
            End If
            Dim n As Integer = 0
            For Each l As VoucherLine In v.Lines
                n += 1
                If l.Debe < 0D OrElse l.Haber < 0D Then Throw New InvalidOperationException("Línea " & n & ": los importes no pueden ser negativos.")
                If (l.Debe = 0D) = (l.Haber = 0D) Then Throw New InvalidOperationException("Línea " & n & ": debe tener importe en el Debe o en el Haber (no ambos ni ninguno).")
                Dim c As DataRow = _ctx.CuentaPorId(l.CuentaId)
                If c Is Nothing Then Throw New InvalidOperationException("Línea " & n & ": seleccione una cuenta.")
                If Not c.GetF("EsMovimiento") Then Throw New InvalidOperationException("Línea " & n & ": la cuenta " & c.GetS("Codigo") & " no es de movimiento.")
                If Not c.GetF("Activa") Then Throw New InvalidOperationException("Línea " & n & ": la cuenta " & c.GetS("Codigo") & " está inactiva.")
            Next
            If Not v.Cuadra Then Throw New InvalidOperationException("El comprobante no cuadra. Diferencia: " & v.Diferencia.ToString("N2"))
        End Sub

        Private Sub ControlarPresupuesto(v As Voucher)
            If Not _ctx.Param.Bool(ParamKeys.ControlPresupuesto) Then Return
            For Each g In v.Lines.Where(Function(l) l.DebeBs > 0).GroupBy(Function(l) l.CuentaId)
                Dim c As DataRow = _ctx.CuentaPorId(g.Key)
                If c Is Nothing OrElse Not c.GetF("Presupuestable") Then Continue For
                Dim presu As Decimal = Db.ScalarDec("SELECT SUM(MontoBs) FROM Presupuesto WHERE CuentaId=@c", "c", g.Key)
                Dim ejec As Decimal = Db.ScalarDec("SELECT SUM(DebeBs) - SUM(HaberBs) FROM ComprobanteDet WHERE CuentaId=@c AND Vigente=1" &
                                                   If(v.Id <> 0, " AND ComprobanteId <> " & v.Id, ""), "c", g.Key)
                Dim nuevo As Decimal = g.Sum(Function(l) l.DebeBs - l.HaberBs)
                If ejec + nuevo > presu Then
                    Throw New InvalidOperationException("No existe presupuesto suficiente para la cuenta " & c.GetS("Codigo") & " " & c.GetS("Nombre") &
                        ". Presupuesto: " & presu.ToString("N2") & ", ejecutado: " & ejec.ToString("N2") & ", este comprobante: " & nuevo.ToString("N2"))
                End If
            Next
        End Sub

        ' ---------- Guardar ----------
        ''' <summary>Guarda (inserta o modifica) un comprobante con sus líneas y facturas IVA. Devuelve el Id.</summary>
        Public Function Guardar(v As Voucher) As Integer
            _ctx.Requiere(If(v.Id = 0, "CONT.COMPROBANTES", "CONT.MODIFICAR"))
            Return Registrar(v)
        End Function

        ''' <summary>Uso interno de los módulos (ventas, planillas...): no exige permiso de captura manual.</summary>
        Friend Function Registrar(v As Voucher) As Integer
            _ctx.RequiereGestionAbierta()
            If v.Estado = "A" Then Throw New InvalidOperationException("No se puede modificar un comprobante anulado.")
            v.Fecha = v.Fecha.Date
            Validar(v)
            CalcularMontos(v)
            ControlarPresupuesto(v)
            Dim tipoId As Integer = Me.TipoId(v.TipoCodigo)
            Return Db.InTx(Function()
                               Dim mes As Integer = If(_ctx.Gestion.CorrelativoMensual, v.Fecha.Month, 0)
                               Dim id As Integer = v.Id
                               Dim totDeb As Decimal = v.Lines.Sum(Function(l) l.DebeBs)
                               Dim totHab As Decimal = v.Lines.Sum(Function(l) l.HaberBs)
                               Dim totDebU As Decimal = v.Lines.Sum(Function(l) l.DebeUsd)
                               Dim totHabU As Decimal = v.Lines.Sum(Function(l) l.HaberUsd)
                               If id = 0 Then
                                   Dim num As Integer = Db.ScalarInt("SELECT MAX(Numero) FROM Comprobante WHERE TipoId=@t AND Mes=@m", "t", tipoId, "m", mes) + 1
                                   id = Db.Insert(
                                       "INSERT INTO Comprobante (TipoId, Numero, Mes, Fecha, TC, Moneda, Glosa, Referencia, Cheque, Banco, Estado, Origen, OrigenId, UsuarioId, Creado, Modificado, DebeBs, HaberBs, DebeUsd, HaberUsd, Observacion) " &
                                       "VALUES (@t, @n, @m, @f, @tc, @mo, @g, @r, @ch, @b, 'V', @o, @oi, @u, @cr, @cr, @d, @h, @du, @hu, @ob)",
                                       "t", tipoId, "n", num, "m", mes, "f", v.Fecha, "tc", CDbl(v.TC), "mo", v.Moneda, "g", v.Glosa, "r", v.Referencia,
                                       "ch", v.Cheque, "b", v.Banco, "o", v.Origen, "oi", v.OrigenId, "u", _ctx.Usuario.Id, "cr", Date.Now,
                                       "d", totDeb, "h", totHab, "du", totDebU, "hu", totHabU, "ob", v.Observacion)
                                   v.Numero = num
                                   v.Mes = mes
                                   _ctx.Audit("Comprobantes", "COMPROBANTE_NUEVO", v.TipoCodigo & "-" & num & " " & v.Fecha.ToString("dd/MM/yyyy") & " Bs " & totDeb.ToString("N2"))
                               Else
                                   Dim actual As DataTable = Db.Query("SELECT TipoId, Mes, Numero, Estado FROM Comprobante WHERE Id=@i", "i", id)
                                   If actual.Rows.Count = 0 Then Throw New InvalidOperationException("El comprobante no existe.")
                                   Dim r As DataRow = actual.Rows(0)
                                   If r.GetS("Estado") = "A" Then Throw New InvalidOperationException("El comprobante está anulado.")
                                   Dim num As Integer = r.GetI("Numero")
                                   If r.GetI("Mes") <> mes OrElse r.GetI("TipoId") <> tipoId Then
                                       num = Db.ScalarInt("SELECT MAX(Numero) FROM Comprobante WHERE TipoId=@t AND Mes=@m", "t", tipoId, "m", mes) + 1
                                   End If
                                   Db.Execute("UPDATE Comprobante SET TipoId=@t, Numero=@n, Mes=@m, Fecha=@f, TC=@tc, Moneda=@mo, Glosa=@g, Referencia=@r, Cheque=@ch, Banco=@b, Modificado=@md, DebeBs=@d, HaberBs=@h, DebeUsd=@du, HaberUsd=@hu, Observacion=@ob WHERE Id=@i",
                                              "t", tipoId, "n", num, "m", mes, "f", v.Fecha, "tc", CDbl(v.TC), "mo", v.Moneda, "g", v.Glosa, "r", v.Referencia,
                                              "ch", v.Cheque, "b", v.Banco, "md", Date.Now, "d", totDeb, "h", totHab, "du", totDebU, "hu", totHabU, "ob", v.Observacion, "i", id)
                                   Db.Execute("DELETE FROM ComprobanteDet WHERE ComprobanteId=@i", "i", id)
                                   v.Numero = num
                                   v.Mes = mes
                                   _ctx.Audit("Comprobantes", "COMPROBANTE_MOD", v.TipoCodigo & "-" & num & " Bs " & totDeb.ToString("N2"))
                               End If
                               Dim linea As Integer = 0
                               For Each l As VoucherLine In v.Lines
                                   linea += 1
                                   Db.Execute("INSERT INTO ComprobanteDet (ComprobanteId, Linea, CuentaId, Fecha, Glosa, DebeBs, HaberBs, DebeUsd, HaberUsd, CentroCostoId, TerceroId, Cheque, Conciliado, Vigente) " &
                                              "VALUES (@c, @l, @cu, @f, @g, @d, @h, @du, @hu, @cc, @te, @ch, 0, 1)",
                                              "c", id, "l", linea, "cu", l.CuentaId, "f", v.Fecha, "g", If(l.Glosa, ""), "d", l.DebeBs, "h", l.HaberBs, "du", l.DebeUsd, "hu", l.HaberUsd,
                                              "cc", OrNull(l.CentroCostoId), "te", OrNull(l.TerceroId), "ch", If(l.Cheque, ""))
                               Next
                               v.Id = id
                               If v.Facturas.Count > 0 Then
                                   Dim fs As New FacturaService(_ctx)
                                   For Each f As FacturaDto In v.Facturas
                                       f.ComprobanteId = id
                                       If f.Id = 0 Then fs.RegistrarInterno(f)
                                   Next
                               End If
                               Return id
                           End Function)
        End Function

        ' ---------- Lectura ----------
        Public Function Cargar(id As Integer) As Voucher
            Dim dt As DataTable = Db.Query("SELECT c.*, t.Codigo AS TipoCodigo, t.Nombre AS TipoNombre FROM Comprobante c INNER JOIN TipoComprobante t ON t.Id = c.TipoId WHERE c.Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Dim r As DataRow = dt.Rows(0)
            Dim v As New Voucher With {
                .Id = id, .TipoCodigo = r.GetS("TipoCodigo"), .TipoNombre = r.GetS("TipoNombre"), .Numero = r.GetI("Numero"), .Mes = r.GetI("Mes"),
                .Fecha = r.GetDt("Fecha"), .TC = ToDec(r("TC")), .Moneda = r.GetS("Moneda"), .Glosa = r.GetS("Glosa"), .Referencia = r.GetS("Referencia"),
                .Cheque = r.GetS("Cheque"), .Banco = r.GetS("Banco"), .Estado = r.GetS("Estado"), .Origen = r.GetS("Origen"), .OrigenId = r.GetI("OrigenId"),
                .Observacion = r.GetS("Observacion"), .UsuarioId = r.GetI("UsuarioId")}
            For Each d As DataRow In Db.Query("SELECT * FROM ComprobanteDet WHERE ComprobanteId=@i ORDER BY Linea", "i", id).Rows
                Dim l As New VoucherLine With {
                    .CuentaId = d.GetI("CuentaId"), .Glosa = d.GetS("Glosa"), .CentroCostoId = d.GetI("CentroCostoId"), .TerceroId = d.GetI("TerceroId"),
                    .Cheque = d.GetS("Cheque"), .DebeBs = d.GetD("DebeBs"), .HaberBs = d.GetD("HaberBs"), .DebeUsd = d.GetD("DebeUsd"), .HaberUsd = d.GetD("HaberUsd")}
                If v.Moneda = "USD" Then
                    l.Debe = l.DebeUsd
                    l.Haber = l.HaberUsd
                Else
                    l.Debe = l.DebeBs
                    l.Haber = l.HaberBs
                End If
                v.Lines.Add(l)
            Next
            Return v
        End Function

        Public Function BuscarId(tipoCodigo As String, numero As Integer, Optional mes As Integer = 0) As Integer
            Dim m As Integer = If(_ctx.Gestion.CorrelativoMensual, mes, 0)
            Dim o As Object = Db.Scalar("SELECT Id FROM Comprobante WHERE TipoId=@t AND Mes=@m AND Numero=@n", "t", TipoId(tipoCodigo), "m", m, "n", numero)
            Return ToInt(o)
        End Function

        ''' <summary>Id del comprobante anterior/siguiente en el mismo tipo y mes (navegación).</summary>
        Public Function Vecino(id As Integer, siguiente As Boolean) As Integer
            Dim dt As DataTable = Db.Query("SELECT TipoId, Mes, Numero FROM Comprobante WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return 0
            Dim r As DataRow = dt.Rows(0)
            Dim sql As String = If(siguiente,
                "SELECT MIN(Numero) FROM Comprobante WHERE TipoId=@t AND Mes=@m AND Numero > @n",
                "SELECT MAX(Numero) FROM Comprobante WHERE TipoId=@t AND Mes=@m AND Numero < @n")
            Dim num As Integer = Db.ScalarInt(sql, "t", r.GetI("TipoId"), "m", r.GetI("Mes"), "n", r.GetI("Numero"))
            If num = 0 Then Return 0
            Return ToInt(Db.Scalar("SELECT Id FROM Comprobante WHERE TipoId=@t AND Mes=@m AND Numero=@n", "t", r.GetI("TipoId"), "m", r.GetI("Mes"), "n", num))
        End Function

        Public Function Listar(desde As Date, hasta As Date, Optional tipoCodigo As String = "", Optional texto As String = "", Optional incluirAnulados As Boolean = True) As DataTable
            Dim sql As String = "SELECT c.Id, t.Codigo AS Tipo, c.Numero, c.Mes, c.Fecha, c.Glosa, c.DebeBs, c.HaberBs, c.Estado, c.Origen, c.Moneda " &
                                "FROM Comprobante c INNER JOIN TipoComprobante t ON t.Id = c.TipoId WHERE c.Fecha >= @d AND c.Fecha <= @h"
            Dim args As New List(Of Object) From {"d", desde.Date, "h", hasta.Date}
            If tipoCodigo <> "" Then
                sql &= " AND t.Codigo=@t"
                args.AddRange({"t", tipoCodigo})
            End If
            If Not incluirAnulados Then sql &= " AND c.Estado='V'"
            sql &= " ORDER BY c.Fecha, t.Codigo, c.Numero"
            Dim dt As DataTable = Db.Query(sql, args.ToArray())
            If texto <> "" Then
                Dim t As String = texto.ToLowerInvariant()
                For i As Integer = dt.Rows.Count - 1 To 0 Step -1
                    Dim r As DataRow = dt.Rows(i)
                    If Not (r.GetS("Glosa").ToLowerInvariant().Contains(t) OrElse (r.GetS("Tipo") & "-" & r.GetS("Numero")).ToLowerInvariant().Contains(t)) Then dt.Rows.RemoveAt(i)
                Next
            End If
            Return dt
        End Function

        ' ---------- Anulación ----------
        Public Sub Anular(id As Integer, motivo As String)
            _ctx.Requiere("CONT.ANULAR")
            AnularInterno(id, motivo)
        End Sub

        Friend Sub AnularInterno(id As Integer, motivo As String)
            _ctx.RequiereGestionAbierta()
            If String.IsNullOrWhiteSpace(motivo) Then Throw New ArgumentException("Indique el motivo de la anulación.")
            Dim dt As DataTable = Db.Query("SELECT c.Estado, c.Numero, t.Codigo FROM Comprobante c INNER JOIN TipoComprobante t ON t.Id=c.TipoId WHERE c.Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Throw New InvalidOperationException("El comprobante no existe.")
            If dt.Rows(0).GetS("Estado") = "A" Then Return
            Db.InTx(Sub()
                        Db.Execute("UPDATE Comprobante SET Estado='A', Modificado=@m, Observacion=@o WHERE Id=@i", "m", Date.Now, "o", "ANULADO: " & motivo, "i", id)
                        Db.Execute("UPDATE ComprobanteDet SET Vigente=0 WHERE ComprobanteId=@i", "i", id)
                        Db.Execute("UPDATE FacturaIva SET Estado='A' WHERE ComprobanteId=@i", "i", id)
                    End Sub)
            _ctx.Audit("Comprobantes", "COMPROBANTE_ANULADO", dt.Rows(0).GetS("Codigo") & "-" & dt.Rows(0).GetS("Numero") & ": " & motivo)
        End Sub

        ' ---------- Utilitarios ----------
        ''' <summary>Renumera los comprobantes de un tipo (y mes) por fecha, como la opción "Orden de comprobantes" de Orion.</summary>
        Public Sub Reordenar(tipoCodigo As String, mes As Integer)
            _ctx.Requiere("CONT.UTILES")
            _ctx.RequiereGestionAbierta()
            Dim t As Integer = TipoId(tipoCodigo)
            Dim m As Integer = If(_ctx.Gestion.CorrelativoMensual, mes, 0)
            Db.InTx(Sub()
                        Dim lista As DataTable = Db.Query("SELECT Id, Numero FROM Comprobante WHERE TipoId=@t AND Mes=@m ORDER BY Fecha, Numero", "t", t, "m", m)
                        Db.Execute("UPDATE Comprobante SET Numero = Numero + 1000000 WHERE TipoId=@t AND Mes=@m", "t", t, "m", m)
                        Dim n As Integer = 0
                        For Each r As DataRow In lista.Rows
                            n += 1
                            Db.Execute("UPDATE Comprobante SET Numero=@n WHERE Id=@i", "n", n, "i", r.GetI("Id"))
                        Next
                    End Sub)
            _ctx.Audit("Comprobantes", "REORDENAR", tipoCodigo & " mes " & mes)
        End Sub

        Public Sub CambiarNumero(tipoCodigo As String, mes As Integer, numero1 As Integer, numero2 As Integer)
            _ctx.Requiere("CONT.UTILES")
            _ctx.RequiereGestionAbierta()
            Dim t As Integer = TipoId(tipoCodigo)
            Dim m As Integer = If(_ctx.Gestion.CorrelativoMensual, mes, 0)
            Dim a As Integer = ToInt(Db.Scalar("SELECT Id FROM Comprobante WHERE TipoId=@t AND Mes=@m AND Numero=@n", "t", t, "m", m, "n", numero1))
            If a = 0 Then Throw New InvalidOperationException("No existe el comprobante " & numero1 & ".")
            Dim b As Integer = ToInt(Db.Scalar("SELECT Id FROM Comprobante WHERE TipoId=@t AND Mes=@m AND Numero=@n", "t", t, "m", m, "n", numero2))
            Db.InTx(Sub()
                        If b = 0 Then
                            Db.Execute("UPDATE Comprobante SET Numero=@n WHERE Id=@i", "n", numero2, "i", a)
                        Else
                            Db.Execute("UPDATE Comprobante SET Numero=@n WHERE Id=@i", "n", 2000000, "i", a)
                            Db.Execute("UPDATE Comprobante SET Numero=@n WHERE Id=@i", "n", numero1, "i", b)
                            Db.Execute("UPDATE Comprobante SET Numero=@n WHERE Id=@i", "n", numero2, "i", a)
                        End If
                    End Sub)
            _ctx.Audit("Comprobantes", "CAMBIAR_NUMERO", tipoCodigo & " " & numero1 & " <-> " & numero2)
        End Sub

        ''' <summary>Copia un comprobante a una nueva fecha generando un comprobante nuevo (sin facturas ni vínculos).</summary>
        Public Function Copiar(id As Integer, nuevaFecha As Date) As Integer
            _ctx.Requiere("CONT.UTILES")
            Dim v As Voucher = Cargar(id)
            If v Is Nothing Then Throw New InvalidOperationException("El comprobante no existe.")
            v.Id = 0
            v.Fecha = nuevaFecha.Date
            v.TC = New TipoCambioService(_ctx).Dolar(nuevaFecha)
            v.Origen = "MAN"
            v.OrigenId = 0
            v.Observacion = "Copia de " & v.TipoCodigo & "-" & v.Numero
            Return Registrar(v)
        End Function

        ''' <summary>Traslada todos los movimientos de una cuenta a otra (utilitario "Cambios" de Orion).</summary>
        Public Function CambiarCuenta(origenId As Integer, destinoId As Integer, desde As Date, hasta As Date) As Integer
            _ctx.Requiere("CONT.UTILES")
            _ctx.RequiereGestionAbierta()
            Dim o As DataRow = _ctx.CuentaPorId(origenId)
            Dim d As DataRow = _ctx.CuentaPorId(destinoId)
            If o Is Nothing OrElse d Is Nothing Then Throw New InvalidOperationException("Seleccione ambas cuentas.")
            If origenId = destinoId Then Throw New InvalidOperationException("Las cuentas deben ser distintas.")
            If Not d.GetF("EsMovimiento") Then Throw New InvalidOperationException("La cuenta destino no es de movimiento.")
            Dim n As Integer = Db.Execute("UPDATE ComprobanteDet SET CuentaId=@d WHERE CuentaId=@o AND Fecha >= @f AND Fecha <= @h", "d", destinoId, "o", origenId, "f", desde.Date, "h", hasta.Date)
            _ctx.Audit("Comprobantes", "CAMBIO_CUENTA", o.GetS("Codigo") & " -> " & d.GetS("Codigo") & " (" & n & " líneas)")
            Return n
        End Function

    End Class

End Namespace
