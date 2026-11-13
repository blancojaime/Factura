const fs = require('fs');
const D = require('docx');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, ImageRun, AlignmentType, LevelFormat, PageBreak, TableOfContents, Footer, Header, PageNumber } = D;
const IMG = '' + __dirname + '/img/';
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

function portada(titulo, subtitulo, nota) {
  kids.push(new Paragraph({ spacing: { before: 2200 }, alignment: AlignmentType.CENTER, children: [run('SICOM-MUNI', { bold: true, size: 72, color: AZUL })] }));
  kids.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Sistema Integrado de Contratación Menor Municipal', { size: 28 })] }));
  kids.push(new Paragraph({ spacing: { before: 700 }, alignment: AlignmentType.CENTER, children: [run(titulo, { bold: true, size: 40 })] }));
  kids.push(new Paragraph({ spacing: { before: 200 }, alignment: AlignmentType.CENTER, children: [run(subtitulo, { size: 26, color: '555555' })] }));
  kids.push(new Paragraph({ spacing: { before: 1800 }, alignment: AlignmentType.CENTER, children: [run(nota, { size: 22, color: '555555' })] }));
}

// =================================================================== MANUAL DE INSTALACIÓN EN RED LOCAL
function manualInstalacion() {
  portada('MANUAL DE INSTALACIÓN EN RED LOCAL', 'Instalador para Windows — explicado paso a paso, sin conocimientos de informática', 'Una sola instalación en un equipo servidor; todos los demás entran con su navegador.');
  kids.push(new Paragraph({ children: [new PageBreak()] }));
  kids.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run('Contenido')] }));
  kids.push(new TableOfContents('Contenido', { hyperlink: true, headingStyleRange: '1-2' }));

  H1('1. ¿Cómo funciona? (explicación sencilla)');
  P('SICOM-MUNI se instala **una sola vez en una computadora llamada «servidor»**. Las demás computadoras de la oficina **no instalan nada**: abren su navegador (Chrome, Edge o Firefox), escriben una dirección y trabajan en el sistema, cada una con su propio usuario y contraseña.');
  CODE('   Computadora SERVIDOR (instalada una vez)\n   ┌──────────────────────────────────────┐\n   │  SICOM-MUNI + base de datos + PDF    │  ← aquí quedan todos los datos\n   └───────────────┬──────────────────────┘\n                   │  red de la oficina (cable o Wi-Fi)\n     ┌─────────────┼─────────────┬──────────────┐\n   Solicitante  Presupuesto  Contrataciones   RPA ...   ← solo usan el navegador');
  H2('1.1 Qué incluye el instalador');
  B(['**Todo en uno:** el sistema, la base de datos PostgreSQL, el generador de PDF con código QR y los servicios de Windows. No tiene que instalar nada más.',
    '**Los 6 roles:** Solicitante, Presupuesto, Contrataciones, RPA, Recepción y Administrador, con todas las funciones del sistema web (importación desde Excel, Certificación del POA, Nota PAC, cotizaciones, adjudicación, documentos con QR y verificación, auditoría).',
    '**Arranque automático:** al encender el servidor, el sistema se inicia solo (no hay que abrir ningún programa).',
    '**Respaldo diario automático** de la base de datos y de los documentos.',
    '**Licencia por equipo** con 30 días de prueba (ver capítulo 7).']);
  H2('1.2 Qué NO hace');
  B(['No funciona «en internet»: está pensado para la **red local** de su oficina. Las personas fuera de la red no pueden entrar.', 'No se conecta al SIGEP ni al SICOES: prepara la información para copiarla.', 'Si el servidor está apagado, nadie puede entrar. Por eso conviene una computadora que quede encendida en horario de trabajo.']);

  H1('2. Antes de empezar: lista de verificación');
  TABLE(['Qué necesita', 'Detalle', '✔'], [
    ['Computadora SERVIDOR', 'Windows 10 u 11 de 64 bits · 8 GB de memoria RAM (mínimo 4 GB) · 20 GB libres en el disco C: · encendida en horario de trabajo (ideal: con UPS)', '☐'],
    ['Permisos de administrador', 'Usted (o el técnico) debe poder aceptar el mensaje «¿Desea permitir que esta aplicación haga cambios?»', '☐'],
    ['Red local', 'El servidor y las demás computadoras conectados al mismo router (por cable o Wi-Fi)', '☐'],
    ['El instalador', 'El archivo ZIP «SICOM-MUNI-Instalador-Windows» (ver capítulo 3)', '☐'],
    ['Datos de su entidad', 'Nombre exacto del Gobierno Autónomo Municipal y la ciudad', '☐'],
    ['Contraseña del administrador', 'Invéntela con antelación: mínimo 10 caracteres, con mayúsculas, minúsculas y números. Ejemplo de forma: «MiAlcaldia#2026»', '☐'],
    ['Persona de apoyo (opcional)', 'Alguien de Sistemas para la dirección fija de red (capítulo 8)', '☐']], [2500, 6200, 660]);
  NOTE('Elija como servidor una computadora **estable**: no la de alguien que la apaga al salir, ni una portátil que viaja. Si el servidor se apaga, el sistema se detiene hasta que vuelva a encenderse (se reinicia solo).', 'FFF4CE', 'Consejo');

  H1('3. Obtener el instalador');
  N(['En una computadora con internet abra el navegador y entre a `https://github.com/blancojaime/Factura/releases`.',
    'Busque la versión más reciente llamada **«SICOM-MUNI instalador para Windows»**.',
    'En la sección **Assets** (archivos) descargue **SICOM-MUNI-Instalador-Windows-X.Y.Z.zip** (el número puede variar). *Es un solo archivo comprimido.*'.replace(/\*/g, ''),
    'Copie el ZIP al servidor (con un pendrive, por red o descargándolo directamente allí).',
    'En el servidor, haga **clic derecho sobre el ZIP → Extraer todo… → Extraer**. Se crea una carpeta con el instalador, el manual y un archivo «LEEME».']);
  NOTE('El otro ZIP de la página («Emisor de Licencias») es una herramienta **del proveedor**: **no** se instala en las oficinas de los clientes.', 'FDE9E7', 'Atención');

  H1('4. Instalar en el servidor (paso a paso)');
  P('Todo el proceso tarda entre **5 y 15 minutos**. Siga las pantallas en este orden:');
  PASO(1, 'servidor', 'Abrir el instalador', ['Entre a la carpeta extraída y haga **doble clic** en `SICOM-MUNI-Instalador-X.Y.Z.exe`.',
    'Windows preguntará «¿Desea permitir que esta aplicación haga cambios en su dispositivo?»: pulse **Sí**.',
    'Si aparece una pantalla azul **«Windows protegió su PC»**: pulse **Más información** y luego **Ejecutar de todas formas** (el instalador es nuevo y aún no tiene firma digital de Microsoft).']);
  PASO(2, 'servidor', 'Pantallas del asistente', ['El asistente está en español. En cada pantalla complete lo indicado y pulse **Siguiente**:']);
  TABLE(['Pantalla', 'Qué hacer'], [
    ['Bienvenida', 'Pulse **Siguiente**.'],
    ['Carpeta de destino', 'Deje la carpeta que propone (`C:\\Program Files\\SICOM-MUNI`) y pulse **Siguiente**.'],
    ['Datos de la entidad', 'Escriba el **nombre del Gobierno Autónomo Municipal** (aparecerá en el membrete de los documentos) y la **ciudad**.'],
    ['Administrador del sistema', 'Escriba el **usuario** (por ejemplo `admin`) y la **contraseña** dos veces. Si no cumple las reglas (10 caracteres, mayúsculas, minúsculas y números) el asistente se lo indica.'],
    ['Red local', 'Deje el **puerto 8080** (solo cámbielo si el técnico se lo indica).'],
    ['Datos de demostración', '**No marque** la casilla si va a trabajar con datos reales. Márquela solo para pruebas o capacitación (instala usuarios y datos de ejemplo).'],
    ['Licencia (opcional)', 'Si ya recibió el archivo **.sicomlic**, selecciónelo. Si no, déjelo vacío: tendrá **30 días de prueba** y podrá activar después.'],
    ['Listo para instalar', 'Pulse **Instalar**.']], [2400, 6960]);
  PASO(3, 'servidor', 'Esperar', ['Verá una barra de avance y luego el mensaje «Configurando la base de datos, los servicios y el firewall…». **No apague ni cierre**: puede tardar unos minutos. Si Windows pregunta por el Firewall o por instalar Visual C++, acepte.']);
  PASO(4, 'servidor', 'Pantalla final: ¡anote las direcciones!', ['Al terminar se muestra un resumen similar a este (con los datos de su equipo):']);
  CODE('SICOM-MUNI quedó instalado y funcionando.\n\nDireccion para los usuarios de la red:  http://192.168.1.50:8080/\nTambien:  http://SERVIDOR-PC:8080/\nEn este equipo:  http://localhost:8080/\nID del equipo (para solicitar la licencia):  03BB-1C9D-F36A-6F68\nEstado de la licencia:  Modo de prueba: quedan 30 dia(s)...');
  P('**Anote la «Dirección para los usuarios de la red»**: es la que usarán todos. También puede volver a verla en cualquier momento: **Menú Inicio → SICOM-MUNI → Estado del sistema**.');
  H2('4.1 Qué se instaló en el servidor');
  TABLE(['Elemento', 'Para qué sirve'], [
    ['Servicio «SICOM-MUNI-BD»', 'La base de datos (PostgreSQL). Solo atiende dentro del propio servidor: no está expuesta a la red.'],
    ['Servicio «SICOM-MUNI»', 'El sistema web. Arranca solo con Windows y se reinicia solo si falla.'],
    ['Regla de Firewall', 'Permite entrar al puerto del sistema **solo desde la red local**.'],
    ['Tarea «SICOM-MUNI Respaldo diario»', 'Cada día a las 02:00 guarda un respaldo (capítulo 10).'],
    ['Menú Inicio → SICOM-MUNI', 'Abrir el sistema, activar la licencia, ver el estado, respaldar, restaurar, cambiar la dirección de red, restablecer una contraseña, reiniciar, manual y desinstalar.'],
    ['Icono «SICOM-MUNI» en el Escritorio', 'Abre el sistema en este equipo.']], [3200, 6160]);

  H1('5. Primer ingreso y configuración inicial');
  PASO(1, 'servidor', 'Entrar con el administrador', ['En el servidor abra el icono **SICOM-MUNI** del Escritorio (o escriba `http://localhost:8080/` en el navegador). Ingrese con el usuario y la contraseña que eligió durante la instalación.']);
  IMGF('inst-web-login-prueba.png', 'Pantalla de ingreso: durante la prueba muestra los días restantes y el enlace para activar la licencia', 5.6, 4.6);
  PASO(2, 'administrador', 'Completar los datos de la entidad', ['Menú **Parámetros del GAM**: revise el nombre y la ciudad, complete **DA** y **UE**, y registre el **nombre y cargo de la Máxima Autoridad Ejecutiva** (`mae_nombre`, `mae_cargo`): se usan en la nota de solicitud de registro al PAC. Pulse **Guardar** en cada fila.']);
  IMGF('inst-web-parametros.png', 'Parámetros del GAM', 5.4, 6);
  PASO(3, 'administrador', 'Crear los usuarios de cada persona', ['Menú **Usuarios → Nuevo usuario**. Cree **una cuenta por persona** (nunca compartan cuentas) y elija su rol:']);
  TABLE(['Rol', 'Quién suele ser', 'Qué puede hacer'], [
    ['Solicitante', 'Jefes de unidad que piden bienes o servicios', 'Crear y enviar solicitudes (C-1), justificar el apoyo al POA'],
    ['Presupuesto', 'Responsable de presupuesto', 'Importar presupuesto y objetivos POA, certificar (C-31 y POA), devengar'],
    ['Contrataciones', 'Encargado de compras menores', 'Importar catálogo CHB, Formulario 110, cotizaciones, apertura, evaluación'],
    ['RPA', 'Responsable del proceso de contratación', 'Aprobar el inicio, adjudicar, formalizar'],
    ['Recepción', 'Almacenes / comisión de recepción', 'Registrar la recepción y conformidad'],
    ['Administrador', 'Sistemas / administrador', 'Usuarios, parámetros, catálogo, licencia y auditoría']], [1800, 3300, 4260]);
  IMGF('inst-web-nuevo-usuario.png', 'Creación de un usuario', 5.2, 5);
  PASO(4, 'presupuesto / contrataciones', 'Cargar sus datos reales', ['Con las plantillas de Excel que ofrece cada pantalla: **Presupuesto → Importar desde Excel** (aperturas programáticas), **Objetivos POA → Importar** y **Catálogo CHB → Importar**. El detalle está en el Manual de Usuario.', 'Una vez cargado el presupuesto, cada **solicitante elige directamente del presupuesto de la institución**: al agregar un ítem selecciona la **apertura programática** (programa, proyecto y actividad), la **fuente / organismo** y la **partida de gasto**, y el sistema le muestra el presupuesto, lo ejecutado y el saldo disponible.']);
  IMGF('46-seleccion-apertura.png', 'El solicitante elige la apertura programática, fuente, organismo y partida del presupuesto', 5.4, 5.0);
  NOTE('Si instaló los **datos de demostración** (solo para pruebas), los usuarios de ejemplo tienen todos la misma contraseña conocida (`Sicom#2026Demo`): **no los use con datos reales**; para pasar a producción reinstale sin esa opción o desactívelos.', 'FDE9E7', 'Atención');

  H1('6. Conectar las demás computadoras (no se instala nada)');
  N(['En la computadora del usuario abra **Chrome, Edge o Firefox**.', 'En la barra de direcciones escriba la **dirección de red** que anotó, por ejemplo `http://192.168.1.50:8080/` y pulse Enter.', 'Verá la pantalla de ingreso de SICOM-MUNI. Ingrese con su **usuario personal**.', 'Para no volver a escribir la dirección: en **Chrome** → menú ⋮ → **Guardar y compartir → Crear acceso directo**; en **Edge** → menú … → **Aplicaciones → Instalar este sitio como aplicación**. Quedará un icono en el Escritorio.']);
  NOTE('Escribir **http://** (no https) y los dos puntos con el puerto (**:8080**) es obligatorio. Con el celular conectado al **mismo Wi-Fi** también puede entrar.', 'E8F1FB', 'Importante');
  H2('6.1 El código QR de los documentos');
  P('Cada PDF lleva un **código QR** que apunta a la página de verificación en **la dirección del servidor**. Para escanearlo, el celular debe estar **conectado a la misma red Wi-Fi** de la oficina. Por eso:');
  B(['La dirección del servidor debe ser **fija** (capítulo 8). Si cambia, los QR de los documentos antiguos dejan de abrir.', 'Si cambia la dirección, use **Menú Inicio → SICOM-MUNI → Cambiar la dirección o el puerto de red**: los documentos nuevos usarán la dirección actual.', 'Para verificar sin escanear: abra el PDF, copie el código del documento y escriba `http://DIRECCIÓN:8080/verificar/CÓDIGO`.']);

  H1('7. Licencia: prueba de 30 días y activación');
  P('Al instalar, el sistema funciona **30 días de prueba** con todas sus funciones. Después se necesita una **licencia**, que se solicita al proveedor y está ligada **a ese servidor** (no se puede copiar a otro equipo).');
  H2('7.1 Cómo activar la licencia');
  N(['En el servidor abra **Menú Inicio → SICOM-MUNI → Activar la licencia** (o, en el navegador, `http://localhost:8080/activacion/`).',
    'Verá el **ID de este equipo** (ejemplo `03BB-1C9D-F36A-6F68`). Pulse **Copiar** y **envíelo al proveedor** (por WhatsApp o correo) junto con el nombre de la entidad.',
    'El proveedor le devolverá **un archivo `.sicomlic`** o una **clave** que empieza con `SICOM1-`.',
    'En la misma pantalla pulse **Choose File / Elegir archivo** y seleccione el `.sicomlic` (o pegue la clave en el cuadro) y pulse **Activar licencia**.',
    'Aparece «Licencia activada». Desde ese momento el sistema sigue funcionando sin límite de prueba.']);
  IMGF('inst-web-activacion.png', 'Pantalla de activación: ID del equipo, estado y cuadro para la licencia', 5.4, 6);
  IMGF('inst-web-activacion-ok.png', 'Licencia activada: muestra entidad, vencimiento y usuarios permitidos', 5.4, 6);
  H2('7.2 Cosas que debe saber');
  TABLE(['Situación', 'Qué ocurre / qué hacer'], [
    ['Termina la prueba o vence la licencia', 'Nadie puede ingresar y se muestra la pantalla de activación. Sus datos **no se pierden**: al activar una licencia vuelve todo.'],
    ['La licencia tiene límite de usuarios', 'No se pueden crear o reactivar más usuarios que el máximo (el sistema lo avisa).'],
    ['Cambia la computadora, o reinstala Windows', 'El ID del equipo cambia: pida una licencia nueva con el ID nuevo.'],
    ['Ver el estado en cualquier momento', 'Inicie sesión como administrador → menú **Licencia**.']], [3200, 6160]);

  H1('8. Dirección fija para el servidor (muy recomendado)');
  P('Los routers suelen cambiar la dirección de las computadoras cada cierto tiempo. Si la del servidor cambia, **los demás dejan de entrar** y los QR antiguos no abren. Hay dos formas de evitarlo; elija una (o pida ayuda a quien administra su red):');
  H2('Opción A: reservar la dirección en el router (la mejor)');
  P('Un técnico entra a la configuración del router, busca «Reserva de DHCP» (o «DHCP estático» / «Asignación de IP») y asocia la dirección actual al servidor.');
  H2('Opción B: fijar la dirección en Windows (en el servidor)');
  N(['Anote primero la dirección actual del servidor y la del router (puerta de enlace). Ejemplo: servidor `192.168.1.50`, router `192.168.1.1`.', '**Configuración → Red e Internet → Ethernet** (o **Wi-Fi → su red**) → **Propiedades del hardware** → en «Asignación de IP» pulse **Editar**.',
    'Elija **Manual**, active **IPv4** y complete: Dirección IP `192.168.1.50` · Longitud del prefijo de subred `24` · Puerta de enlace `192.168.1.1` · DNS preferido `8.8.8.8`.', 'Pulse **Guardar**. Pruebe que sigue entrando a internet y al sistema.', 'Ejecute **Menú Inicio → SICOM-MUNI → Cambiar la dirección o el puerto de red** y pulse Enter en las dos preguntas para registrar la dirección actual.']);
  NOTE('Use una dirección **fuera del rango que reparte el router** o pida el dato al técnico, para no repetirla en otra computadora.', 'FFF4CE', 'Cuidado');

  H1('9. Seguridad: qué hacer y qué no');
  B(['**Cada persona su usuario y su contraseña.** Cambie la del administrador si alguien más la conoció.', 'El sistema solo se abre a la **red local** (el firewall lo restringe). **No** lo publique en internet ni abra puertos en el router hacia el servidor.', 'Mantenga **Windows actualizado** y un antivirus. Si el antivirus bloquea el puerto 8080, permítalo para «SICOM-MUNI».', 'La base de datos solo es accesible desde el propio servidor y con clave generada automáticamente (guardada en `C:\\ProgramData\\SICOM-MUNI\\config`, solo para administradores).', 'Las acciones quedan en la **Auditoría inalterable** (menú Auditoría): revíselo periódicamente con «Verificar integridad».', 'La conexión dentro de la red es **http** (sin cifrado). Para un uso de mayor exigencia, pida a Sistemas poner el servidor detrás de un certificado HTTPS.']);

  H1('10. Respaldos: cómo cuidar su información');
  H2('10.1 Respaldo automático');
  P('Cada día a las **02:00** el sistema guarda: (1) la **base de datos** (archivo `sicom_AAAAMMDD_HHMM.dump`) y (2) los **documentos PDF** (`archivos_AAAAMMDD_HHMM.zip`) en `C:\\ProgramData\\SICOM-MUNI\\respaldos`. Se conservan los **últimos 14**. **El servidor debe estar encendido a esa hora**; si no lo está, haga el respaldo manual.');
  H2('10.2 Respaldo manual (antes de actualizar, o cuando quiera)');
  P('**Menú Inicio → SICOM-MUNI → Respaldar ahora** (acepte el permiso de administrador). Al terminar muestra la carpeta donde quedó.');
  H2('10.3 Copia fuera del servidor (muy importante)');
  P('Si el disco del servidor falla, se pierde todo. Copie periódicamente la carpeta `respaldos` a un **pendrive o disco externo**. Para que el sistema lo haga solo cada día, cree el archivo de texto `C:\\ProgramData\\SICOM-MUNI\\config\\respaldo_destino.txt` y escriba en una línea la unidad o carpeta, por ejemplo `E:\\` (disco externo conectado al servidor).');
  H2('10.4 Restaurar un respaldo');
  N(['**Menú Inicio → SICOM-MUNI → Restaurar un respaldo** (acepte el permiso de administrador).', 'Verá la lista de respaldos con su fecha. Escriba el **número** del que desea y pulse Enter.', 'Escriba **SI** para confirmar. ATENCIÓN: **reemplaza todos los datos actuales** por los del respaldo.', 'Al terminar, el sistema se reinicia solo. Compruebe entrando con el administrador.']);
  NOTE('Haga una **prueba de restauración cada 3 meses** en otra computadora: un respaldo que nunca se probó no es una garantía.', 'E8F1FB', 'Recomendación');

  H1('11. Uso diario y mantenimiento');
  TABLE(['Tarea', 'Cómo'], [
    ['Encender el sistema', 'Solo encienda el servidor: el sistema arranca solo (espere 1 o 2 minutos).'],
    ['Apagar el servidor', 'Apáguelo normalmente desde Windows (Inicio → Apagar). Evite cortar la luz: use un UPS.'],
    ['Ver si está funcionando', '**Menú Inicio → SICOM-MUNI → Estado del sistema**: muestra los servicios, la dirección, la licencia y el último respaldo.'],
    ['Ver la ejecución del presupuesto', 'Menú **Presupuesto**: presupuesto, ejecutado, % de ejecución, preventivo y saldo por apertura y partida, con el **TOTAL** al pie. Al registrar el devengado de un trámite, su tarjeta muestra el total de ejecución cargado.'],
    ['Reiniciar el sistema', '**Menú Inicio → SICOM-MUNI → Reiniciar el servicio**.'],
    ['Cambiar dirección o puerto', '**Menú Inicio → SICOM-MUNI → Cambiar la dirección o el puerto de red**.'],
    ['Olvidé la contraseña', '**Menú Inicio → SICOM-MUNI → Restablecer la contraseña de un usuario** (en el servidor, con permiso de administrador).'],
    ['Actualizar a una versión nueva', 'Haga un respaldo y luego ejecute el instalador nuevo **sobre el existente** (no desinstale): conserva todos los datos y la licencia.'],
    ['Cambiar de servidor', 'Respalde; instale en la computadora nueva; copie los archivos de `respaldos` a la nueva; use «Restaurar un respaldo»; solicite una licencia nueva con el nuevo ID.']], [3000, 6360]);

  H1('12. Desinstalar');
  P('**Configuración → Aplicaciones → SICOM-MUNI → Desinstalar** (o Menú Inicio → SICOM-MUNI → Desinstalar). El asistente pregunta si desea **conservar los datos**:');
  B(['**Sí (recomendado):** se quitan los programas y servicios, pero la base de datos, los documentos y los respaldos quedan en `C:\\ProgramData\\SICOM-MUNI`; podrá reinstalar y seguir trabajando.', '**No:** se **eliminan definitivamente** todos los datos. Haga antes un respaldo y cópielo fuera del servidor.']);

  H1('13. Solución de problemas');
  TABLE(['Qué ve', 'Causa probable', 'Qué hacer'], [
    ['Al instalar aparece «La configuración no terminó correctamente (código 1)»', 'El aviso indica el **Motivo** en la segunda línea. Causas frecuentes: otro programa usa el puerto 8080; un antivirus bloquea la instalación; Windows está instalando actualizaciones; falta espacio en disco', 'Lea el **Motivo**. Si dice que el puerto está en uso, vuelva a ejecutar el instalador y elija otro puerto (8181). Si Windows está actualizando, espere a que termine y reintente. Desactive el antivirus durante la instalación. Si el problema sigue, envíe a soporte el archivo `C:\\ProgramData\\SICOM-MUNI\\logs\\instalacion.log`. Reintentar es seguro: el instalador limpia los restos de un intento incompleto.'],
    ['La base de datos no arranca tras actualizar o reinstalar (el registro de PostgreSQL dice «PANIC … Permission denied»)', 'Permisos de la carpeta de datos dañados por una versión anterior del instalador (2.1.0 y 2.1.1)', 'Instale la **versión 2.1.2 o posterior encima** de la instalada (no hace falta desinstalar): el instalador repara los permisos. Si aun así no arranca, desinstale marcando **conservar datos**, reinicie la computadora e instale de nuevo.'],
    ['Otra computadora no abre la página («No se puede acceder a este sitio»)', 'Dirección o puerto equivocados; servidor apagado; antivirus; otra red/Wi-Fi', 'Confirme la dirección en «Estado del sistema». Escriba **http://** y el **:8080**. Verifique que ambas estén en la **misma red**. Pruebe desde el propio servidor con `http://localhost:8080/`.'],
    ['Funciona en el servidor pero no en las demás', 'Firewall/antivirus de otro fabricante', 'Permita el puerto **8080** (o el que eligió) en el antivirus. El instalador ya creó la regla de Windows.'],
    ['Antes funcionaba y dejó de funcionar tras un tiempo', 'La dirección del servidor cambió', 'Vea la nueva en «Estado del sistema», ejecute «Cambiar la dirección…» y haga la **dirección fija** (capítulo 8).'],
    ['Pantalla «Activación de la licencia»', 'Terminó la prueba o venció la licencia', 'Siga el capítulo 7: envíe el ID del equipo y active la licencia recibida.'],
    ['«El sistema no respondió» al terminar de instalar', 'Un servicio no inició', 'Abra «Estado del sistema». Reinicie el servicio. Si persiste, envíe a soporte el archivo `C:\\ProgramData\\SICOM-MUNI\\logs\\instalacion.log` y la carpeta `logs`.'],
    ['Olvidé la contraseña del administrador', '—', '**Menú Inicio → SICOM-MUNI → Restablecer la contraseña de un usuario**.'],
    ['El respaldo no se creó', 'Servidor apagado a las 02:00 o disco lleno', 'Haga **Respaldar ahora**, libere espacio en el disco C: y revise `logs\\respaldo.log`.'],
    ['Los PDF se ven sin tildes o sin letra', 'Faltan fuentes', 'Reinicie el servicio. Si persiste, informe a soporte con una captura.'],
    ['El QR del celular no abre', 'El celular no está en el Wi-Fi de la oficina o la dirección cambió', 'Conecte el celular al Wi-Fi de la oficina; verifique la dirección fija (capítulo 8).'],
    ['El instalador dice que el puerto está ocupado', 'Otro programa usa el 8080', 'Reinstale eligiendo otro puerto (por ejemplo 8181) o use «Cambiar la dirección o el puerto».']], [3000, 2800, 3560]);

  H1('14. Información técnica (para el personal de Sistemas)');
  TABLE(['Elemento', 'Valor'], [
    ['Programas', '`C:\\Program Files\\SICOM-MUNI` (python, site-packages, backend, web, pgsql, gtk, fonts, herramientas)'],
    ['Datos', '`C:\\ProgramData\\SICOM-MUNI` → `pgdata` (base), `archivos` (PDF), `respaldos`, `logs`, `config`, `cache`'],
    ['Servicios', '`SICOM-MUNI-BD` (PostgreSQL 16, 127.0.0.1:54329) y `SICOM-MUNI` (servidor web, 0.0.0.0:8080). Cuenta: NT AUTHORITY\\NetworkService'],
    ['Configuración', '`C:\\ProgramData\\SICOM-MUNI\\config\\.env` (URL de la base, clave de firmas, puerto, URL pública para los QR) y `secretos.json`: permisos solo para SYSTEM/Administradores'],
    ['Firewall', 'Regla de entrada TCP al puerto del sistema, solo `LocalSubnet`'],
    ['Respaldos', 'Tarea programada diaria 02:00 (SYSTEM): `pg_dump -Fc` + ZIP de `archivos`; retención 14; copia extra opcional (`respaldo_destino.txt`)'],
    ['Registros', '`logs\\instalacion.log`, `respaldo.log`, `herramientas.log`, registros del servicio y `pgdata\\log`'],
    ['Instalación silenciosa', '`SICOM-MUNI-Instalador-X.exe /VERYSILENT /SUPPRESSMSGBOXES /ENTIDAD="GAM X" /CIUDAD="Ciudad" /ADMIN=admin /CLAVE="Clave#Segura2026" /PUERTO=8080 /DEMO=NO /LICENCIA="C:\\lic.sicomlic"`'],
    ['Desinstalación silenciosa', '`unins000.exe /VERYSILENT /ELIMINARDATOS=0|1`'],
    ['Comandos útiles', '`Get-Service SICOM*` · `Restart-Service SICOM-MUNI` · `python\\python.exe -m app.cli licencia` (desde `config`, con el entorno de `herramientas\\comun.ps1`)']], [2600, 6760]);

  H1('15. Preguntas frecuentes');
  TABLE(['Pregunta', 'Respuesta'], [
    ['¿Necesito internet para usarlo?', 'No. Solo para descargar el instalador. El sistema funciona dentro de la red local.'],
    ['¿Cuántas personas pueden usarlo a la vez?', 'Decenas, en una computadora normal. El límite de usuarios lo define la licencia.'],
    ['¿Puedo instalarlo en una portátil?', 'Sí, pero mientras esté apagada o fuera de la red nadie podrá entrar. Es mejor un equipo fijo.'],
    ['¿Los datos están seguros si se apaga la luz?', 'La base de datos está protegida contra cortes, pero use un UPS y haga respaldos externos.'],
    ['¿Puedo instalarlo en varias entidades?', 'Sí, una instalación por servidor; cada servidor necesita su propia licencia.'],
    ['¿Qué pasa si no activo la licencia?', 'Después de 30 días el sistema pide activarla; sus datos se conservan.'],
    ['¿Cómo cambio el nombre del GAM o el logotipo?', 'Menú Parámetros del GAM (administrador).']], [3600, 5760]);

  H1('Anexo A. Hoja de datos de esta instalación (para completar a mano)');
  TABLE(['Dato', 'Anote aquí'], [
    ['Fecha de instalación', ''], ['Nombre de la computadora servidor', ''], ['Dirección para los usuarios (http://…)', ''], ['Puerto', ''],
    ['Usuario del administrador', ''], ['Contraseña del administrador (guárdela en sobre cerrado)', ''], ['ID del equipo (para la licencia)', ''],
    ['Licencia: fecha de activación / vencimiento', ''], ['Persona responsable del servidor', ''], ['Dónde se guardan las copias de los respaldos', '']], [4600, 4760]);
  H1('Anexo B. Lista de verificación al terminar la instalación');
  TABLE(['#', 'Comprobación', '✔'], [
    ['1', 'La pantalla final mostró las direcciones y el ID del equipo', '☐'], ['2', 'Desde el servidor abre `http://localhost:8080/` e ingresa con el administrador', '☐'],
    ['3', 'Desde OTRA computadora abre la dirección de red e ingresa', '☐'], ['4', 'Se crearon los usuarios de cada rol', '☐'], ['5', 'Se registró la Máxima Autoridad Ejecutiva en Parámetros', '☐'],
    ['6', 'Se importaron presupuesto, objetivos POA y catálogo CHB', '☐'], ['7', 'Se generó un documento de prueba y su QR abre desde el celular (en el Wi-Fi)', '☐'],
    ['8', 'Se hizo un respaldo manual y se copió fuera del servidor', '☐'], ['9', 'Se fijó la dirección del servidor (capítulo 8)', '☐'], ['10', 'Se solicitó/activó la licencia', '☐']], [500, 8200, 660]);
}

// =================================================================== MANUAL DEL EMISOR DE LICENCIAS
function manualEmisor() {
  portada('MANUAL DEL EMISOR DE LICENCIAS', 'Herramienta externa del proveedor — solo para quien emite las licencias', 'No distribuya este manual ni la herramienta a los clientes.');
  H1('1. ¿Qué es y cómo funciona?');
  P('El **Emisor de Licencias** es una aplicación **externa e independiente** de SICOM-MUNI. Sirve para generar las licencias que activan el sistema en cada servidor. **No se instala en las computadoras de los clientes.**');
  TABLE(['Pieza', 'Dónde está', 'Qué hace'], [
    ['**Llave privada** (`llave_privada_SICOM.pem`)', 'Solo con el proveedor (guardada en un lugar seguro)', 'Firma las licencias. **Quien la tenga puede emitir licencias.**'],
    ['**Llave pública** (`llave_publica_SICOM.pem`)', 'Dentro del instalador (ya incluida)', 'Verifica que la licencia es auténtica. No sirve para crear licencias.'],
    ['**ID del equipo**', 'Lo muestra el servidor del cliente (pantalla de activación)', 'Liga la licencia a esa computadora.'],
    ['**Licencia** (`.sicomlic` o clave `SICOM1-…`)', 'La genera el emisor y se entrega al cliente', 'Contiene: entidad, equipo, vencimiento, máximo de usuarios, observaciones y la firma.']], [2800, 2900, 3660]);
  IMGF('inst-emisor-gui.png', 'Pantalla del Emisor de Licencias', 4.8, 5.5);
  H1('2. Primer uso: la llave privada');
  P('Junto con el sistema se le entregó **una llave privada** (`llave_privada_SICOM.pem`) cuya llave pública ya está dentro del instalador. Para empezar:');
  N(['Copie `SICOM-Emisor-de-Licencias.exe` a su computadora de trabajo (no a las de los clientes).', 'Ábralo (doble clic). Si Windows muestra «Windows protegió su PC», pulse **Más información → Ejecutar de todas formas**.', 'En el bloque **1. Llave privada** pulse **Abrir…** y seleccione `llave_privada_SICOM.pem`. El programa recuerda la ubicación.']);
  NOTE('**Respalde la llave privada** en al menos dos lugares seguros (por ejemplo un pendrive guardado bajo llave). **Si se pierde**, no se pueden emitir más licencias para los instaladores actuales: habría que generar llaves nuevas y recompilar el instalador (ver capítulo 6). **Nunca** la suba a GitHub ni la envíe por correo a los clientes.', 'FDE9E7', 'Crítico');
  H1('3. Emitir una licencia (paso a paso)');
  N(['El cliente le envía el **ID del equipo** (ejemplo `03BB-1C9D-F36A-6F68`) y el nombre de su entidad.', 'En el bloque **2. Datos de la licencia** escriba: **Entidad / cliente**, **ID del equipo** (o marque «Cualquier equipo (*)» si la licencia no debe ligarse a una computadora), **Vence** (fecha AAAA-MM-DD, o marque «Sin vencimiento») y **Máx. usuarios** (0 = sin límite). En Observaciones puede anotar el contrato o la factura.',
    'Pulse **Emitir licencia**, elija dónde guardar el archivo `.sicomlic` y pulse Guardar.', 'Abajo aparece también la **clave de activación** (una línea que empieza con `SICOM1-`): pulse **Copiar clave** si prefiere enviarla por mensaje.', 'Envíe al cliente el archivo **o** la clave. Él los carga en la pantalla de activación de su servidor.']);
  P('Cada licencia emitida queda anotada en un **registro** (`registro_licencias.csv`, en la carpeta del programa del usuario: botón «Abrir carpeta del registro»), con número, entidad, equipo, fechas y usuarios. Consérvelo como control de sus clientes.');
  H1('4. Verificar una licencia');
  P('Botón **Verificar una licencia…** → elija el archivo. Muestra si la firma es auténtica y sus datos. Sirve para revisar licencias antiguas o resolver reclamos.');
  H1('5. Casos frecuentes');
  TABLE(['Caso', 'Qué hacer'], [
    ['Renovación', 'Emita una licencia nueva con el **mismo ID de equipo** y la nueva fecha; el cliente la activa encima de la anterior.'],
    ['El cliente cambió de computadora o reinstaló Windows', 'Su ID cambió: pida el ID nuevo y emita otra licencia.'],
    ['Aumentar usuarios', 'Emita una licencia nueva con el máximo mayor.'],
    ['Licencia por sede sin ligar a una computadora', 'Marque «Cualquier equipo (*)» (menos control: puede usarse en varios equipos).'],
    ['El cliente dice «licencia no auténtica»', 'Casi siempre se copió mal la clave. Envíe el archivo `.sicomlic` en vez de la clave, o pídale que copie la clave completa.'],
    ['«La licencia fue emitida para otro equipo»', 'El ID enviado no era el del servidor. Pídale el ID desde la pantalla de activación del **servidor**.']], [3600, 5760]);
  H1('6. Uso avanzado');
  H2('6.1 Línea de comandos');
  CODE('SICOM-Emisor-de-Licencias.exe  (sin argumentos = ventana)\n\npython emisor.py emitir --llave llave_privada_SICOM.pem --entidad "GAM de La Paz" \\\n       --equipo 03BB-1C9D-F36A-6F68 --vence 2027-12-31 --max-usuarios 30 --salida licencia.sicomlic\npython emisor.py verificar --llave llave_privada_SICOM.pem licencia.sicomlic\npython emisor.py llaves --salida C:\\Llaves');
  H2('6.2 Generar llaves nuevas (si perdió la privada o quiere cambiarla)');
  N(['En el emisor pulse **Crear llaves nuevas…** y elija una carpeta: se crean `llave_privada_SICOM.pem` y `llave_publica_SICOM.pem`.', 'Reemplace el archivo `sicom-muni/backend/app/licencia_publica.pem` del repositorio por la llave pública nueva.', 'En GitHub ejecute de nuevo el flujo «Instalador Windows (SICOM-MUNI)» para compilar un instalador con la llave nueva.', 'Los clientes con licencias antiguas deberán actualizar al instalador nuevo y recibir una licencia firmada con la llave nueva.']);
  H1('7. Seguridad y límites de la protección');
  B(['La firma **Ed25519** impide fabricar o modificar licencias sin la llave privada.', 'La licencia ligada al ID del equipo impide usarla en otra computadora.', 'Es una protección **razonable para uso comercial**, no un sistema anticopia absoluto: un técnico con acceso total al servidor podría intentar saltar controles. Complemente con el contrato de licencia.', 'No hay verificación en línea: la licencia funciona sin internet.']);
}
function construir(titulo, salida) {
const doc = new Document({
  creator: 'SICOM-MUNI', title: titulo,
  styles: { default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 34, bold: true, color: AZUL, font: 'Calibri' }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 27, bold: true, color: '2E75B6', font: 'Calibri' }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 24, bold: true, font: 'Calibri' }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } }] },
  numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    ...numRefs.map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] }))] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1200, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run('SICOM-MUNI — ' + titulo, { size: 18, color: '888888' })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run('Página ', { size: 18, color: '888888' }), new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '888888' })] })] }) },
    children: kids }],
});
return Packer.toBuffer(doc).then((b) => { fs.writeFileSync(salida, b); console.log('ok', salida, b.length); });
}

const OUT='' + __dirname + '/';
manualInstalacion();
construir('Manual de instalación en red local', OUT+'MANUAL_INSTALACION_RED_LOCAL.docx').then(() => {
  kids.length = 0; numRefs.length = 0;
  manualEmisor();
  return construir('Manual del Emisor de Licencias', OUT+'MANUAL_EMISOR_LICENCIAS.docx');
});
