"""Plan de cuentas."""
from __future__ import annotations

import csv
import re

from ..sistema import ErrorNegocio
from ..util import r2

TIPOS = {"A": "Activo", "P": "Pasivo", "T": "Patrimonio", "I": "Ingresos", "G": "Costos y gastos", "O": "Cuentas de orden"}
FLUJOS = ["EFECTIVO", "COBROS", "PAGOS_PROV", "PAGOS_PERS", "IMPUESTOS", "OTROS_OP", "INV", "FIN", "NOCASH", "TC", "NA"]


class CuentaService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def listar(self, solo_movimiento: bool = False, texto: str = "") -> list[dict]:
        sql = "SELECT * FROM cuenta WHERE activa=1"
        p: list = []
        if solo_movimiento:
            sql += " AND es_movimiento=1"
        if texto:
            sql += " AND (codigo LIKE ? OR nombre LIKE ?)"
            p += [f"%{texto}%", f"%{texto}%"]
        return self.db.query(sql + " ORDER BY codigo", p)

    def obtener(self, cid: int) -> dict | None:
        return self.db.one("SELECT * FROM cuenta WHERE id=?", (cid,))

    def por_codigo(self, codigo: str) -> dict | None:
        return self.db.one("SELECT * FROM cuenta WHERE codigo=?", (codigo.strip(),))

    def hijos(self, cid: int) -> list[dict]:
        return self.db.query("SELECT * FROM cuenta WHERE padre_id=? ORDER BY codigo", (cid,))

    def tiene_movimientos(self, cid: int) -> bool:
        return bool(self.db.scalar("SELECT COUNT(*) FROM comp_det WHERE cuenta_id=?", (cid,), 0))

    def guardar(self, d: dict) -> int:
        self.ctx.requiere("CONT.PLAN")
        self.ctx.requiere_abierta()
        codigo = (d.get("codigo") or "").strip()
        nombre = (d.get("nombre") or "").strip()
        if not re.fullmatch(r"\d+(\.\d+)*", codigo):
            raise ErrorNegocio("El código debe tener la forma 1.1.1.01.001 (números separados por punto).")
        if not nombre:
            raise ErrorNegocio("El nombre de la cuenta es obligatorio.")
        nivel = codigo.count(".") + 1
        padre_cod = ".".join(codigo.split(".")[:-1])
        padre = self.por_codigo(padre_cod) if nivel > 1 else None
        if nivel > 1 and not padre:
            raise ErrorNegocio(f"No existe la cuenta padre {padre_cod}. Créela primero.")
        if padre and padre["es_movimiento"] and self.tiene_movimientos(padre["id"]):
            raise ErrorNegocio(f"La cuenta {padre_cod} ya tiene movimientos y no puede tener subcuentas.")
        cid = d.get("id")
        existe = self.por_codigo(codigo)
        if existe and existe["id"] != cid:
            raise ErrorNegocio(f"Ya existe la cuenta {codigo}.")
        tipo = {"1": "A", "2": "P", "3": "T", "4": "I", "5": "G"}.get(codigo[0], "O")
        reg = 1 if d.get("regularizadora") else 0
        nat = {"A": "D", "P": "C", "T": "C", "I": "C", "G": "D"}.get(tipo, "D" if codigo[0] == "6" else "C")
        if reg:
            nat = "C" if nat == "D" else "D"
        es_mov = 1 if d.get("es_movimiento") else 0
        vals = dict(codigo=codigo, nombre=nombre, nivel=nivel, padre_id=padre["id"] if padre else None, es_movimiento=es_mov,
                    tipo=tipo, naturaleza=nat, moneda_extranjera=1 if d.get("moneda_extranjera") else 0,
                    ajustable=1 if d.get("ajustable") else 0, es_banco=1 if d.get("es_banco") else 0,
                    es_efectivo=1 if d.get("es_efectivo") else 0, regularizadora=reg,
                    corriente=1 if d.get("corriente", 1) else 0, flujo=d.get("flujo") or "NA",
                    patr_col=d.get("patr_col") or None, costo_tipo=d.get("costo_tipo") or None,
                    presupuestable=1 if d.get("presupuestable") else 0)
        with self.db.tx():
            if cid:
                actual = self.obtener(cid)
                if actual["codigo"] != codigo and self.tiene_movimientos(cid):
                    raise ErrorNegocio("No se puede cambiar el código de una cuenta con movimientos.")
                if es_mov and self.hijos(cid):
                    raise ErrorNegocio("Una cuenta con subcuentas no puede ser de movimiento.")
                if not es_mov and self.tiene_movimientos(cid):
                    raise ErrorNegocio("Una cuenta con movimientos debe ser de movimiento.")
                self.db.update("cuenta", cid, **vals)
            else:
                cid = self.db.insert("cuenta", **vals)
        self.ctx.auditar("Plan de cuentas", "GUARDAR_CUENTA", f"{codigo} {nombre}")
        return cid

    def eliminar(self, cid: int) -> None:
        self.ctx.requiere("CONT.PLAN")
        self.ctx.requiere_abierta()
        c = self.obtener(cid)
        if self.hijos(cid):
            raise ErrorNegocio("La cuenta tiene subcuentas.")
        if self.tiene_movimientos(cid):
            raise ErrorNegocio("La cuenta tiene movimientos contables y no puede eliminarse.")
        usada = [k for k, v in self.ctx.params().items() if k.startswith("CTA_") and v == c["codigo"]]
        if usada:
            raise ErrorNegocio(f"La cuenta está configurada en Parámetros ({', '.join(usada)}).")
        self.db.delete("cuenta", cid)
        self.ctx.auditar("Plan de cuentas", "ELIMINAR_CUENTA", c["codigo"])

    def siguiente_codigo(self, padre_codigo: str) -> str:
        hijos = self.db.query("SELECT codigo FROM cuenta WHERE codigo LIKE ? AND nivel=?", (padre_codigo + ".%", padre_codigo.count(".") + 2))
        if not hijos:
            return f"{padre_codigo}.01" if padre_codigo.count(".") < 3 else f"{padre_codigo}.001"
        ult = max(h["codigo"].split(".")[-1] for h in hijos)
        ancho = len(ult)
        return f"{padre_codigo}.{int(ult) + 1:0{ancho}d}"

    def importar_csv(self, ruta: str) -> int:
        """Importa 'codigo;nombre' (UTF-8). Crea las cuentas que no existan, respetando la jerarquía."""
        n = 0
        with open(ruta, newline="", encoding="utf-8-sig") as f:
            filas = sorted((r for r in csv.reader(f, delimiter=";") if len(r) >= 2 and r[0].strip()), key=lambda r: r[0])
        with self.db.tx():
            for r in filas:
                cod = r[0].strip()
                if self.por_codigo(cod):
                    continue
                nivel = cod.count(".") + 1
                self.guardar({"codigo": cod, "nombre": r[1].strip(), "es_movimiento": nivel >= 5})
                n += 1
        return n

    def exportar_csv(self, ruta: str) -> int:
        cuentas = self.listar()
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            for c in cuentas:
                w.writerow([c["codigo"], c["nombre"]])
        return len(cuentas)

    def saldo(self, cid: int, hasta=None, moneda: str = "BS") -> float:
        from ..util import iso
        col = ("debe_bs", "haber_bs") if moneda == "BS" else ("debe_usd", "haber_usd")
        sql = (f"SELECT COALESCE(SUM(d.{col[0]}),0) - COALESCE(SUM(d.{col[1]}),0) FROM comp_det d "
               "JOIN comprobante c ON c.id=d.comprobante_id WHERE c.estado='V' AND d.cuenta_id=?")
        p: list = [cid]
        if hasta:
            sql += " AND c.fecha<=?"
            p.append(iso(hasta))
        v = self.db.scalar(sql, p, 0.0)
        c = self.obtener(cid)
        return r2(v if c["naturaleza"] == "D" else -v)
