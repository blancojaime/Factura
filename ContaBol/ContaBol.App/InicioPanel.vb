Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Tarjeta de indicador (título, valor, detalle).</summary>
Public Class KpiCard
    Inherits Panel

    Private ReadOnly _titulo As New Label()
    Private ReadOnly _valor As New Label()
    Private ReadOnly _detalle As New Label()
    Private ReadOnly _acento As Color

    Public Sub New(titulo As String, acento As Color)
        _acento = acento
        Size = New Size(216, 92)
        BackColor = Color.White
        Margin = New Padding(0, 0, 14, 14)
        _titulo.Text = titulo
        _titulo.ForeColor = Tema.Gris
        _titulo.Font = Tema.FuenteSubtitulo
        _titulo.Location = New Point(14, 10)
        _titulo.AutoSize = True
        _valor.Font = Tema.FuenteKpi
        _valor.ForeColor = Tema.Azul
        _valor.Location = New Point(12, 28)
        _valor.AutoSize = True
        _detalle.ForeColor = Tema.Gris
        _detalle.Font = Tema.FuenteSubtitulo
        _detalle.Location = New Point(14, 66)
        _detalle.AutoSize = True
        Controls.AddRange({_titulo, _valor, _detalle})
        AddHandler Paint, Sub(o, e)
                              e.Graphics.DrawRectangle(New Pen(Tema.Borde), 0, 0, Width - 1, Height - 1)
                              Using b As New SolidBrush(_acento)
                                  e.Graphics.FillRectangle(b, 0, 0, 4, Height)
                              End Using
                          End Sub
    End Sub

    Public Sub Poner(valor As String, Optional detalle As String = "")
        _valor.Text = valor
        _detalle.Text = detalle
    End Sub
End Class

''' <summary>Gráfico simple de barras agrupadas (ingresos vs gastos por mes), dibujado con GDI+.</summary>
Public Class GraficoBarras
    Inherits Panel

    Public Property Etiquetas As New List(Of String)
    Public Property SerieA As New List(Of Decimal)
    Public Property SerieB As New List(Of Decimal)
    Public Property NombreA As String = "Ingresos"
    Public Property NombreB As String = "Gastos"

    Public Sub New()
        DoubleBuffered = True
        BackColor = Color.White
        Size = New Size(520, 250)
    End Sub

    Protected Overrides Sub OnPaint(e As PaintEventArgs)
        MyBase.OnPaint(e)
        Dim g As Graphics = e.Graphics
        g.SmoothingMode = Drawing2D.SmoothingMode.AntiAlias
        g.DrawRectangle(New Pen(Tema.Borde), 0, 0, Width - 1, Height - 1)
        g.DrawString("Ingresos y gastos por mes (Bs)", Tema.FuenteNegrita, New SolidBrush(Tema.Azul), 14, 10)
        Dim n As Integer = Etiquetas.Count
        Dim izq As Integer = 70, der As Integer = 16, sup As Integer = 44, inf As Integer = 36
        Dim ancho As Integer = Width - izq - der
        Dim alto As Integer = Height - sup - inf
        If n = 0 OrElse ancho <= 0 OrElse alto <= 0 Then
            g.DrawString("Sin movimientos para graficar.", Tema.Fuente, New SolidBrush(Tema.Gris), 14, 50)
            Return
        End If
        Dim maximo As Decimal = Math.Max(1D, Math.Max(SerieA.DefaultIfEmpty(0D).Max(), SerieB.DefaultIfEmpty(0D).Max()))
        Dim paso As Decimal = NiceStep(maximo / 4D)
        Dim tope As Decimal = paso * 4D
        If tope < maximo Then tope = paso * 5D
        Using pf As New Pen(Color.FromArgb(232, 236, 242))
            For i As Integer = 0 To 4
                Dim y As Integer = sup + alto - CInt(alto * (paso * i) / tope)
                g.DrawLine(pf, izq, y, izq + ancho, y)
                Dim txt As String = (paso * i).ToString("#,##0", FormatoVal.Cultura)
                Dim sz As SizeF = g.MeasureString(txt, Tema.FuenteSubtitulo)
                g.DrawString(txt, Tema.FuenteSubtitulo, New SolidBrush(Tema.Gris), izq - sz.Width - 6, y - sz.Height / 2)
            Next
        End Using
        Dim grupo As Single = ancho / CSng(n)
        Dim barra As Single = Math.Min(30.0F, grupo / 3.0F)
        For i As Integer = 0 To n - 1
            Dim x0 As Single = izq + grupo * i + (grupo - 2 * barra - 4) / 2
            Dim ha As Single = CSng(alto * SerieA(i) / tope), hb As Single = CSng(alto * SerieB(i) / tope)
            g.FillRectangle(New SolidBrush(Tema.AzulMedio), x0, sup + alto - ha, barra, ha)
            g.FillRectangle(New SolidBrush(Color.FromArgb(214, 140, 60)), x0 + barra + 4, sup + alto - hb, barra, hb)
            Dim sz As SizeF = g.MeasureString(Etiquetas(i), Tema.FuenteSubtitulo)
            g.DrawString(Etiquetas(i), Tema.FuenteSubtitulo, New SolidBrush(Tema.Gris), izq + grupo * i + (grupo - sz.Width) / 2, sup + alto + 6)
        Next
        g.FillRectangle(New SolidBrush(Tema.AzulMedio), Width - 190, 14, 12, 12)
        g.DrawString(NombreA, Tema.FuenteSubtitulo, New SolidBrush(Tema.ColorTexto), Width - 174, 11)
        g.FillRectangle(New SolidBrush(Color.FromArgb(214, 140, 60)), Width - 100, 14, 12, 12)
        g.DrawString(NombreB, Tema.FuenteSubtitulo, New SolidBrush(Tema.ColorTexto), Width - 84, 11)
    End Sub

    Private Shared Function NiceStep(v As Decimal) As Decimal
        If v <= 0D Then Return 1D
        Dim mag As Decimal = CDec(Math.Pow(10, Math.Floor(Math.Log10(CDbl(v)))))
        Dim norm As Decimal = v / mag
        Dim n As Decimal = If(norm <= 1D, 1D, If(norm <= 2D, 2D, If(norm <= 5D, 5D, 10D)))
        Return n * mag
    End Function
End Class

''' <summary>Página de inicio: indicadores del negocio, avisos pendientes y accesos rápidos.</summary>
Public Class InicioPanel
    Inherits Panel

    Private ReadOnly _saludo As New Label()
    Private ReadOnly _sub As New Label()
    Private ReadOnly _kpis As New FlowLayoutPanel()
    Private ReadOnly _avisos As New FlowLayoutPanel()
    Private ReadOnly _accesos As New FlowLayoutPanel()
    Private ReadOnly _grafico As New GraficoBarras()
    Private ReadOnly _kDisp As New KpiCard("Disponible (caja y bancos)", Tema.Verde)
    Private ReadOnly _kVentas As New KpiCard("Ventas del mes", Tema.AzulMedio)
    Private ReadOnly _kCompras As New KpiCard("Compras del mes", Color.FromArgb(214, 140, 60))
    Private ReadOnly _kCobrar As New KpiCard("Cuentas por cobrar", Tema.Azul)
    Private ReadOnly _kPagar As New KpiCard("Cuentas por pagar", Tema.Rojo)
    Private ReadOnly _kIva As New KpiCard("IVA estimado del mes", Tema.Ambar)

    Public Sub New()
        AutoScroll = True
        BackColor = Tema.Fondo
        Padding = New Padding(24, 18, 24, 18)
        _saludo.Font = New Font("Segoe UI Semibold", 20.0F)
        _saludo.ForeColor = Tema.Azul
        _saludo.AutoSize = True
        _saludo.Location = New Point(24, 16)
        _sub.ForeColor = Tema.Gris
        _sub.Font = Tema.FuenteGrande
        _sub.AutoSize = True
        _sub.Location = New Point(26, 56)
        _kpis.Location = New Point(24, 100)
        _kpis.Size = New Size(1000, 106)
        _kpis.WrapContents = True
        _kpis.AutoSize = True
        _kpis.MaximumSize = New Size(1400, 0)
        _kpis.Controls.AddRange({_kDisp, _kVentas, _kCompras, _kCobrar, _kPagar, _kIva})
        _grafico.Location = New Point(24, 224)
        _avisos.Location = New Point(570, 224)
        _avisos.Size = New Size(480, 250)
        _avisos.FlowDirection = FlowDirection.TopDown
        _avisos.WrapContents = False
        _avisos.BackColor = Color.White
        _avisos.Padding = New Padding(14, 40, 10, 8)
        AddHandler _avisos.Paint, Sub(o, e)
                                      e.Graphics.DrawRectangle(New Pen(Tema.Borde), 0, 0, _avisos.Width - 1, _avisos.Height - 1)
                                      e.Graphics.DrawString("Pendientes y avisos", Tema.FuenteNegrita, New SolidBrush(Tema.Azul), 14, 10)
                                  End Sub
        Dim lblAcc As New Label() With {.Text = "Accesos rápidos", .Font = Tema.FuenteGrande, .ForeColor = Tema.Azul, .AutoSize = True, .Location = New Point(24, 494)}
        _accesos.Location = New Point(24, 524)
        _accesos.Size = New Size(1100, 140)
        _accesos.WrapContents = True
        Controls.AddRange({_saludo, _sub, _kpis, _grafico, _avisos, lblAcc, _accesos})
    End Sub

    Private Sub Acceso(titulo As String, detalle As String, accion As Action)
        Dim b As New Button() With {.FlatStyle = FlatStyle.Flat, .BackColor = Color.White, .Size = New Size(210, 62), .TextAlign = ContentAlignment.MiddleLeft,
            .Margin = New Padding(0, 0, 12, 12), .Cursor = Cursors.Hand, .Padding = New Padding(10, 0, 0, 0), .Font = Tema.Fuente}
        b.FlatAppearance.BorderColor = Tema.Borde
        b.FlatAppearance.MouseOverBackColor = Tema.AzulClaro
        b.Text = titulo & vbCrLf & detalle
        b.ForeColor = Tema.Azul
        AddHandler b.Click, Sub(o, e)
                                Try
                                    accion()
                                Catch ex As Exception
                                    Msg.ErrorMsg(ex)
                                End Try
                            End Sub
        _accesos.Controls.Add(b)
    End Sub

    Private Sub Aviso(texto As String, color_ As Color, Optional accion As Action = Nothing)
        Dim l As New LinkLabel() With {.Text = "•  " & texto, .AutoSize = True, .LinkColor = color_, .ActiveLinkColor = Tema.AzulMedio, .LinkBehavior = LinkBehavior.HoverUnderline, .Margin = New Padding(0, 0, 0, 7), .MaximumSize = New Size(440, 0)}
        If accion IsNot Nothing Then AddHandler l.LinkClicked, Sub(o, e) accion()
        _avisos.Controls.Add(l)
    End Sub

    Public Sub Cargar()
        Dim c As Contexto = Sesion.Ctx
        _saludo.Text = "Bienvenido, " & If(Sesion.Usuario Is Nothing, "", Sesion.Usuario.Nombre.Split(" "c)(0))
        _accesos.Controls.Clear()
        _avisos.Controls.Clear()
        If c Is Nothing Then
            _sub.Text = "Seleccione una empresa y gestión para comenzar (Archivo > Cambiar empresa o gestión)."
            For Each k As KpiCard In {_kDisp, _kVentas, _kCompras, _kCobrar, _kPagar, _kIva}
                k.Poner("-")
            Next
            _grafico.Etiquetas.Clear()
            _grafico.Invalidate()
            Return
        End If
        _sub.Text = c.Empresa.RazonSocial & "  ·  Gestión " & c.Gestion.Anio & "  ·  " & If(c.Gestion.Abierta, "abierta", "CERRADA")
        Dim hoy As Date = Date.Today
        If hoy < c.Gestion.FechaInicio OrElse hoy > c.Gestion.FechaFin Then hoy = c.Gestion.FechaFin
        Dim ini As Date = InicioDeMes(hoy), fin As Date = FinDeMes(hoy)
        Try
            Dim led As New LedgerService(c)
            Dim disp As Decimal = 0D
            Dim caja As Integer = c.CuentaParamOpcional(ParamKeys.CtaCaja)
            If caja <> 0 Then
                Dim r As DataRow = c.CuentaPorId(caja)
                While r IsNot Nothing AndAlso r.GetI("Nivel") > 3
                    r = c.CuentaPorId(r.GetI("PadreId"))
                End While
                If r IsNot Nothing Then disp = led.SaldoCuenta(r.GetI("Id"), hoy)
            End If
            _kDisp.Poner(disp.ToString("N2", FormatoVal.Cultura), "Bs al " & hoy.ToString("dd/MM/yyyy"))
        Catch
            _kDisp.Poner("-")
        End Try
        Try
            Dim v As Decimal = c.Db.ScalarDec("SELECT SUM(TotalBs) FROM Venta WHERE Estado='V' AND Fecha >= @d AND Fecha <= @h", "d", ini, "h", fin)
            Dim n As Integer = c.Db.ScalarInt("SELECT COUNT(*) FROM Venta WHERE Estado='V' AND Fecha >= @d AND Fecha <= @h", "d", ini, "h", fin)
            _kVentas.Poner(v.ToString("N2", FormatoVal.Cultura), n & " venta(s) en " & NombreMes(hoy.Month))
            Dim cp As Decimal = c.Db.ScalarDec("SELECT SUM(TotalBs) FROM Compra WHERE Estado='V' AND Fecha >= @d AND Fecha <= @h", "d", ini, "h", fin)
            Dim nc As Integer = c.Db.ScalarInt("SELECT COUNT(*) FROM Compra WHERE Estado='V' AND Fecha >= @d AND Fecha <= @h", "d", ini, "h", fin)
            _kCompras.Poner(cp.ToString("N2", FormatoVal.Cultura), nc & " compra(s) en " & NombreMes(hoy.Month))
        Catch
            _kVentas.Poner("-")
            _kCompras.Poner("-")
        End Try
        Try
            Dim ts As New TerceroService(c)
            Dim xc As Decimal = ts.SaldosPorTercero("CXC", hoy).Rows.Cast(Of DataRow)().Sum(Function(r) r.GetD("Saldo"))
            Dim xp As Decimal = ts.SaldosPorTercero("CXP", hoy).Rows.Cast(Of DataRow)().Sum(Function(r) r.GetD("Saldo"))
            _kCobrar.Poner(xc.ToString("N2", FormatoVal.Cultura), "clientes que nos deben")
            _kPagar.Poner(xp.ToString("N2", FormatoVal.Cultura), "deuda con proveedores")
        Catch
            _kCobrar.Poner("-")
            _kPagar.Poner("-")
        End Try
        Try
            Dim fs As New FacturaService(c)
            Dim v = fs.Totales("V", ini, fin)
            Dim cc = fs.Totales("C", ini, fin)
            Dim dif As Decimal = v.Item2 - cc.Item2
            _kIva.Poner(dif.ToString("N2", FormatoVal.Cultura), "DF " & v.Item2.ToString("N0", FormatoVal.Cultura) & " - CF " & cc.Item2.ToString("N0", FormatoVal.Cultura))
        Catch
            _kIva.Poner("-")
        End Try
        CargarGrafico(c, hoy)
        CargarAvisos(c, hoy)
        If Sesion.Puede("CONT.COMPROBANTES") Then Acceso("Nuevo comprobante", "Ingreso, egreso o traspaso", Sub() Escritorio.AbrirNueva(New ComprobanteForm(), Nothing))
        If Sesion.Puede("COM.VENTAS") Then Acceso("Nueva venta", "Contado o crédito, con factura", Sub() Escritorio.AbrirNueva(New DocumentoForm(True), Nothing))
        If Sesion.Puede("COM.COMPRAS") Then Acceso("Nueva compra", "Con crédito fiscal e inventario", Sub() Escritorio.AbrirNueva(New DocumentoForm(False), Nothing))
        If Sesion.Puede("COM.COBROS") Then Acceso("Cobros y pagos", "Aplicar a documentos", Sub() Escritorio.AbrirNueva(New CobroPagoForm(), Nothing))
        If Sesion.Puede("IVA.REPORTES") Then Acceso("Libro de ventas IVA", "Formato LCV del SIN", Sub() Informes.Abrir("libro_ventas"))
        If Sesion.Puede("CONT.REPORTES") Then Acceso("Balance general", "Al día de hoy", Sub() Informes.Abrir("balance_general"))
        If Sesion.Puede("ADM.BACKUP") Then Acceso("Copia de seguridad", "Proteja sus datos", Sub() BackupForm.Mostrar())
        Acceso("Centro de reportes", "Todos los informes PDF y Excel", Sub() Escritorio.AbrirNueva(New CentroReportesForm(), "CentroReportes"))
    End Sub

    Private Sub CargarGrafico(c As Contexto, hoy As Date)
        _grafico.Etiquetas.Clear()
        _grafico.SerieA.Clear()
        _grafico.SerieB.Clear()
        Try
            Dim meses As New List(Of Date)
            For i As Integer = 5 To 0 Step -1
                Dim m As Date = New Date(hoy.Year, hoy.Month, 1).AddMonths(-i)
                If m >= InicioDeMes(c.Gestion.FechaInicio) Then meses.Add(m)
            Next
            If meses.Count = 0 Then Return
            Dim dt As DataTable = c.Db.Query("SELECT Fecha, CuentaId, DebeBs, HaberBs FROM ComprobanteDet WHERE Vigente=1 AND Fecha >= @d AND Fecha <= @h", "d", meses(0), "h", FinDeMes(meses(meses.Count - 1)))
            Dim ing As New Dictionary(Of Integer, Decimal), gas As New Dictionary(Of Integer, Decimal)
            For Each r As DataRow In dt.Rows
                Dim cta As DataRow = c.CuentaPorId(r.GetI("CuentaId"))
                If cta Is Nothing Then Continue For
                Dim rubro As Integer = cta.GetI("Rubro")
                If rubro <> 4 AndAlso rubro <> 5 Then Continue For
                Dim k As Integer = r.GetDt("Fecha").Year * 12 + r.GetDt("Fecha").Month
                If rubro = 4 Then ing(k) = (If(ing.ContainsKey(k), ing(k), 0D)) + r.GetD("HaberBs") - r.GetD("DebeBs")
                If rubro = 5 Then gas(k) = (If(gas.ContainsKey(k), gas(k), 0D)) + r.GetD("DebeBs") - r.GetD("HaberBs")
            Next
            For Each m In meses
                Dim k As Integer = m.Year * 12 + m.Month
                _grafico.Etiquetas.Add(NombreMes(m.Month).Substring(0, 3))
                _grafico.SerieA.Add(Math.Max(0D, If(ing.ContainsKey(k), ing(k), 0D)))
                _grafico.SerieB.Add(Math.Max(0D, If(gas.ContainsKey(k), gas(k), 0D)))
            Next
        Catch
        End Try
        _grafico.Invalidate()
    End Sub

    Private Sub CargarAvisos(c As Contexto, hoy As Date)
        Try
            If Not c.Gestion.Abierta Then Aviso("La gestión está cerrada: solo se permiten consultas y reportes.", Tema.Ambar)
            If Not New TipoCambioService(c).Existe(Date.Today) AndAlso c.Gestion.Abierta Then
                Aviso("No hay tipo de cambio cargado para hoy. Se usa el último vigente (" & New TipoCambioService(c).Dolar(Date.Today).ToString("0.00", FormatoVal.Cultura) & ").", Tema.Ambar, Sub() Escritorio.Abrir(Of TipoCambioForm)())
            End If
            Dim bajos As Integer = New InventarioService(c).SugerenciaCompras().Rows.Count
            If bajos > 0 Then Aviso(bajos & " ítem(s) bajo el stock mínimo: revise la sugerencia de compras.", Tema.Rojo, Sub() Informes.Abrir("sugerencia_compras"))
            Dim venc As Integer = c.Db.ScalarInt("SELECT COUNT(*) FROM Venta WHERE Estado='V' AND SaldoBs > 0 AND Vencimiento IS NOT NULL AND Vencimiento < @h", "h", Date.Today)
            If venc > 0 Then Aviso(venc & " venta(s) a crédito vencidas sin cobrar.", Tema.Rojo, Sub() Informes.Abrir("documentos_pendientes", New Dictionary(Of String, Object) From {{"clase", "CXC"}}))
            Dim porVencer As Integer = New InventarioService(c).PorVencer(Date.Today.AddDays(30)).Rows.Count
            If porVencer > 0 Then Aviso(porVencer & " lote(s) de productos vencidos o por vencer en 30 días.", Tema.Ambar, Sub() Informes.Abrir("por_vencer"))
            Dim sinUfv As Boolean = New TipoCambioService(c).Ufv(Date.Today) <= 0D
            If sinUfv AndAlso c.Db.ScalarInt("SELECT COUNT(*) FROM ActivoFijo WHERE Estado='A'") > 0 Then Aviso("No hay UFV cargada: la depreciación de activos fijos no se actualizará.", Tema.Ambar, Sub() Escritorio.Abrir(Of TipoCambioForm)())
            Dim ultimoBackup As Object = c.Sistema.Db.Scalar("SELECT MAX(Fecha) FROM RegistroBackup WHERE Resultado='OK'")
            If ultimoBackup Is Nothing Then
                Aviso("Aún no hay copias de seguridad. Haga una desde Archivo > Copia de seguridad.", Tema.Rojo, Sub() BackupForm.Mostrar())
            ElseIf (Date.Now - ToDate(ultimoBackup)).TotalDays > 7 Then
                Aviso("La última copia de seguridad es del " & ToDate(ultimoBackup).ToString("dd/MM/yyyy") & ". Se recomienda respaldar semanalmente.", Tema.Ambar, Sub() BackupForm.Mostrar())
            End If
            If _avisos.Controls.Count = 0 Then Aviso("Todo en orden. No hay pendientes.", Tema.Verde)
        Catch
        End Try
    End Sub
End Class
