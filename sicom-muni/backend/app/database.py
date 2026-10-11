"""Motor SQLAlchemy 2.0 y sesion por peticion."""
from collections.abc import Iterator

from decimal import Decimal

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    url = url or get_settings().database_url
    if url.startswith("sqlite"):
        if url in ("sqlite://", "sqlite:///:memory:"):
            # En memoria (pruebas): una unica conexion compartida
            return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        # Archivo local (modo de prueba sin Docker/PostgreSQL)
        return create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def preparar_sqlite() -> None:
    """Modo de prueba local: si la base es un archivo SQLite, crea las tablas (en PostgreSQL se usa Alembic)."""
    if engine.url.get_backend_name() == "sqlite" and engine.url.database not in (None, "", ":memory:"):
        from . import models  # noqa: F401  (registra las tablas)
        Base.metadata.create_all(engine)
        _agregar_columnas_faltantes()


def _literal(valor) -> str:
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, int | float | Decimal):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def _agregar_columnas_faltantes() -> None:
    """SQLite local: agrega las columnas nuevas a bases creadas con una version anterior (sin Alembic)."""
    insp = inspect(engine)
    with engine.begin() as con:
        for tabla in Base.metadata.sorted_tables:
            if not insp.has_table(tabla.name):
                continue
            existentes = {c["name"] for c in insp.get_columns(tabla.name)}
            for col in tabla.columns:
                if col.name in existentes:
                    continue
                ddl = f'ALTER TABLE "{tabla.name}" ADD COLUMN "{col.name}" {col.type.compile(engine.dialect)}'
                if not col.nullable:
                    arg = col.default.arg if col.default is not None and getattr(col.default, "is_scalar", False) else None
                    ddl += f" DEFAULT {_literal(arg if arg is not None else '')}"
                con.execute(text(ddl))
