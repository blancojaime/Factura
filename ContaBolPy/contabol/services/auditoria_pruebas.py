"""Pruebas sustantivas financieras (MAF) conectadas a Inventarios, Costos, Activos fijos y Planilla.

Cada prueba devuelve un dict con: titulo, conforme (bool), filas (detalle), resumen y conclusion; se puede guardar como papel de trabajo.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from ..util import fdate, r2, to_date


class PruebasFinancierasService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def _enc(self, eid):
        return self.ctx.auditoria.encargo(eid)

    def _saldo(self, codigo: str, hasta) -> float:
        c = self.ctx.cuenta_por_codigo(codigo)
        if not c:
            return 0.0
        return r2(self.ctx.estados._saldos_a(hasta).get(c["id"], 0.0))

    def _mov_periodo(self, codigo: str, desde, hasta) -> tuple[float, float]:
        c = self.ctx.cuenta_por_codigo(codigo)
        if not c:
            return 0.0, 0.0
        d, h = self.ctx.estados._mov(desde, hasta, "BS", False).get(c["id"], (0.0, 0.0))
        return r2(d), r2(h)

    # ---------------------------------------------------------- inventarios
    def muestreo_recuento(self, eid: int, n: int = 10, semilla: int = 2025, estratos: int = 5) -> dict:
        """Selección para recuento físico: los `estratos` ítems de mayor valor (100 %) + muestra aleatoria reproducible (semilla) del resto."""
        e = self._enc(eid)
        items = self.db.query("SELECT id, codigo, nombre, stock, costo_prom, tipo FROM item WHERE es_servicio=0 AND stock<>0")
        for i in items:
            i["valor"] = r2(i["stock"] * i["costo_prom"])
        items.sort(key=lambda x: -x["valor"])
        top, resto = items[:estratos], items[estratos:]
        rnd = random.Random(semilla)
        muestra = rnd.sample(resto, min(max(n - len(top), 0), len(resto)))
        sel = top + sorted(muestra, key=lambda x: x["codigo"])
        total = r2(sum(i["valor"] for i in items))
        cub = r2(sum(i["valor"] for i in sel))
        filas = [{"codigo": i["codigo"], "item": i["nombre"], "tipo": i["tipo"], "cantidad_sistema": i["stock"], "costo": i["costo_prom"], "valor": i["valor"],
                  "estrato": "Alto valor (100 %)" if i in top else "Aleatorio", "conteo_fisico": None} for i in sel]
        return {"titulo": "Selección de muestra para recuento físico de inventarios", "conforme": True, "filas": filas,
                "resumen": {"universo_items": len(items), "valor_universo": total, "items_seleccionados": len(sel), "valor_cubierto": cub, "cobertura_pct": round(cub / total * 100, 1) if total else 0, "semilla": semilla},
                "conclusion": f"Muestra de {len(sel)} ítems que cubre el {round(cub / total * 100, 1) if total else 0} % del valor. Registrar el conteo físico y marcar con ✓ / ≠ en la cédula C.", "fecha_corte": e["periodo_fin"]}

    def corte_documental(self, eid: int, dias: int = 5) -> dict:
        """Compara fechas de documentos (venta/compra) con la del movimiento de inventario y su comprobante cerca del cierre (corte)."""
        e = self._enc(eid)
        fin = to_date(e["periodo_fin"])
        ini, tope = fin - timedelta(days=dias), fin + timedelta(days=dias)
        filas = []
        for tabla, clase in (("venta", "Venta"), ("compra", "Compra")):
            for d in self.db.query(f"SELECT t.id, t.numero, t.fecha, t.total, t.mov_id, t.comprobante_id, t.estado FROM {tabla} t WHERE t.fecha BETWEEN ? AND ? AND t.estado<>'A'", (ini.isoformat(), tope.isoformat())):
                mov = self.db.one("SELECT fecha FROM mov_inv WHERE id=?", (d["mov_id"],)) if d["mov_id"] else None
                comp = self.db.one("SELECT fecha FROM comprobante WHERE id=?", (d["comprobante_id"],)) if d["comprobante_id"] else None
                obs = []
                if mov and (mov["fecha"] <= fin.isoformat()) != (d["fecha"] <= fin.isoformat()):
                    obs.append("Fecha del movimiento de inventario en distinto período que el documento")
                if comp and (comp["fecha"] <= fin.isoformat()) != (d["fecha"] <= fin.isoformat()):
                    obs.append("Fecha del comprobante contable en distinto período que el documento")
                filas.append({"clase": clase, "numero": d["numero"], "fecha_doc": d["fecha"], "fecha_mov_inv": mov["fecha"] if mov else "—", "fecha_comprobante": comp["fecha"] if comp else "—",
                              "total": d["total"], "observacion": "; ".join(obs) or "Conforme"})
        mal = [f for f in filas if f["observacion"] != "Conforme"]
        return {"titulo": f"Prueba de corte documental (±{dias} días del cierre {fdate(fin)})", "conforme": not mal, "filas": filas,
                "resumen": {"documentos_revisados": len(filas), "con_diferencias": len(mal), "monto_en_riesgo": r2(sum(f["total"] for f in mal))},
                "conclusion": "Sin diferencias de corte." if not mal else f"Se detectaron {len(mal)} documento(s) con corte inadecuado: evaluar ajuste por asiento propuesto."}

    def vnr_obsolescencia(self, eid: int, costos_venta_pct: float = 0.0, dias_sin_mov: int = 180) -> dict:
        """Valor neto de realización (NC/NIC 2: menor entre costo y VNR) y obsolescencia (sin movimiento o vencidos)."""
        e = self._enc(eid)
        fin = to_date(e["periodo_fin"])
        filas, total_prev = [], 0.0
        for i in self.db.query("SELECT * FROM item WHERE es_servicio=0 AND stock>0"):
            vnr_u = r2(i["precio_venta"] * (1 - costos_venta_pct / 100))
            ult = self.db.scalar("SELECT MAX(fecha) FROM kardex WHERE item_id=? AND sal_cant>0 AND fecha<=?", (i["id"], fin.isoformat()))
            dias = (fin - to_date(ult)).days if ult else None
            venc = self.db.scalar("SELECT COALESCE(SUM(cantidad),0) FROM item_lote WHERE item_id=? AND vencimiento IS NOT NULL AND vencimiento<? AND cantidad>0", (i["id"], fin.isoformat()), 0.0)
            ajuste_vnr = r2(max(0.0, (i["costo_prom"] - vnr_u) * i["stock"])) if i["tipo"] in ("M", "T", "P") and i["precio_venta"] > 0 else 0.0
            ajuste_venc = r2(venc * i["costo_prom"])
            obs = []
            if ajuste_vnr:
                obs.append("Costo > VNR")
            if ajuste_venc:
                obs.append("Lote vencido")
            if dias is None or dias > dias_sin_mov:
                obs.append(f"Sin salidas hace {dias if dias is not None else '>'+str(dias_sin_mov)} días")
            prev = max(ajuste_vnr, ajuste_venc)
            if prev or obs:
                total_prev += prev
                filas.append({"codigo": i["codigo"], "item": i["nombre"], "stock": i["stock"], "costo": i["costo_prom"], "vnr_unit": vnr_u, "ajuste_vnr": ajuste_vnr, "vencido": ajuste_venc, "dias_sin_salida": dias, "observacion": "; ".join(obs)})
        return {"titulo": "Valor neto de realización y obsolescencia de inventarios", "conforme": total_prev == 0, "filas": filas,
                "resumen": {"items_observados": len(filas), "provision_sugerida": r2(total_prev), "costos_venta_pct": costos_venta_pct, "dias_sin_movimiento": dias_sin_mov},
                "conclusion": "Los inventarios están valuados al menor entre costo y VNR." if not total_prev else f"Provisión sugerida por desvalorización/obsolescencia: Bs {r2(total_prev):,.2f} (proponer ajuste)."}

    def conciliar_inventario_kardex(self, eid: int) -> dict:
        e = self._enc(eid)
        kardex_val = self.db.scalar("SELECT COALESCE(SUM(i.stock*i.costo_prom),0) FROM item i WHERE i.es_servicio=0", default=0.0)
        gl = sum(self._saldo(c, e["periodo_fin"]) for c in ("1.1.3",))
        dif = r2(gl - kardex_val)
        return {"titulo": "Conciliación inventarios: Kardex valorado vs. contabilidad (cuenta 1.1.3)", "conforme": abs(dif) <= 1.0,
                "filas": [{"concepto": "Valor del kardex (existencias × costo promedio)", "importe": r2(kardex_val)}, {"concepto": "Saldo contable de Inventarios", "importe": r2(gl)}, {"concepto": "Diferencia", "importe": dif}],
                "resumen": {"diferencia": dif}, "conclusion": "Conciliado." if abs(dif) <= 1.0 else "Existe diferencia entre kardex y contabilidad: investigar y proponer ajuste."}

    # --------------------------------------------------------------- costos
    def costos_produccion(self, eid: int) -> dict:
        """MP / MOD / CIF por orden de producción, cuota de aplicación de CIF y conciliación con las cuentas de costos."""
        e = self._enc(eid)
        ordenes = self.db.query("SELECT o.*, i.nombre AS producto FROM orden_prod o JOIN item i ON i.id=o.item_id WHERE o.fecha<=? AND o.estado<>'N' ORDER BY o.numero", (e["periodo_fin"],))
        filas = []
        for o in ordenes:
            total = r2(o["costo_mp"] + o["costo_mod"] + o["costo_cif"])
            filas.append({"orden": o["numero"], "producto": o["producto"], "cant_producida": o["cant_prod"], "MP": o["costo_mp"], "MOD": o["costo_mod"], "CIF": o["costo_cif"], "costo_total": total,
                          "costo_unitario": r2(total / o["cant_prod"]) if o["cant_prod"] else 0.0, "estado": o["estado"]})
        mp, mod, cif = (sum(f[k] for f in filas) for k in ("MP", "MOD", "CIF"))
        cuota = round(cif / mod, 4) if mod else 0.0   # cuota de aplicación de CIF sobre MOD
        gl = [self._mov_periodo(c, e["periodo_ini"], e["periodo_fin"])[0] for c in ("5.2.1.01.001", "5.2.1.01.002", "5.2.1.01.003")]
        dif = [r2(gl[0] - mp), r2(gl[1] - mod), r2(gl[2] - cif)]
        return {"titulo": "Costos de conversión: MP, MOD y CIF por orden, cuota de aplicación y variaciones", "conforme": all(abs(x) <= 1.0 for x in dif) if filas else True, "filas": filas,
                "resumen": {"MP_ordenes": r2(mp), "MOD_ordenes": r2(mod), "CIF_ordenes": r2(cif), "cuota_aplicacion_CIF_sobre_MOD": cuota,
                            "var_MP_vs_contabilidad": dif[0], "var_MOD_vs_contabilidad": dif[1], "var_CIF_vs_contabilidad": dif[2]},
                "conclusion": "Los costos de las órdenes concilian con las cuentas de costos de producción." if all(abs(x) <= 1.0 for x in dif) else
                "Variaciones entre el costo acumulado en órdenes y las cuentas 5.2.1.01: analizar subaplicación/sobreaplicación de CIF."}

    # -------------------------------------------------------- activos fijos
    def depreciacion_vs_ds24051(self, eid: int) -> dict:
        """Recalcula la depreciación de la gestión por activo con los porcentajes del D.S. 24051 y la compara con la registrada."""
        e = self._enc(eid)
        ini, fin = to_date(e["periodo_ini"]), to_date(e["periodo_fin"])
        filas = []
        for a in self.db.query("SELECT a.*, g.nombre AS grupo, g.pct AS pct_ds FROM activo a JOIN activo_grupo g ON g.id=a.grupo_id WHERE a.fecha_alta<=?", (fin.isoformat(),)):
            desde = max(to_date(a["fecha_alta"]), ini)
            hasta = min(to_date(a["fecha_baja"]), fin) if a["fecha_baja"] else fin
            if hasta < desde:
                continue
            meses = (hasta.year - desde.year) * 12 + hasta.month - desde.month + (1 if hasta.day >= 28 or desde.day == 1 else 0)
            meses = max(0, min(12, meses))
            max_anual = r2(a["valor_original"] * a["pct_ds"] / 100)
            esperado = r2(max_anual * meses / 12)
            real = self.db.scalar("SELECT COALESCE(SUM(depreciacion),0) FROM activo_dep WHERE activo_id=? AND fecha BETWEEN ? AND ?", (a["id"], ini.isoformat(), fin.isoformat()), 0.0)
            exceso = r2(max(0.0, real - esperado))
            filas.append({"codigo": a["codigo"], "activo": a["nombre"], "grupo": a["grupo"], "pct_ds24051": a["pct_ds"], "valor_original": a["valor_original"], "meses": meses,
                          "dep_recalculada": esperado, "dep_registrada": r2(real), "diferencia": r2(real - esperado), "exceso_no_deducible": exceso,
                          "observacion": "Excede el % máximo del D.S. 24051" if exceso > 0.5 else ("Depreciación menor a la esperada" if esperado - real > 1 else "Conforme")})
        exceso = r2(sum(f["exceso_no_deducible"] for f in filas))
        altas = self.db.query("SELECT codigo, nombre, fecha_alta, valor_original FROM activo WHERE fecha_alta BETWEEN ? AND ?", (ini.isoformat(), fin.isoformat()))
        bajas = self.db.query("SELECT codigo, nombre, fecha_baja, valor_actual FROM activo WHERE fecha_baja BETWEEN ? AND ?", (ini.isoformat(), fin.isoformat()))
        ajuste_ufv = self.ctx.normativa.raw("AJUSTE_INFLACION_CONTABLE", fin) == "1"
        return {"titulo": "Activos fijos: depreciación registrada vs. D.S. 24051, altas y bajas", "conforme": exceso <= 0.5 and not any("menor" in f["observacion"] for f in filas), "filas": filas, "altas": altas, "bajas": bajas,
                "resumen": {"activos": len(filas), "exceso_no_deducible": exceso, "altas": len(altas), "bajas": len(bajas), "ajuste_ufv_contable_vigente": ajuste_ufv},
                "conclusion": ("Depreciación de acuerdo con los porcentajes del D.S. 24051." if exceso <= 0.5 else f"Depreciación excedida por Bs {exceso:,.2f}: gasto no deducible para el IUE.") +
                (" El ajuste por inflación (NC 3) está suspendido contablemente desde 2020 (CTNAC 03/2020); la UFV se mantiene para efectos tributarios." if not ajuste_ufv else "")}

    # --------------------------------------------------------------- planilla
    def conciliar_planilla(self, eid: int) -> dict:
        """Planilla vs. aportes patronales/laborales contabilizados, provisión de aguinaldo/indemnización y RC-IVA (Formulario 110)."""
        e = self._enc(eid)
        ini, fin = to_date(e["periodo_ini"]), to_date(e["periodo_fin"])
        t = self.db.one("""SELECT COALESCE(SUM(d.total_ganado),0) ganado, COALESCE(SUM(d.afp_vejez+d.afp_riesgo+d.afp_comision+d.afp_solidario),0) afp_lab, COALESCE(SUM(d.ans),0) ans,
            COALESCE(SUM(d.pat_cns),0) cns, COALESCE(SUM(d.pat_riesgo),0) riesgo, COALESCE(SUM(d.pat_vivienda),0) viv, COALESCE(SUM(d.pat_solidario),0) sol,
            COALESCE(SUM(d.rc_impuesto),0) rc FROM planilla_det d JOIN planilla p ON p.id=d.planilla_id WHERE p.anio=? AND p.mes BETWEEN 1 AND 12""", (fin.year,))
        dia = lambda c: self._mov_periodo(c, ini, fin)[0]
        filas = [
            {"concepto": "Aporte patronal CNS", "planilla": r2(t["cns"]), "contabilidad": dia("5.3.1.01.008")},
            {"concepto": "Aporte patronal riesgo profesional", "planilla": r2(t["riesgo"]), "contabilidad": dia("5.3.1.01.009")},
            {"concepto": "Aporte patronal Pro-Vivienda", "planilla": r2(t["viv"]), "contabilidad": dia("5.3.1.01.010")},
            {"concepto": "Aporte patronal solidario", "planilla": r2(t["sol"]), "contabilidad": dia("5.3.1.01.011")},
        ]
        rc_gl = self._mov_periodo("2.1.2.01.006", ini, fin)[1]
        filas.append({"concepto": "RC-IVA retenido a dependientes (F-110)", "planilla": r2(t["rc"]), "contabilidad": rc_gl})
        for f in filas:
            f["diferencia"] = r2(f["contabilidad"] - f["planilla"])
        # Provisión de aguinaldo: 1/12 del haber mensual por mes trabajado (referencial).
        prov_esperada = r2(sum(r["haber_basico"] for r in self.db.query("SELECT haber_basico FROM empleado WHERE activo=1")) * 1)
        prov_gl = abs(self._saldo("2.1.3.02.001", fin))
        indem_gl = abs(self._saldo("2.1.3.02.002", fin))
        filas.append({"concepto": "Provisión aguinaldo (≈ 1 haber mensual al cierre)", "planilla": prov_esperada, "contabilidad": prov_gl, "diferencia": r2(prov_gl - prov_esperada)})
        mal = [f for f in filas if abs(f["diferencia"]) > 1.0]
        return {"titulo": "Planilla de sueldos: conciliación con aportes, provisiones y RC-IVA", "conforme": not mal, "filas": filas,
                "resumen": {"total_ganado": r2(t["ganado"]), "aportes_laborales_AFP": r2(t["afp_lab"]), "ANS": r2(t["ans"]), "partidas_con_diferencia": len(mal), "provision_indemnizacion_saldo": indem_gl},
                "conclusion": "La planilla concilia con los saldos contables." if not mal else f"{len(mal)} partida(s) con diferencia: revisar la contabilización de la planilla y las provisiones sociales (aguinaldo, indemnización)."}

    def antiguedad_cxc(self, eid: int) -> dict:
        e = self._enc(eid)
        fin = to_date(e["periodo_fin"])
        tramos = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "91-180": 0.0, ">180": 0.0}
        filas = []
        for v in self.db.query("SELECT v.*, t.nombre cliente FROM venta v JOIN tercero t ON t.id=v.tercero_id WHERE v.saldo>0.005 AND v.estado<>'A' AND v.fecha<=?", (fin.isoformat(),)):
            dias = (fin - to_date(v["vencimiento"] or v["fecha"])).days
            k = "0-30" if dias <= 30 else "31-60" if dias <= 60 else "61-90" if dias <= 90 else "91-180" if dias <= 180 else ">180"
            tramos[k] += v["saldo"]
            filas.append({"cliente": v["cliente"], "documento": v["numero"], "fecha": v["fecha"], "saldo": v["saldo"], "dias_vencido": max(dias, 0), "tramo": k})
        prev = r2(tramos["91-180"] * 0.5 + tramos[">180"] * 1.0)
        return {"titulo": "Antigüedad de saldos de cuentas por cobrar y previsión sugerida", "conforme": True, "filas": filas,
                "resumen": {**{k: r2(v) for k, v in tramos.items()}, "prevision_sugerida": prev, "prevision_contabilizada": abs(self._saldo("1.1.2.05.001", fin))},
                "conclusion": f"Previsión sugerida Bs {prev:,.2f} (50 % entre 91 y 180 días; 100 % sobre 180 días) frente a la contabilizada: evaluar ajuste."}

    CATALOGO = {"muestreo_recuento": ("C", "Inventarios: muestreo para recuento"), "corte_documental": ("C", "Inventarios: corte documental"), "vnr_obsolescencia": ("C", "Inventarios: VNR y obsolescencia"),
                "conciliar_inventario_kardex": ("C", "Inventarios: kardex vs contabilidad"), "costos_produccion": ("GG", "Costos de conversión"), "depreciacion_vs_ds24051": ("E", "Activos fijos vs D.S. 24051"),
                "conciliar_planilla": ("CC", "Planilla y pasivos laborales"), "antiguedad_cxc": ("B", "Cuentas por cobrar: antigüedad")}

    def ejecutar(self, eid: int, clave: str, guardar: bool = True, **kw) -> dict:
        if clave not in self.CATALOGO:
            raise KeyError(clave)
        res = getattr(self, clave)(eid, **kw)
        if guardar:
            self.ctx.auditoria.guardar_prueba(eid, clave, res, self.CATALOGO[clave][0], kw)
        return res
