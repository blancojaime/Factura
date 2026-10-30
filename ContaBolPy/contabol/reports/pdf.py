"""Exportación a PDF con ReportLab (cabecera de empresa, pie con paginación, firmas)."""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether

from ..util import fmt
from .engine import Col, ReporteDef, Tabla, Texto

AZUL = colors.HexColor("#1F3A5F")
AZUL_CLARO = colors.HexColor("#DEE7F3")
GRIS = colors.HexColor("#6C757D")
ZEBRA = colors.HexColor("#F6F8FB")


class _Numerado(canvas.Canvas):
    """Canvas de dos pasadas para mostrar 'Página x de y'."""

    def __init__(self, *a, rep: ReporteDef | None = None, **k):
        super().__init__(*a, **k)
        self._paginas: list[dict] = []
        self.rep = rep

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._pie(total)
            super().showPage()
        super().save()

    def _pie(self, total: int):
        w, _ = self._pagesize
        self.setStrokeColor(colors.HexColor("#C9D1DC"))
        self.setLineWidth(0.5)
        self.line(15 * mm, 13 * mm, w - 15 * mm, 13 * mm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(GRIS)
        self.drawString(15 * mm, 9 * mm, f"ContaBol - Sistema Contable Integrado  |  Usuario: {self.rep.usuario}  |  Emitido: {self.rep.emitido}")
        self.drawRightString(w - 15 * mm, 9 * mm, f"Página {self._pageNumber} de {total}")


def _cabecera(rep: ReporteDef, ancho: float):
    def dibujar(c: canvas.Canvas, doc):
        w, h = doc.pagesize
        c.saveState()
        c.setFillColor(AZUL)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(15 * mm, h - 14 * mm, rep.empresa[:70])
        c.setFont("Helvetica", 8)
        c.setFillColor(GRIS)
        if rep.nit:
            c.drawString(15 * mm, h - 18.5 * mm, f"NIT: {rep.nit}")
        if rep.direccion:
            c.drawString(15 * mm, h - 22.5 * mm, rep.direccion[:90])
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(AZUL)
        c.drawRightString(w - 15 * mm, h - 14 * mm, rep.gestion)
        c.setFont("Helvetica", 8)
        c.setFillColor(GRIS)
        c.drawRightString(w - 15 * mm, h - 18.5 * mm, f"Emitido: {rep.emitido}")
        c.setStrokeColor(AZUL)
        c.setLineWidth(1.2)
        c.line(15 * mm, h - 26 * mm, w - 15 * mm, h - 26 * mm)
        c.restoreState()
    return dibujar


def _fmt_celda(v, col: Col) -> str:
    if v is None or v == "":
        return ""
    if col.tipo == "money":
        return fmt(v, col.decimales)
    if col.tipo == "num":
        return fmt(v, col.decimales)
    if col.tipo == "int":
        return f"{int(v):,}".replace(",", ".")
    if col.tipo == "pct":
        return fmt(v, 2) + "%"
    return str(v)


def _tabla_flowable(t: Tabla, ancho_total: float, st: ParagraphStyle):
    pesos = [c.ancho for c in t.cols]
    anchos = [ancho_total * p / sum(pesos) for p in pesos]
    datos = []
    if not t.sin_encabezado:
        datos.append([Paragraph(f"<b>{c.titulo}</b>", ParagraphStyle("h", parent=st, textColor=colors.white, alignment=TA_CENTER, fontSize=7.8, leading=9.2)) for c in t.cols])
    for f in t.filas:
        fila = []
        for i, (v, c) in enumerate(zip(f.valores + [None] * (len(t.cols) - len(f.valores)), t.cols)):
            s = _fmt_celda(v, c)
            if c.tipo == "txt":
                sangria = "&nbsp;" * (f.nivel * 3) if i == 0 else ""
                s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if f.estilo in ("titulo", "total", "subtotal", "grupo"):
                    s = f"<b>{s}</b>"
                fila.append(Paragraph(sangria + s, st))
            else:
                if f.estilo in ("titulo", "total", "subtotal", "grupo") and s:
                    s = f"<b>{s}</b>"
                fila.append(Paragraph(s, ParagraphStyle("n", parent=st, alignment=2)))
        datos.append(fila)
    tb = Table(datos, colWidths=anchos, repeatRows=0 if t.sin_encabezado else 1)
    estilos = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
               ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E3E8EF"))]
    ini = 0
    if not t.sin_encabezado:
        estilos += [("BACKGROUND", (0, 0), (-1, 0), AZUL), ("VALIGN", (0, 0), (-1, 0), "MIDDLE")]
        ini = 1
    for i, f in enumerate(t.filas):
        r = i + ini
        if f.estilo == "titulo":
            estilos.append(("BACKGROUND", (0, r), (-1, r), AZUL_CLARO))
        elif f.estilo == "total":
            estilos += [("BACKGROUND", (0, r), (-1, r), AZUL_CLARO), ("LINEABOVE", (0, r), (-1, r), 0.9, AZUL)]
        elif f.estilo == "subtotal":
            estilos.append(("LINEABOVE", (0, r), (-1, r), 0.5, colors.HexColor("#8EA0B8")))
        elif f.estilo == "grupo":
            estilos.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
        elif i % 2 == 1:
            estilos.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    tb.setStyle(TableStyle(estilos))
    return tb


def generar_bytes(rep: ReporteDef) -> bytes:
    buf = io.BytesIO()
    pagina = landscape(A4) if rep.orientacion == "H" else A4
    margen = 15 * mm
    doc = SimpleDocTemplate(buf, pagesize=pagina, leftMargin=margen, rightMargin=margen, topMargin=31 * mm, bottomMargin=17 * mm,
                            title=rep.titulo, author="ContaBol", subject=rep.empresa)
    ancho = pagina[0] - 2 * margen
    base = getSampleStyleSheet()["Normal"]
    st = ParagraphStyle("c", parent=base, fontName="Helvetica", fontSize=7.8, leading=9.4)
    story = [Paragraph(f"<b>{rep.titulo.upper()}</b>", ParagraphStyle("t", parent=base, fontName="Helvetica-Bold", fontSize=14, textColor=AZUL, alignment=TA_CENTER, leading=17))]
    for linea in (rep.subtitulo, rep.periodo, rep.moneda):
        if linea:
            story.append(Paragraph(linea, ParagraphStyle("s", parent=base, fontSize=8.8, alignment=TA_CENTER, textColor=GRIS, leading=11)))
    story.append(Spacer(1, 5 * mm))
    for b in rep.bloques:
        if isinstance(b, Texto) and b.estilo == "salto":
            story.append(PageBreak())
        elif isinstance(b, Texto):
            e = ParagraphStyle("x", parent=st, fontSize=8.6, leading=11.5, alignment=TA_LEFT)
            txt = b.texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if b.estilo == "titulo":
                story += [Spacer(1, 3 * mm), Paragraph(f"<b>{txt}</b>", ParagraphStyle("xt", parent=e, fontSize=10, textColor=AZUL, leading=13)), Spacer(1, 1.5 * mm)]
            else:
                story += [Paragraph(txt, e), Spacer(1, 1.5 * mm)]
        else:
            if b.titulo:
                story.append(Paragraph(f"<b>{b.titulo}</b>", ParagraphStyle("tt", parent=st, fontSize=9.5, textColor=AZUL, spaceBefore=4, spaceAfter=3)))
            story.append(_tabla_flowable(b, ancho, st))
            story.append(Spacer(1, 4 * mm))
    for n in rep.notas:
        story.append(Paragraph(n.replace("&", "&amp;"), ParagraphStyle("n", parent=st, fontName="Helvetica-Oblique", textColor=GRIS, fontSize=7.5)))
    if rep.firmas:
        celdas = [[Paragraph(f"<br/><br/><br/>______________________________<br/><b>{f}</b>", ParagraphStyle("f", parent=st, alignment=TA_CENTER, fontSize=8.5, leading=11)) for f in rep.firmas]]
        story += [Spacer(1, 12 * mm), KeepTogether(Table(celdas, colWidths=[ancho / len(rep.firmas)] * len(rep.firmas)))]
    cab = _cabecera(rep, ancho)
    doc.build(story, onFirstPage=cab, onLaterPages=cab, canvasmaker=lambda *a, **k: _Numerado(*a, rep=rep, **k))
    return buf.getvalue()


def exportar(rep: ReporteDef, ruta: str) -> str:
    with open(ruta, "wb") as f:
        f.write(generar_bytes(rep))
    return ruta
