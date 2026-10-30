Imports System.Data.Common
Imports System.Data.OleDb
Imports System.IO
Imports System.Text

Namespace Data

    ''' <summary>
    ''' Proveedor Microsoft Access (.accdb) mediante OleDb / ACE. Requiere el "Microsoft Access Database Engine"
    ''' (redistribuible gratuito) con la misma arquitectura (x86/x64) que la aplicación.
    ''' </summary>
    Public Class AccessProvider
        Implements IDbProvider

        Private Shared _providerName As String = Nothing
        Private Shared ReadOnly Candidatos As String() = {"Microsoft.ACE.OLEDB.16.0", "Microsoft.ACE.OLEDB.12.0"}

        Public ReadOnly Property Nombre As String Implements IDbProvider.Nombre
            Get
                Return "Microsoft Access (ACE OLEDB)"
            End Get
        End Property

        Public ReadOnly Property Extension As String Implements IDbProvider.Extension
            Get
                Return ".accdb"
            End Get
        End Property

        Public ReadOnly Property TipadoNativo As Boolean Implements IDbProvider.TipadoNativo
            Get
                Return True
            End Get
        End Property

        Public ReadOnly Property IdColumnSql As String Implements IDbProvider.IdColumnSql
            Get
                Return "[Id] COUNTER PRIMARY KEY"
            End Get
        End Property

        Public ReadOnly Property LastIdSql As String Implements IDbProvider.LastIdSql
            Get
                Return "SELECT @@IDENTITY"
            End Get
        End Property

        Public Function Quote(ident As String) As String Implements IDbProvider.Quote
            Return "[" & ident & "]"
        End Function

        Private Shared Function ConnString(prov As String, path As String) As String
            Return "Provider=" & prov & ";Data Source=" & path & ";Persist Security Info=False;"
        End Function

        ''' <summary>Detecta qué versión del motor ACE está instalada.</summary>
        Public Shared Function DetectProvider() As String
            If _providerName IsNot Nothing Then Return _providerName
            For Each p As String In Candidatos
                Try
                    Dim t As Type = Type.GetTypeFromProgID(p)
                    If t IsNot Nothing Then
                        _providerName = p
                        Return p
                    End If
                Catch
                End Try
            Next
            Throw New InvalidOperationException(
                "No se encontró el motor de base de datos de Microsoft Access (ACE OLEDB)." & vbCrLf &
                "Instale 'Microsoft Access Database Engine 2016 Redistributable' (gratuito) con la misma arquitectura " &
                "(x64 o x86) que ContaBol y vuelva a abrir la aplicación.")
        End Function

        Public Function OpenConnection(path As String) As DbConnection Implements IDbProvider.OpenConnection
            Dim cn As New OleDbConnection(ConnString(DetectProvider(), path))
            cn.Open()
            Return cn
        End Function

        Public Sub CreateFile(path As String) Implements IDbProvider.CreateFile
            If File.Exists(path) Then Throw New IOException("El archivo ya existe: " & path)
            Dim dir As String = System.IO.Path.GetDirectoryName(path)
            If Not String.IsNullOrEmpty(dir) Then Directory.CreateDirectory(dir)
            Dim cat As Object = Nothing
            Try
                Dim t As Type = Type.GetTypeFromProgID("ADOX.Catalog")
                If t Is Nothing Then Throw New InvalidOperationException("Componente ADOX no disponible en este equipo.")
                cat = Activator.CreateInstance(t)
                Dim d As Object = cat
                Try
                    Dim conn As Object = CallByName(d, "Create", CallType.Method, ConnString(DetectProvider(), path))
                    If conn IsNot Nothing Then
                        Try
                            CallByName(conn, "Close", CallType.Method)
                            System.Runtime.InteropServices.Marshal.ReleaseComObject(conn)
                        Catch
                        End Try
                    End If
                Catch ex As Exception
                    Throw New InvalidOperationException("No se pudo crear el archivo de base de datos " & path & ": " & ex.Message, ex)
                End Try
            Finally
                If cat IsNot Nothing Then
                    Try
                        System.Runtime.InteropServices.Marshal.ReleaseComObject(cat)
                    Catch
                    End Try
                End If
            End Try
        End Sub

        Public Function ColumnSql(c As ColumnDef) As String Implements IDbProvider.ColumnSql
            Dim t As String
            Select Case c.Type
                Case ColType.Text : t = "TEXT(" & Math.Max(1, Math.Min(255, c.Length)) & ")"
                Case ColType.Memo : t = "MEMO"
                Case ColType.Int : t = "LONG"
                Case ColType.Flag : t = "LONG"
                Case ColType.Money : t = "CURRENCY"
                Case ColType.Dbl : t = "DOUBLE"
                Case ColType.Date : t = "DATETIME"
                Case Else : t = "TEXT(255)"
            End Select
            Return Quote(c.Name) & " " & t & If(c.Required, " NOT NULL", "")
        End Function

        ''' <summary>Convierte parámetros nombrados (@nombre) al formato posicional (?) de OleDb.</summary>
        Public Function PrepareCommand(cn As DbConnection, tx As DbTransaction, sql As String, args As Object()) As DbCommand Implements IDbProvider.PrepareCommand
            Dim values As Dictionary(Of String, Object) = ParamMap(args)
            Dim cmd As New OleDbCommand()
            cmd.Connection = CType(cn, OleDbConnection)
            If tx IsNot Nothing Then cmd.Transaction = CType(tx, OleDbTransaction)
            Dim sb As New StringBuilder(sql.Length)
            Dim i As Integer = 0
            Dim inStr As Boolean = False
            While i < sql.Length
                Dim ch As Char = sql(i)
                If ch = "'"c Then
                    inStr = Not inStr
                    sb.Append(ch)
                    i += 1
                ElseIf ch = "@"c AndAlso Not inStr AndAlso i + 1 < sql.Length AndAlso (Char.IsLetter(sql(i + 1)) OrElse sql(i + 1) = "_"c) Then
                    Dim j As Integer = i + 1
                    While j < sql.Length AndAlso (Char.IsLetterOrDigit(sql(j)) OrElse sql(j) = "_"c)
                        j += 1
                    End While
                    Dim nm As String = sql.Substring(i + 1, j - i - 1)
                    Dim v As Object = Nothing
                    If Not values.TryGetValue(nm.ToLowerInvariant(), v) Then
                        Throw New ArgumentException("Falta el valor del parámetro @" & nm & " en la consulta: " & sql)
                    End If
                    cmd.Parameters.Add(MakeParam(v))
                    sb.Append("?"c)
                    i = j
                Else
                    sb.Append(ch)
                    i += 1
                End If
            End While
            cmd.CommandText = sb.ToString()
            Return cmd
        End Function

        Friend Shared Function ParamMap(args As Object()) As Dictionary(Of String, Object)
            Dim d As New Dictionary(Of String, Object)
            If args Is Nothing OrElse args.Length = 0 Then Return d
            If args.Length Mod 2 <> 0 Then Throw New ArgumentException("Los parámetros deben pasarse en pares nombre/valor.")
            For k As Integer = 0 To args.Length - 1 Step 2
                d(CStr(args(k)).TrimStart("@"c).ToLowerInvariant()) = args(k + 1)
            Next
            Return d
        End Function

        Private Shared Function MakeParam(v As Object) As OleDbParameter
            Dim p As New OleDbParameter()
            If v Is Nothing OrElse v Is DBNull.Value Then
                p.OleDbType = OleDbType.VarWChar
                p.Value = DBNull.Value
                Return p
            End If
            Select Case True
                Case TypeOf v Is String
                    Dim s As String = CStr(v)
                    If s.Length = 0 Then
                        p.OleDbType = OleDbType.VarWChar
                        p.Value = DBNull.Value
                    ElseIf s.Length > 255 Then
                        p.OleDbType = OleDbType.LongVarWChar
                        p.Value = s
                    Else
                        p.OleDbType = OleDbType.VarWChar
                        p.Size = s.Length
                        p.Value = s
                    End If
                Case TypeOf v Is Date
                    p.OleDbType = OleDbType.Date
                    Dim d As Date = CDate(v)
                    p.Value = New Date(d.Year, d.Month, d.Day, d.Hour, d.Minute, d.Second)
                Case TypeOf v Is Decimal
                    p.OleDbType = OleDbType.Currency
                    p.Value = v
                Case TypeOf v Is Double OrElse TypeOf v Is Single
                    p.OleDbType = OleDbType.Double
                    p.Value = Convert.ToDouble(v)
                Case TypeOf v Is Boolean
                    p.OleDbType = OleDbType.Integer
                    p.Value = If(CBool(v), 1, 0)
                Case TypeOf v Is Long
                    Dim l As Long = CLng(v)
                    If l >= Integer.MinValue AndAlso l <= Integer.MaxValue Then
                        p.OleDbType = OleDbType.Integer
                        p.Value = CInt(l)
                    Else
                        p.OleDbType = OleDbType.Double
                        p.Value = CDbl(l)
                    End If
                Case Else
                    p.OleDbType = OleDbType.Integer
                    p.Value = Convert.ToInt32(v)
            End Select
            Return p
        End Function

        Public Sub ReleasePools() Implements IDbProvider.ReleasePools
            OleDbConnection.ReleaseObjectPool()
            GC.Collect()
            GC.WaitForPendingFinalizers()
        End Sub

        Public Sub Compact(path As String) Implements IDbProvider.Compact
            ReleasePools()
            Dim tmp As String = path & ".compact.tmp"
            If File.Exists(tmp) Then File.Delete(tmp)
            Dim jro As Object = Nothing
            Try
                Dim t As Type = Type.GetTypeFromProgID("JRO.JetEngine")
                If t Is Nothing Then Throw New InvalidOperationException("Componente JRO no disponible para compactar la base de datos.")
                jro = Activator.CreateInstance(t)
                CallByName(jro, "CompactDatabase", CallType.Method, ConnString(DetectProvider(), path), ConnString(DetectProvider(), tmp) & "Jet OLEDB:Engine Type=6;")
            Finally
                If jro IsNot Nothing Then
                    Try
                        System.Runtime.InteropServices.Marshal.ReleaseComObject(jro)
                    Catch
                    End Try
                End If
            End Try
            File.Delete(path)
            File.Move(tmp, path)
        End Sub

    End Class

End Namespace
