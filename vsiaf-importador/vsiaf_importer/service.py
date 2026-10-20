"""Punto de entrada de alto nivel usado por la interfaz gráfica y por la línea de comandos."""
from __future__ import annotations

import datetime as dt
import os
import tempfile
from typing import Callable, Optional, Tuple

from .excelio import build_template, read_workbook
from .importer import ImportAbort, Importer, Options, Result
from .report import write_report
from .ufv import UfvTable, load_ufv
from .vsiafdb import VsiafDb


def open_db(install_dir: str) -> Tuple[VsiafDb, UfvTable]:
    db = VsiafDb(install_dir)
    return db, load_ufv(install_dir, db.dbfs_dir)


def create_template(path: str, install_dir: Optional[str] = None, ejemplos: bool = False) -> None:
    if install_dir:
        db = VsiafDb(install_dir)
        cats = (db.grupos(), db.estados(), db.motivos_baja(), db.organismos(), db.departamentos())
    else:
        from .vsiafdb import load_bundled_catalogs
        c = load_bundled_catalogs()
        cats = (c["grupos"], c["estados"], c["motivos_baja"], c["organismos_financiadores"], c["departamentos"])
    from .demo import demo_rows
    build_template(path, *cats, ejemplos=demo_rows() if ejemplos else None)


def default_report_path(xlsx: str, mode: str) -> str:
    folder = os.path.dirname(os.path.abspath(xlsx))
    name = f"informe_{'validacion' if mode == 'validación' else 'importacion'}_{dt.datetime.now():%Y%m%d_%H%M%S}.xlsx"
    if not os.access(folder, os.W_OK):
        folder = tempfile.gettempdir()
    return os.path.join(folder, name)


def run(install_dir: str, xlsx: str, options: Options, apply: bool,
        report_path: Optional[str] = None, log: Optional[Callable[[str], None]] = None) -> Tuple[Result, str]:
    """Valida (y opcionalmente importa) un libro.  Devuelve (resultado, ruta del informe)."""
    log = log or (lambda m: None)
    log("Abriendo la base del VSIAF…")
    db, ufv = open_db(install_dir)
    log(f"UFV: {len(ufv)} índices ({ufv.source})")
    log("Leyendo el libro Excel…")
    wb = read_workbook(xlsx)
    imp = Importer(db, ufv, options, log)
    res = imp.plan(wb)
    mode = "validación"
    err: Optional[str] = None
    if apply:
        mode = "importación"
        try:
            log("Escribiendo en la base del VSIAF…")
            imp.apply(xlsx)
            log("Importación terminada.")
        except ImportAbort as e:
            err = str(e)
            res.notes.append(err)
    path = report_path or default_report_path(xlsx, mode)
    write_report(path, imp, res, xlsx, mode)
    if err:
        raise ImportAbortWithResult(err, res, path)
    return res, path


class ImportAbortWithResult(ImportAbort):
    def __init__(self, msg: str, res: Result, report: str):
        super().__init__(msg)
        self.result, self.report = res, report
