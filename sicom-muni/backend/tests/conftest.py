"""Fixtures: base SQLite en memoria (rapida) o PostgreSQL real si se define TEST_DATABASE_URL.

  pytest                                     -> SQLite
  TEST_DATABASE_URL=postgresql+psycopg://... pytest   -> PostgreSQL con migraciones Alembic y trigger de auditoria
"""
import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app import database, seeds, security
from app.database import Base, get_db, make_engine
from app.main import app
from app.services.storage import LocalStorage, set_storage

PG_URL = os.environ.get("TEST_DATABASE_URL", "")
GESTION = date.today().year
USUARIOS = ["solicitante", "presupuesto", "contrataciones", "rpa", "recepcion", "admin"]


@pytest.fixture(scope="session")
def hash_demo() -> str:
    return security.hash_password(seeds.PASSWORD_DEMO)


@pytest.fixture()
def engine():
    if PG_URL:
        from alembic import command
        from alembic.config import Config
        os.environ["DATABASE_URL"] = PG_URL
        from app.config import get_settings
        get_settings.cache_clear()
        cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
        eng = make_engine(PG_URL)
        with eng.begin() as con:
            con.execute(text("DROP SCHEMA public CASCADE"))
            con.execute(text("CREATE SCHEMA public"))
        command.upgrade(cfg, "head")
        yield eng
        eng.dispose()
    else:
        eng = make_engine("sqlite://")
        Base.metadata.create_all(eng)
        yield eng
        eng.dispose()


@pytest.fixture()
def SessionTest(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(SessionTest, hash_demo):
    s = SessionTest()
    seeds.cargar(s, gestion=GESTION, hash_cache=hash_demo)
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def client(SessionTest, db, tmp_path):
    set_storage(LocalStorage(str(tmp_path / "storage")))

    def _get_db():
        s = SessionTest()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    set_storage(None)


@pytest.fixture()
def tokens(client):
    """Inicia sesion con los 6 roles y devuelve {username: headers}."""
    out = {}
    for u in USUARIOS:
        r = client.post("/api/v1/auth/login", json={"username": u, "password": seeds.PASSWORD_DEMO})
        assert r.status_code == 200, r.text
        out[u] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    client.cookies.clear()
    return out
