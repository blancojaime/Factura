Imports System.Data.Common
Imports System.IO
Imports System.Text
Imports ContaBol.Core.Data
Imports Microsoft.Data.Sqlite

''' <summary>Proveedor SQLite usado únicamente para pruebas automatizadas en cualquier sistema operativo.
''' Imita el comportamiento relevante de Access (cadenas vacías como NULL, parámetros posicionales por nombre).</summary>
Public Class SqliteProvider
    Implements IDbProvider

    Public ReadOnly Property Nombre As String Implements IDbProvider.Nombre
        Get
            Return "SQLite (pruebas)"
        End Get
    End Property

    Public ReadOnly Property Extension As String Implements IDbProvider.Extension
        Get
            Return ".db"
        End Get
    End Property

    Public ReadOnly Property TipadoNativo As Boolean Implements IDbProvider.TipadoNativo
        Get
            Return False
        End Get
    End Property

    Public ReadOnly Property IdColumnSql As String Implements IDbProvider.IdColumnSql
        Get
            Return "[Id] INTEGER PRIMARY KEY AUTOINCREMENT"
        End Get
    End Property

    Public ReadOnly Property LastIdSql As String Implements IDbProvider.LastIdSql
        Get
            Return "SELECT last_insert_rowid()"
        End Get
    End Property

    Public Function Quote(ident As String) As String Implements IDbProvider.Quote
        Return "[" & ident & "]"
    End Function

    Public Function OpenConnection(path As String) As DbConnection Implements IDbProvider.OpenConnection
        Dim cn As New SqliteConnection("Data Source=" & path & ";Pooling=False")
        cn.Open()
        Using c As SqliteCommand = cn.CreateCommand()
            c.CommandText = "PRAGMA foreign_keys = ON"
            c.ExecuteNonQuery()
        End Using
        Return cn
    End Function

    Public Sub CreateFile(path As String) Implements IDbProvider.CreateFile
        Dim dir As String = System.IO.Path.GetDirectoryName(path)
        If Not String.IsNullOrEmpty(dir) Then Directory.CreateDirectory(dir)
        File.WriteAllBytes(path, New Byte() {})
    End Sub

    Public Function ColumnSql(c As ColumnDef) As String Implements IDbProvider.ColumnSql
        Dim t As String
        Select Case c.Type
            Case ColType.Text, ColType.Memo : t = "TEXT"
            Case ColType.Int, ColType.Flag : t = "INTEGER"
            Case ColType.Money, ColType.Dbl : t = "REAL"
            Case ColType.Date : t = "DATETIME"
            Case Else : t = "TEXT"
        End Select
        Return Quote(c.Name) & " " & t & If(c.Required, " NOT NULL", "")
    End Function

    Public Function PrepareCommand(cn As DbConnection, tx As DbTransaction, sql As String, args As Object()) As DbCommand Implements IDbProvider.PrepareCommand
        Dim cmd As SqliteCommand = CType(cn, SqliteConnection).CreateCommand()
        cmd.CommandText = sql
        If tx IsNot Nothing Then cmd.Transaction = CType(tx, SqliteTransaction)
        If args IsNot Nothing Then
            If args.Length Mod 2 <> 0 Then Throw New ArgumentException("Parámetros en pares nombre/valor")
            For i As Integer = 0 To args.Length - 1 Step 2
                Dim v As Object = args(i + 1)
                If v Is Nothing Then v = DBNull.Value
                If TypeOf v Is String AndAlso CStr(v).Length = 0 Then v = DBNull.Value
                If TypeOf v Is Decimal Then v = Convert.ToDouble(v)
                If TypeOf v Is Boolean Then v = If(CBool(v), 1, 0)
                If TypeOf v Is Date Then v = CDate(v).ToString("yyyy-MM-dd HH:mm:ss", Globalization.CultureInfo.InvariantCulture)
                cmd.Parameters.AddWithValue("@" & CStr(args(i)).TrimStart("@"c), v)
            Next
        End If
        Return cmd
    End Function

    Public Sub ReleasePools() Implements IDbProvider.ReleasePools
        SqliteConnection.ClearAllPools()
    End Sub

    Public Sub Compact(path As String) Implements IDbProvider.Compact
    End Sub
End Class
