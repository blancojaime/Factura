import datetime as dt

import pytest

from vsiaf_importer.dbf import DbfError, DbfTable, create_table

SPEC = [("CODIGO", "C", 10, 0), ("COSTO", "N", 12, 2), ("CANT", "N", 3, 0), ("FECHA", "D", 8, 0),
        ("OK", "L", 1, 0), ("OBS", "M", 10, 0)]


def mk(tmp_path, lang=0x03):
    p = str(tmp_path / "T.DBF")
    create_table(p, SPEC, lang=lang)
    return p


def test_roundtrip_types_and_memo(tmp_path):
    p = mk(tmp_path)
    t = DbfTable(p)
    n = t.append(dict(CODIGO="A-1", COSTO=1234.567, CANT=7, FECHA=dt.date(2026, 3, 9), OK=True, OBS="Ñandú á é"))
    assert n == 1
    t.append(dict(CODIGO="A-2", COSTO=-5, CANT=0, OK=False))
    t.save()
    t2 = DbfTable(p)
    assert t2.nrec == 2
    r = t2.read(1)
    assert r["CODIGO"] == "A-1" and r["COSTO"] == 1234.57 and r["CANT"] == 7
    assert r["FECHA"] == dt.date(2026, 3, 9) and r["OK"] is True and r["OBS"] == "Ñandú á é"
    r2 = t2.read(2)
    assert r2["COSTO"] == -5.0 and r2["FECHA"] is None and r2["OBS"] is None and r2["OK"] is False
    assert open(p, "rb").read()[-1:] == b"\x1a"


def test_update_delete_and_overflow(tmp_path):
    p = mk(tmp_path)
    t = DbfTable(p)
    t.append(dict(CODIGO="X", COSTO=1, CANT=1))
    t.update(1, dict(COSTO=99.5, OBS="memo largo " * 30))
    t.set_deleted(1)
    t.save()
    t2 = DbfTable(p)
    assert t2.read(1).deleted and t2.read(1)["COSTO"] == 99.5
    assert t2.read(1)["OBS"].startswith("memo largo")
    assert list(t2.records()) == [] and len(list(t2.records(include_deleted=True))) == 1
    with pytest.raises(DbfError):
        t2.append(dict(CODIGO="DEMASIADO LARGO!!"))
    with pytest.raises(DbfError):
        t2.append(dict(CODIGO="X", CANT=12345))
    with pytest.raises(DbfError):
        t2.append(dict(NOEXISTE=1))


def test_cp850_encoding(tmp_path):
    p = mk(tmp_path, lang=0x02)
    t = DbfTable(p)
    t.append(dict(CODIGO="Ñ"))
    t.save()
    raw = open(p, "rb").read()
    assert b"\xa5" in raw            # Ñ en cp850
    assert DbfTable(p).read(1)["CODIGO"] == "Ñ"


def test_nothing_written_if_not_saved(tmp_path):
    p = mk(tmp_path)
    before = open(p, "rb").read()
    t = DbfTable(p)
    t.append(dict(CODIGO="Z"))
    assert open(p, "rb").read() == before


def test_readable_by_independent_library(tmp_path):
    dbfread = pytest.importorskip("dbfread")
    p = mk(tmp_path)
    t = DbfTable(p)
    t.append(dict(CODIGO="IND", COSTO=10.25, CANT=3, FECHA=dt.date(2025, 1, 31), OK=True, OBS="observación"))
    t.save()
    rows = list(dbfread.DBF(p, encoding="cp1252", load=True))
    assert rows[0]["CODIGO"] == "IND" and rows[0]["COSTO"] == 10.25 and rows[0]["OBS"] == "observación"
    assert rows[0]["FECHA"] == dt.date(2025, 1, 31)
