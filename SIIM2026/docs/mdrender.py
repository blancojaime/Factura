"""Mini-renderizador Markdown → PDF (reportlab) y DOCX (python-docx). Subconjunto: #, ##, ###, párrafos, listas, tablas, imágenes, notas (>), código, saltos (---pagina---)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle)

from siim.reports import engine as E

AZUL, GRIS, LINEA, CLARO = E.AZUL, E.GRIS, E.LINEA, E.AZUL_CLARO


def parse(md: str):
    lines, i, out = md.splitlines(), 0, []
    while i < len(lines):
        l = lines[i]
        if not l.strip():
            i += 1; continue
        if l.strip() == "---pagina---":
            out.append(("pb",)); i += 1; continue
        m = re.match(r"^(#{1,3})\s+(.*)", l)
        if m:
            out.append(("h" + str(len(m.group(1))), m.group(2).strip())); i += 1; continue
        if l.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append(("code", "\n".join(lines[i + 1:j]))); i = j + 1; continue
        m = re.match(r"^!\[(.*?)\]\((.*?)\)(\{w=(\d+)\})?", l.strip())
        if m:
            out.append(("img", m.group(1), m.group(2), int(m.group(4) or 150))); i += 1; continue
        if l.startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in lines[i:j] if not re.match(r"^\|\s*:?-{2,}", r)]
            out.append(("table", rows)); i = j; continue
        if l.startswith(">"):
            j = i
            buf = []
            while j < len(lines) and lines[j].startswith(">"):
                buf.append(lines[j].lstrip("> ").rstrip()); j += 1
            out.append(("note", " ".join(buf))); i = j; continue
        if re.match(r"^\s*[-*]\s+", l) or re.match(r"^\s*\d+\.\s+", l):
            ordered = bool(re.match(r"^\s*\d+\.", l))
            j, items = i, []
            while j < len(lines) and (re.match(r"^\s*[-*]\s+", lines[j]) or re.match(r"^\s*\d+\.\s+", lines[j]) or (lines[j].startswith("  ") and lines[j].strip() and items)):
                if re.match(r"^\s*([-*]|\d+\.)\s+", lines[j]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[j]))
                else:
                    items[-1] += " " + lines[j].strip()
                j += 1
            out.append(("ol" if ordered else "ul", items)); i = j; continue
        j, buf = i, []
        while j < len(lines) and lines[j].strip() and not re.match(r"^(#{1,3}\s|\||>|```|!\[|\s*[-*]\s|\s*\d+\.\s|---pagina---)", lines[j]):
            buf.append(lines[j].strip()); j += 1
        out.append(("p", " ".join(buf))); i = j
    return out


def inline_rl(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", lambda m: f"<font name='Courier' color='#1F3A5F'>{m.group(1)}</font>", t)
    t = re.sub(r"\[(.+?)\]\((https?://.+?)\)", r"<link href='\2' color='#2F5D8A'><u>\1</u></link>", t)
    return t


def to_pdf(md, path, titulo, subtitulo="", base=Path("."), portada=True):
    E.setup_fonts()
    f, fb = E.FONT, E.FONT_B
    S = dict(
        p=ParagraphStyle("p", fontName=f, fontSize=9.6, leading=13.4, alignment=TA_JUSTIFY, spaceAfter=5),
        h1=ParagraphStyle("h1", fontName=fb, fontSize=17, leading=21, textColor=AZUL, spaceBefore=6, spaceAfter=8),
        h2=ParagraphStyle("h2", fontName=fb, fontSize=12.5, leading=16, textColor=AZUL, spaceBefore=10, spaceAfter=4),
        h3=ParagraphStyle("h3", fontName=fb, fontSize=10.3, leading=14, textColor=colors.HexColor("#2F5D8A"), spaceBefore=7, spaceAfter=3),
        li=ParagraphStyle("li", fontName=f, fontSize=9.6, leading=13, spaceAfter=1.5),
        note=ParagraphStyle("note", fontName=f, fontSize=9, leading=12.5, textColor=colors.HexColor("#33415A")),
        cell=ParagraphStyle("cell", fontName=f, fontSize=8.2, leading=10.4), cellb=ParagraphStyle("cellb", fontName=fb, fontSize=8.2, leading=10.4, textColor=colors.white),
        code=ParagraphStyle("code", fontName="Courier", fontSize=8, leading=10, backColor=colors.HexColor("#F1F4F8"), borderPadding=5, spaceAfter=6))
    W = A4[0] - 36 * mm
    el = []
    toc = []
    for b in parse(md):
        k = b[0]
        if k == "pb":
            continue                       # los saltos de página los controlan los títulos de nivel 1
        elif k in ("h1", "h2", "h3"):
            st = S[k]
            if k == "h1" and el:
                el.append(PageBreak())
            para = Paragraph(inline_rl(b[1]), st)
            para._bookmark = f"b{len(toc)}"
            el.append(para)
            if k != "h3":
                toc.append((k, b[1]))
        elif k == "p":
            el.append(Paragraph(inline_rl(b[1]), S["p"]))
        elif k in ("ul", "ol"):
            el.append(ListFlowable([ListItem(Paragraph(inline_rl(x), S["li"]), leftIndent=14) for x in b[1]], bulletType="bullet" if k == "ul" else "1", bulletFontName=f, bulletFontSize=8, leftIndent=14, spaceAfter=4,
                                   start="•" if k == "ul" else None))
        elif k == "note":
            t = Table([[Paragraph(inline_rl(b[1]), S["note"])]], colWidths=[W])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CLARO), ("LINEBEFORE", (0, 0), (0, -1), 3, AZUL), ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            el += [t, Spacer(1, 5)]
        elif k == "code":
            el.append(Preformatted(b[1], S["code"]))
        elif k == "img":
            p = (base / b[2])
            if p.exists():
                from PIL import Image as PI
                w, h = PI.open(p).size
                tw = min(W, b[3] * mm * 1.0)
                el.append(KeepTogether([Image(str(p), width=tw, height=tw * h / w), Paragraph(f"<i>{inline_rl(b[1])}</i>", ParagraphStyle("cap", parent=S["note"], fontSize=8, textColor=GRIS, alignment=1, spaceAfter=7))]))
        elif k == "table":
            rows = b[1]
            n = len(rows[0])
            data = [[Paragraph(inline_rl(c), S["cellb"] if r == 0 else S["cell"]) for c in row] + [""] * (n - len(row)) for r, row in enumerate(rows)]
            lens = [max(len(re.sub(r"[*`]", "", row[i])) if i < len(row) else 0 for row in rows) for i in range(n)]
            wts = [min(max(l, 13), 60) for l in lens]
            cw = [W * w / sum(wts) for w in wts]
            t = Table(data, colWidths=cw, repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), AZUL), ("GRID", (0, 0), (-1, -1), 0.25, LINEA), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FB")]),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            el += [t, Spacer(1, 6)]

    class Doc(SimpleDocTemplate):
        def afterFlowable(self, fl):
            if isinstance(fl, Paragraph) and getattr(fl, "_bookmark", None) and fl.style.name in ("h1", "h2"):
                key = fl._bookmark
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(fl.getPlainText(), key, 0 if fl.style.name == "h1" else 1, False)

    def deco(c, d):
        c.saveState()
        c.setFont(f, 7.5); c.setFillColor(GRIS)
        c.drawString(18 * mm, 10 * mm, titulo.replace("\n", " "))
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {d.page}")
        c.setStrokeColor(LINEA); c.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
        c.restoreState()

    def cover(c, d):
        c.saveState()
        c.setFillColor(AZUL); c.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#F2C14E")); c.rect(0, A4[1] * 0.42, A4[0], 4, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(fb, 44); c.drawString(24 * mm, A4[1] * 0.64, "SIIM 2026")
        c.setFont(f, 14); c.drawString(24 * mm, A4[1] * 0.64 - 12 * mm, "Sistema Integrado de Ingresos Municipales")
        y = A4[1] * 0.42 - 18 * mm
        c.setFont(fb, 22)
        for ln in titulo.split("\n"):
            c.drawString(24 * mm, y, ln); y -= 10 * mm
        c.setFont(f, 11); c.setFillColor(colors.HexColor("#C9D6E6"))
        for ln in subtitulo.split("\n"):
            c.drawString(24 * mm, y - 2 * mm, ln); y -= 6 * mm
        c.restoreState()

    doc = Doc(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=20 * mm, title=titulo.replace("\n", " "), author="SIIM 2026")
    story = ([Spacer(1, 1), PageBreak()] if portada else []) + el
    doc.build(story, onFirstPage=cover if portada else deco, onLaterPages=deco)
    return path


def to_docx(md, path, titulo, base=Path(".")):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin = s.right_margin = Cm(2); s.top_margin = s.bottom_margin = Cm(2)
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
    for n, sz in (("Heading 1", 18), ("Heading 2", 14), ("Heading 3", 11.5)):
        h = d.styles[n]; h.font.name = "Calibri"; h.font.size = Pt(sz); h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F); h.font.bold = True
    t = d.add_paragraph(); r = t.add_run("SIIM 2026"); r.font.size = Pt(34); r.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    t = d.add_paragraph(); r = t.add_run("Sistema Integrado de Ingresos Municipales"); r.font.size = Pt(14)
    t = d.add_paragraph(); r = t.add_run(titulo.replace("\n", " – ")); r.font.size = Pt(20); r.bold = True
    d.add_page_break()

    def runs(par, text):
        for part in re.split(r"(\*\*.+?\*\*|`.+?`|\[.+?\]\(https?://.+?\))", text):
            if part.startswith("**"):
                r = par.add_run(part[2:-2]); r.bold = True
            elif part.startswith("`"):
                r = par.add_run(part[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(9.5)
            elif part.startswith("["):
                m = re.match(r"\[(.+?)\]\((.+?)\)", part)
                r = par.add_run(f"{m.group(1)} ({m.group(2)})") if m else par.add_run(part)
            else:
                par.add_run(re.sub(r"(?<![\w*])\*(.+?)\*(?![\w*])", r"\1", part))

    def shade(cell, color):
        tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
        sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), color); tcPr.append(sh)

    for b in parse(md):
        k = b[0]
        if k == "pb":
            d.add_page_break()
        elif k in ("h1", "h2", "h3"):
            if k == "h1" and len(d.paragraphs) > 4:
                d.add_page_break()
            d.add_heading(re.sub(r"[*`]", "", b[1]), int(k[1]))
        elif k == "p":
            runs(d.add_paragraph(), b[1])
        elif k in ("ul", "ol"):
            for x in b[1]:
                runs(d.add_paragraph(style="List Bullet" if k == "ul" else "List Number"), x)
        elif k == "note":
            tb = d.add_table(rows=1, cols=1); c = tb.rows[0].cells[0]; shade(c, "E8EEF5"); c.paragraphs[0].text = ""; runs(c.paragraphs[0], b[1])
            d.add_paragraph()
        elif k == "code":
            p = d.add_paragraph(); r = p.add_run(b[1]); r.font.name = "Consolas"; r.font.size = Pt(9)
        elif k == "img":
            pth = base / b[2]
            if pth.exists():
                d.add_picture(str(pth), width=Cm(min(17, b[3] / 10)))
                d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                c = d.add_paragraph(); r = c.add_run(b[1]); r.italic = True; r.font.size = Pt(8.5); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif k == "table":
            rows = b[1]; n = max(len(r) for r in rows)
            tb = d.add_table(rows=len(rows), cols=n); tb.style = "Table Grid"
            for i, row in enumerate(rows):
                for j in range(n):
                    c = tb.rows[i].cells[j]; c.paragraphs[0].text = ""
                    txt = row[j] if j < len(row) else ""
                    if i == 0:
                        shade(c, "1F3A5F"); r = c.paragraphs[0].add_run(re.sub(r"[*`]", "", txt)); r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255); r.font.size = Pt(9)
                    else:
                        runs(c.paragraphs[0], txt)
                        for r in c.paragraphs[0].runs:
                            r.font.size = Pt(9)
            d.add_paragraph()
    d.save(str(path))
    return path
