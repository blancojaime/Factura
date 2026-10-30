"""Ajustes de fin de gestión, cierre, reapertura y apertura de una nueva gestión con traslado de saldos."""
from __future__ import annotations

import os
import shutil
from datetime import date, datetime, timedelta

from ..db import Database
from ..sistema import ErrorNegocio
from ..util import iso, r2, to_date


class GestionService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    # ---------------------------------------------------------------- ajustes
    def ajuste_inflacion(self, fecha, registrar: bool = False) -> dict:
        """Ajuste por inflación y tenencia de bienes con UFV (Norma Contable N° 3). Suspendido contablemente desde 2020: se habilita por decisión de la empresa."""
        ctx = self.ctx
        f = ctx.requiere_fecha(fecha)
        ufv_fin = ctx.tc.ufv(f)
        ufv_ini = ctx.tc.ufv(ctx.inicio - timedelta(days=1)) or ctx.tc.ufv(ctx.inicio)
        if ufv_fin <= 0 or ufv_ini <= 0:
            raise ErrorNegocio("Se necesita la UFV al inicio de la gestión y a la fecha de ajuste (Tipos de cambio y UFV).")
        fac = ufv_fin / ufv_ini - 1
        saldos = ctx.libros.saldos_a(f, incluir_cierre=False)
        filas = []
        for c in ctx.cuentas.listar(solo_movimiento=True):
            if not c["ajustable"]:
                continue
            s = saldos.get(c["id"], 0.0)
            if abs(s) < 0.005:
                continue
            aj = r2(s * fac)
            if abs(aj) >= 0.005:
                filas.append({"cuenta_id": c["id"], "codigo": c["codigo"], "nombre": c["nombre"], "saldo": r2(s), "ajuste": aj})
        neto = r2(sum(x["ajuste"] for x in filas))
        res = {"fecha": f.isoformat(), "ufv_inicial": ufv_ini, "ufv_final": ufv_fin, "factor": fac, "filas": filas, "neto": neto, "comprobante_id": None}
        if registrar and filas:
            ctx.requiere("CONT.CIERRE")
            ctx.requiere_abierta()
            lineas = [(x["cuenta_id"], x["ajuste"], 0) if x["ajuste"] > 0 else (x["cuenta_id"], 0, -x["ajuste"]) for x in filas]
            # contrapartida: patrimonio con ajuste por inflación y resultado (AITB)
            lineas.append((ctx.cuenta_param("CTA_AJUSTE_ING"), 0, neto) if neto > 0 else (ctx.cuenta_param("CTA_AJUSTE_EGR"), -neto, 0))
            res["comprobante_id"] = ctx.vouchers.asiento(f, f"Ajuste por inflación y tenencia de bienes al {f:%d/%m/%Y}", lineas, "AJUSTE", None, tipo="AJ")
        return res

    def diferencia_cambio(self, fecha, tc_final: float, registrar: bool = False) -> dict:
        ctx = self.ctx
        f = ctx.requiere_fecha(fecha)
        if tc_final <= 0:
            raise ErrorNegocio("Indique el tipo de cambio final.")
        filas = []
        for c in ctx.cuentas.listar(solo_movimiento=True):
            if not c["moneda_extranjera"]:
                continue
            r = ctx.db.one("SELECT COALESCE(SUM(d.debe_bs-d.haber_bs),0) AS bs, COALESCE(SUM(d.debe_usd-d.haber_usd),0) AS usd FROM comp_det d "
                           "JOIN comprobante k ON k.id=d.comprobante_id WHERE k.estado='V' AND k.origen<>'CIERRE' AND d.cuenta_id=? AND k.fecha<=?", (c["id"], f.isoformat()))
            if abs(r["usd"]) < 0.005 and abs(r["bs"]) < 0.005:
                continue
            nuevo = r2(r["usd"] * tc_final)
            dif = r2(nuevo - r["bs"])
            if abs(dif) >= 0.005:
                filas.append({"cuenta_id": c["id"], "codigo": c["codigo"], "nombre": c["nombre"], "saldo_usd": r2(r["usd"]), "saldo_bs": r2(r["bs"]),
                              "actualizado": nuevo, "ajuste": dif, "naturaleza": c["naturaleza"]})
        neto = r2(sum(x["ajuste"] for x in filas))  # positivo = más activo (ingreso) / menos pasivo
        res = {"fecha": f.isoformat(), "tc_final": tc_final, "filas": filas, "neto": neto, "comprobante_id": None}
        if registrar and filas:
            ctx.requiere("CONT.CIERRE")
            ctx.requiere_abierta()
            lineas = [(x["cuenta_id"], x["ajuste"], 0) if x["ajuste"] > 0 else (x["cuenta_id"], 0, -x["ajuste"]) for x in filas]
            lineas.append((ctx.cuenta_param("CTA_DIFCAMBIO_ING"), 0, neto) if neto > 0 else (ctx.cuenta_param("CTA_DIFCAMBIO_EGR"), -neto, 0))
            # el ajuste se registra solo en bolivianos; los dólares no cambian
            cid = ctx.vouchers.crear({"tipo": "AJ", "fecha": f, "glosa": f"Diferencia de cambio al {f:%d/%m/%Y} (T.C. {tc_final})", "origen": "AJUSTE",
                                      "lineas": [{"cuenta_id": a if isinstance(a, int) else None, "debe": d, "haber": h, "debe_usd_fijo": 0.0, "haber_usd_fijo": 0.0}
                                                 for a, d, h in lineas]}, interno=True)
            res["comprobante_id"] = cid
        return res

    # ------------------------------------------------------------------ cierre
    def generar_cierre(self, fecha=None) -> int:
        """Asiento de cierre: salda ingresos y gastos contra el resultado de la gestión."""
        ctx = self.ctx
        ctx.requiere("CONT.CIERRE")
        ctx.requiere_abierta()
        f = ctx.requiere_fecha(fecha or ctx.fin)
        if ctx.db.scalar("SELECT COUNT(*) FROM comprobante WHERE origen='CIERRE' AND estado='V'", (), 0):
            raise ErrorNegocio("Ya existe un asiento de cierre vigente; anúlelo para generarlo de nuevo.")
        mov = ctx.libros.movimientos(None, f, "BS", incluir_cierre=False)
        lineas, total = [], 0.0
        for c in ctx.cuentas.listar(solo_movimiento=True):
            if c["tipo"] not in ("I", "G") or c["id"] not in mov:
                continue
            d, h = mov[c["id"]]
            s = r2(d - h)
            if abs(s) < 0.005:
                continue
            lineas.append((c["id"], 0, s) if s > 0 else (c["id"], -s, 0))
            total += s
        if not lineas:
            raise ErrorNegocio("No hay saldos de ingresos o gastos para cerrar.")
        total = r2(total)  # positivo = pérdida
        rg = ctx.cuenta_param("CTA_RESULTADO")
        lineas.append((rg, total, 0) if total > 0 else (rg, 0, -total))
        return ctx.vouchers.asiento(f, f"Cierre de la gestión {ctx.gestion['anio']}: {'pérdida' if total > 0 else 'utilidad'} Bs {abs(total):,.2f}", lineas, "CIERRE", None, tipo="CI")

    def cerrar_gestion(self) -> None:
        ctx = self.ctx
        ctx.requiere("CONT.CIERRE")
        ctx.requiere_abierta()
        ctx.sistema.db.execute("UPDATE gestion SET estado='C', cerrada_en=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), ctx.gestion["id"]))
        ctx.gestion["estado"] = "C"
        ctx.auditar("Gestión", "CERRAR", str(ctx.gestion["anio"]))

    def reabrir_gestion(self) -> None:
        ctx = self.ctx
        if not ctx.usuario["es_admin"]:
            raise ErrorNegocio("Solo el administrador puede reabrir una gestión.")
        siguiente = ctx.sistema.db.scalar("SELECT COUNT(*) FROM gestion WHERE empresa_id=? AND anio>?", (ctx.empresa["id"], ctx.gestion["anio"]), 0)
        if siguiente:
            raise ErrorNegocio("Existe una gestión posterior abierta con saldos trasladados; reabrir esta gestión podría desincronizarla.")
        ctx.sistema.db.execute("UPDATE gestion SET estado='A', cerrada_en=NULL WHERE id=?", (ctx.gestion["id"],))
        ctx.gestion["estado"] = "A"
        ctx.auditar("Gestión", "REABRIR", str(ctx.gestion["anio"]))

    # --------------------------------------------------------------- apertura
    def abrir_nueva_gestion(self, anio: int | None = None) -> int:
        """Crea la gestión siguiente: copia plan, parámetros y catálogos; asiento de apertura con los saldos finales; existencias y cuentas corrientes."""
        ctx = self.ctx
        ctx.requiere("ADM.GESTIONES")
        sis = ctx.sistema
        anio = anio or ctx.gestion["anio"] + 1
        if sis.db.scalar("SELECT COUNT(*) FROM gestion WHERE empresa_id=? AND anio=?", (ctx.empresa["id"], anio), 0):
            raise ErrorNegocio(f"La gestión {anio} ya existe.")
        gid = sis.nueva_gestion_vacia(ctx.empresa["id"], anio, bool(ctx.gestion["correlativo_mensual"]), 1)
        g = sis.gestion(gid)
        nuevo = Database(sis.ruta_gestion(g))
        try:
            with nuevo.tx():
                self._copiar_base(nuevo)
                self._asiento_apertura(nuevo, g)
                self._trasladar_inventario(nuevo, g)
                self._trasladar_cuentas_corrientes(nuevo, g)
                self._trasladar_activos_y_personal(nuevo)
        except Exception:
            nuevo.close()
            sis.db.execute("DELETE FROM gestion WHERE id=?", (gid,))
            try:
                os.remove(sis.ruta_gestion(g))
            except OSError:
                pass
            raise
        nuevo.close()
        ctx.auditar("Gestión", "ABRIR_NUEVA", str(anio))
        return gid

    def _copiar_base(self, nuevo: Database) -> None:
        """Reemplaza los catálogos sembrados del nuevo archivo con los de la gestión actual (conservando los ids)."""
        for t in ("activo_grupo", "centro_costo", "almacen", "unidad", "grupo_item", "vendedor", "cuenta", "parametro", "tercero"):
            nuevo.execute(f"DELETE FROM {t}")
        nuevo.execute("PRAGMA foreign_keys=OFF")
        for t in ("parametro", "activo_grupo", "centro_costo", "almacen", "unidad", "grupo_item", "vendedor", "tercero"):
            self._copy_rows(t, nuevo)
        filas = self.db.query("SELECT * FROM cuenta ORDER BY nivel, codigo")
        for r in filas:
            cols = ", ".join(r.keys())
            nuevo.execute(f"INSERT INTO cuenta ({cols}) VALUES ({', '.join('?' for _ in r)})", list(r.values()))
        nuevo.execute("PRAGMA foreign_keys=ON")
        nuevo.execute("UPDATE parametro SET valor=? WHERE clave='EMP_GESTION'", (str(self.ctx.gestion["anio"] + 1),))

    def _copy_rows(self, tabla: str, nuevo: Database) -> None:
        for r in self.db.query(f"SELECT * FROM {tabla}"):
            cols = ", ".join(f'"{k}"' for k in r.keys())
            nuevo.execute(f'INSERT INTO "{tabla}" ({cols}) VALUES ({", ".join("?" for _ in r)})', list(r.values()))

    def _asiento_apertura(self, nuevo: Database, g: dict) -> None:
        ctx = self.ctx
        mov = ctx.libros.movimientos(None, ctx.fin, "BS", incluir_cierre=True)
        movu = ctx.libros.movimientos(None, ctx.fin, "USD", incluir_cierre=True)
        cuentas = {c["id"]: c for c in ctx.cuentas.listar(solo_movimiento=True)}
        lineas, resultado = [], 0.0
        for cid, (d, h) in mov.items():
            c = cuentas.get(cid)
            if not c:
                continue
            s = r2(d - h)
            if c["tipo"] in ("I", "G"):
                resultado += s  # pérdida positiva si no se hizo el cierre
                continue
            if c["tipo"] == "O" or abs(s) < 0.005:
                continue
            du, hu = movu.get(cid, (0.0, 0.0))
            su = r2(du - hu)
            lineas.append((cid, s, su))
        # si hay cuenta de resultado de la gestión con saldo (cierre ya generado) pasa a resultados acumulados
        rg = ctx.cuenta_por_codigo(ctx.param("CTA_RESULTADO"))
        ra = ctx.cuenta_por_codigo(ctx.param("CTA_RESULT_ACUM"))
        movs: dict[int, list[float]] = {}
        for cid, s, su in lineas:
            t = movs.setdefault(cid, [0.0, 0.0])
            t[0] += s
            t[1] += su
        if rg and rg["id"] in movs:
            x = movs.pop(rg["id"])
            t = movs.setdefault(ra["id"], [0.0, 0.0])
            t[0] += x[0]
            t[1] += x[1]
        if abs(resultado) >= 0.005:  # cierre no generado: trasladar el resultado directamente
            t = movs.setdefault(ra["id"], [0.0, 0.0])
            t[0] += resultado
            t[1] += resultado / ctx.tc.dolar(ctx.fin)
        total_d = total_h = 0.0
        det = []
        for cid, (s, su) in movs.items():
            if abs(s) < 0.005:
                continue
            if s > 0:
                det.append((cid, r2(s), 0.0, r2(su) if su > 0 else 0.0, 0.0))
                total_d += s
            else:
                det.append((cid, 0.0, r2(-s), 0.0, r2(-su) if su < 0 else 0.0))
                total_h += -s
        if not det:
            return
        if abs(total_d - total_h) > 0.05:
            raise ErrorNegocio(f"El balance de cierre no cuadra (diferencia {abs(total_d - total_h):,.2f}); revise los comprobantes antes de abrir la nueva gestión.")
        inicio = to_date(g["fecha_inicio"])
        cid_new = nuevo.insert("comprobante", tipo="AP", numero=1, mes=inicio.month, fecha=inicio.isoformat(), glosa=f"Asiento de apertura gestión {g['anio']}",
                               moneda="BS", tc=ctx.tc.dolar(ctx.fin), estado="V", origen="APERTURA", debe_bs=r2(total_d), haber_bs=r2(total_h),
                               creado_por=ctx.usuario["id"], creado_en=datetime.now().isoformat(timespec="seconds"))
        for n, (cid, d, h, du, hu) in enumerate(det, 1):
            nuevo.insert("comp_det", comprobante_id=cid_new, linea=n, cuenta_id=cid, glosa="Saldo inicial", debe_bs=d, haber_bs=h, debe_usd=du, haber_usd=hu)

    def _trasladar_inventario(self, nuevo: Database, g: dict) -> None:
        ctx = self.ctx
        inicio = to_date(g["fecha_inicio"]).isoformat()
        for it in ctx.db.query("SELECT * FROM item"):
            cols = ", ".join(f'"{k}"' for k in it.keys() if k not in ("stock",))
            vals = [v for k, v in it.items() if k != "stock"]
            nuevo.execute(f"INSERT INTO item ({cols}, stock) VALUES ({', '.join('?' for _ in vals)}, 0)", vals)
        numero = 0
        for alm in ctx.db.query("SELECT * FROM almacen"):
            filas = ctx.db.query("SELECT s.item_id, s.cantidad, i.costo_prom FROM item_stock s JOIN item i ON i.id=s.item_id WHERE s.almacen_id=? AND s.cantidad>0", (alm["id"],))
            if not filas:
                continue
            numero += 1
            mid = nuevo.insert("mov_inv", tipo="INI", numero=numero, fecha=inicio, almacen_id=alm["id"], glosa="Existencias iniciales (traslado de gestión)")
            for f in filas:
                tot = r2(f["cantidad"] * f["costo_prom"])
                nuevo.insert("mov_inv_det", mov_id=mid, item_id=f["item_id"], cantidad=f["cantidad"], costo_unit=f["costo_prom"], costo_total=tot)
                nuevo.execute("INSERT INTO item_stock (item_id, almacen_id, cantidad) VALUES (?,?,?)", (f["item_id"], alm["id"], f["cantidad"]))
                nuevo.execute("UPDATE item SET stock=ROUND(stock+?,6), costo_prom=? WHERE id=?", (f["cantidad"], f["costo_prom"], f["item_id"]))
                st = nuevo.scalar("SELECT stock FROM item WHERE id=?", (f["item_id"],))
                nuevo.insert("kardex", item_id=f["item_id"], almacen_id=alm["id"], fecha=inicio, mov_id=mid, tipo="INI", detalle="Existencia inicial",
                             ent_cant=f["cantidad"], sal_cant=0, costo_unit=f["costo_prom"], ent_val=tot, sal_val=0, saldo_cant=st,
                             saldo_val=r2(st * f["costo_prom"]), costo_prom=f["costo_prom"])
        for l in ctx.db.query("SELECT * FROM item_lote WHERE cantidad>0"):
            nuevo.insert("item_lote", item_id=l["item_id"], almacen_id=l["almacen_id"], lote=l["lote"], vencimiento=l["vencimiento"], cantidad=l["cantidad"])

    def _trasladar_cuentas_corrientes(self, nuevo: Database, g: dict) -> None:
        ctx = self.ctx
        inicio = to_date(g["fecha_inicio"]).isoformat()
        for tabla in ("venta", "compra"):
            n = 0
            for d in ctx.db.query(f"SELECT * FROM {tabla} WHERE estado='V' AND saldo>0.004"):
                n += 1
                base = dict(numero=n, fecha=inicio, tercero_id=d["tercero_id"], tipo_pago="CRE", con_factura=0, subtotal=d["saldo"], total=d["saldo"],
                            saldo=d["saldo"], vencimiento=d["vencimiento"], glosa=f"Saldo inicial documento {d['numero']} de {d['fecha']}", estado="V")
                nuevo.insert(tabla, **base)

    def _trasladar_activos_y_personal(self, nuevo: Database) -> None:
        ctx = self.ctx
        for t in ("empleado",):
            self._copy_rows(t, nuevo)
        for a in ctx.db.query("SELECT * FROM activo WHERE estado='A'"):
            a = {k: v for k, v in a.items() if k not in ("id", "comprobante_id")}
            cols = ", ".join(f'"{k}"' for k in a.keys())
            nuevo.execute(f"INSERT INTO activo ({cols}) VALUES ({', '.join('?' for _ in a)})", list(a.values()))
        nuevo.execute("UPDATE activo SET ufv_ult=ufv_ult")
