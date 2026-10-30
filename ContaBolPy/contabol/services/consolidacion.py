"""Consolidación de empresas y gestiones por código de cuenta."""
from __future__ import annotations

from ..db import Database
from ..sistema import ErrorNegocio, Sistema
from ..util import iso, r2


class ConsolidacionService:
    def __init__(self, sis: Sistema, usuario: dict):
        self.sis = sis
        self.usuario = usuario
        if not usuario["es_admin"]:
            raise ErrorNegocio("La consolidación requiere perfil de administrador.")

    def disponibles(self) -> list[dict]:
        return self.sis.db.query("SELECT g.id AS gestion_id, e.id AS empresa_id, e.codigo, e.razon_social, g.anio FROM gestion g JOIN empresa e ON e.id=g.empresa_id "
                                 "ORDER BY e.razon_social, g.anio")

    def balance(self, gestion_ids: list[int], desde, hasta, nivel: int = 5, moneda: str = "BS") -> list[dict]:
        if not gestion_ids:
            raise ErrorNegocio("Seleccione al menos una gestión.")
        cd, ch = ("debe_usd", "haber_usd") if moneda == "USD" else ("debe_bs", "haber_bs")
        total: dict[str, dict] = {}
        for gid in gestion_ids:
            g = self.sis.gestion(gid)
            db = Database(self.sis.ruta_gestion(g))
            try:
                plan = {c["id"]: c for c in db.query("SELECT * FROM cuenta")}
                for r in db.query(f"SELECT d.cuenta_id, SUM(d.{cd}) AS d, SUM(d.{ch}) AS h FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id "
                                  "WHERE c.estado='V' AND c.origen<>'CIERRE' AND c.fecha BETWEEN ? AND ? GROUP BY d.cuenta_id", (iso(desde), iso(hasta))):
                    c = plan[r["cuenta_id"]]
                    partes = c["codigo"].split(".")
                    for n in range(1, len(partes) + 1):
                        cod = ".".join(partes[:n])
                        nom = next((x["nombre"] for x in plan.values() if x["codigo"] == cod), cod)
                        t = total.setdefault(cod, {"codigo": cod, "nombre": nom, "nivel": n, "debe": 0.0, "haber": 0.0})
                        t["debe"] += r["d"] or 0.0
                        t["haber"] += r["h"] or 0.0
            finally:
                db.close()
        filas = []
        for cod in sorted(total):
            t = total[cod]
            if t["nivel"] > nivel:
                continue
            s = r2(t["debe"] - t["haber"])
            filas.append({"codigo": cod, "nombre": t["nombre"], "nivel": t["nivel"], "debe": r2(t["debe"]), "haber": r2(t["haber"]),
                          "saldo_d": s if s > 0 else 0.0, "saldo_h": -s if s < 0 else 0.0})
        return filas
