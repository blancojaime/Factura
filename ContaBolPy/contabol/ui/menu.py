"""Menú principal por módulos y barra de accesos rápidos."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDialog, QToolBar

from . import tema


def construir_menu(w) -> None:
    from .login import CambioClaveDialog
    from .p_admin import (AcercaDe, AuditoriaPantalla, BackupPantalla, CierrePantalla, ConsolidarPantalla, ParametrosPantalla, UsuariosPantalla, UtilitariosPantalla)
    from .p_comercial import CobrosPagosPantalla, DocumentosPantalla, TercerosPantalla
    from .p_contab import ComprobantesPantalla, ConciliacionPantalla, PlanCuentasPantalla, PresupuestoPantalla, TipoCambioPantalla
    from .p_inventario import CatalogoPantalla, ItemsPantalla, MovimientosPantalla, MovimientoDialog
    from .p_iva import LibroIvaPantalla, LiquidacionDialog
    from .p_rrhh import ActivosPantalla, AnticiposPantalla, BeneficiosPantalla, DepreciacionPantalla, EmpleadosPantalla, PlanillaPantalla, ProduccionPantalla
    from .reportes_ui import CentroReportes

    ctx = w.ctx
    mb = w.menuBar()
    mb.clear()

    def accion(menu, texto, permiso, fn, atajo=None):
        a = QAction(texto, w)
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
    accion(m, "Acerca de ContaBol", "", lambda: AcercaDe(ctx, w).exec())

    # barra de accesos rápidos
    tb = QToolBar("Accesos rápidos")
    tb.setMovable(False)
    tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    w.addToolBar(tb)
    colores = {"C": "#2E5E96", "V": "#287846", "P": "#BE780A", "L": "#1F3A5F", "I": "#6C4AB6", "R": "#B02424", "B": "#0F7C8A", "E": "#1F3A5F"}

    def boton_(texto, glifo, color, permiso, fn):
        a = QAction(tema.icono(glifo, "white", color, 36), texto, w)
        a.setEnabled(not permiso or ctx.puede(permiso))
        a.triggered.connect(lambda _=False: fn())
        tb.addAction(a)
    boton_("Comprobante", "＋", colores["C"], "CONT.COMPROBANTES", w.nuevo_comprobante)
    boton_("Venta", "V", colores["V"], "COM.VENTAS", lambda: w.nuevo_documento(True))
    boton_("Compra", "C", colores["P"], "COM.COMPRAS", lambda: w.nuevo_documento(False))
    tb.addSeparator()
    boton_("Libro ventas", "LV", colores["L"], "IVA.REGISTRO", lambda: w.abrir_libro_iva("V"))
    boton_("Libro compras", "LC", colores["L"], "IVA.REGISTRO", lambda: w.abrir_libro_iva("C"))
    boton_("Ítems", "I", colores["I"], "INV.ITEMS", lambda: w.abrir(ItemsPantalla))
    boton_("Planilla", "P", colores["B"], "RH.PLANILLA", lambda: w.abrir(PlanillaPantalla))
    tb.addSeparator()
    boton_("Estados fin.", "EF", colores["E"], "CONT.REPORTES", lambda: w.informe("estados_financieros"))
    boton_("Reportes", "R", colores["R"], "", lambda: w.abrir(CentroReportes))
    boton_("Respaldo", "B", colores["B"], "ADM.BACKUP", lambda: w.abrir(BackupPantalla))


def _salir(w, accion: str) -> None:
    w.accion_salida = accion
    w.close()
