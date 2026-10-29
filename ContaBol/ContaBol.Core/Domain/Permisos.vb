Namespace Domain

    Public Class OpcionPermiso
        Public Property Clave As String
        Public Property Titulo As String
        Public Property Grupo As String
        Public Sub New(clave As String, titulo As String, grupo As String)
            Me.Clave = clave
            Me.Titulo = titulo
            Me.Grupo = grupo
        End Sub
    End Class

    ''' <summary>Catálogo de opciones del sistema sobre las que se otorgan permisos por usuario y empresa.</summary>
    Public Module Permisos

        Public ReadOnly Todas As List(Of OpcionPermiso) = Construir()

        Public Const RolAdministrador As String = "Administrador"
        Public Const RolContador As String = "Contador"
        Public Const RolAuxiliar As String = "Auxiliar"
        Public Const RolConsulta As String = "Consulta"
        Public ReadOnly Roles As String() = {RolAdministrador, RolContador, RolAuxiliar, RolConsulta}

        Private Function Construir() As List(Of OpcionPermiso)
            Dim l As New List(Of OpcionPermiso)
            Dim g As String = "Administración"
            l.Add(New OpcionPermiso("ADM.PARAMETROS", "Parámetros de la empresa", g))
            l.Add(New OpcionPermiso("ADM.GESTIONES", "Gestiones (apertura, cierre)", g))
            l.Add(New OpcionPermiso("ADM.USUARIOS", "Usuarios y permisos", g))
            l.Add(New OpcionPermiso("ADM.AUDITORIA", "Auditoría del sistema", g))
            l.Add(New OpcionPermiso("ADM.BACKUP", "Copias de seguridad", g))
            l.Add(New OpcionPermiso("ADM.RESTAURAR", "Restaurar copias de seguridad", g))
            l.Add(New OpcionPermiso("ADM.IMPORTAR", "Importar datos (Orion4, Excel)", g))
            g = "Contabilidad"
            l.Add(New OpcionPermiso("CONT.PLAN", "Plan de cuentas", g))
            l.Add(New OpcionPermiso("CONT.COMPROBANTES", "Introducción de comprobantes", g))
            l.Add(New OpcionPermiso("CONT.MODIFICAR", "Modificar comprobantes", g))
            l.Add(New OpcionPermiso("CONT.ANULAR", "Anular comprobantes", g))
            l.Add(New OpcionPermiso("CONT.TIPOCAMBIO", "Tipos de cambio y UFV", g))
            l.Add(New OpcionPermiso("CONT.CENTROS", "Centros de costo", g))
            l.Add(New OpcionPermiso("CONT.PRESUPUESTO", "Presupuesto", g))
            l.Add(New OpcionPermiso("CONT.BANCOS", "Bancos y conciliación", g))
            l.Add(New OpcionPermiso("CONT.AJUSTES", "Ajuste por inflación / diferencia de cambio", g))
            l.Add(New OpcionPermiso("CONT.CIERRE", "Cierre de gestión", g))
            l.Add(New OpcionPermiso("CONT.UTILES", "Cambio de cuenta, reordenar, copiar", g))
            l.Add(New OpcionPermiso("CONT.REPORTES", "Libros y estados financieros", g))
            l.Add(New OpcionPermiso("CONT.CONSOLIDAR", "Consolidación de empresas", g))
            g = "Libros IVA"
            l.Add(New OpcionPermiso("IVA.COMPRAS", "Libro de compras IVA", g))
            l.Add(New OpcionPermiso("IVA.VENTAS", "Libro de ventas IVA", g))
            l.Add(New OpcionPermiso("IVA.REPORTES", "Reportes y exportación IVA", g))
            g = "Comercial"
            l.Add(New OpcionPermiso("COM.TERCEROS", "Clientes y proveedores", g))
            l.Add(New OpcionPermiso("COM.VENTAS", "Ventas", g))
            l.Add(New OpcionPermiso("COM.COMPRAS", "Compras", g))
            l.Add(New OpcionPermiso("COM.COBROS", "Cobros y pagos", g))
            l.Add(New OpcionPermiso("COM.REPORTES", "Reportes comerciales", g))
            g = "Inventarios"
            l.Add(New OpcionPermiso("INV.ITEMS", "Ítems, almacenes y precios", g))
            l.Add(New OpcionPermiso("INV.MOVIMIENTOS", "Ajustes, traspasos y stock inicial", g))
            l.Add(New OpcionPermiso("INV.REPORTES", "Kardex y reportes de inventario", g))
            g = "Activos fijos"
            l.Add(New OpcionPermiso("AF.ACTIVOS", "Registro de activos fijos", g))
            l.Add(New OpcionPermiso("AF.DEPRECIAR", "Depreciación y actualización", g))
            l.Add(New OpcionPermiso("AF.REPORTES", "Reportes de activos fijos", g))
            g = "Planillas"
            l.Add(New OpcionPermiso("RH.EMPLEADOS", "Empleados", g))
            l.Add(New OpcionPermiso("RH.PLANILLA", "Planilla de sueldos y RC-IVA", g))
            l.Add(New OpcionPermiso("RH.REPORTES", "Reportes de planillas", g))
            g = "Costos y producción"
            l.Add(New OpcionPermiso("COS.PRODUCCION", "Órdenes de producción", g))
            l.Add(New OpcionPermiso("COS.REPORTES", "Reportes de costos", g))
            Return l
        End Function

        ''' <summary>Opciones que otorga cada rol por defecto.</summary>
        Public Function PorRol(rol As String) As IEnumerable(Of String)
            Select Case rol
                Case RolAdministrador
                    Return Todas.Select(Function(o) o.Clave).ToList()
                Case RolContador
                    Return Todas.Where(Function(o) o.Clave <> "ADM.USUARIOS" AndAlso o.Clave <> "ADM.RESTAURAR").Select(Function(o) o.Clave).ToList()
                Case RolAuxiliar
                    Return Todas.Where(Function(o) o.Clave.EndsWith("REPORTES") OrElse o.Clave = "CONT.COMPROBANTES" OrElse
                        o.Clave = "IVA.COMPRAS" OrElse o.Clave = "IVA.VENTAS" OrElse o.Clave = "COM.TERCEROS" OrElse
                        o.Clave = "COM.VENTAS" OrElse o.Clave = "COM.COMPRAS" OrElse o.Clave = "COM.COBROS" OrElse
                        o.Clave = "INV.ITEMS" OrElse o.Clave = "INV.MOVIMIENTOS" OrElse o.Clave = "CONT.TIPOCAMBIO" OrElse
                        o.Clave = "CONT.BANCOS").Select(Function(o) o.Clave).ToList()
                Case Else
                    Return Todas.Where(Function(o) o.Clave.EndsWith("REPORTES")).Select(Function(o) o.Clave).ToList()
            End Select
        End Function

    End Module

End Namespace
