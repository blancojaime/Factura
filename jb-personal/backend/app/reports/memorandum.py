"""Memorándum en PDF (reportlab) y Word editable (python-docx), con el diseño de los modelos del municipio."""
from __future__ import annotations

import io
import re
from xml.sax.saxutils import escape

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, Image, KeepTogether, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

from ..models import Entidad, MemoConfig, Memorandum
from ..services.memos import fecha_larga

TINTA = colors.HexColor("#8A3B12")
GRIS = colors.HexColor("#555555")


def bloques(cuerpo: str):
    """('p'|'h'|'ul', contenido) a partir del texto con marcas: **negrita**, '## ' titulo centrado, '- ' viñetas."""
    out = []
    for b in re.split(r"\n\s*\n", cuerpo.strip()):
        lineas = [l.rstrip() for l in b.split("\n") if l.strip()]
        if not lineas:
            continue
        if lineas[0].startswith("## "):
            out.append(("h", lineas[0][3:]))
        elif all(l.startswith("- ") for l in lineas):
            out.append(("ul", [l[2:] for l in lineas]))
        else:
            out.append(("p", lineas))
    return out


def _ctx(m: Memorandum, ent: Entidad, cfg: MemoConfig):
    firmante = m.firmante_nombre or cfg.firmante_nombre or ent.mae_nombre
    cargo_f = m.firmante_cargo or cfg.firmante_cargo or ent.mae_cargo
    return {
        "entidad": ent.nombre, "lineas": [l for l in cfg.encabezado.splitlines() if l.strip()] or ["ESTADO PLURINACIONAL DE BOLIVIA"],
        "lema": cfg.lema, "pie": [l for l in cfg.pie.splitlines() if l.strip()] or ([ent.direccion] if ent.direccion else []),
        "cite": f"CITE: {m.cite}" if m.cite else "CITE: S/N (BORRADOR — el número se asigna al emitir)",
        "de_nombre": firmante, "de_cargo": cargo_f, "lugar_fecha": f"{ent.ciudad + ', ' if ent.ciudad else ''}{fecha_larga(m.fecha)}",
        "para": m.destinatario, "ci": m.destinatario_ci, "ref": m.referencia, "firmante": firmante, "firmante_cargo": cargo_f,
        "recibido": (f"Recibido: {m.recibido_fecha:%d/%m/%Y}" + (f" — {m.recibido_por}" if m.recibido_por else "")) if m.recibido_fecha else "",
        "marca": "ANULADO" if m.estado == "ANULADO" else ("BORRADOR" if m.estado == "BORRADOR" else ""),
    }


def _inline(t: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escape(t))


# ----------------------------------------------------------------------------- PDF
def pdf(m: Memorandum, ent: Entidad, cfg: MemoConfig) -> bytes:
    c = _ctx(m, ent, cfg)
    buf = io.BytesIO()
    W, H = LETTER
    st = lambda n, **k: ParagraphStyle(n, fontName=k.pop("fontName", "Helvetica"), **k)  # noqa: E731
    normal = st("n", fontSize=10, leading=13.4, alignment=TA_JUSTIFY, spaceAfter=5)
    centro = st("c", fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=GRIS)

    def pagina(canv, doc):
        canv.saveState()
        if c["marca"]:
            canv.setFont("Helvetica-Bold", 90)
            canv.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.45))
            canv.translate(W / 2, H / 2)
            canv.rotate(40)
            canv.drawCentredString(0, 0, c["marca"])
            canv.restoreState()
            canv.saveState()
        canv.setStrokeColor(TINTA)
        canv.setLineWidth(3)
        canv.line(1.6 * cm, 3.05 * cm, W - 1.6 * cm, 3.05 * cm)
        canv.setLineWidth(0.8)
        canv.line(1.6 * cm, 2.9 * cm, W - 1.6 * cm, 2.9 * cm)
        y = 2.35 * cm
        if c["lema"]:
            canv.setFont("Helvetica-BoldOblique", 11)
            canv.setFillColor(TINTA)
            canv.drawCentredString(W / 2, y, c["lema"])
            y -= 0.42 * cm
        canv.setFont("Helvetica", 8.5)
        canv.setFillColor(GRIS)
        for l in c["pie"][:3]:
            canv.drawCentredString(W / 2, y, l)
            y -= 0.36 * cm
        canv.restoreState()

    doc = BaseDocTemplate(buf, pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.2 * cm, bottomMargin=3.3 * cm,
                          title=m.cite or "Memorándum (borrador)", author=ent.nombre)
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(2 * cm, 3.3 * cm, W - 4 * cm, H - 4.5 * cm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=pagina)])
    el = []
    # membrete: logo + nombre de la entidad + líneas
    nombre = Paragraph(f"<font color='#8A3B12'><b><i>{escape(ent.nombre)}</i></b></font>", st("e", fontSize=17, leading=20, alignment=TA_CENTER))
    lineas = [nombre, HRFlowable(width="100%", thickness=2.5, color=TINTA, spaceBefore=2, spaceAfter=3)] + [
        Paragraph(f"<b>{escape(l)}</b>", st("l", fontSize=8.5, leading=10.5, alignment=TA_CENTER)) for l in c["lineas"]]
    logo = ""
    if cfg.logo:
        try:
            iw, ih = ImageReader(io.BytesIO(cfg.logo)).getSize()
            alto = 2.3 * cm
            logo = Image(io.BytesIO(cfg.logo), width=alto * iw / ih, height=alto)
        except Exception:
            logo = ""
    cab = Table([[logo, lineas]], colWidths=[3.4 * cm, W - 4 * cm - 3.4 * cm])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    el += [cab, Spacer(1, 6)]
    caja = Table([[Paragraph("<b>M E M O R Á N D U M</b>", st("t", fontSize=16, leading=20, alignment=TA_CENTER, textColor=colors.HexColor("#3A2A1E")))]], colWidths=[W - 4 * cm])
    caja.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, GRIS), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    el += [caja, Spacer(1, 8), Paragraph(f"<b>{escape(c['cite'])}</b>", st("ci", fontSize=10.5, leading=14, alignment=TA_CENTER))]
    if c["recibido"]:
        el.append(Paragraph(f"<i>{escape(c['recibido'])}</i>", st("r", fontSize=9, leading=11, alignment=TA_RIGHT, textColor=TINTA)))
    el.append(Spacer(1, 8))
    de = [Paragraph(f"<b>{escape(c['de_nombre'])}</b>", st("d1", fontSize=10, leading=13, alignment=TA_CENTER)),
          Paragraph(f"<b>{escape(c['de_cargo'].upper())}<br/>{escape(ent.nombre.upper())}</b>", st("d2", fontSize=9.5, leading=12, alignment=TA_CENTER)),
          Spacer(1, 6), Paragraph(f"<b>{escape(c['lugar_fecha'])}</b>", st("d3", fontSize=10, leading=13, alignment=TA_CENTER))]
    para = [Paragraph("<b>AL SEÑOR (A):</b>", st("p1", fontSize=10, leading=13)), Spacer(1, 6),
            Paragraph(f"<b>{escape(c['para'].upper())}</b>", st("p2", fontSize=11, leading=14, alignment=TA_CENTER)),
            Paragraph(f"<b>C.I. {escape(c['ci'])}</b>" if c["ci"] else "", st("p3", fontSize=10, leading=13, alignment=TA_CENTER)),
            Paragraph("<b>Presente.-</b>", st("p4", fontSize=10, leading=13))]
    dp = Table([[de, para]], colWidths=[(W - 4 * cm) / 2] * 2)
    dp.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEAFTER", (0, 0), (0, 0), 1.2, colors.HexColor("#3A2A1E")),
                            ("LEFTPADDING", (1, 0), (1, 0), 10), ("LINEBELOW", (0, 0), (-1, 0), 0.8, GRIS), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    el += [dp, Spacer(1, 4), Paragraph(f"<u><b>REF.- {escape(c['ref'])}</b></u>", st("rf", fontSize=10.5, leading=14, alignment=TA_RIGHT)), Spacer(1, 6)]
    for tipo, cont in bloques(m.cuerpo):
        if tipo == "p":
            el.append(Paragraph("<br/>".join(_inline(l) for l in cont), normal))
        elif tipo == "h":
            el.append(Paragraph(f"<u><b>{_inline(cont)}</b></u>", st("h", fontSize=12.5, leading=16, alignment=TA_CENTER, spaceBefore=2, spaceAfter=6)))
        else:
            for it in cont:
                el.append(Paragraph(f"•&nbsp;&nbsp;{_inline(it)}", st("b", fontSize=10, leading=13.4, leftIndent=22, firstLineIndent=-10, spaceAfter=1)))
            el.append(Spacer(1, 6))
    firma = KeepTogether([Spacer(1, 26), Table([[None, [Paragraph("_____________________________", st("f0", fontSize=10, alignment=TA_CENTER)),
                          Paragraph(f"<b>{escape(c['firmante'])}</b>", st("f1", fontSize=10, leading=12, alignment=TA_CENTER)),
                          Paragraph(f"<b>{escape(c['firmante_cargo'].upper())}</b><br/>{escape(ent.nombre)}", st("f2", fontSize=9, leading=11, alignment=TA_CENTER, textColor=TINTA))]]],
                         colWidths=[(W - 4 * cm) * 0.38, (W - 4 * cm) * 0.62])])
    el.append(firma)
    doc.build(el)
    return buf.getvalue()


# ----------------------------------------------------------------------------- Word
def _sombra(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), color)
    tcPr.append(sh)


def _runs(p, texto, size=10.5, color=None, italic=False):
    for i, parte in enumerate(re.split(r"\*\*", texto)):
        if parte:
            r = p.add_run(parte)
            r.bold, r.italic, r.font.size = i % 2 == 1, italic, Pt(size)
            if color:
                r.font.color.rgb = color


def word(m: Memorandum, ent: Entidad, cfg: MemoConfig) -> bytes:
    c = _ctx(m, ent, cfg)
    d = docx.Document()
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21.59), Cm(27.94)
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin, s.bottom_margin = Cm(1.5), Cm(2.4)
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(10.5)
    marron = RGBColor(0x8A, 0x3B, 0x12)

    cab = d.add_table(rows=1, cols=2)
    cab.alignment = WD_TABLE_ALIGNMENT.CENTER
    cab.columns[0].width, cab.columns[1].width = Cm(3.4), Cm(14.2)
    if cfg.logo:
        try:
            cab.rows[0].cells[0].paragraphs[0].add_run().add_picture(io.BytesIO(cfg.logo), height=Cm(2.4))
        except Exception:
            pass
    cel = cab.rows[0].cells[1]
    p = cel.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(ent.nombre)
    r.bold, r.italic, r.font.size, r.font.color.rgb = True, True, Pt(18), marron
    for l in c["lineas"]:
        q = cel.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        q.paragraph_format.space_after = Pt(0)
        rr = q.add_run(l)
        rr.bold, rr.font.size = True, Pt(8.5)
    t = d.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    q = t.rows[0].cells[0].paragraphs[0]
    q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = q.add_run("M E M O R Á N D U M")
    r.bold, r.font.size = True, Pt(16)
    q = d.add_paragraph()
    q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = q.add_run(c["cite"])
    r.bold = True
    if c["recibido"]:
        q = d.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = q.add_run(c["recibido"])
        r.italic, r.font.color.rgb, r.font.size = True, marron, Pt(9)
    dp = d.add_table(rows=1, cols=2)
    izq, der = dp.rows[0].cells
    for i, (txt, sz) in enumerate([(c["de_nombre"], 10), (c["de_cargo"].upper() + "\n" + ent.nombre.upper(), 9.5), (c["lugar_fecha"], 10)]):
        q = izq.paragraphs[0] if i == 0 else izq.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = q.add_run(txt)
        rr.bold, rr.font.size = True, Pt(sz)
    for i, (txt, sz, al) in enumerate([("AL SEÑOR (A):", 10, 0), (c["para"].upper(), 11, 1), ("C.I. " + c["ci"] if c["ci"] else "", 10, 1), ("Presente.-", 10, 0)]):
        q = der.paragraphs[0] if i == 0 else der.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER if al else WD_ALIGN_PARAGRAPH.LEFT
        rr = q.add_run(txt)
        rr.bold, rr.font.size = True, Pt(sz)
    q = d.add_paragraph()
    q.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = q.add_run("REF.- " + c["ref"])
    r.bold, r.underline = True, True
    for tipo, cont in bloques(m.cuerpo):
        if tipo == "p":
            q = d.add_paragraph()
            q.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            for i, l in enumerate(cont):
                if i:
                    q.add_run().add_break()
                _runs(q, l)
        elif tipo == "h":
            q = d.add_paragraph()
            q.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = q.add_run(re.sub(r"\*\*", "", cont))
            r.bold, r.underline, r.font.size = True, True, Pt(13)
        else:
            for it in cont:
                q = d.add_paragraph(style="List Bullet")
                _runs(q, it)
    d.add_paragraph()
    for i, (txt, b) in enumerate([("_____________________________", False), (c["firmante"], True), (c["firmante_cargo"].upper(), True), (ent.nombre, False)]):
        q = d.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        q.paragraph_format.space_after = Pt(0)
        rr = q.add_run(txt)
        rr.bold, rr.font.size = b, Pt(9.5)
    pie = s.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if c["lema"]:
        r = pie.add_run(c["lema"] + "\n")
        r.bold, r.italic, r.font.color.rgb = True, True, marron
    r = pie.add_run("\n".join(c["pie"]))
    r.font.size = Pt(8.5)
    out = io.BytesIO()
    d.save(out)
    return out.getvalue()
