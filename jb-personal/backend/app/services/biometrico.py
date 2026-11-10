"""Lectura de marcaciones biométricas con estructuras DIFERENTES según la marca del reloj.

Tres capas (de menor a mayor esfuerzo del usuario):
  1. AUTODETECCIÓN: ZKTeco ATTLOG (sin cabecera), y archivos con cabecera (.csv/.txt/.xlsx) cuyas columnas se
     reconocen por nombre (español/inglés: ID, Person ID, Employee No, Fecha, Date, Hora, Time, Date/Time...).
  2. PERFIL DE MAPEO: el usuario indica qué columna es el ID, la fecha, la hora, etc., el delimitador, la fila de
     cabecera y el orden de la fecha; el perfil se guarda con un nombre y se reutiliza (tabla perfil_biometrico).
  3. ESTRUCTURA ANCHA: una fila por persona y día con VARIAS columnas de hora (Entrada1, Salida1, Entrada2…).
La columna "Estado / Incidencia" del reloj se IGNORA: el sistema recalcula todo con sus propias reglas.

Un perfil es un dict:
  {"estructura": "largo"|"ancho", "delimitador": "auto"|","|";"|"\\t"|"|"|"espacio", "fila_cabecera": 0..n (0 = sin cabecera),
   "hoja": nombre de hoja (xlsx) o null, "orden_fecha": "dmy"|"mdy"|"ymd", "formato_fechahora": strptime opcional,
   "columnas": {"id": i, "fecha": i, "hora": i, "fechahora": i, "tipo": i, "metodo": i, "dispositivo": i},   (0 = 1ª columna)
   "horas": [i, j, ...]   (solo estructura ancha),   "codigos": "zk"|null}
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
CAMPOS = ("id", "fecha", "hora", "fechahora", "tipo", "metodo", "dispositivo")

ALIAS = {
    "id": {"id", "id empleado", "idempleado", "id de empleado", "codigo", "cod", "ci", "c.i.", "c.i", "no", "no.", "nro", "numero",
           "person id", "personid", "user id", "userid", "pin", "enroll number", "enrollnumber", "empleado id", "id de persona",
           "id usuario", "employee id", "employee no", "employee number", "emp no", "emp. no", "emp id", "user no", "staff id", "badge",
           "badge number", "card no", "no de empleado", "n de empleado", "codigo empleado", "codigo de empleado", "id persona"},
    "fecha": {"fecha", "date", "dia", "fecha marcacion", "attendance date", "check date"},
    "hora": {"hora", "time of day", "hora marcacion", "check time", "punch time of day"},
    "fechahora": {"fecha y hora", "fecha/hora", "fecha hora", "datetime", "date time", "date/time", "timestamp", "time", "tiempo",
                  "hora de marcacion", "punch time", "fecha y hora de marcacion", "attendance time", "check time", "authentication date and time",
                  "event time", "clock time", "date and time"},
    "tipo": {"tipo de marcacion", "tipo marcacion", "tipo", "evento", "tipo de evento", "punch", "state", "status", "punch state",
             "check type", "attendance status", "in/out", "entrada/salida", "direction", "event type"},
    "metodo": {"metodo verificacion", "metodo de verificacion", "verificacion", "verify", "verification", "verify mode",
               "verify type", "modo", "metodo", "authentication type", "auth mode"},
    "dispositivo": {"dispositivo", "device", "terminal", "reloj", "device name", "equipo", "device id", "device sn", "machine"},
    "horas_ent": {"entrada", "entrada 1", "entrada1", "ent", "ent 1", "in", "in 1", "check in", "check-in", "hora entrada", "entrada manana", "ent manana"},
}

DELIMS = {",": ",", ";": ";", "\\t": "\t", "tab": "\t", "|": "|"}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", s)


# --------------------------------------------------------------------------- parseo de fechas y horas
_FECHAS = [("%Y-%m-%d", None), ("%Y/%m/%d", None), ("%d/%m/%Y", "dmy"), ("%d-%m-%Y", "dmy"), ("%d.%m.%Y", "dmy"),
           ("%d/%m/%y", "dmy"), ("%d-%m-%y", "dmy"), ("%m/%d/%Y", "mdy"), ("%m-%d-%Y", "mdy"), ("%m/%d/%y", "mdy"),
           ("%y/%m/%d", "ymd"), ("%y-%m-%d", "ymd"), ("%Y%m%d", None)]


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
    pm, am = s.endswith("pm"), s.endswith("am")
    s = re.sub(r"(am|pm)$", "", s)
    parts = [int(x) for x in s.split(":")]
    h, mi, se = (parts + [0, 0])[:3]
    if pm and h < 12:
        h += 12
    if am and h == 12:
        h = 0
    return time(h, mi, se)


def parse_fecha_hora(txt, orden: str = "dmy", formato: str | None = None) -> datetime:
    if isinstance(txt, datetime):
        return txt.replace(microsecond=0)
    t = str(txt).strip()
    if formato:
        try:
            return datetime.strptime(t, formato)
        except ValueError:
            raise ValueError(f"no coincide con el formato {formato}: {t!r}")
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
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            txt = b.decode(enc)
            if enc == "utf-16" and "\x00" in txt:
                continue
            return txt
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace")


# --------------------------------------------------------------------------- lectura de filas crudas
def _delim_auto(lineas: list[str]) -> str | None:
    muestra = lineas[:10]
    d = max([",", ";", "\t", "|"], key=lambda x: sum(l.count(x) for l in muestra))
    return d if sum(l.count(d) for l in muestra) else None


def _filas_texto(data: bytes, delimitador: str = "auto") -> tuple[list[list[str]], str]:
    lineas = [l for l in _decodificar(data).splitlines() if l.strip()]
    if not lineas:
        raise ValueError("Archivo vacío")
    if delimitador == "auto":
        d = _delim_auto(lineas)
    elif delimitador == "espacio":
        d = None
    else:
        d = DELIMS.get(delimitador, delimitador)
    if d:
        return [next(csv.reader([l], delimiter=d)) for l in lineas], (d if d != "\t" else "\\t")
    return [l.split() for l in lineas], "espacio"


def _hojas_xlsx(data: bytes) -> dict[str, list[list]]:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise ValueError("No se pudo leer el archivo Excel (¿está dañado o no es .xlsx?)")
    return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}


def _vacia(f) -> bool:
    return f is None or all(c in (None, "") for c in f)


# --------------------------------------------------------------------------- autodetección
def _en(n: str, k: str) -> bool:
    return n in ALIAS[k] or n.replace(".", "") in ALIAS[k]


def _mapa_cabecera(celdas) -> dict[str, int] | None:
    m: dict[str, int] = {}
    nombres: dict[str, str] = {}
    for i, c in enumerate(celdas):
        n = _norm(c)
        if not n or "incidencia" in n:
            continue
        for k in ("id", "fecha", "hora", "fechahora", "tipo", "metodo", "dispositivo"):
            if _en(n, k) and k not in m:
                m[k], nombres[k] = i, n
                break
    if "id" not in m:
        return None
    if "hora" in m and "fecha" not in m and "fechahora" in m:     # "Time" suelto = fecha-hora
        del m["hora"]
    # hay una columna de fecha aparte y la "fecha-hora" es en realidad un "Time"/"Tiempo" suelto => es la hora
    if "fecha" in m and "hora" not in m and nombres.get("fechahora") in ("time", "tiempo"):
        m["hora"] = m.pop("fechahora")
    if "fechahora" in m or ("fecha" in m and "hora" in m):
        return m
    return None


def _mapa_ancho(celdas) -> tuple[dict[str, int], list[int]] | None:
    """Cabecera con ID + Fecha + varias columnas de hora (Entrada/Salida...)."""
    m: dict[str, int] = {}
    horas: list[int] = []
    for i, c in enumerate(celdas):
        n = _norm(c)
        if not n:
            continue
        if _en(n, "id") and "id" not in m:
            m["id"] = i
        elif _en(n, "fecha") and "fecha" not in m:
            m["fecha"] = i
        elif re.match(r"^(entrada|salida|ent|sal|in|out)\s*\d?\b", n) or re.match(r"^(entrada|salida)\b", n):
            horas.append(i)
    if "id" in m and "fecha" in m and len(horas) >= 2:
        return m, horas
    return None


def _perfil_base(**kw) -> dict:
    p = {"estructura": "largo", "delimitador": "auto", "fila_cabecera": 0, "hoja": None, "orden_fecha": "dmy",
         "formato_fechahora": None, "columnas": {}, "horas": [], "codigos": None}
    p.update(kw)
    return p


def _detectar_en_filas(filas: list[list], orden: str, hoja: str | None, delim: str) -> dict | None:
    for i, f in enumerate(filas[:25]):
        if _vacia(f):
            continue
        m = _mapa_cabecera(f)
        if m:
            return _perfil_base(fila_cabecera=i + 1, columnas=m, hoja=hoja, delimitador=delim, orden_fecha=orden)
        w = _mapa_ancho(f)
        if w:
            return _perfil_base(estructura="ancho", fila_cabecera=i + 1, columnas=w[0], horas=w[1], hoja=hoja,
                                delimitador=delim, orden_fecha=orden)
    return None


def _detectar_zk(filas: list[list], orden: str, delim: str) -> dict | None:
    """ATTLOG sin cabecera: ID, 'AAAA-MM-DD HH:MM:SS' (o fecha y hora en columnas separadas), verificación, estado..."""
    f = next((x for x in filas if not _vacia(x)), None)
    if not f or len(f) < 2:
        return None
    t = [str(x).strip() for x in f]
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", t[1]) and len(t) > 2 and re.match(r"^\d{1,2}:\d{2}", t[2]):
            parse_fecha_hora(f"{t[1]} {t[2]}", orden)
            return _perfil_base(delimitador=delim, orden_fecha=orden, codigos="zk",
                                columnas={"id": 0, "fecha": 1, "hora": 2, "metodo": 3, "tipo": 4})
        parse_fecha_hora(t[1], orden)
        return _perfil_base(delimitador=delim, orden_fecha=orden, codigos="zk",
                            columnas={"id": 0, "fechahora": 1, "metodo": 2, "tipo": 3})
    except (ValueError, IndexError):
        return None


def analizar(nombre: str, data: bytes, orden_fecha: str = "dmy", delimitador: str = "auto") -> dict:
    """Detecta la estructura y devuelve el perfil sugerido y una muestra de filas para que el usuario lo ajuste."""
    es_xlsx = nombre.lower().endswith((".xlsx", ".xlsm"))
    if es_xlsx:
        hojas = _hojas_xlsx(data)
        perfil, hoja_ok = None, None
        for nom, filas in hojas.items():
            perfil = _detectar_en_filas(filas, orden_fecha, nom, "auto")
            if perfil:
                hoja_ok = nom
                break
        hoja = hoja_ok or next(iter(hojas))
        filas = hojas[hoja]
        formato, delim = "XLSX", "auto"
        nombres_hojas = list(hojas)
    else:
        filas, delim = _filas_texto(data, delimitador)
        perfil = _detectar_en_filas(filas, orden_fecha, None, delim) or _detectar_zk(filas, orden_fecha, delim)
        formato = "ZK_ATTLOG" if perfil and perfil.get("codigos") == "zk" else ("TXT" if delim in ("\\t", "espacio") else "CSV")
        nombres_hojas = []
        hoja = None
    muestra = [[("" if c is None else str(c)) for c in f] for f in filas[:25]]
    if not perfil and muestra:       # sin estructura reconocida: sugerir la 1ª fila como cabecera si no parece un dato (fecha/hora)
        if not any(re.search(r"\d{1,2}[:/.-]\d{1,2}", c) for c in muestra[0]):
            base_cab = 1
        else:
            base_cab = 0
    else:
        base_cab = 0
    return {"formato": formato, "delimitador": delim, "hojas": nombres_hojas, "hoja": hoja,
            "detectado": perfil is not None, "perfil": perfil or _perfil_base(delimitador=delim, hoja=hoja, orden_fecha=orden_fecha, fila_cabecera=base_cab),
            "muestra": muestra, "n_columnas": max((len(f) for f in muestra), default=0)}


# --------------------------------------------------------------------------- aplicación de un perfil
def validar_perfil(p: dict) -> dict:
    base = _perfil_base()
    base.update({k: v for k, v in (p or {}).items() if k in base})
    if base["estructura"] not in ("largo", "ancho"):
        raise ValueError("estructura debe ser 'largo' o 'ancho'")
    if base["orden_fecha"] not in ("dmy", "mdy", "ymd"):
        raise ValueError("orden_fecha debe ser dmy, mdy o ymd")
    cols = {k: int(v) for k, v in (base["columnas"] or {}).items() if k in CAMPOS and v not in (None, "")}
    if any(v < 0 for v in cols.values()):
        raise ValueError("los índices de columna no pueden ser negativos")
    base["columnas"] = cols
    base["horas"] = [int(x) for x in (base["horas"] or [])]
    base["fila_cabecera"] = int(base["fila_cabecera"] or 0)
    if "id" not in cols:
        raise ValueError("Indique la columna del ID/código del empleado")
    if base["estructura"] == "largo":
        if not ("fechahora" in cols or ("fecha" in cols and "hora" in cols)):
            raise ValueError("Indique la columna 'Fecha y hora' o bien 'Fecha' y 'Hora' por separado")
    else:
        if "fecha" not in cols or not base["horas"]:
            raise ValueError("En estructura ancha indique la columna de fecha y al menos una columna de hora")
    if base["formato_fechahora"]:
        try:
            datetime.now().strftime(base["formato_fechahora"])
        except Exception:
            raise ValueError("formato_fechahora inválido (ej.: %d/%m/%Y %H:%M:%S)")
    return base


def _celda(f, i):
    return f[i] if i is not None and i < len(f) and f[i] is not None else ""


def _extraer(filas: list[list], p: dict) -> tuple[list[RegMarca], list[str]]:
    c, orden, fmt = p["columnas"], p["orden_fecha"], p.get("formato_fechahora")
    regs: list[RegMarca] = []
    rech: list[str] = []
    ini = p["fila_cabecera"]               # 1-based; los datos empiezan en la fila siguiente (índice 0-based = ini)
    zk = p.get("codigos") == "zk"
    for n, f in enumerate(filas[ini:], start=ini + 1):
        if _vacia(f):
            continue
        try:
            ident = _ident(_celda(f, c["id"]))
            if not ident:
                continue
            tipo, met, disp = (str(_celda(f, c.get(k))).strip() for k in ("tipo", "metodo", "dispositivo"))
            if zk:
                tipo, met = ZK_STATUS.get(tipo, tipo), ZK_VERIFY.get(met, met)
                disp = disp or "ZKTeco"
            if p["estructura"] == "ancho":
                d = parse_fecha(_celda(f, c["fecha"]), orden)
                nuevas = 0
                for hi in p["horas"]:
                    v = _celda(f, hi)
                    if v in ("", None):
                        continue
                    try:
                        h = parse_hora(v)
                    except (ValueError, TypeError):
                        continue           # "SIN MARCA", "—", etc.
                    regs.append(RegMarca(ident, datetime.combine(d, h), tipo, met, disp))
                    nuevas += 1
                continue
            if "fechahora" in c:
                fh = parse_fecha_hora(_celda(f, c["fechahora"]), orden, fmt)
            else:
                fh = datetime.combine(parse_fecha(_celda(f, c["fecha"]), orden), parse_hora(_celda(f, c["hora"])))
            regs.append(RegMarca(ident, fh, tipo, met, disp))
        except (ValueError, TypeError, IndexError) as e:
            rech.append(f"fila {n}: {e}")
    return regs, rech


def parsear_con_perfil(nombre: str, data: bytes, perfil: dict):
    p = validar_perfil(perfil)
    if nombre.lower().endswith((".xlsx", ".xlsm")):
        hojas = _hojas_xlsx(data)
        if p["hoja"] and p["hoja"] in hojas:
            sel = {p["hoja"]: hojas[p["hoja"]]}
        else:
            sel = hojas if not p["hoja"] else {next(iter(hojas)): next(iter(hojas.values()))}
        regs, rech = [], []
        for nom, filas in sel.items():
            r, x = _extraer(filas, p)
            regs += r
            rech += [f"{nom}!{m}" for m in x]
        return "XLSX", regs, rech
    filas, _ = _filas_texto(data, p["delimitador"])
    regs, rech = _extraer(filas, p)
    return ("ZK_ATTLOG" if p.get("codigos") == "zk" else "CSV"), regs, rech


def parsear_biometrico(nombre: str, data: bytes, orden_fecha: str = "dmy", perfil: dict | None = None):
    """Devuelve (formato, [RegMarca], [mensajes_de_rechazo]). Sin perfil: autodetección."""
    if perfil:
        return parsear_con_perfil(nombre, data, perfil)
    a = analizar(nombre, data, orden_fecha)
    if not a["detectado"]:
        raise ValueError("No se reconoció la estructura del archivo (se necesitan columnas de ID, Fecha y Hora). "
                         "Use «Analizar estructura» para indicar manualmente qué columna es cada dato y guarde un perfil")
    fmt, regs, rech = parsear_con_perfil(nombre, data, a["perfil"])
    return (a["formato"] if a["formato"] != "XLSX" else fmt), regs, rech
