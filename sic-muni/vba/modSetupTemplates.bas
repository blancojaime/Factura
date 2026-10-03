Attribute VB_Name = "modSetupTemplates"
'==============================================================================
' SIC-MUNI - modSetupTemplates
' Construye las 5 hojas de plantilla (Doc_*) con formato, rangos con nombre y
' formulas. Se puede re-ejecutar: recrea las plantillas desde cero.
'==============================================================================
Option Explicit

Private Const COL_HDR As Long = 12611584    ' RGB(0,112,192) aprox. (BGR)

Public Sub BuildTemplates()
    BuildC1
    BuildCuadro
    BuildExcepcion
    BuildC31
    BuildOrden
End Sub

'------------------------------------------------------------------------------
' Helpers
'------------------------------------------------------------------------------
Private Function Hoja(ByVal nombre As String, ByVal widths As String, ByVal titulo As String, ByVal pref As String) As Worksheet
    Dim sh As Worksheet, w() As String, i As Long, nCols As Long, nm As Name
    Application.DisplayAlerts = False
    On Error Resume Next
    ThisWorkbook.Worksheets(nombre).Visible = xlSheetVisible
    ThisWorkbook.Worksheets(nombre).Unprotect PROT_PWD
    ThisWorkbook.Worksheets(nombre).Delete
    On Error GoTo 0
    Application.DisplayAlerts = True
    Set sh = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
    sh.Name = nombre
    sh.Cells.Font.Name = "Arial": sh.Cells.Font.Size = 9
    ActiveWindow.DisplayGridlines = False
    w = Split(widths, ",")
    nCols = UBound(w) + 1
    For i = 0 To UBound(w): sh.Columns(i + 1).ColumnWidth = CDbl(w(i)): Next i
    ' Membrete (fila 1 = entidad; fila 2 = titulo; fila 3 = gestion)
    sh.Range(sh.Cells(1, 1), sh.Cells(1, nCols)).Merge
    sh.Range(sh.Cells(2, 1), sh.Cells(2, nCols)).Merge
    sh.Cells(1, 1).Font.Size = 13: sh.Cells(1, 1).Font.Bold = True
    sh.Cells(2, 1).Value = titulo: sh.Cells(2, 1).Font.Size = 11: sh.Cells(2, 1).Font.Bold = True
    sh.Range(sh.Cells(1, 1), sh.Cells(2, nCols)).HorizontalAlignment = xlCenter
    sh.Cells(3, 1).Value = "Gestion:": sh.Cells(3, 2).Font.Bold = True
    sh.Range(sh.Cells(2, 1), sh.Cells(2, nCols)).Borders(xlEdgeBottom).LineStyle = xlContinuous
    NombreRango sh, pref & "_Entidad", 1, 1
    NombreRango sh, pref & "_Gestion", 3, 2
    Set Hoja = sh
End Function

Private Sub NombreRango(ByVal sh As Worksheet, ByVal nm As String, ByVal r As Long, ByVal c As Long)
    ThisWorkbook.Names.Add Name:=nm, RefersTo:="='" & sh.Name & "'!" & sh.Cells(r, c).Address
End Sub

' Par etiqueta/valor. Une celdas si el rango tiene mas de una columna.
Private Sub Par(ByVal sh As Worksheet, ByVal r As Long, ByVal l1 As Long, ByVal l2 As Long, ByVal etiqueta As String, _
                ByVal v1 As Long, ByVal v2 As Long, ByVal nm As String, Optional ByVal fmt As String = "")
    If l2 > l1 Then sh.Range(sh.Cells(r, l1), sh.Cells(r, l2)).Merge
    If v2 > v1 Then sh.Range(sh.Cells(r, v1), sh.Cells(r, v2)).Merge
    sh.Cells(r, l1).Value = etiqueta: sh.Cells(r, l1).Font.Bold = True
    sh.Range(sh.Cells(r, v1), sh.Cells(r, v2)).Borders(xlEdgeBottom).LineStyle = xlContinuous
    sh.Cells(r, v1).HorizontalAlignment = xlLeft
    If Len(fmt) > 0 Then sh.Cells(r, v1).NumberFormat = fmt
    NombreRango sh, nm, r, v1
End Sub

Private Sub Encabezado(ByVal sh As Worksheet, ByVal r As Long, ByVal textos As String)
    Dim t() As String, i As Long
    t = Split(textos, "|")
    For i = 0 To UBound(t): sh.Cells(r, i + 1).Value = t(i): Next i
    With sh.Range(sh.Cells(r, 1), sh.Cells(r, UBound(t) + 1))
        .Font.Bold = True: .Font.Color = vbWhite: .Interior.Color = COL_HDR
        .HorizontalAlignment = xlCenter: .VerticalAlignment = xlCenter: .WrapText = True
        .Borders.LineStyle = xlContinuous
    End With
    sh.Rows(r).RowHeight = 26
End Sub

Private Sub Cuerpo(ByVal sh As Worksheet, ByVal r1 As Long, ByVal r2 As Long, ByVal nCols As Long)
    With sh.Range(sh.Cells(r1, 1), sh.Cells(r2, nCols))
        .Borders.LineStyle = xlContinuous: .VerticalAlignment = xlTop: .WrapText = True
    End With
End Sub

Private Sub Firmas(ByVal sh As Worksheet, ByVal r As Long, ByVal nCols As Long, ByVal roles As String)
    Dim t() As String, i As Long, ancho As Long, c1 As Long
    t = Split(roles, "|")
    ancho = nCols \ (UBound(t) + 1)
    sh.Rows(r).RowHeight = 42
    For i = 0 To UBound(t)
        c1 = i * ancho + 1
        sh.Range(sh.Cells(r, c1), sh.Cells(r, c1 + ancho - 1)).Merge
        sh.Range(sh.Cells(r + 1, c1), sh.Cells(r + 1, c1 + ancho - 1)).Merge
        sh.Cells(r, c1).Borders(xlEdgeBottom).LineStyle = xlNone
        sh.Range(sh.Cells(r, c1), sh.Cells(r, c1 + ancho - 1)).Borders(xlEdgeBottom).LineStyle = xlContinuous
        sh.Cells(r + 1, c1).Value = t(i): sh.Cells(r + 1, c1).HorizontalAlignment = xlCenter: sh.Cells(r + 1, c1).Font.Bold = True
    Next i
End Sub

Private Sub Pie(ByVal sh As Worksheet, ByVal r As Long, ByVal nCols As Long, ByVal pref As String)
    sh.Range(sh.Cells(r, 1), sh.Cells(r, nCols)).Merge
    sh.Cells(r, 1).Font.Size = 7: sh.Cells(r, 1).Font.Italic = True
    NombreRango sh, pref & "_Pie", r, 1
End Sub

Private Sub Texto(ByVal sh As Worksheet, ByVal r1 As Long, ByVal r2 As Long, ByVal nCols As Long, ByVal valor As String, Optional ByVal esFormula As Boolean = False)
    sh.Range(sh.Cells(r1, 1), sh.Cells(r2, nCols)).Merge
    If esFormula Then sh.Cells(r1, 1).Formula = valor Else sh.Cells(r1, 1).Value = valor
    sh.Cells(r1, 1).WrapText = True: sh.Cells(r1, 1).VerticalAlignment = xlTop
End Sub

Private Sub PageSetup_(ByVal sh As Worksheet, ByVal lastRow As Long, ByVal nCols As Long, ByVal horizontal As Boolean)
    On Error Resume Next      ' sin impresora instalada PageSetup puede fallar
    With sh.PageSetup
        .PrintArea = sh.Range(sh.Cells(1, 1), sh.Cells(lastRow, nCols)).Address
        .Orientation = IIf(horizontal, xlLandscape, xlPortrait)
        .PaperSize = xlPaperLetter
        .Zoom = False: .FitToPagesWide = 1: .FitToPagesTall = 1
        .CenterHorizontally = True
        .LeftMargin = Application.CentimetersToPoints(1.5): .RightMargin = Application.CentimetersToPoints(1.5)
    End With
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' 1) Doc_Solicitud_C1  (A:H)
'------------------------------------------------------------------------------
Private Sub BuildC1()
    Dim sh As Worksheet
    Set sh = Hoja(DOC_C1, "6,14,38,10,10,13,13,8", "FORMULARIO C-1 - REQUERIMIENTO Y ESPECIFICACIONES TECNICAS", "C1")
    Par sh, 5, 1, 2, "N Solicitud:", 3, 4, "C1_Solicitud"
    Par sh, 5, 5, 6, "Fecha:", 7, 8, "C1_Fecha", "dd/mm/yyyy"
    Par sh, 6, 1, 2, "Direccion Admin. (DA):", 3, 4, "C1_DA"
    Par sh, 6, 5, 6, "Unidad Ejecutora (UE):", 7, 8, "C1_UE"
    Par sh, 7, 1, 2, "Solicitante:", 3, 4, "C1_Solicitante"
    Par sh, 7, 5, 6, "Modalidad:", 7, 8, "C1_Modalidad"
    sh.Cells(8, 1).Value = "Justificacion:": sh.Cells(8, 1).Font.Bold = True
    sh.Range("A8:B8").Merge: sh.Range("C8:H8").Merge: sh.Cells(8, 3).WrapText = True: sh.Rows(8).RowHeight = 40
    NombreRango sh, "C1_Justificacion", 8, 3
    Encabezado sh, 10, "Item|Codigo UNSPSC|Descripcion y especificaciones tecnicas|Unidad|Cantidad|P. Ref. Unit. (Bs)|Total (Bs)|CHB"
    Cuerpo sh, 11, 25, 8
    NombreRango sh, "C1_ItemsIni", 11, 1
    sh.Range("B11:B25").NumberFormat = "@"
    sh.Range("E11:E25").NumberFormat = "#,##0.00": sh.Range("F11:G25").NumberFormat = "#,##0.00"
    sh.Range("G11:G25").Formula = "=IF(E11="""","""",ROUND(E11*F11,2))"          ' columna calculada
    sh.Cells(26, 6).Value = "TOTAL Bs": sh.Cells(26, 6).Font.Bold = True: sh.Cells(26, 6).HorizontalAlignment = xlRight
    sh.Cells(26, 7).Formula = "=SUM(G11:G25)": sh.Cells(26, 7).NumberFormat = "#,##0.00": sh.Cells(26, 7).Font.Bold = True
    sh.Cells(26, 7).Borders.LineStyle = xlContinuous
    sh.Range("A27:H27").Merge: NombreRango sh, "C1_Literal", 27, 1: sh.Cells(27, 1).Font.Italic = True
    Texto sh, 29, 31, 8, "DECLARACION: El servidor publico solicitante declara que el presente requerimiento responde a una necesidad " & _
        "institucional prevista en el POA/PAC, que las especificaciones tecnicas no direccionan la contratacion hacia un proveedor determinado " & _
        "y que no se encuentra comprendido en causales de impedimento ni conflicto de intereses (art. 43 NB-SABS segun especificacion del proyecto)."
    Firmas sh, 34, 8, "Servidor publico solicitante|Jefe de Unidad / Autoridad|Responsable de Contrataciones (RC)"
    Pie sh, 37, 8, "C1"
    PageSetup_ sh, 37, 8, False
End Sub

'------------------------------------------------------------------------------
' 2) Doc_CuadroComparativo  (A:H)
'------------------------------------------------------------------------------
Private Sub BuildCuadro()
    Dim sh As Worksheet
    Set sh = Hoja(DOC_CUADRO, "5,13,32,12,14,12,14,11", "CUADRO COMPARATIVO DE COTIZACIONES", "CC")
    Par sh, 5, 1, 2, "N Solicitud:", 3, 4, "CC_Solicitud"
    Par sh, 5, 5, 6, "Fecha:", 7, 8, "CC_Fecha", "dd/mm/yyyy"
    Par sh, 6, 1, 2, "Modalidad:", 3, 4, "CC_Modalidad"
    Par sh, 6, 5, 6, "Referencial (Bs):", 7, 8, "CC_Referencial", "#,##0.00"
    Par sh, 7, 1, 2, "Criterio evaluacion:", 3, 8, "CC_Criterio"
    sh.Cells(7, 3).WrapText = True: sh.Rows(7).RowHeight = 26
    Encabezado sh, 9, "N|NIT|Razon social|Validez oferta|Monto cotizado (Bs)|Evaluacion tecnica|Resultado|Var. vs referencial"
    Cuerpo sh, 10, 19, 8
    NombreRango sh, "CC_OfertasIni", 10, 1
    sh.Range("B10:B19").NumberFormat = "@": sh.Range("D10:D19").NumberFormat = "dd/mm/yyyy": sh.Range("E10:E19").NumberFormat = "#,##0.00"
    sh.Range("H10:H19").Formula = "=IF(E10="""","""",E10/$G$6-1)": sh.Range("H10:H19").NumberFormat = "0.0%"   ' columna calculada
    sh.Cells(20, 4).Value = "Menor oferta habil (Bs):": sh.Range("D20:E20").Merge: sh.Cells(20, 4).Font.Bold = True
    sh.Cells(20, 6).Formula = "=IFERROR(AGGREGATE(15,6,E10:E19/(F10:F19=""Cumple""),1),"""")"
    sh.Cells(20, 6).NumberFormat = "#,##0.00": sh.Cells(20, 6).Font.Bold = True
    sh.Range("A22:H23").Merge: NombreRango sh, "CC_Recomendacion", 22, 1
    sh.Cells(22, 1).Font.Bold = True: sh.Cells(22, 1).WrapText = True: sh.Cells(22, 1).VerticalAlignment = xlTop
    Firmas sh, 27, 8, "Responsable de Contrataciones (RC)|Unidad Solicitante"
    Pie sh, 30, 8, "CC"
    PageSetup_ sh, 30, 8, True
End Sub

'------------------------------------------------------------------------------
' 3) Doc_JustificacionExcepcionCHB  (A:G)
'------------------------------------------------------------------------------
Private Sub BuildExcepcion()
    Dim sh As Worksheet
    Set sh = Hoja(DOC_EXCEPCION, "5,13,28,16,16,12,50", "JUSTIFICACION DE EXCEPCION DE FICHA TECNICA - CATALOGO CHB", "EX")
    Par sh, 5, 1, 2, "N Solicitud:", 3, 4, "EX_Solicitud"
    Par sh, 5, 5, 6, "Fecha:", 7, 7, "EX_Fecha", "dd/mm/yyyy"
    Par sh, 6, 1, 2, "Direccion Admin.:", 3, 4, "EX_DA"
    Par sh, 6, 5, 6, "Solicitante:", 7, 7, "EX_Solicitante"
    Texto sh, 8, 10, 7, "Conforme al marco del Catalogo Electronico 'Compro Hecho en Bolivia' (D.S. 4505 y R.B.M. 012/2024, segun la especificacion del proyecto), " & _
        "la Unidad Solicitante justifica la contratacion FUERA del mercado virtual de los items detallados, por insuficiencia tecnica de calidad, cantidad o plazos, " & _
        "contando con la Autorizacion expresa del Ministerio de Desarrollo Productivo y Economia Plural (MDPyEP) y el Codigo Unico de Excepcion consignados."
    Encabezado sh, 12, "Item|Codigo UNSPSC|Descripcion|Cod. Excepcion MDPyEP|N Autorizacion MDPyEP|Fecha autorizacion|Justificacion tecnica / legal"
    Cuerpo sh, 13, 22, 7
    NombreRango sh, "EX_ItemsIni", 13, 1
    sh.Range("B13:B22").NumberFormat = "@": sh.Range("F13:F22").NumberFormat = "dd/mm/yyyy"
    Firmas sh, 26, 7, "Unidad Solicitante|Responsable de Contrataciones (RC)"
    Pie sh, 29, 7, "EX"
    PageSetup_ sh, 29, 7, True
End Sub

'------------------------------------------------------------------------------
' 4) Doc_Preventivo_C31  (A:J)
'------------------------------------------------------------------------------
Private Sub BuildC31()
    Dim sh As Worksheet
    Set sh = Hoja(DOC_C31, "6,10,10,10,8,10,12,16,16,16", "C-31 PREVENTIVO - RESERVA PRESUPUESTARIA (REGISTRO INTERNO)", "PV")
    Par sh, 5, 1, 2, "N Interno:", 3, 4, "PV_Nro"
    Par sh, 5, 5, 7, "N C-31 SIGEP:", 8, 10, "PV_Sigep"
    Par sh, 6, 1, 2, "Fecha:", 3, 4, "PV_Fecha", "dd/mm/yyyy"
    Par sh, 6, 5, 7, "Estado:", 8, 10, "PV_Estado"
    Par sh, 7, 1, 2, "DA:", 3, 4, "PV_DA"
    Par sh, 7, 5, 7, "UE:", 8, 10, "PV_UE"
    Par sh, 8, 1, 2, "Solicitud:", 3, 4, "PV_Solicitud"
    Encabezado sh, 10, "Linea|Programa|Proyecto|Act./Obra|Fuente|Organismo|Partida (Objeto del Gasto)|Importe (Bs)|Revertido (Bs)|Vigente (Bs)"
    Cuerpo sh, 11, 20, 10
    NombreRango sh, "PV_LineasIni", 11, 1
    sh.Range("B11:G20").NumberFormat = "@": sh.Range("H11:J20").NumberFormat = "#,##0.00"
    sh.Range("J11:J20").Formula = "=IF(H11="""","""",H11-I11)"                      ' columna calculada
    sh.Cells(21, 7).Value = "TOTAL Bs": sh.Cells(21, 7).Font.Bold = True: sh.Cells(21, 7).HorizontalAlignment = xlRight
    sh.Cells(21, 8).Formula = "=SUM(H11:H20)": sh.Cells(21, 9).Formula = "=SUM(I11:I20)": sh.Cells(21, 10).Formula = "=SUM(J11:J20)"
    sh.Range("H21:J21").NumberFormat = "#,##0.00": sh.Range("H21:J21").Font.Bold = True: sh.Range("H21:J21").Borders.LineStyle = xlContinuous
    sh.Range("A22:J22").Merge: NombreRango sh, "PV_Literal", 22, 1: sh.Cells(22, 1).Font.Italic = True
    Texto sh, 24, 25, 10, "Boleta interna de reserva presupuestaria preventiva (art. 22 Normas Basicas de Contabilidad Integrada, segun especificacion). " & _
        "El C-31 oficial es el registrado y aprobado en el SIGEP; su numero se consigna en el campo N C-31 SIGEP."
    Firmas sh, 28, 10, "Presupuesto / Finanzas (PF)|Responsable de Contrataciones (RC)|Autoridad competente"
    Pie sh, 31, 10, "PV"
    PageSetup_ sh, 31, 10, True
End Sub

'------------------------------------------------------------------------------
' 5) Doc_OrdenCompraServicio  (A:F)  - clausulas = formulas con rangos nombrados
'------------------------------------------------------------------------------
Private Sub BuildOrden()
    Dim sh As Worksheet
    Set sh = Hoja(DOC_ORDEN, "6,46,12,12,16,16", "ORDEN", "OC")
    sh.Cells(2, 1).Value = "": NombreRango sh, "OC_Titulo", 2, 1
    Par sh, 4, 1, 2, "N Orden:", 3, 4, "OC_Nro"
    Par sh, 4, 5, 5, "Fecha:", 6, 6, "OC_Fecha", "dd/mm/yyyy"
    Par sh, 5, 1, 2, "CUCE (SICOES):", 3, 4, "OC_CUCE"
    Par sh, 5, 5, 5, "Solicitud:", 6, 6, "OC_Solicitud"
    Par sh, 6, 1, 2, "Proveedor adjudicado:", 3, 6, "OC_Proveedor"
    Par sh, 7, 1, 2, "NIT:", 3, 4, "OC_NIT"
    Par sh, 7, 5, 5, "C-31:", 6, 6, "OC_C31"
    Par sh, 8, 1, 2, "Plazo (dias calendario):", 3, 4, "OC_Plazo"
    Par sh, 9, 1, 2, "Lugar entrega/prestacion:", 3, 6, "OC_Lugar"
    Encabezado sh, 11, "Item|Descripcion|Unidad|Cantidad"
    Cuerpo sh, 12, 26, 4
    NombreRango sh, "OC_ItemsIni", 12, 1
    sh.Cells(27, 5).Value = "MONTO TOTAL Bs": sh.Cells(27, 5).Font.Bold = True: sh.Cells(27, 5).HorizontalAlignment = xlRight
    NombreRango sh, "OC_Monto", 27, 6: sh.Cells(27, 6).NumberFormat = "#,##0.00": sh.Cells(27, 6).Font.Bold = True
    sh.Cells(27, 6).Borders.LineStyle = xlContinuous
    sh.Range("A28:F28").Merge: NombreRango sh, "OC_Literal", 28, 1: sh.Cells(28, 1).Font.Italic = True
    ' Parametros de penalidad (celdas de apoyo fuera del area de impresion, col H)
    sh.Cells(1, 8).Value = "PenPorMil": NombreRango sh, "OC_PenPorMil", 2, 8
    sh.Cells(1, 9).Value = "PenMaxPct": NombreRango sh, "OC_PenMaxPct", 2, 9
    Texto sh, 30, 31, 6, "=""CLAUSULA PRIMERA (OBJETO): El proveedor se obliga a proveer los bienes o servicios detallados, conforme a las especificaciones tecnicas del Formulario C-1 de la solicitud ""&OC_Solicitud&"".""", True
    Texto sh, 32, 33, 6, "=""CLAUSULA SEGUNDA (PLAZO Y LUGAR): El plazo es de ""&OC_Plazo&"" dias calendario computables desde la fecha de emision de la presente Orden, en ""&OC_Lugar&"".""", True
    Texto sh, 34, 36, 6, "=""CLAUSULA TERCERA (PENALIDADES): El retraso injustificado se sancionara con multa de ""&OC_PenPorMil&"" por mil del monto total por dia calendario de retraso, ""&""hasta un maximo del ""&OC_PenMaxPct&""% del monto de la Orden, descontable del pago; alcanzado el maximo, la entidad podra resolver la Orden.""", True
    Texto sh, 37, 38, 6, "CLAUSULA CUARTA (RECEPCION): La recepcion estara a cargo del Responsable o Comision de Recepcion, que emitira el Informe o Acta de Conformidad. Lo observado debera subsanarse sin costo para la entidad.", False
    Texto sh, 39, 40, 6, "=""CLAUSULA QUINTA (FORMA DE PAGO): El pago se efectuara contra entrega, conformidad y factura, con cargo al Preventivo C-31 N ""&OC_C31&"", por Bs ""&TEXT(OC_Monto,""#,##0.00"")&"".""", True
    Texto sh, 41, 42, 6, "CLAUSULA SEXTA (MARCO NORMATIVO): La presente Orden se emite en el marco de las NB-SABS para contratacion menor (arts. 85 y 86 segun especificacion del proyecto) y de la condicion CHB/excepcion autorizada de la solicitud.", False
    Firmas sh, 45, 6, "Responsable de Contrataciones (RC)|Proveedor (recibi conforme)"
    Pie sh, 48, 6, "OC"
    PageSetup_ sh, 48, 6, False
End Sub
