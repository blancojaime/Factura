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
               "ufv": float(d.get("ufv") or 0), "banco_id": d.get("banco_id") or None, "nro_cheque": (d.get("nro_cheque") or "").strip() or None,
               "glosa_por_linea": 1 if d.get("glosa_por_linea") else 0,
               "origen": d.get("origen") or "MANUAL", "ref_id": d.get("ref_id")}
        if not self.db.scalar("SELECT COUNT(*) FROM tipo_comprobante WHERE codigo=?", (cab["tipo"],), 0):
            raise ErrorNegocio("Tipo de comprobante no válido.")
        return cab, lineas

    def _validar_presupuesto(self, lineas: list[dict], fecha) -> None:
        if self.ctx.param("CONTROL_PRESUPUESTO") != "1":
            return
        self.ctx.presupuesto.verificar(lineas, to_date(fecha))

    def _guardar_ufv(self, cab: dict) -> None:
        """Si el usuario indicó T.C./UFV en el comprobante, se registran para esa fecha (sin pisar con ceros)."""
        if cab["moneda"] == "USD" or cab["tc"] > 0:
            fila = self.db.one("SELECT dolar, ufv FROM tipo_cambio WHERE fecha=?", (cab["fecha"],))
            ufv = cab["ufv"] if cab["ufv"] > 0 else (fila["ufv"] if fila else 0.0)
            if not fila or abs(fila["dolar"] - cab["tc"]) > 1e-9 or abs(fila["ufv"] - ufv) > 1e-9:
                if cab["ufv"] > 0 or not fila:
                    self.db.execute("INSERT INTO tipo_cambio (fecha, dolar, ufv) VALUES (?,?,?) ON CONFLICT(fecha) DO UPDATE SET dolar=excluded.dolar, ufv=excluded.ufv",
                                    (cab["fecha"], cab["tc"], ufv))

    def siguiente_numero(self, tipo: str, fecha) -> tuple[int, str]:
        """Número que recibirá el próximo comprobante del tipo y mes (la numeración es automática)."""
        f = to_date(fecha)
        n = self._numero(tipo, f.month)
        if self.ctx.gestion["correlativo_mensual"]:
            return n, f"{tipo}-{f.month:02d}/{n:04d}"
        return n, f"{tipo}-{n:05d}"

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
            if not interno:
                self._guardar_ufv(cab)
            if d.get("factura"):
                self._vincular_factura(cid, cab, d["factura"])
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
            self._guardar_ufv(cab)
            if d.get("factura"):
                for f in self.db.query("SELECT id FROM factura WHERE comprobante_id=? AND origen='COMPROBANTE'", (cid,)):
                    self.db.delete("factura", f["id"])
                self._vincular_factura(cid, cab, d["factura"])
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
        if c["origen"] not in ("MANUAL", "AJUSTE", "CIERRE", "REVERSION", "COMPROBANTE") and not interno:
            raise ErrorNegocio(f"Este comprobante pertenece al módulo {c['origen']}; anule el documento de origen.")
        if self.db.scalar("SELECT COUNT(*) FROM comp_det WHERE comprobante_id=? AND conciliado IS NOT NULL", (cid,), 0):
            raise ErrorNegocio("El comprobante tiene líneas conciliadas con el banco; desconcílielas primero.")
        self.db.execute("UPDATE comprobante SET estado='A', anulado_por=?, anulado_en=? WHERE id=?",
                        (ctx.usuario["id"], datetime.now().isoformat(timespec="seconds"), cid))
        self.db.execute("UPDATE factura SET estado='A', importe_total=0, no_sujeto=0, exento=0, tasa_cero=0, subtotal=0, descuentos=0, base_iva=0, iva=0 "
                        "WHERE comprobante_id=? AND origen='COMPROBANTE'", (cid,))
        ctx.auditar("Contabilidad", "ANULAR_COMPROBANTE", f"{c['tipo']}-{c['numero']} {c['fecha']}")

    def eliminar(self, cid: int) -> None:
        """Borra físicamente un comprobante manual. Solo se permite si es el ÚLTIMO de su tipo y mes (para no dejar saltos en la numeración),
        no está conciliado con el banco ni tiene documentos vinculados; en los demás casos use Anular o Revertir."""
        ctx = self.ctx
        ctx.requiere("CONT.ANULAR")
        ctx.requiere_abierta()
        c = self.obtener(cid)
        if not c:
            raise ErrorNegocio("Comprobante inexistente.")
        if c["origen"] not in ("MANUAL", "COMPROBANTE"):
            raise ErrorNegocio(f"Este comprobante pertenece al módulo {c['origen']}; anule el documento de origen.")
        ultimo = self.db.scalar("SELECT MAX(numero) FROM comprobante WHERE tipo=? AND mes=?", (c["tipo"], c["mes"]))
        if c["numero"] != ultimo:
            raise ErrorNegocio("Solo puede eliminar el último comprobante de su tipo y mes (para conservar la numeración correlativa). Use «Anular» o «Revertir».")
        if self.db.scalar("SELECT COUNT(*) FROM comp_det WHERE comprobante_id=? AND conciliado IS NOT NULL", (cid,), 0):
            raise ErrorNegocio("El comprobante tiene líneas conciliadas con el banco; desconcílielas primero.")
        if self.db.scalar("SELECT COUNT(*) FROM comprobante WHERE origen='REVERSION' AND ref_id=?", (cid,), 0):
            raise ErrorNegocio("El comprobante ya fue revertido; no se puede eliminar.")
        with self.db.tx():
            self.db.execute("DELETE FROM factura WHERE comprobante_id=? AND origen='COMPROBANTE'", (cid,))
            self.db.execute("DELETE FROM comp_det WHERE comprobante_id=?", (cid,))
            self.db.execute("DELETE FROM comprobante WHERE id=?", (cid,))
        ctx.auditar("Contabilidad", "ELIMINAR_COMPROBANTE", f"{c['tipo']}-{c['numero']} {c['fecha']} Bs {c['debe_bs']:,.2f}")

    def revertir(self, cid: int, fecha=None, glosa: str = "") -> int:
        """Genera el contra-asiento (debe y haber invertidos) de un comprobante vigente; ambos quedan en los libros. Devuelve el id del nuevo comprobante."""
        ctx = self.ctx
        ctx.requiere("CONT.COMPROBANTES")
        ctx.requiere_abierta()
        c = self.obtener(cid)
        if not c:
            raise ErrorNegocio("Comprobante inexistente.")
        if c["estado"] != "V":
            raise ErrorNegocio("Solo se puede revertir un comprobante vigente.")
        if c["origen"] == "REVERSION":
            raise ErrorNegocio("No se puede revertir un comprobante de reversión; registre uno nuevo.")
        if self.db.scalar("SELECT COUNT(*) FROM comprobante WHERE origen='REVERSION' AND ref_id=? AND estado='V'", (cid,), 0):
            raise ErrorNegocio("Este comprobante ya fue revertido.")
        f = to_date(fecha) or ctx.requiere_fecha(c["fecha"])
        ctx.requiere_fecha(f)
        cod = self.codigo(c)
        lineas = [(l["cuenta_id"], l["haber_bs"], l["debe_bs"], l.get("glosa"), l.get("tercero_id"), l.get("centro_id")) for l in c["lineas"]]
        nid = self.asiento(f, glosa or f"Reversión del comprobante {cod}: {c['glosa']}"[:200], lineas, "REVERSION", cid, "T", c.get("a_nombre"), c.get("nro_doc"))
        ctx.auditar("Contabilidad", "REVERTIR_COMPROBANTE", f"{cod} -> comprobante {nid}")
        return nid

    def reversion_de(self, cid: int) -> dict | None:
        return self.db.one("SELECT * FROM comprobante WHERE origen='REVERSION' AND ref_id=? AND estado='V' ORDER BY id LIMIT 1", (cid,))

    def _vincular_factura(self, cid: int, cab: dict, fac: dict) -> int:
        """Registra en el libro de compras (egresos) o ventas (ingresos) la factura del comprobante, sin generar otro asiento."""
        libro = "C" if cab["tipo"] == "E" else "V"
        datos = dict(fac)
        datos.update({"libro": libro, "fecha": cab["fecha"], "comprobante_id": cid, "origen": "COMPROBANTE", "origen_id": cid, "generar_asiento": False})
        return self.ctx.iva.registrar(datos, interno=True)

    def factura_vinculada(self, cid: int) -> dict | None:
        return self.db.one("SELECT * FROM factura WHERE comprobante_id=? AND origen='COMPROBANTE' ORDER BY id LIMIT 1", (cid,))

    def ajustar_asiento_iva(self, tipo: str, lineas: list[dict], importe_total: float, fecha) -> list[dict]:
        """Agrega al asiento la línea de crédito fiscal (egreso) o débito fiscal (ingreso) y descuenta ese importe del gasto/ingreso principal.

        Si el asiento ya contiene una línea de IVA no hace cambios. Devuelve la nueva lista de líneas (debe/haber en la moneda del comprobante)."""
        ctx = self.ctx
        cta_cf, cta_df = ctx.cuenta_param("CTA_CF_IVA"), ctx.cuenta_param("CTA_DF_IVA")
        if any(l.get("cuenta_id") in (cta_cf, cta_df) for l in lineas):
            return lineas
        iva = r2(importe_total * ctx.iva.iva_pct(fecha) / 100)
        if iva <= 0:
            return lineas
        nuevas = [dict(l) for l in lineas]
        lado = "debe" if tipo == "E" else "haber"
        candidatas = [l for l in nuevas if (l.get(lado) or 0) >= iva]
        if not candidatas:
            raise ErrorNegocio("Ninguna línea tiene importe suficiente para separar el IVA; ajuste el asiento manualmente.")
        mayor = max(candidatas, key=lambda x: x[lado])
        mayor[lado] = r2(mayor[lado] - iva)
        nuevas.append({"cuenta_id": cta_cf if tipo == "E" else cta_df, "glosa": "Crédito fiscal IVA" if tipo == "E" else "Débito fiscal IVA",
                       "debe": iva if tipo == "E" else 0, "haber": 0 if tipo == "E" else iva})
        return nuevas

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
