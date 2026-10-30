"""Genera las capturas REALES del aplicativo (Qt sin pantalla) con la empresa de demostración, para los manuales.

Uso:  QT_QPA_PLATFORM=offscreen python tools/capturas.py [carpeta_salida]
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from contabol import backup  # noqa: E402
from contabol.demo import crear_empresa_demo  # noqa: E402
from contabol.reports import catalogo, pdf  # noqa: E402
from contabol.sistema import Sistema  # noqa: E402
from contabol.ui import tema  # noqa: E402

SALIDA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "img")
os.makedirs(SALIDA, exist_ok=True)
ANIO = 2025
app = QApplication([])
tema.aplicar(app)


def pausa(n=3):
    for _ in range(n):
        app.processEvents()


def guardar(widget, nombre: str, ancho: int | None = None, alto: int | None = None):
    if ancho and alto:
        widget.resize(ancho, alto)
    widget.show()
    pausa()
    widget.grab().save(os.path.join(SALIDA, nombre + ".png"))
    print("  ", nombre)


def main():
    raiz = tempfile.mkdtemp(prefix="contabol_capturas_")
    sis = Sistema(raiz)
    usuario = sis.autenticar("admin", "admin")
    from contabol.ui.login import CambioClaveDialog, LoginDialog, SelectorEmpresa
    d = LoginDialog(sis)
    d.u.setText("admin")
    d.c.setText("••••••")
    guardar(d, "01_login")
    guardar(CambioClaveDialog(sis, usuario, True), "02_cambio_clave")
    eid, gid = crear_empresa_demo(sis, usuario, ANIO)
    sel = SelectorEmpresa(sis, usuario)
    guardar(sel, "03_selector_empresa", 760, 520)
    from contabol.ui.login import dialogo_nueva_empresa  # noqa: F401
    ctx = sis.abrir_contexto(usuario, eid, gid)
    from contabol.ui.ventana import VentanaPrincipal
    w = VentanaPrincipal(sis, usuario, ctx)
    w.resize(1366, 820)
    w.show()
    pausa()
    guardar(w, "04_inicio")
    # menú desplegado
    for nombre, idx in (("05_menu_contabilidad", 1), ("06_menu_estados_financieros", 8)):
        m = w.menuBar().actions()[idx].menu()
        g = w.menuBar().actionGeometry(w.menuBar().actions()[idx])
        m.popup(w.menuBar().mapToGlobal(QPoint(g.left(), g.bottom())))
        pausa()
        from PySide6.QtGui import QPainter
        base = w.grab()
        pos = w.mapFromGlobal(m.mapToGlobal(QPoint(0, 0)))
        pt = QPainter(base)
        pt.drawPixmap(pos, m.grab())
        pt.end()
        base.save(os.path.join(SALIDA, nombre + ".png"))
        m.hide()
    from contabol.ui import p_admin, p_comercial, p_contab, p_inventario, p_iva, p_rrhh
    from contabol.ui.reportes_ui import CentroReportes

    def pantalla(nombre, clase, *args, clave=None, tab=None):
        p = w.abrir(clase, *args, clave=clave or nombre)
        if tab is not None and hasattr(p, "tabs"):
            p.tabs.setCurrentIndex(tab)
        pausa()
        guardar(w, nombre)
        return p

    pantalla("07_plan_cuentas", p_contab.PlanCuentasPantalla)
    pantalla("08_comprobantes", p_contab.ComprobantesPantalla)
    pantalla("09_tipo_cambio", p_contab.TipoCambioPantalla)
    p = pantalla("10_conciliacion", p_contab.ConciliacionPantalla)
    pantalla("11_presupuesto", p_contab.PresupuestoPantalla)
    pantalla("12_libro_ventas", p_iva.LibroIvaPantalla, "V", clave="LV")
    pantalla("13_libro_compras", p_iva.LibroIvaPantalla, "C", clave="LC")
    pantalla("14_clientes", p_comercial.TercerosPantalla, "C", clave="TC")
    pantalla("15_proveedores", p_comercial.TercerosPantalla, "P", clave="TP")
    pantalla("16_ventas", p_comercial.DocumentosPantalla, True, clave="DV")
    pantalla("17_compras", p_comercial.DocumentosPantalla, False, clave="DC")
    pantalla("18_cobros_pagos", p_comercial.CobrosPagosPantalla)
    pantalla("19_items", p_inventario.ItemsPantalla)
    pantalla("20_movimientos_inventario", p_inventario.MovimientosPantalla)
    pantalla("21_almacenes", p_inventario.CatalogoPantalla, "almacen", clave="almacen")
    pantalla("22_activos", p_rrhh.ActivosPantalla)
    pantalla("23_depreciacion", p_rrhh.DepreciacionPantalla)
    pantalla("24_empleados", p_rrhh.EmpleadosPantalla)
    pl = pantalla("25_planilla", p_rrhh.PlanillaPantalla)
    pantalla("26_aguinaldo", p_rrhh.BeneficiosPantalla)
    pantalla("27_anticipos", p_rrhh.AnticiposPantalla)
    pantalla("28_produccion", p_rrhh.ProduccionPantalla)
    pantalla("29_cierre_gestion", p_admin.CierrePantalla)
    pantalla("30_consolidacion", p_admin.ConsolidarPantalla)
    pantalla("31_parametros_empresa", p_admin.ParametrosPantalla, clave="par0", tab=0)
    pantalla("32_parametros_cuentas", p_admin.ParametrosPantalla, clave="par1", tab=1)
    pantalla("33_parametros_normativa", p_admin.ParametrosPantalla, clave="par3", tab=3)
    pantalla("34_usuarios", p_admin.UsuariosPantalla)
    pantalla("35_auditoria", p_admin.AuditoriaPantalla)
    pantalla("36_backup", p_admin.BackupPantalla)
    pantalla("37_utilitarios", p_admin.UtilitariosPantalla)
    pantalla("38_centro_reportes", CentroReportes)
    # diálogos con datos
    fecha = date(ANIO, 12, 15)
    caja, banco, luz, cap = (ctx.cuentas.por_codigo(c)["id"] for c in ("1.1.1.01.001", "1.1.1.02.001", "5.3.1.02.001", "3.1.1.01.001"))
    cd = p_contab.ComprobanteDialog(ctx, None, w)
    cd.tipo.set_valor("E")
    cd.glosa.setText("Pago de energía eléctrica diciembre")
    cd.nombre.setText("Electropaz S.A.")
    cd.nro.setText("F-45821")
    for r, (cta, deb, hab) in enumerate([(luz, "1.043,00", ""), (banco, "", "1.043,00")]):
        c = ctx.cuentas.obtener(cta)
        cd.grid.item(r, 0).setText(f"{c['codigo']}  {c['nombre']}")
        cd.grid.item(r, 0).setData(Qt.UserRole, cta)
        cd.grid.item(r, 2).setText(deb)
        cd.grid.item(r, 3).setText(hab)
    cd.totales()
    guardar(cd, "40_comprobante_nuevo", 1040, 640)
    primero = ctx.db.scalar("SELECT MIN(id) FROM comprobante WHERE origen='VENTA'")
    guardar(p_contab.ComprobanteDialog(ctx, primero, w), "41_comprobante_automatico_venta", 1040, 640)
    fd = p_iva.FacturaDialog(ctx, "V", w)
    fd.nit.setText("1006341022")
    fd.razon.setText("Minimarket El Ahorro")
    fd.nro.setText("2401")
    fd.aut.setText("CUF7B1C9D40A55E")
    fd.total.set_valor(1000.0)
    fd.calcular()
    guardar(fd, "42_factura_ventas", 800, 640)
    guardar(p_iva.LiquidacionDialog(ctx, w), "43_liquidacion_iva", 580, 520)
    dv = p_comercial.DocumentoDialog(ctx, True, w)
    dv.tercero.setCurrentIndex(2)
    dv.nro.setText("2402")
    from contabol.ui.p_comercial import GridItems  # noqa: F401
    for r, (cod, cant) in enumerate([("ARZ01", 300), ("ACE01", 120), ("CAF01", 60)]):
        it = ctx.db.one("SELECT * FROM item WHERE codigo=?", (cod,))
        dv.grid.item(r, 0).setText(f"{it['codigo']}  {it['nombre']}")
        dv.grid.item(r, 0).setData(Qt.UserRole, it["id"])
    dv.grid.blockSignals(False)
    for r, (cant) in enumerate([300, 120, 60]):
        dv.grid.item(r, 1).setText(f"{cant:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    dv.totales()
    guardar(dv, "44_nota_venta", 1020, 700)
    guardar(p_comercial.CobroDialog(ctx, "CO", w), "45_cobro", 780, 560)
    guardar(p_inventario.MovimientoDialog(ctx, w), "46_movimiento_inventario", 920, 600)
    fp = p_rrhh.FilaPlanillaDialog(ctx, ctx.rrhh.planilla(ANIO, 12)["id"], ctx.rrhh.detalle(ctx.rrhh.planilla(ANIO, 12)["id"])[1], w)
    guardar(fp, "47_planilla_variables", 560, 420)
    oid = ctx.db.scalar("SELECT id FROM orden_prod LIMIT 1")
    # permisos
    uid = sis.crear_usuario("operador1", "Juan Pérez (operador)", "clave1234")
    sis.asignar_empresa(uid, eid, "OPERADOR")
    guardar(p_admin.PermisosDialog(sis, uid, ctx.empresa, "Juan Pérez (operador)", w), "48_permisos_usuario", 560, 640)
    guardar(p_admin.AcercaDe(ctx, w), "49_acerca_de")
    # informes en pantalla (visor)
    from contabol.ui.reportes_ui import ParametrosDialog, VisorInforme
    rep = catalogo.buscar("balance_general")
    guardar(ParametrosDialog(ctx, rep, w), "50_parametros_informe", 540, 360)
    for nombre, id_, vals in (("51_visor_balance_general", "balance_general", {}), ("52_visor_estado_resultados", "estado_resultados", {}), ("53_visor_evolucion_patrimonio", "evolucion_patrimonio", {}),
                              ("54_visor_flujo_directo", "flujo_directo", {}), ("55_visor_flujo_indirecto", "flujo_indirecto", {}), ("56_visor_notas", "notas_eeff", {}),
                              ("57_visor_libro_ventas", "libro_ventas", {"mes_desde": 12, "mes_hasta": 12}), ("58_visor_planilla", "planilla_sueldos", {"mes": 12})):
        r = catalogo.ejecutar(ctx, id_, vals)
        v = VisorInforme(ctx, r, w)
        pnt = w.abrir_pantalla(v, r.titulo, clave=nombre)
        pausa()
        guardar(w, nombre)
    # PDF reales -> PNG
    pdfs = {"pdf_balance_general": ("balance_general", {}), "pdf_estado_resultados": ("estado_resultados", {}), "pdf_evolucion_patrimonio": ("evolucion_patrimonio", {}),
            "pdf_flujo_directo": ("flujo_directo", {}), "pdf_flujo_indirecto": ("flujo_indirecto", {}), "pdf_libro_ventas": ("libro_ventas", {"mes_desde": 12, "mes_hasta": 12}),
            "pdf_comprobante": ("comprobante", {"id": primero}), "pdf_planilla": ("planilla_sueldos", {"mes": 12}), "pdf_boleta": ("boletas_pago", {"mes": 12}),
            "pdf_kardex": ("kardex_item", {"item": ctx.db.scalar("SELECT id FROM item WHERE codigo='ARZ01'")}), "pdf_liquidacion_iva": ("resumen_iva", {"mes_hasta": 12})}
    tmp = tempfile.mkdtemp()
    for nombre, (id_, vals) in pdfs.items():
        ruta = os.path.join(tmp, nombre + ".pdf")
        pdf.exportar(catalogo.ejecutar(ctx, id_, vals), ruta)
        subprocess.run(["pdftoppm", "-r", "80", "-png", "-f", "1", "-l", "1", "-singlefile", ruta, os.path.join(SALIDA, nombre)], check=False)
        print("  ", nombre)
    paquete = os.path.join(tmp, "paquete.pdf")
    pdf.exportar(catalogo.ejecutar(ctx, "estados_financieros", {}), paquete)
    shutil.copy(paquete, os.path.join(SALIDA, "ejemplo_estados_financieros.pdf"))
    from contabol.reports import excel
    excel.exportar(catalogo.ejecutar(ctx, "balance_general", {}), os.path.join(SALIDA, "ejemplo_balance_general.xlsx"))
    w.accion_salida = "cambiar"
    w.close()
    ctx.cerrar()
    sis.close()
    shutil.rmtree(raiz, ignore_errors=True)


if __name__ == "__main__":
    main()
    app.quit()
