import json, sys
sys.path.insert(0, '.')
from contenido_novedades import nuevo, guardar

PIE = 'SIGAA · Solicitud 4'

# ───────────── Manual del módulo de Revalúo técnico
def manual_revaluo(f):
    f['cover']('Manual del módulo Revalúo técnico de activos fijos', 'Cómo revaluar los activos totalmente depreciados (valor Bs 1) con el método comparativo de mercado',
               '**Menú:** Activos fijos → Revalúo técnico', '**Quién lo usa:** Encargado de Activos Fijos, perito / comisión calificadora y Administrador (consulta: todos los roles)',
               '**Resultado:** Informe Técnico de Revalúo y Anexos en Word, activos con su nuevo valor y vida útil, e incremento patrimonial a «Reserva por Revalúos Técnicos»')
    f['h1']('1. Para qué sirve y base legal')
    f['p']('Muchos activos fijos de la entidad ya terminaron de depreciarse y figuran en libros con un valor residual de **Bs 1**, aunque siguen en uso. El revalúo técnico les asigna un **valor técnico revaluado (VTR)** y una **nueva vida útil**, y el incremento se lleva a la cuenta de patrimonio «Reserva por Revalúos Técnicos». SIGAA guía todo el procedimiento y prepara los documentos en Word.')
    f['table'](['Norma', 'Qué aporta al procedimiento'], [
        ['**NC 4** — Revalorización Técnica (Colegio de Auditores de Bolivia)', 'Define el informe técnico (inciso 7) y la reserva por revalúo.'],
        ['**NB-SABS** (D.S. 0181)', 'Administración de bienes: registro, control y actualización del valor de los activos.'],
        ['**Ley 1178 (SAFCO)** y Principios de Contabilidad Integrada', 'Responsabilidad por la información, control interno y registro contable.'],
        ['**D.S. 24051** (Reglamento del IUE)', 'Referencia para la depreciación de activos fijos.'],
        ['**NIC 16 / NIIF**', 'Modelo de revaluación (valor razonable) como referencia técnica complementaria.'],
    ])
    f['note']('El módulo implementa el procedimiento tal como fue especificado para la entidad. Antes de aplicarlo, confirme con la Unidad Jurídica y la Unidad de Contabilidad que la norma vigente en su gestión no exige pasos adicionales.', 'warn', 'Importante')
    f['h1']('2. Qué debe tener listo')
    f['ul']('Los activos deben estar **codificados** y con su **ficha técnica** (descripción, estado físico). Se recomienda tener al menos una **fotografía** de cada bien (Fichas técnicas → fotos): la hoja de tasación y el anexo las muestran.',
            'Su **valor en libros neto debe ser Bs 1** (totalmente depreciados). Los activos importados del VSIAF o de Excel con valor 1 cumplen esta condición.',
            'El **estado físico** debe ser **Bueno, Regular o Malo**. Los activos Nuevos o en estado Pésimo no entran.',
            'El activo debe estar **operativo** (campo «¿Operativo?» de la ficha técnica = SI). Los bienes en desuso, obsoletos inservibles o propuestos para baja se marcan **NO** y se excluyen.',
            'Tenga a mano de **1 a 3 cotizaciones** por tipo de bien (proforma, proveedor, fecha, NIT o enlace) y el nombre del perito y de la comisión calificadora.')
    f['h1']('3. Conceptos que usa el módulo')
    f['table'](['Concepto', 'Significado'], [
        ['**VN** (Valor a Nuevo)', 'Precio de mercado de un bien idéntico o similar, nuevo. Se obtiene de cotizaciones.'],
        ['**VN base**', 'Promedio simple o **mediana** de las cotizaciones (el perito elige).'],
        ['**Factor de conservación**', 'Coeficiente por estado físico. Debe estar dentro del rango permitido.'],
        ['**VTR** (Valor Técnico Revaluado)', '**VN base × factor**. Nunca es menor a Bs 1.'],
        ['**Incremento**', 'VTR − valor anterior (Bs 1). Va a «Reserva por Revalúos Técnicos».'],
        ['**Vida útil residual**', 'Años y meses que el perito estima que el bien seguirá útil; se justifica con la inspección y las fotos.'],
    ])
    f['table'](['Estado físico (operativo)', 'Rango permitido del factor', 'Valor sugerido al armar el lote'], [['Bueno', '0,70 a 0,85', '0,78'], ['Regular', '0,40 a 0,60', '0,50'], ['Malo', '0,15 a 0,35', '0,25']])
    f['p']('El sistema **no deja guardar** un factor fuera del rango de su estado. El valor sugerido se puede cambiar dentro del rango según el criterio del perito.')
    f['h1']('4. Paso a paso', True)
    f['h2']('Paso 1 · Bandeja de selección')
    f['p']('Entre a **Activos fijos → Revalúo técnico**. La pestaña **1. Bandeja de selección** muestra **automáticamente** los activos que cumplen las tres condiciones (valor Bs 1, estado Bueno/Regular/Malo y operativo). Use los filtros **Cuenta contable**, **Auxiliar contable** o el buscador para acotar la lista (por ejemplo: solo Escritorios).')
    f['img']('r_bandeja.jpg', 'Bandeja de selección con los activos elegibles. El botón «No operativo» saca un activo de la bandeja.')
    f['p']('Marque los activos que irán en el lote (o «Seleccionar todos» al pie de la tabla) y pulse **Crear lote con N seleccionado(s)**. Un activo solo puede estar en **un lote abierto** a la vez.')
    f['h2']('Paso 2 · Crear el lote')
    f['p']('Escriba la descripción del lote, el **perito / responsable de la tasación** y su cargo, y la **comisión calificadora** (una persona por línea con el formato *Nombre | Cargo*). Estos datos aparecen en las firmas del informe y se pueden corregir después.')
    f['img']('r_modal.jpg', 'Datos del lote: perito y comisión calificadora.', 's')
    f['h2']('Paso 3 · Hoja de tasación de cada activo')
    f['p']('El lote se abre con una fila por activo. Pulse una fila para abrir su **hoja de tasación**: código, descripción, auxiliar, responsable, galería de fotos y el formulario de tasación.')
    f['img']('r_hoja.jpg', 'Hoja de tasación: fotos, cotizaciones, factor, vida útil y justificación. El cálculo se ve al instante.')
    f['ol']('**Cotizaciones (1 a 3):** complete proveedor, NIT, fecha, N.º de proforma, enlace o referencia y el **Valor a nuevo (VN)** y pulse **Agregar cotización**. Cada cotización necesita un respaldo (NIT, proforma o enlace). Con el clip puede adjuntar la proforma escaneada (PDF, JPG o PNG hasta 5 MB).',
            '**Valor base de comparación:** promedio simple o mediana.',
            '**Factor de conservación** dentro del rango de su estado.',
            '**Vida útil residual** en años (0 a 60) y meses (0 a 11).',
            '**Justificación técnica del perito** (mínimo 10 caracteres): inspección, fotos, estado de uso.',
            'Pulse **Guardar hoja**. La fila de la tabla pasa a «✔ completa» cuando tiene cotización, factor, vida útil y justificación.')
    f['h2']('Paso 4 · Consolidación y vista preliminar')
    f['p']('Al pie del lote se ve la **vista preliminar de incrementos patrimoniales**: por cuenta contable (débito Activo Fijo) y el total que se acredita a **Reserva por Revalúos Técnicos**. También hay indicadores arriba: activos, hojas completas, valor anterior, valor revaluado e incremento.')
    f['img']('r_consolidacion.jpg', 'Consolidación: incremento por cuenta y botones de descarga y aprobación.')
    f['h2']('Paso 5 · Documentos Word')
    f['p']('Antes o después de aprobar puede descargar los dos documentos (antes de aprobar llevan la leyenda **DOCUMENTO PRELIMINAR**):')
    f['table'](['Documento', 'Contenido'], [
        ['**Informe Técnico de Revalúo** (Word)', 'Encabezado institucional con el logo de la entidad, antecedentes y justificación, base legal (NC 4, NB-SABS D.S. 0181, Ley 1178, D.S. 24051), bases técnicas (método comparativo, fuentes, tratamiento de datos, factores por estado), documentación examinada, resultados, conclusiones y recomendaciones, y firmas del perito, responsable de activos fijos y comisión.'],
        ['**Cuadros de soporte y anexos** (Word, hoja horizontal)', 'Anexo 1 Cuadro comparativo de valores (código, auxiliar/descripción, estado físico y funcional, **fotografía**, cotización de referencia VN, valor anterior Bs 1,00, VTR, incremento, vida útil restante); Anexo 2 detalle de cotizaciones; Anexo 3 justificación técnica; Anexo 4 **asiento contable modelo** (Debe: Activo Fijo; Haber: Reserva por Revalúos Técnicos).'],
    ])
    f['img']('r_word_informe.jpg', 'Primera página del Informe Técnico de Revalúo.', 's')
    f['img']('r_word_anexos.jpg', 'Anexo 1: cuadro comparativo de valores con fotografía.')
    f['img']('r_word_asiento.jpg', 'Anexo 4: asiento contable modelo sugerido.')
    f['note']('El logo del encabezado es el que se cargó en Administración → Configuración → Logo. El asiento es un **modelo referencial**: el registro definitivo lo hace la Unidad de Contabilidad con su plan de cuentas.', '', 'Dato útil')
    f['h2']('Paso 6 · Aprobar y aplicar')
    f['p']('Cuando **todas las hojas estén completas** se habilita **Aprobar y aplicar el revalúo**. El sistema pide el número de la resolución administrativa (opcional) y una confirmación.')
    f['img']('r_aprobar.jpg', 'Número de resolución que aprueba el revalúo.', 's')
    f['p']('Al aprobar, en una sola operación (si algo falla no se aplica nada):')
    f['ul']('El **valor** y el **valor en libros** de cada activo pasan al VTR y se guarda su **vida útil residual** y la fecha del revalúo.',
            'Cada activo recibe un movimiento **REVÁLUO** en su kardex (Consulta y kardex) con el valor anterior, el nuevo, el método, el factor y el incremento.',
            'Queda registro en la **bitácora** y el lote pasa a **APROBADO** (ya no se puede modificar).',
            'Los activos salen de la bandeja porque su valor dejó de ser Bs 1.')
    f['img']('r_aprobado.jpg', 'Lote aprobado: indicadores finales.')
    f['h1']('5. Ejemplo resuelto con números')
    f['table'](['Dato', 'Escritorio (estado Bueno)', 'Silla (estado Malo)'], [
        ['Cotizaciones (VN)', 'Bs 1.000 · 1.200 · 1.400', 'Bs 2 (solo una)'],
        ['Método', 'Promedio simple → VN base **Bs 1.200**', 'Promedio → VN base Bs 2'],
        ['Factor (rango)', '0,80 (0,70–0,85)', '0,15 (0,15–0,35)'],
        ['VN × factor', '1.200 × 0,80 = 960', '2 × 0,15 = 0,30'],
        ['**VTR**', '**Bs 960,00**', '**Bs 1,00** (mínimo)'],
        ['Incremento (VTR − 1)', 'Bs 959,00', 'Bs 0,00'],
        ['Vida útil residual', '4 años 6 meses', '8 meses'],
    ])
    f['p']('Con la **mediana** del escritorio (1.000 · 1.200 · 3.000) el VN base sería Bs 1.200 en vez de Bs 1.733,33: la mediana evita que una cotización muy alta o muy baja distorsione el resultado.')
    f['h1']('6. Cómo sacar un activo de la revisión')
    f['p']('Si un bien está en desuso, es obsoleto inservible o está propuesto para baja, márquelo **No operativo**: en la bandeja con el botón **No operativo** (pide el motivo) o en **Fichas técnicas** con el campo «¿Operativo?». Para volver a incluirlo, ponga SI en la ficha técnica.')
    f['h1']('7. Mensajes frecuentes y qué hacer')
    f['table'](['Mensaje', 'Qué significa / qué hacer'], [
        ['No son elegibles (o ya están en otro lote abierto)', 'El activo no cumple las tres condiciones o está en otro lote en borrador. Revise valor, estado y «¿Operativo?».'],
        ['…el factor de conservación debe estar entre 0.70 y 0.85', 'El factor no corresponde al estado del activo; use uno dentro del rango.'],
        ['Cada cotización necesita un respaldo', 'Falta NIT, N.º de proforma o enlace.'],
        ['Máximo 3 cotizaciones por activo', 'Quite una para agregar otra.'],
        ['No se puede aprobar: … falta …', 'La lista indica qué hoja está incompleta (cotización, factor, vida útil o justificación).'],
        ['…su valor en libros cambió desde que se armó el lote', 'Alguien modificó el valor del activo; retírelo del lote y vuelva a armarlo.'],
        ['El lote ya fue aprobado: no se puede modificar', 'Un lote aprobado es definitivo.'],
    ])
    f['h1']('8. Alcance y limitaciones')
    f['ul']('El módulo calcula y registra el **revalúo**; **no recalcula la depreciación posterior**: la depreciación del nuevo valor y la vida útil residual se aplican en el sistema contable (VSIAF / SIGEP).',
            'El incremento y el nuevo valor **no se envían automáticamente al VSIAF**. Use el informe y el cuadro comparativo para el registro (el importador del VSIAF acepta una hoja REVALUOS: integración posible en una etapa posterior).',
            'Los coeficientes de conservación vienen de la especificación de la entidad (rangos por estado). Si la normativa de su gestión fija otros rangos, solicite el ajuste.',
            'Las fotografías del anexo son JPG o PNG; las WEBP no se incrustan en el Word.',
            'El módulo de consulta del kardex muestra el movimiento REVÁLUO; los reportes PDF/Excel existentes no cambian.')
    f['h1']('9. Quién puede hacer qué')
    f['table'](['Rol', 'Permiso'], [['ACTIVOS y ADMIN', 'Crear lotes, tasar, marcar no operativo, aprobar, descargar Word.'], ['ALMACEN, COMBUSTIBLE, CONSULTA', 'Solo ver bandeja, lotes y descargar los documentos.']])

# ───────────── Manual de licenciamiento, distribución y bases de datos
def manual_licencia(f):
    f['cover']('Licenciamiento del escritorio, distribución y base de datos', 'Clave de activación para Windows, base de datos vacía de distribución y base demostrativa de capacitación',
               '**Para:** el proveedor (emite las claves y arma los instaladores) y quien instala en la entidad', '**Incluye:** Generador de claves · Ventana de activación · Base vacía · Base demostrativa · Lista de entrega')
    f['h1']('1. Resumen')
    f['table'](['Pieza', 'Qué es', 'Quién la usa'], [
        ['**SIGAA Escritorio** con clave de activación', 'La aplicación de Windows pide una clave. Sin clave funciona **30 días de prueba**.', 'Usuario final'],
        ['**Generador de claves** (`GENERADOR_DE_CLAVES.bat`)', 'Herramienta del proveedor que crea las claves de activación firmadas.', 'Solo el proveedor'],
        ['**Base de datos vacía**', 'Web y escritorio inician sin ningún dato de ejemplo. Traen solo los catálogos normativos y el usuario administrador.', 'Todas las entidades'],
        ['**Base demostrativa** (`distribucion/SIGAA_Base_Demostrativa_Capacitacion.sqlite`)', 'Copia con datos de ejemplo y 14 activos listos para practicar el revalúo.', 'Capacitación'],
    ])
    f['h1']('2. Clave de activación: cómo funciona')
    f['ul']('La clave la fabrica el proveedor con su **clave privada** (secreta). La aplicación solo trae la **clave pública**: puede comprobar que una clave es auténtica, pero **no puede fabricar claves**.',
            'La clave contiene: nombre de la entidad, el **ID del equipo** (o «cualquier equipo»), la **fecha de vencimiento** (o perpetua) y el tipo. Si alguien cambia un solo carácter, la firma deja de coincidir y la clave se rechaza.',
            'El **ID del equipo** (formato `XXXX-XXXX-XXXX-XXXX`) se calcula con datos del equipo (en Windows, su identificador de máquina). Una clave atada a un equipo no sirve en otro.',
            'Sin clave, SIGAA funciona **30 días de prueba**; el registro de la prueba está protegido contra edición simple y contra el retroceso del reloj del equipo.',
            'La aplicación avisa **30 días antes** del vencimiento y revisa la licencia cada hora mientras está abierta.')
    f['note']('Un licenciamiento local **desalienta** el uso no autorizado, pero no es infalible: quien tenga conocimientos para modificar el programa podría saltarlo. Para una protección mayor se necesitaría un servidor de licencias en internet.', 'warn', 'Alcance')
    f['h1']('3. Para el proveedor', True)
    f['h2']('3.1 Primera vez: crear el par de claves')
    f['ol']('Haga doble clic en **GENERADOR_DE_CLAVES.bat** (requiere Node.js).', 'Elija la opción **1) Crear el par de claves**. Se crean `tools\\licencias\\privada\\clave_privada.pem` (SECRETA) y `desktop\\licencia\\publica.pem` (va dentro de la aplicación).',
            '**Haga una copia de seguridad de la carpeta `tools\\licencias\\privada`** en un lugar seguro (pendrive guardado, caja fuerte). **No la suba a internet ni la comparta.** Si se pierde, no podrá emitir claves compatibles con los instaladores ya entregados.',
            'Si `CREAR_INSTALADOR_ESCRITORIO.bat` encuentra que no hay par de claves, lo crea automáticamente la primera vez.')
    f['note']('**Nunca** cree otro par de claves si ya entregó instaladores: las licencias emitidas dejarían de funcionar. El programa no sobrescribe un par existente.', 'warn', 'Cuidado')
    f['h2']('3.2 Crear el instalador')
    f['p']('Ejecute **CREAR_INSTALADOR_ESCRITORIO.bat**. El instalador (`release\\SIGAA Setup 1.0.0.exe`) ya incluye la clave pública. Para una prueba interna **sin** protección existe la variable `SIGAA_SIN_LICENCIA=1` (no distribuya esos instaladores).')
    f['h2']('3.3 Emitir la clave de un cliente')
    f['ol']('Pida al cliente el **ID del equipo** (lo ve en la ventana de activación, botón Copiar).', 'En el generador elija **2) Generar una clave de activación**.',
            'Escriba el **nombre de la entidad**, el **ID del equipo** (o `*` para cualquier equipo) y el **vencimiento** `AAAA-MM-DD` (vacío = perpetua).',
            'Copie la **clave completa** (empieza con `SIGAA1-`) y envíela al cliente por correo o WhatsApp.',
            'La opción **3)** lista las licencias emitidas (también están en `privada\\licencias_emitidas.csv`).')
    f['table'](['Caso', 'ID del equipo', 'Vencimiento'], [['Licencia perpetua para una PC', 'el ID de la PC', 'vacío'], ['Licencia anual para una PC', 'el ID de la PC', 'fecha límite'], ['Licencia para la entidad (cualquier PC)', '`*`', 'vacío o fecha']])
    f['h1']('4. Para el usuario final', True)
    f['ol']('Instale **SIGAA Setup** y ábralo. Aparece la **ventana de activación**.', 'Si desea probar, pulse **Continuar con la prueba** (30 días).', 'Para activar: pulse **Copiar** en «ID de este equipo» y envíelo al proveedor. Con la clave recibida, péguela en el recuadro y pulse **Activar**.',
            'La ventana confirma «✔ Licencia activa…». Pulse **Continuar**. Desde entonces SIGAA abre directo.', 'Para ver o renovar la licencia: menú **SIGAA → Licencia…**')
    f['img']('lic_prueba.jpg', 'Ventana de activación durante el período de prueba.', 's')
    f['img']('lic_activa.jpg', 'Licencia activa: entidad, tipo y vencimiento.', 's')
    f['img']('lic_error.jpg', 'Si la clave está incompleta o alterada se rechaza con un aviso claro.', 's')
    f['img']('lic_bloqueo.jpg', 'Terminada la prueba o vencida la licencia, solo se puede activar o cerrar.', 's')
    f['table'](['Mensaje', 'Qué hacer'], [
        ['La clave no tiene el formato de SIGAA / está incompleta', 'Copie la clave completa, sin cortar el inicio ni el final.'],
        ['La clave no es válida (firma incorrecta)', 'La clave fue alterada o es de otro proveedor. Pida una nueva.'],
        ['Esta clave fue emitida para otro equipo', 'Envíe al proveedor el ID de este equipo y pida una clave nueva.'],
        ['La licencia venció el …', 'Solicite la renovación y péguela en SIGAA → Licencia…'],
        ['Terminó el período de prueba', 'Ingrese su clave de activación.'],
        ['El registro del período de prueba fue alterado / fecha retrocedida', 'Ingrese su clave de activación; no modifique el reloj del equipo.'],
    ])
    f['p']('**Cambio de computadora:** pida una clave nueva con el ID del equipo nuevo. **Reinstalar Windows** puede cambiar el ID del equipo.')
    f['h1']('5. Base de datos vacía de distribución', True)
    f['p']('Tanto la versión **web** como la de **escritorio** inician con la base **vacía**: no se carga ningún dato de ejemplo.')
    f['table'](['Incluye', 'No incluye'], [
        ['Catálogos **normativos**: cuentas contables y auxiliares de activos, campos de ficha, estados físicos, grupos y subgrupos de materiales, unidades de medida, causales y pasos de baja, tipos de vehículo', 'Funcionarios, proveedores, unidades, aperturas, partidas, bodegas, vehículos, edificios, ambientes'],
        ['Configuración técnica (plazos, límites, litros por día, etc.)', 'Datos de la entidad: nombre, NIT, firmantes (quedan en blanco)'],
        ['El usuario **admin** (clave inicial `Admin2026`, que se debe cambiar al entrar)', 'Usuarios de demostración, ingresos, vales, activos, movimientos'],
    ])
    f['h2']('Cómo inicia cada versión')
    f['ul']('**Escritorio:** al abrirlo por primera vez crea la base vacía en la carpeta de datos del usuario.', '**Web con INICIAR_SIGAA.bat / .sh:** crea la base vacía (`npm run seed:vacia`). Para PostgreSQL y Docker la base nace vacía por defecto (`SIGAA_DEMO=0`).',
            'Solo si se necesita (capacitación) se carga el ejemplo con `SIGAA_DEMO=1` o `npm run seed:demo`.')
    f['h2']('Primeros pasos del administrador en una instalación nueva')
    f['img']('vacia_aviso.jpg', 'El tablero avisa «Instalación nueva» hasta que se configure el nombre de la entidad.')
    f['ol']('Ingrese con **admin / Admin2026** y cambie la clave.', 'Vaya a **Administración → Configuración y usuarios**: nombre de la entidad, sigla, NIT, secretaría, municipio, gestión y **firmantes** con sus cargos. Suba el **logo**.',
            'Cree los usuarios de cada encargado (Almacenes, Combustible, Activos fijos, Consulta).', 'En **Catálogos y bases de datos → Importar desde Excel** cargue funcionarios, proveedores, aperturas con presupuesto, partidas, edificios y ambientes, vehículos, etc.',
            'Cargue los activos con **Activos fijos → Importar desde Excel** (o desde el VSIAF) y las fotos.', 'Haga una **copia de seguridad** y pruebe restaurarla en otra PC.')
    f['img']('vacia_catalogos.jpg', 'Catálogos: en la base vacía solo están los normativos; los de la entidad se cargan desde Excel.')
    f['h1']('6. Base demostrativa para capacitación')
    f['p']('El archivo **`distribucion/SIGAA_Base_Demostrativa_Capacitacion.sqlite`** es una copia de respaldo con los datos de ejemplo (entidad «Calamarca») más **14 activos totalmente depreciados** (Bs 1) en estados Bueno, Regular y Malo, uno **no operativo** y uno en estado Nuevo, para practicar el revalúo y ver cómo el filtro de la bandeja los separa.')
    f['table'](['Usuario', 'Clave inicial', 'Rol'], [['admin', 'Admin2026', 'Administrador'], ['almacen', 'Almacen2026', 'Almacenes'], ['combustible', 'Combustible2026', 'Combustible'], ['activos', 'Activos2026', 'Activos fijos'], ['consulta', 'Consulta2026', 'Solo lectura']])
    f['h2']('Cómo cargarla')
    f['ul']('**Escritorio:** menú **SIGAA → Restaurar copia de respaldo…**, elija el archivo y confirme. SIGAA guarda antes una copia de sus datos actuales (carpeta `respaldos`) y se reinicia.',
            '**Web (SQLite):** con el sistema cerrado, copie el archivo a `server\\data\\sigaa.sqlite` (renombrándolo) y abra INICIAR_SIGAA.bat.', '**PostgreSQL:** esta copia es SQLite; para PostgreSQL ejecute `SIGAA_DEMO=1` sobre una base vacía.')
    f['note']('**Nunca** cargue la base demostrativa en un equipo con datos reales: reemplaza todo. Para volver a la base limpia, restaure una copia previa o recree la base vacía.', 'warn', 'Advertencia')
    f['p']('Para regenerar la base demostrativa: `npm run base:demo -w server -- <ruta\\archivo.sqlite>`.')
    f['h1']('7. Lista de verificación de entrega al cliente')
    f['table'](['N.º', 'Verificación', 'Resultado'], [[str(i + 1), t, '☐ ✔   ☐ ✘'] for i, t in enumerate([
        'El instalador se creó **después** de crear el par de claves (incluye la clave pública).', 'La carpeta `tools\\licencias\\privada` tiene copia de seguridad y **no** se entregó al cliente.', 'Se pidió al cliente el ID del equipo y se emitió la clave (entidad, equipo, vencimiento).',
        'Se instaló, se pegó la clave y la ventana mostró «Licencia activa».', 'Con una clave alterada la ventana la rechaza.', 'La base inició **vacía**: aparece el aviso «Instalación nueva».', 'Se cambió la clave del administrador y se completó la configuración de la entidad y el logo.',
        'Se cargaron los catálogos desde Excel.', 'Se hizo una copia de seguridad y se probó restaurarla.', 'Se entregó la base demostrativa solo en el equipo de capacitación.'])])
    f['h1']('8. Qué se verificó y qué no')
    f['table'](['Elemento', 'Estado'], [
        ['Emisión y verificación de claves (firma, equipo, vencimiento, prueba de 30 días, alteración, reloj)', 'Probado con pruebas automáticas.'],
        ['Base vacía: tablas, catálogos normativos, configuración neutra y ausencia de datos de ejemplo', 'Probado con pruebas automáticas (SQLite y PostgreSQL).'],
        ['Servidor empaquetado con sus dependencias arranca con base vacía', 'Probado en Linux.'],
        ['Ventana de activación y restauración de copias dentro de Electron/Windows', '**No se pudo probar en Windows real** en el entorno de desarrollo; pruébelo en el primer equipo de entrega.'],
        ['Instalador de Windows (`SIGAA Setup.exe`)', '**No probado en Windows real**; use la lista de verificación del punto 7.'],
    ])

# ───────────── Novedades de la solicitud 4
def novedades4(f):
    f['cover']('Novedades de la solicitud 4', 'Revalúo técnico, clave de activación, base vacía de distribución y manuales',
               '**Incluye:** módulo de revalúo con informes Word · clave de activación de escritorio · generador de claves · base de datos vacía · base demostrativa · manuales y descarga en un solo comprimido')
    f['h1']('Resumen')
    f['table'](['Qué cambió', 'Dónde se ve', 'Cómo se usa / manual'], [
        ['**Revalúo técnico de activos fijos** (NC 4)', 'Activos fijos → Revalúo técnico (web y escritorio)', 'Bandeja → hoja de tasación → consolidación → aprobación. Manual: *Manual_Revaluo_Tecnico_Activos_Fijos*.'],
        ['Informe Técnico de Revalúo y Anexos en **Word**', 'Botones al pie de cada lote', 'Incluyen logo, base legal, cuadro comparativo con fotografía y asiento contable modelo.'],
        ['Campo **¿Operativo?** del activo', 'Fichas técnicas y botón «No operativo» de la bandeja', 'Los bienes no operativos no entran al revalúo.'],
        ['**Clave de activación** del escritorio', 'Ventana de activación y menú SIGAA → Licencia…', 'Prueba de 30 días; clave atada al equipo y al vencimiento. Manual: *Manual_Licenciamiento_Distribucion_y_Base_de_Datos*.'],
        ['**Generador de claves** del proveedor', '`GENERADOR_DE_CLAVES.bat`', 'Crea el par de claves y emite las claves de los clientes.'],
        ['**Base de datos vacía** para distribución', 'Web y escritorio al iniciar por primera vez', 'Solo catálogos normativos y el usuario admin; aviso «Instalación nueva».'],
        ['**Base demostrativa** de capacitación', '`distribucion/SIGAA_Base_Demostrativa_Capacitacion.sqlite`', 'Se carga con SIGAA → Restaurar copia de respaldo… (escritorio).'],
        ['**Restaurar copia de respaldo**', 'Escritorio: menú SIGAA', 'Guarda antes una copia de los datos actuales.'],
        ['Descarga completa en **un solo comprimido (zip)**', 'GitHub: `SIGAA_Descarga_Completa.zip`', 'Código, manuales, paquete de capacitación, base demostrativa y herramientas.'],
    ])
    f['h1']('Decisiones que se tomaron por usted')
    f['ul']('**Factores por defecto:** al armar un lote se sugiere el punto medio redondeado de cada rango (Bueno 0,78 · Regular 0,50 · Malo 0,25); el perito puede ajustarlo dentro del rango.',
            '**Base de distribución vacía** (no el backup) y **base demostrativa aparte** para capacitación.', '**Licencia:** firma Ed25519 con clave pública dentro de la aplicación; prueba de 30 días; la clave se puede atar a un equipo y a una fecha.',
            '**Pendiente:** integración automática del revalúo con el VSIAF y la depreciación posterior (se hace en el sistema contable).')
    f['h1']('Dónde está cada manual')
    f['table'](['Tema', 'Documento'], [['Revalúo técnico', 'Manual_Revaluo_Tecnico_Activos_Fijos'], ['Clave de activación, base vacía y demostrativa', 'Manual_Licenciamiento_Distribucion_y_Base_de_Datos'],
        ['Pruebas paso a paso (capítulo 12)', 'Guia_SIGAA_Pruebas_por_Rol'], ['Implementación e instalación (capítulo de la solicitud 4)', 'Manual_SIGAA_Implementacion_y_Pruebas']])

# ───────────── Capítulos que se anexan a los manuales existentes (texto, sin imágenes)
def pruebas4(f):
    f['h1']('12. Pruebas de la solicitud 4: revalúo, activación y base vacía')
    f['note']('Estas pruebas usan la **base demostrativa** (`SIGAA_Base_Demostrativa_Capacitacion.sqlite`): restáurela primero (escritorio: SIGAA → Restaurar copia de respaldo…). La base de distribución viene **vacía** y no tiene datos para practicar.', 'warn', 'Antes de empezar')
    f['h2']('R · Revalúo técnico (usuario activos)')
    f['table'](['N.º', 'Prueba', 'Resultado esperado', 'Resultado'], [
        ['R1', 'Activos fijos → Revalúo técnico. Observe la bandeja.', 'Aparecen **14 activos** (valor neto Bs 1, estado Bueno/Regular/Malo, operativos). No aparecen el no operativo ni el de estado Nuevo.', '☐ ✔   ☐ ✘'],
        ['R2', 'Filtre por una cuenta (por ejemplo Equipo de Oficina y Muebles) y por un auxiliar.', 'La lista se reduce a esa cuenta/auxiliar.', '☐ ✔   ☐ ✘'],
        ['R3', 'Marque 3 activos y pulse Crear lote. Escriba perito y comisión (Nombre | Cargo).', 'Se crea el lote REV-0001/AAAA y se abre con 3 hojas; los 3 salen de la bandeja.', '☐ ✔   ☐ ✘'],
        ['R4', 'En la hoja de un activo Bueno escriba el factor 0,95.', 'Error: el factor debe estar entre 0,70 y 0,85.', '☐ ✔   ☐ ✘'],
        ['R5', 'Agregue una cotización sin NIT, proforma ni enlace.', 'Error: cada cotización necesita un respaldo.', '☐ ✔   ☐ ✘'],
        ['R6', 'Agregue 3 cotizaciones (1.000, 1.200, 1.400) con NIT, factor 0,80, vida 4 años 6 meses y una justificación. Guarde.', 'VN base Bs 1.200,00 · VTR Bs 960,00 · incremento Bs 959,00 · fila «✔ completa».', '☐ ✔   ☐ ✘'],
        ['R7', 'Intente agregar una cuarta cotización.', 'Error: máximo 3 cotizaciones.', '☐ ✔   ☐ ✘'],
        ['R8', 'Cambie el método a Mediana y guarde.', 'El VN base cambia según la mediana.', '☐ ✔   ☐ ✘'],
        ['R9', 'Con hojas incompletas observe el botón Aprobar.', 'Está desactivado y avisa que faltan hojas completas.', '☐ ✔   ☐ ✘'],
        ['R10', 'Complete las 3 hojas. Descargue el Informe Técnico y los Anexos (Word).', 'Se descargan 2 archivos .docx con la leyenda DOCUMENTO PRELIMINAR, logo, base legal, cuadro comparativo con fotografía y asiento contable.', '☐ ✔   ☐ ✘'],
        ['R11', 'Pulse Aprobar, escriba una resolución y confirme.', 'El lote queda APROBADO; los documentos Word ya no dicen PRELIMINAR y muestran la resolución.', '☐ ✔   ☐ ✘'],
        ['R12', 'Consulta y kardex del primer activo.', 'Aparece el movimiento REVÁLUO con valor anterior, nuevo, método, factor e incremento; el valor del activo es el VTR.', '☐ ✔   ☐ ✘'],
        ['R13', 'Intente editar una hoja del lote aprobado.', 'No se puede: el lote está aprobado.', '☐ ✔   ☐ ✘'],
        ['R14', 'En Fichas técnicas ponga ¿Operativo? = NO a otro activo de la bandeja.', 'Sale de la bandeja.', '☐ ✔   ☐ ✘'],
        ['R15', 'Ingrese como consulta e intente crear un lote.', 'Sin permiso: solo puede ver y descargar.', '☐ ✔   ☐ ✘'],
    ])
    f['h2']('L · Clave de activación (escritorio Windows)')
    f['table'](['N.º', 'Prueba', 'Resultado esperado', 'Resultado'], [
        ['L1', 'Abra SIGAA Escritorio recién instalado.', 'Aparece la ventana de activación con el ID del equipo y «Período de prueba: le quedan 30 día(s)».', '☐ ✔   ☐ ✘'],
        ['L2', 'Pegue una clave alterada o incompleta y pulse Activar.', 'Mensaje de clave no válida o incompleta; no se guarda.', '☐ ✔   ☐ ✘'],
        ['L3', 'En el generador (GENERADOR_DE_CLAVES.bat) opción 2, emita una clave para el ID del equipo con vencimiento a un año.', 'Se muestra la clave SIGAA1-… y queda anotada en licencias_emitidas.csv.', '☐ ✔   ☐ ✘'],
        ['L4', 'Pegue la clave y pulse Activar; luego Continuar.', '«✔ Licencia activa» con entidad, tipo y vencimiento; SIGAA abre.', '☐ ✔   ☐ ✘'],
        ['L5', 'Cierre y vuelva a abrir.', 'Abre directo, sin pedir la clave.', '☐ ✔   ☐ ✘'],
        ['L6', 'Emita una clave para **otro** ID de equipo y péguela.', 'Mensaje: la clave fue emitida para otro equipo.', '☐ ✔   ☐ ✘'],
        ['L7', 'Menú SIGAA → Licencia…', 'Muestra el estado de la licencia y permite pegar una clave nueva.', '☐ ✔   ☐ ✘'],
    ])
    f['h2']('V · Base de datos vacía y base demostrativa')
    f['table'](['N.º', 'Prueba', 'Resultado esperado', 'Resultado'], [
        ['V1', 'Instale o inicie SIGAA en un equipo nuevo (sin datos).', 'Inicia sin datos: tablero en cero y aviso «Instalación nueva» para el administrador.', '☐ ✔   ☐ ✘'],
        ['V2', 'Ingrese con admin / Admin2026.', 'Exige cambiar la clave. No existen los usuarios de demostración.', '☐ ✔   ☐ ✘'],
        ['V3', 'Catálogos y bases de datos.', 'Funcionarios, proveedores, bodegas, edificios y vehículos están vacíos; cuentas contables de activos, estados y grupos de materiales ya están cargados.', '☐ ✔   ☐ ✘'],
        ['V4', 'Complete Configuración (nombre de la entidad, firmantes, logo).', 'El aviso «Instalación nueva» desaparece y el logo sale en los reportes.', '☐ ✔   ☐ ✘'],
        ['V5', 'Importe funcionarios desde Excel.', 'Se cargan y se pueden elegir en las pantallas.', '☐ ✔   ☐ ✘'],
        ['V6', 'Escritorio: SIGAA → Restaurar copia de respaldo… y elija la base demostrativa.', 'SIGAA guarda una copia previa, se reinicia y muestra los datos de ejemplo.', '☐ ✔   ☐ ✘'],
    ])
    f['p']('Marque cada prueba y archive la hoja firmada junto con las del resto de la guía.')

def impl4(f):
    f['h1']('Solicitud 4: revalúo, licenciamiento y base vacía (para quien instala)')
    f['p']('Esta sección resume lo que cambia en la instalación a partir de la solicitud 4. Los detalles están en los manuales *Manual_Revaluo_Tecnico_Activos_Fijos* y *Manual_Licenciamiento_Distribucion_y_Base_de_Datos*.')
    f['h2']('Qué hay de nuevo')
    f['table'](['Tema', 'Detalle'], [
        ['Revalúo técnico', 'Menú Activos fijos → Revalúo técnico (web y escritorio). Dos tablas nuevas de trabajo (lotes, hojas y cotizaciones) y cuatro columnas nuevas en activos (operativo, valor en libros, vida residual, fecha de revalúo) que se crean solas al actualizar. Dependencia nueva del servidor: la biblioteca `docx` (Word); `npm install` la instala.'],
        ['Base de datos', 'La base de **distribución nace vacía** (web, escritorio, Docker, PostgreSQL). `INICIAR_SIGAA.bat/.sh` ahora ejecutan `npm run seed:vacia`. Para ejemplo: `npm run seed:demo` o `SIGAA_DEMO=1`.'],
        ['Escritorio', 'Ya no carga datos de ejemplo la primera vez. Pide clave de activación (30 días de prueba). Menú SIGAA → Licencia… y Restaurar copia de respaldo….'],
        ['Instalador', '`CREAR_INSTALADOR_ESCRITORIO.bat` crea el par de claves si falta e incluye la clave pública. Sin `desktop\\licencia\\publica.pem` el instalador no se genera (excepto con `SIGAA_SIN_LICENCIA=1`, solo para pruebas).'],
    ])
    f['h2']('Instalaciones existentes')
    f['p']('Al actualizar el programa, las tablas y columnas nuevas se crean automáticamente y los datos actuales no cambian. Las bases ya existentes **conservan** sus datos y configuración; solo las **bases nuevas** nacen vacías.')
    f['h2']('Flujo de distribución recomendado')
    f['ol']('Cree el par de claves (una sola vez) y guarde la carpeta `tools\\licencias\\privada` en lugar seguro.', 'Cree el instalador de escritorio y verifique la activación en un Windows real.', 'En cada entidad: instale, pida el ID del equipo, emita la clave, active.',
            'Entregue la base **vacía** (la aplicación ya la crea sola) y capacite con la **base demostrativa** en un equipo aparte.', 'Descargue todo el material en un solo comprimido: `SIGAA_Descarga_Completa.zip` (GitHub).')
    f['h2']('Verificaciones de esta etapa')
    f['table'](['Verificación', 'Resultado'], [['Pruebas automáticas (SQLite)', 'SQLite: 227 pasan y 3 se omiten (206 anteriores + 21 nuevas de revalúo, licencia y base vacía). PostgreSQL: 226 pasan y 4 se omiten.'],
        ['Informes Word del revalúo', 'Abiertos y convertidos a PDF con LibreOffice para revisar el diseño.'], ['Instalador de Windows y ventana de activación', 'No probados en Windows real (sin entorno disponible).']])

if __name__ == '__main__':
    for nombre, fn, out in [('s4_revaluo', manual_revaluo, 'Manual_Revaluo_Tecnico_Activos_Fijos'), ('s4_licencia', manual_licencia, 'Manual_Licenciamiento_Distribucion_y_Base_de_Datos'), ('s4_novedades', novedades4, 'Novedades_Solicitud_4')]:
        B, f = nuevo(); fn(f); guardar(nombre, B, out)
    for nombre, fn in [('a4_pruebas', pruebas4), ('a4_impl', impl4)]:
        B, f = nuevo(); fn(f); guardar(nombre, B, 'zz_' + nombre)
    print('ok')
