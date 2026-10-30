import pytest

from contabol.sistema import ErrorNegocio
from tests.conftest import BANCO, CAJA, CAPITAL, GASTO_LUZ


def test_crear_empresa_y_plan(env):
    assert env.ctx.db.scalar("SELECT COUNT(*) FROM cuenta") > 200
    assert env.ctx.cuentas.por_codigo(CAJA)["es_movimiento"] == 1
    assert env.ctx.cuentas.por_codigo("1.1.1.01")["es_movimiento"] == 0
    assert env.ctx.param("CTA_CAJA") == CAJA


def test_comprobante_cuadra_y_numera(env):
    c1 = env.asiento("2025-01-01", CAJA, CAPITAL, 50000, "Aporte inicial")
    c2 = env.asiento("2025-01-10", GASTO_LUZ, CAJA, 500, "Luz", tipo="E")
    c3 = env.asiento("2025-01-12", GASTO_LUZ, CAJA, 100, "Luz 2", tipo="E")
    assert env.ctx.vouchers.obtener(c1)["numero"] == 1
    assert env.ctx.vouchers.obtener(c2)["numero"] == 1
    assert env.ctx.vouchers.obtener(c3)["numero"] == 2
    assert env.saldo(CAJA) == 49400.0
    assert env.saldo(CAPITAL) == 50000.0


def test_comprobante_descuadrado_rechazado(env):
    with pytest.raises(ErrorNegocio, match="no cuadra"):
        env.ctx.vouchers.crear({"tipo": "T", "fecha": "2025-02-01", "glosa": "x", "lineas": [
            {"cuenta_id": env.cta(CAJA), "debe": 100}, {"cuenta_id": env.cta(CAPITAL), "haber": 90}]})


def test_validaciones(env):
    v = env.ctx.vouchers
    cj = env.cta(CAJA)
    with pytest.raises(ErrorNegocio, match="fuera de la gestión"):
        v.crear({"tipo": "T", "fecha": "2024-12-31", "glosa": "x", "lineas": [{"cuenta_id": cj, "debe": 1}, {"cuenta_id": env.cta(CAPITAL), "haber": 1}]})
    with pytest.raises(ErrorNegocio, match="no es de movimiento"):
        v.crear({"tipo": "T", "fecha": "2025-01-31", "glosa": "x", "lineas": [{"cuenta_id": env.ctx.cuentas.por_codigo("1.1.1.01")["id"], "debe": 1},
                                                                                {"cuenta_id": env.cta(CAPITAL), "haber": 1}]})
    with pytest.raises(ErrorNegocio, match="glosa"):
        v.crear({"tipo": "T", "fecha": "2025-01-31", "glosa": " ", "lineas": [{"cuenta_id": cj, "debe": 1}, {"cuenta_id": env.cta(CAPITAL), "haber": 1}]})
    with pytest.raises(ErrorNegocio, match="negativos"):
        v.crear({"tipo": "T", "fecha": "2025-01-31", "glosa": "x", "lineas": [{"cuenta_id": cj, "debe": -1}, {"cuenta_id": env.cta(CAPITAL), "haber": 1}]})


def test_anulacion_excluye_de_saldos(env):
    c = env.asiento("2025-01-05", CAJA, CAPITAL, 1000)
    assert env.saldo(CAJA) == 1000
    env.ctx.vouchers.anular(c)
    assert env.saldo(CAJA) == 0
    with pytest.raises(ErrorNegocio):
        env.ctx.vouchers.anular(c)


def test_dolares(env):
    cid = env.ctx.vouchers.crear({"tipo": "E", "fecha": "2025-01-15", "glosa": "Pago en dólares", "moneda": "USD", "tc": 6.96, "lineas": [
        {"cuenta_id": env.cta(GASTO_LUZ), "debe": 100}, {"cuenta_id": env.cta(CAJA), "haber": 100}]})
    c = env.ctx.vouchers.obtener(cid)
    assert c["debe_bs"] == 696.0 and c["haber_bs"] == 696.0
    assert c["lineas"][0]["debe_usd"] == 100.0


def test_sumas_y_saldos_cuadran(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 50000)
    env.asiento("2025-01-02", BANCO, CAJA, 20000)
    env.asiento("2025-01-10", GASTO_LUZ, BANCO, 500)
    filas = env.ctx.libros.sumas_saldos("2025-01-01", "2025-12-31", nivel=5)
    movs = [f for f in filas if f["es_movimiento"]]
    assert round(sum(f["debe"] for f in movs), 2) == round(sum(f["haber"] for f in movs), 2) == 70500
    assert round(sum(f["saldo_d"] for f in movs), 2) == round(sum(f["saldo_h"] for f in movs), 2)
    raiz = [f for f in env.ctx.libros.sumas_saldos("2025-01-01", "2025-12-31", nivel=1)]
    assert {f["codigo"] for f in raiz} == {"1", "3", "5"}


def test_mayor_con_saldo_anterior(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 1000)
    env.asiento("2025-02-01", CAJA, CAPITAL, 500)
    m = env.ctx.libros.mayor(env.cta(CAJA), "2025-02-01", "2025-02-28")
    assert m["saldo_anterior"] == 1000 and m["saldo_final"] == 1500 and len(m["filas"]) == 1


def test_sin_permiso_y_gestion_cerrada(env):
    from contabol.sistema import Sistema
    env.sis.crear_usuario("lector", "Lector", "lector123")
    u = env.sis.autenticar("lector", "lector123") if False else None
    uid = env.sis.db.scalar("SELECT id FROM usuario WHERE login='lector'")
    env.sis.asignar_empresa(uid, env.eid, "CONSULTA")
    usr = env.sis.usuario(uid)
    ctx = env.sis.abrir_contexto(usr, env.eid, env.gid)
    with pytest.raises(ErrorNegocio, match="permiso"):
        ctx.vouchers.crear({"tipo": "T", "fecha": "2025-01-01", "glosa": "x", "lineas": []})
    ctx.cerrar()
    env.sis.db.execute("UPDATE gestion SET estado='C' WHERE id=?", (env.gid,))
    cx = env.sis.abrir_contexto(env.usuario, env.eid, env.gid)
    with pytest.raises(ErrorNegocio, match="cerrada"):
        cx.vouchers.crear({"tipo": "T", "fecha": "2025-01-01", "glosa": "x", "lineas": []})
    cx.cerrar()
