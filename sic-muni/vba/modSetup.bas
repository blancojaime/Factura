Attribute VB_Name = "modSetup"
'==============================================================================
' SIC-MUNI - modSetup
' Instalacion inicial (ejecutar UNA vez, con el libro .xlsm recien creado):
'   1) InstalarSistema  -> crea hojas/tablas, CONFIG, administrador y plantillas.
'   2) (opcional) CargarDatosDemo -> catalogo y presupuesto FICTICIOS de prueba.
'   3) modUIBuilder.ConstruirFormularios -> crea frmLogin y frmContratacionesConsolidado.
'==============================================================================
Option Explicit

Public Sub InstalarSistema()
    InstalarSistemaAuto "", ""
End Sub

' usuario/clave vacios = los pide con InputBox (modo interactivo).
Public Sub InstalarSistemaAuto(ByVal adminUsr As String, ByVal adminPwd As String)
    Application.ScreenUpdating = False
    ThisWorkbook.Unprotect PROT_PWD
    CrearTabla SH_CFG, "Clave|Valor|Descripcion"
    CrearTabla SH_SEQ, "Clave|Ultimo"
    CrearTabla SH_AUTH, "Usuario|PasswordHash|NombreCompleto|Rol|Dependencia_DA|Estado|Intentos|UltimoAcceso"
    CrearTabla SH_CAT, "CodigoUNSPSC|Descripcion|Unidad|FichaTecnicaCHB|Tipo|Vigencia|RequiereAutorizacionMDPyEP"
    CrearTabla SH_PRE, "Gestion|DA|UE|Programa|Proyecto|ActObra|Fuente|Organismo|Partida_ObjetoGasto|DescripcionPartida|PresupuestoAprobado|PreventivoComprometido|SaldoDisponible"
    CrearTabla SH_SOL, "ID_Solicitud|Correlativo|Fecha|Cod_DA|Cod_UE|Solicitante|Justificacion|Estado|Modalidad|MontoReferencial"
    CrearTabla SH_DET, "ID_Solicitud|Item|CodigoUNSPSC|Descripcion|Cantidad|Unidad|PrecioRefUnitario|PrecioRefTotal|CumpleCHB|CodigoExcepcionMDPyEP|JustificacionExcepcion|NroAutorizacionMDPyEP|FechaAutorizacion"
    CrearTabla SH_COT, "ID_Cotizacion|ID_Solicitud|Proveedor_NIT|RazonSocial|FechaCotizacion|ValidezOferta|MontoTotalCotizado|CumplimientoTecnico|Recomendado|Adjudicada|FechaHoraRecepcion|Desempate"
    CrearTabla SH_ORD, "NroOrden|Tipo|CUCE_SICOES|ID_Solicitud|ID_Cotizacion|Proveedor_Adjudicado|NIT|MontoTotal|NroPreventivo_C31|EstadoC31|FechaEmision|PlazoDias|LugarEntrega|EstadoOrden|MotivoAnulacion|Usuario"
    CrearTabla SH_C31, "NroInterno|Fecha|ID_Solicitud|DA|UE|MontoTotal|MontoRevertido|Estado|NroC31_SIGEP|Usuario"
    CrearTabla SH_C31D, "NroInterno|Linea|Programa|Proyecto|ActObra|Fuente|Organismo|Partida|Importe|ImporteRevertido"
    CrearTabla SH_REC, "NroRecepcion|NroOrden|FechaRecepcion|FechaLimite|DiasRetraso|MontoMulta|Resultado|Observaciones|Usuario"
    CrearTabla SH_AUD, "Fecha|Usuario|Rol|Accion|Detalle"

    ' Columnas de codigo = TEXTO (conserva ceros a la izquierda)
    FormatoTexto SH_AUTH, "Usuario"
    FormatoTexto SH_CAT, "CodigoUNSPSC"
    FormatoTexto SH_PRE, "DA|UE|Programa|Proyecto|ActObra|Fuente|Organismo|Partida_ObjetoGasto"
    FormatoTexto SH_SOL, "Cod_DA|Cod_UE"
    FormatoTexto SH_DET, "CodigoUNSPSC"
    FormatoTexto SH_COT, "Proveedor_NIT"
    WS(SH_COT).Columns(ColIdx(WS(SH_COT), "FechaHoraRecepcion")).NumberFormat = "dd/mm/yyyy hh:mm"
    FormatoTexto SH_ORD, "NIT|CUCE_SICOES"
    FormatoTexto SH_C31, "DA|UE|NroC31_SIGEP"
    FormatoTexto SH_C31D, "Programa|Proyecto|ActObra|Fuente|Organismo|Partida"
    ' SaldoDisponible = Aprobado - Comprometido (formula precargada; el motor lee K-L directamente)
    WS(SH_PRE).Range("M2:M2000").Formula = "=IF(K2="""","""",K2-L2)"

    CargarConfigInicial
    CrearAdministrador adminUsr, adminPwd
    modSetupTemplates.BuildTemplates
    On Error Resume Next
    ThisWorkbook.Names.Add Name:="PROT_INFO", RefersTo:="=""SIC-MUNI instalado"""
    On Error GoTo 0
    Application.ScreenUpdating = True
    Aviso "Instalacion completada." & vbLf & "Ejecute modUIBuilder.ConstruirFormularios y luego ProtectDB."
End Sub

Private Sub CrearTabla(ByVal nombre As String, ByVal headers As String)
    Dim sh As Worksheet, h() As String, i As Long
    On Error Resume Next
    Set sh = ThisWorkbook.Worksheets(nombre)
    On Error GoTo 0
    If sh Is Nothing Then
        Set sh = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        sh.Name = nombre
    End If
    h = Split(headers, "|")
    For i = 0 To UBound(h)
        sh.Cells(1, i + 1).Value = h(i)
    Next i
    With sh.Range(sh.Cells(1, 1), sh.Cells(1, UBound(h) + 1))
        .Font.Bold = True: .Interior.Color = RGB(31, 78, 121): .Font.Color = vbWhite
    End With
    sh.Columns.AutoFit
End Sub

Private Sub FormatoTexto(ByVal hoja As String, ByVal cols As String)
    Dim c As Variant
    For Each c In Split(cols, "|")
        WS(hoja).Columns(ColIdx(WS(hoja), CStr(c))).NumberFormat = "@"
    Next c
End Sub

Private Sub Cfg(ByVal clave As String, ByVal valor As String, ByVal desc As String)
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_CFG)
    r = FindRow(sh, "Clave", clave)
    If r = 0 Then r = NewRow(sh)
    sh.Cells(r, 1).Value = clave: sh.Cells(r, 2).Value = valor: sh.Cells(r, 3).Value = desc
End Sub

Private Sub CargarConfigInicial()
    Cfg "Entidad", "GOBIERNO AUTONOMO MUNICIPAL DE (COMPLETAR)", "Nombre para el membrete de documentos"
    Cfg "Gestion", CStr(Year(Date)), "Gestion fiscal vigente"
    Cfg "CodDA", "", "Codigo de Direccion Administrativa (DA)"
    Cfg "CodUE", "", "Codigo de Unidad Ejecutora (UE)"
    Cfg "TopeContratacionMenor", "50000", "Bs. VERIFICAR contra NB-SABS vigente"
    Cfg "TopeSinCuadroComparativo", "20000", "Bs. Sobre este monto: invitacion + cuadro comparativo"
    Cfg "MinCotizaciones", "3", "Cotizaciones minimas sobre el tope sin cuadro"
    Cfg "TolerCotizacionPct", "20", "% de desvio vs referencial que dispara aviso"
    Cfg "CHB_NivelMatch", "8", "Digitos UNSPSC a comparar (8 exacto, 6 familia)"
    Cfg "PatronCodigoExcepcion", "*", "Patron Like del Codigo Unico de Excepcion; AJUSTAR al formato real"
    Cfg "MinCaracteresJustificacion", "80", "Longitud minima de la justificacion de excepcion"
    Cfg "ExigirC31SIGEPParaOrden", "SI", "SI = la Orden exige C-31 asociado (N SIGEP)"
    Cfg "PenalidadPorMil", "3", "Multa por mil por dia de retraso. VERIFICAR con normativa/reglamento"
    Cfg "PenalidadMaxPct", "10", "Tope de multas (% monto). VERIFICAR con normativa/reglamento"
    Cfg "MaxIntentosLogin", "3", "Intentos antes de bloquear el usuario"
    Cfg "TimeoutSesionMin", "20", "Minutos de inactividad antes de cerrar sesion"
End Sub

Private Sub CrearAdministrador(ByVal usr As String, ByVal pwd As String)
    Dim sh As Worksheet, e As String, r As Long
    Set sh = WS(SH_AUTH)
    If LastRow(sh) > 1 Then Exit Sub
    If Len(usr) = 0 Then usr = InputBox("Usuario del Administrador inicial:", "SIC-MUNI", "admin")
    If Len(usr) = 0 Then Fail "Instalacion cancelada."
    If Len(pwd) > 0 Then
        e = PasswordPolicyError(pwd)
        If Len(e) > 0 Then Fail e
    Else
        Do
            pwd = InputBox("Contrasena inicial (min. 10 car., mayus/minus/digitos).", "SIC-MUNI")
            If Len(pwd) = 0 Then Fail "Instalacion cancelada."
            e = PasswordPolicyError(pwd)
            If Len(e) > 0 Then Aviso e, vbExclamation
        Loop While Len(e) > 0
    End If
    r = NewRow(sh)
    SetV sh, r, "Usuario", usr
    SetV sh, r, "PasswordHash", BuildStoredHash(pwd)
    SetV sh, r, "NombreCompleto", "Administrador del Sistema"
    SetV sh, r, "Rol", ROL_ADM
    SetV sh, r, "Estado", "ACTIVO"
    SetV sh, r, "Intentos", 0
End Sub

' Datos FICTICIOS solo para pruebas. No usar en produccion.
Public Sub CargarDatosDemo()
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_CAT)
    r = NewRow(sh): sh.Cells(r, 1).Value = "44121600": sh.Cells(r, 2).Value = "DEMO - Suministros de oficina": sh.Cells(r, 3).Value = "Unidad": sh.Cells(r, 4).Value = True: sh.Cells(r, 5).Value = "Bien": sh.Cells(r, 6).Value = DateSerial(Year(Date), 12, 31): sh.Cells(r, 7).Value = True
    r = NewRow(sh): sh.Cells(r, 1).Value = "56101500": sh.Cells(r, 2).Value = "DEMO - Muebles (sin ficha vigente)": sh.Cells(r, 3).Value = "Unidad": sh.Cells(r, 4).Value = False: sh.Cells(r, 5).Value = "Bien": sh.Cells(r, 6).Value = DateSerial(Year(Date), 12, 31): sh.Cells(r, 7).Value = True
    Set sh = WS(SH_PRE)
    r = NewRow(sh)
    sh.Cells(r, 1).Value = CStr(Year(Date)): sh.Cells(r, 2).Value = "01": sh.Cells(r, 3).Value = "001"
    sh.Cells(r, 4).Value = "01": sh.Cells(r, 5).Value = "0000": sh.Cells(r, 6).Value = "001"
    sh.Cells(r, 7).Value = "20": sh.Cells(r, 8).Value = "230": sh.Cells(r, 9).Value = "31120"
    sh.Cells(r, 10).Value = "DEMO - Material de oficina": sh.Cells(r, 11).Value = 100000: sh.Cells(r, 12).Value = 0
    Aviso "Datos demo cargados (ficticios)."
End Sub
