from datetime import date, timedelta

import pytest
from cryptography.hazmat.primitives import serialization as S
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from contabol import licencia


@pytest.fixture(scope="module")
def llaves():
    k = Ed25519PrivateKey.generate()
    return (k.private_bytes(S.Encoding.PEM, S.PrivateFormat.PKCS8, S.NoEncryption()), k.public_key().public_bytes(S.Encoding.Raw, S.PublicFormat.Raw).hex())


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
    otra = Ed25519PrivateKey.generate().private_bytes(S.Encoding.PEM, S.PrivateFormat.PKCS8, S.NoEncryption())
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
