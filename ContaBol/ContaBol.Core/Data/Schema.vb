Imports System.Text

Namespace Data

    Public Enum ColType
        Text
        Memo
        Int
        Money
        Dbl
        [Date]
        Flag
    End Enum

    Public Class ColumnDef
        Public Property Name As String
        Public Property Type As ColType
        Public Property Length As Integer
        Public Property Required As Boolean
    End Class

    Public Class IndexDef
        Public Property Name As String
        Public Property Columns As String()
        Public Property Unique As Boolean
    End Class

    Public Class ForeignKeyDef
        Public Property Column As String
        Public Property RefTable As String
    End Class

    ''' <summary>Definición declarativa de una tabla (se traduce a DDL según el proveedor de base de datos).</summary>
    Public Class TableDef
        Public ReadOnly Property Name As String
        Public ReadOnly Property Columns As New List(Of ColumnDef)
        Public ReadOnly Property Indexes As New List(Of IndexDef)
        Public ReadOnly Property ForeignKeys As New List(Of ForeignKeyDef)

        Public Sub New(name As String)
            Me.Name = name
        End Sub

        Private Function Add(n As String, t As ColType, len As Integer, req As Boolean) As TableDef
            Columns.Add(New ColumnDef With {.Name = n, .Type = t, .Length = len, .Required = req})
            Return Me
        End Function

        Public Function Txt(n As String, len As Integer, Optional req As Boolean = False) As TableDef
            Return Add(n, ColType.Text, len, req)
        End Function

        Public Function Memo(n As String) As TableDef
            Return Add(n, ColType.Memo, 0, False)
        End Function

        ''' <summary>Entero (32 bits). Si es obligatorio no admite nulos.</summary>
        Public Function Int(n As String, Optional req As Boolean = False) As TableDef
            Return Add(n, ColType.Int, 0, req)
        End Function

        ''' <summary>Importe monetario (exacto, Currency en Access).</summary>
        Public Function Mon(n As String) As TableDef
            Return Add(n, ColType.Money, 0, True)
        End Function

        ''' <summary>Número de punto flotante (cantidades, precios, tipos de cambio).</summary>
        Public Function Dbl(n As String, Optional req As Boolean = True) As TableDef
            Return Add(n, ColType.Dbl, 0, req)
        End Function

        Public Function Dt(n As String, Optional req As Boolean = False) As TableDef
            Return Add(n, ColType.Date, 0, req)
        End Function

        ''' <summary>Indicador 0/1 obligatorio.</summary>
        Public Function Flag(n As String) As TableDef
            Return Add(n, ColType.Flag, 0, True)
        End Function

        ''' <summary>Clave foránea obligatoria hacia otra tabla (Id).</summary>
        Public Function Ref(n As String, refTable As String, Optional req As Boolean = True) As TableDef
            Add(n, ColType.Int, 0, req)
            ForeignKeys.Add(New ForeignKeyDef With {.Column = n, .RefTable = refTable})
            Return Me
        End Function

        Public Function Idx(ParamArray cols() As String) As TableDef
            Indexes.Add(New IndexDef With {.Name = "ix_" & Name & "_" & String.Join("_", cols), .Columns = cols, .Unique = False})
            Return Me
        End Function

        Public Function Uniq(ParamArray cols() As String) As TableDef
            Indexes.Add(New IndexDef With {.Name = "ux_" & Name & "_" & String.Join("_", cols), .Columns = cols, .Unique = True})
            Return Me
        End Function
    End Class

    Public Class SchemaDef
        Public ReadOnly Property Tables As New List(Of TableDef)

        Public Function Table(name As String) As TableDef
            Dim t As New TableDef(name)
            Tables.Add(t)
            Return t
        End Function
    End Class

End Namespace
