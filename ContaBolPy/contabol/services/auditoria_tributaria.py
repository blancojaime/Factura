"""Auditoría tributaria (MAI): conciliaciones IVA/IT, bancarización, depuración de gastos del IUE, anexos ITC y contingencias (Ley 2492)."""
from __future__ import annotations

import json
from datetime import date, datetime

from ..sistema import ErrorNegocio
from ..util import fdate, mes_nombre, r2, to_date
from . import auditoria_plantillas as P

MEDIOS_FEHACIENTES = ("CHQ", "TRF", "DEP")


class AuditoriaTributariaService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def _enc(self, eid):
        return self.ctx.auditoria.encargo(eid)

    def _mov(self, clave_cuenta: str, desde, hasta) -> tuple[float, float]:
        cid = self.ctx.cuenta_param(clave_cuenta)
        d, h = self.ctx.estados._mov(desde, hasta, "BS", False).get(cid, (0.0, 0.0))
        return r2(d), r2(h)

    def _meses(self, e):
        ini, fin = to_date(e["periodo_ini"]), to_date(e["periodo_fin"])
        y, m = ini.year, ini.month
        while (y, m) <= (fin.year, fin.month):
            yield y, m
            m += 1
            if m > 12:
                y, m = y + 1, 1

    # --------------------------------------------------------- IVA e IT
    def conciliacion_iva_it(self, eid: int, tolerancia: float = 1.0) -> dict:
        """Débito fiscal: Libro de Ventas vs. contabilidad vs. ventas del sistema. Crédito fiscal: Libro de Compras vs. contabilidad. IT = tasa × ingresos."""
        e = self._enc(eid)
        from ..util import fin_de_mes
        filas = []
        for y, m in self._meses(e):
            per = f"{y}{m:02d}"
            ini, fin = date(y, m, 1), fin_de_mes(y, m)
            lv = self.db.one("SELECT COALESCE(SUM(iva),0) iva, COALESCE(SUM(importe_total),0) tot FROM factura WHERE libro='V' AND periodo=? AND estado='V'", (per,))
            lc = self.db.one("SELECT COALESCE(SUM(iva),0) iva, COALESCE(SUM(importe_total),0) tot FROM factura WHERE libro='C' AND periodo=? AND estado='V'", (per,))
            df_gl = self._mov("CTA_DF_IVA", ini, fin)[1]
            cf_gl = self._mov("CTA_CF_IVA", ini, fin)[0]
            vt = self.db.scalar("SELECT COALESCE(SUM(total),0) FROM venta WHERE con_factura=1 AND estado<>'A' AND fecha BETWEEN ? AND ?", (ini.isoformat(), fin.isoformat()), 0.0)
            it_pct = self.ctx.iva.it_pct(fin)
            it_teorico = r2(lv["tot"] * it_pct / 100)
            it_gl = self._mov("CTA_IT_GASTO", ini, fin)[0]
            f = {"periodo": f"{mes_nombre(m)} {y}", "ventas_libro": r2(lv["tot"]), "ventas_sistema": r2(vt), "dif_ventas": r2(lv["tot"] - vt), "df_libro": r2(lv["iva"]), "df_contabilidad": df_gl, "dif_df": r2(df_gl - lv["iva"]),
                 "cf_libro": r2(lc["iva"]), "cf_contabilidad": cf_gl, "dif_cf": r2(cf_gl - lc["iva"]), "it_teorico": it_teorico, "it_contabilidad": it_gl, "dif_it": r2(it_gl - it_teorico)}
            f["conforme"] = all(abs(f[k]) <= tolerancia for k in ("dif_ventas", "dif_df", "dif_cf", "dif_it"))
            filas.append(f)
        mal = [f for f in filas if not f["conforme"]]
        return {"titulo": "Conciliación de Débito Fiscal, Crédito Fiscal e IT vs. Libros de Ventas y Compras", "conforme": not mal, "filas": filas,
                "resumen": {"meses": len(filas), "meses_con_diferencia": len(mal), "dif_df_total": r2(sum(f["dif_df"] for f in filas)), "dif_cf_total": r2(sum(f["dif_cf"] for f in filas)), "dif_it_total": r2(sum(f["dif_it"] for f in filas)), "tolerancia": tolerancia},
                "conclusion": "Los libros de IVA concilian con la contabilidad y las ventas del sistema." if not mal else f"{len(mal)} período(s) con diferencias: identificar facturas no contabilizadas/duplicadas y ajustar declaraciones."}

    # ------------------------------------------------------ bancarización
    def bancarizacion(self, eid: int) -> dict:
        """Operaciones ≥ umbral (parámetro normativo) y su respaldo con medio fehaciente de pago de una entidad financiera."""
        e = self._enc(eid)
        umbral = self.ctx.normativa.num("BANCARIZACION_MONTO", e["periodo_fin"])
        filas = []
        for clase, libro, doc in (("Compra", "C", "compra"), ("Venta", "V", "venta")):
            for f in self.db.query("SELECT * FROM factura WHERE libro=? AND estado='V' AND importe_total>=? AND fecha BETWEEN ? AND ?", (libro, umbral, e["periodo_ini"], e["periodo_fin"])):
                d = self.db.one(f"SELECT id, tipo_pago, total, saldo FROM {doc} WHERE factura_id=?", (f["id"],))
                formas, banco = set(), False
                if d:
                    cl = "PA" if doc == "compra" else "CO"
                    for cp in self.db.query("SELECT cp.forma, cp.nro_doc, cp.cuenta_id FROM cobro_pago cp JOIN cobro_doc cd ON cd.cobro_id=cp.id WHERE cd.doc_tipo IN (?,?,?) AND cd.doc_id=? AND cp.estado<>'A'",
                                            (doc[0].upper(), doc, clase[0], d["id"])):
                        formas.add(cp["forma"])
                        banco = banco or cp["forma"] in MEDIOS_FEHACIENTES
                    if not formas and f["comprobante_id"]:
                        cb = self.db.one("SELECT banco_id, nro_cheque FROM comprobante WHERE id=?", (f["comprobante_id"],))
                        if cb and cb["banco_id"]:
                            banco = True
                            formas.add("BANCO")
                    if d["saldo"] >= d["total"] - 0.005 and not formas:
                        formas.add("CREDITO")   # aún sin pago: la bancarización se verifica al pagar
                estado = "Respaldada" if banco else ("Pendiente de pago" if "CREDITO" in formas else "SIN RESPALDO BANCARIO")
                filas.append({"clase": clase, "fecha": f["fecha"], "factura": f["nro_factura"], "proveedor_cliente": f["razon_social"], "nit": f["nit"], "importe": f["importe_total"],
                              "medio": ", ".join(sorted(formas)) or "No identificado", "estado": estado, "factura_id": f["id"], "comprobante_id": f["comprobante_id"]})
        sin = [x for x in filas if x["estado"] == "SIN RESPALDO BANCARIO"]
        cf = r2(sum(x["importe"] for x in sin if x["clase"] == "Compra") * self.ctx.iva.iva_pct(e["periodo_fin"]) / 100)
        return {"titulo": f"Bancarización: operaciones de Bs {umbral:,.0f} o más y respaldo de entidad financiera", "conforme": not sin, "filas": filas,
                "resumen": {"umbral": umbral, "operaciones": len(filas), "sin_respaldo": len(sin), "importe_sin_respaldo": r2(sum(x["importe"] for x in sin)), "credito_fiscal_en_riesgo": cf},
                "conclusion": "Todas las operaciones cumplen la bancarización." if not sin else f"{len(sin)} operación(es) sin respaldo: el crédito fiscal (Bs {cf:,.2f} aprox.) y el gasto no serían admisibles. Verificar la norma vigente del umbral y medios de pago."}

    # ------------------------------------------------ depuración IUE
    def depuracion_iue(self, eid: int) -> dict:
        """Sugiere gastos no deducibles (D.S. 24051) para que el auditor confirme o descarte; calcula utilidad imponible e IUE."""
        e = self._enc(eid)
        self.ctx.auditoria._abierto(eid)
        er = self.ctx.estados.estado_resultados(e["periodo_ini"], e["periodo_fin"], 1)
        utilidad = er["antes_impuestos"]
        db = self.db
        db.execute("DELETE FROM gasto_no_deducible_iue WHERE encargo_id=? AND origen='AUTO' AND estado='SUGERIDO'", (eid,))
        sug = []

        def add(cod, concepto, monto, motivo, base, comp=None):
            if monto and abs(monto) > 0.005:
                sug.append(dict(cuenta_codigo=cod, concepto=concepto, monto=r2(abs(monto)), motivo=motivo, base_legal=base, comprobante_id=comp))
        for c in db.query("SELECT codigo, nombre FROM cuenta WHERE codigo IN ('5.3.1.03.005','5.6.1.01.004','5.3.1.03.002')"):
            d, h = self.ctx.estados._mov(e["periodo_ini"], e["periodo_fin"], "BS", False).get(self.ctx.cuenta_por_codigo(c["codigo"])["id"], (0, 0))
            if c["codigo"] == "5.3.1.03.002":
                add(c["codigo"], "IUE de la gestión registrado como gasto", d - h, "El IUE no es deducible de sí mismo", "D.S. 24051 art. 18")
            elif c["codigo"] == "5.3.1.03.005":
                add(c["codigo"], "Multas y recargos", d - h, "Sanciones y recargos no son gasto deducible", "D.S. 24051 art. 18")
            else:
                add(c["codigo"], "Gastos no deducibles registrados", d - h, "Cuenta de gastos no deducibles", "D.S. 24051 art. 18")
        sin_fact = db.scalar("SELECT COALESCE(SUM(total),0) FROM compra WHERE con_factura=0 AND estado<>'A' AND fecha BETWEEN ? AND ?", (e["periodo_ini"], e["periodo_fin"]), 0.0)
        add(None, "Compras y gastos sin factura válida", sin_fact, "Gasto no respaldado con factura (D.S. 24051 art. 8 inc. a); verificar excepciones de RND", "Ley 843 art. 8; D.S. 24051 art. 8")
        ban = self.bancarizacion(eid)
        add(None, "Operaciones sin respaldo bancario", sum(x["importe"] for x in ban["filas"] if x["clase"] == "Compra" and x["estado"] == "SIN RESPALDO BANCARIO"), "Incumple la bancarización: el gasto no es deducible", "Ley 843 art. 37 (verificar)")
        dep = self.ctx.aud_pruebas.depreciacion_vs_ds24051(eid)
        add("5.3.1.04", "Depreciación en exceso del D.S. 24051", dep["resumen"]["exceso_no_deducible"], "Excede los coeficientes del art. 22", "D.S. 24051 art. 22")
        prev = abs(self.ctx.estados._mov(e["periodo_ini"], e["periodo_fin"], "BS", False).get(self.ctx.cuenta_por_codigo("5.3.1.05.001")["id"], (0, 0))[0]) if self.ctx.cuenta_por_codigo("5.3.1.05.001") else 0
        add("5.3.1.05.001", "Previsión para cuentas incobrables (verificar condiciones del art. 18)", prev, "Solo admisible bajo condiciones del reglamento; confirmar o descartar", "D.S. 24051 art. 18 (verificar)")
        ahora = datetime.now().isoformat(timespec="seconds")
        with db.tx():
            for s in sug:
                db.insert("gasto_no_deducible_iue", encargo_id=eid, origen="AUTO", estado="SUGERIDO", **s)
            self.ctx.auditoria.trail(eid, "iue", None, "DEPURAR", f"{len(sug)} sugerencias")
        return self.cedula_iue(eid, utilidad)

    def gasto_estado(self, gid: int, estado: str, monto: float | None = None) -> None:
        g = self.db.one("SELECT * FROM gasto_no_deducible_iue WHERE id=?", (gid,))
        self.ctx.auditoria._abierto(g["encargo_id"])
        if estado not in ("CONFIRMADO", "DESCARTADO", "SUGERIDO"):
            raise ErrorNegocio("Estado no válido.")
        self.db.update("gasto_no_deducible_iue", gid, estado=estado, **({"monto": r2(monto)} if monto is not None else {}))
        self.ctx.auditoria.trail(g["encargo_id"], "gasto_no_deducible", gid, estado, g["concepto"])

    def gasto_manual(self, eid: int, concepto: str, monto: float, motivo: str, base_legal: str = "", cuenta_codigo: str | None = None) -> int:
        self.ctx.auditoria._abierto(eid)
        i = self.db.insert("gasto_no_deducible_iue", encargo_id=eid, concepto=concepto, monto=r2(monto), motivo=motivo, base_legal=base_legal, cuenta_codigo=cuenta_codigo, origen="MANUAL", estado="CONFIRMADO")
        self.ctx.auditoria.trail(eid, "gasto_no_deducible", i, "MANUAL", concepto)
        return i

    def cedula_iue(self, eid: int, utilidad: float | None = None) -> dict:
        e = self._enc(eid)
        if utilidad is None:
            utilidad = self.ctx.estados.estado_resultados(e["periodo_ini"], e["periodo_fin"], 1)["antes_impuestos"]
        gastos = self.db.query("SELECT * FROM gasto_no_deducible_iue WHERE encargo_id=? ORDER BY id", (eid,))
        conf = r2(sum(g["monto"] for g in gastos if g["estado"] == "CONFIRMADO"))
        sug = r2(sum(g["monto"] for g in gastos if g["estado"] == "SUGERIDO"))
        imponible = r2(utilidad + conf)
        # Donaciones: tope % de la utilidad imponible (se aplica sobre los registros manuales con concepto 'Donación').
        tope_pct = self.ctx.normativa.num("IUE_DONACION_PCT", e["periodo_fin"])
        pct = self.ctx.normativa.num("IUE_PCT_AUD", e["periodo_fin"])
        iue = r2(max(imponible, 0) * pct / 100)
        return {"titulo": "Cédula de depuración de gastos y determinación del IUE", "conforme": sug == 0, "gastos": gastos,
                "filas": [{"concepto": "Utilidad contable antes de impuestos", "importe": r2(utilidad)}, {"concepto": "(+) Gastos no deducibles confirmados", "importe": conf},
                          {"concepto": "Utilidad neta imponible", "importe": imponible}, {"concepto": f"IUE determinado ({pct:g} %)", "importe": iue}],
                "resumen": {"utilidad_contable": r2(utilidad), "no_deducibles_confirmados": conf, "sugerencias_pendientes": sug, "utilidad_imponible": imponible, "iue": iue, "tope_donaciones_pct": tope_pct,
                            "tope_donaciones_monto": r2(max(imponible, 0) * tope_pct / 100)},
                "conclusion": "Cédula de IUE determinada." if sug == 0 else f"Hay sugerencias pendientes por Bs {sug:,.2f}: confirme o descarte cada una antes de emitir el dictamen."}

    # --------------------------------------------------------- anexos ITC
    def generar_anexos(self, eid: int) -> list[dict]:
        """Llena automáticamente los anexos de la Información Tributaria Complementaria con datos del sistema (formatos referenciales)."""
        e = self._enc(eid)
        self.ctx.auditoria._abierto(eid)
        est, ini, fin = self.ctx.estados, e["periodo_ini"], e["periodo_fin"]
        er = est.estado_resultados(ini, fin, 3)
        pr = self.ctx.aud_pruebas
        iva = self.conciliacion_iva_it(eid)
        ban = self.bancarizacion(eid)
        iue = self.cedula_iue(eid)
        dep = pr.depreciacion_vs_ds24051(eid)
        pla = pr.conciliar_planilla(eid)
        sal = est._saldos_a(fin)
        plan = {c["id"]: c for c in self.db.query("SELECT * FROM cuenta")}

        def cuentas(prefijo, signo=1):
            return [{"codigo": c["codigo"], "cuenta": c["nombre"], "saldo": r2(sal.get(cid, 0.0) * signo)} for cid, c in sorted(plan.items(), key=lambda x: x[1]["codigo"])
                    if c["codigo"].startswith(prefijo) and c["es_movimiento"] and abs(sal.get(cid, 0.0)) > 0.005]
        contenido = {
            1: [f for f in er["filas"] if f.get("importe") is not None], 2: [f for f in er["filas"] if f.get("importe") is not None],
            3: [{k: f[k] for k in ("periodo", "ventas_libro", "df_libro", "df_contabilidad", "dif_df")} for f in iva["filas"]],
            4: [{k: f[k] for k in ("periodo", "cf_libro", "cf_contabilidad", "dif_cf")} for f in iva["filas"]],
            5: [{k: f[k] for k in ("periodo", "ventas_libro", "it_teorico", "it_contabilidad", "dif_it")} for f in iva["filas"]],
            6: iue["filas"], 7: dep["filas"], 8: cuentas("1.1.3"), 9: cuentas("1.1.2", 1), 10: cuentas("2.1", -1), 11: pla["filas"], 12: ban["filas"], 13: cuentas("3", -1),
            14: [{"cuenta": c["cuenta"], "saldo": c["saldo"]} for c in cuentas("2.1.2.01.00")],
            15: [{"concepto": h["codigo"], "detalle": h["condicion"], "impacto": h["impacto_monto"]} for h in self.ctx.auditoria.hallazgos(eid)],
        }
        ahora = datetime.now().isoformat(timespec="seconds")
        out = []
        with self.db.tx():
            self.db.execute("DELETE FROM anexo_tributario_itc WHERE encargo_id=?", (eid,))
            for n, titulo in P.ANEXOS_ITC:
                self.db.insert("anexo_tributario_itc", encargo_id=eid, numero=n, titulo=titulo, contenido=json.dumps(contenido.get(n, []), ensure_ascii=False, default=str), generado_en=ahora)
                out.append({"numero": n, "titulo": titulo, "filas": len(contenido.get(n, []))})
            self.ctx.auditoria.trail(eid, "anexo_itc", None, "GENERAR", f"{len(out)} anexos")
        return out

    def anexos(self, eid: int) -> list[dict]:
        self._enc(eid)
        out = self.db.query("SELECT * FROM anexo_tributario_itc WHERE encargo_id=? ORDER BY numero", (eid,))
        for a in out:
            a["datos"] = json.loads(a["contenido"])
        return out

    # ------------------------------------------------------- contingencias
    def contingencia(self, tributo_omitido: float, fecha_vencimiento, fecha_calculo, tasa_anual_pct: float | None = None, sancion_pct: float = 0.0, ufv_venc: float | None = None, ufv_calc: float | None = None) -> dict:
        """Deuda tributaria (Ley 2492 art. 47): tributo omitido actualizado por UFV + intereses + sanción. Las tasas deben ser verificadas por el usuario."""
        fv, fc = to_date(fecha_vencimiento), to_date(fecha_calculo)
        if fc < fv:
            raise ErrorNegocio("La fecha de cálculo debe ser posterior al vencimiento.")
        if tributo_omitido < 0:
            raise ErrorNegocio("El tributo omitido no puede ser negativo.")
        tc = self.ctx.tc
        uv = ufv_venc if ufv_venc is not None else tc.ufv(fv)
        uc = ufv_calc if ufv_calc is not None else tc.ufv(fc)
        factor = (uc / uv) if uv and uc else 1.0
        actualizado = r2(tributo_omitido * max(factor, 1.0))
        tasa = self.ctx.normativa.num("AUD_TASA_INTERES_ANUAL", fc) if tasa_anual_pct is None else tasa_anual_pct
        dias = (fc - fv).days
        interes = r2(actualizado * tasa / 100 * dias / 360)
        sancion = r2(actualizado * sancion_pct / 100)
        total = r2(actualizado + interes + sancion)
        return {"tributo_omitido": r2(tributo_omitido), "ufv_vencimiento": uv, "ufv_calculo": uc, "factor_actualizacion": round(factor, 6), "tributo_actualizado": actualizado, "dias_mora": dias,
                "tasa_interes_anual_pct": tasa, "intereses": interes, "sancion_pct": sancion_pct, "sancion": sancion, "deuda_tributaria": total,
                "advertencia": "Tasa y sanción deben verificarse con la Ley 2492 y la normativa vigente; si la tasa es 0 el interés no se calcula." if not tasa else ""}

    def situacion_tributaria(self, eid: int, fecha_calculo=None, sancion_pct: float = 0.0) -> dict:
        """Liquidación de contingencias a partir de los hallazgos tributarios con impacto en monto y la diferencia del IVA/IT/IUE."""
        e = self._enc(eid)
        fecha = fecha_calculo or date.today()
        filas = []
        for h in self.ctx.auditoria.hallazgos(eid):
            if h["impacto_monto"] and h["estado"] != "DESCARTADO":
                venc = e["periodo_fin"]
                c = self.contingencia(h["impacto_monto"], venc, fecha, sancion_pct=sancion_pct)
                filas.append({"hallazgo": h["codigo"], "concepto": h["condicion"][:90], **{k: c[k] for k in ("tributo_omitido", "tributo_actualizado", "intereses", "sancion", "deuda_tributaria")}})
        tot = r2(sum(f["deuda_tributaria"] for f in filas))
        return {"titulo": "Situación tributaria: liquidación de contingencias (Ley 2492)", "filas": filas, "total_contingencia": tot, "fecha_calculo": str(fecha)}
