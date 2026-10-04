Attribute VB_Name = "modMain"
'==============================================================================
' SIC-MUNI - modMain: punto de entrada y utilidades de administracion (rol ADM)
'==============================================================================
Option Explicit

Public Sub IniciarSistema()
    frmLogin.Show
    If SesionActiva() Then
        If g_Rol = ROL_ADM Then
            MenuAdmin
        Else
            frmContratacionesConsolidado.Show
        End If
    End If
End Sub

' Menu del Administrador (el ADM administra; no opera transacciones).
' Para volver a abrirlo: Alt+F8 > MenuAdmin.
Public Sub MenuAdmin()
    Dim op As String
    Do
        If Not SesionActiva() Then Exit Do
        op = Trim$(InputBox("MENU ADMINISTRADOR  -  " & g_Nombre & vbLf & vbLf & _
            "1 = Crear usuario" & vbLf & _
            "2 = Desbloquear usuario" & vbLf & _
            "3 = Cambiar contrasena de un usuario" & vbLf & _
            "4 = Importar catalogo CHB (CSV)" & vbLf & _
            "5 = Importar presupuesto (CSV)" & vbLf & _
            "6 = Mostrar hojas de datos (mantenimiento / CONFIG)" & vbLf & _
            "7 = Ocultar y proteger hojas de datos" & vbLf & _
            "8 = Ver auditoria" & vbLf & _
            "0 = Cerrar sesion" & vbLf & vbLf & "Escriba el numero:", "SIC-MUNI"))
        Select Case op
            Case "1": AdminCrearUsuario
            Case "2": AdminDesbloquear
            Case "3": AdminCambiarPassword
            Case "4": AdminImportarCatalogo
            Case "5": AdminImportarPresupuesto
            Case "6": AdminMantenimiento
            Case "7": AdminProteger
            Case "8": AdminVerAuditoria
            Case "0", "": Logout: Exit Do
            Case Else: MsgBox "Opcion no valida.", vbExclamation
        End Select
    Loop
End Sub

Public Sub AdminCambiarPassword()
    Dim u As String, p As String
    On Error GoTo EH
    u = InputBox("Usuario:", "Cambiar contrasena"): If Len(u) = 0 Then Exit Sub
    p = InputBox("Nueva contrasena (min. 10 car., mayus/minus/digitos):", "Cambiar contrasena"): If Len(p) = 0 Then Exit Sub
    CambiarPassword u, p
    MsgBox "Contrasena actualizada.", vbInformation
    Exit Sub
EH: MsgBox Err.Description, vbExclamation
End Sub

Public Sub AdminProteger()
    On Error GoTo EH
    RequirePermiso P_CONFIG
    ProtectDB
    LogAudit "PROTECT_DB", "Hojas de datos ocultas y protegidas"
    MsgBox "Hojas de datos ocultas y protegidas.", vbInformation
    Exit Sub
EH: MsgBox Err.Description, vbExclamation
End Sub

Public Sub AdminVerAuditoria()
    On Error GoTo EH
    ShowDB
    WS(SH_AUD).Activate
    MsgBox "Hoja AUDITORIA visible. Use la opcion 7 del menu al terminar para ocultar y proteger.", vbInformation
    Exit Sub
EH: MsgBox Err.Description, vbExclamation
End Sub

Public Sub AdminCrearUsuario()
    Dim u As String, p As String, n As String, r As String, d As String
    On Error GoTo EH
    u = InputBox("Usuario:", "Nuevo usuario"): If Len(u) = 0 Then Exit Sub
    n = InputBox("Nombre completo:", "Nuevo usuario")
    r = InputBox("Rol (US / RC / PF / ADM):", "Nuevo usuario")
    d = InputBox("Codigo de Direccion Administrativa (DA):", "Nuevo usuario")
    p = InputBox("Contrasena inicial (min. 10 car.):", "Nuevo usuario")
    CrearUsuario u, p, n, r, d
    MsgBox "Usuario creado.", vbInformation
    Exit Sub
EH: MsgBox Err.Description, vbExclamation
End Sub

Public Sub AdminDesbloquear()
    On Error GoTo EH
    DesbloquearUsuario InputBox("Usuario a desbloquear:", "SIC-MUNI")
    MsgBox "Usuario desbloqueado.", vbInformation
    Exit Sub
EH: MsgBox Err.Description, vbExclamation
End Sub

Public Sub AdminMantenimiento()
    On Error GoTo EH
    ShowDB                      ' tambien registra en AUDITORIA
    MsgBox "Hojas visibles. Al terminar ejecute modCore.ProtectDB.", vbInformation
    Exit Sub
EH: MsgBox Err.Description, vbExclamation
End Sub

Public Sub AdminImportarCatalogo()
    modImport.ImportarCatalogoCHB
End Sub

Public Sub AdminImportarPresupuesto()
    modImport.ImportarPresupuesto
End Sub
