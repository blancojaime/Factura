' Archivo temporal de marcadores: se elimina cuando existan las pantallas reales.
Public Class DocumentoForm
    Inherits FormBase
    Public Sub New(esVenta As Boolean)
    End Sub
End Class
Public Class CobroPagoForm
    Inherits FormBase
End Class
Public Class BackupForm
    Inherits FormBase
    Public Shared Sub Mostrar()
    End Sub
End Class
Public Class CentroReportesForm
    Inherits FormBase
End Class
Public Module MenuPrincipal
    Public Sub Construir(f As MainForm)
    End Sub
End Module
