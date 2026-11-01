"""Menú principal por módulos y barra de accesos rápidos."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDialog, QToolBar

from . import iconos, tema


def construir_menu(w) -> None:
    from .login import CambioClaveDialog
    from .p_admin import (AcercaDe, AuditoriaPantalla, BackupPantalla, CierrePantalla, ConsolidarPantalla, ParametrosPantalla, UsuariosPantalla, UtilitariosPantalla)
    from .p_comercial import CobrosPagosPantalla, DocumentosPantalla, TercerosPantalla
    from .p_contab import ComprobantesPantalla, ConciliacionPantalla, PlanCuentasPantalla, PresupuestoPantalla, TipoCambioPantalla
    from .p_inventario import CatalogoPantalla, ItemsPantalla, MovimientosPantalla, MovimientoDialog
    from .p_iva import LibroIvaPantalla, LiquidacionDialog
    from .p_rrhh import ActivosPantalla, AnticiposPantalla, BeneficiosPantalla, DepreciacionPantalla, EmpleadosPantalla, PlanillaPantalla, ProduccionPantalla
    from .reportes_ui import CentroReportes
    from .p_auditoria import AuditoriaFinancieraPantalla, AuditoriaTributariaPantalla

    ctx = w.ctx
    mb = w.menuBar()
    mb.clear()

    reglas = [("comprobante", "comprobante", "conta"), ("plan de cuentas", "plan", "conta"), ("tipos de cambio", "dinero", "conta"), ("conciliación", "banco", "conta"),
              ("presupuesto", "estados", "conta"), ("cierre", "candado", "conta"), ("consolidación", "estados", "conta"), ("utilitarios", "config", "admin"),
              ("libro de compras", "libro", "impuesto"), ("libro de ventas", "libro", "impuesto"), ("liquidación", "impuesto", "impuesto"), ("lcv", "libro", "impuesto"),
              ("clientes", "usuario", "venta"), ("proveedores", "proveedor", "compra"), ("venta", "venta", "venta"), ("compra", "compra", "compra"), ("cobros", "cobros", "venta"),
              ("ítems", "items", "inventario"), ("inventario", "items", "inventario"), ("movimiento", "items", "inventario"), ("almacén", "items", "inventario"),
              ("activos", "activo", "activo"), ("depreciación", "activo", "activo"), ("empleados", "usuarios", "personal"), ("planilla", "usuarios", "personal"),
              ("anticipo", "dinero", "personal"), ("aguinaldo", "calendario", "personal"), ("producción", "produccion", "costo"), ("balance", "estados", "informe"),
              ("resultados", "estados", "informe"), ("patrimonio", "estados", "informe"), ("flujo", "cobros", "informe"), ("notas", "libro", "informe"), ("estados financieros", "estados", "informe"),
              ("centro de reportes", "informe", "informe"), ("libro diario", "libro", "informe"), ("libro mayor", "libro", "informe"), ("sumas", "estados", "informe"), ("índices", "informe", "informe"),
              ("parámetros", "config", "admin"), ("usuarios", "usuarios", "admin"), ("auditoría financiera", "buscar", "informe"), ("auditoría tributaria", "buscar", "impuesto"), ("auditoría", "buscar", "admin"), ("copias", "respaldo", "admin"), ("contraseña", "candado", "admin"),
              ("empresa o gestión", "banco", "conta"), ("cerrar sesión", "salir", "admin"), ("salir", "salir", "admin"), ("acerca", "ayuda", "admin")]

    def icono_para(texto):
        t = texto.lower()
        for k, g, c in reglas:
            if k in t:
                return iconos.icono(g, c, 22, plano=True)
        return None

    def accion(menu, texto, permiso, fn, atajo=None):
        a = QAction(texto, w)
        ic = icono_para(texto)
        if ic:
            a.setIcon(ic)
        a.setEnabled(not permiso or ctx.puede(permiso))
        a.triggered.connect(lambda _=False: fn())
        if atajo:
            a.setShortcut(QKeySequence(atajo))
        menu.addAction(a)
        return a

    def inf(id_):
        return lambda: w.informe(id_)

    # Archivo
    m = mb.addMenu("&Archivo")
    accion(m, "Cambiar de empresa o gestión…", "", lambda: _salir(w, "cambiar"))
    accion(m, "Cambiar mi contraseña…", "", lambda: CambioClaveDialog(w.sis, w.usuario, False, w).exec())
    accion(m, "Cerrar sesión", "", lambda: _salir(w, "sesion"))
    m.addSeparator()
    accion(m, "Cerrar pestaña actual", "", w.cerrar_actual, "Ctrl+W")
    accion(m, "Salir", "", lambda: _salir(w, "salir"), "Alt+F4")
    # Contabilidad
    m = mb.addMenu("&Contabilidad")
    accion(m, "Plan de cuentas", "CONT.PLAN", lambda: w.abrir(PlanCuentasPantalla))
    accion(m, "Nuevo comprobante", "CONT.COMPROBANTES", w.nuevo_comprobante, "Ctrl+N")
    accion(m, "Comprobantes", "CONT.COMPROBANTES", lambda: w.abrir(ComprobantesPantalla))
    accion(m, "Tipos de cambio y UFV", "CONT.TIPOCAMBIO", lambda: w.abrir(TipoCambioPantalla))
    m.addSeparator()
    accion(m, "Conciliación bancaria", "CONT.BANCOS", lambda: w.abrir(ConciliacionPantalla))
    accion(m, "Presupuesto", "CONT.PRESUPUESTO", lambda: w.abrir(PresupuestoPantalla))
    m.addSeparator()
    accion(m, "Ajustes y cierre de gestión…", "CONT.CIERRE", lambda: w.abrir(CierrePantalla))
    accion(m, "Consolidación de empresas…", "ADM.GESTIONES", lambda: w.abrir(ConsolidarPantalla))
    accion(m, "Utilitarios y verificación", "CONT.REPORTES", lambda: w.abrir(UtilitariosPantalla))
    # Impuestos
    m = mb.addMenu("&Impuestos")
    accion(m, "Libro de compras IVA (registro)", "IVA.REGISTRO", lambda: w.abrir_libro_iva("C"))
    accion(m, "Libro de ventas IVA (registro)", "IVA.REGISTRO", lambda: w.abrir_libro_iva("V"))
    accion(m, "Liquidación mensual de IVA e IT…", "IVA.REGISTRO", lambda: LiquidacionDialog(ctx, w).exec())
    m.addSeparator()
    for t, i in (("Informe: Libro de compras", "libro_compras"), ("Informe: Libro de ventas", "libro_ventas"), ("Informe: Liquidación de IVA e IT", "resumen_iva"), ("Exportación LCV para el SIN", "lcv_exportacion")):
        accion(m, t, "IVA.REPORTES", inf(i))
    # Comercial
    m = mb.addMenu("C&omercial")
    accion(m, "Clientes", "COM.TERCEROS", lambda: w.abrir(TercerosPantalla, "C", clave="Terceros.C"))
    accion(m, "Proveedores", "COM.TERCEROS", lambda: w.abrir(TercerosPantalla, "P", clave="Terceros.P"))
    m.addSeparator()
    accion(m, "Nota de venta", "COM.VENTAS", lambda: w.nuevo_documento(True), "F5")
    accion(m, "Ventas realizadas", "COM.VENTAS", lambda: w.abrir(DocumentosPantalla, True, clave="Docs.V"))
    accion(m, "Nota de compra", "COM.COMPRAS", lambda: w.nuevo_documento(False), "F6")
    accion(m, "Compras realizadas", "COM.COMPRAS", lambda: w.abrir(DocumentosPantalla, False, clave="Docs.C"))
    accion(m, "Cobros y pagos", "COM.COBROS", lambda: w.abrir(CobrosPagosPantalla))
    # Inventarios
    m = mb.addMenu("&Inventarios")
    accion(m, "Ítems y precios", "INV.ITEMS", lambda: w.abrir(ItemsPantalla))
    accion(m, "Movimiento de inventario (stock inicial, ajustes, traspasos)", "INV.MOVIMIENTOS", lambda: MovimientoDialog(ctx, w).exec())
    accion(m, "Movimientos registrados", "INV.MOVIMIENTOS", lambda: w.abrir(MovimientosPantalla))
    sub = m.addMenu("Tablas auxiliares")
    for t, tb in (("Almacenes", "almacen"), ("Unidades de medida", "unidad"), ("Grupos de ítems", "grupo_item"), ("Vendedores", "vendedor")):
        accion(sub, t, "INV.ITEMS", lambda tb=tb: w.abrir(CatalogoPantalla, tb, clave=f"Cat.{tb}"))
    m.addSeparator()
    for t, i in (("Kardex físico valorado", "kardex_item"), ("Inventario valorado", "existencias"), ("Lista de precios", "lista_precios"), ("Productos por vencer", "por_vencer"), ("Sugerencia de compras", "sugerencia_compras")):
        accion(m, t, "INV.REPORTES", inf(i))
    # Activos
    m = mb.addMenu("Activos &fijos")
    accion(m, "Registro de activos", "AF.ACTIVOS", lambda: w.abrir(ActivosPantalla))
    accion(m, "Depreciación y actualización", "AF.DEPRECIAR", lambda: w.abrir(DepreciacionPantalla))
    m.addSeparator()
    accion(m, "Cuadro de activos fijos", "AF.REPORTES", inf("cuadro_activos"))
    # Planillas
    m = mb.addMenu("&Planillas")
    accion(m, "Empleados", "RH.EMPLEADOS", lambda: w.abrir(EmpleadosPantalla))
    accion(m, "Planilla de sueldos", "RH.PLANILLA", lambda: w.abrir(PlanillaPantalla))
    accion(m, "Anticipos de sueldo", "RH.PLANILLA", lambda: w.abrir(AnticiposPantalla))
    accion(m, "Aguinaldo y finiquitos", "RH.PLANILLA", lambda: w.abrir(BeneficiosPantalla))
    m.addSeparator()
    for t, i in (("Planilla de sueldos (informe)", "planilla_sueldos"), ("Planilla tributaria RC-IVA", "planilla_rciva"), ("Resumen de aportes", "planilla_aportes"), ("Boletas de pago", "boletas_pago")):
        accion(m, t, "RH.REPORTES", inf(i))
    # Costos
    m = mb.addMenu("Cos&tos")
    accion(m, "Órdenes de producción", "COS.PRODUCCION", lambda: w.abrir(ProduccionPantalla))
    accion(m, "Órdenes de producción (informe)", "COS.REPORTES", inf("ordenes_produccion"))
    # Auditoría
    m = mb.addMenu("A&uditoría")
    accion(m, "Auditoría financiera (MAF)", "AUD.FINANCIERA", lambda: w.abrir(AuditoriaFinancieraPantalla))
    accion(m, "Auditoría tributaria (MAI)", "AUD.TRIBUTARIA", lambda: w.abrir(AuditoriaTributariaPantalla))
    m.addSeparator()
    for t, i in (("Memorándum de planificación", "aud_mpa"), ("Matriz de riesgos", "aud_riesgos"), ("Cédulas sumarias y analíticas", "aud_sumarias"), ("Hallazgos de auditoría", "aud_hallazgos"),
                 ("Resumen de desvíos y ajustes", "aud_desvios"), ("Conciliación IVA / IT", "aud_iva_it"), ("Bancarización", "aud_bancarizacion"), ("Depuración de gastos e IUE", "aud_iue"),
                 ("Anexos ITC", "aud_anexos_itc"), ("Situación tributaria y contingencias", "aud_contingencias")):
        accion(m, t, "AUD.REPORTES", inf(i))
    # Estados financieros
    m = mb.addMenu("&Estados financieros")
    for t, i in (("Balance General", "balance_general"), ("Estado de Resultados", "estado_resultados"), ("Estado de Evolución del Patrimonio Neto", "evolucion_patrimonio"),
                 ("Flujo de Efectivo - Método Directo", "flujo_directo"), ("Flujo de Efectivo - Método Indirecto", "flujo_indirecto"), ("Notas a los Estados Financieros", "notas_eeff")):
        accion(m, t, "CONT.REPORTES", inf(i))
    m.addSeparator()
    accion(m, "Todos los estados financieros (paquete completo)", "CONT.REPORTES", inf("estados_financieros"))
    # Reportes
    m = mb.addMenu("&Reportes")
    accion(m, "Centro de reportes…", "", lambda: w.abrir(CentroReportes), "F9")
    m.addSeparator()
    for t, i in (("Libro diario", "libro_diario"), ("Libro mayor", "libro_mayor"), ("Balance de sumas y saldos", "sumas_saldos"), ("Hoja de trabajo", "hoja_trabajo"), ("Índices financieros", "indices")):
        accion(m, t, "CONT.REPORTES", inf(i))
    # Administración
    m = mb.addMenu("A&dministración")
    accion(m, "Parámetros y normativa", "ADM.PARAMETROS", lambda: w.abrir(ParametrosPantalla))
    accion(m, "Usuarios y permisos", "ADM.USUARIOS", lambda: w.abrir(UsuariosPantalla))
    accion(m, "Auditoría del sistema", "ADM.AUDITORIA", lambda: w.abrir(AuditoriaPantalla))
    accion(m, "Copias de seguridad y restauración", "ADM.BACKUP", lambda: w.abrir(BackupPantalla))
    # Ayuda
    m = mb.addMenu("A&yuda")
    accion(m, "Acerca de CONTA JB", "", lambda: AcercaDe(ctx, w).exec())

    # barra de accesos rápidos
    tb = QToolBar("Accesos rápidos")
    tb.setMovable(False)
    tb.setIconSize(QSize(34, 34))
    tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    w.addToolBar(tb)

    def boton_(texto, glifo, cat, permiso, fn):
        a = QAction(iconos.icono(glifo, cat, 40), texto, w)
        a.setEnabled(not permiso or ctx.puede(permiso))
        a.triggered.connect(lambda _=False: fn())
        tb.addAction(a)
    boton_("Comprobante", "nuevo", "conta", "CONT.COMPROBANTES", w.nuevo_comprobante)
    boton_("Venta", "venta", "venta", "COM.VENTAS", lambda: w.nuevo_documento(True))
    boton_("Compra", "compra", "compra", "COM.COMPRAS", lambda: w.nuevo_documento(False))
    tb.addSeparator()
    boton_("Libro ventas", "libro", "venta", "IVA.REGISTRO", lambda: w.abrir_libro_iva("V"))
    boton_("Libro compras", "libro", "compra", "IVA.REGISTRO", lambda: w.abrir_libro_iva("C"))
    boton_("Plan de cuentas", "plan", "conta", "CONT.PLAN", lambda: w.abrir(PlanCuentasPantalla))
    boton_("Ítems", "items", "inventario", "INV.ITEMS", lambda: w.abrir(ItemsPantalla))
    boton_("Planilla", "usuarios", "personal", "RH.PLANILLA", lambda: w.abrir(PlanillaPantalla))
    tb.addSeparator()
    boton_("Estados fin.", "estados", "informe", "CONT.REPORTES", lambda: w.informe("estados_financieros"))
    boton_("Reportes", "informe", "informe", "", lambda: w.abrir(CentroReportes))
    boton_("Calculadora", "calculadora", "admin", "", lambda: __import__("contabol.ui.calculadora", fromlist=["x"]).Calculadora(w).show())
    boton_("Respaldo", "respaldo", "admin", "ADM.BACKUP", lambda: w.abrir(BackupPantalla))


def _salir(w, accion: str) -> None:
    w.accion_salida = accion
    w.close()
