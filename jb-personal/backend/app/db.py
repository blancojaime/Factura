"""Motor de base de datos, sesión y triggers de inalterabilidad de la bitácora."""
from __future__ import annotations

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from . import config
from .models import Base

_kw = {}
if config.DATABASE_URL.startswith("sqlite"):
    _kw["connect_args"] = {"check_same_thread": False, "timeout": 30}
engine = create_engine(config.DATABASE_URL, future=True, **_kw)

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_con, _):            # integridad referencial y concurrencia razonable
        cur = dbapi_con.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

TRIGGERS_SQLITE = [
    "CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log "
    "BEGIN SELECT RAISE(ABORT,'audit_log es inalterable'); END",
    "CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log "
    "BEGIN SELECT RAISE(ABORT,'audit_log es inalterable'); END",
    "CREATE TRIGGER IF NOT EXISTS marca_no_update BEFORE UPDATE ON marca "
    "BEGIN SELECT RAISE(ABORT,'las marcas biometricas son inalterables'); END",
]
TRIGGERS_PG = [
    "CREATE OR REPLACE FUNCTION gam_inalterable() RETURNS trigger AS $$ BEGIN "
    "RAISE EXCEPTION 'registro inalterable'; END; $$ LANGUAGE plpgsql",
    "DROP TRIGGER IF EXISTS audit_no_mod ON audit_log",
    "CREATE TRIGGER audit_no_mod BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION gam_inalterable()",
    "DROP TRIGGER IF EXISTS marca_no_upd ON marca",
    "CREATE TRIGGER marca_no_upd BEFORE UPDATE ON marca FOR EACH ROW EXECUTE FUNCTION gam_inalterable()",
]


def triggers_for(dialect: str) -> list[str]:
    return TRIGGERS_PG if dialect == "postgresql" else TRIGGERS_SQLITE


def migrar_columnas(con) -> list[str]:
    """Agrega a las tablas EXISTENTES las columnas nuevas del modelo (actualización de versiones sin perder datos)."""
    insp, hechas = inspect(con), []
    for t in Base.metadata.sorted_tables:
        if not insp.has_table(t.name):
            continue
        existentes = {c["name"] for c in insp.get_columns(t.name)}
        for c in t.columns:
            if c.name in existentes:
                continue
            tipo = c.type.compile(dialect=con.dialect)
            dflt = ""
            if c.server_default is not None:
                dflt = f" DEFAULT {c.server_default.arg.text if hasattr(c.server_default.arg, 'text') else c.server_default.arg}"
            elif not c.nullable:
                dflt = " DEFAULT ''" if "CHAR" in tipo.upper() or "TEXT" in tipo.upper() else " DEFAULT 0"
            con.execute(text(f"ALTER TABLE {t.name} ADD COLUMN {c.name} {tipo}{dflt}"))
            hechas.append(f"{t.name}.{c.name}")
    return hechas


def init_db() -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as con:
        migrar_columnas(con)
    with engine.begin() as con:
        for stmt in triggers_for(engine.dialect.name):
            con.execute(text(stmt))
    from .seed import seed_defaults
    with SessionLocal() as s:
        seed_defaults(s)
        s.commit()


def get_db():
    with SessionLocal() as s:
        try:
            yield s
        except Exception:
            s.rollback()
            raise
