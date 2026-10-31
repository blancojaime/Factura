"""Motor de reportes: un mismo objeto Report se exporta a PDF (reportlab) y Excel (openpyxl)."""
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL = colors.HexColor("#1F3A5F")
AZUL_CLARO = colors.HexColor("#E8EEF5")
GRIS = colors.HexColor("#5B6573")
LINEA = colors.HexColor("#C5CEDA")

FONT, FONT_B = "Helvetica", "Helvetica-Bold"
_font_ready = False


def setup_fonts():
    """Registra una fuente Unicode (Arial/Segoe en Windows, DejaVu/Liberation en Linux); si no, Helvetica."""
    global FONT, FONT_B, _font_ready
    if _font_ready:
        return
    _font_ready = True
    cands = []
    if os.name == "nt":
        w = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        cands += [(w / "segoeui.ttf", w / "segoeuib.ttf"), (w / "arial.ttf", w / "arialbd.ttf")]
    cands += [(Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
              (Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"), Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"))]
    for r, b in cands:
        if r.exists() and b.exists():
            try:
                pdfmetrics.registerFont(TTFont("SIIM", str(r)))
                pdfmetrics.registerFont(TTFont("SIIM-B", str(b)))
                pdfmetrics.registerFontFamily("SIIM", normal="SIIM", bold="SIIM-B")
                FONT, FONT_B = "SIIM", "SIIM-B"
                return
            except Exception:
                continue


def fmt_num(v, nd=2):
    return f"{float(v):,.{nd}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_date(s):
    if not s:
        return ""
    s = str(s)[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return s


@dataclass
class Col:
    key: str
    label: str
    kind: str = "text"       # text | money | int | date | pct | num
    width: float = 1.0       # peso relativo
    total: bool = False


@dataclass
class Report:
    title: str
    cols: list
    rows: list
    subtitle: str = ""
    notes: list = field(default_factory=list)
    landscape_: bool = None
    code: str = ""

    def cell(self, col, row, raw=False):
        v = row.get(col.key) if isinstance(row, dict) else row[col.key]
        if v is None or v == "":
            return "" if not raw else None
        if raw:
            return v
        if col.kind == "money":
            return fmt_num(v)
        if col.kind == "num":
            return fmt_num(v, 3)
        if col.kind == "int":
            return f"{int(v):,}".replace(",", ".")
        if col.kind == "pct":
            return fmt_num(v, 1) + " %"
        if col.kind == "date":
            return fmt_date(v)
        return str(v)

    def totals(self):
        out = {}
        for c in self.cols:
            if c.total:
                out[c.key] = sum(float((r.get(c.key) if isinstance(r, dict) else r[c.key]) or 0) for r in self.rows)
        return out


class _Numbered(canvas.Canvas):
    def __init__(self, *a, **k):
        self._meta = k.pop("meta")
        super().__init__(*a, **k)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._pages)
        for st in self._pages:
            self.__dict__.update(st)
            self._footer(n)
            super().showPage()
        super().save()

    def _footer(self, n):
        w, h = self._pagesize
        self.setStrokeColor(LINEA)
        self.line(15 * mm, 13 * mm, w - 15 * mm, 13 * mm)
        self.setFont(FONT, 7)
        self.setFillColor(GRIS)
        self.drawString(15 * mm, 9 * mm, f"{self._meta['sistema']} · Emitido: {datetime.now():%d/%m/%Y %H:%M} · Usuario: {self._meta['usuario']}")
        self.drawRightString(w - 15 * mm, 9 * mm, f"Página {self._pageNumber} de {n}")


def _header(canv, doc, meta, rep):
    w, h = canv._pagesize
    canv.saveState()
    canv.setFillColor(AZUL)
    canv.rect(0, h - 22 * mm, w, 22 * mm, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont(FONT_B, 11)
    canv.drawString(15 * mm, h - 10 * mm, meta["municipio"][:90])
    canv.setFont(FONT, 8)
    canv.drawString(15 * mm, h - 16 * mm, meta["sistema"])
    if rep.code:
        canv.drawRightString(w - 15 * mm, h - 10 * mm, rep.code)
    canv.restoreState()


def to_pdf(rep: Report, path, municipio="", usuario="", sistema="SIIM 2026 – Sistema Integrado de Ingresos Municipales"):
    setup_fonts()
    meta = dict(municipio=municipio or "—", usuario=usuario or "—", sistema=sistema)
    land = rep.landscape_ if rep.landscape_ is not None else len(rep.cols) > 6
    page = landscape(A4) if land else A4
    doc = SimpleDocTemplate(str(path), pagesize=page, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=28 * mm, bottomMargin=18 * mm, title=rep.title,
                            author="SIIM 2026")
    avail = page[0] - 30 * mm
    h1 = ParagraphStyle("h1", fontName=FONT_B, fontSize=13, textColor=AZUL, spaceAfter=2)
    sub = ParagraphStyle("sub", fontName=FONT, fontSize=8.5, textColor=GRIS, spaceAfter=6)
    cs = ParagraphStyle("c", fontName=FONT, fontSize=7.5, leading=9)
    hs = ParagraphStyle("hc", fontName=FONT_B, fontSize=7.5, leading=9, textColor=colors.white)
    el = [Paragraph(rep.title, h1)]
    if rep.subtitle:
        el.append(Paragraph(rep.subtitle, sub))
    tw = sum(c.width for c in rep.cols)
    cw = [avail * c.width / tw for c in rep.cols]
    al = lambda c: "RIGHT" if c.kind in ("money", "int", "num", "pct") else "LEFT"
    head = [Paragraph(c.label, ParagraphStyle("x", parent=hs, alignment=2 if al(c) == "RIGHT" else 0)) for c in rep.cols]
    data = [head]
    for r in rep.rows:
        data.append([Paragraph(str(rep.cell(c, r)).replace("&", "&amp;").replace("<", "&lt;"), ParagraphStyle("y", parent=cs, alignment=2 if al(c) == "RIGHT" else 0)) for c in rep.cols])
    tot = rep.totals()
    if tot:
        row = []
        for i, c in enumerate(rep.cols):
            if c.key in tot:
                row.append(Paragraph(f"<b>{rep.cell(c, {c.key: tot[c.key]})}</b>", ParagraphStyle("t", parent=cs, alignment=2)))
            else:
                row.append(Paragraph("<b>TOTAL</b>" if i == 0 else "", cs))
        data.append(row)
    if len(data) == 1:
        data.append([Paragraph("Sin registros para los criterios indicados.", cs)] + [""] * (len(rep.cols) - 1))
    t = Table(data, colWidths=cw, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), AZUL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.25, LINEA),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FB")]), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if tot:
        st += [("BACKGROUND", (0, -1), (-1, -1), AZUL_CLARO), ("LINEABOVE", (0, -1), (-1, -1), 0.8, AZUL)]
    t.setStyle(TableStyle(st))
    el.append(t)
    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph(f"Total de registros: {len(rep.rows)}", sub))
    for n in rep.notes:
        el.append(Paragraph(n, sub))
    doc.build(el, onFirstPage=lambda c, d: _header(c, d, meta, rep), onLaterPages=lambda c, d: _header(c, d, meta, rep),
              canvasmaker=lambda *a, **k: _Numbered(*a, meta=meta, **k))
    return Path(path)


def to_xlsx(rep: Report, path, municipio="", usuario=""):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = rep.title[:31].replace("/", "-").replace(":", "-")
    ws["A1"] = municipio
    ws["A1"].font = Font(bold=True, size=12, color="1F3A5F")
    ws["A2"] = rep.title
    ws["A2"].font = Font(bold=True, size=14)
    ws["A3"] = rep.subtitle or f"Emitido: {datetime.now():%d/%m/%Y %H:%M} · Usuario: {usuario}"
    ws["A3"].font = Font(italic=True, color="5B6573")
    r0 = 5
    thin = Side(style="thin", color="C5CEDA")
    for j, c in enumerate(rep.cols, 1):
        x = ws.cell(row=r0, column=j, value=c.label)
        x.font = Font(bold=True, color="FFFFFF")
        x.fill = PatternFill("solid", fgColor="1F3A5F")
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    fm = {"money": "#,##0.00", "int": "#,##0", "num": "#,##0.000", "pct": '0.0"%"'}
    for i, r in enumerate(rep.rows, r0 + 1):
        for j, c in enumerate(rep.cols, 1):
            v = rep.cell(c, r, raw=True)
            if c.kind == "date" and v:
                try:
                    v = datetime.strptime(str(v)[:10], "%Y-%m-%d")
                except ValueError:
                    pass
            x = ws.cell(row=i, column=j, value=v)
            x.border = Border(bottom=thin)
            if c.kind in fm:
                x.number_format = fm[c.kind]
            elif c.kind == "date":
                x.number_format = "dd/mm/yyyy"
    last = r0 + len(rep.rows)
    tot = rep.totals()
    if tot and rep.rows:
        ws.cell(row=last + 1, column=1, value="TOTAL").font = Font(bold=True)
        for j, c in enumerate(rep.cols, 1):
            if c.key in tot:
                L = get_column_letter(j)
                x = ws.cell(row=last + 1, column=j, value=f"=SUM({L}{r0 + 1}:{L}{last})")
                x.font = Font(bold=True)
                x.number_format = fm.get(c.kind, "General")
                x.fill = PatternFill("solid", fgColor="E8EEF5")
    for j, c in enumerate(rep.cols, 1):
        mx = max([len(str(c.label))] + [len(str(rep.cell(c, r))) for r in rep.rows[:300]])
        ws.column_dimensions[get_column_letter(j)].width = min(max(10, mx + 2), 60)
    ws.freeze_panes = ws.cell(row=r0 + 1, column=1)
    if rep.rows:
        ws.auto_filter.ref = f"A{r0}:{get_column_letter(len(rep.cols))}{last}"
    ws.page_setup.orientation = "landscape" if len(rep.cols) > 6 else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0
    wb.save(path)
    return Path(path)
