"""Compatibilidad Qt: la variante para Windows 7 usa PySide2 (Qt 5.15) en lugar de PySide6 (Qt 6).

Se invoca al importar el paquete `contabol`; si PySide6 no está instalado, expone PySide2 con los nombres de PySide6
(y mueve a QtGui las clases que cambiaron de módulo) para que el resto del código no tenga que distinguirlos.
"""
from __future__ import annotations

import sys

try:  # camino normal (Windows 10/11, Linux): PySide6
    import PySide6  # noqa: F401
    USANDO_PYSIDE2 = False
except ImportError:
    import PySide2
    from PySide2 import QtCore, QtGui, QtWidgets

    # en Qt 6 estas clases están en QtGui
    for nombre in ("QAction", "QActionGroup", "QShortcut"):
        if not hasattr(QtGui, nombre) and hasattr(QtWidgets, nombre):
            setattr(QtGui, nombre, getattr(QtWidgets, nombre))
    sys.modules["PySide6"] = PySide2
    for sub in ("QtCore", "QtGui", "QtWidgets", "QtPrintSupport", "QtSvg", "QtNetwork"):
        try:
            sys.modules["PySide6." + sub] = __import__("PySide2." + sub, fromlist=[sub])
        except ImportError:
            pass
    # QDialog/QMenu/QApplication.exec(): PySide2 5.15 solo trae exec_()
    for cls in (QtWidgets.QDialog, QtWidgets.QMenu, QtWidgets.QApplication, QtWidgets.QMessageBox, QtWidgets.QFileDialog):
        if not hasattr(cls, "exec") and hasattr(cls, "exec_"):
            try:
                cls.exec = cls.exec_
            except (TypeError, AttributeError):
                pass
    USANDO_PYSIDE2 = True
