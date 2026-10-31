"""Folleto comercial (tríptico A4 apaisado, 2 caras). Uso: python docs/folleto.py  → docs/salida/3_Folleto_SIIM2026.pdf"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from PIL import Image

from siim.reports import catalogo, engine as E

NAVY, STEEL, GOLD, PALE, INK = colors.HexColor("#1F3A5F"), colors.HexColor("#2F5D8A"), colors.HexColor("#F2C14E"), colors.HexColor("#E8EEF5"), colors.HexColor("#1B2430")
W, H = landscape(A4)
PW = W / 3
IMG = HERE / "img"


def para(c, text, x, y, w, size=9.5, color=INK, lead=None, bold=False, align=0):
    st = ParagraphStyle("p", fontName=E.FONT_B if bold else E.FONT, fontSize=size, leading=lead or size * 1.35, textColor=color, alignment=align)
    p = Paragraph(text, st)
    _, h = p.wrap(w, 1000)
    p.drawOn(c, x, y - h)
    return y - h


def titulo(c, text, x, y, w, color=NAVY, size=15):
    return para(c, text, x, y, w, size, color, size * 1.15, True)


def bullets(c, items, x, y, w, size=9, gap=3.2, color=INK):
    for t in items:
        c.setFillColor(GOLD); c.circle(x + 1.6 * mm, y - size * 0.55, 1.3, stroke=0, fill=1)
        y = para(c, t, x + 5 * mm, y, w - 5 * mm, size, color) - gap
    return y


def pill(c, text, x, y, w=None):
    c.setFont(E.FONT_B, 8)
    w = w or c.stringWidth(text, E.FONT_B, 8) + 10
    c.setFillColor(GOLD); c.roundRect(x, y, w, 13, 6, stroke=0, fill=1)
    c.setFillColor(NAVY); c.drawString(x + 5, y + 4, text)
    return w


def shot(c, name, x, y, w, crop=None):
    p = IMG / name
    im = Image.open(p)
    if crop:
        im = im.crop(crop); p = Path("/tmp") / ("crop_" + name); im.save(p)
    h = w * im.size[1] / im.size[0]
    c.setFillColor(colors.HexColor("#00000012")); c.roundRect(x + 1, y - h - 1, w, h, 3, stroke=0, fill=1)
    c.drawImage(str(p), x, y - h, width=w, height=h)
    c.setStrokeColor(colors.HexColor("#C9D2DE")); c.setLineWidth(0.5); c.rect(x, y - h, w, h, stroke=1, fill=0)
    return y - h


def build(path):
    E.setup_fonts()
    c = canvas.Canvas(str(path), pagesize=landscape(A4))
    c.setTitle("SIIM 2026 – Folleto"); c.setAuthor("SIIM 2026")
    pad = 11 * mm
    nrep = len(catalogo.CATALOGO)

    # =================== CARA 1 (exterior): solapa | contraportada | portada ===================
    # --- panel 1: seguridad y respaldos
    x0 = 0
    c.setFillColor(colors.white); c.rect(x0, 0, PW, H, stroke=0, fill=1)
    y = H - 16 * mm
    pill(c, "SEGURIDAD", x0 + pad, y); y -= 9 * mm
    y = titulo(c, "Información protegida,<br/>operación sin sobresaltos", x0 + pad, y, PW - 2 * pad, size=16) - 5 * mm
    y = bullets(c, ["<b>Base de datos transaccional</b> (SQLite WAL): un corte de luz no corrompe los datos.",
                    "<b>Respaldos verificados</b>: automáticos y al cerrar, con huella SHA‑256, <b>cifrado opcional</b> y copia a USB o red.",
                    "<b>Restauración segura</b>: crea un respaldo previo y revierte si algo falla.",
                    "<b>Bitácora a prueba de manipulación</b>: cada operación queda encadenada con hashes.",
                    "<b>Roles y permisos</b>: administrador, supervisor, liquidador, cajero, empadronador y consulta.",
                    "<b>Contraseñas protegidas</b>, bloqueo por intentos y cierre de sesión por inactividad.",
                    "<b>Activación por licencia firmada</b>, ligada al equipo, sin Internet."], x0 + pad, y, PW - 2 * pad) - 3 * mm
    c.setFillColor(PALE); c.roundRect(x0 + pad, 14 * mm, PW - 2 * pad, 24 * mm, 4, stroke=0, fill=1)
    para(c, "<b>Funciona en Windows 10 y 11.</b><br/>Instalador único, sin servidores ni Internet. Los datos se guardan fuera del programa y se conservan al actualizar.", x0 + pad + 4 * mm, 35 * mm, PW - 2 * pad - 8 * mm, 8.5)

    # --- panel 2: contraportada / contacto
    x1 = PW
    c.setFillColor(NAVY); c.rect(x1, 0, PW, H, stroke=0, fill=1)
    y = H - 20 * mm
    y = titulo(c, "Solicite una<br/>demostración", x1 + pad, y, PW - 2 * pad, colors.white, 22) - 6 * mm
    y = para(c, "Le mostramos el sistema con datos de ejemplo y calculamos con usted un caso real de su municipio: un inmueble, un vehículo y una actividad económica.", x1 + pad, y, PW - 2 * pad, 10, colors.HexColor("#DCE5F0")) - 8 * mm
    c.setFillColor(GOLD); c.rect(x1 + pad, y, 18 * mm, 1.2, stroke=0, fill=1); y -= 8 * mm
    for l in ("[Nombre de su empresa]", "Teléfono / WhatsApp: [_______________]", "Correo: [_______________]", "Dirección: [_______________]"):
        y = para(c, l, x1 + pad, y, PW - 2 * pad, 10, colors.white, bold=l.startswith("[N")) - 2.5 * mm
    y -= 6 * mm
    y = para(c, "<b>Incluye</b>", x1 + pad, y, PW - 2 * pad, 10, GOLD) - 2 * mm
    y = bullets(c, ["Instalación y activación del sistema", "Manual de implementación y manual de pruebas con ejercicios resueltos", "Capacitación del personal (plan de 3 días)", "Carga inicial de zonas, tablas y padrón (migración desde Excel)", "Soporte y actualizaciones de tablas por gestión"], x1 + pad, y, PW - 2 * pad, 8.8, color=colors.white)
    c.setFillColor(colors.white); c.roundRect(x1 + pad, 12 * mm, 26 * mm, 26 * mm, 3, stroke=0, fill=1)
    d = Drawing(22 * mm, 22 * mm); wq = qr.QrCodeWidget("SIIM2026|DEMOSTRACION|[complete con su enlace]"); b = wq.getBounds()
    d.transform = [22 * mm / (b[2] - b[0]), 0, 0, 22 * mm / (b[3] - b[1]), 0, 0]; d.add(wq); renderPDF.draw(d, c, x1 + pad + 2 * mm, 14 * mm)
    para(c, "Escanee para contactarnos<br/><font size=7>(reemplace este QR por su enlace)</font>", x1 + pad + 30 * mm, 33 * mm, PW - 2 * pad - 30 * mm, 8.5, colors.HexColor("#C9D6E6"))

    # --- panel 3: portada
    x2 = 2 * PW
    c.setFillColor(NAVY); c.rect(x2, 0, PW, H, stroke=0, fill=1)
    c.setFillColor(STEEL); c.rect(x2, 0, PW, H * 0.43, stroke=0, fill=1)
    c.setFillColor(GOLD); c.rect(x2, H * 0.43, PW, 2.2, stroke=0, fill=1)
    y = H - 16 * mm
    c.setFillColor(colors.white); c.setFont(E.FONT_B, 34); c.drawString(x2 + pad, y - 12 * mm, "SIIM"); c.setFillColor(GOLD)
    c.drawString(x2 + pad + c.stringWidth("SIIM ", E.FONT_B, 34), y - 12 * mm, "2026")
    y = para(c, "Sistema Integrado de<br/>Ingresos Municipales", x2 + pad, y - 18 * mm, PW - 2 * pad, 14, colors.white, bold=True) - 5 * mm
    y = para(c, "Impuestos, patentes y tasas en un solo sistema: <b>moderno, seguro y listo para Windows 11</b>.", x2 + pad, y, PW - 2 * pad, 10.5, colors.HexColor("#DCE5F0")) - 4 * mm
    shot(c, "liq_ipbi.png", x2 + pad - 2 * mm, H * 0.43 - 5 * mm, PW - 2 * pad + 4 * mm, crop=(230, 0, 1442, 800))
    para(c, "Continuidad del SIIM que su equipo ya conoce, sobre una base técnica nueva.", x2 + pad, 17 * mm, PW - 2 * pad, 9.5, colors.white, bold=True)
    c.showPage()

    # =================== CARA 2 (interior): tres paneles ===================
    c.setFillColor(colors.white); c.rect(0, 0, W, H, stroke=0, fill=1)
    # --- panel 1: continuidad
    x = 0
    y = H - 16 * mm
    pill(c, "DEL SIIM A SIIM 2026", x + pad, y); y -= 9 * mm
    y = titulo(c, "Lo que su equipo ya sabe hacer,<br/>ahora en Windows 11", x + pad, y, PW - 2 * pad, size=15) - 4 * mm
    y = para(c, "El SIIM de 1998 funcionaba con tecnología de 16 bits que <b>ya no corre en Windows 11</b>. SIIM 2026 conserva su estructura y lenguaje —PMC, F‑019, F‑027, F‑035, F‑1980, F‑2160, F‑501, FUC— con un diseño sobrio y más simple.", x + pad, y, PW - 2 * pad, 9) - 4 * mm
    mods = [("Empadronamiento", "Padrón de contribuyentes, altas, modificaciones y bajas"), ("Liquidación", "IPBI, IPVA, patentes, IMT; individual y masiva"), ("Recaudación", "Caja y bancos, recibos, cuenta corriente, conciliación"),
            ("Otros ingresos", "Tasas, derechos, alquileres y multas con FUC"), ("Reportes", f"{nrep} reportes en PDF y Excel"), ("Mantenimiento", "Tablas por gestión, usuarios y parámetros")]
    for t, d_ in mods:
        c.setFillColor(PALE); c.roundRect(x + pad, y - 11.5 * mm, PW - 2 * pad, 11 * mm, 3, stroke=0, fill=1)
        c.setFillColor(NAVY); c.setFont(E.FONT_B, 9); c.drawString(x + pad + 3 * mm, y - 5 * mm, t)
        para(c, d_, x + pad + 3 * mm, y - 6 * mm, PW - 2 * pad - 6 * mm, 7.8, colors.HexColor("#33415A"))
        y -= 13.2 * mm
    y -= 1 * mm
    shot(c, "padron.png", x + pad, y, PW - 2 * pad)

    # --- panel 2: actividades económicas
    x = PW
    c.setFillColor(NAVY); c.rect(x, 0, PW, H, stroke=0, fill=1)
    y = H - 16 * mm
    pill(c, "ACTIVIDADES ECONÓMICAS, TASAS Y PATENTES", x + pad, y); y -= 9 * mm
    y = titulo(c, "Un módulo de patentes<br/>pensado para la ley municipal", x + pad, y, PW - 2 * pad, colors.white, 15) - 4 * mm
    y = bullets(c, ["<b>Tres modalidades de cálculo</b>: patente máxima × zona‑superficie, patente única por m² o monto por categoría.",
                    "<b>Duodécimas automáticas</b> cuando la actividad abre o cierra en la gestión.",
                    "<b>Licencia de funcionamiento con QR</b> verificable y control de vencimientos.",
                    "<b>Simulador de patentes</b>: compare el efecto de una nueva ordenanza antes de aprobarla.",
                    "Patentes de <b>publicidad</b>, <b>espectáculos y sentajes</b> por formulario único de caja.",
                    "<b>Alertas</b> de licencias por vencer, inspecciones y clausuras, clasificador CIIU/CAEB."], x + pad, y, PW - 2 * pad, 8.8, 3, colors.white) - 2 * mm
    shot(c, "act_simulador.png", x + pad, y, PW - 2 * pad, crop=(238, 100, 1442, 530))

    # --- panel 3: cálculo y reportes
    x = 2 * PW
    y = H - 16 * mm
    pill(c, "CÁLCULO CONFIABLE", x + pad, y); y -= 9 * mm
    y = titulo(c, "Cada boliviano calculado<br/>y explicado", x + pad, y, PW - 2 * pad, size=15) - 4 * mm
    y = bullets(c, ["<b>Deuda Tributaria automática</b> (Art. 47 Ley 2492): mantenimiento de valor con UFV, intereses y multa por deberes formales, para deudas anteriores y posteriores a 2002.",
                    "<b>Descuento por pago al contado</b>, pago en dos cuotas, rectificatorias con crédito y <b>planes de pago</b>.",
                    "<b>IMT</b> con plazo de 10 días hábiles y cambio de propietario al pagar.",
                    "<b>Formularios oficiales en PDF</b> con código de pago y QR.",
                    "<b>Verificado</b> con los ejemplos oficiales de los Apuntes Tributarios del SIIM y pruebas automáticas.",
                    "Importación y exportación <b>Excel</b>; <b>conciliación bancaria</b> por código de pago."], x + pad, y, PW - 2 * pad, 8.8, 3) - 2 * mm
    shot(c, "cobro_mora.png", x + pad, y, PW - 2 * pad, crop=(238, 350, 1376, 790))
    para(c, "Las alícuotas, escalas y aranceles se cargan según la ley municipal vigente de cada GAM. Capturas con datos ficticios de demostración.", x + pad, 14 * mm, PW - 2 * pad, 7, colors.HexColor("#5B6573"))
    # separadores de plegado muy sutiles
    c.setStrokeColor(colors.HexColor("#E3E8EF")); c.setDash(2, 3)
    for k in (1, 2):
        c.line(k * PW, 0, k * PW, 4 * mm); c.line(k * PW, H - 4 * mm, k * PW, H)
    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    out = HERE / "salida"; out.mkdir(exist_ok=True)
    p = build(out / "3_Folleto_SIIM2026.pdf")
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(p))
    for i in range(len(pdf)):
        pdf[i].render(scale=1.6).to_pil().save(out / f"3_Folleto_cara{i + 1}.png")
    print("ok", p)
