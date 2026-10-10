Attribute VB_Name = "modImport"
'==============================================================================
' SIC-MUNI - modImport
' Carga masiva desde CSV (UTF-8, delimitador "," o ";", fila 1 = encabezados con
' los NOMBRES de las columnas de la hoja). Solo rol ADM.
'   CAT_CHB      : upsert por CodigoUNSPSC
'   PRESUPUESTO  : agrega estructuras nuevas; las repetidas se RECHAZAN (no se
'                  pisa PreventivoComprometido). Se ignoran PreventivoComprometido
'                  y SaldoDisponible del archivo.
' Limite: no admite saltos de linea dentro de un campo entre comillas.
'==============================================================================
Option Explicit

Public Sub ImportarCatalogoCHB()
    ImportarDesdeDialogo SH_CAT, "CodigoUNSPSC", "CodigoUNSPSC|Descripcion|Unidad|FichaTecnicaCHB|Tipo|Vigencia|RequiereAutorizacionMDPyEP", True
End Sub

Public Sub ImportarPresupuesto()
    ImportarDesdeDialogo SH_PRE, "Gestion|DA|UE|Programa|Proyecto|ActObra|Fuente|Organismo|Partida_ObjetoGasto", _
        "Gestion|DA|UE|Programa|Proyecto|ActObra|Fuente|Organismo|Partida_ObjetoGasto|DescripcionPartida|PresupuestoAprobado", False
End Sub

Private Sub ImportarDesdeDialogo(ByVal hoja As String, ByVal claves As String, ByVal requeridas As String, ByVal upsert As Boolean)
    Dim ruta As Variant
    On Error GoTo EH
    RequirePermiso P_CONFIG
    ruta = Application.GetOpenFilename("Archivos CSV (*.csv),*.csv", , "Seleccione el CSV de " & hoja)
    If VarType(ruta) = vbBoolean Then Exit Sub
    MsgBox ImportarCSV(hoja, CStr(ruta), claves, requeridas, upsert), vbInformation, "Importacion " & hoja
    Exit Sub
EH: MsgBox Err.Description, vbExclamation
End Sub

Public Function ImportarCSV(ByVal hoja As String, ByVal ruta As String, ByVal claves As String, _
                            ByVal requeridas As String, ByVal upsert As Boolean) As String
    Dim sh As Worksheet, lineas As Variant, delim As String, hdr() As String, cols() As Long
    Dim i As Long, j As Long, f() As String, k As String, r As Long, ok As Boolean
    Dim dic As Object, nuevos As Long, actual As Long, rech As Long, detalle As String, faltan As String, v As Variant
    RequirePermiso P_CONFIG
    Set sh = WS(hoja)
    lineas = LeerLineas(ruta)
    If UBound(lineas) < 1 Then Fail "El archivo no tiene datos."
    delim = IIf(CuentaChar(CStr(lineas(0)), ";") > CuentaChar(CStr(lineas(0)), ","), ";", ",")
    hdr = ParseCsv(CStr(lineas(0)), delim)
    ReDim cols(0 To UBound(hdr))
    For j = 0 To UBound(hdr)
        hdr(j) = Trim$(hdr(j))
        cols(j) = TryColIdx(sh, hdr(j))
        If hdr(j) = "SaldoDisponible" Or (hoja = SH_PRE And hdr(j) = "PreventivoComprometido") Then cols(j) = 0
    Next j
    For Each v In Split(requeridas, "|")
        If Not Contiene(hdr, CStr(v)) Then faltan = faltan & v & " "
    Next v
    If Len(faltan) > 0 Then Fail "Faltan columnas obligatorias en el CSV: " & faltan

    ' indice de claves existentes
    Set dic = CreateObject("Scripting.Dictionary")
    dic.CompareMode = 1
    For r = 2 To LastRow(sh)
        dic(ClaveFila(sh, r, claves)) = r
    Next r

    For i = 1 To UBound(lineas)
        If Len(Trim$(CStr(lineas(i)))) > 0 Then
            f = ParseCsv(CStr(lineas(i)), delim)
            ok = True
            k = ClaveCsv(hdr, f, claves)
            If Len(Replace(k, "|", "")) = 0 Then
                ok = False: detalle = detalle & "Linea " & (i + 1) & ": clave vacia." & vbLf
            ElseIf dic.Exists(k) And Not upsert Then
                ok = False: detalle = detalle & "Linea " & (i + 1) & ": estructura/clave repetida, no se importa." & vbLf
            End If
            If ok Then
                If dic.Exists(k) Then r = dic(k): actual = actual + 1 Else r = NewRow(sh): nuevos = nuevos + 1: dic(k) = r
                For j = 0 To UBound(hdr)
                    If cols(j) > 0 And j <= UBound(f) Then
                        If Not Escribir(sh, r, cols(j), hdr(j), f(j), delim) Then
                            detalle = detalle & "Linea " & (i + 1) & ": valor invalido en " & hdr(j) & " (" & f(j) & ")." & vbLf
                        End If
                    End If
                Next j
                If hoja = SH_PRE Then
                    If IsEmpty(sh.Cells(r, ColIdx(sh, "PreventivoComprometido")).Value) Then sh.Cells(r, ColIdx(sh, "PreventivoComprometido")).Value = 0
                End If
            Else
                rech = rech + 1
            End If
        End If
    Next i
    LogAudit "IMPORT_CSV", hoja & ": nuevos " & nuevos & ", actualizados " & actual & ", rechazados " & rech
    ImportarCSV = "Nuevos: " & nuevos & vbLf & "Actualizados: " & actual & vbLf & "Rechazados: " & rech
    If Len(detalle) > 0 Then ImportarCSV = ImportarCSV & vbLf & vbLf & Left$(detalle, 1500)
End Function

' --- Helpers ---
Private Function TryColIdx(ByVal sh As Worksheet, ByVal h As String) As Long
    Dim c As Long
    For c = 1 To sh.Cells(1, sh.Columns.Count).End(xlToLeft).Column
        If StrComp(CStr(sh.Cells(1, c).Value), h, vbTextCompare) = 0 Then TryColIdx = c: Exit Function
    Next c
End Function

Private Function Contiene(ByRef arr() As String, ByVal x As String) As Boolean
    Dim i As Long
    For i = 0 To UBound(arr)
        If StrComp(arr(i), x, vbTextCompare) = 0 Then Contiene = True: Exit Function
    Next i
End Function

Private Function ClaveFila(ByVal sh As Worksheet, ByVal r As Long, ByVal claves As String) As String
    Dim c As Variant, s As String
    For Each c In Split(claves, "|")
        s = s & Trim$(CStr(sh.Cells(r, ColIdx(sh, CStr(c))).Value)) & "|"
    Next c
    ClaveFila = s
End Function

Private Function ClaveCsv(ByRef hdr() As String, ByRef f() As String, ByVal claves As String) As String
    Dim c As Variant, j As Long, s As String
    For Each c In Split(claves, "|")
        For j = 0 To UBound(hdr)
            If StrComp(hdr(j), CStr(c), vbTextCompare) = 0 Then
                If j <= UBound(f) Then s = s & Trim$(f(j))
            End If
        Next j
        s = s & "|"
    Next c
    ClaveCsv = s
End Function

Private Function Escribir(ByVal sh As Worksheet, ByVal r As Long, ByVal c As Long, ByVal hdr As String, _
                          ByVal txt As String, ByVal delim As String) As Boolean
    Dim s As String, u As String
    s = Trim$(txt): Escribir = True
    Select Case LCase$(hdr)
        Case "fichatecnicachb", "requiereautorizacionmdpyep"
            u = UCase$(s)
            sh.Cells(r, c).Value = (u = "SI" Or u = "TRUE" Or u = "1" Or u = "VERDADERO" Or u = "S")
        Case "vigencia", "fechaautorizacion"
            If Len(s) = 0 Then
                sh.Cells(r, c).ClearContents
            ElseIf IsDate(s) Then
                sh.Cells(r, c).Value = CDate(s): sh.Cells(r, c).NumberFormat = "dd/mm/yyyy"
            Else
                Escribir = False
            End If
        Case "presupuestoaprobado"
            s = Replace(s, " ", "")
            If delim = ";" Then s = Replace(Replace(s, ".", ""), ",", ".")
            If Len(s) > 0 And IsNumeric(Replace(s, ".", "")) Then
                sh.Cells(r, c).Value = Val(s)
            Else
                Escribir = False
            End If
        Case Else
            sh.Cells(r, c).Value = s
    End Select
End Function

Private Function LeerLineas(ByVal ruta As String) As Variant
    Dim st As Object, txt As String
    Set st = CreateObject("ADODB.Stream")
    st.Type = 2: st.Charset = "utf-8": st.Open
    st.LoadFromFile ruta
    txt = st.ReadText
    st.Close
    If Len(txt) > 0 Then If AscW(Left$(txt, 1)) = &HFEFF Then txt = Mid$(txt, 2)
    txt = Replace(Replace(txt, vbCrLf, vbLf), vbCr, vbLf)
    LeerLineas = Split(txt, vbLf)
End Function

Private Function CuentaChar(ByVal s As String, ByVal ch As String) As Long
    CuentaChar = Len(s) - Len(Replace(s, ch, ""))
End Function

' Divide una linea CSV respetando comillas ("" = comilla literal).
Private Function ParseCsv(ByVal linea As String, ByVal delim As String) As String()
    Dim res() As String, n As Long, i As Long, c As String, cur As String, q As Boolean
    ReDim res(0 To 0)
    For i = 1 To Len(linea)
        c = Mid$(linea, i, 1)
        If q Then
            If c = """" Then
                If Mid$(linea, i + 1, 1) = """" Then cur = cur & """": i = i + 1 Else q = False
            Else
                cur = cur & c
            End If
        ElseIf c = """" Then
            q = True
        ElseIf c = delim Then
            res(n) = cur: n = n + 1: ReDim Preserve res(0 To n): cur = ""
        Else
            cur = cur & c
        End If
    Next i
    res(n) = cur
    ParseCsv = res
End Function
