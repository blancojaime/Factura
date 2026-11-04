"""Biblioteca de diapositivas del taller (python-pptx): mismo diseño para los tres módulos."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from PIL import Image

IMG = '/home/user/Factura/sigaa/docs/fuentes/img/'
def rgb(h): return RGBColor.from_string(h.lstrip('#'))
VERDE, OSCURO, CLARO, AMBAR, ROJO, TEXTO, GRIS, BLANCO = '4F7A1E', '243B0F', 'EEF4E4', 'E0A526', 'B3261E', '1F2A1A', '5B6670', 'FFFFFF'
W, H = 13.333, 7.5

class Deck:
    def __init__(self, modulo_corto):
        self.p = Presentation(); self.p.slide_width = Inches(W); self.p.slide_height = Inches(H)
        self.modulo = modulo_corto; self.n = 0

    # ---- primitivas
    def _slide(self, notas=''):
        s = self.p.slides.add_slide(self.p.slide_layouts[6]); self.n += 1
        if notas: s.notes_slide.notes_text_frame.text = notas
        return s
    def _rect(self, s, x, y, w, h, color, shape=MSO_SHAPE.RECTANGLE, line=None):
        r = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h)); r.fill.solid(); r.fill.fore_color.rgb = rgb(color)
        if line: r.line.color.rgb = rgb(line); r.line.width = Pt(1)
        else: r.line.fill.background()
        r.shadow.inherit = False
        return r
    def _text(self, s, x, y, w, h, txt, size=18, bold=False, color=TEXTO, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font='Calibri'):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.03)
        lines = txt if isinstance(txt, list) else [txt]
        for i, l in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align
            r = p.add_run(); r.text = l.replace('`', ''); r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = rgb(color); r.font.name = font
        return tb
    def _bullets(self, s, x, y, w, h, items, size=20, color=TEXTO):
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
        first = True
        for it in items:
            sub = isinstance(it, tuple); txt = it[0] if sub else it
            p = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
            p.space_after = Pt(7 if not sub else 3)
            r0 = p.add_run(); r0.text = ('      –  ' if sub else '▪  '); r0.font.size = Pt(size - (3 if sub else 0)); r0.font.color.rgb = rgb(AMBAR if not sub else GRIS); r0.font.bold = True
            # **negrita** simple
            partes = txt.replace('`', '').split('**')
            for i, t in enumerate(partes):
                if not t: continue
                r = p.add_run(); r.text = t; r.font.size = Pt(size - (3 if sub else 0)); r.font.bold = (i % 2 == 1); r.font.color.rgb = rgb(color); r.font.name = 'Calibri'
        return tb
    def _marco(self, s, titulo, kicker=''):
        self._rect(s, 0, 0, W, 1.05, OSCURO); self._rect(s, 0, 1.05, W, 0.07, AMBAR)
        self._text(s, 0.5, 0.12, 11.3, 0.85, titulo, 28, True, BLANCO, anchor=MSO_ANCHOR.MIDDLE)
        if kicker: self._text(s, 0.5, 0.02, 8, 0.3, kicker.upper(), 10, True, 'C9D8B0')
        self._rect(s, 11.4, 0.1, 1.75, 0.88, BLANCO, MSO_SHAPE.ROUNDED_RECTANGLE); s.shapes.add_picture(IMG + 'logo_gmc.jpg', Inches(11.5), Inches(0.14), height=Inches(0.8))
        self._text(s, 0.4, 7.08, 9, 0.3, f'GMC S.R.L.  ·  Taller AGAMDEPAZ  ·  {self.modulo}', 10, False, GRIS)
        self._text(s, 12.0, 7.08, 0.9, 0.3, str(self.n), 10, True, GRIS, PP_ALIGN.RIGHT)
    def _img(self, s, nombre, x, y, w, h):
        im = Image.open(IMG + nombre); iw, ih = im.size; esc = min(w / iw, h / ih); pw, ph = iw * esc, ih * esc
        px, py = x + (w - pw) / 2, y + (h - ph) / 2
        self._rect(s, px - 0.04, py - 0.04, pw + 0.08, ph + 0.08, 'D5DCC8')
        s.shapes.add_picture(IMG + nombre, Inches(px), Inches(py), Inches(pw), Inches(ph))

    # ---- diapositivas
    def portada(self, titulo, subtitulo, modulo, horas='', notas=''):
        s = self._slide(notas)
        self._rect(s, 0, 0, W, H, OSCURO); self._rect(s, 0, 5.2, W, 0.09, AMBAR)
        card = self._rect(s, 0.6, 0.55, 7.6, 1.5, BLANCO, MSO_SHAPE.ROUNDED_RECTANGLE)
        s.shapes.add_picture(IMG + 'logo_gmc.jpg', Inches(0.8), Inches(0.72), height=Inches(1.15)); s.shapes.add_picture(IMG + 'logo_agamdepaz.jpg', Inches(6.6), Inches(0.62), height=Inches(1.3))
        self._text(s, 0.7, 2.45, 12, 0.5, 'TALLER DE CAPACITACIÓN EN HERRAMIENTAS ADMINISTRATIVAS MUNICIPALES', 16, True, 'C9D8B0')
        self._text(s, 0.7, 2.95, 12, 1.4, titulo, 44, True, BLANCO)
        self._text(s, 0.7, 4.3, 12, 0.8, subtitulo, 20, False, 'E6EED5')
        self._text(s, 0.7, 5.5, 8, 0.45, modulo, 22, True, AMBAR); self._text(s, 0.7, 6.0, 8, 0.4, horas, 16, False, BLANCO)
        self._text(s, 0.7, 6.75, 12, 0.4, 'Asociación de Gobiernos Autónomos Municipales del Departamento de La Paz – AGAMDEPAZ  ·  Grupo Multidisciplinario de Consultores GMC S.R.L.', 11, False, 'C9D8B0')
    def seccion(self, num, titulo, detalle='', notas=''):
        s = self._slide(notas); self._rect(s, 0, 0, W, H, VERDE); self._rect(s, 0, 5.0, W, 0.09, AMBAR)
        self._text(s, 0.8, 1.6, 3, 1.8, num, 96, True, 'DCE8C4'); self._text(s, 0.8, 3.3, 12, 1.4, titulo, 40, True, BLANCO)
        if detalle: self._text(s, 0.8, 5.3, 11.5, 1.2, detalle, 20, False, 'F0F6E2')
        s.shapes.add_picture(IMG + 'logo_gmc.jpg', Inches(11.3), Inches(6.35), height=Inches(0.85)); self._text(s, 12.0, 7.08, 0.9, 0.3, str(self.n), 10, True, 'DCE8C4', PP_ALIGN.RIGHT)
    def lista(self, titulo, items, kicker='', size=25, notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker); self._bullets(s, 0.7, 1.55, 11.9, 5.3, items, size)
    def dos(self, titulo, tit_i, items_i, tit_d, items_d, kicker='', size=19, notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker)
        for x, t, it, c in [(0.5, tit_i, items_i, VERDE), (6.85, tit_d, items_d, AMBAR)]:
            self._rect(s, x, 1.45, 5.95, 0.55, c); self._text(s, x + 0.1, 1.47, 5.8, 0.5, t, 18, True, BLANCO, anchor=MSO_ANCHOR.MIDDLE)
            self._rect(s, x, 2.0, 5.95, 4.85, CLARO); self._bullets(s, x + 0.15, 2.15, 5.65, 4.6, it, size)
    def flujo(self, titulo, pasos, nota='', kicker='', notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker)
        n = len(pasos); gap = 0.18; ancho = (W - 1.0 - gap * (n - 1)) / n
        for i, (t, d) in enumerate(pasos):
            x = 0.5 + i * (ancho + gap)
            self._rect(s, x, 2.2, ancho, 0.95, VERDE if i % 2 == 0 else OSCURO, MSO_SHAPE.PENTAGON if i < n - 1 else MSO_SHAPE.ROUNDED_RECTANGLE)
            self._text(s, x + 0.03, 2.22, ancho - 0.3, 0.9, t, 15, True, BLANCO, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
            self._rect(s, x, 3.3, ancho, 2.2, CLARO); self._text(s, x + 0.06, 3.35, ancho - 0.12, 2.1, d, 13, False, TEXTO, PP_ALIGN.CENTER)
        if nota: self._rect(s, 0.5, 5.8, W - 1.0, 0.95, 'FFF4D1', line=AMBAR); self._text(s, 0.65, 5.85, W - 1.3, 0.85, nota, 17, False, TEXTO, anchor=MSO_ANCHOR.MIDDLE)
    def tabla(self, titulo, cab, filas, anchos=None, kicker='', size=14, notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker)
        nf = len(filas) + 1; alto = min(5.6, 0.5 * nf + 0.1)
        t = s.shapes.add_table(nf, len(cab), Inches(0.5), Inches(1.5), Inches(W - 1.0), Inches(alto)).table
        if anchos:
            tot = sum(anchos)
            for i, a in enumerate(anchos): t.columns[i].width = Inches((W - 1.0) * a / tot)
        for j, c in enumerate(cab):
            ce = t.cell(0, j); ce.fill.solid(); ce.fill.fore_color.rgb = rgb(OSCURO); ce.text = ''; r = ce.text_frame.paragraphs[0].add_run(); r.text = c; r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = rgb(BLANCO)
        for i, fila in enumerate(filas, 1):
            for j, v in enumerate(fila):
                ce = t.cell(i, j); ce.fill.solid(); ce.fill.fore_color.rgb = rgb(CLARO if i % 2 else BLANCO); ce.text = ''
                partes = str(v).replace('`', '').split('**')
                for k, tx in enumerate(partes):
                    if not tx: continue
                    r = ce.text_frame.paragraphs[0].add_run(); r.text = tx; r.font.size = Pt(size); r.font.bold = (k % 2 == 1); r.font.color.rgb = rgb(TEXTO)
                ce.vertical_anchor = MSO_ANCHOR.MIDDLE
    def pasos(self, titulo, pasos, img, pie='', kicker='', size=17, notas='', ancho_img=6.3):
        s = self._slide(notas); self._marco(s, titulo, kicker)
        izq = W - 1.0 - ancho_img - 0.3
        self._bullets(s, 0.5, 1.45, izq, 5.5, [f'{p}' for p in pasos], size)
        self._img(s, img, 0.5 + izq + 0.3, 1.4, ancho_img, 5.25)
        if pie: self._text(s, 0.5 + izq + 0.3, 6.68, ancho_img, 0.35, pie, 11, False, GRIS, PP_ALIGN.CENTER)
    def resultado(self, titulo, esperado, img=None, pie='', kicker='', notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker)
        ancho = 6.0 if img else W - 1.0
        self._rect(s, 0.5, 1.5, ancho, 0.5, VERDE); self._text(s, 0.6, 1.52, ancho - 0.2, 0.46, 'RESULTADO ESPERADO', 16, True, BLANCO, anchor=MSO_ANCHOR.MIDDLE)
        self._rect(s, 0.5, 2.0, ancho, 4.8, CLARO); self._bullets(s, 0.65, 2.15, ancho - 0.3, 4.6, esperado, 18)
        if img:
            self._img(s, img, 6.8, 1.4, 6.0, 5.25)
            if pie: self._text(s, 6.8, 6.68, 6.0, 0.35, pie, 11, False, GRIS, PP_ALIGN.CENTER)
    def imagen(self, titulo, img, pie='', kicker='', notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker); self._img(s, img, 0.8, 1.35, W - 1.6, 5.3)
        if pie: self._text(s, 0.8, 6.68, W - 1.6, 0.35, pie, 12, False, GRIS, PP_ALIGN.CENTER)
    def destacado(self, titulo, frase, apoyo='', kicker='', notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker)
        self._rect(s, 1.0, 1.8, W - 2.0, 2.6, CLARO, MSO_SHAPE.ROUNDED_RECTANGLE, line=VERDE); self._text(s, 1.3, 1.9, W - 2.6, 2.4, frase, 30, True, OSCURO, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        if apoyo: self._bullets(s, 1.2, 4.7, W - 2.4, 2.2, apoyo, 20)
    def preguntas(self, titulo, qs, kicker='', notas=''):
        s = self._slide(notas); self._marco(s, titulo, kicker)
        for i, (q, a) in enumerate(qs):
            y = 1.45 + i * 1.08
            self._rect(s, 0.5, y, 0.6, 0.9, AMBAR); self._text(s, 0.5, y, 0.6, 0.9, str(i + 1), 24, True, BLANCO, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
            self._rect(s, 1.1, y, W - 1.6, 0.9, CLARO); self._text(s, 1.25, y + 0.02, W - 1.9, 0.88, q, 17, True, TEXTO, anchor=MSO_ANCHOR.MIDDLE)
        # respuestas en las notas del facilitador
        self.p.slides[-1].notes_slide.notes_text_frame.text = (notas + '\n\nRESPUESTAS:\n' if notas else 'RESPUESTAS:\n') + '\n'.join(f'{i + 1}. {a}' for i, (q, a) in enumerate(qs))
    def cierre(self, titulo, items, notas=''):
        s = self._slide(notas); self._rect(s, 0, 0, W, H, OSCURO); self._rect(s, 0, 5.4, W, 0.09, AMBAR)
        self._rect(s, 0.6, 0.55, 7.6, 1.5, BLANCO, MSO_SHAPE.ROUNDED_RECTANGLE); s.shapes.add_picture(IMG + 'logo_gmc.jpg', Inches(0.8), Inches(0.72), height=Inches(1.15)); s.shapes.add_picture(IMG + 'logo_agamdepaz.jpg', Inches(6.6), Inches(0.62), height=Inches(1.3))
        self._text(s, 0.7, 2.4, 12, 1.0, titulo, 40, True, BLANCO); self._bullets(s, 0.8, 3.5, 11.5, 2.0, items, 20, 'E6EED5')
        self._text(s, 0.7, 6.0, 12, 0.9, ['Lic. Oscar Fernando Blanco Villegas · Gerente General · GMC S.R.L.', 'Lic. Vicente Yujra Coronado · AGAMDEPAZ'], 14, False, 'C9D8B0')
    def guardar(self, ruta): self.p.save(ruta)
