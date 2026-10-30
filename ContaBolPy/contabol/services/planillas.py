"""Planillas de sueldos: aportes AFP/CNS, bono de antigüedad, ANS, RC-IVA, aguinaldo e indemnización.

Todos los porcentajes y escalas se leen de la normativa con vigencia (tabla normativa) según el período."""
from __future__ import annotations

from datetime import date

from ..sistema import ErrorNegocio
from ..util import anios_meses_dias, fin_de_mes, iso, r2, to_date


class PlanillaService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db
        self.n = ctx.normativa

    # ------------------------------------------------------------- empleados
    def empleados(self, solo_activos: bool = True, texto: str = "") -> list[dict]:
        sql, p = "SELECT * FROM empleado WHERE 1=1", []
        if solo_activos:
            sql += " AND activo=1"
        if texto:
            sql += " AND (nombre LIKE ? OR ci LIKE ? OR codigo LIKE ?)"
            p += [f"%{texto}%"] * 3
        return self.db.query(sql + " ORDER BY nombre", p)

    def empleado(self, eid: int) -> dict | None:
        return self.db.one("SELECT * FROM empleado WHERE id=?", (eid,))

    def guardar_empleado(self, d: dict) -> int:
        ctx = self.ctx
        ctx.requiere("RH.EMPLEADOS")
        nombre, ci = (d.get("nombre") or "").strip(), (d.get("ci") or "").strip()
        if not nombre or not ci:
            raise ErrorNegocio("Nombre y CI son obligatorios.")
        fi = to_date(d.get("fecha_ingreso"))
        if not fi:
            raise ErrorNegocio("La fecha de ingreso no es válida.")
        haber = r2(d.get("haber_basico") or 0)
        smn = self.n.smn(fi if fi > date.today() else date.today())
        if haber < smn and not d.get("permitir_menor_smn"):
            raise ErrorNegocio(f"El haber básico (Bs {haber:,.2f}) es menor al salario mínimo nacional vigente (Bs {smn:,.2f}).")
        codigo = (d.get("codigo") or "").strip() or f"E{int(self.db.scalar('SELECT COUNT(*) FROM empleado', (), 0)) + 1:04d}"
        if self.db.scalar("SELECT COUNT(*) FROM empleado WHERE (codigo=? OR ci=?) AND id<>?", (codigo, ci, d.get("id") or 0)):
            raise ErrorNegocio("Ya existe un empleado con ese código o CI.")
        vals = dict(codigo=codigo, nombre=nombre, ci=ci, nua=d.get("nua"), fecha_ingreso=fi.isoformat(), fecha_retiro=iso(d.get("fecha_retiro")),
                    cargo=d.get("cargo"), haber_basico=haber, bono_fijo=r2(d.get("bono_fijo") or 0), afp=d.get("afp") or "GESTORA",
                    aporta_afp=1 if d.get("aporta_afp", True) else 0, mayor_65=1 if d.get("mayor_65") else 0, jubilado=1 if d.get("jubilado") else 0,
                    centro_id=d.get("centro_id") or None, banco=d.get("banco"), cuenta_banco=d.get("cuenta_banco"),
                    activo=1 if d.get("activo", True) else 0)
        if d.get("id"):
            self.db.update("empleado", d["id"], **vals)
            return d["id"]
        return self.db.insert("empleado", **vals)

    # ---------------------------------------------------------------- cálculos
    def bono_antiguedad(self, fecha_ingreso, fecha_calculo, smn: float | None = None) -> float:
        fi, fc = to_date(fecha_ingreso), to_date(fecha_calculo)
        anios = anios_meses_dias(fi, fc)[0]
        base = self.n.num("BONO_ANTIG_BASE_SMN", fc) * (smn if smn is not None else self.n.smn(fc))
        pct = 0.0
        for desde, hasta, p in self.n.json("BONO_ANTIG_ESCALA", fc):
            if desde <= anios < hasta:
                pct = p
        return r2(base * pct / 100.0)

    def ans(self, total_ganado: float, fecha) -> float:
        total = 0.0
        for i in (1, 2, 3):
            monto, pct = self.n.num(f"ANS_T{i}_MONTO", fecha), self.n.num(f"ANS_T{i}_PCT", fecha)
            if total_ganado > monto:
                total += (total_ganado - monto) * pct / 100.0
        return r2(total)

    def calcular(self, e: dict, anio: int, mes: int, entradas: dict | None = None, rc_saldo_ant: float = 0.0, ufv_ant: float = 0.0,
                 ufv_mes: float = 0.0, anticipo_mes: float = 0.0) -> dict:
        """Calcula una fila de planilla para un empleado."""
        en = entradas or {}
        fin = fin_de_mes(anio, mes)
        n = self.n
        smn = n.smn(fin)
        dias_mes = int(n.num("DIAS_MES_LABORAL", fin))
        dias = int(en.get("dias", dias_mes))
        if not 0 <= dias <= dias_mes:
            raise ErrorNegocio(f"Los días trabajados deben estar entre 0 y {dias_mes}.")
        fa = dias / dias_mes
        haber = r2(e["haber_basico"] * fa)
        bono_ant = r2(self.bono_antiguedad(e["fecha_ingreso"], fin, smn) * fa)
        valor_hora = e["haber_basico"] / dias_mes / n.num("HORAS_DIA", fin)
        he = float(en.get("horas_extra", 0))
        hn = float(en.get("horas_nocturnas", 0))
        dom = float(en.get("domingos", 0))
        monto_extra = r2(he * valor_hora * (1 + n.num("RECARGO_HEXTRA_PCT", fin) / 100))
        recargo_noct = r2(hn * valor_hora * n.num("RECARGO_NOCTURNO_PCT", fin) / 100)
        dominical = r2(dom * (e["haber_basico"] / dias_mes) * n.num("RECARGO_DOMINICAL_PCT", fin) / 100)
        otros = r2(float(en.get("otros_bonos", 0)) + e["bono_fijo"] * fa)
        total_ganado = r2(haber + bono_ant + monto_extra + recargo_noct + dominical + otros)
        pct = lambda k: n.num(k, fin) / 100.0  # noqa: E731
        vejez = riesgo = comision = solidario = ans = 0.0
        if e["aporta_afp"]:
            if e["jubilado"] or e["mayor_65"]:
                solidario = r2(total_ganado * pct("AFP_SOLIDARIO"))
            else:
                vejez = r2(total_ganado * pct("AFP_VEJEZ"))
                riesgo = r2(total_ganado * pct("AFP_RIESGO_COMUN"))
                comision = r2(total_ganado * pct("AFP_COMISION"))
                solidario = r2(total_ganado * pct("AFP_SOLIDARIO"))
            ans = self.ans(total_ganado, fin)
        aportes = r2(vejez + riesgo + comision + solidario)
        # RC-IVA dependientes
        rc_neto = r2(total_ganado - aportes)
        rc_base = r2(max(0.0, rc_neto - n.num("RCIVA_MIN_SMN", fin) * smn))
        rc_imp = r2(rc_base * pct("RCIVA_PCT"))
        rc_cred = r2(min(rc_imp, pct("RCIVA_PCT") * n.num("RCIVA_CRED_SMN", fin) * smn)) if rc_base > 0 else 0.0
        rc_fact = r2(float(en.get("rc_facturas", 0)) * pct("RCIVA_PCT"))
        mant = r2(rc_saldo_ant * (ufv_mes / ufv_ant - 1)) if rc_saldo_ant > 0 and ufv_ant > 0 and ufv_mes > ufv_ant else 0.0
        imp1 = r2(max(0.0, rc_imp - rc_cred))
        disponible = r2(rc_fact + rc_saldo_ant + mant)
        rciva = r2(max(0.0, imp1 - disponible))
        saldo_sig = r2(max(0.0, disponible - imp1))
        otros_desc = r2(float(en.get("otros_desc", 0)))
        total_desc = r2(aportes + ans + rciva + anticipo_mes + otros_desc)
        liquido = r2(total_ganado - total_desc)
        pat_cns = r2(total_ganado * pct("PAT_CNS"))
        pat_riesgo = r2(total_ganado * pct("PAT_RIESGO_PROF"))
        pat_viv = r2(total_ganado * pct("PAT_VIVIENDA"))
        pat_sol = r2(total_ganado * pct("PAT_SOLIDARIO"))
        pat_inf = r2(total_ganado * pct("PAT_INFOCAL"))
        return dict(dias=dias, haber_basico=haber, bono_antig=bono_ant, horas_extra=he, monto_extra=monto_extra, recargo_nocturno=recargo_noct,
                    dominical=dominical, otros_bonos=otros, total_ganado=total_ganado, afp_vejez=vejez, afp_riesgo=riesgo, afp_comision=comision,
                    afp_solidario=solidario, ans=ans, rciva=rciva, anticipos=r2(anticipo_mes), otros_desc=otros_desc, total_desc=total_desc, liquido=liquido,
                    pat_cns=pat_cns, pat_riesgo=pat_riesgo, pat_vivienda=pat_viv, pat_solidario=pat_sol, pat_infocal=pat_inf, rc_neto=rc_neto,
                    rc_base=rc_base, rc_impuesto=rc_imp, rc_cred_smn=rc_cred, rc_facturas=rc_fact, rc_saldo_ant=r2(rc_saldo_ant), rc_mant_valor=mant,
                    rc_saldo_sig=saldo_sig)

    # ----------------------------------------------------------------- planillas
    def planilla(self, anio: int, mes: int) -> dict | None:
        return self.db.one("SELECT * FROM planilla WHERE anio=? AND mes=?", (anio, mes))

    def detalle(self, planilla_id: int) -> list[dict]:
        return self.db.query("SELECT d.*, e.nombre, e.ci, e.cargo, e.codigo, e.fecha_ingreso, e.nua FROM planilla_det d JOIN empleado e ON e.id=d.empleado_id "
                             "WHERE d.planilla_id=? ORDER BY e.nombre", (planilla_id,))

    def _saldo_rc_previo(self, anio: int, mes: int, eid: int) -> tuple[float, float]:
        ant = self.db.one("SELECT d.rc_saldo_sig, p.ufv_mes FROM planilla_det d JOIN planilla p ON p.id=d.planilla_id "
                          "WHERE d.empleado_id=? AND (p.anio*100+p.mes)<? ORDER BY p.anio DESC, p.mes DESC LIMIT 1", (eid, anio * 100 + mes))
        return (ant["rc_saldo_sig"], ant["ufv_mes"]) if ant else (0.0, 0.0)

    def generar(self, anio: int, mes: int) -> int:
        """Crea (o recrea si está en borrador) la planilla del mes con todos los empleados vigentes."""
        ctx = self.ctx
        ctx.requiere("RH.PLANILLA")
        ctx.requiere_abierta()
        if not ctx.inicio <= fin_de_mes(anio, mes) <= ctx.fin:
            raise ErrorNegocio("El mes está fuera de la gestión.")
        fin = fin_de_mes(anio, mes)
        ini = date(anio, mes, 1)
        ex = self.planilla(anio, mes)
        if ex and ex["estado"] != "B":
            raise ErrorNegocio("La planilla de ese mes ya fue cerrada.")
        emps = self.db.query("SELECT * FROM empleado WHERE activo=1 AND fecha_ingreso<=? AND (fecha_retiro IS NULL OR fecha_retiro>=?) ORDER BY nombre",
                             (fin.isoformat(), ini.isoformat()))
        if not emps:
            raise ErrorNegocio("No hay empleados vigentes para el mes.")
        ufv_mes = ctx.tc.ufv(fin)
        with self.db.tx():
            if ex:
                pid = ex["id"]
                self.db.execute("DELETE FROM planilla_det WHERE planilla_id=?", (pid,))
                self.db.update("planilla", pid, smn=self.n.smn(fin), ufv_mes=ufv_mes)
            else:
                pid = self.db.insert("planilla", anio=anio, mes=mes, smn=self.n.smn(fin), ufv_mes=ufv_mes)
            for e in emps:
                dias = 30
                if to_date(e["fecha_ingreso"]) > ini:
                    dias = max(0, 30 - to_date(e["fecha_ingreso"]).day + 1)
                if e["fecha_retiro"] and to_date(e["fecha_retiro"]) <= fin:
                    dias = min(dias, to_date(e["fecha_retiro"]).day if to_date(e["fecha_retiro"]).day <= 30 else 30)
                self._guardar_fila(pid, e, anio, mes, {"dias": dias}, ufv_mes)
        ctx.auditar("Planillas", "GENERAR", f"{mes:02d}/{anio}")
        return pid

    def _guardar_fila(self, pid: int, e: dict, anio: int, mes: int, entradas: dict, ufv_mes: float) -> None:
        saldo_ant, ufv_ant = self._saldo_rc_previo(anio, mes, e["id"])
        ant = self.db.one("SELECT COALESCE(SUM(MIN(descuento_mes, saldo)),0) AS d FROM anticipo WHERE empleado_id=? AND saldo>0", (e["id"],))
        fila = self.calcular(e, anio, mes, entradas, saldo_ant, ufv_ant, ufv_mes, ant["d"] if ant else 0.0)
        existente = self.db.one("SELECT id FROM planilla_det WHERE planilla_id=? AND empleado_id=?", (pid, e["id"]))
        if existente:
            self.db.update("planilla_det", existente["id"], **fila)
        else:
            self.db.insert("planilla_det", planilla_id=pid, empleado_id=e["id"], **fila)

    def recalcular_fila(self, pid: int, empleado_id: int, entradas: dict) -> dict:
        p = self.db.one("SELECT * FROM planilla WHERE id=?", (pid,))
        if p["estado"] != "B":
            raise ErrorNegocio("La planilla ya fue cerrada.")
        e = self.empleado(empleado_id)
        self._guardar_fila(pid, e, p["anio"], p["mes"], entradas, p["ufv_mes"])
        return self.db.one("SELECT * FROM planilla_det WHERE planilla_id=? AND empleado_id=?", (pid, empleado_id))

    def totales(self, pid: int) -> dict:
        cols = ["total_ganado", "afp_vejez", "afp_riesgo", "afp_comision", "afp_solidario", "ans", "rciva", "anticipos", "otros_desc", "total_desc",
                "liquido", "pat_cns", "pat_riesgo", "pat_vivienda", "pat_solidario", "pat_infocal", "haber_basico", "bono_antig", "monto_extra",
                "recargo_nocturno", "dominical", "otros_bonos"]
        r = self.db.one("SELECT " + ", ".join(f"COALESCE(SUM({c}),0) AS {c}" for c in cols) + " FROM planilla_det WHERE planilla_id=?", (pid,))
        return {k: r2(v) for k, v in r.items()}

    def cerrar(self, pid: int) -> int:
        """Cierra la planilla y genera el comprobante contable (gastos, aportes y obligaciones)."""
        ctx = self.ctx
        ctx.requiere("RH.PLANILLA")
        ctx.requiere_abierta()
        p = self.db.one("SELECT * FROM planilla WHERE id=?", (pid,))
        if not p or p["estado"] != "B":
            raise ErrorNegocio("La planilla no existe o ya fue cerrada.")
        t = self.totales(pid)
        if t["total_ganado"] <= 0:
            raise ErrorNegocio("La planilla no tiene importes.")
        cp = ctx.cuenta_param
        fecha = fin_de_mes(p["anio"], p["mes"])
        extras = r2(t["monto_extra"] + t["recargo_nocturno"] + t["dominical"])
        lineas = [(cp("CTA_SUELDOS"), t["haber_basico"], 0), (cp("CTA_BONO_ANTIG"), t["bono_antig"], 0), (cp("CTA_HEXTRAS"), extras, 0),
                  (cp("CTA_OTROS_BONOS"), t["otros_bonos"], 0),
                  (cp("CTA_GASTO_CNS"), t["pat_cns"], 0), (cp("CTA_GASTO_RIESGO"), t["pat_riesgo"], 0), (cp("CTA_GASTO_VIVIENDA"), t["pat_vivienda"], 0),
                  (cp("CTA_GASTO_SOLIDARIO"), t["pat_solidario"], 0),
                  (cp("CTA_SUELDOS_PAGAR"), 0, t["liquido"]),
                  (cp("CTA_AFP_LAB_PAGAR"), 0, r2(t["afp_vejez"] + t["afp_riesgo"] + t["afp_comision"] + t["afp_solidario"] + t["ans"])),
                  (cp("CTA_RCIVA_PAGAR"), 0, t["rciva"]), (cp("CTA_ANTICIPO_PERS"), 0, t["anticipos"]), (cp("CTA_CNS_PAGAR"), 0, t["pat_cns"]),
                  (cp("CTA_AFP_PAT_PAGAR"), 0, t["pat_riesgo"]), (cp("CTA_VIVIENDA_PAGAR"), 0, t["pat_vivienda"]), (cp("CTA_SOLIDARIO_PAGAR"), 0, t["pat_solidario"])]
        if t["otros_desc"] > 0:
            lineas.append((cp("CTA_ACREEDORES"), 0, t["otros_desc"]))
        if t["pat_infocal"] > 0:
            lineas += [(cp("CTA_GASTO_SOLIDARIO"), t["pat_infocal"], 0), (cp("CTA_ACREEDORES"), 0, t["pat_infocal"])]
        lineas = [l for l in lineas if l[1] or l[2]]
        with self.db.tx():
            cid = ctx.vouchers.asiento(fecha, f"Planilla de sueldos {p['mes']:02d}/{p['anio']}", lineas, "PLANILLA", pid, tipo="T")
            self.db.execute("UPDATE planilla SET estado='C', comprobante_id=? WHERE id=?", (cid, pid))
            for d in self.db.query("SELECT empleado_id, anticipos FROM planilla_det WHERE planilla_id=? AND anticipos>0", (pid,)):
                resto = d["anticipos"]
                for a in self.db.query("SELECT * FROM anticipo WHERE empleado_id=? AND saldo>0 ORDER BY fecha", (d["empleado_id"],)):
                    x = min(resto, a["descuento_mes"], a["saldo"])
                    self.db.execute("UPDATE anticipo SET saldo=ROUND(saldo-?,2) WHERE id=?", (x, a["id"]))
                    resto = r2(resto - x)
        ctx.auditar("Planillas", "CERRAR", f"{p['mes']:02d}/{p['anio']} líquido Bs {t['liquido']:,.2f}")
        return cid

    def pagar(self, pid: int, fecha, cuenta_id: int | None = None) -> int:
        ctx = self.ctx
        ctx.requiere("RH.PLANILLA")
        p = self.db.one("SELECT * FROM planilla WHERE id=?", (pid,))
        if p["estado"] != "C":
            raise ErrorNegocio("Primero debe cerrar la planilla.")
        t = self.totales(pid)
        cid = ctx.vouchers.asiento(fecha, f"Pago de sueldos {p['mes']:02d}/{p['anio']}",
                                   [(ctx.cuenta_param("CTA_SUELDOS_PAGAR"), t["liquido"], 0), (cuenta_id or ctx.cuenta_param("CTA_CAJA"), 0, t["liquido"])],
                                   "PLANILLA", pid, tipo="E")
        self.db.execute("UPDATE planilla SET estado='P' WHERE id=?", (pid,))
        return cid

    def reabrir(self, pid: int) -> None:
        ctx = self.ctx
        ctx.requiere("RH.PLANILLA")
        p = self.db.one("SELECT * FROM planilla WHERE id=?", (pid,))
        if p["estado"] == "P":
            raise ErrorNegocio("La planilla ya fue pagada; anule el pago primero.")
        if p["estado"] == "C":
            with self.db.tx():
                ctx.vouchers.anular(p["comprobante_id"], interno=True)
                for d in self.db.query("SELECT empleado_id, anticipos FROM planilla_det WHERE planilla_id=? AND anticipos>0", (pid,)):
                    resto = d["anticipos"]
                    for a in self.db.query("SELECT * FROM anticipo WHERE empleado_id=? ORDER BY fecha DESC", (d["empleado_id"],)):
                        x = min(resto, r2(a["monto"] - a["saldo"]))
                        if x > 0:
                            self.db.execute("UPDATE anticipo SET saldo=ROUND(saldo+?,2) WHERE id=?", (x, a["id"]))
                            resto = r2(resto - x)
                self.db.execute("UPDATE planilla SET estado='B', comprobante_id=NULL WHERE id=?", (pid,))

    # ------------------------------------------------------------------ anticipos
    def anticipo(self, empleado_id: int, fecha, monto: float, descuento_mes: float, glosa: str = "", cuenta_id: int | None = None) -> int:
        ctx = self.ctx
        ctx.requiere("RH.PLANILLA")
        ctx.requiere_abierta()
        monto = r2(monto)
        if monto <= 0:
            raise ErrorNegocio("El monto debe ser mayor a cero.")
        e = self.empleado(empleado_id)
        f = ctx.requiere_fecha(fecha)
        with self.db.tx():
            cid = ctx.vouchers.asiento(f, f"Anticipo de sueldo a {e['nombre']} {glosa}".strip(),
                                       [(ctx.cuenta_param("CTA_ANTICIPO_PERS"), monto, 0), (cuenta_id or ctx.cuenta_param("CTA_CAJA"), 0, monto)],
                                       "PLANILLA", None, tipo="E", a_nombre=e["nombre"])
            return self.db.insert("anticipo", empleado_id=empleado_id, fecha=f.isoformat(), monto=monto, descuento_mes=r2(descuento_mes or monto),
                                  saldo=monto, glosa=glosa, comprobante_id=cid)

    # ---------------------------------------------------------- aguinaldo / finiquito
    def _promedio_ganado(self, eid: int, hasta: date, meses: int = 3) -> float:
        filas = self.db.query("SELECT d.total_ganado FROM planilla_det d JOIN planilla p ON p.id=d.planilla_id WHERE d.empleado_id=? AND (p.anio*100+p.mes)<=? "
                              "ORDER BY p.anio DESC, p.mes DESC LIMIT ?", (eid, hasta.year * 100 + hasta.month, meses))
        if filas:
            return r2(sum(f["total_ganado"] for f in filas) / len(filas))
        e = self.empleado(eid)
        return r2(e["haber_basico"] + self.bono_antiguedad(e["fecha_ingreso"], hasta) + e["bono_fijo"])

    def aguinaldo(self, anio: int, fecha_corte=None) -> list[dict]:
        """Aguinaldo de Navidad (1 sueldo por 360 días; mínimo 3 meses de antigüedad). Segundo aguinaldo opcional por normativa."""
        corte = to_date(fecha_corte) or date(anio, 12, 31)
        ini_anio = date(anio, 1, 1)
        filas = []
        for e in self.db.query("SELECT * FROM empleado WHERE fecha_ingreso<=? ORDER BY nombre", (corte.isoformat(),)):
            if e["fecha_retiro"] and to_date(e["fecha_retiro"]) < ini_anio:
                continue
            desde = max(to_date(e["fecha_ingreso"]), ini_anio)
            hasta = min(to_date(e["fecha_retiro"]) or corte, corte)
            a, m, dd = anios_meses_dias(desde, hasta)
            dias = min(360, a * 360 + m * 30 + dd)
            if dias < self.n.num("AGUINALDO_MESES_MIN", corte) * 30:
                continue
            prom = self._promedio_ganado(e["id"], hasta)
            monto = r2(prom * dias / 360.0)
            segundo = monto if self.n.raw("SEGUNDO_AGUINALDO", corte) == "1" else 0.0
            filas.append({"empleado_id": e["id"], "codigo": e["codigo"], "nombre": e["nombre"], "ci": e["ci"], "ingreso": e["fecha_ingreso"], "dias": dias,
                          "promedio": prom, "aguinaldo": monto, "segundo_aguinaldo": segundo, "total": r2(monto + segundo)})
        return filas

    def finiquito(self, empleado_id: int, fecha_retiro, causal: str = "RETIRO_VOLUNTARIO", vacaciones_pendientes_dias: float = 0.0) -> dict:
        """Cálculo referencial de beneficios sociales: indemnización, desahucio, aguinaldo proporcional y vacaciones."""
        e = self.empleado(empleado_id)
        fr = to_date(fecha_retiro)
        fi = to_date(e["fecha_ingreso"])
        a, m, dd = anios_meses_dias(fi, fr)
        total_dias = a * 360 + m * 30 + dd
        prom = self._promedio_ganado(empleado_id, fr)
        indem = 0.0
        if total_dias >= 90:
            indem = r2(prom * self.n.num("INDEM_MESES_POR_ANIO", fr) * (a + m / 12.0 + dd / 360.0))
        desahucio = r2(prom * self.n.num("DESAHUCIO_MESES", fr)) if causal in ("RETIRO_FORZOSO", "DESPIDO_INTEMPESTIVO") else 0.0
        ini_anio = date(fr.year, 1, 1)
        da, dm, ddd = anios_meses_dias(max(fi, ini_anio), fr)
        dias_ag = min(360, da * 360 + dm * 30 + ddd)
        aguinaldo = r2(prom * dias_ag / 360.0) if dias_ag >= 90 else 0.0
        vac = r2(prom / 30.0 * vacaciones_pendientes_dias)
        sueldo_pend = r2(e["haber_basico"] / 30.0 * min(fr.day, 30))
        total = r2(indem + desahucio + aguinaldo + vac + sueldo_pend)
        return {"empleado": e, "fecha_retiro": fr.isoformat(), "causal": causal, "antiguedad": f"{a} años, {m} meses, {dd} días", "promedio": prom,
                "indemnizacion": indem, "desahucio": desahucio, "aguinaldo_proporcional": aguinaldo, "vacaciones": vac, "sueldo_pendiente": sueldo_pend, "total": total}

    def dias_vacacion(self, fecha_ingreso, fecha) -> int:
        a = anios_meses_dias(to_date(fecha_ingreso), to_date(fecha))[0]
        for desde, hasta, d in self.n.json("VACACION_ESCALA", fecha):
            if desde <= a < hasta:
                return int(d)
        return 0
