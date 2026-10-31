import json
from datetime import date, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from siim.core import backup as B, license as Lic, security as S
from siim.core.db import Database


def _lic(priv, machine, vence, cliente="Municipio X"):
    payload = json.dumps(dict(cliente=cliente, maquina=machine, vence=vence), sort_keys=True).encode()
    return f"{Lic.PREFIX}.{Lic._b64e(payload)}.{Lic._b64e(priv.sign(payload))}"


def test_licencia_firma_maquina_y_vencimiento(db):
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    m = Lic.machine_code()
    mgr = Lic.LicenseManager(db, pub)
    hoy = date.today()
    assert mgr.status().estado == "PRUEBA"
    ok = mgr.install(_lic(priv, m, (hoy + timedelta(days=100)).isoformat()))
    assert ok.estado == "LICENCIADO" and mgr.status().estado == "LICENCIADO"
    # otro equipo
    assert Lic.verify_license_text(_lic(priv, "AAAA-BBBB-CCCC-DDDD", None), pub).estado == "INVALIDO"
    # alterada
    txt = _lic(priv, m, None)
    pre, body, sig = txt.split(".")
    bad = f"{pre}.{Lic._b64e(json.dumps(dict(cliente='Otro', maquina=m, vence=None)).encode())}.{sig}"
    assert Lic.verify_license_text(bad, pub).estado == "INVALIDO"
    # firmada por otra clave
    assert Lic.verify_license_text(_lic(Ed25519PrivateKey.generate(), m, None), pub).estado == "INVALIDO"
    # vencida
    assert Lic.verify_license_text(_lic(priv, m, (hoy - timedelta(days=1)).isoformat()), pub).estado == "VENCIDO"


def test_prueba_vence_y_reloj_atrasado(db):
    mgr = Lic.LicenseManager(db, Ed25519PrivateKey.generate().public_key())
    d0 = date(2026, 1, 1)
    assert mgr.status(d0).estado == "PRUEBA"
    assert mgr.status(d0 + timedelta(days=31)).estado == "VENCIDO"
    assert mgr.status(d0 + timedelta(days=5)).estado == "INVALIDO"       # reloj retrocedido


def test_backup_restore_y_cifrado(db, tmp_path):
    S.create_user(db, "admin", "A", "ADMINISTRADOR", "Clave2026x")
    p = B.create_backup(db, tmp_path / "bk", "prueba", password="secreta1")
    assert B.is_encrypted(p)
    with pytest.raises(B.BackupError):
        B.verify_backup(p, "mala")
    man = B.verify_backup(p, "secreta1")
    assert man["schema"] == db.schema_version
    db.execute("DELETE FROM usuarios")
    assert db.scalar("SELECT COUNT(*) FROM usuarios") == 0
    B.restore_backup(db, p, "secreta1", safety_dir=tmp_path / "bk")
    assert db.scalar("SELECT COUNT(*) FROM usuarios") == 1 and db.integrity_check()[0]
    assert any("antes-de-restaurar" in x["nombre"] for x in B.list_backups(tmp_path / "bk"))


def test_backup_detecta_corrupcion(db, tmp_path):
    p = B.create_backup(db, tmp_path / "bk")
    data = bytearray(p.read_bytes())
    data[len(data) // 2] ^= 0xFF
    p.write_bytes(bytes(data))
    with pytest.raises(B.BackupError):
        B.verify_backup(p)


def test_retencion(db, tmp_path):
    import os, time
    for i in range(6):
        p = B.create_backup(db, tmp_path / "bk", f"r{i}")
        os.utime(p, (time.time() - (6 - i) * 86400 * 40,) * 2)
    rem = B.apply_retention(tmp_path / "bk", keep_last=2, keep_monthly=1)
    assert len(B.list_backups(tmp_path / "bk")) == 2 and len(rem) == 4


def test_password_hash_bloqueo_y_cadena_auditoria(db):
    S.create_user(db, "u", "U", "CAJERO", "Clave2026x")
    for _ in range(S.MAX_INTENTOS):
        with pytest.raises(S.AuthError):
            S.login(db, "u", "mal")
    with pytest.raises(S.AuthError):
        S.login(db, "u", "Clave2026x")            # bloqueada aun con clave correcta
    with pytest.raises(ValueError):
        S.create_user(db, "x", "X", "CAJERO", "corta")
    assert S.verify_audit_chain(db)[0]
    db.execute("UPDATE bitacora SET usuario='intruso' WHERE id=1")
    assert S.verify_audit_chain(db) == (False, 1)


def test_integridad_y_transaccion(db):
    with pytest.raises(RuntimeError):
        with db.tx():
            db.execute("INSERT INTO zonas VALUES('ZZ','x')")
            raise RuntimeError("falla")
    assert db.scalar("SELECT COUNT(*) FROM zonas WHERE codigo='ZZ'") == 0
    assert db.integrity_check()[0]
