"""Ventas, compras, cobros y pagos con contabilización automática."""
from __future__ import annotations

from datetime import timedelta

from ..sistema import ErrorNegocio
from ..util import iso, r2, to_date


def _lineas_validas(d: dict) -> list[dict]:
    ls = []
    for l in d.get("items", []):
        if not l.get("item_id"):
            continue
        cant, precio, desc = float(l.get("cantidad") or 0), float(l.get("precio") or 0), float(l.get("descuento") or 0)
        if cant <= 0:
            raise ErrorNegocio("La cantidad de cada línea debe ser mayor a cero.")
        if precio < 0 or desc < 0:
            raise ErrorNegocio("Precio y descuento no pueden ser negativos.")
        bruto = r2(cant * precio)
        if desc > bruto:
            raise ErrorNegocio("El descuento de una línea supera su importe.")
        ls.append({**l, "cantidad": cant, "precio": precio, "descuento": r2(desc), "bruto": bruto, "total": r2(bruto - desc)})
    if not ls:
        raise ErrorNegocio("Agregue al menos un ítem.")
    return ls


class _DocBase:
    tabla = ""
    det = ""

    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def _numero(self) -> int:
        return int(self.db.scalar(f"SELECT MAX(numero) FROM {self.tabla}", (), 0)) + 1

    def obtener(self, did: int) -> dict | None:
        d = self.db.one(f"SELECT * FROM {self.tabla} WHERE id=?", (did,))
        if d:
            fk = f"{self.tabla}_id"
            d["items"] = self.db.query(f"SELECT x.*, i.codigo, i.nombre FROM {self.det} x JOIN item i ON i.id=x.item_id WHERE x.{fk}=? ORDER BY x.id", (did,))
            d["tercero"] = self.ctx.terceros.obtener(d["tercero_id"])
        return d

    def listar(self, desde=None, hasta=None, tercero_id: int | None = None, estado: str | None = None, pendientes: bool = False) -> list[dict]:
        sql = f"SELECT d.*, t.nombre AS tercero, t.nit FROM {self.tabla} d JOIN tercero t ON t.id=d.tercero_id WHERE 1=1"
        p: list = []
        if desde:
            sql += " AND d.fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND d.fecha<=?"
            p.append(iso(hasta))
        if tercero_id:
            sql += " AND d.tercero_id=?"
            p.append(tercero_id)
        if estado:
            sql += " AND d.estado=?"
            p.append(estado)
        if pendientes:
            sql += " AND d.estado='V' AND d.saldo>0.004"
        return self.db.query(sql + " ORDER BY d.fecha, d.numero", p)

    def _cuenta_contado(self, d: dict) -> int:
        return d.get("cuenta_pago_id") or self.ctx.cuenta_param("CTA_CAJA")

    def _vencimiento(self, d: dict, tercero: dict, f) -> str | None:
        if d.get("tipo_pago") != "CRE":
            return None
        v = to_date(d.get("vencimiento"))
        return (v or (f + timedelta(days=int(tercero.get("dias_credito") or 0)))).isoformat()


class VentaService(_DocBase):
    tabla, det = "venta", "venta_det"

    def registrar(self, d: dict) -> dict:
        ctx = self.ctx
        ctx.requiere("COM.VENTAS")
        ctx.requiere_abierta()
        f = ctx.requiere_fecha(d.get("fecha"))
        cli = ctx.terceros.obtener(d.get("tercero_id") or 0)
        if not cli:
            raise ErrorNegocio("Seleccione el cliente.")
        tipo_pago = d.get("tipo_pago") or "CON"
        ls = _lineas_validas(d)
        almacen = d.get("almacen_id") or ctx.db.scalar("SELECT id FROM almacen ORDER BY id LIMIT 1")
        bruto = r2(sum(l["bruto"] for l in ls))
        desc_lineas = r2(sum(l["descuento"] for l in ls))
        desc_global, recargo = r2(d.get("descuento") or 0), r2(d.get("recargo") or 0)
        subtotal = r2(bruto - desc_lineas)
        total = r2(subtotal - desc_global + recargo)
        if total < 0:
            raise ErrorNegocio("El total no puede ser negativo.")
        a_cuenta = r2(d.get("a_cuenta") or 0) if tipo_pago == "CRE" else 0.0
        if a_cuenta > total:
            raise ErrorNegocio("El pago a cuenta supera el total.")
        saldo = r2(total - a_cuenta) if tipo_pago == "CRE" else 0.0
        if tipo_pago == "CRE":
            limite = float(cli["limite_credito"] or 0)
            if limite > 0 and ctx.terceros.saldo(cli["id"], "C") + saldo > limite + 0.004:
                raise ErrorNegocio(f"Se excede el límite de crédito del cliente (límite Bs {limite:,.2f}; saldo actual Bs {ctx.terceros.saldo(cli['id'], 'C'):,.2f}).")
        con_factura = bool(d.get("con_factura", True))
        if con_factura and not (d.get("nro_factura") or "").strip():
            raise ErrorNegocio("Indique el número de factura (o desmarque 'con factura').")
        iva = r2(total * ctx.iva.iva_pct(f) / 100) if con_factura else 0.0
        with self.db.tx():
            vid = self.db.insert("venta", numero=self._numero(), fecha=f.isoformat(), tercero_id=cli["id"], tipo_pago=tipo_pago, almacen_id=almacen,
                                 vendedor_id=d.get("vendedor_id") or None, con_factura=1 if con_factura else 0, nro_factura=d.get("nro_factura"),
                                 nro_autorizacion=d.get("nro_autorizacion"), subtotal=subtotal, descuento=desc_global, recargo=recargo, total=total,
                                 a_cuenta=a_cuenta, saldo=saldo, vencimiento=self._vencimiento(d, cli, f), glosa=d.get("glosa"))
            # inventario
            mov_items, costo_total = [], 0.0
            for l in ls:
                it = ctx.inventario.item(l["item_id"])
                if not it:
                    raise ErrorNegocio("Ítem inexistente.")
                l["es_serv"] = bool(it["es_servicio"])
                if not it["es_servicio"]:
                    mov_items.append({"item_id": it["id"], "cantidad": l["cantidad"]})
            mid = None
            costos: dict[int, float] = {}
            if mov_items:
                res = ctx.inventario.registrar({"tipo": "SAL", "fecha": f, "almacen_id": almacen, "glosa": f"Venta Nº {self.db.scalar('SELECT numero FROM venta WHERE id=?', (vid,))}",
                                                "items": mov_items, "doc_tipo": "V", "doc_id": vid}, interno=True)
                mid = res["id"]
                for r in self.db.query("SELECT item_id, costo_unit, costo_total FROM mov_inv_det WHERE mov_id=?", (mid,)):
                    costos[r["item_id"]] = r["costo_unit"]
                    costo_total += r["costo_total"]
            costo_total = r2(costo_total)
            for l in ls:
                cu = costos.get(l["item_id"], 0.0)
                self.db.insert("venta_det", venta_id=vid, item_id=l["item_id"], cantidad=l["cantidad"], precio=l["precio"], descuento=l["descuento"],
                               total=l["total"], costo_unit=cu, costo_total=r2(cu * l["cantidad"]) if not l["es_serv"] else 0.0)
            # asiento
            glosa = f"Venta Nº {self.db.scalar('SELECT numero FROM venta WHERE id=?', (vid,))} a {cli['nombre']}" + (f" - Fact. {d['nro_factura']}" if con_factura else "")
            lin: list[tuple] = []
            caja = self._cuenta_contado(d)
            if tipo_pago == "CON":
                lin.append((caja, total, 0))
            else:
                if a_cuenta > 0:
                    lin.append((caja, a_cuenta, 0))
                lin.append((ctx.cuenta_param("CTA_CXC"), saldo, 0, None, cli["id"]))
            desc_total = r2(desc_lineas + desc_global)
            if desc_total > 0:
                lin.append((ctx.cuenta_param("CTA_DESC_VEN"), desc_total, 0))
            if iva > 0:
                lin.append((ctx.cuenta_param("CTA_DF_IVA"), 0, iva))
            if recargo > 0:
                lin.append((ctx.cuenta_param("CTA_REC_VEN"), 0, recargo))
            lin.append((ctx.cuenta_param("CTA_VENTAS"), 0, r2(bruto - iva)))
            if con_factura or ctx.param("IT_SIN_FACTURA") == "1":
                it = ctx.iva.calcular_it(total, f)
                if it > 0:
                    lin += [(ctx.cuenta_param("CTA_IT_GASTO"), it, 0), (ctx.cuenta_param("CTA_IT_PAGAR"), 0, it)]
            if costo_total > 0:
                lin += [(ctx.cuenta_param("CTA_COSTO_VTA"), costo_total, 0), (ctx.cuenta_param("CTA_INVENT"), 0, costo_total)]
            cid = ctx.vouchers.asiento(f, glosa, lin, "VENTA", vid, tipo="I", a_nombre=cli["nombre"], nro_doc=d.get("nro_factura"))
            fid = None
            if con_factura:
                fid = ctx.iva.desde_documento("V", f, cli, d["nro_factura"], d.get("nro_autorizacion") or "", total, 0.0, cid, "VENTA", vid)
            self.db.execute("UPDATE venta SET comprobante_id=?, factura_id=?, mov_id=?, costo_total=? WHERE id=?", (cid, fid, mid, costo_total, vid))
        ctx.auditar("Ventas", "REGISTRAR_VENTA", f"Venta {vid} Bs {total:,.2f}")
        return {"id": vid, "total": total, "iva": iva, "comprobante_id": cid, "costo": costo_total}

    def anular(self, vid: int) -> None:
        ctx = self.ctx
        ctx.requiere("COM.VENTAS")
        ctx.requiere_abierta()
        v = self.db.one("SELECT * FROM venta WHERE id=?", (vid,))
        if not v or v["estado"] != "V":
            raise ErrorNegocio("Venta inexistente o ya anulada.")
        if self.db.scalar("SELECT COUNT(*) FROM cobro_doc cd JOIN cobro_pago c ON c.id=cd.cobro_id WHERE cd.doc_tipo='V' AND cd.doc_id=? AND c.estado='V'", (vid,), 0):
            raise ErrorNegocio("La venta tiene cobros aplicados: anule primero los cobros.")
        with self.db.tx():
            if v["mov_id"]:
                ctx.inventario.reversar(v["mov_id"])
            if v["comprobante_id"]:
                ctx.vouchers.anular(v["comprobante_id"], interno=True)
            if v["factura_id"]:
                self.db.execute("UPDATE factura SET estado='A', importe_total=0, no_sujeto=0, exento=0, tasa_cero=0, subtotal=0, descuentos=0, base_iva=0, iva=0 WHERE id=?",
                                (v["factura_id"],))
            self.db.execute("UPDATE venta SET estado='A', saldo=0 WHERE id=?", (vid,))
        ctx.auditar("Ventas", "ANULAR_VENTA", f"Venta {vid}")


class CompraService(_DocBase):
    tabla, det = "compra", "compra_det"

    def registrar(self, d: dict) -> dict:
        ctx = self.ctx
        ctx.requiere("COM.COMPRAS")
        ctx.requiere_abierta()
        f = ctx.requiere_fecha(d.get("fecha"))
        prov = ctx.terceros.obtener(d.get("tercero_id") or 0)
        if not prov:
            raise ErrorNegocio("Seleccione el proveedor.")
        tipo_pago = d.get("tipo_pago") or "CON"
        ls = _lineas_validas(d)
        almacen = d.get("almacen_id") or ctx.db.scalar("SELECT id FROM almacen ORDER BY id LIMIT 1")
        bruto = r2(sum(l["bruto"] for l in ls))
        subtotal = r2(bruto - sum(l["descuento"] for l in ls))
        desc_global, recargo = r2(d.get("descuento") or 0), r2(d.get("recargo") or 0)
        total = r2(subtotal - desc_global + recargo)
        a_cuenta = r2(d.get("a_cuenta") or 0) if tipo_pago == "CRE" else 0.0
        if a_cuenta > total:
            raise ErrorNegocio("El pago a cuenta supera el total.")
        saldo = r2(total - a_cuenta) if tipo_pago == "CRE" else 0.0
        con_factura = bool(d.get("con_factura", True))
        if con_factura and not (d.get("nro_factura") or "").strip():
            raise ErrorNegocio("Indique el número de factura (o desmarque 'con factura').")
        iva = r2(total * ctx.iva.iva_pct(f) / 100) if con_factura else 0.0
        neto = r2(total - iva)
        factor = neto / subtotal if subtotal else 0.0
        with self.db.tx():
            cid_num = self._numero()
            cid = self.db.insert("compra", numero=cid_num, fecha=f.isoformat(), tercero_id=prov["id"], tipo_pago=tipo_pago, almacen_id=almacen,
                                 con_factura=1 if con_factura else 0, nro_factura=d.get("nro_factura"), nro_autorizacion=d.get("nro_autorizacion"),
                                 subtotal=subtotal, descuento=desc_global, recargo=recargo, total=total, a_cuenta=a_cuenta, saldo=saldo,
                                 vencimiento=self._vencimiento(d, prov, f), glosa=d.get("glosa"))
            mov_items, gasto_directo = [], 0.0
            for l in ls:
                it = ctx.inventario.item(l["item_id"])
                costo_linea = r2(l["total"] * factor)
                self.db.insert("compra_det", compra_id=cid, item_id=l["item_id"], cantidad=l["cantidad"], precio=l["precio"], descuento=l["descuento"],
                               total=l["total"], lote=l.get("lote"), vencimiento=iso(l.get("vencimiento")))
                if it["es_servicio"]:
                    gasto_directo += costo_linea
                else:
                    mov_items.append({"item_id": it["id"], "cantidad": l["cantidad"], "costo_unit": costo_linea / l["cantidad"],
                                      "lote": l.get("lote"), "vencimiento": l.get("vencimiento")})
            mid, inv_total = None, 0.0
            if mov_items:
                res = ctx.inventario.registrar({"tipo": "ING", "fecha": f, "almacen_id": almacen, "glosa": f"Compra Nº {cid_num}", "items": mov_items,
                                                "doc_tipo": "C", "doc_id": cid}, interno=True)
                mid, inv_total = res["id"], res["total"]
            glosa = f"Compra Nº {cid_num} a {prov['nombre']}" + (f" - Fact. {d['nro_factura']}" if con_factura else "")
            lin: list[tuple] = []
            caja = self._cuenta_contado(d)
            gasto_directo = r2(gasto_directo)
            # el neto total debe repartirse entre inventario y gasto: ajustamos diferencias de redondeo al inventario
            if inv_total > 0:
                lin.append((ctx.cuenta_param("CTA_INVENT"), r2(neto - gasto_directo) if gasto_directo or True else inv_total, 0))
            if gasto_directo > 0:
                cuenta_g = d.get("cuenta_gasto_id") or ctx.cuenta_param("CTA_REC_COMP")
                lin.append((cuenta_g, gasto_directo, 0))
            if inv_total == 0 and gasto_directo == 0:
                raise ErrorNegocio("La compra no tiene importe.")
            if iva > 0:
                lin.append((ctx.cuenta_param("CTA_CF_IVA"), iva, 0))
            if tipo_pago == "CON":
                lin.append((caja, 0, total))
            else:
                if a_cuenta > 0:
                    lin.append((caja, 0, a_cuenta))
                lin.append((ctx.cuenta_param("CTA_CXP"), 0, saldo, None, prov["id"]))
            comp = ctx.vouchers.asiento(f, glosa, lin, "COMPRA", cid, tipo="E", a_nombre=prov["nombre"], nro_doc=d.get("nro_factura"))
            fid = None
            if con_factura:
                fid = ctx.iva.desde_documento("C", f, prov, d["nro_factura"], d.get("nro_autorizacion") or "", total, 0.0, comp, "COMPRA", cid)
            self.db.execute("UPDATE compra SET comprobante_id=?, factura_id=?, mov_id=? WHERE id=?", (comp, fid, mid, cid))
        ctx.auditar("Compras", "REGISTRAR_COMPRA", f"Compra {cid} Bs {total:,.2f}")
        return {"id": cid, "total": total, "iva": iva, "comprobante_id": comp}

    def anular(self, cid: int) -> None:
        ctx = self.ctx
        ctx.requiere("COM.COMPRAS")
        ctx.requiere_abierta()
        c = self.db.one("SELECT * FROM compra WHERE id=?", (cid,))
        if not c or c["estado"] != "V":
            raise ErrorNegocio("Compra inexistente o ya anulada.")
        if self.db.scalar("SELECT COUNT(*) FROM cobro_doc cd JOIN cobro_pago p ON p.id=cd.cobro_id WHERE cd.doc_tipo='C' AND cd.doc_id=? AND p.estado='V'", (cid,), 0):
            raise ErrorNegocio("La compra tiene pagos aplicados: anule primero los pagos.")
        with self.db.tx():
            if c["mov_id"]:
                ctx.inventario.reversar(c["mov_id"])
            if c["comprobante_id"]:
                ctx.vouchers.anular(c["comprobante_id"], interno=True)
            if c["factura_id"]:
                self.db.execute("UPDATE factura SET estado='A', importe_total=0, no_sujeto=0, exento=0, tasa_cero=0, subtotal=0, descuentos=0, base_iva=0, iva=0 WHERE id=?",
                                (c["factura_id"],))
            self.db.execute("UPDATE compra SET estado='A', saldo=0 WHERE id=?", (cid,))
        ctx.auditar("Compras", "ANULAR_COMPRA", f"Compra {cid}")


class CobroPagoService:
    """clase 'CO' = cobro a cliente, 'PA' = pago a proveedor."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def pendientes(self, tercero_id: int, clase: str) -> list[dict]:
        tabla = "venta" if clase == "CO" else "compra"
        return self.db.query(f"SELECT id, numero, fecha, total, saldo, vencimiento, nro_factura FROM {tabla} WHERE tercero_id=? AND estado='V' AND saldo>0.004 ORDER BY fecha, numero", (tercero_id,))

    def registrar(self, d: dict) -> dict:
        ctx = self.ctx
        ctx.requiere("COM.COBROS")
        ctx.requiere_abierta()
        clase = d.get("clase")
        if clase not in ("CO", "PA"):
            raise ErrorNegocio("Clase no válida.")
        f = ctx.requiere_fecha(d.get("fecha"))
        t = ctx.terceros.obtener(d.get("tercero_id") or 0)
        if not t:
            raise ErrorNegocio("Seleccione el cliente/proveedor.")
        monto = r2(d.get("monto") or 0)
        if monto <= 0:
            raise ErrorNegocio("El monto debe ser mayor a cero.")
        tabla = "venta" if clase == "CO" else "compra"
        tdoc = "V" if clase == "CO" else "C"
        aplic = d.get("aplicaciones")
        if aplic is None:  # automático: documentos más antiguos primero
            aplic, resto = [], monto
            for p in self.pendientes(t["id"], clase):
                if resto <= 0:
                    break
                x = min(resto, p["saldo"])
                aplic.append({"doc_id": p["id"], "monto": r2(x)})
                resto = r2(resto - x)
        total_aplic = r2(sum(a["monto"] for a in aplic))
        if total_aplic > monto + 0.004:
            raise ErrorNegocio("Lo aplicado a documentos supera el monto.")
        excedente = r2(monto - total_aplic)
        with self.db.tx():
            numero = int(self.db.scalar("SELECT MAX(numero) FROM cobro_pago WHERE clase=?", (clase,), 0)) + 1
            cuenta = d.get("cuenta_id") or ctx.cuenta_param("CTA_CAJA")
            pid = self.db.insert("cobro_pago", clase=clase, numero=numero, fecha=f.isoformat(), tercero_id=t["id"], monto=monto, forma=d.get("forma") or "EFE",
                                 cuenta_id=cuenta, nro_doc=d.get("nro_doc"), glosa=d.get("glosa"))
            for a in aplic:
                doc = self.db.one(f"SELECT saldo, estado, tercero_id FROM {tabla} WHERE id=?", (a["doc_id"],))
                if not doc or doc["estado"] != "V" or doc["tercero_id"] != t["id"]:
                    raise ErrorNegocio("Documento no válido para este cobro/pago.")
                if a["monto"] > doc["saldo"] + 0.004:
                    raise ErrorNegocio(f"Se aplica más que el saldo del documento (saldo Bs {doc['saldo']:,.2f}).")
                self.db.execute(f"UPDATE {tabla} SET saldo=ROUND(saldo-?,2) WHERE id=?", (a["monto"], a["doc_id"]))
                self.db.insert("cobro_doc", cobro_id=pid, doc_tipo=tdoc, doc_id=a["doc_id"], monto=a["monto"])
            if clase == "CO":
                glosa = d.get("glosa") or f"Cobro Nº {numero} de {t['nombre']}"
                lin = [(cuenta, monto, 0)]
                if total_aplic > 0:
                    lin.append((ctx.cuenta_param("CTA_CXC"), 0, total_aplic, None, t["id"]))
                if excedente > 0:
                    lin.append((ctx.cuenta_param("CTA_ANT_CLI"), 0, excedente, None, t["id"]))
                tipo = "I"
            else:
                glosa = d.get("glosa") or f"Pago Nº {numero} a {t['nombre']}"
                lin = [(cuenta, 0, monto)]
                if total_aplic > 0:
                    lin.append((ctx.cuenta_param("CTA_CXP"), total_aplic, 0, None, t["id"]))
                if excedente > 0:
                    lin.append((ctx.cuenta_param("CTA_ANT_PROV"), excedente, 0, None, t["id"]))
                tipo = "E"
            cid = ctx.vouchers.asiento(f, glosa, lin, "COBRO", pid, tipo=tipo, a_nombre=t["nombre"], nro_doc=d.get("nro_doc"))
            self.db.execute("UPDATE cobro_pago SET comprobante_id=? WHERE id=?", (cid, pid))
        ctx.auditar("Cobros y pagos", "COBRO" if clase == "CO" else "PAGO", f"{numero} Bs {monto:,.2f}")
        return {"id": pid, "numero": numero, "comprobante_id": cid, "excedente": excedente}

    def anular(self, pid: int) -> None:
        ctx = self.ctx
        ctx.requiere("COM.COBROS")
        ctx.requiere_abierta()
        p = self.db.one("SELECT * FROM cobro_pago WHERE id=?", (pid,))
        if not p or p["estado"] != "V":
            raise ErrorNegocio("Registro inexistente o ya anulado.")
        tabla = "venta" if p["clase"] == "CO" else "compra"
        with self.db.tx():
            for a in self.db.query("SELECT * FROM cobro_doc WHERE cobro_id=?", (pid,)):
                self.db.execute(f"UPDATE {tabla} SET saldo=ROUND(saldo+?,2) WHERE id=? AND estado='V'", (a["monto"], a["doc_id"]))
            if p["comprobante_id"]:
                ctx.vouchers.anular(p["comprobante_id"], interno=True)
            self.db.execute("UPDATE cobro_pago SET estado='A' WHERE id=?", (pid,))
        ctx.auditar("Cobros y pagos", "ANULAR", f"{p['clase']}-{p['numero']}")

    def listar(self, clase: str | None = None, desde=None, hasta=None) -> list[dict]:
        sql = "SELECT c.*, t.nombre AS tercero FROM cobro_pago c JOIN tercero t ON t.id=c.tercero_id WHERE 1=1"
        p: list = []
        if clase:
            sql += " AND c.clase=?"
            p.append(clase)
        if desde:
            sql += " AND c.fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND c.fecha<=?"
            p.append(iso(hasta))
        return self.db.query(sql + " ORDER BY c.fecha, c.numero", p)

    def estado_cuenta(self, tercero_id: int, clase: str, desde=None, hasta=None) -> list[dict]:
        """Movimientos del tercero: cargos (ventas/compras) y abonos (cobros/pagos) con saldo corrido."""
        tabla = "venta" if clase == "C" else "compra"
        filas = []
        for d in self.db.query(f"SELECT fecha, numero, total, a_cuenta, nro_factura FROM {tabla} WHERE tercero_id=? AND estado='V' AND tipo_pago='CRE'", (tercero_id,)):
            filas.append({"fecha": d["fecha"], "doc": f"{'Venta' if clase == 'C' else 'Compra'} {d['numero']}", "cargo": d["total"], "abono": d["a_cuenta"], "ref": d["nro_factura"]})
        cl = "CO" if clase == "C" else "PA"
        for c in self.db.query("SELECT fecha, numero, monto FROM cobro_pago WHERE tercero_id=? AND clase=? AND estado='V'", (tercero_id, cl)):
            filas.append({"fecha": c["fecha"], "doc": f"{'Cobro' if clase == 'C' else 'Pago'} {c['numero']}", "cargo": 0.0, "abono": c["monto"], "ref": ""})
        filas.sort(key=lambda x: (x["fecha"], x["doc"]))
        saldo = 0.0
        for f in filas:
            saldo = r2(saldo + f["cargo"] - f["abono"])
            f["saldo"] = saldo
        if desde:
            filas = [f for f in filas if f["fecha"] >= iso(desde)]
        if hasta:
            filas = [f for f in filas if f["fecha"] <= iso(hasta)]
        return filas
