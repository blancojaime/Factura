Imports System.IO
Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    ''' <summary>
    ''' Base de datos maestra del sistema: empresas, gestiones, usuarios, permisos y auditoría.
    ''' Es el punto de entrada multiempresa: desde aquí se abren las bases de datos de cada empresa/gestión.
    ''' </summary>
    Public Class SistemaService
        Implements IDisposable

        Public ReadOnly Property Provider As IDbProvider
        Public ReadOnly Property RutaRaiz As String
        Public ReadOnly Property Db As Database

        Public Const NombreMaestra As String = "Sistema"

        Private Sub New(provider As IDbProvider, ruta As String, db As Database)
            Me.Provider = provider
            Me.RutaRaiz = ruta
            Me.Db = db
        End Sub

        Public ReadOnly Property RutaMaestra As String
            Get
                Return Path.Combine(RutaRaiz, NombreMaestra & Provider.Extension)
            End Get
        End Property

        Public ReadOnly Property RutaDatos As String
            Get
                Return Path.Combine(RutaRaiz, "Datos")
            End Get
        End Property

        Public ReadOnly Property RutaBackups As String
            Get
                Return Path.Combine(RutaRaiz, "Backups")
            End Get
        End Property

        ''' <summary>Abre (o crea la primera vez) el sistema en la carpeta indicada.</summary>
        Public Shared Function Abrir(provider As IDbProvider, rutaRaiz As String) As SistemaService
            Directory.CreateDirectory(rutaRaiz)
            Directory.CreateDirectory(Path.Combine(rutaRaiz, "Datos"))
            Directory.CreateDirectory(Path.Combine(rutaRaiz, "Backups"))
            Dim archivo As String = Path.Combine(rutaRaiz, NombreMaestra & provider.Extension)
            Dim nuevo As Boolean = Not File.Exists(archivo)
            If Not nuevo Then
                ' Un intento anterior fallido puede haber dejado un archivo sin tablas: se recrea.
                Dim incompleto As Boolean
                Using chk As New Database(provider, archivo)
                    incompleto = Not chk.TableExists("Usuario")
                End Using
                If incompleto Then
                    provider.ReleasePools()
                    File.Delete(archivo)
                    nuevo = True
                End If
            End If
            If nuevo Then provider.CreateFile(archivo)
            Dim db As New Database(provider, archivo)
            Dim s As New SistemaService(provider, rutaRaiz, db)
            If nuevo Then
                SchemaInstaller.Install(db, Schemas.Maestra())
                s.SetConfig("SchemaVersion", Schemas.VersionEsquema.ToString())
                s.SembrarAdmin()
            End If
            Return s
        End Function

        Private Sub SembrarAdmin()
            Dim sal As String = NuevaSal()
            Db.Execute("INSERT INTO Usuario (Login, Nombre, Hash, Salt, Activo, EsAdmin, CambiarClave, Intentos) VALUES (@l, @n, @h, @s, 1, 1, 1, 0)",
                       "l", "admin", "n", "Administrador del Sistema", "h", HashClave("admin", sal), "s", sal)
        End Sub

        ' ---------- Configuración global ----------
        Public Function GetConfig(clave As String, Optional defecto As String = "") As String
            Dim o As Object = Db.Scalar("SELECT Valor FROM ConfigGlobal WHERE Clave=@k", "k", clave)
            If o Is Nothing Then Return defecto
            Return ToStr(o)
        End Function

        Public Sub SetConfig(clave As String, valor As String)
            Dim n As Integer = Db.Execute("UPDATE ConfigGlobal SET Valor=@v WHERE Clave=@k", "v", If(valor, ""), "k", clave)
            If n = 0 Then Db.Execute("INSERT INTO ConfigGlobal (Clave, Valor) VALUES (@k, @v)", "k", clave, "v", If(valor, ""))
        End Sub

        ' ---------- Usuarios ----------
        Public Function Autenticar(login As String, clave As String) As UsuarioInfo
            Dim dt As DataTable = Db.Query("SELECT * FROM Usuario WHERE Login=@l", "l", If(login, "").Trim())
            If dt.Rows.Count = 0 Then Throw New UnauthorizedAccessException("Usuario o contraseña incorrectos.")
            Dim r As DataRow = dt.Rows(0)
            If Not r.GetF("Activo") Then Throw New UnauthorizedAccessException("El usuario está inactivo. Consulte con el administrador.")
            If r.GetI("Intentos") >= 5 Then Throw New UnauthorizedAccessException("Usuario bloqueado por intentos fallidos. El administrador debe restablecer la contraseña.")
            If Not Verificar(If(clave, ""), r.GetS("Salt"), r.GetS("Hash")) Then
                Db.Execute("UPDATE Usuario SET Intentos = Intentos + 1 WHERE Id=@i", "i", r.GetI("Id"))
                Auditar(r.GetI("Id"), r.GetS("Login"), 0, 0, "Seguridad", "LOGIN_FALLIDO", "Contraseña incorrecta")
                Throw New UnauthorizedAccessException("Usuario o contraseña incorrectos.")
            End If
            Db.Execute("UPDATE Usuario SET Intentos = 0, UltimoAcceso=@d WHERE Id=@i", "d", Date.Now, "i", r.GetI("Id"))
            Auditar(r.GetI("Id"), r.GetS("Login"), 0, 0, "Seguridad", "LOGIN", "Ingreso al sistema")
            Return LeerUsuario(r)
        End Function

        Private Shared Function LeerUsuario(r As DataRow) As UsuarioInfo
            Return New UsuarioInfo With {
                .Id = r.GetI("Id"), .Login = r.GetS("Login"), .Nombre = r.GetS("Nombre"), .Email = r.GetS("Email"),
                .Activo = r.GetF("Activo"), .EsAdmin = r.GetF("EsAdmin"), .CambiarClave = r.GetF("CambiarClave"),
                .UltimoAcceso = ToDateOrNull(r.Cell("UltimoAcceso"))}
        End Function

        Public Function ListarUsuarios() As DataTable
            Return Db.Query("SELECT Id, Login, Nombre, Email, Activo, EsAdmin, UltimoAcceso, Intentos FROM Usuario ORDER BY Login")
        End Function

        Public Function ObtenerUsuario(id As Integer) As UsuarioInfo
            Dim dt As DataTable = Db.Query("SELECT * FROM Usuario WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Return LeerUsuario(dt.Rows(0))
        End Function

        Public Function CrearUsuario(login As String, nombre As String, clave As String, esAdmin As Boolean, Optional email As String = "") As Integer
            login = If(login, "").Trim()
            If login.Length < 3 Then Throw New ArgumentException("El usuario debe tener al menos 3 caracteres.")
            ValidarClave(clave)
            If Db.ScalarInt("SELECT COUNT(*) FROM Usuario WHERE Login=@l", "l", login) > 0 Then Throw New InvalidOperationException("Ya existe un usuario con ese nombre.")
            Dim sal As String = NuevaSal()
            Return Db.Insert("INSERT INTO Usuario (Login, Nombre, Hash, Salt, Activo, EsAdmin, CambiarClave, Email, Intentos) VALUES (@l, @n, @h, @s, 1, @a, 0, @e, 0)",
                             "l", login, "n", nombre, "h", HashClave(clave, sal), "s", sal, "a", If(esAdmin, 1, 0), "e", email)
        End Function

        Public Sub ActualizarUsuario(id As Integer, nombre As String, email As String, activo As Boolean, esAdmin As Boolean)
            Db.Execute("UPDATE Usuario SET Nombre=@n, Email=@e, Activo=@a, EsAdmin=@ad WHERE Id=@i",
                       "n", nombre, "e", email, "a", If(activo, 1, 0), "ad", If(esAdmin, 1, 0), "i", id)
        End Sub

        Public Shared Sub ValidarClave(clave As String)
            If String.IsNullOrEmpty(clave) OrElse clave.Length < 4 Then Throw New ArgumentException("La contraseña debe tener al menos 4 caracteres.")
        End Sub

        Public Sub CambiarClave(id As Integer, nueva As String, Optional forzarCambio As Boolean = False)
            ValidarClave(nueva)
            Dim sal As String = NuevaSal()
            Db.Execute("UPDATE Usuario SET Hash=@h, Salt=@s, CambiarClave=@c, Intentos=0 WHERE Id=@i",
                       "h", HashClave(nueva, sal), "s", sal, "c", If(forzarCambio, 1, 0), "i", id)
        End Sub

        Public Sub EliminarUsuario(id As Integer)
            Dim u As UsuarioInfo = ObtenerUsuario(id)
            If u Is Nothing Then Return
            If u.Login.Equals("admin", StringComparison.OrdinalIgnoreCase) Then Throw New InvalidOperationException("El usuario 'admin' no se puede eliminar.")
            Db.InTx(Sub()
                        Db.Execute("DELETE FROM Permiso WHERE UsuarioId=@i", "i", id)
                        Db.Execute("DELETE FROM UsuarioEmpresa WHERE UsuarioId=@i", "i", id)
                        Db.Execute("DELETE FROM Usuario WHERE Id=@i", "i", id)
                    End Sub)
        End Sub

        ' ---------- Acceso por empresa ----------
        Public Function EmpresasDeUsuario(u As UsuarioInfo) As DataTable
            If u.EsAdmin Then
                Return Db.Query("SELECT * FROM Empresa WHERE Activa=1 ORDER BY RazonSocial")
            End If
            Dim dt As DataTable = Db.Query("SELECT e.* FROM Empresa e INNER JOIN UsuarioEmpresa ue ON ue.EmpresaId = e.Id WHERE e.Activa=1 AND ue.UsuarioId=@u ORDER BY e.RazonSocial", "u", u.Id)
            Return dt
        End Function

        Public Function RolDe(usuarioId As Integer, empresaId As Integer) As String
            Return Db.ScalarStr("SELECT Rol FROM UsuarioEmpresa WHERE UsuarioId=@u AND EmpresaId=@e", "u", usuarioId, "e", empresaId)
        End Function

        ''' <summary>Otorga acceso a una empresa con un rol; los permisos del rol se copian y luego pueden ajustarse.</summary>
        Public Sub AsignarEmpresa(usuarioId As Integer, empresaId As Integer, rol As String)
            Db.InTx(Sub()
                        Dim n As Integer = Db.Execute("UPDATE UsuarioEmpresa SET Rol=@r WHERE UsuarioId=@u AND EmpresaId=@e", "r", rol, "u", usuarioId, "e", empresaId)
                        If n = 0 Then Db.Execute("INSERT INTO UsuarioEmpresa (UsuarioId, EmpresaId, Rol) VALUES (@u, @e, @r)", "u", usuarioId, "e", empresaId, "r", rol)
                        EstablecerPermisos(usuarioId, empresaId, Permisos.PorRol(rol))
                    End Sub)
        End Sub

        Public Sub QuitarEmpresa(usuarioId As Integer, empresaId As Integer)
            Db.InTx(Sub()
                        Db.Execute("DELETE FROM Permiso WHERE UsuarioId=@u AND EmpresaId=@e", "u", usuarioId, "e", empresaId)
                        Db.Execute("DELETE FROM UsuarioEmpresa WHERE UsuarioId=@u AND EmpresaId=@e", "u", usuarioId, "e", empresaId)
                    End Sub)
        End Sub

        Public Function PermisosDe(usuarioId As Integer, empresaId As Integer) As HashSet(Of String)
            Dim h As New HashSet(Of String)(StringComparer.OrdinalIgnoreCase)
            For Each r As DataRow In Db.Query("SELECT Opcion FROM Permiso WHERE UsuarioId=@u AND EmpresaId=@e", "u", usuarioId, "e", empresaId).Rows
                h.Add(r.GetS("Opcion"))
            Next
            Return h
        End Function

        Public Sub EstablecerPermisos(usuarioId As Integer, empresaId As Integer, opciones As IEnumerable(Of String))
            Db.InTx(Sub()
                        Db.Execute("DELETE FROM Permiso WHERE UsuarioId=@u AND EmpresaId=@e", "u", usuarioId, "e", empresaId)
                        For Each o As String In opciones.Distinct()
                            Db.Execute("INSERT INTO Permiso (UsuarioId, EmpresaId, Opcion) VALUES (@u, @e, @o)", "u", usuarioId, "e", empresaId, "o", o)
                        Next
                    End Sub)
        End Sub

        ' ---------- Auditoría ----------
        Public Sub Auditar(usuarioId As Integer, login As String, empresaId As Integer, gestionId As Integer, modulo As String, accion As String, detalle As String)
            Db.Execute("INSERT INTO Auditoria (Fecha, UsuarioId, Login, EmpresaId, GestionId, Modulo, Accion, Detalle, Equipo) VALUES (@f, @u, @l, @e, @g, @m, @a, @d, @q)",
                       "f", Date.Now, "u", usuarioId, "l", login, "e", empresaId, "g", gestionId, "m", modulo, "a", accion,
                       "d", If(detalle IsNot Nothing AndAlso detalle.Length > 255, detalle.Substring(0, 255), detalle), "q", Environment.MachineName)
        End Sub

        Public Function ConsultarAuditoria(desde As Date, hasta As Date, Optional empresaId As Integer = 0, Optional login As String = "", Optional modulo As String = "") As DataTable
            Dim sql As String = "SELECT Fecha, Login, Modulo, Accion, Detalle, Equipo, EmpresaId FROM Auditoria WHERE Fecha >= @d AND Fecha < @h"
            Dim args As New List(Of Object) From {"d", desde.Date, "h", hasta.Date.AddDays(1)}
            If empresaId <> 0 Then
                sql &= " AND EmpresaId=@e"
                args.AddRange({"e", empresaId})
            End If
            If login <> "" Then
                sql &= " AND Login=@l"
                args.AddRange({"l", login})
            End If
            If modulo <> "" Then
                sql &= " AND Modulo=@m"
                args.AddRange({"m", modulo})
            End If
            sql &= " ORDER BY Fecha DESC"
            Return Db.Query(sql, args.ToArray())
        End Function

        ' ---------- Empresas / Gestiones ----------
        Public Function ListarEmpresas(Optional soloActivas As Boolean = False) As DataTable
            Return Db.Query("SELECT * FROM Empresa" & If(soloActivas, " WHERE Activa=1", "") & " ORDER BY RazonSocial")
        End Function

        Public Function ObtenerEmpresa(id As Integer) As EmpresaInfo
            Dim dt As DataTable = Db.Query("SELECT * FROM Empresa WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Return LeerEmpresa(dt.Rows(0))
        End Function

        Public Shared Function LeerEmpresa(r As DataRow) As EmpresaInfo
            Return New EmpresaInfo With {
                .Id = r.GetI("Id"), .Codigo = r.GetS("Codigo"), .RazonSocial = r.GetS("RazonSocial"),
                .NombreComercial = r.GetS("NombreComercial"), .Nit = r.GetS("Nit"), .Direccion = r.GetS("Direccion"),
                .Ciudad = r.GetS("Ciudad"), .Telefono = r.GetS("Telefono"), .Email = r.GetS("Email"),
                .Actividad = r.GetS("Actividad"), .RepLegal = r.GetS("RepLegal"), .Matricula = r.GetS("Matricula"),
                .Carpeta = r.GetS("Carpeta"), .Activa = r.GetF("Activa"), .EsDefecto = r.GetF("EsDefecto"),
                .FechaCreacion = r.GetDt("FechaCreacion"), .Observacion = r.GetS("Observacion")}
        End Function

        Public Function ListarGestiones(empresaId As Integer) As DataTable
            Return Db.Query("SELECT * FROM Gestion WHERE EmpresaId=@e ORDER BY Anio DESC", "e", empresaId)
        End Function

        Public Function ObtenerGestion(id As Integer) As GestionInfo
            Dim dt As DataTable = Db.Query("SELECT * FROM Gestion WHERE Id=@i", "i", id)
            If dt.Rows.Count = 0 Then Return Nothing
            Return LeerGestion(dt.Rows(0))
        End Function

        Public Shared Function LeerGestion(r As DataRow) As GestionInfo
            Return New GestionInfo With {
                .Id = r.GetI("Id"), .EmpresaId = r.GetI("EmpresaId"), .Anio = r.GetI("Anio"),
                .FechaInicio = r.GetDt("FechaInicio"), .FechaFin = r.GetDt("FechaFin"), .Archivo = r.GetS("Archivo"),
                .Estado = r.GetS("Estado"), .CorrelativoMensual = r.GetF("CorrelativoMensual"), .MesInicio = r.GetI("MesInicio"),
                .EsDefecto = r.GetF("EsDefecto"), .FechaCreacion = r.GetDt("FechaCreacion")}
        End Function

        Public Function RutaAbsoluta(g As GestionInfo) As String
            Return Path.Combine(RutaDatos, g.Archivo)
        End Function

        Public Sub CambiarEstadoGestion(gestionId As Integer, estado As String)
            If estado <> "A" AndAlso estado <> "C" Then Throw New ArgumentException("Estado inválido.")
            Db.Execute("UPDATE Gestion SET Estado=@e, FechaCierre=@f WHERE Id=@i", "e", estado, "f", If(estado = "C", CObj(Date.Now), CObj(DBNull.Value)), "i", gestionId)
        End Sub

        ''' <summary>Marca empresa y gestión predeterminadas (inician directamente al abrir el sistema).</summary>
        Public Sub MarcarDefecto(empresaId As Integer, gestionId As Integer)
            Db.InTx(Sub()
                        Db.Execute("UPDATE Empresa SET EsDefecto=0")
                        Db.Execute("UPDATE Empresa SET EsDefecto=1 WHERE Id=@i", "i", empresaId)
                        Db.Execute("UPDATE Gestion SET EsDefecto=0 WHERE EmpresaId=@e", "e", empresaId)
                        Db.Execute("UPDATE Gestion SET EsDefecto=1 WHERE Id=@i", "i", gestionId)
                    End Sub)
        End Sub

        ''' <summary>Abre el contexto de trabajo para un usuario en una empresa y gestión.</summary>
        Public Function AbrirContexto(usuario As UsuarioInfo, empresaId As Integer, gestionId As Integer) As Contexto
            Dim emp As EmpresaInfo = ObtenerEmpresa(empresaId)
            If emp Is Nothing Then Throw New InvalidOperationException("La empresa no existe.")
            Dim ges As GestionInfo = ObtenerGestion(gestionId)
            If ges Is Nothing OrElse ges.EmpresaId <> empresaId Then Throw New InvalidOperationException("La gestión no corresponde a la empresa.")
            If Not usuario.EsAdmin Then
                If Db.ScalarInt("SELECT COUNT(*) FROM UsuarioEmpresa WHERE UsuarioId=@u AND EmpresaId=@e", "u", usuario.Id, "e", empresaId) = 0 Then
                    Throw New UnauthorizedAccessException("No tiene acceso a la empresa seleccionada.")
                End If
            End If
            Dim u As New UsuarioInfo With {.Id = usuario.Id, .Login = usuario.Login, .Nombre = usuario.Nombre, .Email = usuario.Email,
                .Activo = usuario.Activo, .EsAdmin = usuario.EsAdmin, .CambiarClave = usuario.CambiarClave, .UltimoAcceso = usuario.UltimoAcceso}
            u.Rol = If(usuario.EsAdmin, Permisos.RolAdministrador, RolDe(usuario.Id, empresaId))
            For Each o As String In PermisosDe(usuario.Id, empresaId)
                u.Permisos.Add(o)
            Next
            Dim ruta As String = RutaAbsoluta(ges)
            If Not File.Exists(ruta) Then Throw New FileNotFoundException("No se encuentra la base de datos de la gestión: " & ruta)
            Dim bd As New Database(Provider, ruta)
            Dim ctx As New Contexto(Me, bd, emp, ges, u)
            ctx.Audit("Sistema", "ABRIR_GESTION", emp.Codigo & " / " & ges.Anio)
            Return ctx
        End Function

        Public Sub Dispose() Implements IDisposable.Dispose
            Db?.Dispose()
        End Sub

    End Class

End Namespace
