import os

import pytest

from contabol import backup
from contabol.sistema import ErrorNegocio
from contabol.services.consolidacion import ConsolidacionService
from tests.conftest import CAJA, CAPITAL


def test_backup_y_restauracion(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 1000)
    ruta = backup.crear_backup(env.sis, env.eid)
    assert os.path.exists(ruta)
    meta = backup.verificar(ruta)
    assert len(meta["gestiones"]) == 1
    env.asiento("2025-01-02", CAJA, CAPITAL, 500)
    assert env.saldo(CAJA) == 1500
    env.ctx.cerrar()
    r = backup.restaurar(env.sis, ruta, env.usuario)
    assert r["gestiones"] == 1
    ctx = env.sis.abrir_contexto(env.usuario, env.eid, env.gid)
    assert ctx.cuentas.saldo(ctx.cuentas.por_codigo(CAJA)["id"]) == 1000.0
    ctx.cerrar()
    env.ctx = env.sis.abrir_contexto(env.usuario, env.eid, env.gid)


def test_backup_corrupto_es_rechazado(env, tmp_path):
    ruta = backup.crear_backup(env.sis, env.eid)
    datos = bytearray(open(ruta, "rb").read())
    datos[len(datos) // 2] ^= 0xFF
    malo = tmp_path / "malo.cbk"
    malo.write_bytes(bytes(datos))
    with pytest.raises(Exception):
        backup.verificar(str(malo))


def test_multiempresa_aislada_y_consolidacion(env):
    env.asiento("2025-01-01", CAJA, CAPITAL, 1000)
    eid2, gid2 = env.sis.crear_empresa({"codigo": "FILIAL", "razon_social": "Filial S.R.L."}, 2025, env.usuario)
    c2 = env.sis.abrir_contexto(env.usuario, eid2, gid2)
    c2.vouchers.crear({"tipo": "T", "fecha": "2025-01-01", "glosa": "x", "lineas": [{"cuenta_id": c2.cuentas.por_codigo(CAJA)["id"], "debe": 300},
                                                                                  {"cuenta_id": c2.cuentas.por_codigo(CAPITAL)["id"], "haber": 300}]})
    assert env.saldo(CAJA) == 1000 and c2.cuentas.saldo(c2.cuentas.por_codigo(CAJA)["id"]) == 300
    c2.cerrar()
    filas = ConsolidacionService(env.sis, env.usuario).balance([env.gid, gid2], "2025-01-01", "2025-12-31", nivel=5)
    caja = [f for f in filas if f["codigo"] == CAJA][0]
    assert caja["saldo_d"] == 1300.0


def test_usuarios_y_bloqueo(env):
    sis = env.sis
    sis.crear_usuario("juan", "Juan", "clave123")
    for _ in range(5):
        with pytest.raises(ErrorNegocio):
            sis.autenticar("juan", "mala")
    with pytest.raises(ErrorNegocio, match="bloqueado"):
        sis.autenticar("juan", "clave123")
    uid = sis.db.scalar("SELECT id FROM usuario WHERE login='juan'")
    sis.cambiar_clave(uid, "nueva1234")
    assert sis.autenticar("juan", "nueva1234")["login"] == "juan"
