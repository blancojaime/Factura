import json
def mk():
    B = []
    return B, {
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

def chk(f, *items): f['table'](['N.º', 'Verificación', 'Resultado'], [[str(i + 1), t, '☐ ✔   ☐ ✘'] for i, t in enumerate(items)])

# ====================================================== 1. IMPORTAR ACTIVOS DESDE EXCEL
B, f = mk()
f['cover']('Importar activos fijos desde Excel', 'Manual específico: libro de Excel + carpeta de fotografías',
           '**Para quién:** el encargado de Activos Fijos (usuario `activos`) y el administrador del sistema.',
           '**Qué hace:** carga de una sola vez un inventario ya existente (por ejemplo 100 pupitres) desde un libro de Excel, y relaciona cada fotografía de una **carpeta aparte** con su activo mediante tres columnas del Excel: `foto1`, `foto2` y `foto3`.',
           '**Dónde está:** menú **Activos fijos → Importar desde Excel**.')
f['h1']('1. Cuándo usar esta importación')
f['ul']('Cuando la entidad **ya tiene** un inventario de activos (en Excel u otro sistema) y quiere pasarlo a SIGAA sin volver a digitar.',
        'Cuando los bienes ya tienen su **código** y se quiere conservar (por ejemplo `001-01-30121-0001`); si el código se deja vacío, SIGAA genera uno.',
        'Cuando se tienen fotografías de los bienes y se quieren dejar ya asociadas a cada ficha.')
f['note']('Para bienes **nuevos** que ingresan por compra o donación use el flujo normal: *Ingreso a almacén → Codificación*. Esta importación es para inventarios existentes.', '', 'No confundir')
f['h1']('2. Antes de empezar')
f['ol']('Verifique que existan en **Catálogos y bases de datos** (Activos fijos): las **cuentas contables**, los **auxiliares** (Mesa, Silla, Pupitre…), los **edificios** y sus **ambientes**. El Excel solo puede usar lo que ya está creado.',
        'Si va a indicar responsables, deben existir en **Catálogos → Funcionarios**.',
        'Reúna todas las fotografías en **una sola carpeta** (JPG, PNG o WEBP, de hasta 8 MB cada una).',
        'Descargue la **plantilla de Excel** desde la propia pantalla (botón **Descargar plantilla de Excel**): trae los encabezados correctos, un ejemplo y la hoja **CATALOGOS** con los valores válidos de su entidad.')
f['h1']('3. Estructura del libro de Excel')
f['p']('La plantilla tiene tres hojas: **DATOS** (donde usted escribe), **INSTRUCCIONES** y **CATALOGOS** (lista de cuentas, auxiliares, edificios, ambientes, estados y responsables válidos). La fila 1 de DATOS son los encabezados — **no los cambie ni los reordene**. Desde la fila 2, **un activo por fila**. Los encabezados naranja son obligatorios y los verdes son las fotos.')
f['table'](['Columna', 'Obligatoria', 'Qué escribir', 'Ejemplo'], [
    ['`codigo`', 'No', 'Código del activo (máx. 20). Vacío = SIGAA lo genera. Si ya existe en SIGAA se rechaza.', '001-01-30121-0001'],
    ['`descripcion`', '**Sí**', 'Descripción del bien (máx. 240).', 'PUPITRE BIPERSONAL DE MADERA'],
    ['`cuenta`', '**Sí**', 'Número o nombre de la cuenta contable (hoja CATALOGOS).', '3'],
    ['`auxiliar`', '**Sí**', 'Número o nombre del auxiliar de **esa** cuenta.', 'MESA'],
    ['`edificio`', '**Sí**', 'Código o nombre del edificio / establecimiento.', 'U.E. CARAZANI'],
    ['`ambiente`', 'No', 'Código o nombre del ambiente. Vacío = «SIN ASIGNAR (ALMACÉN)».', 'AULA 2'],
    ['`estado`', 'No', 'Nuevo, Bueno, Regular, Malo o Pésimo. Vacío = Bueno.', 'Bueno'],
    ['`valor`', '**Sí**', 'Valor en Bs, sin separador de miles.', '350.50'],
    ['`fecha_ingreso`', 'No', 'Fecha dd/mm/aaaa. Vacío = hoy.', '15/03/2024'],
    ['`responsable`', 'No', 'Funcionario a cargo (debe existir en Funcionarios). Con responsable el activo queda **ASIGNADO**; sin él, **EN ALMACÉN**.', 'EDWIN TONY CHUCA ORDOÑEZ'],
    ['`marca`, `modelo`, `serie`, `color`, `observaciones`', 'No', 'Datos de la ficha técnica.', 'CAFÉ'],
    ['`foto1`, `foto2`, `foto3`', 'No', 'Nombre **exacto** del archivo de la foto (con extensión). Hasta tres fotos por activo.', 'pupitre_001.jpg'],
])
f['h1']('4. La carpeta de fotografías')
f['ul']('Las fotos **no van dentro del Excel**: se dejan en una carpeta aparte, por ejemplo `C:\\fotos_inventario`.',
        'En `foto1`, `foto2` y `foto3` se escribe solo el **nombre del archivo** (no la ruta): `pupitre_001.jpg`. Mayúsculas o minúsculas no importan.',
        'Un mismo activo puede tener hasta 3 fotos; varios activos **no** deben compartir el mismo archivo (cada activo guarda su propia copia).',
        'Formatos admitidos: **JPG, PNG y WEBP**. Cada foto puede pesar hasta **8 MB**.',
        'No es obligatorio que todas las filas tengan fotos: las columnas pueden quedar vacías.')
f['h1']('5. Paso a paso en SIGAA', True)
f['ol']('Ingrese con el usuario de Activos Fijos y abra **Activos fijos → Importar desde Excel**. Arriba verá la estructura del Excel y el botón para descargar la plantilla.',
        'En **2. Elija los archivos** pulse **Seleccionar Excel…** y elija su libro.',
        'Pulse **Seleccionar carpeta de fotos…** y elija la carpeta (el navegador pedirá confirmar que permite leer los archivos de esa carpeta). Verá «Carpeta de fotos: N archivo(s)».',
        'Pulse **Validar (no guarda nada)**. SIGAA revisa **todas** las filas y le dice si el Excel está correcto, qué filas tienen problemas y qué fotos nombradas **faltan** en la carpeta.',
        'Si hay errores, corrija el Excel y repita la validación. Mientras haya errores el botón **Importar** permanece bloqueado: **no se importa nada a medias**.',
        'Con el Excel correcto pulse **Importar**. SIGAA crea los activos (con su historial/kardex) y luego **sube las fotografías** una a una, mostrando cuántas se subieron.')
f['img']('af_importar_1.jpg', 'Pantalla de importación: estructura, plantilla y selección de archivos.')
f['img']('af_importar_2.jpg', 'Resultado: activos importados y fotografías subidas (se avisa de las que faltaban en la carpeta).')
f['note']('Si alguna foto nombrada en el Excel no está en la carpeta, el activo **sí se crea** y la pantalla le indica qué foto falta. Después puede agregarla en **Fichas técnicas** del activo.', 'warn', 'Fotos faltantes')
f['h1']('6. Ejemplo completo')
f['p']('Se quiere importar dos pupitres de la U.E. Carazani, con tres fotografías en total.')
f['table'](['codigo', 'descripcion', 'cuenta', 'auxiliar', 'edificio', 'ambiente', 'estado', 'valor', 'fecha_ingreso', 'color', 'foto1', 'foto2'], [
    ['001-01-30121-0001', 'PUPITRE BIPERSONAL DE MADERA', '3', 'MESA', 'U.E. CARAZANI', 'AULA 2', 'Bueno', '350.5', '15/03/2024', 'CAFÉ', 'pupitre_001.jpg', ''],
    ['*(vacío)*', 'PUPITRE UNIPERSONAL', '3', 'MESA', 'U.E. CARAZANI', 'AULA 2', 'Nuevo', '210', '*(hoy)*', 'AZUL', 'pupitre_002.png', 'pupitre_003.jpg'],
])
f['ul']('El primer activo conserva su código `001-01-30121-0001`; el segundo recibe un código generado por SIGAA.',
        'La carpeta contiene `pupitre_001.jpg` y `pupitre_002.png`, pero **no** `pupitre_003.jpg`: la validación avisa «Faltan 1 foto(s)» y, al importar, se suben 2 de 3.')
f['h1']('7. Mensajes de error frecuentes')
f['table'](['Mensaje', 'Qué significa', 'Qué hacer'], [
    ['«La cuenta … no existe»', 'La cuenta no está en el catálogo o está mal escrita.', 'Use el número o el nombre tal como aparece en la hoja CATALOGOS.'],
    ['«El auxiliar … no existe en la cuenta …»', 'El auxiliar pertenece a otra cuenta.', 'Elija un auxiliar de esa misma cuenta, o créelo en Catálogos → Auxiliares contables.'],
    ['«El edificio … no existe» / «El ambiente …»', 'Edificio o ambiente no registrado.', 'Cree el edificio/ambiente en Catálogos o corrija el nombre.'],
    ['«El responsable … no está en Catálogos → Funcionarios»', 'El nombre no coincide con el funcionario.', 'Cópielo exactamente de la hoja CATALOGOS o regístrelo antes.'],
    ['«El valor debe ser un número…»', 'Valor vacío o con texto.', 'Escriba solo números: 350.50.'],
    ['«El código … ya existe en SIGAA» / «está repetido en el Excel»', 'Código duplicado.', 'Cambie el código o déjelo vacío para que SIGAA genere uno.'],
    ['«La foto … debe ser JPG, PNG o WEBP»', 'Extensión no admitida.', 'Convierta la foto o corrija el nombre.'],
    ['«Faltan columnas obligatorias en la fila 1»', 'Se cambiaron o borraron encabezados.', 'Use la plantilla descargada de SIGAA.'],
])
f['h1']('8. Después de importar')
f['ul']('Imprima las **etiquetas con código QR** en *Etiquetas (stickers)*: cada QR incluye la entidad, el edificio, el auxiliar contable y el código del activo.',
        'Complete en *Fichas técnicas* lo que falte (características, fotos adicionales).',
        'Los activos con responsable quedan **asignados**; los demás se asignan en *Asignación y entrega*.',
        'Cada importación queda registrada en la **bitácora** (Administración).',
        'Si cargó el **logo de la entidad** (Administración → Configuración → Logo), saldrá en las etiquetas y en todos los reportes. Los textos largos de las etiquetas se reducen o recortan solos; el QR siempre lleva el texto completo.')
f['h2']('Lista de verificación')
chk(f, 'Descargué la plantilla y no cambié los encabezados.', 'Todas las cuentas, auxiliares, edificios y responsables existen en los catálogos.', 'Las fotos están en una sola carpeta y sus nombres coinciden con foto1/foto2/foto3.', 'La validación terminó sin errores.', 'Tras importar, revisé 3 activos al azar (datos y fotos) en Fichas técnicas.', 'Imprimí las etiquetas con QR.')
json.dump({'out': 'Manual_Importar_Activos_Excel_y_Fotos', 'bloques': B}, open('/home/user/Factura/sigaa/docs/fuentes/m1.json', 'w'), ensure_ascii=False)

# ====================================================== 2. IMPORTAR DESDE VSIAF
B, f = mk()
f['cover']('Importar activos desde el VSIAF a SIGAA', 'Manual específico: traer a SIGAA lo que ya existe en el VSIAF',
           '**Para quién:** el administrador del sistema y, si el administrador lo permite, el encargado de Activos Fijos.',
           '**Qué hace:** lee las tablas del VSIAF 2.0 (sin modificarlas) y crea en SIGAA los activos que SIGAA aún no tiene. El VSIAF no guarda todo lo que usa SIGAA: se importa **lo que tenga**.',
           '**Dónde está:** menú **Activos fijos → Importar desde el VSIAF**.')
f['h1']('1. Qué se trae y qué no')
f['table'](['Dato en SIGAA', 'Viene del VSIAF', 'Observación'], [
    ['Código del activo', 'Sí (`CODIGO`)', 'Se conserva el mismo código.'],
    ['Descripción', 'Sí', 'Hasta 240 caracteres.'],
    ['Cuenta contable', 'Sí, por el **grupo contable**', 'La cuenta de SIGAA debe tener cargado su «Cód. VSIAF» (Catálogos → Cuentas contables).'],
    ['Auxiliar contable', 'Sí (nombre)', 'Si no existe en la cuenta, SIGAA lo crea (opción activada por defecto).'],
    ['Valor', 'Sí (costo)', ''],
    ['Fecha de ingreso', 'Sí (día, mes y año)', ''],
    ['Estado del bien', 'Sí (Bueno, Regular, Malo…)', 'Si no coincide, queda «Bueno».'],
    ['Responsable', 'Sí (nombre, cargo y CI)', 'El activo queda **ASIGNADO**. Si el funcionario no existe, SIGAA lo crea (opción por defecto).'],
    ['Oficina', 'Sí', 'Si coincide con un ambiente del edificio elegido, se ubica allí; si no, queda en el ambiente que usted elija y la oficina se anota en las observaciones.'],
    ['Edificio', '**No** (el VSIAF no lo tiene)', 'Lo elige usted para todo el lote.'],
    ['Marca, modelo, serie, color, **fotografías**, ficha técnica', '**No**', 'Se completan después en *Fichas técnicas*.'],
])
f['h1']('2. Antes de empezar', True)
f['ol']('**Cierre el VSIAF** en todas las computadoras (SIGAA solo lo lee, pero así los datos están completos).',
        'Verifique que cada **grupo contable del VSIAF** tenga su cuenta equivalente en SIGAA: *Catálogos y bases de datos → Cuentas contables y partidas*, columna **Cód. VSIAF**. Los activos de un grupo sin cuenta equivalente **no se importan** y la vista previa lo avisa.',
        'Cree en SIGAA el **edificio** donde quedarán los activos (por ejemplo «U.E. Carazani») y su ambiente «SIN ASIGNAR».',
        'Anote la carpeta de instalación del VSIAF (normalmente `C:\\vsiaf`, la que contiene `vsiaf.exe` y la carpeta `dbfs`).')
f['h1']('3. Paso a paso')
f['ol']('Abra **Activos fijos → Importar desde el VSIAF**.',
        'En **1. Origen** escriba la carpeta del VSIAF y pulse **Comprobar carpeta**. Debe aparecer el nombre de la entidad y el número de unidades. Elija la **unidad administrativa** a traer (o «Todas») y si quiere **todos** los activos o **solo los aprobados**.',
        'En **2. Dónde quedarán en SIGAA** elija el **edificio** y el ambiente por defecto. Deje marcadas las opciones de crear auxiliares y funcionarios que falten (recomendado).',
        'Pulse **Leer el VSIAF (vista previa)**. No se escribe nada: verá cuántos activos se leyeron, cuántos son nuevos, cuántos **ya existen** en SIGAA (se omiten), los totales por grupo contable y los primeros activos.',
        'Revise los avisos en amarillo (por ejemplo, grupos sin cuenta equivalente).',
        'Pulse **Importar N activo(s) a SIGAA** y confirme.')
f['img']('vsiaf_desde_1.jpg', 'Vista previa de lo que se traerá del VSIAF.')
f['img']('vsiaf_desde_2.jpg', 'Importación realizada.')
f['h1']('4. Qué ocurre al importar')
f['ul']('Cada activo se crea con el **mismo código del VSIAF**, queda asignado a su responsable y con su movimiento en el kardex («Importado del VSIAF»).',
        'En observaciones se anota la unidad del VSIAF, si estaba **ELABORADO** o **APROBADO**, la oficina y el grupo contable.',
        'Quedan registrados como **ya enviados** al VSIAF: si después usa *Enviar al VSIAF*, SIGAA **no** vuelve a mandarlos (ya están allí).',
        'Si ejecuta la importación otra vez, los activos que ya vinieron se **omiten**: no se duplican.',
        'La operación queda en la **bitácora** y en el historial de lotes.')
f['h1']('5. Después de importar')
f['ul']('Complete en *Fichas técnicas*: marca, modelo, serie y **fotografías**.',
        'Imprima las **etiquetas con QR** (entidad, edificio, auxiliar y código).',
        'Si el edificio asignado no es el real, use *Devolución / transferencia* para ubicar los bienes, o cree edificios/ambientes y reasigne.')
f['h1']('6. Problemas frecuentes')
f['table'](['Mensaje o situación', 'Qué hacer'], [
    ['«No se encontró la carpeta de datos (dbfs)»', 'Escriba la carpeta que contiene `vsiaf.exe` y `dbfs`.'],
    ['«El grupo contable N … no tiene cuenta equivalente»', 'Cargue el «Cód. VSIAF» de la cuenta en Catálogos y repita la vista previa.'],
    ['«El responsable … no está en Funcionarios»', 'Active «Crear los funcionarios que falten» o regístrelos antes.'],
    ['«No hay activos nuevos para traer del VSIAF»', 'Ya se importaron todos o el filtro (unidad / aprobados) no coincide.'],
    ['«Elija el edificio de SIGAA…»', 'Seleccione el edificio de destino en el paso 2.'],
])
f['h1']('7. Quién puede usarlo')
f['p']('El administrador del sistema puede **reservar** el envío y la importación con el VSIAF solo para administradores: en **Administración → Configuración → Activos fijos**, marque *«Reservar al administrador el envío e importación con el VSIAF»* y guarde. Con esa opción activada, el encargado de Activos Fijos **no ve** los menús *Enviar al VSIAF* ni *Importar desde el VSIAF* y el servidor rechaza cualquier intento de usarlos. Desmarque la opción para devolver el acceso.')
f['h2']('Lista de verificación')
chk(f, 'El VSIAF está cerrado y conozco su carpeta.', 'Las cuentas de SIGAA tienen cargado el «Cód. VSIAF».', 'La vista previa muestra los totales por grupo esperados.', 'Importé y revisé 3 activos (código, responsable, valor y fecha).', 'Completé fichas y fotos de los activos más importantes.', 'Una segunda lectura muestra 0 activos nuevos.')
json.dump({'out': 'Manual_Importar_Activos_desde_VSIAF', 'bloques': B}, open('/home/user/Factura/sigaa/docs/fuentes/m2.json', 'w'), ensure_ascii=False)

# ====================================================== 3. CONCILIACIÓN
B, f = mk()
f['cover']('Conciliación de vales con la estación de servicio', 'Guía detallada paso a paso, con un caso práctico',
           '**Para quién:** el encargado de Combustible (usuario `combustible`), el Responsable de Activos Fijos y Almacenes, y quien autoriza el pago.',
           '**Qué hace:** compara lo que **cobra la estación de servicio** (vale por vale) con lo que SIGAA sabe: qué vales se entregaron, a quién, para qué vehículo y si ya se presentó el descargo. Solo los vales **conformes** se pagan.',
           '**Dónde está:** menú **Combustible → Conciliación**.')
f['h1']('1. La idea en una página')
f['p']('Cada vale de combustible tiene un número y un valor (Bs 30, 50 o 100). Pasa por estos estados:')
f['table'](['Estado del vale', 'Qué significa', 'Se genera cuando…'], [
    ['**Disponible**', 'Está en el almacén de vales.', 'Se recibe el lote del proveedor (*Recepción de vales*).'],
    ['**Entregado**', 'Lo tiene el conductor.', 'Se emite la solicitud y el vale (*Emitir vales*).'],
    ['**Utilizado**', 'El conductor ya presentó el descargo con la factura.', 'Se registra el *Descargo de vales*.'],
    ['**Conciliado / pagado**', 'La estación lo cobró y se verificó.', 'Se ejecuta esta *Conciliación*: el vale queda marcado con el Nº de conciliación (CC-0001/2026).'],
    ['Devuelto, Anulado, Vencido, Extraviado', 'Casos de baja.', 'Devoluciones y bajas.'],
])
f['note']('La conciliación **solo da por buenos** los vales en estado **Utilizado** (con descargo) cuyo monto y placa coinciden con lo cobrado. Todo lo demás queda **observado** y no se paga hasta aclararlo.', 'ok', 'Regla de oro')
f['h1']('2. Antes de conciliar: lista de control', True)
f['ol']('Todos los **descargos** del periodo están registrados (*Descargo de vales*). Si falta un descargo, el vale aparecerá «SIN DESCARGO».',
        'Las **devoluciones** de vales no usados se hicieron (*Devolución / baja de vales*); los vales sin usar vuelven al almacén.',
        'Revise el visor **Vales emitidos** para ver cuántas emisiones están aún «Emitido» (sin descargo).',
        'Tenga a mano el **detalle de cobro** que entrega la estación de servicio (factura + planilla de vales).')
f['img']('com_emitidos.jpg', 'Visor «Vales emitidos»: una fila por solicitud, con vales, monto y estado del descargo.')
f['h1']('3. Cómo preparar el detalle de la estación')
f['p']('La estación entrega, junto con su factura, una lista de los vales que recibió. Necesita **una fila por vale** con estas columnas (en este orden o con encabezados):')
f['table'](['Columna', 'Obligatoria', 'Ejemplo'], [
    ['Nº vale', '**Sí**', '1001'], ['Fecha', 'No', '07/10/2026'], ['Placa', 'No (recomendable)', '2345ABC'], ['Litros', 'No', '4.31'], ['Monto Bs', '**Sí**', '30'], ['Factura', 'No', 'F-5001'],
])
f['ul']('Puede **cargar un archivo Excel (.xlsx)** o un CSV con esas columnas, o **copiar las filas desde Excel y pegarlas** en el recuadro.',
        'Con o sin encabezado: SIGAA reconoce los títulos «Nro Vale», «Fecha», «Placa», «Litros», «Monto» y «Factura».',
        'Los montos pueden venir como `30`, `30,00` o `1.250,50`.')
f['h1']('4. Paso a paso en SIGAA')
f['ol']('Abra **Combustible → Conciliación**.',
        'En **1. Proveedor y periodo** elija la **estación de servicio**, el contrato (opcional) y las fechas **desde / hasta** del cobro (normalmente el mes).',
        'En **2. Vales cobrados por el proveedor** pulse **Choose File / Seleccionar archivo** para cargar el Excel, o pegue las filas en el recuadro. Debajo verá «Se reconocen N vale(s) por Bs X»: **compare ese total con la factura de la estación**.',
        'Pulse **Conciliar**. SIGAA procesa cada vale, registra la conciliación (CC-0001/2026) y abre el **documento PDF** para firma.',
        'Revise el **resultado** en pantalla: vales conformes, **monto a pagar** y observados por tipo.')
f['img']('conc_1.jpg', 'Datos del proveedor y vales pegados antes de conciliar (5 vales por Bs 170).')
f['img']('conc_2.jpg', 'Resultado: 2 conformes (Bs 60 a pagar) y 3 observados.')
f['h1']('5. Cómo leer el resultado', True)
f['table'](['Resultado', 'Qué significa', 'Qué hacer'], [
    ['**CONFORME**', 'El vale fue entregado, el conductor presentó el descargo, el monto y la placa coinciden y no se había pagado antes.', 'Se **paga**. Queda marcado como conciliado.'],
    ['MONTO DIFERENTE', 'La estación cobra un monto distinto del valor del vale.', 'Pida a la estación la corrección o la nota de crédito. **No pagar** esa línea.'],
    ['PLACA DIFERENTE', 'El vale se cargó a un vehículo distinto del entregado (Art. 14: prohibido).', 'Investigar. Solicitar explicación escrita al conductor y a la estación.'],
    ['NO ENTREGADO', 'El vale está en el almacén de vales y no fue entregado, pero la estación lo cobró.', '**Posible uso indebido.** Investigar de inmediato; no pagar.'],
    ['SIN DESCARGO', 'Entregado y cobrado, pero el conductor aún no presentó el descargo.', 'Pedir el descargo al conductor; concilie de nuevo cuando exista.'],
    ['NO REGISTRADO', 'El número de vale no existe en SIGAA para ese proveedor.', 'Verificar el número (¿error de digitación?) o posible vale falso.'],
    ['DUPLICADO', 'El vale aparece más de una vez en el detalle de la estación.', 'Pedir aclaración; solo puede pagarse una vez.'],
    ['YA CONCILIADO', 'El vale ya fue pagado en otra conciliación.', 'No pagar de nuevo; pedir a la estación que lo retire de la factura.'],
    ['DADO DE BAJA', 'El vale figura anulado, vencido o extraviado.', 'No pagar; verificar la causa.'],
    ['NO COBRADO', 'Vale utilizado según el descargo que la estación **no** cobró en el periodo.', 'Informativo: puede cobrarse en la siguiente factura.'],
])
f['h1']('6. El documento de conciliación')
f['p']('Al conciliar se genera el PDF **«Conciliación de vales con el proveedor»**, con el detalle vale por vale, el **monto a pagar** y las firmas del Responsable de Activos Fijos y Almacenes (**responsable de combustible**) y del Secretario Municipal Administrativo y Financiero (**autoriza pago**). El documento lleva el **logo de la entidad** si se cargó en Administración → Configuración. Imprímalo, fírmelo y adjúntelo al comprobante de pago. Puede reimprimirlo desde la tabla **Conciliaciones realizadas** (botón **PDF**).')
f['img']('conc_pdf.jpg', 'Documento de conciliación para firma.')
f['h1']('7. Caso práctico completo')
f['p']('**Situación:** la estación «El Alto SRL» presenta su cobro de octubre por **5 vales, Bs 170**. En SIGAA, la solicitud VC-0001/2026 entregó los vales 1001 a 1005 (Bs 30 c/u) a un conductor; este presentó descargo con los vales 1001, 1002 y 1003; los 1004 y 1005 se devolvieron al almacén.')
f['table'](['Vale cobrado', 'Monto cobrado', 'Lo que SIGAA sabe', 'Resultado', 'Decisión'], [
    ['1001', '30', 'Utilizado, placa 2345ABC', 'CONFORME', 'Pagar Bs 30'],
    ['1002', '30', 'Utilizado, placa 2345ABC', 'CONFORME', 'Pagar Bs 30'],
    ['1003', '**50**', 'Utilizado; el vale vale Bs 30', 'MONTO DIFERENTE', 'No pagar; pedir corrección'],
    ['1004', '30', 'Devuelto: está en el almacén', 'NO ENTREGADO', 'No pagar; investigar'],
    ['9999', '30', 'No existe', 'NO REGISTRADO', 'No pagar; verificar'],
])
f['p']('**Resultado:** 2 conformes, **monto a pagar Bs 60** (no Bs 170), 3 observados. El Nº de conciliación es CC-0001/2026 y los vales 1001 y 1002 quedan marcados como conciliados: no podrán cobrarse otra vez.')
f['h1']('8. Buenas prácticas')
f['ul']('Concilie **cada mes** y antes de autorizar cualquier pago.',
        'Compare siempre el total reconocido en pantalla con el total de la **factura** de la estación.',
        'Use el **código QR** del *Vale de combustible* (Nº de solicitud, cantidad de vales y monto) para verificar rápidamente un vale en la estación o en la oficina.',
        'No pague líneas observadas: pida aclaración por escrito y concilie de nuevo cuando se resuelvan.',
        'Si una línea observada se aclara (por ejemplo, llega el descargo), vuelva a conciliar con ese vale: pasará a CONFORME.',
        'Archive el PDF de conciliación junto con la factura y el descargo.')
f['h2']('Lista de verificación')
chk(f, 'Todos los descargos del periodo están registrados.', 'El detalle de la estación tiene Nº de vale y monto por fila.', 'El total reconocido coincide con la factura.', 'Revisé cada línea observada y anoté la decisión.', 'Imprimí y firmé el PDF de conciliación.', 'Solo pagué el monto de los vales CONFORMES.')
f['h1']('9. Preguntas frecuentes')
f['table'](['Pregunta', 'Respuesta'], [
    ['¿Puedo conciliar varias veces el mismo periodo?', 'Sí, pero cada vale conforme queda conciliado la primera vez; en una segunda conciliación aparecerá «YA CONCILIADO».'],
    ['La estación cobra vales de dos cortes con el mismo número.', 'SIGAA toma el que coincide con el monto cobrado; si no coincide, aparece «MONTO DIFERENTE».'],
    ['¿Quién puede conciliar?', 'Combustible y el administrador. Los demás roles solo consultan.'],
    ['Me equivoqué de archivo, ¿puedo deshacer?', 'La conciliación queda registrada. Si fue un error de carga, pida al administrador revisar la bitácora; los vales no pagados siguen sin conciliar.'],
])
json.dump({'out': 'Guia_Conciliacion_Vales_Estacion_Servicio', 'bloques': B}, open('/home/user/Factura/sigaa/docs/fuentes/m3.json', 'w'), ensure_ascii=False)
print('ok')
