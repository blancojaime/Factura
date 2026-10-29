Imports System.IO
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Entorno de pruebas: sistema maestro + empresa + gestión sobre SQLite en una carpeta temporal.</summary>
Public Class Entorno
    Implements IDisposable

    Public ReadOnly Property Raiz As String
    Public ReadOnly Property Sistema As SistemaService
    Public ReadOnly Property Ctx As Contexto
    Public ReadOnly Property Usuario As UsuarioInfo

    Public Sub New(Optional mensual As Boolean = True, Optional anio As Integer = 2025)
        Raiz = Path.Combine(Path.GetTempPath(), "contabol_test_" & Guid.NewGuid().ToString("N"))
        Sistema = SistemaService.Abrir(New SqliteProvider(), Raiz)
        Usuario = Sistema.Autenticar("admin", "admin")
        Dim emp As New EmpresaInfo With {.Codigo = "TEST", .RazonSocial = "Comercial Prueba S.R.L.", .Nit = "1020304050", .Direccion = "Av. Camacho 123", .Ciudad = "La Paz"}
        Dim opc As New NuevaGestionOpciones With {.Anio = anio, .CorrelativoMensual = mensual}
        Dim r = New EmpresaService(Sistema).CrearEmpresa(emp, opc, Usuario.Id)
        Ctx = Sistema.AbrirContexto(Usuario, r.Item1, r.Item2)
    End Sub

    Public Sub Dispose() Implements IDisposable.Dispose
        Try
            Ctx.Dispose()
            Sistema.Dispose()
            Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools()
            If Directory.Exists(Raiz) Then Directory.Delete(Raiz, True)
        Catch
        End Try
    End Sub
End Class
