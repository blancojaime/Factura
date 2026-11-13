"""Recorre el caso de servicio (Bs 32.000) sobre una base SQLite temporal y deja los PDF del expediente en una carpeta.

Uso:  python scripts/generar_expediente_demo.py [carpeta_salida]
Sirve para revisar visualmente los documentos sin levantar Docker.
"""
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import seeds  # noqa: E402
from app.database import Base, get_db, make_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ContratacionMenor  # noqa: E402
from app.services.storage import LocalStorage, set_storage  # noqa: E402
from tests.helpers import Flujo, ahora_mas  # noqa: E402


def main() -> None:
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="expediente_"))
    salida.mkdir(parents=True, exist_ok=True)
    eng = make_engine("sqlite://")
    Base.metadata.create_all(eng)
    Sess = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    with Sess() as s:
        seeds.cargar(s)
        s.commit()
    set_storage(LocalStorage(str(salida / "_storage")))

    def _db():
        s = Sess()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    tokens = {}
    for u in ("solicitante", "presupuesto", "contrataciones", "rpa", "recepcion", "admin"):
        r = client.post("/api/v1/auth/login", json={"username": u, "password": seeds.PASSWORD_DEMO})
        tokens[u] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    f = Flujo(client, tokens)
    cid = f.crear("Mantenimiento correctivo de las instalaciones eléctricas del edificio municipal", "SERVICIO_GENERAL", 12)["id"]
    f.item(cid, "25800", "Mantenimiento correctivo de instalaciones eléctricas (mano de obra y materiales)", "Global", 1, "32000.00")
    f.accion(cid, "solicitar", "solicitante")
    f.accion(cid, "certificar", "presupuesto", json={"preventivo_c31_nro": "C31-2026-00456"})
    f.accion(cid, "aprobar-inicio", "rpa")
    f.req("PUT", f"/contrataciones/{cid}/formulario-110", "contrataciones", 200, json={
        "nro_formulario_110": "F110-2026-000457", "fecha_limite_ofertas": ahora_mas(hours=2)})
    f.req("POST", f"/contrataciones/{cid}/fichas-cotizacion", "contrataciones", 200, json={
        "destinatarios": [{"razon_social": "ELECTRO SERVICIOS S.R.L."}, {"razon_social": "INSTALACIONES BOLIVIA LTDA."}],
        "canales": ["IMPRESO"]})
    for nit, razon, monto, plazo in (("1020304050", "ELECTRO SERVICIOS S.R.L.", "31500", 12),
                                     ("2030405060", "INSTALACIONES BOLIVIA LTDA. (MyPE)", "30800", 10),
                                     ("3040506070", "MANTENIMIENTO INTEGRAL S.A.", "29900", 12),
                                     ("4050607080", "OFERTAS BARATAS S.R.L.", "28000", 12)):
        f.req("POST", f"/contrataciones/{cid}/cotizaciones", "contrataciones", 201, json={
            "nit_ci": nit, "razon_social": razon, "monto_total_ofertado": monto, "plazo_ofertado_dias": plazo})
    with Sess() as s:
        c = s.scalar(select(ContratacionMenor).where(ContratacionMenor.id == __import__("uuid").UUID(cid)))
        c.fecha_limite_ofertas = datetime.now(timezone.utc) - timedelta(minutes=1)
        s.commit()
    f.accion(cid, "abrir-ofertas", "contrataciones")
    for q in f.detalle(cid)["cotizaciones"]:
        datos = {"cumple_especificaciones": q["nit_ci"] != "4050607080"}
        if q["nit_ci"] == "2030405060":
            datos.update(registro_preferencia="MYPE", registro_preferencia_valido=True, margen_preferencia_pct="5")
        f.req("PATCH", f"/contrataciones/{cid}/cotizaciones/{q['id']}", "contrataciones", 200, json=datos)
    f.accion(cid, "evaluar", "contrataciones")
    f.accion(cid, "adjudicar", "rpa", json={})
    f.accion(cid, "formalizar", "rpa", json={"cuce": "26-1234-00-1234567-1-1"})
    hoy = datetime.now().date().isoformat()
    f.accion(cid, "recepcion", "recepcion", json={"fecha_recepcion": hoy, "conforme": True, "observaciones": ""})
    c = f.detalle(cid)
    for d in c["documentos"]:
        pdf = f.req("GET", f"/contrataciones/{cid}/documentos/{d['id']}/descargar", "rpa", 200).content
        (salida / f"{d['tipo_doc']}_v{d['version']}.pdf").write_bytes(pdf)
    print(f"{len(c['documentos'])} documentos en {salida}")


if __name__ == "__main__":
    main()
