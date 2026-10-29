Imports System.IO
Imports System.IO.Compression
Imports System.Security.Cryptography
Imports System.Text.Json
Imports System.Text.Json.Nodes
Imports System.Text.Json.Serialization.Metadata
Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    Public Class BackupInfo
        Public Property Archivo As String
        Public Property Fecha As Date
        Public Property Tipo As String
        Public Property EmpresaCodigo As String
        Public Property EmpresaNombre As String
        Public Property Gestiones As String
        Public Property TamanoMb As Double
        Public Property Valido As Boolean
        Public Property Mensaje As String
    End Class

    ''' <summary>
    ''' Copias de seguridad comprimidas (.cbk = ZIP con manifiesto y huellas SHA-256) y restauración.
    ''' Cada copia de empresa incluye todas sus gestiones y los accesos de usuarios para poder recuperarla en otro equipo.
    ''' </summary>
    Public Class BackupService
        Public Const Extension As String = ".cbk"
        Private Const Formato As String = "ContaBol-Backup"
        Private ReadOnly _sis As SistemaService

        Public Sub New(sis As SistemaService)
            _sis = sis
        End Sub

        Private Shared Function OpcionesJson() As JsonSerializerOptions
            Return New JsonSerializerOptions With {.WriteIndented = True, .TypeInfoResolver = New DefaultJsonTypeInfoResolver()}
        End Function

        Private Shared Function Huella(path As String) As String
            Using fs As New FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)
                Using h As SHA256 = SHA256.Create()
                    Return Convert.ToHexString(h.ComputeHash(fs))
                End Using
            End Using
        End Function

        Private Shared Sub AgregarArchivo(zip As ZipArchive, origen As String, nombreEnZip As String)
            Dim e As ZipArchiveEntry = zip.CreateEntry(nombreEnZip.Replace("\"c, "/"c), CompressionLevel.Optimal)
            Using dst As Stream = e.Open()
                Using src As New FileStream(origen, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)
                    src.CopyTo(dst)
                End Using
            End Using
        End Sub

        Private Function DestinoPor(destino As String) As String
            Dim d As String = If(String.IsNullOrWhiteSpace(destino), _sis.RutaBackups, destino)
            Directory.CreateDirectory(d)
            Return d
        End Function

        ''' <summary>Copia de seguridad de una empresa (todas sus gestiones). Devuelve la ruta del archivo creado.</summary>
        Public Function BackupEmpresa(empresaId As Integer, Optional destino As String = "", Optional nota As String = "", Optional prefijo As String = "") As String
            Dim emp As EmpresaInfo = _sis.ObtenerEmpresa(empresaId)
            If emp Is Nothing Then Throw New InvalidOperationException("Empresa inexistente.")
            _sis.Provider.ReleasePools()
            Dim ruta As String = Path.Combine(DestinoPor(destino), prefijo & "ContaBol_" & emp.Codigo & "_" & Date.Now.ToString("yyyyMMdd_HHmmss") & Extension)
            Dim manifest As New JsonObject()
            manifest("formato") = Formato
            manifest("version") = 1
            manifest("tipo") = "EMPRESA"
            manifest("fecha") = Date.Now.ToString("o")
            manifest("esquema") = Schemas.VersionEsquema
            manifest("nota") = nota
            Dim jEmp As New JsonObject()
            jEmp("codigo") = emp.Codigo : jEmp("razonSocial") = emp.RazonSocial : jEmp("nombreComercial") = emp.NombreComercial
            jEmp("nit") = emp.Nit : jEmp("direccion") = emp.Direccion : jEmp("ciudad") = emp.Ciudad : jEmp("telefono") = emp.Telefono
            jEmp("email") = emp.Email : jEmp("actividad") = emp.Actividad : jEmp("repLegal") = emp.RepLegal : jEmp("matricula") = emp.Matricula
            jEmp("carpeta") = emp.Carpeta : jEmp("observacion") = emp.Observacion
            manifest("empresa") = jEmp
            Dim jGes As New JsonArray()
            Dim archivos As New List(Of Tuple(Of String, String))
            For Each g As DataRow In _sis.ListarGestiones(empresaId).Rows
                Dim abs As String = Path.Combine(_sis.RutaDatos, g.GetS("Archivo"))
                If Not File.Exists(abs) Then Continue For
                Dim jg As New JsonObject()
                jg("anio") = g.GetI("Anio") : jg("archivo") = g.GetS("Archivo") : jg("estado") = g.GetS("Estado")
                jg("correlativoMensual") = g.GetF("CorrelativoMensual") : jg("mesInicio") = g.GetI("MesInicio")
                jg("fechaInicio") = g.GetDt("FechaInicio").ToString("yyyy-MM-dd") : jg("fechaFin") = g.GetDt("FechaFin").ToString("yyyy-MM-dd")
                jg("sha256") = Huella(abs)
                jg("bytes") = New FileInfo(abs).Length
                jGes.Add(jg)
                archivos.Add(Tuple.Create(abs, "datos/" & g.GetS("Archivo")))
            Next
            manifest("gestiones") = jGes
            Dim jUsr As New JsonArray()
            For Each r As DataRow In _sis.Db.Query("SELECT u.*, ue.Rol FROM Usuario u INNER JOIN UsuarioEmpresa ue ON ue.UsuarioId = u.Id WHERE ue.EmpresaId=@e", "e", empresaId).Rows
                Dim ju As New JsonObject()
                ju("login") = r.GetS("Login") : ju("nombre") = r.GetS("Nombre") : ju("hash") = r.GetS("Hash") : ju("salt") = r.GetS("Salt")
                ju("esAdmin") = r.GetF("EsAdmin") : ju("activo") = r.GetF("Activo") : ju("rol") = r.GetS("Rol") : ju("email") = r.GetS("Email")
                Dim jp As New JsonArray()
                For Each p As String In _sis.PermisosDe(r.GetI("Id"), empresaId)
                    jp.Add(p)
                Next
                ju("permisos") = jp
                jUsr.Add(ju)
            Next
            manifest("usuarios") = jUsr
            If archivos.Count = 0 Then Throw New InvalidOperationException("La empresa no tiene archivos de datos para respaldar.")
            Using zfs As New FileStream(ruta, FileMode.CreateNew)
                Using zip As New ZipArchive(zfs, ZipArchiveMode.Create)
                    Dim me1 As ZipArchiveEntry = zip.CreateEntry("manifest.json")
                    Using w As New StreamWriter(me1.Open(), New Text.UTF8Encoding(False))
                        w.Write(manifest.ToJsonString(OpcionesJson()))
                    End Using
                    For Each a In archivos
                        AgregarArchivo(zip, a.Item1, a.Item2)
                    Next
                End Using
            End Using
            Try
                _sis.Db.Execute("INSERT INTO RegistroBackup (Fecha, Tipo, Archivo, EmpresaId, Resultado, TamanoMb) VALUES (@f, 'EMPRESA', @a, @e, 'OK', @t)",
                                "f", Date.Now, "a", ruta, "e", empresaId, "t", Math.Round(New FileInfo(ruta).Length / 1048576.0, 2))
            Catch
            End Try
            Return ruta
        End Function

        ''' <summary>Copia total: base de datos del sistema y todas las empresas/gestiones.</summary>
        Public Function BackupTotal(Optional destino As String = "", Optional nota As String = "") As String
            _sis.Provider.ReleasePools()
            Dim ruta As String = Path.Combine(DestinoPor(destino), "ContaBol_TOTAL_" & Date.Now.ToString("yyyyMMdd_HHmmss") & Extension)
            Dim manifest As New JsonObject()
            manifest("formato") = Formato : manifest("version") = 1 : manifest("tipo") = "TOTAL"
            manifest("fecha") = Date.Now.ToString("o") : manifest("esquema") = Schemas.VersionEsquema : manifest("nota") = nota
            Dim jf As New JsonArray()
            Dim lista As New List(Of Tuple(Of String, String))
            lista.Add(Tuple.Create(_sis.RutaMaestra, Path.GetFileName(_sis.RutaMaestra)))
            If Directory.Exists(_sis.RutaDatos) Then
                For Each f As String In Directory.GetFiles(_sis.RutaDatos, "*" & _sis.Provider.Extension, SearchOption.AllDirectories)
                    lista.Add(Tuple.Create(f, "Datos/" & Path.GetRelativePath(_sis.RutaDatos, f).Replace("\"c, "/"c)))
                Next
            End If
            For Each a In lista
                Dim j As New JsonObject()
                j("ruta") = a.Item2.Replace("\"c, "/"c)
                j("sha256") = Huella(a.Item1)
                j("bytes") = New FileInfo(a.Item1).Length
                jf.Add(j)
            Next
            manifest("archivos") = jf
            Using zfs As New FileStream(ruta, FileMode.CreateNew)
                Using zip As New ZipArchive(zfs, ZipArchiveMode.Create)
                    Dim me1 As ZipArchiveEntry = zip.CreateEntry("manifest.json")
                    Using w As New StreamWriter(me1.Open(), New Text.UTF8Encoding(False))
                        w.Write(manifest.ToJsonString(OpcionesJson()))
                    End Using
                    For Each a In lista
                        AgregarArchivo(zip, a.Item1, a.Item2)
                    Next
                End Using
            End Using
            Try
                _sis.Db.Execute("INSERT INTO RegistroBackup (Fecha, Tipo, Archivo, EmpresaId, Resultado, TamanoMb) VALUES (@f, 'TOTAL', @a, 0, 'OK', @t)",
                                "f", Date.Now, "a", ruta, "t", Math.Round(New FileInfo(ruta).Length / 1048576.0, 2))
            Catch
            End Try
            Return ruta
        End Function

        Private Shared Function LeerManifiesto(zip As ZipArchive) As JsonNode
            Dim e As ZipArchiveEntry = zip.GetEntry("manifest.json")
            If e Is Nothing Then Throw New InvalidDataException("El archivo no es una copia de seguridad de ContaBol (falta el manifiesto).")
            Using r As New StreamReader(e.Open())
                Dim n As JsonNode = JsonNode.Parse(r.ReadToEnd())
                If n("formato") Is Nothing OrElse n("formato").GetValue(Of String)() <> Formato Then Throw New InvalidDataException("Formato de copia de seguridad desconocido.")
                Return n
            End Using
        End Function

        Private Shared Function HashEntry(e As ZipArchiveEntry) As String
            Using s As Stream = e.Open()
                Using h As SHA256 = SHA256.Create()
                    Return Convert.ToHexString(h.ComputeHash(s))
                End Using
            End Using
        End Function

        ''' <summary>Comprueba la integridad de una copia (todas las huellas SHA-256).</summary>
        Public Function Verificar(rutaCopia As String) As BackupInfo
            Dim info As New BackupInfo With {.Archivo = rutaCopia, .TamanoMb = Math.Round(New FileInfo(rutaCopia).Length / 1048576.0, 2)}
            Try
                Using zip As ZipArchive = ZipFile.OpenRead(rutaCopia)
                    Dim m As JsonNode = LeerManifiesto(zip)
                    info.Tipo = m("tipo").GetValue(Of String)()
                    info.Fecha = DateTime.Parse(m("fecha").GetValue(Of String)(), Inv, Globalization.DateTimeStyles.RoundtripKind)
                    If info.Tipo = "EMPRESA" Then
                        info.EmpresaCodigo = m("empresa")("codigo").GetValue(Of String)()
                        info.EmpresaNombre = m("empresa")("razonSocial").GetValue(Of String)()
                        Dim gs As New List(Of String)
                        For Each g As JsonNode In m("gestiones").AsArray()
                            Dim entry As ZipArchiveEntry = zip.GetEntry("datos/" & g("archivo").GetValue(Of String)().Replace("\"c, "/"c))
                            If entry Is Nothing Then Throw New InvalidDataException("Falta un archivo de datos en la copia (gestión " & g("anio").GetValue(Of Integer)() & ").")
                            If HashEntry(entry) <> g("sha256").GetValue(Of String)() Then Throw New InvalidDataException("La gestión " & g("anio").GetValue(Of Integer)() & " está dañada (huella SHA-256 distinta).")
                            gs.Add(g("anio").GetValue(Of Integer)().ToString())
                        Next
                        info.Gestiones = String.Join(", ", gs)
                    Else
                        For Each f As JsonNode In m("archivos").AsArray()
                            Dim entry As ZipArchiveEntry = zip.GetEntry(f("ruta").GetValue(Of String)())
                            If entry Is Nothing Then Throw New InvalidDataException("Falta el archivo " & f("ruta").GetValue(Of String)())
                            If HashEntry(entry) <> f("sha256").GetValue(Of String)() Then Throw New InvalidDataException("El archivo " & f("ruta").GetValue(Of String)() & " está dañado.")
                        Next
                        info.EmpresaNombre = "(Copia total del sistema)"
                    End If
                    info.Valido = True
                    info.Mensaje = "Copia íntegra"
                End Using
            Catch ex As Exception
                info.Valido = False
                info.Mensaje = ex.Message
            End Try
            Return info
        End Function

        ''' <summary>
        ''' Restaura una copia de empresa. Si la empresa ya existe sus datos se reemplazan (se hace antes una copia de seguridad de lo actual).
        ''' Con nuevoCodigo se restaura como una empresa distinta (útil para pruebas o clonar).
        ''' </summary>
        Public Function RestaurarEmpresa(rutaCopia As String, Optional nuevoCodigo As String = "") As Integer
            Dim v As BackupInfo = Verificar(rutaCopia)
            If Not v.Valido Then Throw New InvalidDataException("La copia no es válida: " & v.Mensaje)
            If v.Tipo <> "EMPRESA" Then Throw New InvalidOperationException("Esta es una copia total del sistema. Restáurela desde la pantalla de inicio (Restaurar copia total).")
            Using zip As ZipArchive = ZipFile.OpenRead(rutaCopia)
                Dim m As JsonNode = LeerManifiesto(zip)
                Dim je As JsonNode = m("empresa")
                Dim codigo As String = If(String.IsNullOrWhiteSpace(nuevoCodigo), je("codigo").GetValue(Of String)(), nuevoCodigo.Trim().ToUpperInvariant())
                Dim carpeta As String = EmpresaService.CarpetaSegura(codigo)
                Dim existente As DataTable = _sis.Db.Query("SELECT Id FROM Empresa WHERE Codigo=@c", "c", codigo)
                Dim empresaId As Integer = 0
                If existente.Rows.Count > 0 Then
                    empresaId = existente.Rows(0).GetI("Id")
                    ' copia de seguridad previa de lo que se va a reemplazar
                    Try
                        BackupEmpresa(empresaId, "", "Antes de restaurar", "PRE-RESTAURACION_")
                    Catch
                    End Try
                End If
                _sis.Provider.ReleasePools()
                Dim carpetaOrigen As String = je("carpeta").GetValue(Of String)()
                Dim escritos As New List(Of String)
                Try
                    For Each g As JsonNode In m("gestiones").AsArray()
                        Dim rel As String = g("archivo").GetValue(Of String)()
                        Dim relDestino As String = rel
                        If carpeta <> carpetaOrigen Then relDestino = Path.Combine(carpeta, g("anio").GetValue(Of Integer)().ToString(), Path.GetFileName(rel))
                        Dim destino As String = Path.Combine(_sis.RutaDatos, relDestino)
                        Directory.CreateDirectory(Path.GetDirectoryName(destino))
                        Dim entry As ZipArchiveEntry = zip.GetEntry("datos/" & rel.Replace("\"c, "/"c))
                        Dim tmp As String = destino & ".restore.tmp"
                        If File.Exists(tmp) Then File.Delete(tmp)
                        entry.ExtractToFile(tmp, True)
                        If Huella(tmp) <> g("sha256").GetValue(Of String)() Then Throw New InvalidDataException("La verificación posterior a la extracción falló.")
                        If File.Exists(destino) Then File.Delete(destino)
                        File.Move(tmp, destino)
                        escritos.Add(destino)
                    Next
                Catch
                    Throw
                End Try
                _sis.Db.InTx(Sub()
                                 If empresaId = 0 Then
                                     empresaId = _sis.Db.Insert("INSERT INTO Empresa (Codigo, RazonSocial, NombreComercial, Nit, Direccion, Ciudad, Telefono, Email, Actividad, RepLegal, Matricula, Carpeta, FechaCreacion, Activa, EsDefecto, Observacion) VALUES (@c, @rs, @nc, @nit, @d, @ci, @t, @e, @a, @r, @ma, @ca, @fc, 1, 0, @o)",
                                         "c", codigo, "rs", S(je, "razonSocial"), "nc", S(je, "nombreComercial"), "nit", S(je, "nit"), "d", S(je, "direccion"), "ci", S(je, "ciudad"), "t", S(je, "telefono"),
                                         "e", S(je, "email"), "a", S(je, "actividad"), "r", S(je, "repLegal"), "ma", S(je, "matricula"), "ca", carpeta, "fc", Date.Today, "o", "Restaurada desde copia " & Path.GetFileName(rutaCopia))
                                 End If
                                 For Each g As JsonNode In m("gestiones").AsArray()
                                     Dim rel As String = g("archivo").GetValue(Of String)()
                                     If carpeta <> carpetaOrigen Then rel = Path.Combine(carpeta, g("anio").GetValue(Of Integer)().ToString(), Path.GetFileName(rel))
                                     Dim anio As Integer = g("anio").GetValue(Of Integer)()
                                     Dim n As Integer = _sis.Db.Execute("UPDATE Gestion SET Archivo=@a, Estado=@e, CorrelativoMensual=@cm, MesInicio=@mi, FechaInicio=@fi, FechaFin=@ff WHERE EmpresaId=@emp AND Anio=@an",
                                         "a", rel, "e", g("estado").GetValue(Of String)(), "cm", If(g("correlativoMensual").GetValue(Of Boolean)(), 1, 0), "mi", g("mesInicio").GetValue(Of Integer)(),
                                         "fi", DateTime.Parse(g("fechaInicio").GetValue(Of String)(), Inv), "ff", DateTime.Parse(g("fechaFin").GetValue(Of String)(), Inv), "emp", empresaId, "an", anio)
                                     If n = 0 Then
                                         _sis.Db.Execute("INSERT INTO Gestion (EmpresaId, Anio, FechaInicio, FechaFin, Archivo, Estado, CorrelativoMensual, MesInicio, EsDefecto, FechaCreacion) VALUES (@emp, @an, @fi, @ff, @a, @e, @cm, @mi, 0, @fc)",
                                             "emp", empresaId, "an", anio, "fi", DateTime.Parse(g("fechaInicio").GetValue(Of String)(), Inv), "ff", DateTime.Parse(g("fechaFin").GetValue(Of String)(), Inv), "a", rel,
                                             "e", g("estado").GetValue(Of String)(), "cm", If(g("correlativoMensual").GetValue(Of Boolean)(), 1, 0), "mi", g("mesInicio").GetValue(Of Integer)(), "fc", Date.Today)
                                     End If
                                 Next
                                 ' accesos de usuarios
                                 If m("usuarios") IsNot Nothing Then
                                     For Each u As JsonNode In m("usuarios").AsArray()
                                         Dim login As String = u("login").GetValue(Of String)()
                                         Dim ex As DataTable = _sis.Db.Query("SELECT Id FROM Usuario WHERE Login=@l", "l", login)
                                         Dim uid As Integer
                                         If ex.Rows.Count = 0 Then
                                             uid = _sis.Db.Insert("INSERT INTO Usuario (Login, Nombre, Hash, Salt, Activo, EsAdmin, CambiarClave, Email, Intentos) VALUES (@l, @n, @h, @s, @a, @ad, 0, @e, 0)",
                                                 "l", login, "n", S(u, "nombre"), "h", S(u, "hash"), "s", S(u, "salt"), "a", If(u("activo").GetValue(Of Boolean)(), 1, 0), "ad", If(u("esAdmin").GetValue(Of Boolean)(), 1, 0), "e", S(u, "email"))
                                         Else
                                             uid = ex.Rows(0).GetI("Id")
                                         End If
                                         If _sis.Db.ScalarInt("SELECT COUNT(*) FROM UsuarioEmpresa WHERE UsuarioId=@u AND EmpresaId=@e", "u", uid, "e", empresaId) = 0 Then
                                             _sis.Db.Execute("INSERT INTO UsuarioEmpresa (UsuarioId, EmpresaId, Rol) VALUES (@u, @e, @r)", "u", uid, "e", empresaId, "r", S(u, "rol"))
                                             For Each p As JsonNode In u("permisos").AsArray()
                                                 _sis.Db.Execute("INSERT INTO Permiso (UsuarioId, EmpresaId, Opcion) VALUES (@u, @e, @o)", "u", uid, "e", empresaId, "o", p.GetValue(Of String)())
                                             Next
                                         End If
                                     Next
                                 End If
                             End Sub)
                _sis.Auditar(0, "", empresaId, 0, "Administración", "RESTAURAR_EMPRESA", Path.GetFileName(rutaCopia))
                Return empresaId
            End Using
        End Function

        Private Shared Function S(n As JsonNode, clave As String) As String
            If n(clave) Is Nothing Then Return ""
            Return n(clave).GetValue(Of String)()
        End Function

        ''' <summary>Restaura una copia total reemplazando la carpeta de datos. Debe ejecutarse sin el sistema abierto (antes de iniciar sesión).</summary>
        Public Shared Sub RestaurarTotal(provider As IDbProvider, rutaRaiz As String, rutaCopia As String)
            Dim temp As SistemaService = Nothing
            Using zip As ZipArchive = ZipFile.OpenRead(rutaCopia)
                Dim m As JsonNode = LeerManifiesto(zip)
                If m("tipo").GetValue(Of String)() <> "TOTAL" Then Throw New InvalidOperationException("La copia no es una copia total.")
                For Each f As JsonNode In m("archivos").AsArray()
                    Dim e As ZipArchiveEntry = zip.GetEntry(f("ruta").GetValue(Of String)())
                    If e Is Nothing OrElse HashEntry(e) <> f("sha256").GetValue(Of String)() Then Throw New InvalidDataException("La copia está dañada: " & f("ruta").GetValue(Of String)())
                Next
                provider.ReleasePools()
                ' respaldo de seguridad de lo existente
                If Directory.Exists(rutaRaiz) AndAlso Directory.GetFiles(rutaRaiz, "*" & provider.Extension, SearchOption.AllDirectories).Length > 0 Then
                    Dim seg As String = Path.Combine(rutaRaiz, "Backups")
                    Directory.CreateDirectory(seg)
                    Dim zp As String = Path.Combine(seg, "PRE-RESTAURACION_TOTAL_" & Date.Now.ToString("yyyyMMdd_HHmmss") & Extension)
                    Using zfs As New FileStream(zp, FileMode.CreateNew)
                        Using z As New ZipArchive(zfs, ZipArchiveMode.Create)
                            For Each f As String In Directory.GetFiles(rutaRaiz, "*" & provider.Extension, SearchOption.AllDirectories)
                                AgregarArchivo(z, f, Path.GetRelativePath(rutaRaiz, f))
                            Next
                        End Using
                    End Using
                End If
                For Each f As JsonNode In m("archivos").AsArray()
                    Dim destino As String = Path.Combine(rutaRaiz, f("ruta").GetValue(Of String)().Replace("/"c, Path.DirectorySeparatorChar))
                    Directory.CreateDirectory(Path.GetDirectoryName(destino))
                    zip.GetEntry(f("ruta").GetValue(Of String)()).ExtractToFile(destino, True)
                Next
            End Using
        End Sub

        Public Function Listar() As List(Of BackupInfo)
            Dim res As New List(Of BackupInfo)
            If Not Directory.Exists(_sis.RutaBackups) Then Return res
            For Each f As String In Directory.GetFiles(_sis.RutaBackups, "*" & Extension)
                Dim fi As New FileInfo(f)
                res.Add(New BackupInfo With {.Archivo = f, .Fecha = fi.LastWriteTime, .TamanoMb = Math.Round(fi.Length / 1048576.0, 2), .Tipo = If(fi.Name.Contains("_TOTAL_"), "TOTAL", "EMPRESA"), .EmpresaCodigo = fi.Name})
            Next
            Return res.OrderByDescending(Function(x) x.Fecha).ToList()
        End Function

        ''' <summary>Conserva solo las últimas N copias de cada empresa.</summary>
        Public Function Depurar(mantener As Integer) As Integer
            Dim borrados As Integer = 0
            If mantener < 1 Then Return 0
            Dim grupos = Listar().GroupBy(Function(b) If(b.Tipo = "TOTAL", "TOTAL", b.EmpresaCodigo.Split("_"c).Skip(1).FirstOrDefault()))
            For Each g In grupos
                For Each b In g.OrderByDescending(Function(x) x.Fecha).Skip(mantener)
                    Try
                        File.Delete(b.Archivo)
                        borrados += 1
                    Catch
                    End Try
                Next
            Next
            Return borrados
        End Function

    End Class

End Namespace
