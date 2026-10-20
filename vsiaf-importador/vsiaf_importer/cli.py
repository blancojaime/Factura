"""Línea de comandos:  python -m vsiaf_importer  <comando> ...   (sin argumentos abre la ventana)."""
from __future__ import annotations

import argparse
import datetime as dt
import sys

from . import __version__, service
from .excelio import as_date
from .importer import ImportAbort, Options
from .vsiafdb import VsiafDb, detect_installation


def _fecha(s: str) -> dt.date:
    d = as_date(s)
    if d is None:
        raise argparse.ArgumentTypeError("fecha vacía")
    return d


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="importador-vsiaf", description=f"Importador Excel → VSIAF {__version__}")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("plantilla", help="crea el libro Excel de importación")
    a.add_argument("salida")
    a.add_argument("--vsiaf", help="carpeta del VSIAF (para tomar sus catálogos reales)")
    a.add_argument("--ejemplos", action="store_true", help="incluye filas de ejemplo autocontenidas")

    def common(sp):
        sp.add_argument("excel")
        sp.add_argument("--vsiaf", help="carpeta de instalación del VSIAF (por defecto se detecta)")
        sp.add_argument("--unidad", default="", help="unidad por defecto para filas sin columna 'unidad'")
        sp.add_argument("--usuario", default=None, help="usuario que queda en los registros (máx. 8)")
        sp.add_argument("--fecha-calculo", type=_fecha, default=None, help="fecha de la vista previa (dd/mm/aaaa)")
        sp.add_argument("--estado-defecto", choices=["ELABORADO", "APROBADO"], default="ELABORADO")
        sp.add_argument("--informe", help="ruta del informe .xlsx")

    v = sub.add_parser("validar", help="valida el libro sin escribir nada")
    common(v)
    i = sub.add_parser("importar", help="valida e importa a la base del VSIAF")
    common(i)
    i.add_argument("--solo-validas", action="store_true", help="importa las filas correctas aunque otras tengan error")
    i.add_argument("--sin-respaldo", action="store_true", help="NO crear respaldo previo (no recomendado)")

    f = sub.add_parser("info", help="muestra datos de la instalación del VSIAF")
    f.add_argument("--vsiaf")

    args = p.parse_args(argv)
    if args.cmd is None:
        from .gui import run_gui
        run_gui()
        return 0

    if args.cmd == "plantilla":
        service.create_template(args.salida, args.vsiaf, args.ejemplos)
        print(f"Plantilla creada: {args.salida}")
        return 0

    root = args.vsiaf or detect_installation()
    if not root:
        print("No se encontró el VSIAF. Indique la carpeta con --vsiaf.", file=sys.stderr)
        return 2

    if args.cmd == "info":
        db, ufv = service.open_db(root)
        print(f"Carpeta: {root}\nEntidad: {db.entidad} — {db.entidad_nombre}")
        print(f"Gestión cerrada: {'SI' if db.gestion_cerrada() else 'no'}")
        for u in db.unidades():
            print(f"  Unidad {u['unidad']}: {u['descripcion']} ({u['ciudad']})")
        print(f"UFV: {len(ufv)} índices {ufv.first:%d/%m/%Y}–{ufv.last:%d/%m/%Y}; último cambio {ufv.last_change:%d/%m/%Y} ({ufv.source})")
        return 0

    db = VsiafDb(root)
    opt = Options(default_unit=args.unidad, user=(args.usuario or db.usuario_por_defecto)[:8],
                  calc_date=args.fecha_calculo or dt.date.today(), default_state=args.estado_defecto)
    apply = args.cmd == "importar"
    if apply:
        opt.only_valid = args.solo_validas
        opt.make_backup = not args.sin_respaldo
    try:
        res, path = service.run(root, args.excel, opt, apply, args.informe, log=print)
    except ImportAbort as e:
        res, path = getattr(e, "result", None), getattr(e, "report", None)
        print(f"\nNO SE IMPORTÓ: {e}", file=sys.stderr)
        if path:
            print(f"Informe: {path}")
        return 1
    for it in res.issues:
        if it.level in ("ERROR", "AVISO"):
            print(f"[{it.level}] {it.sheet} fila {it.row} {it.column}: {it.message}")
    print(f"\nOperaciones: {res.counts}  Errores: {res.errors}  Avisos: {res.warnings}")
    if res.applied:
        print(f"Respaldo: {res.backup_path}")
        print("IMPORTANTE: abra el VSIAF y ejecute Administradores → Re-indexar.")
    print(f"Informe: {path}")
    return 0 if res.errors == 0 or res.applied else 1


if __name__ == "__main__":
    sys.exit(main())
