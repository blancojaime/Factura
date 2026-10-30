"""Bancos: libreta y conciliación bancaria."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import iso, r2


class BancoService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def cuentas_banco(self) -> list[dict]:
        return self.db.query("SELECT * FROM cuenta WHERE es_movimiento=1 AND (es_banco=1 OR es_efectivo=1) ORDER BY codigo")

    def libreta(self, cuenta_id: int, desde, hasta) -> dict:
        return self.ctx.libros.mayor(cuenta_id, desde, hasta)

    def pendientes(self, cuenta_id: int, hasta) -> list[dict]:
        return self.db.query(
            "SELECT d.id, c.fecha, c.tipo, c.numero, c.nro_doc, COALESCE(d.glosa,c.glosa) AS glosa, d.debe_bs AS debe, d.haber_bs AS haber "
            "FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id WHERE c.estado='V' AND d.cuenta_id=? AND c.fecha<=? "
            "AND d.conciliado IS NULL ORDER BY c.fecha, c.id", (cuenta_id, iso(hasta)))

    def conciliar(self, det_ids: list[int], fecha) -> None:
        self.ctx.requiere("CONT.BANCOS")
        self.ctx.requiere_abierta()
        with self.db.tx():
            for i in det_ids:
                self.db.execute("UPDATE comp_det SET conciliado=? WHERE id=?", (iso(fecha), i))

    def desconciliar(self, det_ids: list[int]) -> None:
        self.ctx.requiere("CONT.BANCOS")
        with self.db.tx():
            for i in det_ids:
                self.db.execute("UPDATE comp_det SET conciliado=NULL WHERE id=?", (i,))

    def conciliacion(self, cuenta_id: int, hasta, saldo_extracto: float | None = None) -> dict:
        c = self.ctx.cuentas.obtener(cuenta_id)
        if not c:
            raise ErrorNegocio("Cuenta inexistente.")
        saldo_libros = self.ctx.cuentas.saldo(cuenta_id, hasta)
        pend = self.pendientes(cuenta_id, hasta)
        depositos = r2(sum(p["debe"] for p in pend))
        cheques = r2(sum(p["haber"] for p in pend))
        saldo_banco_calc = r2(saldo_libros - depositos + cheques)
        return {"cuenta": c, "saldo_libros": saldo_libros, "depositos_transito": depositos, "cheques_circulacion": cheques,
                "saldo_banco_calculado": saldo_banco_calc, "saldo_extracto": saldo_extracto,
                "diferencia": r2(saldo_banco_calc - saldo_extracto) if saldo_extracto is not None else None, "pendientes": pend}
