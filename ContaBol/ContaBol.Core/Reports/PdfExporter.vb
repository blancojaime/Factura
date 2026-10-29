Imports System.IO
Imports System.Runtime.InteropServices
Imports MigraDoc.DocumentObjectModel
Imports MigraDoc.DocumentObjectModel.Tables
Imports MigraDoc.Rendering
Imports PdfSharp.Fonts
Imports PdfSharp.Pdf

Namespace Reports

    ''' <summary>PDFsharp necesita un resolvedor de fuentes: usa Arial en Windows y Liberation Sans/DejaVu en Linux.</summary>
    Friend Class ResolvedorFuentes
        Implements IFontResolver

        Private Shared ReadOnly Rutas As String() = ConstruirRutas()

        Private Shared Function ConstruirRutas() As String()
            Dim l As New List(Of String)
            Try
                Dim f As String = Environment.GetFolderPath(Environment.SpecialFolder.Fonts)
                If Not String.IsNullOrEmpty(f) Then l.Add(f & Path.DirectorySeparatorChar)
            Catch
            End Try
            l.AddRange({"/usr/share/fonts/truetype/liberation/", "/usr/share/fonts/liberation/", "/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/", "/System/Library/Fonts/Supplemental/"})
            Return l.ToArray()
        End Function

        Private Shared Function Buscar(ParamArray nombres() As String) As String
            For Each r As String In Rutas
                For Each n As String In nombres
                    If File.Exists(r & n) Then Return r & n
                Next
            Next
            Return Nothing
        End Function

        Public Function ResolveTypeface(familyName As String, bold As Boolean, italic As Boolean) As FontResolverInfo Implements IFontResolver.ResolveTypeface
            Dim clave As String = "sans" & If(bold, "-b", "") & If(italic, "-i", "")
            Return New FontResolverInfo(clave)
        End Function

        Public Function GetFont(faceName As String) As Byte() Implements IFontResolver.GetFont
            Dim ruta As String
            Select Case faceName
                Case "sans-b-i" : ruta = Buscar("arialbi.ttf", "LiberationSans-BoldItalic.ttf", "DejaVuSans-BoldOblique.ttf", "Arial Bold Italic.ttf")
                Case "sans-b" : ruta = Buscar("arialbd.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf")
                Case "sans-i" : ruta = Buscar("ariali.ttf", "LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf", "Arial Italic.ttf")
                Case Else : ruta = Buscar("arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf", "Arial.ttf")
            End Select
            If ruta Is Nothing Then Throw New FileNotFoundException("No se encontró ninguna fuente para generar PDF en este sistema.")
            Return File.ReadAllBytes(ruta)
        End Function
    End Class

    ''' <summary>Genera PDF profesionales (membrete, encabezado repetido, paginación, firmas) con PDFsharp/MigraDoc.</summary>
    Public Module PdfExporter

        Private _fuentesListas As Boolean

        Private Sub PrepararFuentes()
            If _fuentesListas Then Return
            GlobalFontSettings.FontResolver = New ResolvedorFuentes()
            _fuentesListas = True
        End Sub

        Private ReadOnly Azul As Color = Color.FromRgb(31, 58, 95)
        Private ReadOnly AzulClaro As Color = Color.FromRgb(222, 231, 243)
        Private ReadOnly Gris As Color = Color.FromRgb(242, 244, 247)
        Private ReadOnly LineaGris As Color = Color.FromRgb(200, 205, 212)

        Private Function Alinear(a As Alinea) As ParagraphAlignment
            Select Case a
                Case Alinea.Derecha : Return ParagraphAlignment.Right
                Case Alinea.Centro : Return ParagraphAlignment.Center
                Case Else : Return ParagraphAlignment.Left
            End Select
        End Function

        Public Sub Exportar(rep As ReporteDef, ruta As String)
            Dim bytes As Byte() = GenerarBytes(rep)
            Dim dir As String = Path.GetDirectoryName(ruta)
            If Not String.IsNullOrEmpty(dir) Then Directory.CreateDirectory(dir)
            File.WriteAllBytes(ruta, bytes)
        End Sub

        Public Function GenerarBytes(rep As ReporteDef) As Byte()
            PrepararFuentes()
            Dim doc As New Document()
            doc.Info.Title = rep.Titulo
            doc.Info.Author = "ContaBol"
            doc.Info.Subject = rep.Empresa
            Dim normal As Style = doc.Styles("Normal")
            normal.Font.Name = "Arial"
            normal.Font.Size = 8
            Dim sec As Section = doc.AddSection()
            sec.PageSetup.PageFormat = PageFormat.Letter
            sec.PageSetup.Orientation = If(rep.Horizontal, Orientation.Landscape, Orientation.Portrait)
            sec.PageSetup.LeftMargin = Unit.FromCentimeter(1.5)
            sec.PageSetup.RightMargin = Unit.FromCentimeter(1.5)
            sec.PageSetup.TopMargin = Unit.FromCentimeter(3.9)
            sec.PageSetup.BottomMargin = Unit.FromCentimeter(1.8)
            sec.PageSetup.HeaderDistance = Unit.FromCentimeter(0.8)
            sec.PageSetup.FooterDistance = Unit.FromCentimeter(0.8)
            Dim ancho As Double = If(rep.Horizontal, 27.94, 21.59) - 3.0
            ConstruirEncabezado(sec, rep, ancho)
            ConstruirPie(sec, rep, ancho)
            ConstruirCabeceraDocumento(sec, rep, ancho)
            ConstruirTablas(sec, rep, ancho)
            For Each n As String In rep.Notas
                Dim p As Paragraph = sec.AddParagraph(n)
                p.Format.Font.Size = 7.5
                p.Format.Font.Italic = True
                p.Format.SpaceBefore = Unit.FromPoint(4)
            Next
            ConstruirFirmas(sec, rep, ancho)
            Dim r As New PdfDocumentRenderer() With {.Document = doc}
            r.RenderDocument()
            Using ms As New MemoryStream()
                r.PdfDocument.Save(ms, False)
                Return ms.ToArray()
            End Using
        End Function

        Private Sub ConstruirEncabezado(sec As Section, rep As ReporteDef, ancho As Double)
            Dim h As HeaderFooter = sec.Headers.Primary
            Dim t As Table = h.AddTable()
            t.Borders.Visible = False
            t.AddColumn(Unit.FromCentimeter(ancho * 0.62))
            t.AddColumn(Unit.FromCentimeter(ancho * 0.38))
            Dim r As Row = t.AddRow()
            Dim p As Paragraph = r.Cells(0).AddParagraph(rep.Empresa)
            p.Format.Font.Bold = True
            p.Format.Font.Size = 11
            p.Format.Font.Color = Azul
            If rep.Nit <> "" Then
                Dim p2 As Paragraph = r.Cells(0).AddParagraph("NIT: " & rep.Nit)
                p2.Format.Font.Size = 8
            End If
            If rep.Direccion <> "" Then
                Dim p3 As Paragraph = r.Cells(0).AddParagraph(rep.Direccion)
                p3.Format.Font.Size = 7.5
                p3.Format.Font.Color = Color.FromRgb(90, 90, 90)
            End If
            Dim q As Paragraph = r.Cells(1).AddParagraph(If(rep.Gestion <> "", "Gestión " & rep.Gestion, ""))
            q.Format.Alignment = ParagraphAlignment.Right
            q.Format.Font.Size = 8
            q.Format.Font.Bold = True
            Dim q2 As Paragraph = r.Cells(1).AddParagraph("Emitido: " & Date.Now.ToString("dd/MM/yyyy HH:mm"))
            q2.Format.Alignment = ParagraphAlignment.Right
            q2.Format.Font.Size = 7.5
            q2.Format.Font.Color = Color.FromRgb(90, 90, 90)
            Dim ttl As Paragraph = h.AddParagraph(rep.Titulo.ToUpperInvariant())
            ttl.Format.Alignment = ParagraphAlignment.Center
            ttl.Format.Font.Size = 13
            ttl.Format.Font.Bold = True
            ttl.Format.SpaceBefore = Unit.FromPoint(6)
            ttl.Format.Font.Color = Azul
            Dim sub1 As String = String.Join("  ·  ", {rep.Subtitulo, rep.Periodo}.Where(Function(s) s <> ""))
            If sub1 <> "" Then
                Dim sp As Paragraph = h.AddParagraph(sub1)
                sp.Format.Alignment = ParagraphAlignment.Center
                sp.Format.Font.Size = 9
            End If
            If rep.Moneda <> "" Then
                Dim mp As Paragraph = h.AddParagraph(rep.Moneda)
                mp.Format.Alignment = ParagraphAlignment.Center
                mp.Format.Font.Size = 7.5
                mp.Format.Font.Italic = True
                mp.Format.Font.Color = Color.FromRgb(90, 90, 90)
            End If
            Dim linea As Paragraph = h.AddParagraph()
            linea.Format.Borders.Bottom.Width = 0.75
            linea.Format.Borders.Bottom.Color = Azul
            linea.Format.Font.Size = 2
        End Sub

        Private Sub ConstruirPie(sec As Section, rep As ReporteDef, ancho As Double)
            Dim f As HeaderFooter = sec.Footers.Primary
            Dim p As Paragraph = f.AddParagraph()
            p.Format.Font.Size = 7
            p.Format.Font.Color = Color.FromRgb(90, 90, 90)
            p.Format.Borders.Top.Width = 0.25
            p.Format.Borders.Top.Color = LineaGris
            p.Format.TabStops.AddTabStop(Unit.FromCentimeter(ancho), TabAlignment.Right)
            p.AddText("ContaBol · Sistema Contable Integrado" & If(rep.Usuario <> "", " · Usuario: " & rep.Usuario, ""))
            p.AddTab()
            p.AddText("Página ")
            p.AddPageField()
            p.AddText(" de ")
            p.AddNumPagesField()
        End Sub

        Private Sub ConstruirCabeceraDocumento(sec As Section, rep As ReporteDef, ancho As Double)
            If rep.Cabecera.Count = 0 Then Return
            Dim t As Table = sec.AddTable()
            t.Borders.Visible = False
            t.Format.SpaceBefore = Unit.FromPoint(2)
            t.Shading.Color = Gris
            t.Borders.Color = LineaGris
            Dim colsPar As Integer = If(rep.Horizontal, 3, 2)
            Dim wLab As Double = ancho / colsPar * 0.3, wVal As Double = ancho / colsPar * 0.7
            For i As Integer = 1 To colsPar
                t.AddColumn(Unit.FromCentimeter(wLab))
                t.AddColumn(Unit.FromCentimeter(wVal))
            Next
            Dim idx As Integer = 0
            Dim row As Row = Nothing
            For Each kv In rep.Cabecera
                If idx Mod colsPar = 0 Then
                    row = t.AddRow()
                    row.TopPadding = 2
                    row.BottomPadding = 2
                End If
                Dim c As Integer = (idx Mod colsPar) * 2
                Dim l As Paragraph = row.Cells(c).AddParagraph(kv.Key)
                l.Format.Font.Bold = True
                l.Format.Font.Size = 8
                Dim v As Paragraph = row.Cells(c + 1).AddParagraph(kv.Value)
                v.Format.Font.Size = 8
                idx += 1
            Next
            sec.AddParagraph().Format.SpaceAfter = Unit.FromPoint(2)
        End Sub

        Private Sub ConstruirTablas(sec As Section, rep As ReporteDef, ancho As Double)
            If rep.Columnas.Count = 0 Then Return
            Dim suma As Double = rep.Columnas.Sum(Function(c) c.Peso)
            Dim tamano As Double = If(rep.Columnas.Count > 10, 6.5, If(rep.Columnas.Count > 7, 7, 7.5))
            Dim tabla As Table = Nothing
            Dim crear = Sub()
                            tabla = sec.AddTable()
                            tabla.Borders.Visible = False
                            tabla.Format.Font.Size = tamano
                            tabla.Rows.LeftIndent = 0
                            For Each c As ColumnaRep In rep.Columnas
                                tabla.AddColumn(Unit.FromCentimeter(ancho * c.Peso / suma))
                            Next
                            Dim hr As Row = tabla.AddRow()
                            hr.HeadingFormat = True
                            hr.Shading.Color = Azul
                            hr.Format.Font.Color = Colors.White
                            hr.Format.Font.Bold = True
                            hr.TopPadding = 3
                            hr.BottomPadding = 3
                            hr.VerticalAlignment = VerticalAlignment.Center
                            For i As Integer = 0 To rep.Columnas.Count - 1
                                Dim p As Paragraph = hr.Cells(i).AddParagraph(rep.Columnas(i).Titulo)
                                p.Format.Alignment = If(rep.Columnas(i).Alineacion = Alinea.Izquierda, ParagraphAlignment.Left, ParagraphAlignment.Center)
                            Next
                        End Sub
            crear()
            Dim n As Integer = rep.Columnas.Count
            Dim zebra As Boolean = False
            For Each f As FilaRep In rep.Filas
                Select Case f.Tipo
                    Case TipoFila.Salto
                        sec.AddPageBreak()
                        crear()
                        zebra = False
                        Continue For
                    Case TipoFila.Vacia
                        Dim vr As Row = tabla.AddRow()
                        vr.Height = Unit.FromPoint(5)
                        vr.Cells(0).MergeRight = n - 1
                        Continue For
                End Select
                Dim r As Row = tabla.AddRow()
                r.TopPadding = 1.6
                r.BottomPadding = 1.6
                r.VerticalAlignment = VerticalAlignment.Center
                Select Case f.Tipo
                    Case TipoFila.Grupo, TipoFila.Titulo
                        r.Shading.Color = AzulClaro
                        r.Format.Font.Bold = True
                        r.Cells(0).MergeRight = n - 1
                        Dim p As Paragraph = r.Cells(0).AddParagraph(If(f.Celdas.Count > 0, Convert.ToString(f.Celdas(0)), ""))
                        p.Format.LeftIndent = Unit.FromPoint(f.Nivel * 8)
                        zebra = False
                        Continue For
                    Case TipoFila.Texto
                        r.Cells(0).MergeRight = n - 1
                        r.Cells(0).AddParagraph(If(f.Celdas.Count > 0, Convert.ToString(f.Celdas(0)), ""))
                        If f.Negrita Then r.Format.Font.Bold = True
                        Continue For
                    Case TipoFila.Subtotal
                        r.Format.Font.Bold = True
                        r.Borders.Top.Width = 0.5
                        r.Borders.Top.Color = Azul
                    Case TipoFila.Total
                        r.Format.Font.Bold = True
                        r.Shading.Color = AzulClaro
                        r.Borders.Top.Width = 0.75
                        r.Borders.Top.Color = Azul
                        r.Borders.Bottom.Width = 1.25
                        r.Borders.Bottom.Color = Azul
                    Case Else
                        If f.Negrita Then r.Format.Font.Bold = True
                        r.Borders.Bottom.Width = 0.25
                        r.Borders.Bottom.Color = LineaGris
                        If zebra Then r.Shading.Color = Gris
                        zebra = Not zebra
                End Select
                For i As Integer = 0 To n - 1
                    Dim v As Object = If(i < f.Celdas.Count, f.Celdas(i), Nothing)
                    Dim txt As String = FormatoVal.Texto(v, rep.Columnas(i).Formato)
                    Dim p As Paragraph = r.Cells(i).AddParagraph(txt)
                    p.Format.Alignment = Alinear(rep.Columnas(i).Alineacion)
                    If i = 0 AndAlso f.Nivel > 0 Then p.Format.LeftIndent = Unit.FromPoint(f.Nivel * 8)
                Next
            Next
        End Sub

        Private Sub ConstruirFirmas(sec As Section, rep As ReporteDef, ancho As Double)
            If rep.Firmas.Count = 0 Then Return
            Dim esp As Paragraph = sec.AddParagraph()
            esp.Format.SpaceBefore = Unit.FromCentimeter(1.6)
            Dim t As Table = sec.AddTable()
            t.Borders.Visible = False
            Dim n As Integer = rep.Firmas.Count
            Dim w As Double = ancho / n
            For i As Integer = 1 To n
                t.AddColumn(Unit.FromCentimeter(w))
            Next
            Dim r As Row = t.AddRow()
            For i As Integer = 0 To n - 1
                Dim c As Cell = r.Cells(i)
                c.Format.Alignment = ParagraphAlignment.Center
                Dim linea As Paragraph = c.AddParagraph("______________________________")
                linea.Format.Font.Color = Color.FromRgb(70, 70, 70)
                Dim lab As Paragraph = c.AddParagraph(rep.Firmas(i))
                lab.Format.Font.Size = 7.5
                lab.Format.Font.Bold = True
            Next
        End Sub

    End Module

End Namespace
