from taller_comun import *
B, f = nuevo()
B.append({'t': 'cover', 'title': 'Paquete de capacitación para AGAMDEPAZ', 'sub': 'Índice, datos comunes y campos por completar', 'logos': LOGOS,
          'lines': [f'**Taller:** {TALLER.capitalize()}', f'**Presenta:** {GMC} — {GERENTE}, {GERENTE_CARGO}', f'**Para:** {AGAM} — {REPRES}', f'**Participantes:** {PARTICIPANTES} · **Duración:** {HORAS} horas académicas en dos días']})
f['h1']('1. Documentos del paquete')
f['table'](['N.º', 'Documento', 'Formato', 'Para qué sirve'], [
    ['1', '01_Nota_de_Propuesta_Capacitacion_AGAMDEPAZ', 'Word', 'Nota que presenta la propuesta a AGAMDEPAZ'],
    ['2', '02_Nota_de_Oferta_de_Servicios_GMC_SRL', 'Word', 'Oferta formal: alcance, productos, responsabilidades e inversión'],
    ['3', '03_Temas_para_Capacitar', 'Word', 'Contenido de Almacenes, Combustible y Activos Fijos'],
    ['4', '04_Tiempo_de_Capacitacion', 'Word', 'Cronograma de 12 horas y cálculo de tiempos'],
    ['5', '05_Diapositivas_Modulo1/2/3 (3 archivos)', 'PowerPoint', 'Presentaciones de cada tema con los casos, notas del facilitador y evaluaciones'],
    ['5', '05a/05b/05c_Casos_Resueltos (3 archivos)', 'Word', 'Seis casos completos resueltos, paso a paso, con capturas'],
    ['6', '06_Medios_de_Capacitacion', 'Word', 'Cuadros de equipos, aplicativo instalado, materiales, personal y logística']])
f['note']('Cada documento también tiene su versión PDF (los Word son los editables).', '', 'Formatos')
f['h1']('2. Datos comunes (iguales en todos los documentos)')
f['table'](['Dato', 'Valor'], [
    ['Participantes', f'{PARTICIPANTES} (15 puestos de trabajo en parejas)'], ['Duración', f'{HORAS} horas académicas = 3 bloques de 4 horas'], ['Día 1 · mañana', 'Módulo 1 · Almacenes · 08:30 – 12:30'], ['Día 1 · tarde', 'Módulo 2 · Combustible · 14:30 – 18:30'], ['Día 2 · mañana', 'Módulo 3 · Activos Fijos y VSIAF · 08:30 – 12:30'],
    ['Casos resueltos', '6 (2 por módulo)'], ['Computadoras', '17 (15 para participantes, 1 del facilitador, 1 de respaldo)'], ['Aplicativo', APP], ['Referencias de las notas', 'GMC/AGAMDEPAZ/CAP Nº 001/2026 y GMC/AGAMDEPAZ/OFE Nº 001/2026']])
f['h1']('3. Campos que debe completar antes de enviar')
f['p']('En los documentos están **resaltados en amarillo** los datos que no se pudieron inventar:')
f['table'](['Dónde', 'Qué completar'], [
    ['Nota de oferta · cuadro de inversión', 'Costos unitarios, totales, monto en literal y forma de pago'], ['Nota de oferta', 'Fecha y lugar del taller (por coordinar con AGAMDEPAZ)'], ['Medios de capacitación · cuadro 1', 'Quién provee las computadoras (AGAMDEPAZ o participantes con laptop) y los refrigerios'],
    ['Medios de capacitación · cuadro de personal', 'Nombre del asistente técnico de GMC y de la coordinación de AGAMDEPAZ'], ['Medios de capacitación · costos de insumos', 'Costos de impresión, certificados, USB y demás insumos'], ['Notas', 'Fecha (hoy: 4 de noviembre de 2026) y, si desea, el cargo del Lic. Vicente Yujra Coronado']])
f['h1']('4. Antes del taller')
f['ol']('Instalar el aplicativo de escritorio en los 17 equipos (instalador `SIGAA Setup`) y verificar que abre.', 'Cargar el logo de AGAMDEPAZ en Administración → Configuración para que salga en los documentos del taller.', 'Guardar una copia limpia de la base de demostración para restaurar equipos.', 'Imprimir los cuadernillos de los casos (05a, 05b y 05c) sin la sección «Respuestas y errores» si se desea evaluar.', 'Probar la proyección de las diapositivas y revisar las notas del facilitador (pestaña de notas en PowerPoint).')
guardar('t00', B, 'capacitacion/00_Indice_del_Paquete_de_Capacitacion')
