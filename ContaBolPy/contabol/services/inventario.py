"""Inventarios: ítems, almacenes, movimientos y kardex valorado (costo promedio ponderado, FEFO)."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import iso, r2, rn, to_date


class InventarioService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    # ------------------------------------------------------------ catálogos
    def catalogo(self, tabla: str) -> list[dict]:
        assert tabla in ("almacen", "unidad", "grupo_item", "vendedor")
        return self.db.query(f"SELECT * FROM {tabla} ORDER BY codigo")

    def guardar_catalogo(self, tabla: str, d: dict) -> int:
        assert tabla in ("almacen", "unidad", "grupo_item", "vendedor")
        self.ctx.requiere("INV.ITEMS")
        cod, nom = (d.get("codigo") or "").strip().upper(), (d.get("nombre") or "").strip()
        if not cod or not nom:
            raise ErrorNegocio("Código y nombre son obligatorios.")
        if self.db.scalar(f"SELECT COUNT(*) FROM {tabla} WHERE codigo=? AND id<>?", (cod, d.get("id") or 0)):
            raise ErrorNegocio(f"Ya existe el código {cod}.")
        extra = {}
        if tabla == "almacen":
            extra = {"direccion": d.get("direccion")}
        if tabla == "vendedor":
            extra = {"comision": float(d.get("comision") or 0)}
        if d.get("id"):
            self.db.update(tabla, d["id"], codigo=cod, nombre=nom, **extra)
            return d["id"]
        return self.db.insert(tabla, codigo=cod, nombre=nom, **extra)

    def eliminar_catalogo(self, tabla: str, id_: int) -> None:
        self.ctx.requiere("INV.ITEMS")
        try:
            self.db.delete(tabla, id_)
        except Exception as ex:
            raise ErrorNegocio("El registro está en uso y no puede eliminarse.") from ex

    # ---------------------------------------------------------------- ítems
    def items(self, texto: str = "", solo_activos: bool = True) -> list[dict]:
        sql = ("SELECT i.*, u.codigo AS unidad, g.nombre AS grupo FROM item i LEFT JOIN unidad u ON u.id=i.unidad_id "
               "LEFT JOIN grupo_item g ON g.id=i.grupo_id WHERE 1=1")
        p: list = []
        if solo_activos:
            sql += " AND i.activo=1"
        if texto:
            sql += " AND (i.codigo LIKE ? OR i.nombre LIKE ?)"
            p += [f"%{texto}%"] * 2
        return self.db.query(sql + " ORDER BY i.codigo", p)

    def item(self, iid: int) -> dict | None:
        return self.db.one("SELECT * FROM item WHERE id=?", (iid,))

    def guardar_item(self, d: dict) -> int:
        self.ctx.requiere("INV.ITEMS")
        cod, nom = (d.get("codigo") or "").strip().upper(), (d.get("nombre") or "").strip()
        if not cod or not nom:
            raise ErrorNegocio("Código y nombre del ítem son obligatorios.")
        if self.db.scalar("SELECT COUNT(*) FROM item WHERE codigo=? AND id<>?", (cod, d.get("id") or 0)):
            raise ErrorNegocio(f"Ya existe el ítem {cod}.")
        vals = dict(codigo=cod, nombre=nom, grupo_id=d.get("grupo_id") or None, unidad_id=d.get("unidad_id") or None,
                    precio_venta=float(d.get("precio_venta") or 0), stock_min=float(d.get("stock_min") or 0),
                    es_servicio=1 if d.get("es_servicio") else 0, controla_venc=1 if d.get("controla_venc") else 0,
                    tipo=d.get("tipo") or "M", activo=1 if d.get("activo", True) else 0)
        if vals["precio_venta"] < 0:
            raise ErrorNegocio("El precio no puede ser negativo.")
        if d.get("id"):
            self.db.update("item", d["id"], **vals)
            return d["id"]
        return self.db.insert("item", **vals)

    def eliminar_item(self, iid: int) -> None:
        self.ctx.requiere("INV.ITEMS")
        if self.db.scalar("SELECT COUNT(*) FROM kardex WHERE item_id=?", (iid,), 0):
            self.db.execute("UPDATE item SET activo=0 WHERE id=?", (iid,))
            raise ErrorNegocio("El ítem tiene movimientos: se marcó como inactivo.")
        self.db.delete("item", iid)

    def stock(self, item_id: int, almacen_id: int | None = None) -> float:
        if almacen_id:
            return float(self.db.scalar("SELECT cantidad FROM item_stock WHERE item_id=? AND almacen_id=?", (item_id, almacen_id), 0.0))
        return float(self.db.scalar("SELECT stock FROM item WHERE id=?", (item_id,), 0.0))

    # ------------------------------------------------------------ movimientos
    def _numero(self) -> int:
        return int(self.db.scalar("SELECT MAX(numero) FROM mov_inv", (), 0)) + 1

    def _aplicar(self, item_id: int, almacen_id: int, fecha: str, mov_id: int, tipo: str, detalle: str, cant: float,
                 costo_unit: float | None, lote=None, venc=None) -> tuple[float, float]:
        """Aplica una entrada (cant>0) o salida (cant<0) y devuelve (costo_unit, costo_total) de la operación."""
        it = self.item(item_id)
        if it["es_servicio"]:
            return 0.0, 0.0
        stock_antes = float(it["stock"])
        costo_antes = float(it["costo_prom"])
        stock_alm = self.stock(item_id, almacen_id)
        if cant < 0:
            if (stock_alm + cant) < -1e-9 and self.ctx.param("STOCK_NEGATIVO") != "1":
                raise ErrorNegocio(f"Stock insuficiente de '{it['nombre']}' en el almacén (disponible {stock_alm:g}, requerido {-cant:g}).")
            cu = costo_antes if costo_unit is None else costo_unit
            total = r2(abs(cant) * cu)
            nuevo_stock = rn(stock_antes + cant, 6)
            nuevo_costo = costo_antes
            ent_c = sal_c = 0.0
            sal_c = -cant
            ent_v, sal_v = 0.0, total
            if it["controla_venc"]:
                self._consumir_lotes(item_id, almacen_id, -cant)
        else:
            cu = costo_unit if costo_unit is not None else costo_antes
            total = r2(cant * cu)
            nuevo_stock = rn(stock_antes + cant, 6)
            valor_antes = stock_antes * costo_antes if stock_antes > 0 else 0.0
            base = (stock_antes if stock_antes > 0 else 0.0) + cant
            nuevo_costo = rn((valor_antes + cant * cu) / base, 6) if base > 0 else cu
            ent_c, sal_c, ent_v, sal_v = cant, 0.0, total, 0.0
            if it["controla_venc"] and lote:
                self._ingresar_lote(item_id, almacen_id, lote, venc, cant)
        self.db.execute("UPDATE item SET stock=?, costo_prom=? WHERE id=?", (nuevo_stock, nuevo_costo, item_id))
        self.db.execute("INSERT INTO item_stock (item_id, almacen_id, cantidad) VALUES (?,?,?) "
                        "ON CONFLICT(item_id, almacen_id) DO UPDATE SET cantidad=ROUND(cantidad+excluded.cantidad, 6)",
                        (item_id, almacen_id, cant))
        self.db.insert("kardex", item_id=item_id, almacen_id=almacen_id, fecha=fecha, mov_id=mov_id, tipo=tipo, detalle=detalle,
                       ent_cant=ent_c, sal_cant=sal_c, costo_unit=cu, ent_val=ent_v, sal_val=sal_v, saldo_cant=nuevo_stock,
                       saldo_val=r2(max(nuevo_stock, 0) * nuevo_costo), costo_prom=nuevo_costo)
        return cu, total

    def _ingresar_lote(self, item_id, almacen_id, lote, venc, cant) -> None:
        fila = self.db.one("SELECT id FROM item_lote WHERE item_id=? AND almacen_id=? AND lote=?", (item_id, almacen_id, lote))
        if fila:
            self.db.execute("UPDATE item_lote SET cantidad=cantidad+? WHERE id=?", (cant, fila["id"]))
        else:
            self.db.insert("item_lote", item_id=item_id, almacen_id=almacen_id, lote=lote, vencimiento=iso(venc), cantidad=cant)

    def _consumir_lotes(self, item_id, almacen_id, cant) -> None:
        """FEFO: primero el lote que vence antes."""
        resto = cant
        for l in self.db.query("SELECT * FROM item_lote WHERE item_id=? AND almacen_id=? AND cantidad>0 "
                               "ORDER BY CASE WHEN vencimiento IS NULL THEN 1 ELSE 0 END, vencimiento, id", (item_id, almacen_id)):
            if resto <= 1e-9:
                break
            t = min(l["cantidad"], resto)
            self.db.execute("UPDATE item_lote SET cantidad=cantidad-? WHERE id=?", (t, l["id"]))
            resto -= t

    def registrar(self, d: dict, *, interno: bool = False) -> dict:
        """d: tipo (INI,ING,SAL,AJE,AJS,TRA), fecha, almacen_id, almacen_dest_id, glosa, items=[{item_id, cantidad, costo_unit, lote, vencimiento}],
        contra_cuenta (código) opcional para generar asiento."""
        ctx = self.ctx
        if not interno:
            ctx.requiere("INV.MOVIMIENTOS")
        ctx.requiere_abierta()
        f = ctx.requiere_fecha(d.get("fecha"))
        tipo = d["tipo"]
        if tipo not in ("INI", "ING", "SAL", "AJE", "AJS", "TRA"):
            raise ErrorNegocio("Tipo de movimiento no válido.")
        its = [i for i in d.get("items", []) if i.get("item_id") and float(i.get("cantidad") or 0) != 0]
        if not its:
            raise ErrorNegocio("Agregue al menos un ítem con cantidad.")
        alm = d.get("almacen_id")
        if not alm:
            raise ErrorNegocio("Seleccione el almacén.")
        if tipo == "TRA" and (not d.get("almacen_dest_id") or d["almacen_dest_id"] == alm):
            raise ErrorNegocio("Seleccione un almacén de destino distinto al de origen.")
        total_mov = 0.0
        with self.db.tx():
            mid = self.db.insert("mov_inv", tipo=tipo, numero=self._numero(), fecha=f.isoformat(), almacen_id=alm,
                                 almacen_dest_id=d.get("almacen_dest_id"), glosa=d.get("glosa"), doc_tipo=d.get("doc_tipo"), doc_id=d.get("doc_id"))
            for i in its:
                cant = abs(float(i["cantidad"]))
                if cant <= 0:
                    continue
                it = self.item(i["item_id"])
                if not it:
                    raise ErrorNegocio("Ítem inexistente.")
                if tipo in ("INI", "ING", "AJE"):
                    cu = float(i["costo_unit"]) if i.get("costo_unit") is not None else None
                    if tipo == "INI" and (cu is None or cu < 0):
                        raise ErrorNegocio(f"Indique el costo unitario del ítem {it['codigo']}.")
                    cu, tot = self._aplicar(it["id"], alm, f.isoformat(), mid, tipo, d.get("glosa") or tipo, cant, cu, i.get("lote"), i.get("vencimiento"))
                elif tipo in ("SAL", "AJS"):
                    cu, tot = self._aplicar(it["id"], alm, f.isoformat(), mid, tipo, d.get("glosa") or tipo, -cant, i.get("costo_unit"), i.get("lote"))
                else:  # TRA: sale de origen al costo promedio y entra a destino al mismo costo
                    cu, tot = self._aplicar(it["id"], alm, f.isoformat(), mid, "TRA-S", d.get("glosa") or "Traspaso", -cant, None)
                    self._entrada_traspaso(it["id"], d["almacen_dest_id"], f.isoformat(), mid, cant, cu)
                self.db.insert("mov_inv_det", mov_id=mid, item_id=it["id"], cantidad=cant, costo_unit=cu, costo_total=tot,
                               lote=i.get("lote"), vencimiento=iso(i.get("vencimiento")))
                total_mov += tot
            total_mov = r2(total_mov)
            comp = None
            if d.get("generar_asiento") and tipo in ("INI", "AJE", "AJS", "ING", "SAL") and total_mov > 0:
                comp = self._asiento(tipo, f, total_mov, d, mid)
                self.db.execute("UPDATE mov_inv SET comprobante_id=? WHERE id=?", (comp, mid))
        ctx.auditar("Inventarios", f"MOV_{tipo}", f"Nº {mid} Bs {total_mov:,.2f}")
        return {"id": mid, "total": total_mov, "comprobante_id": comp}

    def _entrada_traspaso(self, item_id, alm_dest, fecha, mid, cant, cu) -> None:
        """Entrada en destino sin recalcular el costo promedio global (el traspaso no cambia el valor total)."""
        it = self.item(item_id)
        self.db.execute("INSERT INTO item_stock (item_id, almacen_id, cantidad) VALUES (?,?,?) "
                        "ON CONFLICT(item_id, almacen_id) DO UPDATE SET cantidad=ROUND(cantidad+excluded.cantidad, 6)", (item_id, alm_dest, cant))
        # la salida del origen redujo el stock global; la entrada lo restituye
        self.db.execute("UPDATE item SET stock=ROUND(stock+?,6) WHERE id=?", (cant, item_id))
        it = self.item(item_id)
        self.db.insert("kardex", item_id=item_id, almacen_id=alm_dest, fecha=fecha, mov_id=mid, tipo="TRA-E", detalle="Traspaso",
                       ent_cant=cant, sal_cant=0, costo_unit=cu, ent_val=r2(cant * cu), sal_val=0, saldo_cant=it["stock"],
                       saldo_val=r2(max(it["stock"], 0) * it["costo_prom"]), costo_prom=it["costo_prom"])

    def _asiento(self, tipo: str, fecha, total: float, d: dict, mid: int) -> int:
        ctx = self.ctx
        inv = ctx.cuenta_param("CTA_INVENT")
        glosa = d.get("glosa") or f"Movimiento de inventario {tipo}"
        contra_cod = d.get("contra_cuenta")
        if tipo in ("INI", "ING", "AJE"):
            contra = ctx.cuentas.por_codigo(contra_cod)["id"] if contra_cod else (
                ctx.cuenta_param("CTA_RESULT_ACUM") if tipo == "INI" else ctx.cuenta_param("CTA_DESC_COMP"))
            lineas = [(inv, total, 0), (contra, 0, total)]
        else:
            contra = ctx.cuentas.por_codigo(contra_cod)["id"] if contra_cod else ctx.cuenta_param("CTA_MERMAS")
            lineas = [(contra, total, 0), (inv, 0, total)]
        return ctx.vouchers.asiento(fecha, glosa, lineas, "INV", mid, tipo="T")

    def anular(self, mid: int) -> None:
        """Reversa un movimiento (solo manuales sin documento de origen)."""
        ctx = self.ctx
        ctx.requiere("INV.MOVIMIENTOS")
        ctx.requiere_abierta()
        m = self.db.one("SELECT * FROM mov_inv WHERE id=?", (mid,))
        if not m or m["estado"] != "V":
            raise ErrorNegocio("Movimiento inexistente o ya anulado.")
        if m["doc_tipo"]:
            raise ErrorNegocio("El movimiento pertenece a una nota de venta/compra/producción; anule el documento.")
        with self.db.tx():
            self.reversar(mid)
            if m["comprobante_id"]:
                ctx.vouchers.anular(m["comprobante_id"], interno=True)

    def reversar(self, mid: int) -> None:
        m = self.db.one("SELECT * FROM mov_inv WHERE id=?", (mid,))
        det = self.db.query("SELECT * FROM mov_inv_det WHERE mov_id=?", (mid,))
        f = self.ctx.requiere_fecha(m["fecha"]).isoformat()
        for d in det:
            if m["tipo"] in ("INI", "ING", "AJE"):
                self._aplicar(d["item_id"], m["almacen_id"], f, mid, "ANUL", "Anulación", -d["cantidad"], d["costo_unit"])
            elif m["tipo"] in ("SAL", "AJS"):
                self._aplicar(d["item_id"], m["almacen_id"], f, mid, "ANUL", "Anulación", d["cantidad"], d["costo_unit"], d.get("lote"), d.get("vencimiento"))
            else:
                self._aplicar(d["item_id"], m["almacen_dest_id"], f, mid, "ANUL", "Anulación traspaso", -d["cantidad"], d["costo_unit"])
                self._entrada_traspaso(d["item_id"], m["almacen_id"], f, mid, d["cantidad"], d["costo_unit"])
        self.db.execute("UPDATE mov_inv SET estado='A' WHERE id=?", (mid,))

    # ----------------------------------------------------------------- consultas
    def kardex(self, item_id: int, desde=None, hasta=None, almacen_id: int | None = None) -> dict:
        it = self.item(item_id)
        sql = "SELECT k.*, a.codigo AS almacen FROM kardex k JOIN almacen a ON a.id=k.almacen_id WHERE k.item_id=?"
        p: list = [item_id]
        if almacen_id:
            sql += " AND k.almacen_id=?"
            p.append(almacen_id)
        todos = self.db.query(sql + " ORDER BY k.fecha, k.id", p)
        ini_cant = ini_val = 0.0
        filas = []
        for k in todos:
            if desde and k["fecha"] < iso(desde):
                ini_cant, ini_val = k["saldo_cant"], k["saldo_val"]
            elif not hasta or k["fecha"] <= iso(hasta):
                filas.append(k)
        return {"item": it, "saldo_inicial_cant": ini_cant, "saldo_inicial_val": ini_val, "filas": filas}

    def existencias(self, hasta=None, almacen_id: int | None = None, grupo_id: int | None = None) -> list[dict]:
        """Existencias valoradas al cierre de la fecha (reconstruidas desde el kardex)."""
        h = iso(hasta) or "9999-12-31"
        filas = []
        for it in self.items(solo_activos=False):
            if it["es_servicio"] or (grupo_id and it["grupo_id"] != grupo_id):
                continue
            sql = "SELECT saldo_cant, saldo_val, costo_prom FROM kardex WHERE item_id=? AND fecha<=?"
            p: list = [it["id"], h]
            if almacen_id:
                cant = self.db.scalar("SELECT COALESCE(SUM(ent_cant-sal_cant),0) FROM kardex WHERE item_id=? AND almacen_id=? AND fecha<=?",
                                      (it["id"], almacen_id, h), 0.0)
                last = self.db.one(sql + " ORDER BY fecha DESC, id DESC LIMIT 1", p)
                cp = last["costo_prom"] if last else 0.0
                cant, val = cant, r2(cant * cp)
            else:
                last = self.db.one(sql + " ORDER BY fecha DESC, id DESC LIMIT 1", p)
                cant, val, cp = (last["saldo_cant"], last["saldo_val"], last["costo_prom"]) if last else (0.0, 0.0, 0.0)
            if abs(cant) < 1e-9 and abs(val) < 0.005:
                continue
            filas.append({"codigo": it["codigo"], "nombre": it["nombre"], "unidad": it["unidad"], "grupo": it["grupo"], "cantidad": cant,
                          "costo_unit": cp, "valor": r2(val), "stock_min": it["stock_min"]})
        return filas

    def por_vencer(self, hasta) -> list[dict]:
        return self.db.query(
            "SELECT i.codigo, i.nombre, a.codigo AS almacen, l.lote, l.vencimiento, l.cantidad FROM item_lote l JOIN item i ON i.id=l.item_id "
            "JOIN almacen a ON a.id=l.almacen_id WHERE l.cantidad>0 AND l.vencimiento IS NOT NULL AND l.vencimiento<=? ORDER BY l.vencimiento",
            (iso(hasta),))

    def movimientos(self, desde=None, hasta=None, tipo: str | None = None) -> list[dict]:
        sql = ("SELECT m.*, a.nombre AS almacen, (SELECT COALESCE(SUM(costo_total),0) FROM mov_inv_det WHERE mov_id=m.id) AS total "
               "FROM mov_inv m JOIN almacen a ON a.id=m.almacen_id WHERE 1=1")
        p: list = []
        if desde:
            sql += " AND m.fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND m.fecha<=?"
            p.append(iso(hasta))
        if tipo:
            sql += " AND m.tipo=?"
            p.append(tipo)
        return self.db.query(sql + " ORDER BY m.fecha, m.id", p)

    def valor_total(self, hasta=None) -> float:
        return r2(sum(f["valor"] for f in self.existencias(hasta)))
