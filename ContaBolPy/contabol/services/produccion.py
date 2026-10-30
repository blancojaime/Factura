"""Órdenes de producción: materia prima, mano de obra directa y costos indirectos de fabricación."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import iso, r2


class ProduccionService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def listar(self, estado: str | None = None) -> list[dict]:
        sql = ("SELECT o.*, i.codigo AS item_codigo, i.nombre AS item_nombre, (o.costo_mp+o.costo_mod+o.costo_cif) AS costo_total FROM orden_prod o "
               "JOIN item i ON i.id=o.item_id")
        p: list = []
        if estado:
            sql += " WHERE o.estado=?"
            p.append(estado)
        return self.db.query(sql + " ORDER BY o.fecha, o.numero", p)

    def obtener(self, oid: int) -> dict | None:
        o = self.db.one("SELECT o.*, i.codigo AS item_codigo, i.nombre AS item_nombre FROM orden_prod o JOIN item i ON i.id=o.item_id WHERE o.id=?", (oid,))
        if o:
            o["mp"] = self.db.query("SELECT m.*, i.codigo, i.nombre FROM orden_mp m JOIN item i ON i.id=m.item_id WHERE m.orden_id=? ORDER BY m.id", (oid,))
            o["mod"] = self.db.query("SELECT * FROM orden_mod WHERE orden_id=? ORDER BY id", (oid,))
            o["cif"] = self.db.query("SELECT * FROM orden_cif WHERE orden_id=? ORDER BY id", (oid,))
            o["costo_total"] = r2(o["costo_mp"] + o["costo_mod"] + o["costo_cif"])
            o["costo_unit"] = r2(o["costo_total"] / o["cant_prod"]) if o["cant_prod"] else 0.0
        return o

    def abrir(self, fecha, item_id: int, cantidad: float, almacen_mp_id: int, almacen_pt_id: int, glosa: str = "") -> int:
        ctx = self.ctx
        ctx.requiere("COS.PRODUCCION")
        ctx.requiere_abierta()
        f = ctx.requiere_fecha(fecha)
        if cantidad <= 0:
            raise ErrorNegocio("La cantidad a producir debe ser mayor a cero.")
        numero = int(self.db.scalar("SELECT MAX(numero) FROM orden_prod", (), 0)) + 1
        return self.db.insert("orden_prod", numero=numero, fecha=f.isoformat(), item_id=item_id, cant_plan=cantidad, almacen_mp_id=almacen_mp_id,
                              almacen_pt_id=almacen_pt_id, glosa=glosa)

    def _abierta(self, oid: int) -> dict:
        o = self.db.one("SELECT * FROM orden_prod WHERE id=?", (oid,))
        if not o or o["estado"] != "A":
            raise ErrorNegocio("La orden no existe o ya está cerrada.")
        self.ctx.requiere("COS.PRODUCCION")
        self.ctx.requiere_abierta()
        return o

    def consumir_mp(self, oid: int, fecha, items: list[dict]) -> float:
        """items: [{item_id, cantidad}] — sale del almacén de MP al costo promedio vigente."""
        o = self._abierta(oid)
        f = self.ctx.requiere_fecha(fecha)
        with self.db.tx():
            res = self.ctx.inventario.registrar({"tipo": "SAL", "fecha": f, "almacen_id": o["almacen_mp_id"], "glosa": f"Consumo MP orden {o['numero']}",
                                                 "items": items, "doc_tipo": "P", "doc_id": oid}, interno=True)
            total = 0.0
            for d in self.db.query("SELECT * FROM mov_inv_det WHERE mov_id=?", (res["id"],)):
                self.db.insert("orden_mp", orden_id=oid, item_id=d["item_id"], fecha=f.isoformat(), cantidad=d["cantidad"], costo_unit=d["costo_unit"],
                               costo_total=d["costo_total"], mov_id=res["id"])
                total += d["costo_total"]
            self.db.execute("UPDATE orden_prod SET costo_mp=ROUND(costo_mp+?,2) WHERE id=?", (total, oid))
        return r2(total)

    def agregar_mod(self, oid: int, empleado_id: int | None, horas: float, tarifa: float | None = None, descripcion: str = "") -> float:
        o = self._abierta(oid)
        if horas <= 0:
            raise ErrorNegocio("Las horas deben ser mayores a cero.")
        if tarifa is None:
            e = self.ctx.rrhh.empleado(empleado_id) if empleado_id else None
            if not e:
                raise ErrorNegocio("Indique la tarifa por hora o seleccione un empleado.")
            tarifa = r2(e["haber_basico"] / 30 / 8)
        monto = r2(horas * tarifa)
        self.db.insert("orden_mod", orden_id=oid, empleado_id=empleado_id, descripcion=descripcion, horas=horas, tarifa=tarifa, monto=monto)
        self.db.execute("UPDATE orden_prod SET costo_mod=ROUND(costo_mod+?,2) WHERE id=?", (monto, oid))
        return monto

    def agregar_cif(self, oid: int, concepto: str, monto: float) -> None:
        self._abierta(oid)
        if monto <= 0 or not concepto.strip():
            raise ErrorNegocio("Indique el concepto y un monto mayor a cero.")
        self.db.insert("orden_cif", orden_id=oid, concepto=concepto.strip(), monto=r2(monto))
        self.db.execute("UPDATE orden_prod SET costo_cif=ROUND(costo_cif+?,2) WHERE id=?", (r2(monto), oid))

    def cerrar(self, oid: int, fecha, cantidad_producida: float) -> int:
        """Ingresa el producto terminado al costo total y capitaliza MOD y CIF en inventarios."""
        ctx = self.ctx
        o = self._abierta(oid)
        f = ctx.requiere_fecha(fecha)
        if cantidad_producida <= 0:
            raise ErrorNegocio("La cantidad producida debe ser mayor a cero.")
        total = r2(o["costo_mp"] + o["costo_mod"] + o["costo_cif"])
        if total <= 0:
            raise ErrorNegocio("La orden no tiene costos cargados.")
        with self.db.tx():
            ctx.inventario.registrar({"tipo": "ING", "fecha": f, "almacen_id": o["almacen_pt_id"], "glosa": f"Producto terminado orden {o['numero']}",
                                      "items": [{"item_id": o["item_id"], "cantidad": cantidad_producida, "costo_unit": total / cantidad_producida}],
                                      "doc_tipo": "P", "doc_id": oid}, interno=True)
            lineas = [(ctx.cuenta_param("CTA_INVENT"), total, 0)]
            if o["costo_mp"]:
                lineas.append((ctx.cuenta_param("CTA_INVENT"), 0, o["costo_mp"]))
            if o["costo_mod"]:
                lineas.append((ctx.cuenta_param("CTA_MOD"), 0, o["costo_mod"]))
            if o["costo_cif"]:
                lineas.append((ctx.cuenta_param("CTA_CIF"), 0, o["costo_cif"]))
            cid = ctx.vouchers.asiento(f, f"Cierre de orden de producción Nº {o['numero']}", lineas, "PROD", oid, tipo="T")
            self.db.execute("UPDATE orden_prod SET estado='C', cant_prod=?, fecha_cierre=?, comprobante_id=? WHERE id=?", (cantidad_producida, f.isoformat(), cid, oid))
        ctx.auditar("Producción", "CERRAR_ORDEN", f"Orden {o['numero']} costo Bs {total:,.2f}")
        return cid
