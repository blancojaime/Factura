"""El lanzador de Windows debe arrancar aunque config.ini traiga BOM (PowerShell 5.1) o esté dañado."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("launcher", Path(__file__).resolve().parents[2] / "desktop" / "launcher.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)


@pytest.mark.parametrize("contenido,esperado", [
    (b"\xef\xbb\xbf[servidor]\r\nhost = 0.0.0.0\r\nport = 8800\r\n", ("0.0.0.0", 8800)),         # BOM UTF-8
    (b"[servidor]\r\nhost = 127.0.0.1\r\nport = 8765\r\n", ("127.0.0.1", 8765)),
    (b"\xff\xfe[\x00s\x00", ("127.0.0.1", 8765)),                                                # basura: valores por defecto
    (b"[servidor]\nport = abc\n", ("127.0.0.1", 8765)),
])
def test_config_tolerante(tmp_path, contenido, esperado):
    (tmp_path / "config.ini").write_bytes(contenido)
    assert L.leer_config(tmp_path) == esperado


def test_config_ausente_se_crea(tmp_path):
    assert L.leer_config(tmp_path) == ("127.0.0.1", 8765) and (tmp_path / "config.ini").exists()


def test_scripts_powershell_son_ascii():
    """PowerShell 5.1 lee los .ps1 sin BOM como ANSI: deben ser ASCII puro para no corromperse."""
    for f in (Path(__file__).resolve().parents[2] / "desktop" / "windows").glob("*.ps1"):
        assert all(ord(c) < 128 for c in f.read_text(encoding="utf-8")), f.name
