"""Datos comunes del taller: todos los documentos y diapositivas salen de aquí para que sean coherentes entre sí."""
import json, sys
sys.path.insert(0, '/home/user/Factura/sigaa/docs/fuentes')
from contenido_novedades import nuevo

OUT = '/home/user/Factura/sigaa/docs/fuentes/'
GMC = 'GRUPO MULTIDISCIPLINARIO DE CONSULTORES GMC S.R.L.'
GMC_C = 'GMC S.R.L.'
AGAM = 'ASOCIACIÓN DE GOBIERNOS AUTÓNOMOS MUNICIPALES DEL DEPARTAMENTO DE LA PAZ – AGAMDEPAZ'
AGAM_C = 'AGAMDEPAZ'
TALLER = 'TALLER DE CAPACITACIÓN EN HERRAMIENTAS ADMINISTRATIVAS MUNICIPALES'
TALLER_SUB = 'Administración de Almacenes · Administración de Uso de Combustibles · Administración de Activos Fijos complementarios al VSIAF'
FECHA = 'La Paz, 4 de noviembre de 2026'
GERENTE = 'Lic. Oscar Fernando Blanco Villegas'
GERENTE_CARGO = 'Gerente General'
REPRES = 'Lic. Vicente Yujra Coronado'
APP = 'SIGAA (Sistema Integrado de Gestión de Almacenes, Combustible y Activos Fijos)'
PARTICIPANTES = 30
HORAS = 12
LOGOS = ['logo_gmc.jpg', 'logo_agamdepaz.jpg']
PIE = 'GMC S.R.L. · Taller de capacitación AGAMDEPAZ'

# Cronograma único (minutos) — lo usan la nota, el documento de tiempos y las diapositivas
DIA1_M = [('08:30', '08:50', 'Inauguración y presentación de participantes', 20), ('08:50', '09:30', 'Módulo 1 · Marco general de la administración de almacenes y recorrido del aplicativo', 40),
          ('09:30', '10:45', 'Caso 1 resuelto: compra, ingreso (CGI), pedido y entrega (vale) de material', 75), ('10:45', '11:00', 'Receso', 15),
          ('11:00', '12:15', 'Caso 2 resuelto: control de existencias — reposición e inventario físico', 75), ('12:15', '12:30', 'Evaluación del módulo y cierre', 15)]
DIA1_T = [('14:30', '15:05', 'Módulo 2 · Marco del uso de combustible, contratos, vales y roles', 35), ('15:05', '16:25', 'Caso 1 resuelto: ciclo completo del vale — recepción, emisión (con QR) y descargo', 80),
          ('16:25', '16:40', 'Receso', 15), ('16:40', '18:00', 'Caso 2 resuelto: conciliación con la estación de servicio y control de observados', 80),
          ('18:00', '18:15', 'Evaluación del módulo', 15), ('18:15', '18:30', 'Cierre del primer día', 15)]
DIA2_M = [('08:30', '09:05', 'Módulo 3 · Activos fijos y su relación con el VSIAF; recorrido del aplicativo', 35), ('09:05', '10:15', 'Caso 1 resuelto: ingreso, codificación, ficha técnica, asignación y etiquetas con QR', 70),
          ('10:15', '10:30', 'Receso', 15), ('10:30', '11:40', 'Caso 2 resuelto: lote de pupitres — copia de ficha, importación desde Excel con fotos y envío al VSIAF', 70),
          ('11:40', '12:00', 'Evaluación final', 20), ('12:00', '12:30', 'Conclusiones, entrega de certificados y clausura', 30)]

def guardar(nombre, B, out):
    json.dump({'out': out, 'bloques': B}, open(OUT + nombre + '.json', 'w'), ensure_ascii=False)

def nota_encabezado(f, ref, asunto):
    f['membrete'] = None

def mem(B): B.append({'t': 'membrete', 'logos': LOGOS})
def p_al(B, x, al=''): B.append({'t': 'p', 'x': x, 'align': al})
def sig(B, *firmas): B.append({'t': 'sig', 'firmas': [list(x) for x in firmas]})
def firma_gmc(B): sig(B, (GERENTE, GERENTE_CARGO, GMC))
