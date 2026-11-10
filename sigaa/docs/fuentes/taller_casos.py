from taller_comun import *

def caso_portada(B, modulo, usuario, color_txt, *extra):
    B.append({'t': 'cover', 'title': f'Casos resueltos — {modulo}', 'sub': 'Dos casos completos, paso a paso, para el taller de capacitación', 'logos': LOGOS,
              'lines': [f'**Taller:** {TALLER.capitalize()}', f'**Organiza:** {AGAM_C} · **Facilita:** {GMC_C}', f'**Usuario del aplicativo para este módulo:** `{usuario}` ({color_txt})', *extra,
                        '**Cómo usar este documento:** el facilitador proyecta cada caso; usted lo repite en su computadora siguiendo los pasos. Los resultados indicados deben coincidir con los de su pantalla.']})

def cuerpo_caso(B, f, num, titulo, situacion, logro, datos, pasos, verif, preguntas, errores):
    f['h1'](f'Caso {num}: {titulo}', True)
    f['h2']('Situación')
    f['p'](situacion)
    f['h2']('Lo que debe lograr')
    f['ul'](*logro)
    if datos:
        f['h2']('Datos del caso')
        for t in datos: f['table'](*t)
    f['h2']('Solución paso a paso')
    for bloque in pasos:
        kind = bloque[0]
        if kind == 'h': f['h2'](bloque[1])
        elif kind == 'ol': f['ol'](*bloque[1])
        elif kind == 'img': f['img'](bloque[1], bloque[2])
        elif kind == 'ok': f['note'](bloque[1], 'ok', 'Resultado esperado')
        elif kind == 'note': f['note'](bloque[1], bloque[2] if len(bloque) > 2 else '', bloque[3] if len(bloque) > 3 else '')
        elif kind == 'p': f['p'](bloque[1])
    f['h2']('Verificación')
    f['table'](['N.º', 'Compruebe que…', 'Resultado'], [[str(i + 1), t, '☐ ✔   ☐ ✘'] for i, t in enumerate(verif)])
    f['h2']('Preguntas de refuerzo y respuestas')
    f['table'](['Pregunta', 'Respuesta'], preguntas)
    f['h2']('Errores frecuentes')
    f['table'](['Si aparece…', 'Qué hacer'], errores)

# ═════════════════════════ ALMACENES
B, f = nuevo()
caso_portada(B, 'Administración de Almacenes', 'almacen', 'rol Administración de Almacenes, color azul',
             '**Casos:** (1) compra, ingreso y entrega de material de escritorio; (2) control de existencias: reposición e inventario físico.')
f['h1']('Antes de comenzar')
f['ol']('Abra el aplicativo SIGAA e ingrese con el usuario `almacen` (la primera vez pide cambiar la clave).', 'En el menú de la izquierda, bajo **ALMACENES**, están las pantallas que usaremos: Ingresos (CGI), Salidas (vales), Existencias y kardex, Reposición e Inventario físico.',
        'Bodega de trabajo: **BODEGA PAPELERÍA Y ÚTILES DE ESCRITORIO**. Moneda: bolivianos (Bs).')
f['note']('Los números de documento (CGI-0009/2026, VS-0008/2026…) son los que da el sistema en la base de demostración del taller. Si su pantalla muestra otro número, use el suyo: lo importante son los importes y los saldos.', 'warn', 'Números de documento')
cuerpo_caso(B, f, 1, 'Compra de bolígrafos, ingreso al almacén y entrega de papel',
    'La Secretaría Municipal Administrativa y Financiera compró **100 bolígrafos azules** a la librería El Altiplano (orden de compra OC-045/2026, factura FAC-1520). El almacén debe **registrar el ingreso con su respaldo**. Luego la Unidad de Educación pide **5 resmas de papel bond carta** y el almacén las **entrega** descontando por lotes. Al final se verifica todo en el **kardex**.',
    ['Registrar y confirmar el ingreso (CGI) con la documentación de respaldo.', 'Atender un pedido con aprobación del inmediato superior y obtener el vale de salida.', 'Leer el kardex y comprobar los saldos.'],
    [(['Campo en pantalla', 'Dato'], [['Bodega', 'BODEGA PAPELERÍA Y ÚTILES DE ESCRITORIO'], ['Tipo de ingreso', 'COMPRA (ORDEN DE COMPRA / CONTRATO)'], ['Proveedor', 'LIBRERÍA Y PAPELERÍA EL ALTIPLANO S.R.L.'], ['Nº orden de compra', 'OC-045/2026'], ['Factura', 'FAC-1520'], ['Unidad solicitante', 'SECRETARÍA MUNICIPAL ADMINISTRATIVA Y FINANCIERA'], ['Apertura / destino', 'La primera de la lista'], ['Comisión de recepción', 'LIC. ROSA MARÍA CHOQUE TICONA (el **Cargo** se completa solo)'], ['Ítem', '1-2-0000001 BOLÍGRAFO AZUL PUNTA MEDIA — cantidad 100 — precio Bs 1,50']]),
     (['Pedido', 'Dato'], [['Solicitante', 'ANA MARÍA QUISPE LIMACHI (cargo y unidad se llenan solos)'], ['Inmediato superior', 'LIC. ROSA MARÍA CHOQUE TICONA'], ['Apertura / destino', 'La primera de la lista'], ['Justificación', 'Material de escritorio para trabajo administrativo del mes'], ['Material', '1-1-0000001 PAPEL BOND CARTA 75 G — cantidad 5']])],
    [('h', 'Parte A · Ingreso con CGI'),
     ('ol', ['Menú **Ingresos (CGI)**. A la izquierda está la lista de ingresos ya registrados; a la derecha, el formulario **Nuevo ingreso**.', 'Elija bodega, tipo de ingreso y proveedor de las listas, y escriba la orden de compra y la factura.', 'Elija la **Apertura / destino** y, en **Comisión / responsable de recepción**, a LIC. ROSA MARÍA CHOQUE TICONA: el campo **Cargo** se llena solo.', 'En **Detalle de bienes recibidos**, escriba `1-2-0000001`, elija el bolígrafo, cantidad 100 y precio 1.5. Arriba verá **Total: Bs 150,00**.', 'En **Documentación de respaldo** marque todas las casillas (las que tienen (*) son obligatorias para confirmar).', 'Pulse **Guardar**.']),
     ('img', 'n_A1_form.jpg', 'Formulario del ingreso completo antes de guardar.'),
     ('img', 'n_A1_ok.jpg', 'Ingreso guardado: estado REGISTRADO.'),
     ('ol', ['Pulse el botón verde **Confirmar ingreso** y acepte la ventana de confirmación.', 'Pulse **Imprimir CGI** para ver el documento con los firmantes.']),
     ('img', 'n_A1_conf.jpg', 'Ingreso confirmado: las existencias ya están disponibles.'),
     ('ok', 'Mensaje «Ingreso confirmado: existencias disponibles». Total **Bs 150,00**, estado **INGRESADO**, y el PDF del CGI (con la Apertura / destino y el cargo de la comisión).'),
     ('h', 'Parte B · Pedido y entrega con vale de salida'),
     ('ol', ['Menú **Salidas (vales)**. Deje la fecha de hoy.', 'Elija la bodega y el solicitante: el **cargo** y la **unidad** se completan solos.', 'Elija el inmediato superior, la apertura/destino y escriba la justificación.', 'En **Materiales** escriba `1-1-0000001`, elija el papel y cantidad **5**. Después de guardar, la columna **Saldo** mostrará lo que hay (70).', 'Pulse **Guardar pedido**: queda en estado PEDIDO.', 'Pulse **Aprobar y entregar** y acepte. (En el trabajo real son dos pasos: aprobar cuando el superior firma el Vo.Bo., y luego entregar.)', 'Pulse **Imprimir vale**.']),
     ('img', 'n_A2_form.jpg', 'Pedido listo para guardar.'),
     ('img', 'n_A2_ok.jpg', 'Pedido entregado: Bs 190,00.'),
     ('ok', '«Entrega registrada por **Bs 190,00**. Las existencias se descargaron por PEPS.» (5 resmas × Bs 38). Estado **ENTREGADO**. El saldo del papel carta baja de 70 a **65**.'),
     ('h', 'Parte C · Verificación en el kardex'),
     ('ol', ['Menú **Existencias y kardex**. Bodega: BODEGA PAPELERÍA Y ÚTILES DE ESCRITORIO. Ítem: `1-2-0000001` (bolígrafo).', 'Revise cada fila: fecha, documento, entrada, salida, saldo y precio promedio.']),
     ('img', 't_A5_1.jpg', 'Kardex valorado del bolígrafo.'),
     ('ok', 'El kardex termina con saldo **386** (Bs 585,00); la última fila es el ingreso CGI-0009/2026 (+100). Debajo, **Lotes con saldo**: 226, 60 y 100 unidades; sale primero el lote más antiguo (PEPS).')],
    ['El CGI está CONFIRMADO (estado INGRESADO) y se imprimió con la apertura y el cargo.', 'El vale de salida es de Bs 190,00 y el estado es ENTREGADO.', 'El saldo del papel carta bajó de 70 a 65.', 'El kardex del bolígrafo termina en 386 unidades.'],
    [['¿Por qué el sistema pide documentos de respaldo antes de confirmar?', 'Porque el ingreso debe quedar respaldado según el manual de procedimientos; sin los documentos obligatorios no se confirma.'], ['¿Qué significa PEPS?', 'Primero en entrar, primero en salir: se entrega primero lo que ingresó (o vence) antes.'], ['¿Quién debe firmar antes de entregar?', 'El inmediato superior del solicitante (Vo.Bo.).']],
    [['«Seleccione la unidad solicitante» (o similar)', 'Falta un campo obligatorio: complételo y guarde de nuevo.'], ['«El pedido no cumple las reglas del Manual…»', 'El pedido está fuera del plazo (días 1 al 25) o supera el máximo del mes; registre quién autoriza la excepción.'], ['No puedo confirmar el ingreso', 'Falta marcar un documento de respaldo obligatorio (*).']])
cuerpo_caso(B, f, 2, 'Control de existencias: reposición por stock mínimo e inventario físico',
    'Al cierre del mes el responsable del almacén debe **reponer** lo que está por acabarse y **verificar físicamente** que lo registrado coincide con lo que hay en estantería. Primero genera el **requerimiento de compra** de los materiales bajo el stock mínimo. Luego un funcionario designado hace un **inventario con conteo ciego** (sin ver el saldo del sistema) y el sistema calcula **faltantes y sobrantes**.',
    ['Generar un requerimiento de compra desde el stock mínimo.', 'Realizar un inventario físico con conteo ciego y cerrarlo.', 'Interpretar el acta y decidir qué hacer con los faltantes y los sobrantes.'],
    [(['Dato', 'Valor'], [['Reposición — bodega', 'Todas (deje «— seleccione —»)'], ['Justificación', 'Reposición de existencias bajo el stock mínimo'], ['Inventario — tipo', 'PROGRAMADO'], ['Funcionario designado', 'TÉC. MARIO CONDORI QUISPE'], ['Observador', 'LIC. ROSA MARÍA CHOQUE TICONA']]),
     (['Material', 'Conteo físico'], [['PAPEL BOND CARTA 75 G', '63'], ['PAPEL BOND OFICIO 75 G', '40'], ['CARTULINA ESCOLAR DE COLORES', '14'], ['BOLÍGRAFO AZUL PUNTA MEDIA', '388'], ['LÁPIZ NEGRO HB', '120'], ['FOLDER MANILA TAMAÑO OFICIO', '350'], ['GRAPAS 26/6', '30'], ['CINTA ADHESIVA 48 MM', '21'], ['MARCADOR ACRÍLICO PERMANENTE NEGRO', '7'], ['TÓNER HP 85A NEGRO', '6'], ['TINTA EPSON 664 NEGRO', '10']])],
    [('h', 'Parte A · Reposición por stock mínimo'),
     ('ol', ['Menú **Reposición**. Deje la bodega en «— seleccione —» y pulse **Calcular reposición**.', 'Revise la tabla: material, stock, mínimo, máximo, **sugerido** (máximo menos stock), precio de referencia e importe. Puede cambiar la columna **A solicitar**.', 'Escriba la justificación y deje el tipo PREVISTO - REPOSICIÓN DE STOCK.', 'Pulse **Guardar requerimiento** e **Imprimir**.']),
     ('img', 't_A6_1.jpg', 'Requerimiento de compra calculado por el sistema.'),
     ('ok', 'Dos materiales en la lista: MARCADOR ACRÍLICO (stock 7, mínimo 12, sugerido 53) y AMOXICILINA 500 MG (stock 0, mínimo 300, sugerido 2000). **Total estimado Bs 1.865,00**.'),
     ('h', 'Parte B · Inventario físico con conteo ciego'),
     ('ol', ['Menú **Inventario físico** → **Nuevo inventario**. Bodega, tipo PROGRAMADO, funcionario designado y observador según los datos. Pulse **Abrir inventario**.', 'Aparece «Inventario abierto con 14 ítems» y un aviso de **conteo ciego**: no se ve el saldo del sistema.', 'En la columna **Conteo físico** escriba los números de la tabla de datos.', 'Pulse **Guardar conteo** y luego **Cerrar inventario** → Aceptar.']),
     ('img', 't_A8_2.jpg', 'Conteo físico ingresado (conteo ciego).'),
     ('img', 't_A8_3.jpg', 'Inventario cerrado: el sistema muestra faltantes y sobrantes.'),
     ('ok', '«Inventario cerrado. **Faltantes Bs 76,00 · Sobrantes Bs 3,03**». El papel carta tenía 65 y se contaron 63 (faltan 2 resmas × Bs 38 = Bs 76). Los bolígrafos tenían 386 y se contaron 388 (sobran 2 × Bs 1,515 = Bs 3,03).'),
     ('img', 't_A8_4.jpg', 'Acta de inventario.'),
     ('h', 'Parte C · Qué hacer con las diferencias'),
     ('ol', ['Sobrantes: pulse **Ingresar sobrantes** → se crea un ingreso por ajuste que se completa y se confirma.', 'Faltantes: según el Manual, primero se pide la **reposición** (botón **Acta de reposición**); solo si no se repone se crea el expediente de baja con **Baja por faltantes** y se determina responsabilidad.']),
     ('img', 't_A9_1.jpg', 'Expediente de baja creado desde el inventario.')],
    ['El requerimiento muestra dos materiales y un total estimado de Bs 1.865,00.', 'El inventario cerró con faltantes de Bs 76,00 y sobrantes de Bs 3,03.', 'Se imprimió el acta de inventario.', 'Se identificó qué botón corresponde a sobrantes y cuál a faltantes.'],
    [['¿Por qué el conteo es «ciego»?', 'Para que quien cuenta no se influya por el saldo del sistema y el conteo sea independiente.'], ['¿Cómo se calcula la cantidad sugerida de reposición?', 'Máximo menos stock actual.'], ['¿Qué se hace primero con un faltante?', 'Pedir su reposición; solo si no se repone, se tramita la baja y se determina responsabilidad.']],
    [['Los saldos no coinciden con la tabla', 'Haga el Caso 1 antes del Caso 2: el inventario parte de las existencias que dejó el Caso 1.'], ['No puedo cerrar el inventario', 'Falta guardar el conteo de algún ítem o hay una cantidad vacía.']])
guardar('c_alm', B, 'capacitacion/05a_Casos_Resueltos_Almacenes')

# ═════════════════════════ COMBUSTIBLE
B, f = nuevo()
caso_portada(B, 'Administración de Combustible', 'combustible', 'rol Administración de Combustible, color bronce',
             '**Casos:** (1) ciclo completo del vale: recepción, emisión con QR y descargo; (2) conciliación con la estación de servicio.')
f['h1']('Antes de comenzar')
f['ol']('Ingrese con el usuario `combustible` (la primera vez pide cambiar la clave).', 'En el menú, bajo **COMBUSTIBLE**: Recepción de vales, Emitir vales, **Vales emitidos**, Descargo de vales, Conciliación y otras.', 'Contrato de trabajo: **GAMC-CONT-001/2026 · Gasolina (prepago)** con la ESTACIÓN DE SERVICIO EL ALTO SRL. Vehículo: **2345ABC · Vagoneta Toyota Land Cruiser** (uso Ejecutivo).')
f['note']('El combustible se maneja con **vales** que el municipio compra a la estación de servicio. Se reciben al almacén, se **emiten** a un vehículo, el conductor los usa y presenta su **descargo** (bitácora). A fin de mes se **concilia** con lo que cobra la estación.', '', 'Idea del módulo')
cuerpo_caso(B, f, 1, 'Ciclo completo del vale: recepción, emisión con QR y descargo',
    'El municipio recibe de la estación **30 vales** (20 de Bs 50 y 10 de Bs 100) con la factura FAC-2051. El Alcalde viaja a La Paz en la vagoneta del Ejecutivo del **lunes 2 al miércoles 4 de noviembre**: el almacén emite **3 vales de Bs 100**. A su regreso el conductor presenta su **descargo**: usó 1 vale y recorrió 120 km; los otros 2 vales vuelven al almacén.',
    ['Registrar la recepción de vales y la nota de ingreso.', 'Emitir los vales verificando litros y máximo permitido; ver el vale con su código QR.', 'Registrar el descargo con la bitácora y comprobar el rendimiento.'],
    [(['Paso', 'Datos'], [['Recepción', 'Contrato GAMC-CONT-001/2026 · Factura FAC-2051 · Fila 1: corte Bs 50, vales 1001 a 1020 · Fila 2: corte Bs 100, vales 2001 a 2010'], ['Emisión', 'Destino VEHICULO · Placa 2345ABC · Km 45230 · Conductor JOSÉ LUIS MAMANI CHOQUE · Solicitante ING. EDGAR NINA CALLISAYA (Alcalde Municipal) · Unidad DESPACHO DEL EJECUTIVO MUNICIPAL · Apertura 00 0 001 · Utilización del lunes 2 al miércoles 4 · Trabajo: viaje oficial a La Paz · 3 vales de Bs 100'], ['Descargo', 'Emisión VC-0001/2026 · Ruta Calamarca - La Paz - Calamarca · Lectura 45230 → 45350 · Vale 2001 · 14,37 litros · Factura FAC-8841']])],
    [('h', 'Parte A · Recepción de vales'),
     ('ol', ['Menú **Recepción de vales**. Elija el contrato: aparece un cuadro azul con el proveedor, la modalidad y el saldo del contrato (Bs 200.000,00).', 'Escriba la factura. En «Vales recibidos» elija el corte y el rango de numeración; pulse **+ Agregar línea** para la segunda fila. Arriba verá «30 vales · Bs 2.000,00».', 'Pulse **Registrar ingreso a almacén**.']),
     ('img', 't_C1_1.jpg', 'Recepción llena antes de registrar.'),
     ('ok', '«Ingreso **IV-0001/2026** registrado: 30 vales por **Bs 2.000,00**» y se abre la nota de ingreso en PDF. Un número de vale no se puede repetir para el mismo proveedor.'),
     ('h', 'Parte B · Emisión con solicitud y vale (QR)'),
     ('ol', ['Menú **Emitir vales**. Elija el vehículo: aparece un cuadro con sus datos (Gasolina, uso Ejecutivo, tanque 90 L). El conductor se llena solo.', 'Complete solicitante, unidad, apertura programática, periodo de utilización y trabajo a realizar.', 'En «3. Vales a entregar» escriba **3** en «Vales de Bs 100». Los tres cuadros muestran **Bs 300,00**, **43,10 L** y **Máximo permitido 48,00 L**.', 'Pulse **Emitir vales e imprimir**.']),
     ('img', 't_C2_1.jpg', 'Emisión lista: monto, litros y máximo permitido.'),
     ('ok', '«Emisión registrada: **VC-0001/2026** — Bs 100 x 3: 2001-2003». 43,10 L ≤ 48 L (16 litros por día, de lunes a miércoles). Se abren el **vale** y la planilla de descargo en blanco.'),
     ('p', 'En la segunda hoja del vale aparece el recuadro **«Datos de verificación (QR)»**: al escanearlo se leen el Nº de solicitud, la cantidad de vales a entregar y el monto total.'),
     ('img', 'n_C2_vale_qr.jpg', 'Vale de combustible (Anexo 2) con su código QR de verificación.'),
     ('h', 'Parte C · Descargo (Anexo 3)'),
     ('ol', ['Menú **Descargo de vales**. En Nº de emisión elija **VC-0001/2026**: un cuadro resume los vales entregados (2001-2003).', 'En la bitácora llene la fila con los datos del caso. Deje marcada la casilla **«Devolver automáticamente al almacén los vales no utilizados»**.', 'Pulse **Registrar descargo**.']),
     ('img', 't_C4_1.jpg', 'Bitácora de recorrido llena.'),
     ('ok', '«Descargo **DS-0001/2026** registrado (**Conforme**)». Rendimiento: 14,37 L ÷ 120 km = **0,12 L/km**, igual al de referencia del vehículo. Los vales 2002 y 2003 vuelven al almacén.'),
     ('h', 'Parte D · Consulta en «Vales emitidos»'),
     ('ol', ['Menú **Vales emitidos**: una fila por solicitud, con vales, monto, litros y estado.', 'Pulse la fila para ver cada vale y reimprimir el vale con QR.']),
     ('img', 'n_C_emit.jpg', 'Visor de vales emitidos: la emisión VC-0001/2026, ya descargada.')],
    ['La nota de ingreso IV-0001/2026 muestra 30 vales por Bs 2.000,00.', 'La emisión VC-0001/2026 es de Bs 300,00 y 43,10 L (máximo 48 L).', 'El vale impreso trae el recuadro con QR.', 'El descargo DS-0001/2026 es Conforme con 0,12 L/km.', 'En «Vales emitidos» la emisión figura como Descargado.'],
    [['¿Qué evita el límite de litros por vehículo?', 'Que se entregue más combustible del permitido para el periodo (16 L por día en uso ejecutivo).'], ['¿Qué pasa con los vales que no se usaron?', 'Con la casilla marcada, vuelven automáticamente al almacén como disponibles.'], ['¿Para qué sirve el QR del vale?', 'Para verificar rápidamente el Nº de solicitud, la cantidad de vales y el monto.']],
    [['«La licencia del conductor está VENCIDA»', 'No se puede emitir: elija otro conductor o actualice la licencia en Catálogos.'], ['«Los litros equivalentes superan el máximo permitido»', 'Reduzca los vales o escriba la justificación del excedente.'], ['El descargo queda OBSERVADO', 'El consumo se aleja más de 20 % del rendimiento del vehículo: revise la bitácora.']])
cuerpo_caso(B, f, 2, 'Conciliación con la estación de servicio',
    'A fin de mes la estación presenta su cobro con **3 vales por Bs 300**: el 2001, el 2002 y el 9999. El responsable debe **comparar** lo cobrado con lo que el sistema tiene entregado y descargado, **pagar solo lo conforme** y dejar las observaciones por escrito.',
    ['Conciliar el detalle de la estación con el sistema.', 'Interpretar los resultados: conforme, no entregado y no registrado.', 'Decidir el monto a pagar y qué hacer con los observados.'],
    [(['Dato', 'Valor'], [['Proveedor', 'ESTACIÓN DE SERVICIO EL ALTO SRL'], ['Periodo', 'Del 01/11/2026 al 30/11/2026']]),
     (['Línea para pegar en «Vales cobrados» (separadas por punto y coma)'], [['2001;04/11/2026;2345ABC;14.37;100;FAC-8841'], ['2002;04/11/2026;2345ABC;14.37;100;FAC-8842'], ['9999;04/11/2026;3456BCD;10;100;FAC-8843']])],
    [('ol', ['Menú **Conciliación**. Elija el proveedor y el periodo.', 'Pegue las 3 líneas en el cuadro (también puede copiar desde un Excel o cargar un archivo .xlsx/.csv). Debajo debe decir «**Se reconocen 3 vale(s) por Bs 300,00**»: compárelo con la factura de la estación.', 'Pulse **Conciliar**. Se registra la conciliación y se abre el PDF para firma.']),
     ('img', 'n_C7_form.jpg', 'Detalle del proveedor pegado, antes de conciliar.'),
     ('img', 'n_C7_ok.jpg', 'Resultado de la conciliación.'),
     ('ok', 'Resultado **CC-0001/2026**: **1 conforme** (vale 2001, **Bs 100,00 a pagar**) y **2 observados**: NO ENTREGADO (vale 2002: se devolvió al almacén, la estación no debió cobrarlo) y NO REGISTRADO (vale 9999: no existe en el sistema).'),
     ('img', 'n_C7_pdf.jpg', 'Documento de conciliación para firma.'),
     ('h', 'Qué hacer con cada resultado'),
     ('p', '**CONFORME:** se paga. **NO ENTREGADO:** el vale figura en el almacén; es posible uso indebido: se investiga y no se paga. **NO REGISTRADO:** el número no existe: se verifica si hubo error de digitación o vale falso; no se paga. Otros resultados posibles: MONTO DIFERENTE, PLACA DIFERENTE, SIN DESCARGO, DUPLICADO, YA CONCILIADO y DADO DE BAJA.'),
     ('note', 'Se paga **solo lo conforme**: de los Bs 300 cobrados se pagan Bs 100. El resto queda observado hasta que la estación lo aclare por escrito.', 'ok', 'Regla de oro')],
    ['El cuadro reconoce 3 vales por Bs 300,00.', 'La conciliación CC-0001/2026 muestra 1 conforme y 2 observados.', 'El monto a pagar es Bs 100,00.', 'Se imprimió el PDF de conciliación.'],
    [['¿Por qué el vale 2002 sale «NO ENTREGADO» si lo usaron?', 'Porque en este caso el conductor no lo usó: se devolvió al almacén con el descargo; la estación no debió recibirlo.'], ['¿Se puede volver a conciliar un vale conforme?', 'No: queda marcado con el número de conciliación y aparecería «YA CONCILIADO».'], ['¿Quién firma el documento de conciliación?', 'El responsable de combustible y quien autoriza el pago.']],
    [['«Se reconocen 0 vale(s)»', 'Revise el formato de las líneas: Nº de vale; fecha; placa; litros; monto; factura, separados por punto y coma.'], ['Todos salen «SIN DESCARGO»', 'Falta registrar los descargos del periodo (Caso 1, parte C).']])
guardar('c_com', B, 'capacitacion/05b_Casos_Resueltos_Combustible')

# ═════════════════════════ ACTIVOS FIJOS
B, f = nuevo()
caso_portada(B, 'Administración de Activos Fijos', 'activos', 'rol Administración de Activos Fijos, color verde',
             '**Casos:** (1) del ingreso a la asignación con etiquetas QR; (2) lote de pupitres: copia de ficha, importación desde Excel con fotos y envío al VSIAF.')
f['h1']('Antes de comenzar')
f['ol']('Ingrese con el usuario `activos` (la primera vez pide cambiar la clave).', 'Bajo **ACTIVOS FIJOS**: Ingreso a almacén, Codificación, Fichas técnicas, Solicitudes, Asignación y entrega, Etiquetas, Consulta y kardex, Importar desde Excel, Enviar al VSIAF e Importar desde el VSIAF.')
f['note']('El **VSIAF** es el sistema oficial del registro contable de activos fijos (con depreciación y actualización). El aplicativo lo **complementa**: lleva el control diario —código, ficha, fotografía, responsable, ubicación, etiqueta— y le **envía** los activos sin volver a digitarlos.', '', 'Cómo se relacionan')
cuerpo_caso(B, f, 1, 'Del ingreso a la asignación, con etiquetas QR',
    'La Unidad de Contabilidad compró **2 escritorios y 1 laptop** (orden de compra OC-050/2026). El responsable de activos fijos debe **ingresarlos**, darles su **código único**, completar la **ficha técnica con fotografía**, atender la **solicitud** del funcionario Edwin Tony Chuca y **asignarle los dos escritorios con acta**. Por último imprime las **etiquetas con código QR**.',
    ['Registrar el ingreso con su acta de conformidad.', 'Codificar los activos y completar la ficha técnica con fotografía.', 'Asignar con acta y emitir las etiquetas con QR.'],
    [(['Línea', 'Cuenta contable', 'Auxiliar', 'Descripción', 'Cant.', 'P. unit. Bs'], [['1', '03 - Equipo de Oficina y Muebles', '001 - ESCRITORIO', 'Escritorio de melamina 1.20 x 0.60 m con cajonera', '2', '1.200'], ['2', '04 - Equipo de Computación', '032 - LAPTOP', 'Laptop Lenovo ThinkPad 14 pulgadas, 16 GB RAM', '1', '6.500']]),
     (['Dato', 'Valor'], [['Tipo de ingreso', 'ORDEN DE COMPRA — OC-050/2026 — factura 1550'], ['Proveedor', 'COMERCIAL MUEBLES ANDINOS S.R.L. (DEMO)'], ['Comisión de recepción', 'EDWIN TONY CHUCA ORDOÑEZ / LIC. ROSA MARÍA CHOQUE TICONA'], ['Unidad', 'UNIDAD DE CONTABILIDAD'], ['Edificio de destino', '009 - UNIDAD DE CONTABILIDAD']])],
    [('h', 'Parte A · Ingreso a almacén'),
     ('ol', ['Menú **Ingreso a almacén**. Llene los datos y las dos líneas de activos (use **+ Agregar línea**).', 'Pulse **Guardar ingreso**. Luego **Acta de conformidad** y **Formulario de ingreso** para ver los documentos.']),
     ('img', 't_F1_1.jpg', 'Ingreso de activos antes de guardar.'),
     ('ok', '«Ingreso **ING-0005/2026** guardado (**Bs 8.900,00**). Siguiente paso: Codificación.» (2 × 1.200 + 6.500).'),
     ('h', 'Parte B · Codificación'),
     ('ol', ['Menú **Codificación**. En «Ingreso a codificar» elija ING-0005/2026; estado físico inicial **Nuevo**.', 'En la columna **Edificio** elija 009 - UNIDAD DE CONTABILIDAD en las dos filas; deje el ambiente vacío (queda «sin asignar»).', 'Pulse **Generar códigos**.']),
     ('img', 't_F2_2.jpg', 'Códigos generados.'),
     ('ok', 'Se generan 3 códigos: `009-00-03001-01` y `009-00-03001-02` (escritorios) y `009-00-04032-01` (laptop). Formato EEE-AA-CCXXX-NN: edificio – ambiente – cuenta + auxiliar – correlativo.'),
     ('h', 'Parte C · Ficha técnica con fotografía'),
     ('ol', ['Menú **Fichas técnicas**. Busque `009-00-04032-01` y haga clic.', 'Marca **Lenovo**, Modelo **ThinkPad T14**, Serie **PF3K8L2M**, Color **Negro**; complete las características de la cuenta.', 'En **Registro fotográfico** pulse **Subir** en «Foto 1» y elija una imagen JPG o PNG (hasta 4 fotos).', 'Pulse **Guardar ficha**.']),
     ('img', 't_F3_1.jpg', 'Ficha técnica completa.'),
     ('h', 'Parte D · Solicitud y asignación con acta'),
     ('ol', ['Menú **Solicitudes**: Edwin Tony Chuca Ordoñez pide 2 escritorios (cuenta 03, auxiliar 001). El **saldo en almacén** se muestra al elegir la línea. Pulse **Guardar solicitud** (SOL-0006/2026).', 'En la solicitud pulse **Atender (asignar activos)**. Elija edificio 009 y ambiente 01 - OFICINA DE CONTABILIDAD.', 'Pulse **Mostrar activos disponibles**, luego **Desmarcar** y marque solo `009-00-03001-01` y `009-00-03001-02` (título: «2 marcado(s) · Bs 2.400,00»).', 'Pulse **Generar asignación e imprimir acta**.']),
     ('img', 't_F5_2.jpg', 'Selección correcta: los dos escritorios nuevos.'),
     ('img', 't_F5_3.jpg', 'Acta de asignación para firma.'),
     ('ok', '«Acta **ASG-0004/2026**: 2 activos por **Bs 2.400,00**». La solicitud pasa a ATENDIDA. Atención: el sistema propone los activos más antiguos, pero **usted decide** cuáles se entregan.'),
     ('h', 'Parte E · Etiquetas con código QR'),
     ('ol', ['Menú **Etiquetas (stickers)**. Edificio 009; deje marcada «Solo pendientes de impresión»; **Marcar todo**.', 'Pulse **Generar stickers (3)**. Se abre la hoja carta de 30 etiquetas (3 × 10).']),
     ('img', 'stickers_nuevo.jpg', 'Etiquetas: entidad, edificio, auxiliar, código y QR (el QR contiene esas cuatro líneas).'),
     ('ok', 'Cada etiqueta lleva la entidad, el edificio, el auxiliar contable, el código y un **QR**; al escanearlo se leen esas cuatro líneas. Los textos largos se ajustan solos para no superponerse.')],
    ['El ingreso ING-0005/2026 es de Bs 8.900,00.', 'Se generaron 3 códigos (2 escritorios y 1 laptop).', 'La ficha de la laptop tiene marca, modelo, serie, color y foto.', 'El acta ASG-0004/2026 es de 2 activos por Bs 2.400,00 y la solicitud está ATENDIDA.', 'Las etiquetas se imprimieron y el QR se lee con el celular.'],
    [['¿Qué significa cada parte del código 009-00-03001-01?', 'Edificio 009, ambiente 00 (sin asignar), cuenta 03 + auxiliar 001, correlativo 01.'], ['¿Por qué el código tiene 15 caracteres?', 'Es el límite del VSIAF; así el mismo código sirve en ambos sistemas.'], ['¿Quién queda responsable del activo tras el acta?', 'El funcionario que lo recibe: aparece en su kardex y en la consulta.']],
    [['El sistema preselecciona activos de otro edificio', 'Pulse «Desmarcar» y marque solo los que corresponden: la preselección solo propone los más antiguos.'], ['No se imprimen las etiquetas en la versión de escritorio', 'Use la versión actualizada del instalador (corrige la apertura del PDF).']])
cuerpo_caso(B, f, 2, 'Lote de pupitres: copia de ficha, importación desde Excel y envío al VSIAF',
    'Se compraron **6 pupitres iguales** para la U.E. Carazani. Se llena la ficha de **uno** y se **copia a los otros cinco**. Además, el municipio tiene un **inventario antiguo en Excel** con fotografías que debe cargarse al sistema. Finalmente, los activos se **envían al VSIAF** con validación previa, respaldo y reversión.',
    ['Copiar la ficha técnica a varios activos iguales.', 'Importar un inventario desde Excel relacionando las fotografías de una carpeta.', 'Enviar activos al VSIAF: validar, importar y re-indexar.'],
    [(['Dato', 'Valor'], [['Lote', 'Cuenta 03 - Equipo de Oficina y Muebles · auxiliar 005 - MESA · 6 unidades · edificio 001 - U.E. CARAZANI'], ['Ficha', 'Marca CARPINTERÍA ORURO · Modelo P-2026 · Color CAFÉ · Madera de pino, 60 x 45 cm, barniz café, tablero abatible']]),
     (['codigo', 'descripcion', 'cuenta', 'auxiliar', 'edificio', 'ambiente', 'estado', 'valor', 'fecha_ingreso', 'foto1', 'foto2'], [['001-01-30121-0001', 'PUPITRE BIPERSONAL DE MADERA', '3', 'MESA', 'U.E. CARAZANI', 'AULA 2', 'Bueno', '350.5', '15/03/2024', 'pupitre_001.jpg', ''], ['(vacío)', 'PUPITRE UNIPERSONAL', '3', 'MESA', 'U.E. CARAZANI', 'AULA 2', 'Nuevo', '210', '(hoy)', 'pupitre_002.png', 'pupitre_003.jpg']])],
    [('h', 'Parte A · Copiar la ficha a los demás pupitres'),
     ('ol', ['Menú **Fichas técnicas**. Busque el primer código del lote y haga clic.', 'Llene Marca, Modelo, Color y las características técnicas; **Guardar ficha**.', 'Pulse **Copiar esta ficha a otros activos…**. Quedan marcados por defecto: marca, modelo, color, características y observaciones (no la serie, el valor ni las fotos).', 'Elija **Solo completar lo que esté vacío**, pulse **Marcar los del mismo ingreso** (se marcan los otros 5) y **Copiar a 5 activo(s)**.']),
     ('img', 't_F9_2.jpg', 'Ventana de copia: datos a copiar y activos marcados.'),
     ('img', 't_F9_3.jpg', 'Copia realizada.'),
     ('ok', '«Ficha copiada a 5 activo(s).» Cada pupitre ya tiene marca, modelo, color y características; la **serie** queda vacía porque es propia de cada bien.'),
     ('h', 'Parte B · Importar un inventario existente desde Excel con fotos'),
     ('ol', ['Menú **Importar desde Excel**. Pulse **Descargar plantilla de Excel**: trae las columnas, un ejemplo y la hoja CATALOGOS con los valores válidos.', 'Llene la hoja DATOS con los activos del caso (arriba). En `foto1`, `foto2` y `foto3` va **solo el nombre del archivo** de la foto.', 'Pulse **Seleccionar Excel…** y elija el libro; pulse **Seleccionar carpeta de fotos…** y elija la carpeta con las imágenes.', 'Pulse **Validar (no guarda nada)**: indica errores por fila y las fotos que **faltan** en la carpeta.', 'Con el Excel correcto pulse **Importar**. El sistema crea los activos y sube las fotografías.']),
     ('img', 'af_importar_1.jpg', 'Estructura del Excel y selección de archivos.'),
     ('img', 'af_importar_2.jpg', 'Resultado: activos importados y fotos subidas.'),
     ('ok', '«Se importaron **2 activo(s)**». El primero conserva su código `001-01-30121-0001`; el segundo recibe uno generado. Si una foto nombrada no está en la carpeta (aquí `pupitre_003.jpg`), el activo se crea y se avisa cuál falta.'),
     ('h', 'Parte C · Enviar al VSIAF'),
     ('ol', ['Menú **Enviar al VSIAF**. **1. Destino:** escriba la carpeta del VSIAF (`C:\\vsiaf`), la unidad y pulse **Guardar y comprobar**.', '**2. Selección:** busque los pendientes y marque los activos a enviar; elija si entran ELABORADOS (recomendado) o APROBADOS.', '**3. Equivalencias:** pulse «Revisar lo que falta» y complete (por ejemplo el organismo financiador de 3 dígitos).', '**4. Validar:** pulse «Validar y calcular»: no escribe nada y muestra errores, avisos y el cálculo por grupo contable.', '**5. Importar:** confirme. Se hace un **respaldo** del VSIAF antes de escribir y, si algo falla, se **restaura**.']),
     ('img', 'v_validar.jpg', 'Vista previa de la validación con el cálculo por grupo contable.'),
     ('img', 'v_fin.jpg', 'Importación realizada: lote, respaldo e historial.'),
     ('note', 'Después de importar: abra el **VSIAF → Administradores → Re-indexar**, revise el Reporte 6 y **apruebe** los activos ELABORADOS. Sin re-indexar, el VSIAF no verá los registros nuevos.', 'warn', 'Último paso obligatorio'),
     ('p', 'El administrador puede **reservar** esta función solo para administradores (Administración → Configuración → Activos fijos). También puede **traer** al aplicativo lo que ya está en el VSIAF con «Importar desde el VSIAF».')],
    ['Los 5 pupitres tienen la marca, el modelo, el color y las características del primero.', 'La importación creó 2 activos y avisó la foto faltante.', 'La validación del envío al VSIAF no muestra errores.', 'Después de importar se anotó el paso de Re-indexar y aprobar en el VSIAF.'],
    [['¿Por qué las fotos van en una carpeta y no dentro del Excel?', 'Porque el Excel solo guarda texto; las columnas foto1–foto3 relacionan cada fila con el archivo de la carpeta por su nombre.'], ['¿Por qué el envío importa los activos como ELABORADOS?', 'Porque en el VSIAF deben ser aprobados por el responsable; revalúo, transferencia y baja solo se hacen sobre activos aprobados.'], ['¿Qué pasa si la importación al VSIAF falla a la mitad?', 'El sistema restaura el respaldo: la base del VSIAF queda como estaba.']],
    [['«El VSIAF está abierto»', 'Ciérrelo en todas las computadoras y valide de nuevo.'], ['Faltan equivalencias', 'Complételas en el paso 3 (sobre todo el organismo financiador).'], ['«La cuenta … no existe» (Excel)', 'Use el número o el nombre tal como aparece en la hoja CATALOGOS.']])
B.append({'t': 'h1', 'x': 'Cierre del taller', 'pb': True})
B.append({'t': 'p', 'x': 'Con estos seis casos (dos por módulo) los participantes pueden repetir en su municipio los procesos de **almacenes**, **combustible** y **activos fijos**. Se recomienda archivar la hoja de verificación de cada caso y practicar con los datos propios del municipio antes de usar el sistema en producción.'})
guardar('c_af', B, 'capacitacion/05c_Casos_Resueltos_Activos_Fijos')
print('casos ok')
