const fs = require('fs');
const D = require('docx');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, ImageRun, AlignmentType, LevelFormat, PageBreak, TableOfContents, Footer, Header, PageNumber } = D;
const IMG = '/home/user/Factura/sicom-muni/docs/img/';
const AZUL = '1F4E79', GRIS = 'F2F5F9';
const kids = [];
const run = (t, o = {}) => new TextRun({ text: t, font: 'Calibri', ...o });
// **negrita** inline y `codigo`
function runs(t) {
  const out = []; const re = /(\*\*[^*]+\*\*|`[^`]+`)/g; let last = 0, m;
  while ((m = re.exec(t))) {
    if (m.index > last) out.push(run(t.slice(last, m.index)));
    const s = m[0];
    if (s.startsWith('**')) out.push(run(s.slice(2, -2), { bold: true }));
    else out.push(new TextRun({ text: s.slice(1, -1), font: 'Consolas', size: 20, color: '7A1F1F' }));
    last = m.index + s.length;
  }
  if (last < t.length) out.push(run(t.slice(last)));
  return out;
}
const H1 = (t) => kids.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [run(t)] }));
const H1n = (t) => kids.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run(t)] }));
const H2 = (t) => kids.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(t)] }));
const H3 = (t) => kids.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [run(t)] }));
const P = (t, o = {}) => kids.push(new Paragraph({ spacing: { after: 120 }, ...o, children: runs(t) }));
const B = (items) => items.forEach((t) => kids.push(new Paragraph({ numbering: { reference: 'bul', level: 0 }, spacing: { after: 60 }, children: runs(t) })));
const N = (items) => { const ref = 'num' + Math.random().toString(36).slice(2); numRefs.push(ref); items.forEach((t) => kids.push(new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 80 }, children: runs(t) }))); };
const numRefs = [];
function CODE(txt) {
  txt.split('\n').forEach((l, i, a) => kids.push(new Paragraph({ shading: { type: ShadingType.CLEAR, fill: '1E1E1E', color: 'auto' }, spacing: { after: i === a.length - 1 ? 160 : 0 }, indent: { left: 120, right: 120 },
    children: [new TextRun({ text: l || ' ', font: 'Consolas', size: 18, color: 'D4D4D4' })] })));
}
const bd = { style: BorderStyle.SINGLE, size: 4, color: 'BFC8D4' }; const borders = { top: bd, bottom: bd, left: bd, right: bd };
function TABLE(head, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, h) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders, margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: h ? { type: ShadingType.CLEAR, fill: AZUL, color: 'auto' } : undefined,
    children: String(t).split('\n').map((l) => new Paragraph({ children: h ? [run(l, { bold: true, color: 'FFFFFF', size: 19 })] : runs(l).map((r) => r) })) });
  kids.push(new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, widths[i], true)) }), ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, widths[i], false)) }))] }));
  kids.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
}
function NOTE(t, color = 'FFF4CE', titulo = 'Nota') {
  kids.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360], rows: [new TableRow({ children: [new TableCell({ width: { size: 9360, type: WidthType.DXA }, borders, margins: { top: 100, bottom: 100, left: 160, right: 160 }, shading: { type: ShadingType.CLEAR, fill: color, color: 'auto' },
    children: [new Paragraph({ children: [run(titulo + ': ', { bold: true }), ...runs(t)] })] })] })] }));
  kids.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
}
function pngSize(f) { const b = fs.readFileSync(f); return [b.readUInt32BE(16), b.readUInt32BE(20)]; }
function IMGF(file, caption, maxW = 6.3, maxH = 8.2) {
  const [w, h] = pngSize(IMG + file); let W = maxW, H = maxW * h / w; if (H > maxH) { H = maxH; W = maxH * w / h; }
  kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 40 }, keepNext: true, children: [new ImageRun({ type: 'png', data: fs.readFileSync(IMG + file), transformation: { width: Math.round(W * 96), height: Math.round(H * 96) },
    altText: { title: caption, description: caption, name: file } })] }));
  kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [run('Figura: ' + caption, { italics: true, size: 18, color: '555555' })] }));
}
const PASO = (n, quien, titulo, desc) => { kids.push(new Paragraph({ keepNext: true, spacing: { before: 200, after: 60 }, children: [run(`Paso ${n} — `, { bold: true, color: AZUL }), run(titulo, { bold: true }), run(`   [${quien}]`, { color: '666666', size: 20 })] })); desc.forEach((t) => P(t)); };

// ---------------- PORTADA
kids.push(new Paragraph({ spacing: { before: 2400 }, alignment: AlignmentType.CENTER, children: [run('SICOM-MUNI', { bold: true, size: 72, color: AZUL })] }));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Sistema Integrado de Contratación Menor Municipal', { size: 32 })] }));
kids.push(new Paragraph({ spacing: { before: 600 }, alignment: AlignmentType.CENTER, children: [run('MANUAL DE IMPLEMENTACIÓN Y PRUEBA', { bold: true, size: 40 })] }));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run('con ejemplos detallados paso a paso y capturas del sistema funcionando', { size: 26, color: '555555' })] }));
kids.push(new Paragraph({ spacing: { before: 1800 }, alignment: AlignmentType.CENTER, children: [run('Contratación Menor (Bs 1 a Bs 50.000) — Gobierno Autónomo Municipal', { size: 22 })] }));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Stack: FastAPI · PostgreSQL · Next.js · WeasyPrint · MinIO · Docker', { size: 22, color: '555555' })] }));
kids.push(new Paragraph({ spacing: { before: 1200 }, alignment: AlignmentType.CENTER, children: [run('Las capturas de este manual fueron tomadas del sistema real ejecutándose con los datos demo; los datos de personas y empresas son ficticios.', { italics: true, size: 18, color: '777777' })] }));
kids.push(new Paragraph({ children: [new PageBreak()] }));
kids.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run('Contenido')] }));
kids.push(new TableOfContents('Contenido', { hyperlink: true, headingStyleRange: '1-2' }));

// ---------------- 1
H1('1. Introducción');
P('SICOM-MUNI es una aplicación web de código abierto que gestiona de punta a punta la **Contratación Menor** de un Gobierno Autónomo Municipal: desde la Solicitud (formulario C-1) hasta el devengado, generando un expediente digital de PDF con marca de agua, código QR y huella SHA-256 verificable.');
P('Este manual cubre tres cosas: (1) cómo **instalar** el sistema, (2) cómo **funciona** cada pantalla con dos ejemplos completos y capturas reales, y (3) una **guía paso a paso para probarlo** usted mismo, tanto desde la interfaz como con pruebas automáticas.');
H2('1.1 Qué hace el sistema');
B(['Calcula la **modalidad por cuantía**: compra directa hasta Bs 20.000; Consulta de Precios SICOES (con Formulario 110) de Bs 20.001 a Bs 50.000; sobre Bs 50.000 bloquea y sugiere derivar a ANPE.',
  'Aplica la regla **Compro Hecho en Bolivia (CHB)**: si un bien existe en el catálogo, la compra es obligatoria por catálogo salvo excepción justificada (el sistema genera el Informe de Excepción).',
  'Define la **formalización por plazo**: hasta 15 días calendario → Orden de Compra/Servicio; más de 15 días → Contrato Administrativo.',
  'Controla el **presupuesto**: certifica el preventivo C-31 descontando el saldo por partida, ofrece el **bloque de captura rápida para SIGEP** y libera la diferencia al devengar.',
  'Evalúa por **Precio Evaluado Más Bajo** con margen de preferencia Pro-Bolivia/MyPE, con ofertas **selladas** (monto cifrado) hasta la apertura.',
  'Registra una **auditoría inalterable** encadenada por hash y emite PDF verificables públicamente por QR.']);
H2('1.2 Roles');
TABLE(['Rol', 'Usuario demo', 'Responsabilidad principal'], [
  ['Solicitante', '`solicitante`', 'Crea y envía la solicitud (C-1)'],
  ['Presupuesto', '`presupuesto`', 'Certifica C-31, copia bloque SIGEP, devenga, administra partidas'],
  ['Contrataciones', '`contrataciones`', 'F110, fichas, cotizaciones, apertura, calificación y evaluación'],
  ['RPA', '`rpa`', 'Aprueba inicio, adjudica, declara desierto, formaliza'],
  ['Recepción', '`recepcion`', 'Registra recepción y conformidad'],
  ['Administrador', '`admin`', 'Usuarios, parámetros, catálogo CHB, auditoría']], [1900, 2200, 5260]);
P('Contraseña de todos los usuarios demo: `Sicom#2026Demo`. **Cámbiela antes de usar datos reales.**');
H2('1.3 Estados del trámite');
CODE('BORRADOR → SOLICITADO → CERTIFICADO_PRESUPUESTO → EN_COTIZACION → EVALUADO\n   → ADJUDICADO → FORMALIZADO → RECEPCIONADO → DEVENGADO       (ANULADO desde etapas permitidas)');

// ---------------- 2
H1('2. Arquitectura y requisitos');
CODE('Navegador ──► Next.js :3000 ──(reenvío /api/*)──► FastAPI :8000 ──► PostgreSQL 15+\n                                                         └────────► MinIO/S3 (PDF) o disco local');
P('El navegador solo habla con el frontend (mismo origen). Next.js reenvía `/api/*` al backend; así la cookie del refresh token es HTTP-only con `SameSite=Strict` y no se requiere CORS.');
H2('2.1 Requisitos');
TABLE(['Modo', 'Requisitos'], [
  ['Docker (recomendado)', 'Docker Engine 24+, Docker Compose v2, 2 GB de RAM libres, puertos 3000 libre'],
  ['Manual', 'Python 3.12, Node.js 20, PostgreSQL 15+, librerías del sistema para WeasyPrint (`libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b shared-mime-info fonts-dejavu-core` en Debian/Ubuntu)'],
  ['Para probar', 'Un navegador moderno (Chrome, Edge o Firefox). Opcional: `curl` para probar la API']], [2200, 7160]);
H2('2.2 Variables de entorno del backend');
TABLE(['Variable', 'Valor por defecto', 'Descripción'], [
  ['`DATABASE_URL`', 'postgresql+psycopg://sicom:sicom@localhost:5432/sicom', 'Conexión a PostgreSQL'],
  ['`SECRET_KEY`', '(solo desarrollo)', 'Firma de JWT. Mínimo 32 caracteres aleatorios'],
  ['`FERNET_KEY`', 'derivada de SECRET_KEY', 'Clave de cifrado de ofertas selladas'],
  ['`ACCESS_TOKEN_MINUTES`', '15', 'Vigencia del token de acceso'],
  ['`REFRESH_TOKEN_DAYS`', '7', 'Vigencia de la sesión (refresh)'],
  ['`COOKIE_SECURE`', 'false', 'true cuando se sirva por HTTPS'],
  ['`PUBLIC_BASE_URL`', 'http://localhost:3000', 'URL pública impresa en los QR'],
  ['`STORAGE_BACKEND`', 'local', '`local` o `s3` (MinIO)'],
  ['`S3_*`', 'MinIO local', 'Endpoint, claves y bucket'],
  ['`SMTP_*`', 'vacío', 'Correo de fichas; vacío = NO_CONFIGURADO']], [2300, 3300, 3760]);

// ---------------- 3
H1('3. Instalación');
H2('3.1 Con Docker Compose (recomendado)');
N(['Obtenga el código: `git clone https://github.com/blancojaime/Factura.git` y entre a `Factura/sicom-muni` (rama `claude/tender-einstein-76nc7n` o la principal tras la fusión).',
  'Cree el archivo de entorno: `cp .env.example .env` y edite **todas** las claves (`POSTGRES_PASSWORD`, `SECRET_KEY`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `PUBLIC_BASE_URL`).',
  'Levante los servicios: `docker compose up -d --build`. Se crean `db`, `minio`, `minio-init` (bucket privado), `backend` (ejecuta las migraciones y arranca) y `frontend`.',
  'Cargue los datos demo: `docker compose --profile seed run --rm seed`.',
  'Abra `http://localhost:3000` en el navegador.']);
CODE('cd sicom-muni\ncp .env.example .env\nnano .env\ndocker compose up -d --build\ndocker compose --profile seed run --rm seed\ndocker compose ps');
NOTE('El backend no publica puerto al exterior. Para ver la documentación Swagger (`/api/docs`) agregue temporalmente `ports: ["127.0.0.1:8000:8000"]` al servicio `backend`. En el entorno donde se desarrolló este sistema no había daemon Docker: los Dockerfile y el compose se validaron de forma estática y las capturas de este manual provienen de la instalación manual (3.2). Realice la primera construcción de imágenes en un entorno de prueba.', 'FFF4CE', 'Importante');
H2('3.2 Instalación manual (sin Docker)');
N(['**Base de datos.** Cree usuario y base: `createuser sicom -P` y `createdb sicom -O sicom`.',
  '**Backend.** Cree el entorno virtual e instale: `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.',
  'Exporte las variables (`DATABASE_URL`, `SECRET_KEY`) y ejecute las migraciones: `alembic upgrade head`.',
  'Cargue datos demo (opcional): `python -m app.seeds`.',
  'Inicie la API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.',
  '**Frontend.** En otra terminal: `cd frontend && npm ci && BACKEND_URL=http://localhost:8000 npm run build`.',
  'Inicie la web: `npm start` (o `node .next/standalone/server.js` copiando antes `.next/static` y `public` dentro de `.next/standalone`).']);
CODE('# Terminal 1 — backend\ncd sicom-muni/backend\npython -m venv .venv && . .venv/bin/activate\npip install -r requirements.txt\nexport DATABASE_URL=postgresql+psycopg://sicom:CLAVE@localhost:5432/sicom\nexport SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))")\nalembic upgrade head && python -m app.seeds\nuvicorn app.main:app --port 8000\n\n# Terminal 2 — frontend\ncd sicom-muni/frontend\nnpm ci && BACKEND_URL=http://localhost:8000 npm run build && npm start');
H2('3.3 Comprobación de la instalación');
TABLE(['Verificación', 'Cómo', 'Resultado esperado'], [
  ['API viva', '`curl http://localhost:3000/api/v1/salud`', '`{"estado":"ok"}`'],
  ['Base migrada', 'Iniciar sesión con `admin`', 'Entra al panel sin errores'],
  ['Datos demo', 'Menú Presupuesto (como `presupuesto`)', 'Partidas 25800, 34200, 39500 y 43100'],
  ['PDF', 'Completar el Caso 1 (sección 5)', 'PDF descargables en la pestaña Documentos']], [2000, 3900, 3460]);

// ---------------- 4 Recorrido
H1('4. Recorrido por la interfaz');
H2('4.1 Inicio de sesión');
P('Ingrese a `http://localhost:3000`. Escriba usuario y contraseña. Tras 5 intentos fallidos la cuenta se bloquea 15 minutos.');
IMGF('01-login.png', 'Pantalla de inicio de sesión', 5.4, 5);
H2('4.2 Panel de inicio por rol');
P('Cada rol ve contadores por estado y la lista **«Pendientes de mi atención»** con la columna **«Qué debe hacer»**: es su bandeja de trabajo. El menú lateral cambia según el rol.');
IMGF('02-dashboard-solicitante.png', 'Panel del Solicitante', 6.0, 5.5);
IMGF('25-dashboard-contrataciones.png', 'Panel del rol Contrataciones (otro rol, otra bandeja)', 6.0, 5.5);

// ---------------- 5 CASO 1
H1('5. Ejemplo 1 — Bienes: material de construcción, Bs 18.500');
P('**Objetivo:** validar compra directa (≤ Bs 20.000, sin Formulario 110), regla CHB con excepción, ofertas selladas, Orden de Compra (plazo ≤ 15 días), recepción y devengado con liberación de saldo.');
P('**Partida usada:** 34200 (saldo inicial Bs 80.000). **Duración estimada de la prueba:** 20 a 25 minutos.');
H2('5.1 Datos de entrada');
TABLE(['Dato', 'Valor'], [
  ['Objeto', 'Adquisición de material de construcción para mantenimiento de la plaza principal'],
  ['Tipo / plazo', 'Bien / 10 días calendario'],
  ['Lugar de entrega', 'Plaza principal, calle Bolívar N° 123'],
  ['Ítem 1', 'UNSPSC 30111505 — Cemento portland IP-30 bolsa de 50 kg — Bolsa — 120 × Bs 62,00 = 7.440,00'],
  ['Ítem 2', 'UNSPSC 30131501 — Ladrillo cerámico de 6 huecos — Unidad — 3.950 × Bs 1,30 = 5.135,00'],
  ['Ítem 3', 'UNSPSC 11111501 — Arena fina lavada — m³ — 30 × Bs 85,00 = 2.550,00'],
  ['Ítem 4', 'UNSPSC 11111503 — Piedra chancada de 3/4 pulgada — m³ — 25 × Bs 135,00 = 3.375,00'],
  ['**Total referencial**', '**Bs 18.500,00**'],
  ['Cotización A', 'FERRETERIA EL CONSTRUCTOR S.R.L. — NIT 1023456028 — Bs 18.200,00 — 8 días'],
  ['Cotización B', 'MATERIALES BOLIVIA LTDA. — NIT 4012345011 — Bs 17.900,00 — 10 días'],
  ['Preventivo C-31', 'C31-2026-00123']], [2300, 7060]);

PASO(1, 'solicitante', 'Crear la solicitud', ['Inicie sesión como `solicitante`. Menú **Nueva solicitud** o botón del panel. Complete: objeto, tipo **Bien**, plazo **10**, unidad, lugar, justificación y especificaciones técnicas (la **guía de redacción** le orienta). Presione **Crear**.', '**Resultado:** se crea el trámite `CM-AAAA-NNNNNN` en estado **BORRADOR** y se abre el **Formulador asistido del C-1**.']);
PASO(2, 'solicitante', 'Agregar ítems y ver las reglas en vivo', ['En **«2. Ítems → Agregar ítem»** escriba el código UNSPSC (o parte del nombre para buscar en el catálogo CHB), elija la partida **34200**, descripción, unidad, cantidad y precio; presione **Agregar**. Repita para los 4 ítems.',
  '**Qué observar** (ver figura): cemento y ladrillo se marcan en rojo **«Compra obligatoria en CHB»** porque existen en el catálogo; arena y piedra quedan en amarillo **«Sin coincidencia en CHB»**. El bloque **«3. Verificación normativa»** muestra monto Bs 18.500, modalidad **Compra directa (hasta Bs 20.000)**, formalización **Orden de Compra** y bloquea el envío con el mensaje de compra obligatoria.']);
IMGF('03-formulador-chb.png', 'Formulador asistido: ítems con estado CHB, reglas en vivo y envío bloqueado', 5.0, 9);
PASO(3, 'solicitante', 'Probar el bloqueo CHB', ['Presione **Enviar solicitud a Presupuesto** con el estado anterior. **Resultado esperado:** el sistema rechaza (HTTP 422 `SOLICITUD_INCOMPLETA`) y lista los ítems 1 y 2: «El bien está disponible en el Catálogo Compro Hecho en Bolivia (D.S. 4505): debe adquirirse por catálogo o fundamentarse la excepción».']);
PASO(4, 'solicitante', 'Registrar la excepción CHB', ['Edite el ítem 1 y el ítem 2 (ícono del lápiz) y marque **«Fuera de catálogo CHB»**. En el recuadro amarillo escriba la **justificación técnico-legal (mínimo 80 caracteres)**, por ejemplo: «Los proveedores del catálogo CHB no pueden entregar los materiales en el plazo de obra de 10 días ni en la cantidad requerida por la unidad; se fundamenta la compra directa en el mercado local.» y el código de autorización `MDPyEP-AUT-0391`. Presione **Guardar datos** y luego **Enviar solicitud a Presupuesto**.',
  '**Resultado:** estado **SOLICITADO**. Se generan automáticamente el PDF **C-1 (Solicitud)** y el **Informe Técnico-Legal de Excepción CHB**.']);
IMGF('04-documentos-c1.png', 'Pestaña Documentos tras enviar la solicitud: C-1 e Informe de Excepción CHB', 6.0, 4.8);
IMGF('pdf-c1-1.png', 'Primera página del PDF C-1 generado (membrete, marca de agua, QR y hash al pie)', 4.2, 6.2);
PASO(5, 'presupuesto', 'Verificar partida y bloque SIGEP previsto', ['Inicie sesión como `presupuesto` y abra el trámite → pestaña **Presupuesto y SIGEP**. Se muestra la verificación de saldo de la partida 34200 y el **Panel de captura rápida SIGEP** con la estructura programática (DA, UE, programa, proyecto, actividad, fuente, organismo, partida, importe).']);
IMGF('05-presupuesto-sigep.png', 'Panel de presupuesto antes de certificar', 6.0, 5.5);
PASO(6, 'presupuesto', 'Certificar el preventivo C-31', ['Escriba el N.° de comprobante `C31-2026-00123` y presione **Certificar presupuesto**. Pulse **Copiar Bloque SIGEP** para copiar al portapapeles una línea por partida con el formato `DA | UE | PROGRAMA | PROYECTO | ACTIVIDAD | FTE | ORG | PARTIDA | IMPORTE`; péguela en la pantalla de captura del SIGEP.',
  '**Resultado esperado:** estado **CERTIFICADO_PRESUPUESTO**; el saldo de la partida 34200 baja de **Bs 80.000 a Bs 61.500**; se genera la **Certificación presupuestaria C-31**. Bloque copiado: `01 | 001 | 01 | 0000 | 001 | 20 | 230 | 34200 | 18500.00`.']);
IMGF('06-bloque-sigep-certificado.png', 'Panel de captura rápida SIGEP con el preventivo certificado', 6.0, 6);
PASO(7, 'rpa', 'Aprobar el inicio del proceso', ['Inicie sesión como `rpa` y abra el trámite: aparece la tarjeta **Aprobar inicio**. Presione el botón. **Resultado:** estado **EN_COTIZACION**. Al ser compra directa no se exige Formulario 110.']);
IMGF('07-rpa-aprobar-inicio.png', 'El RPA ve la acción pendiente de aprobar el inicio', 6.0, 4.5);
PASO(8, 'contrataciones', 'Cargar cotizaciones (sobres sellados)', ['Inicie sesión como `contrataciones`, pestaña **Cotizaciones y adjudicación**. Registre las cotizaciones A y B con NIT, razón social, monto y plazo. **Pruebe** repetir el NIT 4012345011: el sistema lo rechaza (un proveedor no puede cotizar dos veces).',
  '**Qué observar:** mientras las ofertas no se abren, los montos aparecen **sellados** (el monto está cifrado en la base de datos y no viaja al navegador).']);
IMGF('08-cotizaciones-selladas.png', 'Cotizaciones registradas con monto sellado', 6.0, 5.5);
PASO(9, 'contrataciones', 'Abrir ofertas y calificar', ['Presione **Abrir ofertas** (en compra directa sin plazo fijado se puede abrir de inmediato; en consulta de precios solo tras vencer el plazo). Ahora los montos son visibles. Presione **Calificar** en cada oferta y marque **Cumple especificaciones**.']);
IMGF('09-calificar-oferta.png', 'Diálogo de calificación de una oferta', 6.0, 6);
PASO(10, 'contrataciones', 'Revisar la matriz y evaluar', ['La **Matriz comparativa — Precio Evaluado Más Bajo** ordena las ofertas elegibles. **Resultado esperado:** 1.° MATERIALES BOLIVIA LTDA. (17.900,00, «Recomendada»); 2.° FERRETERIA EL CONSTRUCTOR (18.200,00). Presione **Evaluar y generar cuadro comparativo**: estado **EVALUADO** y se genera el **Cuadro Comparativo**.']);
IMGF('10-matriz-comparativa.png', 'Matriz comparativa con la oferta recomendada', 6.0, 7);
IMGF('pdf-cuadro-1.png', 'PDF del Cuadro Comparativo', 4.0, 5.8);
PASO(11, 'rpa', 'Adjudicar con el Asistente de Adjudicación', ['Como `rpa`, en la pestaña Cotizaciones verá el **Asistente de adjudicación** con la oferta recomendada preseleccionada. Si elige otra oferta elegible, el sistema exige un **motivo**; una oferta no elegible no puede adjudicarse. Presione **Adjudicar** (la alternativa es **Declarar desierto**, que cierra el trámite como ANULADO y libera el presupuesto).',
  '**Resultado:** estado **ADJUDICADO** y se genera la **Nota de adjudicación**.']);
IMGF('11-asistente-adjudicacion.png', 'Asistente de adjudicación', 6.0, 6.5);
PASO(12, 'rpa', 'Formalizar: Orden de Compra', ['Pestaña **Formalización y recepción**. El sistema determina el método por el plazo (10 días ≤ 15): **Orden de Compra**. Si intenta forzar «Contrato» el servidor lo rechaza. Presione **Formalizar**.', '**Resultado:** estado **FORMALIZADO** y PDF de **Orden de Compra**.']);
IMGF('12-formalizacion.png', 'Formalización: método determinado por el plazo', 6.0, 5.5);
IMGF('pdf-orden-1.png', 'PDF de la Orden de Compra', 4.0, 5.8);
PASO(13, 'recepcion', 'Registrar la recepción', ['Inicie sesión como `recepcion`. En **Formalización y recepción** registre la fecha y las cantidades recibidas por ítem. **Prueba negativa:** registre 100 bolsas de cemento (faltan 20) marcando «conforme»: el sistema lo rechaza porque la cantidad no coincide. Registre la misma recepción como **No conforme** con la observación «Faltan 20 bolsas de cemento por entregar»: queda registrada y el trámite sigue **FORMALIZADO**. Luego registre la recepción **conforme y completa**.',
  '**Resultado:** estado **RECEPCIONADO**; se emite el **Acta de recepción (Form. 500)** con N.° NIA-…']);
IMGF('13-recepcion.png', 'Formulario de recepción', 6.0, 6.5);
PASO(14, 'presupuesto', 'Devengar y liberar saldo', ['Como `presupuesto`, presione **Devengar**. **Resultado esperado:** estado **DEVENGADO**; el sistema libera la diferencia entre lo reservado (Bs 18.500) y lo adjudicado (Bs 17.900): **Bs 600**. Saldo de la partida 34200 = 80.000 − 18.500 + 600 = **Bs 62.100**.']);
IMGF('14-resumen-devengado.png', 'Resumen del trámite devengado', 6.0, 7);
PASO(15, 'cualquiera', 'Revisar el expediente completo', ['Pestaña **Documentos**: 7 PDF (C-1, Informe de Excepción CHB, Certificación C-31, Cuadro Comparativo, Nota de Adjudicación, Orden de Compra, Acta de Recepción), cada uno con versión, fecha y hash.']);
IMGF('15-documentos-expediente.png', 'Expediente digital completo', 6.0, 6);
H2('5.2 Lista de verificación del Ejemplo 1');
TABLE(['#', 'Comprobación', 'Esperado', 'OK'], [
  ['1', 'Total referencial', 'Bs 18.500,00', '☐'], ['2', 'Modalidad / método', 'Compra directa / Orden de Compra', '☐'],
  ['3', 'Cemento y ladrillo', 'Compra obligatoria CHB (bloquea envío)', '☐'], ['4', 'Tras excepción', 'Se envía; PDF C-1 + Informe de Excepción', '☐'],
  ['5', 'Saldo 34200 tras certificar', 'Bs 61.500', '☐'], ['6', 'Bloque SIGEP', '`01 | 001 | 01 | 0000 | 001 | 20 | 230 | 34200 | 18500.00`', '☐'],
  ['7', 'NIT repetido', 'Rechazado', '☐'], ['8', 'Ranking', '1.° MATERIALES BOLIVIA 17.900', '☐'],
  ['9', 'Contrato con plazo 10 días', 'Rechazado', '☐'], ['10', 'Recepción con faltante «conforme»', 'Rechazada', '☐'],
  ['11', 'Saldo 34200 tras devengar', 'Bs 62.100', '☐'], ['12', 'Documentos del expediente', '7 PDF', '☐']], [500, 3500, 4660, 700]);

// ---------------- 6 CASO 2
H1('6. Ejemplo 2 — Servicio: mantenimiento eléctrico, Bs 32.000');
P('**Objetivo:** validar Consulta de Precios SICOES (Formulario 110 obligatorio), fichas de cotización multicanal, mínimo de 3 cotizaciones, apertura de sobres tras el plazo, margen de preferencia MyPE y formalización con CUCE.');
P('**Partida:** 25800 (saldo Bs 45.000). Los servicios no están sujetos al catálogo CHB (estado «No aplica»).');
H2('6.1 Datos de entrada');
TABLE(['Dato', 'Valor'], [
  ['Objeto', 'Mantenimiento correctivo de las instalaciones eléctricas del edificio municipal'],
  ['Tipo / plazo', 'Servicio general / 12 días calendario'],
  ['Ítem único', 'Mantenimiento correctivo de instalaciones eléctricas (mano de obra y materiales) — Global — 1 × Bs 32.000,00'],
  ['Preventivo C-31', 'C31-2026-00456'],
  ['Formulario 110', 'F110-2026-000457, plazo de ofertas: 2 horas desde ahora'],
  ['Oferta 1', 'ELECTRO SERVICIOS S.R.L. — NIT 1020304050 — Bs 31.500 — 12 días'],
  ['Oferta 2', 'INSTALACIONES BOLIVIA LTDA. (MyPE) — NIT 2030405060 — Bs 30.800 — 10 días — registro MyPE válido, margen 5 %'],
  ['Oferta 3', 'MANTENIMIENTO INTEGRAL S.A. — NIT 3040506070 — Bs 29.900 — 12 días'],
  ['Oferta 4', 'OFERTAS BARATAS S.R.L. — NIT 4050607080 — Bs 28.000 — 12 días — **no cumple** (sin certificado de idoneidad)'],
  ['CUCE', '26-1234-00-1234567-1-1']], [2300, 7060]);
PASO(1, 'solicitante, presupuesto, rpa', 'Preparar el trámite', ['Como `solicitante` cree la solicitud (Servicio general, plazo 12) con el ítem de Bs 32.000 en la partida 25800 y envíela. Como `presupuesto` certifique con `C31-2026-00456` (saldo 25800: 45.000 → **13.000**). Como `rpa` apruebe el inicio.', '**Observe:** modalidad **Consulta de precios SICOES (Bs 20.001 a 50.000)**; formalización **Orden de Servicio**; no se genera informe de excepción CHB.']);
PASO(2, 'contrataciones', 'Comprobar que sin Formulario 110 no se puede cotizar', ['En la pestaña Cotizaciones, el sistema muestra que falta el N.° de Formulario 110 y bloquea la carga de ofertas y la emisión de fichas (API: `FORMULARIO_110_REQUERIDO`).']);
IMGF('17-f110-requerido.png', 'Consulta de precios: el F110 es requisito previo', 6.0, 5.5);
PASO(3, 'contrataciones', 'Registrar F110 y emitir fichas de cotización', ['Registre `F110-2026-000457` y la **fecha límite de presentación** (hoy + 2 horas). Presione **Emitir y enviar fichas de cotización**: ingrese el proveedor y elija los canales **Impreso (PDF)**, **WhatsApp** (se genera el enlace `https://wa.me/591…?text=…`) y **Correo** (si no hay SMTP configurado responde «NO_CONFIGURADO», sin fallar).']);
IMGF('18-f110-registrado.png', 'F110 registrado y diálogo de emisión de fichas multicanal', 6.0, 6);
PASO(4, 'contrataciones', 'Cargar las 4 ofertas y probar la apertura anticipada', ['Registre las 4 ofertas. Presione **Abrir ofertas** antes de que venza el plazo: el sistema responde `PLAZO_VIGENTE` («Aún no vence el plazo de presentación de ofertas»).',
  '**Cómo probar el vencimiento sin esperar:** (a) registre una fecha límite de pocos minutos y espere; o (b) solo para pruebas, ejecute en la base: `UPDATE contrataciones_menores SET fecha_limite_ofertas = now() - interval \'5 minutes\' WHERE correlativo_interno = \'CM-AAAA-NNNNNN\';`. Luego abra las ofertas.']);
PASO(5, 'contrataciones', 'Calificar con margen de preferencia MyPE', ['Califique: Oferta 1 y 3 «Cumple»; Oferta 2 «Cumple» con **registro de preferencia MyPE válido** y margen **5 %**; Oferta 4 «No cumple» con la observación «No presenta certificado de idoneidad».',
  '**Resultado esperado (ver figura):** precio evaluado de la Oferta 2 = 30.800 × 0,95 = **Bs 29.260**, que supera a la Oferta 3 (29.900) gracias al margen: queda **1.°, Recomendada**. La Oferta 4, aunque es la más barata, queda **excluida**. El margen solo se aplica con registro válido.']);
IMGF('19-matriz-mype.png', 'Matriz con margen de preferencia MyPE: la Oferta 2 pasa al primer lugar', 6.0, 8);
PASO(6, 'contrataciones', 'Probar el mínimo de cotizaciones', ['En un trámite aparte con solo 2 ofertas, **Evaluar** responde `COTIZACIONES_INSUFICIENTES`. Con 4 ofertas el trámite se evalúa y queda **EVALUADO**.']);
PASO(7, 'rpa', 'Adjudicar y formalizar con CUCE', ['Como `rpa` intente adjudicar a la Oferta 3 sin motivo (rechazado) y a la Oferta 4 (rechazado, no elegible). Adjudique la recomendada. En **Formalización** ingrese el **CUCE** `26-1234-00-1234567-1-1` (en consulta de precios es obligatorio) y formalice: se emite **Orden de Servicio**.']);
IMGF('20-formalizar-cuce.png', 'Formalización de consulta de precios con CUCE', 6.0, 5.5);
PASO(8, 'recepcion, presupuesto', 'Recepción y devengado', ['Recepción conforme (se emite el **Informe de conformidad IC-…**). Devengado: se libera Bs 1.200 (32.000 − 30.800). Saldo 25800 = 45.000 − 32.000 + 1.200 = **Bs 14.200**.']);
H2('6.2 Variante: plazo de 20 días (Contrato Administrativo)');
P('Cree el mismo trámite con **plazo 20 días**. El sistema calcula formalización **Contrato**. Al formalizar, si se intenta Orden de Servicio/Compra responde `FORMALIZACION_CONTRATO_OBLIGATORIO`. Al formalizar correctamente se emite el **Contrato Administrativo** y no la orden.');
H2('6.3 Lista de verificación del Ejemplo 2');
TABLE(['#', 'Comprobación', 'Esperado', 'OK'], [
  ['1', 'Modalidad', 'Consulta de precios SICOES', '☐'], ['2', 'Cotizar sin F110', 'Rechazado', '☐'],
  ['3', 'Saldo 25800 tras certificar', 'Bs 13.000', '☐'], ['4', 'Abrir antes del plazo', '`PLAZO_VIGENTE`', '☐'],
  ['5', 'Precio evaluado Oferta 2', 'Bs 29.260 (1.°)', '☐'], ['6', 'Oferta 4', 'Excluida (no cumple)', '☐'],
  ['7', 'Evaluar con < 3 ofertas', '`COTIZACIONES_INSUFICIENTES`', '☐'], ['8', 'Formalizar sin CUCE', 'Rechazado', '☐'],
  ['9', 'Método con plazo 12', 'Orden de Servicio', '☐'], ['10', 'Método con plazo 20', 'Contrato Administrativo', '☐'],
  ['11', 'Saldo 25800 al devengar', 'Bs 14.200', '☐']], [500, 3500, 4660, 700]);

// ---------------- 7 Verificación
H1('7. Verificación de autenticidad de documentos');
P('Cada PDF lleva un **código QR** que apunta a `{PUBLIC_BASE_URL}/verificar/{id}`. Esa página es **pública** (no requiere iniciar sesión) y muestra tipo de documento, versión, trámite, estado y los hashes registrados.');
N(['Abra un PDF del expediente (por ejemplo el Acta de recepción) y escanee el QR con el celular, o copie la URL desde la pestaña Documentos.',
  'En la página de verificación confirme que el documento figura «registrado en el expediente digital» y si es la **versión vigente**.',
  'Presione **Choose File**, cargue el PDF que recibió: el sistema calcula su SHA-256 y lo compara. **Coincide** → «El archivo es auténtico». **No coincide** → alertas de alteración. El archivo no se almacena.',
  '**Prueba de alteración:** descargue un PDF, modifíquelo (por ejemplo, abriéndolo y guardándolo con otro programa) y cárguelo: debe indicar que **NO coincide**.']);
IMGF('16-verificacion-publica.png', 'Página pública de verificación', 5.6, 5.8);
NOTE('El hash impreso al pie de cada PDF es el del **contenido canónico** (un archivo no puede imprimir su propio hash). El hash del **archivo final** se guarda en la base y es el que se compara al cargar el PDF.', 'E8F1FB', 'Cómo leerlo');

// ---------------- 8 Admin
H1('8. Administración');
H2('8.1 Usuarios y roles');
P('Menú **Usuarios** (solo `admin`): crear usuarios, asignar uno de los 6 roles, activar/desactivar y restablecer contraseñas (≥ 10 caracteres con mayúscula, minúscula y número; se almacenan con Argon2id).');
IMGF('22-usuarios.png', 'Gestión de usuarios', 6.0, 4.5);
H2('8.2 Catálogo Compro Hecho en Bolivia');
P('Menú **Catálogo CHB**: busque por código o descripción y agregue bienes (código UNSPSC de 8 dígitos, unidad y precio referencial nacional). Cargue aquí el catálogo oficial de su entidad; los cinco bienes incluidos son ilustrativos.');
IMGF('23-catalogo.png', 'Catálogo CHB', 6.0, 4.5);
H2('8.3 Parámetros del GAM');
P('Menú **Parámetros del GAM**: nombre y ciudad del GAM (membrete de los PDF), DA/UE, gestión, logotipo y los parámetros normativos.');
IMGF('24-parametros.png', 'Parámetros institucionales', 6.0, 5);
TABLE(['Parámetro', 'Defecto', 'Uso'], [
  ['`tope_contratacion_menor`', '50000', 'Sobre este monto se bloquea y se deriva a ANPE'], ['`tope_compra_directa`', '20000', 'Hasta este monto no se exige consulta de precios'],
  ['`plazo_orden_max_dias`', '15', 'Hasta este plazo Orden; sobre él Contrato'], ['`min_cotizaciones_consulta`', '3', 'Mínimo en consulta de precios (supuesto)'],
  ['`min_cotizaciones_directa`', '1', 'Mínimo en compra directa'], ['`chb_min_justificacion`', '80', 'Longitud mínima de la justificación CHB']], [3200, 1200, 4960]);
H2('8.4 Auditoría inalterable');
P('Menú **Auditoría**: cada acción (inicios de sesión, creación, envío, certificación, adjudicación…) queda registrada con usuario, IP, datos previos/nuevos y un hash SHA-256 que encadena el registro anterior. En PostgreSQL un *trigger* impide modificar o borrar filas. Presione **Verificar integridad de la cadena** para recalcular todos los hashes.');
IMGF('21-auditoria.png', 'Auditoría con verificación de integridad de la cadena', 6.0, 6);

// ---------------- 9 Pruebas negativas
H1('9. Guía de pruebas: casos positivos y negativos');
P('Use esta tabla como plan de pruebas de aceptación. «Mensaje/código» es lo que debe ver (interfaz) o recibir (API).');
TABLE(['#', 'Prueba', 'Usuario', 'Resultado esperado'], [
  ['1', 'Ítems que suman Bs 50.001', 'solicitante', 'Bloqueo: «El monto supera el límite de Contratación Menor (Bs 50.000). Derive a la modalidad ANPE»'],
  ['2', 'Bien del catálogo sin excepción', 'solicitante', '422 `SOLICITUD_INCOMPLETA` (CHB)'],
  ['3', 'Justificación CHB de menos de 80 caracteres', 'solicitante', 'Rechazada'],
  ['4', 'Plazo 20 días + orden simple', 'rpa', '422 `FORMALIZACION_CONTRATO_OBLIGATORIO`'],
  ['5', 'Certificar con saldo insuficiente', 'presupuesto', 'Rechazado; ningún saldo se descuenta (todo o nada)'],
  ['6', 'Cotizar sin F110 (> 20.000)', 'contrataciones', '422 `FORMULARIO_110_REQUERIDO`'],
  ['7', 'Abrir ofertas antes del plazo', 'contrataciones', '422 `PLAZO_VIGENTE`'],
  ['8', 'NIT duplicado en cotizaciones', 'contrataciones', 'Rechazado'],
  ['9', 'Evaluar con menos de 3 ofertas (consulta)', 'contrataciones', '422 `COTIZACIONES_INSUFICIENTES`'],
  ['10', 'Adjudicar oferta no elegible', 'rpa', 'Rechazado'],
  ['11', 'Un solicitante intenta certificar', 'solicitante', '403 `ROL_NO_AUTORIZADO`'],
  ['12', 'Acción fuera de secuencia (devengar en BORRADOR)', 'presupuesto', '409 estado inválido'],
  ['13', '5 contraseñas erróneas', 'cualquiera', '423 cuenta bloqueada 15 min'],
  ['14', 'Anular un trámite certificado', 'rpa/presupuesto', 'ANULADO; el saldo reservado se libera'],
  ['15', 'Declarar desierto', 'rpa', 'Trámite ANULADO con el motivo; saldo liberado'],
  ['16', 'Auditoría → Verificar integridad', 'admin', 'Cadena íntegra']], [450, 3300, 1500, 4110]);

// ---------------- 10 Pruebas automáticas y API
H1('10. Pruebas automáticas y prueba por API');
H2('10.1 Pruebas del backend (pytest)');
CODE('cd sicom-muni/backend\npip install -r requirements-dev.txt\npytest                       # SQLite en memoria\nTEST_DATABASE_URL=postgresql+psycopg://sicom:sicom@127.0.0.1:5433/sicom_test pytest   # PostgreSQL real');
TABLE(['Archivo', 'Qué prueba'], [
  ['`test_unitarias_reglas.py`', 'Cuantía, formalización por plazo, CHB, evaluador, margen de preferencia, desempate'],
  ['`test_flujo_bienes.py`', 'Ejemplo 1 completo (Bs 18.500) de BORRADOR a DEVENGADO'],
  ['`test_flujo_servicio.py`', 'Ejemplo 2 (Bs 32.000), mínimo de cotizaciones, variante de Contrato'],
  ['`test_auth_rbac.py`', 'Login, refresh rotativo, bloqueo, permisos por rol'],
  ['`test_reglas_negativas.py`', 'Casos que deben rechazarse'],
  ['`test_documentos_auditoria.py`', 'PDF, QR, hash, verificación pública y cadena de auditoría']], [3200, 6160]);
P('Resultado esperado: todas las pruebas en verde (62 con PostgreSQL; 61 con SQLite, pues la prueba del trigger de auditoría solo corre en PostgreSQL).');
H2('10.2 Pruebas del frontend');
CODE('cd sicom-muni/frontend\nnpm ci\nnpx tsc --noEmit      # tipos\nnpm run lint\nnpm test              # Vitest\nnpm run build');
H2('10.3 Probar la API con curl');
P('La documentación interactiva está en `/api/docs` (Swagger) si expone el puerto 8000. Ejemplo mínimo:');
CODE('API=http://localhost:3000/api/v1\nTOKEN=$(curl -s -X POST $API/auth/login -H "Content-Type: application/json" \\\n  -d \'{"username":"solicitante","password":"Sicom#2026Demo"}\' | python -c "import sys,json;print(json.load(sys.stdin)[\'access_token\'])")\n\n# Simular reglas sin crear trámite\ncurl -s "$API/contrataciones/reglas/simular?monto=32000&plazo=12&tipo_objeto=SERVICIO_GENERAL" \\\n  -H "Authorization: Bearer $TOKEN"\n\n# Listar partidas\ncurl -s $API/partidas -H "Authorization: Bearer $TOKEN"');
NOTE('Resultado esperado del simulador: modalidad `CONSULTA_PRECIOS_SICOES`, `requiere_formulario_110: true`, método de formalización `ORDEN_SERVICIO`.', 'E8F1FB', 'Respuesta');
H2('10.4 Generar un expediente demo automático');
P('Para ver todos los PDF sin usar la interfaz: `cd backend && python scripts/generar_expediente_demo.py`. Recorre el flujo completo contra una base temporal y deja los PDF para inspección.');

// ---------------- 11 Seguridad / operación
H1('11. Seguridad, respaldo y operación');
H2('11.1 Seguridad');
B(['Contraseñas con **Argon2id**; política ≥ 10 caracteres; bloqueo tras 5 intentos fallidos.',
  'Token de acceso JWT de 15 minutos en memoria del navegador; **refresh token rotativo** en cookie HTTP-only/SameSite=Strict (guardado como hash; su reutilización invalida la sesión).',
  'RBAC por acción y estado; respuestas 403/409/422 coherentes.',
  'Ofertas **selladas**: monto cifrado (Fernet) hasta la apertura legítima.',
  'Auditoría solo-inserción con cadena de hashes.',
  'PDF generados sin acceso a recursos externos (el motor solo admite imágenes `data:`).',
  '**En producción:** HTTPS con proxy inverso (Nginx/Caddy/Traefik), `COOKIE_SECURE=true`, claves distintas a las del ejemplo, consola de MinIO solo local.']);
H2('11.2 Respaldo y restauración');
CODE('# Respaldo diario de la base\ndocker compose exec db pg_dump -U sicom sicom > respaldo_$(date +%F).sql\n# Restauración\ndocker compose exec -T db psql -U sicom sicom < respaldo_2026-01-31.sql\n# Archivos PDF: respaldar el volumen miniodata (o usar `mc mirror`)');
H2('11.3 Actualización');
CODE('git pull\ndocker compose up -d --build   # las migraciones se aplican al iniciar el backend');

// ---------------- 12 Limitaciones
H1('12. Limitaciones y validaciones pendientes');
P('Para uso institucional real, la entidad debe validar lo siguiente con su asesoría legal y de sistemas:');
B(['**Normativa no verificada.** Los topes (Bs 50.000 y Bs 20.000), el plazo de 15 días, el mínimo de 3 cotizaciones, el catálogo y las referencias a D.S. 4505, a los formularios (F110, C-31, Form. 500) y a los márgenes Pro-Bolivia/MyPE provienen del encargo y **no fueron contrastados con la normativa vigente**. Son parámetros configurables.',
  '**Supuestos del sistema:** una oferta es elegible si cumple, no supera el monto referencial y su plazo no excede el solicitado; el desempate favorece a la primera propuesta recibida; mínimo 3 cotizaciones en consulta de precios y 1 en compra directa.',
  '**Sin integración** con SIGEP ni SICOES: el sistema genera el bloque de captura y registra los números (C-31, F110, CUCE) que el operador obtiene allí.',
  '**Datos ilustrativos:** códigos de partida, catálogo CHB y usuarios demo.',
  '**Docker:** los Dockerfile y el compose se validaron estáticamente; las imágenes no pudieron construirse en el entorno de desarrollo.',
  '**Correo:** sin SMTP configurado, el envío de fichas por correo devuelve `NO_CONFIGURADO`.',
  'Los archivos PDF de un intento fallido pueden quedar huérfanos en el almacenamiento aunque la transacción de base de datos se revierta; no afectan el expediente.']);

// ---------------- 13 Troubleshooting
H1('13. Solución de problemas');
TABLE(['Síntoma', 'Causa probable y solución'], [
  ['Pantalla «Verificando sesión…» infinita', 'Los archivos estáticos del frontend no cargan (404 en `/_next/static`). En modo *standalone* copie `.next/static` y `public` dentro de `.next/standalone` y reinicie.'],
  ['Backend: «relation does not exist»', 'Falta `alembic upgrade head`.'],
  ['PDF vacío o error de WeasyPrint', 'Faltan librerías pango/harfbuzz/fuentes (la imagen Docker ya las incluye).'],
  ['La sesión se pierde al recargar', '`COOKIE_SECURE=true` sin HTTPS, o frontend y API en dominios distintos.'],
  ['El QR apunta a localhost', 'Configure `PUBLIC_BASE_URL` o el parámetro `url_publica`.'],
  ['423 al iniciar sesión', 'Cuenta bloqueada 15 min; el admin puede restablecer la clave.'],
  ['`FORMULARIO_110_REQUERIDO`', 'Monto > 20.000: registre el F110 antes de cotizar.'],
  ['Error del trigger de auditoría', 'Use PostgreSQL 15+ (SQLite solo sirve para pruebas).'],
  ['Puerto 3000 ocupado', 'Cambie el mapeo en `docker-compose.yml` (`"8080:3000"`).']], [3000, 6360]);

H1('Anexo A. Datos demo');
TABLE(['Usuario', 'Nombre (ficticio)', 'Rol'], [
  ['solicitante', 'María Lidia Quispe Mamani', 'Solicitante'], ['presupuesto', 'Juan Carlos Mendoza Rojas', 'Presupuesto'],
  ['contrataciones', 'Rosario Elena Vargas Choque', 'Contrataciones'], ['rpa', 'Ing. Fernando Luis Condori Apaza', 'RPA'],
  ['recepcion', 'Pedro Pablo Mamani Flores', 'Recepción'], ['admin', 'Administrador del Sistema', 'Administrador']], [2000, 4400, 2960]);
TABLE(['Partida', 'Descripción', 'Saldo inicial (Bs)'], [
  ['39500', 'Útiles de escritorio y oficina', '30.000,00'], ['34200', 'Productos minerales y no metálicos (materiales de construcción)', '80.000,00'],
  ['25800', 'Mantenimiento y reparación de inmuebles y equipos', '45.000,00'], ['43100', 'Equipo de oficina y muebles', '60.000,00']], [1500, 5360, 2500]);
P('Estructura programática demo: Programa 01 / Proyecto 0000 / Actividad 001 / Fuente 20 / Organismo 230. Catálogo CHB demo: 30111505 cemento, 30131501 ladrillo, 14111507, 43211500, 56101500.');

const doc = new Document({
  creator: 'SICOM-MUNI', title: 'Manual de Implementación y Prueba — SICOM-MUNI',
  styles: { default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 34, bold: true, color: AZUL, font: 'Calibri' }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 27, bold: true, color: '2E75B6', font: 'Calibri' }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 24, bold: true, font: 'Calibri' }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } }] },
  numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    ...numRefs.map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] }))] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1200, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run('SICOM-MUNI — Manual de Implementación y Prueba', { size: 18, color: '888888' })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Página ', { size: 18, color: '888888' }), new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '888888' })] })] }) },
    children: kids }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync('/home/user/Factura/sicom-muni/docs/MANUAL_IMPLEMENTACION_SICOM-MUNI.docx', b); console.log('ok', b.length); });
