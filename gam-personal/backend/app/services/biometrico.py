"""Parser de archivos de relojes biométricos (ZKTeco, Anviz, Dahua y exportaciones .csv/.xlsx genéricas).

Formatos soportados
  1. ZKTeco ATTLOG (.dat/.txt sin cabecera):  PIN <tab> AAAA-MM-DD HH:MM:SS <tab> verificación <tab> estado ...
  2. Texto delimitado con cabecera (.csv/.txt; delimitador coma, punto y coma, tabulador o barra)
  3. Excel (.xlsx) con cabecera en cualquiera de las primeras 25 filas (como "1_Marcaciones_Crudas").
La columna "Estado / Incidencia" del reloj se IGNORA: el sistema recalcula todo con sus propias reglas.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time

import openpyxl


@dataclass
class RegMarca:
    identificador: str
    fecha_hora: datetime
    tipo_evento: str = ""
    metodo: str = ""
    dispositivo: str = ""


ZK_STATUS = {"0": "Entrada", "1": "Salida", "2": "Salida Descanso", "3": "Entrada Descanso",
             "4": "Entrada Extra", "5": "Salida Extra"}
ZK_VERIFY = {"0": "Contraseña", "1": "Huella Digital", "2": "Tarjeta", "3": "Tarjeta", "15": "Rostro"}

ALIAS = {
    "id": {"id", "id empleado", "idempleado", "codigo", "cod", "ci", "c.i.", "c.i", "no", "no.", "nro", "numero",
           "person id", "personid", "user id", "userid", "pin", "enroll number", "enrollnumber", "empleado id",
           "id de persona", "id usuario"},
    "fecha": {"fecha", "date", "dia"},
    "hora": {"hora", "time of day"},
    "fechahora": {"fecha y hora", "fecha/hora", "fecha hora", "datetime", "date time", "date/time", "timestamp",
                  "time", "tiempo", "hora de marcacion", "punch time"},
    "tipo": {"tipo de marcacion", "tipo marcacion", "tipo", "evento", "tipo de evento", "punch", "state", "status",
             "punch state", "check type"},
    "metodo": {"metodo verificacion", "metodo de verificacion", "verificacion", "verify", "verification",
               "verify mode", "modo", "metodo"},
    "dispositivo": {"dispositivo", "device", "terminal", "reloj", "device name", "equipo"},
}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", s)


def _mapa_cabecera(celdas) -> dict[str, int] | None:
    m: dict[str, int] = {}
    for i, c in enumerate(celdas):
        n = _norm(c)
        if not n or "incidencia" in n:
            continue
        for k, vals in ALIAS.items():
            if n in vals and k not in m:
                m[k] = i
                break
    if "id" not in m:
        return None
    if "hora" in m and "fecha" not in m and "fechahora" in m:     # "Time" suelto = fecha-hora
        del m["hora"]
    if "fechahora" in m or ("fecha" in m and "hora" in m):
        return m
    return None


_FECHAS = [("%Y-%m-%d", None), ("%Y/%m/%d", None), ("%d/%m/%Y", "dmy"), ("%d-%m-%Y", "dmy"), ("%d.%m.%Y", "dmy"),
           ("%d/%m/%y", "dmy"), ("%d-%m-%y", "dmy"), ("%m/%d/%Y", "mdy"), ("%m-%d-%Y", "mdy")]


def parse_fecha(v, orden: str = "dmy") -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt, o in _FECHAS:
        if o is not None and o != orden:
            continue
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"fecha no reconocida: {s!r}")


def parse_hora(v) -> time:
    if isinstance(v, datetime):
        return v.time().replace(microsecond=0)
    if isinstance(v, time):
        return v.replace(microsecond=0)
    if isinstance(v, float) and 0 <= v < 1:                    # fracción de día de Excel
        sec = round(v * 86400)
        return time(sec // 3600, (sec % 3600) // 60, sec % 60)
    s = _norm(v).replace(".", "").replace(" ", "")
    pm = s.endswith("pm") or s.endswith("pm")
    am = s.endswith("am")
    s = re.sub(r"(am|pm)$", "", s)
    parts = [int(x) for x in s.split(":")]
    h, mi, se = (parts + [0, 0])[:3]
    if pm and h < 12:
        h += 12
    if am and h == 12:
        h = 0
    return time(h, mi, se)


def parse_fecha_hora(txt: str, orden: str = "dmy") -> datetime:
    t = str(txt).strip()
    m = re.match(r"^(\S+)\s+(.+)$", t)
    if not m:
        raise ValueError(f"fecha-hora no reconocida: {t!r}")
    return datetime.combine(parse_fecha(m.group(1), orden), parse_hora(m.group(2)))


def _ident(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    s = str(v).strip()
    return s.lstrip("0") or "0" if s.isdigit() else s


def _decodificar(b: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace")


def _fila_a_marca(f, m, orden, rechazos, n_fila) -> RegMarca | None:
    def g(k):
        i = m.get(k)
        return f[i] if i is not None and i < len(f) and f[i] is not None else ""
    try:
        ident = _ident(g("id"))
        if not ident:
            return None
        if "fechahora" in m:
            v = g("fechahora")
            fh = v if isinstance(v, datetime) else parse_fecha_hora(v, orden)
        else:
            fh = datetime.combine(parse_fecha(g("fecha"), orden), parse_hora(g("hora")))
        return RegMarca(ident, fh, str(g("tipo")).strip(), str(g("metodo")).strip(), str(g("dispositivo")).strip())
    except (ValueError, TypeError, IndexError) as e:
        rechazos.append(f"fila {n_fila}: {e}")
        return None


def _parse_xlsx(data: bytes, orden: str):
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise ValueError("No se pudo leer el archivo Excel (¿está dañado o no es .xlsx?)")
    regs: list[RegMarca] = []
    rechazos: list[str] = []
    usadas = 0
    for ws in wb.worksheets:
        filas = list(ws.iter_rows(values_only=True))
        m, h = None, -1
        for i, f in enumerate(filas[:25]):
            m = _mapa_cabecera(f)
            if m:
                h = i
                break
        if not m:
            continue
        usadas += 1
        for i, f in enumerate(filas[h + 1:], start=h + 2):
            if f is None or all(c in (None, "") for c in f):
                continue
            r = _fila_a_marca(f, m, orden, rechazos, f"{ws.title}!{i}")
            if r:
                regs.append(r)
    if not usadas:
        raise ValueError("El Excel no contiene una hoja con columnas de ID, Fecha y Hora de marcaciones")
    return "XLSX", regs, rechazos


def _parse_texto(data: bytes, orden: str):
    txt = _decodificar(data)
    lineas = [l for l in txt.splitlines() if l.strip()]
    if not lineas:
        raise ValueError("Archivo vacío")
    muestra = lineas[:10]
    delim = max([",", ";", "\t", "|"], key=lambda d: sum(l.count(d) for l in muestra))
    if sum(l.count(delim) for l in muestra) == 0:
        delim = None                      # separado por espacios (ATTLOG con espacios)
    split = (lambda l: next(csv.reader([l], delimiter=delim))) if delim else (lambda l: l.split())
    regs: list[RegMarca] = []
    rechazos: list[str] = []
    m = _mapa_cabecera(split(lineas[0]))
    if m:
        for n, l in enumerate(lineas[1:], start=2):
            r = _fila_a_marca(split(l), m, orden, rechazos, n)
            if r:
                regs.append(r)
        return "CSV" if delim in (",", ";", "|") else "TXT", regs, rechazos
    # sin cabecera: ZKTeco ATTLOG  -> ID, "fecha hora", verificación, estado, ...
    for n, l in enumerate(lineas, start=1):
        t = [x.strip() for x in split(l)]
        try:
            ident = _ident(t[0])
            if re.match(r"^\d{4}-\d{2}-\d{2}$", t[1]) and len(t) > 2 and re.match(r"^\d{1,2}:\d{2}", t[2]):
                fh = parse_fecha_hora(f"{t[1]} {t[2]}", orden)
                resto = t[3:]
            else:
                fh = parse_fecha_hora(t[1], orden)
                resto = t[2:]
            verify = resto[0] if len(resto) > 0 else ""
            status = resto[1] if len(resto) > 1 else ""
            regs.append(RegMarca(ident, fh, ZK_STATUS.get(status, status), ZK_VERIFY.get(verify, verify), "ZKTeco"))
        except (ValueError, IndexError) as e:
            rechazos.append(f"línea {n}: {e}")
    return "ZK_ATTLOG", regs, rechazos


def parsear_biometrico(nombre: str, data: bytes, orden_fecha: str = "dmy"):
    """Devuelve (formato, [RegMarca], [mensajes_de_rechazo])."""
    if nombre.lower().endswith((".xlsx", ".xlsm")):
        return _parse_xlsx(data, orden_fecha)
    return _parse_texto(data, orden_fecha)
