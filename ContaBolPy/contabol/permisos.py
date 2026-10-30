"""Catálogo de opciones de permiso y roles predefinidos."""

OPCIONES: list[tuple[str, str, str]] = [
    ("ADM.PARAMETROS", "Parámetros de la empresa y normativa", "Administración"),
    ("ADM.GESTIONES", "Gestiones (apertura y cierre)", "Administración"),
    ("ADM.USUARIOS", "Usuarios y permisos", "Administración"),
    ("ADM.AUDITORIA", "Auditoría del sistema", "Administración"),
    ("ADM.BACKUP", "Copias de seguridad", "Administración"),
    ("ADM.RESTAURAR", "Restaurar copias de seguridad", "Administración"),
    ("CONT.PLAN", "Plan de cuentas", "Contabilidad"),
    ("CONT.COMPROBANTES", "Registrar comprobantes", "Contabilidad"),
    ("CONT.ANULAR", "Anular comprobantes", "Contabilidad"),
    ("CONT.TIPOCAMBIO", "Tipos de cambio y UFV", "Contabilidad"),
    ("CONT.BANCOS", "Bancos y conciliación", "Contabilidad"),
    ("CONT.PRESUPUESTO", "Presupuesto y centros de costo", "Contabilidad"),
    ("CONT.CIERRE", "Ajustes y cierre de gestión", "Contabilidad"),
    ("CONT.REPORTES", "Libros y estados financieros", "Contabilidad"),
    ("IVA.REGISTRO", "Libros de compras y ventas IVA", "Impuestos"),
    ("IVA.REPORTES", "Reportes e informes tributarios", "Impuestos"),
    ("COM.TERCEROS", "Clientes y proveedores", "Comercial"),
    ("COM.VENTAS", "Ventas", "Comercial"),
    ("COM.COMPRAS", "Compras", "Comercial"),
    ("COM.COBROS", "Cobros y pagos", "Comercial"),
    ("COM.REPORTES", "Reportes comerciales", "Comercial"),
    ("INV.ITEMS", "Ítems y catálogos de inventario", "Inventarios"),
    ("INV.MOVIMIENTOS", "Ajustes, traspasos y stock inicial", "Inventarios"),
    ("INV.REPORTES", "Kardex y reportes de inventario", "Inventarios"),
    ("AF.ACTIVOS", "Registro de activos fijos", "Activos fijos"),
    ("AF.DEPRECIAR", "Depreciación y actualización", "Activos fijos"),
    ("AF.REPORTES", "Reportes de activos fijos", "Activos fijos"),
    ("RH.EMPLEADOS", "Empleados", "Planillas"),
    ("RH.PLANILLA", "Planilla de sueldos, aguinaldo y finiquitos", "Planillas"),
    ("RH.REPORTES", "Reportes laborales", "Planillas"),
    ("COS.PRODUCCION", "Órdenes de producción", "Costos"),
    ("COS.REPORTES", "Reportes de costos", "Costos"),
]

TODAS = [o[0] for o in OPCIONES]

ROLES = {
    "ADMIN": "Administrador (todo)",
    "CONTADOR": "Contador (todo menos usuarios y restaurar)",
    "OPERADOR": "Operador (registro de operaciones)",
    "CONSULTA": "Consulta (solo reportes)",
}


def permisos_de_rol(rol: str) -> list[str]:
    if rol == "ADMIN":
        return list(TODAS)
    if rol == "CONTADOR":
        return [o for o in TODAS if o not in ("ADM.USUARIOS", "ADM.RESTAURAR")]
    if rol == "OPERADOR":
        return [o for o in TODAS if o.split(".")[1] in ("COMPROBANTES", "REGISTRO", "TERCEROS", "VENTAS", "COMPRAS", "COBROS",
                                                         "ITEMS", "MOVIMIENTOS", "TIPOCAMBIO", "BANCOS") or o.endswith("REPORTES")]
    if rol == "CONSULTA":
        return [o for o in TODAS if o.endswith("REPORTES")]
    return []
