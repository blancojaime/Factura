Imports System.IO
Imports System.IO.Compression
Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class BackupTests

    <Fact>
    Public Sub BackupYRestauracionRecuperanLosDatos()
        Using e As New Entorno()
            Asiento(e, "I", New Date(2025, 1, 5), Caja, Capital, 1000D)
            Dim uid = e.Sistema.CrearUsuario("maria", "María", "clave123", False)
            e.Sistema.AsignarEmpresa(uid, e.Ctx.Empresa.Id, Permisos.RolAuxiliar)
            Dim bs As New BackupService(e.Sistema)
            Dim ruta = bs.BackupEmpresa(e.Ctx.Empresa.Id)
            Assert.True(File.Exists(ruta))
            Dim v = bs.Verificar(ruta)
            Assert.True(v.Valido, v.Mensaje)
            Assert.Equal("EMPRESA", v.Tipo)
            Assert.Equal("TEST", v.EmpresaCodigo)
            ' desastre: se agregan datos y luego se restaura la copia
            Asiento(e, "I", New Date(2025, 1, 6), Caja, Capital, 500D)
            Assert.Equal(1500D, Saldo(e, Caja))
            Dim empId = e.Ctx.Empresa.Id
            Dim gestionId = e.Ctx.Gestion.Id
            e.Ctx.Dispose()
            Dim restaurada = bs.RestaurarEmpresa(ruta)
            Assert.Equal(empId, restaurada)
            Using c2 = e.Sistema.AbrirContexto(e.Usuario, empId, gestionId)
                Dim led As New LedgerService(c2)
                Assert.Equal(1000D, led.SaldoCuenta(c2.CuentaPorCodigo(Caja).GetI("Id"), New Date(2025, 12, 31)))
            End Using
            ' se creó automáticamente una copia previa a la restauración
            Assert.Contains(bs.Listar(), Function(b) Path.GetFileName(b.Archivo).StartsWith("PRE-RESTAURACION_"))
        End Using
    End Sub

    <Fact>
    Public Sub RestauraComoNuevaEmpresaConOtroCodigo()
        Using e As New Entorno()
            Asiento(e, "I", New Date(2025, 1, 5), Caja, Capital, 1000D)
            Dim bs As New BackupService(e.Sistema)
            Dim ruta = bs.BackupEmpresa(e.Ctx.Empresa.Id)
            Dim nueva = bs.RestaurarEmpresa(ruta, "CLON")
            Assert.NotEqual(e.Ctx.Empresa.Id, nueva)
            Assert.Equal(2, e.Sistema.ListarEmpresas().Rows.Count)
            Dim g = e.Sistema.ListarGestiones(nueva).Rows(0)
            Using c2 = e.Sistema.AbrirContexto(e.Usuario, nueva, g.GetI("Id"))
                Assert.Equal(1000D, New LedgerService(c2).SaldoCuenta(c2.CuentaPorCodigo(Caja).GetI("Id"), New Date(2025, 12, 31)))
                Assert.NotEqual(e.Ctx.RutaGestion, c2.RutaGestion)
            End Using
            ' el original sigue intacto
            Assert.Equal(1000D, Saldo(e, Caja))
        End Using
    End Sub

    <Fact>
    Public Sub DetectaCopiaDanada()
        Using e As New Entorno()
            Dim bs As New BackupService(e.Sistema)
            Dim ruta = bs.BackupEmpresa(e.Ctx.Empresa.Id)
            ' corrompe el archivo de datos dentro del zip
            Using zip = ZipFile.Open(ruta, ZipArchiveMode.Update)
                Dim entry = zip.Entries.First(Function(x) x.FullName.StartsWith("datos/"))
                Dim name = entry.FullName
                entry.Delete()
                Dim n = zip.CreateEntry(name)
                Using w = New StreamWriter(n.Open())
                    w.Write("contenido alterado")
                End Using
            End Using
            Dim v = bs.Verificar(ruta)
            Assert.False(v.Valido)
            Assert.Contains("dañada", v.Mensaje)
            Assert.Throws(Of InvalidDataException)(Sub() bs.RestaurarEmpresa(ruta))
            ' archivo cualquiera no es una copia
            Dim basura = Path.Combine(e.Raiz, "x.cbk")
            File.WriteAllText(basura, "no es zip")
            Assert.False(bs.Verificar(basura).Valido)
        End Using
    End Sub

    <Fact>
    Public Sub CopiaTotalYDepuracion()
        Using e As New Entorno()
            Dim bs As New BackupService(e.Sistema)
            Dim total = bs.BackupTotal()
            Dim v = bs.Verificar(total)
            Assert.True(v.Valido, v.Mensaje)
            Assert.Equal("TOTAL", v.Tipo)
            For i = 1 To 3
                Threading.Thread.Sleep(1100)
                bs.BackupEmpresa(e.Ctx.Empresa.Id)
            Next
            Assert.Equal(4, bs.Listar().Count)
            Assert.Equal(1, bs.Depurar(2))        ' deja 2 de la empresa (la copia total es otro grupo)
            Assert.Equal(3, bs.Listar().Count)
        End Using
    End Sub

    <Fact>
    Public Sub RestauracionTotalRecuperaTodoElSistema()
        Dim raiz As String = Path.Combine(Path.GetTempPath(), "contabol_total_" & Guid.NewGuid().ToString("N"))
        Dim prov As New SqliteProvider()
        Try
            Dim copia As String
            Using sis = SistemaService.Abrir(prov, raiz)
                Dim u = sis.Autenticar("admin", "admin")
                Dim r = New EmpresaService(sis).CrearEmpresa(New EmpresaInfo With {.Codigo = "AAA", .RazonSocial = "Empresa A"}, New NuevaGestionOpciones With {.Anio = 2025}, u.Id)
                copia = New BackupService(sis).BackupTotal()
                sis.CrearUsuario("temporal", "Temporal", "abcd", False)
            End Using
            prov.ReleasePools()
            BackupService.RestaurarTotal(prov, raiz, copia)
            Using sis = SistemaService.Abrir(prov, raiz)
                Assert.Equal(1, sis.ListarEmpresas().Rows.Count)
                Assert.Equal(1, sis.ListarUsuarios().Rows.Count)    ' el usuario creado después de la copia ya no existe
            End Using
        Finally
            prov.ReleasePools()
            Try
                If Directory.Exists(raiz) Then Directory.Delete(raiz, True)
            Catch
            End Try
        End Try
    End Sub
End Class
