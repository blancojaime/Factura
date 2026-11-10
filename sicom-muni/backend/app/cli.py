"""Herramientas de linea de comandos para la instalacion y el mantenimiento (usadas por el instalador de Windows).

  python -m app.cli inicializar        # migra la base, configura la entidad y crea el administrador (idempotente)
  python -m app.cli id-equipo          # muestra el ID del equipo para solicitar la licencia
  python -m app.cli licencia           # estado de la licencia
  python -m app.cli activar-licencia ARCHIVO
  python -m app.cli restablecer-clave USUARIO   (nueva clave en la variable SICOM_NUEVA_CLAVE)
  python -m app.cli probar-pdf SALIDA.pdf       (comprueba el motor de PDF y el codigo QR)

Los datos sensibles se reciben por variables de entorno (no por la linea de comandos).
"""
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path


def _alembic() -> None:
    from alembic import command
    from alembic.config import Config

    raiz = Path(__file__).resolve().parent.parent
    cfg = Config(str(raiz / "alembic.ini"))
    cfg.set_main_option("script_location", str(raiz / "alembic"))
    command.upgrade(cfg, "head")


def _migrar() -> str:
    from .database import SessionLocal, engine, preparar_sqlite  # noqa: F401

    if engine.url.get_backend_name() == "sqlite":
        preparar_sqlite()
        return "sqlite"
    _alembic()
    return "postgresql"


def cmd_inicializar(a) -> int:
    from sqlalchemy import select

    from . import security, seeds
    from .database import SessionLocal
    from .enums import Rol
    from .models import Usuario
    from .services import parametros

    motor = _migrar()
    entidad = os.environ.get("SICOM_ENTIDAD", "").strip()
    ciudad = os.environ.get("SICOM_CIUDAD", "").strip()
    usuario = os.environ.get("SICOM_ADMIN_USUARIO", "admin").strip() or "admin"
    clave = os.environ.get("SICOM_ADMIN_CLAVE", "")
    resultado = {"motor": motor, "administrador": "existente", "demo": False}
    with SessionLocal() as db:
        if a.demo:
            seeds.cargar(db, gestion=int(a.gestion))
            resultado["demo"] = True
        if entidad:
            parametros.guardar(db, "nombre_gam", entidad)
        if ciudad:
            parametros.guardar(db, "ciudad", ciudad)
        parametros.guardar(db, "gestion", str(a.gestion))
        existe = db.scalar(select(Usuario).where(Usuario.username == usuario))
        if existe is None and clave:
            err = security.password_error(clave)
            if err:
                print(f"ERROR: la contraseña del administrador no es válida: {err}", file=sys.stderr)
                return 2
            db.add(Usuario(username=usuario, password_hash=security.hash_password(clave), nombre_completo="Administrador del Sistema",
                           cargo="Administrador", rol=Rol.ADMIN.value, email=""))
            resultado["administrador"] = "creado"
        elif existe is None:
            print("ERROR: falta SICOM_ADMIN_CLAVE para crear el administrador", file=sys.stderr)
            return 2
        db.commit()
    print(json.dumps(resultado))
    return 0


def cmd_id_equipo(_a) -> int:
    from .services import licencia_core

    print(licencia_core.id_equipo())
    return 0


def cmd_licencia(_a) -> int:
    from .database import SessionLocal
    from .services import licencia

    with SessionLocal() as db:
        print(json.dumps(licencia.estado(db, forzar=True), ensure_ascii=False, indent=2))
    return 0


def cmd_activar(a) -> int:
    from fastapi import HTTPException

    from .database import SessionLocal
    from .services import licencia

    texto = Path(a.archivo).read_text(encoding="utf-8-sig")
    with SessionLocal() as db:
        try:
            e = licencia.activar(db, texto)
        except HTTPException as exc:
            print(f"ERROR: {exc.detail}", file=sys.stderr)
            return 2
    print(json.dumps(e, ensure_ascii=False, indent=2))
    return 0


def cmd_restablecer(a) -> int:
    from sqlalchemy import select

    from . import security
    from .database import SessionLocal
    from .models import Usuario

    clave = os.environ.get("SICOM_NUEVA_CLAVE", "")
    err = security.password_error(clave)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        u = db.scalar(select(Usuario).where(Usuario.username == a.usuario))
        if u is None:
            print("ERROR: el usuario no existe", file=sys.stderr)
            return 2
        u.password_hash, u.intentos_fallidos, u.bloqueado_hasta, u.activo = security.hash_password(clave), 0, None, True
        db.commit()
    print("Contraseña restablecida")
    return 0


def cmd_probar_pdf(a) -> int:
    from .services import generador_pdf as g

    if not g.PDF_DISPONIBLE:
        print("ERROR: el motor de PDF (WeasyPrint/Pango) no está disponible", file=sys.stderr)
        return 3
    qr = g.qr_data_uri("http://localhost:8080/verificar/prueba")
    html = (f"<html><body><h1>SICOM-MUNI — prueba de PDF</h1><p>Ñandú, canción, año {date.today().year}.</p>"
            f"<img src='{qr}' width='120'></body></html>")
    pdf = g.HTML(string=html, url_fetcher=g._SoloImagenesEmbebidas()).write_pdf()
    Path(a.salida).write_bytes(pdf)
    print(f"PDF generado: {a.salida} ({len(pdf)} bytes)")
    return 0 if pdf.startswith(b"%PDF") else 4


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inicializar")
    p.add_argument("--demo", action="store_true", help="carga usuarios y datos de demostración")
    p.add_argument("--gestion", default=str(date.today().year))
    p.set_defaults(fn=cmd_inicializar)
    sub.add_parser("id-equipo").set_defaults(fn=cmd_id_equipo)
    sub.add_parser("licencia").set_defaults(fn=cmd_licencia)
    p = sub.add_parser("activar-licencia")
    p.add_argument("archivo")
    p.set_defaults(fn=cmd_activar)
    p = sub.add_parser("restablecer-clave")
    p.add_argument("usuario")
    p.set_defaults(fn=cmd_restablecer)
    p = sub.add_parser("probar-pdf")
    p.add_argument("salida")
    p.set_defaults(fn=cmd_probar_pdf)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
