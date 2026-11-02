"""Utilidades para generar los manuales en Word (python-docx) con imágenes reales anotadas."""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from PIL import Image, ImageDraw, ImageFont

AZUL = RGBColor(0x14, 0x30, 0x4F); DORADO = RGBColor(0xB8, 0x96, 0x3C); GRIS = RGBColor(0x55, 0x5F, 0x6B)
ROJO = (214, 69, 69)

def anotar(src, dst, cajas):
    """cajas: [(x0,y0,x1,y1,'n')...] en píxeles de la captura recortada. Dibuja marco rojo y número."""
    im = Image.open(src).convert("RGB"); d = ImageDraw.Draw(im)
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception: f = ImageFont.load_default()
    for (x0, y0, x1, y1, n) in cajas:
        d.rectangle((x0, y0, x1, y1), outline=ROJO, width=3)
        r = 15; cx, cy = x0 - 2, y0 - 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ROJO, outline=(255, 255, 255), width=2)
        d.text((cx, cy), str(n), fill=(255, 255, 255), font=f, anchor="mm")
    im.save(dst); return dst

def _shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hex_); tcPr.append(sh)

def _field(run, instr):
    for t, txt in (("begin", None), (None, instr), ("end", None)):
        if t:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), t); run._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; run._r.append(e)

class Manual:
    def __init__(self, titulo, subtitulo, version, fecha):
        self.d = Document(); self.titulo = titulo; self.fig = 0
        s = self.d.sections[0]; s.page_width = Cm(21); s.page_height = Cm(29.7)
        s.left_margin = s.right_margin = Cm(2); s.top_margin = Cm(2.2); s.bottom_margin = Cm(2)
        st = self.d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri"); st.paragraph_format.space_after = Pt(6)
        for n, sz, col in (("Heading 1", 18, AZUL), ("Heading 2", 14, AZUL), ("Heading 3", 11.5, DORADO)):
            h = self.d.styles[n]; h.font.name = "Calibri"; h.font.size = Pt(sz); h.font.bold = True; h.font.color.rgb = col
            h.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri"); h.paragraph_format.space_before = Pt(14 if n != "Heading 3" else 10)
        self._portada(titulo, subtitulo, version, fecha)
        self._pie()

    def _portada(self, titulo, subtitulo, version, fecha):
        for _ in range(6): self.d.add_paragraph()
        p = self.d.add_paragraph(); r = p.add_run("ComexBol Pro"); r.font.size = Pt(40); r.bold = True; r.font.color.rgb = AZUL
        p = self.d.add_paragraph(); r = p.add_run(titulo); r.font.size = Pt(26); r.font.color.rgb = DORADO
        p = self.d.add_paragraph(); r = p.add_run(subtitulo); r.font.size = Pt(13); r.font.color.rgb = GRIS
        for _ in range(8): self.d.add_paragraph()
        p = self.d.add_paragraph(); r = p.add_run(f"Versión {version} · {fecha}"); r.font.size = Pt(11); r.font.color.rgb = GRIS
        p = self.d.add_paragraph(); r = p.add_run("Herramienta de apoyo a la decisión, el seguimiento y la documentación de importaciones en Bolivia. "
            "No sustituye el criterio del despachante de aduana ni la normativa vigente."); r.italic = True; r.font.size = Pt(9.5); r.font.color.rgb = GRIS
        self.d.add_page_break()

    def _pie(self):
        sec = self.d.sections[0]
        hp = sec.header.paragraphs[0]; hp.text = f"ComexBol Pro — {self.titulo}"; hp.runs[0].font.size = Pt(8.5); hp.runs[0].font.color.rgb = GRIS
        fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("Página "); r.font.size = Pt(8.5)
        r2 = fp.add_run(); r2.font.size = Pt(8.5); _field(r2, "PAGE")

    def contenido(self, items):
        self.h1("Contenido")
        for i, t in enumerate(items, 1):
            p = self.d.add_paragraph(f"{i}.  {t}"); p.paragraph_format.space_after = Pt(2)
        self.d.add_page_break()

    def h1(self, t): self.d.add_heading(t, 1)
    def h2(self, t): self.d.add_heading(t, 2)
    def h3(self, t): self.d.add_heading(t, 3)
    def p(self, t, bold=False, italic=False):
        para = self.d.add_paragraph(); self._runs(para, t, bold, italic); return para
    def _runs(self, para, t, bold=False, italic=False):
        # **negrita** simple
        partes = t.split("**")
        for i, x in enumerate(partes):
            if not x: continue
            r = para.add_run(x); r.bold = bold or (i % 2 == 1); r.italic = italic
    def bullets(self, items, num=False):
        for i, t in enumerate(items, 1):
            para = self.d.add_paragraph(); pf = para.paragraph_format
            pf.left_indent = Cm(0.9); pf.first_line_indent = Cm(-0.6); pf.space_after = Pt(3)
            para.add_run(f"{i}.  " if num else "•  ").bold = num
            self._runs(para, t)
    def code(self, txt):
        para = self.d.add_paragraph(); r = para.add_run(txt); r.font.name = "Consolas"; r.font.size = Pt(9)
        para.paragraph_format.left_indent = Cm(0.5)
        pPr = para._p.get_or_add_pPr(); sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "F0F2F5"); pPr.append(sh)
    def caja(self, titulo, texto, color="FFF4D6"):
        t = self.d.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER; c = t.rows[0].cells[0]; _shade(c, color)
        c.paragraphs[0].text = ""; r = c.paragraphs[0].add_run(titulo + "  "); r.bold = True; r.font.color.rgb = AZUL
        self._runs(c.paragraphs[0], texto); self.d.add_paragraph().paragraph_format.space_after = Pt(2)
    def tabla(self, filas, anchos=None, encabezado=True, tam=9.5):
        t = self.d.add_table(rows=len(filas), cols=len(filas[0])); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        if anchos:
            t.autofit = False
            tblPr = t._tbl.tblPr; lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
            for j, w in enumerate(anchos): t.columns[j].width = Cm(w)
        for i, fila in enumerate(filas):
            for j, val in enumerate(fila):
                c = t.rows[i].cells[j]; c.paragraphs[0].text = ""; para = c.paragraphs[0]; self._runs(para, str(val))
                for r in para.runs:
                    r.font.size = Pt(tam)
                    if encabezado and i == 0: r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
                if encabezado and i == 0: _shade(c, "14304F")
                elif i % 2 == 0: _shade(c, "F5F7FA")
                if anchos: c.width = Cm(anchos[j])
        self.d.add_paragraph().paragraph_format.space_after = Pt(2); return t
    def figura(self, ruta, leyenda, ancho=17):
        if not os.path.exists(ruta):
            self.p(f"[Falta la captura {os.path.basename(ruta)}]", italic=True); return
        self.fig += 1
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(ruta, width=Cm(ancho))
        c = self.d.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(f"Figura {self.fig}. {leyenda}"); r.italic = True; r.font.size = Pt(9); r.font.color.rgb = GRIS
    def salto(self): self.d.add_page_break()
    def guardar(self, ruta): self.d.save(ruta)
