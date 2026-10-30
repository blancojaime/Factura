"""Datos de demostración: empresa comercial ficticia con un año de operaciones (para aprender el sistema y para el manual)."""
from __future__ import annotations

from datetime import date, timedelta

from .sistema import Sistema
from .util import fin_de_mes


class _Azar:
    """Generador congruencial determinista: produce SIEMPRE los mismos datos de demostración en cualquier versión de Python."""

    def __init__(self, semilla: int):
        self.e = semilla

    def _sig(self) -> float:
        self.e = (self.e * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (self.e >> 11) / float(1 << 53)

    def random(self) -> float:
        return self._sig()

    def randint(self, a: int, b: int) -> int:
        return a + int(self._sig() * (b - a + 1))

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self._sig()

    def choice(self, seq):
        return seq[int(self._sig() * len(seq))]

    def sample(self, seq, k: int):
        pool, out = list(seq), []
        for _ in range(k):
            out.append(pool.pop(int(self._sig() * len(pool))))
        return out


def crear_empresa_demo(sis: Sistema, usuario: dict, anio: int | None = None, codigo: str = "DEMO") -> tuple[int, int]:
    anio = anio or 2025
    rnd = _Azar(42)
    eid, gid = sis.crear_empresa({"codigo": codigo, "razon_social": "Distribuidora Andina S.R.L.", "nombre_comercial": "Andina", "nit": "1023456022",
                                  "direccion": "Av. 6 de Agosto Nº 2170, Edif. Torre Azul", "ciudad": "La Paz", "telefono": "2-2445566", "email": "contabilidad@andina.com.bo",
                                  "actividad": "Venta al por mayor y menor de abarrotes y productos de consumo masivo", "rep_legal": "María Fernanda Quispe Mamani",
                                  "matricula": "00134562"}, anio, usuario, True)
    c = sis.abrir_contexto(usuario, eid, gid)
    try:
        _poblar(c, anio, rnd)
    finally:
        c.cerrar()
    return eid, gid


def _poblar(c, anio: int, rnd: _Azar) -> None:
    cta = lambda cod: c.cuentas.por_codigo(cod)["id"]  # noqa: E731
    for m in range(1, 13):
        c.tc.guardar(date(anio, m, 1), 6.96, round(2.46 + 0.012 * m, 5))
    c.tc.guardar(date(anio, 12, 31), 6.96, round(2.46 + 0.012 * 13, 5))
    # capital, bancos y préstamo
    c.vouchers.crear({"tipo": "AP", "fecha": date(anio, 1, 2), "glosa": "Aporte inicial de socios", "lineas": [
        {"cuenta_id": cta("1.1.1.01.001"), "debe": 80000}, {"cuenta_id": cta("1.1.1.02.001"), "debe": 220000}, {"cuenta_id": cta("1.2.1.01.002"), "debe": 150000},
        {"cuenta_id": cta("3.1.1.01.001"), "haber": 450000}]}) if False else c.vouchers.crear({"tipo": "T", "fecha": date(anio, 1, 2), "glosa": "Aporte inicial de socios", "lineas": [
            {"cuenta_id": cta("1.1.1.01.001"), "debe": 120000}, {"cuenta_id": cta("1.1.1.02.001"), "debe": 600000}, {"cuenta_id": cta("1.2.1.01.002"), "debe": 150000},
            {"cuenta_id": cta("3.1.1.01.001"), "haber": 870000}]})
    c.vouchers.crear({"tipo": "I", "fecha": date(anio, 1, 10), "glosa": "Préstamo Banco Unión a 36 meses", "lineas": [
        {"cuenta_id": cta("1.1.1.02.001"), "debe": 120000}, {"cuenta_id": cta("2.2.1.01.001"), "haber": 120000}]})
    # catálogos
    inv = c.inventario
    alm = c.db.scalar("SELECT id FROM almacen LIMIT 1")
    un = {u["codigo"]: u["id"] for u in inv.catalogo("unidad")}
    grp = c.db.scalar("SELECT id FROM grupo_item LIMIT 1")
    productos = [("ARZ01", "Arroz grano largo 1 kg", 9.5, 7.2), ("AZU01", "Azúcar blanca 1 kg", 8.0, 6.1), ("ACE01", "Aceite vegetal 1 L", 14.0, 11.0), ("FID01", "Fideo tallarín 400 g", 5.5, 3.9),
                 ("HAR01", "Harina de trigo 1 kg", 6.8, 5.0), ("LEC01", "Leche entera 1 L", 7.5, 5.9), ("SAL01", "Sal yodada 1 kg", 3.0, 1.9), ("ATU01", "Atún en lata 170 g", 15.5, 11.8),
                 ("CAF01", "Café molido 250 g", 22.0, 16.5), ("GAL01", "Galletas surtidas 300 g", 6.5, 4.6), ("DET01", "Detergente en polvo 1 kg", 17.0, 12.8), ("JAB01", "Jabón de tocador x3", 9.0, 6.4)]
    items = {}
    for cod, nom, pv, cp in productos:
        pv = round(pv * 1.22, 2)
        items[cod] = (inv.guardar_item({"codigo": cod, "nombre": nom, "precio_venta": pv, "unidad_id": un["UN"], "grupo_id": grp, "stock_min": 800}), pv, cp)
    inv.guardar_item({"codigo": "FLE01", "nombre": "Servicio de flete y entrega", "precio_venta": 50, "es_servicio": True})
    inv.registrar({"tipo": "INI", "fecha": date(anio, 1, 2), "almacen_id": alm, "glosa": "Existencias iniciales", "generar_asiento": True,
                   "items": [{"item_id": i, "cantidad": 3000, "costo_unit": cp} for i, pv, cp in items.values()], "contra_cuenta": "3.1.1.01.001"})
    # terceros
    clientes = [c.terceros.guardar({"clase": "C", "nombre": n, "nit": nit, "limite_credito": lim, "dias_credito": 30, "telefono": "7" + str(rnd.randint(1000000, 9999999)),
                                    "direccion": "La Paz"}) for n, nit, lim in [("Minimarket El Ahorro", "1006341022", 150000), ("Supermercado Los Pinos S.A.", "1013274024", 400000), ("Tienda Doña Rosa", "3254412", 80000),
                                                                           ("Hotel Illimani S.R.L.", "1020143029", 200000), ("Restaurante Sabor Andino", "1018852029", 120000), ("Comercial Titicaca", "1007785023", 300000)]]
    provs = [c.terceros.guardar({"clase": "P", "nombre": n, "nit": nit, "dias_credito": 30}) for n, nit in [("Industrias Alimenticias del Sur S.A.", "1003220026"), ("Importadora Cóndor Ltda.", "1015537025"),
                                                                                                         ("Distribuciones Valle S.R.L.", "1022019020")]]
    c.vendedor = inv.guardar_catalogo("vendedor", {"codigo": "V01", "nombre": "Carlos Mendoza", "comision": 2})
    # operaciones mensuales
    nfac_v, nfac_c = 1000, 5000
    claves = list(items)
    for m in range(1, 13):
        for _ in range(4):  # compras
            d = date(anio, m, rnd.randint(3, 12))
            cods = rnd.sample(claves, 4)
            nfac_c += 1
            c.compras.registrar({"fecha": d, "tercero_id": rnd.choice(provs), "nro_factura": str(nfac_c), "nro_autorizacion": f"CUF{nfac_c}A9B7C", "tipo_pago": rnd.choice(["CON", "CRE"]),
                                 "items": [{"item_id": items[k][0], "cantidad": rnd.randint(1200, 2600), "precio": round(items[k][2] * rnd.uniform(1.0, 1.06), 2)} for k in cods]})
        for _ in range(26):  # ventas
            d = date(anio, m, rnd.randint(13, 28))
            cods = rnd.sample(claves, 3)
            nfac_v += 1
            cli = rnd.choice(clientes)
            try:
                c.ventas.registrar({"fecha": d, "tercero_id": cli, "nro_factura": str(nfac_v), "nro_autorizacion": f"CUF{nfac_v}X1Y2Z", "tipo_pago": rnd.choice(["CON", "CRE", "CRE"]),
                                    "vendedor_id": c.vendedor, "items": [{"item_id": items[k][0], "cantidad": rnd.randint(250, 800), "precio": items[k][1]} for k in cods]})
            except Exception:  # noqa: BLE001  (límite de crédito o stock): se omite la venta
                pass
        # cobros y pagos del mes
        for cli in clientes:
            pend = c.cobros.pendientes(cli, "CO")
            if pend and rnd.random() < 0.7:
                c.cobros.registrar({"clase": "CO", "fecha": fin_de_mes(anio, m) - timedelta(days=2), "tercero_id": cli, "monto": round(sum(p["saldo"] for p in pend[:6]), 2),
                                    "cuenta_id": cta("1.1.1.02.001"), "forma": "TRF"})
        for pv in provs:
            pend = c.cobros.pendientes(pv, "PA")
            if pend and rnd.random() < 0.7:
                c.cobros.registrar({"clase": "PA", "fecha": fin_de_mes(anio, m) - timedelta(days=1), "tercero_id": pv, "monto": round(sum(p["saldo"] for p in pend[:3]), 2), "cuenta_id": cta("1.1.1.02.001"), "forma": "CHQ"})
        # gastos del mes
        for cod, glosa, monto in (("5.3.1.02.004", "Alquiler del local", 6500), ("5.3.1.02.001", "Energía eléctrica", rnd.randint(850, 1150)), ("5.3.1.02.003", "Teléfono e internet", 640),
                                  ("5.4.1.01.001", "Publicidad y propaganda", rnd.randint(500, 1800)), ("5.4.1.01.003", "Fletes y transportes", rnd.randint(900, 2200))):
            c.vouchers.crear({"tipo": "E", "fecha": date(anio, m, 25), "glosa": f"{glosa} {m:02d}/{anio}", "a_nombre": "Proveedor de servicios", "lineas": [
                {"cuenta_id": cta(cod), "debe": monto}, {"cuenta_id": cta("1.1.1.02.001"), "haber": monto}]})
        c.vouchers.crear({"tipo": "E", "fecha": date(anio, m, 28), "glosa": f"Cuota préstamo bancario {m:02d}/{anio}", "lineas": [
            {"cuenta_id": cta("2.2.1.01.001"), "debe": 3000}, {"cuenta_id": cta("5.5.1.01.001"), "debe": 800}, {"cuenta_id": cta("1.1.1.02.001"), "haber": 3800}]})
    # activos fijos
    g = {x["nombre"]: x["id"] for x in c.activos.grupos()}
    for cod, nom, grupo, valor, fecha in (("VEH01", "Camioneta Toyota Hilux 2022", "Vehículos", 185000, date(anio, 1, 15)), ("COM01", "Computadora de escritorio Dell", "Equipo de Computación", 6800, date(anio, 2, 3)),
                                          ("COM02", "Laptop gerencia HP", "Equipo de Computación", 9200, date(anio, 2, 3)), ("MUE01", "Estanterías metálicas de almacén", "Muebles y Enseres", 14500, date(anio, 1, 20))):
        c.activos.guardar({"codigo": cod, "nombre": nom, "grupo_id": g[grupo], "fecha_alta": fecha, "valor_original": valor, "ubicacion": "Oficina central", "responsable": "Administración"})
    for m in range(1, 13):
        c.activos.depreciar(anio, m, True)
    # personal y planillas
    for cod, nom, ci, cargo, haber, ingreso in (("E001", "María Fernanda Quispe Mamani", "4521377 LP", "Gerente General", 9500, date(2017, 3, 1)), ("E002", "Carlos Mendoza Rojas", "6012884 LP", "Jefe de Ventas", 6200, date(2019, 7, 15)),
                                                ("E003", "Lucía Condori Flores", "7345901 LP", "Contadora", 5400, date(2021, 2, 1)), ("E004", "José Luis Apaza", "8123456 LP", "Encargado de almacén", 3900, date(2022, 5, 2)),
                                                ("E005", "Ana Patricia Choque", "9087123 LP", "Asistente administrativa", 3500, date(2023, 9, 4)), ("E006", "Pedro Limachi Vargas", "5432167 LP", "Chofer repartidor", 3600, date(2020, 11, 9))):
        c.rrhh.guardar_empleado({"codigo": cod, "nombre": nom, "ci": ci, "cargo": cargo, "haber_basico": haber, "fecha_ingreso": ingreso, "nua": "NUA" + cod[1:]})
    for m in range(1, 13):
        pid = c.rrhh.generar(anio, m)
        c.rrhh.cerrar(pid)
        c.rrhh.pagar(pid, date(anio, m, 28))
    # IVA mensual
    for m in range(1, 13):
        try:
            c.iva.liquidar(anio, m)
        except Exception:  # noqa: BLE001
            pass
    c.set_param("IUE_PROVISION", "1")
