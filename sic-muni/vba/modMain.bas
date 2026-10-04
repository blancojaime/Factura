Attribute VB_Name = "modMain"
'==============================================================================
' SIC-MUNI - modMain: punto de entrada y utilidades de administracion (rol ADM)
'==============================================================================
Option Explicit

Public Sub IniciarSistema()
    frmLogin.Show
    If SesionActiva() Then
        If g_Rol = ROL_ADM Then
            MsgBox "Sesion ADM: use los macros Admin* (usuarios, auditoria, mantenimiento)." & vbLf & _
                   "El rol ADM no opera transacciones (segregacion de funciones).", vbInformation
        Else
            frmContratacionesConsolidado.Show
        End If
    End If
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
