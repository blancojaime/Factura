"""PDF de boleta de permiso e instructivo (reportlab, tamaño Carta)."""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import Entidad, Instructivo, Permiso

AZUL = colors.HexColor("#1B365D")
SS = getSampleStyleSheet()
N = ParagraphStyle("n", parent=SS["Normal"], fontName="Helvetica", fontSize=10, leading=13)
NJ = ParagraphStyle("nj", parent=N, alignment=4)
T = ParagraphStyle("t", parent=N, fontName="Helvetica-Bold", fontSize=13, alignment=1, textColor=AZUL, spaceAfter=6)
C = ParagraphStyle("c", parent=N, alignment=1, fontSize=9, textColor=colors.HexColor("#555555"))


def _membrete(ent: Entidad):
    return [Paragraph("ESTADO PLURINACIONAL DE BOLIVIA", C),
            Paragraph(f"<b>{escape(ent.nombre.upper())}</b>", ParagraphStyle("m", parent=C, fontSize=11, textColor=AZUL)),
            Paragraph("UNIDAD DE RECURSOS HUMANOS", C), Spacer(1, 10)]


def _firma(textos):
    t = Table([[Paragraph(f"<br/><br/>_______________________________<br/>{escape(x)}", C) for x in textos]],
              colWidths=[(LETTER[0] - 4 * cm) / len(textos)] * len(textos))
    return t


def boleta_pdf(p: Permiso, ent: Entidad) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title=f"Boleta {p.nro_boleta}")
    e = p.empleado
    horas = f"{p.hora_desde:%H:%M} a {p.hora_hasta:%H:%M}" if p.hora_desde else "Jornada completa"
    periodo = f"{p.fecha_desde:%d/%m/%Y}" + (f" al {p.fecha_hasta:%d/%m/%Y}" if p.fecha_hasta != p.fecha_desde else "")
    filas = [["N° de boleta", p.nro_boleta], ["Servidor(a)", e.nombre_completo], ["C.I.", e.ci_completo],
             ["Cargo / Unidad", f"{e.cargo} / {e.unidad.nombre if e.unidad else '—'}"], ["Tipo", p.tipo.nombre],
             ["Con goce de haberes", "SÍ" if p.tipo.con_goce else "NO"], ["Fecha(s)", periodo], ["Horario", horas],
             ["Motivo", p.motivo or "—"], ["Respaldo", p.doc_respaldo or "—"], ["Estado", p.estado]]
    if p.tipo.categoria == "VACACION":
        filas.append(["Gestión / saldo", f"{p.gestion_vacacion or '—'} / {p.saldo_vacacion or '—'}"])
    tb = Table([[Paragraph(f"<b>{escape(a)}</b>", N), Paragraph(escape(str(b)), N)] for a, b in filas],
               colWidths=[4.5 * cm, 12.5 * cm])
    tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F4F8")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    el = _membrete(ent) + [Paragraph("BOLETA DE PERMISO / SALIDA", T), tb, Spacer(1, 14),
                           Paragraph("El presente documento actualiza automáticamente el control de asistencia del periodo. "
                                     "Las marcas biométricas originales no se modifican.", C), Spacer(1, 40),
                           _firma(["Solicitante", f"Autorizado: {p.autorizado_por or 'Inmediato superior'}", "Vo.Bo. Recursos Humanos"])]
    doc.build(el)
    return buf.getvalue()


def instructivo_pdf(i: Instructivo, ent: Entidad) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title=i.cite)
    dest = "; ".join(f"{d.empleado.nombre_completo}" for d in i.destinatarios[:40])
    if len(i.destinatarios) > 40:
        dest += f" y {len(i.destinatarios) - 40} más"
    cuerpo = [Paragraph(escape(par).replace("\n", "<br/>"), NJ) for par in i.contenido.split("\n\n")]
    el = _membrete(ent) + [Paragraph(f"INSTRUCTIVO {escape(i.cite)}", T), Paragraph(escape(i.titulo), ParagraphStyle("tt", parent=T, fontSize=11)),
                           Paragraph(f"<b>Fecha de emisión:</b> {i.fecha_emision:%d/%m/%Y}", N),
                           Paragraph(f"<b>Destinatarios ({len(i.destinatarios)}):</b> {escape(dest)}", N), Spacer(1, 10)]
    for c in cuerpo:
        el += [c, Spacer(1, 6)]
    el += [Spacer(1, 40), _firma([f"{ent.rrhh_nombre or ''}\n{ent.rrhh_cargo}".replace("\n", " — ")])]
    doc.build(el)
    return buf.getvalue()
