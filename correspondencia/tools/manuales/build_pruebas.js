const L = require('./lib.js'); const { h1, h2, p, ul, ol, note, img, table } = L;
h1('1. Objetivo y alcance');
p('Este documento es el **plan y registro de pruebas** de la versión 1.2 del Sistema de Correspondencia. Sirve para comprobar, caso por caso, que el sistema hace lo esperado, y para dejar constancia firmada de la aceptación. Está escrito para que lo ejecute una persona sin formación técnica.');
h2('1.1 Qué se prueba');
ul(['Las **cinco novedades de la v1.2**: documentos por colores, nombre y cargo arriba a la derecha, Ventanilla en colores, sello QR con escudo y consulta con código de control.', 'La **regresión**: lo que ya funcionaba (ingreso, crear, derivar, recepcionar, responder, archivar, agrupar, hoja de ruta, reportes).', 'La **seguridad y permisos** más importantes.']);
h2('1.2 Qué NO se probó aún');
note('warn', 'Los instaladores **INSTALAR.bat / ACTUALIZAR.bat** no pudieron ejecutarse en Windows durante el desarrollo; los casos de instalación (grupo I) están pensados para que usted los ejecute y reporte. Las impresiones físicas (papel real) también deben verificarlas ustedes: aquí se verificó el PDF generado.');
h2('1.3 Verificaciones ya realizadas por el equipo de desarrollo');
table(['Verificación', 'Resultado'], [['Pruebas automáticas de negocio (tests/flujo.php): documentos, NUR/CITE, derivación, respuestas, agrupar, accesos, concurrencia, importador, QR, trazabilidad sin nombres, migraciones', 'TODO OK'], ['Recorrido de pantallas con navegador real (capturas de este manual)', 'Sin errores de JavaScript'], ['Lectura del QR del sello impreso en PDF con un lector (zbar)', 'Texto correcto: NUR, tipo de entrada, fecha, referencia, remitente, fojas, anexos, celular'], ['Hoja de ruta: código de control impreso y dentro del QR', 'Correcto']], [6400, 2960]);
h1('2. Entorno y datos de prueba');
ol(['Sistema instalado y abierto (http://127.0.0.1:8080).', 'Escudo de la entidad cargado (Administración → Entidad).', 'Oficinas y cargos importados desde el Excel y nombres asignados.', 'Usuarios de práctica: Ana (u401, jefa), Beto (u402), Elena (u403), Luis (u404), **Dani (u435, Ventanilla)**, **admin**. Clave de práctica: Demo12345 (admin: Admin12345).', 'Navegador Chrome, Edge o Firefox actualizado. Presione Ctrl + F5 antes de empezar.']);
h2('2.1 Cómo usar las tablas de casos');
p('Cada caso tiene un **ID**, los **pasos**, el **resultado esperado** y una **figura de referencia** (la captura de cómo debe verse). Marque **☐ Aprobó** si ocurre lo esperado o **☐ Falló** si no, y anote observaciones. Si falla, registre una incidencia (sección 9).');
h1('3. Casos: novedades de la versión 1.2');
h2('3.1 Documentos con colores (DOC)');
table(['ID', 'Pasos', 'Resultado esperado', 'Ref.', 'Aprobó / Falló'], [
 ['DOC-01', 'Ingresar como Ana. Menú Documentos → Crear nuevo.', 'Se ve una tarjeta por tipo, **cada una de color distinto** (INF azul marino, CAR burdeos, CIR verde…) con prefijo, descripción y ejemplo de CITE.', 'Ver imagen', '☐ / ☐'],
 ['DOC-02', 'Pulsar la tarjeta Informe.', 'El formulario muestra una franja con el color y el prefijo de Informe.', 'Ver imagen', '☐ / ☐'],
 ['DOC-03', 'Guardar un Informe para Beto.', 'Se crea con NUR y CITE (INF/…/Nº 0001/2026). La vista del documento conserva el color en la franja lateral.', 'Ver imagen', '☐ / ☐'],
 ['DOC-04', 'Crear una Carta y una Nota Interna.', 'Cada una usa su propio color; en “Documentos creados” las etiquetas de tipo conservan el color.', '—', '☐ / ☐'],
 ['DOC-05', 'Mirar con tamaño de pantalla pequeño (reducir ventana).', 'Las tarjetas se reacomodan sin superponerse.', '—', '☐ / ☐']], [900, 2700, 3560, 800, 1400]);
img('05-tipos-documento.jpg', 'Referencia DOC-01: menú de tipos de documento por colores.', 500);
img('06-form-documento.jpg', 'Referencia DOC-02: formulario con franja de color.', 500);
img('07-documento-creado.jpg', 'Referencia DOC-03: documento creado.', 500);
h2('3.2 Nombre y cargo en la esquina (CAB)');
table(['ID', 'Pasos', 'Resultado esperado', 'Ref.', 'Aprobó / Falló'], [
 ['CAB-01', 'Ingresar como Ana.', 'Arriba a la derecha: **Ana Mamani Quispe** (negrita) y debajo su **cargo** (ALCALDE (SA) MUNICIPAL).', 'Ver imagen', '☐ / ☐'],
 ['CAB-02', 'Cerrar sesión e ingresar como Dani.', 'Cambia a Dani Torrez Lima y su cargo.', 'Ver imagen', '☐ / ☐'],
 ['CAB-03', 'Pasar el mouse sobre el nombre.', 'Aparece nombre, cargo y oficina; al pulsar abre “Información de usuario”.', '—', '☐ / ☐'],
 ['CAB-04', 'Ver la cabecera en todas las pantallas (Inicio, Bandeja, Documentos).', 'El bloque es visible y no tapa el buscador ni el enlace “Salir”.', '—', '☐ / ☐']], [900, 2700, 3560, 800, 1400]);
img('04-inicio.jpg', 'Referencia CAB-01 (marca 7).', 500);
h2('3.3 Ventanilla en colores (VEN)');
table(['ID', 'Pasos', 'Resultado esperado', 'Ref.', 'Aprobó / Falló'], [
 ['VEN-01', 'Ingresar como Dani. Ventanilla → Registrar nueva.', 'Encabezado institucional y **cuatro secciones numeradas de color** (1 azul, 2 verde, 3 ocre, 4 violeta).', 'Ver imagen', '☐ / ☐'],
 ['VEN-02', 'Llenar: Juan Pérez Mamani, Comunidad Tacopaya, 71234567, “Nota CCT-014/2026”, 3 fojas, “1 planilla”, referencia, derivar a Ana. Pulsar Registrar y derivar.', 'Aviso verde con NUR nuevo y enlaces de impresión.', 'Ver imagen', '☐ / ☐'],
 ['VEN-03', 'Intentar registrar sin Remitente.', 'El sistema no deja continuar y pide el dato.', '—', '☐ / ☐'],
 ['VEN-04', 'Abrir Registros externos.', 'El registro aparece con NUR, remitente, código de control y botones Cargo + etiquetas / Etiquetas / **Sello QR**.', 'Ver imagen', '☐ / ☐'],
 ['VEN-05', 'Abrir “Cargo + etiquetas”.', 'Una página Carta con el cargo y las etiquetas, con escudo, NUR y QR.', 'Ver imagen', '☐ / ☐']], [900, 2700, 3560, 800, 1400]);
img('41-ventanilla-nueva.jpg', 'Referencia VEN-01/02.', 480);
img('43-ventanilla-lista.jpg', 'Referencia VEN-04.', 480);
img('44-cargo.jpg', 'Referencia VEN-05.', 480);
h2('3.4 Sello QR con escudo (SEL)');
table(['ID', 'Pasos', 'Resultado esperado', 'Ref.', 'Aprobó / Falló'], [
 ['SEL-01', 'En el registro pulsar **Sello QR**.', 'Pantalla con casillas de posición, tamaño, ajuste fino y vista previa de la hoja Carta.', 'Ver imagen', '☐ / ☐'],
 ['SEL-02', 'Marcar solo **Superior derecha**.', 'La vista previa muestra un solo sello arriba a la derecha con **escudo, NUR, QR y fecha**.', 'Ver imagen', '☐ / ☐'],
 ['SEL-03', 'Desmarcar y marcar **Media derecha**; luego **Inferior derecha**.', 'El sello se mueve a esa zona. Marcando varias, aparecen varios sellos.', 'Ver imagen', '☐ / ☐'],
 ['SEL-04', 'Cambiar tamaño a pequeño y grande.', 'El sello cambia de tamaño y el QR sigue siendo nítido.', '—', '☐ / ☐'],
 ['SEL-05', 'Poner ajuste horizontal 5 y vertical −5 mm.', 'El sello se desplaza ligeramente.', '—', '☐ / ☐'],
 ['SEL-06', 'Imprimir (o Guardar como PDF) en Carta vertical.', 'Una sola página; **solo el sello** impreso, el resto en blanco, sin encabezados del navegador.', '—', '☐ / ☐'],
 ['SEL-07', 'Colocar una copia de nota en la impresora y reimprimir.', 'El sello cae en el espacio libre elegido sin cubrir el texto.', 'Ver imagen', '☐ / ☐'],
 ['SEL-08', 'Escanear el QR con el celular.', 'Texto: CODIGO DE CONTROL (NUR), TIPO DE ENTRADA, FECHA/HORA, REFERENCIA, REMITENTE, FOJAS, ANEXOS, CELULAR.', '—', '☐ / ☐'],
 ['SEL-09', 'Ingresar como Beto (no Ventanilla) y abrir la dirección del sello.', 'Error 403: sin permiso.', '—', '☐ / ☐'],
 ['SEL-10', 'Como admin, abrir Auditoría.', 'Figura la acción **sello_qr** con el usuario y el NUR.', '—', '☐ / ☐']], [900, 2700, 3560, 800, 1400]);
img('45-sello-form.jpg', 'Referencia SEL-01/02.', 500);
img('46-sello-tres-posiciones.jpg', 'Referencia SEL-03/07: tres posiciones sobre una copia de nota (composición ilustrativa).', 580);
h2('3.5 Consulta con código de control (CON)');
table(['ID', 'Pasos', 'Resultado esperado', 'Ref.', 'Aprobó / Falló'], [
 ['CON-01', 'Abrir una hoja de ruta para imprimir.', 'Debajo del NUR se lee **Código de control: XXXXXX** (6 caracteres).', 'Ver imagen', '☐ / ☐'],
 ['CON-02', 'Salir. En el ingreso pulsar “Consulta de trámite”.', 'Formulario con NUR y Código de control; no pide usuario.', 'Ver imagen', '☐ / ☐'],
 ['CON-03', 'Escribir NUR correcto y código **equivocado**.', 'Mensaje de que no corresponde; **ningún dato** del trámite.', 'Ver imagen', '☐ / ☐'],
 ['CON-04', 'Escribir NUR y código correctos.', 'Ficha, estado, **dónde se encuentra ahora** y tabla de trazabilidad completa.', 'Ver imagen', '☐ / ☐'],
 ['CON-05', 'Revisar el resultado.', '**No aparecen nombres de personas**, proveídos ni contenido; solo oficinas y cargos.', 'Ver imagen', '☐ / ☐'],
 ['CON-06', 'Derivar el trámite a otra persona y consultar de nuevo.', 'La ubicación actual cambia a la nueva oficina/cargo y se añade una fila.', '—', '☐ / ☐'],
 ['CON-07', 'Archivar el trámite y consultar.', 'Estado “Concluido / archivado”.', '—', '☐ / ☐'],
 ['CON-08', 'Fallar el código muchas veces seguidas.', 'El sistema limita los intentos temporalmente.', '—', '☐ / ☐'],
 ['CON-09', 'Usar “Imprimir esta consulta”.', 'Se imprime solo la ficha, sin menús.', '—', '☐ / ☐']], [900, 2700, 3560, 800, 1400]);
img('48-hoja-ruta-control.jpg', 'Referencia CON-01.', 480);
img('50-consulta-form.jpg', 'Referencia CON-02.', 440);
img('51-consulta-error.jpg', 'Referencia CON-03.', 440);
img('52-consulta-resultado.jpg', 'Referencia CON-04/05.', 520);
h1('4. Casos de regresión (lo que ya existía)');
table(['ID', 'Pasos', 'Resultado esperado', 'Aprobó / Falló'], [
 ['REG-01', 'Ingresar con usuario y clave correctos / incorrectos.', 'Entra / mensaje de error sin pistas.', '☐ / ☐'],
 ['REG-02', 'Primer ingreso con clave temporal.', 'Obliga a elegir clave nueva.', '☐ / ☐'],
 ['REG-03', 'Crear Informe y derivar como oficial con proveído y urgente.', 'Aparece en la Entrada del destinatario como URGENTE.', '☐ / ☐'],
 ['REG-04', 'Derivar dos copias.', 'Las copias aparecen en la entrada de cada destinatario como copia.', '☐ / ☐'],
 ['REG-05', 'Recepcionar y mirar Pendientes.', 'Pasa a Pendientes con semáforo.', '☐ / ☐'],
 ['REG-06', 'Generar respuesta.', 'Mismo NUR, nuevo CITE.', '☐ / ☐'],
 ['REG-07', 'Cancelar derivación no recibida.', 'Vuelve a Pendientes del emisor.', '☐ / ☐'],
 ['REG-08', 'Archivar y desarchivar.', 'Va a la carpeta y regresa.', '☐ / ☐'],
 ['REG-09', 'Agrupar dos hojas.', 'Carátula de agrupación y bandeja Agrupados.', '☐ / ☐'],
 ['REG-10', 'Imprimir hoja de ruta Carta vertical, en blanco y con hojas anexas.', 'QR, escudo, cuerpo; anexas con NUR arriba.', '☐ / ☐'],
 ['REG-11', 'Cuaderno de derivaciones.', 'PDF con las derivaciones elegidas.', '☐ / ☐'],
 ['REG-12', 'Buscar por NUR, CITE, palabra.', 'Resultados correctos.', '☐ / ☐'],
 ['REG-13', 'Reportes (oficina, recibida, personalizado, CSV).', 'Datos coherentes.', '☐ / ☐'],
 ['REG-14', 'Adjuntar y descargar un archivo.', 'Se sube y baja intacto.', '☐ / ☐']], [900, 3300, 3560, 1600]);
h1('5. Seguridad y permisos');
table(['ID', 'Pasos', 'Resultado esperado', 'Aprobó / Falló'], [
 ['SEG-01', 'Un usuario común intenta abrir Administración.', 'Error 403.', '☐ / ☐'],
 ['SEG-02', 'Un usuario ve un trámite en el que no participa (por la dirección).', 'No lo permite (o solo según su jerarquía).', '☐ / ☐'],
 ['SEG-03', 'Cerrar sesión y usar el botón “atrás”.', 'No muestra datos sin ingresar.', '☐ / ☐'],
 ['SEG-04', 'Consulta pública: probar texto raro en NUR (comillas, <script>).', 'Se rechaza o se muestra como texto; no se rompe nada.', '☐ / ☐'],
 ['SEG-05', 'Intentos de ingreso repetidos con clave mala.', 'Bloqueo temporal.', '☐ / ☐']], [900, 3300, 3560, 1600]);
h1('6. Instalación y actualización (a ejecutar por ustedes)');
table(['ID', 'Pasos', 'Resultado esperado', 'Aprobó / Falló'], [
 ['INS-01', 'Ejecutar INSTALAR.bat en una computadora limpia.', 'Pasos [1/6]…[6/6] terminan sin error y abre el sistema.', '☐ / ☐'],
 ['INS-02', 'Cerrar y volver a abrir con INICIAR.bat.', 'Los datos siguen ahí.', '☐ / ☐'],
 ['INS-03', 'Ejecutar ACTUALIZAR.bat con la v1.2 sobre una instalación anterior.', 'Respalda, copia y sistema funciona; datos intactos.', '☐ / ☐'],
 ['INS-04', 'Importar el Excel de oficinas y cargos.', 'Crea oficinas y usuarios con claves temporales.', '☐ / ☐']], [900, 3300, 3560, 1600]);
img('80-consola-instalar.jpg', 'Referencia INS-01 (ilustración: no ejecutado en Windows).', 480);
h1('7. Pruebas de impresión');
table(['ID', 'Documento', 'Qué verificar', 'Aprobó / Falló'], [
 ['IMP-01', 'Hoja de ruta', 'Carta vertical, una página con el escudo, QR y código de control legibles.', '☐ / ☐'],
 ['IMP-02', 'Cargo + etiquetas', 'Cargo arriba y dos etiquetas; QR legible.', '☐ / ☐'],
 ['IMP-03', 'Sello QR', 'Solo el sello; posición correcta; QR legible con el celular.', '☐ / ☐'],
 ['IMP-04', 'Documento (Informe/Carta)', 'Se imprime sin menús; la franja de color no oculta el texto.', '☐ / ☐']], [900, 2400, 4460, 1600]);
h1('8. Criterios de aceptación');
ul(['Todos los casos 3.x (novedades) aprobados, salvo observaciones menores aceptadas por escrito.', 'Ningún caso de seguridad (SEG) fallido.', 'Regresión: al menos 90 % aprobado y sin fallos críticos.', 'Ninguna incidencia de gravedad **Alta** abierta.']);
h1('9. Registro de incidencias');
table(['N.º', 'Caso', 'Descripción', 'Gravedad (A/M/B)', 'Estado'], [['1', '', '', '', ''], ['2', '', '', '', ''], ['3', '', '', '', ''], ['4', '', '', '', ''], ['5', '', '', '', ''], ['6', '', '', '', '']], [700, 1100, 4400, 1760, 1400]);
h1('10. Resumen y acta de aprobación');
table(['Grupo', 'Casos', 'Aprobados', 'Fallados'], [['Documentos (DOC)', '5', '', ''], ['Cabecera (CAB)', '4', '', ''], ['Ventanilla (VEN)', '5', '', ''], ['Sello QR (SEL)', '10', '', ''], ['Consulta (CON)', '9', '', ''], ['Regresión (REG)', '14', '', ''], ['Seguridad (SEG)', '5', '', ''], ['Instalación (INS)', '4', '', ''], ['Impresión (IMP)', '4', '', '']], [3400, 1800, 2080, 2080]);
p('**Conclusión:**  ☐ Aceptado   ☐ Aceptado con observaciones   ☐ Rechazado');
table(['Rol', 'Nombre', 'Firma', 'Fecha'], [['Probador/a', '', '', ''], ['Responsable de área', '', '', ''], ['Administrador del sistema', '', '', '']], [2400, 2800, 2400, 1760]);
L.generar({ entidad: 'Gobierno Autónomo Municipal', titulo: 'Manual de Pruebas', subtitulo: 'Plan y registro de pruebas del Sistema de Correspondencia', version: '1.2', fecha: 'noviembre de 2026', portada: '45-sello-form.jpg', lema: 'Cada caso se marca como aprobado o fallado; al final se firma el acta.' }, process.argv[2]);
