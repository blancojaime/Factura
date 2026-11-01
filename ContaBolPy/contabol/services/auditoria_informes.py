"""Redacción de dictámenes e informes de auditoría (NIA 700/705/706 y tributarios) a partir de los papeles de trabajo."""
from __future__ import annotations

from ..util import fdate, to_date

OPINIONES = {
    "LIMPIA": "Opinión no modificada (limpia)", "SALVEDAD": "Opinión con salvedades", "ADVERSA": "Opinión adversa", "ABSTENCION": "Abstención de opinión",
}
CLASES_F = {"NIA700": "Dictamen de auditoría de estados financieros (NIA 700)", "NIA705": "Dictamen con opinión modificada (NIA 705)", "NIA706": "Párrafos de énfasis y otras cuestiones (NIA 706)"}
CLASES_T = {"DICTAMEN_TRIBUTARIO": "Dictamen Tributario", "PROCEDIMIENTOS_MINIMOS": "Informe de procedimientos mínimos tributarios", "SITUACION_TRIBUTARIA": "Informe sobre la situación tributaria"}

AVISO = ("Borrador generado por el sistema a partir de los papeles de trabajo. Debe ser revisado y adaptado por el profesional responsable; el modelo oficial del Dictamen Tributario "
         "y la adopción vigente de las NIA en Bolivia deben verificarse con el CAUB/CTNAC y el SIN.")


class InformesAuditoriaService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def _datos(self, eid):
        a = self.ctx.auditoria
        e = a.encargo(eid)
        return e, self.ctx.empresa, a.materialidad(eid), a.resumen_desvios(eid), a.hallazgos(eid)

    def borrador_nia700(self, eid: int, opinion: str | None = None, kam: list[dict] | None = None, enfasis: str = "") -> dict:
        e, emp, mat, res, hall = self._datos(eid)
        sug, motivo = self.ctx.auditoria.sugerir_opinion(eid)
        op = opinion or sug
        fin = fdate(to_date(e["periodo_fin"]))
        cab = f"A los señores Socios / Directores de {emp['razon_social']}"
        base_op = (f"Hemos auditado los estados financieros de {emp['razon_social']} (NIT {emp.get('nit') or 's/n'}), que comprenden el Balance General al {fin}, el Estado de Resultados, "
                   "el Estado de Evolución del Patrimonio Neto, el Estado de Flujo de Efectivo y las Notas a los estados financieros por el período terminado en esa fecha.")
        if op == "LIMPIA":
            opin = ("En nuestra opinión, los estados financieros adjuntos presentan razonablemente, en todos los aspectos significativos, la situación patrimonial y financiera de la empresa al "
                    f"{fin}, así como sus resultados, la evolución del patrimonio y sus flujos de efectivo por el período terminado en esa fecha, de conformidad con las Normas de Contabilidad "
                    "Generalmente Aceptadas en Bolivia.")
            fund = "Hemos llevado a cabo nuestra auditoría de conformidad con las Normas de Auditoría Generalmente Aceptadas en Bolivia / Normas Internacionales de Auditoría. Somos independientes de la empresa y hemos cumplido las demás responsabilidades éticas."
        elif op == "SALVEDAD":
            opin = ("Excepto por los efectos de la cuestión descrita en el párrafo «Fundamento de la opinión con salvedades», los estados financieros presentan razonablemente, en todos los aspectos "
                    f"significativos, la situación patrimonial y financiera de la empresa al {fin}, de conformidad con las Normas de Contabilidad Generalmente Aceptadas en Bolivia.")
            fund = ("Fundamento de la opinión con salvedades: " + "; ".join(f"{h['codigo']}: {h['condicion']} (efecto estimado Bs {h['impacto_monto']:,.2f})" for h in hall if h["nivel"] in ("A", "M") and h["impacto_monto"]) +
                    f". Las incorrecciones no corregidas ascienden a Bs {res['no_corregidos_no_triviales']:,.2f} frente a una materialidad global de Bs {res['materialidad_global']:,.2f}.")
        elif op == "ADVERSA":
            opin = (f"En nuestra opinión, debido a la significatividad de la cuestión descrita en el fundamento, los estados financieros NO presentan razonablemente la situación patrimonial y financiera al {fin} "
                    "de conformidad con las Normas de Contabilidad Generalmente Aceptadas en Bolivia.")
            fund = f"Fundamento de la opinión adversa: las incorrecciones no corregidas (Bs {res['no_corregidos_no_triviales']:,.2f}) son materiales y generalizadas."
        else:
            opin = "No expresamos una opinión sobre los estados financieros adjuntos. Debido a la significatividad de la cuestión descrita en el fundamento, no hemos podido obtener evidencia de auditoría suficiente y adecuada."
            fund = "Fundamento de la abstención de opinión: limitación al alcance de nuestro trabajo (NIA 705)."
        kam_txt = "\n".join(f"• {k['titulo']}: {k['descripcion']} Respuesta de auditoría: {k['respuesta']}" for k in (kam or [])) if kam else ""
        texto = "\n\n".join(x for x in (
            "DICTAMEN DEL AUDITOR INDEPENDIENTE", cab, ("Opinión\n" if op in ("LIMPIA", "SALVEDAD", "ADVERSA") else "Abstención de opinión\n") + base_op + " " + opin, "Fundamento\n" + fund,
            ("Cuestiones clave de la auditoría (NIA 701)\n" + kam_txt) if kam_txt else "", ("Párrafo de énfasis (NIA 706)\n" + enfasis) if enfasis else "",
            "Responsabilidades de la Gerencia y del auditor\nLa Gerencia es responsable de la preparación y presentación razonable de los estados financieros y del control interno necesario. "
            "Nuestra responsabilidad es expresar una opinión sobre ellos con base en nuestra auditoría, planificada y ejecutada para obtener seguridad razonable de que no contienen incorrecciones materiales.",
            f"Lugar y fecha: {emp.get('ciudad') or ''}, {fdate(to_date(e['periodo_fin']))}\nFirma del profesional responsable: ____________________", f"[{AVISO}]") if x)
        return {"clase": "NIA705" if op != "LIMPIA" else "NIA700", "opinion": op, "opinion_sugerida": sug, "motivo_sugerencia": motivo, "texto": texto, "kam": kam_txt, "enfasis": enfasis}

    def kam_desde_hallazgos(self, eid: int, solo_altos: bool = True) -> list[dict]:
        out = []
        for h in self.ctx.auditoria.hallazgos(eid):
            if h["nivel"] == "A" or not solo_altos:
                out.append({"titulo": h["componente"] or h["codigo"], "descripcion": h["condicion"], "respuesta": h["recomendacion"] or "Procedimientos sustantivos ampliados."})
        return out

    def borrador_tributario(self, eid: int, clase: str = "DICTAMEN_TRIBUTARIO") -> dict:
        e, emp, mat, res, hall = self._datos(eid)
        trib = self.ctx.aud_trib
        iva, ban, iue = trib.conciliacion_iva_it(eid), trib.bancarizacion(eid), trib.cedula_iue(eid)
        fin = fdate(to_date(e["periodo_fin"]))
        sit = trib.situacion_tributaria(eid)
        hall_t = "\n".join(f"{h['codigo']}. Condición: {h['condicion']}\n   Criterio: {h['criterio']}\n   Causa: {h['causa']}\n   Efecto: {h['efecto']}\n   Recomendación: {h['recomendacion'] or '—'}\n   Descargo de la Gerencia: {h['descargo_gerencia'] or 'Sin descargo'}" for h in hall) or "No se identificaron hallazgos."
        if clase == "DICTAMEN_TRIBUTARIO":
            cuerpo = (f"Hemos examinado el cumplimiento de las obligaciones tributarias de {emp['razon_social']} (NIT {emp.get('nit') or 's/n'}) por el período {fdate(to_date(e['periodo_ini']))} al {fin}, "
                      "y la Información Tributaria Complementaria (anexos) adjunta.\n\n"
                      f"Conciliación IVA/IT: {iva['resumen']['meses_con_diferencia']} de {iva['resumen']['meses']} períodos con diferencias.\n"
                      f"Bancarización: {ban['resumen']['sin_respaldo']} operación(es) sin respaldo por Bs {ban['resumen']['importe_sin_respaldo']:,.2f}.\n"
                      f"IUE determinado sobre utilidad imponible de Bs {iue['resumen']['utilidad_imponible']:,.2f}: Bs {iue['resumen']['iue']:,.2f}.\n\n"
                      "En nuestra opinión, excepto por lo mencionado en los hallazgos, la empresa ha cumplido en todos los aspectos significativos con las obligaciones tributarias examinadas." if hall else
                      "En nuestra opinión, la empresa ha cumplido en todos los aspectos significativos con las obligaciones tributarias examinadas.")
        elif clase == "PROCEDIMIENTOS_MINIMOS":
            cuerpo = ("Procedimientos mínimos aplicados:\n1. Conciliación del Débito Fiscal con Libro de Ventas y contabilidad.\n2. Conciliación del Crédito Fiscal con Libro de Compras.\n3. Verificación del IT.\n"
                      "4. Depuración de gastos y cálculo del IUE.\n5. Verificación de bancarización.\n6. Verificación de retenciones y planilla de sueldos (RC-IVA).\n\nResultados: ver cédulas y hallazgos.")
        else:
            cuerpo = ("Situación tributaria y contingencias estimadas:\n" + "\n".join(f"• {f['hallazgo']}: tributo Bs {f['tributo_omitido']:,.2f} → deuda Bs {f['deuda_tributaria']:,.2f}" for f in sit["filas"]) +
                      f"\nTotal contingencia estimada: Bs {sit['total_contingencia']:,.2f}.\n(Cálculo con Ley 2492; verifique tasas y sanciones aplicables.)")
        texto = f"{CLASES_T[clase].upper()}\n\n{cuerpo}\n\nHALLAZGOS\n{hall_t}\n\n[{AVISO}]"
        return {"clase": clase, "opinion": "", "texto": texto, "kam": "", "enfasis": ""}

    def emitir(self, eid: int, borrador: dict, texto: str | None = None, firmante: str = "") -> int:
        return self.ctx.auditoria.dictamen_guardar(eid, borrador["clase"], borrador.get("opinion", ""), texto or borrador["texto"], borrador.get("kam", ""), borrador.get("enfasis", ""), firmante)
