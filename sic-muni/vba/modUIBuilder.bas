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
    Aviso "Formularios creados. Pegue ThisWorkbook.code.txt en ThisWorkbook y ejecute modCore.ProtectDB."
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
    vbc.Properties("BackColor") = RGB(245, 247, 250)
    Set NuevoForm = vbc
End Function

' Texto con acentos: {a}{e}{i}{o}{u}{n} y mayusculas {A}{E}{I}{O}{U}{N}; {deg} = grado.
' (el codigo fuente es ASCII; los acentos se construyen con ChrW)
Private Function Ac(ByVal s As String) As String
    s = Replace(s, "{a}", ChrW(225)): s = Replace(s, "{e}", ChrW(233)): s = Replace(s, "{i}", ChrW(237))
    s = Replace(s, "{o}", ChrW(243)): s = Replace(s, "{u}", ChrW(250)): s = Replace(s, "{n}", ChrW(241))
    s = Replace(s, "{A}", ChrW(193)): s = Replace(s, "{E}", ChrW(201)): s = Replace(s, "{I}", ChrW(205))
    s = Replace(s, "{O}", ChrW(211)): s = Replace(s, "{U}", ChrW(218)): s = Replace(s, "{N}", ChrW(209))
    Ac = Replace(s, "{deg}", ChrW(176))
End Function

Private Function ColorPagina(ByVal n As Long) As Long
    Select Case n
        Case 1: ColorPagina = RGB(31, 78, 121)      ' azul marino: solicitud
        Case 2: ColorPagina = RGB(0, 121, 107)      ' verde azulado: CHB
        Case 3: ColorPagina = RGB(96, 74, 150)      ' violeta: cotizaciones
        Case 4: ColorPagina = RGB(176, 96, 0)       ' ambar oscuro: presupuesto
        Case Else: ColorPagina = RGB(56, 118, 29)   ' verde: orden y recepcion
    End Select
End Function

' Estilo de boton segun su funcion: primario (azul), ok (verde: avanza el tramite),
' pdf (violeta: imprime), peligro (rojo: anula/revierte), neutro (gris), salir.
Private Sub Estilo(ByVal c As Object, ByVal tipo As String)
    Select Case tipo
        Case "primario": c.BackColor = RGB(46, 117, 182)
        Case "ok": c.BackColor = RGB(56, 142, 60)
        Case "pdf": c.BackColor = RGB(112, 48, 160)
        Case "peligro": c.BackColor = RGB(192, 57, 43)
        Case "salir": c.BackColor = RGB(150, 40, 40)
        Case "tab": c.BackColor = RGB(222, 230, 240)
        Case Else: c.BackColor = RGB(96, 108, 118)
    End Select
    If tipo = "tab" Then c.ForeColor = RGB(31, 78, 121) Else c.ForeColor = RGB(255, 255, 255)
    c.Font.Bold = True
End Sub

Private Function Ctl(ByVal vbc As Object, ByVal prog As String, ByVal nombre As String, _
                     ByVal l As Double, ByVal t As Double, ByVal w As Double, ByVal h As Double, _
                     Optional ByVal cap As String = "", Optional ByVal pag As String = "", _
                     Optional ByVal tip As String = "") As Object
    Dim c As Object
    Set c = vbc.Designer.Controls.Add(prog, nombre, True)
    c.Left = l: c.Top = t: c.Width = w: c.Height = h
    On Error Resume Next
    c.Font.Name = "Segoe UI": c.Font.Size = 9
    If Len(cap) > 0 Then c.Caption = Ac(cap)
    If Len(tip) > 0 Then c.ControlTipText = Ac(tip)
    On Error GoTo 0
    c.Tag = pag
    Set Ctl = c
End Function

' Etiqueta transparente (texto de apoyo)
Private Function Etq(ByVal vbc As Object, ByVal nombre As String, ByVal l As Double, ByVal t As Double, _
                     ByVal w As Double, ByVal h As Double, ByVal txt As String, Optional ByVal pag As String = "") As Object
    Dim c As Object
    Set c = Ctl(vbc, FM_LBL, nombre, l, t, w, h, txt, pag)
    c.BackStyle = 0: c.ForeColor = RGB(64, 64, 64)
    Set Etq = c
End Function

' Barra de seccion dentro de una pestana
Private Sub Barra(ByVal vbc As Object, ByVal nombre As String, ByVal t As Double, ByVal txt As String, ByVal pag As String)
    Dim c As Object
    Set c = Ctl(vbc, FM_LBL, nombre, 10, t, 765, 17, "  " & txt, pag)
    c.BackStyle = 1: c.BackColor = RGB(221, 232, 245): c.ForeColor = RGB(31, 78, 121): c.Font.Bold = True
End Sub

' Banner de pestana (color propio por pantalla)
Private Sub Banner(ByVal vbc As Object, ByVal n As Long, ByVal txt As String)
    Dim c As Object
    Set c = Ctl(vbc, FM_LBL, "bnrP" & n, 0, 124, 790, 22, "   " & txt, "P" & n)
    c.BackStyle = 1: c.BackColor = ColorPagina(n): c.ForeColor = RGB(255, 255, 255): c.Font.Bold = True: c.Font.Size = 10
End Sub

' Etiqueta + control de entrada
Private Function Fld(ByVal vbc As Object, ByVal pag As String, ByVal etiqueta As String, ByVal nombre As String, _
                     ByVal prog As String, ByVal l As Double, ByVal t As Double, ByVal w As Double, _
                     Optional ByVal h As Double = 18, Optional ByVal tip As String = "") As Object
    Dim e As Object
    Set e = Etq(vbc, "lbl" & nombre, l, t, 95, 16, etiqueta, pag)
    Set Fld = Ctl(vbc, prog, nombre, l + 98, t - 2, w, h, "", pag, tip)
End Function

Private Function Btn(ByVal vbc As Object, ByVal nombre As String, ByVal l As Double, ByVal t As Double, _
                     ByVal w As Double, ByVal h As Double, ByVal cap As String, ByVal tipo As String, _
                     ByVal pag As String, Optional ByVal tip As String = "") As Object
    Dim c As Object
    Set c = Ctl(vbc, FM_BTN, nombre, l, t, w, h, cap, pag, tip)
    Estilo c, tipo
    Set Btn = c
End Function

Private Sub Inyectar(ByVal vbc As Object, ByVal archivo As String)
    If Len(Dir$(archivo)) = 0 Then Err.Raise vbObjectError + 800, , "No se encuentra " & archivo
    vbc.CodeModule.AddFromFile archivo
End Sub

Private Sub BuildLogin(ByVal dirV As String)
    Dim f As Object, c As Object
    Set f = NuevoForm("frmLogin", "SIC-MUNI - Inicio de sesi" & ChrW(243) & "n", 300, 215)
    Set c = Ctl(f, FM_LBL, "lblTitulo", 0, 0, 300, 50, "SIC-MUNI")
    c.BackColor = RGB(31, 78, 121): c.ForeColor = RGB(255, 255, 255): c.Font.Bold = True: c.Font.Size = 18
    c.TextAlign = 2: c.BackStyle = 1
    Set c = Ctl(f, FM_LBL, "lblSub", 0, 34, 300, 16, "Sistema Integrado de Contrataciones Municipales")
    c.BackStyle = 1: c.BackColor = RGB(31, 78, 121): c.ForeColor = RGB(200, 220, 240): c.TextAlign = 2: c.Font.Size = 8
    Set c = Etq(f, "lblUsuario", 20, 68, 70, 16, "Usuario")
    c.Font.Bold = True
    Ctl f, FM_TXT, "txtUsuario", 100, 66, 170, 20, "", "", "Escriba su usuario"
    Set c = Etq(f, "lblClave", 20, 98, 75, 16, "Contrase{n}a")
    c.Caption = Ac("Contrase{n}a"): c.Font.Bold = True
    Ctl f, FM_TXT, "txtPassword", 100, 96, 170, 20, "", "", "Escriba su contrase{n}a"
    Set c = Ctl(f, FM_LBL, "lblMsg", 20, 124, 260, 28, "")
    c.ForeColor = RGB(192, 57, 43): c.Font.Bold = True: c.BackStyle = 0
    Set c = Btn(f, "cmdIngresar", 100, 156, 85, 28, "Ingresar", "ok", "")
    c.Default = True
    Set c = Btn(f, "cmdCancelar", 192, 156, 78, 28, "Cancelar", "neutro", "")
    c.Cancel = True
    Inyectar f, dirV & "frmLogin.code.txt"
End Sub

Private Sub BuildConsolidado(ByVal dirV As String)
    Dim f As Object, c As Object

    Set f = NuevoForm("frmContratacionesConsolidado", "SIC-MUNI", 790, 600)

    ' ---------- Barra de titulo ----------
    Set c = Ctl(f, FM_LBL, "lblTitulo", 0, 0, 790, 34, "   SIC-MUNI   |   Contrataciones Menores")
    c.BackStyle = 1: c.BackColor = RGB(31, 78, 121): c.ForeColor = RGB(255, 255, 255): c.Font.Bold = True: c.Font.Size = 14
    Set c = Ctl(f, FM_LBL, "lblSesion", 380, 9, 300, 18, "")
    c.BackStyle = 0: c.ForeColor = RGB(214, 228, 245): c.TextAlign = 3
    Btn f, "cmdSalir", 690, 6, 90, 22, "Cerrar sesi{o}n", "salir", "", "Cierra su sesi{o}n y el formulario"

    ' ---------- Solicitud activa, estado y sugerencia ----------
    Set c = Etq(f, "lblSolTit", 10, 42, 80, 16, "Solicitud N{deg}:")
    c.Font.Bold = True
    Ctl f, FM_TXT, "txtSol", 90, 40, 140, 20, "", "", "Escriba el n{u}mero de la solicitud (ej. SOL-2026-000001) y pulse Cargar"
    Btn f, "cmdCargar", 236, 39, 70, 22, "Cargar", "primario", "", "Carga la solicitud escrita a la izquierda"
    Set c = Ctl(f, FM_LBL, "lblEstado", 314, 40, 466, 20, "  Sin solicitud cargada")
    c.BackStyle = 1: c.BackColor = RGB(150, 160, 170): c.ForeColor = RGB(255, 255, 255): c.Font.Bold = True
    Set c = Ctl(f, FM_LBL, "lblSugerencia", 10, 64, 770, 20, "")
    c.BackStyle = 1: c.BackColor = RGB(255, 248, 220): c.ForeColor = RGB(110, 80, 0)
    c.BorderStyle = 1: c.BorderColor = RGB(240, 215, 140)

    ' ---------- Pestanas ----------
    Btn f, "cmdP1", 10, 90, 150, 28, "1  Solicitud", "tab", "", "Crear la solicitud y agregar {i}tems"
    Btn f, "cmdP2", 165, 90, 150, 28, "2  Evaluaci{o}n CHB", "tab", "", "Cat{a}logo Compro Hecho en Bolivia y excepciones"
    Btn f, "cmdP3", 320, 90, 150, 28, "3  Cotizaciones", "tab", "", "Ofertas, cuadro comparativo y adjudicaci{o}n"
    Btn f, "cmdP4", 475, 90, 150, 28, "4  Presupuesto / C-31", "tab", "", "Reserva presupuestaria, SIGEP y reversiones"
    Btn f, "cmdP5", 630, 90, 150, 28, "5  Orden / Recepci{o}n", "tab", "", "Orden de Compra o Servicio, recepci{o}n y anulaciones"

    ' ====================== P1 SOLICITUD ======================
    Banner f, 1, "1  SOLICITUD   -   Registre lo que necesita comprar y env{i}elo a cotizaci{o}n"
    Barra f, "barP1a", 150, "DATOS DE LA SOLICITUD", "P1"
    Fld f, "P1", "DA", "txtDA", FM_TXT, 10, 174, 80, 18, "Direcci{o}n Administrativa (su c{o}digo)"
    Fld f, "P1", "UE", "txtUE", FM_TXT, 290, 174, 80, 18, "Unidad Ejecutora"
    Set c = Fld(f, "P1", "Justificaci{o}n", "txtJustificacion", FM_TXT, 10, 200, 520, 44, "Explique por qu{e} se necesita (m{i}nimo 20 caracteres)")
    c.MultiLine = True
    Btn f, "cmdCrearSolicitud", 640, 200, 135, 34, "Crear solicitud", "primario", "P1", "Crea la solicitud y le asigna su n{u}mero"
    Barra f, "barP1b", 254, "AGREGAR {I}TEMS", "P1"
    Fld f, "P1", "C{o}digo UNSPSC", "txtCodigo", FM_TXT, 10, 278, 90, 18, "Si el c{o}digo est{a} en el cat{a}logo CHB ver{a} una alerta"
    Set c = Ctl(f, FM_LBL, "lblAlertaCHB", 210, 272, 570, 30, "", "P1")
    c.Font.Bold = True: c.WordWrap = True: c.BackStyle = 0
    Fld f, "P1", "Descripci{o}n", "txtDescItem", FM_TXT, 10, 306, 330, 18, "Especificaciones t{e}cnicas claras, sin direccionar a un proveedor"
    Fld f, "P1", "Unidad", "txtUnidad", FM_TXT, 540, 306, 80, 18
    Fld f, "P1", "Cantidad", "txtCant", FM_TXT, 10, 332, 80, 18
    Fld f, "P1", "P. ref. unit. (Bs)", "txtPrecio", FM_TXT, 290, 332, 80, 18, "Precio referencial por unidad"
    Btn f, "cmdAgregarItem", 640, 328, 135, 28, "Agregar {i}tem", "primario", "P1", "Agrega el {i}tem a la solicitud"
    Barra f, "barP1c", 362, "{I}TEMS CARGADOS", "P1"
    Ctl f, FM_LST, "lstItems", 10, 382, 765, 128, "", "P1"
    Btn f, "cmdEnviarCot", 10, 520, 180, 32, "Enviar a cotizaci{o}n", "ok", "P1", "Cierra la edici{o}n y la env{i}a a cotizaci{o}n (ya no se podr{a}n agregar {i}tems)"
    Btn f, "cmdC1", 200, 520, 180, 32, "Imprimir C-1 (PDF)", "pdf", "P1", "Formulario de requerimiento y especificaciones t{e}cnicas"

    ' ====================== P2 EVALUACION CHB ======================
    Banner f, 2, "2  EVALUACI{O}N CHB   -   Cat{a}logo 'Compro Hecho en Bolivia' y excepciones"
    Barra f, "barP2a", 150, "{I}TEM A EVALUAR", "P2"
    Set c = Etq(f, "lblHintP2", 10, 172, 765, 30, "Para cada {i}tem que figura en el cat{a}logo: c{o}mprelo por cat{a}logo o, si no es posible, marque la casilla y registre la excepci{o}n autorizada.", "P2")
    c.WordWrap = True
    Fld f, "P2", "N{deg} de {i}tem", "txtItemCHB", FM_TXT, 10, 212, 60, 18, "N{u}mero de {i}tem que aparece en la lista de la pesta{n}a 1"
    Ctl f, FM_CHK, "chkFuera", 290, 210, 400, 20, "Comprar FUERA del cat{a}logo CHB (requiere excepci{o}n)", "P2", "Marque solo si se compra fuera del mercado virtual"
    Barra f, "barP2b", 244, "DATOS DE LA EXCEPCI{O}N (solo si compra fuera del cat{a}logo)", "P2"
    Fld f, "P2", "C{o}d. excepci{o}n", "txtCodExc", FM_TXT, 10, 268, 180, 18, "C{o}digo {U}nico de Excepci{o}n"
    Fld f, "P2", "N{deg} autoriz. MDPyEP", "txtNroAut", FM_TXT, 10, 296, 180, 18, "N{u}mero de la autorizaci{o}n expresa del Ministerio"
    Fld f, "P2", "Fecha autoriz.", "txtFechaAut", FM_TXT, 10, 324, 100, 18, "Fecha de la autorizaci{o}n (no puede ser futura)"
    Set c = Fld(f, "P2", "Justificaci{o}n", "txtJustExc", FM_TXT, 10, 352, 560, 110, "Raz{o}n t{e}cnica y legal (m{i}nimo 80 caracteres)")
    c.MultiLine = True
    Btn f, "cmdEvalCHB", 10, 476, 210, 32, "Registrar evaluaci{o}n CHB", "ok", "P2", "Guarda el resultado de este {i}tem"
    Btn f, "cmdDocExc", 230, 476, 240, 32, "Imprimir justificaci{o}n de excepci{o}n (PDF)", "pdf", "P2", "Reporte de excepci{o}n para el expediente"

    ' ====================== P3 COTIZACIONES ======================
    Banner f, 3, "3  COTIZACIONES   -   Registre las ofertas, eval{u}e el cuadro y adjudique"
    Barra f, "barP3a", 150, "REGISTRAR UNA OFERTA", "P3"
    Fld f, "P3", "NIT", "txtNIT", FM_TXT, 10, 174, 120, 18, "Solo n{u}meros (6 o m{a}s d{i}gitos)"
    Fld f, "P3", "Raz{o}n social", "txtRazon", FM_TXT, 290, 174, 230, 18
    Fld f, "P3", "Validez (fecha)", "txtValidez", FM_TXT, 10, 202, 100, 18, "Fecha hasta la que vale la oferta"
    Fld f, "P3", "Monto cotizado", "txtMontoCot", FM_TXT, 290, 202, 100, 18, "Monto total de la oferta (Bs)"
    Ctl f, FM_CHK, "chkCumple", 520, 202, 150, 20, "Cumple t{e}cnicamente", "P3", "Marque si cumple las especificaciones"
    Fld f, "P3", "Recibida el", "txtRecibida", FM_TXT, 10, 230, 130, 18, "Opcional: fecha y hora en que el proveedor entreg{o} su oferta (dd/mm/aaaa hh:mm). Vac{i}o = ahora. Sirve para desempatar ofertas de igual precio"
    Set c = Etq(f, "lblHintRec", 250, 232, 400, 16, "(opcional; vac{i}o = ahora. Desempata ofertas de igual precio)", "P3")
    c.Font.Size = 8: c.ForeColor = RGB(110, 110, 110)
    Btn f, "cmdRegCot", 640, 174, 135, 34, "Registrar oferta", "primario", "P3", "Guarda la oferta"
    Barra f, "barP3b", 258, "OFERTAS REGISTRADAS   (seleccione una fila para adjudicar)", "P3"
    Ctl f, FM_LST, "lstCot", 10, 278, 765, 170, "", "P3"
    Btn f, "cmdEvaluar", 10, 458, 180, 32, "Evaluar cuadro", "ok", "P3", "Marca la oferta recomendada (menor precio que cumple; empate = primera recepci{o}n)"
    Btn f, "cmdCuadro", 200, 458, 210, 32, "Imprimir cuadro comparativo (PDF)", "pdf", "P3"
    Btn f, "cmdAdjudicar", 420, 458, 200, 32, "Adjudicar seleccionada", "ok", "P3", "Requiere reserva presupuestaria (C-31) vigente"
    Set c = Etq(f, "lblHintP3", 10, 500, 765, 30, "Regla: gana la oferta de menor precio que cumple t{e}cnicamente. Si dos ofertas igualan el precio, se adjudica a la que se recibi{o} primero (fecha y hora de recepci{o}n).", "P3")
    c.WordWrap = True: c.Font.Size = 8: c.ForeColor = RGB(110, 110, 110)

    ' ====================== P4 PRESUPUESTO / C-31 ======================
    Banner f, 4, "4  PRESUPUESTO / C-31   -   Reserve el presupuesto, as{o}ciele el N{deg} de SIGEP y revierta si corresponde"
    Barra f, "barP4a", 150, "IMPUTACI{O}N PRESUPUESTARIA (una l{i}nea por partida)", "P4"
    Fld f, "P4", "Programa", "txtProg", FM_TXT, 10, 174, 80, 18
    Fld f, "P4", "Proyecto", "txtProy", FM_TXT, 290, 174, 80, 18
    Fld f, "P4", "Act./Obra", "txtAct", FM_TXT, 10, 200, 80, 18
    Fld f, "P4", "Fuente", "txtFte", FM_TXT, 290, 200, 80, 18
    Fld f, "P4", "Organismo", "txtOrg", FM_TXT, 10, 226, 80, 18
    Fld f, "P4", "Partida", "txtPartida", FM_TXT, 290, 226, 80, 18, "Objeto del gasto"
    Fld f, "P4", "Importe (Bs)", "txtImporte", FM_TXT, 10, 252, 100, 18
    Btn f, "cmdSaldo", 500, 174, 150, 28, "Consultar saldo", "primario", "P4", "Muestra el saldo disponible de la partida escrita"
    Btn f, "cmdAddLinea", 500, 208, 150, 28, "Agregar l{i}nea", "primario", "P4", "Agrega la l{i}nea a la lista del preventivo"
    Set c = Ctl(f, FM_LBL, "lblSaldo", 500, 244, 280, 20, "", "P4")
    c.Font.Bold = True: c.BackStyle = 0: c.ForeColor = RGB(31, 78, 121)
    Barra f, "barP4b", 276, "L{I}NEAS DEL PREVENTIVO", "P4"
    Ctl f, FM_LST, "lstLineas", 10, 296, 765, 70, "", "P4"
    Btn f, "cmdEmitirC31", 10, 372, 220, 30, "Emitir C-31 Preventivo", "ok", "P4", "Reserva el presupuesto (valida el saldo de todas las l{i}neas)"
    Barra f, "barP4c", 410, "ASOCIAR AL SIGEP E IMPRIMIR", "P4"
    Fld f, "P4", "N{deg} C-31 interno", "txtNroC31", FM_TXT, 10, 434, 140, 18, "Se completa al emitir; escr{i}balo para consultar uno anterior"
    Fld f, "P4", "N{deg} C-31 SIGEP", "txtNroSigep", FM_TXT, 290, 434, 120, 18, "N{u}mero del C-31 registrado en SIGEP (solo n{u}meros)"
    Btn f, "cmdAsociar", 540, 430, 120, 26, "Asociar C-31", "ok", "P4", "Asocia el n{u}mero de SIGEP al preventivo"
    Btn f, "cmdDocC31", 668, 430, 107, 26, "C-31 (PDF)", "pdf", "P4"
    Barra f, "barP4d", 464, "REVERSIONES (devuelven saldo al presupuesto)", "P4"
    Fld f, "P4", "L{i}nea a revertir", "txtLineaRev", FM_TXT, 10, 488, 60, 18
    Fld f, "P4", "Monto a revertir", "txtMontoRev", FM_TXT, 290, 488, 100, 18
    Set c = Fld(f, "P4", "Motivo", "txtMotivoRev", FM_TXT, 10, 514, 520, 40, "Obligatorio (m{i}nimo 10 caracteres)")
    c.MultiLine = True
    Btn f, "cmdRevParcial", 640, 486, 135, 30, "Reversi{o}n parcial", "peligro", "P4", "Revierte parte de una l{i}nea"
    Btn f, "cmdRevTotal", 640, 522, 135, 30, "Reversi{o}n total", "peligro", "P4", "Revierte todo el preventivo (pide confirmaci{o}n)"

    ' ====================== P5 ORDEN / RECEPCION ======================
    Banner f, 5, "5  ORDEN / RECEPCI{O}N   -   Emita la Orden, registre la recepci{o}n y gestione anulaciones"
    Barra f, "barP5a", 150, "ORDEN DE COMPRA O DE SERVICIO", "P5"
    Fld f, "P5", "Tipo", "cboTipo", FM_CBO, 10, 174, 120, 18, "COMPRA para bienes, SERVICIO para servicios"
    Fld f, "P5", "CUCE (SICOES)", "txtCUCE", FM_TXT, 290, 174, 180, 18, "C{o}digo {U}nico de Contrataci{o}n Estatal"
    Fld f, "P5", "Plazo (d{i}as)", "txtPlazo", FM_TXT, 10, 202, 60, 18, "D{i}as calendario desde la emisi{o}n"
    Fld f, "P5", "Lugar", "txtLugar", FM_TXT, 10, 230, 560, 18, "Lugar de entrega o de prestaci{o}n"
    Btn f, "cmdGenOrden", 10, 260, 190, 32, "Generar Orden", "ok", "P5", "Requiere adjudicaci{o}n y C-31 asociado a SIGEP"
    Set c = Ctl(f, FM_LBL, "lblNroOrden", 210, 267, 160, 20, "", "P5")
    c.Font.Bold = True: c.BackStyle = 0: c.ForeColor = RGB(56, 118, 29): c.Font.Size = 10
    Btn f, "cmdDocOrden", 380, 260, 190, 32, "Imprimir Orden (PDF)", "pdf", "P5"
    Barra f, "barP5b", 302, "RECEPCI{O}N Y ACTA", "P5"
    Fld f, "P5", "Fecha recepci{o}n", "txtFechaRec", FM_TXT, 10, 326, 100, 18, "No puede ser anterior a la Orden ni futura"
    Ctl f, FM_CHK, "chkConforme", 290, 324, 220, 20, "Recepci{o}n CONFORME", "P5", "Marque si todo se recibi{o} conforme; si no, detalle las observaciones"
    Set c = Fld(f, "P5", "Observaciones", "txtObsRec", FM_TXT, 10, 352, 560, 40, "Obligatorio si la recepci{o}n NO es conforme")
    c.MultiLine = True
    Btn f, "cmdRecepcion", 10, 400, 190, 32, "Registrar recepci{o}n", "ok", "P5", "Calcula d{i}as de retraso y multa"
    Set c = Ctl(f, FM_LBL, "lblNroActa", 210, 407, 160, 20, "", "P5")
    c.Font.Bold = True: c.BackStyle = 0: c.ForeColor = RGB(56, 118, 29): c.Font.Size = 10
    Btn f, "cmdActa", 380, 400, 190, 32, "Imprimir acta (PDF)", "pdf", "P5"
    Barra f, "barP5c", 444, "ANULACIONES", "P5"
    Set c = Fld(f, "P5", "Motivo anulaci{o}n", "txtMotivoAnu", FM_TXT, 10, 468, 560, 40, "Obligatorio (m{i}nimo 10 caracteres)")
    c.MultiLine = True
    Btn f, "cmdAnularOrden", 10, 516, 190, 32, "Anular Orden", "peligro", "P5", "No se puede si ya hay recepci{o}n conforme"
    Btn f, "cmdAnularSol", 210, 516, 190, 32, "Anular solicitud", "peligro", "P5", "Cancela todo el tr{a}mite (sin Orden ni C-31 vigentes)"

    Inyectar f, dirV & "frmContratacionesConsolidado.code.txt"
End Sub
