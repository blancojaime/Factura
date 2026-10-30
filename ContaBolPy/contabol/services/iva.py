"""Libros de compras y ventas IVA (LCV), débito/crédito fiscal e IT."""
from __future__ import annotations

import re

from ..sistema import ErrorNegocio
from ..util import fin_de_mes, iso, r2, to_date


class IvaService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    def iva_pct(self, fecha=None) -> float:
        return self.ctx.normativa.num("IVA_PCT", fecha)

    def it_pct(self, fecha=None) -> float:
        return self.ctx.normativa.num("IT_PCT", fecha)

    def calcular(self, d: dict) -> dict:
        fecha = d.get("fecha")
        total = r2(d.get("importe_total") or 0)
        ns, ex, tc0, desc = (r2(d.get(k) or 0) for k in ("no_sujeto", "exento", "tasa_cero", "descuentos"))
        if min(total, ns, ex, tc0, desc) < 0:
            raise ErrorNegocio("Los importes no pueden ser negativos.")
        subtotal = r2(total - ns - ex - tc0)
        if subtotal < 0:
            raise ErrorNegocio("Los importes no sujetos/exentos superan el importe total.")
        base = r2(subtotal - desc)
        if base < 0:
            raise ErrorNegocio("El descuento supera el subtotal.")
        iva = r2(base * self.iva_pct(fecha) / 100.0)
        return {"importe_total": total, "no_sujeto": ns, "exento": ex, "tasa_cero": tc0, "descuentos": desc,
                "subtotal": subtotal, "base_iva": base, "iva": iva}

    # ------------------------------------------------------------- validación
    def _validar(self, d: dict, fid: int | None) -> None:
        libro = d.get("libro")
        if libro not in ("C", "V"):
            raise ErrorNegocio("Libro no válido.")
        self.ctx.requiere_fecha(d.get("fecha"))
        nit = (d.get("nit") or "").strip()
        estado = d.get("estado", "V")
        if estado == "V" and nit and not re.fullmatch(r"[0-9A-Za-z\-]{1,20}", nit):
            raise ErrorNegocio("NIT/CI no válido.")
        if not (d.get("nro_factura") or "").strip():
            raise ErrorNegocio("El número de factura es obligatorio.")
        if estado == "V" and libro == "C" and not nit:
            raise ErrorNegocio("El NIT del proveedor es obligatorio en el libro de compras.")
        dup = self.db.one(
            "SELECT id FROM factura WHERE libro=? AND estado='V' AND nro_factura=? AND COALESCE(nro_autorizacion,'')=? AND COALESCE(nit,'')=? AND id<>?",
            (libro, d["nro_factura"].strip(), (d.get("nro_autorizacion") or "").strip(), nit, fid or 0)) if estado == "V" else None
        if dup:
            raise ErrorNegocio(f"Ya está registrada la factura {d['nro_factura']} de NIT {nit or '(s/n)'} con la misma autorización.")

    # ---------------------------------------------------------------- registro
    def registrar(self, d: dict, *, interno: bool = False) -> int:
        ctx = self.ctx
        if not interno:
            ctx.requiere("IVA.REGISTRO")
        ctx.requiere_abierta()
        self._validar(d, None)
        estado = d.get("estado", "V")
        f = to_date(d["fecha"])
        if estado in ("A", "N"):
            c = {k: 0.0 for k in ("importe_total", "no_sujeto", "exento", "tasa_cero", "descuentos", "subtotal", "base_iva", "iva")}
        else:
            c = self.calcular(d)
        with self.db.tx():
            comp_id = d.get("comprobante_id")
            if estado == "V" and d.get("generar_asiento") and not comp_id:
                comp_id = self._asiento(d, c)
            fid = self.db.insert(
                "factura", libro=d["libro"], fecha=f.isoformat(), nit=(d.get("nit") or "").strip(), razon_social=(d.get("razon_social") or "").strip(),
                nro_factura=d["nro_factura"].strip(), nro_autorizacion=(d.get("nro_autorizacion") or "").strip(), cod_control=d.get("cod_control"),
                dui=d.get("dui"), tipo_compra=int(d.get("tipo_compra") or 1), estado=estado, tercero_id=d.get("tercero_id"),
                comprobante_id=comp_id, origen=d.get("origen", "MANUAL"), origen_id=d.get("origen_id"), periodo=f"{f.year}{f.month:02d}",
                modalidad=d.get("modalidad"), **c)
        ctx.auditar("IVA", "REGISTRAR_FACTURA", f"{'Venta' if d['libro'] == 'V' else 'Compra'} {d['nro_factura']} Bs {c['importe_total']:,.2f}")
        return fid

    def _asiento(self, d: dict, c: dict) -> int:
        ctx = self.ctx
        contra = d.get("contra_cuenta_id")
        cuenta = d.get("cuenta_id")
        if not contra or not cuenta:
            raise ErrorNegocio("Indique la cuenta de contrapartida (caja/banco/cuentas por cobrar o pagar) y la cuenta de ingreso/gasto.")
        glosa = d.get("glosa") or (f"Venta factura {d['nro_factura']} - {d.get('razon_social','')}" if d["libro"] == "V"
                                   else f"Compra factura {d['nro_factura']} - {d.get('razon_social','')}")
        tid = d.get("tercero_id")
        if d["libro"] == "V":
            lineas = [(contra, c["importe_total"], 0, None, tid), (ctx.cuenta_param("CTA_DF_IVA"), 0, c["iva"], None),
                      (cuenta, 0, r2(c["importe_total"] - c["iva"]), None)]
            it = self.calcular_it(c["importe_total"], d["fecha"])
            if it > 0:
                lineas += [(ctx.cuenta_param("CTA_IT_GASTO"), it, 0), (ctx.cuenta_param("CTA_IT_PAGAR"), 0, it)]
            tipo = "I"
        else:
            lineas = [(cuenta, r2(c["importe_total"] - c["iva"]), 0), (ctx.cuenta_param("CTA_CF_IVA"), c["iva"], 0),
                      (contra, 0, c["importe_total"], None, tid)]
            tipo = "E"
        lineas = [l for l in lineas if (l[1] or l[2])]
        return ctx.vouchers.asiento(d["fecha"], glosa, lineas, "MANUAL", None, tipo=tipo, a_nombre=d.get("razon_social"), nro_doc=d["nro_factura"])

    def calcular_it(self, total: float, fecha) -> float:
        return r2(total * self.it_pct(fecha) / 100.0)

    def anular(self, fid: int) -> None:
        ctx = self.ctx
        ctx.requiere("IVA.REGISTRO")
        ctx.requiere_abierta()
        f = self.obtener(fid)
        if not f:
            raise ErrorNegocio("Factura inexistente.")
        if f["origen"] != "MANUAL":
            raise ErrorNegocio("Esta factura pertenece a una nota de venta/compra; anule el documento de origen.")
        with self.db.tx():
            if f["comprobante_id"]:
                ctx.vouchers.anular(f["comprobante_id"], interno=True)
            self.db.execute("UPDATE factura SET estado='A', importe_total=0, no_sujeto=0, exento=0, tasa_cero=0, subtotal=0, descuentos=0, "
                            "base_iva=0, iva=0 WHERE id=?", (fid,))
        ctx.auditar("IVA", "ANULAR_FACTURA", f"{f['nro_factura']}")

    def obtener(self, fid: int) -> dict | None:
        return self.db.one("SELECT * FROM factura WHERE id=?", (fid,))

    def listar(self, libro: str, anio: int | None = None, mes: int | None = None, estado: str | None = None) -> list[dict]:
        sql, p = "SELECT * FROM factura WHERE libro=?", [libro]
        if anio and mes:
            sql += " AND periodo=?"
            p.append(f"{anio}{mes:02d}")
        elif anio:
            sql += " AND periodo LIKE ?"
            p.append(f"{anio}%")
        if estado:
            sql += " AND estado=?"
            p.append(estado)
        return self.db.query(sql + " ORDER BY fecha, nro_factura", p)

    def desde_documento(self, libro: str, fecha, tercero: dict, nro: str, autorizacion: str, total: float, descuentos: float,
                        comprobante_id: int | None, origen: str, origen_id: int) -> int:
        """Registra la factura de una nota de venta/compra (el asiento lo genera el módulo comercial)."""
        return self.registrar({"libro": libro, "fecha": fecha, "nit": tercero.get("nit"), "razon_social": tercero["nombre"], "nro_factura": nro,
                               "nro_autorizacion": autorizacion, "importe_total": total, "descuentos": 0, "tercero_id": tercero["id"],
                               "comprobante_id": comprobante_id, "origen": origen, "origen_id": origen_id}, interno=True)

    # ------------------------------------------------------------ liquidación
    def resumen_mensual(self, anio: int, mes: int) -> dict:
        """DF, CF, saldo de crédito arrastrado (con mantenimiento de valor por UFV) e IT del mes."""
        ctx = self.ctx
        carry = 0.0
        ufv_prev = ctx.tc.ufv(ctx.inicio)
        detalle: dict = {}
        for m in range(1, mes + 1):
            per = f"{anio}{m:02d}"
            df = self.db.scalar("SELECT COALESCE(SUM(iva),0) FROM factura WHERE libro='V' AND estado='V' AND periodo=?", (per,), 0.0)
            cf = self.db.scalar("SELECT COALESCE(SUM(iva),0) FROM factura WHERE libro='C' AND estado='V' AND periodo=?", (per,), 0.0)
            ufv_m = ctx.tc.ufv(fin_de_mes(anio, m))
            ant = carry
            mant = r2(ant * (ufv_m / ufv_prev - 1)) if ant > 0 and ufv_prev > 0 and ufv_m > 0 else 0.0
            credito = r2(cf + ant + mant)
            neto = r2(df - credito)
            carry = r2(-neto) if neto < 0 else 0.0
            detalle = {"anio": anio, "mes": m, "debito_fiscal": r2(df), "credito_fiscal": r2(cf), "saldo_anterior": r2(ant),
                       "mant_valor": mant, "credito_total": credito, "iva_a_pagar": neto if neto > 0 else 0.0, "saldo_favor": carry}
            if ufv_m > 0:
                ufv_prev = ufv_m
        it_dev = self.db.scalar(
            "SELECT COALESCE(SUM(d.haber_bs - d.debe_bs),0) FROM comp_det d JOIN comprobante c ON c.id=d.comprobante_id "
            "WHERE c.estado='V' AND d.cuenta_id=? AND c.mes=? AND c.origen<>'CIERRE'", (ctx.cuenta_param("CTA_IT_PAGAR"), mes), 0.0)
        per = f"{anio}{mes:02d}"
        detalle["it_devengado"] = r2(it_dev)
        detalle["ventas_facturadas"] = r2(self.db.scalar("SELECT COALESCE(SUM(importe_total),0) FROM factura WHERE libro='V' AND estado='V' AND periodo=?", (per,), 0.0))
        detalle["compras_facturadas"] = r2(self.db.scalar("SELECT COALESCE(SUM(importe_total),0) FROM factura WHERE libro='C' AND estado='V' AND periodo=?", (per,), 0.0))
        return detalle

    def liquidar(self, anio: int, mes: int, cuenta_pago_id: int | None = None) -> int | None:
        """Asiento mensual: salda el débito fiscal con el crédito fiscal disponible y registra el pago de la diferencia."""
        ctx = self.ctx
        ctx.requiere("IVA.REGISTRO")
        r = self.resumen_mensual(anio, mes)
        df = r["debito_fiscal"]
        if df == 0:
            raise ErrorNegocio("No hay débito fiscal en el período para liquidar.")
        disponible = r2(r["credito_fiscal"] + r["saldo_anterior"])
        pagar = r2(max(0.0, df - disponible))
        usa_cf = r2(df - pagar)
        lineas = [(ctx.cuenta_param("CTA_DF_IVA"), df, 0)]
        if usa_cf > 0:
            lineas.append((ctx.cuenta_param("CTA_CF_IVA"), 0, usa_cf))
        if pagar > 0:
            lineas.append((cuenta_pago_id or ctx.cuenta_param("CTA_CAJA"), 0, pagar))
        return ctx.vouchers.asiento(fin_de_mes(anio, mes), f"Liquidación IVA {mes:02d}/{anio}: DF {df:,.2f} - CF {disponible:,.2f}",
                                    lineas, "AJUSTE", tipo="E")
