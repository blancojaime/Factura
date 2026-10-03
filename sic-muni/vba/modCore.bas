Attribute VB_Name = "modCore"
'==============================================================================
' SIC-MUNI - modCore
' Utilidades comunes: acceso a "tablas" (hojas), configuracion, secuencias,
' auditoria. Todas las lecturas/escrituras se hacen por NOMBRE de columna
' (fila 1 = encabezados) para no depender del orden de las columnas.
' Nota: este archivo es ASCII puro a proposito (sin tildes) para que el
' importador del VBE no corrompa caracteres.
'==============================================================================
Option Explicit

' --- Nombres de hojas (base de datos) ---
Public Const SH_CFG As String = "CONFIG"
Public Const SH_SEQ As String = "SECUENCIAS"
Public Const SH_AUTH As String = "SYS_AUTH"
Public Const SH_CAT As String = "CAT_CHB"
Public Const SH_PRE As String = "PRESUPUESTO"
Public Const SH_SOL As String = "SOLICITUDES"
Public Const SH_DET As String = "SOLICITUDES_DET"
Public Const SH_COT As String = "COTIZACIONES"
Public Const SH_ORD As String = "ORDENES_GASTO"
Public Const SH_C31 As String = "C31"
Public Const SH_C31D As String = "C31_DET"
Public Const SH_AUD As String = "AUDITORIA"

' Clave de proteccion de hojas/estructura. CAMBIAR antes de implantar y
' proteger tambien el proyecto VBA (Herramientas > Propiedades de VBAProject).
Public Const PROT_PWD As String = "CambiarEstaClave#2025"

Public Function WS(ByVal nombre As String) As Worksheet
    Set WS = ThisWorkbook.Worksheets(nombre)
End Function

Public Function ColIdx(ByVal sh As Worksheet, ByVal hdr As String) As Long
    Dim c As Long, lastC As Long
    lastC = sh.Cells(1, sh.Columns.Count).End(xlToLeft).Column
    For c = 1 To lastC
        If StrComp(CStr(sh.Cells(1, c).Value), hdr, vbTextCompare) = 0 Then
            ColIdx = c: Exit Function
        End If
    Next c
    Err.Raise vbObjectError + 1001, "modCore", "Columna no encontrada: " & sh.Name & "." & hdr
End Function

Public Function LastRow(ByVal sh As Worksheet) As Long
    LastRow = sh.Cells(sh.Rows.Count, 1).End(xlUp).Row
    If LastRow < 1 Then LastRow = 1
End Function

Public Function NewRow(ByVal sh As Worksheet) As Long
    NewRow = LastRow(sh) + 1
End Function

Public Function GetV(ByVal sh As Worksheet, ByVal r As Long, ByVal hdr As String) As Variant
    GetV = sh.Cells(r, ColIdx(sh, hdr)).Value
End Function

Public Sub SetV(ByVal sh As Worksheet, ByVal r As Long, ByVal hdr As String, ByVal v As Variant)
    sh.Cells(r, ColIdx(sh, hdr)).Value = v
End Sub

' Busca la primera fila (>=2) cuyo valor en la columna hdr es igual a key
' (comparacion como texto, sin distinguir mayusculas). Devuelve 0 si no existe.
Public Function FindRow(ByVal sh As Worksheet, ByVal hdr As String, ByVal key As Variant) As Long
    Dim c As Long, lr As Long, r As Long, v As Variant
    lr = LastRow(sh)
    If lr < 2 Then Exit Function
    c = ColIdx(sh, hdr)
    v = sh.Range(sh.Cells(2, c), sh.Cells(lr, c)).Value
    If lr = 2 Then
        If StrComp(CStr(v), CStr(key), vbTextCompare) = 0 Then FindRow = 2
        Exit Function
    End If
    For r = 1 To UBound(v, 1)
        If StrComp(CStr(v(r, 1)), CStr(key), vbTextCompare) = 0 Then
            FindRow = r + 1: Exit Function
        End If
    Next r
End Function

' --- Configuracion (hoja CONFIG: Clave | Valor | Descripcion) ---
Public Function CfgVal(ByVal clave As String, Optional ByVal def As String = "") As String
    Dim r As Long
    r = FindRow(WS(SH_CFG), "Clave", clave)
    If r = 0 Then
        CfgVal = def
    Else
        CfgVal = CStr(GetV(WS(SH_CFG), r, "Valor"))
    End If
End Function

Public Function CfgNum(ByVal clave As String, ByVal def As Double) As Double
    Dim s As String
    s = CfgVal(clave, "")
    If Len(s) > 0 And IsNumeric(s) Then CfgNum = CDbl(s) Else CfgNum = def
End Function

' --- Secuencias / correlativos (hoja SECUENCIAS: Clave | Ultimo) ---
Public Function NextSeq(ByVal clave As String) As Long
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_SEQ)
    r = FindRow(sh, "Clave", clave)
    If r = 0 Then
        r = NewRow(sh)
        SetV sh, r, "Clave", clave
        SetV sh, r, "Ultimo", 0
    End If
    NextSeq = CLng(GetV(sh, r, "Ultimo")) + 1
    SetV sh, r, "Ultimo", NextSeq
End Function

' Ej.: FormatCorrelativo("SOL", 7) -> "SOL-2025-000007"
Public Function FormatCorrelativo(ByVal prefijo As String, ByVal n As Long) As String
    FormatCorrelativo = prefijo & "-" & CfgVal("Gestion", CStr(Year(Date))) & "-" & Format$(n, "000000")
End Function

' --- Auditoria (hoja AUDITORIA: Fecha | Usuario | Rol | Accion | Detalle) ---
Public Sub LogAudit(ByVal accion As String, ByVal detalle As String)
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_AUD)
    r = NewRow(sh)
    sh.Cells(r, 1).Value = Now
    sh.Cells(r, 2).Value = IIf(Len(g_Usuario) > 0, g_Usuario, "(sistema)")
    sh.Cells(r, 3).Value = g_Rol
    sh.Cells(r, 4).Value = accion
    sh.Cells(r, 5).Value = detalle
End Sub

Public Function RoundM(ByVal x As Double) As Double
    ' Redondeo comercial a 2 decimales (VBA Round() es bancario).
    RoundM = Int(Abs(x) * 100 + 0.5) / 100 * Sgn(x)
End Function

Public Sub Fail(ByVal msg As String)
    Err.Raise vbObjectError + 513, "SIC-MUNI", msg
End Sub

' --- Proteccion de hojas de datos ---
Public Function TodasLasHojas() As Variant
    TodasLasHojas = Array(SH_CFG, SH_SEQ, SH_AUTH, SH_CAT, SH_PRE, SH_SOL, SH_DET, SH_COT, SH_ORD, SH_C31, SH_C31D, SH_AUD, _
                          DOC_C1, DOC_CUADRO, DOC_EXCEPCION, DOC_C31, DOC_ORDEN)
End Function

Public Sub ProtectDB()
    Dim nm As Variant, sh As Worksheet
    On Error Resume Next: ThisWorkbook.Unprotect PROT_PWD: On Error GoTo 0
    For Each nm In TodasLasHojas()
        Set sh = WS(CStr(nm))
        sh.Protect Password:=PROT_PWD, UserInterfaceOnly:=True
        sh.Visible = xlSheetVeryHidden
    Next nm
    ThisWorkbook.Protect Password:=PROT_PWD, Structure:=True
End Sub

' Solo ADM (ver modSecurity): muestra las hojas de datos para mantenimiento.
Public Sub ShowDB()
    Dim nm As Variant
    RequirePermiso P_CONFIG
    ThisWorkbook.Unprotect PROT_PWD
    For Each nm In TodasLasHojas()
        WS(CStr(nm)).Visible = xlSheetVisible
        WS(CStr(nm)).Unprotect PROT_PWD
    Next nm
    LogAudit "SHOW_DB", "Hojas de datos desprotegidas para mantenimiento"
End Sub
