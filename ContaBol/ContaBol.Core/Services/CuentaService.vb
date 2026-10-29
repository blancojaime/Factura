Imports System.Text.RegularExpressions
Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class CuentaDto
        Public Property Id As Integer
        Public Property Codigo As String = ""
        Public Property Nombre As String = ""
        Public Property Moneda As String = "BS"
        Public Property Ajustable As Boolean
        Public Property Presupuestable As Boolean
        Public Property CostoTipo As String = ""
        Public Property EsBanco As Boolean
        Public Property EsMovimiento As Boolean = True
        Public Property Activa As Boolean = True
    End Class

    ''' <summary>Administración del plan de cuentas (jerárquico, multinivel).</summary>
    Public Class CuentaService
        Private ReadOnly _ctx As Contexto

        Public Sub New(ctx As Contexto)
            _ctx = ctx
        End Sub

        Public Function Listar(Optional soloMovimiento As Boolean = False, Optional soloActivas As Boolean = True) As DataTable
            Dim sql As String = "SELECT * FROM Cuenta WHERE 1=1"
            If soloMovimiento Then sql &= " AND EsMovimiento=1"
            If soloActivas Then sql &= " AND Activa=1"
            Return _ctx.Db.Query(sql & " ORDER BY Codigo")
        End Function

        ''' <summary>Búsqueda estilo Orion: * como comodín (ej. "2*", "*sueldos*"). Sin comodín busca "contiene".</summary>
        Public Function Buscar(patron As String, porCodigo As Boolean, Optional soloMovimiento As Boolean = True) As List(Of DataRow)
            Dim res As New List(Of DataRow)
            Dim p As String = If(patron, "").Trim()
            Dim rx As Regex = Nothing
            If p <> "" Then
                If p.Contains("*"c) OrElse p.Contains("?"c) Then
                    rx = New Regex("^" & Regex.Escape(p).Replace("\*", ".*").Replace("\?", ".") & "$", RegexOptions.IgnoreCase Or RegexOptions.CultureInvariant)
                Else
                    rx = New Regex(Regex.Escape(p), RegexOptions.IgnoreCase Or RegexOptions.CultureInvariant)
                End If
            End If
            For Each r As DataRow In _ctx.Cuentas().Rows
                If soloMovimiento AndAlso Not r.GetF("EsMovimiento") Then Continue For
                If Not r.GetF("Activa") Then Continue For
                If rx Is Nothing OrElse rx.IsMatch(If(porCodigo, r.GetS("Codigo"), r.GetS("Nombre"))) Then res.Add(r)
            Next
            Return res
        End Function

        Public Function TieneMovimientos(cuentaId As Integer) As Boolean
            Return _ctx.Db.ScalarInt("SELECT COUNT(*) FROM ComprobanteDet WHERE CuentaId=@c", "c", cuentaId) > 0
        End Function

        Public Function Hijos(cuentaId As Integer) As Integer
            Return _ctx.Db.ScalarInt("SELECT COUNT(*) FROM Cuenta WHERE PadreId=@c", "c", cuentaId)
        End Function

        Public Shared Function CodigoValido(codigo As String) As Boolean
            Return Regex.IsMatch(If(codigo, ""), "^[0-9]+(\.[0-9A-Za-z]+)*$|^[0-9]+$")
        End Function

        Public Function Guardar(c As CuentaDto) As Integer
            _ctx.Requiere("CONT.PLAN")
            _ctx.RequiereGestionAbierta()
            c.Codigo = If(c.Codigo, "").Trim()
            c.Nombre = If(c.Nombre, "").Trim()
            If Not CodigoValido(c.Codigo) Then Throw New ArgumentException("Código de cuenta inválido. Use dígitos y puntos, ej. 1.1.1.01.001")
            If c.Nombre = "" Then Throw New ArgumentException("La descripción de la cuenta es obligatoria.")
            If c.Codigo(0) < "1"c OrElse c.Codigo(0) > "7"c Then Throw New ArgumentException("El primer dígito debe ser el rubro: 1 Activo, 2 Pasivo, 3 Patrimonio, 4 Ingreso, 5 Egreso, 6/7 Cuentas de orden.")
            Dim id As Integer = _ctx.Db.InTx(Function() GuardarInterno(c))
            _ctx.InvalidarCuentas()
            Return id
        End Function

        Private Function GuardarInterno(c As CuentaDto) As Integer
            Dim db As Database = _ctx.Db
            Dim existente As DataRow = _ctx.CuentaPorCodigo(c.Codigo)
            If c.Id = 0 AndAlso existente IsNot Nothing Then Throw New InvalidOperationException("El código " & c.Codigo & " ya existe: " & existente.GetS("Nombre"))
            If c.Id <> 0 AndAlso existente IsNot Nothing AndAlso existente.GetI("Id") <> c.Id Then Throw New InvalidOperationException("El código " & c.Codigo & " ya pertenece a otra cuenta.")

            Dim codigos As New HashSet(Of String)(_ctx.Cuentas().Rows.Cast(Of DataRow)().Where(Function(r) r.GetI("Id") <> c.Id).Select(Function(r) r.GetS("Codigo")), StringComparer.OrdinalIgnoreCase)
            Dim padreCod As String = EmpresaService.PadreDe(c.Codigo, codigos)
            Dim padreId As Object = DBNull.Value
            Dim nivel As Integer = 1
            If padreCod <> "" Then
                Dim p As DataRow = _ctx.CuentaPorCodigo(padreCod)
                padreId = p.GetI("Id")
                nivel = p.GetI("Nivel") + 1
            End If
            Dim rubro As Integer = ToInt(c.Codigo.Substring(0, 1))
            Dim nat As String = If(rubro = 1 OrElse rubro = 5 OrElse rubro = 6, "D", "A")

            If c.Id = 0 Then
                If padreCod <> "" Then
                    Dim p As DataRow = _ctx.CuentaPorCodigo(padreCod)
                    If TieneMovimientos(p.GetI("Id")) Then Throw New InvalidOperationException("La cuenta padre '" & padreCod & "' tiene movimientos; no puede tener subcuentas.")
                    db.Execute("UPDATE Cuenta SET EsMovimiento=0 WHERE Id=@i", "i", p.GetI("Id"))
                End If
                Dim id As Integer = db.Insert(
                    "INSERT INTO Cuenta (Codigo, Nombre, Nivel, PadreId, Rubro, Naturaleza, EsMovimiento, Moneda, Ajustable, Presupuestable, CostoTipo, EsBanco, Activa) VALUES (@c, @n, @nv, @p, @r, @na, 1, @mo, @aj, @pr, @ct, @b, 1)",
                    "c", c.Codigo, "n", c.Nombre, "nv", nivel, "p", padreId, "r", rubro, "na", nat, "mo", c.Moneda,
                    "aj", If(c.Ajustable, 1, 0), "pr", If(c.Presupuestable, 1, 0), "ct", c.CostoTipo, "b", If(c.EsBanco, 1, 0))
                _ctx.Audit("Plan de cuentas", "CUENTA_NUEVA", c.Codigo & " " & c.Nombre)
                Return id
            Else
                Dim actual As DataRow = _ctx.CuentaPorId(c.Id)
                If actual Is Nothing Then Throw New InvalidOperationException("La cuenta no existe.")
                If actual.GetS("Codigo") <> c.Codigo Then
                    If Hijos(c.Id) > 0 OrElse TieneMovimientos(c.Id) Then Throw New InvalidOperationException("No se puede cambiar el código de una cuenta con subcuentas o movimientos. Use 'Cambio de cuenta' en utilitarios.")
                End If
                Dim movi As Boolean = c.EsMovimiento
                If Hijos(c.Id) > 0 Then movi = False
                If movi = False AndAlso Hijos(c.Id) = 0 AndAlso TieneMovimientos(c.Id) Then movi = True
                db.Execute("UPDATE Cuenta SET Codigo=@c, Nombre=@n, Nivel=@nv, PadreId=@p, Rubro=@r, EsMovimiento=@m, Moneda=@mo, Ajustable=@aj, Presupuestable=@pr, CostoTipo=@ct, EsBanco=@b, Activa=@a WHERE Id=@i",
                           "c", c.Codigo, "n", c.Nombre, "nv", nivel, "p", padreId, "r", rubro, "m", If(movi, 1, 0), "mo", c.Moneda,
                           "aj", If(c.Ajustable, 1, 0), "pr", If(c.Presupuestable, 1, 0), "ct", c.CostoTipo, "b", If(c.EsBanco, 1, 0),
                           "a", If(c.Activa, 1, 0), "i", c.Id)
                _ctx.Audit("Plan de cuentas", "CUENTA_MOD", c.Codigo & " " & c.Nombre)
                Return c.Id
            End If
        End Function

        Public Sub Eliminar(id As Integer)
            _ctx.Requiere("CONT.PLAN")
            _ctx.RequiereGestionAbierta()
            Dim r As DataRow = _ctx.CuentaPorId(id)
            If r Is Nothing Then Return
            If Hijos(id) > 0 Then Throw New InvalidOperationException("La cuenta tiene subcuentas. Elimínelas primero.")
            If TieneMovimientos(id) Then Throw New InvalidOperationException("La cuenta tiene movimientos contables y no puede eliminarse. Puede desactivarla.")
            For Each kv In _ctx.Param.Todos()
                If kv.Key.StartsWith("CTA_", StringComparison.Ordinal) AndAlso String.Equals(kv.Value, r.GetS("Codigo"), StringComparison.OrdinalIgnoreCase) Then
                    Throw New InvalidOperationException("La cuenta está configurada en Parámetros (" & kv.Key & "). Cambie el parámetro antes de eliminarla.")
                End If
            Next
            If _ctx.Db.ScalarInt("SELECT COUNT(*) FROM Presupuesto WHERE CuentaId=@c", "c", id) > 0 Then _ctx.Db.Execute("DELETE FROM Presupuesto WHERE CuentaId=@c", "c", id)
            _ctx.Db.Execute("DELETE FROM Cuenta WHERE Id=@i", "i", id)
            _ctx.InvalidarCuentas()
            ' Si el padre queda sin hijos vuelve a ser cuenta de movimiento.
            Dim pid As Integer = r.GetI("PadreId")
            If pid <> 0 AndAlso Hijos(pid) = 0 Then _ctx.Db.Execute("UPDATE Cuenta SET EsMovimiento=1 WHERE Id=@i", "i", pid)
            _ctx.InvalidarCuentas()
            _ctx.Audit("Plan de cuentas", "CUENTA_ELIM", r.GetS("Codigo") & " " & r.GetS("Nombre"))
        End Sub

        ''' <summary>Importa un plan desde líneas "codigo;nombre;flags". Solo permitido si la gestión no tiene comprobantes.</summary>
        Public Sub ImportarPlan(lineas As IEnumerable(Of String), reemplazar As Boolean)
            _ctx.Requiere("CONT.PLAN")
            _ctx.RequiereGestionAbierta()
            If _ctx.Db.ScalarInt("SELECT COUNT(*) FROM Comprobante") > 0 AndAlso reemplazar Then
                Throw New InvalidOperationException("No se puede reemplazar el plan de cuentas porque ya existen comprobantes.")
            End If
            _ctx.Db.InTx(Sub()
                             If reemplazar Then
                                 _ctx.Db.Execute("DELETE FROM Presupuesto")
                                 _ctx.Db.Execute("DELETE FROM Cuenta")
                             End If
                             Dim nuevas As New List(Of String)
                             For Each l As String In lineas
                                 If String.IsNullOrWhiteSpace(l) Then Continue For
                                 Dim cod As String = l.Split(";"c)(0).Trim()
                                 If Not reemplazar AndAlso _ctx.CuentaPorCodigo(cod) IsNot Nothing Then Continue For
                                 nuevas.Add(l)
                             Next
                             If reemplazar Then
                                 EmpresaService.CargarPlan(_ctx.Db, nuevas)
                             Else
                                 For Each l As String In nuevas.OrderBy(Function(x) x.Split(";"c)(0), StringComparer.Ordinal)
                                     Dim a As String() = l.Split(";"c)
                                     Dim flags As String = If(a.Length > 2, a(2).ToUpperInvariant(), "")
                                     Guardar(New CuentaDto With {.Codigo = a(0).Trim(), .Nombre = a(1).Trim(), .Moneda = If(flags.Contains("U"c), "USD", "BS"),
                                         .Ajustable = flags.Contains("A"c), .EsBanco = flags.Contains("B"c), .CostoTipo = If(flags.Contains("F"c), "F", If(flags.Contains("V"c), "V", ""))})
                                     _ctx.InvalidarCuentas()
                                 Next
                             End If
                         End Sub)
            _ctx.InvalidarCuentas()
            _ctx.Audit("Plan de cuentas", "PLAN_IMPORTADO", "Reemplazar=" & reemplazar)
        End Sub

    End Class

End Namespace
