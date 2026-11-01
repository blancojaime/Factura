"""Iconos vectoriales profesionales dibujados con QPainter (nítidos a cualquier tamaño, sin archivos externos).

Cada icono es un glifo blanco de trazo uniforme sobre una insignia redondeada con degradado."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

# categoría -> (color superior, color inferior)
PALETA = {
    "conta": ("#3B6FB6", "#1F4E8C"), "venta": ("#2F9E63", "#1E7A4A"), "compra": ("#E09A2B", "#B87414"), "impuesto": ("#7A5BC7", "#5638A6"),
    "inventario": ("#2BA3B4", "#177A89"), "personal": ("#D2647A", "#A8405A"), "informe": ("#C9453F", "#9C2C27"), "admin": ("#64748B", "#3F4C5E"),
    "activo": ("#8A6A3B", "#634A25"), "costo": ("#E0702B", "#B24F12"),
}


def _g_plus(p):
    p.drawLine(QPointF(12, 5), QPointF(12, 19))
    p.drawLine(QPointF(5, 12), QPointF(19, 12))


def _g_doc(p):
    path = QPainterPath()
    path.moveTo(7, 4); path.lineTo(14, 4); path.lineTo(18, 8); path.lineTo(18, 20); path.lineTo(7, 20); path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(14, 4), QPointF(14, 8)); p.drawLine(QPointF(14, 8), QPointF(18, 8))
    for y in (12, 15, 18):
        p.drawLine(QPointF(9.5, y), QPointF(15.5, y))


def _g_arrow_up(p):
    p.drawEllipse(QRectF(4, 4, 16, 16))
    p.drawLine(QPointF(12, 16), QPointF(12, 8)); p.drawLine(QPointF(8.5, 11.5), QPointF(12, 8)); p.drawLine(QPointF(15.5, 11.5), QPointF(12, 8))


def _g_arrow_down(p):
    p.drawEllipse(QRectF(4, 4, 16, 16))
    p.drawLine(QPointF(12, 8), QPointF(12, 16)); p.drawLine(QPointF(8.5, 12.5), QPointF(12, 16)); p.drawLine(QPointF(15.5, 12.5), QPointF(12, 16))


def _g_book(p):
    p.drawRoundedRect(QRectF(4.5, 5, 7, 14), 1, 1)
    p.drawRoundedRect(QRectF(12.5, 5, 7, 14), 1, 1)
    for y in (9, 12, 15):
        p.drawLine(QPointF(6.5, y), QPointF(9.5, y)); p.drawLine(QPointF(14.5, y), QPointF(17.5, y))


def _g_box(p):
    path = QPainterPath()
    path.moveTo(12, 4); path.lineTo(19.5, 8); path.lineTo(19.5, 16); path.lineTo(12, 20); path.lineTo(4.5, 16); path.lineTo(4.5, 8); path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(4.5, 8), QPointF(12, 12)); p.drawLine(QPointF(19.5, 8), QPointF(12, 12)); p.drawLine(QPointF(12, 12), QPointF(12, 20))


def _g_user(p):
    p.drawEllipse(QRectF(8.5, 4.5, 7, 7))
    path = QPainterPath()
    path.moveTo(5, 20); path.cubicTo(5, 14, 19, 14, 19, 20)
    p.drawPath(path)


def _g_users(p):
    p.drawEllipse(QRectF(5, 5, 6, 6))
    p.drawEllipse(QRectF(13.5, 7, 5, 5))
    path = QPainterPath(); path.moveTo(3, 19); path.cubicTo(3, 13.5, 13, 13.5, 13, 19); p.drawPath(path)
    path2 = QPainterPath(); path2.moveTo(14.5, 15); path2.cubicTo(18, 14, 21, 15.5, 21, 19); p.drawPath(path2)


def _g_bars(p):
    for x, h in ((5, 8), (10.5, 12), (16, 15)):
        p.drawRoundedRect(QRectF(x, 20 - h, 3.5, h), 0.8, 0.8)
    p.drawLine(QPointF(4, 20.5), QPointF(20, 20.5))


def _g_pie(p):
    p.drawEllipse(QRectF(4, 4, 16, 16))
    p.drawLine(QPointF(12, 12), QPointF(12, 4)); p.drawLine(QPointF(12, 12), QPointF(18.5, 16))


def _g_db(p):
    p.drawEllipse(QRectF(5, 4.5, 14, 5))
    p.drawLine(QPointF(5, 7), QPointF(5, 17)); p.drawLine(QPointF(19, 7), QPointF(19, 17))
    path = QPainterPath(); path.moveTo(5, 12); path.arcTo(QRectF(5, 9.5, 14, 5), 180, 180); p.drawPath(path)
    path = QPainterPath(); path.moveTo(5, 17); path.arcTo(QRectF(5, 14.5, 14, 5), 180, 180); p.drawPath(path)


def _g_bank(p):
    path = QPainterPath(); path.moveTo(3.5, 9); path.lineTo(12, 4); path.lineTo(20.5, 9); path.closeSubpath(); p.drawPath(path)
    for x in (6.5, 10.5, 14.5):
        p.drawLine(QPointF(x + 1, 11), QPointF(x + 1, 17))
    p.drawLine(QPointF(4.5, 19.5), QPointF(19.5, 19.5))


def _g_factory(p):
    path = QPainterPath()
    path.moveTo(4, 20); path.lineTo(4, 11); path.lineTo(9, 14); path.lineTo(9, 11); path.lineTo(14, 14); path.lineTo(14, 6); path.lineTo(20, 6); path.lineTo(20, 20); path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(7, 17), QPointF(17, 17))


def _g_percent(p):
    p.drawEllipse(QRectF(5, 5.5, 5, 5)); p.drawEllipse(QRectF(14, 13.5, 5, 5)); p.drawLine(QPointF(18.5, 5), QPointF(5.5, 19))


def _g_gear(p):
    p.drawEllipse(QRectF(8.5, 8.5, 7, 7))
    for k in range(8):
        a = k * math.pi / 4
        p.drawLine(QPointF(12 + 6 * math.cos(a), 12 + 6 * math.sin(a)), QPointF(12 + 8.5 * math.cos(a), 12 + 8.5 * math.sin(a)))
    p.drawEllipse(QRectF(6, 6, 12, 12))


def _g_calc(p):
    p.drawRoundedRect(QRectF(6, 3.5, 12, 17), 1.8, 1.8)
    p.drawRect(QRectF(8, 6, 8, 3.5))
    for r in range(3):
        for c in range(3):
            p.drawPoint(QPointF(9 + c * 3, 12.5 + r * 3))


def _g_tree(p):
    p.drawRoundedRect(QRectF(4, 4, 7, 4.5), 1, 1)
    p.drawLine(QPointF(7.5, 8.5), QPointF(7.5, 18)); p.drawLine(QPointF(7.5, 12), QPointF(12, 12)); p.drawLine(QPointF(7.5, 18), QPointF(12, 18))
    p.drawRoundedRect(QRectF(12, 9.8, 8, 4.4), 1, 1); p.drawRoundedRect(QRectF(12, 15.8, 8, 4.4), 1, 1)


def _g_lock(p):
    p.drawRoundedRect(QRectF(5.5, 11, 13, 9), 1.8, 1.8)
    path = QPainterPath(); path.moveTo(8.5, 11); path.lineTo(8.5, 8.5); path.arcTo(QRectF(8.5, 4, 7, 9), 180, -180); path.lineTo(15.5, 11); p.drawPath(path)


def _g_search(p):
    p.drawEllipse(QRectF(4.5, 4.5, 10, 10)); p.drawLine(QPointF(13, 13), QPointF(19.5, 19.5))


def _g_truck(p):
    p.drawRect(QRectF(3.5, 7, 10, 8)); path = QPainterPath(); path.moveTo(13.5, 10); path.lineTo(17.5, 10); path.lineTo(20.5, 13); path.lineTo(20.5, 15); path.lineTo(13.5, 15); p.drawPath(path)
    p.drawEllipse(QRectF(6, 15, 3.5, 3.5)); p.drawEllipse(QRectF(15.5, 15, 3.5, 3.5))


def _g_cart(p):
    path = QPainterPath(); path.moveTo(3.5, 5.5); path.lineTo(6.5, 5.5); path.lineTo(8.5, 15); path.lineTo(18, 15); path.lineTo(19.5, 8.5); path.lineTo(7, 8.5); p.drawPath(path)
    p.drawEllipse(QRectF(9, 17, 2.4, 2.4)); p.drawEllipse(QRectF(15, 17, 2.4, 2.4))


def _g_check(p):
    p.drawLine(QPointF(5.5, 12.5), QPointF(10, 17)); p.drawLine(QPointF(10, 17), QPointF(18.5, 7))


def _g_help(p):
    p.drawEllipse(QRectF(4, 4, 16, 16))
    path = QPainterPath(); path.moveTo(9.5, 9.5); path.cubicTo(9.5, 6, 14.5, 6, 14.5, 9.5); path.cubicTo(14.5, 11.5, 12, 11.5, 12, 14); p.drawPath(path)
    p.drawPoint(QPointF(12, 16.8))


def _g_exit(p):
    p.drawRoundedRect(QRectF(4.5, 4.5, 9, 15), 1.2, 1.2)
    p.drawLine(QPointF(10, 12), QPointF(19.5, 12)); p.drawLine(QPointF(16, 8.5), QPointF(19.5, 12)); p.drawLine(QPointF(16, 15.5), QPointF(19.5, 12))


def _g_calendar(p):
    p.drawRoundedRect(QRectF(4.5, 6, 15, 13.5), 1.5, 1.5); p.drawLine(QPointF(4.5, 10), QPointF(19.5, 10))
    p.drawLine(QPointF(8.5, 4), QPointF(8.5, 7.5)); p.drawLine(QPointF(15.5, 4), QPointF(15.5, 7.5))


def _g_money(p):
    p.drawRoundedRect(QRectF(3.5, 7, 17, 10), 1.5, 1.5); p.drawEllipse(QRectF(9.5, 9.5, 5, 5))


def _g_transfer(p):
    p.drawLine(QPointF(5, 9), QPointF(18, 9)); p.drawLine(QPointF(14.5, 5.5), QPointF(18, 9)); p.drawLine(QPointF(14.5, 12.5), QPointF(18, 9))
    p.drawLine(QPointF(19, 15), QPointF(6, 15)); p.drawLine(QPointF(9.5, 11.5), QPointF(6, 15)); p.drawLine(QPointF(9.5, 18.5), QPointF(6, 15))


GLIFOS = {"nuevo": _g_plus, "comprobante": _g_doc, "venta": _g_arrow_up, "compra": _g_arrow_down, "libro": _g_book, "items": _g_box, "usuario": _g_user, "usuarios": _g_users,
          "estados": _g_bars, "informe": _g_pie, "respaldo": _g_db, "banco": _g_bank, "produccion": _g_factory, "impuesto": _g_percent, "config": _g_gear, "calculadora": _g_calc,
          "plan": _g_tree, "candado": _g_lock, "buscar": _g_search, "proveedor": _g_truck, "carrito": _g_cart, "ok": _g_check, "ayuda": _g_help, "salir": _g_exit,
          "calendario": _g_calendar, "dinero": _g_money, "cobros": _g_transfer, "activo": _g_factory}


def icono(nombre: str, categoria: str = "conta", tam: int = 40, plano: bool = False) -> QIcon:
    """Icono con insignia de color. plano=True dibuja solo el glifo con el color de la categoría (para menús)."""
    escala = 4
    T = tam * escala
    pm = QPixmap(T, T)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    c1, c2 = PALETA.get(categoria, PALETA["conta"])
    if not plano:
        g = QLinearGradient(0, 0, 0, T)
        g.setColorAt(0, QColor(c1)); g.setColorAt(1, QColor(c2))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(g))
        p.drawRoundedRect(QRectF(T * 0.04, T * 0.04, T * 0.92, T * 0.92), T * 0.24, T * 0.24)
    p.save()
    margen = T * (0.0 if plano else 0.14)
    s = (T - 2 * margen) / 24.0
    p.translate(margen, margen)
    p.scale(s, s)
    pen = QPen(QColor(c2) if plano else QColor("white"), 1.9)
    pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.NoBrush)
    GLIFOS.get(nombre, _g_doc)(p)
    p.restore()
    p.end()
    pm = pm.scaled(tam * 2, tam * 2, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return QIcon(pm)
