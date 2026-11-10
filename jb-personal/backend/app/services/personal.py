"""Importación masiva de personal desde plantilla Excel/CSV y generación de la plantilla."""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..models import MODALIDADES, Contrato, Empleado, UnidadOrganizacional
from .biometrico import _decodificar, parse_fecha

COLUMNAS = ["codigo", "ci", "complemento", "nombres", "apellidos", "cargo", "unidad", "modalidad", "partida",
            "haber_basico", "bono_antiguedad", "fecha_ingreso", "fecha_fin", "estado", "nro_cua", "nro_documento"]
TITULOS = ["Código (ID reloj)", "C.I.", "Complemento", "Nombres", "Apellidos", "Cargo", "Unidad Organizacional",
           "Modalidad (Permanente/Eventual/Consultor en Línea)", "Partida", "Haber Básico / Honorario",
           "Bono Antigüedad", "Fecha de Ingreso (dd/mm/aaaa)", "Fecha fin contrato", "Estado (Activo/Inactivo)",
           "N° CUA", "N° Memorándum/Contrato"]
MOD_ALIAS = {"permanente": "PERMANENTE", "planta": "PERMANENTE", "eventual": "EVENTUAL",
             "consultor": "CONSULTOR_LINEA", "consultor en linea": "CONSULTOR_LINEA",
             "consultor de linea": "CONSULTOR_LINEA", "consultor_linea": "CONSULTOR_LINEA",
             "consultor individual de linea": "CONSULTOR_LINEA"}
PARTIDA_DEF = {"PERMANENTE": "11000", "EVENTUAL": "12100", "CONSULTOR_LINEA": "25200"}


def _n(s) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def plantilla_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Personal"
    ws.append(TITULOS)
    ws.append(["1001", "1234567", "", "Juan", "Pérez Mamani", "Técnico", "Unidad de Obras", "Permanente", "11000",
               6000, 0, "01/02/2025", "", "Activo", "", ""])
    for i, w in enumerate([14, 12, 12, 18, 22, 28, 28, 26, 10, 16, 14, 18, 16, 16, 12, 20], 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    for c in ws[1]:
        c.font = openpyxl.styles.Font(bold=True)
        c.alignment = openpyxl.styles.Alignment(wrap_text=True)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _filas(nombre: str, data: bytes) -> list[list]:
    if nombre.lower().endswith((".xlsx", ".xlsm")):
        ws = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True).worksheets[0]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    txt = _decodificar(data)
    delim = max([",", ";", "\t"], key=lambda d: txt.splitlines()[0].count(d))
    return list(csv.reader(io.StringIO(txt), delimiter=delim))


def _dec(v) -> Decimal:
    if v in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(v).replace(",", ".").strip())
    except InvalidOperation:
        raise ValueError(f"monto inválido: {v!r}")


def _fecha(v):
    if v in (None, ""):
        return None
    return parse_fecha(v)


def importar_personal(db: Session, nombre: str, data: bytes, usuario: str) -> dict:
    filas = _filas(nombre, data)
    if len(filas) < 2:
        raise ValueError("El archivo no tiene filas de datos")
    cab = [_n(c) for c in filas[0]]
    # el encabezado puede ser el título largo de la plantilla o el nombre corto de columna
    idx = {}
    for k, tit in zip(COLUMNAS, TITULOS):
        corto = _n(tit).split(" (")[0]
        for i, c in enumerate(cab):
            if k not in idx and (c == k or c == _n(tit) or c == corto):
                idx[k] = i
    faltan = [k for k in ("ci", "nombres", "apellidos", "modalidad", "haber_basico", "fecha_ingreso") if k not in idx]
    if faltan:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltan)}")
    res = {"creados": 0, "actualizados": 0, "errores": []}
    unidades = {u.nombre.lower(): u for u in db.execute(select(UnidadOrganizacional)).scalars()}
    for n, f in enumerate(filas[1:], start=2):
        if not f or all(c in (None, "") for c in f):
            continue
        g = lambda k: (f[idx[k]] if k in idx and idx[k] < len(f) and f[idx[k]] is not None else "")  # noqa: E731
        try:
            ci = str(g("ci")).strip().split(".")[0] if isinstance(g("ci"), float) else str(g("ci")).strip()
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ci or "-"):
                raise ValueError(f"C.I. con caracteres no permitidos: {ci!r}")
            if not ci or not str(g("nombres")).strip() or not str(g("apellidos")).strip():
                raise ValueError("C.I., nombres y apellidos son obligatorios")
            mod = MOD_ALIAS.get(_n(g("modalidad")).replace("_", " ")) or MOD_ALIAS.get(_n(g("modalidad")))
            if mod not in MODALIDADES:
                raise ValueError(f"modalidad inválida: {g('modalidad')!r}")
            haber = _dec(g("haber_basico"))
            if haber <= 0:
                raise ValueError("haber/honorario debe ser mayor a 0")
            ingreso = _fecha(g("fecha_ingreso"))
            if not ingreso:
                raise ValueError("fecha de ingreso obligatoria")
            fin = _fecha(g("fecha_fin"))
            if fin and fin < ingreso:
                raise ValueError("fecha fin anterior al ingreso")
            activo = _n(g("estado")) not in ("inactivo", "baja", "0", "no")
            comp = str(g("complemento")).strip()
            codigo = str(g("codigo")).strip().split(".")[0] if g("codigo") != "" else ci
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", codigo):
                raise ValueError(f"código de reloj con caracteres no permitidos: {codigo!r}")
            unidad = None
            if str(g("unidad")).strip():
                nm = str(g("unidad")).strip()
                unidad = unidades.get(nm.lower())
                if not unidad:
                    unidad = UnidadOrganizacional(nombre=nm)
                    db.add(unidad)
                    db.flush()
                    unidades[nm.lower()] = unidad
            emp = db.execute(select(Empleado).where(Empleado.ci == ci, Empleado.complemento == comp)).scalars().first()
            nuevo = emp is None
            if nuevo:
                dup = db.execute(select(Empleado).where(Empleado.codigo == codigo)).scalars().first()
                if dup:
                    raise ValueError(f"el código de reloj {codigo} ya pertenece a otra persona")
                emp = Empleado(codigo=codigo, ci=ci, complemento=comp)
                db.add(emp)
            emp.nombres, emp.apellidos = str(g("nombres")).strip(), str(g("apellidos")).strip()
            emp.cargo, emp.unidad, emp.activo = str(g("cargo")).strip(), unidad, activo
            emp.nro_cua = str(g("nro_cua")).strip()
            db.flush()
            c = next((x for x in emp.contratos if x.fecha_inicio == ingreso and x.modalidad == mod), None)
            if c is None:
                c = Contrato(empleado_id=emp.id, fecha_inicio=ingreso, modalidad=mod, haber_basico=haber)
                db.add(c)
            c.haber_basico, c.bono_antiguedad, c.fecha_fin = haber, _dec(g("bono_antiguedad")), fin
            c.partida = str(g("partida")).strip().split(".")[0] or PARTIDA_DEF[mod]
            c.aplica_aporte = mod != "CONSULTOR_LINEA"
            c.nro_documento = str(g("nro_documento")).strip()
            if not activo and not c.fecha_baja:
                c.fecha_baja = date.today()
                c.causal_baja = c.causal_baja or "OTRO"
            res["creados" if nuevo else "actualizados"] += 1
        except Exception as e:  # una fila mala no detiene la carga: se informa
            res["errores"].append(f"Fila {n}: {e}")
    audit.registrar(db, usuario, "IMPORTAR_PERSONAL", "empleado", "", {"archivo": nombre, **{k: (v if k != 'errores' else len(v)) for k, v in res.items()}})
    return res
