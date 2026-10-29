Imports ContaBol.Core.Common
Imports ContaBol.Core.Data
Imports ContaBol.Core.Domain

Namespace Services

    ''' <summary>Sesión de trabajo: usuario + empresa + gestión abiertos. Todos los servicios operan sobre un contexto.</summary>
    Public Class Contexto
        Implements IDisposable

        Public ReadOnly Property Sistema As SistemaService
        Public ReadOnly Property Db As Database
        Public ReadOnly Property Empresa As EmpresaInfo
        Public ReadOnly Property Gestion As GestionInfo
        Public ReadOnly Property Usuario As UsuarioInfo
        Public ReadOnly Property Param As Parametros

        Private _cuentasPorCodigo As Dictionary(Of String, DataRow)
        Private _cuentasPorId As Dictionary(Of Integer, DataRow)
        Private _tabla As DataTable

        Public Sub New(sistema As SistemaService, db As Database, empresa As EmpresaInfo, gestion As GestionInfo, usuario As UsuarioInfo)
            Me.Sistema = sistema
            Me.Db = db
            Me.Empresa = empresa
            Me.Gestion = gestion
            Me.Usuario = usuario
            Me.Param = New Parametros(db)
        End Sub

        Public ReadOnly Property RutaGestion As String
            Get
                Return Db.Path
            End Get
        End Property

        Public Sub Requiere(opcion As String)
            If Not Usuario.Puede(opcion) Then
                Throw New UnauthorizedAccessException("Su usuario no tiene permiso para esta opción (" & opcion & ").")
            End If
        End Sub

        Public Sub RequiereGestionAbierta()
            If Not Gestion.Abierta Then
                Throw New InvalidOperationException("La gestión " & Gestion.Anio & " está cerrada. No se permiten cambios.")
            End If
        End Sub

        Public Sub Audit(modulo As String, accion As String, detalle As String)
            Try
                Sistema.Auditar(Usuario.Id, Usuario.Login, Empresa.Id, Gestion.Id, modulo, accion, detalle)
            Catch
                ' La auditoría nunca debe interrumpir la operación principal.
            End Try
        End Sub

        ' ---------- Caché de cuentas ----------
        Public Sub InvalidarCuentas()
            _cuentasPorCodigo = Nothing
            _cuentasPorId = Nothing
            _tabla = Nothing
        End Sub

        Private Sub CargarCuentas()
            If _cuentasPorCodigo IsNot Nothing Then Return
            _tabla = Db.Query("SELECT * FROM Cuenta ORDER BY Codigo")
            _cuentasPorCodigo = New Dictionary(Of String, DataRow)(StringComparer.OrdinalIgnoreCase)
            _cuentasPorId = New Dictionary(Of Integer, DataRow)
            For Each r As DataRow In _tabla.Rows
                _cuentasPorCodigo(r.GetS("Codigo")) = r
                _cuentasPorId(r.GetI("Id")) = r
            Next
        End Sub

        Public Function Cuentas() As DataTable
            CargarCuentas()
            Return _tabla
        End Function

        Public Function CuentaPorCodigo(codigo As String) As DataRow
            CargarCuentas()
            Dim r As DataRow = Nothing
            If codigo IsNot Nothing AndAlso _cuentasPorCodigo.TryGetValue(codigo.Trim(), r) Then Return r
            Return Nothing
        End Function

        Public Function CuentaPorId(id As Integer) As DataRow
            CargarCuentas()
            Dim r As DataRow = Nothing
            If _cuentasPorId.TryGetValue(id, r) Then Return r
            Return Nothing
        End Function

        ''' <summary>Id de la cuenta configurada en un parámetro (CTA_*). Falla con un mensaje claro si no está configurada.</summary>
        Public Function CuentaParam(claveParam As String) As Integer
            Dim cod As String = Param.Valor(claveParam)
            If cod = "" Then Throw New InvalidOperationException("Falta configurar la cuenta '" & claveParam & "' en Administración > Parámetros.")
            Dim r As DataRow = CuentaPorCodigo(cod)
            If r Is Nothing Then Throw New InvalidOperationException("La cuenta '" & cod & "' configurada en '" & claveParam & "' no existe en el plan de cuentas.")
            Return r.GetI("Id")
        End Function

        Public Function CuentaParamOpcional(claveParam As String) As Integer
            Dim cod As String = Param.Valor(claveParam)
            If cod = "" Then Return 0
            Dim r As DataRow = CuentaPorCodigo(cod)
            If r Is Nothing Then Return 0
            Return r.GetI("Id")
        End Function

        Public Function NombreCuenta(id As Integer) As String
            Dim r As DataRow = CuentaPorId(id)
            If r Is Nothing Then Return ""
            Return r.GetS("Nombre")
        End Function

        Public Function CodigoCuenta(id As Integer) As String
            Dim r As DataRow = CuentaPorId(id)
            If r Is Nothing Then Return ""
            Return r.GetS("Codigo")
        End Function

        ''' <summary>Siguiente valor de una secuencia numérica (correlativos de documentos).</summary>
        Public Function Siguiente(clave As String) As Integer
            Return Db.InTx(Function()
                               Dim n As Integer = Db.Execute("UPDATE Secuencia SET Valor = Valor + 1 WHERE Clave=@k", "k", clave)
                               If n = 0 Then
                                   Db.Execute("INSERT INTO Secuencia (Clave, Valor) VALUES (@k, 1)", "k", clave)
                                   Return 1
                               End If
                               Return Db.ScalarInt("SELECT Valor FROM Secuencia WHERE Clave=@k", "k", clave)
                           End Function)
        End Function

        Public Sub Dispose() Implements IDisposable.Dispose
            Db?.Dispose()
        End Sub
    End Class

End Namespace
