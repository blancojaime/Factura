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

kids.push(new Paragraph({ spacing: { before: 2200 }, alignment: AlignmentType.CENTER, children: [run('SICOM-MUNI', { bold: true, size: 72, color: AZUL })] }));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run('GUÍA DE PRUEBA PARA PRINCIPIANTES', { bold: true, size: 40 })] }));
kids.push(new Paragraph({ spacing: { before: 200 }, alignment: AlignmentType.CENTER, children: [run('Cómo instalar y probar el sistema sin conocimientos de informática', { size: 28, color: '555555' })] }));
kids.push(new Paragraph({ spacing: { before: 1600 }, alignment: AlignmentType.CENTER, children: [run('Cada paso indica exactamente qué botón pulsar y qué texto escribir.', { size: 24 })] }));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Tiempo estimado: 30 minutos de instalación (la primera vez) + 40 minutos de prueba.', { size: 22, color: '555555' })] }));

H1('0. Antes de empezar');
H2('0.1 Qué va a hacer');
P('Va a poner el sistema a funcionar **en su propio computador** (nadie más lo verá) y a recorrer una compra completa, desde que un funcionario la solicita hasta que se registra el pago. Todo lo que escriba es de prueba; puede repetirlo cuantas veces quiera.');
H2('0.2 Qué necesita');
B(['Un computador con **Windows 10 u 11**, 8 GB de memoria (RAM) y 10 GB libres en el disco.', 'Conexión a internet (para descargar los programas la primera vez).', 'Una cuenta de GitHub con acceso al proyecto `blancojaime/Factura` (si el repositorio es privado, el propietario debe darle acceso).', 'Un navegador: Chrome, Edge o Firefox.']);
H2('0.3 Palabras que verá');
TABLE(['Palabra', 'Qué significa'], [
  ['Docker Desktop', 'Un programa gratuito que «enciende» el sistema dentro de su computador sin que usted tenga que configurar nada más.'],
  ['ZIP', 'Una carpeta comprimida (como una caja cerrada). Hay que «extraerla» para usar lo que contiene.'],
  ['Navegador', 'El programa con el que entra a internet (Chrome, Edge…). El sistema se usa desde ahí.'],
  ['`localhost:3000`', 'La dirección del sistema en SU computador. Se escribe en la barra de direcciones del navegador.']], [2400, 6960]);
NOTE('Si prefiere no hacerlo usted mismo, entregue esta guía a la persona de sistemas de su entidad: la Parte 1 (instalación) le tomará 15 minutos. Después usted solo necesita la Parte 2.', 'E8F1FB', 'Opción');

H1('PARTE 1 — Instalar el sistema (se hace una sola vez)');
H2('Paso 1.1 — Instalar Docker Desktop');
N(['Abra su navegador y entre a: `https://www.docker.com/products/docker-desktop`',
  'Pulse el botón **Download Docker Desktop** y elija **Windows** (si pregunta por el tipo, elija **AMD64**, que corresponde a la mayoría de los computadores; si su equipo es un Surface/Snapdragon elija ARM64).',
  'Cuando termine la descarga, abra el archivo `Docker Desktop Installer.exe` (aparece abajo en el navegador o en la carpeta **Descargas**). Si Windows pregunta «¿Desea permitir que esta aplicación haga cambios?», pulse **Sí**.',
  'En la ventana del instalador deje marcada la casilla **Use WSL 2** (viene marcada) y pulse **OK**. Espere unos minutos.',
  'Al terminar pulse **Close and restart** (cerrar y reiniciar). El computador se reiniciará.',
  'Cuando vuelva a encender, abra **Docker Desktop** desde el menú Inicio (ícono de una ballena azul). Si aparece un acuerdo de servicio, pulse **Accept**. Si le pide crear una cuenta, pulse **Skip** (omitir) o «Continue without signing in».',
  '**Espere** hasta que abajo a la izquierda de la ventana de Docker se vea un círculo **verde** y el texto **Engine running**. Esto puede tardar 1 a 3 minutos. **Deje Docker Desktop abierto** (puede minimizarlo).']);
NOTE('Si Docker muestra un mensaje rojo sobre «virtualización» o «WSL», pida a la persona de sistemas que active la virtualización en el equipo (se hace una vez en la BIOS) y que ejecute `wsl --install` en PowerShell.', 'FDE9E7', 'Problema frecuente');

H2('Paso 1.2 — Descargar el sistema');
N(['En el navegador entre a `https://github.com/blancojaime/Factura` e inicie sesión en GitHub si se lo pide.',
  'Arriba a la izquierda, junto a la palabra **Code**, hay un botón gris que dice **main** (o el nombre de una rama). Púlselo y escriba `claude/tender-einstein-76nc7n`; elíjala en la lista. (Si ya se unió el trabajo a la rama principal, deje **main**.)',
  'Pulse el botón verde **<> Code** y luego **Download ZIP**. Se descargará un archivo, por ejemplo `Factura-claude-tender-einstein-76nc7n.zip`, normalmente en la carpeta **Descargas**.',
  'Abra la carpeta **Descargas**, haga **clic derecho** sobre el archivo ZIP y elija **Extraer todo…**',
  'En «Los archivos se extraerán en esta carpeta», borre lo que aparece y escriba `C:\\SICOM` (una ruta corta evita problemas). Pulse **Extraer**.',
  'Abra la carpeta `C:\\SICOM`. Dentro hay otra carpeta con nombre largo; entre a ella y luego a la carpeta **sicom-muni**. Allí verá archivos como `INICIAR-WINDOWS.bat`, `docker-compose.yml` y las carpetas `backend`, `frontend` y `docs`.']);

H2('Paso 1.3 — Encender el sistema');
N(['Compruebe que **Docker Desktop está abierto** y con el círculo verde (Engine running).',
  'En la carpeta `sicom-muni`, haga **doble clic** en **INICIAR-WINDOWS.bat**.',
  'Si Windows muestra una pantalla azul «Windows protegió su PC», pulse **Más información** y luego **Ejecutar de todas formas**.',
  'Se abrirá una **ventana negra** con texto. **No la cierre.** Verá los avisos `[1/4]`, `[2/4]`, `[3/4]` y `[4/4]`. El paso `[2/4]` descarga e instala componentes: **la primera vez tarda entre 5 y 15 minutos** y se ven muchas líneas de texto; es normal.',
  'Si Windows pregunta por el **Firewall**, pulse **Permitir acceso**.',
  'Cuando la ventana negra muestre **LISTO**, el navegador se abrirá solo en `http://localhost:3000`. Si no se abre, escriba usted esa dirección en la barra del navegador.',
  'Verá la pantalla de **inicio de sesión** (azul, con el título SICOM-MUNI). **El sistema está funcionando.** Ya puede cerrar la ventana negra pulsando una tecla (el sistema sigue encendido).']);
IMGF('01-login.png', 'Pantalla de inicio de sesión: si la ve, la instalación fue exitosa', 5.0, 4.6);
H2('Paso 1.4 — Apagar y volver a encender');
B(['**Apagar:** doble clic en **DETENER-WINDOWS.bat** (sus datos de prueba se conservan).', '**Encender otra vez:** doble clic en **INICIAR-WINDOWS.bat** (ahora tarda menos de 1 minuto).', 'Al reiniciar el computador, abra primero Docker Desktop, espere el círculo verde y luego use INICIAR-WINDOWS.bat.']);
H2('Paso 1.5 — Si algo no funciona');
TABLE(['Qué ve', 'Qué hacer'], [
  ['«Docker Desktop no está instalado»', 'Repita el Paso 1.1.'],
  ['«Docker Desktop NO está abierto»', 'Abra Docker Desktop, espere el círculo verde y repita el doble clic.'],
  ['El navegador dice «No se puede acceder a este sitio»', 'Espere 1 minuto más y recargue (tecla F5). El sistema aún está arrancando.'],
  ['La ventana negra se cierra enseguida', 'Abra el menú Inicio, escriba `cmd`, abra «Símbolo del sistema», arrastre `INICIAR-WINDOWS.bat` dentro de la ventana, pulse Enter y envíe una captura del mensaje de error a soporte.'],
  ['Mensaje de «puerto 3000 en uso»', 'Cierre otros programas que usen internet local o reinicie el computador.'],
  ['Sigue sin funcionar', 'Haga una captura de pantalla de la ventana negra y envíela a quien le dio el sistema.']], [3600, 5760]);

H1('ALTERNATIVA — Probar sin Docker');
P('Use esta opción **si Docker no funciona en su computador** (por ejemplo el error «Virtual Machine Platform not enabled» o «No virtualization available»). Es **solo para pruebas**: los datos se guardan en un archivo dentro de la carpeta y no tiene toda la protección de un servidor oficial.');
H2('Qué hace por usted');
B(['Instala **Python** y **Node.js** si no los tiene (los descarga con Windows, usando el programa «winget»).', 'Prepara el sistema y crea una base de datos de prueba con los usuarios de demostración.', 'Lo enciende y abre el navegador en `http://localhost:3000`.']);
H2('Paso a paso');
N(['Descargue y extraiga el sistema como en el **Paso 1.2** de esta guía (carpeta `C:\\SICOM`, luego `sicom-muni`). (No necesita Docker.)',
  'En la carpeta `sicom-muni` haga **doble clic** en **INICIAR-SIN-DOCKER.bat**. Si aparece «Windows protegió su PC», pulse **Más información → Ejecutar de todas formas**.',
  'Se abre una ventana azul con 6 etapas: `1/6` Python, `2/6` Node, `3/6` servidor, `4/6` pantalla web, `5/6` encendido, `6/6` espera. **No la cierre.**',
  'Si Windows pide **permiso de administrador** para instalar Python o Node, pulse **Sí**. Después de instalarlos, el programa continúa solo; si la ventana se cierra, vuelva a hacer doble clic en el mismo archivo.',
  'La **primera vez tarda entre 10 y 25 minutos** (descargas y compilación). Las siguientes veces tarda menos de 1 minuto.',
  'Cuando aparezca el cuadro verde **LISTO**, se abre el navegador. Entre con `solicitante` y `Sicom#2026Demo` y continúe en la **PARTE 2** de esta guía.']);
IMGF('01-login.png', 'Si ve esta pantalla, el sistema está funcionando', 4.6, 4.2);
H2('Apagar y volver a encender');
B(['**Apagar:** doble clic en **DETENER-SIN-DOCKER.bat**.', '**Encender:** doble clic en **INICIAR-SIN-DOCKER.bat** (los datos de prueba se conservan en la carpeta `.local`).']);
H2('Diferencias con la versión Docker');
TABLE(['Tema', 'Modo sin Docker'], [
  ['Base de datos', 'Archivo SQLite local (no PostgreSQL). Suficiente para probar.'],
  ['Documentos PDF', 'Si el equipo no tiene las librerías gráficas, los documentos se muestran como **página HTML imprimible**: se abre en el navegador y con **Ctrl + P → Guardar como PDF** se obtiene el PDF. Opcional: ejecute **INSTALAR-SOPORTE-PDF.bat** para generar PDF reales (puede tardar 10 minutos).'],
  ['Auditoría inalterable', 'Se registra y se verifica la cadena de huellas, pero **sin** el bloqueo a nivel de base de datos que ofrece PostgreSQL.'],
  ['Uso oficial', '**No** se recomienda: ver la sección «Cómo se trabajará de forma oficial».']], [2400, 6960]);
H2('Si algo falla');
TABLE(['Qué ve', 'Qué hacer'], [
  ['«Su Windows no tiene winget»', 'Instale a mano **Python 3.12** (python.org, marcando «Add python.exe to PATH») y **Node.js LTS** (nodejs.org) y repita el doble clic.'],
  ['Error rojo durante la instalación', 'Revise su conexión a internet y repita el doble clic; el programa continúa donde se quedó.'],
  ['El navegador no abre', 'Escriba `http://localhost:3000` en la barra de direcciones.'],
  ['Sigue sin funcionar', 'Envíe una captura de la ventana azul y los archivos de la carpeta `sicom-muni\\.local\\logs`.']], [3400, 5960]);

H1('PARTE 2 — Probar el sistema paso a paso');
P('Va a simular la compra de **material de construcción por Bs 18.500** para la plaza principal. En el sistema participan **seis personas** (usuarios). Usted hará el papel de cada una, **una a la vez**.');
H2('2.1 Reglas de oro');
B(['Para **cambiar de persona** pulse **Salir** (arriba a la derecha) y entre con el siguiente usuario. Todos usan la misma clave: `Sicom#2026Demo` (respete mayúsculas, el símbolo # y los números).',
  'Después de pulsar un botón espere el **aviso verde** o el cambio en pantalla. Si aparece un **aviso rojo**, léalo: el sistema le está explicando qué falta.',
  'Los textos entre comillas «así» o en `este formato` son los que debe **escribir tal cual**.',
  'Si se equivoca, no pasa nada: puede crear otra solicitud nueva y empezar de nuevo.']);
TABLE(['Orden', 'Usuario', 'Quién es', 'Qué hará'], [
  ['1', '`solicitante`', 'María, Jefa de Unidad de Obras', 'Pide los materiales'],
  ['2', '`presupuesto`', 'Juan Carlos, Responsable de Presupuesto', 'Asegura el dinero'],
  ['3', '`rpa`', 'Ing. Fernando, autoridad del proceso', 'Autoriza iniciar'],
  ['4', '`contrataciones`', 'Rosario, Encargada de compras', 'Recibe y compara ofertas'],
  ['5', '`rpa`', '(vuelve)', 'Adjudica y formaliza'],
  ['6', '`recepcion`', 'Pedro Pablo, Almacenes', 'Recibe los materiales'],
  ['7', '`presupuesto`', '(vuelve)', 'Registra el devengado (cierre)'],
  ['8', '`admin`', 'Administrador', 'Revisa la auditoría']], [800, 2000, 3560, 3000]);

H2('ETAPA A — La solicitud  (usuario: solicitante)');
PASO('A1', 'solicitante', 'Entrar al sistema', ['En la pantalla de inicio escriba **Usuario:** `solicitante` y **Contraseña:** `Sicom#2026Demo`. Pulse **Ingresar**. Verá «Hola, María» y cuatro cuadros con números.']);
IMGF('02-dashboard-solicitante.png', 'Panel de inicio de María (Solicitante)', 5.6, 4.6);
PASO('A2', 'solicitante', 'Crear la solicitud', ['Pulse el botón azul **Nueva solicitud**. Complete los campos así:']);
TABLE(['Campo', 'Qué escribir o elegir'], [
  ['Objeto de la contratación', 'Adquisición de material de construcción para mantenimiento de la plaza principal'],
  ['Tipo de objeto', 'Bien (ya viene elegido)'], ['Plazo de entrega / ejecución (días calendario)', '10'],
  ['Unidad solicitante', '(ya aparece «Jefa de Unidad de Obras»; déjelo)'], ['Lugar de entrega / ejecución', 'Plaza principal, calle Bolívar N° 123'],
  ['Justificación de la necesidad', 'Mantenimiento de la plaza principal programado en el POA.'],
  ['Redacción (mínimo 20 caracteres)', 'Materiales nuevos, de primera calidad, entregados en obra.']], [3600, 5760]);
P('Pulse **Guardar borrador y continuar**. Se abre la hoja del trámite con un número, por ejemplo `CM-2026-000001`, y la etiqueta «Borrador».');
PASO('A3', 'solicitante', 'Agregar los 4 materiales', ['Baje hasta el recuadro **«Agregar ítem»**. Para **cada fila de la tabla siguiente**: (1) escriba el código en el primer campo; (2) en **Partida presupuestaria** elija la que empieza con **34200**; (3) complete descripción, unidad, cantidad y precio; (4) pulse **Agregar**. Repita 4 veces.']);
TABLE(['Código', 'Descripción específica', 'Unidad', 'Cantidad', 'Precio unit. (Bs)'], [
  ['30111505', 'Cemento portland IP-30 bolsa de 50 kg', 'Bolsa', '120', '62.00'], ['30131501', 'Ladrillo cerámico de 6 huecos', 'Unidad', '3950', '1.30'],
  ['11111501', 'Arena fina lavada', 'm3', '30', '85.00'], ['11111503', 'Piedra chancada de 3/4 pulgada', 'm3', '25', '135.00']], [1500, 3400, 1100, 1300, 2060]);
P('**Qué debe ver:** al final la tabla de ítems suma **Total referencial Bs 18.500,00**. El cemento y el ladrillo salen con una etiqueta **roja «Compra obligatoria en CHB»**; la arena y la piedra con etiqueta **amarilla «Sin coincidencia en CHB»**. Abajo, en «3. Verificación normativa», dice **Compra directa (hasta Bs 20.000)** y **Orden de Compra**.');
NOTE('Si al escribir el código del cemento o del ladrillo aparece una casilla «Se compra fuera del catálogo por incompatibilidad», **no la marque todavía**: lo haremos en el paso A5 para ver cómo reacciona el sistema.', 'FFF4CE');
IMGF('03-formulador-chb.png', 'Así debe verse la hoja de la solicitud con los 4 ítems', 4.6, 8.5);
PASO('A4', 'solicitante', 'Probar que el sistema bloquea una compra irregular', ['Baje al final y observe el recuadro **rojo**: «Compra obligatoria en el Catálogo CHB — Ítem 1 (30111505)… Ítem 2 (30131501)…». El botón verde **Enviar solicitud a Presupuesto** está ahí: púlselo. **Resultado esperado:** aviso rojo que rechaza el envío. ✔ Primera regla comprobada: *si el bien existe en el catálogo Compro Hecho en Bolivia, no se puede comprar por fuera sin justificar*.']);
PASO('A5', 'solicitante', 'Registrar la excepción justificada', [
  '1) En la tabla de ítems, en la fila del **Cemento**, pulse el ícono del **lápiz**. Marque la casilla **«Se compra fuera del catálogo por incompatibilidad (requiere justificación)»** y pulse **Actualizar**. Haga lo mismo con el **Ladrillo**.',
  '2) Suba a la zona amarilla **«Justificación de compra fuera del Catálogo CHB»**. En **Justificación técnico-legal** escriba (debe tener al menos 80 caracteres): «Los proveedores del catálogo CHB no pueden entregar los materiales en el plazo de obra de 10 días ni en la cantidad requerida por la unidad; se fundamenta la compra directa en el mercado local.»',
  '3) En **Código de autorización CHB** escriba `MDPyEP-AUT-0391`. Pulse **Guardar datos**.',
  '4) Baje y pulse **Enviar solicitud a Presupuesto**.',
  '**Resultado esperado:** el estado cambia a **Solicitado**. En la pestaña **Documentos** aparecen dos PDF: **Formulario C-1 (Solicitud)** y el **Informe de Excepción CHB**. Pulse **Ver PDF** en uno para abrirlo: tiene membrete, marca de agua, un código QR y una huella (hash) al pie.']);
IMGF('04-documentos-c1.png', 'Pestaña Documentos con los dos PDF generados', 5.6, 4.4);
P('Pulse **Salir**.');

H2('ETAPA B — El dinero  (usuario: presupuesto)');
PASO('B1', 'presupuesto', 'Entrar y abrir el trámite', ['Entre con `presupuesto`. En «Pendientes de mi atención» aparece su trámite con «Qué debe hacer». Pulse **Abrir →**, y luego la pestaña **Presupuesto y SIGEP**.']);
IMGF('05-presupuesto-sigep.png', 'Pestaña Presupuesto y SIGEP antes de certificar', 5.6, 5);
PASO('B2', 'presupuesto', 'Certificar el presupuesto', ['En **N° de comprobante C-31 (SIGEP)** escriba `C31-2026-00123` y pulse **Certificar presupuesto**.',
  '**Resultado esperado:** estado **Presupuesto certificado**. El **Panel de captura rápida SIGEP** muestra una fila con DA 01, UE 001, Programa 01, Proyecto 0000, Actividad 001, Fte 20, Org 230, Partida 34200 e Importe 18.500,00. Pulse **Copiar Bloque SIGEP** (copia esa línea para pegarla en el SIGEP real; aquí solo se comprueba que aparece el aviso de copiado).',
  '**Comprobación del dinero:** en el menú izquierdo pulse **Presupuesto**: la partida 34200 ahora tiene saldo **80.000 − 18.500 = 61.500,00**.']);
IMGF('06-bloque-sigep-certificado.png', 'Bloque SIGEP listo para copiar', 5.6, 5);
P('Pulse **Salir**.');

H2('ETAPA C — La autorización  (usuario: rpa)');
PASO('C1', 'rpa', 'Aprobar el inicio', ['Entre con `rpa` (clave igual). Abra el trámite (**Abrir →**). Verá un recuadro con el botón verde **Aprobar inicio del proceso**. Púlselo. **Resultado esperado:** estado **En cotización**.']);
IMGF('07-rpa-aprobar-inicio.png', 'El RPA aprueba el inicio del proceso', 5.4, 4.2);
P('Pulse **Salir**.');

H2('ETAPA D — Las ofertas  (usuario: contrataciones)');
PASO('D1', 'contrataciones', 'Registrar las dos ofertas', ['Entre con `contrataciones`, abra el trámite y pulse la pestaña **Cotizaciones y adjudicación**. Baje a **«Registrar cotización (sobre sellado)»**. Complete y pulse **Registrar cotización** (dos veces, una por cada empresa):']);
TABLE(['Campo', 'Oferta 1', 'Oferta 2'], [
  ['NIT / CI', '1023456028', '4012345011'], ['Razón social', 'FERRETERIA EL CONSTRUCTOR S.R.L.', 'MATERIALES BOLIVIA LTDA.'],
  ['Monto total ofertado (Bs)', '18200', '17900'], ['Plazo ofertado (días)', '8', '10']], [3000, 3180, 3180]);
P('**Resultado esperado:** ambas aparecen en «Cotizaciones recibidas» pero con el monto **oculto (sellado)**: nadie puede ver cuánto ofertó cada empresa hasta abrir los sobres. **Prueba extra:** intente registrar otra vez el NIT `4012345011`; el sistema debe rechazarlo.');
IMGF('08-cotizaciones-selladas.png', 'Cotizaciones recibidas con los montos sellados', 5.6, 5);
PASO('D2', 'contrataciones', 'Abrir los sobres y calificar', ['Pulse **Abrir ofertas**. Ahora los montos son visibles. En la fila de cada empresa pulse **Calificar**, marque **«Cumple las especificaciones técnicas»** y pulse **Guardar calificación** (haga esto con las dos empresas).']);
IMGF('09-calificar-oferta.png', 'Ventana para calificar una oferta', 5.4, 5.4);
PASO('D3', 'contrataciones', 'Comparar y evaluar', ['Baje a la **Matriz comparativa — Precio Evaluado Más Bajo**. **Resultado esperado:** en el 1.er lugar, marcada **Recomendada**, está **MATERIALES BOLIVIA LTDA. (17.900,00)**; en el 2.º, FERRETERIA EL CONSTRUCTOR (18.200,00). Pulse **Evaluar y generar cuadro comparativo**. Estado: **Evaluado**. Se crea el PDF «Cuadro Comparativo».']);
IMGF('10-matriz-comparativa.png', 'Matriz comparativa con la oferta recomendada', 5.4, 6.2);
P('Pulse **Salir**.');

H2('ETAPA E — Adjudicar y formalizar  (usuario: rpa)');
PASO('E1', 'rpa', 'Adjudicar', ['Entre con `rpa`, abra el trámite, pestaña **Cotizaciones y adjudicación**. En el **Asistente de adjudicación** ya está seleccionada la oferta recomendada. Pulse el botón verde **Adjudicar**. Estado: **Adjudicado** (se crea la Nota de adjudicación).']);
IMGF('11-asistente-adjudicacion.png', 'Asistente de adjudicación', 5.4, 6);
PASO('E2', 'rpa', 'Formalizar con Orden de Compra', ['Pulse la pestaña **Formalización y recepción**. Verá que el sistema decidió **Orden de Compra** (porque el plazo es de 10 días, menor a 15). Pulse **Formalizar (Orden de Compra)**. Estado: **Formalizado**. Se genera el PDF de la Orden.']);
IMGF('12-formalizacion.png', 'Formalización', 5.4, 4.6);
P('Pulse **Salir**.');

H2('ETAPA F — Recepción de los materiales  (usuario: recepcion)');
PASO('F1', 'recepcion', 'Primero, una recepción con faltantes', ['Entre con `recepcion`, abra el trámite, pestaña **Formalización y recepción**. Verá la tabla «Verificación cuantitativa y cualitativa». En el cemento cambie **Recibido** de 120 a `100`. Deje marcada **Recepción conforme** y pulse **Registrar recepción**. **Resultado esperado:** aviso rojo (no puede declararse conforme si faltan 20 bolsas).',
  'Ahora **desmarque «Recepción conforme»**, en **Observaciones** escriba «Faltan 20 bolsas de cemento por entregar» y pulse **Registrar recepción**: queda anotada y el trámite sigue en **Formalizado**.']);
PASO('F2', 'recepcion', 'Recepción completa', ['Vuelva a poner `120` en el cemento, marque **Recepción conforme**, deje Observaciones vacío y pulse **Registrar recepción**. Estado: **Recepcionado**. Se genera el **Acta de recepción (Form. 500)**.']);
IMGF('13-recepcion.png', 'Formulario de recepción', 5.4, 5.4);
P('Pulse **Salir**.');

H2('ETAPA G — Cierre del dinero  (usuario: presupuesto)');
PASO('G1', 'presupuesto', 'Registrar el devengado', ['Entre con `presupuesto`, abra el trámite. Verá un aviso con el botón **Registrar devengado**: púlselo. Estado: **Devengado** (último paso).',
  '**Comprobación final del dinero:** menú **Presupuesto**: la partida 34200 muestra **62.100,00**. Explicación: se reservaron 18.500, pero se compró en 17.900; los **600** de diferencia se devolvieron al saldo (80.000 − 18.500 + 600 = 62.100).']);
IMGF('14-resumen-devengado.png', 'Trámite terminado (estado Devengado)', 5.4, 6.4);
IMGF('15-documentos-expediente.png', 'Expediente final: siete documentos PDF', 5.4, 5.5);

H2('ETAPA H — Comprobar que los documentos son auténticos');
PASO('H1', 'cualquiera', 'Verificar un PDF', ['En la pestaña **Documentos** pulse **Ver PDF** en el **Acta de recepción**: se abre o descarga un PDF (guárdelo en el Escritorio si el navegador solo lo muestra). Abajo a la derecha tiene un **código QR** y una huella al pie.',
  'Ahora, en esa misma fila, pulse el enlace **Verificar**: se abre una página nueva llamada «Verificación de autenticidad», con el tipo de documento, el trámite y su huella digital (esta página es pública: no pide usuario).',
  'En esa página pulse **Elegir archivo** (o *Choose File*), seleccione el PDF que guardó y el sistema responde **«El archivo es auténtico»**.']);
IMGF('16-verificacion-publica.png', 'Página de verificación', 5.0, 4.8);
NOTE('Para ver que detecta cambios: abra el PDF con un programa de edición de PDF, guárdelo con otro nombre y súbalo: dirá «El archivo NO coincide».', 'E8F1FB', 'Prueba extra');

H2('ETAPA I — Auditoría  (usuario: admin)');
PASO('I1', 'admin', 'Revisar quién hizo qué', ['Entre con `admin`. Menú **Auditoría**: verá cada acción realizada (inicios de sesión, solicitud enviada, certificado, adjudicado…) con fecha, hora y huella. Pulse **Verificar integridad de la cadena**: debe decir **«Cadena íntegra: N registros verificados»**. Esto demuestra que nadie modificó el historial.']);
IMGF('21-auditoria.png', 'Auditoría inalterable', 5.4, 5);

H1('PARTE 3 — Segunda prueba: un servicio de Bs 32.000');
P('Esta prueba comprueba lo que cambia cuando el monto supera Bs 20.000: se exige el **Formulario 110**, **tres cotizaciones como mínimo** y se aplica el **margen de preferencia a una microempresa (MyPE)**.');
H2('3.1 Preparación rápida (pasos ya conocidos)');
TABLE(['Quién', 'Qué hace'], [
  ['`solicitante`', 'Nueva solicitud: Objeto «Mantenimiento correctivo de las instalaciones eléctricas del edificio municipal»; Tipo de objeto **Servicio general**; plazo **12**; lugar «Edificio municipal»; justificación y redacción cualquiera (más de 20 letras). Un ítem: Descripción «Mantenimiento correctivo de instalaciones eléctricas (mano de obra y materiales)», Unidad «Global», Cantidad 1, Precio 32000, Partida **25800**. Pulse **Enviar solicitud a Presupuesto**.'],
  ['`presupuesto`', 'Comprobante `C31-2026-00456` → **Certificar presupuesto**. (Saldo de la partida 25800: 45.000 → 13.000).'],
  ['`rpa`', '**Aprobar inicio del proceso**.']], [1700, 7660]);
P('Observe en la hoja del trámite: **Consulta de precios SICOES (Bs 20.001 a 50.000)** y **Orden de Servicio**.');
H2('3.2 Formulario 110 y ofertas (usuario: contrataciones)');
PASO(1, 'contrataciones', 'Ver que el F110 es obligatorio', ['Pestaña **Cotizaciones y adjudicación**. Se muestra un aviso: falta el Formulario 110. Aún no puede registrar ofertas.']);
IMGF('17-f110-requerido.png', 'Sin Formulario 110 no se puede cotizar', 5.4, 5);
PASO(2, 'contrataciones', 'Registrar el F110', ['En **N° Formulario 110** escriba `F110-2026-000457`. En **Fecha y hora límite de presentación** elija la fecha de hoy y una hora **dentro de 2 horas**. Pulse **Registrar**.']);
PASO(3, 'contrataciones', 'Emitir las fichas de cotización (opcional)', ['Pulse **Emitir y enviar fichas de cotización**, escriba una línea `ELECTRO SERVICIOS S.R.L.; ventas@electro.bo; 71234567`, marque los canales y pulse **Emitir fichas**. Verá el enlace de WhatsApp y el PDF de la ficha; el correo dirá «NO_CONFIGURADO» (es normal en la prueba).']);
IMGF('18-f110-registrado.png', 'Fichas de cotización', 5.4, 5.4);
PASO(4, 'contrataciones', 'Registrar 4 ofertas', ['Registre estas cuatro cotizaciones (NIT, razón social, monto, plazo):']);
TABLE(['NIT', 'Razón social', 'Monto (Bs)', 'Plazo'], [
  ['1020304050', 'ELECTRO SERVICIOS S.R.L.', '31500', '12'], ['2030405060', 'INSTALACIONES BOLIVIA LTDA. (MyPE)', '30800', '10'],
  ['3040506070', 'MANTENIMIENTO INTEGRAL S.A.', '29900', '12'], ['4050607080', 'OFERTAS BARATAS S.R.L.', '28000', '12']], [1700, 4300, 1800, 1560]);
PASO(5, 'contrataciones', 'Intentar abrir antes de tiempo', ['Pulse **Abrir ofertas**: el sistema debe rechazarlo («Aún no vence el plazo de presentación de ofertas»). Para continuar **sin esperar 2 horas**, pida a la persona de sistemas que ejecute el comando de la nota siguiente, o simplemente espere a que pase la hora límite y pulse **Abrir ofertas**.']);
NOTE('Solo para pruebas — comando para vencer el plazo (lo ejecuta la persona de sistemas en la ventana de comandos, dentro de la carpeta sicom-muni): `docker compose exec db psql -U sicom -d sicom -c "update contrataciones_menores set fecha_limite_ofertas = now() - interval \'5 minutes\' where estado = \'EN_COTIZACION\'"`', 'FFF4CE', 'Atajo');
PASO(6, 'contrataciones', 'Calificar', ['Con las ofertas abiertas pulse **Calificar** en cada una: ELECTRO y MANTENIMIENTO INTEGRAL → marque «Cumple»; **INSTALACIONES BOLIVIA** → marque «Cumple», en **Registro de preferencia** elija **MyPE**, marque **«El registro es válido y vigente»** y en **Margen de preferencia (%)** escriba `5`; **OFERTAS BARATAS** → déjela **sin marcar** «Cumple» y en Observaciones escriba «No presenta certificado de idoneidad».']);
PASO(7, 'contrataciones', 'Leer la matriz', ['**Resultado esperado:** INSTALACIONES BOLIVIA queda **1.ª y Recomendada** con precio evaluado **29.260,00** (30.800 menos el 5 % de preferencia), superando a MANTENIMIENTO INTEGRAL (29.900). OFERTAS BARATAS aparece **atenuada y excluida**, aunque sea la más barata, porque no cumple. Pulse **Evaluar y generar cuadro comparativo**.']);
IMGF('19-matriz-mype.png', 'Matriz con margen de preferencia', 5.4, 7);
H2('3.3 Cierre (usuarios: rpa → recepcion → presupuesto)');
TABLE(['Quién', 'Qué hace', 'Resultado'], [
  ['`rpa`', 'Pestaña Cotizaciones → **Adjudicar** (recomendada).', 'Adjudicado'],
  ['`rpa`', 'Pestaña Formalización: en **CUCE** escriba `26-1234-00-1234567-1-1`; pulse **Formalizar (Orden de Servicio)**. (Sin CUCE el sistema lo rechaza.)', 'Formalizado'],
  ['`recepcion`', 'Pestaña Formalización → **Recepción conforme** → **Registrar recepción**.', 'Recepcionado + Informe de conformidad'],
  ['`presupuesto`', '**Registrar devengado**.', 'Devengado. Saldo 25800 = 14.200,00']], [1700, 5400, 2260]);
IMGF('20-formalizar-cuce.png', 'Formalización con CUCE', 5.4, 4.8);

H1('PARTE 4 — Lista final de comprobación');
P('Marque cada casilla a medida que lo vea con sus propios ojos. Si todo está marcado, el sistema funciona como se diseñó.');
TABLE(['#', 'Qué comprobar', '✔'], [
  ['1', 'Al ingresar los 4 ítems el total es Bs 18.500,00 y dice «Compra directa» y «Orden de Compra»', '☐'],
  ['2', 'Cemento y ladrillo salen en rojo y el sistema impide enviar sin justificación', '☐'],
  ['3', 'Tras justificar, se generan los PDF C-1 e Informe de Excepción', '☐'],
  ['4', 'Al certificar, el saldo de la partida 34200 baja a 61.500,00 y aparece el bloque SIGEP', '☐'],
  ['5', 'Las ofertas se ven «selladas» hasta pulsar Abrir ofertas', '☐'],
  ['6', 'La oferta de Bs 17.900 queda primera y recomendada', '☐'],
  ['7', 'Recepción con faltante marcada como conforme es rechazada', '☐'],
  ['8', 'Al devengar, el saldo de 34200 queda en 62.100,00', '☐'],
  ['9', 'El expediente tiene 7 PDF y la página de verificación dice «auténtico»', '☐'],
  ['10', 'Auditoría: «Cadena íntegra»', '☐'],
  ['11', 'Servicio de Bs 32.000: no se puede cotizar sin Formulario 110', '☐'],
  ['12', 'No se puede abrir ofertas antes del plazo', '☐'],
  ['13', 'La oferta MyPE (29.260) queda 1.ª y la más barata que no cumple queda excluida', '☐'],
  ['14', 'Sin CUCE no se puede formalizar; con plazo 12 días se emite Orden de Servicio', '☐'],
  ['15', 'Saldo de la partida 25800 final: 14.200,00', '☐']], [500, 8000, 860]);
H2('Prueba extra: plazo de 20 días');
P('Cree otra solicitud igual a la del servicio pero con **Plazo = 20**. En la hoja del trámite dirá **Contrato** en lugar de Orden de Servicio. Al llegar a Formalizar (pasos de la Parte 3), el botón será **Formalizar (Contrato)** y se generará un **Contrato Administrativo**.');
H1('Cómo se trabajará de forma oficial');
P('Las dos formas de prueba (Docker en su PC y «sin Docker») son para **conocer** el sistema. En el uso real **no se instala en cada computador**: se instala **una sola vez en un servidor** de la entidad y todos los funcionarios entran con su navegador a una dirección propia, por ejemplo `https://sicom.micomuna.gob.bo`.');
CODE('PC de funcionarios (solo navegador) --HTTPS--> Servidor SICOM-MUNI --> Base de datos PostgreSQL + archivos\n  solicitante, presupuesto, rpa ...               (a cargo del área de Sistemas)        (con respaldo diario)');
H2('Qué debe hacer la entidad');
TABLE(['#', 'Qué', 'Quién'], [
  ['1', 'Conseguir un servidor o máquina virtual (Ubuntu Server, 2 CPU, 4 GB RAM, 50 GB de disco como mínimo). Alternativa: servidor en la nube, previa aprobación legal.', 'Sistemas'],
  ['2', 'Instalar Docker en ese servidor (allí no hay el problema de virtualización de las PC con Windows) y poner el sistema con `docker compose`.', 'Sistemas'],
  ['3', 'Configurar **HTTPS** con un certificado, un nombre de dirección oficial y claves nuevas y largas. Cerrar el acceso directo a la base de datos.', 'Sistemas'],
  ['4', 'Cargar los datos reales: parámetros del GAM y logotipo, partidas presupuestarias de la gestión, catálogo CHB oficial y usuarios reales (y desactivar los usuarios de demostración).', 'Administrador del sistema'],
  ['5', 'Programar **respaldos diarios** de la base y de los PDF, guardarlos fuera del servidor y probar una restauración cada trimestre.', 'Sistemas'],
  ['6', '**Validar con la asesoría legal** los topes, plazos, mínimo de cotizaciones, formularios y márgenes de preferencia (se ajustan en el menú «Parámetros del GAM»). Confirmar también si los PDF con QR tienen validez por sí solos o si requieren firma.', 'Asesoría legal'],
  ['7', 'Aprobar el uso con una **resolución o instructivo interno** y designar responsable técnico y plan de soporte.', 'Autoridad / RPA'],
  ['8', '**Piloto en paralelo** de 1 a 2 meses (sistema y procedimiento actual) y **capacitación** de cada rol.', 'Contrataciones y Sistemas'],
  ['9', 'Revisión de seguridad independiente antes de operar con información real.', 'Sistemas / auditoría']], [500, 6760, 2100]);
NOTE('Todos los pasos técnicos (comandos, ejemplo de HTTPS, respaldos y lista de control) están en el archivo `docs/PUESTA_EN_PRODUCCION.md` del proyecto; entrégueselo a la persona de Sistemas.', 'E8F1FB', 'Documento técnico');
H2('Lo que el sistema todavía no hace');
B(['No se conecta al **SIGEP** ni al **SICOES**: el operador copia el bloque de captura y registra allí los números (C-31, F110, CUCE).', 'No incluye **firma digital**, doble verificación al ingresar ni recuperación de contraseña por correo (el administrador restablece las claves).', 'No ha pasado una **prueba de penetración** ni de **carga** realizada por terceros.', 'Las reglas legales **no fueron verificadas** contra la normativa vigente.']);

H1('Aviso importante');
B(['Esta es una **versión de demostración**: los nombres, empresas, códigos de partida y catálogo son ficticios.',
  'Los topes (Bs 50.000 y Bs 20.000), el plazo de 15 días, el mínimo de 3 cotizaciones y las referencias normativas fueron tomados del encargo y **no se han contrastado con la normativa vigente**. Antes de usarlo oficialmente, su asesoría legal debe validarlos (se pueden cambiar en el menú **Parámetros del GAM**, usuario `admin`).',
  'El sistema **no se conecta** al SIGEP ni al SICOES: ayuda a preparar la información para copiarla.',
  'Las instrucciones de instalación con Docker no pudieron ejecutarse de punta a punta en el entorno donde se desarrolló el sistema; si algún paso de la Parte 1 falla, envíe una captura de pantalla para corregirlo.']);
const doc = new Document({
  creator: 'SICOM-MUNI', title: 'Guía de prueba para principiantes — SICOM-MUNI',
  styles: { default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 34, bold: true, color: AZUL, font: 'Calibri' }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 27, bold: true, color: '2E75B6', font: 'Calibri' }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 24, bold: true, font: 'Calibri' }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } }] },
  numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    ...numRefs.map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] }))] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1200, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run('SICOM-MUNI — Guía de prueba para principiantes', { size: 18, color: '888888' })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Página ', { size: 18, color: '888888' }), new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '888888' })] })] }) },
    children: kids }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync('/home/user/Factura/sicom-muni/docs/GUIA_PRUEBA_PARA_PRINCIPIANTES.docx', b); console.log('ok', b.length); });
