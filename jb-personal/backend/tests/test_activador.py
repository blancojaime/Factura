"""El emisor (activador) y la aplicación deben hablar el mismo formato."""
import base64
import sys
import threading
import urllib.request
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "activador"))
import jb_activador as A  # noqa: E402
from app import licencia as L  # noqa: E402


@pytest.fixture
def emisor(tmp_path, monkeypatch):
    k, nueva = A.cargar_clave(tmp_path)
    assert nueva
    monkeypatch.setattr(L, "CLAVE_PUBLICA_B64", A.publica_b64(k))
    return k, tmp_path


def test_codigo_emitido_lo_acepta_la_aplicacion(emisor):
    k, d = emisor
    c = A.emitir(k, "  GAM   Villa  Ejemplo ", L.id_equipo(), (date.today() + timedelta(days=30)).isoformat(), d)
    r = L.verificar_codigo(c)
    assert r["e"] == "GAM Villa Ejemplo" and r["m"] == L.id_equipo()
    assert (d / "emitidas.csv").read_text().count("\n") == 2 and c not in (d / "emitidas.csv").read_text()   # el historial no guarda el código


def test_validaciones_del_emisor(emisor):
    k, d = emisor
    for args in (("", L.id_equipo(), None), ("X", "equipo-malo", None), ("X", "JBP-ZZZZZ-00000-00000", None),
                 ("X", L.id_equipo(), (date.today() - timedelta(days=1)).isoformat())):
        with pytest.raises(ValueError):
            A.emitir(k, *args, d)
    assert L.verificar_codigo(A.emitir(k, "X", "*", None))


def test_clave_se_conserva_y_se_puede_rotar(tmp_path):
    k1, n1 = A.cargar_clave(tmp_path)
    k2, n2 = A.cargar_clave(tmp_path)
    assert n1 and not n2 and A.publica_b64(k1) == A.publica_b64(k2)


def test_interfaz_web_local_protegida_por_token(emisor):
    k, d = emisor
    from http.server import ThreadingHTTPServer
    import re
    salida = {}
    # se arranca el servidor en un hilo capturando token desde la impresión
    import io, contextlib
    buf = io.StringIO()
    def run():
        with contextlib.redirect_stdout(buf):
            A.servir(d, abrir=False, puerto=0)
    t = threading.Thread(target=run, daemon=True); t.start()
    import time
    for _ in range(50):
        m = re.search(r"http://127.0.0.1:(\d+)/\?k=(\S+)", buf.getvalue())
        if m:
            break
        time.sleep(0.1)
    puerto, tok = m.group(1), m.group(2)
    base = f"http://127.0.0.1:{puerto}"
    with pytest.raises(urllib.error.HTTPError) as ei:
        urllib.request.urlopen(base + "/?k=incorrecto")
    assert ei.value.code == 403
    assert b"JB-Activador" in urllib.request.urlopen(f"{base}/?k={tok}").read()
    datos = urllib.parse.urlencode({"entidad": "<script>x</script>", "equipo": L.id_equipo(), "vig": "dias", "dias": "10"}).encode()
    pag = urllib.request.urlopen(urllib.request.Request(f"{base}/emitir?k={tok}", datos)).read().decode()
    assert "JBP1." in pag and "<script>x</script>" not in pag and "&lt;script&gt;" in pag      # escapado contra XSS
    urllib.request.urlopen(urllib.request.Request(f"{base}/cerrar?k={tok}", b""))
