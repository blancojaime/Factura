"""Las cifras del Manual de Pruebas se verifican automáticamente aquí: si el cálculo cambia, el manual debe actualizarse."""
import pytest

from tests.conftest import Entorno


@pytest.fixture
def e26():
    e = Entorno(anio=2026)
    yield e
    e.cerrar()


def test_cifras_del_manual(e26):
    e, c = e26, e26.ctx
    caja, ventas, gasto = e.cta("1.1.1.01.001"), e.cta("4.1.1.01.001"), e.cta("5.3.1.02.001")
    c.vouchers.crear({"tipo": "T", "fecha": "2026-01-02", "glosa": "Aporte inicial", "lineas": [{"cuenta_id": caja, "debe": 50000}, {"cuenta_id": e.cta("3.1.1.01.001"), "haber": 50000}]})
    c.iva.registrar({"libro": "V", "fecha": "2026-01-15", "nit": "1006341022", "razon_social": "Minimarket El Ahorro", "nro_factura": "1001", "nro_autorizacion": "CUF1",
                     "importe_total": 1000, "generar_asiento": True, "contra_cuenta_id": caja, "cuenta_id": ventas})
    c.iva.registrar({"libro": "C", "fecha": "2026-01-16", "nit": "1003220026", "razon_social": "Industrias Alimenticias", "nro_factura": "5001", "nro_autorizacion": "CUF2",
                     "importe_total": 500, "generar_asiento": True, "contra_cuenta_id": caja, "cuenta_id": gasto})
    assert (e.saldo("2.1.2.01.001"), e.saldo("4.1.1.01.001"), e.saldo("5.3.1.03.001"), e.saldo("2.1.2.01.002"), e.saldo("1.1.2.03.001"), e.saldo("5.3.1.02.001")) == (130, 870, 30, 30, 65, 435)
    assert e.saldo("1.1.1.01.001") == 50500
    r = c.iva.resumen_mensual(2026, 1)
    assert (r["debito_fiscal"], r["credito_fiscal"], r["iva_a_pagar"], r["it_devengado"]) == (130, 65, 65, 30)
    alm = c.db.scalar("select id from almacen limit 1")
    it = c.inventario.guardar_item({"codigo": "ARZ01", "nombre": "Arroz 1kg", "precio_venta": 10})
    prv = c.terceros.guardar({"clase": "P", "nombre": "Proveedor SA", "nit": "2"})
    cli = c.terceros.guardar({"clase": "C", "nombre": "Cliente Uno", "nit": "1234567", "limite_credito": 5000})
    c.inventario.registrar({"tipo": "INI", "fecha": "2026-01-05", "almacen_id": alm, "items": [{"item_id": it, "cantidad": 100, "costo_unit": 5.0}], "generar_asiento": True})
    c.compras.registrar({"fecha": "2026-01-10", "tercero_id": prv, "nro_factura": "7001", "items": [{"item_id": it, "cantidad": 100, "precio": 8.0}]})
    x = c.inventario.item(it)
    assert (x["stock"], x["costo_prom"]) == (200, 5.98)
    v = c.ventas.registrar({"fecha": "2026-01-20", "tercero_id": cli, "nro_factura": "1002", "tipo_pago": "CRE", "items": [{"item_id": it, "cantidad": 50, "precio": 10}]})
    assert (v["total"], v["iva"], v["costo"]) == (500, 65, 299)
    assert c.inventario.item(it)["stock"] == 150 and e.saldo("1.1.3.01.001") == 897
    c.cobros.registrar({"clase": "CO", "fecha": "2026-01-25", "tercero_id": cli, "monto": 200})
    assert c.terceros.saldo(cli, "C") == 300
    g = [g for g in c.activos.grupos() if g["nombre"] == "Equipo de Computación"][0]
    c.activos.guardar({"codigo": "PC1", "nombre": "Computadora", "grupo_id": g["id"], "fecha_alta": "2026-01-10", "valor_original": 12000})
    assert c.activos.depreciar(2026, 1, False)[0]["depreciacion"] == 250
    emp = c.rrhh.empleado(c.rrhh.guardar_empleado({"nombre": "Ana Mamani", "ci": "111", "fecha_ingreso": "2020-01-01", "haber_basico": 6000, "cargo": "Contadora"}))
    f = c.rrhh.calcular(emp, 2026, 1)
    assert (f["bono_antig"], f["total_ganado"], f["afp_vejez"], f["afp_riesgo"], f["afp_comision"], f["afp_solidario"], f["total_desc"], f["liquido"]) == (1089, 7089, 708.9, 121.22, 35.45, 35.45, 901.02, 6187.98)
    assert (f["pat_cns"], f["pat_riesgo"], f["pat_vivienda"], f["pat_solidario"]) == (708.9, 121.22, 141.78, 248.12)
    emp["haber_basico"] = 20000
    g2 = c.rrhh.calcular(emp, 2026, 1)
    assert (g2["total_ganado"], g2["ans"], g2["rc_base"], g2["rc_impuesto"], g2["rciva"], g2["liquido"]) == (21089, 93.02, 5208.58, 677.12, 0, 18315.56)
    fq = c.rrhh.finiquito(emp["id"], "2026-06-30", "DESPIDO_INTEMPESTIVO", 10)
    assert (fq["indemnizacion"], fq["desahucio"], fq["aguinaldo_proporcional"], fq["total"]) == (46078.5, 21267.0, 3544.5, 79253.0)


def test_demo_estados_cuadran(tmp_path):
    from contabol.demo import crear_empresa_demo
    from contabol.sistema import Sistema
    s = Sistema(str(tmp_path))
    u = s.autenticar("admin", "admin")
    eid, gid = crear_empresa_demo(s, u, 2025)
    c = s.abrir_contexto(u, eid, gid)
    b = c.estados.balance_general("2025-12-31")
    assert b["cuadra"]
    d, i = c.estados.flujo_directo("2025-01-01", "2025-12-31"), c.estados.flujo_indirecto("2025-01-01", "2025-12-31")
    assert d["cuadra"] and i["cuadra"] and abs(d["variacion"] - i["variacion"]) < 0.02
    ev = c.estados.evolucion_patrimonio("2025-01-01", "2025-12-31")
    assert abs(ev["total_final"] - b["total_patrimonio"]) < 0.02
    c.cerrar()
    s.close()
