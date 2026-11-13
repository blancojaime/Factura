from __future__ import annotations
import os
import tempfile

import pytest

from contabol.reports import catalogo, word
from contabol.sistema import ErrorNegocio
from tests.conftest import CAJA, CAPITAL, GASTO_LUZ, VENTAS


def test_eliminar_solo_el_ultimo_del_tipo_y_mes(env):
    a = env.asiento("2025-03-02", CAJA, CAPITAL, 1000)
    b = env.asiento("2025-03-05", CAJA, VENTAS, 500)
    v = env.ctx.vouchers
    with pytest.raises(ErrorNegocio, match="último"):
        v.eliminar(a)
    v.eliminar(b)
    assert v.obtener(b) is None
    v.eliminar(a)                               # ahora a es el último
    assert env.saldo(CAJA, "2025-12-31") == 0
    c = env.asiento("2025-03-09", CAJA, VENTAS, 10)
    assert v.obtener(c)["numero"] == 1          # la numeración se conserva correlativa


def test_revertir_genera_contraasiento(env):
    v = env.ctx.vouchers
    c = env.asiento("2025-04-02", GASTO_LUZ, CAJA, 300, "luz")
    antes = env.saldo(CAJA, "2025-12-31")
    r = v.revertir(c, "2025-04-30")
    assert env.saldo(CAJA, "2025-12-31") == antes + 300       # la caja vuelve a su saldo
    assert v.reversion_de(c)["id"] == r
    assert v.obtener(r)["origen"] == "REVERSION" and "Reversión" in v.obtener(r)["glosa"]
    with pytest.raises(ErrorNegocio, match="ya fue revertido"):
        v.revertir(c)
    with pytest.raises(ErrorNegocio):
        v.revertir(r)                                          # no se revierte una reversión
    with pytest.raises(ErrorNegocio, match="último|revertido"):
        v.eliminar(c)
    v.anular(r)                                               # la reversión sí se puede anular
    assert v.reversion_de(c) is None


def test_informe_control_y_word_de_todos_los_informes(env):
    env.asiento("2025-02-02", CAJA, CAPITAL, 100)
    rep = catalogo.ejecutar(env.ctx, "control_comprobantes", {"estado": "V"})
    assert rep.tablas[0].filas and rep.tablas[0].filas[-1].estilo == "total"
    d = tempfile.mkdtemp()
    ruta = word.exportar(rep, os.path.join(d, "c.docx"))
    from docx import Document
    doc = Document(ruta)
    assert doc.tables and "CONTROL DE COMPROBANTES" in "\n".join(p.text for p in doc.paragraphs)
    # texto libre (dictamen)
    r2_ = word.exportar_texto("Dictamen", "Línea 1\nLínea 2", os.path.join(d, "t.docx"), env.ctx)
    assert len(Document(r2_).paragraphs) >= 4
