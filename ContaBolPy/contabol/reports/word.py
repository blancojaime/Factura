"""Exportación a Word (.docx) de cualquier informe (texto y tablas), para editarlo o incorporarlo a otros documentos."""
from __future__ import annotations

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from ..util import fdate, fmt
from .engine import ReporteDef, Tabla, Texto

AZUL = RGBColor(0x1F, 0x3A, 0x5F)


def _sombrear(celda, color: str) -> None:
    tc = celda._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), color)
    tc.append(sh)


def _valor(v, tipo: str, dec: int) -> str:
    if v is None or v == "":
        return ""
    if tipo in ("money", "num"):
        return fmt(v, dec) if isinstance(v, (int, float)) else str(v)
    if tipo == "int":
        return f"{int(v):,}".replace(",", ".") if isinstance(v, (int, float)) else str(v)
    if tipo == "pct":
        return fmt(v, 2) + " %" if isinstance(v, (int, float)) else str(v)
    if tipo == "date":
        try:
            return fdate(v)
        except Exception:  # noqa: BLE001
            return str(v)
    return str(v)


def _parrafo(doc, texto: str, negrita=False, tam=10, color=None, centro=False, cursiva=False, espacio=4):
    p = doc.add_paragraph()
    r = p.add_run(texto)
    r.bold, r.italic = negrita, cursiva
    r.font.size = Pt(tam)
    if color is not None:
        r.font.color.rgb = color
    if centro:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(espacio)
    return p


def _tabla(doc, t: Tabla) -> None:
    if t.titulo:
        _parrafo(doc, t.titulo, True, 10.5, AZUL, espacio=2)
    n = len(t.cols)
    tb = doc.add_table(rows=0 if t.sin_encabezado else 1, cols=n)
    tb.style = "Table Grid"
    tb.alignment = WD_TABLE_ALIGNMENT.CENTER
    if not t.sin_encabezado:
        for i, c in enumerate(t.cols):
            cel = tb.rows[0].cells[i]
            cel.text = ""
            r = cel.paragraphs[0].add_run(c.titulo)
            r.bold = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            _sombrear(cel, "1F3A5F")
            if c.tipo in ("money", "num", "int", "pct"):
                cel.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for f in t.filas:
        fila = tb.add_row()
        for i, c in enumerate(t.cols):
            v = f.valores[i] if i < len(f.valores) else None
            txt = _valor(v, c.tipo, c.decimales)
            if i == 0 and f.nivel:
                txt = "    " * f.nivel + txt
            cel = fila.cells[i]
            cel.text = ""
            r = cel.paragraphs[0].add_run(txt)
            r.font.size = Pt(8.5)
            if f.estilo in ("titulo", "grupo", "subtotal", "total"):
                r.bold = True
            if f.estilo == "titulo":
                _sombrear(cel, "DEE7F3")
            elif f.estilo == "total":
                _sombrear(cel, "E9EEF6")
            if c.tipo in ("money", "num", "int", "pct"):
                cel.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def exportar(rep: ReporteDef, ruta: str) -> str:
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10)
    sec = doc.sections[0]
    if rep.orientacion == "H":
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for lado in ("left_margin", "right_margin"):
        setattr(sec, lado, Cm(1.8))
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    _parrafo(doc, rep.empresa, True, 13, AZUL, espacio=0)
    _parrafo(doc, " · ".join(x for x in (f"NIT {rep.nit}" if rep.nit else "", rep.direccion, rep.gestion) if x), False, 8.5, RGBColor(0x6C, 0x75, 0x7D))
    _parrafo(doc, rep.titulo.upper(), True, 14, AZUL, centro=True, espacio=2)
    for x in (rep.subtitulo, rep.periodo, rep.moneda):
        if x:
            _parrafo(doc, x, False, 9.5, centro=True, espacio=0)
    doc.add_paragraph()
    for b in rep.bloques:
        if isinstance(b, Texto):
            if b.estilo == "salto":
                doc.add_page_break()
            elif b.estilo == "titulo":
                _parrafo(doc, b.texto, True, 11, AZUL, espacio=2)
            elif b.estilo == "nota":
                _parrafo(doc, b.texto, False, 9, RGBColor(0x55, 0x5F, 0x6B), cursiva=True)
            else:
                for par in (b.texto or "").split("\n"):
                    _parrafo(doc, par, False, 10, espacio=3)
        elif isinstance(b, Tabla):
            _tabla(doc, b)
    for nota in rep.notas:
        _parrafo(doc, nota, False, 8.5, RGBColor(0x55, 0x5F, 0x6B), cursiva=True)
    if rep.firmas:
        doc.add_paragraph()
        ft = doc.add_table(rows=2, cols=len(rep.firmas))
        for i, nombre in enumerate(rep.firmas):
            ft.rows[0].cells[i].text = "\n\n______________________________"
            ft.rows[1].cells[i].text = nombre
            for fila in ft.rows:
                fila.cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _parrafo(doc, f"Emitido: {rep.emitido} · Usuario: {rep.usuario}", False, 8, RGBColor(0x6C, 0x75, 0x7D))
    doc.save(ruta)
    return ruta


def exportar_texto(titulo: str, texto: str, ruta: str, ctx=None) -> str:
    """Documento Word a partir de un texto libre (p. ej. un dictamen editado en pantalla)."""
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    if ctx is not None:
        _parrafo(doc, ctx.empresa["razon_social"], True, 13, AZUL, espacio=0)
        _parrafo(doc, f"NIT {ctx.empresa.get('nit') or 's/n'} · Gestión {ctx.gestion['anio']}", False, 9, RGBColor(0x6C, 0x75, 0x7D))
    _parrafo(doc, titulo.upper(), True, 14, AZUL, centro=True)
    for par in texto.split("\n"):
        _parrafo(doc, par, False, 11, espacio=4)
    doc.save(ruta)
    return ruta
