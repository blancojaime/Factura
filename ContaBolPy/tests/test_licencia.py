from __future__ import annotations
from datetime import date, timedelta

import pytest
from contabol import _ed25519, licencia


@pytest.fixture(scope="module")
def llaves():
    return licencia.generar_par()


def test_codigo_solicitud_estable_y_con_formato():
    a, b = licencia.codigo_solicitud("equipo-1"), licencia.codigo_solicitud("equipo-2")
    assert a == licencia.codigo_solicitud("equipo-1") and a != b
    assert a.startswith("JB-") and len(a) == 27 and a.count("-") == 5


def test_emision_y_verificacion(llaves):
    pem, pub = llaves
    sol = licencia.codigo_solicitud("pc-cliente")
    cod = licencia.emitir(pem, sol, None)
    assert licencia.verificar(cod, sol, clave_publica_hex=pub) == {"vence": None, "perpetua": True}
    # tolera espacios, minúsculas y saltos de línea al pegar
    pegado = " " + cod.lower().replace("-", "\n") + " "
    assert licencia.verificar(pegado, sol, clave_publica_hex=pub)["perpetua"]
    # otra solicitud (otro equipo) => rechazado
    with pytest.raises(ValueError, match="no corresponde"):
        licencia.verificar(cod, licencia.codigo_solicitud("otro-pc"), clave_publica_hex=pub)
    # código alterado
    mal = cod[:-3] + ("AAA" if not cod.endswith("AAA") else "BBB")
    with pytest.raises(ValueError):
        licencia.verificar(mal, sol, clave_publica_hex=pub)
    # firmado con otra clave
    otra, _ = licencia.generar_par()
    with pytest.raises(ValueError, match="auténtico"):
        licencia.verificar(licencia.emitir(otra, sol, None), sol, clave_publica_hex=pub)
    with pytest.raises(ValueError, match="Ingrese"):
        licencia.verificar("", sol, clave_publica_hex=pub)


def test_vencimiento(llaves):
    pem, pub = llaves
    sol = licencia.codigo_solicitud("pc")
    cod = licencia.emitir(pem, sol, date(2026, 12, 31))
    assert licencia.verificar(cod, sol, date(2026, 12, 31), pub)["vence"] == date(2026, 12, 31)
    with pytest.raises(ValueError, match="venció"):
        licencia.verificar(cod, sol, date(2027, 1, 1), pub)
    with pytest.raises(ValueError):
        licencia.emitir(pem, "JB-1234", None)


def test_estado_prueba_vencida_y_activacion(env, monkeypatch, llaves):
    pem, pub = llaves
    monkeypatch.setattr(licencia, "CLAVE_PUBLICA_HEX", pub)
    sis = env.sis
    hoy = date(2026, 1, 10)
    e = licencia.estado(sis, hoy)
    assert e["modo"] == "prueba" and e["dias"] == licencia.DIAS_PRUEBA
    assert licencia.estado(sis, hoy + timedelta(days=10))["dias"] == licencia.DIAS_PRUEBA - 10
    ven = licencia.estado(sis, hoy + timedelta(days=licencia.DIAS_PRUEBA + 1))
    assert ven["modo"] == "vencida" and not licencia.puede_usarse(ven)
    # activar
    cod = licencia.emitir(pem, licencia.codigo_solicitud(), None)
    with pytest.raises(ValueError):
        licencia.activar(sis, "ABCD")
    licencia.activar(sis, cod)
    a = licencia.estado(sis, hoy + timedelta(days=200))
    assert a["modo"] == "activada" and a["perpetua"] and licencia.puede_usarse(a)
    # adelantar y luego retroceder la fecha del equipo => bloqueada
    b = licencia.estado(sis, hoy)
    assert b["modo"] == "bloqueada"


def test_dialogo_de_activacion(env, monkeypatch, llaves):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    pem, pub = llaves
    monkeypatch.setattr(licencia, "CLAVE_PUBLICA_HEX", pub)
    from contabol.ui.p_activacion import ActivacionDialog, EmisionDialog
    d = ActivacionDialog(env.sis, None, al_inicio=True)
    assert d.c_sol.text() == licencia.codigo_solicitud() and d.b_prueba.isEnabled()
    d.c_cod.setPlainText("CODIGO-INVALIDO")
    d.activar()
    assert d.err.text() and d.est["modo"] == "prueba"
    d.c_cod.setPlainText(licencia.emitir(pem, d.c_sol.text(), None))
    d.activar()
    assert d.est["modo"] == "activada" and not d.err.text()
    e = EmisionDialog()
    import tempfile
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    f.write(pem)
    f.close()
    e.e_clave.setText(f.name)
    e.e_sol.setText(licencia.codigo_solicitud("x"))
    e.generar()
    assert licencia.verificar(e.salida.toPlainText(), licencia.codigo_solicitud("x"), clave_publica_hex=pub)["perpetua"]
    e.e_sol.setText("mal")
    e.generar()
    assert "No se pudo" in e.err.text()
    os.unlink(f.name)
    assert app


def test_ed25519_vectores_rfc8032_y_pem():
    # RFC 8032, prueba 1 (mensaje vacío)
    sec = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pub = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    sig = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert _ed25519.clave_publica(sec) == pub and _ed25519.firmar(sec, b"") == sig and _ed25519.verificar(pub, b"", sig)
    assert not _ed25519.verificar(pub, b"x", sig) and not _ed25519.verificar(pub, b"", sig[:-1] + bytes([sig[-1] ^ 1]))
    assert _ed25519.semilla_desde_pem(_ed25519.pem_desde_semilla(sec)) == sec
    for malo in (b"", b"-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----\n", b"texto cualquiera"):
        with pytest.raises(ValueError):
            _ed25519.semilla_desde_pem(malo)


def test_ed25519_coincide_con_cryptography_si_esta_instalada():
    """En el desarrollo se contrasta con la biblioteca `cryptography`; la edición de Windows 7 no la incluye."""
    pytest.importorskip("cryptography")
    import os
    from cryptography.hazmat.primitives import serialization as S
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    for i in range(8):
        sem, msg = os.urandom(32), os.urandom(i * 11)
        k = Ed25519PrivateKey.from_private_bytes(sem)
        assert _ed25519.firmar(sem, msg) == k.sign(msg)
        assert _ed25519.clave_publica(sem) == k.public_key().public_bytes(S.Encoding.Raw, S.PublicFormat.Raw)
        assert k.private_bytes(S.Encoding.PEM, S.PrivateFormat.PKCS8, S.NoEncryption()) == _ed25519.pem_desde_semilla(sem)


def test_el_paquete_no_depende_de_cryptography():
    """cryptography (Rust) no funciona en Windows 7: el código de la aplicación no debe importarla."""
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parent.parent / "contabol"
    for f in raiz.rglob("*.py"):
        assert "import cryptography" not in f.read_text(encoding="utf-8") and "from cryptography" not in f.read_text(encoding="utf-8"), f
