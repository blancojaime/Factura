"""Compone los manuales (Markdown -> Word y PDF) con tablas generadas desde el propio sistema (catálogo de informes y normativa)."""
from __future__ import annotations

import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
DOCS = os.path.join(RAIZ, "docs")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from contabol.normativa import DEFECTOS  # noqa: E402
from contabol.reports import catalogo  # noqa: E402


def tabla_catalogo() -> str:
    L = ["| Módulo | Informe | Parámetros | Control |", "|---|---|---|---|"]
    for r in sorted(catalogo.todos(), key=lambda x: (x.modulo, x.titulo)):
        L.append(f"| {r.modulo} | {r.titulo} | {', '.join(p.titulo for p in r.params) or '—'} | ☐ Pantalla ☐ PDF ☐ Excel |")
    return f"**Total: {len(catalogo.todos())} informes.**\n\n" + "\n".join(L)


def tabla_normativa() -> str:
    L = ["| Parámetro | Vigente desde | Valor | Descripción | Fuente |", "|---|---|---|---|---|"]
    for clave, desde, valor, desc, fuente in DEFECTOS:
        if len(valor) > 40:
            valor = "(escala)"
        L.append(f"| {clave} | {desde} | {valor} | {desc} | {fuente} |")
    return "\n".join(L)


def figuras() -> None:
    f = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)  # noqa: E731
    AZ, CL, GR = (31, 58, 95), (222, 231, 243), (108, 117, 125)
    # estructura de datos
    im = Image.new("RGB", (1000, 430), "white")
    d = ImageDraw.Draw(im)
    d.text((20, 12), "Estructura de la carpeta de datos (%LOCALAPPDATA%\\ContaBol)", font=f(17, True), fill=AZ)
    cajas = [(40, 70, 300, 70, "sistema.db", "Usuarios, empresas, permisos,\nnormativa vigente, auditoría"), (40, 170, 300, 70, "datos\\EMPRESA1\\2025.db", "Contabilidad de la gestión 2025"),
             (40, 260, 300, 70, "datos\\EMPRESA1\\2026.db", "Contabilidad de la gestión 2026"), (380, 170, 280, 70, "datos\\EMPRESA2\\2025.db", "Otra empresa: datos aislados"),
             (700, 70, 260, 70, "backups\\*.cbk", "Copias verificables (SHA-256)"), (700, 170, 260, 70, "reportes\\", "PDF y Excel exportados"), (700, 260, 260, 70, "logs\\contabol.log", "Registro de errores")]
    for x, y, w, h, t, s in cajas:
        d.rounded_rectangle([x, y, x + w, y + h], 8, fill=CL, outline=AZ, width=2)
        d.text((x + 12, y + 8), t, font=f(13, True), fill=AZ)
        d.text((x + 12, y + 32), s, font=f(11), fill=GR)
    d.text((40, 360), "Cada empresa y cada gestión tienen su propio archivo SQLite (WAL): un problema en uno no afecta a los demás.", font=f(12), fill=GR)
    im.save(os.path.join(DOCS, "img", "estructura_datos.png"))
    # flujo de implementación
    im = Image.new("RGB", (1100, 190), "white")
    d = ImageDraw.Draw(im)
    pasos = ["Instalar\nContaBol", "Ingresar y cambiar\ncontraseña", "Crear la\nempresa", "Cargar T.C. y UFV;\nrevisar parámetros", "Usuarios y\npermisos", "Saldos iniciales\ny primera copia"]
    for i, p in enumerate(pasos):
        x = 15 + i * 178
        d.rounded_rectangle([x, 50, x + 160, 130], 10, fill=AZ)
        d.multiline_text((x + 80, 90), p, font=f(12, True), fill="white", anchor="mm", align="center")
        if i < 5:
            d.line([x + 160, 90, x + 178, 90], fill=GR, width=3)
    d.text((15, 12), "Flujo de implementación", font=f(16, True), fill=AZ)
    im.save(os.path.join(DOCS, "img", "flujo_implementacion.png"))


def construir(nombre: str, salida: str) -> None:
    src = os.path.join(DOCS, "fuente", nombre + ".md")
    txt = open(src, encoding="utf-8").read().replace("<!--CATALOGO-->", tabla_catalogo()).replace("<!--NORMATIVA-->", tabla_normativa())
    tmp = os.path.join(DOCS, salida + ".md")
    open(tmp, "w", encoding="utf-8").write(txt)
    docx = os.path.join(DOCS, salida + ".docx")
    subprocess.run(["pandoc", tmp, "-o", docx, "--resource-path", DOCS, "--toc", "--toc-depth=2"], check=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", DOCS, docx], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(tmp)
    print(salida, "OK")


if __name__ == "__main__":
    figuras()
    construir("Manual_Pruebas", "Manual_de_Pruebas_ContaBol")
    construir("Manual_Implementacion", "Manual_de_Implementacion_ContaBol")
