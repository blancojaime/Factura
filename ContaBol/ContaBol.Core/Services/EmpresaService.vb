Imports System.IO
Imports System.Text.RegularExpressions
Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Seed

Namespace Services

    Public Enum PlantillaPlan
        Comercial
        Vacio
    End Enum

    Public Class NuevaGestionOpciones
        Public Property Anio As Integer = Date.Today.Year
        ''' <summary>Mes en que inicia el ejercicio fiscal (1 comercial, 4 industrial, 7 agropecuario, 10 minero).</summary>
        Public Property MesInicio As Integer = 1
        Public Property CorrelativoMensual As Boolean = True
        Public Property Plantilla As PlantillaPlan = PlantillaPlan.Comercial
        Public Property TipoCambioInicial As Decimal = 6.96D
    End Class

    ''' <summary>Alta de empresas y creación de gestiones (cada gestión es un archivo de base de datos independiente).</summary>
    Public Class EmpresaService

        Private ReadOnly _sis As SistemaService

        Public Sub New(sis As SistemaService)
            _sis = sis
        End Sub

        Public Shared Function CarpetaSegura(codigo As String) As String
            Dim c As String = Regex.Replace(If(codigo, "").Trim(), "[^A-Za-z0-9_\-]", "_")
            If c = "" Then Throw New ArgumentException("El código de la empresa es obligatorio.")
            Return c.ToUpperInvariant()
        End Function

        ''' <summary>Crea la empresa y su primera gestión. Devuelve (empresaId, gestionId).</summary>
        Public Function CrearEmpresa(e As EmpresaInfo, opc As NuevaGestionOpciones, Optional usuarioCreadorId As Integer = 0) As Tuple(Of Integer, Integer)
            If String.IsNullOrWhiteSpace(e.Codigo) Then Throw New ArgumentException("El código de la empresa es obligatorio.")
            If String.IsNullOrWhiteSpace(e.RazonSocial) Then Throw New ArgumentException("La razón social es obligatoria.")
            e.Codigo = e.Codigo.Trim().ToUpperInvariant()
            If _sis.Db.ScalarInt("SELECT COUNT(*) FROM Empresa WHERE Codigo=@c", "c", e.Codigo) > 0 Then
                Throw New InvalidOperationException("Ya existe una empresa con el código '" & e.Codigo & "'.")
            End If
            e.Carpeta = CarpetaSegura(e.Codigo)
            Dim empresaId As Integer = _sis.Db.Insert(
                "INSERT INTO Empresa (Codigo, RazonSocial, NombreComercial, Nit, Direccion, Ciudad, Telefono, Email, Actividad, RepLegal, Matricula, Carpeta, FechaCreacion, Activa, EsDefecto, Observacion) " &
                "VALUES (@c, @rs, @nc, @nit, @dir, @ciu, @tel, @em, @act, @rep, @mat, @car, @fc, 1, 0, @obs)",
                "c", e.Codigo, "rs", e.RazonSocial, "nc", e.NombreComercial, "nit", e.Nit, "dir", e.Direccion, "ciu", e.Ciudad,
                "tel", e.Telefono, "em", e.Email, "act", e.Actividad, "rep", e.RepLegal, "mat", e.Matricula, "car", e.Carpeta,
                "fc", Date.Today, "obs", e.Observacion)
            e.Id = empresaId
            Dim gestionId As Integer
            Try
                gestionId = CrearGestion(e, opc)
            Catch
                ' Si falla la creación de la base de la gestión no deja la empresa a medias.
                _sis.Db.Execute("DELETE FROM Empresa WHERE Id=@i", "i", empresaId)
                Throw
            End Try
            If usuarioCreadorId <> 0 Then
                _sis.AsignarEmpresa(usuarioCreadorId, empresaId, Permisos.RolAdministrador)
            End If
            If _sis.Db.ScalarInt("SELECT COUNT(*) FROM Empresa WHERE EsDefecto=1") = 0 Then _sis.MarcarDefecto(empresaId, gestionId)
            _sis.Auditar(usuarioCreadorId, "", empresaId, gestionId, "Administración", "EMPRESA_NUEVA", e.Codigo & " - " & e.RazonSocial)
            Return Tuple.Create(empresaId, gestionId)
        End Function

        Public Sub ActualizarEmpresa(e As EmpresaInfo)
            _sis.Db.Execute("UPDATE Empresa SET RazonSocial=@rs, NombreComercial=@nc, Nit=@nit, Direccion=@dir, Ciudad=@ciu, Telefono=@tel, Email=@em, Actividad=@act, RepLegal=@rep, Matricula=@mat, Activa=@a, Observacion=@obs WHERE Id=@i",
                            "rs", e.RazonSocial, "nc", e.NombreComercial, "nit", e.Nit, "dir", e.Direccion, "ciu", e.Ciudad, "tel", e.Telefono,
                            "em", e.Email, "act", e.Actividad, "rep", e.RepLegal, "mat", e.Matricula, "a", If(e.Activa, 1, 0), "obs", e.Observacion, "i", e.Id)
            ' Sincroniza la copia de los datos de la empresa dentro de cada gestión abierta (para encabezados de reportes).
            For Each r As DataRow In _sis.ListarGestiones(e.Id).Rows
                Dim ruta As String = Path.Combine(_sis.RutaDatos, r.GetS("Archivo"))
                If File.Exists(ruta) Then
                    Using db As New Database(_sis.Provider, ruta)
                        SincronizarDatosEmpresa(db, e, r.GetI("Anio"))
                    End Using
                End If
            Next
        End Sub

        Public Shared Sub SincronizarDatosEmpresa(db As Database, e As EmpresaInfo, anio As Integer)
            Dim p As New Parametros(db)
            p.Guardar(ParamKeys.EmpNombre, e.RazonSocial)
            p.Guardar(ParamKeys.EmpNit, e.Nit)
            p.Guardar(ParamKeys.EmpDireccion, e.Direccion)
            p.Guardar(ParamKeys.EmpCiudad, e.Ciudad)
            p.Guardar(ParamKeys.EmpGestion, anio.ToString())
        End Sub

        ''' <summary>Crea una gestión nueva (base de datos vacía con plan de cuentas y parámetros iniciales). No genera apertura.</summary>
        Public Function CrearGestion(e As EmpresaInfo, opc As NuevaGestionOpciones) As Integer
            If opc.Anio < 1990 OrElse opc.Anio > 2200 Then Throw New ArgumentException("Año de gestión inválido.")
            If Not ({1, 4, 7, 10}).Contains(opc.MesInicio) Then Throw New ArgumentException("El mes de inicio debe ser enero, abril, julio u octubre.")
            If _sis.Db.ScalarInt("SELECT COUNT(*) FROM Gestion WHERE EmpresaId=@e AND Anio=@a", "e", e.Id, "a", opc.Anio) > 0 Then
                Throw New InvalidOperationException("La gestión " & opc.Anio & " ya existe para esta empresa.")
            End If
            Dim ini As New Date(opc.Anio, opc.MesInicio, 1)
            Dim fin As Date = ini.AddMonths(12).AddDays(-1)
            Dim rel As String = Path.Combine(e.Carpeta, opc.Anio.ToString(), "conta" & _sis.Provider.Extension)
            Dim abs As String = Path.Combine(_sis.RutaDatos, rel)
            If File.Exists(abs) Then Throw New IOException("Ya existe un archivo de datos en " & abs)
            _sis.Provider.CreateFile(abs)
            Try
                Using db As New Database(_sis.Provider, abs)
                    SchemaInstaller.Install(db, Schemas.Gestion())
                    db.InTx(Sub() Sembrar(db, e, opc, ini))
                End Using
            Catch
                Try
                    _sis.Provider.ReleasePools()
                    If File.Exists(abs) Then File.Delete(abs)
                Catch
                End Try
                Throw
            End Try
            Return _sis.Db.Insert(
                "INSERT INTO Gestion (EmpresaId, Anio, FechaInicio, FechaFin, Archivo, Estado, CorrelativoMensual, MesInicio, EsDefecto, FechaCreacion) VALUES (@e, @a, @i, @f, @ar, 'A', @cm, @mi, 0, @fc)",
                "e", e.Id, "a", opc.Anio, "i", ini, "f", fin, "ar", rel, "cm", If(opc.CorrelativoMensual, 1, 0), "mi", opc.MesInicio, "fc", Date.Today)
        End Function

        Private Sub Sembrar(db As Database, e As EmpresaInfo, opc As NuevaGestionOpciones, ini As Date)
            Dim p As New Parametros(db)
            For Each kv In PlanBase.ParametrosPorDefecto()
                p.Guardar(kv.Key, kv.Value)
            Next
            p.Guardar("CORRELATIVO_MENSUAL", If(opc.CorrelativoMensual, "1", "0"))
            p.Guardar("MES_INICIO", opc.MesInicio.ToString())
            p.Guardar("TC_DEFECTO", opc.TipoCambioInicial.ToString(Inv))
            SincronizarDatosEmpresa(db, e, opc.Anio)

            ' Tipos de comprobante del sistema
            Dim tipos As String() = {"I;Ingreso", "E;Egreso", "T;Traspaso (Diario)", "AP;Apertura", "AJ;Ajuste", "CI;Cierre"}
            For Each t As String In tipos
                Dim a As String() = t.Split(";"c)
                db.Execute("INSERT INTO TipoComprobante (Codigo, Nombre, Sistema, Activo) VALUES (@c, @n, 1, 1)", "c", a(0), "n", a(1))
            Next

            db.Execute("INSERT INTO TipoCambio (Fecha, Usd, Ufv) VALUES (@f, @u, 0)", "f", ini, "u", CDbl(opc.TipoCambioInicial))

            db.Execute("INSERT INTO UnidadMedida (Codigo, Nombre) VALUES ('UND', 'Unidad')")
            db.Execute("INSERT INTO UnidadMedida (Codigo, Nombre) VALUES ('KG', 'Kilogramo')")
            db.Execute("INSERT INTO UnidadMedida (Codigo, Nombre) VALUES ('LT', 'Litro')")
            db.Execute("INSERT INTO UnidadMedida (Codigo, Nombre) VALUES ('MT', 'Metro')")
            db.Execute("INSERT INTO UnidadMedida (Codigo, Nombre) VALUES ('CJA', 'Caja')")
            db.Execute("INSERT INTO UnidadMedida (Codigo, Nombre) VALUES ('DOC', 'Docena')")
            db.Execute("INSERT INTO Almacen (Codigo, Nombre, Direccion, Activo) VALUES ('ALM01', 'Almacén Central', @d, 1)", "d", e.Direccion)
            db.Execute("INSERT INTO Almacen (Codigo, Nombre, Direccion, Activo) VALUES ('PROD', 'Almacén de Producción', @d, 1)", "d", e.Direccion)
            db.Execute("INSERT INTO Sucursal (Codigo, Nombre, Direccion, Activa) VALUES ('0', 'Casa Matriz', @d, 1)", "d", e.Direccion)

            If opc.Plantilla = PlantillaPlan.Comercial Then
                CargarPlan(db, PlanBase.Lineas)
                For Each g As String In PlanBase.GruposActivo
                    Dim a As String() = g.Split(";"c)
                    db.Execute("INSERT INTO GrupoActivo (Nombre, VidaUtilAnios, PorcDep, CuentaActivoId, CuentaDepAcumId, CuentaGastoId) VALUES (@n, @v, @p, @a, @d, @g)",
                               "n", a(0), "v", ToInt(a(1)), "p", ToDbl(a(2)), "a", IdCuenta(db, a(3)), "d", IdCuenta(db, a(4)), "g", IdCuenta(db, a(5)))
                Next
            End If
        End Sub

        Private Shared Function IdCuenta(db As Database, codigo As String) As Object
            Dim o As Object = db.Scalar("SELECT Id FROM Cuenta WHERE Codigo=@c", "c", codigo)
            If o Is Nothing Then Return DBNull.Value
            Return ToInt(o)
        End Function

        ''' <summary>Carga un plan de cuentas desde líneas "codigo;nombre;flags" calculando nivel, padre, rubro y naturaleza.</summary>
        Public Shared Sub CargarPlan(db As Database, lineas As IEnumerable(Of String))
            Dim items As New List(Of Tuple(Of String, String, String))
            For Each l As String In lineas
                If String.IsNullOrWhiteSpace(l) Then Continue For
                Dim a As String() = l.Split(";"c)
                items.Add(Tuple.Create(a(0).Trim(), a(1).Trim(), If(a.Length > 2, a(2).Trim().ToUpperInvariant(), "")))
            Next
            Dim codigos As New HashSet(Of String)(items.Select(Function(t) t.Item1))
            Dim ids As New Dictionary(Of String, Integer)
            ' Los padres siempre preceden a los hijos al ordenar por código.
            For Each it In items.OrderBy(Function(t) t.Item1, StringComparer.Ordinal)
                Dim cod As String = it.Item1
                Dim padre As String = PadreDe(cod, codigos)
                Dim hijos As Boolean = items.Any(Function(t) t.Item1 <> cod AndAlso EsDescendiente(t.Item1, cod))
                Dim flags As String = it.Item3
                Dim rubro As Integer = ToInt(cod.Substring(0, 1))
                Dim nat As String = If(rubro = 1 OrElse rubro = 5 OrElse rubro = 6, "D", "A")
                If flags.Contains("-"c) Then nat = If(nat = "D", "A", "D")
                Dim nivel As Integer = NivelDe(cod, codigos)
                Dim pid As Object = DBNull.Value
                If padre <> "" Then pid = ids(padre)
                Dim costo As String = ""
                If flags.Contains("F"c) Then costo = "F"
                If flags.Contains("V"c) Then costo = "V"
                Dim id As Integer = db.Insert(
                    "INSERT INTO Cuenta (Codigo, Nombre, Nivel, PadreId, Rubro, Naturaleza, EsMovimiento, Moneda, Ajustable, Presupuestable, CostoTipo, EsBanco, Activa) " &
                    "VALUES (@c, @n, @nv, @p, @r, @na, @m, @mo, @aj, @pr, @ct, @b, 1)",
                    "c", cod, "n", it.Item2, "nv", nivel, "p", pid, "r", rubro, "na", nat, "m", If(hijos, 0, 1),
                    "mo", If(flags.Contains("U"c), "USD", "BS"), "aj", If(flags.Contains("A"c), 1, 0), "pr", If(flags.Contains("P"c), 1, 0),
                    "ct", costo, "b", If(flags.Contains("B"c), 1, 0))
                ids(cod) = id
            Next
        End Sub

        Public Shared Function EsDescendiente(hijo As String, padre As String) As Boolean
            If hijo.Length <= padre.Length OrElse Not hijo.StartsWith(padre, StringComparison.Ordinal) Then Return False
            If hijo.Contains("."c) Then Return hijo(padre.Length) = "."c
            Return True
        End Function

        Public Shared Function PadreDe(cod As String, codigos As HashSet(Of String)) As String
            Dim mejor As String = ""
            For Each c As String In codigos
                If c <> cod AndAlso EsDescendiente(cod, c) AndAlso c.Length > mejor.Length Then mejor = c
            Next
            Return mejor
        End Function

        Private Shared Function NivelDe(cod As String, codigos As HashSet(Of String)) As Integer
            Dim n As Integer = 1
            Dim p As String = PadreDe(cod, codigos)
            While p <> ""
                n += 1
                p = PadreDe(p, codigos)
            End While
            Return n
        End Function

        Public Sub EliminarEmpresa(empresaId As Integer, borrarArchivos As Boolean)
            Dim emp As EmpresaInfo = _sis.ObtenerEmpresa(empresaId)
            If emp Is Nothing Then Return
            Dim gests As DataTable = _sis.ListarGestiones(empresaId)
            _sis.Db.InTx(Sub()
                             _sis.Db.Execute("DELETE FROM Permiso WHERE EmpresaId=@e", "e", empresaId)
                             _sis.Db.Execute("DELETE FROM UsuarioEmpresa WHERE EmpresaId=@e", "e", empresaId)
                             _sis.Db.Execute("DELETE FROM Gestion WHERE EmpresaId=@e", "e", empresaId)
                             _sis.Db.Execute("DELETE FROM Empresa WHERE Id=@e", "e", empresaId)
                         End Sub)
            If borrarArchivos Then
                _sis.Provider.ReleasePools()
                Dim carpeta As String = Path.Combine(_sis.RutaDatos, emp.Carpeta)
                If Directory.Exists(carpeta) Then Directory.Delete(carpeta, True)
            End If
        End Sub

    End Class

End Namespace
