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


def test_comprobante_con_factura_vinculada_a_libros(env):
    """Un egreso/ingreso manual con factura alimenta el libro de compras/ventas y ajusta el asiento con el IVA."""
    ctx = env.ctx
    gasto, caja, venta = env.cta("5.3.1.02.001"), env.cta("1.1.1.01.001"), env.cta("4.1.1.01.001")
    lineas = [{"cuenta_id": gasto, "debe": 500, "haber": 0}, {"cuenta_id": caja, "debe": 0, "haber": 500}]
    aj = ctx.vouchers.ajustar_asiento_iva("E", lineas, 500, "2025-02-10")
    assert [(l["cuenta_id"], l["debe"], l["haber"]) for l in aj][-1] == (env.cta("1.1.2.03.001"), 65.0, 0)
    assert aj[0]["debe"] == 435.0
    cid = ctx.vouchers.crear({"tipo": "E", "fecha": "2025-02-10", "glosa": "Compra de servicios", "ufv": 2.61234, "nro_cheque": "000123", "lineas": aj,
                              "factura": {"nit": "1003220026", "razon_social": "Proveedor SA", "nro_factura": "991", "nro_autorizacion": "CUF9", "importe_total": 500}})
    f = ctx.iva.listar("C", 2025, 2)
    assert len(f) == 1 and f[0]["iva"] == 65.0 and f[0]["comprobante_id"] == cid and f[0]["origen"] == "COMPROBANTE"
    assert ctx.vouchers.obtener(cid)["nro_cheque"] == "000123"
    assert ctx.tc.ufv("2025-02-10") == 2.61234          # la UFV escrita en el comprobante queda registrada para esa fecha
    assert env.saldo("1.1.2.03.001") == 65.0 and env.saldo("5.3.1.02.001") == 435.0
    ctx.vouchers.anular(cid)
    assert ctx.iva.listar("C", 2025, 2)[0]["estado"] == "A" and ctx.iva.resumen_mensual(2025, 2)["credito_fiscal"] == 0
    # ingreso con débito fiscal
    li = ctx.vouchers.ajustar_asiento_iva("I", [{"cuenta_id": caja, "debe": 1000, "haber": 0}, {"cuenta_id": venta, "debe": 0, "haber": 1000}], 1000, "2025-02-12")
    ctx.vouchers.crear({"tipo": "I", "fecha": "2025-02-12", "glosa": "Venta de contado", "lineas": li, "factura": {"nit": "1", "razon_social": "Cliente", "nro_factura": "7", "importe_total": 1000}})
    assert ctx.iva.listar("V", 2025, 2)[0]["iva"] == 130.0 and env.saldo("2.1.2.01.001") == 130.0 and env.saldo("4.1.1.01.001") == 870.0


def test_numero_automatico_y_migracion(env):
    n, cod = env.ctx.vouchers.siguiente_numero("I", "2025-03-05")
    assert (n, cod) == (1, "I-03/0001")
    env.asiento("2025-03-05", "1.1.1.01.001", "3.1.1.01.001", 10, tipo="I")
    assert env.ctx.vouchers.siguiente_numero("I", "2025-03-20")[1] == "I-03/0002"
    from contabol import schema
    db = env.ctx.db
    schema.migrar_gestion(db)   # idempotente
