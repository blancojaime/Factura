from taller_comun import *

def horas_total(*dias): return sum(m for d in dias for *_, m in d)
assert horas_total(DIA1_M, DIA1_T, DIA2_M) == 12 * 60

# ───────────────────────── 1. NOTA DE PROPUESTA
B, f = nuevo(); mem(B)
p_al(B, FECHA, 'r'); p_al(B, '**GMC/AGAMDEPAZ/CAP Nº 001/2026**', 'r')
p_al(B, 'Señor:'); p_al(B, f'**{REPRES}**'); p_al(B, f'Representante de la {AGAM}'); p_al(B, '**Presente.-**')
p_al(B, f'**Ref.: PROPUESTA DE {TALLER} PARA LOS MUNICIPIOS MIEMBROS DE AGAMDEPAZ**', 'j')
p_al(B, 'De mi mayor consideración:')
p_al(B, f'Reciba un cordial saludo de {GMC} y los mejores deseos de éxito en la gestión que usted representa al frente de la {AGAM_C}.', 'j')
p_al(B, 'Los Gobiernos Autónomos Municipales administran cada día bienes y recursos que exigen orden, respaldo documental y control: los **materiales de almacén**, el **combustible** que consumen sus vehículos y maquinaria, y los **activos fijos** que forman su patrimonio. Cuando estos procesos se llevan con herramientas ágiles, trazables y comprensibles para el personal, se reducen los riesgos de pérdida, de uso indebido y de observaciones en las auditorías.', 'j')
p_al(B, f'Con ese propósito, {GMC_C} pone a consideración de {AGAM_C} la presente **propuesta de un taller de capacitación** dirigido a los municipios miembros, en tres áreas:', 'j')
f['ol']('**Administración de Almacenes.**', '**Administración del Uso de Combustibles.**', '**Administración de Activos Fijos, complementaria al VSIAF.**')
B.extend([]) 
p_al(B, f'El taller se desarrollaría en **dos días** (mañana y tarde del primer día y mañana del segundo día), con una duración total de **{HORAS} horas académicas**, para **{PARTICIPANTES} participantes**. La metodología es práctica: en cada área se proyectan y resuelven **dos casos completos** con el aplicativo {APP}, de modo que el personal vea el proceso de principio a fin y pueda repetirlo en su municipio.', 'j')
p_al(B, 'Para realizarlo contamos con el proyector para las presentaciones, los dos casos completos por área ya elaborados y el ambiente equipado que AGAMDEPAZ pondría a disposición. Los detalles de contenidos, tiempos y medios se encuentran en los documentos que se adjuntan a esta nota.', 'j')
p_al(B, 'Quedamos a la espera de su respuesta para coordinar la **fecha**, la **convocatoria** a los municipios y la **visita previa** al ambiente. Agradecemos de antemano la atención que se sirva dar a la presente.', 'j')
p_al(B, 'Con este motivo, saludo a usted atentamente.')
firma_gmc(B)
f2 = {'h2': lambda x: B.append({'t': 'h2', 'x': x}), 'ul': lambda *i: B.append({'t': 'ul', 'items': list(i)})}
f2['h2']('Documentos adjuntos')
f2['ul']('Nota de oferta de servicios de capacitación (GMC/AGAMDEPAZ/OFE Nº 001/2026).', 'Temas para capacitar: contenido de Almacenes, Combustible y Activos Fijos.', 'Tiempo de capacitación (cronograma y distribución de horas).', 'Medios de capacitación (equipos, aplicativo instalado, materiales y personal).', 'Material de capacitación: diapositivas de los tres módulos y seis casos resueltos (Word).')
guardar('t01', B, 'capacitacion/01_Nota_de_Propuesta_Capacitacion_AGAMDEPAZ')

# ───────────────────────── 2. NOTA DE OFERTA
B, f = nuevo(); mem(B)
p_al(B, FECHA, 'r'); p_al(B, '**GMC/AGAMDEPAZ/OFE Nº 001/2026**', 'r')
p_al(B, 'Señor:'); p_al(B, f'**{REPRES}**'); p_al(B, f'Representante de la {AGAM}'); p_al(B, '**Presente.-**')
p_al(B, f'**Ref.: OFERTA DE SERVICIOS DE CAPACITACIÓN POR {GMC}**', 'j')
p_al(B, 'De mi consideración:')
p_al(B, f'En seguimiento a la nota GMC/AGAMDEPAZ/CAP Nº 001/2026, {GMC} presenta su **oferta formal de servicios de capacitación**, en los términos siguientes:', 'j')
f['h2']('1. Objeto')
p_al(B, f'Realizar el **Taller de capacitación en herramientas administrativas municipales** para el personal de los municipios miembros de {AGAM_C}, en las áreas de Administración de Almacenes, Administración del Uso de Combustibles y Administración de Activos Fijos complementaria al VSIAF.', 'j')
f['h2']('2. Alcance de los servicios')
f['table'](['Área', 'Servicio ofertado'], [
    ['**Administración de Almacenes**', 'Capacitación de 4 horas académicas: ingreso (CGI), salida (vale), kardex valorado, reposición, inventario físico. Dos casos completos resueltos.'],
    ['**Uso de Combustibles**', 'Capacitación de 4 horas académicas: contratos y vales, emisión con QR, descargo, conciliación con la estación de servicio. Dos casos completos resueltos.'],
    ['**Activos Fijos complementarios al VSIAF**', 'Capacitación de 4 horas académicas: ingreso, codificación, ficha técnica, asignación, etiquetas QR, importación desde Excel y envío al VSIAF. Dos casos completos resueltos.'],
])
f['h2']('3. Duración y modalidad')
f['ul'](f'**{HORAS} horas académicas** en modalidad presencial, en **dos días**: primer día mañana (08:30 a 12:30) y tarde (14:30 a 18:30); segundo día mañana (08:30 a 12:30).',
        f'**{PARTICIPANTES} participantes**, trabajando en parejas frente a una computadora (15 puestos).',
        'Fecha y lugar: [[por coordinar con AGAMDEPAZ]].')
f['h2']('4. Metodología')
p_al(B, 'Exposición breve del marco de cada área y **resolución proyectada de dos casos completos por módulo**, que los participantes siguen y repiten paso a paso en su computadora. Cada módulo cierra con una evaluación corta.', 'j')
f['h2']('5. Productos que se entregan')
f['ul']('Diapositivas de los tres módulos (formato PowerPoint).', 'Seis casos completos resueltos (dos por módulo) en Word, para uso posterior en cada municipio.', 'Manual de implementación y manual de pruebas del aplicativo.', 'Aplicativo instalado en los equipos del taller, con datos de demostración.', 'Certificado de participación y evaluación de cada módulo.', 'Informe final del taller con lista de asistencia y resultados.')
f['h2']('6. Responsabilidades')
f['table'](['GMC S.R.L.', 'AGAMDEPAZ'], [['Facilitación del taller, material impreso y digital, instalación y configuración del aplicativo, evaluación, certificados e informe.', 'Ambiente equipado, proyector, convocatoria a los municipios, lista de participantes, refrigerios y coordinación de fecha.']])
f['h2']('7. Inversión')
p_al(B, 'La inversión por los servicios descritos es la siguiente (montos en bolivianos):', 'j')
f['table'](['Concepto', 'Cantidad', 'Unidad', 'Costo unitario (Bs)', 'Total (Bs)'], [
    ['Facilitación del taller (3 módulos de 4 horas)', '12', 'hora académica', '[[ ]]', '[[ ]]'],
    ['Preparación de casos, diapositivas y material', '1', 'global', '[[ ]]', '[[ ]]'],
    ['Instalación y configuración del aplicativo en los equipos del taller', '1', 'global', '[[ ]]', '[[ ]]'],
    ['Cuadernillos impresos de casos (por participante)', str(PARTICIPANTES), 'unidad', '[[ ]]', '[[ ]]'],
    ['Certificados de participación', str(PARTICIPANTES), 'unidad', '[[ ]]', '[[ ]]'],
    ['Informe final', '1', 'global', '[[ ]]', '[[ ]]'],
    ['**TOTAL**', '', '', '', '**[[ ]]**'],
])
p_al(B, 'Son: [[monto total en literal]] bolivianos. Forma de pago: [[por acordar]]. Los montos se completan al fijar la fecha y las condiciones con AGAMDEPAZ.')
f['h2']('8. Condiciones')
f['ul']('**Validez de la oferta:** 30 días calendario desde la fecha de esta nota.', 'La fecha del taller se define de común acuerdo, con al menos 15 días de anticipación para la convocatoria.', 'Cualquier ajuste de participantes, horas o medios se acuerda por escrito antes del taller.')
p_al(B, 'Agradezco la atención y quedo a su disposición para ampliar cualquier detalle.', 'j')
p_al(B, 'Atentamente,')
firma_gmc(B)
guardar('t02', B, 'capacitacion/02_Nota_de_Oferta_de_Servicios_GMC_SRL')
print('notas ok')
