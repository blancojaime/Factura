"""Formularios y documentos oficiales en PDF: liquidaciones (F-1980, F-2160, F-501, F-502), boleta resumen, recibo, intimación F-345,
FUC, licencia de funcionamiento con QR verificable, kardex del contribuyente, plan de pagos, certificado de solvencia y hoja de deuda tributaria."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..core.seed import NOMBRE_RUBRO
from ..services import liquidacion as L, padron
from ..services import recaudacion as R
from ..services.base import ServiceError, hoy
from . import engine as E
from .engine import AZUL, AZUL_CLARO, GRIS, LINEA, fmt_date, fmt_num

FORM_TITULO = {"IPBI": ("F-1980", "DECLARACIÓN JURADA Y LIQUIDACIÓN – IMPUESTO A LA PROPIEDAD DE BIENES INMUEBLES"),
               "IPVA": ("F-2160", "DECLARACIÓN JURADA Y LIQUIDACIÓN – IMPUESTO A LA PROPIEDAD DE VEHÍCULOS AUTOMOTORES"),
               "PAF": ("F-501", "DECLARACIÓN JURADA Y LIQUIDACIÓN – PATENTE ANUAL DE FUNCIONAMIENTO"),
               "PUB": ("F-501P", "LIQUIDACIÓN – PATENTE DE PUBLICIDAD Y PROPAGANDA"),
               "IMT": ("F-502/503", "LIQUIDACIÓN – IMPUESTO MUNICIPAL A LAS TRANSFERENCIAS")}


class QRCode(Flowable):
    def __init__(self, text, size=26 * mm):
        super().__init__()
        self.text, self.size = text, size
        self.width = self.height = size

    def draw(self):
        w = qr.QrCodeWidget(self.text)
        b = w.getBounds()
        d = Drawing(self.size, self.size, transform=[self.size / (b[2] - b[0]), 0, 0, self.size / (b[3] - b[1]), 0, 0])
        d.add(w)
        renderPDF.draw(d, self.canv, 0, 0)


def _styles():
    E.setup_fonts()
    f, fb = E.FONT, E.FONT_B
    return dict(
        h1=ParagraphStyle("h1", fontName=fb, fontSize=11.5, leading=14, textColor=AZUL),
        sec=ParagraphStyle("sec", fontName=fb, fontSize=8.5, textColor=colors.white),
        k=ParagraphStyle("k", fontName=f, fontSize=7.5, textColor=GRIS, leading=9),
        v=ParagraphStyle("v", fontName=fb, fontSize=8.5, leading=10.5),
        n=ParagraphStyle("n", fontName=f, fontSize=7.5, textColor=GRIS, leading=9.5),
        c=ParagraphStyle("c", fontName=f, fontSize=8, leading=10), cb=ParagraphStyle("cb", fontName=fb, fontSize=8, leading=10),
        big=ParagraphStyle("big", fontName=fb, fontSize=13, textColor=AZUL, alignment=2))


def _esc(x):
    return str(x if x is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_doc(spec: dict, path, municipio="", usuario="", pagesize=A4):
    """spec: titulo, codigo, nro, qr, bloques[...], total(label,valor), notas[], firmas[]"""
    st = _styles()
    W = pagesize[0] - 30 * mm
    doc = SimpleDocTemplate(str(path), pagesize=pagesize, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=30 * mm, bottomMargin=18 * mm, title=spec["titulo"], author="SIIM 2026")
    el = []
    left = [Paragraph(f"{spec['codigo']}", ParagraphStyle("cd", parent=st["k"], fontSize=9, textColor=AZUL)), Paragraph(spec["titulo"], st["h1"])]
    if spec.get("nro"):
        left.append(Paragraph(f"N° <b>{_esc(spec['nro'])}</b>" + (f" &nbsp;&nbsp; Código de pago: <b>{_esc(spec['codigo_pago'])}</b>" if spec.get("codigo_pago") else ""), st["c"]))
    head = Table([[left, QRCode(spec["qr"]) if spec.get("qr") else ""]], colWidths=[W - 30 * mm, 30 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    el += [head, Spacer(1, 3 * mm)]
    for b in spec["bloques"]:
        rows = [[Paragraph(_esc(b["titulo"]).upper(), st["sec"])] + [""] * 3]
        t = [("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, 0), AZUL), ("BOX", (0, 0), (-1, -1), 0.5, LINEA), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
        if "pares" in b:
            p = b["pares"]
            for i in range(0, len(p), 2):
                row = []
                for k, v in p[i:i + 2]:
                    row += [Paragraph(_esc(k), st["k"]), Paragraph(_esc(v), st["v"])]
                row += [""] * (4 - len(row))
                rows.append(row)
            cw = [W * .17, W * .33, W * .17, W * .33]
            t += [("LINEBELOW", (0, 1), (-1, -1), 0.25, LINEA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
        else:
            cols = b["columnas"]
            rows[0] = [Paragraph(_esc(b["titulo"]).upper(), st["sec"])] + [""] * (len(cols) - 1)
            t[0] = ("SPAN", (0, 0), (-1, 0))
            rows.append([Paragraph(f"<b>{_esc(c)}</b>", st["c"]) for c in cols])
            t.append(("BACKGROUND", (0, 1), (-1, 1), AZUL_CLARO))
            for r in b["filas"]:
                rows.append([Paragraph(_esc(x), st["cb"] if (isinstance(r, (list, tuple)) and r and str(r[0]).startswith("TOTAL")) else st["c"]) for x in r])
            tw = sum(b.get("pesos", [1] * len(cols)))
            cw = [W * w / tw for w in b.get("pesos", [1] * len(cols))]
            t += [("LINEBELOW", (0, 1), (-1, -1), 0.25, LINEA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
            for j in b.get("derecha", []):
                t.append(("ALIGN", (j, 1), (j, -1), "RIGHT"))
        tb = Table(rows, colWidths=cw)
        tb.setStyle(TableStyle(t))
        el += [tb, Spacer(1, 2.5 * mm)]
    if spec.get("total"):
        tt = Table([[Paragraph(_esc(spec["total"][0]).upper(), st["cb"]), Paragraph(spec["total"][1], st["big"])]], colWidths=[W * .6, W * .4])
        tt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, AZUL), ("BACKGROUND", (0, 0), (-1, -1), AZUL_CLARO), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        el += [tt, Spacer(1, 2 * mm)]
    for n in spec.get("notas", []):
        el.append(Paragraph(_esc(n), st["n"]))
    if spec.get("firmas"):
        el.append(Spacer(1, 16 * mm))
        n = len(spec["firmas"])
        fr = Table([[Paragraph(f"<para alignment='center'>______________________________<br/>{_esc(f)}</para>", st["k"]) for f in spec["firmas"]]], colWidths=[W / n] * n)
        el.append(KeepTogether(fr))
    meta = dict(municipio=municipio or "—", usuario=usuario or "—", sistema="SIIM 2026 – Sistema Integrado de Ingresos Municipales")
    rep = type("R", (), dict(code=spec["codigo"]))()
    doc.build(el, onFirstPage=lambda c, d: E._header(c, d, meta, rep), onLaterPages=lambda c, d: E._header(c, d, meta, rep), canvasmaker=lambda *a, **k: E._Numbered(*a, meta=meta, **k))
    return Path(path)


# ---------------------------------------------------------------------------------------------------------- bloques reutilizables
def _nombre(c):
    return padron.nombre_completo(c)


def _bloque_contribuyente(c):
    return {"titulo": "Contribuyente", "pares": [("PMC", c["pmc"]), ("Tipo de persona", {"N": "Natural", "J": "Jurídica", "S": "Sucesión indivisa"}.get(c["persona"], c["persona"])),
            ("Nombre / Razón social", _nombre(c)), ("Documento", f"{c['tipo_doc'] or ''} {c['nro_doc'] or ''} {c['expedido'] or ''}".strip()), ("NIT", c["nit"] or "—"),
            ("Dirección", f"{c['tipo_via'] or ''} {c['calle'] or ''} {c['numero'] or ''} – Zona {c['zona'] or '-'}".strip()), ("Teléfono", c["telefono"] or c["celular"] or "—"), ("Correo", c["email"] or "—")]}


def lineas_detalle(rubro, det: dict):
    """Filas (concepto, valor) legibles de la determinación del impuesto."""
    m = lambda x: fmt_num(x)
    out = []
    if rubro == "IPBI":
        if "alicuota_rural" in det:
            out += [("Valor declarado del inmueble rural", m(det["base_imponible"])), ("Alícuota (%)", fmt_num(det["alicuota_rural"]))]
        else:
            if "valor_m2" in det:
                out += [("Valor por m² (material de vía y zona)", m(det["valor_m2"])), ("Factor de inclinación", fmt_num(det["f_inclinacion"], 2)), ("Factor de servicios", fmt_num(det["f_servicios"], 2))]
            out += [("Valor del terreno", m(det.get("valor_terreno", 0)))]
            if "valor_const_m2" in det:
                out += [("Valor de la construcción por m²", m(det["valor_const_m2"])), ("Factor de depreciación", fmt_num(det["f_depreciacion"], 3))]
            out += [("Valor de la construcción", m(det.get("valor_construccion", 0))), ("Otras construcciones", m(det.get("otras_construcciones", 0)))]
    elif rubro == "IPVA":
        out += [("Código cilindrada", det.get("codigo", "")), ("Valor según tabla (cilindrada–procedencia)", m(det.get("valor_tabla", 0)))]
        if "incremento_chasis_carroceria" in det:
            out.append(("Incremento por chasis y carrocería", fmt_num(det["incremento_chasis_carroceria"], 2)))
        if "ajuste_caracteristicas" in det:
            out.append(("Factor por características especiales", fmt_num(det["ajuste_caracteristicas"], 2)))
        out += [(f"Factor de depreciación (antigüedad {det.get('antiguedad', 0)} años)", fmt_num(det.get("f_depreciacion", 1), 3))]
    elif rubro == "PAF":
        out.append(("Modalidad de cálculo", det.get("modalidad", "")))
        for k, lab in (("patente_maxima", "Patente máxima anual (PMA)"), ("pzs", "Porcentaje zona–superficie (%)"), ("valor_m2", "Valor por m² (PUA)"), ("f_consumo", "Factor de consumo eléctrico"),
                       ("f_actualizacion_dolar", "Factor de actualización por dólar"), ("duodecimas", "Duodécimas (meses de funcionamiento)")):
            if k in det:
                out.append((lab, det[k] if isinstance(det[k], str) else fmt_num(det[k], 2)))
    elif rubro == "PUB":
        out += [("Área del anuncio (m²)", fmt_num(det.get("area_m2", 0))), ("Arancel por m² anual", fmt_num(det.get("valor_m2", 0)))]
    elif rubro == "IMT":
        out += [("Monto de la transferencia", m(det.get("monto_declarado", 0))), (f"Base IPBI/IPVA gestión {det.get('gestion_base') or '—'}", m(det.get("base_gestion", 0))), ("Alícuota (%)", fmt_num(det.get("alicuota", 3)))]
    out.append(("BASE IMPONIBLE", m(det.get("base_imponible", 0))))
    if det.get("nota"):
        out.append(("Observación", det["nota"]))
    return out


def _detalle_bloque(rubro, det):
    return {"titulo": "Determinación del impuesto", "columnas": ["Concepto", "Valor"], "filas": [list(x) for x in lineas_detalle(rubro, det)], "pesos": [3, 1.2], "derecha": [1]}


def _importes(rubro, d_, pago=None):
    f = lambda x: fmt_num(x)
    rows = [["Impuesto determinado", f(d_["impuesto"])]]
    if d_.get("credito"):
        rows.append(["(–) Pagos a cuenta / liquidaciones anteriores", f(d_["credito"])])
    rows.append(["IMPUESTO NETO", f(d_["neto"])])
    return {"titulo": "Importes", "columnas": ["Concepto", "Bs"], "filas": rows, "pesos": [3, 1.2], "derecha": [1]}


def _fechas_bloque(db, liq_or_pre):
    pares = []
    try:
        rubro = liq_or_pre["rubro"]
        if rubro == "IMT":
            pares.append(("Fecha límite de pago (10 días hábiles)", fmt_date(liq_or_pre["fecha_venc"])))
        else:
            fe = L.fechas(db, rubro, liq_or_pre["gestion"])
            pares += [("Pago al contado (con descuento) hasta", fmt_date(fe["contado"])), ("Sin descuento ni accesorios hasta", fmt_date(fe["sin_accesorios"] or fe["contado"]))]
            if liq_or_pre["forma_pago"] == "CUOTAS":
                pares += [("1.ª cuota hasta", fmt_date(fe["cuota1"])), ("2.ª cuota hasta", fmt_date(fe["cuota2"]))]
    except ServiceError:
        pass
    return {"titulo": "Plazos de pago", "pares": pares} if pares else None


def _pie(db):
    return [f"Base legal: {db.param('base_legal')}. Documento generado por SIIM 2026; vence el plazo indicado, pasada la fecha se aplican accesorios de la Deuda Tributaria (mantenimiento de valor, intereses y multa por deberes formales) – Art. 47 Ley 2492 y DS 27310.",
            "Esta liquidación tiene carácter de declaración jurada del contribuyente."]


def spec_liquidacion(ctx, liq_id, preliminar=None):
    db = ctx.db
    if preliminar is not None:
        liq = dict(preliminar, nro="PRELIMINAR", codigo_pago="", fecha=hoy(), estado="PRELIMINAR", forma_pago=preliminar["forma_pago"])
        det = preliminar["detalle"]
    else:
        liq = dict(db.one("SELECT * FROM liquidaciones WHERE id=?", (liq_id,)))
        det = json.loads(liq["detalle"] or "{}")
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (liq["pmc"],))
    code, titulo = FORM_TITULO[liq["rubro"]]
    if preliminar is not None:
        titulo = "BOLETA RESUMEN (PRELIQUIDACIÓN) – " + NOMBRE_RUBRO[liq["rubro"]].upper()
    bl = [_bloque_contribuyente(c),
          {"titulo": "Bien / actividad liquidada", "pares": [("Rubro", NOMBRE_RUBRO[liq["rubro"]]), ("Gestión", liq["gestion"]), ("Descripción", liq["objeto_desc"]), ("Tipo de liquidación", f"{liq['tipo_liq']} – {liq['forma_pago'].replace('CUOTAS', 'EN DOS CUOTAS')}")] if liq["rubro"] != "IMT" else
           [("Rubro", NOMBRE_RUBRO["IMT"]), ("Año", liq["gestion"]), ("Bien transferido", liq["objeto_desc"]), ("Comprador PMC", det.get("comprador", ""))]},
          _detalle_bloque(liq["rubro"], det), _importes(liq["rubro"], liq)]
    if liq.get("cuotas") or (preliminar is None and db.scalar("SELECT COUNT(*) FROM liq_cuotas WHERE liq_id=?", (liq_id,), 0)):
        cu = liq.get("cuotas") or [dict(r) for r in db.all("SELECT * FROM liq_cuotas WHERE liq_id=? ORDER BY nro", (liq_id,))]
        bl.append({"titulo": "Cuotas", "columnas": ["Cuota", "Vencimiento", "Monto Bs"], "filas": [[x["nro"], fmt_date(x["vence"]), fmt_num(x["monto"])] for x in cu], "pesos": [1, 2, 2], "derecha": [2]})
    fb = _fechas_bloque(db, liq)
    if fb:
        bl.append(fb)
    qrtxt = f"SIIM|{liq['rubro']}|{liq['nro']}|{liq.get('codigo_pago','')}|{liq['neto']}|{liq['pmc']}"
    return dict(titulo=titulo, codigo=code if preliminar is None else "BOLETA RESUMEN", nro=liq["nro"], codigo_pago=liq.get("codigo_pago"), qr=qrtxt, bloques=bl,
                total=("Importe neto a pagar al vencimiento (Bs)", fmt_num(liq["neto"])), notas=_pie(db) + ([f"Saldo a favor por pagos anteriores: Bs {fmt_num(det['saldo_favor'])}"] if det.get("saldo_favor") else []),
                firmas=["Contribuyente", "Liquidador municipal"])


def spec_recibo(ctx, pago_id):
    db = ctx.db
    p = db.one("SELECT * FROM pagos WHERE id=?", (pago_id,))
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (p["pmc"],))
    l = db.one("SELECT * FROM liquidaciones WHERE id=?", (p["liq_id"],))
    f = fmt_num
    filas = [["Impuesto / tributo", f(p["monto_neto"])]]
    for lab, k in (("(–) Descuento por pago al contado", "descuento"), ("(+) Mantenimiento de valor", "mant_valor"), ("(+) Intereses", "interes"), ("(+) Multa por incumplimiento de deberes formales", "multa_df"), ("(+) Sanción administrativa", "sancion")):
        if p[k]:
            filas.append([lab, f(p[k])])
    filas.append(["TOTAL PAGADO", f(p["total"])])
    det = json.loads(p["detalle"] or "{}")
    bl = [_bloque_contribuyente(c), {"titulo": "Concepto", "pares": [("Liquidación", l["nro"] if l else "—"), ("Rubro", NOMBRE_RUBRO.get(p["rubro"], p["rubro"])), ("Gestión", p["gestion"]), ("Bien", l["objeto_desc"] if l else ""),
                                                                      ("Fecha y hora", f"{fmt_date(p['fecha'])} {p['hora'] or ''}"), ("Modalidad", f"{p['modalidad']} {p['entidad'] or ''}")]},
          {"titulo": "Detalle del pago", "columnas": ["Concepto", "Bs"], "filas": filas, "pesos": [3, 1.2], "derecha": [1]}]
    if det.get("mora"):
        bl.append({"titulo": "Cálculo de accesorios", "pares": [("Días de mora", det["mora"]), ("UFV vencimiento", det.get("ufv_fv")), ("UFV de pago", det.get("ufv_fp")), ("Tasa anual r", fmt_num(det.get("r", 0) * 100) + " %")]})
    return dict(titulo="RECIBO OFICIAL DE PAGO", codigo="RECIBO", nro=p["nro_recibo"], qr=f"SIIM|REC|{p['nro_recibo']}|{p['total']}|{p['fecha']}", bloques=bl,
                total=("Total pagado (Bs)", fmt_num(p["total"]) + (" – ANULADO" if p["estado"] != "VIGENTE" else "")), notas=["Conserve este recibo como comprobante de pago. Anulado: " + (p["anulado_motivo"] or "no") if p["estado"] != "VIGENTE" else "Conserve este recibo como comprobante de pago."],
                firmas=["Cajero", "Contribuyente"])


def spec_intimacion(ctx, pmc, plazo_dias=10, guardar=True):
    """F-345 Intimación por falta de pago: lista deudas (liquidadas y no liquidadas vencidas) a la fecha."""
    db = ctx.db
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (pmc,))
    filas = [f for f in R.cuenta_corriente(ctx, pmc, True) if f["a_pagar"] > 0]
    if not filas:
        raise ServiceError("El contribuyente no tiene deudas vencidas.")
    total = sum(f["a_pagar"] for f in filas)
    nro = None
    if guardar:
        from ..services.base import numero
        nro = numero(db, "F345")
        db.insert("intimaciones", dict(nro=nro, pmc=pmc, fecha=hoy(), plazo_dias=plazo_dias, deuda=total, detalle=json.dumps(filas, default=str), usuario=ctx.user))
        ctx.log("INTIMACION", "intimaciones", nro, {"pmc": pmc, "deuda": total})
    bl = [_bloque_contribuyente(c), {"titulo": "Deuda tributaria exigible", "columnas": ["Gestión", "Rubro", "Bien / actividad", "Impuesto", "Deuda a hoy"],
                                      "filas": [[f["gestion"], f["rubro"], f["objeto"], fmt_num(f["impuesto"]), fmt_num(f["a_pagar"])] for f in filas] + [["TOTAL", "", "", "", fmt_num(total)]], "pesos": [.7, .7, 4, 1.2, 1.3], "derecha": [3, 4]}]
    return dict(titulo="INTIMACIÓN POR FALTA DE PAGO", codigo="F-345", nro=nro or "(vista previa)", qr=f"SIIM|F345|{nro}|{pmc}|{total}", bloques=bl, total=("Deuda total a la fecha (Bs)", fmt_num(total)),
                notas=[f"Se intima al contribuyente a cancelar su obligación tributaria en el plazo de {plazo_dias} días hábiles computables desde su notificación, bajo apercibimiento de iniciar la ejecución tributaria (cobranza coactiva) conforme a los Arts. 108 y siguientes de la Ley 2492. Las acciones de la Administración Tributaria prescriben a los 4 años (Art. 59).",
                       "La deuda incluye mantenimiento de valor, intereses y multa por incumplimiento de deberes formales calculados a la fecha de emisión (Art. 47 Ley 2492)."] + _pie(db)[:1],
                firmas=["Jefe de la Administración Tributaria Municipal", "Recibí conforme (contribuyente)"])


def spec_fuc(ctx, fid):
    db = ctx.db
    f = db.one("SELECT * FROM fuc WHERE id=?", (fid,))
    det = db.all("SELECT * FROM fuc_det WHERE fuc_id=? ORDER BY id", (fid,))
    bl = [{"titulo": "Datos del formulario", "pares": [("Nombre", f["nombre"]), ("Documento", f["documento"] or "—"), ("Fecha", fmt_date(f["fecha"])), ("Hora", f["hora"]), ("Estado", f["estado"]), ("Detalle", f["detalle"] or "—")]},
          {"titulo": "Conceptos", "columnas": ["Rubro", "Subnivel", "Descripción", "Costo", "Cant.", "Total"], "filas": [[d["rubro"], d["subnivel"], d["descripcion"], fmt_num(d["costo"]), fmt_num(d["cantidad"], 0 if float(d["cantidad"]).is_integer() else 2), fmt_num(d["total"])] for d in det],
           "pesos": [.8, 1.1, 3.4, .9, .6, 1], "derecha": [3, 4, 5]}]
    return dict(titulo="FORMULARIO ÚNICO DE CAJA (FUC)", codigo="FUC", nro=f["nro"], qr=f"SIIM|FUC|{f['nro']}|{f['total']}", bloques=bl, total=("Total a recaudar (Bs)", fmt_num(f["total"])),
                notas=[f"Estado: {f['estado']}" + (f" – pagado el {fmt_date(f['fecha_pago'])} por {f['cajero']}" if f["fecha_pago"] else " – pendiente de pago en caja")], firmas=["Cajero", "Contribuyente"])


def sello_licencia(db, a) -> str:
    sec = db.param("sello_secreto")
    if not sec:
        import secrets
        sec = secrets.token_hex(16)
        db.set_param("sello_secreto", sec)
    return hashlib.sha256(f"{sec}|{a['nro_licencia']}|{a['pmc']}|{a['licencia_vence']}".encode()).hexdigest()[:10].upper()


def verificar_licencia(db, nro, sello) -> dict:
    a = db.one("SELECT * FROM actividades WHERE nro_licencia=?", (nro.strip(),))
    if not a:
        return dict(valida=False, motivo="Número de licencia inexistente")
    ok = sello_licencia(db, a) == sello.strip().upper()
    vig = a["estado"] == "ACTIVO" and a["estado_licencia"] == "VIGENTE" and (a["licencia_vence"] or "") >= hoy()
    return dict(valida=ok, vigente=ok and vig, estado=a["estado_licencia"], vence=a["licencia_vence"], establecimiento=a["nombre_comercial"], pmc=a["pmc"],
                motivo="" if ok else "El sello no coincide: documento alterado")


def spec_licencia(ctx, act_id):
    db = ctx.db
    a = db.one("SELECT * FROM actividades WHERE id=?", (act_id,))
    if not a or not a["nro_licencia"]:
        raise ServiceError("La actividad no tiene licencia emitida.")
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (a["pmc"],))
    tipo = db.scalar("SELECT descripcion FROM act_tipos WHERE codigo=?", (a["act"],), "")
    cat = db.scalar("SELECT descripcion FROM act_categorias WHERE act=? AND cat=?", (a["act"], a["cat"]), "")
    ultima = db.one("SELECT gestion FROM liquidaciones WHERE rubro='PAF' AND objeto_id=? AND estado='PAGADA' ORDER BY gestion DESC LIMIT 1", (act_id,))
    sello = sello_licencia(db, a)
    exento = a["exento"] and a["exento"] != "NINGUNO"
    bl = [_bloque_contribuyente(c), {"titulo": "Establecimiento autorizado", "pares": [("Nombre comercial", a["nombre_comercial"] or "—"), ("Actividad", f"{a['act']}-{a['cat']} {tipo}"), ("Categoría", cat), ("CIIU", a["ciiu"] or "—"),
          ("Ubicación", f"{a['tipo_via'] or ''} {a['calle'] or ''} {a['numero'] or ''} – Zona {a['zona'] or '-'}"), ("Superficie", f"{fmt_num(a['superficie'])} m²"), ("Inicio de actividades", fmt_date(a["fecha_inicio"])),
          ("Última patente pagada", f"Gestión {ultima['gestion']}" if ultima else ("Exento de la Patente de Funcionamiento" if exento else "—"))]},
          {"titulo": "Vigencia", "pares": [("Fecha de emisión", fmt_date(a["licencia_emision"])), ("Válida hasta", fmt_date(a["licencia_vence"])), ("Código de verificación", sello), ("Estado", a["estado_licencia"])]}]
    return dict(titulo="LICENCIA DE FUNCIONAMIENTO", codigo="LICENCIA", nro=a["nro_licencia"], qr=f"SIIM-LIC|{a['nro_licencia']}|{sello}|{a['licencia_vence']}", bloques=bl, total=("Vigente hasta", fmt_date(a["licencia_vence"])),
                notas=["La presente licencia autoriza el funcionamiento de la actividad económica descrita, en el domicilio indicado, previo pago de la Patente de Funcionamiento de la gestión. Debe exhibirse en lugar visible.",
                       "Verificación: escanee el QR o ingrese el número y el código de verificación en SIIM 2026 ▸ Actividades ▸ Verificar licencia. Todo documento adulterado será sancionado.", f"Base legal: {db.param('base_legal')}"],
                firmas=["Alcalde Municipal / Jefe Tributario"])


def spec_kardex(ctx, pmc):
    db = ctx.db
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (pmc,))
    bl = [_bloque_contribuyente(c)]
    inm = padron.objetos(db, "inmuebles", pmc)
    if inm:
        bl.append({"titulo": "Bienes inmuebles", "columnas": ["Tipo", "Dirección", "Zona", "Sup. m²", "Constr. m²", "Año", "Exención"], "filas": [[i["tipo"], f"{i['calle'] or ''} {i['numero'] or ''}", i["zona"], fmt_num(i["superficie"]), fmt_num(i["sup_construida"]), i["anio_construccion"] or "", i["exento"]] for i in inm],
                   "pesos": [1, 2.5, .6, .9, .9, .6, 1.2], "derecha": [3, 4]})
    veh = padron.objetos(db, "vehiculos", pmc)
    if veh:
        bl.append({"titulo": "Vehículos automotores", "columnas": ["Placa", "Tipo", "Marca / modelo", "Año", "cc", "Procedencia", "Exención"], "filas": [[v["placa"], v["tipo"], f"{v['marca'] or ''} {v['modelo'] or ''}", v["anio_fab"], v["cilindrada"], v["procedencia"], v["exento"]] for v in veh],
                   "pesos": [1, 1.2, 2, .6, .7, 1.4, 1.1]})
    act = padron.objetos(db, "actividades", pmc)
    if act:
        bl.append({"titulo": "Actividades económicas", "columnas": ["Establecimiento", "Act-Cat", "Zona", "m²", "Inicio", "Licencia", "Estado"], "filas": [[a["nombre_comercial"], f"{a['act']}-{a['cat']}", a["zona"], fmt_num(a["superficie"]), fmt_date(a["fecha_inicio"]), a["nro_licencia"] or "—", a["estado_licencia"]] for a in act],
                   "pesos": [2.2, .8, .6, .8, 1, 1.3, 1.1], "derecha": [3]})
    pub = padron.objetos(db, "publicidad", pmc)
    if pub:
        bl.append({"titulo": "Publicidad y propaganda", "columnas": ["Tipo", "Descripción", "Ubicación", "m²"], "filas": [[p["tipo"], p["descripcion"], p["ubicacion"], fmt_num(p["ancho"] * p["alto"])] for p in pub], "pesos": [1.3, 2.5, 2.2, .7], "derecha": [3]})
    form = db.all("SELECT * FROM emp_formularios WHERE pmc=? ORDER BY id", (pmc,))
    bl.append({"titulo": "Historial de formularios", "columnas": ["Fecha", "Formulario", "N° orden", "Usuario"], "filas": [[fmt_date(f["fecha"]), f["tipo"], f["nro_orden"], f["usuario"]] for f in form] or [["—", "", "", ""]], "pesos": [1, 1, 1, 1]})
    return dict(titulo="KARDEX DEL CONTRIBUYENTE – PADRÓN MUNICIPAL (PMC)", codigo="KARDEX", nro=str(pmc), qr=f"SIIM|PMC|{pmc}", bloques=bl, notas=[f"Estado del registro: {c['estado']} – Registrado el {fmt_date(c['fecha_registro'])}"], firmas=["Contribuyente", "Responsable del padrón"])


def spec_plan(ctx, plan_id):
    db = ctx.db
    p = db.one("SELECT * FROM planes_pago WHERE id=?", (plan_id,))
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (p["pmc"],))
    liqs = db.all("SELECT l.nro,l.rubro,l.gestion,l.objeto_desc,pl.deuda FROM plan_liqs pl JOIN liquidaciones l ON l.id=pl.liq_id WHERE pl.plan_id=?", (plan_id,))
    q = db.all("SELECT * FROM plan_cuotas WHERE plan_id=? ORDER BY nro", (plan_id,))
    bl = [_bloque_contribuyente(c), {"titulo": "Deudas incluidas en el plan", "columnas": ["Liquidación", "Rubro", "Gestión", "Bien", "Deuda Bs"], "filas": [[x["nro"], x["rubro"], x["gestion"], x["objeto_desc"], fmt_num(x["deuda"])] for x in liqs], "pesos": [1.4, .7, .7, 3, 1.1], "derecha": [4]},
          {"titulo": f"Cronograma de pagos – {p['n_cuotas']} cuotas, interés anual {fmt_num(p['tasa_anual'] * 100)} %", "columnas": ["Cuota", "Vence", "Capital", "Interés", "Monto", "Saldo", "Estado"],
           "filas": [["Inicial" if x["nro"] == 0 else x["nro"], fmt_date(x["vence"]), fmt_num(x["capital"]), fmt_num(x["interes"]), fmt_num(x["monto"]), fmt_num(x["saldo"]), x["estado"]] for x in q], "pesos": [.8, 1, 1.1, 1, 1.1, 1.1, 1], "derecha": [2, 3, 4, 5]}]
    return dict(titulo="PLAN DE PAGOS – FACILIDADES DE PAGO", codigo="PLAN DE PAGOS", nro=p["nro"], qr=f"SIIM|PLAN|{p['nro']}|{p['deuda_total']}", bloques=bl, total=("Deuda total financiada (Bs)", fmt_num(p["deuda_total"])),
                notas=["Facilidades de pago concedidas por una sola vez con carácter improrrogable (Art. 55 Ley 2492). El incumplimiento de una cuota deja sin efecto el plan y habilita la ejecución tributaria por el saldo.", f"Resolución: {p['resolucion'] or '—'}"],
                firmas=["Contribuyente", "Administración Tributaria Municipal"])


def spec_solvencia(ctx, pmc):
    db = ctx.db
    c = db.one("SELECT * FROM contribuyentes WHERE pmc=?", (pmc,))
    deudas = [f for f in R.cuenta_corriente(ctx, pmc, True) if f["a_pagar"] > 0]
    solvente = not deudas
    bl = [_bloque_contribuyente(c)]
    if deudas:
        bl.append({"titulo": "Obligaciones pendientes", "columnas": ["Gestión", "Rubro", "Detalle", "Deuda Bs"], "filas": [[d["gestion"], d["rubro"], d["objeto"], fmt_num(d["a_pagar"])] for d in deudas], "pesos": [.8, .8, 4, 1.2], "derecha": [3]})
    return dict(titulo="CERTIFICADO DE SOLVENCIA MUNICIPAL", codigo="SOLVENCIA", nro=f"{pmc}-{hoy()}", qr=f"SIIM|SOLV|{pmc}|{hoy()}|{int(solvente)}", bloques=bl,
                total=("Resultado", "SOLVENTE" if solvente else "CON DEUDA"), notas=[f"A la fecha {fmt_date(hoy())}, el contribuyente " + ("NO registra obligaciones tributarias vencidas pendientes de pago en el Padrón Municipal de Contribuyentes." if solvente else "registra obligaciones tributarias vencidas pendientes de pago (detalle arriba).") + " Sujeto a verificación de gestiones no empadronadas."],
                firmas=["Responsable Tributario"])


def spec_calculo_deuda(d, datos: dict, municipio=""):
    f = fmt_num
    bl = [{"titulo": "Datos", "pares": [(k, v) for k, v in datos.items()]},
          {"titulo": "Cálculo de la Deuda Tributaria", "columnas": ["Componente", "Valor"], "filas": [["Tributo omitido (TO)", f(d.to_bs)], ["Días de mora (n)", str(d.mora)], ["Mantenimiento de valor (Mv)", f(d.mv)], ["TO + Mv", f(d.to_mv)],
                                                                                                         ["Intereses", f(d.interes)], [f"Multa deberes formales ({f(d.multa_ufv)} UFV)", f(d.multa_bs)], ["Sanción administrativa", f(d.sancion)], ["TOTAL DEUDA TRIBUTARIA", f(d.total)]], "pesos": [3, 1.3], "derecha": [1]}]
    return dict(titulo="HOJA DE CÁLCULO DE LA DEUDA TRIBUTARIA", codigo="DEUDA", nro="", bloques=bl, total=("Deuda tributaria (Bs)", f(d.total)),
                notas=["DT = TO × (1 + r/360)^n + M (Art. 47 Ley 2492; DS 27310). " + ("Deuda anterior al 26/12/2002: se actualiza con el tipo de cambio del dólar al 26/12/2002." if d.anterior_2002 else "Deuda posterior al 26/12/2002: mantenimiento de valor con la UFV.")])


def generar(ctx, spec, path):
    return render_doc(spec, path, ctx.db.param("municipio", ""), ctx.user)
