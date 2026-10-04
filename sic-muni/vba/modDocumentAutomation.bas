Attribute VB_Name = "modDocumentAutomation"
'==============================================================================
' SIC-MUNI - modDocumentAutomation
' Vuelca datos a las plantillas (hojas Doc_*) y exporta a PDF.
' Las plantillas se crean con modSetup.BuildTemplates. Cada plantilla usa
' RANGOS CON NOMBRE (prefijo C1_, CC_, EX_, PV_, OC_) para campos y para la
' primera celda de la tabla de detalle; las columnas calculadas (totales)
' son FORMULAS de la plantilla y no se sobrescriben desde VBA.
'==============================================================================
Option Explicit

Public Const DOC_C1 As String = "Doc_Solicitud_C1"
Public Const DOC_CUADRO As String = "Doc_CuadroComparativo"
Public Const DOC_EXCEPCION As String = "Doc_JustificacionExcepcionCHB"
Public Const DOC_C31 As String = "Doc_Preventivo_C31"
Public Const DOC_ORDEN As String = "Doc_OrdenCompraServicio"
Public Const DOC_ACTA As String = "Doc_ActaRecepcion"

'------------------------------------------------------------------------------
' Helpers de plantilla
'------------------------------------------------------------------------------
Private Sub PutN(ByVal nombre As String, ByVal v As Variant)
    ThisWorkbook.Names(nombre).RefersToRange.Cells(1, 1).Value = v
End Sub

' Escribe filas en la tabla de la plantilla. data(1..n, 1..m). Las columnas en
' skipCols ("|7|") contienen formulas y se respetan. Oculta filas sobrantes.
Private Sub FillTable(ByVal firstName As String, ByVal cap As Long, ByRef data As Variant, _
                      ByVal nRows As Long, ByVal nCols As Long, Optional ByVal skipCols As String = "")
    Dim c0 As Range, sh As Worksheet, i As Long, j As Long
    Set c0 = ThisWorkbook.Names(firstName).RefersToRange.Cells(1, 1)
    Set sh = c0.Worksheet
    If nRows > cap Then Fail "El documento admite hasta " & cap & " filas de detalle (hay " & nRows & ")."
    sh.Rows(c0.Row & ":" & (c0.Row + cap - 1)).Hidden = False
    For i = 1 To cap
        For j = 1 To nCols
            If InStr(skipCols, "|" & j & "|") = 0 Then c0.Offset(i - 1, j - 1).ClearContents
        Next j
    Next i
    For i = 1 To nRows
        For j = 1 To nCols
            If InStr(skipCols, "|" & j & "|") = 0 Then c0.Offset(i - 1, j - 1).Value = data(i, j)
        Next j
    Next i
    If nRows < cap Then sh.Rows((c0.Row + nRows) & ":" & (c0.Row + cap - 1)).Hidden = True
    If nRows > 0 Then sh.Rows(c0.Row & ":" & (c0.Row + nRows - 1)).AutoFit
End Sub

Private Sub Membrete(ByVal prefijo As String)
    PutN prefijo & "_Entidad", UCase$(CfgVal("Entidad", "GOBIERNO AUTONOMO MUNICIPAL"))
    PutN prefijo & "_Gestion", CfgVal("Gestion", CStr(Year(Date)))
    PutN prefijo & "_Pie", "Documento generado por SIC-MUNI el " & Format$(Now, "dd/mm/yyyy hh:nn") & " - usuario: " & g_Usuario
End Sub

Private Sub ChequeoDoc(Optional ByVal soloC1 As Boolean = False)
    RequirePermiso P_DOCS
    If g_Rol = ROL_US And Not soloC1 Then Fail "La Unidad Solicitante solo puede emitir el Formulario C-1."
End Sub

'------------------------------------------------------------------------------
' 1) Formulario C-1: Requerimiento y Especificaciones Tecnicas
'------------------------------------------------------------------------------
Public Function GenerarC1(ByVal idSol As String, Optional ByVal aPDF As Boolean = True) As String
    Dim rS As Long, shD As Worksheet, r As Long, n As Long, d() As Variant, sh As Worksheet
    ChequeoDoc True
    rS = FilaSolicitud(idSol)
    Set sh = WS(SH_SOL)
    Membrete "C1"
    PutN "C1_Solicitud", idSol
    PutN "C1_Fecha", GetV(sh, rS, "Fecha")
    PutN "C1_DA", GetV(sh, rS, "Cod_DA")
    PutN "C1_UE", GetV(sh, rS, "Cod_UE")
    PutN "C1_Solicitante", GetV(sh, rS, "Solicitante")
    PutN "C1_Justificacion", GetV(sh, rS, "Justificacion")
    PutN "C1_Modalidad", GetV(sh, rS, "Modalidad")
    Set shD = WS(SH_DET)
    ReDim d(1 To 40, 1 To 8)
    For r = 2 To LastRow(shD)
        If CStr(GetV(shD, r, "ID_Solicitud")) = idSol Then
            n = n + 1
            d(n, 1) = GetV(shD, r, "Item"): d(n, 2) = GetV(shD, r, "CodigoUNSPSC")
            d(n, 3) = GetV(shD, r, "Descripcion"): d(n, 4) = GetV(shD, r, "Unidad")
            d(n, 5) = GetV(shD, r, "Cantidad"): d(n, 6) = GetV(shD, r, "PrecioRefUnitario")
            d(n, 8) = GetV(shD, r, "CumpleCHB")
        End If
    Next r
    FillTable "C1_ItemsIni", 15, d, n, 8, "|7|"            ' col 7 = formula Cant x P.Unit
    PutN "C1_Literal", MontoLiteral(CDbl(GetV(sh, rS, "MontoReferencial")))
    GenerarC1 = Cerrar(DOC_C1, "C1_" & idSol, aPDF)
End Function

'------------------------------------------------------------------------------
' 2) Cuadro Comparativo de Cotizaciones
'------------------------------------------------------------------------------
Public Function GenerarCuadroComparativo(ByVal idSol As String, Optional ByVal aPDF As Boolean = True) As String
    Dim rS As Long, sh As Worksheet, shC As Worksheet, r As Long, n As Long, d() As Variant, rec As String, req As Long
    ChequeoDoc
    rS = FilaSolicitud(idSol)
    Set sh = WS(SH_SOL): Set shC = WS(SH_COT)
    req = CotizacionesRequeridas(CDbl(GetV(sh, rS, "MontoReferencial")))
    If ContarCotizaciones(idSol) < req Then Fail "Se requieren " & req & " cotizaciones para el cuadro comparativo."
    Membrete "CC"
    PutN "CC_Solicitud", idSol
    PutN "CC_Fecha", Date
    PutN "CC_Modalidad", GetV(sh, rS, "Modalidad")
    PutN "CC_Referencial", GetV(sh, rS, "MontoReferencial")
    PutN "CC_Criterio", "Cumplimiento de especificaciones tecnicas (Cumple / No cumple) y Precio Evaluado Mas Bajo"
    ReDim d(1 To 10, 1 To 7)
    For r = 2 To LastRow(shC)
        If CStr(GetV(shC, r, "ID_Solicitud")) = idSol Then
            n = n + 1
            d(n, 1) = n: d(n, 2) = GetV(shC, r, "Proveedor_NIT"): d(n, 3) = GetV(shC, r, "RazonSocial")
            d(n, 4) = GetV(shC, r, "ValidezOferta"): d(n, 5) = GetV(shC, r, "MontoTotalCotizado")
            d(n, 6) = IIf(CStr(GetV(shC, r, "CumplimientoTecnico")) = "SI", "Cumple", "No cumple")
            d(n, 7) = IIf(CStr(GetV(shC, r, "Recomendado")) = "SI", "RECOMENDADA", "")
            If CStr(GetV(shC, r, "Recomendado")) = "SI" Then rec = GetV(shC, r, "RazonSocial") & " - Bs " & Format$(GetV(shC, r, "MontoTotalCotizado"), "#,##0.00")
        End If
    Next r
    If Len(rec) = 0 Then Fail "Ejecute primero la evaluacion del cuadro (no hay oferta recomendada)."
    FillTable "CC_OfertasIni", 10, d, n, 7
    PutN "CC_Recomendacion", "Se recomienda adjudicar a: " & rec
    GenerarCuadroComparativo = Cerrar(DOC_CUADRO, "CC_" & idSol, aPDF)
End Function

'------------------------------------------------------------------------------
' 3) Justificacion de Excepcion de Ficha Tecnica CHB
'------------------------------------------------------------------------------
Public Function GenerarJustificacionExcepcion(ByVal idSol As String, Optional ByVal aPDF As Boolean = True) As String
    Dim rS As Long, shD As Worksheet, r As Long, n As Long, d() As Variant
    ChequeoDoc
    rS = FilaSolicitud(idSol)
    Set shD = WS(SH_DET)
    ReDim d(1 To 10, 1 To 7)
    For r = 2 To LastRow(shD)
        If CStr(GetV(shD, r, "ID_Solicitud")) = idSol And UCase$(CStr(GetV(shD, r, "CumpleCHB"))) = "EXCEPCION" Then
            n = n + 1
            d(n, 1) = GetV(shD, r, "Item"): d(n, 2) = GetV(shD, r, "CodigoUNSPSC"): d(n, 3) = GetV(shD, r, "Descripcion")
            d(n, 4) = GetV(shD, r, "CodigoExcepcionMDPyEP"): d(n, 5) = GetV(shD, r, "NroAutorizacionMDPyEP")
            d(n, 6) = GetV(shD, r, "FechaAutorizacion"): d(n, 7) = GetV(shD, r, "JustificacionExcepcion")
        End If
    Next r
    If n = 0 Then Fail "La solicitud no tiene items con excepcion CHB."
    Membrete "EX"
    PutN "EX_Solicitud", idSol
    PutN "EX_Fecha", Date
    PutN "EX_DA", GetV(WS(SH_SOL), rS, "Cod_DA")
    PutN "EX_Solicitante", GetV(WS(SH_SOL), rS, "Solicitante")
    FillTable "EX_ItemsIni", 10, d, n, 7
    GenerarJustificacionExcepcion = Cerrar(DOC_EXCEPCION, "EXC_" & idSol, aPDF)
End Function

'------------------------------------------------------------------------------
' 4) Preventivo C-31 (boleta interna de reserva y estructura programatica)
'------------------------------------------------------------------------------
Public Function GenerarPreventivoC31(ByVal nroInterno As String, Optional ByVal aPDF As Boolean = True) As String
    Dim shC As Worksheet, shD As Worksheet, rC As Long, r As Long, n As Long, d() As Variant
    ChequeoDoc
    Set shC = WS(SH_C31): Set shD = WS(SH_C31D)
    rC = FindRow(shC, "NroInterno", nroInterno)
    If rC = 0 Then Fail "Preventivo inexistente."
    Membrete "PV"
    PutN "PV_Nro", nroInterno
    PutN "PV_Sigep", GetV(shC, rC, "NroC31_SIGEP")
    PutN "PV_Fecha", GetV(shC, rC, "Fecha")
    PutN "PV_DA", GetV(shC, rC, "DA")
    PutN "PV_UE", GetV(shC, rC, "UE")
    PutN "PV_Solicitud", GetV(shC, rC, "ID_Solicitud")
    PutN "PV_Estado", GetV(shC, rC, "Estado")
    ReDim d(1 To 10, 1 To 9)
    For r = 2 To LastRow(shD)
        If CStr(GetV(shD, r, "NroInterno")) = nroInterno Then
            n = n + 1
            d(n, 1) = GetV(shD, r, "Linea"): d(n, 2) = GetV(shD, r, "Programa"): d(n, 3) = GetV(shD, r, "Proyecto")
            d(n, 4) = GetV(shD, r, "ActObra"): d(n, 5) = GetV(shD, r, "Fuente"): d(n, 6) = GetV(shD, r, "Organismo")
            d(n, 7) = GetV(shD, r, "Partida"): d(n, 8) = GetV(shD, r, "Importe"): d(n, 9) = GetV(shD, r, "ImporteRevertido")
        End If
    Next r
    FillTable "PV_LineasIni", 10, d, n, 9
    PutN "PV_Literal", MontoLiteral(CDbl(GetV(shC, rC, "MontoTotal")) - CDbl(GetV(shC, rC, "MontoRevertido")))
    GenerarPreventivoC31 = Cerrar(DOC_C31, "C31_" & nroInterno, aPDF)
End Function

'------------------------------------------------------------------------------
' 5) Orden de Compra / Servicio
'------------------------------------------------------------------------------
Public Function GenerarDocOrden(ByVal nroOrden As String, Optional ByVal aPDF As Boolean = True) As String
    Dim shO As Worksheet, rO As Long, shD As Worksheet, r As Long, n As Long, d() As Variant, idSol As String
    ChequeoDoc
    Set shO = WS(SH_ORD)
    rO = FindRow(shO, "NroOrden", nroOrden)
    If rO = 0 Then Fail "Orden inexistente."
    idSol = CStr(GetV(shO, rO, "ID_Solicitud"))
    FilaSolicitud idSol
    If CStr(GetV(shO, rO, "EstadoOrden")) = "ANULADA" Then Fail "La Orden esta ANULADA; no se imprime."
    If Len(ValidarSolicitudParaOrden(idSol)) > 0 Then Fail "No se imprime: la solicitud tiene observaciones CHB."
    Membrete "OC"
    PutN "OC_Titulo", "ORDEN DE " & UCase$(CStr(GetV(shO, rO, "Tipo")))
    PutN "OC_Nro", nroOrden
    PutN "OC_CUCE", GetV(shO, rO, "CUCE_SICOES")
    PutN "OC_Fecha", GetV(shO, rO, "FechaEmision")
    PutN "OC_Proveedor", GetV(shO, rO, "Proveedor_Adjudicado")
    PutN "OC_NIT", GetV(shO, rO, "NIT")
    PutN "OC_Solicitud", idSol
    PutN "OC_C31", GetV(shO, rO, "NroPreventivo_C31")
    PutN "OC_Plazo", GetV(shO, rO, "PlazoDias")
    PutN "OC_Lugar", GetV(shO, rO, "LugarEntrega")
    PutN "OC_Monto", GetV(shO, rO, "MontoTotal")
    PutN "OC_Literal", MontoLiteral(CDbl(GetV(shO, rO, "MontoTotal")))
    PutN "OC_PenPorMil", CfgNum("PenalidadPorMil", 3)
    PutN "OC_PenMaxPct", CfgNum("PenalidadMaxPct", 10)
    Set shD = WS(SH_DET)
    ReDim d(1 To 15, 1 To 4)
    For r = 2 To LastRow(shD)
        If CStr(GetV(shD, r, "ID_Solicitud")) = idSol Then
            n = n + 1
            d(n, 1) = GetV(shD, r, "Item"): d(n, 2) = GetV(shD, r, "Descripcion")
            d(n, 3) = GetV(shD, r, "Unidad"): d(n, 4) = GetV(shD, r, "Cantidad")
        End If
    Next r
    FillTable "OC_ItemsIni", 15, d, n, 4
    GenerarDocOrden = Cerrar(DOC_ORDEN, nroOrden, aPDF)
End Function

'------------------------------------------------------------------------------
' 6) Acta de Recepcion y Conformidad
'------------------------------------------------------------------------------
Public Function GenerarActaRecepcion(ByVal nroRecepcion As String, Optional ByVal aPDF As Boolean = True) As String
    Dim shR As Worksheet, shO As Worksheet, rR As Long, rO As Long
    ChequeoDoc
    Set shR = WS(SH_REC): Set shO = WS(SH_ORD)
    rR = FindRow(shR, "NroRecepcion", nroRecepcion)
    If rR = 0 Then Fail "Recepcion inexistente."
    rO = FindRow(shO, "NroOrden", CStr(GetV(shR, rR, "NroOrden")))
    FilaSolicitud CStr(GetV(shO, rO, "ID_Solicitud"))
    Membrete "AR"
    PutN "AR_Nro", nroRecepcion
    PutN "AR_Fecha", GetV(shR, rR, "FechaRecepcion")
    PutN "AR_Orden", GetV(shR, rR, "NroOrden")
    PutN "AR_Solicitud", GetV(shO, rO, "ID_Solicitud")
    PutN "AR_Proveedor", GetV(shO, rO, "Proveedor_Adjudicado")
    PutN "AR_Limite", GetV(shR, rR, "FechaLimite")
    PutN "AR_Dias", GetV(shR, rR, "DiasRetraso")
    PutN "AR_Monto", GetV(shO, rO, "MontoTotal")
    PutN "AR_Multa", GetV(shR, rR, "MontoMulta")
    PutN "AR_Conformidad", GetV(shR, rR, "Resultado")
    PutN "AR_Obs", GetV(shR, rR, "Observaciones")
    GenerarActaRecepcion = Cerrar(DOC_ACTA, "ACTA_" & nroRecepcion, aPDF)
End Function

'------------------------------------------------------------------------------
' Cierre: audita y exporta a PDF (o solo deja la hoja lista para imprimir)
'------------------------------------------------------------------------------
Private Function Cerrar(ByVal hoja As String, ByVal baseName As String, ByVal aPDF As Boolean) As String
    LogAudit "DOC_GENERADO", hoja & " / " & baseName
    If aPDF Then Cerrar = ExportarPDF(hoja, baseName) Else Cerrar = hoja
End Function

Public Function ExportarPDF(ByVal hoja As String, ByVal baseName As String) As String
    Dim sh As Worksheet, carpeta As String, ruta As String
    Set sh = WS(hoja)
    carpeta = ThisWorkbook.Path & "\PDF"
    If Len(Dir$(carpeta, vbDirectory)) = 0 Then MkDir carpeta
    ruta = carpeta & "\" & Replace(baseName, "/", "-") & "_" & Format$(Now, "yyyymmdd_hhnnss") & ".pdf"
    ThisWorkbook.Unprotect PROT_PWD            ' ExportAsFixedFormat exige hoja visible
    sh.Visible = xlSheetVisible
    On Error GoTo Fin
    sh.ExportAsFixedFormat Type:=xlTypePDF, Filename:=ruta, Quality:=xlQualityStandard, _
                           IncludeDocProperties:=True, IgnorePrintAreas:=False, OpenAfterPublish:=False
    ExportarPDF = ruta
Fin:
    sh.Visible = xlSheetVeryHidden
    ThisWorkbook.Protect Password:=PROT_PWD, Structure:=True
    If Err.Number <> 0 Then Fail "No se pudo exportar el PDF: " & Err.Description
End Function
