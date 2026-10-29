Imports System.IO
Imports ClosedXML.Excel
Imports ContaBol.Core.Reports
Imports Xunit

Public Class ReportEngineTests

    Public Shared Function Muestra() As ReporteDef
        Dim r As New ReporteDef With {.Titulo = "Balance de Sumas y Saldos", .Periodo = "Del 01/01/2025 al 31/12/2025", .Moneda = "(Expresado en Bolivianos)", .Empresa = "Comercial Prueba S.R.L.",
            .Nit = "1020304050", .Direccion = "Av. Camacho 123 - La Paz", .Gestion = "2025", .Usuario = "admin"}
        r.Col("Código", 2.2).Col("Cuenta", 6).Col("Debe", 2, Formato.Monto).Col("Haber", 2, Formato.Monto).Col("Saldo Deudor", 2, Formato.Monto).Col("Saldo Acreedor", 2, Formato.Monto)
        r.Grupo("ACTIVO")
        r.Fila("1", "ACTIVO", 12500.5D, 3000D, 9500.5D, 0D).Negrita = True
        Dim f = r.Fila("1.1.1.01.001", "Caja Moneda Nacional con un nombre bastante largo para probar el ajuste de línea dentro de la celda", 12500.5D, 3000D, 9500.5D, 0D)
        f.Nivel = 2
        r.Subtotal("", "Subtotal activo", 12500.5D, 3000D, 9500.5D, 0D)
        For i = 1 To 60
            r.Fila("5.3.1.02." & i.ToString("000"), "Gasto de ejemplo número " & i, i * 10D, 0D, i * 10D, 0D)
        Next
        r.Total("", "TOTALES", 99999.99D, 99999.99D, 50000D, 50000D)
        r.Firmas.AddRange({"Elaborado por", "Revisado por", "Aprobado por"})
        r.Notas.Add("Este reporte fue generado por ContaBol.")
        Return r
    End Function

    <Fact>
    Public Sub GeneraPdfValido()
        Dim bytes = PdfExporter.GenerarBytes(Muestra())
        Assert.True(bytes.Length > 2000)
        Assert.Equal("%PDF", Text.Encoding.ASCII.GetString(bytes, 0, 4))
        Dim ruta = Path.Combine(Path.GetTempPath(), "contabol_muestra.pdf")
        File.WriteAllBytes(ruta, bytes)
    End Sub

    <Fact>
    Public Sub GeneraPdfHorizontalYExcel()
        Dim r = Muestra()
        r.Horizontal = True
        Dim bytes = PdfExporter.GenerarBytes(r)
        File.WriteAllBytes(Path.Combine(Path.GetTempPath(), "contabol_muestra_h.pdf"), bytes)
        Dim xl = Path.Combine(Path.GetTempPath(), "contabol_muestra.xlsx")
        ExcelExporter.Exportar(r, xl)
        Using wb As New XLWorkbook(xl)
            Dim ws = wb.Worksheet(1)
            Assert.Equal("Comercial Prueba S.R.L.", ws.Cell(1, 1).GetString())
            ' fila de encabezado de la tabla
            Dim fila = ws.RowsUsed().First(Function(x) x.Cell(1).GetString() = "Código").RowNumber()
            Assert.Equal("Haber", ws.Cell(fila, 4).GetString())
            ' los importes son numéricos, no texto
            Dim caja = ws.RowsUsed().First(Function(x) x.Cell(1).GetString() = "1.1.1.01.001")
            Assert.Equal(12500.5R, caja.Cell(3).GetDouble())
        End Using
    End Sub
End Class
