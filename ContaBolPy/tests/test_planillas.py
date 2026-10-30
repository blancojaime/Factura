from contabol.sistema import ErrorNegocio
import pytest
from tests.conftest import CAJA, CAPITAL


def _emp(env, haber=6000.0, ingreso="2020-01-01", **kw):
    return env.ctx.rrhh.guardar_empleado({"nombre": "Ana Mamani", "ci": "111", "fecha_ingreso": ingreso, "haber_basico": haber, "cargo": "Contadora", **kw})


def test_normativa_2026_vigente(env):
    n = env.sis.normativa
    assert n.smn("2026-03-01") == 3300 and n.smn("2025-06-01") == 2750 and n.smn("2024-06-01") == 2500
    assert n.num("PAT_SOLIDARIO", "2025-01-01") == 3.5 and n.num("PAT_SOLIDARIO", "2023-01-01") == 3
    assert n.num("ANS_T3_PCT", "2025-01-01") == 11.48


def test_bono_antiguedad_y_ans(env):
    rh = env.ctx.rrhh
    # 6 años completos: 11 % de 3 SMN (3300) = 1089
    assert rh.bono_antiguedad("2020-01-01", "2026-03-31", 3300) == 1089.0
    assert rh.bono_antiguedad("2025-06-01", "2026-03-31", 3300) == 0.0
    assert rh.ans(10000, "2026-03-31") == 0.0
    assert rh.ans(20000, "2026-03-31") == round(7000 * 0.0115, 2)
    assert rh.ans(40000, "2026-03-31") == round(27000 * 0.0115 + 15000 * 0.0574 + 5000 * 0.1148, 2)


def test_calculo_planilla_basico(env):
    env.ctx.tc.guardar("2025-01-01", 6.96, 2.5)
    e = env.ctx.rrhh.empleado(_emp(env, 6000.0))
    f = env.ctx.rrhh.calcular(e, 2025, 1)
    smn = 2750
    bono = round(smn * 3 * 0.11, 2)
    tg = round(6000 + bono, 2)
    assert f["total_ganado"] == tg
    assert f["afp_vejez"] == round(tg * 0.10, 2)
    assert f["afp_vejez"] + f["afp_riesgo"] + f["afp_comision"] + f["afp_solidario"] == pytest.approx(tg * 0.1271, abs=0.02)
    assert f["pat_solidario"] == round(tg * 0.035, 2)
    assert f["pat_cns"] == round(tg * 0.10, 2)
    # RC-IVA: (TG - AFP) - 4*SMN(11000) = pequeño positivo/negativo
    neto = tg - round(tg * 0.1271, 2)
    base = max(0, neto - 4 * smn)
    assert f["rc_base"] == pytest.approx(base, abs=0.02)
    assert f["liquido"] == round(tg - f["total_desc"], 2)


def test_haber_menor_al_smn_rechazado(env):
    with pytest.raises(ErrorNegocio, match="salario mínimo"):
        _emp(env, 1000.0, ingreso="2025-01-01")


def test_planilla_cierre_y_pago(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 100000)
    _emp(env, 6000.0)
    pid = env.ctx.rrhh.generar(2025, 1)
    t = env.ctx.rrhh.totales(pid)
    env.ctx.rrhh.cerrar(pid)
    assert env.saldo("2.1.3.01.001") == t["liquido"]
    assert env.saldo("2.1.3.01.004") == t["pat_cns"]
    assert env.saldo("5.3.1.01.001") == t["haber_basico"]
    env.ctx.rrhh.pagar(pid, "2025-02-05")
    assert env.saldo("2.1.3.01.001") == 0.0
    assert env.saldo(CAJA) == round(100000 - t["liquido"], 2)


def test_anticipo_se_descuenta(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 100000)
    eid = _emp(env)
    env.ctx.rrhh.anticipo(eid, "2025-01-10", 500, 500)
    pid = env.ctx.rrhh.generar(2025, 1)
    d = env.ctx.rrhh.detalle(pid)[0]
    assert d["anticipos"] == 500
    env.ctx.rrhh.cerrar(pid)
    assert env.saldo("1.1.2.02.002") == 0.0


def test_aguinaldo_y_finiquito(env):
    eid = _emp(env, 6000.0, ingreso="2024-01-01")
    ag = env.ctx.rrhh.aguinaldo(2025)
    assert len(ag) == 1 and ag[0]["dias"] == 360
    f = env.ctx.rrhh.finiquito(eid, "2026-01-01", "DESPIDO_INTEMPESTIVO")
    assert f["indemnizacion"] > 0 and f["desahucio"] > 0 and f["total"] > f["indemnizacion"]
