"""Comprobantes contables (partida doble, bimonetarios)."""
from __future__ import annotations

from datetime import datetime

from ..sistema import ErrorNegocio
from ..util import iso, r2, to_date


class ComprobanteService:
    TOL = 0.005

    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    # ---------------------------------------------------------------- numeración
    def _numero(self, tipo: str, mes: int) -> int:
        if self.ctx.gestion["correlativo_mensual"]:
            v = self.db.scalar("SELECT MAX(numero) FROM comprobante WHERE tipo=? AND mes=?", (tipo, mes), 0)
        else:
            v = self.db.scalar("SELECT MAX(numero) FROM comprobante WHERE tipo=?", (tipo,), 0)
        return int(v) + 1

    # ---------------------------------------------------------------- registro
    def _preparar(self, d: dict) -> tuple[dict, list[dict]]:
        ctx = self.ctx
        f = ctx.requiere_fecha(d.get("fecha"))
        glosa = (d.get("glosa") or "").strip()
        if not glosa:
            raise ErrorNegocio("La glosa del comprobante es obligatoria.")
        moneda = (d.get("moneda") or "BS").upper()
        tc = float(d.get("tc") or 0) or ctx.tc.dolar(f)
        if tc <= 0:
            raise ErrorNegocio("Tipo de cambio no válido.")
        lineas_in = [l for l in d.get("lineas", []) if l.get("cuenta_id")]
        if len(lineas_in) < 2:
            raise ErrorNegocio("El comprobante necesita al menos dos líneas con cuenta.")
        lineas: list[dict] = []
        for i, l in enumerate(lineas_in, 1):
            debe, haber = float(l.get("debe") or 0), float(l.get("haber") or 0)
            if debe < 0 or haber < 0:
                raise ErrorNegocio(f"Línea {i}: no se permiten importes negativos.")
            if debe > 0 and haber > 0:
                raise ErrorNegocio(f"Línea {i}: una línea no puede tener importe en el debe y en el haber.")
            if debe == 0 and haber == 0:
                continue
            cta = ctx.cuentas.obtener(int(l["cuenta_id"]))
            if not cta or not cta["activa"]:
                raise ErrorNegocio(f"Línea {i}: la cuenta no existe.")
            if not cta["es_movimiento"]:
                raise ErrorNegocio(f"Línea {i}: la cuenta {cta['codigo']} no es de movimiento.")
            if moneda == "USD":
                dbs, hbs, dus, hus = r2(debe * tc), r2(haber * tc), r2(debe), r2(haber)
            else:
                dbs, hbs, dus, hus = r2(debe), r2(haber), r2(debe / tc), r2(haber / tc)
            if l.get("debe_usd_fijo") is not None:
                dus = r2(l["debe_usd_fijo"])
            if l.get("haber_usd_fijo") is not None:
                hus = r2(l["haber_usd_fijo"])
            lineas.append({"cuenta_id": cta["id"], "glosa": (l.get("glosa") or "").strip() or None, "debe_bs": dbs, "haber_bs": hbs,
                           "debe_usd": dus, "haber_usd": hus, "centro_id": l.get("centro_id") or None,
                           "tercero_id": l.get("tercero_id") or None, "doc_ref": l.get("doc_ref") or None})
        if len(lineas) < 2:
            raise ErrorNegocio("El comprobante necesita al menos dos líneas con importe.")
        td = r2(sum(l["debe_bs"] for l in lineas))
        th = r2(sum(l["haber_bs"] for l in lineas))
        dif = r2(td - th)
        if abs(dif) > self.TOL:
            if moneda == "USD" and abs(dif) <= 0.05:
                # ajuste por redondeo de la conversión: se absorbe en la última línea del lado menor
                lado = "haber_bs" if dif > 0 else "debe_bs"
                for l in reversed(lineas):
                    if l[lado] > 0:
                        l[lado] = r2(l[lado] + dif)
                        break
                td = r2(sum(l["debe_bs"] for l in lineas))
                th = r2(sum(l["haber_bs"] for l in lineas))
            else:
                raise ErrorNegocio(f"El comprobante no cuadra: Debe {td:,.2f} / Haber {th:,.2f} (diferencia {abs(dif):,.2f}).")
        cab = {"tipo": d.get("tipo") or "T", "fecha": f.isoformat(), "mes": f.month, "glosa": glosa, "moneda": moneda, "tc": tc,
               "debe_bs": td, "haber_bs": th, "a_nombre": d.get("a_nombre"), "nro_doc": d.get("nro_doc"),
               "origen": d.get("origen") or "MANUAL", "ref_id": d.get("ref_id")}
        if not self.db.scalar("SELECT COUNT(*) FROM tipo_comprobante WHERE codigo=?", (cab["tipo"],), 0):
            raise ErrorNegocio("Tipo de comprobante no válido.")
        return cab, lineas

    def _validar_presupuesto(self, lineas: list[dict], fecha) -> None:
        if self.ctx.param("CONTROL_PRESUPUESTO") != "1":
            return
        self.ctx.presupuesto.verificar(lineas, to_date(fecha))

    def crear(self, d: dict, *, interno: bool = False) -> int:
        ctx = self.ctx
        if not interno:
            ctx.requiere("CONT.COMPROBANTES")
        ctx.requiere_abierta()
        cab, lineas = self._preparar(d)
        self._validar_presupuesto(lineas, cab["fecha"])
        with self.db.tx():
            cab["numero"] = self._numero(cab["tipo"], cab["mes"])
            cid = self.db.insert("comprobante", **cab, estado="V", creado_por=ctx.usuario["id"],
                                 creado_en=datetime.now().isoformat(timespec="seconds"))
            for n, l in enumerate(lineas, 1):
                self.db.insert("comp_det", comprobante_id=cid, linea=n, **l)
        ctx.auditar("Contabilidad", "CREAR_COMPROBANTE", f"{cab['tipo']}-{cab['numero']} {cab['fecha']} Bs {cab['debe_bs']:,.2f}")
        return cid

    def modificar(self, cid: int, d: dict) -> None:
        ctx = self.ctx
        ctx.requiere("CONT.COMPROBANTES")
        ctx.requiere_abierta()
        c = self.obtener(cid)
        if not c:
            raise ErrorNegocio("Comprobante inexistente.")
        if c["estado"] != "V":
            raise ErrorNegocio("No se puede modificar un comprobante anulado.")
        if c["origen"] != "MANUAL":
            raise ErrorNegocio(f"Este comprobante fue generado por el módulo {c['origen']} y debe corregirse desde allí (o anularse).")
        cab, lineas = self._preparar(d)
        with self.db.tx():
            cambia_num = cab["tipo"] != c["tipo"] or cab["mes"] != c["mes"]
            if cambia_num:
                cab["numero"] = self._numero(cab["tipo"], cab["mes"])
            else:
                cab["numero"] = c["numero"]
            self.db.update("comprobante", cid, **cab, modificado_por=ctx.usuario["id"], modificado_en=datetime.now().isoformat(timespec="seconds"))
            self.db.execute("DELETE FROM comp_det WHERE comprobante_id=?", (cid,))
            for n, l in enumerate(lineas, 1):
                self.db.insert("comp_det", comprobante_id=cid, linea=n, **l)
        ctx.auditar("Contabilidad", "MODIFICAR_COMPROBANTE", f"{cab['tipo']}-{cab['numero']}")

    def anular(self, cid: int, *, interno: bool = False) -> None:
        ctx = self.ctx
        if not interno:
            ctx.requiere("CONT.ANULAR")
        ctx.requiere_abierta()
        c = self.obtener(cid)
        if not c:
            raise ErrorNegocio("Comprobante inexistente.")
        if c["estado"] == "A":
            raise ErrorNegocio("El comprobante ya está anulado.")
        if c["origen"] not in ("MANUAL", "AJUSTE", "CIERRE") and not interno:
            raise ErrorNegocio(f"Este comprobante pertenece al módulo {c['origen']}; anule el documento de origen.")
        if self.db.scalar("SELECT COUNT(*) FROM comp_det WHERE comprobante_id=? AND conciliado IS NOT NULL", (cid,), 0):
            raise ErrorNegocio("El comprobante tiene líneas conciliadas con el banco; desconcílielas primero.")
        self.db.execute("UPDATE comprobante SET estado='A', anulado_por=?, anulado_en=? WHERE id=?",
                        (ctx.usuario["id"], datetime.now().isoformat(timespec="seconds"), cid))
        ctx.auditar("Contabilidad", "ANULAR_COMPROBANTE", f"{c['tipo']}-{c['numero']} {c['fecha']}")

    # ------------------------------------------------------------------ consulta
    def obtener(self, cid: int) -> dict | None:
        c = self.db.one("SELECT * FROM comprobante WHERE id=?", (cid,))
        if c:
            c["lineas"] = self.lineas(cid)
        return c

    def lineas(self, cid: int) -> list[dict]:
        return self.db.query(
            "SELECT d.*, c.codigo AS cuenta_codigo, c.nombre AS cuenta_nombre FROM comp_det d JOIN cuenta c ON c.id=d.cuenta_id "
            "WHERE d.comprobante_id=? ORDER BY d.linea", (cid,))

    def listar(self, desde=None, hasta=None, tipo: str | None = None, texto: str = "", estado: str | None = None) -> list[dict]:
        sql = ("SELECT c.*, t.nombre AS tipo_nombre FROM comprobante c JOIN tipo_comprobante t ON t.codigo=c.tipo WHERE 1=1")
        p: list = []
        if desde:
            sql += " AND c.fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND c.fecha<=?"
            p.append(iso(hasta))
        if tipo:
            sql += " AND c.tipo=?"
            p.append(tipo)
        if estado:
            sql += " AND c.estado=?"
            p.append(estado)
        if texto:
            sql += " AND (c.glosa LIKE ? OR c.a_nombre LIKE ? OR c.nro_doc LIKE ?)"
            p += [f"%{texto}%"] * 3
        return self.db.query(sql + " ORDER BY c.fecha, c.tipo, c.numero", p)

    def tipos(self) -> list[dict]:
        return self.db.query("SELECT * FROM tipo_comprobante ORDER BY codigo")

    def codigo(self, c: dict) -> str:
        return f"{c['tipo']}-{c['mes']:02d}/{c['numero']:04d}" if self.ctx.gestion["correlativo_mensual"] else f"{c['tipo']}-{c['numero']:05d}"

    # -------------------------------------------------- utilidades para módulos
    def asiento(self, fecha, glosa: str, lineas_bs: list[tuple], origen: str, ref_id: int | None = None, tipo: str = "T",
                a_nombre: str | None = None, nro_doc: str | None = None) -> int:
        """Genera un comprobante desde otro módulo. lineas_bs: (cuenta_id|codigo, debe_bs, haber_bs[, glosa, tercero_id, centro_id])."""
        ls = []
        for t in lineas_bs:
            cta = t[0]
            if isinstance(cta, str):
                c = self.ctx.cuentas.por_codigo(cta)
                if not c:
                    raise ErrorNegocio(f"La cuenta {cta} no existe en el plan.")
                cta = c["id"]
            ls.append({"cuenta_id": cta, "debe": t[1], "haber": t[2], "glosa": t[3] if len(t) > 3 else None,
                       "tercero_id": t[4] if len(t) > 4 else None, "centro_id": t[5] if len(t) > 5 else None})
        return self.crear({"tipo": tipo, "fecha": fecha, "glosa": glosa, "lineas": ls, "origen": origen, "ref_id": ref_id,
                           "a_nombre": a_nombre, "nro_doc": nro_doc}, interno=True)
