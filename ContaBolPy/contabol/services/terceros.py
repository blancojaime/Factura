"""Clientes y proveedores."""
from __future__ import annotations

from ..sistema import ErrorNegocio
from ..util import r2


class TerceroService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def listar(self, clase: str | None = None, texto: str = "", solo_activos: bool = True) -> list[dict]:
        sql, p = "SELECT * FROM tercero WHERE 1=1", []
        if clase == "C":
            sql += " AND clase IN ('C','A')"
        elif clase == "P":
            sql += " AND clase IN ('P','A')"
        if solo_activos:
            sql += " AND activo=1"
        if texto:
            sql += " AND (nombre LIKE ? OR nit LIKE ? OR codigo LIKE ?)"
            p += [f"%{texto}%"] * 3
        return self.db.query(sql + " ORDER BY nombre", p)

    def obtener(self, tid: int) -> dict | None:
        return self.db.one("SELECT * FROM tercero WHERE id=?", (tid,))

    def guardar(self, d: dict) -> int:
        self.ctx.requiere("COM.TERCEROS")
        nombre = (d.get("nombre") or "").strip()
        if not nombre:
            raise ErrorNegocio("El nombre es obligatorio.")
        clase = d.get("clase") or "C"
        tid = d.get("id")
        codigo = (d.get("codigo") or "").strip()
        if not codigo:
            pref = "CLI" if clase == "C" else "PRV" if clase == "P" else "TER"
            n = int(self.db.scalar("SELECT COUNT(*) FROM tercero", (), 0)) + 1
            codigo = f"{pref}{n:04d}"
            while self.db.scalar("SELECT COUNT(*) FROM tercero WHERE codigo=?", (codigo,)):
                n += 1
                codigo = f"{pref}{n:04d}"
        if self.db.scalar("SELECT COUNT(*) FROM tercero WHERE codigo=? AND id<>?", (codigo, tid or 0)):
            raise ErrorNegocio(f"Ya existe el código {codigo}.")
        vals = dict(clase=clase, codigo=codigo, nombre=nombre, nit=(d.get("nit") or "").strip(), direccion=d.get("direccion"),
                    telefono=d.get("telefono"), email=d.get("email"), contacto=d.get("contacto"),
                    limite_credito=float(d.get("limite_credito") or 0), dias_credito=int(d.get("dias_credito") or 0),
                    activo=1 if d.get("activo", True) else 0)
        if tid:
            self.db.update("tercero", tid, **vals)
        else:
            tid = self.db.insert("tercero", **vals)
        return tid

    def eliminar(self, tid: int) -> None:
        self.ctx.requiere("COM.TERCEROS")
        uso = (self.db.scalar("SELECT COUNT(*) FROM venta WHERE tercero_id=?", (tid,), 0) + self.db.scalar("SELECT COUNT(*) FROM compra WHERE tercero_id=?", (tid,), 0)
               + self.db.scalar("SELECT COUNT(*) FROM cobro_pago WHERE tercero_id=?", (tid,), 0) + self.db.scalar("SELECT COUNT(*) FROM comp_det WHERE tercero_id=?", (tid,), 0))
        if uso:
            self.db.execute("UPDATE tercero SET activo=0 WHERE id=?", (tid,))
            raise ErrorNegocio("El registro tiene movimientos: se marcó como inactivo en lugar de eliminarse.")
        self.db.delete("tercero", tid)

    def saldo(self, tid: int, clase: str) -> float:
        tabla = "venta" if clase == "C" else "compra"
        return r2(self.db.scalar(f"SELECT COALESCE(SUM(saldo),0) FROM {tabla} WHERE tercero_id=? AND estado='V'", (tid,), 0.0))

    def saldos(self, clase: str) -> list[dict]:
        tabla = "venta" if clase == "C" else "compra"
        return self.db.query(
            f"SELECT t.id, t.codigo, t.nombre, t.nit, t.limite_credito, COALESCE(SUM(d.total),0) AS facturado, COALESCE(SUM(d.saldo),0) AS saldo, COUNT(d.id) AS documentos "
            f"FROM tercero t LEFT JOIN {tabla} d ON d.tercero_id=t.id AND d.estado='V' "
            f"WHERE t.clase IN (?, 'A') GROUP BY t.id HAVING ABS(COALESCE(SUM(d.saldo),0))>0.004 ORDER BY t.nombre", (clase,))
