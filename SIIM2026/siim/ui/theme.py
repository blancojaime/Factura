"""Tema visual formal (azul institucional, grises neutros)."""
NAVY = "#1F3A5F"
STEEL = "#2F5D8A"
BG = "#F3F5F8"
LINE = "#C9D2DE"
TEXT = "#1B2430"
MUTED = "#5B6573"
OK = "#2E7D5B"
WARN = "#B7791F"
BAD = "#B3392F"

QSS = f"""
* {{ font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", Arial; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog, QWidget#page {{ background: {BG}; }}
QLabel#titulo {{ font-size: 16pt; font-weight: 600; color: {NAVY}; }}
QLabel#subtitulo {{ color: {MUTED}; }}
QLabel#kpi {{ font-size: 20pt; font-weight: 700; color: {NAVY}; }}
QLabel#ok {{ color: {OK}; font-weight: 600; }} QLabel#warn {{ color: {WARN}; font-weight: 600; }} QLabel#bad {{ color: {BAD}; font-weight: 600; }}
QFrame#card {{ background: white; border: 1px solid {LINE}; border-radius: 6px; }}
QFrame#sidebar {{ background: {NAVY}; }}
QListWidget#nav {{ background: {NAVY}; border: none; outline: 0; color: #DCE5F0; }}
QListWidget#nav::item {{ padding: 9px 16px; border-left: 3px solid transparent; }}
QListWidget#nav::item:hover {{ background: #28496F; }}
QListWidget#nav::item:selected {{ background: #2F5D8A; color: white; border-left: 3px solid #F2C14E; }}
QLabel#brand {{ color: white; font-size: 15pt; font-weight: 700; padding: 14px 16px 2px 16px; }}
QLabel#brandsub {{ color: #A9BBD0; font-size: 8pt; padding: 0 16px 12px 16px; }}
QPushButton {{ background: white; border: 1px solid {LINE}; border-radius: 4px; padding: 6px 14px; }}
QPushButton:hover {{ border-color: {STEEL}; background: #EEF3F9; }}
QPushButton:disabled {{ color: #9AA5B4; background: #EEF1F5; }}
QPushButton#primary {{ background: {STEEL}; color: white; border: 1px solid {NAVY}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {NAVY}; }} QPushButton#primary:disabled {{ background: #9FB3CA; color: white; }}
QPushButton#danger {{ color: {BAD}; border-color: {BAD}; }}
QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{ background: white; border: 1px solid {LINE}; border-radius: 4px; padding: 4px 6px; min-height: 20px; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{ border: 1px solid {STEEL}; }}
QLineEdit:read-only {{ background: #EEF1F5; }}
QTableWidget, QTreeWidget, QListWidget {{ background: white; alternate-background-color: #F6F8FB; border: 1px solid {LINE}; gridline-color: #E3E8EF; selection-background-color: #CFE0F2; selection-color: {TEXT}; }}
QHeaderView::section {{ background: {NAVY}; color: white; padding: 5px 6px; border: none; border-right: 1px solid #3A557A; font-weight: 600; }}
QTabWidget::pane {{ border: 1px solid {LINE}; background: white; top: -1px; }}
QTabBar::tab {{ background: #E3E9F1; padding: 8px 16px; border: 1px solid {LINE}; border-bottom: none; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
QTabBar::tab:selected {{ background: white; color: {NAVY}; font-weight: 600; }}
QGroupBox {{ background: white; border: 1px solid {LINE}; border-radius: 6px; margin-top: 14px; padding: 12px 10px 8px 10px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {NAVY}; }}
QStatusBar {{ background: #E3E9F1; color: {MUTED}; }}
QMessageBox {{ background: white; }}
"""
