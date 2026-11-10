"""Informe técnico de asistencia (.docx) generado a partir de la plantilla institucional.

La plantilla (templates/informe_asistencia.docx) conserva membrete, estilos, marco normativo y firmas; el
generador sustituye los marcadores [..] y reconstruye las tablas con los datos reales del periodo.
"""
from __future__ import annotations

import copy
import io
import re
from collections import defaultdict
from datetime import date, timedelta

import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from .. import config
from ..services import motor
from ..services.consultas import MESES, DatosPeriodo

SIN_REGISTROS = "Sin registros en el periodo"


# ----------------------------------------------------------------------------- helpers XML
def _set_run_lines(run_el, lines: list[str]):
    for ch in list(run_el):
        if ch.tag != qn("w:rPr"):
            run_el.remove(ch)
    for i, ln in enumerate(lines):
        if i:
            run_el.append(run_el.makeelement(qn("w:br"), {}))
        t = run_el.makeelement(qn("w:t"), {})
        t.text = ln
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        run_el.append(t)


def set_cell_text(tc, text: str):
    ps = tc.findall(qn("w:p"))
    for p in ps[1:]:
        tc.remove(p)
    p = ps[0]
    runs = p.findall(qn("w:r"))
    for r in runs[1:]:
        p.remove(r)
    _set_run_lines(runs[0], str(text).split("\n"))


def rebuild_table(tbl, rows: list[list[str]], vacio_col: int = 1):
    """Conserva la fila de cabecera; clona alternadamente las filas modelo 1 y 2."""
    trs = tbl._tbl.findall(qn("w:tr"))
    protos = [copy.deepcopy(trs[1]), copy.deepcopy(trs[2] if len(trs) > 2 else trs[1])]
    for tr in trs[1:]:
        tbl._tbl.remove(tr)
    if not rows:
        ncols = len(protos[0].findall(qn("w:tc")))
        rows = [["—"] * ncols]
        rows[0][min(vacio_col, ncols - 1)] = SIN_REGISTROS
    for i, vals in enumerate(rows):
        tr = copy.deepcopy(protos[i % 2])
        for tc, v in zip(tr.findall(qn("w:tc")), vals):
            set_cell_text(tc, v)
        tbl._tbl.append(tr)


def replace_text(par: Paragraph, mapping: dict[str, str]):
    """Reemplaza dentro de cada run (conserva negritas)."""
    for r in par.runs:
        t = r.text
        for k, v in mapping.items():
            if k in t:
                t = t.replace(k, v)
        if t != r.text:
            r.text = t


def clonar_parrafo_tras(p_el, texto_base: str | None = None):
    n = copy.deepcopy(p_el)
    p_el.addnext(n)
    return n


# ----------------------------------------------------------------------------- datos
def _fmt(f: date) -> str:
    return f.strftime("%d/%m/%Y")


def _rangos(fechas: list[date], cal, dias_lab) -> str:
    """Agrupa fechas hábiles consecutivas: '15/10 y 16/10/2026', '21/10, 22/10 y 23/10/2026'."""
    fs = sorted(fechas)
    txt = [f.strftime("%d/%m") for f in fs]
    if len(txt) == 1:
        return f"{txt[0]}/{fs[0].year}"
    return ", ".join(txt[:-1]) + f" y {txt[-1]}/{fs[-1].year}"


def _num(x) -> str:
    x = float(x)
    return f"{x:g}"


def construir(d: DatosPeriodo, cite_nro: str | None, fecha_emision: date) -> bytes:
    doc = docx.Document(str(config.TEMPLATE_INFORME))
    ent = d.entidad
    mes_n, anio = MESES[d.mes - 1], d.anio
    ult = d.fin.day
    n_dias_hab = d.dias_habiles()
    h = d.horario
    jornada = " y ".join(f"de {t.hora_entrada:%H:%M} a {t.hora_salida:%H:%M}" for t in h.turnos)
    sigla = ent.sigla or "XXX"
    cite = f"GAM-{sigla}/DAF/URRHH/INF-ASIST/N° {cite_nro or 'S/N (BORRADOR)'}/{anio}"

    # ---------- agregados
    liqs = d.liquidaciones
    por_emp = {l.empleado_id: l for l in liqs}
    dias_hombre = sum(l.dias_laborables for l in liqs)
    normales = defaultdict(int)
    cat_dias = defaultdict(float)
    cat_emp = defaultdict(set)
    faltas_f = defaultdict(list)
    omisiones = defaultdict(list)
    for eid, rows in d.asistencia.items():
        if eid not in por_emp:
            continue
        for a in rows:
            if a.estado == motor.NORMAL:
                normales[eid] += 1
            if a.justificado > 0:
                cat_dias[a.categoria_just] += float(a.justificado)
                cat_emp[a.categoria_just].add(eid)
            if a.falta > 0:
                faltas_f[eid].append(a.fecha)
            if a.estado == motor.OMISION or any(o.startswith("Omisión") for o in a.observacion.split("; ")):
                omisiones[eid].append(a.fecha)
    sin_obs = [e for e, l in por_emp.items() if (l.min_retraso == 0 and l.faltas == 0 and l.dias_justificados == 0
                                                 and e not in omisiones)]
    reg_dias = sum(normales.values())

    def pct(x):
        return f"{(100 * float(x) / float(dias_hombre)):.2f}%" if dias_hombre else "—"

    con_atraso = [l for l in liqs if l.min_retraso > 0 or l.nro_retrasos > 0]
    perm_dias = cat_dias["PERMISO"] + cat_dias["COMISION"]
    perm_emp = cat_emp["PERMISO"] | cat_emp["COMISION"]
    falta_dias = sum(float(l.faltas) for l in liqs)
    indic = [
        ["Total Personal Controlado (Planta, Eventual y Consultores)", str(len(liqs)), f"{float(dias_hombre):g} días-hombre", "100.0%"],
        ["Asistencia Regular Puntual (Sin observaciones)", str(len(sin_obs)), f"{reg_dias} días", pct(reg_dias)],
        ["Personal con Atrasos Acumulados (Sujetos a descuento/llamada)", str(len(con_atraso)),
         f"{sum(l.min_retraso for l in con_atraso)} minutos", "—"],
        [f"Ausencias Justificadas por Vacación Programada (Art. 49 Ley 2027)", str(len(cat_emp['VACACION'])),
         f"{_num(cat_dias['VACACION'])} días", pct(cat_dias["VACACION"])],
        ["Licencias con Goce de Haberes (Baja Médica CNS, Paternidad, Ley 252, etc.)", str(len(cat_emp["LICENCIA"])),
         f"{_num(cat_dias['LICENCIA'])} días", pct(cat_dias["LICENCIA"])],
        ["Permisos Particulares / Comisiones Oficiales (Papeletas aprobadas)", str(len(perm_emp)),
         f"{_num(perm_dias)} días ({_num(perm_dias * float(ent.horas_jornada))} h)", pct(perm_dias)],
        ["Faltas / Ausencias Injustificadas (Sujetas a descuento/sanción)", str(len(faltas_f)),
         f"{_num(falta_dias)} días", pct(falta_dias)],
    ]
    escala_txt = {l.empleado_id: l.sancion for l in liqs}
    atrasos = [[str(i), l.empleado.ci_completo, l.empleado.nombre_completo,
                f"{l.empleado.cargo} / {l.empleado.unidad.nombre}" if l.empleado.unidad else l.empleado.cargo,
                str(l.nro_retrasos), f"{l.min_retraso} min",
                (l.sancion or "Sin sanción (dentro de la escala)") +
                (f" — {_num(l.dias_desc_atrasos)} día(s) de haber" if l.dias_desc_atrasos > 0 and "Descuento" not in l.sancion else "")]
               for i, l in enumerate(sorted(con_atraso, key=lambda x: -x.min_retraso), 1)]

    def dias_habiles_en(p):
        a, b = max(p.fecha_desde, d.ini), min(p.fecha_hasta, d.fin)
        n, x = 0, a
        while x <= b:
            n += d.cal.laborable(x, h.dias_laborables)
            x += timedelta(days=1)
        return n

    vac, lic = [], []
    for p in d.permisos:
        e = p.empleado
        cu = f"{e.cargo} / {e.unidad.nombre}" if e.unidad else e.cargo
        if p.tipo.categoria == "VACACION":
            n = dias_habiles_en(p)
            vac.append([str(len(vac) + 1), e.nombre_completo, cu, p.gestion_vacacion or "—",
                        f"{_fmt(p.fecha_desde)} al {_fmt(p.fecha_hasta)}", f"{n} día(s)", p.saldo_vacacion or "—"])
        else:
            if p.hora_desde:
                periodo = f"{_fmt(p.fecha_desde)} ({p.hora_desde:%H:%M}-{p.hora_hasta:%H:%M})"
                hrs = (p.hora_hasta.hour * 60 + p.hora_hasta.minute - p.hora_desde.hour * 60 - p.hora_desde.minute) / 60
                comp = f"{hrs:g} hrs ({'c/goce' if p.tipo.con_goce else 's/goce'})"
            else:
                periodo = _fmt(p.fecha_desde) if p.fecha_desde == p.fecha_hasta else f"{p.fecha_desde:%d/%m} al {_fmt(p.fecha_hasta)}"
                comp = f"{dias_habiles_en(p)} día(s) {'c/goce' if p.tipo.con_goce else 's/goce'}"
            lic.append([str(len(lic) + 1), e.nombre_completo, p.tipo.nombre,
                        p.doc_respaldo or p.tipo.base_legal or "—", periodo, comp])

    def es_lab(x):
        return d.cal.laborable(x, h.dias_laborables)
    faltas_t, abandonos = [], []
    for eid, fechas in sorted(faltas_f.items(), key=lambda kv: por_emp[kv[0]].empleado.apellidos):
        l = por_emp[eid]
        e = l.empleado
        ab = motor.detectar_abandono(fechas, es_lab)
        accion = f"Descuento ×{_num(l.dias_desc_faltas / l.faltas)} del haber diario ({_num(l.dias_desc_faltas)} día(s))"
        if ab:
            accion = "Remisión a Autoridad Sumariante (Abandono de funciones)"
            abandonos.append(e)
        faltas_t.append([str(len(faltas_t) + 1), e.ci_completo, e.nombre_completo,
                         f"{e.cargo} / {e.unidad.nombre}" if e.unidad else e.cargo,
                         f"{_rangos(fechas, d.cal, h.dias_laborables)} ({_num(l.faltas)} día(s))", accion])
    omis_t = [[str(i), por_emp[eid].empleado.ci_completo, por_emp[eid].empleado.nombre_completo,
               f"{por_emp[eid].empleado.cargo}", _rangos(fs, d.cal, h.dias_laborables),
               "Regularizar con papeleta/justificación (no genera descuento por sí misma)"]
              for i, (eid, fs) in enumerate(sorted(omisiones.items()), 1)]

    # ---------- plantilla: cuerpo
    body = list(doc.element.body.iterchildren())
    paras = {i: Paragraph(el, doc) for i, el in enumerate(body) if el.tag == qn("w:p")}
    tables = doc.tables
    glob = {"[Nombre del Municipio]": ent.nombre.replace("Gobierno Autónomo Municipal de ", "").strip() or ent.nombre,
            "[NOMBRE DEL MUNICIPIO]": ent.nombre.upper()}

    # membrete
    for s in doc.sections:
        for p in s.header.paragraphs:
            for r in p.runs:
                if "[NOMBRE DEL MUNICIPIO]" in r.text:
                    r.text = ent.nombre.upper() + "\n"
    # título / cite
    paras[1].runs[0].text = f"CITE: {cite}"
    # tabla encabezado
    t0 = tables[0]
    vals = [f"{ent.aprobador_nombre or '[Nombre Completo]'}\n{ent.aprobador_cargo.upper()}",
            f"{ent.rrhh_nombre or '[Nombre Completo]'}\n{ent.rrhh_cargo.upper()}",
            f"INFORME MENSUAL DETALLADO DE CONTROL DE ASISTENCIA BIOMÉTRICA, ATRASOS, PERMISOS, LICENCIAS, AUSENCIAS "
            f"Y VACACIONES CORRESPONDIENTE AL MES DE {mes_n.upper()} DE {anio}.",
            f"{ent.ciudad or '[Ciudad/Localidad]'}, {fecha_emision.day:02d} de {MESES[fecha_emision.month - 1]} de {fecha_emision.year}",
            f"Del 01 al {ult} de {mes_n} de {anio} ({n_dias_hab} días hábiles administrativos)"]
    for row, v in zip(t0.rows, vals):
        set_cell_text(row.cells[1]._tc, v)

    # textos con marcadores
    fix_year = lambda t: t.replace("2026", str(anio))  # noqa: E731
    for i in (5,):
        for r in paras[i].runs:
            r.text = fix_year(r.text.replace("[Nombre del Municipio]", glob["[Nombre del Municipio]"])
                              .replace("[30/31]", str(ult)).replace("[Mes]", mes_n))
    for r in paras[13].runs:
        r.text = r.text.replace("[Sigla]", sigla).replace("Decreto Edil N° [XXX/AAAA]", ent.reglamento_rip)
    for r in paras[16].runs:
        r.text = re.sub(r"\[XX\] días hábiles administrativos, bajo jornada discontinua de .*?\)",
                        f"{n_dias_hab} días hábiles administrativos, bajo jornada {'discontinua' if len(h.turnos) > 1 else 'continua'} {jornada})",
                        r.text)
    for r in paras[19].runs:
        r.text = r.text.replace("[5/10]", str(h.tolerancia_min))
    for r in paras[28].runs:
        if ent.factor_falta_planta != 2:
            r.text = r.text.replace("equivalente al doble del haber diario", f"equivalente a {_num(ent.factor_falta_planta)} veces el haber diario")

    rebuild_table(tables[1], indic, 0)
    rebuild_table(tables[2], atrasos, 2)
    rebuild_table(tables[3], vac, 1)
    rebuild_table(tables[4], lic, 1)
    rebuild_table(tables[5], faltas_t, 2)

    # omisiones de marcación (tabla extra tras la de faltas)
    if omis_t:
        t5 = tables[5]._tbl
        intro = copy.deepcopy(paras[28]._p)
        t5.addnext(intro)
        ip = Paragraph(intro, doc)
        ip.runs[0].text = "Omisiones de marcación detectadas (marcas incompletas que deben regularizarse):"
        for r in ip.runs[1:]:
            r.text = ""
        t_om = copy.deepcopy(t5)
        intro.addnext(t_om)
        om = docx.table.Table(t_om, doc)
        hdr = t_om.findall(qn("w:tr"))[0].findall(qn("w:tc"))
        set_cell_text(hdr[4], "FECHAS CON OMISIÓN")
        set_cell_text(hdr[5], "TRATAMIENTO")
        rebuild_table(om, omis_t, 2)

    # conclusiones
    indice = (100 * reg_dias / float(dias_hombre)) if dias_hombre else 0
    concl = [
        f"El control biométrico correspondiente al mes de {mes_n} de {anio} refleja un índice de asistencia regular del "
        f"{indice:.2f}% ({reg_dias} de {float(dias_hombre):g} días-hombre), sobre {len(liqs)} servidores controlados.",
        f"Se recomienda instruir al Área de Planillas y Remuneraciones proceder con la aplicación de los descuentos por "
        f"concepto de atrasos acumulados ({sum(1 for l in liqs if l.dias_desc_atrasos > 0)} servidores) e inasistencias "
        f"injustificadas ({len(faltas_f)} servidores) detallados en los numerales 4 y 7 del presente informe, para su "
        f"incorporación en la planilla salarial del mes."]
    exceso = [l for l in liqs if l.dias_desc_exceso_consultor > 0]
    if exceso:
        concl.append(f"Se recomienda aplicar el descuento por exceso del máximo contractual de ausencias justificadas a "
                     f"{len(exceso)} consultor(es) en línea: " + "; ".join(l.empleado.nombre_completo for l in exceso) + ".")
    if abandonos:
        concl.append("Se recomienda remitir antecedentes de " + ", ".join(e.nombre_completo for e in abandonos) +
                     " a la Autoridad Sumariante del Gobierno Autónomo Municipal, al haberse evidenciado inasistencias "
                     "que configuran abandono de funciones (3 días hábiles continuos o 6 discontinuos en el mes), conforme "
                     "al D.S. N° 23318-A (Reglamento de la Responsabilidad por la Función Pública) y el Reglamento Interno de Personal.")
    concl.append(paras[34].text)  # recomendación de archivo (texto de la plantilla)
    bullets = [paras[i]._p for i in (31, 32, 33, 34)]
    modelo = copy.deepcopy(bullets[0])
    anchor = bullets[-1]
    for b in bullets:
        b.getparent().remove(b)
    prev = paras[30]._p
    for txt in concl:
        n = copy.deepcopy(modelo)
        prev.addnext(n)
        Paragraph(n, doc).runs[0].text = txt
        prev = n

    # firmas
    t6 = tables[6]
    firm = [ent.rrhh_nombre or "[Nombre Completo]", ent.aprobador_nombre or "[Nombre Completo]"]
    cargos = [ent.rrhh_cargo.upper(), ent.aprobador_cargo.upper()]
    for cell, nom, cargo in zip(t6.rows[0].cells, firm, cargos):
        for run_el in cell._tc.iter(qn("w:r")):
            _set_run_lines(run_el, ["_" * 41, "Elaborado y Verificado por:" if cell is t6.rows[0].cells[0]
                                    else "Visto Bueno y Aprobación:", nom, cargo, ent.nombre.upper()])
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()
