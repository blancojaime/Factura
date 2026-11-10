from taller_comun import *

def hm(m): return f'{m // 60} h {m % 60:02d} min' if m % 60 else f'{m // 60} h'

def portada(B, titulo, sub, *lineas):
    B.append({'t': 'cover', 'title': titulo, 'sub': sub, 'logos': LOGOS, 'lines': list(lineas)})

# ───────────────────────── 3. TEMAS PARA CAPACITAR
B, f = nuevo()
portada(B, 'Temas para capacitar', 'Contenido de los tres módulos del taller',
        f'**Taller:** {TALLER.capitalize()}', f'**Dirigido a:** personal de los municipios miembros de {AGAM_C} ({PARTICIPANTES} participantes)', f'**Duración:** {HORAS} horas académicas en dos días', f'**Presenta:** {GMC}')
f['h1']('Resumen de los tres módulos')
f['table'](['Módulo', 'Tema', 'Duración', 'Casos resueltos'], [
    ['1', '**Administración de Almacenes**', '4 horas', '2'], ['2', '**Administración del Uso de Combustibles**', '4 horas', '2'], ['3', '**Administración de Activos Fijos complementarios al VSIAF**', '4 horas', '2'], ['', '**Total**', f'**{HORAS} horas**', '**6**']])
f['note']('Todos los módulos se desarrollan con el aplicativo SIGAA instalado en los equipos del taller y con **datos de demostración**, de modo que cada participante repite el caso en su propia computadora.', '', 'Metodología común')

f['h1']('a. Contenido de Administración de Almacenes', True)
f['p']('**Objetivo:** que el participante pueda registrar el ingreso, la salida y el control de los materiales de almacén, con respaldo documental y valoración correcta, y detectar a tiempo faltantes, sobrantes y reposiciones.')
f['p']('**Dirigido a:** responsables y auxiliares de almacén, personal de contrataciones, bienes y servicios y administrativo-financiero.')
f['table'](['Unidad', 'Contenido', 'Tiempo'], [
    ['1', '**Marco general.** Rol del almacén en el GAM; ciclo del material (compra → ingreso → custodia → salida → control → baja); referencia al Sistema de Administración de Bienes y Servicios (D.S. 0181); documentos que respaldan cada movimiento (CGI, vale, kardex, actas).', '40 min'],
    ['2', '**Catálogo y bodegas.** Códigos de ítems (grupo-subgrupo-correlativo), unidades de medida, stock mínimo y máximo, bodegas y responsables. Recorrido del aplicativo y roles de usuario.', '(incluido)'],
    ['3', '**Ingreso de bienes (CGI).** Registro con orden de compra y factura, apertura/destino, comisión de recepción con su cargo, documentación de respaldo obligatoria, confirmación del ingreso y kardex valorado por lotes.', '75 min'],
    ['4', '**Salidas.** Pedido del solicitante, plazo y máximo de pedidos del mes, Vo.Bo. del inmediato superior, aprobación y entrega con descarga PEPS (primero lo que vence o ingresó antes); pedido sin existencia.', '(Caso 1)'],
    ['5', '**Existencias y reposición.** Kardex por ítem, lotes con saldo, alertas de stock mínimo, requerimiento de compra automático y transferencias entre bodegas.', '75 min'],
    ['6', '**Control.** Inventario físico con conteo ciego, acta, sobrantes y faltantes, bajas por causal y su trámite, seguridad e higiene (extintores), reportes y cierre de gestión.', '(Caso 2)'],
    ['', '**Evaluación y cierre del módulo**', '15 min']])
f['h2']('Casos completos resueltos')
f['ul']('**Caso 1:** Compra de 100 bolígrafos, ingreso con CGI y entrega de 5 resmas de papel a una unidad solicitante; verificación en el kardex.', '**Caso 2:** Reposición por stock mínimo (requerimiento de compra) e inventario físico con conteo ciego, con cálculo de faltantes y sobrantes.')
f['h2']('Al terminar, el participante sabrá')
f['ul']('Registrar un ingreso con todos sus respaldos y confirmarlo.', 'Atender un pedido respetando los plazos y entregar con valoración PEPS.', 'Leer un kardex valorado y explicar un saldo.', 'Generar un requerimiento de compra y realizar un inventario con conteo ciego.')

f['h1']('b. Contenido de Administración de Combustible', True)
f['p']('**Objetivo:** que el participante pueda controlar el combustible desde la compra de vales hasta el pago a la estación de servicio, con límites por vehículo, descargo con bitácora y conciliación.')
f['p']('**Dirigido a:** responsables de combustible y de bienes y servicios, encargados de vehículos, conductores responsables y personal administrativo-financiero.')
f['table'](['Unidad', 'Contenido', 'Tiempo'], [
    ['1', '**Marco general.** Reglamento interno de uso de combustible; riesgos (uso indebido, rendimiento, falta de respaldo); ciclo del vale: compra → almacén → entrega → descargo → conciliación → pago.', '35 min'],
    ['2', '**Contratos y catálogos.** Contrato con la estación de servicio (prepago/posterior), precios, vales por corte (Bs 30, 50 y 100), parque automotor, conductores y licencias, rendimiento de referencia y apertura programática.', '(incluido)'],
    ['3', '**Recepción de vales.** Nota de ingreso, numeración sin repetición y control del saldo del contrato.', '80 min'],
    ['4', '**Emisión.** Solicitud (Anexo 1) y vale (Anexo 2) con código QR; cálculo de litros y máximo permitido; alertas y bloqueos (licencia vencida, descargos pendientes, stock de vales).', '(Caso 1)'],
    ['5', '**Descargo.** Bitácora de recorrido (Anexo 3), rendimiento por kilómetro, descargo conforme u observado, devolución automática de vales no usados. Turriles y viajes (visión general).', '(Caso 1)'],
    ['6', '**Conciliación y control.** Conciliación con la estación de servicio (conformes, monto a pagar y observados), visor de vales emitidos y tablero de control.', '80 min (Caso 2)'],
    ['', '**Evaluación y cierre del módulo**', '30 min']])
f['h2']('Casos completos resueltos')
f['ul']('**Caso 1:** Ciclo completo: recepción de 30 vales, emisión de 3 vales de Bs 100 a una vagoneta del Ejecutivo y descargo conforme del conductor.', '**Caso 2:** Conciliación de lo cobrado por la estación de servicio: pago de vales conformes y análisis de observados (no entregado, no registrado, monto diferente).')
f['h2']('Al terminar, el participante sabrá')
f['ul']('Recibir un lote de vales y emitir vales con el cálculo de litros permitido.', 'Registrar el descargo con la bitácora y entender el rendimiento.', 'Conciliar con la estación de servicio y pagar solo lo conforme.', 'Usar el visor de vales emitidos y el código QR para verificar.')

f['h1']('c. Contenido de Administración de Activos Fijos', True)
f['p']('**Objetivo:** que el participante pueda llevar el control operativo de los activos fijos del municipio —código, ficha, responsable, ubicación, fotografía y etiqueta— y conectarlo con el **VSIAF**, que es el sistema oficial del registro contable.')
f['p']('**Dirigido a:** responsables de activos fijos, contadores, personal de bienes y servicios y administrativo-financiero.')
f['table'](['Unidad', 'Contenido', 'Tiempo'], [
    ['1', '**Marco general.** Activos fijos en el GAM; qué hace el VSIAF (registro contable, depreciación y actualización) y qué complementa el aplicativo (control diario: ingreso, código, ficha, fotos, asignación, etiquetas, movimientos).', '35 min'],
    ['2', '**Ingreso y codificación.** Ingreso por orden de compra, memorándum de comisión, acta de conformidad; código único EEE-AA-CCXXX-NN (edificio, ambiente, cuenta + auxiliar, correlativo).', '70 min'],
    ['3', '**Ficha técnica y fotografías.** Datos del bien, características por cuenta, hasta 4 fotos; copia de la ficha a decenas de bienes iguales.', '(Caso 1)'],
    ['4', '**Solicitud, asignación y acta.** Atención de solicitudes, responsable del bien, devolución, transferencia y baja con resolución y motivo.', '(Caso 1)'],
    ['5', '**Etiquetas con QR y consulta.** Etiquetas con entidad, edificio, auxiliar y código; consulta y kardex del activo; reportes.', '(Caso 1)'],
    ['6', '**Inventarios existentes.** Importación desde Excel con carpeta de fotografías (columnas foto1, foto2, foto3).', '70 min'],
    ['7', '**Conexión con el VSIAF.** Enviar al VSIAF (validar, equivalencias, importar, re-indexar y aprobar), traer del VSIAF lo ya registrado y reservar esta función al administrador.', '(Caso 2)'],
    ['', '**Evaluación final, conclusiones y clausura**', '50 min']])
f['h2']('Casos completos resueltos')
f['ul']('**Caso 1:** Ingreso de 2 escritorios y 1 laptop, codificación, ficha técnica con fotografía, asignación con acta a la unidad solicitante y etiquetas con QR.', '**Caso 2:** Lote de 6 pupitres: copia de la ficha a los 5 restantes, importación de un inventario desde Excel con fotos y envío al VSIAF (validar, importar, re-indexar).')
f['h2']('Al terminar, el participante sabrá')
f['ul']('Codificar activos y completar su ficha técnica, incluida la copia a lotes grandes.', 'Asignar bienes con acta y mantener el kardex de cada activo.', 'Imprimir etiquetas con QR legibles.', 'Cargar un inventario existente desde Excel y enviarlo al VSIAF con respaldo.')
guardar('t03', B, 'capacitacion/03_Temas_para_Capacitar')

# ───────────────────────── 4. TIEMPO DE CAPACITACIÓN
B, f = nuevo()
portada(B, 'Tiempo de capacitación', 'Cronograma, distribución de horas y cálculo de tiempos',
        f'**Duración total:** {HORAS} horas académicas (720 minutos) en dos días', f'**Participantes:** {PARTICIPANTES}', f'**Horario:** primer día 08:30–12:30 y 14:30–18:30; segundo día 08:30–12:30')
f['h1']('1. Resumen')
f['table'](['Día', 'Turno', 'Módulo', 'Horario', 'Duración'], [
    ['1', 'Mañana', '1 · Administración de Almacenes', '08:30 – 12:30', '4 h'], ['1', 'Tarde', '2 · Administración del Uso de Combustibles', '14:30 – 18:30', '4 h'], ['2', 'Mañana', '3 · Administración de Activos Fijos complementarios al VSIAF', '08:30 – 12:30', '4 h'], ['', '', '**Total**', '', f'**{HORAS} h**']])
def tabla_dia(titulo, filas):
    f['h2'](titulo)
    f['table'](['Hora', 'Actividad', 'Duración'], [[f'{a} – {b}', t, f'{m} min'] for a, b, t, m in filas] + [['', '**Total del turno**', f'**{sum(m for *_, m in filas)} min**']])
f['h1']('2. Cronograma detallado', True)
tabla_dia('Primer día · Mañana — Módulo 1: Administración de Almacenes', DIA1_M)
tabla_dia('Primer día · Tarde — Módulo 2: Administración del Uso de Combustibles', DIA1_T)
tabla_dia('Segundo día · Mañana — Módulo 3: Administración de Activos Fijos complementarios al VSIAF', DIA2_M)
f['h1']('3. Distribución del tiempo', True)
def suma(pred): return sum(m for d in (DIA1_M, DIA1_T, DIA2_M) for a, b, t, m in d if pred(t))
casos = suma(lambda t: t.startswith('Caso')); marco = suma(lambda t: t.startswith('Módulo') or t.startswith('Inauguración') or t.startswith('Conclusiones')); recesos = suma(lambda t: t == 'Receso'); evals = suma(lambda t: t.startswith('Evaluación') or t.startswith('Cierre'))
assert casos + marco + recesos + evals == 720, (casos, marco, recesos, evals)
f['table'](['Tipo de actividad', 'Minutos', 'Horas', '%'], [
    ['Casos completos resueltos (6 casos)', str(casos), f'{casos / 60:.2f}', f'{casos / 7.2:.0f} %'], ['Marco conceptual, inauguración y clausura', str(marco), f'{marco / 60:.2f}', f'{marco / 7.2:.0f} %'],
    ['Evaluaciones y cierres', str(evals), f'{evals / 60:.2f}', f'{evals / 7.2:.0f} %'], ['Recesos', str(recesos), f'{recesos / 60:.2f}', f'{recesos / 7.2:.0f} %'], ['**Total**', '**720**', '**12.00**', '**100 %**']])
f['note']('Más de la mitad del taller es **práctica con casos resueltos**; el marco teórico se mantiene breve (35 a 40 minutos por módulo) porque el participante aprende repitiendo el caso en su computadora.', 'ok', 'Criterio')
f['h1']('4. Cómo se calculó el tiempo de cada caso')
f['table'](['Concepto', 'Cálculo'], [
    ['Tiempo por caso', 'Se estimó con el recorrido real de cada caso en el aplicativo (entre 20 y 30 minutos para un usuario experimentado) multiplicado por 2,5 a 3 para el ritmo de un grupo que sigue por primera vez, más el tiempo de preguntas.'],
    ['Trabajo en parejas', f'{PARTICIPANTES} participantes ÷ 2 = 15 puestos de trabajo; el facilitador y un asistente atienden consultas mientras se proyecta el caso.'],
    ['Recesos', 'Un receso de 15 minutos por turno, a mitad de la jornada.'],
    ['Holgura', 'Cada turno incluye 15 minutos de evaluación y cierre que pueden absorber retrasos sin recortar los casos.'],
])
f['h1']('5. Recomendaciones de organización')
f['ul']('Iniciar puntualmente: el primer módulo incluye la inauguración dentro de las 4 horas.', 'Entregar el cuadernillo de casos antes de comenzar cada módulo.', 'Dejar el aplicativo abierto y con la sesión iniciada en cada equipo antes del ingreso de los participantes (30 minutos antes).', 'Si un municipio ya conoce el aplicativo, puede avanzar con el caso 2 mientras el grupo termina el caso 1.')
guardar('t04', B, 'capacitacion/04_Tiempo_de_Capacitacion')

# ───────────────────────── 6. MEDIOS DE CAPACITACIÓN
B, f = nuevo()
portada(B, 'Medios de capacitación', 'Cuadros de equipos, aplicativo, materiales, personal y ambiente',
        f'**Para:** taller de {PARTICIPANTES} participantes, {HORAS} horas académicas, dos días', '**Incluye:** responsables, cantidades, lista de verificación y cuadros de costos de insumos para completar')
f['h1']('1. Cuadro general de medios y quién los provee')
f['table'](['Medio', 'Detalle', 'Cantidad', 'Provee'], [
    ['Ambiente', 'Sala equipada con mesas y sillas para 30 personas, buena iluminación y energía eléctrica', '1', 'AGAMDEPAZ'],
    ['Proyector multimedia', 'Para las presentaciones y la proyección de los casos', '1', 'AGAMDEPAZ'],
    ['Pantalla o pared blanca', 'Superficie de proyección visible desde toda la sala', '1', 'AGAMDEPAZ'],
    ['Computadoras', 'Una por pareja de participantes (ver cuadro 2)', '15 + 2', '[[AGAMDEPAZ / participantes con su laptop]]'],
    ['Aplicativo SIGAA instalado', 'Versión de escritorio, con datos de demostración y usuarios por rol', '17 equipos', 'GMC'],
    ['Casos completos y diapositivas', '6 casos resueltos en Word y 3 presentaciones', '1 juego', 'GMC'],
    ['Material impreso', 'Cuadernillo de casos y hojas de evaluación', f'{PARTICIPANTES} juegos', 'GMC'],
    ['Certificados y credenciales', 'Certificado de participación y credencial', f'{PARTICIPANTES}', 'GMC'],
    ['Refrigerios', 'Un receso por turno', f'{PARTICIPANTES + 2} × 3', '[[AGAMDEPAZ]]']])
f['h1']('2. Equipos informáticos', True)
f['table'](['Equipo', 'Cálculo', 'Cantidad'], [
    ['Computadoras para participantes', f'{PARTICIPANTES} participantes ÷ 2 por equipo', '15'], ['Computadora del facilitador (conectada al proyector)', '1', '1'], ['Computadora de respaldo con el aplicativo', '1', '1'],
    ['**Total de computadoras**', '', '**17**'], ['Regletas o extensiones eléctricas', '1 por cada 3 equipos', '6'], ['Cable HDMI/VGA y adaptadores', 'Para el equipo del facilitador', '2'], ['Memoria USB con instalador y datos de demostración', '1 por cada 5 equipos + 1', '4'], ['Mouse (si los equipos son laptops)', '1 por equipo', '17']])
f['h2']('Características mínimas de cada computadora')
f['table'](['Característica', 'Mínimo'], [['Sistema operativo', 'Windows 10 o superior (64 bits)'], ['Procesador y memoria', 'Doble núcleo y 4 GB de RAM'], ['Espacio libre en disco', '2 GB'], ['Pantalla', '1366 × 768 o superior'], ['Navegador / lector de PDF', 'Para abrir los documentos que genera el aplicativo (el escritorio los abre solo)'], ['Internet', 'No es necesario durante el taller (el aplicativo de escritorio funciona sin conexión)']])
f['h1']('3. Aplicativo instalado')
f['table'](['Elemento', 'Preparación por GMC', 'Verificación'], [
    ['Instalación', 'Versión de escritorio de SIGAA instalada en los 17 equipos (instalador `SIGAA Setup`)', 'Abre sin errores en cada equipo'],
    ['Datos de demostración', 'Base de ejemplo cargada: bodega, catálogo de 35 ítems, vehículos, edificios, funcionarios, proveedores', 'Los casos dan exactamente los resultados de los documentos'],
    ['Usuarios por rol', 'almacen, combustible, activos, consulta y admin (claves del manual); cambio de clave en el primer ingreso', 'Cada equipo ingresa con el usuario del módulo que se trabaja'],
    ['Logo de la entidad', 'Logo de AGAMDEPAZ cargado en Administración → Configuración para los documentos del taller', 'Aparece en el PDF de un CGI de prueba'],
    ['Copia limpia', 'Una copia de la base de demostración para restaurar un equipo si un participante la altera', 'Restauración probada antes del taller'],
    ['VSIAF de práctica', 'Carpeta de ejemplo con estructura de VSIAF para el Caso 2 de Activos Fijos (no se usa un VSIAF real)', 'Se envía y se lee desde el aplicativo']])
f['h1']('4. Material impreso y digital', True)
f['table'](['Material', 'Cantidad para 30 participantes', 'Detalle'], [
    ['Cuadernillo de casos (Almacenes)', '30', 'Enunciados y pasos de los 2 casos (sin la solución completa)'], ['Cuadernillo de casos (Combustible)', '30', 'Ídem'], ['Cuadernillo de casos (Activos Fijos)', '30', 'Ídem'],
    ['Hojas de evaluación por módulo', '90', '10 preguntas cada una'], ['Hoja de evaluación del taller (satisfacción)', '30', ''], ['Lista de asistencia', '3', 'Una por turno'], ['Credenciales', '32', 'Participantes y facilitadores'], ['Certificados de participación', '30', 'Con firma de GMC y AGAMDEPAZ'],
    ['Material digital (USB o enlace)', '30', 'Diapositivas, casos resueltos y manuales en PDF']])
f['h1']('5. Personal')
f['table'](['Función', 'Persona', 'Cantidad', 'Responsabilidad'], [
    ['Facilitador principal', f'{GERENTE}, {GERENTE_CARGO} de GMC', '1', 'Expone, conduce los casos y evalúa'], ['Asistente técnico', '[[Por designar por GMC]]', '1', 'Apoya a los participantes en los equipos y revisa los puestos'],
    ['Coordinación de AGAMDEPAZ', f'[[Por designar]] — bajo {REPRES}', '1', 'Convocatoria, ambiente, refrigerios y lista de participantes']])
f['h1']('6. Ambiente y logística')
f['table'](['Requisito', 'Detalle'], [['Distribución', '15 mesas de trabajo para parejas, orientadas a la pantalla; pasillo central'], ['Energía', 'Un punto de energía por cada 2 mesas; regletas de respaldo'], ['Climatización e iluminación', 'Ambiente ventilado y con luz que permita ver la pantalla'], ['Sonido', 'Micrófono solo si la sala supera las 40 personas'], ['Acceso', 'Ingreso del equipo 60 minutos antes de la inauguración'], ['Pizarra y marcadores', '1 pizarra acrílica y 4 marcadores']])
f['h1']('7. Lista de verificación', True)
f['table'](['Cuándo', 'Verificación', 'Responsable', 'Hecho'], [
    ['15 días antes', 'Fecha confirmada y convocatoria enviada a los municipios', 'AGAMDEPAZ', '☐'], ['10 días antes', 'Lista de 30 participantes con municipio y cargo', 'AGAMDEPAZ', '☐'], ['7 días antes', 'Visita al ambiente: energía, proyección, mesas', 'GMC y AGAMDEPAZ', '☐'],
    ['3 días antes', 'Material impreso, certificados y credenciales listos', 'GMC', '☐'], ['1 día antes', 'Aplicativo instalado y probado en los 17 equipos; copia limpia guardada', 'GMC', '☐'],
    ['Día 1, 07:30', 'Equipos encendidos con el aplicativo abierto; proyector y sonido probados', 'GMC', '☐'], ['Cada turno', 'Lista de asistencia firmada y evaluación aplicada', 'GMC', '☐'], ['Al cierre', 'Certificados entregados; informe final preparado', 'GMC', '☐']])
f['h1']('8. Cuadro de costos de insumos para completar')
f['p']('Cuadro para estimar el costo de los medios. Las columnas de costo las completa GMC con sus cotizaciones antes de enviar la oferta.')
f['table'](['Insumo', 'Cantidad', 'Unidad', 'Costo unitario (Bs)', 'Total (Bs)'], [
    ['Impresión de cuadernillos de casos (3 módulos × 30)', '90', 'cuadernillo', '[[ ]]', '[[ ]]'], ['Hojas de evaluación', '120', 'hoja', '[[ ]]', '[[ ]]'], ['Credenciales y portacredenciales', '32', 'unidad', '[[ ]]', '[[ ]]'],
    ['Certificados de participación', '30', 'unidad', '[[ ]]', '[[ ]]'], ['Memorias USB con el material', '34', 'unidad', '[[ ]]', '[[ ]]'], ['Marcadores y papelería', '1', 'global', '[[ ]]', '[[ ]]'],
    ['Refrigerios (si los cubre GMC)', '96', 'refrigerio', '[[ ]]', '[[ ]]'], ['Alquiler de computadoras (si se requiere)', '15', 'equipo × 2 días', '[[ ]]', '[[ ]]'], ['**TOTAL**', '', '', '', '**[[ ]]**']])
guardar('t06', B, 'capacitacion/06_Medios_de_Capacitacion')
print('docs ok')
