"""Actualizar una base de la versión anterior (sin las columnas/tablas nuevas) no debe perder datos."""
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _py(codigo, datos):
    env = {**os.environ, "GAM_DATA_DIR": datos, "PYTHONPATH": str(RAIZ)}
    env.pop("GAM_DATABASE_URL", None)
    r = subprocess.run([sys.executable, "-c", codigo], env=env, capture_output=True, text=True, cwd=RAIZ)
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


def test_actualizacion_desde_esquema_anterior():
    datos = tempfile.mkdtemp()
    _py("from app.db import init_db; init_db()", datos)                           # crea el esquema actual
    db = Path(datos) / "gam_personal.db"
    con = sqlite3.connect(db)
    con.execute("INSERT INTO usuario(username,nombre,password_hash,rol,activo) VALUES('viejo','Usuario previo','x','ADMIN',1)")
    con.execute("INSERT INTO empleado(codigo,ci,complemento,expedido,nombres,apellidos,cargo,nro_cua,activo) VALUES('1','111','','','Ana','Previa','C','',1)")
    # se simula la versión anterior: se quitan las columnas y tablas añadidas después
    for tabla, col in (("liquidacion", "desc_multas"), ("liquidacion", "horas_permiso"), ("asistencia_dia", "parcial"), ("asistencia_dia", "parcial_sin_goce")):
        con.execute(f"ALTER TABLE {tabla} DROP COLUMN {col}")
    for t in ("memorandum", "memo_plantilla", "memo_config", "ajuste"):
        con.execute(f"DROP TABLE {t}")
    con.commit()
    cols = {r[1] for r in con.execute("PRAGMA table_info(liquidacion)")}
    assert "desc_multas" not in cols
    con.close()
    # arranca la versión nueva sobre la base vieja
    salida = _py("""
from app.db import init_db, SessionLocal, engine
from sqlalchemy import text, inspect
init_db()
insp = inspect(engine)
print('LIQ', sorted(c['name'] for c in insp.get_columns('liquidacion') if c['name'] in ('desc_multas','horas_permiso')))
print('ASIS', sorted(c['name'] for c in insp.get_columns('asistencia_dia') if c['name'] in ('parcial','parcial_sin_goce')))
print('TABLAS', all(insp.has_table(t) for t in ('memorandum','memo_plantilla','memo_config','ajuste')))
with SessionLocal() as s:
    print('USUARIOS', s.execute(text("select count(*) from usuario")).scalar(), 'EMPLEADOS', s.execute(text("select count(*) from empleado")).scalar())
    print('PLANTILLAS', s.execute(text("select count(*) from memo_plantilla")).scalar())
init_db()      # idempotente: una segunda ejecución no falla
print('OK')
""", datos)
    assert "LIQ ['desc_multas', 'horas_permiso']" in salida and "ASIS ['parcial', 'parcial_sin_goce']" in salida
    assert "TABLAS True" in salida and "USUARIOS 1 EMPLEADOS 1" in salida and "PLANTILLAS 3" in salida and salida.strip().endswith("OK")
