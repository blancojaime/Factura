import pytest

from contabol.sistema import ErrorNegocio
from tests.conftest import CAJA, CAPITAL


def _base(env):
    inv = env.ctx.inventario
    cli = env.ctx.terceros.guardar({"clase": "C", "nombre": "Cliente Uno", "nit": "1234567", "limite_credito": 5000})
    prv = env.ctx.terceros.guardar({"clase": "P", "nombre": "Proveedor SA", "nit": "7654321"})
    item = inv.guardar_item({"codigo": "A1", "nombre": "Arroz 1 kg", "precio_venta": 10})
    alm = env.ctx.db.scalar("SELECT id FROM almacen LIMIT 1")
    return cli, prv, item, alm


def test_ejemplo_manual_orion_venta_1000(env):
    """Venta de Bs 1.000 con factura: DF 130, ventas 870, IT 30 (ejemplo del manual de Orion)."""
    env.asiento("2025-01-01", CAJA, CAPITAL, 10000)
    cli, prv, item, alm = _base(env)
    env.ctx.inventario.registrar({"tipo": "INI", "fecha": "2025-01-01", "almacen_id": alm, "items": [{"item_id": item, "cantidad": 1000, "costo_unit": 0.0}]})
    env.ctx.ventas.registrar({"fecha": "2025-01-15", "tercero_id": cli, "nro_factura": "1001", "items": [{"item_id": item, "cantidad": 100, "precio": 10}]})
    assert env.saldo("2.1.2.01.001") == 130.0
    assert env.saldo("4.1.1.01.001") == 870.0
    assert env.saldo("5.3.1.03.001") == 30.0
    assert env.saldo("2.1.2.01.002") == 30.0
    assert env.saldo(CAJA) == 11000.0
    f = env.ctx.iva.listar("V", 2025, 1)[0]
    assert f["importe_total"] == 1000.0 and f["iva"] == 130.0 and f["base_iva"] == 1000.0


def test_costo_promedio_y_cobros(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 100000)
    cli, prv, item, alm = _base(env)
    inv = env.ctx.inventario
    inv.registrar({"tipo": "INI", "fecha": "2025-01-01", "almacen_id": alm, "items": [{"item_id": item, "cantidad": 100, "costo_unit": 5.0}], "generar_asiento": True})
    env.ctx.compras.registrar({"fecha": "2025-01-10", "tercero_id": prv, "nro_factura": "5001", "con_factura": True, "tipo_pago": "CON",
                               "items": [{"item_id": item, "cantidad": 100, "precio": 8.0}]})
    it = inv.item(item)
    assert it["stock"] == 200
    assert 5.5 < it["costo_prom"] < 6.5
    assert env.saldo("1.1.2.03.001") == 104.0  # CF = 13% de 800
    v = env.ctx.ventas.registrar({"fecha": "2025-01-20", "tercero_id": cli, "nro_factura": "9", "tipo_pago": "CRE",
                                  "items": [{"item_id": item, "cantidad": 50, "precio": 10}]})
    assert env.ctx.terceros.saldo(cli, "C") == 500.0
    r = env.ctx.cobros.registrar({"clase": "CO", "fecha": "2025-01-25", "tercero_id": cli, "monto": 200})
    assert env.ctx.terceros.saldo(cli, "C") == 300.0
    env.ctx.cobros.anular(r["id"])
    assert env.ctx.terceros.saldo(cli, "C") == 500.0
    env.ctx.ventas.anular(v["id"])
    assert env.ctx.terceros.saldo(cli, "C") == 0.0
    assert inv.item(item)["stock"] == 200


def test_stock_insuficiente_y_limite_credito(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 1000)
    cli, prv, item, alm = _base(env)
    env.ctx.inventario.registrar({"tipo": "INI", "fecha": "2025-01-01", "almacen_id": alm, "items": [{"item_id": item, "cantidad": 10, "costo_unit": 5.0}]})
    with pytest.raises(ErrorNegocio, match="Stock insuficiente"):
        env.ctx.ventas.registrar({"fecha": "2025-01-05", "tercero_id": cli, "nro_factura": "1", "items": [{"item_id": item, "cantidad": 11, "precio": 10}]})
    with pytest.raises(ErrorNegocio, match="límite de crédito"):
        env.ctx.inventario.registrar({"tipo": "AJE", "fecha": "2025-01-05", "almacen_id": alm, "items": [{"item_id": item, "cantidad": 1000, "costo_unit": 1.0}]})
        env.ctx.ventas.registrar({"fecha": "2025-01-06", "tercero_id": cli, "nro_factura": "2", "tipo_pago": "CRE", "items": [{"item_id": item, "cantidad": 600, "precio": 10}]})


def test_liquidacion_iva(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 100000)
    cli, prv, item, alm = _base(env)
    env.ctx.inventario.registrar({"tipo": "INI", "fecha": "2025-01-01", "almacen_id": alm, "items": [{"item_id": item, "cantidad": 500, "costo_unit": 5.0}]})
    env.ctx.ventas.registrar({"fecha": "2025-01-15", "tercero_id": cli, "nro_factura": "1", "items": [{"item_id": item, "cantidad": 100, "precio": 10}]})
    env.ctx.compras.registrar({"fecha": "2025-01-16", "tercero_id": prv, "nro_factura": "7", "items": [{"item_id": item, "cantidad": 50, "precio": 10}]})
    r = env.ctx.iva.resumen_mensual(2025, 1)
    assert r["debito_fiscal"] == 130.0 and r["credito_fiscal"] == 65.0 and r["iva_a_pagar"] == 65.0
    env.ctx.iva.liquidar(2025, 1)
    assert env.saldo("2.1.2.01.001") == 0.0 and env.saldo("1.1.2.03.001") == 0.0


def test_factura_manual_y_duplicados(env):
    caja, ventas = env.cta(CAJA), env.cta("4.1.1.01.001")
    env.ctx.iva.registrar({"libro": "V", "fecha": "2025-02-01", "nit": "123", "razon_social": "X", "nro_factura": "50", "nro_autorizacion": "A1",
                           "importe_total": 1000, "generar_asiento": True, "contra_cuenta_id": caja, "cuenta_id": ventas})
    with pytest.raises(ErrorNegocio, match="Ya está registrada"):
        env.ctx.iva.registrar({"libro": "V", "fecha": "2025-02-01", "nit": "123", "razon_social": "X", "nro_factura": "50", "nro_autorizacion": "A1",
                               "importe_total": 10, "generar_asiento": False})
    a = env.ctx.iva.registrar({"libro": "V", "fecha": "2025-02-02", "nro_factura": "51", "estado": "A", "importe_total": 999})
    assert env.ctx.iva.obtener(a)["importe_total"] == 0
