Attribute VB_Name = "modSecurity"
'==============================================================================
' SIC-MUNI - modSecurity
' Hash de contrasenas (SHA-256 con sal e iteraciones), sesion, bloqueo por
' intentos fallidos y matriz de permisos por rol (RBAC).
' Requiere Windows con .NET Framework 3.5 habilitado (CreateObject de las
' clases System.Security.Cryptography). Sin referencias externas (late binding).
'==============================================================================
Option Explicit

Public Const ROL_US As String = "US"    ' Unidad Solicitante
Public Const ROL_RC As String = "RC"    ' Responsable de Contrataciones
Public Const ROL_PF As String = "PF"    ' Presupuesto / Finanzas
Public Const ROL_ADM As String = "ADM"  ' Administrador del Sistema

' Permisos (acciones atomicas del sistema)
Public Const P_SOLICITUD As String = "SOLICITUD_EDIT"
Public Const P_COTIZACION As String = "COTIZACION_EDIT"
Public Const P_CHB As String = "CHB_EVAL"
Public Const P_ADJUDICAR As String = "ADJUDICAR"
Public Const P_ORDEN As String = "ORDEN_EMIT"
Public Const P_PRESUP As String = "PRESUPUESTO_EDIT"
Public Const P_C31 As String = "C31_EMIT"
Public Const P_REVERSION As String = "C31_REVERT"
Public Const P_DOCS As String = "DOC_PRINT"
Public Const P_USUARIOS As String = "USUARIOS_ADM"
Public Const P_CONFIG As String = "CONFIG_ADM"
Public Const P_AUDIT As String = "AUDIT_VIEW"

' Estado de sesion
Public g_Usuario As String
Public g_Rol As String
Public g_Nombre As String
Public g_DA As String
Public g_UltimaActividad As Date

Private m_enc As Object
Private m_sha As Object

'------------------------------------------------------------------------------
' HASH
'------------------------------------------------------------------------------
Public Function SHA256Hex(ByVal s As String) As String
    Dim b() As Byte, h() As Byte, i As Long, out As String
    If m_enc Is Nothing Then Set m_enc = CreateObject("System.Text.UTF8Encoding")
    If m_sha Is Nothing Then Set m_sha = CreateObject("System.Security.Cryptography.SHA256Managed")
    b = m_enc.GetBytes_4(s)
    h = m_sha.ComputeHash_2((b))
    For i = LBound(h) To UBound(h)
        out = out & Right$("0" & Hex$(h(i)), 2)
    Next i
    SHA256Hex = LCase$(out)
End Function

Public Function NewSalt() As String
    ' GUID sin llaves ni guiones = 32 hex aleatorios (Scriptlet.TypeLib).
    Dim g As String
    g = CreateObject("Scriptlet.TypeLib").GUID
    NewSalt = LCase$(Replace(Replace(Replace(Left$(g, 38), "{", ""), "}", ""), "-", ""))
End Function

' Hash lentificado: SHA256 iterado (estiramiento de clave) con sal por usuario.
Public Function HashPassword(ByVal pwd As String, ByVal salt As String) As String
    Dim h As String, i As Long
    h = pwd
    For i = 1 To 1000
        h = SHA256Hex(salt & h & pwd)
    Next i
    HashPassword = h
End Function

' Formato almacenado en SYS_AUTH.PasswordHash:  sal$hash
Public Function BuildStoredHash(ByVal pwd As String) As String
    Dim s As String
    s = NewSalt()
    BuildStoredHash = s & "$" & HashPassword(pwd, s)
End Function

Public Function VerifyPassword(ByVal pwd As String, ByVal stored As String) As Boolean
    Dim p As Long
    p = InStr(stored, "$")
    If p = 0 Then Exit Function
    VerifyPassword = (HashPassword(pwd, Left$(stored, p - 1)) = Mid$(stored, p + 1))
End Function

' Politica: >= 10 caracteres, mayuscula, minuscula y digito.
Public Function PasswordPolicyError(ByVal pwd As String) As String
    Dim i As Long, c As String, up As Boolean, lo As Boolean, dg As Boolean
    If Len(pwd) < 10 Then PasswordPolicyError = "La contrasena debe tener al menos 10 caracteres.": Exit Function
    For i = 1 To Len(pwd)
        c = Mid$(pwd, i, 1)
        If c Like "[A-Z]" Then up = True
        If c Like "[a-z]" Then lo = True
        If c Like "#" Then dg = True
    Next i
    If Not (up And lo And dg) Then PasswordPolicyError = "Debe combinar mayusculas, minusculas y digitos."
End Function

'------------------------------------------------------------------------------
' LOGIN / SESION
'------------------------------------------------------------------------------
Public Function Login(ByVal usr As String, ByVal pwd As String, ByRef msg As String) As Boolean
    Dim sh As Worksheet, r As Long, maxInt As Long, intentos As Long
    Set sh = WS(SH_AUTH)
    usr = Trim$(usr)
    maxInt = CLng(CfgNum("MaxIntentosLogin", 3))
    r = FindRow(sh, "Usuario", usr)
    If r = 0 Then
        Call HashPassword(pwd, "x")              ' iguala tiempos de respuesta
        msg = "Usuario o contrasena incorrectos."
        Exit Function
    End If
    If UCase$(CStr(GetV(sh, r, "Estado"))) <> "ACTIVO" Then
        msg = "Usuario inactivo o bloqueado. Contacte al Administrador."
        Exit Function
    End If
    If VerifyPassword(pwd, CStr(GetV(sh, r, "PasswordHash"))) Then
        SetV sh, r, "Intentos", 0
        SetV sh, r, "UltimoAcceso", Now
        g_Usuario = usr
        g_Nombre = CStr(GetV(sh, r, "NombreCompleto"))
        g_Rol = UCase$(CStr(GetV(sh, r, "Rol")))
        g_DA = CStr(GetV(sh, r, "Dependencia_DA"))
        g_UltimaActividad = Now
        LogAudit "LOGIN_OK", usr
        Login = True
    Else
        intentos = Val(GetV(sh, r, "Intentos")) + 1
        SetV sh, r, "Intentos", intentos
        If intentos >= maxInt Then
            SetV sh, r, "Estado", "BLOQUEADO"
            LogAudit "LOGIN_BLOQUEO", usr
            msg = "Usuario bloqueado por intentos fallidos."
        Else
            LogAudit "LOGIN_FALLIDO", usr & " (" & intentos & "/" & maxInt & ")"
            msg = "Usuario o contrasena incorrectos."
        End If
    End If
End Function

Public Sub Logout()
    If Len(g_Usuario) > 0 Then LogAudit "LOGOUT", g_Usuario
    g_Usuario = "": g_Rol = "": g_Nombre = "": g_DA = ""
End Sub

Public Function SesionActiva() As Boolean
    Dim minutos As Double
    If Len(g_Usuario) = 0 Then Exit Function
    minutos = CfgNum("TimeoutSesionMin", 20)
    If DateDiff("n", g_UltimaActividad, Now) > minutos Then
        LogAudit "SESION_EXPIRADA", g_Usuario
        Logout
        Exit Function
    End If
    g_UltimaActividad = Now
    SesionActiva = True
End Function

'------------------------------------------------------------------------------
' RBAC - matriz de permisos. Se separan funciones: ADM no transacciona
' (segregacion de funciones); PF es la unica que reserva/revierte C-31.
'------------------------------------------------------------------------------
Public Function PuedeHacer(ByVal permiso As String) As Boolean
    If Not SesionActiva() Then Exit Function
    Select Case g_Rol
        Case ROL_US
            PuedeHacer = (permiso = P_SOLICITUD Or permiso = P_DOCS)
        Case ROL_RC
            PuedeHacer = (permiso = P_SOLICITUD Or permiso = P_COTIZACION Or permiso = P_CHB _
                       Or permiso = P_ADJUDICAR Or permiso = P_ORDEN Or permiso = P_DOCS)
        Case ROL_PF
            PuedeHacer = (permiso = P_PRESUP Or permiso = P_C31 Or permiso = P_REVERSION Or permiso = P_DOCS)
        Case ROL_ADM
            PuedeHacer = (permiso = P_USUARIOS Or permiso = P_CONFIG Or permiso = P_AUDIT Or permiso = P_DOCS)
    End Select
End Function

Public Sub RequirePermiso(ByVal permiso As String)
    If Not PuedeHacer(permiso) Then
        If Len(g_Usuario) = 0 Then
            Fail "Sesion no iniciada o expirada. Ingrese nuevamente."
        Else
            LogAudit "ACCESO_DENEGADO", permiso
            Fail "Su rol (" & g_Rol & ") no tiene permiso para esta operacion."
        End If
    End If
End Sub

' La US solo ve/edita solicitudes de su propia dependencia (DA); los demas roles, todas.
Public Function PuedeVerSolicitud(ByVal codDA As String) As Boolean
    If g_Rol = ROL_US Then PuedeVerSolicitud = (codDA = g_DA) Else PuedeVerSolicitud = SesionActiva()
End Function

'------------------------------------------------------------------------------
' ABM de usuarios (solo ADM)
'------------------------------------------------------------------------------
Public Sub CrearUsuario(ByVal usr As String, ByVal pwd As String, ByVal nombre As String, _
                        ByVal rol As String, ByVal da As String)
    Dim sh As Worksheet, r As Long, e As String
    RequirePermiso P_USUARIOS
    rol = UCase$(rol)
    If InStr("|US|RC|PF|ADM|", "|" & rol & "|") = 0 Then Fail "Rol invalido."
    e = PasswordPolicyError(pwd): If Len(e) > 0 Then Fail e
    Set sh = WS(SH_AUTH)
    If FindRow(sh, "Usuario", usr) > 0 Then Fail "El usuario ya existe."
    r = NewRow(sh)
    SetV sh, r, "Usuario", usr
    SetV sh, r, "PasswordHash", BuildStoredHash(pwd)
    SetV sh, r, "NombreCompleto", nombre
    SetV sh, r, "Rol", rol
    SetV sh, r, "Dependencia_DA", da
    SetV sh, r, "Estado", "ACTIVO"
    SetV sh, r, "Intentos", 0
    LogAudit "USUARIO_CREADO", usr & " / " & rol
End Sub

Public Sub CambiarPassword(ByVal usr As String, ByVal nuevo As String)
    Dim sh As Worksheet, r As Long, e As String
    ' Un usuario puede cambiar la propia; ADM puede cambiar cualquiera.
    If Not (usr = g_Usuario And SesionActiva()) Then RequirePermiso P_USUARIOS
    e = PasswordPolicyError(nuevo): If Len(e) > 0 Then Fail e
    Set sh = WS(SH_AUTH)
    r = FindRow(sh, "Usuario", usr)
    If r = 0 Then Fail "Usuario no existe."
    SetV sh, r, "PasswordHash", BuildStoredHash(nuevo)
    LogAudit "PASSWORD_CAMBIADO", usr
End Sub

Public Sub DesbloquearUsuario(ByVal usr As String)
    Dim sh As Worksheet, r As Long
    RequirePermiso P_USUARIOS
    Set sh = WS(SH_AUTH)
    r = FindRow(sh, "Usuario", usr)
    If r = 0 Then Fail "Usuario no existe."
    SetV sh, r, "Estado", "ACTIVO"
    SetV sh, r, "Intentos", 0
    LogAudit "USUARIO_DESBLOQUEADO", usr
End Sub
