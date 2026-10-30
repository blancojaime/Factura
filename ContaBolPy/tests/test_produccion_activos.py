from tests.conftest import CAJA, CAPITAL


def test_depreciacion_computadora(env):
    env.ctx.tc.guardar("2025-01-01", 6.96, 2.5)
    env.asiento("2025-01-01", CAJA, CAPITAL, 50000)
    g = [x for x in env.ctx.activos.grupos() if x["nombre"] == "Equipo de Computación"][0]
    aid = env.ctx.activos.guardar({"codigo": "PC1", "nombre": "Computadora", "grupo_id": g["id"], "fecha_alta": "2025-01-10", "valor_original": 12000,
                                   "contra_cuenta_id": env.cta(CAPITAL)})
    prev = env.ctx.activos.depreciar(2025, 1, registrar=False)
    assert prev[0]["depreciacion"] == 250.0
    env.ctx.activos.depreciar(2025, 1, registrar=True)
    assert env.saldo("1.2.1.02.005") == 250.0 and env.saldo("5.3.1.04.005") == 250.0
    assert env.ctx.activos.depreciar(2025, 1, registrar=True) == []  # no duplica
    env.ctx.tc.guardar("2025-12-31", 6.96, 2.6)
    env.ctx.activos.depreciar(2025, 2, registrar=True)
    act = env.ctx.activos.actualizar_ufv(2025, 12, registrar=True)
    assert round(act[0]["actualizacion"], 2) == round(12000 * (2.6 / 2.5 - 1), 2)
    env.ctx.activos.baja(aid, "2025-12-31", 3000)
    assert env.saldo("1.2.1.01.005") == 0.0 and env.saldo("1.2.1.02.005") == 0.0


def test_orden_produccion(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 50000)
    inv, rh = env.ctx.inventario, env.ctx.rrhh
    alm = env.ctx.db.scalar("SELECT id FROM almacen LIMIT 1")
    mp = inv.guardar_item({"codigo": "MP1", "nombre": "Harina", "precio_venta": 0})
    pt = inv.guardar_item({"codigo": "PT1", "nombre": "Pan", "precio_venta": 3})
    inv.registrar({"tipo": "INI", "fecha": "2025-01-01", "almacen_id": alm, "items": [{"item_id": mp, "cantidad": 100, "costo_unit": 3.0}], "generar_asiento": True})
    oid = env.ctx.produccion.abrir("2025-02-01", pt, 10, alm, alm)
    env.ctx.produccion.consumir_mp(oid, "2025-02-02", [{"item_id": mp, "cantidad": 20}])
    env.ctx.produccion.agregar_mod(oid, None, 8, 12.5)
    env.ctx.produccion.agregar_cif(oid, "Energía", 40)
    env.ctx.produccion.cerrar(oid, "2025-02-20", 10)
    o = env.ctx.produccion.obtener(oid)
    assert o["costo_total"] == 200.0 and o["costo_unit"] == 20.0
    assert inv.item(pt)["stock"] == 10 and inv.item(pt)["costo_prom"] == 20.0
