#!/usr/bin/env python3
"""Genera el dataset de prueba (5 servidores ficticios, octubre 2026) de forma DETERMINISTA.

Salidas (en esta carpeta):
  personal.csv                      -> carga masiva de personal
  biometrico_octubre_2026.csv       -> marcaciones (formato delimitado con cabecera)
  biometrico_octubre_2026.dat       -> las MISMAS marcaciones en formato ZKTeco ATTLOG
  biometrico_octubre_2026.xlsx      -> las MISMAS marcaciones con el diseño '1_Marcaciones_Crudas'
  permisos_octubre_2026.csv         -> permisos/licencias a registrar (ver GUIA_PRUEBAS.md)
Todos los nombres y C.I. son FICTICIOS.
"""
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl

AQUI = Path(__file__).resolve().parent
rnd = random.Random(20261001)

PERSONAL = [  # codigo, ci, nombres, apellidos, cargo, unidad, modalidad, partida, haber, ingreso, fin, doc
    ("1001", "1000001", "Juan Carlos", "Mamani Quispe", "Técnico de Catastro", "Dirección de Obras Públicas", "Permanente", "11000", 6000, "01/03/2022", "", "MEM-014/2022"),
    ("1002", "1000002", "María Elena", "Vargas Rojas", "Auxiliar Contable", "Dirección Administrativa Financiera", "Permanente", "11000", 4500, "15/01/2021", "", "MEM-003/2021"),
    ("2001", "1000003", "Luis Alberto", "Choque Condori", "Inspector Municipal", "Intendencia Municipal", "Eventual", "12100", 3800, "01/02/2026", "31/12/2026", "CONT-021/2026"),
    ("2002", "1000004", "Carla Andrea", "Flores Apaza", "Profesional Jurídico", "Dirección Jurídica", "Eventual", "12100", 3500, "01/10/2026", "31/12/2026", "CONT-077/2026"),
    ("3001", "1000005", "Miguel Ángel", "Salazar Copa", "Consultor Individual de Línea - Supervisión", "Dirección de Obras Públicas", "Consultor en Línea", "25200", 7000, "01/07/2026", "30/10/2026", "CIL-009/2026"),
]

DIAS = [date(2026, 10, d) for d in range(1, 32) if date(2026, 10, d).weekday() < 5]   # 22 días hábiles

def hm(minutos, seg=None):
    return f"{minutos // 60:02d}:{minutos % 60:02d}:{(seg if seg is not None else rnd.randint(0, 59)):02d}"

def m(s):  # "08:12" -> minutos
    h, mi = s.split(":")
    return int(h) * 60 + int(mi)

# Escenarios: {codigo: {fecha: lista de marcas "HH:MM" | None=sin marcas}}  (solo excepciones; el resto es puntual)
OVR = {
    "1001": {date(2026, 10, 6): ["08:12", "12:03", "14:28", "18:34"],           # retraso 12 min
             date(2026, 10, 14): ["08:00", "14:28", "18:35"],                    # omisión: falta salida mañana
             date(2026, 10, 20): ["07:58", "12:02", "14:48", "18:36"]},         # retraso 18 min
    "1002": {date(2026, 10, 2): ["08:25", "12:04", "14:27", "18:33"],           # retraso 25 min
             date(2026, 10, 7): ["08:45", "12:01", "14:30", "18:40"],           # retraso GRAVE 45 min
             date(2026, 10, 15): None},                                          # falta injustificada (día completo)
    "2001": {date(2026, 10, 12): None, date(2026, 10, 13): None,                # licencia médica (permiso aprobado)
             date(2026, 10, 21): ["10:05", "12:03", "14:25", "18:35"],          # llegó 10:05 con permiso 08:00-10:00
             date(2026, 10, 28): ["07:55", "12:06"]},                            # media falta: sin marcas en la tarde
    "2002": {date(2026, 10, 9): None,                                            # permiso particular SIN goce
             date(2026, 10, 14): ["07:57", "12:02", "14:52", "18:37"],          # retraso 22 min (tarde)
             date(2026, 10, 22): ["07:59", "12:05", "18:35"]},                  # omisión: falta entrada tarde
    "3001": {date(2026, 10, 8): None, date(2026, 10, 19): None,                 # 2 días justificados con fiscal
             date(2026, 10, 13): ["08:50", "12:02", "14:29", "18:38"],          # retraso grave 50 min
             date(2026, 10, 27): None},                                          # permiso PENDIENTE (no cuenta) => falta
}

def marcas_dia(cod, d):
    if cod in OVR and d in OVR[cod]:
        v = OVR[cod][d]
        return [] if v is None else [hm(m(x)) for x in v]
    return [hm(rnd.randint(470, 485)), hm(rnd.randint(720, 735)), hm(rnd.randint(860, 875)), hm(rnd.randint(1110, 1130))]

def main():
    with open(AQUI / "personal.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["codigo", "ci", "complemento", "nombres", "apellidos", "cargo", "unidad", "modalidad", "partida", "haber_basico",
                    "bono_antiguedad", "fecha_ingreso", "fecha_fin", "estado", "nro_cua", "nro_documento"])
        for c, ci, nom, ape, cargo, un, mod, part, haber, ing, fin, doc in PERSONAL:
            w.writerow([c, ci, "", nom, ape, cargo, un, mod, part, haber, 0, ing, fin, "Activo", "", doc])

    filas = []
    for cod, ci, nom, ape, *_ in PERSONAL:
        for d in DIAS:
            if cod == "2002" and d < date(2026, 10, 1):
                continue
            tipos = ["Entrada", "Salida Mañana", "Entrada Tarde", "Salida"]
            for t, h in zip(tipos, marcas_dia(cod, d)):
                filas.append((cod, f"{ape} {nom}", d, h, t, rnd.choice(["Huella Digital", "Rostro"]), "Reloj Recepción"))
    # tipos de evento se reasignan según el orden real de las marcas del día (las excepciones tienen menos marcas)
    with open(AQUI / "biometrico_octubre_2026.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID Empleado", "Nombre Completo", "Fecha", "Hora", "Tipo de Marcación", "Método Verificación", "Dispositivo"])
        for cod, nom, d, h, t, mt, dv in filas:
            w.writerow([cod, nom, d.strftime("%d/%m/%Y"), h, t, mt, dv])
    with open(AQUI / "biometrico_octubre_2026.dat", "w", encoding="utf-8", newline="\n") as f:
        for cod, nom, d, h, t, mt, dv in filas:     # PIN \t fecha hora \t verify \t status \t workcode \t reserved
            f.write(f"{cod}\t{d:%Y-%m-%d} {h}\t{1 if mt == 'Huella Digital' else 15}\t{0 if t.startswith('Entrada') else 1}\t0\t0\n")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "1_Marcaciones_Crudas"
    ws["A1"] = "REPORTE DE MARCACIONES BIOMÉTRICAS (DATOS CRUDOS)"
    ws["A2"] = "Periodo: 01/10/2026 al 31/10/2026 | Dispositivo: ZKTeco BioTime / Terminal Principal"
    ws.append([])
    ws.append(["ID Empleado", "Nombre Completo", "Departamento", "Fecha", "Hora", "Tipo de Marcación", "Método Verificación",
               "Dispositivo", "Estado / Incidencia"])
    for cod, nom, d, h, t, mt, dv in filas:
        ws.append([cod, nom, "", d.strftime("%d/%m/%Y"), h, t, mt, dv, "Normal"])
    wb.save(AQUI / "biometrico_octubre_2026.xlsx")

    with open(AQUI / "permisos_octubre_2026.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["codigo_empleado", "tipo", "desde", "hasta", "hora_desde", "hora_hasta", "motivo", "doc_respaldo",
                    "autorizado_por", "estado"])
        w.writerows([
            ["2001", "LIC_MEDICA", "2026-10-12", "2026-10-13", "", "", "Incapacidad temporal", "Cert. CNS N° 44589", "Jefe inmediato", "APROBADO"],
            ["2001", "PARTICULAR_CGH", "2026-10-21", "2026-10-21", "08:00", "10:00", "Trámite personal", "Boleta firmada", "Jefe inmediato", "APROBADO"],
            ["2002", "PARTICULAR_SGH", "2026-10-09", "2026-10-09", "", "", "Asunto familiar", "Solicitud escrita", "Jefe inmediato", "APROBADO"],
            ["3001", "PARTICULAR_CGH", "2026-10-08", "2026-10-08", "", "", "Trámite personal", "Solicitud escrita", "Ing. Fiscal de Obra", "APROBADO"],
            ["3001", "LIC_MEDICA", "2026-10-19", "2026-10-19", "", "", "Consulta médica", "Certificado médico", "Ing. Fiscal de Obra", "APROBADO"],
            ["3001", "PARTICULAR_CGH", "2026-10-27", "2026-10-27", "", "", "Trámite personal", "Solicitud escrita", "", "PENDIENTE"],
        ])
    print("Dataset generado:", len(filas), "marcas")

if __name__ == "__main__":
    main()
