Imports System.IO
Imports ClosedXML.Excel

Namespace Reports

    ''' <summary>Exporta el mismo reporte a un libro Excel (.xlsx) con formato profesional, listo para filtrar y analizar.</summary>
    Public Module ExcelExporter

        Public Sub Exportar(rep As ReporteDef, ruta As String)
            Dim dir As String = Path.GetDirectoryName(ruta)
            If Not String.IsNullOrEmpty(dir) Then Directory.CreateDirectory(dir)
            Using wb As XLWorkbook = Generar(rep)
                wb.SaveAs(ruta)
            End Using
        End Sub

        Private Function NombreHoja(s As String) As String
            Dim t As String = If(s, "Reporte")
            For Each c As Char In "[]:*?/\".ToCharArray()
                t = t.Replace(c, "-"c)
            Next
            If t.Length > 31 Then t = t.Substring(0, 31)
            Return If(t.Trim() = "", "Reporte", t)
        End Function

        Public Function Generar(rep As ReporteDef) As XLWorkbook
            Dim wb As New XLWorkbook()
            Dim ws As IXLWorksheet = wb.Worksheets.Add(NombreHoja(If(rep.Hoja <> "", rep.Hoja, rep.Titulo)))
            Dim n As Integer = Math.Max(1, rep.Columnas.Count)
            Dim azul As XLColor = XLColor.FromArgb(31, 58, 95)
            Dim azulClaro As XLColor = XLColor.FromArgb(222, 231, 243)
            Dim r As Integer = 1
            ws.Cell(r, 1).Value = rep.Empresa
            ws.Cell(r, 1).Style.Font.Bold = True
            ws.Cell(r, 1).Style.Font.FontSize = 14
            ws.Cell(r, 1).Style.Font.FontColor = azul
            r += 1
            Dim linea2 As String = String.Join("   ", {If(rep.Nit <> "", "NIT: " & rep.Nit, ""), rep.Direccion, If(rep.Gestion <> "", "Gestión " & rep.Gestion, "")}.Where(Function(s) s <> ""))
            If linea2 <> "" Then
                ws.Cell(r, 1).Value = linea2
                ws.Cell(r, 1).Style.Font.FontSize = 9
                r += 1
            End If
            ws.Cell(r, 1).Value = rep.Titulo.ToUpperInvariant()
            ws.Range(r, 1, r, n).Merge()
            ws.Cell(r, 1).Style.Font.Bold = True
            ws.Cell(r, 1).Style.Font.FontSize = 13
            ws.Cell(r, 1).Style.Alignment.Horizontal = XLAlignmentHorizontalValues.Center
            r += 1
            Dim sub1 As String = String.Join("  ·  ", {rep.Subtitulo, rep.Periodo, rep.Moneda}.Where(Function(s) s <> ""))
            If sub1 <> "" Then
                ws.Cell(r, 1).Value = sub1
                ws.Range(r, 1, r, n).Merge()
                ws.Cell(r, 1).Style.Alignment.Horizontal = XLAlignmentHorizontalValues.Center
                ws.Cell(r, 1).Style.Font.Italic = True
                r += 1
            End If
            r += 1
            For Each kv In rep.Cabecera
                ws.Cell(r, 1).Value = kv.Key
                ws.Cell(r, 1).Style.Font.Bold = True
                ws.Cell(r, 2).Value = kv.Value
                If n > 2 Then ws.Range(r, 2, r, n).Merge()
                r += 1
            Next
            If rep.Cabecera.Count > 0 Then r += 1
            Dim filaEnc As Integer = r
            For i As Integer = 0 To rep.Columnas.Count - 1
                Dim c As IXLCell = ws.Cell(r, i + 1)
                c.Value = rep.Columnas(i).Titulo
                c.Style.Font.Bold = True
                c.Style.Font.FontColor = XLColor.White
                c.Style.Fill.BackgroundColor = azul
                c.Style.Alignment.Horizontal = If(rep.Columnas(i).Alineacion = Alinea.Izquierda, XLAlignmentHorizontalValues.Left, XLAlignmentHorizontalValues.Center)
                c.Style.Alignment.Vertical = XLAlignmentVerticalValues.Center
                c.Style.Alignment.WrapText = True
            Next
            ws.Row(r).Height = 24
            r += 1
            Dim primeraDato As Integer = r
            For Each f As FilaRep In rep.Filas
                Select Case f.Tipo
                    Case TipoFila.Salto, TipoFila.Vacia
                        r += 1
                        Continue For
                    Case TipoFila.Grupo, TipoFila.Titulo, TipoFila.Texto
                        ws.Cell(r, 1).Value = If(f.Celdas.Count > 0, Convert.ToString(f.Celdas(0)), "")
                        ws.Range(r, 1, r, n).Merge()
                        If f.Tipo <> TipoFila.Texto Then
                            ws.Range(r, 1, r, n).Style.Fill.BackgroundColor = azulClaro
                            ws.Range(r, 1, r, n).Style.Font.Bold = True
                        ElseIf f.Negrita Then
                            ws.Cell(r, 1).Style.Font.Bold = True
                        End If
                        r += 1
                        Continue For
                End Select
                For i As Integer = 0 To rep.Columnas.Count - 1
                    Dim v As Object = If(i < f.Celdas.Count, f.Celdas(i), Nothing)
                    Dim c As IXLCell = ws.Cell(r, i + 1)
                    Dim col As ColumnaRep = rep.Columnas(i)
                    If v IsNot Nothing AndAlso v IsNot DBNull.Value Then
                        Select Case col.Formato
                            Case Formato.Monto
                                If TypeOf v Is String Then
                                    c.Value = CStr(v)
                                Else
                                    c.Value = Convert.ToDecimal(v)
                                    c.Style.NumberFormat.Format = "#,##0.00;[Red]-#,##0.00;0.00"
                                End If
                            Case Formato.Cantidad
                                If TypeOf v Is String Then
                                    c.Value = CStr(v)
                                Else
                                    c.Value = Convert.ToDecimal(v)
                                    c.Style.NumberFormat.Format = "#,##0.####"
                                End If
                            Case Formato.Precio
                                If TypeOf v Is String Then
                                    c.Value = CStr(v)
                                Else
                                    c.Value = Convert.ToDecimal(v)
                                    c.Style.NumberFormat.Format = "#,##0.0000"
                                End If
                            Case Formato.Entero
                                If TypeOf v Is String Then
                                    c.Value = CStr(v)
                                Else
                                    c.Value = Convert.ToInt64(v)
                                    c.Style.NumberFormat.Format = "#,##0"
                                End If
                            Case Formato.Porcentaje
                                If TypeOf v Is String Then
                                    c.Value = CStr(v)
                                Else
                                    c.Value = Convert.ToDecimal(v) / 100D
                                    c.Style.NumberFormat.Format = "0.00%"
                                End If
                            Case Formato.Fecha
                                If TypeOf v Is Date Then
                                    If CDate(v) <> Date.MinValue Then
                                        c.Value = CDate(v)
                                        c.Style.NumberFormat.Format = "dd/MM/yyyy"
                                    End If
                                Else
                                    c.Value = Convert.ToString(v)
                                End If
                            Case Else
                                c.Value = Convert.ToString(v)
                        End Select
                    End If
                    c.Style.Alignment.Horizontal = If(col.Alineacion = Alinea.Derecha, XLAlignmentHorizontalValues.Right, If(col.Alineacion = Alinea.Centro, XLAlignmentHorizontalValues.Center, XLAlignmentHorizontalValues.Left))
                    If i = 0 AndAlso f.Nivel > 0 Then c.Style.Alignment.Indent = Math.Min(15, f.Nivel)
                    c.Style.Alignment.Vertical = XLAlignmentVerticalValues.Top
                    If col.Formato = Formato.Texto Then c.Style.Alignment.WrapText = True
                Next
                Dim rango As IXLRange = ws.Range(r, 1, r, n)
                Select Case f.Tipo
                    Case TipoFila.Subtotal
                        rango.Style.Font.Bold = True
                        rango.Style.Border.TopBorder = XLBorderStyleValues.Thin
                    Case TipoFila.Total
                        rango.Style.Font.Bold = True
                        rango.Style.Fill.BackgroundColor = azulClaro
                        rango.Style.Border.TopBorder = XLBorderStyleValues.Thin
                        rango.Style.Border.BottomBorder = XLBorderStyleValues.Double
                    Case Else
                        If f.Negrita Then rango.Style.Font.Bold = True
                        rango.Style.Border.BottomBorder = XLBorderStyleValues.Hair
                End Select
                r += 1
            Next
            Dim ultima As Integer = r - 1
            ' anchos
            Dim suma As Double = Math.Max(1R, rep.Columnas.Sum(Function(c) c.Peso))
            Dim total As Double = If(rep.Horizontal, 150R, 115R)
            For i As Integer = 0 To rep.Columnas.Count - 1
                ws.Column(i + 1).Width = Math.Max(7R, Math.Round(total * rep.Columnas(i).Peso / suma, 1))
            Next
            If ultima >= primeraDato AndAlso rep.Columnas.Count > 0 Then
                ws.SheetView.FreezeRows(filaEnc)
            End If
            r += 1
            For Each nota As String In rep.Notas
                ws.Cell(r, 1).Value = nota
                ws.Cell(r, 1).Style.Font.Italic = True
                ws.Cell(r, 1).Style.Font.FontSize = 9
                r += 1
            Next
            ' impresión
            ws.PageSetup.PaperSize = XLPaperSize.LetterPaper
            ws.PageSetup.PageOrientation = If(rep.Horizontal, XLPageOrientation.Landscape, XLPageOrientation.Portrait)
            ws.PageSetup.PagesWide = 1
            ws.PageSetup.PagesTall = 0
            ws.PageSetup.Margins.Left = 0.5
            ws.PageSetup.Margins.Right = 0.5
            ws.PageSetup.SetRowsToRepeatAtTop(filaEnc, filaEnc)
            ws.PageSetup.Footer.Left.AddText("ContaBol")
            ws.PageSetup.Footer.Right.AddText("Página &P de &N")
            wb.Properties.Title = rep.Titulo
            wb.Properties.Author = "ContaBol"
            Return wb
        End Function

    End Module

End Namespace
