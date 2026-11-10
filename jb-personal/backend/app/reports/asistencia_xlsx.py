"""Reporte detallado de asistencia, faltas y retrasos (institucional + individual + detalle diario)."""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from ..services import motor
from ..services.consultas import NOMBRE_MOD, DatosPeriodo

def _seguro(c):
    """Evita inyección de fórmulas: un texto que empiece por = + - @ se guarda como cadena, no como fórmula."""
    v = c.value
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") and not v.startswith("=SUM("):
        c.data_type = "s"
    return c

AZUL = "8A3B12"
THIN = Side(style="thin", color="AAAAAA")
B = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
COLOR = {motor.NORMAL: None, motor.RETRASO_LEVE: "FFF2CC", motor.RETRASO_GRAVE: "F8CBAD",
         motor.FALTA_INJUSTIFICADA: "F4B6B6", motor.FALTA_JUSTIFICADA: "DDEBF7", motor.OMISION: "EDEDED",
         motor.NO_LABORABLE: "F2F2F2", motor.FERIADO: "E2EFDA"}
ETIQ = {motor.NORMAL: "Asistencia normal", motor.RETRASO_LEVE: "Retraso leve", motor.RETRASO_GRAVE: "Retraso grave",
        motor.FALTA_INJUSTIFICADA: "Falta injustificada", motor.FALTA_JUSTIFICADA: "Falta justificada",
        motor.OMISION: "Omisión de marcación", motor.NO_LABORABLE: "No laborable", motor.FERIADO: "Feriado"}
DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _tabla(ws, r, cabecera, anchos=None):
    for i, h in enumerate(cabecera, 1):
        c = ws.cell(r, i, h)
        c.font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = B
    if anchos:
        for i, w in enumerate(anchos, 1):
            ws.column_dimensions[L(i)].width = w


def _fila(ws, r, vals, fill=None, fmt=None):
    for i, v in enumerate(vals, 1):
        c = _seguro(ws.cell(r, i, v))
        c.font, c.border = Font(name="Arial", size=9), B
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
        if fmt and i in fmt:
            c.number_format = fmt[i]


def _titulo(ws, d, texto, ncol):
    ws["A1"], ws["A2"] = d.entidad.nombre.upper(), f"{texto} — {d.titulo_periodo.upper()}"
    ws["A1"].font, ws["A2"].font = Font(name="Arial", size=12, bold=True, color=AZUL), Font(name="Arial", size=10, bold=True)
    for r in (1, 2):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol)


def _imputacion(a, l, es_cons) -> str:
    if a.estado == motor.FALTA_INJUSTIFICADA:
        return f"Falta injustificada ({a.falta} día) → descuento ×{l.dias_desc_faltas / l.faltas if l.faltas else 0:g}"
    if a.estado in (motor.RETRASO_LEVE, motor.RETRASO_GRAVE):
        return f"{a.min_retraso} min acumulados para escala de sanción"
    if a.estado == motor.FALTA_JUSTIFICADA:
        return f"Justificada ({a.categoria_just or 'permiso'})"
    return ""


def reporte_asistencia(d: DatosPeriodo) -> bytes:
    wb = Workbook()
    # --- 1. Institucional
    ws = wb.active
    ws.title = "Resumen institucional"
    _titulo(ws, d, "REPORTE DETALLADO DE ASISTENCIA, FALTAS Y RETRASOS", 14)
    cab = ["N°", "C.I.", "Código", "Apellidos y nombres", "Cargo / Unidad", "Modalidad", "Días laborables",
           "Días asistidos", "Faltas injust.", "Días justificados", "N° retrasos", "Min. retraso", "Sanción RIP",
           "Días de descuento"]
    _tabla(ws, 4, cab, [5, 13, 9, 30, 34, 20, 10, 10, 9, 11, 9, 9, 40, 11])
    ws.row_dimensions[4].height = 32
    r = 5
    for n, l in enumerate(d.liquidaciones, 1):
        e = l.empleado
        fill = "F4B6B6" if l.faltas > 0 else ("FFF2CC" if l.min_retraso else None)
        _fila(ws, r, [n, e.ci_completo, e.codigo, e.nombre_completo,
                      f"{e.cargo} / {e.unidad.nombre}" if e.unidad else e.cargo, NOMBRE_MOD[l.modalidad],
                      float(l.dias_laborables), float(l.dias_asistidos), float(l.faltas), float(l.dias_justificados),
                      l.nro_retrasos, l.min_retraso, l.sancion, float(l.dias_descuento)], fill)
        r += 1
    _fila(ws, r, ["TOTAL", "", "", "", "", "", f"=SUM(G5:G{r - 1})", f"=SUM(H5:H{r - 1})", f"=SUM(I5:I{r - 1})",
                  f"=SUM(J5:J{r - 1})", f"=SUM(K5:K{r - 1})", f"=SUM(L5:L{r - 1})", "", f"=SUM(N5:N{r - 1})"], "F6E4CC")
    ws.freeze_panes = "E5"
    ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # --- 2. Detalle diario
    w2 = wb.create_sheet("Detalle diario")
    _titulo(w2, d, "DETALLE DIARIO DE MARCACIONES", 10)
    _tabla(w2, 4, ["C.I.", "Apellidos y nombres", "Fecha", "Día", "Marcas (HH:MM)", "Estado", "Min. retraso",
                   "Falta (días)", "Justif. (días)", "Observaciones"], [13, 30, 11, 6, 30, 22, 10, 10, 10, 50])
    r = 5
    for l in d.liquidaciones:
        for a in d.asistencia.get(l.empleado_id, []):
            _fila(w2, r, [l.empleado.ci_completo, l.empleado.nombre_completo, a.fecha, DIAS_ES[a.fecha.weekday()],
                          a.marcas, ETIQ.get(a.estado, a.estado), a.min_retraso, float(a.falta), float(a.justificado),
                          a.observacion], COLOR.get(a.estado), {3: "dd/mm/yyyy"})
            r += 1
    w2.freeze_panes = "C5"
    w2.auto_filter.ref = f"A4:J{r - 1}"

    # --- 3. Faltas y retrasos
    w3 = wb.create_sheet("Faltas y retrasos")
    _titulo(w3, d, "IMPUTACIÓN DE FALTAS Y RETRASOS", 7)
    _tabla(w3, 4, ["C.I.", "Apellidos y nombres", "Fecha", "Estado", "Min. retraso", "Imputación", "Observaciones"],
           [13, 30, 11, 22, 11, 52, 50])
    r = 5
    for l in d.liquidaciones:
        for a in d.asistencia.get(l.empleado_id, []):
            if a.estado in (motor.RETRASO_LEVE, motor.RETRASO_GRAVE, motor.FALTA_INJUSTIFICADA, motor.FALTA_JUSTIFICADA,
                            motor.OMISION):
                _fila(w3, r, [l.empleado.ci_completo, l.empleado.nombre_completo, a.fecha, ETIQ[a.estado],
                              a.min_retraso, _imputacion(a, l, l.modalidad == "CONSULTOR_LINEA"), a.observacion],
                      COLOR.get(a.estado), {3: "dd/mm/yyyy"})
                r += 1
    w3.freeze_panes = "C5"
    # --- 4. Individual (una hoja por persona con su detalle) -> se resuelve con filtro; hoja de leyenda
    w4 = wb.create_sheet("Leyenda")
    w4["A1"] = "Leyenda de estados y reglas aplicadas"
    w4["A1"].font = Font(name="Arial", size=11, bold=True)
    h = d.horario
    filas = [(ETIQ[k], k) for k in COLOR]
    r = 3
    for txt, k in filas:
        w4.cell(r, 1, txt).fill = PatternFill("solid", fgColor=COLOR[k] or "FFFFFF")
        w4.cell(r, 1).border = B
        r += 1
    r += 1
    for t in [f"Horario: {h.nombre} — " + " / ".join(f"{x.nombre} {x.hora_entrada:%H:%M}-{x.hora_salida:%H:%M}" for x in h.turnos),
              f"Tolerancia: {h.tolerancia_min} min ({'se cuenta el retraso completo al superarla' if d.entidad.tolerancia_cuenta_total else 'se cuenta solo el exceso'}); "
              f"retraso grave: más de {h.umbral_grave_min} min.",
              f"Escala de sanción por: {'minutos acumulados' if d.entidad.escala_modo == 'MINUTOS' else 'cantidad de retrasos'}.",
              f"Descuento por falta injustificada: ×{d.entidad.factor_falta_planta} del haber diario (planta/eventual), "
              f"×{d.entidad.factor_falta_consultor} (consultores).",
              f"Consultores en línea: hasta {d.entidad.max_justificados_consultor} día(s) justificado(s) al mes sin descuento.",
              "Los segundos de cada marca se descartan; las marcas de días no laborables no computan."]:
        w4.cell(r, 1, t).font = Font(name="Arial", size=9)
        r += 1
    w4.column_dimensions["A"].width = 120
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
