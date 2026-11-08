#!/usr/bin/env python3
"""Genera el Manual de Implementación, Instalación y Pruebas (Word + PDF).

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
AZUL = RGBColor(0x1B, 0x36, 0x5D)
VERSION = "1.0.0"
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
    B(items, "List Number")


def CODE(txt):
    t = doc.add_table(rows=1, cols=1)
    borders(t, "CCCCCC")
    c = t.rows[0].cells[0]
    shade(c, "F3F5F8")
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
    borders(tb, "E0A800" if tipo != "Nota" else "2C7BE5")
    c = tb.rows[0].cells[0]
    shade(c, "FFF8E1" if tipo != "Nota" else "EAF2FD")
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
        shade(c, "1B365D")
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
                shade(cells[i], "F7F9FC")
    if anchos:
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
    r = p.add_run("Gestión de Personal y Asistencia Municipal · Manual v" + VERSION + " · Página ")
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
for _ in range(6):
    P()
P("ESTADO PLURINACIONAL DE BOLIVIA", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=11, color=RGBColor(0x55, 0x55, 0x55))
P("GESTIÓN DE PERSONAL Y ASISTENCIA MUNICIPAL", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=26, color=AZUL)
P("Manual de implementación, instalación y pruebas", align=WD_ALIGN_PARAGRAPH.CENTER, size=16, color=AZUL)
P()
P(f"Versión {VERSION}", align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
P("Modalidad Web y Escritorio (Windows 10 o superior)", align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
for _ in range(8):
    P()
P("Documento de uso interno · Unidad de Recursos Humanos / Unidad de Sistemas", align=WD_ALIGN_PARAGRAPH.CENTER, size=9, color=RGBColor(0x55, 0x55, 0x55))
SALTO()

# ================================================================= CONTENIDO
H("Contenido")
for t in ["1. Introducción", "2. Requisitos", "3. Instalación (instalador sencillo para Windows · servidor web · PostgreSQL · construir el instalador)",
          "4. Primer ingreso y configuración inicial", "5. Operación mensual paso a paso", "6. Respaldos y recuperación",
          "7. Guía de pruebas con casos reales (dataset, resultados esperados, lista de aceptación)", "8. Seguridad", "9. Solución de problemas",
          "10. Supuestos legales y limitaciones conocidas"]:
    P(t)
SALTO()

# ================================================================= 1
H("1. Introducción")
P("El sistema administra el personal de un Gobierno Autónomo Municipal (GAM): **permanente**, **eventual** y **consultores individuales de línea**. "
  "Importa las marcaciones del reloj biométrico, calcula atrasos, faltas y permisos, y genera las planillas e informes mensuales.")
T(["Módulo", "Qué hace"], [
    ["A. Institucional", "Datos del municipio, horarios y tolerancias, escala de sanción por retrasos, feriados, carga masiva de personal (Excel/CSV)"],
    ["B. Biometría y asistencia", "Lee archivos ZKTeco (.dat/.txt), CSV y Excel; cruza con el horario y clasifica cada día: normal, retraso leve/grave, falta justificada/injustificada, omisión"],
    ["C. Permisos e instructivos", "Solicitudes con boleta PDF y correlativo; instructivos con cite oficial (GAM-RRHH-INST-001/2026), destinatarios y notificación"],
    ["D. Reportes", "Informe de asistencia (.docx), planilla de nuevo personal, planilla de desvinculados, planilla de sueldos, reporte detallado (.xlsx) y consolidado plano UTF-8 para auditoría"],
    ["Transversal", "Usuarios y roles, bitácora inalterable, cierre de periodo, respaldos cifrados con verificación SHA-256"],
], [4, 12.5])
P("**Dos modalidades con el mismo código y las mismas reglas:** (1) *Escritorio*: se instala en una PC con Windows 10 o superior y guarda todo localmente; "
  "(2) *Web*: se instala en un servidor y se usa desde el navegador de varias PC.")
IMG("ui_inicio.png", 16, "Figura 1. Pantalla «Inicio / Planilla» con el periodo procesado.")

# ================================================================= 2
H("2. Requisitos")
T(["Componente", "Escritorio (instalador)", "Servidor web"], [
    ["Sistema operativo", "Windows 10 o superior, 64 bits", "Linux (Ubuntu 22.04+/Debian 12) o Windows Server"],
    ["Software previo", "**Ninguno** (el instalador incluye Python y todas las librerías)", "Python 3.11+; opcional PostgreSQL 14+"],
    ["Permisos", "Usuario normal (instala en su perfil, sin administrador)", "Administrador del servidor"],
    ["Espacio en disco", "≈ 250 MB + datos", "≈ 300 MB + datos y respaldos"],
    ["Memoria", "4 GB", "4 GB (8 GB si hay muchos usuarios)"],
    ["Navegador", "El predeterminado de Windows (Edge, Chrome, Firefox)", "Edge, Chrome o Firefox actualizados"],
    ["Internet", "No se necesita para operar", "No se necesita para operar (solo para instalar)"],
], [3.5, 6.5, 6.5])

# ================================================================= 3
H("3. Instalación")
H("3.1 Instalador sencillo para Windows (recomendado)", 2)
P("El archivo **GAMPersonal_Setup.exe** instala todo con un asistente de pocos clics.")
N(["Copie **GAMPersonal_Setup.exe** a la PC (correo, USB o carpeta compartida).",
   "Haga doble clic. Si Windows muestra «Windows protegió su PC» (el instalador no está firmado digitalmente), pulse **Más información → Ejecutar de todas formas**.",
   "Pulse **Siguiente**, elija la carpeta (por defecto `%LOCALAPPDATA%\\Programs\\GAMPersonal`) y pulse **Instalar**.",
   "Deje marcada la casilla **Abrir el sistema ahora** y pulse **Finalizar**.",
   "Se abre una ventana de consola minimizada (es el servidor local; **no la cierre mientras trabaja**) y el sistema se abre en su navegador en una dirección como `http://127.0.0.1:52341/`.",
   "En el primer ingreso cree la cuenta de administrador (ver capítulo 4)."])
T(["Elemento", "Ubicación"], [
    ["Programa", "`%LOCALAPPDATA%\\Programs\\GAMPersonal` (Python embebido, librerías, código, manuales)"],
    ["Datos (base de datos, respaldos, clave de sesión)", "`%APPDATA%\\GAMPersonal` — **no se borran al desinstalar**"],
    ["Accesos directos", "Escritorio y menú Inicio → «GAM Personal» (sistema, manuales, desinstalar)"],
    ["Dataset de prueba", "`...\\GAMPersonal\\datos_prueba`"],
], [6, 10.5])
P("**Para detener el sistema:** cierre la ventana de consola minimizada de la barra de tareas. **Para desinstalar:** menú Inicio → GAM Personal → Desinstalar "
  "(o Configuración de Windows → Aplicaciones). Los datos permanecen en `%APPDATA%\\GAMPersonal`; bórrelos manualmente solo si ya no los necesita.")
NOTE("El instalador se construyó en un entorno Linux con NSIS y Python embebido oficial; **no pudo ejecutarse en Windows durante el desarrollo**. "
     "Antes de distribuirlo a todas las PC, instálelo en una PC de prueba y realice la lista de aceptación del capítulo 7.6.", "Importante")
H("3.2 Construir el instalador (personal de Sistemas)", 2)
P("Puede reconstruirse desde Linux, macOS o Windows con Python 3.9+ y NSIS (`makensis`) e Internet:")
CODE("""cd gam-personal/desktop
python build_installer.py --version 1.0.0 --manual ../docs/Manual_GAM_Personal.pdf ../docs/Manual_GAM_Personal.docx
# Resultado: desktop/GAMPersonal_Setup.exe""")
P("El script descarga Python embebido 3.12 (win_amd64) y las librerías como *wheels* para Windows, copia el código y arma el instalador. "
  "Alternativa avanzada: `desktop\\build_windows.bat` genera un `.exe` con PyInstaller (ventana nativa con pywebview) y un instalador NSIS; requiere compilar en Windows.")

H("3.3 Servidor web en Linux", 2)
CODE("""sudo apt update && sudo apt install -y python3 python3-venv
sudo useradd -r -m -d /opt/gam gam
sudo -u gam bash -c 'cd /opt/gam && git clone <URL-DEL-REPOSITORIO> app && cd app/gam-personal/backend \\
   && python3 -m venv /opt/gam/venv && /opt/gam/venv/bin/pip install -r requirements.txt'
sudo mkdir -p /var/lib/gam && sudo chown gam: /var/lib/gam""")
P("Archivo `/etc/gam.env` (permisos 600):")
CODE("""GAM_DATA_DIR=/var/lib/gam
GAM_BACKUP_DIR=/var/lib/gam/backups
GAM_SECRET_KEY=<cadena aleatoria de 48+ caracteres>
GAM_BACKUP_PASSWORD=<clave de cifrado de respaldos>
# GAM_DATABASE_URL=postgresql+psycopg://gam:CLAVE@127.0.0.1:5432/gam   (omitir para usar SQLite)""")
P("Servicio `/etc/systemd/system/gam.service`:")
CODE("""[Unit]
Description=Gestion de Personal y Asistencia Municipal
After=network.target
[Service]
User=gam
EnvironmentFile=/etc/gam.env
WorkingDirectory=/opt/gam/app/gam-personal/backend
ExecStart=/opt/gam/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
[Install]
WantedBy=multi-user.target""")
CODE("""sudo systemctl daemon-reload && sudo systemctl enable --now gam
curl http://127.0.0.1:8000/api/salud        # debe responder {"ok":true,...}""")
NOTE("En producción publique el puerto 8000 detrás de nginx/Apache/IIS con **HTTPS**; no exponga uvicorn directamente. Con SQLite use **un solo worker**.", "Importante")
H("3.4 Servidor web en Windows", 2)
CODE("""py -3 -m venv C:\\gam\\venv
C:\\gam\\venv\\Scripts\\pip install -r backend\\requirements.txt
set GAM_DATA_DIR=C:\\gam\\datos
set GAM_SECRET_KEY=<cadena aleatoria>
C:\\gam\\venv\\Scripts\\uvicorn app.main:app --host 127.0.0.1 --port 8000""")
P("Para dejarlo como servicio use NSSM o el Programador de tareas («Al iniciar el sistema»).")
H("3.5 PostgreSQL (opcional)", 2)
CODE("""sudo -u postgres psql -c "CREATE USER gam WITH PASSWORD 'CLAVE'" -c "CREATE DATABASE gam OWNER gam ENCODING 'UTF8'"
/opt/gam/venv/bin/pip install "psycopg[binary]"
# Defina GAM_DATABASE_URL y reinicie: tablas y triggers se crean al iniciar.
# Alternativa manual: psql -d gam -f db/schema_postgresql.sql""")
P("Verificado con PostgreSQL 16: las 53 pruebas automáticas, el respaldo con `pg_dump` y la restauración con `psql` pasan. Los respaldos y restauraciones en PostgreSQL requieren `pg_dump` y `psql` en el PATH.")

# ================================================================= 4
H("4. Primer ingreso y configuración inicial")
N(["**Crear el administrador:** la primera vez la pantalla pide usuario, contraseña (mínimo 8 caracteres) y nombre. Esta cuenta tiene todos los permisos.",
   "**Configuración → Datos institucionales:** nombre del municipio, sigla, código SIGEP, ciudad, Máxima Autoridad Ejecutiva, responsable de RR.HH., quien aprueba el informe y número del Reglamento Interno. "
   "Si quedan vacíos, el informe `.docx` mostrará marcadores como «[Nombre Completo]».",
   "**Configuración → Horario:** verifique turnos (por defecto 08:00–12:00 y 14:30–18:30), tolerancia (10 min) y umbral de retraso grave (30 min).",
   "**Configuración → Escala de sanción:** ajuste los tramos a su Reglamento Interno. Elija si la escala se aplica por minutos acumulados o por cantidad de retrasos.",
   "**Configuración → Reglas de cálculo:** factor de descuento por falta (×2 planta/eventual, ×1 consultor), días justificados libres del consultor (1), tasas de aporte.",
   "**Feriados:** revise los feriados nacionales precargados 2026–2030 y agregue los locales.",
   "**Usuarios:** cree una cuenta por persona. ADMIN: todo · RRHH: opera personal, asistencia, permisos y reportes · CONSULTA: solo lectura y descargas.",
   "**Personal → Descargar plantilla Excel**, complétela y use **Importar**. La carga informa las filas con error sin detener las demás."])
IMG("ui_reportes.png", 15, "Figura 2. Pantalla «Reportes y planillas».")

# ================================================================= 5
H("5. Operación mensual paso a paso")
N(["**Importar marcaciones** (Marcaciones → Importar): archivo del reloj (.dat/.txt de ZKTeco, .csv de Anviz/Dahua o Excel). Un archivo repetido se rechaza y las marcas duplicadas se descartan.",
   "**Revisar «identificadores sin servidor asociado»:** son códigos del reloj sin persona registrada; corrija el código en Personal.",
   "**Registrar permisos, licencias y vacaciones** (Permisos y boletas → Nueva solicitud). Se genera la boleta PDF con correlativo. Los permisos de consultores requieren «Autorizado por» (fiscal de servicio).",
   "**Registrar altas y bajas** (Personal): las bajas piden fecha efectiva y causal (renuncia, conclusión de contrato, destitución…).",
   "**Inicio / Planilla → Procesar periodo.** Revise la liquidación individual y la pantalla **Asistencia diaria** (colores por estado).",
   "**Reportes:** descargue los 6 documentos. Para el informe oficial marque «Emitir con N° correlativo» (consume número; sin marcar sale como BORRADOR).",
   "**Instructivos:** cree el instructivo (cite automático), emítalo y registre la notificación de cada destinatario.",
   "**Cerrar periodo** cuando las planillas estén aprobadas: bloquea importaciones, permisos y reproceso. Reabrir exige rol ADMIN y un motivo, que queda en la bitácora.",
   "**Respaldo** del mes (capítulo 6)."])
IMG("ui_asistencia.png", 15, "Figura 3. Asistencia diaria con colores: amarillo = retraso leve, naranja = grave, rojo = falta, gris = no laborable.")
P("Los estados diarios son: Asistencia normal · Retraso leve · Retraso grave · Falta injustificada · Falta justificada · Omisión de marcación · No laborable · Feriado. "
  "Las marcas del reloj **no se pueden editar**: cualquier corrección se hace con un permiso o justificación aprobada.")

# ================================================================= 6
H("6. Respaldos y recuperación")
P("El respaldo es un script SQL **cifrado con AES-256-GCM** (clave derivada de su contraseña). Junto a cada archivo `...sql.enc` se escribe `...sql.enc.sha256`.")
NOTE("Anote la contraseña de cifrado en un sobre sellado y guárdelo en un lugar seguro. **Sin ella el respaldo no se puede abrir.** Aplique la regla 3-2-1: 3 copias, 2 medios distintos, 1 fuera de la oficina.", "Importante")
T(["Cuándo", "Cómo"], [
    ["Manual", "Menú **Respaldos** → contraseña → **Crear respaldo**. En escritorio, en «Destino» escriba la unidad USB (p. ej. `E:\\Respaldos`); en web puede descargarlo"],
    ["Programado (Windows)", "Defina la variable de sistema `GAM_BACKUP_PASSWORD` y ejecute en cmd: `schtasks /create /tn \"GAM Respaldo\" /tr \"\\\"%LOCALAPPDATA%\\Programs\\GAMPersonal\\desktop\\respaldo_programado.bat\\\"\" /sc daily /st 18:45`"],
    ["Programado (Linux)", "cron: `45 18 * * * gam ... python -m app.cli backup && python -m app.cli retencion --dias 90`"],
    ["Verificar (mensual)", "Respaldos → **Verificar integridad** (archivo + hash + contraseña) o `python -m app.cli verificar ARCHIVO.sql.enc`"],
    ["Restaurar", "Respaldos → **Restaurar** (solo ADMIN). Exige el SHA-256 de referencia y la contraseña; si el hash no coincide o el archivo fue alterado, **no restaura**. En SQLite se guarda antes una copia del estado actual; en PostgreSQL se ejecuta en una sola transacción"],
], [3.5, 13])
P("**Prueba de recuperación:** al menos una vez por trimestre restaure un respaldo en una PC de prueba y compare el total de empleados y el último registro de la bitácora.")

# ================================================================= 7
H("7. Guía de pruebas con casos reales")
H("7.1 Pruebas automáticas", 2)
CODE("""cd gam-personal/backend
pip install -r requirements-dev.txt
python -m pytest tests -q                       # SQLite  -> 53 passed
# PostgreSQL (base VACÍA):
GAM_DATABASE_URL=postgresql+psycopg://usuario@host/base_vacia python -m pytest tests -q""")
P("Son 53 pruebas: 26 del motor de reglas, 6 del lector de archivos biométricos y 21 de punta a punta (importación, permisos, procesamiento, 6 reportes, cierre de periodo, "
  "bitácora inalterable, respaldo y restauración, roles e inyección de fórmulas).")
H("7.2 Dataset de prueba", 2)
P("Datos **ficticios** del mes de **octubre de 2026** (22 días hábiles, sin feriados nacionales). Carpeta `datos_prueba/`:")
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
H("7.3 Procedimiento", 2)
N(["Cree el administrador y complete **Configuración** (sobre todo nombre, sigla, ciudad, responsables).",
   "**Personal → Importar** `personal.csv` → debe decir *Creados: 5 · Errores: 0*.",
   "**Marcaciones → Importar** `biometrico_octubre_2026.dat` → *leídas 408, nuevas 408, duplicadas 0, rechazadas 0*. Luego importe el `.csv`: *nuevas 0, duplicadas 408*. Reimportar el mismo archivo debe rechazarse.",
   "**Permisos → Nueva solicitud**: registre las 6 filas de `permisos_octubre_2026.csv`. Compruebe la boleta PDF `GAM-RRHH-BOL-00N/2026` y que aprobar el permiso del consultor **sin** «Autorizado por» se rechaza.",
   "**Inicio / Planilla**: mes *Octubre 2026* → **Procesar periodo**.",
   "**Reportes**: descargue los 6 y compare con la sección 7.4.",
   "Alternativa por script: `python datos_prueba/cargar_dataset.py --url http://127.0.0.1:8000 --clave 'SuClave#2026' --salida reportes_prueba`."])
H("7.4 Resultados esperados (calculados a mano)", 2)
P("Cálculo del descuento: `haber ÷ 30 × días de descuento`. Falta injustificada de planta/eventual = ×2; consultor = ×1. Aporte laboral = 12,71 % del total ganado.")
T(["Servidor", "Faltas", "Min. retraso", "Días desc.", "Total ganado", "AFP", "Desc. asist.", "Líquido"], [
    ["1001 Mamani", "0", "30", "0", "6.000,00", "762,60", "0,00", "**5.237,40**"],
    ["1002 Vargas", "1", "70", "2,5 (1×2 + 0,5)", "4.500,00", "571,95", "375,00", "**3.553,05**"],
    ["2001 Choque", "0,5", "0", "1 (0,5×2)", "3.800,00", "482,98", "126,67", "**3.190,35**"],
    ["2002 Flores", "0", "22", "1 (sin goce)", "3.500,00", "444,85", "116,67", "**2.938,48**"],
    ["3001 Salazar", "1", "50", "2 (falta + exceso)", "7.000,00", "0,00", "466,66", "**6.533,34**"],
    ["**TOTAL**", "", "", "", "**24.800,00**", "**2.262,38**", "**1.085,00**", "**21.452,62**"],
], [3.1, 1.3, 1.7, 2.8, 2.2, 1.7, 1.9, 2.2], size=8)
P("Control de cruce: 24.800,00 − 2.262,38 − 1.085,00 = 21.452,62. Sanciones por retrasos: Vargas → descuento de 0,5 día (70 min); Salazar → amonestación escrita (50 min); "
  "Mamani (30 min) y Flores (22 min) → sin sanción.")
T(["N°", "Reporte", "Resultado esperado"], [
    ["1", "Informe de asistencia (.docx)", "Periodo «Del 01 al 31 de octubre de 2026 (22 días hábiles)». Resumen: 5 servidores / 110 días-hombre; asistencia regular 94 días (85,45 %); con atrasos 4 (172 min); licencias con goce 2 servidores / 3 días; permisos 2 / 2 días; faltas 3 / 2,5 días. Tabla de atrasos (Vargas, Salazar, Mamani, Flores), faltas (Vargas, Choque, Salazar) y omisiones (Mamani 14/10, Flores 22/10). Sin abandono de funciones. CITE «N° S/N (BORRADOR)» o «N° 001» al emitir"],
    ["2", "Planilla de nuevo personal", "1 fila: Flores Apaza Carla Andrea, ingreso 01/10/2026, Eventual, partida 12100, vigencia 31/12/2026, líquido 2.938,48"],
    ["3", "Planilla de desvinculados", "1 fila: Salazar Copa Miguel Ángel, baja 30/10/2026, causal «Conclusión de contrato», líquido 6.533,34"],
    ["4", "Planilla de sueldos", "3 bloques: Permanentes (2; ganado 10.500,00; líquido 8.790,45), Eventuales (2; 7.300,00; 6.128,83), Consultores (1; 7.000,00; 6.533,34). Total general 24.800,00 / 21.452,62"],
    ["5", "Reporte detallado (.xlsx)", "Resumen institucional (5 filas), detalle diario de 154 filas, 16 imputaciones (4 retrasos leves, 2 graves, 3 faltas injustificadas, 5 justificadas, 2 omisiones), leyenda de reglas"],
    ["6", "Consolidado plano (.txt UTF-8, tabulador)", "5 filas; p. ej. `2026-10 1000002 1002 PERMANENTE 22 21.00 1.00 70 0.00 375.00` y `2026-10 1000005 3001 CONSULTOR_LINEA 22 19.00 1.00 50 2.00 466.66`"],
], [0.9, 4, 11.6], size=8.5)
P("**Comportamiento del motor que conviene comprobar:** 21/10 Choque queda *Normal* (el permiso de 08:00 a 10:00 cubre el retraso); 27/10 Salazar es *Falta injustificada* porque el permiso está pendiente, "
  "pero al **aprobarlo** con fiscal el sistema se actualiza solo y el descuento sube a 466,67; una vacación aprobada el 15/10 convierte la falta de Vargas en justificada.")
H("7.5 Pruebas negativas y de control", 2)
T(["Acción", "Resultado esperado"], [
    ["Aprobar permiso de consultor sin «Autorizado por»", "Error: debe ser autorizado por el fiscal de servicio"],
    ["Reimportar el mismo archivo biométrico", "Error: «ya fue importado (lote N)»"],
    ["Importar un Excel dañado o sin columnas de ID/Fecha/Hora", "Error con mensaje claro"],
    ["Fila con fecha u hora inválida", "Se rechaza solo esa fila; el resto se importa y se informa"],
    ["Generar reportes de un mes no procesado", "Error: «aún no fue procesado»"],
    ["Cerrar periodo y luego importar, registrar permiso o reprocesar", "Bloqueado; reabrir exige ADMIN y motivo de 10+ caracteres"],
    ["Modificar o borrar la bitácora, o modificar una marca, directamente en la base", "La base lo rechaza (triggers)"],
    ["Alterar un byte de un respaldo, usar hash o contraseña incorrectos", "Verificación y restauración fallan sin tocar los datos"],
    ["Usuario CONSULTA intenta procesar, respaldar o registrar", "Acceso denegado (403)"],
    ["Importar personal con nombre «=HYPERLINK(...)» o C.I. con símbolos", "El nombre sale como texto en los Excel; el C.I. con símbolos se rechaza"],
], [7.5, 9])
H("7.6 Lista de aceptación (instalación en PC nueva)", 2)
T(["☐", "Verificación", "Resultado"], [
    ["☐", "El instalador se ejecuta sin errores y crea los accesos directos", ""],
    ["☐", "El sistema abre en el navegador y permite crear el administrador", ""],
    ["☐", "Importación del dataset: 5 servidores y 408 marcas", ""],
    ["☐", "Procesar octubre 2026: totales 24.800,00 / 2.262,38 / 1.085,00 / 21.452,62", ""],
    ["☐", "Los 6 reportes se descargan y abren correctamente (Word y Excel)", ""],
    ["☐", "Se crea un respaldo, se verifica su integridad y se restaura en la PC de prueba", ""],
    ["☐", "Cerrar y reabrir el periodo; la bitácora registra ambos eventos", ""],
    ["☐", "Cerrar la ventana de consola detiene el sistema; al reabrir los datos siguen ahí", ""],
    ["☐", "Desinstalar elimina el programa y conserva los datos en %APPDATA%\\GAMPersonal", ""],
], [1, 11, 4.5])
P("Antes de usar datos reales, **borre los datos de prueba**: desinstale, elimine `%APPDATA%\\GAMPersonal` y vuelva a instalar, o use una PC distinta para las pruebas.")

# ================================================================= 8
H("8. Seguridad")
B(["Un usuario por persona; no comparta la cuenta `admin`. Use el rol CONSULTA para auditoría interna.",
   "Contraseñas almacenadas con scrypt; sesión de 10 horas; bloqueo de 5 minutos tras 5 intentos fallidos.",
   "En modo servidor use siempre HTTPS y mantenga uvicorn solo en `127.0.0.1`; defina su propia `GAM_SECRET_KEY`.",
   "La bitácora está encadenada por hash: use **Auditoría → Verificar integridad de la cadena** una vez al mes.",
   "Las marcas biométricas son inalterables; los periodos cerrados no admiten cambios.",
   "En el modo escritorio el servidor escucha solo en la propia PC (127.0.0.1): no es accesible desde la red."])

# ================================================================= 9
H("9. Solución de problemas")
T(["Síntoma", "Causa probable y solución"], [
    ["El navegador no abre el sistema", "Abra manualmente la dirección que muestra la ventana de consola (`http://127.0.0.1:NNNNN/`). Si la consola se cerró, vuelva a abrir el acceso directo"],
    ["Windows SmartScreen bloquea el instalador", "Más información → Ejecutar de todas formas (el instalador no está firmado). Para evitarlo, la institución puede firmarlo con su certificado de código"],
    ["Antivirus elimina o bloquea el programa", "Agregue una excepción para la carpeta de instalación; verifique el origen del archivo"],
    ["«Ya existe una instancia»", "El sistema ya está abierto: use su ventana de navegador o la dirección de la consola"],
    ["Importación de marcas: «0 nuevas»", "Las marcas ya estaban cargadas (mismo ID, fecha-hora y dispositivo). Es normal al reimportar"],
    ["Marcas de una persona no aparecen en el cálculo", "Revise Marcaciones → «identificadores sin servidor asociado»: el código del reloj debe coincidir con el «Código» de Personal"],
    ["Fechas mal leídas (día y mes invertidos)", "En la importación elija el formato «mes/día/año» si su reloj exporta así"],
    ["El informe .docx muestra «[Nombre Completo]»", "Complete Configuración → Datos institucionales y vuelva a descargar"],
    ["«El periodo aún no fue procesado»", "Inicio / Planilla → Procesar periodo"],
    ["«Periodo CERRADO»", "Un ADMIN debe reabrirlo indicando el motivo"],
    ["Restauración falla: «Falla de integridad SHA-256»", "El archivo cambió o el hash corresponde a otro respaldo; use el `.sha256` original"],
    ["Olvidó la contraseña de un respaldo", "No hay forma de recuperarlo (cifrado AES-256). Por eso se guarda en sobre sellado"],
    ["Puerto ocupado / servicio no inicia (web)", "`journalctl -u gam -n 50` (Linux); revise `GAM_DATABASE_URL` y permisos de `GAM_DATA_DIR`"],
], [5.5, 11])

# ================================================================= 10
H("10. Supuestos legales y limitaciones conocidas")
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
B(["El instalador y el `.exe` no pudieron ejecutarse en Windows durante el desarrollo: pruébelos en una PC piloto.",
   "Los formatos Anviz/Dahua se cubren por nombres de columna habituales; no se probaron con exportaciones reales.",
   "Un servidor liquida con un solo contrato por mes (el de inicio más reciente); un cambio de haber a mitad de mes no se prorratea.",
   "Los saldos de vacaciones no se calculan: gestión y saldo se registran como texto informativo.",
   "No se calculan retenciones de consultores (IT/IVA) ni bono de antigüedad automático: bono y RC-IVA son datos de entrada.",
   "Un retorno del almuerzo antes de las 13:15 se interpreta como salida de la mañana y se marca como omisión para su regularización."])

doc.save(AQUI / "Manual_GAM_Personal.docx")
print("Word:", AQUI / "Manual_GAM_Personal.docx")
if shutil.which("soffice"):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(AQUI), str(AQUI / "Manual_GAM_Personal.docx")],
                   check=True, capture_output=True, timeout=180)
    print("PDF:", AQUI / "Manual_GAM_Personal.pdf")
else:
    print("LibreOffice no disponible: convierta el .docx a PDF desde Word (Guardar como PDF).")
