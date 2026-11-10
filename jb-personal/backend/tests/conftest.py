import os
import sys
import tempfile
from pathlib import Path

import pytest

TMP = tempfile.mkdtemp(prefix="gam_test_")
os.environ["GAM_DATA_DIR"] = TMP
os.environ["GAM_SECRET_KEY"] = "clave-de-pruebas-" + "x" * 32
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DATOS = Path(__file__).resolve().parents[2] / "datos_prueba"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/api/auth/setup", json={"username": "admin", "password": "Admin#2026!", "nombre": "Administrador"})
        assert r.status_code == 200, r.text
        c.headers["Authorization"] = "Bearer " + r.json()["token"]
        yield c
