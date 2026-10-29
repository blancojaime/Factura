Imports System.Text

Namespace Data

    ''' <summary>Genera y ejecuta el DDL de un esquema declarativo para el proveedor indicado.</summary>
    Public Class SchemaInstaller

        Public Shared Function CreateTableSql(p As IDbProvider, t As TableDef, withFk As Boolean) As String
            Dim sb As New StringBuilder()
            sb.Append("CREATE TABLE ").Append(p.Quote(t.Name)).Append(" (").AppendLine()
            sb.Append("  ").Append(p.IdColumnSql)
            For Each c As ColumnDef In t.Columns
                sb.Append(",").AppendLine().Append("  ").Append(p.ColumnSql(c))
            Next
            If withFk Then
                Dim k As Integer = 0
                For Each fk As ForeignKeyDef In t.ForeignKeys
                    k += 1
                    sb.Append(",").AppendLine().Append("  CONSTRAINT ").Append(p.Quote("fk_" & t.Name & "_" & fk.Column)).
                        Append(" FOREIGN KEY (").Append(p.Quote(fk.Column)).Append(") REFERENCES ").
                        Append(p.Quote(fk.RefTable)).Append(" (").Append(p.Quote("Id")).Append(")")
                Next
            End If
            sb.AppendLine().Append(")")
            Return sb.ToString()
        End Function

        Public Shared Function CreateIndexSql(p As IDbProvider, t As TableDef, ix As IndexDef) As String
            Dim cols As New List(Of String)
            For Each c As String In ix.Columns
                cols.Add(p.Quote(c))
            Next
            Return "CREATE " & If(ix.Unique, "UNIQUE ", "") & "INDEX " & p.Quote(ix.Name) & " ON " & p.Quote(t.Name) & " (" & String.Join(", ", cols) & ")"
        End Function

        ''' <summary>Crea todas las tablas e índices. Si una restricción de clave foránea no es aceptada se reintenta sin ella.</summary>
        Public Shared Sub Install(db As Database, schema As SchemaDef, Optional log As Action(Of String) = Nothing)
            Dim p As IDbProvider = db.Provider
            For Each t As TableDef In schema.Tables
                Try
                    db.Execute(CreateTableSql(p, t, True))
                Catch ex As Exception
                    If t.ForeignKeys.Count = 0 Then Throw
                    If log IsNot Nothing Then log("Tabla " & t.Name & ": reintento sin claves foráneas (" & ex.Message & ")")
                    db.Execute(CreateTableSql(p, t, False))
                End Try
                For Each ix As IndexDef In t.Indexes
                    db.Execute(CreateIndexSql(p, t, ix))
                Next
            Next
        End Sub

    End Class

End Namespace
