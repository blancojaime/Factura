#!/usr/bin/env python3
"""Genera el Manual de JB-Personal: implementación, instalación y pruebas (Word + PDF).

Uso:  python generar_manual.py        (requiere python-docx; el PDF usa LibreOffice 'soffice' si está instalado)
"""
import shutil
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AQUI = Path(__file__).resolve().parent
AZUL = RGBColor(0x8A, 0x3B, 0x12)
VERSION = "1.1.1"
NTEST = 92
doc = Document()

# ---------------------------------------------------------------- estilos
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)          # Carta
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = sec.bottom_margin = Cm(2.0)
st = doc.styles
st["Normal"].font.name = "Calibri"
st["Normal"].font.size = Pt(10.5)
st["Normal"].paragraph_format.space_after = Pt(6)
for n, sz in (("Heading 1", 18), ("Heading 2", 14), ("Heading 3", 11.5)):
    s = st[n]
    s.font.name, s.font.size, s.font.bold, s.font.color.rgb = "Calibri", Pt(sz), True, AZUL
    s.paragraph_format.space_before, s.paragraph_format.space_after = Pt(14 if n != "Heading 3" else 8), Pt(6)
    s.paragraph_format.keep_with_next = True


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), color)
    tcPr.append(sh)


def borders(tbl, color="B8C2D0"):
    tblPr = tbl._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement(f"w:{e}")
        x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), color)
        b.append(x)
    tblPr.append(b)


def H(t, n=1):
    return doc.add_heading(t, n)


def P(t="", bold=False, italic=False, align=None, size=None, color=None):
    p = doc.add_paragraph()
    _runs(p, t, bold, italic, size, color)
    if align:
        p.alignment = align
    return p


def _runs(p, t, bold=False, italic=False, size=None, color=None):
    """Soporta **negrita** y `código` dentro del texto."""
    for i, parte in enumerate(t.split("**")):
        for j, frag in enumerate(parte.split("`")):
            if not frag:
                continue
            r = p.add_run(frag)
            r.bold = bold or i % 2 == 1
            r.italic = italic
            if j % 2 == 1:
                r.font.name = "Consolas"
                r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
                r.font.size = Pt((size or 10.5) - 1)
            elif size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = color


def B(items, style="List Bullet"):
    for t in items:
        p = doc.add_paragraph(style=style)
        _runs(p, t)
        p.paragraph_format.space_after = Pt(2)


def N(items):
    """Lista numerada que SIEMPRE empieza en 1 (numeración manual con sangría francesa)."""
    for i, txt in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(3)
        _runs(p, f"{i}.  " + txt)


def CODE(txt):
    t = doc.add_table(rows=1, cols=1)
    borders(t, "CCCCCC")
    c = t.rows[0].cells[0]
    shade(c, "F8F1E7")
    c.paragraphs[0].text = ""
    for i, ln in enumerate(txt.strip("\n").split("\n")):
        p = c.paragraphs[0] if i == 0 else c.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(ln or " ")
        r.font.name, r.font.size = "Consolas", Pt(8.5)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def NOTE(t, tipo="Nota"):
    tb = doc.add_table(rows=1, cols=1)
    borders(tb, "E0A800" if tipo != "Nota" else "C98B4B")
    c = tb.rows[0].cells[0]
    shade(c, "FFF3D6" if tipo != "Nota" else "F6E9D8")
    p = c.paragraphs[0]
    _runs(p, f"**{tipo}:** " + t)
    p.paragraph_format.space_after = Pt(0)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def T(cab, filas, anchos=None, size=9):
    t = doc.add_table(rows=1, cols=len(cab))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    borders(t)
    for i, h in enumerate(cab):
        c = t.rows[0].cells[i]
        shade(c, "8A3B12")
        c.paragraphs[0].text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size, r.font.color.rgb = True, Pt(size), RGBColor(255, 255, 255)
    for k, f in enumerate(filas):
        cells = t.add_row().cells
        for i, v in enumerate(f):
            cells[i].paragraphs[0].text = ""
            _runs(cells[i].paragraphs[0], str(v), size=size)
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
            if k % 2:
                shade(cells[i], "FFF7EC")
    if anchos:
        t.autofit = False
        for i, w in enumerate(anchos):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(anchos):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def IMG(nombre, ancho=16, pie=""):
    f = AQUI / "img" / nombre
    if f.exists():
        doc.add_picture(str(f), width=Cm(ancho))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if pie:
            P(pie, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)


def SALTO():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------- pie de página
def numero_pagina(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("JB-Personal · Manual v" + VERSION + " · Página ")
    r.font.size = Pt(8)
    r2 = p.add_run()
    r2.font.size = Pt(8)
    for tipo, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tipo)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt
        r2._r.append(e)


numero_pagina(sec)

# ================================================================= PORTADA
for _ in range(2):
    P()
logo = AQUI.parent / "frontend" / "img" / "logo.jpg"
if logo.exists():
    doc.add_picture(str(logo), width=Cm(8.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
P()
P("JB-PERSONAL", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=30, color=AZUL)
P("Gestión de Personal y Asistencia Municipal", align=WD_ALIGN_PARAGRAPH.CENTER, size=15, color=AZUL)
P()
P("Manual de implementación, instalación, activación y pruebas", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
P(f"Versión {VERSION} · Windows 10 o superior (servicio) · Servidor web Linux/Windows", align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
for _ in range(7):
    P()
P("Jaime Blanco · Consultor Administrativo Financiero", align=WD_ALIGN_PARAGRAPH.CENTER, size=10, color=RGBColor(0x6B, 0x5A, 0x4B))
P("Documento de uso interno · Unidad de Recursos Humanos / Unidad de Sistemas", align=WD_ALIGN_PARAGRAPH.CENTER, size=9, color=RGBColor(0x6B, 0x5A, 0x4B))
SALTO()

# ================================================================= CONTENIDO
H("Contenido")
for t in ["1. Introducción y novedades de la versión 1.1", "2. Requisitos",
          "3. Instalación (servicio de Windows · construir instaladores · servidor Linux · PostgreSQL)",
          "4. Activación y licencia", "5. Primer ingreso y configuración inicial",
          "6. Importación de marcaciones de relojes de distintas marcas", "7. Operación mensual y reportes",
          "8. Respaldos y recuperación", "9. Guía de pruebas con casos reales", "10. Seguridad", "11. Solución de problemas",
          "12. Supuestos legales y limitaciones conocidas", "Anexo A. Manual del JB-Activador (emisor de licencias)", "Anexo B. Rutas, puertos y archivos"]:
    P(t)
SALTO()

# ================================================================= 1
H("1. Introducción y novedades de la versión 1.1")
P("**JB-Personal** administra el personal de un Gobierno Autónomo Municipal (GAM): **permanente**, **eventual** y **consultores individuales de línea**. "
  "Importa las marcaciones del reloj biométrico, calcula atrasos, faltas y permisos, y genera las planillas e informes mensuales.")
T(["Módulo", "Qué hace"], [
    ["A. Institucional", "Datos del municipio, horarios y tolerancias, escala de sanción, feriados, carga masiva de personal (Excel/CSV)"],
    ["B. Biometría y asistencia", "Lee marcaciones de relojes de distintas marcas (autodetección + perfiles de mapeo de columnas) y clasifica cada día: normal, retraso leve/grave, falta justificada/injustificada, omisión"],
    ["C. Permisos e instructivos", "Solicitudes con boleta PDF y correlativo; instructivos con cite oficial (GAM-RRHH-INST-001/2026), destinatarios y notificación"],
    ["D. Reportes", "Informe de asistencia (.docx), planillas de nuevo personal, desvinculados y sueldos (.xlsx), reporte detallado (.xlsx) y consolidado plano para auditoría en **.txt/.csv y .xlsx**"],
    ["Transversal", "Usuarios y roles, bitácora inalterable, cierre de periodo, respaldos cifrados, **licencia y activación**"],
], [4, 12.5])
H("Novedades de la versión 1.1", 2)
T(["N°", "Cambio", "Dónde se ve"], [
    ["1", "**Instalador independiente de la sesión:** JB-Personal se instala como servicio (tarea de arranque de Windows, cuenta SYSTEM). Funciona al encender el equipo, sin que ningún usuario haya iniciado sesión", "Cap. 3"],
    ["2", "**Nueva identidad:** la aplicación se denomina **JB-Personal** y usa el logotipo y el icono de Jaime Blanco (instalador, accesos directos, pantalla de ingreso, menú y pestaña del navegador)", "Cap. 1, 3"],
    ["3", "**Consolidado de auditoría también en Excel:** archivo `.xlsx` plano con solo títulos y datos, además del `.txt/.csv` UTF-8", "Cap. 7"],
    ["4", "**Marcaciones de cualquier marca de reloj:** autodetección ampliada, **asistente para indicar qué columna es cada dato**, perfiles reutilizables y formato «ancho» (varias horas por fila)", "Cap. 6"],
    ["5", "**Diseño cálido:** nueva paleta (terracota, ámbar y crema) en la aplicación, los reportes Excel/PDF y el informe Word", "Toda la aplicación"],
    ["6", "**Planillas corregidas:** las planillas mostraban hojas sin empleados cuando el personal se importaba después de «Procesar». Ahora los reportes de periodos abiertos **se recalculan siempre al descargarse** y avisan si no hay personal con contrato vigente", "Cap. 7"],
    ["7", "**Activador externo:** herramienta JB-Activador (solo del emisor) que genera códigos de activación firmados por equipo; la aplicación incluye prueba de 30 días y modo solo lectura", "Cap. 4, Anexo A"],
    ["8", "**Manuales actualizados** (Word, PDF y GitHub)", "Este documento"],
], [0.9, 12.2, 3.4], size=9)
IMG("ui_inicio.png", 16, "Figura 1. Pantalla «Inicio / Planilla» con el nuevo diseño y el aviso de periodo de prueba.")

# ================================================================= 2
H("2. Requisitos")
T(["Componente", "Instalador de Windows (servicio)", "Servidor web Linux"], [
    ["Sistema operativo", "Windows 10 o superior, 64 bits (PowerShell 5.1 incluido en Windows)", "Ubuntu 22.04+/Debian 12 o similar"],
    ["Software previo", "**Ninguno** (el instalador incluye Python y todas las librerías)", "Python 3.11+; opcional PostgreSQL 14+"],
    ["Permisos para instalar", "**Administrador** (registra el servicio y, si se elige, la regla de firewall)", "Administrador del servidor"],
    ["Espacio en disco", "≈ 250 MB + datos y respaldos", "≈ 300 MB + datos y respaldos"],
    ["Memoria", "4 GB", "4 GB (8 GB con muchos usuarios)"],
    ["Navegador de los usuarios", "Edge, Chrome o Firefox actualizados", "Edge, Chrome o Firefox actualizados"],
    ["Internet", "No se necesita para operar", "No se necesita para operar (solo para instalar)"],
], [3.5, 6.5, 6.5])

# ================================================================= 3
H("3. Instalación")
H("3.1 Instalador de Windows como servicio (recomendado)", 2)
P("El archivo **JBPersonal_Setup.exe** instala JB-Personal como un **servicio de Windows** (tarea programada de arranque, cuenta SYSTEM). "
  "Esto significa que el sistema **se inicia solo al encender el equipo y sigue funcionando aunque no haya ninguna sesión de usuario abierta** "
  "o se cierre la sesión; si el proceso falla, Windows lo reinicia al minuto.")
N(["Copie **JBPersonal_Setup.exe** al equipo (USB, correo o carpeta compartida) y haga doble clic. Acepte el aviso de permisos de administrador.",
   "Si Windows muestra «Windows protegió su PC» (el instalador no está firmado digitalmente), pulse **Más información → Ejecutar de todas formas**.",
   "Pulse **Siguiente** y luego **Instalar**: no hay más preguntas. El asistente copia los archivos en `C:\\Program Files\\JB-Personal`, registra la tarea de arranque, la inicia y verifica que responda.",
   "Deje marcada **Abrir JB-Personal en el navegador** y pulse **Finalizar**: se abre `http://127.0.0.1:8765/`.",
   "En el primer ingreso cree la cuenta de administrador (capítulo 5) y, en el menú **Licencia**, active el sistema (capítulo 4)."])
T(["Elemento", "Ubicación / detalle"], [
    ["Programa (solo lectura)", "`C:\\Program Files\\JB-Personal` — Python embebido, librerías, código, manuales y dataset de prueba"],
    ["Servicio", "Tarea programada **JB-Personal** (al arrancar, cuenta SYSTEM, reinicio automático cada minuto si falla, sin límite de tiempo)"],
    ["Datos, respaldos y registro", "`C:\\ProgramData\\JB-Personal` (base de datos `gam_personal.db`, carpeta `backups`, `logs\\servicio.log`, `config.ini`). **No se borran al desinstalar**"],
    ["Dirección de uso", "`http://127.0.0.1:8765/` (desde otras PC, si se habilitó la red: `http://IP-DEL-EQUIPO:8765/`)"],
    ["Accesos directos", "Escritorio y menú Inicio → JB-Personal: *JB-Personal* (abre el navegador), *Administrar el servicio*, *Habilitar acceso desde la red*, *Solo esta PC*, *Manuales*, *Desinstalar*"],
], [4.2, 12.3])
H("Administrar el servicio", 3)
P("Menú Inicio → JB-Personal → **Administrar el servicio** (pide permisos de administrador): iniciar, detener, reiniciar, abrir el navegador, ver el registro y abrir la carpeta de datos. "
  "Equivalentes en una consola de administrador: `schtasks /Run /TN \"JB-Personal\"` (iniciar) · `schtasks /End /TN \"JB-Personal\"` (detener) · `schtasks /Query /TN \"JB-Personal\"` (estado).")
P("**Acceso desde otras PC de la red (opcional):** por defecto el sistema solo responde en la propia PC. Para habilitarlo use el acceso directo **Habilitar acceso desde la red** (menú Inicio → JB-Personal; abre el puerto 8765 en el Firewall para redes de dominio y privadas) y para revertirlo **Solo esta PC**. Luego, desde las otras PC: `http://IP-DE-ESTA-PC:8765/`.")
P("Para cambiar el puerto o abrir/cerrar el acceso de red a mano edite `C:\\ProgramData\\JB-Personal\\config.ini` (`host = 127.0.0.1` solo esta PC · `host = 0.0.0.0` toda la red; `port = 8765`), reinicie el servicio y, si cambió el puerto, actualice las reglas del Firewall y el acceso directo.")
H("Actualizar y desinstalar", 3)
P("**Actualizar:** ejecute el instalador nuevo sobre el anterior: detiene el servicio, reemplaza el programa y lo vuelve a iniciar; los datos y la licencia se conservan. Haga un respaldo antes. "
  "**Desinstalar:** menú Inicio → JB-Personal → Desinstalar (o Configuración → Aplicaciones). Se elimina el programa, el servicio y la regla de firewall; los datos permanecen en `C:\\ProgramData\\JB-Personal`.")
NOTE("El instalador se construyó en un entorno Linux con NSIS y Python embebido oficial; **no pudo ejecutarse en Windows durante el desarrollo** (el modo servicio del lanzador sí se probó en Linux). "
     "Instálelo primero en una PC piloto y complete la lista de aceptación del capítulo 9.7, en especial la prueba «reiniciar sin iniciar sesión».", "Importante")
H("3.2 Cómo comprobar que funciona sin sesión", 2)
N(["Instale y confirme que abre en el navegador.", "Cierre la sesión de Windows (o reinicie el equipo) **sin volver a iniciar sesión**.",
   "Desde **otra PC** con acceso de red habilitado abra `http://IP-DEL-EQUIPO:8765/`: debe cargar la pantalla de ingreso. "
   "(Si solo se usa la misma PC, inicie sesión y compruebe en `C:\\ProgramData\\JB-Personal\\logs\\servicio.log` que el servicio arrancó al encender, antes de su inicio de sesión.)"])

H("3.3 Construir los instaladores (personal de Sistemas)", 2)
P("Pueden construirse desde Linux, macOS o Windows con Python 3.9+, NSIS (`makensis`) e Internet:")
CODE("""cd jb-personal/desktop
python build_installer.py --version 1.1.0 --manual ../docs/Manual_JB-Personal.pdf ../docs/Manual_JB-Personal.docx
#   -> desktop/JBPersonal_Setup.exe          (aplicación, para las entidades)
python build_activador.py --clave-privada RUTA/clave_privada.pem
#   -> desktop/JBActivador_Setup.exe         (herramienta del emisor, NO se entrega a las entidades)""")
P("El script descarga Python embebido 3.12 (win_amd64) y las librerías como *wheels* para Windows, copia el código y arma el instalador. "
  "Los scripts de PowerShell que registran el servicio están en `desktop/windows/`.")

H("3.4 Servidor web en Linux", 2)
CODE("""sudo apt update && sudo apt install -y python3 python3-venv
sudo useradd -r -m -d /opt/jb jb
sudo -u jb bash -c 'cd /opt/jb && git clone <URL-DEL-REPOSITORIO> app && cd app/jb-personal/backend \\
   && python3 -m venv /opt/jb/venv && /opt/jb/venv/bin/pip install -r requirements.txt'
sudo mkdir -p /var/lib/jb-personal && sudo chown jb: /var/lib/jb-personal""")
P("Archivo `/etc/jb-personal.env` (permisos 600):")
CODE("""GAM_DATA_DIR=/var/lib/jb-personal
GAM_BACKUP_DIR=/var/lib/jb-personal/backups
GAM_SECRET_KEY=<cadena aleatoria de 48+ caracteres>
GAM_BACKUP_PASSWORD=<clave de cifrado de respaldos>
# GAM_DATABASE_URL=postgresql+psycopg://jb:CLAVE@127.0.0.1:5432/jbpersonal   (omitir para usar SQLite)""")
P("Servicio `/etc/systemd/system/jb-personal.service`:")
CODE("""[Unit]
Description=JB-Personal
After=network.target
[Service]
User=jb
EnvironmentFile=/etc/jb-personal.env
WorkingDirectory=/opt/jb/app/jb-personal/backend
ExecStart=/opt/jb/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
[Install]
WantedBy=multi-user.target""")
CODE("""sudo systemctl daemon-reload && sudo systemctl enable --now jb-personal
curl http://127.0.0.1:8000/api/salud        # debe responder {"ok":true,...}""")
NOTE("En producción publique el puerto 8000 detrás de nginx/Apache/IIS con **HTTPS**; no exponga uvicorn directamente. Con SQLite use **un solo worker**. "
     "Las variables de entorno conservan el prefijo `GAM_` por compatibilidad.", "Importante")
H("3.5 PostgreSQL (opcional)", 2)
CODE("""sudo -u postgres psql -c "CREATE USER jb WITH PASSWORD 'CLAVE'" -c "CREATE DATABASE jbpersonal OWNER jb ENCODING 'UTF8'"
/opt/jb/venv/bin/pip install "psycopg[binary]"
# Defina GAM_DATABASE_URL y reinicie: tablas y triggers se crean al iniciar. Manual: psql -d jbpersonal -f db/schema_postgresql.sql""")
P(f"Verificado con PostgreSQL 16: las {NTEST} pruebas automáticas, el respaldo con `pg_dump` y la restauración con `psql` pasan. Los respaldos en PostgreSQL requieren `pg_dump` y `psql` en el PATH del servicio.")

# ================================================================= 4
H("4. Activación y licencia")
P("JB-Personal se entrega **sin activar**. Funciona con todas sus funciones durante **30 días de prueba**; después pasa a **modo solo lectura** hasta ingresar un código de activación válido. "
  "Los datos nunca se pierden ni se bloquean para consulta.")
T(["Estado", "Qué permite"], [
    ["PRUEBA (30 días)", "Todo. Un aviso amarillo muestra los días restantes"],
    ["ACTIVADA", "Todo. Si la licencia tiene vencimiento, se muestra la fecha"],
    ["PRUEBA VENCIDA / VENCIDA", "**Solo lectura:** consultar pantallas, respaldar y activar. No permite registrar, importar, procesar ni generar reportes (aviso rojo)"],
], [4.5, 12])
H("Cómo activar", 3)
N(["Ingrese como **administrador** → menú **Licencia**.", "Copie el **código de equipo** (formato `JBP-XXXXX-XXXXX-XXXXX`) con el botón *Copiar* y envíelo a su proveedor (Jaime Blanco).",
   "El proveedor lo ingresa en el JB-Activador (Anexo A) y le devuelve un **código de activación** (`JBP1.…`) o un archivo `licencia.jbp`.",
   "Pegue el código en el recuadro y pulse **Activar**. La pantalla muestra «ACTIVADA», la entidad y el vencimiento. Queda registrado en la bitácora."])
P("**Instalación asistida por Sistemas:** si copia el archivo `licencia.jbp` a `C:\\ProgramData\\JB-Personal\\` y reinicia el servicio, la licencia se activa automáticamente.")
P("**Importante:** el código está ligado a **un equipo** (huella del identificador de la máquina). Si cambia de computadora, reinstala Windows o restaura en otro servidor, pida un código nuevo. "
  "Una licencia «multiequipo» (`*`) solo la emite el proveedor para casos especiales.")
IMG("ui_licencia.png", 15, "Figura 2. Pantalla «Licencia» con el código de equipo y el recuadro de activación.")
NOTE("La activación es una medida **disuasiva y de control comercial**: el código está firmado criptográficamente (Ed25519) y no puede falsificarse sin la clave privada del emisor, "
     "pero ninguna protección de un programa escrito en un lenguaje interpretado es infranqueable frente a un técnico con acceso total al equipo.", "Nota")

# ================================================================= 5
H("5. Primer ingreso y configuración inicial")
IMG("ui_login.png", 9, "Figura 3. Pantalla de ingreso con el logotipo.")
N(["**Crear el administrador:** la primera vez la pantalla pide usuario, contraseña (mínimo 8 caracteres) y nombre. Esta cuenta tiene todos los permisos.",
   "**Configuración → Datos institucionales:** nombre del municipio, sigla, código SIGEP, ciudad, Máxima Autoridad Ejecutiva, responsable de RR.HH., quien aprueba el informe y número del Reglamento Interno. Si quedan vacíos, el informe `.docx` mostrará marcadores como «[Nombre Completo]».",
   "**Configuración → Horario:** verifique turnos (por defecto 08:00–12:00 y 14:30–18:30), tolerancia (10 min) y umbral de retraso grave (30 min).",
   "**Configuración → Escala de sanción:** ajuste los tramos a su Reglamento Interno y elija si se aplica por minutos acumulados o por cantidad de retrasos.",
   "**Configuración → Reglas de cálculo:** factor de descuento por falta (×2 planta/eventual, ×1 consultor), días justificados libres del consultor (1) y tasas de aporte.",
   "**Feriados:** revise los feriados nacionales precargados 2026–2030 y agregue los locales.",
   "**Usuarios:** cree una cuenta por persona. ADMIN: todo · RRHH: opera personal, asistencia, permisos y reportes · CONSULTA: solo lectura y descargas.",
   "**Personal → Descargar plantilla Excel**, complétela y use **Importar**. La carga informa las filas con error sin detener las demás.",
   "**Licencia:** active el sistema (capítulo 4)."])

# ================================================================= 6
H("6. Importación de marcaciones de relojes de distintas marcas")
P("Cada fabricante (ZKTeco, Anviz, Dahua, Hikvision, Suprema y otros) exporta sus marcaciones con **una estructura diferente**: otros nombres de columna, la fecha y la hora juntas o separadas, "
  "otro delimitador, títulos antes de la tabla, o incluso una fila por día con varias horas. JB-Personal se adapta en tres niveles:")
T(["Nivel", "Cuándo usarlo", "Qué hace el sistema"], [
    ["1. Automático", "Archivos habituales", "Reconoce ZKTeco ATTLOG (`.dat`/`.txt` sin cabecera, con tabuladores o espacios) y archivos con cabecera `.csv`/`.txt`/`.xlsx` cuyas columnas se identifican por nombre en español o inglés (ID, Person ID, Employee No, Fecha, Date, Hora, Time, Date/Time, Estado, Dispositivo…). Busca la cabecera en las primeras 25 filas y la hoja correcta del Excel"],
    ["2. Perfil de mapeo", "El automático no reconoce el archivo o lo interpreta mal", "**Analizar estructura**: usted indica qué columna es cada dato, el delimitador, la fila de cabecera y el orden de la fecha; puede **guardar un perfil** con el nombre del reloj y reutilizarlo en cada importación"],
    ["3. Estructura ancha", "El archivo trae **una fila por persona y día** con columnas Entrada1, Salida1, Entrada2, Salida2…", "Cada columna de hora con valor se convierte en una marca; los textos como «SIN MARCA» se omiten sin error"],
], [3, 4.7, 8.8], size=8.5)
H("Procedimiento", 3)
N(["Menú **Marcaciones**: elija el archivo del reloj. Con «Perfil: Automático» pulse **Importar**. Si el archivo se reconoce, verá *leídas / nuevas / duplicadas / rechazadas*.",
   "Si aparece «No se reconoció la estructura del archivo», o los datos salen mal, pulse **Analizar estructura…**. Se abre el asistente con el contenido del archivo (primeras filas).",
   "En el asistente: elija la **estructura** (una marca por fila / varias horas por fila), el **delimitador**, la **fila de cabecera** (0 si el archivo no tiene títulos) y el **orden de fecha** (día/mes/año, mes/día/año o año/mes/día). Si es un Excel con varias hojas, elija la hoja.",
   "En «¿Qué columna es cada dato?» seleccione el **ID del empleado** (obligatorio) y la **fecha y hora** (juntas) o **fecha** y **hora** por separado. Opcionales: tipo de marcación, método y dispositivo. En estructura ancha seleccione varias columnas de hora con Ctrl.",
   "Pulse **Probar interpretación**: muestra cuántas marcas se leyeron, ejemplos y las filas rechazadas, **sin guardar nada**. Ajuste hasta que sea correcto.",
   "Escriba un **nombre** (ej. «Anviz oficina central») y pulse **Guardar perfil**. Desde entonces aparece en la lista «Perfil» y se usa con un clic.",
   "Pulse **Importar con esta configuración**."])
IMG("ui_asistente.png", 15.5, "Figura 4. Asistente de estructura con un archivo de columnas desconocidas, estructura «varias horas por fila» y la prueba de interpretación.")
T(["Campo del asistente", "Significado"], [
    ["ID / código del empleado", "Debe coincidir con el «Código (ID reloj)» del empleado en Personal. Los ceros a la izquierda se ignoran (0007 = 7)"],
    ["Fecha y hora (juntas)", "Una sola columna con ambos datos (p. ej. `2026-10-01 08:02:05` o `01/10/2026 8:02 a. m.`)"],
    ["Fecha / Hora (separadas)", "Dos columnas; la hora admite `08:02`, `08:02:05` y formato AM/PM"],
    ["Formato propio de fecha-hora", "Solo para formatos raros, con códigos de Python: `%Y%m%d-%H%M%S`, `%d.%m.%y %H:%M`…"],
    ["Fila de cabecera", "Número de la fila con los títulos (los datos empiezan en la siguiente). 0 = el archivo no tiene títulos"],
    ["Columnas de hora (ancha)", "Todas las columnas que contienen una hora de marcación en la fila del día"],
], [5, 11.5], size=8.5)
NOTE("Las marcas importadas **no se pueden editar** (inalterabilidad). Un archivo repetido se rechaza y las marcas duplicadas (mismo ID, fecha-hora y dispositivo) se descartan, "
     "aunque lleguen en otro formato de archivo. La columna «Estado/Incidencia» que algunos relojes calculan se ignora: el sistema recalcula con sus propias reglas.", "Nota")
P("**Limitación:** los formatos Anviz, Dahua, Hikvision y Suprema se cubren por los nombres de columna habituales, pero **no se probaron con exportaciones reales de esos equipos**. Si un modelo exporta otra estructura, el asistente lo resuelve sin programar.")

# ================================================================= 7
H("7. Operación mensual y reportes")
N(["**Importar marcaciones** (capítulo 6). Revise «identificadores del reloj sin servidor asociado»: son códigos sin persona registrada; corrija el código en Personal.",
   "**Registrar permisos, licencias y vacaciones** (Permisos y boletas → Nueva solicitud). Se genera la boleta PDF con correlativo. Los permisos de consultores requieren «Autorizado por» (fiscal de servicio).",
   "**Registrar altas y bajas** (Personal): las bajas piden fecha efectiva y causal (renuncia, conclusión de contrato, destitución…).",
   "**Inicio / Planilla:** revise la liquidación individual y **Asistencia diaria** (colores por estado). El botón *Procesar periodo* recalcula a pedido.",
   "**Reportes:** descargue los 6 documentos. **Los reportes de un periodo abierto se recalculan automáticamente al descargarse**, de modo que siempre reflejan al personal, marcas y permisos más recientes. Para el informe oficial marque «Emitir con N° correlativo» (consume número).",
   "**Instructivos:** cree el instructivo (cite automático), emítalo y registre la notificación de cada destinatario.",
   "**Cerrar periodo** cuando las planillas estén aprobadas: bloquea importaciones, permisos y reproceso y **congela** los resultados. Reabrir exige rol ADMIN y un motivo, que queda en la bitácora.",
   "**Respaldo** del mes (capítulo 8)."])
IMG("ui_asistencia.png", 15.5, "Figura 5. Asistencia diaria: amarillo = retraso leve, naranja = grave, rojo = falta, azul = justificada, gris = no laborable.")
T(["N°", "Reporte", "Formato", "Contenido"], [
    ["1", "Informe de asistencia", ".docx", "Informe técnico editable (membrete, antecedentes, marco normativo, resumen, atrasos, vacaciones, licencias, faltas, omisiones, conclusiones y firmas)"],
    ["2", "Planilla de nuevo personal", ".xlsx", "Altas del periodo: designación/contrato, partida, vigencia, días trabajados y líquido"],
    ["3", "Planilla de desvinculados", ".xlsx", "Bajas del periodo con causal y fecha efectiva"],
    ["4", "Planilla de sueldos y salarios", ".xlsx", "Por modalidad (Permanente, Eventual, Consultores) con subtotales, total general y hoja *Resumen*"],
    ["5", "Reporte detallado de asistencia", ".xlsx", "Resumen institucional, detalle diario, faltas y retrasos, leyenda de reglas"],
    ["6", "Consolidado para auditoría (UAI/CGE)", ".txt/.csv UTF-8 y **.xlsx**", "Una fila por servidor: periodo, C.I., código, tipo de contrato, días laborables, asistidos, faltas, minutos de retraso, días justificados e importe de descuentos. El `.xlsx` es **plano: solo títulos de columna y datos** (sin membrete, celdas combinadas ni estilos); C.I. y código van como texto y las cifras como números"],
], [0.9, 4.2, 2.8, 8.6], size=8.5)
IMG("ui_reportes.png", 15.5, "Figura 6. Pantalla «Reportes y planillas» (el consolidado 6 ofrece .txt/.csv y .xlsx).")
NOTE("Si una planilla sale sin empleados, el mensaje indica la causa: «No hay personal con contrato vigente en el mes». Verifique en Personal que la **fecha de ingreso** del contrato sea anterior o dentro del mes y que la baja no sea anterior al mes.", "Nota")

# ================================================================= 8
H("8. Respaldos y recuperación")
P("El respaldo es un script SQL **cifrado con AES-256-GCM** (clave derivada de su contraseña). Junto a cada archivo `...sql.enc` se escribe `...sql.enc.sha256`. "
  "En el instalador de Windows los respaldos van por defecto a `C:\\ProgramData\\JB-Personal\\backups`.")
NOTE("Anote la contraseña de cifrado en un sobre sellado y guárdelo en un lugar seguro. **Sin ella el respaldo no se puede abrir.** Aplique la regla 3-2-1: 3 copias, 2 medios distintos, 1 fuera de la oficina.", "Importante")
T(["Cuándo", "Cómo"], [
    ["Manual", "Menú **Respaldos** → contraseña → **Crear respaldo**. En «Destino» puede indicar una unidad USB (p. ej. `E:\\Respaldos`) o una ruta de red accesible para el servicio; también puede descargarlo"],
    ["Programado (Windows)", "Defina la variable de **sistema** `GAM_BACKUP_PASSWORD` y, en una consola de administrador: `schtasks /create /tn \"JB Respaldo\" /tr \"\\\"C:\\Program Files\\JB-Personal\\desktop\\respaldo_programado.bat\\\"\" /sc daily /st 18:45 /ru SYSTEM`"],
    ["Programado (Linux)", "cron: `45 18 * * * jb ... python -m app.cli backup && python -m app.cli retencion --dias 90`"],
    ["Verificar (mensual)", "Respaldos → **Verificar integridad** (archivo + hash + contraseña) o `python -m app.cli verificar ARCHIVO.sql.enc`"],
    ["Restaurar", "Respaldos → **Restaurar** (solo ADMIN). Exige el SHA-256 de referencia y la contraseña; si no coinciden, **no restaura**. En SQLite se guarda antes una copia del estado actual; en PostgreSQL se ejecuta en una sola transacción"],
], [3.5, 13])
P("**Prueba de recuperación:** al menos una vez por trimestre restaure un respaldo en una PC de prueba y compare el total de empleados y el último registro de la bitácora. "
  "El respaldo incluye el estado de la licencia, por lo que restaurarlo en **otro** equipo requerirá un código de activación nuevo.")

# ================================================================= 9
H("9. Guía de pruebas con casos reales")
H("9.1 Pruebas automáticas", 2)
CODE("""cd jb-personal/backend
pip install -r requirements-dev.txt
python -m pytest tests -q                       # SQLite  -> %d passed
# PostgreSQL (base VACÍA):
GAM_DATABASE_URL=postgresql+psycopg://usuario@host/base_vacia python -m pytest tests -q""" % NTEST)
P(f"Son {NTEST} pruebas: motor de reglas, lector de marcaciones, **estructuras de distintas marcas de reloj**, flujo completo (importación, permisos, procesamiento, 6 reportes, cierre de periodo, bitácora inalterable, "
  "respaldo y restauración, roles, inyección de fórmulas), **regresión de planillas con todos los empleados**, **licencia (códigos válidos, de otro equipo, vencidos, alterados; prueba y modo solo lectura)** y el **JB-Activador**.")
H("9.2 Dataset de prueba", 2)
P("Datos **ficticios** de **octubre de 2026** (22 días hábiles, sin feriados nacionales). Carpeta `datos_prueba/` (instalada en `C:\\Program Files\\JB-Personal\\datos_prueba`):")
T(["Archivo", "Contenido"], [
    ["personal.csv", "5 servidores: 2 permanentes, 2 eventuales, 1 consultor en línea"],
    ["biometrico_octubre_2026.csv / .dat / .xlsx", "Las mismas 408 marcas en tres formatos (delimitado, ZKTeco ATTLOG y Excel con el diseño «1_Marcaciones_Crudas»)"],
    ["permisos_octubre_2026.csv", "6 permisos (5 aprobados y 1 pendiente)"],
    ["cargar_dataset.py", "Carga todo por la API y descarga los 6 reportes (requiere `pip install httpx`)"],
], [6.5, 10])
T(["Servidor", "Modalidad / haber", "Incidencias sembradas"], [
    ["1001 Mamani Quispe Juan Carlos", "Permanente 6.000", "06/10 entra 08:12 (12 min) · 20/10 14:48 (18 min) · 14/10 sin marca de salida de la mañana (omisión)"],
    ["1002 Vargas Rojas María Elena", "Permanente 4.500", "02/10 08:25 (25 min) · 07/10 08:45 (45 min, grave) · 15/10 falta de día completo"],
    ["2001 Choque Condori Luis Alberto", "Eventual 3.800", "12–13/10 licencia médica · 21/10 permiso 08:00–10:00 y llega 10:05 (retraso cubierto) · 28/10 sin marcas en la tarde (media falta)"],
    ["2002 Flores Apaza Carla Andrea", "Eventual 3.500 (alta 01/10)", "09/10 permiso sin goce · 14/10 14:52 (22 min) · 22/10 sin marca de entrada de la tarde"],
    ["3001 Salazar Copa Miguel Ángel", "Consultor 7.000 (concluye 30/10)", "08/10 y 19/10 dos días justificados con fiscal · 13/10 08:50 (50 min, grave) · 27/10 permiso PENDIENTE (no justifica)"],
], [4.6, 3.6, 8.3], size=8.5)
H("9.3 Procedimiento", 2)
N(["Cree el administrador y complete **Configuración** (nombre, sigla, ciudad, responsables).",
   "**Personal → Importar** `personal.csv` → *Creados: 5 · Errores: 0*.",
   "**Marcaciones → Importar** `biometrico_octubre_2026.dat` → *leídas 408, nuevas 408, duplicadas 0, rechazadas 0*. Luego importe el `.csv`: *nuevas 0, duplicadas 408*. Reimportar el mismo archivo debe rechazarse.",
   "**Permisos → Nueva solicitud**: registre las 6 filas de `permisos_octubre_2026.csv`. Compruebe la boleta PDF y que aprobar el permiso del consultor **sin** «Autorizado por» se rechaza.",
   "**Reportes** (mes *Octubre 2026*): descargue los 6 (se recalculan solos) y compare con 9.4. Alternativa por script: `python datos_prueba/cargar_dataset.py --url http://127.0.0.1:8765 --clave 'SuClave#2026' --salida reportes_prueba`."])
H("9.4 Resultados esperados (calculados a mano)", 2)
P("Descuento = `haber ÷ 30 × días de descuento`. Falta injustificada de planta/eventual = ×2; consultor = ×1. Aporte laboral = 12,71 % del total ganado.")
T(["Servidor", "Faltas", "Min. retraso", "Días desc.", "Total ganado", "AFP", "Desc. asist.", "Líquido"], [
    ["1001 Mamani", "0", "30", "0", "6.000,00", "762,60", "0,00", "**5.237,40**"],
    ["1002 Vargas", "1", "70", "2,5 (1×2 + 0,5)", "4.500,00", "571,95", "375,00", "**3.553,05**"],
    ["2001 Choque", "0,5", "0", "1 (0,5×2)", "3.800,00", "482,98", "126,67", "**3.190,35**"],
    ["2002 Flores", "0", "22", "1 (sin goce)", "3.500,00", "444,85", "116,67", "**2.938,48**"],
    ["3001 Salazar", "1", "50", "2 (falta + exceso)", "7.000,00", "0,00", "466,66", "**6.533,34**"],
    ["**TOTAL**", "", "", "", "**24.800,00**", "**2.262,38**", "**1.085,00**", "**21.452,62**"],
], [3.1, 1.3, 1.7, 2.8, 2.2, 1.7, 1.9, 2.2], size=8)
P("Control de cruce: 24.800,00 − 2.262,38 − 1.085,00 = 21.452,62. Sanciones por retrasos: Vargas → descuento de 0,5 día (70 min); Salazar → amonestación escrita (50 min); Mamani (30 min) y Flores (22 min) → sin sanción.")
T(["N°", "Reporte", "Resultado esperado"], [
    ["1", "Informe (.docx)", "Periodo «Del 01 al 31 de octubre de 2026 (22 días hábiles)». Resumen: 5 servidores / 110 días-hombre; asistencia regular 94 días (85,45 %); con atrasos 4 (172 min); licencias con goce 2 servidores / 3 días; permisos 2 / 2 días; faltas 3 / 2,5 días. Atrasos (Vargas, Salazar, Mamani, Flores), faltas (Vargas, Choque, Salazar), omisiones (Mamani 14/10, Flores 22/10). Sin abandono de funciones"],
    ["2", "Nuevo personal", "1 fila: Flores Apaza Carla Andrea, ingreso 01/10/2026, Eventual, partida 12100, vigencia 31/12/2026, líquido 2.938,48"],
    ["3", "Desvinculados", "1 fila: Salazar Copa Miguel Ángel, baja 30/10/2026, «Conclusión de contrato», líquido 6.533,34"],
    ["4", "Sueldos y salarios", "Permanentes (2; ganado 10.500,00; líquido 8.790,45), Eventuales (2; 7.300,00; 6.128,83), Consultores (1; 7.000,00; 6.533,34). **Total general 24.800,00 / 21.452,62**. Deben verse los 5 empleados con nombre, C.I. y cargo"],
    ["5", "Detallado (.xlsx)", "Resumen institucional (5 filas), detalle diario de 154 filas, 16 imputaciones (4 retrasos leves, 2 graves, 3 faltas injustificadas, 5 justificadas, 2 omisiones), leyenda"],
    ["6a", "Consolidado .txt", "5 filas separadas por tabulador, p. ej. `2026-10 1000002 1002 PERMANENTE 22 21.00 1.00 70 0.00 375.00`"],
    ["6b", "Consolidado .xlsx", "Hoja «Consolidado»: fila 1 con los 10 títulos y 5 filas de datos, **sin** membrete, combinadas ni formato; los mismos valores que el `.txt`"],
], [0.9, 3.2, 12.4], size=8.5)
H("9.5 Pruebas de estructuras de reloj", 2)
T(["Archivo de prueba", "Esperado"], [
    ["`datos_prueba/biometrico_octubre_2026.dat` (ZKTeco ATTLOG)", "Autodetectado: 408 marcas"],
    ["`.csv` con cabeceras `Employee ID, Name, Authentication Date and Time` o `Person ID, Name, Time` o `No; Nombre; Fecha/Hora`", "Autodetectado (el ID `007` se lee como 7)"],
    ["Texto `Cod|Dia|E1|S1|E2|S2` con filas `1001|01/09/2026|08:02|12:01|14:28|18:33`", "No se autodetecta → asistente: estructura *varias horas por fila*, ID = col. 1, fecha = col. 2, horas = col. 3–6, cabecera = fila 1 → **7 marcas** en el ejemplo de 2 días, 0 rechazadas; guardar perfil e importar"],
    ["Excel con títulos, una hoja «Resumen» y la hoja «Marcaciones» con cabecera en la fila 3", "Detecta la hoja y la fila de cabecera"],
    ["Fila con fecha inválida (`no-es-fecha`)", "Se rechaza solo esa fila; las demás se importan"],
], [8.2, 8.3], size=8.5)
H("9.6 Pruebas negativas y de control", 2)
T(["Acción", "Resultado esperado"], [
    ["Aprobar permiso de consultor sin «Autorizado por»", "Error: debe ser autorizado por el fiscal de servicio"],
    ["Reimportar el mismo archivo biométrico", "Error: «ya fue importado (lote N)»"],
    ["Generar un reporte de un mes sin personal con contrato", "Error claro: «No hay personal con contrato vigente…»"],
    ["Cargar personal **después** de procesar y descargar la planilla", "La planilla incluye a todos (se recalcula)"],
    ["Cerrar el periodo y luego importar, registrar permiso o reprocesar", "Bloqueado; reabrir exige ADMIN y motivo de 10+ caracteres"],
    ["Modificar o borrar la bitácora, o modificar una marca, directamente en la base", "La base lo rechaza (triggers)"],
    ["Alterar un byte de un respaldo, usar hash o contraseña incorrectos", "Verificación y restauración fallan sin tocar los datos"],
    ["Ingresar un código de activación de otro equipo, vencido, alterado o basura", "Error con mensaje claro; no activa"],
    ["Prueba vencida (o licencia vencida) y se intenta procesar o generar reportes", "Error 402 con mensaje de licencia; consultas y respaldos siguen funcionando"],
    ["Usuario CONSULTA intenta procesar, respaldar o activar", "Acceso denegado (403)"],
    ["Importar personal con nombre «=HYPERLINK(...)» o C.I. con símbolos", "El nombre sale como texto en los Excel; el C.I. con símbolos se rechaza"],
], [7.5, 9])
H("9.7 Lista de aceptación (instalación en PC nueva)", 2)
T(["☐", "Verificación", "Resultado"], [
    ["☐", "El instalador se ejecuta con permisos de administrador y termina sin errores", ""],
    ["☐", "Existe la tarea «JB-Personal» (`schtasks /Query /TN \"JB-Personal\"`) y `http://127.0.0.1:8765/` carga con el logotipo y la paleta cálida", ""],
    ["☐", "**Reiniciar el equipo SIN iniciar sesión:** desde otra PC (con acceso de red habilitado) la pantalla de ingreso carga; o el registro `servicio.log` muestra el arranque previo al inicio de sesión", ""],
    ["☐", "Cerrar la sesión de Windows no detiene el sistema", ""],
    ["☐", "Se crea el administrador y la pestaña/menú muestran «JB-Personal»", ""],
    ["☐", "Licencia: aparece el código de equipo; un código emitido con el JB-Activador activa el sistema", ""],
    ["☐", "Importación del dataset: 5 servidores y 408 marcas", ""],
    ["☐", "Importar el archivo de estructura desconocida con el asistente y guardar el perfil", ""],
    ["☐", "Totales de octubre 2026: 24.800,00 / 2.262,38 / 1.085,00 / 21.452,62", ""],
    ["☐", "Los 7 archivos de reportes (incluido el consolidado .xlsx) se descargan y abren; las planillas muestran a los 5 empleados", ""],
    ["☐", "Se crea un respaldo, se verifica su integridad y se restaura en la PC de prueba", ""],
    ["☐", "Reinstalar sobre la versión existente conserva los datos y la licencia", ""],
    ["☐", "Desinstalar elimina programa, servicio y regla de firewall, y conserva `C:\\ProgramData\\JB-Personal`", ""],
], [1, 11.3, 4.2], size=8.5)
P("Antes de usar datos reales, **borre los datos de prueba**: desinstale, elimine `C:\\ProgramData\\JB-Personal` y vuelva a instalar (la licencia deberá activarse otra vez), o use otra PC para las pruebas.")

# ================================================================= 10
H("10. Seguridad")
B(["Un usuario por persona; no comparta la cuenta `admin`. Use el rol CONSULTA para auditoría interna.",
   "Contraseñas almacenadas con scrypt; sesión de 10 horas; bloqueo de 5 minutos tras 5 intentos fallidos.",
   "El servicio escucha por defecto **solo en la propia PC** (`127.0.0.1`). Habilite el acceso de red únicamente si lo necesita; el tráfico no está cifrado (HTTP): use una red interna confiable, VPN o un proxy con HTTPS.",
   "El servicio corre como SYSTEM: la carpeta de programa (Archivos de programa) no es modificable por usuarios comunes; los datos están en ProgramData.",
   "En servidor Linux use HTTPS y defina su propia `GAM_SECRET_KEY`.",
   "La bitácora está encadenada por hash: use **Auditoría → Verificar integridad de la cadena** una vez al mes.",
   "Las marcas biométricas son inalterables; los periodos cerrados no admiten cambios.",
   "**JB-Activador:** la clave privada permite emitir licencias; guárdela cifrada y con copia fuera de línea. Nunca la suba a un repositorio ni la entregue a las entidades."])

# ================================================================= 11
H("11. Solución de problemas")
T(["Síntoma", "Causa probable y solución"], [
    ["El navegador dice «127.0.0.1 rechazó la conexión» (ERR_CONNECTION_REFUSED)", "El servicio no está en ejecución. Ejecute **menú Inicio → JB-Personal → Diagnostico (si no abre)**: muestra el estado de la tarea, los últimos fallos (`logs\\fallos.log`) y arranca el sistema en esa ventana para ver el error. Versiones anteriores a 1.1.1 fallaban si `config.ini` traía una marca BOM: actualice con el instalador nuevo"],
    ["El navegador no abre `http://127.0.0.1:8765/` (otros casos)", "Inicie el servicio: menú Inicio → JB-Personal → Administrar el servicio → 1. Revise `C:\\ProgramData\\JB-Personal\\logs\\servicio.log`. Si el puerto 8765 está ocupado, cambie `port` en `config.ini`"],
    ["El instalador dice que el servicio no respondió a tiempo", "Revise el registro; suele ser un antivirus bloqueando `pythonw.exe` o el puerto en uso. Agregue una excepción para `C:\\Program Files\\JB-Personal`"],
    ["Otras PC no acceden", "Ejecute el acceso directo «Habilitar acceso desde la red» (o ponga `host = 0.0.0.0` en `config.ini`, reinicie el servicio y cree la regla de firewall del puerto 8765). Pruebe con la IP del equipo, no con `127.0.0.1`"],
    ["Windows SmartScreen bloquea el instalador", "Más información → Ejecutar de todas formas (no está firmado). La institución puede firmarlo con su certificado de código"],
    ["«Periodo de prueba terminó» / error 402", "El sistema está en solo lectura. Active la licencia (capítulo 4). Los datos están intactos y se puede respaldar"],
    ["«Este código fue emitido para OTRO equipo»", "El código de equipo cambió (otra PC o reinstalación de Windows). Envíe el código de equipo actual para recibir uno nuevo"],
    ["Importación de marcas: «No se reconoció la estructura»", "Use «Analizar estructura…» y mapee las columnas (capítulo 6)"],
    ["Importación: «0 nuevas»", "Las marcas ya estaban cargadas. Es normal al reimportar"],
    ["Marcas de una persona no aparecen en el cálculo", "Revise «identificadores sin servidor asociado»: el código del reloj debe coincidir con el «Código» de Personal"],
    ["Fechas con día y mes invertidos", "En la importación (o en el perfil) elija el orden «mes/día/año»"],
    ["Una planilla sale sin empleados", "Lea el mensaje: no hay contratos vigentes en el mes. Corrija las fechas de ingreso/baja en Personal y descargue de nuevo"],
    ["El informe .docx muestra «[Nombre Completo]»", "Complete Configuración → Datos institucionales y vuelva a descargar"],
    ["«Periodo CERRADO»", "Un ADMIN debe reabrirlo indicando el motivo"],
    ["Restauración falla: «Falla de integridad SHA-256»", "El archivo cambió o el hash corresponde a otro respaldo; use el `.sha256` original"],
    ["Olvidó la contraseña de un respaldo", "No hay forma de recuperarlo (cifrado AES-256). Por eso se guarda en sobre sellado"],
], [5.5, 11])

# ================================================================= 12
H("12. Supuestos legales y limitaciones conocidas")
NOTE("Los valores siguientes se tomaron de los documentos de ejemplo del municipio y de la especificación del sistema; **no se verificaron contra la normativa vigente**. "
     "La Unidad Jurídica debe validarlos antes de aplicarlos a planillas reales. Todos son editables en Configuración.", "Atención")
T(["Tema", "Valor usado", "Origen"], [
    ["Descuento por falta injustificada", "Doble del haber diario (Art. 22 D.S. 25749)", "Informe tipo adjunto"],
    ["Tolerancia y jornada", "10 minutos; 08:00–12:00 y 14:30–18:30", "Informe tipo"],
    ["Escala por minutos: tramo 46–60", "Amonestación escrita", "Supuesto del desarrollo (el informe tipo no lo define)"],
    ["Escala por cantidad de retrasos", "1–3 / 4–6 / 7 o más", "Ejemplo ilustrativo de la especificación"],
    ["Aportes", "Laboral 12,71 %; patronal 17,21 % (informativo)", "Planilla de remuneración adjunta"],
    ["Consultor en línea", "1 día justificado al mes sin descuento, con autorización del fiscal", "Especificación"],
    ["Licencias de luto, matrimonio, cumpleaños, lactancia", "Sin tope (según el RIP)", "No se inventaron plazos"],
    ["Feriados 2026–2030", "Calculados automáticamente", "Verificar cada año los decretos (p. ej. Carnaval)"],
], [5, 6, 5.5], size=8.5)
P("**Limitaciones:**")
B(["El instalador de Windows (servicio) y el JB-Activador instalable **no pudieron ejecutarse en Windows durante el desarrollo**: pruébelos en una PC piloto (lista 9.7).",
   "El servicio usa una tarea programada de arranque (SYSTEM), no un servicio SCM nativo: no aparece en `services.msc` sino en el Programador de tareas, aunque se comporta igual (arranque sin sesión y reinicio automático).",
   "El acceso desde la red local es HTTP sin cifrar; para redes no confiables use VPN o un proxy con HTTPS.",
   "Los formatos Anviz/Dahua/Hikvision/Suprema se cubren por nombres de columna habituales y por el asistente de mapeo; no se probaron con exportaciones reales.",
   "La licencia es disuasiva: no impide que un técnico con acceso total modifique el programa.",
   "Un servidor liquida con un solo contrato por mes (el de inicio más reciente); un cambio de haber a mitad de mes no se prorratea.",
   "Los saldos de vacaciones no se calculan: gestión y saldo se registran como texto informativo.",
   "No se calculan retenciones de consultores (IT/IVA) ni bono de antigüedad automático: bono y RC-IVA son datos de entrada.",
   "Un retorno del almuerzo antes de las 13:15 se interpreta como salida de la mañana y se marca como omisión para su regularización."])

# ================================================================= ANEXO A
SALTO()
H("Anexo A. Manual del JB-Activador (emisor de licencias)")
NOTE("Este anexo es **solo para el emisor** (Jaime Blanco). El JB-Activador y su clave privada **no se entregan a las entidades**.", "Confidencial")
H("A.1 Qué es y cómo funciona", 2)
P("El JB-Activador es una herramienta externa e independiente de JB-Personal. Con una **clave privada Ed25519** firma un «código de activación» que contiene: producto, nombre de la entidad, "
  "**código de equipo** del cliente, fecha de emisión y vencimiento (o sin vencimiento). JB-Personal solo contiene la **clave pública**: puede **verificar** licencias pero no **emitirlas**. "
  "Cualquier cambio en el código (otra entidad, otra fecha) invalida la firma.")
H("A.2 Instalación", 2)
N(["Ejecute **JBActivador_Setup.exe** (no requiere administrador). Crea el acceso directo «JB-Activador» en el escritorio.",
   "Si el instalador fue construido con la clave privada, queda lista; en caso contrario, al primer uso se **genera una clave nueva** y el programa muestra su clave pública (ver A.5).",
   "La clave y el historial se guardan en `%APPDATA%\\JB-Activador` (`clave_privada.pem`, `emitidas.csv`) y **no se borran al desinstalar**."])
H("A.3 Emitir una licencia", 2)
N(["Abra **JB-Activador**: se abre una página local en su navegador (`http://127.0.0.1:…`, protegida con un token y accesible solo desde su PC).",
   "Escriba el **nombre de la entidad** y pegue el **código de equipo** que le envió el cliente (`JBP-XXXXX-XXXXX-XXXXX`).",
   "Elija la **vigencia**: sin vencimiento (perpetua), por cantidad de días o hasta una fecha.",
   "Pulse **Emitir código de activación**. Copie el código (`JBP1.…`) o use **Descargar licencia.jbp**, y envíelo al cliente por correo o mensajería.",
   "El historial muestra las licencias emitidas (fecha, entidad, equipo, vencimiento y una huella del código; el código completo no se guarda). Pulse **Cerrar el activador** al terminar."])
IMG("ui_licencia.png", 14, "Figura A1. Del lado del cliente: la pantalla Licencia donde se pega el código emitido.")
H("A.4 Línea de comandos", 2)
CODE("""python jb_activador.py --emitir --entidad "GAM Villa Ejemplo" --equipo JBP-AAAAA-BBBBB-CCCCC --dias 365
python jb_activador.py --emitir --entidad "GAM Villa Ejemplo" --equipo JBP-AAAAA-BBBBB-CCCCC          # sin vencimiento
python jb_activador.py --emitir --entidad "GAM Villa Ejemplo" --equipo JBP-AAAAA-BBBBB-CCCCC --vence 2027-12-31
python jb_activador.py --publica                 # muestra la clave pública
python jb_activador.py --nueva-clave             # ¡invalida las licencias firmadas con la clave anterior!""")
H("A.5 Clave privada: cuidados y cambio de clave", 2)
B(["**Respalde** `%APPDATA%\\JB-Activador\\clave_privada.pem` en un medio cifrado y fuera de línea. Si la pierde, no podrá emitir licencias verificables por las instalaciones existentes.",
   "**No la comparta ni la suba a GitHub.** Quien la tenga puede emitir licencias válidas.",
   "El instalador de ejemplo entregado con esta versión incluye una clave generada durante el desarrollo; **recomendamos generar su propia clave** antes de comercializar: "
   "ejecute `--nueva-clave`, copie la clave pública mostrada en `backend/app/licencia_publica.py` (`CLAVE_PUBLICA_B64`), reconstruya `JBPersonal_Setup.exe` y reemita las licencias.",
   "Las licencias son por equipo: si el cliente cambia de computadora, emita un código nuevo con su nuevo código de equipo."])
H("A.6 Formato del código (referencia técnica)", 2)
P("`JBP1.<datos>.<firma>`: `<datos>` es un JSON compacto en base64url `{\"p\":\"JB-Personal\",\"e\":entidad,\"m\":código de equipo o \"*\",\"i\":emisión,\"v\":vencimiento o null}`; "
  "`<firma>` es la firma Ed25519 de esos bytes. El código de equipo es `JBP-` + 15 hex del SHA-256 de «JB-Personal|MachineGuid» (registro de Windows o `/etc/machine-id`).")

# ================================================================= ANEXO B
H("Anexo B. Rutas, puertos y archivos")
T(["Elemento", "Windows (instalador)", "Linux (servidor)"], [
    ["Programa", "`C:\\Program Files\\JB-Personal`", "`/opt/jb/app/jb-personal`"],
    ["Datos y base de datos", "`C:\\ProgramData\\JB-Personal\\gam_personal.db`", "`$GAM_DATA_DIR/gam_personal.db`"],
    ["Respaldos", "`C:\\ProgramData\\JB-Personal\\backups`", "`$GAM_BACKUP_DIR`"],
    ["Registro del servicio", "`C:\\ProgramData\\JB-Personal\\logs\\servicio.log`", "`journalctl -u jb-personal`"],
    ["Configuración", "`C:\\ProgramData\\JB-Personal\\config.ini` (host, port)", "Variables `GAM_*` en `/etc/jb-personal.env`"],
    ["Licencia (archivo opcional)", "`C:\\ProgramData\\JB-Personal\\licencia.jbp`", "`$GAM_DATA_DIR/licencia.jbp`"],
    ["Puerto", "8765 (configurable)", "8000 detrás de un proxy HTTPS"],
    ["Servicio", "Tarea programada «JB-Personal»", "Unidad `jb-personal.service`"],
    ["Manuales", "`C:\\Program Files\\JB-Personal\\docs`", "`jb-personal/docs`"],
], [4, 6.6, 5.9], size=8.5)

doc.save(AQUI / "Manual_JB-Personal.docx")
print("Word:", AQUI / "Manual_JB-Personal.docx")
if shutil.which("soffice"):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(AQUI), str(AQUI / "Manual_JB-Personal.docx")],
                   check=True, capture_output=True, timeout=240)
    print("PDF:", AQUI / "Manual_JB-Personal.pdf")
else:
    print("LibreOffice no disponible: convierta el .docx a PDF desde Word (Guardar como PDF).")
