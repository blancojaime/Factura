Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services

''' <summary>Estado global de la sesión: sistema (multiempresa), usuario y empresa/gestión abiertas.</summary>
Public Module Sesion

    Public Property Config As AppSettings = New AppSettings()
    Public Property Sis As SistemaService
    Public Property Usuario As UsuarioInfo
    Public Property Ctx As Contexto

    ''' <summary>Se invoca cuando cambia la empresa o gestión activa (para refrescar la barra de estado, etc.).</summary>
    Public Property AlCambiarContexto As Action

    Public ReadOnly Property HayContexto As Boolean
        Get
            Return Ctx IsNot Nothing
        End Get
    End Property

    Public Sub AbrirContexto(empresaId As Integer, gestionId As Integer)
        Dim nuevo As Contexto = Sis.AbrirContexto(Usuario, empresaId, gestionId)
        CerrarContexto()
        Ctx = nuevo
        Config.UltimaEmpresaId = empresaId
        Config.UltimaGestionId = gestionId
        Config.Guardar()
        If AlCambiarContexto IsNot Nothing Then AlCambiarContexto.Invoke()
    End Sub

    Public Sub CerrarContexto()
        If Ctx IsNot Nothing Then
            Try
                Ctx.Dispose()
            Catch
            End Try
            Ctx = Nothing
        End If
    End Sub

    ''' <summary>Verifica que haya una gestión abierta y el permiso indicado antes de operar.</summary>
    Public Function Puede(opcion As String) As Boolean
        Return Usuario IsNot Nothing AndAlso Usuario.Puede(opcion) AndAlso Ctx IsNot Nothing AndAlso Ctx.Usuario.Puede(opcion)
    End Function

End Module
