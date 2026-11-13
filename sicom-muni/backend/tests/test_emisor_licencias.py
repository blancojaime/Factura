"""Emisor de Licencias (herramienta externa): llaves, emision por consola, registro y verificacion."""
import importlib.util
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.services import licencia_core as core

RUTA = Path(__file__).resolve().parents[3] / "herramientas" / "emisor-licencias" / "emisor.py"


@pytest.fixture()
def emisor(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("emisor", RUTA)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "CONFIG_DIR", tmp_path / "cfg")
    monkeypatch.setattr(m, "REGISTRO", tmp_path / "cfg" / "registro.csv")
    return m


def test_flujo_completo_por_consola(emisor, tmp_path, capsys):
    assert emisor.cli(["llaves", "--salida", str(tmp_path / "k")]) == 0
    priv = tmp_path / "k" / "llave_privada_SICOM.pem"
    assert priv.exists() and (tmp_path / "k" / "llave_publica_SICOM.pem").exists()
    assert emisor.cli(["llaves", "--salida", str(tmp_path / "k")]) == 2  # no sobrescribe la llave privada
    lic = tmp_path / "cliente.sicomlic"
    venc = (date.today() + timedelta(days=90)).isoformat()
    assert emisor.cli(["emitir", "--llave", str(priv), "--entidad", "GAM Ñandú", "--equipo", core.id_equipo(),
                       "--vence", venc, "--max-usuarios", "12", "--salida", str(lic)]) == 0
    pub = (tmp_path / "k" / "llave_publica_SICOM.pem").read_bytes()
    r = core.verificar(lic.read_text(encoding="utf-8"), pub, core.id_equipo())
    assert r.valida and r.datos["entidad"] == "GAM Ñandú" and r.datos["max_usuarios"] == 12
    assert "SICOM1-" in capsys.readouterr().out
    registro = (tmp_path / "cfg" / "registro.csv").read_text(encoding="utf-8-sig")
    assert "GAM Ñandú" in registro and venc in registro
    assert emisor.cli(["verificar", "--llave", str(priv), str(lic)]) == 0
    assert emisor.cli(["verificar", "--llave", str(priv), str(lic), "--equipo", "AAAA-BBBB-CCCC-DDDD"]) == 1  # otro equipo
    assert emisor.cli(["emitir", "--llave", str(priv), "--entidad", "", "--salida", str(lic)]) == 2


def test_licencia_del_emisor_se_activa_en_el_servidor(emisor, tmp_path):
    emisor.cli(["llaves", "--salida", str(tmp_path / "k")])
    priv = tmp_path / "k" / "llave_privada_SICOM.pem"
    lic = tmp_path / "x.sicomlic"
    emisor.cli(["emitir", "--llave", str(priv), "--entidad", "GAM", "--salida", str(lic)])  # cualquier equipo
    assert core.verificar(core.leer(lic.read_text(encoding="utf-8")), core.publica_de(priv.read_bytes()), "XXXX-XXXX-XXXX-XXXX").valida
