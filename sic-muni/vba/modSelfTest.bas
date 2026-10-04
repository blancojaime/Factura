Attribute VB_Name = "modSelfTest"
'==============================================================================
' SIC-MUNI - modSelfTest
' Bateria de pruebas automaticas de la logica de negocio (sin interfaz).
'   modSelfTest.EjecutarPruebas      -> corre todo y escribe resultado_pruebas.txt
'   modSelfTest.LimpiarDatosPrueba   -> borra los datos creados por las pruebas
' Fuerza sesiones de prueba (usuarios t_us / t_rc / t_pf) y usa los datos DEMO.
'==============================================================================
Option Explicit

Private Const PWD_OK As String = "Prueba#Segura2026"
Private m_log As String
Private m_ok As Long
Private m_fail As Long
Private m_id1 As String, m_nro1 As String, m_oc1 As String, m_oc2 As String, m_rec As String

Private Sub Reg(ByVal nombre As String, ByVal ok As Boolean, Optional ByVal detalle As String = "")
    If ok Then
        m_ok = m_ok + 1
        m_log = m_log & "PASS  " & nombre & vbCrLf
    Else
        m_fail = m_fail + 1
        m_log = m_log & "FAIL  " & nombre
        If Len(detalle) > 0 Then m_log = m_log & "  -> " & detalle
        m_log = m_log & vbCrLf
    End If
End Sub

Private Sub RegEx(ByVal nombre As String)
    Reg nombre & " (error inesperado)", False, "[" & Err.Number & "] " & Err.Description
    Err.Clear
End Sub

Private Sub Sesion(ByVal usr As String, ByVal rol As String)
    g_Usuario = usr: g_Rol = rol: g_Nombre = usr: g_DA = "01": g_UltimaActividad = Now
End Sub

Private Function Estado(ByVal hoja As String, ByVal hdrKey As String, ByVal key As String, ByVal hdr As String) As String
    Dim r As Long
    r = FindRow(WS(hoja), hdrKey, key)
    If r > 0 Then Estado = CStr(GetV(WS(hoja), r, hdr))
End Function

Private Function NombreVal(ByVal nm As String) As Variant
    NombreVal = ThisWorkbook.Names(nm).RefersToRange.Cells(1, 1).Value
End Function

'------------------------------------------------------------------------------
Public Function EjecutarPruebas() As Long
    Dim ruta As String, f As Integer
    m_log = "SIC-MUNI - Resultado de pruebas  " & Format$(Now, "yyyy-mm-dd hh:nn:ss") & vbCrLf & String(70, "-") & vbCrLf
    m_ok = 0: m_fail = 0
    SetSilent True
    On Error GoTo EH
    PrepararDatos
    T_Hash
    T_Roles
    T_Reglas
    T_CHB
    T_Flujo
    T_Reversion
    T_DocC1
    T_DocPDF
    T_DocCuadro
    T_DocExcepcion
    T_DocC31
    T_DocOrden
    T_DocActa
    T_Import
    GoTo Fin
EH:
    RegEx "Preparacion/ejecucion"
Fin:
    g_Usuario = "": g_Rol = ""
    m_log = m_log & String(70, "-") & vbCrLf & "RESUMEN: PASS=" & m_ok & "  FAIL=" & m_fail & vbCrLf
    ruta = ThisWorkbook.Path & "\resultado_pruebas.txt"
    f = FreeFile
    Open ruta For Output As #f
    Print #f, m_log
    Close #f
    EjecutarPruebas = m_fail
End Function

Private Sub PrepararDatos()
    If FindRow(WS(SH_CAT), "CodigoUNSPSC", "44121600") = 0 Then modSetup.CargarDatosDemo
    Sesion "test", ROL_ADM
    If FindRow(WS(SH_AUTH), "Usuario", "t_us") = 0 Then CrearUsuario "t_us", PWD_OK, "Test US", ROL_US, "01"
    If FindRow(WS(SH_AUTH), "Usuario", "t_rc") = 0 Then CrearUsuario "t_rc", PWD_OK, "Test RC", ROL_RC, "01"
    If FindRow(WS(SH_AUTH), "Usuario", "t_pf") = 0 Then CrearUsuario "t_pf", PWD_OK, "Test PF", ROL_PF, "01"
End Sub

Private Sub T_Hash()
    Dim st As String
    On Error GoTo EH
    Reg "SHA-256 de 'a' coincide con el valor conocido", SHA256Hex("a") = "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"
    st = BuildStoredHash(PWD_OK)
    Reg "Hash con sal: verifica contrasena correcta", VerifyPassword(PWD_OK, st)
    Reg "Hash con sal: rechaza contrasena incorrecta", Not VerifyPassword("otraClave#1", st)
    Reg "Politica: rechaza clave corta", Len(PasswordPolicyError("Ab1")) > 0
    Reg "Politica: acepta clave valida", Len(PasswordPolicyError(PWD_OK)) = 0
    Exit Sub
EH: RegEx "T_Hash"
End Sub

Private Sub T_Roles()
    Dim msg As String, i As Long
    On Error GoTo EH
    Sesion "t_us", ROL_US
    Reg "RBAC: US no puede emitir C-31", Not PuedeHacer(P_C31)
    Reg "RBAC: US puede crear solicitud", PuedeHacer(P_SOLICITUD)
    Sesion "t_pf", ROL_PF
    Reg "RBAC: PF puede emitir C-31", PuedeHacer(P_C31)
    Reg "RBAC: PF no puede emitir Orden", Not PuedeHacer(P_ORDEN)
    Sesion "t_rc", ROL_RC
    Reg "RBAC: RC puede adjudicar y no puede revertir C-31", PuedeHacer(P_ADJUDICAR) And Not PuedeHacer(P_REVERSION)
    Sesion "t_adm", ROL_ADM
    Reg "RBAC: ADM no transacciona (sin ORDEN_EMIT)", Not PuedeHacer(P_ORDEN) And PuedeHacer(P_USUARIOS)
    Logout
    Reg "Login correcto (t_us)", Login("t_us", PWD_OK, msg) And g_Rol = ROL_US, msg
    Logout
    For i = 1 To 3: Call Login("t_rc", "claveMala1", msg): Next i
    Reg "Bloqueo tras 3 intentos fallidos", Not Login("t_rc", PWD_OK, msg), msg
    Sesion "t_adm", ROL_ADM
    DesbloquearUsuario "t_rc"
    Logout
    Reg "Desbloqueo por ADM y login posterior", Login("t_rc", PWD_OK, msg), msg
    Logout
    Reg "Sin sesion: PuedeHacer es falso", Not PuedeHacer(P_DOCS)
    Exit Sub
EH: RegEx "T_Roles"
End Sub

Private Sub T_Reglas()
    On Error GoTo EH
    Reg "Modalidad 15.000 = contratacion menor", ModalidadPorMonto(15000) = "CONTRATACION MENOR", ModalidadPorMonto(15000)
    Reg "Modalidad 30.000 exige cuadro comparativo", ModalidadPorMonto(30000) Like "*CUADRO*", ModalidadPorMonto(30000)
    Reg "Modalidad 60.000 fuera de alcance", ModalidadPorMonto(60000) Like "FUERA*", ModalidadPorMonto(60000)
    Reg "Cotizaciones requeridas: 1 hasta 20.000, 3 sobre 20.000", CotizacionesRequeridas(15000) = 1 And CotizacionesRequeridas(30000) = 3
    Reg "Literal 1.234,50", MontoLiteral(1234.5) = "Son: MIL DOSCIENTOS TREINTA Y CUATRO 50/100 BOLIVIANOS", MontoLiteral(1234.5)
    Reg "Literal 21.000", MontoLiteral(21000) = "Son: VEINTIUN MIL 00/100 BOLIVIANOS", MontoLiteral(21000)
    Reg "Literal 100.000", MontoLiteral(100000) = "Son: CIEN MIL 00/100 BOLIVIANOS", MontoLiteral(100000)
    Reg "Literal 1.500.000", MontoLiteral(1500000) = "Son: UN MILLON QUINIENTOS MIL 00/100 BOLIVIANOS", MontoLiteral(1500000)
    Reg "Redondeo comercial 2.675 -> 2.68", RoundM(2.675) = 2.68
    Exit Sub
EH: RegEx "T_Reglas"
End Sub

Private Sub T_CHB()
    Dim r As CHBResultado
    On Error GoTo EH
    r = ConsultarCHB("44121600")
    Reg "CHB: codigo en catalogo con ficha vigente", r.EnCatalogo And r.FichaVigente
    r = ConsultarCHB("56101500")
    Reg "CHB: codigo en catalogo sin ficha vigente", r.EnCatalogo And Not r.FichaVigente
    r = ConsultarCHB("99999999")
    Reg "CHB: codigo fuera de catalogo", Not r.EnCatalogo
    Reg "Excepcion incompleta es rechazada", Len(ValidarExcepcion("", "corta", "", Empty)) > 0
    Reg "Excepcion completa es aceptada", Len(ValidarExcepcion("EXC-2026-001", String(90, "x"), "MDPYEP-0001", Date - 1)) = 0
    Reg "Excepcion con fecha futura es rechazada", Len(ValidarExcepcion("EXC-2026-001", String(90, "x"), "MDPYEP-0001", Date + 5)) > 0
    Exit Sub
EH: RegEx "T_CHB"
End Sub

Private Sub T_Flujo()
    Dim id As String, a As String, cot As String, nro As String, oc As String, rs As String
    Dim L(1 To 1) As LineaC31, rO As Long, rSh As Long, rP As Long
    On Error GoTo EH
    ' --- US: solicitud ---
    Sesion "t_us", ROL_US
    id = CrearSolicitud("01", "001", "Adquisicion de material de oficina para pruebas del sistema")
    m_id1 = id
    Reg "Solicitud creada con correlativo", id Like "SOL-*", id
    a = AgregarItem(id, "44121600", "Papel bond tamano carta", 10, "Paquete", 50)
    Reg "Alerta CHB al agregar item de catalogo", Len(a) > 0
    a = AgregarItem(id, "56101500", "Escritorio metalico", 2, "Unidad", 100)
    Reg "Alerta CHB item sin ficha", Len(a) > 0
    Reg "Monto referencial = 700", CDbl(GetV(WS(SH_SOL), FindRow(WS(SH_SOL), "ID_Solicitud", id), "MontoReferencial")) = 700
    EnviarACotizacion id
    Reg "Estado EN_COTIZACION", Estado(SH_SOL, "ID_Solicitud", id, "Estado") = "EN_COTIZACION"
    ' --- RC: CHB, cotizacion, cuadro ---
    Sesion "t_rc", ROL_RC
    Reg "Orden bloqueada mientras CHB este pendiente", Len(ValidarSolicitudParaOrden(id)) > 0
    a = EvaluarItemCHB(id, 1, False, "", "", "", Empty)
    Reg "Item 1 por catalogo = SI", CStr(GetV(WS(SH_DET), FilaItem(id, 1), "CumpleCHB")) = "SI"
    a = EvaluarItemCHB(id, 2, True, "EXC", "corta", "", Empty)
    Reg "Item 2: excepcion incompleta queda en NO", CStr(GetV(WS(SH_DET), FilaItem(id, 2), "CumpleCHB")) = "NO" And Len(a) > 0
    a = EvaluarItemCHB(id, 2, True, "EXC-2026-001", String(90, "x"), "MDPYEP-0001", Date - 1)
    Reg "Item 2: excepcion completa = EXCEPCION", CStr(GetV(WS(SH_DET), FilaItem(id, 2), "CumpleCHB")) = "EXCEPCION"
    Reg "CHB habilitado para Orden", Len(ValidarSolicitudParaOrden(id)) = 0, ValidarSolicitudParaOrden(id)
    cot = RegistrarCotizacion(id, "1234567", "PROVEEDOR PRUEBA SRL", Date + 30, 650, True)
    Reg "Cotizacion registrada", cot Like "COT-*", cot
    rs = EvaluarCuadro(id)
    Reg "Cuadro recomienda la oferta", InStr(rs, "Recomendada") > 0, rs
    ' --- PF: C-31 ---
    Sesion "t_pf", ROL_PF
    L(1).Programa = "01": L(1).Proyecto = "0000": L(1).ActObra = "001"
    L(1).Fuente = "20": L(1).Organismo = "230": L(1).Partida = "31120"
    L(1).Importe = 999999
    On Error Resume Next
    nro = EmitirC31(id, L)
    Reg "C-31 rechazado por saldo insuficiente", Err.Number <> 0 And InStr(Err.Description, "Saldo insuficiente") > 0, Err.Description
    Err.Clear
    On Error GoTo EH
    L(1).Importe = 700
    nro = EmitirC31(id, L): m_nro1 = nro
    Reg "C-31 emitido", nro Like "C31P-*", nro
    rP = FilaPresupuesto("01", "001", L(1))
    Reg "Presupuesto: comprometido = 700", CDbl(GetV(WS(SH_PRE), rP, "PreventivoComprometido")) = 700
    Reg "Presupuesto: saldo disponible = 99.300", SaldoDisponible("01", "001", L(1)) = 99300
    ' --- RC: adjudicar y orden ---
    Sesion "t_rc", ROL_RC
    Adjudicar id, cot
    Reg "Solicitud ADJUDICADA", Estado(SH_SOL, "ID_Solicitud", id, "Estado") = "ADJUDICADA"
    On Error Resume Next
    oc = GenerarOrden(id, "COMPRA", "TEST-CUCE-001", 10, "Almacen Municipal")
    Reg "Orden exige C-31 asociado a SIGEP", Err.Number <> 0 And InStr(Err.Description, "Asocie primero") > 0, Err.Description
    Err.Clear
    On Error GoTo EH
    Sesion "t_pf", ROL_PF
    AsociarC31SIGEP nro, "123456"
    Reg "C-31 asociado a SIGEP", Estado(SH_C31, "NroInterno", nro, "Estado") = "ASOCIADO"
    Sesion "t_rc", ROL_RC
    oc = GenerarOrden(id, "COMPRA", "TEST-CUCE-001", 10, "Almacen Municipal"): m_oc1 = oc
    Reg "Orden emitida", oc Like "OC-*", oc
    Reg "Solicitud ORDEN_EMITIDA", Estado(SH_SOL, "ID_Solicitud", id, "Estado") = "ORDEN_EMITIDA"
    Sesion "t_pf", ROL_PF
    On Error Resume Next
    RevertirTotal nro, "Intento de reversion con orden vigente"
    Reg "No se revierte C-31 con Orden vigente", Err.Number <> 0, Err.Description
    Err.Clear
    On Error GoTo EH
    ' --- anulacion y reemision ---
    Sesion "t_rc", ROL_RC
    AnularOrden oc, "Prueba de anulacion de orden"
    Reg "Orden ANULADA", Estado(SH_ORD, "NroOrden", oc, "EstadoOrden") = "ANULADA"
    Reg "Solicitud vuelve a ADJUDICADA", Estado(SH_SOL, "ID_Solicitud", id, "Estado") = "ADJUDICADA"
    oc = GenerarOrden(id, "COMPRA", "TEST-CUCE-002", 10, "Almacen Municipal"): m_oc2 = oc
    Reg "Segunda Orden emitida tras anular", oc Like "OC-*" And oc <> m_oc1, oc
    ' --- recepcion con retraso: forzamos emision 20 dias atras, plazo 10 => 10 dias, multa 650*3/1000*10 = 19,50
    rO = FindRow(WS(SH_ORD), "NroOrden", oc)
    SetV WS(SH_ORD), rO, "FechaEmision", Date - 20
    m_rec = RegistrarRecepcion(oc, Date, True, "")
    Reg "Recepcion conforme registrada", m_rec Like "REC-*", m_rec
    Reg "Recepcion: 10 dias de retraso", CLng(Estado(SH_REC, "NroRecepcion", m_rec, "DiasRetraso")) = 10
    Reg "Recepcion: multa 19,50", CDbl(Estado(SH_REC, "NroRecepcion", m_rec, "MontoMulta")) = 19.5
    Reg "Orden RECIBIDA", Estado(SH_ORD, "NroOrden", oc, "EstadoOrden") = "RECIBIDA"
    On Error Resume Next
    AnularOrden oc, "Intento de anular orden recibida"
    Reg "No se anula una Orden con recepcion conforme", Err.Number <> 0, Err.Description
    Err.Clear
    Exit Sub
EH: RegEx "T_Flujo"
End Sub

Private Sub T_Reversion()
    Dim id As String, cot As String, nro As String, L(1 To 1) As LineaC31, rP As Long
    On Error GoTo EH
    Sesion "t_us", ROL_US
    id = CrearSolicitud("01", "001", "Segunda solicitud para probar reversiones de preventivo")
    AgregarItem id, "44121600", "Papel bond tamano oficio", 2, "Paquete", 50
    EnviarACotizacion id
    Sesion "t_rc", ROL_RC
    EvaluarItemCHB id, 1, False, "", "", "", Empty
    cot = RegistrarCotizacion(id, "7654321", "OTRO PROVEEDOR SRL", Date + 15, 90, True)
    EvaluarCuadro id
    Sesion "t_pf", ROL_PF
    L(1).Programa = "01": L(1).Proyecto = "0000": L(1).ActObra = "001"
    L(1).Fuente = "20": L(1).Organismo = "230": L(1).Partida = "31120": L(1).Importe = 100
    nro = EmitirC31(id, L)
    rP = FilaPresupuesto("01", "001", L(1))
    Reg "Reversion: comprometido sube a 800", CDbl(GetV(WS(SH_PRE), rP, "PreventivoComprometido")) = 800
    RevertirParcial nro, 1, 40, "Prueba reversion parcial"
    Reg "Reversion parcial devuelve 40 (comprometido 760)", CDbl(GetV(WS(SH_PRE), rP, "PreventivoComprometido")) = 760
    Reg "Estado REVERTIDO_PARCIAL", Estado(SH_C31, "NroInterno", nro, "Estado") = "REVERTIDO_PARCIAL"
    RevertirTotal nro, "Prueba reversion total"
    Reg "Reversion total devuelve el saldo (comprometido 700)", CDbl(GetV(WS(SH_PRE), rP, "PreventivoComprometido")) = 700
    Reg "Estado REVERTIDO_TOTAL", Estado(SH_C31, "NroInterno", nro, "Estado") = "REVERTIDO_TOTAL"
    Reg "Solicitud vuelve a EVALUADA", Estado(SH_SOL, "ID_Solicitud", id, "Estado") = "EVALUADA"
    On Error Resume Next
    RevertirParcial nro, 1, 10, "Reversion sobre preventivo ya revertido"
    Reg "No se revierte un C-31 ya revertido", Err.Number <> 0, Err.Description
    Err.Clear
    On Error GoTo EH
    Sesion "t_rc", ROL_RC
    AnularSolicitud id, "Anulacion de solicitud de prueba"
    Reg "Solicitud anulada", Estado(SH_SOL, "ID_Solicitud", id, "Estado") = "ANULADA"
    On Error Resume Next
    AnularSolicitud m_id1, "Intento de anular solicitud con orden"
    Reg "No se anula una solicitud con Orden vigente", Err.Number <> 0, Err.Description
    Err.Clear
    Exit Sub
EH: RegEx "T_Reversion"
End Sub

'--- Documentos (se llenan sin exportar; el PDF se prueba aparte) ---
Private Sub T_DocC1()
    On Error GoTo EH
    Sesion "t_rc", ROL_RC
    GenerarC1 m_id1, False
    Application.Calculate
    Reg "C-1: datos volcados (N de solicitud)", CStr(NombreVal("RQ_Solicitud")) = m_id1
    Reg "C-1: total por formula = 700", Round(CDbl(WS(DOC_C1).Range("G26").Value), 2) = 700, CStr(WS(DOC_C1).Range("G26").Value)
    Reg "C-1: filas sobrantes ocultas", WS(DOC_C1).Rows(13).Hidden And Not WS(DOC_C1).Rows(12).Hidden
    Exit Sub
EH: RegEx "T_DocC1"
End Sub

Private Sub T_DocPDF()
    Dim p As String
    On Error GoTo EH
    Sesion "t_rc", ROL_RC
    p = GenerarC1(m_id1, True)
    Reg "Exportacion a PDF del C-1", Len(p) > 0 And Len(Dir$(p)) > 0, p
    Exit Sub
EH: RegEx "T_DocPDF"
End Sub

Private Sub T_DocCuadro()
    On Error GoTo EH
    Sesion "t_rc", ROL_RC
    GenerarCuadroComparativo m_id1, False
    Application.Calculate
    Reg "Cuadro: recomendacion consignada", CStr(NombreVal("CC_Recomendacion")) Like "Se recomienda*"
    Reg "Cuadro: menor oferta habil = 650", Round(CDbl(WS(DOC_CUADRO).Range("F20").Value), 2) = 650, CStr(WS(DOC_CUADRO).Range("F20").Value)
    Exit Sub
EH: RegEx "T_DocCuadro"
End Sub

Private Sub T_DocExcepcion()
    On Error GoTo EH
    Sesion "t_rc", ROL_RC
    GenerarJustificacionExcepcion m_id1, False
    Reg "Excepcion CHB: lista el item 2", CLng(NombreVal("EX_ItemsIni")) = 2
    Exit Sub
EH: RegEx "T_DocExcepcion"
End Sub

Private Sub T_DocC31()
    On Error GoTo EH
    Sesion "t_pf", ROL_PF
    GenerarPreventivoC31 m_nro1, False
    Application.Calculate
    Reg "C-31: numero y total por formula = 700", CStr(NombreVal("PV_Nro")) = m_nro1 And Round(CDbl(WS(DOC_C31).Range("H21").Value), 2) = 700, CStr(WS(DOC_C31).Range("H21").Value)
    Exit Sub
EH: RegEx "T_DocC31"
End Sub

Private Sub T_DocOrden()
    On Error GoTo EH
    Sesion "t_rc", ROL_RC
    GenerarDocOrden m_oc2, False
    Application.Calculate
    Reg "Orden: monto = 650", CDbl(NombreVal("OC_Monto")) = 650
    Reg "Orden: clausula de plazo usa los rangos con nombre", InStr(CStr(WS(DOC_ORDEN).Range("A32").Value), "10 dias") > 0, CStr(WS(DOC_ORDEN).Range("A32").Value)
    Reg "Orden: clausula de penalidad usa parametros CONFIG", InStr(CStr(WS(DOC_ORDEN).Range("A34").Value), " por mil") > 0, CStr(WS(DOC_ORDEN).Range("A34").Value)
    On Error Resume Next
    GenerarDocOrden m_oc1, False
    Reg "Orden anulada no se imprime", Err.Number <> 0, Err.Description
    Err.Clear
    Exit Sub
EH: RegEx "T_DocOrden"
End Sub

Private Sub T_DocActa()
    On Error GoTo EH
    Sesion "t_rc", ROL_RC
    GenerarActaRecepcion m_rec, False
    Application.Calculate
    Reg "Acta: dias de retraso = 10", CLng(NombreVal("AR_Dias")) = 10
    Reg "Acta: neto a pagar por formula = 630,50", Round(CDbl(WS(DOC_ACTA).Range("C11").Value), 2) = 630.5, CStr(WS(DOC_ACTA).Range("C11").Value)
    Exit Sub
EH: RegEx "T_DocActa"
End Sub

Private Sub T_Import()
    Dim ruta As String, f As Integer, res As String, rr As Long
    On Error GoTo EH
    Sesion "t_adm", ROL_ADM
    ruta = Environ$("TEMP") & "\sicmuni_test_cat.csv"
    f = FreeFile
    Open ruta For Output As #f
    Print #f, "CodigoUNSPSC;Descripcion;Unidad;FichaTecnicaCHB;Tipo;Vigencia;RequiereAutorizacionMDPyEP"
    Print #f, "99000001;""DEMO item; con punto y coma"";Unidad;SI;Bien;2030-12-31;NO"
    Print #f, "44121600;""DEMO - Suministros de oficina ACTUALIZADO"";Unidad;SI;Bien;2030-12-31;SI"
    Close #f
    res = modImport.ImportarCSV(SH_CAT, ruta, "CodigoUNSPSC", "CodigoUNSPSC|Descripcion|Unidad|FichaTecnicaCHB|Tipo|Vigencia|RequiereAutorizacionMDPyEP", True)
    Reg "Import catalogo: 1 nuevo y 1 actualizado", InStr(res, "Nuevos: 1") > 0 And InStr(res, "Actualizados: 1") > 0, res
    rr = FindRow(WS(SH_CAT), "CodigoUNSPSC", "99000001")
    Reg "Import catalogo: campo con ; entre comillas", rr > 0 And InStr(CStr(GetV(WS(SH_CAT), rr, "Descripcion")), "; con") > 0
    Reg "Import catalogo: upsert actualiza la descripcion", InStr(CStr(GetV(WS(SH_CAT), FindRow(WS(SH_CAT), "CodigoUNSPSC", "44121600"), "Descripcion")), "ACTUALIZADO") > 0
    Kill ruta
    f = FreeFile
    Open ruta For Output As #f
    Print #f, "Gestion,DA,UE,Programa,Proyecto,ActObra,Fuente,Organismo,Partida_ObjetoGasto,DescripcionPartida,PresupuestoAprobado"
    Print #f, CfgVal("Gestion") & ",01,001,01,0000,001,20,230,31130,""DEMO - Otra partida"",5000.50"
    Print #f, CfgVal("Gestion") & ",01,001,01,0000,001,20,230,31120,""DEMO - Duplicada"",1"
    Close #f
    res = modImport.ImportarCSV(SH_PRE, ruta, "Gestion|DA|UE|Programa|Proyecto|ActObra|Fuente|Organismo|Partida_ObjetoGasto", _
          "Gestion|DA|UE|Programa|Proyecto|ActObra|Fuente|Organismo|Partida_ObjetoGasto|DescripcionPartida|PresupuestoAprobado", False)
    Reg "Import presupuesto: 1 nuevo y 1 duplicado rechazado", InStr(res, "Nuevos: 1") > 0 And InStr(res, "Rechazados: 1") > 0, res
    Kill ruta
    Exit Sub
EH: RegEx "T_Import"
End Sub

'------------------------------------------------------------------------------
' Deja la base lista para produccion: borra todo lo operativo, los datos DEMO
' y los usuarios de prueba (t_*). NO toca CONFIG ni el administrador.
'------------------------------------------------------------------------------
Public Sub LimpiarDatosPrueba()
    Dim nm As Variant, sh As Worksheet, r As Long
    For Each nm In Array(SH_SOL, SH_DET, SH_COT, SH_ORD, SH_C31, SH_C31D, SH_REC, SH_AUD, SH_SEQ)
        Set sh = WS(CStr(nm))
        r = LastRow(sh)
        If r >= 2 Then sh.Rows("2:" & r).Delete
    Next nm
    BorrarFilas SH_CAT, "Descripcion", "DEMO*"
    BorrarFilas SH_PRE, "DescripcionPartida", "DEMO*"
    BorrarFilas SH_AUTH, "Usuario", "t_*"
    g_Usuario = "": g_Rol = ""
End Sub

Private Sub BorrarFilas(ByVal hoja As String, ByVal hdr As String, ByVal patron As String)
    Dim sh As Worksheet, c As Long, r As Long
    Set sh = WS(hoja)
    c = ColIdx(sh, hdr)
    For r = LastRow(sh) To 2 Step -1
        If CStr(sh.Cells(r, c).Value) Like patron Then sh.Rows(r).Delete
    Next r
End Sub
