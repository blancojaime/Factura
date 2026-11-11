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
    más multas/descuentos adicionales (no incluye aportes de ley ni RC-IVA)."""
    if delimitador not in ("\t", ",", ";", "|"):
        raise ValueError("Delimitador no soportado")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimitador, lineterminator="\r\n")
    w.writerow(COLUMNAS)
    per = f"{d.anio}-{d.mes:02d}"
    for l in d.liquidaciones:
        e = l.empleado
        w.writerow([per, e.ci_completo, e.codigo, l.modalidad, f"{l.dias_laborables:.0f}", f"{l.dias_asistidos:.2f}",
                    f"{l.faltas:.2f}", l.min_retraso, f"{l.dias_justificados:.2f}", f"{l.desc_asistencia + l.desc_multas:.2f}"])
    data = buf.getvalue().encode("utf-8")
    return (b"\xef\xbb\xbf" + data) if bom else data


COLUMNAS_XLSX = [
    "PERIODO", "CI", "CODIGO_EMPLEADO", "NOMBRES", "APELLIDOS", "CARGO", "UNIDAD", "TIPO_CONTRATO", "PARTIDA", "NRO_CUA", "NRO_DOCUMENTO",
    "FECHA_INGRESO", "FECHA_BAJA", "CAUSAL_BAJA", "HABER_BASICO", "DIAS_TRABAJADOS", "BONO_ANTIGUEDAD", "TOTAL_GANADO", "APORTE_LABORAL",
    "APORTE_PATRONAL", "RC_IVA", "TOTAL_DIAS_LABORABLES", "DIAS_ASISTIDOS", "FALTAS", "NRO_RETRASOS", "MINUTOS_RETRASO",
    "DIAS_PERMISO_JUSTIFICADO", "DIAS_DESC_FALTAS", "DIAS_DESC_ATRASOS", "DIAS_DESC_PERMISO_SIN_GOCE", "DIAS_DESC_EXCESO_CONSULTOR",
    "DIAS_DESCUENTO_TOTAL", "DESC_FALTAS", "DESC_ATRASOS", "DESC_PERMISOS_SIN_GOCE_Y_OTROS", "MULTAS_Y_DESCUENTOS_ADICIONALES",
    "IMPORTE_DESCUENTOS_APLICADOS", "FALTAS_ATRASOS_Y_OTROS_PLANILLA", "TOTAL_DESCUENTOS", "LIQUIDO_PAGABLE", "SANCION_RIP", "OBSERVACIONES"]

TEXTOS_XLSX = {"PERIODO", "CI", "CODIGO_EMPLEADO", "NOMBRES", "APELLIDOS", "CARGO", "UNIDAD", "TIPO_CONTRATO", "PARTIDA", "NRO_CUA",
               "NRO_DOCUMENTO", "FECHA_INGRESO", "FECHA_BAJA", "CAUSAL_BAJA", "SANCION_RIP", "OBSERVACIONES"}


def reporte_plano_xlsx(d: DatosPeriodo) -> bytes:
    """Consolidado plano en Excel con TODA la información de las planillas salariales y de asistencia.
    Solo títulos de columna y datos (sin membrete, celdas combinadas, fórmulas ni estilos): una fila por servidor.
    IMPORTE_DESCUENTOS_APLICADOS = faltas + atrasos + permisos sin goce/exceso de consultor + multas (igual que el .txt);
    FALTAS_ATRASOS_Y_OTROS_PLANILLA es la columna homónima de la Planilla de Sueldos; TOTAL_DESCUENTOS incluye aportes y RC-IVA."""
    from openpyxl import Workbook
    from ..services.consultas import baja_info
    wb = Workbook()
    ws = wb.active
    ws.title = "Consolidado"
    ws.append(COLUMNAS_XLSX)
    per = f"{d.anio}-{d.mes:02d}"
    for l in d.liquidaciones:
        e, c = l.empleado, l.contrato
        bj = baja_info(c, d.ini, d.fin)
        f = lambda x: float(x)  # noqa: E731
        fila = [per, e.ci_completo, e.codigo, e.nombres, e.apellidos, e.cargo, e.unidad.nombre if e.unidad else "", l.modalidad, c.partida, e.nro_cua,
                c.nro_documento, c.fecha_inicio.isoformat(), (bj[0].isoformat() if bj else ""), (bj[1] if bj else ""),
                f(l.haber_basico), f(l.dias_trabajados), f(l.bono_antiguedad), f(l.total_ganado), f(l.aporte_laboral), f(l.aporte_patronal), f(l.rc_iva),
                int(l.dias_laborables), f(l.dias_asistidos), f(l.faltas), int(l.nro_retrasos), int(l.min_retraso), f(l.dias_justificados),
                f(l.dias_desc_faltas), f(l.dias_desc_atrasos), f(l.dias_desc_sin_goce), f(l.dias_desc_exceso_consultor), f(l.dias_descuento),
                f(l.desc_faltas), f(l.desc_atrasos), f(l.desc_otros), f(l.desc_multas), f(l.desc_asistencia + l.desc_multas),
                f(l.desc_asistencia + l.desc_multas), f(l.total_descuentos), f(l.liquido_pagable), l.sancion, l.observacion]
        ws.append(fila)
        for cel, titulo in zip(ws[ws.max_row], COLUMNAS_XLSX):          # textos: nunca fórmula ni número
            if titulo in TEXTOS_XLSX:
                cel.value = "" if cel.value is None else str(cel.value)
                cel.data_type = "s"
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
