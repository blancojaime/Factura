"""Tipos de cambio del dólar y UFV."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import iso, to_date


class TipoCambioService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def guardar(self, fecha, dolar: float, ufv: float = 0.0) -> None:
        self.ctx.requiere("CONT.TIPOCAMBIO")
        f = to_date(fecha)
        if f is None:
            raise ErrorNegocio("Fecha no válida.")
        if dolar <= 0:
            raise ErrorNegocio("El tipo de cambio del dólar debe ser mayor a cero.")
        if ufv < 0:
            raise ErrorNegocio("La UFV no puede ser negativa.")
        self.db.execute("INSERT INTO tipo_cambio (fecha, dolar, ufv) VALUES (?,?,?) ON CONFLICT(fecha) DO UPDATE SET dolar=excluded.dolar, ufv=excluded.ufv",
                        (f.isoformat(), dolar, ufv))

    def eliminar(self, fecha) -> None:
        self.ctx.requiere("CONT.TIPOCAMBIO")
        self.db.execute("DELETE FROM tipo_cambio WHERE fecha=?", (iso(fecha),))

    def listar(self, desde=None, hasta=None) -> list[dict]:
        sql, p = "SELECT * FROM tipo_cambio WHERE 1=1", []
        if desde:
            sql += " AND fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND fecha<=?"
            p.append(iso(hasta))
        return self.db.query(sql + " ORDER BY fecha", p)

    def existe(self, fecha) -> bool:
        return bool(self.db.scalar("SELECT COUNT(*) FROM tipo_cambio WHERE fecha=?", (iso(fecha),), 0))

    def dolar(self, fecha=None) -> float:
        """T.C. vigente a la fecha (el último cargado hasta esa fecha); si no hay, el parámetro por defecto."""
        f = iso(fecha) or "9999-12-31"
        v = self.db.scalar("SELECT dolar FROM tipo_cambio WHERE fecha<=? ORDER BY fecha DESC LIMIT 1", (f,))
        return float(v) if v else self.ctx.pnum("TC_DEFECTO", 6.96)

    def ufv(self, fecha=None) -> float:
        f = iso(fecha) or "9999-12-31"
        v = self.db.scalar("SELECT ufv FROM tipo_cambio WHERE fecha<=? AND ufv>0 ORDER BY fecha DESC LIMIT 1", (f,))
        return float(v) if v else 0.0
