"""Reporte consolidado plano (UTF-8) para verificación cruzada de la UAI / Contraloría General del Estado."""
from __future__ import annotations

import csv
import io

from ..services.consultas import DatosPeriodo

COLUMNAS = ["PERIODO", "CI", "CODIGO_EMPLEADO", "TIPO_CONTRATO", "TOTAL_DIAS_LABORABLES", "DIAS_ASISTIDOS", "FALTAS",
            "MINUTOS_RETRASO", "DIAS_PERMISO_JUSTIFICADO", "IMPORTE_DESCUENTOS_APLICADOS"]


def reporte_plano(d: DatosPeriodo, delimitador: str = "\t", bom: bool = False) -> bytes:
    """Una fila por servidor. Decimales con punto; importes con 2 decimales; sin separador de miles.

    IMPORTE_DESCUENTOS_APLICADOS = descuentos por faltas + atrasos + permisos sin goce / exceso de consultor
    (no incluye aportes de ley ni RC-IVA)."""
    if delimitador not in ("\t", ",", ";", "|"):
        raise ValueError("Delimitador no soportado")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimitador, lineterminator="\r\n")
    w.writerow(COLUMNAS)
    per = f"{d.anio}-{d.mes:02d}"
    for l in d.liquidaciones:
        e = l.empleado
        w.writerow([per, e.ci_completo, e.codigo, l.modalidad, f"{l.dias_laborables:.0f}", f"{l.dias_asistidos:.2f}",
                    f"{l.faltas:.2f}", l.min_retraso, f"{l.dias_justificados:.2f}", f"{l.desc_asistencia:.2f}"])
    data = buf.getvalue().encode("utf-8")
    return (b"\xef\xbb\xbf" + data) if bom else data


def reporte_plano_xlsx(d: DatosPeriodo) -> bytes:
    """Mismo contenido que el consolidado plano, en Excel: SOLO títulos de columna y datos (sin membrete, combinadas ni estilos)."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Consolidado"
    ws.append(COLUMNAS)
    per = f"{d.anio}-{d.mes:02d}"
    for l in d.liquidaciones:
        e = l.empleado
        ws.append([per, e.ci_completo, e.codigo, l.modalidad, int(l.dias_laborables), float(l.dias_asistidos), float(l.faltas),
                   int(l.min_retraso), float(l.dias_justificados), float(l.desc_asistencia)])
        for c in ws[ws.max_row][:3]:                      # PERIODO, CI y CODIGO siempre como texto (nunca fórmula ni número)
            c.value = str(c.value)
            c.data_type = "s"
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
