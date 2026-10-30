import pytest

from tests.conftest import BANCO, CAJA, CAPITAL


def _escenario(env):
    ctx = env.ctx
    env.asiento("2025-01-01", CAJA, CAPITAL, 100000, "Aporte de capital", tipo="I")
    env.asiento("2025-01-02", BANCO, CAJA, 40000, "Depósito")
    # préstamo bancario LP (financiamiento)
    env.asiento("2025-01-05", BANCO, "2.2.1.01.001", 30000, "Préstamo")
    # compra de activo fijo (inversión)
    env.asiento("2025-01-06", "1.2.1.01.007", BANCO, 20000, "Compra de maquinaria")
    cli = ctx.terceros.guardar({"clase": "C", "nombre": "Cliente", "nit": "1"})
    prv = ctx.terceros.guardar({"clase": "P", "nombre": "Proveedor", "nit": "2"})
    it = ctx.inventario.guardar_item({"codigo": "A1", "nombre": "Arroz", "precio_venta": 10})
    alm = ctx.db.scalar("SELECT id FROM almacen LIMIT 1")
    ctx.compras.registrar({"fecha": "2025-01-10", "tercero_id": prv, "nro_factura": "C1", "tipo_pago": "CRE", "items": [{"item_id": it, "cantidad": 1000, "precio": 5.0}]})
    ctx.ventas.registrar({"fecha": "2025-02-10", "tercero_id": cli, "nro_factura": "V1", "tipo_pago": "CRE", "items": [{"item_id": it, "cantidad": 400, "precio": 10}]})
    ctx.cobros.registrar({"clase": "CO", "fecha": "2025-02-20", "tercero_id": cli, "monto": 1500, "cuenta_id": env.cta(BANCO)})
    ctx.cobros.registrar({"clase": "PA", "fecha": "2025-02-25", "tercero_id": prv, "monto": 2000, "cuenta_id": env.cta(BANCO)})
    env.asiento("2025-03-01", "5.3.1.02.001", CAJA, 800, "Luz", tipo="E")
    env.asiento("2025-03-31", "5.3.1.04.007", "1.2.1.02.007", 1000, "Depreciación")


def test_balance_general_cuadra(env):
    _escenario(env)
    b = env.ctx.estados.balance_general("2025-03-31")
    assert b["cuadra"], b["diferencia"]
    assert b["total_activo"] == b["total_pasivo"] + b["total_patrimonio"]
    assert b["resultado"] == env.ctx.estados.resultado("2025-01-01", "2025-03-31")


def test_estado_resultados(env):
    _escenario(env)
    er = env.ctx.estados.estado_resultados("2025-01-01", "2025-03-31")
    assert er["ventas"] == pytest.approx(4000 - 520, abs=0.01)  # ventas netas de IVA (13% de 4000)
    assert er["neto"] == env.ctx.estados.resultado("2025-01-01", "2025-03-31")


def test_flujo_directo_igual_indirecto_igual_variacion(env):
    _escenario(env)
    est = env.ctx.estados
    d = est.flujo_directo("2025-01-01", "2025-03-31")
    i = est.flujo_indirecto("2025-01-01", "2025-03-31")
    assert d["cuadra"] and i["cuadra"]
    assert d["variacion"] == pytest.approx(i["variacion"], abs=0.02)
    assert d["inversion"] == -20000.0 and i["inversion"] == pytest.approx(-20000.0, abs=0.01)
    assert d["financiamiento"] == 130000.0 and i["financiamiento"] == pytest.approx(130000.0, abs=0.01)
    assert d["operacion"] == pytest.approx(i["operacion"], abs=0.02) == pytest.approx(-1300.0, abs=0.02)
    assert d["efectivo_final"] == est._efectivo("2025-03-31")


def test_patrimonio_cuadra_con_balance(env):
    _escenario(env)
    ev = env.ctx.estados.evolucion_patrimonio("2025-01-01", "2025-03-31")
    b = env.ctx.estados.balance_general("2025-03-31")
    assert ev["total_final"] == pytest.approx(b["total_patrimonio"], abs=0.02)


def test_notas(env):
    _escenario(env)
    n = env.ctx.estados.notas("2025-01-01", "2025-03-31")
    assert len(n) == 14 and n[2]["tabla"]["filas"]
    total_disp = n[2]["tabla"]["filas"][-1][2]
    assert total_disp == env.ctx.estados._efectivo("2025-03-31")
