Imports System.Data.Common
Imports ContaBol.Core.Common

Namespace Data

    ''' <summary>
    ''' Acceso a una base de datos (un archivo). Parámetros como pares nombre/valor: <c>db.Query("... WHERE Id=@id", "id", 5)</c>.
    ''' Soporta transacciones anidadas (la más externa confirma).
    ''' </summary>
    Public Class Database
        Implements IDisposable

        Private _cn As DbConnection
        Private _tx As DbTransaction
        Private _depth As Integer
        Private _disposed As Boolean

        Public ReadOnly Property Provider As IDbProvider
        Public ReadOnly Property Path As String

        Public Sub New(provider As IDbProvider, path As String)
            Me.Provider = provider
            Me.Path = path
            _cn = provider.OpenConnection(path)
        End Sub

        Public ReadOnly Property Connection As DbConnection
            Get
                Return _cn
            End Get
        End Property

        Public ReadOnly Property EnTransaccion As Boolean
            Get
                Return _depth > 0
            End Get
        End Property

        Private Function Cmd(sql As String, args As Object()) As DbCommand
            If _disposed Then Throw New ObjectDisposedException("Database")
            Return Provider.PrepareCommand(_cn, _tx, sql, args)
        End Function

        ''' <summary>Agrega al error del motor la consulta que lo provocó y el detalle de OLE DB, para poder diagnosticar.</summary>
        Friend Shared Function Detallar(ex As Exception, sql As String) As Exception
            Dim sb As New System.Text.StringBuilder(ex.Message)
            Dim oe As System.Data.OleDb.OleDbException = TryCast(ex, System.Data.OleDb.OleDbException)
            If oe IsNot Nothing Then
                For Each e As System.Data.OleDb.OleDbError In oe.Errors
                    sb.AppendLine().Append("  [OLE DB ").Append(e.NativeError).Append(" ").Append(e.SQLState).Append("] ").Append(e.Message)
                Next
            End If
            sb.AppendLine().Append("SQL: ").Append(If(sql.Length > 400, sql.Substring(0, 400) & "...", sql))
            Return New DataException(sb.ToString(), ex)
        End Function

        Public Function Query(sql As String, ParamArray args() As Object) As DataTable
            Try
                Return QueryInterno(sql, args)
            Catch ex As DbException
                Throw Detallar(ex, sql)
            End Try
        End Function

        Private Function QueryInterno(sql As String, args As Object()) As DataTable
            Using c As DbCommand = Cmd(sql, args)
                Using rd As DbDataReader = c.ExecuteReader()
                    Dim dt As New DataTable()
                    Dim n As Integer = rd.FieldCount
                    For i As Integer = 0 To n - 1
                        Dim col As New DataColumn(rd.GetName(i), If(Provider.TipadoNativo, rd.GetFieldType(i), GetType(Object)))
                        dt.Columns.Add(col)
                    Next
                    dt.BeginLoadData()
                    While rd.Read()
                        Dim vals(n - 1) As Object
                        rd.GetValues(vals)
                        dt.Rows.Add(vals)
                    End While
                    dt.EndLoadData()
                    Return dt
                End Using
            End Using
        End Function

        Public Function Scalar(sql As String, ParamArray args() As Object) As Object
            Try
                Using c As DbCommand = Cmd(sql, args)
                    Dim o As Object = c.ExecuteScalar()
                    If o Is Nothing OrElse o Is DBNull.Value Then Return Nothing
                    Return o
                End Using
            Catch ex As DbException
                Throw Detallar(ex, sql)
            End Try
        End Function

        Public Function ScalarDec(sql As String, ParamArray args() As Object) As Decimal
            Return ToDec(Scalar(sql, args))
        End Function

        Public Function ScalarInt(sql As String, ParamArray args() As Object) As Integer
            Return ToInt(Scalar(sql, args))
        End Function

        Public Function ScalarStr(sql As String, ParamArray args() As Object) As String
            Return ToStr(Scalar(sql, args))
        End Function

        Public Function Execute(sql As String, ParamArray args() As Object) As Integer
            Try
                Using c As DbCommand = Cmd(sql, args)
                    Return c.ExecuteNonQuery()
                End Using
            Catch ex As DbException
                Throw Detallar(ex, sql)
            End Try
        End Function

        ''' <summary>Ejecuta un INSERT y devuelve el Id autonumérico generado.</summary>
        Public Function Insert(sql As String, ParamArray args() As Object) As Integer
            Execute(sql, args)
            Using c As DbCommand = Provider.PrepareCommand(_cn, _tx, Provider.LastIdSql, Nothing)
                Return ToInt(c.ExecuteScalar())
            End Using
        End Function

        Public Sub BeginTx()
            If _depth = 0 Then _tx = _cn.BeginTransaction()
            _depth += 1
        End Sub

        Public Sub CommitTx()
            If _depth = 0 Then Return
            _depth -= 1
            If _depth = 0 Then
                _tx.Commit()
                _tx.Dispose()
                _tx = Nothing
            End If
        End Sub

        Public Sub RollbackTx()
            If _depth = 0 Then Return
            _depth = 0
            Try
                _tx.Rollback()
            Finally
                _tx.Dispose()
                _tx = Nothing
            End Try
        End Sub

        Public Sub InTx(work As Action)
            BeginTx()
            Try
                work()
            Catch
                RollbackTx()
                Throw
            End Try
            CommitTx()
        End Sub

        Public Function InTx(Of T)(work As Func(Of T)) As T
            BeginTx()
            Dim r As T
            Try
                r = work()
            Catch
                RollbackTx()
                Throw
            End Try
            CommitTx()
            Return r
        End Function

        Public Function TableExists(name As String) As Boolean
            Try
                Using c As DbCommand = Cmd("SELECT * FROM " & Provider.Quote(name) & " WHERE 1=0", Nothing)
                    Using rd As DbDataReader = c.ExecuteReader()
                    End Using
                End Using
                Return True
            Catch
                Return False
            End Try
        End Function

        Public Sub Dispose() Implements IDisposable.Dispose
            If _disposed Then Return
            _disposed = True
            Try
                If _tx IsNot Nothing Then _tx.Rollback()
            Catch
            End Try
            Try
                _cn?.Dispose()
            Catch
            End Try
        End Sub

    End Class

End Namespace
