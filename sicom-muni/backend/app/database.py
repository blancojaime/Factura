"""Motor SQLAlchemy 2.0 y sesion por peticion."""
from collections.abc import Iterator

from sqlalchemy import create_engine
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
