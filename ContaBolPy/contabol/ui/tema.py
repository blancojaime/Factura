"""Tema visual profesional: paleta, hoja de estilos (QSS), fuentes e iconos dibujados."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap

AZUL = "#1F3A5F"
AZUL_OSC = "#142844"
AZUL_MED = "#2E5E96"
AZUL_CLARO = "#DEE7F3"
AZUL_FONDO = "#EEF3FA"
FONDO = "#F4F6F9"
BORDE = "#D5DBE4"
TEXTO = "#212529"
GRIS = "#6C757D"
VERDE = "#287846"
ROJO = "#B02424"
AMBAR = "#BE780A"
BLANCO = "#FFFFFF"

FAMILIAS = ["Segoe UI", "Inter", "Noto Sans", "DejaVu Sans", "Arial"]


def fuente(tam: float = 10.0, negrita: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(FAMILIAS)
    f.setPointSizeF(tam)
    f.setBold(negrita)
    return f


QSS = f"""
* {{ font-size: 10pt; color: {TEXTO}; }}
QMainWindow, QDialog {{ background: {FONDO}; }}
QWidget#lienzo {{ background: {FONDO}; }}
QLabel {{ background: transparent; }}
QLabel#h1 {{ font-size: 16pt; font-weight: 600; color: {AZUL}; }}
QLabel#sub {{ color: {GRIS}; font-size: 9pt; }}
QLabel#etq {{ color: {GRIS}; font-size: 9pt; }}
QLabel#kpiv {{ font-size: 17pt; font-weight: 600; color: {AZUL}; }}
QLabel#kpit {{ color: {GRIS}; font-size: 9pt; }}
QFrame#banner {{ background: {BLANCO}; border-bottom: 1px solid {BORDE}; }}
QFrame#tarjeta {{ background: {BLANCO}; border: 1px solid {BORDE}; border-radius: 8px; }}
QFrame#panel {{ background: {BLANCO}; border: 1px solid {BORDE}; border-radius: 6px; }}
QMenuBar {{ background: {AZUL}; color: white; padding: 2px 6px; }}
QMenuBar::item {{ background: transparent; color: white; padding: 6px 12px; border-radius: 4px; }}
QMenuBar::item:selected {{ background: {AZUL_MED}; }}
QMenu {{ background: white; border: 1px solid {BORDE}; padding: 4px; }}
QMenu::item {{ padding: 6px 26px 6px 22px; border-radius: 3px; }}
QMenu::item:selected {{ background: {AZUL_CLARO}; color: {AZUL}; }}
QMenu::item:disabled {{ color: #A8B0BA; }}
QMenu::separator {{ height: 1px; background: {BORDE}; margin: 4px 8px; }}
QToolBar {{ background: white; border-bottom: 1px solid {BORDE}; spacing: 4px; padding: 4px 8px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 5px 10px; color: {AZUL}; font-weight: 500; }}
QToolButton:hover {{ background: {AZUL_FONDO}; border-color: {AZUL_CLARO}; }}
QToolButton:disabled {{ color: #A8B0BA; }}
QTabWidget::pane {{ border: none; background: {FONDO}; }}
QTabBar::tab {{ background: #E4E9F0; color: {GRIS}; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; min-width: 110px; }}
QTabBar::tab:selected {{ background: white; color: {AZUL}; font-weight: 600; border-bottom: 2px solid {AZUL_MED}; }}
QTabBar::tab:hover:!selected {{ background: {AZUL_CLARO}; }}
QStatusBar {{ background: {AZUL_OSC}; color: white; }}
QStatusBar QLabel {{ color: white; padding: 0 10px; }}
QPushButton {{ background: white; color: {AZUL}; border: 1px solid {AZUL_MED}; border-radius: 6px; padding: 7px 16px; font-weight: 500; }}
QPushButton:hover {{ background: {AZUL_FONDO}; }}
QPushButton:pressed {{ background: {AZUL_CLARO}; }}
QPushButton:disabled {{ color: #A8B0BA; border-color: {BORDE}; background: #F3F5F8; }}
QPushButton[tipo="primario"] {{ background: {AZUL}; color: white; border: 1px solid {AZUL}; }}
QPushButton[tipo="primario"]:hover {{ background: {AZUL_MED}; }}
QPushButton[tipo="primario"]:disabled {{ background: #9FB0C6; border-color: #9FB0C6; color: white; }}
QPushButton[tipo="exito"] {{ background: {VERDE}; color: white; border: 1px solid {VERDE}; }}
QPushButton[tipo="exito"]:hover {{ background: #2F8F55; }}
QPushButton[tipo="peligro"] {{ background: white; color: {ROJO}; border: 1px solid {ROJO}; }}
QPushButton[tipo="peligro"]:hover {{ background: #FBEDED; }}
QLineEdit, QTextEdit, QPlainTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: white; border: 1px solid {BORDE}; border-radius: 5px; padding: 5px 8px; selection-background-color: {AZUL_MED}; }}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {AZUL_MED}; }}
QLineEdit:read-only {{ background: #F1F4F8; color: {GRIS}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: white; border: 1px solid {BORDE}; selection-background-color: {AZUL_CLARO}; selection-color: {AZUL}; }}
QTableWidget, QTableView, QTreeWidget, QListWidget {{ background: white; alternate-background-color: #F6F8FB; border: 1px solid {BORDE}; gridline-color: #E6EAF0; selection-background-color: {AZUL_CLARO}; selection-color: {AZUL}; }}
QHeaderView::section {{ background: {AZUL}; color: white; padding: 7px 8px; border: none; border-right: 1px solid {AZUL_MED}; font-weight: 600; }}
QTableCornerButton::section {{ background: {AZUL}; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #C3CCD8; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #A9B5C5; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; }}
QScrollBar::handle:horizontal {{ background: #C3CCD8; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QGroupBox {{ background: white; border: 1px solid {BORDE}; border-radius: 6px; margin-top: 14px; padding: 14px 10px 8px 10px; font-weight: 600; color: {AZUL}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; background: {FONDO}; }}
QCheckBox {{ spacing: 7px; }}
QCheckBox::indicator {{ width: 17px; height: 17px; border: 1px solid #9FB0C6; border-radius: 4px; background: white; }}
QCheckBox::indicator:checked {{ background: {AZUL_MED}; border-color: {AZUL_MED}; }}
QToolTip {{ background: {AZUL_OSC}; color: white; border: none; padding: 5px 8px; }}
QProgressBar {{ border: 1px solid {BORDE}; border-radius: 5px; background: white; text-align: center; }}
QProgressBar::chunk {{ background: {AZUL_MED}; border-radius: 4px; }}
QSplitter::handle {{ background: {BORDE}; }}
"""


def icono(glifo: str, color: str = AZUL, fondo: str | None = None, tam: int = 32) -> QIcon:
    """Icono dibujado: glifo sobre una insignia redondeada (sin archivos externos)."""
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if fondo:
        p.setBrush(QBrush(QColor(fondo)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(1, 1, tam - 2, tam - 2), tam * 0.22, tam * 0.22)
    p.setPen(QPen(QColor(color)))
    f = fuente(tam * 0.42, True)
    p.setFont(f)
    p.drawText(QRectF(0, 0, tam, tam), Qt.AlignCenter, glifo)
    p.end()
    return QIcon(pm)


def logo_pixmap(tam: int = 64) -> QPixmap:
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(2, 2, tam - 4, tam - 4), tam * 0.2, tam * 0.2)
    p.fillPath(path, QColor(AZUL))
    p.setPen(QPen(QColor("white")))
    p.setFont(fuente(tam * 0.46, True))
    p.drawText(QRectF(0, 0, tam, tam * 0.92), Qt.AlignCenter, "CB")
    p.setPen(QPen(QColor("#7FB2F0"), max(2, tam // 22)))
    p.drawLine(int(tam * 0.22), int(tam * 0.8), int(tam * 0.78), int(tam * 0.8))
    p.end()
    return pm


def aplicar(app) -> None:
    app.setStyle("Fusion")
    app.setFont(fuente(10))
    app.setStyleSheet(QSS)
