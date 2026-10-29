Imports System.Security.Cryptography
Imports System.Text

Namespace Services

    ''' <summary>Hash de contraseñas con PBKDF2-SHA256 (a diferencia de Orion4, nunca se guardan en texto plano).</summary>
    Public Module Seguridad

        Private Const Iteraciones As Integer = 100000

        Public Function NuevaSal() As String
            Dim b(15) As Byte
            RandomNumberGenerator.Fill(b)
            Return Convert.ToBase64String(b)
        End Function

        Public Function HashClave(clave As String, sal As String) As String
            Dim h As Byte() = Rfc2898DeriveBytes.Pbkdf2(Encoding.UTF8.GetBytes(clave), Convert.FromBase64String(sal), Iteraciones, HashAlgorithmName.SHA256, 32)
            Return Convert.ToBase64String(h)
        End Function

        Public Function Verificar(clave As String, sal As String, hash As String) As Boolean
            Dim a As Byte() = Convert.FromBase64String(HashClave(clave, sal))
            Dim b As Byte() = Convert.FromBase64String(hash)
            Return CryptographicOperations.FixedTimeEquals(a, b)
        End Function

    End Module

End Namespace
