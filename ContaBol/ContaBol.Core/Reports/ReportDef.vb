Imports System.Globalization

Namespace Reports

    Public Enum Formato
        Texto
        Entero
        Monto
        Cantidad
        Fecha
        Porcentaje
        Precio
    End Enum

    Public Enum Alinea
        Izquierda
        Derecha
        Centro
    End Enum

    Public Enum TipoFila
        Normal
        Grupo
        Subtotal
        Total
        Titulo
        Texto
        Salto
        Vacia
    End Enum

    Public Class ColumnaRep
        Public Property Titulo As String
        ''' <summary>Peso relativo del ancho de la columna.</summary>
        Public Property Peso As Double = 1R
        Public Property Formato As Formato = Formato.Texto
        Public Property Alineacion As Alinea = Alinea.Izquierda
    End Class

    Public Class FilaRep
        Public Property Tipo As TipoFila = TipoFila.Normal
        Public Property Celdas As New List(Of Object)
        ''' <summary>Sangría (niveles) para jerarquías de cuentas.</summary>
        Public Property Nivel As Integer
        Public Property Negrita As Boolean
    End Class

    ''' <summary>Definición neutral de un reporte tabular. Un mismo reporte se exporta a PDF, Excel y pantalla.</summary>
    Public Class ReporteDef
        Public Property Titulo As String = ""
        Public Property Subtitulo As String = ""
        Public Property Periodo As String = ""
        Public Property Moneda As String = ""
        Public Property Empresa As String = ""
        Public Property Nit As String = ""
        Public Property Direccion As String = ""
        Public Property Gestion As String = ""
        Public Property Usuario As String = ""
        Public Property Horizontal As Boolean
        Public Property Hoja As String = "Reporte"
        Public Property NombreArchivo As String = "Reporte"
        Public ReadOnly Property Columnas As New List(Of ColumnaRep)
        Public ReadOnly Property Filas As New List(Of FilaRep)
        ''' <summary>Pares etiqueta/valor que se muestran en un recuadro antes de la tabla (datos del documento).</summary>
        Public ReadOnly Property Cabecera As New List(Of KeyValuePair(Of String, String))
        Public ReadOnly Property Notas As New List(Of String)
        ''' <summary>Cuadros de firma al pie (ej. Elaborado, Revisado, Aprobado).</summary>
        Public ReadOnly Property Firmas As New List(Of String)

        Public Function Col(titulo As String, peso As Double, Optional formato As Formato = Formato.Texto, Optional alin As Alinea? = Nothing) As ReporteDef
            Dim a As Alinea = If(alin.HasValue, alin.Value, If(formato = Formato.Texto, Alinea.Izquierda, If(formato = Formato.Fecha, Alinea.Centro, Alinea.Derecha)))
            Columnas.Add(New ColumnaRep With {.Titulo = titulo, .Peso = peso, .Formato = formato, .Alineacion = a})
            Return Me
        End Function

        Public Function Fila(ParamArray celdas() As Object) As FilaRep
            Dim f As New FilaRep()
            f.Celdas.AddRange(celdas)
            Filas.Add(f)
            Return f
        End Function

        Public Function Grupo(texto As String) As FilaRep
            Dim f As New FilaRep With {.Tipo = TipoFila.Grupo}
            f.Celdas.Add(texto)
            Filas.Add(f)
            Return f
        End Function

        Public Function Subtotal(ParamArray celdas() As Object) As FilaRep
            Dim f As New FilaRep With {.Tipo = TipoFila.Subtotal}
            f.Celdas.AddRange(celdas)
            Filas.Add(f)
            Return f
        End Function

        Public Function Total(ParamArray celdas() As Object) As FilaRep
            Dim f As New FilaRep With {.Tipo = TipoFila.Total}
            f.Celdas.AddRange(celdas)
            Filas.Add(f)
            Return f
        End Function

        Public Function Texto(t As String) As FilaRep
            Dim f As New FilaRep With {.Tipo = TipoFila.Texto}
            f.Celdas.Add(t)
            Filas.Add(f)
            Return f
        End Function

        Public Sub Salto()
            Filas.Add(New FilaRep With {.Tipo = TipoFila.Salto})
        End Sub

        Public Sub Vacia()
            Filas.Add(New FilaRep With {.Tipo = TipoFila.Vacia})
        End Sub

        Public ReadOnly Property NumeroFilasDatos As Integer
            Get
                Return Filas.Where(Function(f) f.Tipo = TipoFila.Normal).Count()
            End Get
        End Property
    End Class

    ''' <summary>Formateo de valores para pantalla y PDF (usa la cultura del equipo, ej. 1.234,56 en es-BO).</summary>
    Public Module FormatoVal
        Public Property Cultura As CultureInfo = CultureInfo.CurrentCulture

        Public Function Texto(v As Object, f As Formato) As String
            If v Is Nothing OrElse v Is DBNull.Value Then Return ""
            Select Case f
                Case Formato.Monto
                    If TypeOf v Is String Then Return CStr(v)
                    Dim d As Decimal = Convert.ToDecimal(v)
                    Return d.ToString("#,##0.00;-#,##0.00;0.00", Cultura)
                Case Formato.Cantidad
                    If TypeOf v Is String Then Return CStr(v)
                    Return Convert.ToDecimal(v).ToString("#,##0.####", Cultura)
                Case Formato.Precio
                    If TypeOf v Is String Then Return CStr(v)
                    Return Convert.ToDecimal(v).ToString("#,##0.0000", Cultura)
                Case Formato.Entero
                    If TypeOf v Is String Then Return CStr(v)
                    Return Convert.ToInt64(v).ToString("#,##0", Cultura)
                Case Formato.Porcentaje
                    If TypeOf v Is String Then Return CStr(v)
                    Return Convert.ToDecimal(v).ToString("0.00", Cultura) & "%"
                Case Formato.Fecha
                    If TypeOf v Is Date Then
                        Dim d As Date = CDate(v)
                        If d = Date.MinValue Then Return ""
                        Return d.ToString("dd/MM/yyyy", CultureInfo.InvariantCulture)
                    End If
                    Return Convert.ToString(v, CultureInfo.InvariantCulture)
                Case Else
                    Return Convert.ToString(v, CultureInfo.InvariantCulture)
            End Select
        End Function
    End Module

End Namespace
