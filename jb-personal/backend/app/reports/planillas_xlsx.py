"""Planillas en Excel con el diseño de 'Planilla de Remuneración' (Nuevos / Desvinculados / Sueldos)."""
from __future__ import annotations

import io
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from ..services.consultas import CAUSALES, NOMBRE_MOD, DatosPeriodo, baja_info, filtrar_liq

def _seguro(c):
    """Evita inyección de fórmulas: un texto que empiece por = + - @ se guarda como cadena, no como fórmula."""
    v = c.value
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") and not v.startswith("=SUM("):
        c.data_type = "s"
    return c

AZUL = "8A3B12"
THIN = Side(style="thin", color="999999")
BORDE = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HFILL = PatternFill("solid", fgColor=AZUL)
GFILL = PatternFill("solid", fgColor="F6E4CC")
TFILL = PatternFill("solid", fgColor="FBF1E3")
MONEY = '#,##0.00'


def _hdr(c, fill=HFILL, color="FFFFFF"):
    c.font = Font(name="Arial", size=8, bold=True, color=color)
    c.fill = fill
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = BORDE


def _encabezado(ws, d: DatosPeriodo, titulo: str, ncols: int):
    ws["A1"] = d.entidad.nombre.upper()
    ws["A2"] = titulo
    ws["A3"] = f"MES DE {d.titulo_periodo.upper()}"
    ws["A4"] = f"Empleador: {d.entidad.nombre}  |  Código SIGEP: {d.entidad.codigo_sigep or '—'}"
    for r, (sz, b) in enumerate([(12, True), (11, True), (10, True), (8, False)], start=1):
        ws.cell(r, 1).font = Font(name="Arial", size=sz, bold=b, color=AZUL if r < 4 else "000000")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
        ws.cell(r, 1).alignment = Alignment(horizontal="center")


def _cols(extras: list[tuple[str, str, int]], honor=False):
    """Definición de columnas: (clave, encabezado, ancho)."""
    base = [("nro", "Nº", 5), ("cua", "Nº CUA", 11), ("nombre", "NOMBRE Y APELLIDOS", 32), ("ci", "C.I.", 13),
            ("cargo", "CARGO", 34)] + extras
    num = [("haber", "HONORARIO PACTADO" if honor else "HABER BÁSICO", 13), ("dias", "DÍAS TRAB.", 8),
           ("bono", "BONO ANTIGÜEDAD", 11), ("ganado", "TOTAL GANADO", 13),
           ("afp", "APORTE LABORAL\nAFP/Gestora\n12,71%", 13), ("patronal", "Ap. Patronal\n17,21%\n(informativo)", 13),
           ("rciva", "RC - IVA", 9), ("ripdias", "DÍAS", 7), ("ripmonto", "FALTAS, ATRASOS Y OTROS", 13),
           ("totdesc", "TOTAL DESCUENTOS", 13), ("liquido", "LÍQUIDO PAGABLE", 13), ("firma", "FIRMAS", 18)]
    return base + num


def _valores(l):
    return {"haber": l.haber_basico, "dias": l.dias_trabajados, "bono": l.bono_antiguedad, "ganado": l.total_ganado,
            "afp": l.aporte_laboral, "patronal": l.aporte_patronal, "rciva": l.rc_iva, "ripdias": l.dias_descuento,
            "ripmonto": l.desc_asistencia, "totdesc": l.total_descuentos, "liquido": l.liquido_pagable}


SUMABLES = {"haber", "bono", "ganado", "afp", "patronal", "rciva", "ripdias", "ripmonto", "totdesc", "liquido"}


def _cabecera_tabla(ws, r0, cols):
    """Tres filas de cabecera con celdas combinadas (como la planilla original). Cada rango se combina UNA sola vez."""
    idx = {k: i + 1 for i, (k, _, _) in enumerate(cols)}
    etiqueta = {k: h for k, h, _ in cols}
    grupo = ("afp", "patronal", "rciva", "ripdias", "ripmonto", "totdesc")
    for k, i in idx.items():
        if k in grupo:
            continue
        ws.cell(r0, i, etiqueta[k])
        ws.merge_cells(start_row=r0, start_column=i, end_row=r0 + 2, end_column=i)
    a, b = idx["afp"], idx["totdesc"]
    ws.cell(r0, a, "DESCUENTOS")
    ws.merge_cells(start_row=r0, start_column=a, end_row=r0, end_column=b)
    ws.cell(r0 + 1, a, "DESC. DE LEY")
    ws.merge_cells(start_row=r0 + 1, start_column=a, end_row=r0 + 1, end_column=idx["rciva"])
    ws.cell(r0 + 1, idx["ripdias"], "R.I.P.")
    ws.merge_cells(start_row=r0 + 1, start_column=idx["ripdias"], end_row=r0 + 1, end_column=idx["ripmonto"])
    ws.cell(r0 + 1, idx["totdesc"], etiqueta["totdesc"])
    ws.merge_cells(start_row=r0 + 1, start_column=idx["totdesc"], end_row=r0 + 2, end_column=idx["totdesc"])
    for k in ("afp", "patronal", "rciva", "ripdias", "ripmonto"):
        ws.cell(r0 + 2, idx[k], etiqueta[k])
    for r in range(r0, r0 + 3):                       # estilo en todas las celdas (también las combinadas)
        for c in range(1, len(cols) + 1):
            _hdr(ws.cell(r, c))
    return r0 + 3, idx


def _fila(ws, r, n, l, cols, extras_val):
    emp = l.empleado
    v = _valores(l)
    v.update({"nro": n, "cua": emp.nro_cua, "nombre": f"{emp.nombres} {emp.apellidos}", "ci": emp.ci_completo,
              "cargo": emp.cargo, "firma": ""})
    v.update(extras_val)
    for i, (k, _, _) in enumerate(cols, start=1):
        c = _seguro(ws.cell(r, i, float(v[k]) if k in SUMABLES or k == "dias" else v.get(k, "")))
        c.font = Font(name="Arial", size=8)
        c.border = BORDE
        c.alignment = Alignment(vertical="center", wrap_text=k in ("nombre", "cargo"),
                                horizontal="right" if k in SUMABLES or k == "dias" else "left")
        if k in SUMABLES:
            c.number_format = MONEY if k != "ripdias" else "0.00"
        if k == "dias":
            c.number_format = "0"


def _totales(ws, r, r_ini, r_fin, cols, etiqueta="TOTALES"):
    ws.cell(r, 1, etiqueta)
    ncol_lbl = next(i for i, (k, _, _) in enumerate(cols, 1) if k == "haber") - 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol_lbl)
    for i, (k, _, _) in enumerate(cols, 1):
        c = ws.cell(r, i)
        c.fill, c.border = TFILL, BORDE
        c.font = Font(name="Arial", size=8, bold=True)
        if k in SUMABLES and r_fin >= r_ini:
            c.value = f"=SUM({L(i)}{r_ini}:{L(i)}{r_fin})"
            c.number_format = MONEY if k != "ripdias" else "0.00"
            c.alignment = Alignment(horizontal="right")
    ws.cell(r, 1).alignment = Alignment(horizontal="right")


def _pagina(ws, r_cab_fin):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = 1            # Carta
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{r_cab_fin - 2}:{r_cab_fin}"
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.freeze_panes = ws.cell(r_cab_fin + 1, 4)


def _anchos(ws, cols):
    for i, (_, _, w) in enumerate(cols, 1):
        ws.column_dimensions[L(i)].width = w


def _pie(ws, r, d, ncols):
    r += 2
    ws.cell(r, 1, "(*) El aporte patronal es informativo: no se descuenta al servidor. R.I.P.: Reglamento Interno de "
                  "Personal. Descuentos por asistencia calculados por el sistema (haber/30 × días).").font = \
        Font(name="Arial", size=7, italic=True)
    r += 4
    mitad = max(3, ncols // 2)
    for col, (rol, nom, cargo) in ((2, ("Elaborado por", d.entidad.rrhh_nombre, d.entidad.rrhh_cargo)),
                                   (mitad + 1, ("Aprobado por", d.entidad.aprobador_nombre, d.entidad.aprobador_cargo))):
        ws.cell(r, col, "______________________________")
        ws.cell(r + 1, col, f"{rol}: {nom}")
        ws.cell(r + 2, col, cargo)
        for k in range(3):
            ws.cell(r + k, col).font = Font(name="Arial", size=8)


def planilla_altas(d: DatosPeriodo) -> bytes:
    liqs = filtrar_liq(d, "ALTAS")
    extras = [("ingreso", "FECHA INGRESO", 11), ("modalidad", "MODALIDAD", 17), ("partida", "PARTIDA", 8),
              ("vigencia", "VIGENCIA HASTA", 12), ("doc", "N° MEMORÁNDUM / CONTRATO", 16)]
    return _planilla_simple(d, "PLANILLA DE NUEVO PERSONAL (ALTAS DEL PERIODO)", "Nuevos", liqs, extras,
                            lambda l: {"ingreso": l.contrato.fecha_inicio.strftime("%d/%m/%Y"),
                                       "modalidad": NOMBRE_MOD[l.modalidad], "partida": l.contrato.partida,
                                       "vigencia": l.contrato.fecha_fin.strftime("%d/%m/%Y") if l.contrato.fecha_fin else "Indefinida",
                                       "doc": l.contrato.nro_documento})


def planilla_bajas(d: DatosPeriodo) -> bytes:
    liqs = filtrar_liq(d, "BAJAS")
    extras = [("baja", "FECHA EFECTIVA DE BAJA", 12), ("causal", "CAUSAL", 22), ("modalidad", "MODALIDAD", 17),
              ("partida", "PARTIDA", 8), ("doc", "N° DOCUMENTO", 16)]

    def ex(l):
        f, c = baja_info(l.contrato, d.ini, d.fin)
        return {"baja": f.strftime("%d/%m/%Y"), "causal": c, "modalidad": NOMBRE_MOD[l.modalidad],
                "partida": l.contrato.partida, "doc": l.contrato.nro_documento}
    return _planilla_simple(d, "PLANILLA DE PERSONAL DESVINCULADO (BAJAS DEL PERIODO)", "Desvinculados", liqs, extras, ex)


def _planilla_simple(d, titulo, hoja, liqs, extras, fn_extra) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    cols = _cols(extras)
    _encabezado(ws, d, titulo, len(cols))
    r, _ = _cabecera_tabla(ws, 6, cols)
    r0 = r
    for n, l in enumerate(liqs, 1):
        _fila(ws, r, n, l, cols, fn_extra(l))
        r += 1
    if not liqs:
        ws.cell(r, 3, "Sin registros en el periodo").font = Font(name="Arial", size=9, italic=True)
        r += 1
    _totales(ws, r, r0, r - 1 if liqs else r0 - 1, cols)
    _pie(ws, r, d, len(cols))
    _anchos(ws, cols)
    _pagina(ws, 8)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def planilla_sueldos(d: DatosPeriodo) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Planilla"
    cols_plan = _cols([("modalidad", "UNIDAD ORGANIZACIONAL", 24)])
    cols_cons = _cols([("modalidad", "UNIDAD ORGANIZACIONAL", 24)], honor=True)
    _encabezado(ws, d, "PLANILLA DE SUELDOS Y SALARIOS", len(cols_plan))
    grupos = defaultdict(list)
    for l in d.liquidaciones:
        grupos[l.modalidad].append(l)
    r = 6
    subtotales: dict[str, int] = {}
    primera = True
    for mod in ("PERMANENTE", "EVENTUAL", "CONSULTOR_LINEA"):
        liqs = grupos.get(mod, [])
        cols = cols_cons if mod == "CONSULTOR_LINEA" else cols_plan
        c = ws.cell(r, 1, f"{NOMBRE_MOD[mod].upper()}" + (" — HONORARIOS (sin sueldo; partidas 25200/25800)" if mod == "CONSULTOR_LINEA"
                                                          else " — SUELDOS" + (" (partida 12100)" if mod == "EVENTUAL" else "")))
        c.font = Font(name="Arial", size=10, bold=True, color=AZUL)
        c.fill = GFILL
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=len(cols))
        r += 1
        r_cab = r
        r, _ = _cabecera_tabla(ws, r, cols)
        if primera:
            primera = False
        r0 = r
        for n, l in enumerate(liqs, 1):
            _fila(ws, r, n, l, cols, {"modalidad": l.empleado.unidad.nombre if l.empleado.unidad else ""})
            r += 1
        if not liqs:
            ws.cell(r, 3, "Sin registros").font = Font(name="Arial", size=9, italic=True)
            r += 1
        _totales(ws, r, r0, r - 1 if liqs else r0 - 1, cols, f"SUBTOTAL {NOMBRE_MOD[mod].upper()}")
        subtotales[mod] = r
        r += 2
    # TOTAL GENERAL (suma de subtotales)
    ws.cell(r, 1, "TOTAL GENERAL")
    ncol_lbl = next(i for i, (k, _, _) in enumerate(cols_plan, 1) if k == "haber") - 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncol_lbl)
    for i, (k, _, _) in enumerate(cols_plan, 1):
        c = ws.cell(r, i)
        c.fill, c.border, c.font = GFILL, BORDE, Font(name="Arial", size=9, bold=True)
        if k in SUMABLES:
            c.value = "=" + "+".join(f"{L(i)}{x}" for x in subtotales.values())
            c.number_format = MONEY if k != "ripdias" else "0.00"
    ws.cell(r, 1).alignment = Alignment(horizontal="right")
    _pie(ws, r, d, len(cols_plan))
    _anchos(ws, cols_plan)
    ws.page_setup.orientation, ws.page_setup.paperSize = "landscape", 1
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.freeze_panes = "D6"

    # Resumen por modalidad
    rs = wb.create_sheet("Resumen")
    rs.append([d.entidad.nombre.upper()])
    rs.append([f"RESUMEN DE PLANILLA — {d.titulo_periodo.upper()}"])
    rs.append([])
    rs.append(["Modalidad", "N° personas", "Total ganado", "Aporte laboral", "RC-IVA", "Desc. asistencia",
               "Total descuentos", "Líquido pagable", "Aporte patronal (info)"])
    for c in rs[4]:
        _hdr(c)
    for mod in ("PERMANENTE", "EVENTUAL", "CONSULTOR_LINEA"):
        ls = grupos.get(mod, [])
        rs.append([NOMBRE_MOD[mod], len(ls)] + [float(sum(getattr(l, a) for l in ls)) for a in
                  ("total_ganado", "aporte_laboral", "rc_iva", "desc_asistencia", "total_descuentos", "liquido_pagable",
                   "aporte_patronal")])
    rs.append(["TOTAL"] + [f"=SUM({L(i)}5:{L(i)}7)" for i in range(2, 10)])
    for row in rs.iter_rows(min_row=5, max_row=8):
        for c in row:
            c.border = BORDE
            c.number_format = MONEY if c.column > 2 else "General"
            c.font = Font(name="Arial", size=9, bold=row[0].row == 8)
    rs["A1"].font, rs["A2"].font = Font(name="Arial", size=12, bold=True, color=AZUL), Font(name="Arial", size=10, bold=True)
    for i, w in enumerate([36, 12, 16, 16, 12, 16, 16, 16, 20], 1):
        rs.column_dimensions[L(i)].width = w
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
