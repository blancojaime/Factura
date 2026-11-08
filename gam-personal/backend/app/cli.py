"""Herramientas de línea de comandos (cron / Programador de tareas de Windows).

  python -m app.cli backup  [--destino RUTA]        contraseña en la variable GAM_BACKUP_PASSWORD
  python -m app.cli verificar ARCHIVO.sql.enc       (usa ARCHIVO.sql.enc.sha256 si existe; GAM_BACKUP_PASSWORD opcional)
  python -m app.cli restaurar ARCHIVO.sql.enc       (SQLite; pide hash del .sha256 contiguo)
  python -m app.cli ddl [--salida db/]              exporta el esquema SQL de SQLite y PostgreSQL
  python -m app.cli retencion --dias 60             borra respaldos .sql.enc más antiguos que N días
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def _ddl(salida: Path):
    from sqlalchemy.dialects import postgresql, sqlite
    from sqlalchemy.schema import CreateIndex, CreateTable
    from .db import TRIGGERS_PG, TRIGGERS_SQLITE
    from .models import Base
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, dialecto, trig in (("sqlite", sqlite.dialect(), TRIGGERS_SQLITE), ("postgresql", postgresql.dialect(), TRIGGERS_PG)):
        partes = [f"-- Esquema del Sistema de Gestión de Personal y Asistencia Municipal ({nombre})",
                  "-- Generado desde app/models.py (python -m app.cli ddl). No editar a mano.\n"]
        if nombre == "sqlite":
            partes.append("PRAGMA foreign_keys = ON;\n")
        for t in Base.metadata.sorted_tables:
            partes.append(str(CreateTable(t).compile(dialect=dialecto)).strip() + ";\n")
            for ix in sorted(t.indexes, key=lambda i: i.name or ""):
                partes.append(str(CreateIndex(ix).compile(dialect=dialecto)).strip() + ";")
            partes.append("")
        partes.append("-- Inalterabilidad de la bitácora y de las marcas biométricas (SAFCO)")
        partes += [s + ";" for s in trig]
        (salida / f"schema_{nombre}.sql").write_text("\n".join(partes) + "\n", encoding="utf-8")
        print("escrito", salida / f"schema_{nombre}.sql")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m app.cli")
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("backup"); b.add_argument("--destino")
    v = sp.add_parser("verificar"); v.add_argument("archivo")
    r = sp.add_parser("restaurar"); r.add_argument("archivo")
    d = sp.add_parser("ddl"); d.add_argument("--salida", default="db")
    n = sp.add_parser("retencion"); n.add_argument("--dias", type=int, default=60)
    a = ap.parse_args(argv)

    if a.cmd == "ddl":
        return _ddl(Path(a.salida))
    from . import config
    from .services import backup as bk
    pw = os.environ.get("GAM_BACKUP_PASSWORD", "")
    try:
        if a.cmd == "backup":
            from .db import SessionLocal, init_db
            init_db()
            with SessionLocal() as s:
                res = bk.crear_respaldo(s, pw, "cli", "PROGRAMADO", Path(a.destino) if a.destino else None)
                s.commit()
            print("Respaldo creado:", res["ruta"], "SHA-256:", res["sha256"])
        elif a.cmd in ("verificar", "restaurar"):
            f = Path(a.archivo)
            sha_f = Path(str(f) + ".sha256")
            sha = sha_f.read_text().split()[0] if sha_f.exists() else None
            if a.cmd == "restaurar" and not sha:
                sys.exit("No se restaura sin el archivo .sha256 contiguo (verificación de integridad obligatoria)")
            res = (bk.verificar_respaldo(f.read_bytes(), sha, pw or None) if a.cmd == "verificar"
                   else bk.restaurar_sqlite(f.read_bytes(), sha, pw))
            print(res)
        elif a.cmd == "retencion":
            limite = time.time() - a.dias * 86400
            n_ = 0
            for f in config.BACKUP_DIR.glob("gam_backup_*.sql.enc*"):
                if f.stat().st_mtime < limite:
                    f.unlink()
                    n_ += 1
            print("Eliminados:", n_)
    except bk.BackupError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
