import json, sys
sys.path.insert(0, '.')
OUT = '/home/user/Factura/sigaa/docs/fuentes/'

def nuevo():
    B = []
    f = {
        'h1': lambda x, pb=False: B.append({'t': 'h1', 'x': x, 'pb': pb}),
        'h2': lambda x: B.append({'t': 'h2', 'x': x}),
        'p': lambda x: B.append({'t': 'p', 'x': x}),
        'ul': lambda *i: B.append({'t': 'ul', 'items': list(i)}),
        'ol': lambda *i: B.append({'t': 'ol', 'items': list(i)}),
        'table': lambda head, rows: B.append({'t': 'table', 'head': head, 'rows': rows}),
        'img': lambda src, cap='', size='': B.append({'t': 'img', 'src': src, 'cap': cap, 'size': size}),
        'note': lambda x, kind='', title='': B.append({'t': 'note', 'x': x, 'kind': kind, 'title': title}),
        'cover': lambda title, sub, *lines: B.append({'t': 'cover', 'title': title, 'sub': sub, 'lines': list(lines)}),
    }
    return B, f

def guardar(nombre, B, out=None):
    json.dump({'out': out or nombre, 'bloques': B}, open(OUT + nombre + '.json', 'w'), ensure_ascii=False)

# ───────────── Resumen de novedades (documento propio y capítulo del manual de implementación)
def resumen(f, con_img=True):
    f['h1']('Novedades de las solicitudes 2 y 3')
    f['p']('Resumen de lo que cambió en SIGAA, dónde se encuentra y cómo se usa. Los manuales específicos se mencionan al final de cada punto.')
    f['table'](['Qué cambió', 'Dónde se ve', 'Cómo se usa'], [
        ['**Logo de JB** en la portada', 'Pantalla de ingreso (solo ahí)', 'Se ve al abrir SIGAA; no hay nada que configurar.'],
        ['**Logo de la entidad** subido desde la PC', 'Administración → Configuración → Entidad y firmantes → **Logo**', 'Pulse **Examinar…**, elija un JPG o PNG (hasta 3 MB) y listo: aparece en el encabezado de **todos los PDF**, en los **reportes de Excel** y en las **etiquetas**. **Quitar** lo retira.'],
        ['**Etiquetas con QR** rediseñadas', 'Activos fijos → Etiquetas (stickers) / Codificación', 'Los textos ya no se superponen (se reducen o recortan solos si el nombre es largo). El QR es más grande, tiene margen blanco y lleva **4 líneas**: entidad, edificio, auxiliar contable y código.'],
        ['**QR en el Vale de combustible**', 'Combustible → Emitir vales → Vale (PDF)', 'El vale trae un recuadro «Datos de verificación» con Nº de solicitud, cantidad de vales y monto.'],
        ['Visor **Vales emitidos**', 'Combustible → Vales emitidos', 'Tabla con filtros y totales; una fila por solicitud. Pulse una fila para ver sus vales.'],
        ['**Conciliación** con la estación de servicio', 'Combustible → Conciliación', 'Guía detallada: *Guia_Conciliacion_Vales_Estacion_Servicio*.'],
        ['**Apertura / destino** y **comisión con cargo**', 'Almacenes → Ingresos (CGI) y Salidas (vales)', 'El campo «Proyecto / destino» ahora se llama **Apertura / destino**. La comisión de recepción se elige de la **lista de personal** y se completa el **Cargo**.'],
        ['**Importar desde Excel** los catálogos', 'Catálogos y bases de datos (botón arriba a la derecha)', 'Aperturas programáticas / destino, aperturas con presupuesto, partidas presupuestarias y los demás catálogos: se ve la estructura, se descarga la plantilla y se carga el Excel.'],
        ['**Importar activos desde Excel** con fotos', 'Activos fijos → Importar desde Excel', 'Manual: *Manual_Importar_Activos_Excel_y_Fotos*.'],
        ['**Importar desde el VSIAF**', 'Activos fijos → Importar desde el VSIAF', 'Manual: *Manual_Importar_Activos_desde_VSIAF*.'],
        ['**VSIAF solo para el administrador**', 'Administración → Configuración → Activos fijos', 'Marque «Reservar al administrador el envío e importación con el VSIAF»: el encargado de Activos Fijos deja de verlo y de poder usarlo.'],
        ['**Pasar a producción**', 'Administración → pestaña **Pasar a producción**', 'Elimina los datos de demostración (con copia previa y confirmación escrita) para empezar con la base limpia. Ver «Lista de verificación para entrar en producción».'],
        ['Seguridad reforzada', 'Todo el sistema', 'Componentes actualizados, fotos y logo validados, numeración de documentos a prueba de usuarios simultáneos, cabeceras de seguridad y token fuera del registro. Ver *Informe_Auditoria_SIGAA*.'],
        ['Reportes **sin hojas en blanco**', 'Todos los PDF', 'Cada documento sale con las páginas justas (antes añadía 2 hojas vacías).'],
        ['Instalador de escritorio **más robusto**', '`CREAR_INSTALADOR_ESCRITORIO.bat`', 'Si una instalación quedó dañada («no es una aplicación Win32 válida»), se repara sola. Con el QR ya se pueden imprimir las etiquetas en la versión de escritorio.'],
    ])
    f['h2']('Nombres que cambiaron')
    f['table'](['Antes', 'Ahora'], [
        ['Proyecto / destino (ingresos y salidas de Almacenes, reportes, PDF)', '**Apertura / destino**'],
        ['Catálogo «Proyectos / destinos»', '**Aperturas programáticas / destino**'],
        ['Comisión / responsable de recepción (texto libre)', '**Comisión / responsable de recepción** (lista de personal) + **Cargo**'],
        ['QR de la etiqueta: solo el código', 'QR con **entidad, edificio, auxiliar y código**'],
    ])
    f['note']('Si algún manual anterior dice «Proyecto / destino», léalo como **Apertura / destino**.', 'warn', 'Fe de erratas')

# ───────────── Pruebas nuevas por rol (capítulo de la guía de pruebas)
def pruebas(f):
    f['h1']('11. Pruebas de las solicitudes 2 y 3')
    f['p']('Pruebas nuevas para repetir con cada rol. Úselas junto a las anteriores y anote el resultado en la hoja de resultados de esta sección.')
    f['h2']('A10 · Apertura / destino y comisión con cargo (Almacenes · usuario almacen)')
    f['ol']('Menú **Ingresos (CGI)** → **Nuevo CGI**. Revise que el campo diga **Apertura / destino** (ya no «Proyecto / destino») y elija una apertura.',
            'En **Comisión / responsable de recepción** abra la lista: aparece el personal registrado. Elija a una persona.',
            'Compruebe que el campo **Cargo** se llenó solo. Corríjalo si hace falta, complete el CGI y guarde.',
            'Imprima el CGI: en los datos aparece **Comisión de recepción** y **Cargo de la comisión**, y la firma de recepción lleva el cargo.',
            'Menú **Salidas (vales)** → **Nuevo pedido**: el campo también dice **Apertura / destino**.')
    f['note']('Resultado esperado: «Apertura / destino» en ingreso, salida, PDF y reportes; la comisión sale de una lista y su cargo queda impreso.', 'ok')
    f['h2']('C9 · Vale de combustible con QR y visor de vales emitidos (Combustible · usuario combustible)')
    f['ol']('Emita vales como en la prueba C2 y abra el **Vale (PDF)**: la segunda página trae el recuadro **Datos de verificación (QR)**.',
            'Escanee el QR con el celular: debe mostrar el **Nº de solicitud**, la **cantidad de vales a entregar** y el **monto total**.',
            'Menú **Vales emitidos**: aparece la emisión con vales, monto, litros y estado. Pruebe los filtros (fechas, estado, placa) y la búsqueda.',
            'Pulse la fila: se abre el detalle con cada vale; el botón **Vale con QR (PDF)** reimprime el documento.')
    f['note']('Resultado esperado: el QR se lee y coincide con el vale impreso; los totales del visor cuadran con las emisiones del periodo.', 'ok')
    f['h2']('C10 · Conciliación con la estación de servicio (Combustible)')
    f['p']('Siga la *Guía de conciliación de vales con la estación de servicio* (caso práctico de 5 vales). Resultado esperado: 2 conformes (Bs 60), 3 observados (monto diferente, no entregado, no registrado) y el PDF de conciliación firmado.')
    f['h2']('F11 · Etiquetas con QR de cuatro datos (Activos Fijos · usuario activos)')
    f['ol']('Menú **Etiquetas (stickers)**, elija un edificio con nombre largo y pulse **Generar stickers**.',
            'Revise la hoja: los textos del edificio y del auxiliar **no se superponen** con el código ni con el QR.',
            'Escanee un QR con el celular: aparecen **cuatro líneas**: entidad, edificio, auxiliar contable y código del activo.',
            'En la **versión de escritorio** repita el paso 1: el PDF abre y se puede **imprimir**.')
    f['note']('Resultado esperado: etiquetas legibles, QR leído al primer intento, impresión posible también en escritorio.', 'ok')
    f['h2']('F12 · Importar activos desde Excel con fotos (Activos Fijos)')
    f['p']('Siga el *Manual: importar activos desde Excel* (menú **Importar desde Excel**). Resultado esperado: «Se importaron N activo(s)», fotos subidas y aviso de las que no estaban en la carpeta.')
    f['h2']('F13 · Importar desde el VSIAF (Activos Fijos o administrador)')
    f['p']('Siga el *Manual: importar activos desde el VSIAF* con una copia del VSIAF. Resultado esperado: vista previa con totales por grupo, importación con el mismo código del VSIAF y, en una segunda lectura, 0 activos nuevos.')
    f['h2']('M5 · Logo de la entidad (Administrador · usuario admin)')
    f['ol']('Menú **Configuración y usuarios** → **Configuración** → tarjeta **Entidad y firmantes**, campo **Logo**.',
            'Pulse **Examinar…**, elija un JPG o PNG de su computadora y espere «Logo cargado».',
            'Imprima un CGI, un reporte PDF y descargue un reporte en Excel: el logo aparece en el encabezado de los tres.',
            'Genere una hoja de etiquetas: el logo aparece en cada etiqueta.',
            'Pulse **Quitar**: los documentos nuevos salen sin logo.')
    f['note']('Resultado esperado: el mismo logo en PDF, Excel y etiquetas. Un archivo que no sea JPG/PNG o que pese más de 3 MB se rechaza con un mensaje.', 'ok')
    f['h2']('M6 · Importar catálogos desde Excel (Administrador)')
    f['ol']('Menú **Catálogos y bases de datos** → **Aperturas programáticas y presupuesto** → **Importar desde Excel**.',
            'Revise la estructura que muestra la ventana, pulse **Descargar plantilla de Excel**, llénela con 2 aperturas y su presupuesto.',
            'Pulse **Seleccionar Excel e importar…**: aparece «2 creado(s)». Repita con una apertura ya existente: aparece «1 actualizado(s)».',
            'Haga lo mismo con **Partidas presupuestarias** y **Aperturas programáticas / destino**.',
            'Cargue un Excel con una fila errónea: no se importa nada y se indica la fila y el problema.')
    f['h2']('M7 · Reservar el VSIAF al administrador (Administrador)')
    f['ol']('Menú **Configuración y usuarios** → tarjeta **Activos fijos** → marque **Reservar al administrador el envío e importación con el VSIAF** → **Guardar configuración**.',
            'Ingrese con el usuario `activos`: en el menú ya no aparecen **Enviar al VSIAF** ni **Importar desde el VSIAF**.',
            'Vuelva con `admin` y desmarque la opción: el usuario `activos` recupera los menús.')
    f['h2']('M8 · Pasar a producción (Administrador) — hágala SOLO en una copia de prueba')
    f['ol']('Menú **Configuración y usuarios** → pestaña **Pasar a producción**: se ve cuántos registros y usuarios de demostración hay.',
            'Deje marcada **Conservar los catálogos de la entidad**. Escriba **ELIMINAR** y pulse **Eliminar datos de demostración**; confirme.',
            'Aparece «Listo: el sistema quedó limpio» y la ruta de la copia previa. Compruebe: los tableros están en cero, los catálogos siguen, solo existe el usuario `admin`.',
            'Registre un ingreso nuevo: el número del documento empieza en **0001**.')
    f['note']('Resultado esperado: sistema limpio, catálogos y configuración intactos, copia previa creada. **No repita esta prueba en la base real.**', 'warn')
    f['h2']('Hoja de resultados de las pruebas nuevas')
    filas = [[c, n, r, '☐ ✔   ☐ ✘', ''] for c, n, r in [
        ('A10', 'Apertura / destino y comisión con cargo', 'Almacenes'), ('C9', 'Vale con QR y visor de vales emitidos', 'Combustible'), ('C10', 'Conciliación con la estación', 'Combustible'),
        ('F11', 'Etiquetas con QR de cuatro datos', 'Activos Fijos'), ('F12', 'Importar activos desde Excel con fotos', 'Activos Fijos'), ('F13', 'Importar desde el VSIAF', 'Activos Fijos'),
        ('M5', 'Logo de la entidad', 'Administrador'), ('M6', 'Importar catálogos desde Excel', 'Administrador'), ('M7', 'Reservar el VSIAF al administrador', 'Administrador'), ('M8', 'Pasar a producción (solo en copia de prueba)', 'Administrador')]]
    f['table'](['N.º', 'Prueba', 'Rol', 'Resultado', 'Observaciones'], filas)

# ───────────── Guía de envío al VSIAF
def vsiaf(f):
    f['h1']('5. Actualización: quién ve el VSIAF y la importación inversa')
    f['h2']('5.1 Reservar el envío y la importación al administrador')
    f['p']('En **Administración → Configuración → Activos fijos** hay una casilla **«Reservar al administrador el envío e importación con el VSIAF»**. Si se marca y se guarda:')
    f['ul']('Los menús **Enviar al VSIAF** e **Importar desde el VSIAF** solo los ve el administrador.',
            'Aunque alguien conozca la dirección de la pantalla, el sistema **rechaza** cualquier operación del VSIAF que no sea de un administrador.',
            'Al desmarcarla, el encargado de Activos Fijos recupera el acceso. Por defecto la casilla está **desmarcada**.')
    f['h2']('5.2 Importar del VSIAF a SIGAA')
    f['p']('Además de enviar activos de SIGAA al VSIAF, ahora se pueden **traer** a SIGAA los activos que ya están en el VSIAF (menú **Activos fijos → Importar desde el VSIAF**). Los activos traídos conservan el código del VSIAF y quedan registrados como «ya enviados», por lo que **no se vuelven a mandar** al VSIAF. Vea el *Manual: importar activos desde el VSIAF*.')
    f['h2']('5.3 Etiquetas y logo')
    f['ul']('Las etiquetas con QR muestran entidad, edificio, auxiliar y código; el logo de la entidad (Administración → Configuración) sale en reportes, documentos y etiquetas.',
            'Los informes de validación e importación en Excel que genera esta pantalla son archivos técnicos y no llevan logo.')

# ───────────── Manual de implementación
def implementacion(f):
    resumen(f)
    f['h1']('Actualización para quien instala')
    f['h2']('Instalador de escritorio (Windows)')
    f['ol']('Copie el `CREAR_INSTALADOR_ESCRITORIO.bat` actualizado a la carpeta `sigaa` y ejecútelo (necesita Node.js e internet).',
            'Si una instalación anterior quedó dañada (mensaje «no es una aplicación Win32 válida»), el archivo **borra `node_modules` y reinstala solo**; basta esperar.',
            'Para actualizar una PC que ya usa SIGAA: instale el nuevo `SIGAA Setup` encima. **Los datos no se pierden**: la base y las fotos están en la carpeta de datos del usuario y las tablas nuevas se crean al abrir.')
    f['h2']('Dónde se guardan los datos nuevos')
    f['table'](['Dato', 'Dónde'], [
        ['Logo de la entidad', 'Carpeta `logo` junto a la carpeta de fotos (en escritorio: carpeta de datos de SIGAA → «Abrir carpeta de datos»).'],
        ['Fotografías de activos', 'Carpeta `fotos` (también las que llegan por «Importar desde Excel»).'],
        ['Respaldos del VSIAF', 'Carpeta `backups` dentro de la instalación del VSIAF.'],
    ])
    f['note']('Haga una **copia de seguridad** (Administración → Respaldo) antes de actualizar una PC que ya está en uso.', 'warn', 'Antes de actualizar')
    f['h1']('Lista de verificación para entrar en producción')
    f['table'](['N.º', 'Verificación', 'Resultado'], [[str(i + 1), t, '☐ ✔   ☐ ✘'] for i, t in enumerate([
        '**Cambie la clave** del administrador (se exige al primer ingreso). Cree un usuario por encargado y use claves distintas (mín. 8 caracteres con letras y números).',
        'Entre a **Administración → Pasar a producción** y elimine los datos de demostración (y los usuarios de prueba).',
        'Cargue los catálogos de la entidad con **Catálogos → Importar desde Excel** (funcionarios, proveedores, aperturas con presupuesto, partidas, edificios, vehículos…).',
        'Cargue el **logo** de la entidad y revise el encabezado de un reporte PDF y de uno en Excel.',
        'Complete en **Configuración** el nombre de la entidad, los firmantes y sus cargos, la gestión y las unidades.',
        'Defina **SIGAA_JWT_SECRET** (cadena larga y aleatoria) si usa el servidor web; así las sesiones no se pierden al reiniciar.',
        'Si usa varias PC en red, publique el sistema detrás de **HTTPS** (por ejemplo un proxy inverso) y no exponga el puerto a internet.',
        'Programe **copias de seguridad**: SQLite se respalda a diario en la carpeta `respaldos` (copie esa carpeta a otro equipo o disco); con PostgreSQL use `pg_dump`.',
        'Pruebe **restaurar** una copia en otra PC antes de empezar a trabajar de verdad.',
        'Haga las pruebas de la *Guía de pruebas por rol* (capítulos 1 a 11) con datos reales de un caso pequeño y archive la hoja de resultados firmada.'])])
    f['h2']('Seguridad: lo que ya está y lo que depende de usted')
    f['table'](['Tema', 'Estado'], [
        ['Claves y bloqueo', 'Claves guardadas con scrypt; bloqueo de 15 minutos tras 5 intentos fallidos; cambio de clave obligatorio al primer ingreso.'],
        ['Permisos', 'Cada rol solo modifica su módulo; los catálogos compartidos, usuarios, logo y paso a producción son solo del administrador (verificado por el servidor).'],
        ['Archivos subidos', 'Fotos y logo se validan por su contenido (JPG/PNG/WEBP) y su nombre no puede salirse de la carpeta de datos.'],
        ['Sesiones', 'Duran 10 horas; el token no se guarda en el registro del sistema.'],
        ['**Depende de usted**', 'HTTPS en red, firewall, copias de seguridad fuera del equipo, actualizaciones periódicas y no compartir el usuario administrador.'],
    ])

if __name__ == '__main__':
    B, f = nuevo(); f['cover']('Novedades de las solicitudes 2 y 3', 'Resumen para usuarios, administradores y quien instala', '**Incluye:** logo, etiquetas con QR, vale con QR, vales emitidos, conciliación, apertura/destino, comisión con cargo, importaciones desde Excel y desde el VSIAF, opción VSIAF solo administrador.'); resumen(f)
    f['h1']('Dónde está cada manual')
    f['table'](['Tema', 'Documento'], [
        ['Importar activos desde Excel con fotos', 'Manual_Importar_Activos_Excel_y_Fotos'], ['Importar activos desde el VSIAF', 'Manual_Importar_Activos_desde_VSIAF'], ['Conciliación con la estación de servicio', 'Guia_Conciliacion_Vales_Estacion_Servicio'],
        ['Pruebas paso a paso por rol (incluye el capítulo 11 con las pruebas nuevas)', 'Guia_SIGAA_Pruebas_por_Rol'], ['Implementación e instalación', 'Manual_SIGAA_Implementacion_y_Pruebas'], ['Envío de activos al VSIAF', 'Guia_Envio_VSIAF']])
    guardar('n_resumen', B, 'Novedades_Solicitudes_2_y_3')
    for nombre, fn in [('a_pruebas', pruebas), ('a_vsiaf', vsiaf), ('a_impl', implementacion)]:
        B, f = nuevo(); fn(f); guardar(nombre, B, 'zz_' + nombre)
    print('ok')
