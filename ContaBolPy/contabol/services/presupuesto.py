"""Presupuesto por cuenta y mes."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import r2, to_date


class PresupuestoService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def guardar(self, cuenta_id: int, montos: list[float]) -> None:
        self.ctx.requiere("CONT.PRESUPUESTO")
        if len(montos) != 12:
            raise ErrorNegocio("Se requieren 12 montos mensuales.")
        with self.db.tx():
            for m, v in enumerate(montos, 1):
                self.db.execute("INSERT INTO presupuesto (cuenta_id, mes, monto) VALUES (?,?,?) ON CONFLICT(cuenta_id, mes) DO UPDATE SET monto=excluded.monto",
                                (cuenta_id, m, r2(v)))

    def obtener(self, cuenta_id: int) -> list[float]:
        d = {r["mes"]: r["monto"] for r in self.db.query("SELECT mes, monto FROM presupuesto WHERE cuenta_id=?", (cuenta_id,))}
        return [d.get(m, 0.0) for m in range(1, 13)]

    def ejecucion(self, mes_desde: int = 1, mes_hasta: int = 12) -> list[dict]:
        filas = []
        for c in self.db.query("SELECT c.id, c.codigo, c.nombre FROM cuenta c WHERE c.id IN (SELECT cuenta_id FROM presupuesto WHERE monto<>0) ORDER BY c.codigo"):
            pres = self.db.scalar("SELECT SUM(monto) FROM presupuesto WHERE cuenta_id=? AND mes BETWEEN ? AND ?", (c["id"], mes_desde, mes_hasta), 0.0)
            ejec = self.db.scalar(
                "SELECT COALESCE(SUM(d.debe_bs-d.haber_bs),0) FROM comp_det d JOIN comprobante k ON k.id=d.comprobante_id "
                "WHERE k.estado='V' AND k.origen<>'CIERRE' AND d.cuenta_id=? AND k.mes BETWEEN ? AND ?", (c["id"], mes_desde, mes_hasta), 0.0)
            filas.append({"codigo": c["codigo"], "nombre": c["nombre"], "presupuesto": r2(pres), "ejecutado": r2(ejec), "saldo": r2(pres - ejec),
                          "pct": round(ejec / pres * 100, 1) if pres else 0.0})
        return filas

    def verificar(self, lineas: list[dict], fecha) -> None:
        f = to_date(fecha)
        for l in lineas:
            if l["debe_bs"] <= 0:
                continue
            pres = self.db.scalar("SELECT SUM(monto) FROM presupuesto WHERE cuenta_id=? AND mes<=?", (l["cuenta_id"], f.month))
            if pres is None:
                continue
            ejec = self.db.scalar("SELECT COALESCE(SUM(d.debe_bs-d.haber_bs),0) FROM comp_det d JOIN comprobante k ON k.id=d.comprobante_id "
                                  "WHERE k.estado='V' AND d.cuenta_id=? AND k.mes<=?", (l["cuenta_id"], f.month), 0.0)
            if ejec + l["debe_bs"] > pres + 0.005:
                c = self.ctx.cuentas.obtener(l["cuenta_id"])
                raise ErrorNegocio(f"Se excede el presupuesto de {c['codigo']} {c['nombre']} (presupuesto acumulado Bs {pres:,.2f}, ejecutado Bs {ejec:,.2f}).")
