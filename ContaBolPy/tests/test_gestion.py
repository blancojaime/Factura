import pytest

from tests.conftest import CAJA, CAPITAL
from tests.test_estados import _escenario


def test_cierre_y_apertura_traslada_saldos(env):
    _escenario(env)
    ctx = env.ctx
    antes = ctx.estados.balance_general("2025-12-31")
    ctx.gestiones.generar_cierre()
    # el balance previo al cierre no cambia por el asiento de cierre
    despues = ctx.estados.balance_general("2025-12-31")
    assert despues["total_activo"] == antes["total_activo"] and despues["cuadra"]
    ctx.gestiones.cerrar_gestion()
    gid = ctx.gestiones.abrir_nueva_gestion()
    c26 = env.sis.abrir_contexto(env.usuario, env.eid, gid)
    b = c26.estados.balance_general("2026-01-01")
    assert b["cuadra"]
    assert b["total_activo"] == antes["total_activo"]
    assert c26.cuentas.saldo(c26.cuentas.por_codigo("3.2.1.01.001")["id"]) == antes["resultado"]  # resultado -> resultados acumulados
    # existencias y saldos de clientes trasladados
    assert c26.inventario.valor_total("2026-01-01") == pytest.approx(ctx.inventario.valor_total("2025-12-31"), abs=0.01)
    cli = c26.terceros.listar("C")[0]
    assert c26.terceros.saldo(cli["id"], "C") == ctx.terceros.saldo(cli["id"], "C")
    # el estado de flujo del nuevo año arranca con el efectivo de apertura
    f = c26.estados.flujo_directo("2026-01-01", "2026-12-31")
    assert f["efectivo_inicial"] == ctx.estados._efectivo("2025-12-31")
    c26.cerrar()


def test_diferencia_de_cambio(env):
    ctx = env.ctx
    ctx.vouchers.crear({"tipo": "I", "fecha": "2025-01-05", "glosa": "Aporte en dólares", "moneda": "USD", "tc": 6.96, "lineas": [
        {"cuenta_id": env.cta("1.1.1.01.002"), "debe": 1000}, {"cuenta_id": env.cta(CAPITAL), "haber": 1000}]})
    r = ctx.gestiones.diferencia_cambio("2025-12-31", 7.00, registrar=True)
    assert r["neto"] == 40.0
    assert env.saldo("1.1.1.01.002") == 7000.0
    assert env.saldo("4.2.1.01.004") == 40.0


def test_ajuste_inflacion_con_ufv(env):
    env.ctx.tc.guardar("2024-12-31", 6.96, 2.5)
    env.ctx.tc.guardar("2025-12-31", 6.96, 2.6)
    env.asiento("2025-01-01", "1.2.1.01.001", CAPITAL, 100000)
    r = env.ctx.gestiones.ajuste_inflacion("2025-12-31", registrar=True)
    assert round(r["factor"], 4) == 0.04
    assert env.saldo("1.2.1.01.001") == 104000.0
