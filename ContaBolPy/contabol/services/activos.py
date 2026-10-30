"""Activos fijos: registro, depreciación (D.S. 24051), actualización por UFV y baja."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import fin_de_mes, iso, r2, to_date


class ActivoService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def grupos(self) -> list[dict]:
        return self.db.query("SELECT * FROM activo_grupo ORDER BY nombre")

    def guardar_grupo(self, d: dict) -> int:
        self.ctx.requiere("AF.ACTIVOS")
        for k in ("cta_activo", "cta_dep", "cta_gasto"):
            if not self.ctx.cuenta_por_codigo(d.get(k, "")):
                raise ErrorNegocio(f"La cuenta indicada en '{k}' no existe.")
        if float(d.get("pct") or 0) <= 0 or float(d.get("vida_anios") or 0) <= 0:
            raise ErrorNegocio("La vida útil y el porcentaje deben ser mayores a cero.")
        vals = dict(nombre=d["nombre"].strip(), vida_anios=float(d["vida_anios"]), pct=float(d["pct"]),
                    cta_activo=d["cta_activo"], cta_dep=d["cta_dep"], cta_gasto=d["cta_gasto"])
        if d.get("id"):
            self.db.update("activo_grupo", d["id"], **vals)
            return d["id"]
        return self.db.insert("activo_grupo", **vals)

    def listar(self, texto: str = "", estado: str | None = None) -> list[dict]:
        sql = "SELECT a.*, g.nombre AS grupo FROM activo a JOIN activo_grupo g ON g.id=a.grupo_id WHERE 1=1"
        p: list = []
        if estado:
            sql += " AND a.estado=?"
            p.append(estado)
        if texto:
            sql += " AND (a.codigo LIKE ? OR a.nombre LIKE ?)"
            p += [f"%{texto}%"] * 2
        return self.db.query(sql + " ORDER BY a.codigo", p)

    def obtener(self, aid: int) -> dict | None:
        return self.db.one("SELECT a.*, g.nombre AS grupo FROM activo a JOIN activo_grupo g ON g.id=a.grupo_id WHERE a.id=?", (aid,))

    def guardar(self, d: dict) -> int:
        ctx = self.ctx
        ctx.requiere("AF.ACTIVOS")
        ctx.requiere_abierta()
        cod, nom = (d.get("codigo") or "").strip().upper(), (d.get("nombre") or "").strip()
        if not cod or not nom:
            raise ErrorNegocio("Código y nombre del activo son obligatorios.")
        if self.db.scalar("SELECT COUNT(*) FROM activo WHERE codigo=? AND id<>?", (cod, d.get("id") or 0)):
            raise ErrorNegocio(f"Ya existe el activo {cod}.")
        g = self.db.one("SELECT * FROM activo_grupo WHERE id=?", (d.get("grupo_id"),))
        if not g:
            raise ErrorNegocio("Seleccione el grupo de activo.")
        fa = to_date(d.get("fecha_alta"))
        if not fa:
            raise ErrorNegocio("Fecha de alta no válida.")
        valor = r2(d.get("valor_original") or 0)
        if valor <= 0:
            raise ErrorNegocio("El valor del activo debe ser mayor a cero.")
        if d.get("id"):
            a = self.obtener(d["id"])
            if self.db.scalar("SELECT COUNT(*) FROM activo_dep WHERE activo_id=?", (d["id"],), 0) and (valor != a["valor_original"] or g["id"] != a["grupo_id"]):
                raise ErrorNegocio("No se puede cambiar el valor o grupo de un activo ya depreciado.")
            self.db.update("activo", d["id"], codigo=cod, nombre=nom, ubicacion=d.get("ubicacion"), responsable=d.get("responsable"),
                           centro_id=d.get("centro_id") or None, serie=d.get("serie"))
            return d["id"]
        ufv = ctx.tc.ufv(fa)
        with self.db.tx():
            aid = self.db.insert("activo", codigo=cod, nombre=nom, grupo_id=g["id"], fecha_alta=fa.isoformat(), valor_original=valor,
                                 valor_actual=valor, dep_acum=r2(d.get("dep_acum") or 0), vida_meses=int(g["vida_anios"] * 12), pct=g["pct"],
                                 ufv_alta=ufv, ufv_ult=ufv, ubicacion=d.get("ubicacion"), responsable=d.get("responsable"),
                                 centro_id=d.get("centro_id") or None, serie=d.get("serie"))
            if d.get("contra_cuenta_id") and ctx.inicio <= fa <= ctx.fin:
                cid = ctx.vouchers.asiento(fa, f"Alta de activo fijo {cod} - {nom}",
                                           [(g["cta_activo"], valor, 0), (d["contra_cuenta_id"], 0, valor)], "ACTIVO", aid, tipo="T")
                self.db.execute("UPDATE activo SET comprobante_id=? WHERE id=?", (cid, aid))
        ctx.auditar("Activos fijos", "ALTA", f"{cod} Bs {valor:,.2f}")
        return aid

    # ------------------------------------------------------------- depreciación
    def depreciar(self, anio: int, mes: int, registrar: bool = False) -> list[dict]:
        """Calcula (y registra si corresponde) la depreciación mensual de todos los activos vigentes."""
        ctx = self.ctx
        if registrar:
            ctx.requiere("AF.DEPRECIAR")
            ctx.requiere_abierta()
        per = f"{anio}{mes:02d}"
        fin = fin_de_mes(anio, mes)
        filas = []
        for a in self.db.query("SELECT a.*, g.nombre AS grupo, g.cta_dep, g.cta_gasto FROM activo a JOIN activo_grupo g ON g.id=a.grupo_id "
                               "WHERE a.estado='A' AND a.fecha_alta<=? ORDER BY a.codigo", (fin.isoformat(),)):
            if self.db.scalar("SELECT COUNT(*) FROM activo_dep WHERE activo_id=? AND periodo=?", (a["id"], per), 0):
                continue
            tope = r2(a["valor_actual"] - a["dep_acum"])
            if tope <= 0:
                continue
            dep = min(r2(a["valor_actual"] * a["pct"] / 100.0 / 12.0), tope)
            filas.append({"activo_id": a["id"], "codigo": a["codigo"], "nombre": a["nombre"], "grupo": a["grupo"], "valor_actual": a["valor_actual"],
                          "dep_acum": a["dep_acum"], "depreciacion": dep, "cta_dep": a["cta_dep"], "cta_gasto": a["cta_gasto"],
                          "dep_acum_nueva": r2(a["dep_acum"] + dep)})
        if registrar and filas:
            with self.db.tx():
                por_grupo: dict[tuple, float] = {}
                for f in filas:
                    por_grupo[(f["cta_gasto"], f["cta_dep"])] = r2(por_grupo.get((f["cta_gasto"], f["cta_dep"]), 0) + f["depreciacion"])
                lineas = []
                for (cg, cd), v in por_grupo.items():
                    lineas += [(cg, v, 0), (cd, 0, v)]
                cid = ctx.vouchers.asiento(fin, f"Depreciación de activos fijos {mes:02d}/{anio}", lineas, "ACTIVO", None, tipo="T")
                for f in filas:
                    self.db.insert("activo_dep", activo_id=f["activo_id"], periodo=per, fecha=fin.isoformat(), depreciacion=f["depreciacion"], comprobante_id=cid)
                    self.db.execute("UPDATE activo SET dep_acum=? WHERE id=?", (f["dep_acum_nueva"], f["activo_id"]))
            ctx.auditar("Activos fijos", "DEPRECIAR", f"{mes:02d}/{anio}: {len(filas)} activos")
        return filas

    def actualizar_ufv(self, anio: int, mes: int, registrar: bool = False) -> list[dict]:
        """Actualización de valor y depreciación acumulada con la variación de la UFV (efectos tributarios)."""
        ctx = self.ctx
        fin = fin_de_mes(anio, mes)
        ufv_fin = ctx.tc.ufv(fin)
        if ufv_fin <= 0:
            raise ErrorNegocio(f"No hay UFV cargada al {fin:%d/%m/%Y}. Regístrela en Tipos de cambio y UFV.")
        filas = []
        for a in self.db.query("SELECT a.*, g.cta_activo, g.cta_dep, g.nombre AS grupo FROM activo a JOIN activo_grupo g ON g.id=a.grupo_id "
                               "WHERE a.estado='A' AND a.fecha_alta<=? ORDER BY a.codigo", (fin.isoformat(),)):
            ini = a["ufv_ult"] or a["ufv_alta"]
            if ini <= 0 or ufv_fin <= ini:
                continue
            fac = ufv_fin / ini - 1
            act, dact = r2(a["valor_actual"] * fac), r2(a["dep_acum"] * fac)
            if act == 0 and dact == 0:
                continue
            filas.append({"activo_id": a["id"], "codigo": a["codigo"], "nombre": a["nombre"], "grupo": a["grupo"], "ufv_ini": ini, "ufv_fin": ufv_fin,
                          "actualizacion": act, "dep_actualizacion": dact, "cta_activo": a["cta_activo"], "cta_dep": a["cta_dep"]})
        if registrar and filas:
            ctx.requiere("AF.DEPRECIAR")
            ctx.requiere_abierta()
            with self.db.tx():
                por: dict[str, float] = {}
                for f in filas:
                    por[f["cta_activo"]] = por.get(f["cta_activo"], 0) + f["actualizacion"]
                    por[f["cta_dep"]] = por.get(f["cta_dep"], 0) - f["dep_actualizacion"]
                lineas, neto = [], 0.0
                for cta, v in por.items():
                    v = r2(v)
                    if v > 0:
                        lineas.append((cta, v, 0))
                        neto += v
                    elif v < 0:
                        lineas.append((cta, 0, -v))
                        neto -= -v
                aj = ctx.cuenta_param("CTA_AJUSTE_AF")
                lineas.append((aj, 0, r2(neto)) if neto > 0 else (aj, r2(-neto), 0))
                cid = ctx.vouchers.asiento(fin, f"Actualización de activos fijos por UFV {mes:02d}/{anio}", lineas, "ACTIVO", None, tipo="T")
                for f in filas:
                    self.db.execute("UPDATE activo SET valor_actual=valor_actual+?, dep_acum=dep_acum+?, ufv_ult=? WHERE id=?",
                                    (f["actualizacion"], f["dep_actualizacion"], ufv_fin, f["activo_id"]))
        return filas

    def baja(self, aid: int, fecha, importe_venta: float = 0.0, cuenta_cobro_id: int | None = None, motivo: str = "") -> int:
        ctx = self.ctx
        ctx.requiere("AF.ACTIVOS")
        ctx.requiere_abierta()
        a = self.obtener(aid)
        if not a or a["estado"] != "A":
            raise ErrorNegocio("Activo inexistente o ya dado de baja.")
        f = ctx.requiere_fecha(fecha)
        g = self.db.one("SELECT * FROM activo_grupo WHERE id=?", (a["grupo_id"],))
        neto = r2(a["valor_actual"] - a["dep_acum"])
        venta = r2(importe_venta)
        lineas = [(g["cta_activo"], 0, a["valor_actual"])]
        if a["dep_acum"] > 0:
            lineas.append((g["cta_dep"], a["dep_acum"], 0))
        if venta > 0:
            lineas.append((cuenta_cobro_id or ctx.cuenta_param("CTA_CAJA"), venta, 0))
        dif = r2(neto - venta)
        if dif > 0:
            lineas.append((ctx.cuenta_param("CTA_BAJA_AF"), dif, 0))
        elif dif < 0:
            lineas.append((ctx.cuenta_param("CTA_REC_VEN"), 0, -dif))
        with self.db.tx():
            cid = ctx.vouchers.asiento(f, f"Baja de activo {a['codigo']} - {a['nombre']} {motivo}".strip(), lineas, "ACTIVO", aid, tipo="T")
            self.db.execute("UPDATE activo SET estado='B', fecha_baja=? WHERE id=?", (f.isoformat(), aid))
        ctx.auditar("Activos fijos", "BAJA", a["codigo"])
        return cid

    def cuadro(self, hasta=None) -> list[dict]:
        return self.db.query(
            "SELECT g.nombre AS grupo, a.codigo, a.nombre, a.fecha_alta, a.valor_original, a.valor_actual, a.dep_acum, "
            "ROUND(a.valor_actual-a.dep_acum,2) AS valor_neto, a.estado, a.pct FROM activo a JOIN activo_grupo g ON g.id=a.grupo_id "
            "WHERE a.fecha_alta<=? ORDER BY g.nombre, a.codigo", (iso(hasta) or "9999-12-31",))
