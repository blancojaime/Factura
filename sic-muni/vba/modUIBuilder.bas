Attribute VB_Name = "modUIBuilder"
'==============================================================================
' SIC-MUNI - modUIBuilder
' Crea por codigo los UserForms (frmLogin, frmContratacionesConsolidado) e
' inyecta su codigo desde los archivos *.code.txt de la carpeta \vba junto al libro.
' Requisito: Archivo > Opciones > Centro de confianza > Configuracion de macros >
'            "Confiar en el acceso al modelo de objetos de proyectos de VBA".
' Ejecutar una sola vez (reemplaza los formularios si ya existen).
'==============================================================================
Option Explicit

Private Const FM_TXT As String = "Forms.TextBox.1"
Private Const FM_LBL As String = "Forms.Label.1"
Private Const FM_BTN As String = "Forms.CommandButton.1"
Private Const FM_LST As String = "Forms.ListBox.1"
Private Const FM_CHK As String = "Forms.CheckBox.1"
Private Const FM_CBO As String = "Forms.ComboBox.1"

Public Sub ConstruirFormularios()
    Dim dirV As String
    dirV = ThisWorkbook.Path & "\vba\"
    BuildLogin dirV
    BuildConsolidado dirV
    MsgBox "Formularios creados. Pegue ThisWorkbook.code.txt en ThisWorkbook y ejecute modCore.ProtectDB.", vbInformation
End Sub

Private Function NuevoForm(ByVal nombre As String, ByVal cap As String, ByVal w As Double, ByVal h As Double) As Object
    Dim vbc As Object
    On Error Resume Next
    ThisWorkbook.VBProject.VBComponents.Remove ThisWorkbook.VBProject.VBComponents(nombre)
    On Error GoTo 0
    Set vbc = ThisWorkbook.VBProject.VBComponents.Add(3)       ' 3 = vbext_ct_MSForm
    vbc.Name = nombre
    vbc.Properties("Caption") = cap
    vbc.Properties("Width") = w
    vbc.Properties("Height") = h
    Set NuevoForm = vbc
End Function

Private Function Ctl(ByVal vbc As Object, ByVal prog As String, ByVal nombre As String, _
                     ByVal l As Double, ByVal t As Double, ByVal w As Double, ByVal h As Double, _
                     Optional ByVal cap As String = "", Optional ByVal pag As String = "") As Object
    Dim c As Object
    Set c = vbc.Designer.Controls.Add(prog, nombre, True)
    c.Left = l: c.Top = t: c.Width = w: c.Height = h
    If Len(cap) > 0 Then c.Caption = cap
    c.Tag = pag
    Set Ctl = c
End Function

' Etiqueta + control de entrada
Private Function Fld(ByVal vbc As Object, ByVal pag As String, ByVal etiqueta As String, ByVal nombre As String, _
                     ByVal prog As String, ByVal l As Double, ByVal t As Double, ByVal w As Double, Optional ByVal h As Double = 18) As Object
    Ctl vbc, FM_LBL, "lbl" & nombre, l, t, 95, 16, etiqueta, pag
    Set Fld = Ctl(vbc, prog, nombre, l + 98, t - 2, w, h, "", pag)
End Function

Private Sub Inyectar(ByVal vbc As Object, ByVal archivo As String)
    If Len(Dir$(archivo)) = 0 Then Err.Raise vbObjectError + 800, , "No se encuentra " & archivo
    vbc.CodeModule.AddFromFile archivo
End Sub

Private Sub BuildLogin(ByVal dirV As String)
    Dim f As Object, c As Object
    Set f = NuevoForm("frmLogin", "SIC-MUNI - Inicio de sesion", 300, 200)
    Set c = Ctl(f, FM_LBL, "lblTitulo", 12, 10, 270, 20, "SISTEMA INTEGRADO DE CONTRATACIONES MUNICIPALES")
    c.Font.Bold = True
    Ctl f, FM_LBL, "lblUsuario", 12, 48, 70, 16, "Usuario"
    Ctl f, FM_TXT, "txtUsuario", 90, 46, 180, 20
    Ctl f, FM_LBL, "lblClave", 12, 78, 70, 16, "Contrasena"
    Ctl f, FM_TXT, "txtPassword", 90, 76, 180, 20
    Set c = Ctl(f, FM_LBL, "lblMsg", 12, 106, 270, 30, "")
    c.ForeColor = RGB(192, 0, 0)
    Set c = Ctl(f, FM_BTN, "cmdIngresar", 90, 140, 85, 26, "Ingresar"): c.Default = True
    Set c = Ctl(f, FM_BTN, "cmdCancelar", 185, 140, 85, 26, "Cancelar"): c.Cancel = True
    Inyectar f, dirV & "frmLogin.code.txt"
End Sub

Private Sub BuildConsolidado(ByVal dirV As String)
    Dim f As Object, c As Object, i As Long
    Set f = NuevoForm("frmContratacionesConsolidado", "SIC-MUNI", 790, 560)
    ' --- Barra comun ---
    Set c = Ctl(f, FM_LBL, "lblSesion", 10, 6, 560, 16): c.Font.Bold = True
    Ctl f, FM_BTN, "cmdSalir", 700, 4, 75, 20, "Cerrar sesion"
    Ctl f, FM_LBL, "lblSolTit", 10, 30, 80, 16, "Solicitud N:"
    Ctl f, FM_TXT, "txtSol", 90, 28, 130, 18
    Ctl f, FM_BTN, "cmdCargar", 226, 27, 60, 20, "Cargar"
    Set c = Ctl(f, FM_LBL, "lblEstado", 295, 30, 480, 16)
    Ctl f, FM_BTN, "cmdP1", 10, 54, 150, 24, "1 Solicitud"
    Ctl f, FM_BTN, "cmdP2", 165, 54, 150, 24, "2 Evaluacion CHB"
    Ctl f, FM_BTN, "cmdP3", 320, 54, 150, 24, "3 Cotizaciones"
    Ctl f, FM_BTN, "cmdP4", 475, 54, 150, 24, "4 Presupuesto / C-31"
    Ctl f, FM_BTN, "cmdP5", 630, 54, 145, 24, "5 Orden / Recepcion"

    ' --- P1 Solicitud ---
    Fld f, "P1", "DA", "txtDA", FM_TXT, 10, 92, 80
    Fld f, "P1", "UE", "txtUE", FM_TXT, 290, 92, 80
    Set c = Fld(f, "P1", "Justificacion", "txtJustificacion", FM_TXT, 10, 116, 560, 44): c.MultiLine = True
    Ctl f, FM_BTN, "cmdCrearSolicitud", 680, 116, 95, 26, "Crear solicitud", "P1"
    Fld f, "P1", "Codigo UNSPSC", "txtCodigo", FM_TXT, 10, 172, 90
    Set c = Ctl(f, FM_LBL, "lblAlertaCHB", 210, 168, 570, 28, "", "P1"): c.Font.Bold = True: c.WordWrap = True
    Fld f, "P1", "Descripcion", "txtDescItem", FM_TXT, 10, 200, 330
    Fld f, "P1", "Unidad", "txtUnidad", FM_TXT, 540, 200, 80
    Fld f, "P1", "Cantidad", "txtCant", FM_TXT, 10, 224, 80
    Fld f, "P1", "P. ref. unit. (Bs)", "txtPrecio", FM_TXT, 290, 224, 80
    Ctl f, FM_BTN, "cmdAgregarItem", 680, 222, 95, 24, "Agregar item", "P1"
    Ctl f, FM_LST, "lstItems", 10, 256, 765, 190, "", "P1"
    Ctl f, FM_BTN, "cmdEnviarCot", 10, 456, 160, 26, "Enviar a cotizacion", "P1"
    Ctl f, FM_BTN, "cmdC1", 180, 456, 160, 26, "Generar C-1 (PDF)", "P1"

    ' --- P2 CHB ---
    Fld f, "P2", "N de item", "txtItemCHB", FM_TXT, 10, 100, 60
    Ctl f, FM_CHK, "chkFuera", 290, 98, 380, 20, "Comprar FUERA del catalogo CHB (requiere excepcion)", "P2"
    Fld f, "P2", "Cod. Excepcion", "txtCodExc", FM_TXT, 10, 136, 180
    Fld f, "P2", "N Autoriz. MDPyEP", "txtNroAut", FM_TXT, 10, 164, 180
    Fld f, "P2", "Fecha autoriz.", "txtFechaAut", FM_TXT, 10, 192, 100
    Set c = Fld(f, "P2", "Justificacion", "txtJustExc", FM_TXT, 10, 220, 560, 110): c.MultiLine = True
    Ctl f, FM_BTN, "cmdEvalCHB", 10, 350, 170, 28, "Registrar evaluacion CHB", "P2"
    Ctl f, FM_BTN, "cmdDocExc", 190, 350, 200, 28, "Justificacion de excepcion (PDF)", "P2"

    ' --- P3 Cotizaciones ---
    Fld f, "P3", "NIT", "txtNIT", FM_TXT, 10, 100, 120
    Fld f, "P3", "Razon social", "txtRazon", FM_TXT, 290, 100, 300
    Fld f, "P3", "Validez (fecha)", "txtValidez", FM_TXT, 10, 128, 100
    Fld f, "P3", "Monto cotizado", "txtMontoCot", FM_TXT, 290, 128, 100
    Ctl f, FM_CHK, "chkCumple", 520, 128, 160, 20, "Cumple tecnicamente", "P3"
    Ctl f, FM_BTN, "cmdRegCot", 680, 100, 95, 26, "Registrar", "P3"
    Ctl f, FM_LST, "lstCot", 10, 164, 765, 190, "", "P3"
    Ctl f, FM_BTN, "cmdEvaluar", 10, 366, 170, 28, "Evaluar cuadro", "P3"
    Ctl f, FM_BTN, "cmdCuadro", 190, 366, 190, 28, "Cuadro comparativo (PDF)", "P3"
    Ctl f, FM_BTN, "cmdAdjudicar", 390, 366, 170, 28, "Adjudicar seleccionada", "P3"

    ' --- P4 Presupuesto / C-31 ---
    Fld f, "P4", "Programa", "txtProg", FM_TXT, 10, 96, 80
    Fld f, "P4", "Proyecto", "txtProy", FM_TXT, 290, 96, 80
    Fld f, "P4", "Act./Obra", "txtAct", FM_TXT, 10, 120, 80
    Fld f, "P4", "Fuente", "txtFte", FM_TXT, 290, 120, 80
    Fld f, "P4", "Organismo", "txtOrg", FM_TXT, 10, 144, 80
    Fld f, "P4", "Partida", "txtPartida", FM_TXT, 290, 144, 80
    Fld f, "P4", "Importe (Bs)", "txtImporte", FM_TXT, 10, 168, 100
    Ctl f, FM_BTN, "cmdSaldo", 500, 96, 120, 24, "Consultar saldo", "P4"
    Ctl f, FM_BTN, "cmdAddLinea", 500, 126, 120, 24, "Agregar linea", "P4"
    Set c = Ctl(f, FM_LBL, "lblSaldo", 500, 160, 280, 18, "", "P4"): c.Font.Bold = True
    Ctl f, FM_LST, "lstLineas", 10, 196, 765, 80, "", "P4"
    Ctl f, FM_BTN, "cmdEmitirC31", 10, 284, 170, 26, "Emitir C-31 Preventivo", "P4"
    Fld f, "P4", "N C-31 interno", "txtNroC31", FM_TXT, 10, 324, 140
    Fld f, "P4", "N C-31 SIGEP", "txtNroSigep", FM_TXT, 290, 324, 120
    Ctl f, FM_BTN, "cmdAsociar", 540, 322, 120, 24, "Asociar C-31", "P4"
    Ctl f, FM_BTN, "cmdDocC31", 670, 322, 105, 24, "C-31 (PDF)", "P4"
    Fld f, "P4", "Linea a revertir", "txtLineaRev", FM_TXT, 10, 360, 60
    Fld f, "P4", "Monto a revertir", "txtMontoRev", FM_TXT, 290, 360, 100
    Set c = Fld(f, "P4", "Motivo", "txtMotivoRev", FM_TXT, 10, 388, 560, 40): c.MultiLine = True
    Ctl f, FM_BTN, "cmdRevParcial", 10, 440, 150, 26, "Reversion parcial", "P4"
    Ctl f, FM_BTN, "cmdRevTotal", 170, 440, 150, 26, "Reversion total", "P4"

    ' --- P5 Orden ---
    Fld f, "P5", "Tipo", "cboTipo", FM_CBO, 10, 100, 120
    Fld f, "P5", "CUCE (SICOES)", "txtCUCE", FM_TXT, 290, 100, 180
    Fld f, "P5", "Plazo (dias)", "txtPlazo", FM_TXT, 10, 128, 60
    Fld f, "P5", "Lugar", "txtLugar", FM_TXT, 10, 156, 560
    Ctl f, FM_BTN, "cmdGenOrden", 10, 200, 170, 28, "Generar Orden", "P5"
    Set c = Ctl(f, FM_LBL, "lblNroOrden", 190, 206, 180, 18, "", "P5"): c.Font.Bold = True
    Ctl f, FM_BTN, "cmdDocOrden", 380, 200, 170, 28, "Orden (PDF)", "P5"
    Fld f, "P5", "Fecha recepcion", "txtFechaRec", FM_TXT, 10, 260, 100
    Ctl f, FM_CHK, "chkConforme", 290, 258, 200, 20, "Recepcion CONFORME", "P5"
    Set c = Fld(f, "P5", "Observaciones", "txtObsRec", FM_TXT, 10, 286, 560, 40): c.MultiLine = True
    Ctl f, FM_BTN, "cmdRecepcion", 10, 336, 170, 28, "Registrar recepcion", "P5"
    Set c = Ctl(f, FM_LBL, "lblNroActa", 190, 342, 180, 18, "", "P5"): c.Font.Bold = True
    Ctl f, FM_BTN, "cmdActa", 380, 336, 170, 28, "Acta de recepcion (PDF)", "P5"
    Set c = Fld(f, "P5", "Motivo anulacion", "txtMotivoAnu", FM_TXT, 10, 390, 560, 40): c.MultiLine = True
    Ctl f, FM_BTN, "cmdAnularOrden", 10, 440, 170, 28, "Anular Orden", "P5"
    Ctl f, FM_BTN, "cmdAnularSol", 190, 440, 170, 28, "Anular solicitud", "P5"

    Inyectar f, dirV & "frmContratacionesConsolidado.code.txt"
End Sub
