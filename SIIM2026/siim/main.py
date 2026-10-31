"""Punto de entrada de SIIM 2026."""
import sys
import traceback


def selftest() -> int:
    """Autoprueba del ejecutable empaquetado: BD, tablas semilla, PDF/Excel/QR, respaldo cifrado y código de licencia."""
    import os
    import tempfile
    from pathlib import Path
    os.environ["SIIM_HOME"] = tempfile.mkdtemp()
    from .core import backup, license as Lic, security
    from .core.db import Database
    from .core.paths import db_path
    from .core.seed import seed_base
    from .core import demo
    from .reports import engine, formularios as FM
    from .reports import catalogo
    from .services import liquidacion as L
    from .services.base import Ctx
    db = Database(db_path())
    seed_base(db)
    demo.cargar_cotizaciones_demo(db)
    security.create_user(db, "t", "T", "ADMINISTRADOR", "Clave2026x")
    ctx = Ctx(db, security.login(db, "t", "Clave2026x"))
    ids = demo.cargar_padron_demo(ctx)
    lid = L.liquidar(ctx, "IPBI", ids["inm_perez"], 2004)
    td = Path(tempfile.mkdtemp())
    FM.generar(ctx, FM.spec_liquidacion(ctx, lid), td / "f.pdf")
    rep = catalogo.ejecutar(ctx, "emp_contribuyentes")
    engine.to_pdf(rep, td / "r.pdf", "Prueba", "t")
    engine.to_xlsx(rep, td / "r.xlsx", "Prueba", "t")
    b = backup.create_backup(db, td, "selftest", "clave")
    backup.verify_backup(b, "clave")
    assert db.integrity_check()[0] and security.verify_audit_chain(db)[0]
    for p in ("f.pdf", "r.pdf", "r.xlsx"):
        assert (td / p).stat().st_size > 1000, p
    print("SELFTEST OK · código de instalación:", Lic.machine_code())
    return 0


def run():
    if "--selftest" in sys.argv:
        try:
            return selftest()
        except Exception:
            traceback.print_exc()
            print("SELFTEST FALLÓ")
            return 1
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
    from . import APP_NAME
    from .core import license as Lic
    from .core import paths, security
    from .core.db import Database
    from .core.seed import seed_base
    from .ui import theme
    from .ui.acceso import Activacion, FirstRun, Login
    from .ui.main_window import AppState, MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(theme.QSS)
    sys.excepthook = lambda t, v, tb: (traceback.print_exception(t, v, tb), QMessageBox.critical(None, "Error", f"Error inesperado: {v}"))
    try:
        db = Database(paths.db_path())
    except Exception as e:
        QMessageBox.critical(None, APP_NAME, f"No se pudo abrir la base de datos:\n{e}\n\nRestaure un respaldo desde la carpeta {paths.backup_dir()}.")
        return 1
    ok, det = db.integrity_check()
    if not ok:
        QMessageBox.critical(None, APP_NAME, "La base de datos presenta errores de integridad:\n" + "\n".join(det[:5]) + f"\n\nRestaure el último respaldo ({paths.backup_dir()}).")
    seed_base(db)
    if not security.has_users(db):
        d = FirstRun()
        if d.exec() != QDialog.DialogCode.Accepted:
            return 0
        mun, nombre, usuario, clave = d.datos
        db.set_param("municipio", mun)
        security.create_user(db, usuario, nombre, "ADMINISTRADOR", clave)
        security.audit(db, usuario, "INSTALACION", detalle={"municipio": mun})
    lic = Lic.LicenseManager(db)
    st = lic.status()
    if st.estado in ("VENCIDO", "INVALIDO", "SIN_CONFIG") and not (st.estado == "SIN_CONFIG"):
        d = Activacion(lic, st)
        if d.exec() != QDialog.DialogCode.Accepted:
            return 0
        st = lic.status()
        if not st.ok:
            return 0
    elif st.estado == "PRUEBA" and (st.dias is not None and st.dias <= 10):
        d = Activacion(lic, st, puede_continuar=True)
        if d.exec() != QDialog.DialogCode.Accepted:
            return 0
    login = Login(db, db.param("municipio", ""))
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0
    state = AppState(db, login.session, lic)
    w = MainWindow(state)
    w.show()
    code = app.exec()
    db.close()
    return code


if __name__ == "__main__":
    sys.exit(run())
