import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from siim.core import demo, security, seed
from siim.core.db import Database
from siim.services.base import Ctx


@pytest.fixture()
def db(tmp_path):
    d = Database(tmp_path / "t.db")
    seed.seed_base(d)
    demo.cargar_cotizaciones_demo(d)
    yield d
    d.close()


@pytest.fixture()
def ctx(db):
    security.create_user(db, "admin", "Admin", "ADMINISTRADOR", "Clave2026x")
    return Ctx(db, security.login(db, "admin", "Clave2026x"))


@pytest.fixture()
def ids(ctx):
    return demo.cargar_padron_demo(ctx)
