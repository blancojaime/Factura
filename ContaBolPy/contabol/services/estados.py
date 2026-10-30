"""Estados financieros: Balance General, Estado de Resultados, Evolución del Patrimonio Neto,
Flujo de Efectivo (métodos directo e indirecto) y Notas a los Estados Financieros.

Todos se calculan sobre comprobantes vigentes, EXCLUYENDO el asiento de cierre (los estados son previos al cierre)."""
from __future__ import annotations

from datetime import timedelta

from ..util import fdate, iso, r2, to_date


def _f(texto="", importe=None, nivel=0, estilo="", codigo="", extra=None):
    return {"codigo": codigo, "texto": texto, "importe": importe, "nivel": nivel, "estilo": estilo, **(extra or {})}


class EstadosService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    # ---------------------------------------------------------------- base
    def _mov(self, desde, hasta, moneda="BS", con_apertura=True, solo_apertura=False) -> dict[int, tuple[float, float]]:
        """Movimientos por cuenta. con_apertura=False excluye comprobantes de apertura."""
        cd, ch = ("debe_usd", "haber_usd") if moneda == "USD" else ("debe_bs", "haber_bs")
        sql = (f"SELECT d.cuenta_id, SUM(d.{cd}) AS d, SUM(d.{ch}) AS h FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id "
               "WHERE c.estado='V' AND c.origen<>'CIERRE'")
        p: list = []
        if solo_apertura:
            sql += " AND c.origen='APERTURA'"
        elif not con_apertura:
            sql += " AND c.origen<>'APERTURA'"
        if desde:
            sql += " AND c.fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND c.fecha<=?"
            p.append(iso(hasta))
        return {r["cuenta_id"]: (r["d"] or 0.0, r["h"] or 0.0) for r in self.db.query(sql + " GROUP BY d.cuenta_id", p)}

    def _saldos_a(self, fecha, moneda="BS") -> dict[int, float]:
        """Saldos acumulados (debe-haber) por cuenta y ancestros, desde el inicio de la gestión hasta la fecha."""
        acum = self.ctx.libros.acumular(self._mov(None, fecha, moneda, True))
        return {k: v[0] - v[1] for k, v in acum.items()}

    def _saldos_periodo(self, desde, hasta) -> dict[int, float]:
        acum = self.ctx.libros.acumular(self._mov(desde, hasta, "BS", False))
        return {k: v[0] - v[1] for k, v in acum.items()}

    def _plan(self):
        return self.db.query("SELECT * FROM cuenta ORDER BY codigo")

    def resultado(self, desde, hasta) -> float:
        """Utilidad (pérdida) neta del período = ingresos - costos y gastos."""
        mov = self._mov(desde, hasta, "BS", False)
        tot = 0.0
        for c in self._plan():
            if c["es_movimiento"] and c["tipo"] in ("I", "G") and c["id"] in mov:
                d, h = mov[c["id"]]
                tot += h - d
        return r2(tot)

    # ------------------------------------------------------------ balance general
    def balance_general(self, fecha, nivel: int = 4, moneda: str = "BS") -> dict:
        ctx = self.ctx
        f = to_date(fecha)
        sal = self._saldos_a(f, moneda)
        ini = ctx.inicio
        ni = self._resultado_acum(f, moneda)
        filas = []

        def seccion(raiz: str, titulo: str, signo: int, extra_total: float = 0.0):
            c0 = next(c for c in self._plan() if c["codigo"] == raiz)
            filas.append(_f(titulo, None, 0, "titulo", raiz))
            total = 0.0
            for c in self._plan():
                if not c["codigo"].startswith(raiz + ".") or c["nivel"] > nivel or c["nivel"] < 2:
                    continue
                v = sal.get(c["id"], 0.0) * signo
                if abs(v) < 0.005:
                    continue
                grupo = c["nivel"] <= 3 and not c["es_movimiento"]
                filas.append(_f(c["nombre"], r2(v), c["nivel"] - 1, "subtotal" if c["nivel"] == 2 else ("grupo" if grupo else ""), c["codigo"]))
            total = r2(sal.get(c0["id"], 0.0) * signo + extra_total)
            return total

        total_a = seccion("1", "ACTIVO", 1)
        filas.append(_f("TOTAL ACTIVO", total_a, 0, "total"))
        total_p = seccion("2", "PASIVO", -1)
        filas.append(_f("TOTAL PASIVO", total_p, 0, "total"))
        # patrimonio con resultado del ejercicio
        filas.append(_f("PATRIMONIO", None, 0, "titulo", "3"))
        c3 = next(c for c in self._plan() if c["codigo"] == "3")
        for c in self._plan():
            if not c["codigo"].startswith("3.") or c["nivel"] > nivel or c["nivel"] < 2:
                continue
            v = -sal.get(c["id"], 0.0)
            if abs(v) < 0.005:
                continue
            filas.append(_f(c["nombre"], r2(v), c["nivel"] - 1, "subtotal" if c["nivel"] == 2 else "", c["codigo"]))
        filas.append(_f("Resultado de la gestión (utilidad o pérdida del período)", ni, 1, "", "RES"))
        total_pat = r2(-sal.get(c3["id"], 0.0) + ni)
        filas.append(_f("TOTAL PATRIMONIO", total_pat, 0, "total"))
        filas.append(_f("TOTAL PASIVO Y PATRIMONIO", r2(total_p + total_pat), 0, "total"))
        dif = r2(total_a - total_p - total_pat)
        return {"titulo": "BALANCE GENERAL", "fecha": f.isoformat(), "inicio": ini.isoformat(), "moneda": moneda, "filas": filas,
                "total_activo": total_a, "total_pasivo": total_p, "total_patrimonio": total_pat, "resultado": ni, "diferencia": dif, "cuadra": abs(dif) < 0.02}

    def _resultado_acum(self, fecha, moneda="BS") -> float:
        """Resultado acumulado de las cuentas de ingresos y gastos desde el inicio de la gestión a la fecha (excluye cierre)."""
        acum = self._mov(None, fecha, moneda, False)
        tot = 0.0
        for c in self._plan():
            if c["es_movimiento"] and c["tipo"] in ("I", "G") and c["id"] in acum:
                d, h = acum[c["id"]]
                tot += h - d
        return r2(tot)

    # ------------------------------------------------------- estado de resultados
    def estado_resultados(self, desde, hasta, nivel: int = 4, moneda: str = "BS") -> dict:
        mov = self.ctx.libros.acumular(self._mov(desde, hasta, moneda, False))
        plan = self._plan()
        by_code = {c["codigo"]: c for c in plan}

        def val(cod: str, signo: int) -> float:
            c = by_code.get(cod)
            if not c or c["id"] not in mov:
                return 0.0
            d, h = mov[c["id"]]
            return r2((h - d) if signo > 0 else (d - h))

        filas: list[dict] = []

        def detalle(prefijo: str, signo: int, nivel_ini: int = 3):
            for c in plan:
                if c["codigo"].startswith(prefijo + ".") and nivel_ini <= c["nivel"] <= nivel and c["id"] in mov:
                    d, h = mov[c["id"]]
                    v = r2((h - d) if signo > 0 else (d - h))
                    if abs(v) >= 0.005:
                        filas.append(_f(c["nombre"], v, c["nivel"] - 2, "grupo" if not c["es_movimiento"] else "", c["codigo"]))

        ventas = val("4.1", 1)
        filas.append(_f("INGRESOS OPERATIVOS", None, 0, "titulo"))
        detalle("4.1", 1)
        filas.append(_f("Ventas netas", ventas, 0, "subtotal"))
        costo = r2(val("5.1", -1) + val("5.2", -1))
        filas.append(_f("COSTO DE VENTAS Y PRODUCCIÓN", None, 0, "titulo"))
        detalle("5.1", -1)
        detalle("5.2", -1)
        filas.append(_f("Total costo de ventas", costo, 0, "subtotal"))
        bruta = r2(ventas - costo)
        filas.append(_f("UTILIDAD BRUTA", bruta, 0, "total"))
        adm, com = val("5.3", -1), val("5.4", -1)
        filas.append(_f("GASTOS OPERATIVOS", None, 0, "titulo"))
        filas.append(_f("Gastos de administración", adm, 0, "subtotal"))
        detalle("5.3", -1)
        filas.append(_f("Gastos de comercialización", com, 0, "subtotal"))
        detalle("5.4", -1)
        operativo = r2(bruta - adm - com)
        filas.append(_f("UTILIDAD (PÉRDIDA) OPERATIVA", operativo, 0, "total"))
        otros_i, fin, otros_g = val("4.2", 1), val("5.5", -1), val("5.6", -1)
        filas.append(_f("OTROS INGRESOS Y EGRESOS", None, 0, "titulo"))
        filas.append(_f("Otros ingresos", otros_i, 0, "subtotal"))
        detalle("4.2", 1)
        filas.append(_f("Gastos financieros (incluye diferencia de cambio y ajuste por inflación)", fin, 0, "subtotal"))
        detalle("5.5", -1)
        filas.append(_f("Otros gastos", otros_g, 0, "subtotal"))
        detalle("5.6", -1)
        antes = r2(operativo + otros_i - fin - otros_g)
        filas.append(_f("RESULTADO ANTES DE IMPUESTOS", antes, 0, "total"))
        iue = 0.0
        neto = antes
        if self.ctx.param("IUE_PROVISION") == "1" and antes > 0:
            iue = r2(antes * self.ctx.normativa.num("IUE_PCT", hasta) / 100)
            filas.append(_f(f"Impuesto a las Utilidades de las Empresas - IUE ({self.ctx.normativa.num('IUE_PCT', hasta):g}%) estimado", iue, 0, "subtotal"))
            neto = r2(antes - iue)
        filas.append(_f("RESULTADO NETO DEL PERÍODO", neto, 0, "total"))
        return {"titulo": "ESTADO DE RESULTADOS", "desde": iso(desde), "hasta": iso(hasta), "moneda": moneda, "filas": filas, "ventas": ventas, "costo": costo,
                "utilidad_bruta": bruta, "operativo": operativo, "antes_impuestos": antes, "iue": iue, "neto": neto}

    # ----------------------------------------------------- evolución del patrimonio
    def evolucion_patrimonio(self, desde, hasta) -> dict:
        d, h = to_date(desde), to_date(hasta)
        plan = [c for c in self._plan() if c["tipo"] == "T" and c["es_movimiento"]]
        cols = [("CAPITAL", "Capital social"), ("AJCAPITAL", "Ajuste de capital"), ("RESERVAS", "Reservas"), ("RESULT", "Resultados acumulados"),
                ("EJERCICIO", "Resultado del ejercicio")]
        # saldo inicial: apertura + todo lo anterior a 'desde'
        previo = self._mov(None, d - timedelta(days=1), "BS", True)
        apertura = self._mov(d, h, "BS", True, solo_apertura=True)
        periodo = self._mov(d, h, "BS", False)
        ini = {k: 0.0 for k, _ in cols}
        mov_filas = []
        movimientos = {k: 0.0 for k, _ in cols}
        for c in plan:
            col = c["patr_col"] or "RESULT"
            pd, ph = previo.get(c["id"], (0.0, 0.0))
            ad, ah = apertura.get(c["id"], (0.0, 0.0))
            ini[col] += (ph - pd) + (ah - ad)
            md, mh = periodo.get(c["id"], (0.0, 0.0))
            v = mh - md
            if abs(v) >= 0.005:
                mov_filas.append({"texto": c["nombre"], "columna": col, "importe": r2(v)})
                movimientos[col] += v
        # resultado: resultados previos de la misma gestión pasan a iniciales si el período no empieza con la gestión
        res_prev = 0.0
        if d > self.ctx.inicio:
            res_prev = self._resultado_acum(d - timedelta(days=1))
        ini["RESULT"] += res_prev
        ni = self.resultado(d, h)
        movimientos["EJERCICIO"] += ni
        fin = {k: r2(ini[k] + movimientos[k]) for k, _ in cols}
        filas = [{"texto": f"Saldos al {fdate(d)} (inicio del período)", "valores": {k: r2(ini[k]) for k, _ in cols}, "estilo": "total"}]
        for m in mov_filas:
            filas.append({"texto": f"Movimiento: {m['texto']}", "valores": {m["columna"]: m["importe"]}, "estilo": ""})
        filas.append({"texto": "Resultado neto del período", "valores": {"EJERCICIO": ni}, "estilo": ""})
        filas.append({"texto": f"Saldos al {fdate(h)}", "valores": fin, "estilo": "total"})
        return {"titulo": "ESTADO DE EVOLUCIÓN DEL PATRIMONIO NETO", "desde": d.isoformat(), "hasta": h.isoformat(), "columnas": cols, "filas": filas,
                "total_inicial": r2(sum(ini.values())), "total_final": r2(sum(fin.values())), "neto": ni}

    # --------------------------------------------------------- flujo de efectivo
    def _efectivo(self, fecha) -> float:
        sal = self._saldos_a(fecha)
        return r2(sum(sal.get(c["id"], 0.0) for c in self._plan() if c["es_movimiento"] and c["flujo"] == "EFECTIVO"))

    def _efectivo_inicial(self, desde) -> float:
        d = to_date(desde)
        previo = self._mov(None, d - timedelta(days=1), "BS", True)
        aper = self._mov(d, None, "BS", True, solo_apertura=True)
        tot = 0.0
        for c in self._plan():
            if c["es_movimiento"] and c["flujo"] == "EFECTIVO":
                a, b = previo.get(c["id"], (0, 0))
                x, y = aper.get(c["id"], (0, 0))
                tot += (a - b) + (x - y)
        return r2(tot)

    def flujo_directo(self, desde, hasta) -> dict:
        d, h = to_date(desde), to_date(hasta)
        cuentas = {c["id"]: c for c in self._plan()}
        rows = self.db.query(
            "SELECT d.comprobante_id, d.cuenta_id, d.debe_bs, d.haber_bs FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id "
            "WHERE c.estado='V' AND c.origen NOT IN ('CIERRE','APERTURA') AND c.fecha BETWEEN ? AND ? ORDER BY d.comprobante_id", (d.isoformat(), h.isoformat()))
        por_comp: dict[int, list] = {}
        for r in rows:
            por_comp.setdefault(r["comprobante_id"], []).append(r)
        cat = {k: 0.0 for k in ("COBROS", "PAGOS_PROV", "PAGOS_PERS", "IMPUESTOS", "OTROS_OP", "INV_ENT", "INV_SAL", "FIN_ENT", "FIN_SAL", "TC")}
        for lineas in por_comp.values():
            if not any(cuentas[l["cuenta_id"]]["flujo"] == "EFECTIVO" for l in lineas):
                continue
            for l in lineas:
                c = cuentas[l["cuenta_id"]]
                if c["flujo"] == "EFECTIVO":
                    continue
                w = -(l["debe_bs"] - l["haber_bs"])  # efecto en efectivo de esta línea
                fl = c["flujo"]
                if fl == "INV":
                    cat["INV_ENT" if w > 0 else "INV_SAL"] += w
                elif fl == "FIN":
                    cat["FIN_ENT" if w > 0 else "FIN_SAL"] += w
                elif fl in cat:
                    cat[fl] += w
                else:  # NOCASH, NA: se asigna a otros operativos para no perder la conciliación
                    cat["OTROS_OP"] += w
        cat = {k: r2(v) for k, v in cat.items()}
        op = r2(cat["COBROS"] + cat["PAGOS_PROV"] + cat["PAGOS_PERS"] + cat["IMPUESTOS"] + cat["OTROS_OP"])
        inv = r2(cat["INV_ENT"] + cat["INV_SAL"])
        fin = r2(cat["FIN_ENT"] + cat["FIN_SAL"])
        variacion = r2(op + inv + fin + cat["TC"])
        ini, fin_ef = self._efectivo_inicial(d), self._efectivo(h)
        filas = [
            _f("ACTIVIDADES DE OPERACIÓN", None, 0, "titulo"),
            _f("Cobros a clientes y por ventas", cat["COBROS"], 1), _f("Pagos a proveedores, costos y gastos de operación", cat["PAGOS_PROV"], 1),
            _f("Pagos al personal y cargas sociales", cat["PAGOS_PERS"], 1), _f("Impuestos pagados y recuperados, netos (IVA, IT, IUE y otros)", cat["IMPUESTOS"], 1),
            _f("Otros cobros y pagos operativos (incluye intereses)", cat["OTROS_OP"], 1),
            _f("Flujo neto de actividades de operación", op, 0, "subtotal"),
            _f("ACTIVIDADES DE INVERSIÓN", None, 0, "titulo"),
            _f("Venta de activos fijos e inversiones", cat["INV_ENT"], 1), _f("Adquisición de activos fijos e inversiones", cat["INV_SAL"], 1),
            _f("Flujo neto de actividades de inversión", inv, 0, "subtotal"),
            _f("ACTIVIDADES DE FINANCIAMIENTO", None, 0, "titulo"),
            _f("Obtención de préstamos y aportes de capital", cat["FIN_ENT"], 1), _f("Pago de préstamos y distribución de utilidades", cat["FIN_SAL"], 1),
            _f("Flujo neto de actividades de financiamiento", fin, 0, "subtotal"),
            _f("Efecto de la variación del tipo de cambio sobre el efectivo", cat["TC"], 0, "subtotal"),
            _f("VARIACIÓN NETA DEL EFECTIVO Y EQUIVALENTES", variacion, 0, "total"),
            _f("Efectivo y equivalentes al inicio del período", ini, 0), _f("Efectivo y equivalentes al final del período", r2(ini + variacion), 0, "total"),
        ]
        return {"titulo": "ESTADO DE FLUJO DE EFECTIVO - MÉTODO DIRECTO", "desde": d.isoformat(), "hasta": h.isoformat(), "filas": filas, "operacion": op,
                "inversion": inv, "financiamiento": fin, "tc": cat["TC"], "variacion": variacion, "efectivo_inicial": ini, "efectivo_final": fin_ef,
                "cuadra": abs(ini + variacion - fin_ef) < 0.05}

    def flujo_indirecto(self, desde, hasta) -> dict:
        d, h = to_date(desde), to_date(hasta)
        mov = self._mov(d, h, "BS", False)
        ni = self.resultado(d, h)
        filas_ind = {"NOCASH": 0.0, "CXC": 0.0, "INVENT": 0.0, "OTROS_ACT": 0.0, "CXP": 0.0, "IMPUESTOS": 0.0, "LABORAL": 0.0, "OTROS_PAS": 0.0,
                     "INV": 0.0, "FIN": 0.0}
        for c in self._plan():
            if not c["es_movimiento"] or c["tipo"] not in ("A", "P", "T") or c["flujo"] in ("EFECTIVO", "NA"):
                continue
            dd, hh = mov.get(c["id"], (0.0, 0.0))
            aporte = -(dd - hh)  # contribución al efectivo
            if abs(aporte) < 1e-9:
                continue
            cod, fl = c["codigo"], c["flujo"]
            if fl == "NOCASH":
                k = "NOCASH"
            elif fl == "INV":
                k = "INV"
            elif fl == "FIN":
                k = "FIN"
            elif fl == "COBROS":
                k = "CXC"
            elif cod.startswith("1.1.3"):
                k = "INVENT"
            elif fl == "IMPUESTOS":
                k = "IMPUESTOS"
            elif fl == "PAGOS_PERS":
                k = "LABORAL"
            elif cod.startswith("2.1.1.01") or (fl == "PAGOS_PROV" and c["tipo"] == "P"):
                k = "CXP"
            elif c["tipo"] == "A":
                k = "OTROS_ACT"
            else:
                k = "OTROS_PAS"
            filas_ind[k] += aporte
        v = {k: r2(x) for k, x in filas_ind.items()}
        op = r2(ni + v["NOCASH"] + v["CXC"] + v["INVENT"] + v["OTROS_ACT"] + v["CXP"] + v["IMPUESTOS"] + v["LABORAL"] + v["OTROS_PAS"])
        variacion = r2(op + v["INV"] + v["FIN"])
        ini, fin_ef = self._efectivo_inicial(d), self._efectivo(h)
        filas = [
            _f("ACTIVIDADES DE OPERACIÓN", None, 0, "titulo"),
            _f("Resultado neto del período", ni, 1),
            _f("Ajustes por partidas que no requieren efectivo (depreciaciones, amortizaciones y otras)", v["NOCASH"], 1),
            _f("Cambios en activos y pasivos operativos:", None, 1, "grupo"),
            _f("(Aumento) disminución en cuentas por cobrar y anticipos de clientes", v["CXC"], 2),
            _f("(Aumento) disminución en inventarios", v["INVENT"], 2),
            _f("(Aumento) disminución en gastos pagados por adelantado y otros activos", v["OTROS_ACT"], 2),
            _f("Aumento (disminución) en cuentas por pagar comerciales", v["CXP"], 2),
            _f("Aumento (disminución) en obligaciones fiscales (IVA, IT, IUE)", v["IMPUESTOS"], 2),
            _f("Aumento (disminución) en obligaciones laborales y sociales", v["LABORAL"], 2),
            _f("Aumento (disminución) en otros pasivos", v["OTROS_PAS"], 2),
            _f("Flujo neto de actividades de operación", op, 0, "subtotal"),
            _f("ACTIVIDADES DE INVERSIÓN", None, 0, "titulo"),
            _f("Adquisición / venta de activos fijos, intangibles e inversiones (neto)", v["INV"], 1),
            _f("Flujo neto de actividades de inversión", v["INV"], 0, "subtotal"),
            _f("ACTIVIDADES DE FINANCIAMIENTO", None, 0, "titulo"),
            _f("Préstamos, aportes de capital y distribución de utilidades (neto)", v["FIN"], 1),
            _f("Flujo neto de actividades de financiamiento", v["FIN"], 0, "subtotal"),
            _f("VARIACIÓN NETA DEL EFECTIVO Y EQUIVALENTES", variacion, 0, "total"),
            _f("Efectivo y equivalentes al inicio del período", ini, 0), _f("Efectivo y equivalentes al final del período", r2(ini + variacion), 0, "total"),
        ]
        return {"titulo": "ESTADO DE FLUJO DE EFECTIVO - MÉTODO INDIRECTO", "desde": d.isoformat(), "hasta": h.isoformat(), "filas": filas, "operacion": op,
                "inversion": v["INV"], "financiamiento": v["FIN"], "variacion": variacion, "efectivo_inicial": ini, "efectivo_final": fin_ef,
                "cuadra": abs(ini + variacion - fin_ef) < 0.05}

    # ------------------------------------------------------------------- notas
    def notas(self, fecha_ini, fecha_fin) -> list[dict]:
        ctx = self.ctx
        d, h = to_date(fecha_ini), to_date(fecha_fin)
        e = ctx.empresa
        sal = self._saldos_a(h)
        plan = self._plan()
        usd = ctx.tc.dolar(h)

        def tabla(prefijo: str, signo: int = 1, nivel_max: int = 5, solo_mov=True):
            filas = []
            for c in plan:
                if c["codigo"].startswith(prefijo) and c["codigo"] != prefijo and (c["es_movimiento"] if solo_mov else c["nivel"] <= nivel_max):
                    v = sal.get(c["id"], 0.0) * signo
                    if abs(v) >= 0.005:
                        filas.append([c["codigo"], c["nombre"], r2(v)])
            return filas

        def total(filas):
            return r2(sum(f[2] for f in filas))

        def con_total(filas):
            return filas + [["", "TOTAL", total(filas)]] if filas else []

        notas = []
        notas.append({"n": 1, "titulo": "NATURALEZA Y OBJETO DE LA EMPRESA", "parrafos": [
            f"{e['razon_social']}"
            + (f" ({e['nombre_comercial']})" if e.get("nombre_comercial") else "")
            + f", con NIT {e.get('nit') or 's/n'}, domiciliada en {e.get('direccion') or 's/d'}, {e.get('ciudad') or ''}, Bolivia."
            + (f" Actividad principal: {e['actividad']}." if e.get("actividad") else ""),
            f"Los presentes estados financieros corresponden a la gestión comprendida entre el {fdate(d)} y el {fdate(h)}."]})
        infl = ctx.normativa.raw("AJUSTE_INFLACION_CONTABLE", h) == "1"
        notas.append({"n": 2, "titulo": "BASES DE PREPARACIÓN Y PRINCIPALES POLÍTICAS CONTABLES", "parrafos": [
            "a) Bases de preparación: los estados financieros se presentan en bolivianos (Bs) y se preparan de acuerdo con las Normas de Contabilidad "
            "Generalmente Aceptadas en Bolivia (PCGA) emitidas por el Consejo Técnico Nacional de Auditoría y Contabilidad (CTNAC).",
            "b) Consideración de los efectos de la inflación: " + (
                "los estados financieros se reexpresan en moneda constante utilizando la Unidad de Fomento a la Vivienda (UFV), según la Norma Contable N° 3."
                if infl else
                "de acuerdo con la Resolución CTNAC 03/2020 se suspendió el ajuste por inflación contable de la Norma Contable N° 3; los saldos se presentan a valores "
                "históricos. Para efectos tributarios se mantiene la actualización de activos fijos con la variación de la UFV conforme al D.S. 24051."),
            f"c) Moneda extranjera: los activos y pasivos en dólares estadounidenses se convierten al tipo de cambio oficial vigente al cierre (Bs {usd:.2f} por US$ 1). "
            "Las diferencias de cambio se registran en los resultados del ejercicio.",
            "d) Inventarios: se valúan al costo de adquisición o producción mediante el método de promedio ponderado, sin exceder el valor neto de realización; "
            "para productos con vencimiento se aplica el criterio de primeros en vencer, primeros en salir.",
            "e) Activos fijos: se registran al costo de adquisición. La depreciación se calcula por el método de línea recta aplicando los coeficientes del "
            "Decreto Supremo N° 24051 sobre el valor del activo.",
            "f) Previsión para indemnizaciones: se constituye para todo el personal por el total del pasivo devengado a la fecha de cierre, de acuerdo con "
            "disposiciones legales vigentes (indemnización por tiempo de servicio).",
            f"g) Impuestos: la empresa está sujeta al IVA ({ctx.normativa.num('IVA_PCT', h):g}%), al Impuesto a las Transacciones ({ctx.normativa.num('IT_PCT', h):g}%) y al "
            f"Impuesto a las Utilidades de las Empresas ({ctx.normativa.num('IUE_PCT', h):g}%). Las retenciones y aportes laborales se pagan en los plazos de ley."]})
        disp = con_total(tabla("1.1.1."))
        notas.append({"n": 3, "titulo": "DISPONIBLE (CAJA Y BANCOS)", "parrafos": [f"El disponible al {fdate(h)} se compone de:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": disp}})
        exig = con_total(tabla("1.1.2.", 1))
        notas.append({"n": 4, "titulo": "EXIGIBLE", "parrafos": ["Comprende cuentas por cobrar comerciales, anticipos e impuestos por recuperar:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": exig}})
        inv = con_total(tabla("1.1.3."))
        notas.append({"n": 5, "titulo": "INVENTARIOS", "parrafos": ["Los inventarios se valúan al costo promedio ponderado:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": inv}})
        af_filas = []
        for g in ctx.activos.grupos():
            ca, cd = ctx.cuentas.por_codigo(g["cta_activo"]), ctx.cuentas.por_codigo(g["cta_dep"])
            costo = sal.get(ca["id"], 0.0) if ca else 0.0
            dep = -sal.get(cd["id"], 0.0) if cd else 0.0
            if abs(costo) >= 0.005 or abs(dep) >= 0.005:
                af_filas.append([g["nombre"], r2(costo), r2(dep), r2(costo - dep)])
        if af_filas:
            af_filas.append(["TOTAL", r2(sum(f[1] for f in af_filas)), r2(sum(f[2] for f in af_filas)), r2(sum(f[3] for f in af_filas))])
        notas.append({"n": 6, "titulo": "ACTIVOS FIJOS", "parrafos": ["El detalle de activos fijos, depreciación acumulada y valor neto es:"],
                      "tabla": {"cols": ["Grupo", "Costo", "Depreciación acumulada", "Valor neto"], "filas": af_filas}})
        pas_c = con_total(tabla("2.1.", -1))
        notas.append({"n": 7, "titulo": "PASIVO CORRIENTE", "parrafos": ["Las obligaciones a corto plazo comprenden:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": pas_c}})
        pas_n = con_total(tabla("2.2.", -1))
        notas.append({"n": 8, "titulo": "PASIVO NO CORRIENTE", "parrafos": ["Las obligaciones a largo plazo y previsiones comprenden:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": pas_n}})
        pat = tabla("3.", -1)
        pat.append(["RES", "Resultado de la gestión (utilidad o pérdida)", self._resultado_acum(h)])
        notas.append({"n": 9, "titulo": "PATRIMONIO", "parrafos": ["El patrimonio neto está compuesto por:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": con_total(pat)}})
        mov = self.ctx.libros.acumular(self._mov(d, h, "BS", False))
        ing_filas = []
        for c in plan:
            if c["tipo"] == "I" and c["es_movimiento"] and c["id"] in mov:
                dd, hh = mov[c["id"]]
                if abs(hh - dd) >= 0.005:
                    ing_filas.append([c["codigo"], c["nombre"], r2(hh - dd)])
        notas.append({"n": 10, "titulo": "INGRESOS", "parrafos": ["Los ingresos de la gestión se detallan a continuación:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": con_total(ing_filas)}})
        gas_filas = []
        for c in plan:
            if c["tipo"] == "G" and c["es_movimiento"] and c["id"] in mov:
                dd, hh = mov[c["id"]]
                if abs(dd - hh) >= 0.005:
                    gas_filas.append([c["codigo"], c["nombre"], r2(dd - hh)])
        notas.append({"n": 11, "titulo": "COSTOS Y GASTOS", "parrafos": ["Los costos y gastos de la gestión se detallan a continuación:"], "tabla": {"cols": ["Código", "Cuenta", "Bs"], "filas": con_total(gas_filas)}})
        me_filas = []
        usd_sal = self._saldos_a(h, "USD")
        for c in plan:
            if c["moneda_extranjera"] and c["es_movimiento"]:
                u = usd_sal.get(c["id"], 0.0)
                if abs(u) >= 0.005:
                    me_filas.append([c["codigo"], c["nombre"], r2(u), r2(sal.get(c["id"], 0.0))])
        notas.append({"n": 12, "titulo": "POSICIÓN EN MONEDA EXTRANJERA", "parrafos": [f"Saldos en dólares estadounidenses al tipo de cambio de Bs {usd:.2f}:"],
                      "tabla": {"cols": ["Código", "Cuenta", "US$", "Equivalente Bs"], "filas": me_filas}})
        notas.append({"n": 13, "titulo": "CONTINGENCIAS", "parrafos": [ctx.param("NOTA_CONTINGENCIAS") or
                      "Al cierre de la gestión la empresa no tiene conocimiento de contingencias probables o significativas que requieran ser registradas o reveladas."]})
        notas.append({"n": 14, "titulo": "HECHOS POSTERIORES", "parrafos": [ctx.param("NOTA_HECHOS_POSTERIORES") or
                      "Con posterioridad al cierre de la gestión y hasta la fecha de emisión de estos estados financieros no se han producido hechos significativos que afecten su presentación."]})
        return notas
