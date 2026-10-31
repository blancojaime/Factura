"""Panel de inicio: indicadores, alertas y gráfico de recaudación mensual."""
from datetime import date, datetime

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..core import backup as B
from ..core.paths import backup_dir
from ..reports.engine import fmt_num
from ..services import padron
from ..services.base import hoy
from . import theme
from .widgets import card, titulo


class Bars(QWidget):
    def __init__(self):
        super().__init__()
        self.vals = [0] * 12
        self.setMinimumHeight(220)

    def set(self, vals):
        self.vals = vals; self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m = max(self.vals) or 100
        pad_l, pad_b, pad_t = 56, 26, 10
        p.setPen(QPen(QColor(theme.LINE)))
        for i in range(5):
            y = pad_t + (h - pad_b - pad_t) * i / 4
            p.drawLine(pad_l, int(y), w - 10, int(y))
            p.setPen(QColor(theme.MUTED)); p.setFont(QFont("Segoe UI", 7))
            p.drawText(0, int(y) - 7, pad_l - 6, 14, Qt.AlignRight | Qt.AlignVCenter, fmt_num(m * (1 - i / 4), 0))
            p.setPen(QPen(QColor(theme.LINE)))
        bw = (w - pad_l - 10) / 12
        meses = "Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic".split()
        for i, v in enumerate(self.vals):
            bh = (h - pad_b - pad_t) * v / m
            r = QRectF(pad_l + i * bw + bw * 0.18, h - pad_b - bh, bw * 0.64, bh)
            p.setBrush(QColor(theme.STEEL)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 2, 2)
            p.setPen(QColor(theme.MUTED)); p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRectF(pad_l + i * bw, h - pad_b + 4, bw, 16), Qt.AlignCenter, meses[i])


class InicioPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("page")
        l = QVBoxLayout(self)
        self.t = titulo("Panel de control", " ")
        l.addWidget(self.t)
        self.grid = QGridLayout()
        l.addLayout(self.grid)
        self.kp = {}
        for i, (k, n) in enumerate((("contrib", "Contribuyentes activos"), ("inm", "Inmuebles"), ("veh", "Vehículos"), ("act", "Actividades económicas"), ("hoy", "Recaudado hoy (Bs)"), ("mes", "Recaudado en el mes (Bs)"), ("anio", "Recaudado en el año (Bs)"))):
            c = card()
            cl = QVBoxLayout(c)
            v = QLabel("0"); v.setObjectName("kpi")
            cl.addWidget(v); cl.addWidget(QLabel(n))
            self.kp[k] = v
            self.grid.addWidget(c, i // 4, i % 4)
        row = QHBoxLayout()
        c1 = card(); l1 = QVBoxLayout(c1)
        l1.addWidget(QLabel("<b>Recaudación mensual del año (Bs)</b>"))
        self.bars = Bars()
        l1.addWidget(self.bars)
        row.addWidget(c1, 3)
        c2 = card(); self.l2 = QVBoxLayout(c2)
        self.l2.addWidget(QLabel("<b>Alertas</b>"))
        self.alertas = QLabel(); self.alertas.setWordWrap(True); self.alertas.setTextFormat(Qt.RichText)
        self.l2.addWidget(self.alertas); self.l2.addStretch(1)
        row.addWidget(c2, 2)
        l.addLayout(row, 1)

    def showEvent(self, e):
        super().showEvent(e)
        self.refrescar()

    def refrescar(self):
        db = self.app.db
        e = padron.estadisticas(db)
        for k, v in (("contrib", e["contribuyentes"]), ("inm", e["inmuebles"]), ("veh", e["vehiculos"]), ("act", e["actividades"])):
            self.kp[k].setText(f"{v:,}".replace(",", "."))
        h = hoy()
        s = lambda q, a=(): db.scalar(q, a, 0)
        fuc = lambda f1, f2: s("SELECT COALESCE(SUM(total),0) FROM fuc WHERE estado='RECAUDADO' AND fecha_pago BETWEEN ? AND ?", (f1, f2))
        pag = lambda f1, f2: s("SELECT COALESCE(SUM(total),0) FROM pagos WHERE estado='VIGENTE' AND fecha BETWEEN ? AND ?", (f1, f2))
        y, m = h[:4], h[:7]
        self.kp["hoy"].setText(fmt_num(pag(h, h) + fuc(h, h), 0))
        self.kp["mes"].setText(fmt_num(pag(m + "-01", m + "-31") + fuc(m + "-01", m + "-31"), 0))
        self.kp["anio"].setText(fmt_num(pag(y + "-01-01", y + "-12-31") + fuc(y + "-01-01", y + "-12-31"), 0))
        vals = [pag(f"{y}-{i:02d}-01", f"{y}-{i:02d}-31") + fuc(f"{y}-{i:02d}-01", f"{y}-{i:02d}-31") for i in range(1, 13)]
        self.bars.set(vals)
        self.t.findChild(QLabel, "subtitulo") and self.t.findChild(QLabel, "subtitulo").setText(db.param("municipio", ""))
        al = []
        padron.refrescar_licencias(db)
        n = len(padron.licencias_por_vencer(db))
        if n:
            al.append(f"<span style='color:{theme.WARN}'>● {n} licencia(s) vencen en los próximos {db.param('alerta_licencia_dias')} días</span>")
        v = s("SELECT COUNT(*) FROM actividades WHERE estado='ACTIVO' AND estado_licencia IN ('VENCIDA','SIN LICENCIA')")
        if v:
            al.append(f"<span style='color:{theme.BAD}'>● {v} actividad(es) sin licencia vigente</span>")
        if not db.one("SELECT 1 FROM cotizaciones WHERE fecha=?", (h,)):
            al.append(f"<span style='color:{theme.BAD}'>● Falta la cotización del dólar/UFV de hoy (Mantenimiento ▸ Generales)</span>")
        inc = s("SELECT COUNT(*) FROM contribuyentes WHERE estado='INCOMPLETO'")
        if inc:
            al.append(f"<span style='color:{theme.WARN}'>● {inc} registro(s) de contribuyentes incompletos</span>")
        pl = s("SELECT COUNT(DISTINCT plan_id) FROM plan_cuotas WHERE estado='PENDIENTE' AND vence<?", (h,))
        if pl:
            al.append(f"<span style='color:{theme.BAD}'>● {pl} plan(es) de pago con cuotas vencidas</span>")
        bk = B.list_backups(backup_dir())
        if not bk:
            al.append(f"<span style='color:{theme.BAD}'>● No existe ningún respaldo. Cree uno en Utilitarios.</span>")
        else:
            dias = (datetime.now() - bk[0]["fecha"]).days
            al.append(f"<span style='color:{theme.OK if dias < 2 else theme.WARN}'>● Último respaldo: hace {dias} día(s)</span>")
        self.alertas.setText("<br><br>".join(al) or "Sin alertas.")
