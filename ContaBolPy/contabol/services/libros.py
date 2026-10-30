"""Libros contables: diario, mayor, sumas y saldos y agregaciones jerárquicas."""
from __future__ import annotations

from ..util import iso, r2


class LibroService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    @staticmethod
    def _cols(moneda: str) -> tuple[str, str]:
        return ("debe_usd", "haber_usd") if moneda == "USD" else ("debe_bs", "haber_bs")

    def movimientos(self, desde, hasta, moneda: str = "BS", incluir_cierre: bool = True, origenes_excluir: tuple = ()) -> dict[int, tuple[float, float]]:
        """Suma de debe/haber por cuenta entre fechas (comprobantes vigentes)."""
        cd, ch = self._cols(moneda)
        sql = (f"SELECT d.cuenta_id, SUM(d.{cd}) AS debe, SUM(d.{ch}) AS haber FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id "
               "WHERE c.estado='V'")
        p: list = []
        if desde:
            sql += " AND c.fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND c.fecha<=?"
            p.append(iso(hasta))
        if not incluir_cierre:
            sql += " AND c.origen<>'CIERRE'"
        for o in origenes_excluir:
            sql += " AND c.origen<>?"
            p.append(o)
        sql += " GROUP BY d.cuenta_id"
        return {r["cuenta_id"]: (r["debe"] or 0.0, r["haber"] or 0.0) for r in self.db.query(sql, p)}

    def plan(self) -> dict[int, dict]:
        return {c["id"]: c for c in self.db.query("SELECT * FROM cuenta ORDER BY codigo")}

    def acumular(self, mov: dict[int, tuple[float, float]]) -> dict[int, list[float]]:
        """Acumula los importes de cuentas de movimiento hacia todos sus ancestros."""
        plan = self.plan()
        acum: dict[int, list[float]] = {}
        for cid, (d, h) in mov.items():
            actual = cid
            while actual is not None:
                a = acum.setdefault(actual, [0.0, 0.0])
                a[0] += d
                a[1] += h
                actual = plan[actual]["padre_id"]
        return acum

    # ---------------------------------------------------------------- sumas y saldos
    def sumas_saldos(self, desde, hasta, nivel: int = 5, moneda: str = "BS", solo_con_saldo: bool = True,
                     incluir_cierre: bool = True) -> list[dict]:
        ini = self.acumular(self.movimientos(None, self._dia_antes(desde), moneda, incluir_cierre)) if desde else {}
        per = self.acumular(self.movimientos(desde, hasta, moneda, incluir_cierre))
        filas = []
        for c in self.db.query("SELECT * FROM cuenta WHERE nivel<=? ORDER BY codigo", (nivel,)):
            i = ini.get(c["id"], [0.0, 0.0])
            p = per.get(c["id"], [0.0, 0.0])
            if solo_con_saldo and abs(i[0]) + abs(i[1]) + abs(p[0]) + abs(p[1]) < 0.005:
                continue
            si = r2(i[0] - i[1])
            sf = r2(i[0] - i[1] + p[0] - p[1])
            filas.append({"cuenta_id": c["id"], "codigo": c["codigo"], "nombre": c["nombre"], "nivel": c["nivel"],
                          "es_movimiento": c["es_movimiento"], "tipo": c["tipo"],
                          "saldo_ini_d": si if si > 0 else 0.0, "saldo_ini_h": -si if si < 0 else 0.0,
                          "debe": r2(p[0]), "haber": r2(p[1]),
                          "saldo_d": sf if sf > 0 else 0.0, "saldo_h": -sf if sf < 0 else 0.0})
        return filas

    @staticmethod
    def _dia_antes(d):
        from datetime import timedelta
        from ..util import to_date
        return to_date(d) - timedelta(days=1)

    def saldos_a(self, hasta, moneda: str = "BS", incluir_cierre: bool = False, desde=None) -> dict[int, float]:
        """Saldo (debe - haber) por cuenta y ancestros hasta una fecha."""
        acum = self.acumular(self.movimientos(desde, hasta, moneda, incluir_cierre))
        return {cid: r2(v[0] - v[1]) for cid, v in acum.items()}

    # --------------------------------------------------------------------- mayor
    def mayor(self, cuenta_id: int, desde, hasta, moneda: str = "BS") -> dict:
        c = self.ctx.cuentas.obtener(cuenta_id)
        cd, ch = self._cols(moneda)
        # saldo anterior incluye todas las cuentas hijas si es una cuenta de grupo
        like = c["codigo"] + ".%"
        cond = "(cu.id=? OR cu.codigo LIKE ?)"
        ant = self.db.one(
            f"SELECT COALESCE(SUM(d.{cd}),0) AS d, COALESCE(SUM(d.{ch}),0) AS h FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id "
            f"JOIN cuenta cu ON cu.id=d.cuenta_id WHERE c.estado='V' AND {cond} AND c.fecha<?", (cuenta_id, like, iso(desde)))
        nat = 1 if c["naturaleza"] == "D" else -1
        saldo = r2((ant["d"] - ant["h"]) * nat)
        filas = self.db.query(
            f"SELECT c.fecha, c.tipo, c.numero, c.mes, c.id AS comprobante_id, COALESCE(d.glosa, c.glosa) AS glosa, cu.codigo AS cuenta_codigo, "
            f"d.{cd} AS debe, d.{ch} AS haber FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id JOIN cuenta cu ON cu.id=d.cuenta_id "
            f"WHERE c.estado='V' AND {cond} AND c.fecha BETWEEN ? AND ? ORDER BY c.fecha, c.tipo, c.numero, d.linea",
            (cuenta_id, like, iso(desde), iso(hasta)))
        sal = saldo
        for f in filas:
            sal = r2(sal + (f["debe"] - f["haber"]) * nat)
            f["saldo"] = sal
        return {"cuenta": c, "saldo_anterior": saldo, "filas": filas, "saldo_final": sal,
                "total_debe": r2(sum(f["debe"] for f in filas)), "total_haber": r2(sum(f["haber"] for f in filas))}

    # -------------------------------------------------------------------- diario
    def diario(self, desde, hasta, moneda: str = "BS") -> list[dict]:
        cd, ch = self._cols(moneda)
        return self.db.query(
            f"SELECT c.id AS comprobante_id, c.fecha, c.tipo, c.numero, c.mes, c.glosa AS glosa_cab, cu.codigo AS cuenta_codigo, "
            f"cu.nombre AS cuenta_nombre, COALESCE(d.glosa,'') AS glosa, d.{cd} AS debe, d.{ch} AS haber, d.linea "
            f"FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id JOIN cuenta cu ON cu.id=d.cuenta_id "
            f"WHERE c.estado='V' AND c.fecha BETWEEN ? AND ? ORDER BY c.fecha, c.tipo, c.numero, d.linea", (iso(desde), iso(hasta)))
