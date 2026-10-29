Imports System.Data.Common

Namespace Data

    ''' <summary>Abstracción del motor de base de datos. La implementación de producción es Access (OleDb).</summary>
    Public Interface IDbProvider
        ReadOnly Property Nombre As String
        ''' <summary>Extensión del archivo de base de datos (ej. ".accdb").</summary>
        ReadOnly Property Extension As String
        ''' <summary>Si es True los DataTable conservan el tipo nativo de cada columna.</summary>
        ReadOnly Property TipadoNativo As Boolean
        Function OpenConnection(path As String) As DbConnection
        Sub CreateFile(path As String)
        Function PrepareCommand(cn As DbConnection, tx As DbTransaction, sql As String, args As Object()) As DbCommand
        Function ColumnSql(c As ColumnDef) As String
        ReadOnly Property IdColumnSql As String
        ReadOnly Property LastIdSql As String
        Function Quote(ident As String) As String
        ''' <summary>Libera conexiones agrupadas para poder copiar/reemplazar el archivo.</summary>
        Sub ReleasePools()
        ''' <summary>Compacta y repara el archivo (si el motor lo soporta).</summary>
        Sub Compact(path As String)
    End Interface

End Namespace
