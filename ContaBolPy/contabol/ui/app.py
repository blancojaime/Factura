"""Punto de entrada de la aplicación de escritorio."""
from __future__ import annotations

import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from .. import APP_NAME, backup
from ..sistema import Sistema
from . import tema


def carpeta_datos() -> str:
    """Carpeta de datos del usuario: %LOCALAPPDATA%\\ContaBol (Windows) o ~/.contabol. Se puede cambiar con CONTABOL_DATOS."""
    env = os.environ.get("CONTABOL_DATOS")
    if env:
        return env
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "ContaBol" if os.environ.get("LOCALAPPDATA") else ".contabol")


def configurar_log(raiz: str) -> None:
    os.makedirs(os.path.join(raiz, "logs"), exist_ok=True)
    h = RotatingFileHandler(os.path.join(raiz, "logs", "contabol.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(h)
    logging.getLogger().setLevel(logging.INFO)


def main() -> int:
    raiz = carpeta_datos()
    os.makedirs(raiz, exist_ok=True)
    configurar_log(raiz)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    tema.aplicar(app)

    def excepcion(tipo, valor, tb):
        logging.getLogger("contabol").error("Excepción no controlada", exc_info=(tipo, valor, tb))
        QMessageBox.critical(None, "Error inesperado", f"{valor}\n\nEl detalle quedó registrado en:\n{os.path.join(raiz, 'logs', 'contabol.log')}")
    sys.excepthook = excepcion
    try:
        sis = Sistema(raiz)
    except Exception as ex:  # noqa: BLE001
        QMessageBox.critical(None, APP_NAME, f"No se pudo abrir la base de datos del sistema en:\n{raiz}\n\n{ex}")
        return 1
    from .login import CambioClaveDialog, LoginDialog, SelectorEmpresa
    from .ventana import VentanaPrincipal
    usuario = None
    while True:
        if usuario is None:
            dlg = LoginDialog(sis)
            if dlg.exec() != QDialog.Accepted:
                break
            usuario = dlg.usuario
            if usuario["cambiar_clave"]:
                if CambioClaveDialog(sis, usuario, True).exec() != QDialog.Accepted:
                    usuario = None
                    continue
                usuario = sis.usuario(usuario["id"])
        sel = SelectorEmpresa(sis, usuario)
        if sel.exec() != QDialog.Accepted or not sel.seleccion:
            if sel.result() == QDialog.Rejected:
                break
            continue
        try:
            ctx = sis.abrir_contexto(usuario, *sel.seleccion)
        except Exception as ex:  # noqa: BLE001
            QMessageBox.warning(None, APP_NAME, str(ex))
            continue
        w = VentanaPrincipal(sis, usuario, ctx)
        w.showMaximized()
        app.exec()
        accion = w.accion_salida
        try:
            ctx.cerrar()
        except Exception:  # noqa: BLE001
            pass
        if accion == "sesion":
            usuario = None
        elif accion == "cambiar":
            continue
        else:
            break
    try:
        backup.crear_backup(sis, None, tipo="AUTOMATICO")
        backup.limpiar_antiguos(sis)
    except Exception:  # noqa: BLE001
        logging.getLogger("contabol").exception("Respaldo automático fallido")
    sis.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
